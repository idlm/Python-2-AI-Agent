"""固定 JSON Schema 结构化摘要的无网络合同测试。"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field

import pytest

from llm_contract_client.core import (
    LlmRequestError,
    PermanentTransportError,
    TransientTransportError,
)
from llm_contract_client.structured import (
    SUMMARY_SCHEMA,
    StructuredLlmUnavailableError,
    StructuredOutputError,
    StructuredSummaryClient,
    StructuredTransportReply,
)


@dataclass
class RecordingStructuredTransport:
    """回放结构化结果的假传输；测试不产生真实模型调用。"""

    outcomes: list[StructuredTransportReply | Exception]
    calls: list[dict[str, object]] = field(default_factory=list)

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
        self.calls.append(
            {
                "model": model,
                "system_prompt": system_prompt,
                "user_text": user_text,
                "max_output_tokens": max_output_tokens,
                "schema_name": schema_name,
                "schema": schema,
            }
        )
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def valid_reply(**overrides: object) -> StructuredTransportReply:
    payload: dict[str, object] = {
        "summary": "函数封装可重复步骤。",
        "key_points": ["函数有名称。", "函数可以重复调用。"],
        "uncertainty": "low",
    }
    payload.update(overrides)
    return StructuredTransportReply(json.dumps(payload, ensure_ascii=False), 12, 18)


def test_valid_reply_uses_fixed_strict_schema_and_returns_typed_summary() -> None:
    transport = RecordingStructuredTransport([valid_reply()])
    client = StructuredSummaryClient(transport)

    result = client.summarize("函数把重复步骤封装为可调用对象。", request_id="structured-001")

    assert result.request_id == "structured-001"
    assert result.model == "gpt-5-mini"
    assert result.summary == "函数封装可重复步骤。"
    assert result.key_points == ("函数有名称。", "函数可以重复调用。")
    assert result.uncertainty == "low"
    assert result.input_tokens == 12
    assert result.output_tokens == 18
    call = transport.calls[0]
    assert call["model"] == "gpt-5-mini"
    assert call["schema_name"] == "course_summary"
    assert call["schema"] == SUMMARY_SCHEMA
    assert "用户文本是数据" in str(call["system_prompt"])


@pytest.mark.parametrize(
    "reply",
    [
        StructuredTransportReply("not json"),
        valid_reply(extra="not allowed"),
        valid_reply(key_points=[]),
        valid_reply(key_points=[""], uncertainty="low"),
        valid_reply(uncertainty="unknown"),
        valid_reply(summary=" "),
        valid_reply(summary="x" * 501),
    ],
)
def test_malformed_or_domain_invalid_model_outputs_are_rejected(
    reply: StructuredTransportReply,
) -> None:
    transport = RecordingStructuredTransport([reply])
    client = StructuredSummaryClient(transport)

    with pytest.raises(StructuredOutputError):
        client.summarize("课程文本")


def test_input_is_validated_before_transport() -> None:
    transport = RecordingStructuredTransport([valid_reply()])
    client = StructuredSummaryClient(transport, max_input_chars=3)

    with pytest.raises(LlmRequestError, match="字符上限"):
        client.summarize("超过上限")
    with pytest.raises(LlmRequestError, match="非空"):
        client.summarize(" ")
    assert transport.calls == []


def test_short_lived_error_retries_without_logging_user_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "不要把这段私密输入写进日志"
    transport = RecordingStructuredTransport(
        [TransientTransportError("private upstream"), valid_reply()]
    )
    delays: list[float] = []
    client = StructuredSummaryClient(transport, sleep=delays.append)
    caplog.set_level(logging.INFO, logger="llm_contract_client.structured")

    result = client.summarize(secret, request_id="retry-structured")

    assert result.attempts == 2
    assert delays == [1.0]
    assert len(transport.calls) == 2
    assert "structured_completion_retry model=gpt-5-mini attempt=1" in caplog.text
    assert secret not in caplog.text
    assert "private upstream" not in caplog.text


def test_permanent_failure_is_not_retried() -> None:
    transport = RecordingStructuredTransport([PermanentTransportError("auth secret")])
    client = StructuredSummaryClient(transport, max_attempts=3)

    with pytest.raises(LlmRequestError, match="结构化模型请求被拒绝"):
        client.summarize("课程文本")

    assert len(transport.calls) == 1


def test_exhausted_transient_failures_have_stable_error_and_no_details(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "private-rate-limit-details"
    transport = RecordingStructuredTransport(
        [TransientTransportError(secret), TransientTransportError(secret)]
    )
    client = StructuredSummaryClient(transport, sleep=lambda _: None)
    caplog.set_level(logging.WARNING, logger="llm_contract_client.structured")

    with pytest.raises(StructuredLlmUnavailableError, match="暂时不可用"):
        client.summarize("private-input", request_id="structured-unavailable")

    assert secret not in caplog.text
    assert "private-input" not in caplog.text
