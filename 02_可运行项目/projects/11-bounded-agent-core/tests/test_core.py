from __future__ import annotations

import pytest

from bounded_agent_core.core import (
    ActionKind,
    AgentContractError,
    AgentStatus,
    AgentTask,
    BoundedAgent,
    StopReason,
)


def test_pure_tool_progress_and_completion() -> None:
    calls: list[str] = []
    agent = BoundedAgent(calls.append)
    task = agent.start(AgentTask(task_id="task-1", goal="公开事实查询"))

    task, event = agent.step(task, ActionKind.LOOKUP_PUBLIC_FACT, "Python")
    task, completed = agent.step(task, ActionKind.COMPLETE)

    assert calls == ["Python"]
    assert event.result_category == "public_lookup_completed"
    assert task.status is AgentStatus.COMPLETED
    assert completed.result_category == "completed"


def test_approval_is_a_pause_not_model_text() -> None:
    agent = BoundedAgent(lambda _: "public")
    task = agent.start(AgentTask(task_id="task-2", goal="审批"))

    waiting, event = agent.step(task, ActionKind.REQUEST_APPROVAL)
    resumed = agent.approve(waiting, approved=True)
    denied = agent.approve(waiting, approved=False)

    assert event.status is AgentStatus.WAITING_FOR_APPROVAL
    assert resumed.status is AgentStatus.RUNNING
    assert denied.status is AgentStatus.STOPPED
    assert denied.stop_reason is StopReason.APPROVAL_DENIED


def test_budget_and_invalid_paths_are_controlled() -> None:
    agent = BoundedAgent(lambda _: "public")
    task = agent.start(AgentTask(task_id="task-3", goal="预算", step_count=5))

    stopped, event = agent.step(task, ActionKind.LOOKUP_PUBLIC_FACT, "Python")

    assert stopped.status is AgentStatus.STOPPED
    assert event.result_category == "budget_exhausted"
    assert stopped.stop_reason is StopReason.STEP_BUDGET_EXHAUSTED
    with pytest.raises(AgentContractError, match="只有 running"):
        agent.step(stopped, ActionKind.COMPLETE)
    invalid_task = agent.start(AgentTask(task_id="task-4", goal="参数"))
    with pytest.raises(AgentContractError, match="1–120"):
        agent.step(invalid_task, ActionKind.LOOKUP_PUBLIC_FACT)


@pytest.mark.parametrize(
    ("task_id", "goal", "step_count"),
    [
        ("bad id", "合法目标", 0),
        ("task-5", "", 0),
        ("task-5", "x" * 301, 0),
        ("task-5", "合法目标", -1),
    ],
)
def test_task_rejects_invalid_identity_goal_or_counter(
    task_id: str,
    goal: str,
    step_count: int,
) -> None:
    with pytest.raises(AgentContractError):
        AgentTask(task_id=task_id, goal=goal, step_count=step_count)


def test_tool_call_budget_stops_before_pure_tool_executes() -> None:
    calls: list[str] = []
    agent = BoundedAgent(calls.append)
    task = agent.start(AgentTask(task_id="task-tool-budget", goal="工具预算", tool_calls=2))

    stopped, event = agent.step(task, ActionKind.LOOKUP_PUBLIC_FACT, "Python")

    assert calls == []
    assert stopped.status is AgentStatus.STOPPED
    assert stopped.tool_calls == 2
    assert stopped.step_count == 0
    assert stopped.stop_reason is StopReason.TOOL_CALL_BUDGET_EXHAUSTED
    assert event.result_category == "tool_call_budget_exhausted"


def test_task_rejects_uncontrolled_stop_reason() -> None:
    with pytest.raises(AgentContractError, match="stop_reason"):
        AgentTask(task_id="task-stop", goal="停止原因", stop_reason="arbitrary")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("status", "stop_reason"),
    [
        (AgentStatus.STOPPED, None),
        (AgentStatus.RUNNING, StopReason.APPROVAL_DENIED),
    ],
)
def test_task_rejects_inconsistent_status_and_stop_reason(
    status: AgentStatus,
    stop_reason: StopReason | None,
) -> None:
    with pytest.raises(AgentContractError):
        AgentTask(
            task_id="task-inconsistent-stop",
            goal="状态一致性",
            status=status,
            stop_reason=stop_reason,
        )
