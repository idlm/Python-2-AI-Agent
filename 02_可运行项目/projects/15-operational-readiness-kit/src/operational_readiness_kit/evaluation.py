"""公开静态运行准备夹具回放；不读取环境、秘密或任何外部服务。"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from .core import (
    Capability,
    DeploymentProfile,
    DrillState,
    Environment,
    OperationalReadinessError,
    OperationalRunbook,
    ReadinessDecision,
    RecoveryPlan,
    SecretMetadata,
    SecretState,
    evaluate_operational_readiness,
)

_CASE_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "case_id",
        "environment",
        "app_version",
        "required_secret_states",
        "drain_supported",
        "drill_state",
        "compatible_versions",
        "runbook_complete",
        "expected",
    }
)


class ReadinessFixtureError(ValueError):
    """公开静态运行准备夹具不能按固定合同解析或写入。"""


@dataclass(frozen=True)
class StaticReadinessResult:
    case_id: str
    expected: ReadinessDecision
    actual: ReadinessDecision
    passed: bool
    blocker_count: int


def run_static_readiness_cases(path: Path) -> tuple[StaticReadinessResult, ...]:
    """回放公开教学夹具，不接受任意部署配置、秘密或网络输入。"""
    raw_cases = _read_case_array(path)
    seen_ids: set[str] = set()
    results: list[StaticReadinessResult] = []
    for raw_case in raw_cases:
        case = _parse_case(raw_case)
        case_id = _required_string(case, "case_id")
        if case_id in seen_ids:
            raise ReadinessFixtureError("静态案例 ID 不可重复。")
        seen_ids.add(case_id)
        result = _evaluate_case(case)
        results.append(result)
    return tuple(results)


def write_public_readiness_report(
    results: tuple[StaticReadinessResult, ...], output_path: Path
) -> None:
    """原子写入最小公开报告；绝不持久化夹具详情、秘密或 Runbook 正文。"""
    report = {
        "case_count": len(results),
        "passed_count": sum(result.passed for result in results),
        "results": [
            {
                "case_id": result.case_id,
                "expected": result.expected.value,
                "actual": result.actual.value,
                "passed": result.passed,
                "blocker_count": result.blocker_count,
            }
            for result in results
        ],
    }
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary_path, output_path)
    except OSError as exc:
        temporary_path.unlink(missing_ok=True)
        raise ReadinessFixtureError("公开评测报告不可写入。") from exc


def _read_case_array(path: Path) -> list[Mapping[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReadinessFixtureError("静态评测夹具不可读取或不是合法 JSON。") from exc
    if not isinstance(raw, list) or not raw:
        raise ReadinessFixtureError("静态评测夹具必须是非空案例数组。")
    if not all(isinstance(item, dict) for item in raw):
        raise ReadinessFixtureError("静态评测夹具的每项必须是对象。")
    return raw


def _parse_case(raw_case: Mapping[str, Any]) -> Mapping[str, Any]:
    if set(raw_case) != _CASE_FIELDS:
        raise ReadinessFixtureError("静态评测案例必须且只能包含固定字段。")
    return raw_case


def _evaluate_case(case: Mapping[str, Any]) -> StaticReadinessResult:
    case_id = _required_string(case, "case_id")
    try:
        environment = Environment(_required_string(case, "environment"))
        expected = ReadinessDecision(_required_string(case, "expected"))
        secret_states = _string_list(case, "required_secret_states")
        compatible_versions = frozenset(_string_list(case, "compatible_versions"))
        drain_supported = _required_bool(case, "drain_supported")
        runbook_complete = _required_bool(case, "runbook_complete")
        profile = DeploymentProfile(
            profile_id=f"profile-{case_id}",
            app_version=_required_string(case, "app_version"),
            environment=environment,
            enabled_capabilities=frozenset(Capability),
            required_secret_ids=tuple(
                f"secret-{case_id}-{index}" for index in range(len(secret_states))
            ),
            drain_supported=drain_supported,
        )
        secrets = tuple(
            SecretMetadata(
                secret_id=f"secret-{case_id}-{index}",
                environment=environment,
                purpose="runtime-auth",
                state=SecretState(state),
                rotation_version="r1",
            )
            for index, state in enumerate(secret_states)
        )
        recovery = RecoveryPlan(
            plan_id=f"recovery-{case_id}",
            backup_format_version="backup-v1",
            compatible_app_versions=compatible_versions,
            drill_state=DrillState(_required_string(case, "drill_state")),
        )
        runbook = OperationalRunbook(
            runbook_id=f"runbook-{case_id}",
            has_pause_step=runbook_complete,
            has_recovery_step=runbook_complete,
            has_escalation_step=runbook_complete,
            reviewed=runbook_complete,
        )
        report = evaluate_operational_readiness(profile, secrets, recovery, runbook)
    except (OperationalReadinessError, ValueError) as exc:
        raise ReadinessFixtureError("静态评测案例字段或枚举不合法。") from exc
    return StaticReadinessResult(
        case_id=case_id,
        expected=expected,
        actual=report.decision,
        passed=expected is report.decision,
        blocker_count=len(report.blockers),
    )


def _required_string(case: Mapping[str, Any], name: str) -> str:
    value = case[name]
    if not isinstance(value, str) or not value:
        raise ReadinessFixtureError(f"静态评测案例字段 {name} 必须是非空字符串。")
    return value


def _required_bool(case: Mapping[str, Any], name: str) -> bool:
    value = case[name]
    if not isinstance(value, bool):
        raise ReadinessFixtureError(f"静态评测案例字段 {name} 必须是布尔值。")
    return value


def _string_list(case: Mapping[str, Any], name: str) -> list[str]:
    value = case[name]
    if not isinstance(value, list) or not value:
        raise ReadinessFixtureError(f"静态评测案例字段 {name} 必须是非空字符串数组。")
    strings: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise ReadinessFixtureError(f"静态评测案例字段 {name} 必须是非空字符串数组。")
        strings.append(item)
    return strings
