"""有界进程内队列与受控 worker（版本 0.1.0）。

该模块用于一次进程生命周期内的教学批处理。它不持久化队列、不跨进程共享任务，
也不承诺崩溃后的投递；调用方必须把这些限制写入公开服务合同。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from contextlib import suppress

from .core import (
    InvalidTransitionError,
    PublicTask,
    TaskRecord,
    TaskRequest,
    TaskState,
    WorkflowRegistry,
)

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
TaskHandler = Callable[[TaskRecord], Awaitable[None]]


class QueueCapacityError(Exception):
    """有界进程内队列已满，任务尚未被注册或入队。"""


class WorkerConfigurationError(Exception):
    """处理器、并发数、队列上限或超时不符合受控合同。"""


class WorkerBusyError(Exception):
    """同一 engine 已有一次 drain 正在运行。"""


class WorkflowWorkerEngine:
    """把已受审查任务交给有限并发 worker 的单进程协调器。"""

    def __init__(
        self,
        registry: WorkflowRegistry,
        *,
        handlers: Mapping[str, TaskHandler],
        queue_maxsize: int = 10,
        worker_count: int = 1,
        task_timeout_seconds: float = 5.0,
    ) -> None:
        if queue_maxsize < 1 or worker_count < 1 or task_timeout_seconds <= 0:
            raise WorkerConfigurationError("队列上限、worker 数和任务超时必须大于零。")
        handler_types = frozenset(handlers)
        if handler_types != registry.allowed_task_types:
            raise WorkerConfigurationError("处理器类型必须与工作流允许列表完全一致。")
        self._registry = registry
        self._handlers = dict(handlers)
        self._queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=queue_maxsize)
        self._worker_count = worker_count
        self._task_timeout_seconds = task_timeout_seconds
        self._submitted_task_ids: set[str] = set()
        self._running_handlers: dict[str, asyncio.Task[None]] = {}
        self._is_draining = False

    @property
    def queued_count(self) -> int:
        """返回当前尚未被 worker 取走的内存队列项数。"""
        return self._queue.qsize()

    async def submit(self, request: TaskRequest) -> PublicTask:
        """接受一个新任务或返回既有幂等任务，并仅在容量允许时把 pending 任务入队。"""
        existing = self._registry.lookup_idempotency(request)
        if existing is not None:
            return existing
        if self._queue.full():
            raise QueueCapacityError("当前进程内工作队列已满，请稍后重试。")
        accepted = self._registry.accept(request)
        self._queue.put_nowait(accepted.task_id)
        self._submitted_task_ids.add(accepted.task_id)
        LOGGER.info(
            "workflow_task_enqueued task_type=%s queue_size=%s",
            accepted.task_type,
            self._queue.qsize(),
        )
        return accepted

    def cancel(self, task_id: str) -> PublicTask:
        """记录取消状态，并取消该进程当前持有的对应处理器任务（如存在）。"""
        public = self._registry.cancel(task_id)
        handler_task = self._running_handlers.get(task_id)
        if handler_task is not None:
            handler_task.cancel()
        LOGGER.info("workflow_task_cancel_requested task_type=%s", public.task_type)
        return public

    async def run_until_idle(self) -> None:
        """以 TaskGroup 运行有限 worker，直到当前已入队工作被完成、失败或取消。"""
        if self._is_draining:
            raise WorkerBusyError("当前 engine 已在处理队列。")
        self._is_draining = True
        try:
            async with asyncio.TaskGroup() as group:
                for worker_number in range(self._worker_count):
                    group.create_task(self._worker_loop(worker_number))
                await self._queue.join()
                for _ in range(self._worker_count):
                    self._queue.put_nowait(None)
        finally:
            self._is_draining = False

    async def _worker_loop(self, worker_number: int) -> None:
        while True:
            task_id = await self._queue.get()
            try:
                if task_id is None:
                    return
                await self._process(task_id, worker_number=worker_number)
            finally:
                self._queue.task_done()

    async def _process(self, task_id: str, *, worker_number: int) -> None:
        public = self._registry.get(task_id)
        if public.state is TaskState.CANCELLED:
            LOGGER.info("workflow_cancelled_task_skipped task_type=%s", public.task_type)
            return
        try:
            record = self._registry.begin(task_id)
        except InvalidTransitionError:
            LOGGER.warning("workflow_non_pending_task_skipped task_type=%s", public.task_type)
            return
        handler = self._handlers[record.task_type]
        handler_task: asyncio.Task[None] = asyncio.create_task(
            self._invoke_handler(handler, record),
            name=f"workflow-handler-{record.task_type}",
        )
        self._running_handlers[task_id] = handler_task
        try:
            async with asyncio.timeout(self._task_timeout_seconds):
                await handler_task
        except TimeoutError:
            self._mark_failed_if_active(task_id, error_code="timeout")
            LOGGER.warning(
                "workflow_task_timeout task_type=%s worker=%s",
                record.task_type,
                worker_number,
            )
        except asyncio.CancelledError:
            self._mark_cancelled_if_active(task_id)
            LOGGER.info(
                "workflow_task_handler_cancelled task_type=%s worker=%s",
                record.task_type,
                worker_number,
            )
        except Exception:
            self._mark_failed_if_active(task_id, error_code="execution_failed")
            LOGGER.warning(
                "workflow_task_execution_failed task_type=%s worker=%s",
                record.task_type,
                worker_number,
            )
        else:
            self._registry.succeed(task_id)
            LOGGER.info(
                "workflow_task_execution_succeeded task_type=%s worker=%s",
                record.task_type,
                worker_number,
            )
        finally:
            self._running_handlers.pop(task_id, None)

    @staticmethod
    async def _invoke_handler(handler: TaskHandler, record: TaskRecord) -> None:
        """把允许的 Awaitable 处理器包装为可由 create_task 管理的协程。"""
        await handler(record)

    def _mark_failed_if_active(self, task_id: str, *, error_code: str) -> None:
        with suppress(InvalidTransitionError):
            self._registry.fail(task_id, error_code=error_code)

    def _mark_cancelled_if_active(self, task_id: str) -> None:
        with suppress(InvalidTransitionError):
            self._registry.cancel(task_id)
