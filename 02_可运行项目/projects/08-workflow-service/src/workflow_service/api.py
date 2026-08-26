"""受控服务工作流的 FastAPI 边缘层（版本 0.1.0）。"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Annotated, cast
from uuid import uuid4

from fastapi import FastAPI, Header, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .core import (
    IdempotencyConflictError,
    InvalidTransitionError,
    PublicTask,
    TaskRecord,
    TaskRequest,
    TaskRequestError,
    UnknownTaskError,
    WorkflowError,
    WorkflowRegistry,
)
from .worker import QueueCapacityError, WorkflowWorkerEngine

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="unknown")


class ErrorDetail(BaseModel):
    """客户端可见的稳定错误细节。"""

    code: str
    message: str


class ErrorEnvelope(BaseModel):
    """所有预期 API 失败的公开载荷。"""

    error: ErrorDetail
    request_id: str


class HealthResponse(BaseModel):
    """不泄露队列实现、环境变量或依赖版本的健康响应。"""

    status: str
    request_id: str


class TaskCreate(BaseModel):
    """任务接受端点允许的固定字段。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    task_type: str = Field(min_length=1, max_length=80)
    work_reference: str = Field(min_length=1, max_length=160)


class TaskResponse(BaseModel):
    """公开任务视图；不回显工作引用或幂等键。"""

    task_id: str
    task_type: str
    state: str
    attempts: int
    recoveries: int
    error_code: str | None
    created_at: str
    updated_at: str
    request_id: str


class TaskListResponse(BaseModel):
    """受控的小规模任务列表响应。"""

    tasks: list[TaskResponse]
    request_id: str


@dataclass(frozen=True)
class WorkflowRuntime:
    """由 lifespan 创建并在服务关闭时清理的进程内教学原型。"""

    registry: WorkflowRegistry
    engine: WorkflowWorkerEngine


async def _teaching_handler(record: TaskRecord) -> None:
    """无外部副作用的短任务处理器，只用于证明 API 的接受/状态边界。"""
    _ = record.task_type
    await asyncio.sleep(0)


def _request_id() -> str:
    return REQUEST_ID.get()


def _task_response(task: PublicTask) -> TaskResponse:
    return TaskResponse(
        task_id=task.task_id,
        task_type=task.task_type,
        state=task.state.value,
        attempts=task.attempts,
        recoveries=task.recoveries,
        error_code=task.error_code,
        created_at=task.created_at,
        updated_at=task.updated_at,
        request_id=_request_id(),
    )


def _error_response(*, status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorEnvelope(
            error=ErrorDetail(code=code, message=message),
            request_id=_request_id(),
        ).model_dump(),
    )


def _default_runtime() -> WorkflowRuntime:
    registry = WorkflowRegistry(allowed_task_types={"refresh_catalog"}, max_tasks=100)
    engine = WorkflowWorkerEngine(
        registry,
        handlers={"refresh_catalog": _teaching_handler},
        queue_maxsize=10,
        worker_count=1,
        task_timeout_seconds=1.0,
    )
    return WorkflowRuntime(registry=registry, engine=engine)


def create_app(*, runtime: WorkflowRuntime | None = None) -> FastAPI:
    """创建可注入 runtime 的应用，便于测试生命周期与不持久化边界。"""
    selected_runtime = runtime or _default_runtime()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        LOGGER.info("workflow_service_started")
        try:
            yield
        finally:
            recovered = selected_runtime.registry.mark_interrupted_for_recovery()
            LOGGER.info("workflow_service_stopped recovery_candidates=%s", len(recovered))

    app = FastAPI(title="Course Workflow Service", version="0.1.0", lifespan=lifespan)
    app.state.workflow_runtime = selected_runtime

    @app.middleware("http")
    async def request_context(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """关联公开响应与脱敏元数据日志，绝不读取请求正文用于日志。"""
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        token = REQUEST_ID.set(request_id)
        try:
            response = await call_next(request)
        except Exception:
            LOGGER.exception(
                "workflow_api_request_failed method=%s path=%s request_id=%s",
                request.method,
                request.url.path,
                request_id,
            )
            raise
        finally:
            REQUEST_ID.reset(token)
        response.headers["X-Request-ID"] = request_id
        LOGGER.info(
            "workflow_api_request_completed method=%s path=%s status=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            request_id,
        )
        return response

    @app.exception_handler(UnknownTaskError)
    async def unknown_task_handler(_: Request, __: UnknownTaskError) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="task_not_found",
            message="找不到该任务。",
        )

    @app.exception_handler(IdempotencyConflictError)
    async def idempotency_conflict_handler(
        _: Request, __: IdempotencyConflictError
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_409_CONFLICT,
            code="idempotency_conflict",
            message="该幂等键已用于不同的任务请求。",
        )

    @app.exception_handler(InvalidTransitionError)
    async def transition_handler(_: Request, __: InvalidTransitionError) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_409_CONFLICT,
            code="task_state_conflict",
            message="任务当前状态不允许该操作。",
        )

    @app.exception_handler(TaskRequestError)
    async def task_request_handler(_: Request, __: TaskRequestError) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="task_request_rejected",
            message="任务类型、工作引用或幂等键不符合服务合同。",
        )

    @app.exception_handler(QueueCapacityError)
    async def queue_capacity_handler(_: Request, __: QueueCapacityError) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="queue_busy",
            message="服务当前无法接受新任务，请稍后重试。",
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, __: RequestValidationError) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="invalid_request",
            message="请求格式或字段值不符合工作流 API 合同。",
        )

    @app.exception_handler(WorkflowError)
    async def workflow_error_handler(_: Request, __: WorkflowError) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="workflow_unavailable",
            message="工作流暂时不可用，请稍后重试。",
        )

    def get_runtime(request: Request) -> WorkflowRuntime:
        return cast(WorkflowRuntime, request.app.state.workflow_runtime)

    @app.get("/health", response_model=HealthResponse)
    def read_health() -> HealthResponse:
        return HealthResponse(status="ok", request_id=_request_id())

    @app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
    async def accept_task(
        payload: TaskCreate,
        response: Response,
        idempotency_key: Annotated[
            str,
            Header(alias="Idempotency-Key", min_length=1, max_length=160),
        ],
        request: Request,
    ) -> TaskResponse:
        """接受任务并返回 pending 事实；不会在此响应中宣称已由 worker 完成。"""
        runtime = get_runtime(request)
        task = await runtime.engine.submit(
            TaskRequest(
                task_type=payload.task_type,
                work_reference=payload.work_reference,
                idempotency_key=idempotency_key,
            )
        )
        response.headers["Location"] = f"/tasks/{task.task_id}"
        return _task_response(task)

    @app.get("/tasks", response_model=TaskListResponse)
    def list_tasks(request: Request) -> TaskListResponse:
        runtime = get_runtime(request)
        return TaskListResponse(
            tasks=[_task_response(task) for task in runtime.registry.list_tasks()],
            request_id=_request_id(),
        )

    @app.get("/tasks/{task_id}", response_model=TaskResponse)
    def read_task(task_id: str, request: Request) -> TaskResponse:
        return _task_response(get_runtime(request).registry.get(task_id))

    @app.post("/tasks/{task_id}/cancel", response_model=TaskResponse)
    def cancel_task(task_id: str, request: Request) -> TaskResponse:
        task = get_runtime(request).engine.cancel(task_id)
        return _task_response(task)

    return app


app = create_app()
