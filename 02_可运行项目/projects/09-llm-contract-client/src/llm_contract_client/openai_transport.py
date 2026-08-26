"""OpenAI-compatible Chat Completions 传输适配器。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from .core import PermanentTransportError, TransientTransportError, TransportReply
from .structured import StructuredTransportReply


class OpenAiChatTransport:
    """把已配置环境变量中的 SDK 客户端收敛为课程传输协议。"""

    def __init__(self, client: OpenAI | None = None) -> None:
        self._client = client or OpenAI()

    def complete(
        self,
        *,
        model: str,
        system_prompt: str,
        user_text: str,
        max_output_tokens: int,
    ) -> TransportReply:
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                max_completion_tokens=max_output_tokens,
            )
        except (APIConnectionError, APITimeoutError, RateLimitError, APIError) as exc:
            if isinstance(
                exc,
                (AuthenticationError, BadRequestError, NotFoundError, PermissionDeniedError),
            ):
                raise PermanentTransportError("模型服务拒绝当前受控请求。") from exc
            raise TransientTransportError("模型服务暂时不可用。") from exc
        message = response.choices[0].message if response.choices else None
        content = message.content if message is not None else None
        if not isinstance(content, str):
            raise PermanentTransportError("模型没有返回文本内容。")
        usage = cast(Any, response.usage)
        input_tokens = usage.prompt_tokens if usage is not None else None
        output_tokens = usage.completion_tokens if usage is not None else None
        return TransportReply(
            text=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def complete_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_text: str,
        max_output_tokens: int,
        schema_name: str,
        schema: Mapping[str, object],
    ) -> StructuredTransportReply:
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                max_completion_tokens=max_output_tokens,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "strict": True,
                        "schema": dict(schema),
                    },
                },
            )
        except (APIConnectionError, APITimeoutError, RateLimitError, APIError) as exc:
            if isinstance(
                exc,
                (AuthenticationError, BadRequestError, NotFoundError, PermissionDeniedError),
            ):
                raise PermanentTransportError("结构化模型服务拒绝当前受控请求。") from exc
            raise TransientTransportError("结构化模型服务暂时不可用。") from exc
        message = response.choices[0].message if response.choices else None
        refusal = getattr(message, "refusal", None) if message is not None else None
        if isinstance(refusal, str) and refusal:
            raise PermanentTransportError("模型拒绝了当前结构化请求。")
        content = message.content if message is not None else None
        if not isinstance(content, str):
            raise PermanentTransportError("模型没有返回结构化文本内容。")
        usage = cast(Any, response.usage)
        input_tokens = usage.prompt_tokens if usage is not None else None
        output_tokens = usage.completion_tokens if usage is not None else None
        return StructuredTransportReply(
            json_text=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
