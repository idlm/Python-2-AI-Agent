"""最小可观察 LLM 客户端的受控命令行入口。"""

from __future__ import annotations

import argparse
import json
import logging
from typing import NoReturn

from .core import (
    LlmClient,
    LlmRequestError,
    LlmResponseError,
    LlmUnavailableError,
    PromptRequest,
    PromptTask,
)
from .openai_transport import OpenAiChatTransport
from .structured import (
    StructuredLlmUnavailableError,
    StructuredOutputError,
    StructuredSummaryClient,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="受控 LLM 摘要教学客户端")
    parser.add_argument("--text", help="要摘要的文本；最大长度由受控客户端限制。")
    parser.add_argument("--request-id", help="用于关联公开结果与脱敏日志的 ID。")
    parser.add_argument("--verbose", action="store_true", help="将脱敏运行日志输出到 stderr。")
    parser.add_argument("--status", action="store_true", help="输出当前客户端能力和明确限制。")
    parser.add_argument(
        "--structured",
        action="store_true",
        help="使用固定 JSON Schema 返回结构化摘要；不开放自定义 Schema。",
    )
    return parser


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(levelname)s %(name)s %(message)s",
    )


def _status() -> dict[str, object]:
    return {
        "version": "0.3.0",
        "allowed_models": ["gpt-5-mini"],
        "allowed_tasks": [PromptTask.SUMMARIZE.value],
        "not_supported": [
            "arbitrary_system_prompts",
            "tool_execution",
            "streaming",
            "arbitrary_json_schemas",
            "unbounded_retries",
            "automatic_fact_verification",
        ],
    }


def main() -> NoReturn:
    args = build_parser().parse_args()
    _configure_logging(args.verbose)
    if args.status:
        if args.text is not None or args.request_id is not None or args.structured:
            message = "错误：--status 不能与 --text、--request-id 或 --structured 一起使用。"
            raise SystemExit(message)
        print(json.dumps(_status(), ensure_ascii=False, sort_keys=True))
        raise SystemExit(0)
    if args.text is None:
        raise SystemExit("错误：必须提供 --text，或使用 --status。")
    if args.structured:
        _run_structured(args.text, args.request_id)
    client = LlmClient(OpenAiChatTransport())
    try:
        result = client.complete(
            PromptRequest(
                task=PromptTask.SUMMARIZE,
                text=args.text,
                request_id=args.request_id,
            )
        )
    except (LlmRequestError, LlmResponseError) as exc:
        print(
            json.dumps(
                {"error": {"code": "invalid_request", "message": str(exc)}},
                ensure_ascii=False,
            )
        )
        raise SystemExit(2) from exc
    except LlmUnavailableError as exc:
        print(
            json.dumps(
                {"error": {"code": "llm_unavailable", "message": str(exc)}},
                ensure_ascii=False,
            )
        )
        raise SystemExit(3) from exc
    print(
        json.dumps(
            {
                "request_id": result.request_id,
                "task": result.task.value,
                "model": result.model,
                "text": result.text,
                "attempts": result.attempts,
                "input_chars": result.input_chars,
                "output_chars": result.output_chars,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    raise SystemExit(0)


def _run_structured(text: str, request_id: str | None) -> NoReturn:
    try:
        result = StructuredSummaryClient(OpenAiChatTransport()).summarize(
            text,
            request_id=request_id,
        )
    except (LlmRequestError, StructuredOutputError) as exc:
        print(
            json.dumps(
                {"error": {"code": "invalid_structured_response", "message": str(exc)}},
                ensure_ascii=False,
            )
        )
        raise SystemExit(2) from exc
    except StructuredLlmUnavailableError as exc:
        print(
            json.dumps(
                {"error": {"code": "llm_unavailable", "message": str(exc)}},
                ensure_ascii=False,
            )
        )
        raise SystemExit(3) from exc
    print(
        json.dumps(
            {
                "request_id": result.request_id,
                "task": PromptTask.SUMMARIZE.value,
                "model": result.model,
                "summary": result.summary,
                "key_points": result.key_points,
                "uncertainty": result.uncertainty,
                "attempts": result.attempts,
                "input_chars": result.input_chars,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    raise SystemExit(0)


if __name__ == "__main__":
    main()
