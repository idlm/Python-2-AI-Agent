"""受控异步 API 客户端（版本 0.1.0）。

本模块只允许已审查 HTTPS 基址下的 GET JSON 请求。它不接受任意认证头、
任意方法、无限重试或无限响应；网络错误、重试和日志均不记录查询参数、响应
正文或秘密头。
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Final

import httpx

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
_RETRYABLE_STATUS_CODES: Final[frozenset[int]] = frozenset({408, 429, 500, 502, 503, 504})


class CollectionError(Exception):
    """采集器向调用方公开的受控失败基类。"""


class EndpointRejectedError(CollectionError):
    """路径、协议或主机不在当前采集合同内。"""


class UpstreamTransportError(CollectionError):
    """连接、读取、写入、池等待或协议层请求失败。"""


class UpstreamResponseError(CollectionError):
    """上游返回非成功状态，或重试已耗尽。"""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"上游服务返回状态码 {status_code}。")
        self.status_code = status_code


class ResponseTooLargeError(CollectionError):
    """响应正文超过当前采集规则允许的字节数。"""


class UnexpectedContentTypeError(CollectionError):
    """成功响应不是调用方约定的 JSON 类型。"""


class InvalidJsonResponseError(CollectionError):
    """响应声称是 JSON，但其内容无法解析为对象。"""


@dataclass(frozen=True)
class RetryPolicy:
    """只为幂等 GET 定义有限的、可测试的重试退避。"""

    max_attempts: int = 3
    base_delay_seconds: float = 0.1
    max_delay_seconds: float = 1.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("最大尝试次数至少为 1。")
        if self.base_delay_seconds < 0 or self.max_delay_seconds < 0:
            raise ValueError("重试延时不能为负数。")
        if self.base_delay_seconds > self.max_delay_seconds:
            raise ValueError("基础延时不能大于最大延时。")

    def delay_for_retry(self, failed_attempt: int) -> float:
        """返回确定性指数退避；第 1 次失败后的延时为基础延时。"""
        if failed_attempt < 1:
            raise ValueError("失败次数至少为 1。")
        return float(
            min(self.base_delay_seconds * (2 ** (failed_attempt - 1)), self.max_delay_seconds)
        )


@dataclass(frozen=True)
class ClientPolicy:
    """构造客户端时必须明确的目标、资源与内容边界。"""

    base_url: str
    allowed_hosts: frozenset[str]
    user_agent: str
    connect_timeout_seconds: float = 2.0
    read_timeout_seconds: float = 5.0
    write_timeout_seconds: float = 5.0
    pool_timeout_seconds: float = 2.0
    max_connections: int = 4
    max_keepalive_connections: int = 2
    max_response_bytes: int = 1_000_000

    def __post_init__(self) -> None:
        base = httpx.URL(self.base_url)
        if base.scheme != "https" or not base.host:
            raise ValueError("采集基址必须是带主机名的 HTTPS URL。")
        if base.host not in self.allowed_hosts:
            raise ValueError("采集基址主机必须出现在允许列表中。")
        if not self.user_agent.strip():
            raise ValueError("User-Agent 不能为空。")
        if self.max_connections < 1 or self.max_keepalive_connections < 0:
            raise ValueError("连接限制不合法。")
        if self.max_keepalive_connections > self.max_connections:
            raise ValueError("保持连接数不能超过最大连接数。")
        if self.max_response_bytes < 1:
            raise ValueError("最大响应字节数至少为 1。")
        for timeout in (
            self.connect_timeout_seconds,
            self.read_timeout_seconds,
            self.write_timeout_seconds,
            self.pool_timeout_seconds,
        ):
            if timeout <= 0:
                raise ValueError("所有网络超时时间必须大于零。")


def build_async_client(
    policy: ClientPolicy, *, transport: httpx.AsyncBaseTransport | None = None
) -> httpx.AsyncClient:
    """以明确超时、连接池和用户代理构造一个可在批次内复用的客户端。"""
    timeout = httpx.Timeout(
        connect=policy.connect_timeout_seconds,
        read=policy.read_timeout_seconds,
        write=policy.write_timeout_seconds,
        pool=policy.pool_timeout_seconds,
    )
    limits = httpx.Limits(
        max_connections=policy.max_connections,
        max_keepalive_connections=policy.max_keepalive_connections,
    )
    return httpx.AsyncClient(
        base_url=policy.base_url,
        headers={"User-Agent": policy.user_agent},
        timeout=timeout,
        limits=limits,
        follow_redirects=False,
        transport=transport,
    )


class SafeApiClient:
    """将 HTTPX 的传输细节适配为受控 JSON 采集合同。"""

    def __init__(
        self,
        client: httpx.AsyncClient,
        policy: ClientPolicy,
        retry_policy: RetryPolicy | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._client = client
        self._policy = policy
        self._retry_policy = retry_policy or RetryPolicy()
        self._sleep = sleep

    async def get_json(
        self, endpoint: str, *, params: Mapping[str, str] | None = None
    ) -> dict[str, object]:
        """获取一个小型 JSON 对象；只对约定的可重试失败做有限重试。"""
        self._validate_endpoint(endpoint)
        for attempt in range(1, self._retry_policy.max_attempts + 1):
            try:
                outcome = await self._request_once(endpoint, params=params)
            except httpx.TransportError as exc:
                if attempt == self._retry_policy.max_attempts:
                    raise UpstreamTransportError("无法完成到上游服务的网络请求。") from exc
                await self._wait_before_retry(attempt, reason="transport")
                continue
            if isinstance(outcome, int):
                if attempt == self._retry_policy.max_attempts:
                    raise UpstreamResponseError(outcome)
                await self._wait_before_retry(attempt, reason=f"status_{outcome}")
                continue
            return outcome
        raise AssertionError("有限重试循环必须在返回或抛出前结束。")

    def _validate_endpoint(self, endpoint: str) -> None:
        if not endpoint.startswith("/") or endpoint.startswith("//"):
            raise EndpointRejectedError("端点必须是基址下的绝对路径。")
        candidate = self._client.build_request("GET", endpoint).url
        if candidate.scheme != "https" or candidate.host not in self._policy.allowed_hosts:
            raise EndpointRejectedError("端点不在允许的 HTTPS 主机范围内。")

    async def _request_once(
        self, endpoint: str, *, params: Mapping[str, str] | None
    ) -> dict[str, object] | int:
        async with self._client.stream("GET", endpoint, params=params) as response:
            if response.status_code in _RETRYABLE_STATUS_CODES:
                LOGGER.warning(
                    "collector_upstream_retryable_status host=%s path=%s status=%s",
                    response.request.url.host,
                    response.request.url.path,
                    response.status_code,
                )
                return response.status_code
            if response.is_error:
                raise UpstreamResponseError(response.status_code)
            content_type = response.headers.get("content-type", "").lower()
            is_json_content = "application/json" in content_type or "+json" in content_type
            if not is_json_content:
                raise UnexpectedContentTypeError("上游成功响应不是 JSON 内容类型。")
            body = await self._read_bounded_body(response)
        return self._decode_json_object(body)

    async def _read_bounded_body(self, response: httpx.Response) -> bytes:
        chunks: list[bytes] = []
        size = 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > self._policy.max_response_bytes:
                raise ResponseTooLargeError("上游响应超过当前大小限制。")
            chunks.append(chunk)
        return b"".join(chunks)

    @staticmethod
    def _decode_json_object(body: bytes) -> dict[str, object]:
        try:
            decoded: object = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidJsonResponseError("上游响应不是有效 JSON 对象。") from exc
        if not isinstance(decoded, dict):
            raise InvalidJsonResponseError("上游 JSON 根节点必须是对象。")
        result: dict[str, object] = {}
        for key, value in decoded.items():
            if not isinstance(key, str):
                raise InvalidJsonResponseError("上游 JSON 对象含有无效键。")
            result[key] = value
        return result

    async def _wait_before_retry(self, failed_attempt: int, *, reason: str) -> None:
        delay = self._retry_policy.delay_for_retry(failed_attempt)
        LOGGER.info(
            "collector_retry_scheduled attempt=%s delay_seconds=%s reason=%s",
            failed_attempt,
            delay,
            reason,
        )
        await self._sleep(delay)
