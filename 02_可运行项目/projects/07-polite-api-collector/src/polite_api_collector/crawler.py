"""礼貌、受控的并发 JSON 采集协调器（版本 0.1.0）。

协调器不发现 URL、不绕过 robots、不把并发上限当作访问许可，也不自行保存
结果正文。它只调度调用方已审查的路径，并把并发数、每站起始间隔和 robots
规则显式变成可测试的合同。
"""

from __future__ import annotations

import asyncio
import logging
import time
import urllib.robotparser
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urljoin, urlsplit

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())


class RobotsDeniedError(Exception):
    """robots 规则未允许当前 User-Agent 访问某个已审查端点。"""


class JsonFetcher(Protocol):
    """协调器所需的最小 JSON 读取合同。"""

    async def get_json(
        self, endpoint: str, *, params: Mapping[str, str] | None = None
    ) -> dict[str, object]:
        """读取一个符合上层客户端合同的 JSON 对象。"""


@dataclass(frozen=True)
class PageRequest:
    """一个由代码或受控配置选择的采集单元。"""

    name: str
    endpoint: str
    params: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("采集请求名称不能为空。")
        if not self.endpoint.startswith("/") or self.endpoint.startswith("//"):
            raise ValueError("采集端点必须是单个主机下以 / 开头的路径。")


@dataclass(frozen=True)
class CollectedPage:
    """一项成功采集的明确输出；正文只交给调用方，不写入协调器日志。"""

    name: str
    endpoint: str
    payload: dict[str, object]


@dataclass(frozen=True)
class CrawlPolicy:
    """采集批次的本地并发与节奏限制。"""

    max_concurrency: int = 2
    minimum_interval_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.max_concurrency < 1:
            raise ValueError("最大并发数至少为 1。")
        if self.minimum_interval_seconds < 0:
            raise ValueError("最小请求间隔不能为负数。")


class RobotsGuard:
    """在内存中解析已取得的 robots.txt，不负责网络下载或法律判断。"""

    def __init__(self, *, site_url: str, user_agent: str, robots_text: str) -> None:
        parsed_site = urlsplit(site_url)
        if parsed_site.scheme != "https" or not parsed_site.netloc:
            raise ValueError("robots 站点基址必须是 HTTPS URL。")
        if not user_agent.strip():
            raise ValueError("robots User-Agent 不能为空。")
        self._site_url = site_url
        self._user_agent = user_agent
        parser = urllib.robotparser.RobotFileParser(urljoin(site_url, "/robots.txt"))
        parser.parse(robots_text.splitlines())
        self._parser = parser

    def allows(self, endpoint: str) -> bool:
        """只回答 robots 文件对该 User-Agent 和路径的技术规则结果。"""
        return self._parser.can_fetch(self._user_agent, urljoin(self._site_url, endpoint))

    def crawl_delay_seconds(self) -> float | None:
        """读取 robots 声明的 Crawl-delay；缺失或无效时返回 None。"""
        raw_delay = self._parser.crawl_delay(self._user_agent)
        if raw_delay is None:
            return None
        try:
            return float(raw_delay)
        except (TypeError, ValueError):
            return None


class RequestPacer:
    """以单个异步锁协调一个站点内相邻请求的最小起始间隔。"""

    def __init__(
        self,
        minimum_interval_seconds: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._minimum_interval_seconds = minimum_interval_seconds
        self._clock = clock
        self._sleep = sleep
        self._next_allowed_at = 0.0
        self._lock = asyncio.Lock()

    async def wait_turn(self) -> None:
        """等待并保留下一个请求起始槽；不在网络等待期间持有锁。"""
        async with self._lock:
            now = self._clock()
            wait_seconds = max(0.0, self._next_allowed_at - now)
            if wait_seconds > 0:
                await self._sleep(wait_seconds)
                now = self._clock()
            self._next_allowed_at = max(now, self._next_allowed_at) + self._minimum_interval_seconds


async def collect_pages(
    requests: Sequence[PageRequest],
    *,
    fetcher: JsonFetcher,
    crawl_policy: CrawlPolicy,
    robots_guard: RobotsGuard,
    pacer: RequestPacer | None = None,
) -> list[CollectedPage]:
    """在 robots 预检后，以受限并发和节奏采集固定页面；输出顺序保持输入顺序。"""
    for request in requests:
        if not robots_guard.allows(request.endpoint):
            raise RobotsDeniedError(f"robots 规则不允许访问端点 {request.endpoint}。")
    effective_interval = crawl_policy.minimum_interval_seconds
    declared_delay = robots_guard.crawl_delay_seconds()
    if declared_delay is not None:
        effective_interval = max(effective_interval, declared_delay)
    request_pacer = pacer or RequestPacer(effective_interval)
    semaphore = asyncio.Semaphore(crawl_policy.max_concurrency)
    tasks: list[asyncio.Task[CollectedPage]] = []
    async with asyncio.TaskGroup() as group:
        for request in requests:
            tasks.append(
                group.create_task(
                    _collect_one(
                        request,
                        fetcher=fetcher,
                        semaphore=semaphore,
                        pacer=request_pacer,
                    ),
                    name=request.name,
                )
            )
    return [task.result() for task in tasks]


async def _collect_one(
    request: PageRequest,
    *,
    fetcher: JsonFetcher,
    semaphore: asyncio.Semaphore,
    pacer: RequestPacer,
) -> CollectedPage:
    async with semaphore:
        await pacer.wait_turn()
        LOGGER.info("collector_page_started name=%s path=%s", request.name, request.endpoint)
        payload = await fetcher.get_json(request.endpoint, params=request.params)
    LOGGER.info("collector_page_completed name=%s path=%s", request.name, request.endpoint)
    return CollectedPage(name=request.name, endpoint=request.endpoint, payload=payload)
