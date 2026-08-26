"""离线评测门禁夹具回放与无正文报告；不执行被评测系统。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .core import (
    CaseStatus,
    EvaluationCase,
    EvaluationGateError,
    EvaluationResult,
    ReleaseDecision,
    RiskLevel,
    SuiteKind,
    TraceEvent,
    TraceKind,
    evaluate_release,
)


class GateFixtureError(ValueError):
    """公开离线门禁夹具不符合字段闭集与类型合同。"""


@dataclass(frozen=True)
class GateCaseResult:
    case_id: str
    expected: str
    actual: str
    passed: bool
    blocker_count: int


_ALLOWED_CASE_FIELDS = {
    "case_id",
    "cases",
    "baseline",
    "candidate",
    "max_soft_regressions",
    "expected",
}
_ALLOWED_EVALUATION_CASE_FIELDS = {"case_id", "suite_kind", "risk_level"}
_ALLOWED_OUTCOMES = {decision.value for decision in ReleaseDecision}


def run_static_gate_cases(path: Path) -> tuple[GateCaseResult, ...]:
    """回放固定公开夹具，不接受任意运行或外部数据。"""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateFixtureError("静态门禁夹具不可读取或不是合法 JSON。") from exc
    if not isinstance(raw, list) or not raw:
        raise GateFixtureError("静态门禁夹具必须是非空数组。")

    results: list[GateCaseResult] = []
    case_ids: set[str] = set()
    for raw_case in raw:
        case_id, cases, baseline, candidate, maximum, expected = _parse_case(raw_case)
        if case_id in case_ids:
            raise GateFixtureError("静态门禁案例 ID 不可重复。")
        case_ids.add(case_id)
        report = evaluate_release(
            cases,
            baseline,
            candidate,
            baseline_version="fixture-baseline-1",
            candidate_version="fixture-candidate-1",
            max_soft_regressions=maximum,
        )
        actual = report.decision.value
        results.append(
            GateCaseResult(
                case_id=case_id,
                expected=expected,
                actual=actual,
                passed=actual == expected,
                blocker_count=len(report.blockers),
            )
        )
    return tuple(results)


def write_public_gate_report(results: tuple[GateCaseResult, ...], path: Path) -> None:
    """原子写入无正文报告，只保存案例 ID、决定、通过标记和计数。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "case_count": len(results),
        "passed_count": sum(result.passed for result in results),
        "results": [asdict(result) for result in results],
    }
    temporary_path = path.with_name(f".{path.name}.tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def _parse_case(
    raw_case: Any,
) -> tuple[
    str,
    tuple[EvaluationCase, ...],
    dict[str, EvaluationResult],
    dict[str, EvaluationResult],
    int,
    str,
]:
    if not isinstance(raw_case, dict) or set(raw_case) != _ALLOWED_CASE_FIELDS:
        raise GateFixtureError("静态门禁案例必须恰好含固定字段。")
    case_id = raw_case["case_id"]
    raw_cases = raw_case["cases"]
    raw_baseline = raw_case["baseline"]
    raw_candidate = raw_case["candidate"]
    maximum = raw_case["max_soft_regressions"]
    expected = raw_case["expected"]
    if (
        not isinstance(case_id, str)
        or not isinstance(raw_cases, list)
        or not raw_cases
        or not isinstance(raw_baseline, dict)
        or not isinstance(raw_candidate, dict)
        or isinstance(maximum, bool)
        or not isinstance(maximum, int)
        or maximum < 0
        or expected not in _ALLOWED_OUTCOMES
    ):
        raise GateFixtureError("静态门禁案例字段或期望类别不合法。")
    cases = tuple(_parse_evaluation_case(raw_evaluation_case) for raw_evaluation_case in raw_cases)
    try:
        baseline = _parse_result_map(raw_baseline)
        candidate = _parse_result_map(raw_candidate)
    except (EvaluationGateError, TypeError, ValueError) as exc:
        raise GateFixtureError("基线或候选结果不符合受限合同。") from exc
    return case_id, cases, baseline, candidate, maximum, expected


def _parse_evaluation_case(raw_case: Any) -> EvaluationCase:
    if not isinstance(raw_case, dict) or set(raw_case) != _ALLOWED_EVALUATION_CASE_FIELDS:
        raise GateFixtureError("评测案例必须恰好含固定字段。")
    try:
        return EvaluationCase(
            case_id=raw_case["case_id"],
            suite_version="fixture-suite-1",
            suite_kind=SuiteKind(raw_case["suite_kind"]),
            risk_level=RiskLevel(raw_case["risk_level"]),
        )
    except (EvaluationGateError, KeyError, TypeError, ValueError) as exc:
        raise GateFixtureError("评测案例不符合受限合同。") from exc


def _parse_result_map(raw_results: dict[str, Any]) -> dict[str, EvaluationResult]:
    results: dict[str, EvaluationResult] = {}
    for case_id, raw_status in raw_results.items():
        if not isinstance(case_id, str) or not isinstance(raw_status, str):
            raise EvaluationGateError("结果映射必须是案例 ID 到状态字符串。")
        status = CaseStatus(raw_status)
        events = () if status is CaseStatus.NOT_RUN else (_event_for(case_id),)
        results[case_id] = EvaluationResult(case_id=case_id, status=status, events=events)
    return results


def _event_for(case_id: str) -> TraceEvent:
    return TraceEvent(
        run_id="fixture-run",
        case_id=case_id,
        kind=TraceKind.STATE_TRANSITION,
        before_status="running",
        after_status="stopped",
        step_count=1,
        tool_call_count=0,
    )
