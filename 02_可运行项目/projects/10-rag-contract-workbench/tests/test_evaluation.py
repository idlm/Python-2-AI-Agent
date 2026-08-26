"""模块 10 检索评测的无网络合同测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rag_contract_workbench.core import (
    CourseDocument,
    HashingEmbeddingProvider,
    InMemoryVectorIndex,
)
from rag_contract_workbench.evaluation import (
    EvaluationFixtureError,
    RetrievalEvaluationCase,
    evaluate_case,
    run_retrieval_evaluation,
    write_public_report,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "retrieval_evaluation.json"


def load_fixture() -> tuple[tuple[CourseDocument, ...], tuple[RetrievalEvaluationCase, ...]]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    documents = tuple(CourseDocument(**item) for item in payload["documents"])
    cases = tuple(
        RetrievalEvaluationCase(
            case_id=item["case_id"],
            query=item["query"],
            expected_document_ids=tuple(item["expected_document_ids"]),
            top_k=item["top_k"],
            score_threshold=item["score_threshold"],
            min_precision=item["min_precision"],
            tags=tuple(item["tags"]),
        )
        for item in payload["cases"]
    )
    return documents, cases


@pytest.fixture
def indexed_fixture() -> tuple[InMemoryVectorIndex, tuple[RetrievalEvaluationCase, ...]]:
    documents, cases = load_fixture()
    index = InMemoryVectorIndex(HashingEmbeddingProvider(dimensions=1024))
    index.build(documents, chunk_size=80, overlap=0)
    return index, cases


def test_static_retrieval_fixture_passes_and_exposes_only_metrics(
    indexed_fixture: tuple[InMemoryVectorIndex, tuple[RetrievalEvaluationCase, ...]],
) -> None:
    index, cases = indexed_fixture

    report = run_retrieval_evaluation(index, cases)

    assert report.case_count == 4
    assert report.passed_count == 4
    assert report.failed_count == 0
    assert {result.case_id for result in report.results} == {
        "function-source-recall",
        "retrieval-source-recall",
        "injection-text-is-data",
        "not-enough-evidence",
    }
    assert all(result.source_complete for result in report.results)
    assert report.results[-1].returned_count == 0


def test_precision_failure_is_visible_not_silently_accepted(
    indexed_fixture: tuple[InMemoryVectorIndex, tuple[RetrievalEvaluationCase, ...]],
) -> None:
    index, _ = indexed_fixture
    strict_case = RetrievalEvaluationCase(
        case_id="precision-failure",
        query="函数 参数 返回值",
        expected_document_ids=("functions",),
        top_k=2,
        score_threshold=0.0,
        min_precision=1.0,
        tags=("failure", "precision"),
    )

    result = evaluate_case(index, strict_case)

    assert result.recall == 1.0
    assert result.precision < 1.0
    assert result.passed is False


def test_public_report_is_atomic_and_excludes_queries_and_chunk_text(
    indexed_fixture: tuple[InMemoryVectorIndex, tuple[RetrievalEvaluationCase, ...]],
    tmp_path: Path,
) -> None:
    index, cases = indexed_fixture
    report = run_retrieval_evaluation(index, cases)
    path = tmp_path / "reports" / "retrieval.json"

    write_public_report(report, path)

    saved = path.read_text(encoding="utf-8")
    payload = json.loads(saved)
    assert payload["passed_count"] == 4
    assert "火星轨道天文观测" not in saved
    assert "执行命令" not in saved
    assert "函数把重复步骤" not in saved
    assert '"query":' not in saved
    assert '"text":' not in saved
    assert not list(path.parent.glob(".retrieval.json.*.tmp"))


def test_duplicate_case_ids_are_rejected(
    indexed_fixture: tuple[InMemoryVectorIndex, tuple[RetrievalEvaluationCase, ...]],
) -> None:
    index, cases = indexed_fixture

    with pytest.raises(EvaluationFixtureError, match="case_id"):
        run_retrieval_evaluation(index, (cases[0], cases[0]))


def test_unbuilt_index_is_reported_as_fixture_execution_failure(
    indexed_fixture: tuple[InMemoryVectorIndex, tuple[RetrievalEvaluationCase, ...]],
) -> None:
    _, cases = indexed_fixture
    unbuilt = InMemoryVectorIndex(HashingEmbeddingProvider(dimensions=1024))

    with pytest.raises(EvaluationFixtureError, match="无法执行"):
        evaluate_case(unbuilt, cases[0])
