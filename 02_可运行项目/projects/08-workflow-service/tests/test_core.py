"""服务工作流领域状态机测试。"""

import logging
from datetime import UTC, datetime

import pytest

from workflow_service.core import (
    CapacityExceededError,
    IdempotencyConflictError,
    InvalidTransitionError,
    TaskRequest,
    TaskRequestError,
    TaskState,
    UnknownTaskError,
    WorkflowRegistry,
)


class FixedClock:
    """每次调用都前进一秒的可预测时钟。"""

    def __init__(self) -> None:
        self._second = 0

    def __call__(self) -> datetime:
        self._second += 1
        return datetime(2026, 8, 26, 0, 0, self._second, tzinfo=UTC)


def registry(*, max_tasks: int = 100) -> WorkflowRegistry:
    return WorkflowRegistry(
        allowed_task_types={"refresh_catalog", "rebuild_index"},
        max_tasks=max_tasks,
        clock=FixedClock(),
    )


def request(
    *,
    task_type: str = "refresh_catalog",
    work_reference: str = "catalog-2026-08",
    idempotency_key: str = "accept-catalog-001",
) -> TaskRequest:
    return TaskRequest(
        task_type=task_type,
        work_reference=work_reference,
        idempotency_key=idempotency_key,
    )


def test_accept_returns_pending_public_view_without_sensitive_reference() -> None:
    task = registry().accept(request(work_reference="private-work-reference"))

    assert task.state is TaskState.PENDING
    assert task.attempts == 0
    assert task.recoveries == 0
    assert not hasattr(task, "work_reference")
    assert task.created_at == task.updated_at


def test_same_idempotency_contract_returns_existing_task() -> None:
    tasks = registry()

    first = tasks.accept(request())
    second = tasks.accept(request())

    assert second.task_id == first.task_id
    assert len(tasks.list_tasks()) == 1


def test_idempotency_key_cannot_be_reused_for_different_work() -> None:
    tasks = registry()
    tasks.accept(request())

    with pytest.raises(IdempotencyConflictError, match="不能对应不同"):
        tasks.accept(request(work_reference="different-catalog"))


def test_rejects_unknown_type_invalid_text_and_capacity() -> None:
    tasks = registry(max_tasks=1)

    with pytest.raises(TaskRequestError, match="允许列表"):
        tasks.accept(request(task_type="arbitrary_command"))
    with pytest.raises(TaskRequestError, match="控制字符"):
        tasks.accept(request(work_reference="catalog\nsecret"))
    tasks.accept(request())
    with pytest.raises(CapacityExceededError, match="上限"):
        tasks.accept(request(idempotency_key="another-key"))


def test_start_succeed_and_terminal_state_transition_rules() -> None:
    tasks = registry()
    pending = tasks.accept(request())

    running = tasks.start(pending.task_id)
    succeeded = tasks.succeed(pending.task_id)

    assert running.state is TaskState.RUNNING
    assert running.attempts == 1
    assert succeeded.state is TaskState.SUCCEEDED
    with pytest.raises(InvalidTransitionError, match="不能转换"):
        tasks.start(pending.task_id)


def test_failure_requires_controlled_code_and_transitions_from_running() -> None:
    tasks = registry()
    pending = tasks.accept(request())

    with pytest.raises(InvalidTransitionError):
        tasks.fail(pending.task_id, error_code="execution_failed")
    tasks.start(pending.task_id)
    failed = tasks.fail(pending.task_id, error_code="upstream_failed")

    assert failed.state is TaskState.FAILED
    assert failed.error_code == "upstream_failed"
    with pytest.raises(TaskRequestError, match="允许集合"):
        tasks.fail(pending.task_id, error_code="private_stack_trace")


def test_cancel_accepts_pending_or_running_but_not_terminal() -> None:
    tasks = registry()
    first = tasks.accept(request())
    cancelled = tasks.cancel(first.task_id)
    second = tasks.accept(request(idempotency_key="running-cancel"))
    tasks.start(second.task_id)
    running_cancelled = tasks.cancel(second.task_id)

    assert cancelled.state is TaskState.CANCELLED
    assert running_cancelled.state is TaskState.CANCELLED
    with pytest.raises(InvalidTransitionError):
        tasks.cancel(first.task_id)


def test_running_tasks_are_marked_pending_for_explicit_recovery() -> None:
    tasks = registry()
    first = tasks.accept(request())
    second = tasks.accept(request(idempotency_key="second-task"))
    tasks.start(first.task_id)
    recovered = tasks.mark_interrupted_for_recovery()

    assert [item.task_id for item in recovered] == [first.task_id]
    restored = tasks.get(first.task_id)
    untouched = tasks.get(second.task_id)
    assert restored.state is TaskState.PENDING
    assert restored.recoveries == 1
    assert restored.error_code == "interrupted"
    assert untouched.state is TaskState.PENDING


def test_unknown_task_is_controlled_error() -> None:
    with pytest.raises(UnknownTaskError, match="不存在"):
        registry().get("task-missing")


def test_logs_task_type_and_counts_without_work_reference(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_reference = "正文和秘密工作引用绝不进入运行日志"
    tasks = registry()

    caplog.set_level(logging.INFO, logger="workflow_service.core")
    accepted = tasks.accept(request(work_reference=secret_reference))
    tasks.start(accepted.task_id)
    tasks.succeed(accepted.task_id)

    assert "workflow_task_accepted task_type=refresh_catalog" in caplog.text
    assert "workflow_task_started task_type=refresh_catalog attempts=1" in caplog.text
    assert secret_reference not in caplog.text
