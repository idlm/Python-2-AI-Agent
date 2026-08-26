"""受控 HTTP 客户端的确定性测试。"""

import asyncio
import logging

import httpx
import pytest

from polite_api_collector.client import (
    ClientPolicy,
    EndpointRejectedError,
    InvalidJsonResponseError,
    ResponseTooLargeError,
    RetryPolicy,
    SafeApiClient,
    UnexpectedContentTypeError,
    UpstreamResponseError,
    UpstreamTransportError,
    build_async_client,
)

BASE_URL = "https://api.example.test"


def policy(**overrides: object) -> ClientPolicy:
    values: dict[str, object] = {
        "base_url": BASE_URL,
        "allowed_hosts": frozenset({"api.example.test"}),
        "user_agent": "python-private-course-collector/0.1",
        "max_response_bytes": 1_000,
    }
    values.update(overrides)
    return ClientPolicy(**values)  # type: ignore[arg-type]


def run(coroutine: object) -> object:
    return asyncio.run(coroutine)  # type: ignore[arg-type]


def test_get_json_returns_json_object_and_sends_user_agent() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["User-Agent"] == "python-private-course-collector/0.1"
        assert request.url.path == "/records"
        assert request.url.query == b"page=1"
        return httpx.Response(200, json={"items": ["one"]}, request=request)

    async def scenario() -> dict[str, object]:
        async with build_async_client(policy(), transport=httpx.MockTransport(handler)) as client:
            return await SafeApiClient(client, policy()).get_json("/records", params={"page": "1"})

    assert run(scenario()) == {"items": ["one"]}


def test_retries_retryable_status_with_bounded_backoff() -> None:
    attempts = 0
    delays: list[float] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(503, request=request)
        return httpx.Response(200, json={"ok": True}, request=request)

    async def sleeper(delay: float) -> None:
        delays.append(delay)

    async def scenario() -> dict[str, object]:
        async with build_async_client(policy(), transport=httpx.MockTransport(handler)) as client:
            collector = SafeApiClient(
                client,
                policy(),
                RetryPolicy(max_attempts=3, base_delay_seconds=0.1, max_delay_seconds=0.2),
                sleep=sleeper,
            )
            return await collector.get_json("/retry")

    assert run(scenario()) == {"ok": True}
    assert attempts == 3
    assert delays == [0.1, 0.2]


def test_transport_failure_retries_then_exposes_controlled_error() -> None:
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectError("offline", request=request)

    async def no_wait(_: float) -> None:
        return None

    async def scenario() -> None:
        async with build_async_client(policy(), transport=httpx.MockTransport(handler)) as client:
            collector = SafeApiClient(
                client,
                policy(),
                RetryPolicy(max_attempts=2, base_delay_seconds=0, max_delay_seconds=0),
                sleep=no_wait,
            )
            await collector.get_json("/offline")

    with pytest.raises(UpstreamTransportError):
        run(scenario())
    assert attempts == 2


def test_non_retryable_status_is_not_retried() -> None:
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(404, request=request)

    async def scenario() -> None:
        async with build_async_client(policy(), transport=httpx.MockTransport(handler)) as client:
            await SafeApiClient(client, policy()).get_json("/missing")

    with pytest.raises(UpstreamResponseError) as error:
        run(scenario())
    assert error.value.status_code == 404
    assert attempts == 1


@pytest.mark.parametrize("endpoint", ["records", "//other.example.test/data", "https://other.example.test/data"])
def test_rejects_uncontrolled_endpoint(endpoint: str) -> None:
    async def scenario() -> None:
        async with build_async_client(
            policy(), transport=httpx.MockTransport(lambda _: None)
        ) as client:
            await SafeApiClient(client, policy()).get_json(endpoint)

    with pytest.raises(EndpointRejectedError):
        run(scenario())


def test_rejects_response_larger_than_policy() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b'{"too_long": true}',
            headers={"content-type": "application/json"},
            request=request,
        )

    async def scenario() -> None:
        small_policy = policy(max_response_bytes=8)
        async with build_async_client(
            small_policy, transport=httpx.MockTransport(handler)
        ) as client:
            await SafeApiClient(client, small_policy).get_json("/large")

    with pytest.raises(ResponseTooLargeError):
        run(scenario())


def test_rejects_unexpected_content_type_and_non_object_json() -> None:
    async def text_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json", request=request)

    async def list_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["not", "an object"], request=request)

    async def text_scenario() -> None:
        async with build_async_client(
            policy(), transport=httpx.MockTransport(text_handler)
        ) as client:
            await SafeApiClient(client, policy()).get_json("/text")

    async def list_scenario() -> None:
        async with build_async_client(
            policy(), transport=httpx.MockTransport(list_handler)
        ) as client:
            await SafeApiClient(client, policy()).get_json("/list")

    with pytest.raises(UnexpectedContentTypeError):
        run(text_scenario())
    with pytest.raises(InvalidJsonResponseError):
        run(list_scenario())


def test_retry_log_does_not_include_query_value(caplog: pytest.LogCaptureFixture) -> None:
    secret = "token-that-must-not-enter-logs"

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, request=request)

    async def no_wait(_: float) -> None:
        return None

    async def scenario() -> None:
        async with build_async_client(policy(), transport=httpx.MockTransport(handler)) as client:
            collector = SafeApiClient(
                client,
                policy(),
                RetryPolicy(max_attempts=2, base_delay_seconds=0, max_delay_seconds=0),
                sleep=no_wait,
            )
            await collector.get_json("/records", params={"api_key": secret})

    caplog.set_level(logging.INFO, logger="polite_api_collector.client")
    with pytest.raises(UpstreamResponseError):
        run(scenario())
    assert secret not in caplog.text
    assert "path=/records" in caplog.text


def test_policy_rejects_unapproved_host_and_invalid_limits() -> None:
    with pytest.raises(ValueError, match="允许列表"):
        policy(allowed_hosts=frozenset({"other.example.test"}))
    with pytest.raises(ValueError, match="连接限制"):
        policy(max_connections=0)
    with pytest.raises(ValueError, match="最大响应"):
        policy(max_response_bytes=0)
