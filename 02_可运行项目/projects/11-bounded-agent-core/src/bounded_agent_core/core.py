"""无框架受限 Agent 的最小状态与纯工具合同。"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Final

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
_MAX_STEPS: Final[int] = 5
_MAX_TOOL_CALLS: Final[int] = 2


class AgentContractError(ValueError):
    """任务状态、动作或工具合同不符合允许边界。"""


class AgentStatus(StrEnum):
    READY = "ready"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class ActionKind(StrEnum):
    LOOKUP_PUBLIC_FACT = "lookup_public_fact"
    COMPLETE = "complete"
    REQUEST_APPROVAL = "request_approval"


class StopReason(StrEnum):
    STEP_BUDGET_EXHAUSTED = "step_budget_exhausted"
    TOOL_CALL_BUDGET_EXHAUSTED = "tool_call_budget_exhausted"
    APPROVAL_DENIED = "approval_denied"


@dataclass(frozen=True)
class AgentTask:
    task_id: str
    goal: str
    status: AgentStatus = AgentStatus.READY
    step_count: int = 0
    tool_calls: int = 0
    stop_reason: StopReason | None = None

    def __post_init__(self) -> None:
        valid_task_id = (
            isinstance(self.task_id, str)
            and 1 <= len(self.task_id) <= 64
            and self.task_id.replace("-", "").replace("_", "").isalnum()
        )
        if not valid_task_id:
            raise AgentContractError("task_id 必须是 1–64 字符的字母数字、短横线或下划线。")
        if not isinstance(self.goal, str) or not self.goal.strip() or len(self.goal) > 300:
            raise AgentContractError("goal 必须是 1–300 字符的非空字符串。")
        if not isinstance(self.status, AgentStatus):
            raise AgentContractError("status 必须是当前受限 Agent 状态枚举。")
        if self.step_count < 0 or self.tool_calls < 0:
            raise AgentContractError("步骤数和工具调用数必须非负。")
        if self.stop_reason is not None and not isinstance(self.stop_reason, StopReason):
            raise AgentContractError("stop_reason 必须是当前受限 Agent 停止原因枚举或 None。")
        if self.status is AgentStatus.STOPPED and self.stop_reason is None:
            raise AgentContractError("stopped 任务必须携带受控 stop_reason。")
        if self.status is not AgentStatus.STOPPED and self.stop_reason is not None:
            raise AgentContractError("只有 stopped 任务可携带 stop_reason。")


@dataclass(frozen=True)
class AgentEvent:
    task_id: str
    step_count: int
    status: AgentStatus
    action: ActionKind
    result_category: str


PureTool = Callable[[str], str]


class BoundedAgent:
    """只执行固定纯工具、最多五步的教学状态机；不是自主执行系统。"""

    def __init__(self, public_lookup: PureTool) -> None:
        self._public_lookup = public_lookup

    def start(self, task: AgentTask) -> AgentTask:
        if task.status is not AgentStatus.READY:
            raise AgentContractError("任务只能从 ready 状态启动。")
        return replace(task, status=AgentStatus.RUNNING)

    def step(
        self,
        task: AgentTask,
        action: ActionKind,
        argument: str = "",
    ) -> tuple[AgentTask, AgentEvent]:
        if task.status is not AgentStatus.RUNNING:
            raise AgentContractError("只有 running 任务可执行步骤。")
        if task.step_count >= _MAX_STEPS:
            stopped = replace(
                task,
                status=AgentStatus.STOPPED,
                stop_reason=StopReason.STEP_BUDGET_EXHAUSTED,
            )
            return stopped, _event(stopped, action, "budget_exhausted")
        if action is ActionKind.REQUEST_APPROVAL:
            waiting = replace(
                task,
                status=AgentStatus.WAITING_FOR_APPROVAL,
                step_count=task.step_count + 1,
            )
            return waiting, _event(waiting, action, "approval_required")
        if action is ActionKind.COMPLETE:
            completed = replace(
                task,
                status=AgentStatus.COMPLETED,
                step_count=task.step_count + 1,
            )
            return completed, _event(completed, action, "completed")
        if action is not ActionKind.LOOKUP_PUBLIC_FACT:
            raise AgentContractError("动作不在当前 Agent 允许列表中。")
        if not isinstance(argument, str) or not argument.strip() or len(argument) > 120:
            raise AgentContractError("纯工具参数必须是 1–120 字符的非空字符串。")
        if task.tool_calls >= _MAX_TOOL_CALLS:
            stopped = replace(
                task,
                status=AgentStatus.STOPPED,
                stop_reason=StopReason.TOOL_CALL_BUDGET_EXHAUSTED,
            )
            return stopped, _event(stopped, action, "tool_call_budget_exhausted")
        self._public_lookup(argument.strip())
        advanced = replace(task, step_count=task.step_count + 1, tool_calls=task.tool_calls + 1)
        LOGGER.info("agent_pure_tool task_id=%s step=%s", task.task_id, advanced.step_count)
        return advanced, _event(advanced, action, "public_lookup_completed")

    def approve(self, task: AgentTask, *, approved: bool) -> AgentTask:
        if task.status is not AgentStatus.WAITING_FOR_APPROVAL:
            raise AgentContractError("只有等待审批的任务可被审批。")
        if not approved:
            return replace(
                task,
                status=AgentStatus.STOPPED,
                stop_reason=StopReason.APPROVAL_DENIED,
            )
        return replace(task, status=AgentStatus.RUNNING)


def _event(task: AgentTask, action: ActionKind, result_category: str) -> AgentEvent:
    return AgentEvent(
        task_id=task.task_id,
        step_count=task.step_count,
        status=task.status,
        action=action,
        result_category=result_category,
    )
