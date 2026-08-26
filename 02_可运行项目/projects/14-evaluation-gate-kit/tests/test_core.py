from __future__ import annotations

import pytest

from evaluation_gate_kit import (
    CaseStatus,
    EvaluationCase,
    EvaluationGateError,
    EvaluationResult,
    ReleaseBlocker,
    ReleaseDecision,
    RiskLevel,
    SuiteKind,
    TraceEvent,
    TraceKind,
    evaluate_release,
)


def _case(case_id: str, *, risk: RiskLevel = RiskLevel.SOFT) -> EvaluationCase:
    return EvaluationCase(
        case_id=case_id,
        suite_version="suite-1",
        suite_kind=SuiteKind.REGRESSION,
        risk_level=risk,
    )


def _event(case_id: str) -> TraceEvent:
    return TraceEvent(
        run_id="run-1",
        case_id=case_id,
        kind=TraceKind.STATE_TRANSITION,
        before_status="running",
        after_status="stopped",
        step_count=1,
        tool_call_count=0,
    )


def _result(case_id: str, status: CaseStatus = CaseStatus.PASSED) -> EvaluationResult:
    events = () if status is CaseStatus.NOT_RUN else (_event(case_id),)
    return EvaluationResult(case_id=case_id, status=status, events=events)


def test_passing_baseline_and_candidate_approve_release() -> None:
    cases = (_case("hard-a", risk=RiskLevel.HARD), _case("soft-b"))
    baseline = {case.case_id: _result(case.case_id) for case in cases}
    candidate = {case.case_id: _result(case.case_id) for case in cases}

    report = evaluate_release(
        cases,
        baseline,
        candidate,
        baseline_version="baseline-1",
        candidate_version="candidate-1",
    )

    assert report.decision is ReleaseDecision.APPROVED
    assert report.blockers == ()
    assert report.passed_count == 2


def test_hard_failure_and_not_run_always_block_release() -> None:
    cases = (_case("hard-a", risk=RiskLevel.HARD), _case("soft-b"))
    baseline = {case.case_id: _result(case.case_id) for case in cases}
    candidate = {
        "hard-a": _result("hard-a", CaseStatus.FAILED),
        "soft-b": _result("soft-b", CaseStatus.NOT_RUN),
    }

    report = evaluate_release(
        cases,
        baseline,
        candidate,
        baseline_version="baseline-1",
        candidate_version="candidate-1",
    )

    assert report.decision is ReleaseDecision.REJECTED
    assert ReleaseBlocker.HARD_FAILURE in report.blockers
    assert ReleaseBlocker.NOT_RUN in report.blockers


def test_soft_regressions_obey_explicit_threshold() -> None:
    cases = (_case("soft-a"), _case("soft-b"))
    baseline = {case.case_id: _result(case.case_id) for case in cases}
    candidate = {
        "soft-a": _result("soft-a", CaseStatus.FAILED),
        "soft-b": _result("soft-b"),
    }

    blocked = evaluate_release(
        cases,
        baseline,
        candidate,
        baseline_version="baseline-1",
        candidate_version="candidate-1",
        max_soft_regressions=0,
    )
    allowed = evaluate_release(
        cases,
        baseline,
        candidate,
        baseline_version="baseline-1",
        candidate_version="candidate-1",
        max_soft_regressions=1,
    )

    assert ReleaseBlocker.REGRESSION_FAILURE in blocked.blockers
    assert allowed.decision is ReleaseDecision.APPROVED


def test_non_passing_baseline_is_itself_a_blocker() -> None:
    cases = (_case("soft-a"),)
    baseline = {"soft-a": _result("soft-a", CaseStatus.FAILED)}
    candidate = {"soft-a": _result("soft-a")}

    report = evaluate_release(
        cases,
        baseline,
        candidate,
        baseline_version="baseline-1",
        candidate_version="candidate-1",
    )

    assert ReleaseBlocker.BASELINE_MISMATCH in report.blockers


def test_gate_rejects_missing_case_coverage_and_duplicate_case_ids() -> None:
    case = _case("soft-a")
    with pytest.raises(EvaluationGateError, match="恰好覆盖"):
        evaluate_release(
            (case,),
            {"soft-a": _result("soft-a")},
            {},
            baseline_version="baseline-1",
            candidate_version="candidate-1",
        )

    with pytest.raises(EvaluationGateError, match="不可重复"):
        evaluate_release(
            (case, case),
            {"soft-a": _result("soft-a")},
            {"soft-a": _result("soft-a")},
            baseline_version="baseline-1",
            candidate_version="candidate-1",
        )


def test_trace_is_minimal_and_result_requires_matching_case_id() -> None:
    event = _event("case-a")
    assert "prompt" not in repr(event)
    assert "response" not in repr(event)

    with pytest.raises(EvaluationGateError, match="案例 ID"):
        EvaluationResult(
            case_id="case-b",
            status=CaseStatus.PASSED,
            events=(event,),
        )
