"""知识笔记 FastAPI 应用（版本 0.2.0）。"""

from __future__ import annotations

import logging
import os
from collections.abc import Awaitable, Callable, Generator
from contextvars import ContextVar
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .core import Note, NoteNotFoundError, NoteRepository, SqliteNoteRepository, StorageError

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="unknown")
_DEFAULT_DATABASE_PATH = Path("data") / "knowledge-api.sqlite3"


class ErrorDetail(BaseModel):
    """客户端可见的稳定错误细节。"""

    code: str
    message: str


class ErrorEnvelope(BaseModel):
    """所有预期错误的公开载荷。"""

    error: ErrorDetail
    request_id: str


class HealthResponse(BaseModel):
    """不泄露内部依赖版本的健康检查响应。"""

    status: str
    request_id: str


class NoteCreate(BaseModel):
    """创建笔记时允许的输入字段。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=2_000)


class NoteResponse(BaseModel):
    """公开笔记响应；不自动暴露领域对象之外的字段。"""

    id: int
    title: str
    content: str
    request_id: str


class NoteListResponse(BaseModel):
    """笔记集合响应。"""

    notes: list[NoteResponse]
    request_id: str


def _request_id() -> str:
    return REQUEST_ID.get()


def _database_path() -> Path:
    """仅允许以一个显式路径配置数据库；不接受模块、SQL 或任意 callable 配置。"""
    configured_path = os.environ.get("COURSE_KNOWLEDGE_API_DB")
    if not configured_path:
        return _DEFAULT_DATABASE_PATH
    return Path(configured_path).expanduser()


def _error_response(*, status_code: int, code: str, message: str) -> JSONResponse:
    body = ErrorEnvelope(
        error=ErrorDetail(code=code, message=message),
        request_id=_request_id(),
    ).model_dump()
    return JSONResponse(status_code=status_code, content=body)


def _note_response(note: Note) -> NoteResponse:
    return NoteResponse(
        id=note.id,
        title=note.title,
        content=note.content,
        request_id=_request_id(),
    )


def get_store() -> Generator[NoteRepository, None, None]:
    """为每个请求提供一个指向同一受控路径的 SQLite 仓储。"""
    yield SqliteNoteRepository(_database_path())


StoreDependency = Annotated[NoteRepository, Depends(get_store)]
app = FastAPI(title="Course Knowledge API", version="0.2.0")


@app.middleware("http")
async def request_context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """为每个请求添加相关 ID；只记录方法、路径和状态，不记录请求正文。"""
    request_id = request.headers.get("X-Request-ID") or uuid4().hex
    token = REQUEST_ID.set(request_id)
    try:
        response = await call_next(request)
    except Exception:
        LOGGER.exception(
            "api_request_failed method=%s path=%s request_id=%s",
            request.method,
            request.url.path,
            request_id,
        )
        raise
    finally:
        REQUEST_ID.reset(token)
    response.headers["X-Request-ID"] = request_id
    LOGGER.info(
        "api_request_completed method=%s path=%s status=%s request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        request_id,
    )
    return response


@app.exception_handler(NoteNotFoundError)
async def note_not_found_handler(_: Request, exc: NoteNotFoundError) -> JSONResponse:
    """将领域层资源缺失映射为公开 404 合同。"""
    return _error_response(
        status_code=status.HTTP_404_NOT_FOUND,
        code="note_not_found",
        message=f"找不到编号为 {exc.note_id} 的笔记。",
    )


@app.exception_handler(StorageError)
async def storage_error_handler(_: Request, __: StorageError) -> JSONResponse:
    """将数据库锁、损坏或磁盘故障隐藏在稳定服务不可用合同后。"""
    return _error_response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code="storage_unavailable",
        message="笔记存储暂时不可用，请稍后重试。",
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, __: RequestValidationError) -> JSONResponse:
    """拒绝不合法请求，但不把原始请求体和内部定位信息返回客户端。"""
    return _error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="invalid_request",
        message="请求格式或字段值不符合笔记 API 合同。",
    )


@app.get("/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    """返回最小进程健康信号；存储读写验收由独立端点测试承担。"""
    return HealthResponse(status="ok", request_id=_request_id())


@app.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteCreate, store: StoreDependency) -> NoteResponse:
    """创建一条经过模型验证并在 SQLite 事务中提交的笔记。"""
    note = store.create(title=payload.title, content=payload.content)
    return _note_response(note)


@app.get("/notes", response_model=NoteListResponse)
def list_notes(store: StoreDependency) -> NoteListResponse:
    """读取稳定排序的持久化笔记快照。"""
    notes = [_note_response(note) for note in store.list_all()]
    return NoteListResponse(notes=notes, request_id=_request_id())


@app.get("/notes/{note_id}", response_model=NoteResponse)
def read_note(note_id: int, store: StoreDependency) -> NoteResponse:
    """读取一个编号有效的笔记；领域缺失由异常处理器转为 404。"""
    return _note_response(store.get(note_id))
