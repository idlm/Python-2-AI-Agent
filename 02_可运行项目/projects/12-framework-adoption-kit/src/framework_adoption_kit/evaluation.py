"""框架迁移合同的无网络静态回放；不创建真实 checkpoint 或工具调用。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import (
    ActionCandidate,
    ApprovalDecision,
    ApprovalResume,
    CheckpointStatus,
    CheckpointView,
    FrameworkContractError,
    ToolDescriptor,
    candidate_fingerprint,
    validate_approved_resume,
)


class MigrationFixtureError(ValueError):
    """静态迁移夹具不符合固定公开合同。"""


@dataclass(frozen=True)
class MigrationCaseResult:
    case_id: str
    expected: str
    actual: str
    passed: bool


_DESCRIPTOR = ToolDescriptor(
    name="notify_preview",
    allowed_argument_fields=frozenset({"recipient_id", "template_id"}),
    required_argument_fields=frozenset({"recipient_id", "template_id"}),
)
_ALLOWED_CASE_FIELDS = {
    "case_id",
    "candidate",
    "resume_decision",
    "resume_tenant_id",
    "expected",
}
_ALLOWED_CANDIDATE_FIELDS = {"tool_name", "arguments"}
_ALLOWED_RESULTS = {"accepted", "rejected"}


def run_static_migration_cases(path: Path) -> tuple[MigrationCaseResult, ...]:
    """回放公开案例；将受控拒绝归类，而不落盘夹具正文。"""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationFixtureError("静态迁移夹具不可读取或不是合法 JSON。") from exc
    if not isinstance(raw, list) or not raw:
        raise MigrationFixtureError("静态迁移夹具必须是非空数组。")

    results: list[MigrationCaseResult] = []
    case_ids: set[str] = set()
    for raw_case in raw:
        case_id, candidate, decision, resume_tenant, expected = _parse_case(raw_case)
        if case_id in case_ids:
            raise MigrationFixtureError("静态迁移案例 ID 不可重复。")
        case_ids.add(case_id)
        actual = _run_case(candidate, decision, resume_tenant)
        results.append(
            MigrationCaseResult(
                case_id=case_id,
                expected=expected,
                actual=actual,
                passed=actual == expected,
            )
        )
    return tuple(results)


def write_public_migration_report(results: tuple[MigrationCaseResult, ...], path: Path) -> None:
    """原子写入无正文静态报告，仅保存案例 ID、类别和通过标记。"""
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


def _parse_case(raw_case: Any) -> tuple[str, ActionCandidate, ApprovalDecision, str, str]:
    if not isinstance(raw_case, dict) or not set(raw_case) <= _ALLOWED_CASE_FIELDS:
        raise MigrationFixtureError("静态迁移案例必须是字段闭集对象。")
    case_id = raw_case.get("case_id")
    raw_candidate = raw_case.get("candidate")
    raw_decision = raw_case.get("resume_decision")
    resume_tenant = raw_case.get("resume_tenant_id")
    expected = raw_case.get("expected")
    if (
        not isinstance(case_id, str)
        or not isinstance(raw_candidate, dict)
        or not isinstance(raw_decision, str)
        or not isinstance(resume_tenant, str)
        or expected not in _ALLOWED_RESULTS
    ):
        raise MigrationFixtureError("静态迁移案例缺少固定字段或字段值不合法。")
    if set(raw_candidate) != _ALLOWED_CANDIDATE_FIELDS:
        raise MigrationFixtureError("候选必须正好含工具名和参数字段。")
    try:
        candidate = ActionCandidate(
            tool_name=raw_candidate["tool_name"],
            arguments=raw_candidate["arguments"],
        )
        decision = ApprovalDecision(raw_decision)
    except (FrameworkContractError, KeyError, ValueError) as exc:
        raise MigrationFixtureError("候选或审批决定不符合受限合同。") from exc
    return case_id, candidate, decision, resume_tenant, expected


def _run_case(candidate: ActionCandidate, decision: ApprovalDecision, resume_tenant: str) -> str:
    fingerprint = candidate_fingerprint(candidate)
    checkpoint = CheckpointView(
        task_id="fixture-task",
        tenant_id="tenant-1",
        status=CheckpointStatus.WAITING_FOR_APPROVAL,
        pending_tool_name=candidate.tool_name,
        candidate_fingerprint=fingerprint,
    )
    resume = ApprovalResume(
        approval_id="fixture-approval",
        task_id="fixture-task",
        tenant_id=resume_tenant,
        decision=decision,
        tool_name=candidate.tool_name,
        candidate_fingerprint=fingerprint,
        expires_at=datetime(2030, 1, 1, tzinfo=UTC),
    )
    try:
        validate_approved_resume(
            checkpoint,
            candidate,
            _DESCRIPTOR,
            resume,
            now=datetime(2029, 1, 1, tzinfo=UTC),
        )
    except FrameworkContractError:
        return "rejected"
    return "accepted"
