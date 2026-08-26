"""OpenAI-compatible 适配器的无网络结构化输出测试。"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import pytest

from llm_contract_client.core import PermanentTransportError
from llm_contract_client.openai_transport import OpenAiChatTransport
from llm_contract_client.structured import SUMMARY_SCHEMA


@dataclass
class FakeCompletions:
    """记录 SDK 调用形状并回放预构造响应；绝不发起网络请求。"""

    outcomes: list[object]
    calls: list[dict[str, object]] = field(default_factory=list)

    def create(self, **kwargs: object) -> object:
        self.calls.append(dict(kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def fake_sdk(completions: FakeCompletions) -> Any:
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


def fake_response(
    content: str | None,
    *,
    refusal: str | None = None,
    include_choice: bool = True,
) -> object:
    choices = []
    if include_choice:
        message = SimpleNamespace(content=content, refusal=refusal)
        choices = [SimpleNamespace(message=message)]
    usage = SimpleNamespace(prompt_tokens=21, completion_tokens=34)
    return SimpleNamespace(choices=choices, usage=usage)


def call_json(transport: OpenAiChatTransport) -> object:
    return transport.complete_json(
        model="gpt-5-mini",
        system_prompt="fixed course prompt",
        user_text="course text",
        max_output_tokens=128,
        schema_name="course_summary",
        schema=SUMMARY_SCHEMA,
    )


def test_complete_json_sends_strict_fixed_response_format_and_returns_minimal_usage() -> None:
    completions = FakeCompletions([fake_response('{"summary":"x"}')])
    transport = OpenAiChatTransport(client=fake_sdk(completions))

    reply = call_json(transport)

    assert reply.json_text == '{"summary":"x"}'
    assert reply.input_tokens == 21
    assert reply.output_tokens == 34
    call = completions.calls[0]
    assert call["model"] == "gpt-5-mini"
    assert call["max_completion_tokens"] == 128
    assert call["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "course_summary",
            "strict": True,
            "schema": SUMMARY_SCHEMA,
        },
    }
    assert "fixed course prompt" in str(call["messages"])
    assert "course text" in str(call["messages"])


@pytest.mark.parametrize(
    "response, message",
    [
        (fake_response(None, refusal="policy refusal"), "模型拒绝"),
        (fake_response(None), "没有返回结构化文本内容"),
        (fake_response("", include_choice=False), "没有返回结构化文本内容"),
    ],
)
def test_refusal_empty_content_and_empty_choices_are_stable_permanent_failures(
    response: object,
    message: str,
) -> None:
    transport = OpenAiChatTransport(client=fake_sdk(FakeCompletions([response])))

    with pytest.raises(PermanentTransportError, match=message):
        call_json(transport)
