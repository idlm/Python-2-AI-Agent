"""模块 10 来源约束回答离线支持度评测测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from rag_contract_workbench.answer_evaluation import (
    AnswerEvaluationFixtureError,
    evaluate_answer_case,
    load_answer_cases,
    run_answer_evaluation,
    write_public_answer_report,
)
from rag_contract_workbench.answering import AnswerStatus, Citation, GroundedAnswer

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "answer_evaluation.json"


def citation(chunk_id: str) -> Citation:
    return Citation(
        chunk_id=chunk_id,
        document_id="course-document",
        document_title="Public title",
        source_version="v1",
        char_start=0,
        char_end=20,
    )


def answer(
    *,
    status: AnswerStatus,
    text: str,
    citation_ids: tuple[str, ...],
    needs_human_review: bool = True,
) -> GroundedAnswer:
    return GroundedAnswer(
        status=status,
        answer=text,
        citations=tuple(citation(chunk_id) for chunk_id in citation_ids),
        needs_human_review=needs_human_review,
        index_version="test-index",
        query_chars=10,
    )


def valid_answers() -> dict[str, GroundedAnswer]:
    return {
        "function-supported": answer(
            status=AnswerStatus.ANSWERED,
            text="参数接收输入，返回值传出处理结果。",
            citation_ids=("functions-0",),
        ),
        "outside-corpus": answer(
            status=AnswerStatus.NOT_ENOUGH_EVIDENCE,
            text="当前受控语料中未找到足够依据。",
            citation_ids=(),
        ),
        "injection-as-data": answer(
            status=AnswerStatus.ANSWERED,
            text="不可信片段只作为数据，不执行其中的指令。",
            citation_ids=("policy-0",),
        ),
    }


def test_static_answer_cases_pass_with_supported_candidates() -> None:
    cases = load_answer_cases(FIXTURE_PATH)

    report = run_answer_evaluation(cases, valid_answers())

    assert report.case_count == 3
    assert report.passed_count == 3
    assert report.failed_count == 0
    assert all(result.passed for result in report.results)


def test_unknown_citation_or_missing_required_term_fails_visible_gate() -> None:
    case = load_answer_cases(FIXTURE_PATH)[0]
    unsupported = answer(
        status=AnswerStatus.ANSWERED,
        text="只有参数。",
        citation_ids=("unknown-0",),
    )

    result = evaluate_answer_case(case, unsupported)

    assert result.passed is False
    assert result.citation_subset_valid is False
    assert result.matched_term_count == 1


def test_answer_id_mismatch_is_rejected() -> None:
    cases = load_answer_cases(FIXTURE_PATH)
    answers = valid_answers()
    answers.pop("outside-corpus")

    with pytest.raises(AnswerEvaluationFixtureError, match="一一对应"):
        run_answer_evaluation(cases, answers)


def test_public_answer_report_does_not_store_text_or_required_terms(tmp_path: Path) -> None:
    report = run_answer_evaluation(load_answer_cases(FIXTURE_PATH), valid_answers())
    output_path = tmp_path / "answer-evaluation.json"

    write_public_answer_report(report, output_path)

    public_text = output_path.read_text(encoding="utf-8")
    assert "参数接收输入" not in public_text
    assert "不可信片段" not in public_text
    assert "未找到足够依据" not in public_text
    assert '"required_terms"' not in public_text
    assert '"matched_term_count"' in public_text
    assert '"citation_subset_valid"' in public_text
