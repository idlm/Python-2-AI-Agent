"""命令行任务管理器核心（版本 0.1.0，Python 3.11+）。

持久化边界刻意很窄：调用者显式给出一个 JSON 文件路径；文件只接受固定的
版本化结构；每次改变先备份旧文件，再原子替换新文件。
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TypedDict, cast

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
_FILE_VERSION = 1
_MAX_FILE_BYTES = 1_048_576
_MAX_TASKS = 5_000
_MAX_TITLE_LENGTH = 200


class TaskManagerError(Exception):
    """所有可预期任务管理器错误的基类。"""


class TaskValidationError(TaskManagerError):
    """任务字段、命令参数或 JSON 模式不符合契约。"""


class TaskStorageError(TaskManagerError):
    """任务文件无法被安全读取、写入或替换。"""


class TaskNotFoundError(TaskManagerError):
    """请求的任务编号不存在。"""


class TaskRecord(TypedDict):
    """写入 JSON 的固定任务记录。"""

    id: int
    title: str
    priority: int
    done: bool


@dataclass(frozen=True)
class Task:
    """一条不可变任务记录。"""

    id: int
    title: str
    priority: int
    done: bool = False

    def to_record(self) -> TaskRecord:
        """返回由 JSON 模式约束的普通字典。"""
        return cast(TaskRecord, asdict(self))


def _require_task_id(value: object, *, field: str = "id") -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise TaskValidationError(f"{field} 必须是大于 0 的整数。")
    return value


def _require_title(value: object, *, field: str = "title") -> str:
    if not isinstance(value, str):
        raise TaskValidationError(f"{field} 必须是字符串。")
    title = value.strip()
    if not title:
        raise TaskValidationError(f"{field} 不能为空或只包含空白字符。")
    if len(title) > _MAX_TITLE_LENGTH:
        raise TaskValidationError(f"{field} 最长为 {_MAX_TITLE_LENGTH} 个字符。")
    return title


def _require_priority(value: object, *, field: str = "priority") -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
        raise TaskValidationError(f"{field} 必须是 1–5 的整数。")
    return value


def _require_done(value: object, *, field: str = "done") -> bool:
    if not isinstance(value, bool):
        raise TaskValidationError(f"{field} 必须是布尔值。")
    return value


def _task_from_mapping(value: object, *, position: int) -> Task:
    if not isinstance(value, Mapping):
        raise TaskValidationError(f"tasks[{position}] 必须是对象。")
    expected_fields = {"id", "title", "priority", "done"}
    unknown_fields = set(value) - expected_fields
    missing_fields = expected_fields - set(value)
    if unknown_fields or missing_fields:
        raise TaskValidationError(
            f"tasks[{position}] 字段必须恰为 {sorted(expected_fields)}；"
            f"缺失={sorted(missing_fields)}，额外={sorted(unknown_fields)}。"
        )
    return Task(
        id=_require_task_id(value.get("id"), field=f"tasks[{position}].id"),
        title=_require_title(value.get("title"), field=f"tasks[{position}].title"),
        priority=_require_priority(value.get("priority"), field=f"tasks[{position}].priority"),
        done=_require_done(value.get("done"), field=f"tasks[{position}].done"),
    )


class TaskStore:
    """一个显式 JSON 文件的版本化任务存储。"""

    def __init__(self, path: Path) -> None:
        if path.suffix.lower() != ".json":
            raise TaskValidationError("任务文件必须使用 .json 扩展名。")
        self._path = path

    @property
    def path(self) -> Path:
        """返回经校验的任务文件路径。"""
        return self._path

    @property
    def backup_path(self) -> Path:
        """返回上一次成功写入前的备份文件路径。"""
        return self._path.with_suffix(self._path.suffix + ".bak")

    def list_tasks(self) -> list[Task]:
        """读取并验证所有任务；不存在的文件被视为空列表。"""
        if not self._path.exists():
            return []
        try:
            size = self._path.stat().st_size
        except OSError as exc:
            raise TaskStorageError(f"无法读取任务文件元数据：{self._path}") from exc
        if size > _MAX_FILE_BYTES:
            raise TaskStorageError(f"任务文件超过 {_MAX_FILE_BYTES} 字节上限。")
        try:
            with self._path.open("r", encoding="utf-8") as task_file:
                raw: object = json.load(task_file)
        except OSError as exc:
            raise TaskStorageError(f"无法读取任务文件：{self._path}") from exc
        except json.JSONDecodeError as exc:
            message = f"任务文件不是有效 JSON：第 {exc.lineno} 行第 {exc.colno} 列。"
            raise TaskValidationError(message) from exc
        return self._validate_document(raw)

    def add(self, title: object, priority: object = 3) -> Task:
        """创建并保存新任务，自动分配稳定的正整数编号。"""
        tasks = self.list_tasks()
        if len(tasks) >= _MAX_TASKS:
            raise TaskValidationError(f"任务数量不得超过 {_MAX_TASKS} 条。")
        next_id = max((task.id for task in tasks), default=0) + 1
        task = Task(id=next_id, title=_require_title(title), priority=_require_priority(priority))
        self._save([*tasks, task])
        LOGGER.info("task_added id=%s priority=%s", task.id, task.priority)
        return task

    def get(self, task_id: object) -> Task:
        """按编号返回任务，找不到时拒绝而不是猜测。"""
        normalized_id = _require_task_id(task_id)
        for task in self.list_tasks():
            if task.id == normalized_id:
                return task
        raise TaskNotFoundError(f"找不到编号为 {normalized_id} 的任务。")

    def update(self, task_id: object, *, title: object | None, priority: object | None) -> Task:
        """修改任务标题和/或优先级；至少必须提供一个变更。"""
        if title is None and priority is None:
            raise TaskValidationError("更新任务时必须提供 --title 或 --priority。")
        normalized_id = _require_task_id(task_id)
        normalized_title = _require_title(title) if title is not None else None
        normalized_priority = _require_priority(priority) if priority is not None else None
        tasks = self.list_tasks()
        for index, task in enumerate(tasks):
            if task.id == normalized_id:
                updated = Task(
                    id=task.id,
                    title=normalized_title if normalized_title is not None else task.title,
                    priority=(
                        normalized_priority if normalized_priority is not None else task.priority
                    ),
                    done=task.done,
                )
                tasks[index] = updated
                self._save(tasks)
                LOGGER.info("task_updated id=%s", updated.id)
                return updated
        raise TaskNotFoundError(f"找不到编号为 {normalized_id} 的任务。")

    def complete(self, task_id: object) -> Task:
        """把指定任务设为完成；重复完成仍是幂等的显式保存。"""
        task = self.get(task_id)
        if task.done:
            return task
        return self._set_done(task.id, True)

    def remove(self, task_id: object) -> Task:
        """显式删除一条任务，并在替换前备份原 JSON 文件。"""
        normalized_id = _require_task_id(task_id)
        tasks = self.list_tasks()
        for index, task in enumerate(tasks):
            if task.id == normalized_id:
                del tasks[index]
                self._save(tasks)
                LOGGER.info("task_removed id=%s", task.id)
                return task
        raise TaskNotFoundError(f"找不到编号为 {normalized_id} 的任务。")

    def _set_done(self, task_id: int, done: bool) -> Task:
        tasks = self.list_tasks()
        for index, task in enumerate(tasks):
            if task.id == task_id:
                completed = Task(task.id, task.title, task.priority, done)
                tasks[index] = completed
                self._save(tasks)
                LOGGER.info("task_completed id=%s", completed.id)
                return completed
        raise TaskNotFoundError(f"找不到编号为 {task_id} 的任务。")

    def _validate_document(self, raw: object) -> list[Task]:
        if not isinstance(raw, Mapping):
            raise TaskValidationError("任务文件根节点必须是对象。")
        expected_fields = {"version", "tasks"}
        unknown_fields = set(raw) - expected_fields
        missing_fields = expected_fields - set(raw)
        if unknown_fields or missing_fields:
            raise TaskValidationError(
                f"任务文件字段必须恰为 {sorted(expected_fields)}；"
                f"缺失={sorted(missing_fields)}，额外={sorted(unknown_fields)}。"
            )
        version = raw.get("version")
        if isinstance(version, bool) or not isinstance(version, int) or version != _FILE_VERSION:
            raise TaskValidationError(f"任务文件 version 必须为 {_FILE_VERSION}。")
        items = raw.get("tasks")
        if not isinstance(items, Sequence) or isinstance(items, (str, bytes, bytearray)):
            raise TaskValidationError("任务文件 tasks 必须是数组。")
        if len(items) > _MAX_TASKS:
            raise TaskValidationError(f"任务数量不得超过 {_MAX_TASKS} 条。")
        tasks = [_task_from_mapping(item, position=index) for index, item in enumerate(items)]
        ids = [task.id for task in tasks]
        if len(ids) != len(set(ids)):
            raise TaskValidationError("任务文件中的 id 不能重复。")
        return sorted(tasks, key=lambda task: task.id)

    def _save(self, tasks: Sequence[Task]) -> None:
        document: dict[str, object] = {
            "version": _FILE_VERSION,
            "tasks": [task.to_record() for task in tasks],
        }
        serialized = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            if self._path.exists():
                shutil.copy2(self._path, self.backup_path)
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self._path.parent, delete=False
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(serialized)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            temporary_path.replace(self._path)
        except OSError as exc:
            raise TaskStorageError(f"无法安全写入任务文件：{self._path}") from exc
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink(missing_ok=True)
