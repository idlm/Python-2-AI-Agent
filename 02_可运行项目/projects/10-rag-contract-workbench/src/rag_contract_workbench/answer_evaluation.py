"""来源约束回答的离线支持度评测，不调用模型或保存回答正文。"""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .answering import AnswerStatus, GroundedAnswer


class AnswerEvaluationFixtureError(ValueError):
    """回答评测夹具缺失、重复或不满足课程合同。"""


@dataclass(frozen=True)
class AnswerEvaluationCase:
    """公开教学回答夹具的最小期望；答案文本只在内存中比较。"""

    case_id: str
    label: str
    expected_status: AnswerStatus
    allowed_citation_ids: tuple[str, ...]
    require_human_review: bool
    required_terms: tuple[str, ...]


@dataclass(frozen=True)
class AnswerEvaluationResult:
    """可安全持久化的单案例评测摘要。"""

    case_id: str
    label: str
    actual_status: AnswerStatus
    expected_citation_count: int
    actual_citation_count: int
    citation_subset_valid: bool
    required_term_count: int
    matched_term_count: int
    human_review_matches: bool
    passed: bool


@dataclass(frozen=True)
class AnswerEvaluationReport:
    """可安全持久化的聚合结果。"""

    case_count: int
    passed_count: int
    failed_count: int
    results: tuple[AnswerEvaluationResult, ...]


def load_answer_cases(path: Path) -> tuple[AnswerEvaluationCase, ...]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AnswerEvaluationFixtureError("回答评测夹具不可读取。") from exc
    if not isinstance(raw, list) or not raw:
        raise AnswerEvaluationFixtureError("回答评测夹具必须是非空数组。")
    cases = tuple(_parse_case(item) for item in raw)
    if len({case.case_id for case in cases}) != len(cases):
        raise AnswerEvaluationFixtureError("回答评测案例 ID 不可重复。")
    return cases


def evaluate_answer_case(
    case: AnswerEvaluationCase,
    answer: GroundedAnswer,
) -> AnswerEvaluationResult:
    actual_ids = {citation.chunk_id for citation in answer.citations}
    allowed_ids = set(case.allowed_citation_ids)
    citation_subset_valid = actual_ids <= allowed_ids
    matched_term_count = sum(term in answer.answer for term in case.required_terms)
    status_matches = answer.status is case.expected_status
    review_matches = answer.needs_human_review is case.require_human_review
    citations_match = (
        len(answer.citations) == 0
        if case.expected_status is AnswerStatus.NOT_ENOUGH_EVIDENCE
        else bool(answer.citations) and citation_subset_valid
    )
    passed = (
        status_matches
        and citations_match
        and review_matches
        and matched_term_count == len(case.required_terms)
    )
    return AnswerEvaluationResult(
        case_id=case.case_id,
        label=case.label,
        actual_status=answer.status,
        expected_citation_count=len(case.allowed_citation_ids),
        actual_citation_count=len(answer.citations),
        citation_subset_valid=citation_subset_valid,
        required_term_count=len(case.required_terms),
        matched_term_count=matched_term_count,
        human_review_matches=review_matches,
        passed=passed,
    )


def run_answer_evaluation(
    cases: tuple[AnswerEvaluationCase, ...],
    answers: dict[str, GroundedAnswer],
) -> AnswerEvaluationReport:
    if set(answers) != {case.case_id for case in cases}:
        raise AnswerEvaluationFixtureError("回答集合必须与评测案例 ID 一一对应。")
    results = tuple(evaluate_answer_case(case, answers[case.case_id]) for case in cases)
    passed_count = sum(result.passed for result in results)
    return AnswerEvaluationReport(
        case_count=len(results),
        passed_count=passed_count,
        failed_count=len(results) - passed_count,
        results=results,
    )


def write_public_answer_report(report: AnswerEvaluationReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "case_count": report.case_count,
        "passed_count": report.passed_count,
        "failed_count": report.failed_count,
        "results": [asdict(result) for result in report.results],
    }
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        prefix=f".{path.name}.",
    ) as temporary:
        json.dump(payload, temporary, ensure_ascii=False, sort_keys=True)
        temporary.write("\n")
        temp_path = Path(temporary.name)
    temp_path.replace(path)


def _parse_case(raw: Any) -> AnswerEvaluationCase:
    if not isinstance(raw, dict):
        raise AnswerEvaluationFixtureError("回答评测案例必须是对象。")
    expected_keys = {
        "case_id",
        "label",
        "expected_status",
        "allowed_citation_ids",
        "require_human_review",
        "required_terms",
    }
    if set(raw) != expected_keys:
        raise AnswerEvaluationFixtureError("回答评测案例字段不符合固定合同。")
    case_id = raw["case_id"]
    label = raw["label"]
    allowed_ids = raw["allowed_citation_ids"]
    required_terms = raw["required_terms"]
    if not isinstance(case_id, str) or not case_id:
        raise AnswerEvaluationFixtureError("回答评测案例必须有非空 ID。")
    if not isinstance(label, str) or not label:
        raise AnswerEvaluationFixtureError("回答评测案例必须有非空标签。")
    if not isinstance(allowed_ids, list) or not all(isinstance(item, str) for item in allowed_ids):
        raise AnswerEvaluationFixtureError("允许引用必须是字符串数组。")
    if not isinstance(required_terms, list) or not all(
        isinstance(item, str) for item in required_terms
    ):
        raise AnswerEvaluationFixtureError("所需术语必须是字符串数组。")
    if not isinstance(raw["require_human_review"], bool):
        raise AnswerEvaluationFixtureError("人工复核字段必须是布尔值。")
    try:
        expected_status = AnswerStatus(raw["expected_status"])
    except (TypeError, ValueError) as exc:
        raise AnswerEvaluationFixtureError("回答评测状态不在允许枚举中。") from exc
    return AnswerEvaluationCase(
        case_id=case_id,
        label=label,
        expected_status=expected_status,
        allowed_citation_ids=tuple(allowed_ids),
        require_human_review=raw["require_human_review"],
        required_terms=tuple(required_terms),
    )
