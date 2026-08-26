"""模块 10 真实回答 SDK 适配层的无网络合同测试。"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from rag_contract_workbench.openai_answer_transport import (
    AnswerTransportRejectedError,
    OpenAiSourceBoundAnswerTransport,
)


@dataclass
class FakeCreate:
    response: object
    kwargs: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> object:
        self.kwargs = kwargs
        return self.response


def fake_client(response: object) -> tuple[object, FakeCreate]:
    create = FakeCreate(response)
    client = SimpleNamespace(chat=SimpleNamespace(completions=create))
    return client, create


def completion(content: str | None, *, refusal: str | None = None) -> object:
    message = SimpleNamespace(content=content, refusal=refusal)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_adapter_sends_fixed_model_and_strict_source_bound_schema() -> None:
    client, create = fake_client(completion('{"status":"answered"}'))

    result = OpenAiSourceBoundAnswerTransport(client).complete(
        system_instruction="fixed instruction",
        user_payload="fixed payload",
    )

    assert result == '{"status":"answered"}'
    assert create.kwargs is not None
    assert create.kwargs["model"] == "gpt-5-mini"
    assert create.kwargs["max_completion_tokens"] == 360
    schema = create.kwargs["response_format"]["json_schema"]
    assert schema["name"] == "source_bound_answer"
    assert schema["strict"] is True
    assert schema["schema"]["additionalProperties"] is False
    assert schema["schema"]["properties"]["status"]["enum"] == [
        "answered",
        "not_enough_evidence",
    ]
    assert create.kwargs["messages"] == [
        {"role": "system", "content": "fixed instruction"},
        {"role": "user", "content": "fixed payload"},
    ]


@pytest.mark.parametrize(
    "response",
    [
        completion(None, refusal="cannot comply"),
        completion(None),
        SimpleNamespace(choices=[]),
    ],
)
def test_refusal_or_missing_content_is_a_permanent_controlled_failure(response: object) -> None:
    client, _ = fake_client(response)

    with pytest.raises(AnswerTransportRejectedError):
        OpenAiSourceBoundAnswerTransport(client).complete(
            system_instruction="instruction",
            user_payload="payload",
        )
