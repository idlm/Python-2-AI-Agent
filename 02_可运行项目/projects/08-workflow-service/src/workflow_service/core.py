"""服务工作流的受控领域状态机（版本 0.1.0）。

此模块只建模短任务的状态、幂等接受和进程中断后的恢复候选。它不是持久化
消息队列、跨进程锁、分布式事务或任务结果存储；这些边界由后续适配层明确处理。
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from threading import RLock
from uuid import uuid4

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())


class TaskState(StrEnum):
    """工作流任务允许向调用方公开的状态。"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATES: frozenset[TaskState] = frozenset(
    {TaskState.SUCCEEDED, TaskState.FAILED, TaskState.CANCELLED}
)


class WorkflowError(Exception):
    """工作流领域层的公开受控失败基类。"""


class TaskRequestError(WorkflowError):
    """提交的任务类型、工作引用或幂等键不符合合同。"""


class UnknownTaskError(WorkflowError):
    """请求了不存在的任务。"""


class InvalidTransitionError(WorkflowError):
    """请求的状态转换不在受审查状态图中。"""


class IdempotencyConflictError(WorkflowError):
    """同一幂等键被用于不同工作合同。"""


class CapacityExceededError(WorkflowError):
    """进程内教学注册表已达到受控任务上限。"""


@dataclass(frozen=True)
class TaskRequest:
    """只含任务调度必要元数据的提交请求，不承载任意可执行配置。"""

    task_type: str
    work_reference: str
    idempotency_key: str


@dataclass(frozen=True)
class TaskRecord:
    """不可变的内部任务状态；work_reference 不应进入运行日志或公开响应。"""

    task_id: str
    task_type: str
    work_reference: str
    idempotency_key: str
    state: TaskState
    attempts: int
    recoveries: int
    error_code: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class PublicTask:
    """返回给 API/CLI 的任务视图，刻意不含工作引用和幂等键。"""

    task_id: str
    task_type: str
    state: TaskState
    attempts: int
    recoveries: int
    error_code: str | None
    created_at: str
    updated_at: str


class WorkflowRegistry:
    """受控任务状态表，适合单进程教学原型。"""

    def __init__(
        self,
        *,
        allowed_task_types: Iterable[str],
        max_tasks: int = 100,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        normalized_types = frozenset(item.strip() for item in allowed_task_types if item.strip())
        if not normalized_types:
            raise ValueError("至少要声明一个允许任务类型。")
        if max_tasks < 1:
            raise ValueError("任务上限必须大于零。")
        self._allowed_task_types = normalized_types
        self._max_tasks = max_tasks
        self._clock = clock or (lambda: datetime.now(UTC))
        self._records: dict[str, TaskRecord] = {}
        self._idempotency: dict[str, tuple[str, str, str]] = {}
        self._lock = RLock()

    @property
    def allowed_task_types(self) -> frozenset[str]:
        """返回不可变允许列表，供受控 worker 注册处理器而非动态导入。"""
        return self._allowed_task_types

    def lookup_idempotency(self, request: TaskRequest) -> PublicTask | None:
        """读取同一幂等合同的既有公开任务；冲突仍受控拒绝。"""
        self._validate_request(request)
        with self._lock:
            existing = self._idempotency.get(request.idempotency_key)
            if existing is None:
                return None
            existing_type, existing_reference, existing_task_id = existing
            if (existing_type, existing_reference) != (request.task_type, request.work_reference):
                raise IdempotencyConflictError("同一幂等键不能对应不同任务类型或工作引用。")
            return self._public(self._records[existing_task_id])

    def accept(self, request: TaskRequest) -> PublicTask:
        """接受新任务，或在同一幂等合同下返回既有任务。"""
        self._validate_request(request)
        signature = (request.task_type, request.work_reference, request.idempotency_key)
        with self._lock:
            existing = self._idempotency.get(request.idempotency_key)
            if existing is not None:
                existing_type, existing_reference, existing_task_id = existing
                if (existing_type, existing_reference) != signature[:2]:
                    raise IdempotencyConflictError("同一幂等键不能对应不同任务类型或工作引用。")
                return self._public(self._records[existing_task_id])
            if len(self._records) >= self._max_tasks:
                raise CapacityExceededError("当前工作流注册表已达到任务上限。")
            now = self._timestamp()
            task_id = f"task-{uuid4().hex}"
            record = TaskRecord(
                task_id=task_id,
                task_type=request.task_type,
                work_reference=request.work_reference,
                idempotency_key=request.idempotency_key,
                state=TaskState.PENDING,
                attempts=0,
                recoveries=0,
                error_code=None,
                created_at=now,
                updated_at=now,
            )
            self._records[task_id] = record
            self._idempotency[request.idempotency_key] = (
                request.task_type,
                request.work_reference,
                task_id,
            )
        LOGGER.info("workflow_task_accepted task_type=%s", request.task_type)
        return self._public(record)

    def get(self, task_id: str) -> PublicTask:
        """读取单个公开任务视图。"""
        with self._lock:
            return self._public(self._require(task_id))

    def list_tasks(self) -> list[PublicTask]:
        """按创建顺序返回公开视图；当前实现不提供无界分页。"""
        with self._lock:
            return [self._public(record) for record in self._records.values()]

    def start(self, task_id: str) -> PublicTask:
        """将 pending 任务交给一个受控 worker 开始处理，并返回公开视图。"""
        return self._public(self.begin(task_id))

    def begin(self, task_id: str) -> TaskRecord:
        """供同一受控进程内 worker 原子领取任务；不得直接回显返回的工作引用。"""
        record = self._transition(
            task_id,
            expected={TaskState.PENDING},
            next_state=TaskState.RUNNING,
        )
        updated = replace(record, attempts=record.attempts + 1)
        self._replace(updated)
        LOGGER.info(
            "workflow_task_started task_type=%s attempts=%s",
            updated.task_type,
            updated.attempts,
        )
        with self._lock:
            return self._records[task_id]

    def succeed(self, task_id: str) -> PublicTask:
        """将 running 任务标为成功；完成不是“已接受”。"""
        record = self._transition(
            task_id,
            expected={TaskState.RUNNING},
            next_state=TaskState.SUCCEEDED,
        )
        LOGGER.info("workflow_task_succeeded task_type=%s", record.task_type)
        return self._public(record)

    def fail(self, task_id: str, *, error_code: str) -> PublicTask:
        """将 running 任务以白名单风格错误代码标为失败。"""
        self._validate_error_code(error_code)
        record = self._transition(
            task_id,
            expected={TaskState.RUNNING},
            next_state=TaskState.FAILED,
        )
        updated = replace(record, error_code=error_code)
        self._replace(updated)
        LOGGER.info(
            "workflow_task_failed task_type=%s error_code=%s",
            updated.task_type,
            error_code,
        )
        return self._public(updated)

    def cancel(self, task_id: str) -> PublicTask:
        """取消尚未终结的任务；运行中执行者仍必须自行响应取消和清理。"""
        record = self._transition(
            task_id,
            expected={TaskState.PENDING, TaskState.RUNNING},
            next_state=TaskState.CANCELLED,
        )
        LOGGER.info("workflow_task_cancelled task_type=%s", record.task_type)
        return self._public(record)

    def mark_interrupted_for_recovery(self) -> list[PublicTask]:
        """把进程停止时仍 running 的任务放回 pending，供显式恢复策略决定是否重跑。"""
        recovered: list[PublicTask] = []
        with self._lock:
            running_records = [
                record for record in self._records.values() if record.state is TaskState.RUNNING
            ]
            for record in running_records:
                updated = replace(
                    record,
                    state=TaskState.PENDING,
                    recoveries=record.recoveries + 1,
                    error_code="interrupted",
                    updated_at=self._timestamp(),
                )
                self._records[record.task_id] = updated
                recovered.append(self._public(updated))
        if recovered:
            LOGGER.warning("workflow_interrupted_tasks_marked count=%s", len(recovered))
        return recovered

    def _transition(
        self,
        task_id: str,
        *,
        expected: set[TaskState],
        next_state: TaskState,
    ) -> TaskRecord:
        with self._lock:
            record = self._require(task_id)
            if record.state not in expected:
                raise InvalidTransitionError(
                    f"任务当前状态为 {record.state.value}，不能转换到 {next_state.value}。"
                )
            updated = replace(record, state=next_state, updated_at=self._timestamp())
            self._records[task_id] = updated
            return updated

    def _replace(self, record: TaskRecord) -> None:
        with self._lock:
            self._records[record.task_id] = replace(record, updated_at=self._timestamp())

    def _require(self, task_id: str) -> TaskRecord:
        try:
            return self._records[task_id]
        except KeyError as exc:
            raise UnknownTaskError("任务不存在。") from exc

    def _validate_request(self, request: TaskRequest) -> None:
        if request.task_type not in self._allowed_task_types:
            raise TaskRequestError("任务类型不在允许列表中。")
        self._validate_text(request.work_reference, "工作引用")
        self._validate_text(request.idempotency_key, "幂等键")

    @staticmethod
    def _validate_text(value: str, label: str) -> None:
        if not isinstance(value, str) or not value.strip() or len(value) > 160:
            raise TaskRequestError(f"{label}必须是 1–160 个字符的非空字符串。")
        if any(ord(character) < 32 for character in value):
            raise TaskRequestError(f"{label}不能含控制字符。")

    @staticmethod
    def _validate_error_code(error_code: str) -> None:
        allowed_codes = frozenset(
            {"cancelled_by_policy", "execution_failed", "timeout", "upstream_failed"}
        )
        if error_code not in allowed_codes:
            raise TaskRequestError("错误代码不在允许集合中。")

    def _timestamp(self) -> str:
        now = self._clock()
        if now.tzinfo is None:
            raise ValueError("工作流时钟必须返回带时区的时间。")
        return now.astimezone(UTC).isoformat()

    @staticmethod
    def _public(record: TaskRecord) -> PublicTask:
        return PublicTask(
            task_id=record.task_id,
            task_type=record.task_type,
            state=record.state,
            attempts=record.attempts,
            recoveries=record.recoveries,
            error_code=record.error_code,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
