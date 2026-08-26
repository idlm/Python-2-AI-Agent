"""模块 10 来源约束回答合同的无网络测试。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

import pytest

from rag_contract_workbench.answering import (
    AnswerContractError,
    AnswerStatus,
    SourceBoundAnswerClient,
)
from rag_contract_workbench.core import (
    CourseDocument,
    HashingEmbeddingProvider,
    InMemoryVectorIndex,
)


@dataclass
class FakeAnswerTransport:
    response: str
    calls: list[tuple[str, str]] = field(default_factory=list)

    def complete(self, *, system_instruction: str, user_payload: str) -> str:
        self.calls.append((system_instruction, user_payload))
        return self.response


def build_retrieval() -> tuple[InMemoryVectorIndex, object]:
    index = InMemoryVectorIndex(HashingEmbeddingProvider(dimensions=1024))
    index.build(
        [
            CourseDocument(
                document_id="functions",
                title="函数课程笔记",
                version="v1",
                text="函数把重复步骤封装为可调用单元。参数把输入交给函数，返回值传出处理结果。",
            )
        ],
        chunk_size=80,
        overlap=0,
    )
    return index, index.search("函数 参数 返回值", score_threshold=0.0)


def response_payload(
    *,
    status: str = "answered",
    answer: str = "函数通过参数接收输入，并通过返回值传出处理结果。",
    citation_chunk_ids: list[str] | None = None,
    needs_human_review: bool = True,
) -> str:
    return json.dumps(
        {
            "status": status,
            "answer": answer,
            "citation_chunk_ids": (
                citation_chunk_ids if citation_chunk_ids is not None else ["functions-0"]
            ),
            "needs_human_review": needs_human_review,
        },
        ensure_ascii=False,
    )


def test_answer_accepts_only_actual_retrieved_citation() -> None:
    _, retrieval = build_retrieval()
    transport = FakeAnswerTransport(response_payload())

    answer = SourceBoundAnswerClient(transport).answer("函数如何处理输入？", retrieval)

    assert answer.status is AnswerStatus.ANSWERED
    assert answer.citations[0].chunk_id == "functions-0"
    assert answer.citations[0].source_version == "v1"
    assert answer.needs_human_review is True
    assert len(transport.calls) == 1
    system_instruction, user_payload = transport.calls[0]
    assert "不可信数据" in system_instruction
    assert "函数如何处理输入？" in user_payload
    assert "functions-0" in user_payload


def test_no_evidence_returns_local_refusal_without_transport_call() -> None:
    index, _ = build_retrieval()
    no_evidence = index.search("火星轨道天文观测", score_threshold=1.0)
    transport = FakeAnswerTransport(response_payload())

    answer = SourceBoundAnswerClient(transport).answer("火星轨道天文观测是什么？", no_evidence)

    assert answer.status is AnswerStatus.NOT_ENOUGH_EVIDENCE
    assert answer.citations == ()
    assert answer.needs_human_review is True
    assert transport.calls == []


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ("not-json", "非法 JSON"),
        (response_payload(citation_chunk_ids=["unknown-0"]), "未实际检索"),
        (response_payload(citation_chunk_ids=[]), "至少引用"),
        (response_payload(citation_chunk_ids=["functions-0", "functions-0"]), "不可重复"),
        (
            response_payload(
                status="not_enough_evidence",
                citation_chunk_ids=["functions-0"],
            ),
            "不能附带",
        ),
    ],
)
def test_invalid_model_candidates_are_rejected(payload: str, message: str) -> None:
    _, retrieval = build_retrieval()

    client = SourceBoundAnswerClient(FakeAnswerTransport(payload))
    with pytest.raises(AnswerContractError, match=message):
        client.answer("函数如何处理输入？", retrieval)


def test_answer_logs_do_not_include_question_or_source_body(
    caplog: pytest.LogCaptureFixture,
) -> None:
    index = InMemoryVectorIndex(HashingEmbeddingProvider(dimensions=1024))
    index.build(
        [
            CourseDocument(
                document_id="private-demo",
                title="公开测试标题",
                version="v1",
                text="private-source-body-must-not-appear-in-log",
            )
        ],
        chunk_size=40,
        overlap=0,
    )
    retrieval = index.search("private-source-body", score_threshold=0.0)
    transport = FakeAnswerTransport(
        response_payload(citation_chunk_ids=["private-demo-0"])
    )
    caplog.set_level(logging.INFO, logger="rag_contract_workbench.answering")

    SourceBoundAnswerClient(transport).answer("private-question-must-not-appear", retrieval)

    assert "private-question-must-not-appear" not in caplog.text
    assert "private-source-body-must-not-appear-in-log" not in caplog.text
    assert "rag_answer_completed" in caplog.text
