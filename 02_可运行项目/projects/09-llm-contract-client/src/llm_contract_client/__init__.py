"""项目 9：最小可观察 LLM 客户端公共接口。"""

from .core import (
    CompletionResult,
    LlmClient,
    LlmRequestError,
    LlmResponseError,
    LlmTransport,
    LlmUnavailableError,
    PermanentTransportError,
    PromptRequest,
    PromptTask,
    TransientTransportError,
    TransportReply,
)
from .openai_transport import OpenAiChatTransport

__all__ = [
    "CompletionResult",
    "LlmClient",
    "LlmRequestError",
    "LlmResponseError",
    "LlmTransport",
    "LlmUnavailableError",
    "OpenAiChatTransport",
    "PermanentTransportError",
    "PromptRequest",
    "PromptTask",
    "TransientTransportError",
    "TransportReply",
]
