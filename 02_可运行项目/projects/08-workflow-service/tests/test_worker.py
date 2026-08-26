"""有界工作器与结构化并发测试。"""

import asyncio
import logging

import pytest

from workflow_service.core import TaskRecord, TaskRequest, TaskState, WorkflowRegistry
from workflow_service.worker import (
    QueueCapacityError,
    WorkerBusyError,
    WorkerConfigurationError,
    WorkflowWorkerEngine,
)


async def no_op_handler(record: TaskRecord) -> None:
    assert record.work_reference


def make_registry() -> WorkflowRegistry:
    return WorkflowRegistry(allowed_task_types={"refresh_catalog"})


def make_engine(
    registry: WorkflowRegistry,
    *,
    handler: object = no_op_handler,
    queue_maxsize: int = 10,
    worker_count: int = 1,
    timeout: float = 1.0,
) -> WorkflowWorkerEngine:
    assert callable(handler)
    return WorkflowWorkerEngine(
        registry,
        handlers={"refresh_catalog": handler},
        queue_maxsize=queue_maxsize,
        worker_count=worker_count,
        task_timeout_seconds=timeout,
    )


def request(*, key: str = "key-001", reference: str = "catalog-001") -> TaskRequest:
    return TaskRequest(
        task_type="refresh_catalog",
        work_reference=reference,
        idempotency_key=key,
    )


@pytest.mark.asyncio
async def test_submit_then_drain_marks_task_succeeded() -> None:
    registry = make_registry()
    engine = make_engine(registry)

    accepted = await engine.submit(request())
    await engine.run_until_idle()

    finished = registry.get(accepted.task_id)
    assert finished.state is TaskState.SUCCEEDED
    assert finished.attempts == 1
    assert engine.queued_count == 0


@pytest.mark.asyncio
async def test_queue_backpressure_rejects_new_task_before_registry_acceptance() -> None:
    registry = make_registry()
    engine = make_engine(registry, queue_maxsize=1)
    first = await engine.submit(request())

    with pytest.raises(QueueCapacityError, match="已满"):
        await engine.submit(request(key="key-002", reference="catalog-002"))
    duplicate = await engine.submit(request())

    assert duplicate.task_id == first.task_id
    assert len(registry.list_tasks()) == 1


@pytest.mark.asyncio
async def test_handler_exception_maps_to_controlled_failure_code() -> None:
    async def failing_handler(record: TaskRecord) -> None:
        assert record.task_type == "refresh_catalog"
        raise RuntimeError("private stack details")

    registry = make_registry()
    engine = make_engine(registry, handler=failing_handler)
    accepted = await engine.submit(request())

    await engine.run_until_idle()

    finished = registry.get(accepted.task_id)
    assert finished.state is TaskState.FAILED
    assert finished.error_code == "execution_failed"


@pytest.mark.asyncio
async def test_timeout_cancels_handler_and_runs_cleanup() -> None:
    cleaned = asyncio.Event()

    async def slow_handler(record: TaskRecord) -> None:
        try:
            assert record.task_type == "refresh_catalog"
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    registry = make_registry()
    engine = make_engine(registry, handler=slow_handler, timeout=0.01)
    accepted = await engine.submit(request())

    await engine.run_until_idle()

    assert cleaned.is_set()
    finished = registry.get(accepted.task_id)
    assert finished.state is TaskState.FAILED
    assert finished.error_code == "timeout"


@pytest.mark.asyncio
async def test_cancel_running_handler_cleans_up_and_leaves_cancelled_state() -> None:
    started = asyncio.Event()
    cleaned = asyncio.Event()

    async def waiting_handler(record: TaskRecord) -> None:
        try:
            assert record.work_reference == "catalog-001"
            started.set()
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    registry = make_registry()
    engine = make_engine(registry, handler=waiting_handler)
    accepted = await engine.submit(request())
    drain = asyncio.create_task(engine.run_until_idle())
    await started.wait()

    cancelled = engine.cancel(accepted.task_id)
    await drain

    assert cancelled.state is TaskState.CANCELLED
    assert cleaned.is_set()
    assert registry.get(accepted.task_id).state is TaskState.CANCELLED


@pytest.mark.asyncio
async def test_worker_count_is_a_real_concurrency_upper_bound() -> None:
    release = asyncio.Event()
    started = asyncio.Event()
    active = 0
    maximum_active = 0

    async def measured_handler(record: TaskRecord) -> None:
        nonlocal active, maximum_active
        assert record.task_type == "refresh_catalog"
        active += 1
        maximum_active = max(maximum_active, active)
        if active == 2:
            started.set()
        await release.wait()
        active -= 1

    registry = make_registry()
    engine = make_engine(registry, handler=measured_handler, worker_count=2)
    for number in range(3):
        await engine.submit(request(key=f"key-{number}", reference=f"catalog-{number}"))
    drain = asyncio.create_task(engine.run_until_idle())
    await started.wait()

    assert maximum_active == 2
    release.set()
    await drain
    assert all(task.state is TaskState.SUCCEEDED for task in registry.list_tasks())


@pytest.mark.asyncio
async def test_second_drain_is_rejected_while_first_is_running() -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    async def blocking_handler(record: TaskRecord) -> None:
        assert record.task_type == "refresh_catalog"
        started.set()
        await release.wait()

    registry = make_registry()
    engine = make_engine(registry, handler=blocking_handler)
    await engine.submit(request())
    first_drain = asyncio.create_task(engine.run_until_idle())
    await started.wait()

    with pytest.raises(WorkerBusyError):
        await engine.run_until_idle()
    release.set()
    await first_drain


def test_configuration_requires_exact_handlers_and_positive_limits() -> None:
    registry = make_registry()

    with pytest.raises(WorkerConfigurationError, match="完全一致"):
        WorkflowWorkerEngine(registry, handlers={})
    with pytest.raises(WorkerConfigurationError, match="必须大于零"):
        WorkflowWorkerEngine(registry, handlers={"refresh_catalog": no_op_handler}, worker_count=0)


@pytest.mark.asyncio
async def test_logs_do_not_include_work_reference_or_handler_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "私密正文和原始异常绝不进入工作器日志"

    async def failing_handler(record: TaskRecord) -> None:
        assert record.work_reference == secret
        raise RuntimeError(secret)

    registry = make_registry()
    engine = make_engine(registry, handler=failing_handler)
    caplog.set_level(logging.INFO, logger="workflow_service.worker")
    await engine.submit(request(reference=secret))
    await engine.run_until_idle()

    assert "workflow_task_execution_failed task_type=refresh_catalog worker=0" in caplog.text
    assert secret not in caplog.text
