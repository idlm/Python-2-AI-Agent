"""离线评测基线和发布门禁合同；绝不调用模型、工具或被评测 Agent。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

_MAX_ID_LENGTH: Final[int] = 64
_MAX_VERSION_LENGTH: Final[int] = 32


class EvaluationGateError(ValueError):
    """评测案例、结果、trace 或发布门禁输入违反受限合同。"""


class SuiteKind(StrEnum):
    REGRESSION = "regression"
    CAPABILITY = "capability"


class RiskLevel(StrEnum):
    HARD = "hard"
    SOFT = "soft"


class CaseStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_RUN = "not_run"


class TraceKind(StrEnum):
    STATE_TRANSITION = "state_transition"
    TOOL_CANDIDATE = "tool_candidate"
    APPROVAL_PAUSE = "approval_pause"
    BUDGET_STOP = "budget_stop"


class ReleaseBlocker(StrEnum):
    BASELINE_MISMATCH = "baseline_mismatch"
    HARD_FAILURE = "hard_failure"
    NOT_RUN = "not_run"
    REGRESSION_FAILURE = "regression_failure"


class ReleaseDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class EvaluationCase:
    """固定案例元数据；不含用户正文、提示、参数或工具结果。"""

    case_id: str
    suite_version: str
    suite_kind: SuiteKind
    risk_level: RiskLevel

    def __post_init__(self) -> None:
        _validate_identifier(self.case_id, "案例 ID")
        _validate_version(self.suite_version, "套件版本")
        if not isinstance(self.suite_kind, SuiteKind) or not isinstance(self.risk_level, RiskLevel):
            raise EvaluationGateError("套件类型和风险等级必须是固定枚举。")


@dataclass(frozen=True)
class TraceEvent:
    """最小过程事件，刻意不提供正文、提示、参数或原始响应字段。"""

    run_id: str
    case_id: str
    kind: TraceKind
    before_status: str
    after_status: str
    step_count: int
    tool_call_count: int

    def __post_init__(self) -> None:
        _validate_identifier(self.run_id, "运行 ID")
        _validate_identifier(self.case_id, "案例 ID")
        if not isinstance(self.kind, TraceKind):
            raise EvaluationGateError("事件类型必须是固定枚举。")
        _validate_identifier(self.before_status, "事件前状态")
        _validate_identifier(self.after_status, "事件后状态")
        _validate_non_negative(self.step_count, "步骤计数")
        _validate_non_negative(self.tool_call_count, "工具调用计数")


@dataclass(frozen=True)
class EvaluationResult:
    """一个案例的离线可比较结果；只含状态和最小事件。"""

    case_id: str
    status: CaseStatus
    events: tuple[TraceEvent, ...]

    def __post_init__(self) -> None:
        _validate_identifier(self.case_id, "案例 ID")
        if not isinstance(self.status, CaseStatus):
            raise EvaluationGateError("结果状态必须是固定枚举。")
        if self.status is CaseStatus.NOT_RUN and self.events:
            raise EvaluationGateError("未运行案例不可携带过程事件。")
        if self.status is not CaseStatus.NOT_RUN and not self.events:
            raise EvaluationGateError("已运行案例必须有最小过程事件。")
        if any(event.case_id != self.case_id for event in self.events):
            raise EvaluationGateError("过程事件案例 ID 必须与结果匹配。")


@dataclass(frozen=True)
class ReleaseReport:
    """发布门禁的最小公开决策视图。"""

    baseline_version: str
    candidate_version: str
    decision: ReleaseDecision
    blockers: tuple[ReleaseBlocker, ...]
    case_count: int
    passed_count: int
    failed_count: int
    not_run_count: int


def evaluate_release(
    cases: tuple[EvaluationCase, ...],
    baseline: Mapping[str, EvaluationResult],
    candidate: Mapping[str, EvaluationResult],
    *,
    baseline_version: str,
    candidate_version: str,
    max_soft_regressions: int = 0,
) -> ReleaseReport:
    """比较受控基线与候选，不允许硬失败、未运行或超限软回归。"""
    _validate_version(baseline_version, "基线版本")
    _validate_version(candidate_version, "候选版本")
    if isinstance(max_soft_regressions, bool) or max_soft_regressions < 0:
        raise EvaluationGateError("软回归上限必须是非负整数。")
    if not cases:
        raise EvaluationGateError("发布门禁至少需要一个评测案例。")

    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise EvaluationGateError("评测案例 ID 不可重复。")
    if set(baseline) != set(case_ids) or set(candidate) != set(case_ids):
        raise EvaluationGateError("基线和候选结果必须恰好覆盖固定案例集合。")

    blockers: set[ReleaseBlocker] = set()
    passed_count = 0
    failed_count = 0
    not_run_count = 0
    soft_regressions = 0
    for case in cases:
        baseline_result = baseline[case.case_id]
        candidate_result = candidate[case.case_id]
        _validate_result_identity(case, baseline_result)
        _validate_result_identity(case, candidate_result)
        if baseline_result.status is not CaseStatus.PASSED:
            blockers.add(ReleaseBlocker.BASELINE_MISMATCH)
        if candidate_result.status is CaseStatus.PASSED:
            passed_count += 1
        elif candidate_result.status is CaseStatus.FAILED:
            failed_count += 1
        else:
            not_run_count += 1
            blockers.add(ReleaseBlocker.NOT_RUN)
        if case.risk_level is RiskLevel.HARD and candidate_result.status is not CaseStatus.PASSED:
            blockers.add(ReleaseBlocker.HARD_FAILURE)
        if (
            baseline_result.status is CaseStatus.PASSED
            and candidate_result.status is CaseStatus.FAILED
            and case.risk_level is RiskLevel.SOFT
        ):
            soft_regressions += 1
    if soft_regressions > max_soft_regressions:
        blockers.add(ReleaseBlocker.REGRESSION_FAILURE)
    blocker_tuple = tuple(sorted(blockers, key=str))
    return ReleaseReport(
        baseline_version=baseline_version,
        candidate_version=candidate_version,
        decision=ReleaseDecision.REJECTED if blocker_tuple else ReleaseDecision.APPROVED,
        blockers=blocker_tuple,
        case_count=len(cases),
        passed_count=passed_count,
        failed_count=failed_count,
        not_run_count=not_run_count,
    )


def _validate_result_identity(case: EvaluationCase, result: EvaluationResult) -> None:
    if result.case_id != case.case_id:
        raise EvaluationGateError("评测结果案例 ID 必须与案例匹配。")


def _validate_identifier(value: str, label: str) -> None:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= _MAX_ID_LENGTH
        or not value.replace("-", "").replace("_", "").isalnum()
    ):
        raise EvaluationGateError(f"{label}必须是 1–64 字符的字母数字、短横线或下划线。")


def _validate_version(value: str, label: str) -> None:
    if not isinstance(value, str) or not 1 <= len(value) <= _MAX_VERSION_LENGTH:
        raise EvaluationGateError(f"{label}必须是 1–32 字符的受控字符串。")


def _validate_non_negative(value: int, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise EvaluationGateError(f"{label}必须是非负整数。")
