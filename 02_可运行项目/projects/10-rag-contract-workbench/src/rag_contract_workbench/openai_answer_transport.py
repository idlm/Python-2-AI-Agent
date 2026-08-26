"""OpenAI-compatible 的来源约束回答传输适配器。"""

from __future__ import annotations

from typing import Any, Final, cast

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

from .answering import StructuredAnswerTransport

_ALLOWED_MODEL: Final[str] = "gpt-5-mini"
_MAX_OUTPUT_TOKENS: Final[int] = 360


class AnswerTransportUnavailableError(RuntimeError):
    """短暂的供应商/网络故障；调用方可按受控策略决定是否重试。"""


class AnswerTransportRejectedError(RuntimeError):
    """永久请求、拒答或输出边界失败；调用方不应自动重试。"""


class OpenAiSourceBoundAnswerTransport(StructuredAnswerTransport):
    """将预配置环境凭据收敛为固定模型的严格回答 JSON 传输。"""

    def __init__(self, client: OpenAI | None = None) -> None:
        self._client = client or OpenAI()

    def complete(self, *, system_instruction: str, user_payload: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=_ALLOWED_MODEL,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_payload},
                ],
                max_completion_tokens=_MAX_OUTPUT_TOKENS,
                response_format=cast(Any, _response_format()),
            )
        except (APIConnectionError, APITimeoutError, RateLimitError, APIError) as exc:
            if isinstance(
                exc,
                (AuthenticationError, BadRequestError, NotFoundError, PermissionDeniedError),
            ):
                raise AnswerTransportRejectedError("受控回答请求被模型服务拒绝。") from exc
            raise AnswerTransportUnavailableError("受控回答模型服务暂时不可用。") from exc
        message = response.choices[0].message if response.choices else None
        refusal = getattr(message, "refusal", None) if message is not None else None
        if isinstance(refusal, str) and refusal:
            raise AnswerTransportRejectedError("模型拒绝了当前受控回答请求。")
        content = message.content if message is not None else None
        if not isinstance(content, str) or not content.strip():
            raise AnswerTransportRejectedError("模型没有返回受控结构化回答。")
        return content


def _response_format() -> dict[str, object]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "source_bound_answer",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["answered", "not_enough_evidence"],
                    },
                    "answer": {"type": "string", "minLength": 1, "maxLength": 600},
                    "citation_chunk_ids": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1, "maxLength": 64},
                        "maxItems": 3,
                    },
                    "needs_human_review": {"type": "boolean"},
                },
                "required": [
                    "status",
                    "answer",
                    "citation_chunk_ids",
                    "needs_human_review",
                ],
                "additionalProperties": False,
            },
        },
    }
