"""受限 Agent 的离线静态夹具回放；不调用模型或外部工具。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .core import ActionKind, AgentStatus, AgentTask, BoundedAgent


class EvaluationFixtureError(ValueError):
    """静态 Agent 评测夹具不符合固定合同。"""


@dataclass(frozen=True)
class AgentCaseResult:
    case_id: str
    expected_status: AgentStatus
    actual_status: AgentStatus
    passed: bool


def run_static_cases(path: Path) -> tuple[AgentCaseResult, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise EvaluationFixtureError("评测夹具必须是非空数组。")
    results: list[AgentCaseResult] = []
    case_ids: set[str] = set()
    for raw_case in raw:
        case_id, actions, approval, argument, expected = _parse_case(raw_case)
        if case_id in case_ids:
            raise EvaluationFixtureError("评测案例 ID 不可重复。")
        case_ids.add(case_id)
        agent = BoundedAgent(lambda _: "public-test-result")
        task = agent.start(AgentTask(task_id=case_id, goal="static-case"))
        for action in actions:
            action_argument = argument if action is ActionKind.LOOKUP_PUBLIC_FACT else ""
            task, _ = agent.step(task, action, action_argument)
        if task.status is AgentStatus.WAITING_FOR_APPROVAL:
            task = agent.approve(task, approved=approval)
        results.append(
            AgentCaseResult(
                case_id=case_id,
                expected_status=expected,
                actual_status=task.status,
                passed=task.status is expected,
            )
        )
    return tuple(results)


def write_public_evaluation_report(results: tuple[AgentCaseResult, ...], path: Path) -> None:
    """写入无正文评测摘要；仅持久化固定案例状态合同。"""
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


def _parse_case(raw: Any) -> tuple[str, tuple[ActionKind, ...], bool, str, AgentStatus]:
    if not isinstance(raw, dict):
        raise EvaluationFixtureError("评测案例必须是对象。")
    expected_fields = {"case_id", "action_sequence", "expected_status", "approval", "argument"}
    if not set(raw) <= expected_fields:
        raise EvaluationFixtureError("评测案例含未允许字段。")
    case_id = raw.get("case_id")
    actions = raw.get("action_sequence")
    expected = raw.get("expected_status")
    if (
        not isinstance(case_id, str)
        or not isinstance(actions, list)
        or not isinstance(expected, str)
    ):
        raise EvaluationFixtureError("评测案例缺少固定字段。")
    if not actions:
        raise EvaluationFixtureError("评测动作序列不可为空。")
    try:
        action_values = tuple(ActionKind(item) for item in actions)
        expected_status = AgentStatus(expected)
    except ValueError as exc:
        raise EvaluationFixtureError("评测动作或状态不在允许枚举中。") from exc
    approval = raw.get("approval", True)
    argument = raw.get("argument", "公开测试输入")
    if not isinstance(approval, bool) or not isinstance(argument, str):
        raise EvaluationFixtureError("审批和参数字段类型不合法。")
    return case_id, action_values, approval, argument, expected_status
