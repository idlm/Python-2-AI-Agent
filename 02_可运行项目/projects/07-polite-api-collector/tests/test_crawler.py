"""礼貌并发采集协调器测试。"""

import asyncio
import logging
from collections.abc import Mapping

import pytest

from polite_api_collector.crawler import (
    CollectedPage,
    CrawlPolicy,
    PageRequest,
    RequestPacer,
    RobotsDeniedError,
    RobotsGuard,
    collect_pages,
)

SITE_URL = "https://api.example.test"
USER_AGENT = "course-collector"


def run(coroutine: object) -> object:
    return asyncio.run(coroutine)  # type: ignore[arg-type]


def robots(text: str = "User-agent: *\nAllow: /\n") -> RobotsGuard:
    return RobotsGuard(site_url=SITE_URL, user_agent=USER_AGENT, robots_text=text)


class TrackingFetcher:
    def __init__(
        self,
        *,
        delays: Mapping[str, float] | None = None,
        failure_path: str | None = None,
    ) -> None:
        self.delays = delays or {}
        self.failure_path = failure_path
        self.calls: list[str] = []
        self.active = 0
        self.max_active = 0
        self.cancelled_paths: list[str] = []

    async def get_json(
        self, endpoint: str, *, params: Mapping[str, str] | None = None
    ) -> dict[str, object]:
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        self.calls.append(endpoint)
        try:
            if endpoint == self.failure_path:
                raise RuntimeError("受控采集失败")
            await asyncio.sleep(self.delays.get(endpoint, 0))
            return {"path": endpoint, "params": dict(params or {})}
        except asyncio.CancelledError:
            self.cancelled_paths.append(endpoint)
            raise
        finally:
            self.active -= 1


def test_robots_denial_happens_before_any_fetch() -> None:
    fetcher = TrackingFetcher()

    async def scenario() -> None:
        await collect_pages(
            [PageRequest("private", "/private")],
            fetcher=fetcher,
            crawl_policy=CrawlPolicy(),
            robots_guard=robots("User-agent: *\nDisallow: /private\n"),
        )

    with pytest.raises(RobotsDeniedError):
        run(scenario())
    assert fetcher.calls == []


def test_collection_preserves_input_order_despite_completion_order() -> None:
    fetcher = TrackingFetcher(delays={"/slow": 0.02, "/fast": 0.01})

    async def scenario() -> list[CollectedPage]:
        return await collect_pages(
            [PageRequest("slow", "/slow"), PageRequest("fast", "/fast")],
            fetcher=fetcher,
            crawl_policy=CrawlPolicy(max_concurrency=2),
            robots_guard=robots(),
        )

    pages = run(scenario())

    assert [page.name for page in pages] == ["slow", "fast"]
    assert [page.payload["path"] for page in pages] == ["/slow", "/fast"]


def test_semaphore_limits_active_fetches() -> None:
    fetcher = TrackingFetcher(delays={"/one": 0.02, "/two": 0.02, "/three": 0.02})

    async def scenario() -> None:
        await collect_pages(
            [
                PageRequest("one", "/one"),
                PageRequest("two", "/two"),
                PageRequest("three", "/three"),
            ],
            fetcher=fetcher,
            crawl_policy=CrawlPolicy(max_concurrency=2),
            robots_guard=robots(),
        )

    run(scenario())

    assert fetcher.max_active == 2


def test_pacer_waits_before_second_request_start() -> None:
    clock_values = iter([0.0, 0.3, 1.0])
    delays: list[float] = []

    def clock() -> float:
        return next(clock_values)

    async def sleeper(delay: float) -> None:
        delays.append(delay)

    async def scenario() -> None:
        pacer = RequestPacer(1.0, clock=clock, sleep=sleeper)
        await pacer.wait_turn()
        await pacer.wait_turn()

    run(scenario())

    assert delays == [0.7]


def test_robots_crawl_delay_is_exposed_for_policy_combination() -> None:
    guard = robots("User-agent: course-collector\nCrawl-delay: 3\nAllow: /\n")

    assert guard.crawl_delay_seconds() == 3
    assert guard.allows("/allowed") is True


def test_failure_cancels_sibling_task() -> None:
    fetcher = TrackingFetcher(delays={"/slow": 0.2}, failure_path="/broken")

    async def scenario() -> None:
        await collect_pages(
            [PageRequest("broken", "/broken"), PageRequest("slow", "/slow")],
            fetcher=fetcher,
            crawl_policy=CrawlPolicy(max_concurrency=2),
            robots_guard=robots(),
        )

    with pytest.raises(ExceptionGroup):
        run(scenario())
    assert "/slow" in fetcher.cancelled_paths


def test_logs_do_not_include_collected_payload(caplog: pytest.LogCaptureFixture) -> None:
    secret = "采集结果正文绝不进入日志"
    fetcher = TrackingFetcher()

    async def scenario() -> None:
        await collect_pages(
            [PageRequest("public", "/public", {"q": secret})],
            fetcher=fetcher,
            crawl_policy=CrawlPolicy(),
            robots_guard=robots(),
        )

    caplog.set_level(logging.INFO, logger="polite_api_collector.crawler")
    run(scenario())

    assert "collector_page_completed name=public path=/public" in caplog.text
    assert secret not in caplog.text


def test_request_and_policy_validate_local_boundaries() -> None:
    with pytest.raises(ValueError):
        PageRequest("", "/records")
    with pytest.raises(ValueError):
        PageRequest("cross-host", "//other.example.test/records")
    with pytest.raises(ValueError):
        CrawlPolicy(max_concurrency=0)
    with pytest.raises(ValueError):
        CrawlPolicy(minimum_interval_seconds=-0.1)
