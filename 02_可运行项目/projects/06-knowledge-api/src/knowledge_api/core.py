"""知识笔记 API 的领域与持久化层（版本 0.2.0）。

`NoteStore` 保留给第 6.1 章的内存合同示例；生产化路径使用
`SqliteNoteRepository`。SQLite 连接从不跨请求共享，每次操作都在明确
提交/回滚并关闭连接的边界中完成。
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class NoteNotFoundError(Exception):
    """请求的笔记编号不存在。"""

    def __init__(self, note_id: int) -> None:
        super().__init__(f"找不到编号为 {note_id} 的笔记。")
        self.note_id = note_id


class StorageError(Exception):
    """存储层故障；公开 API 不应把驱动异常、SQL 或文件路径暴露给客户端。"""


@dataclass(frozen=True)
class Note:
    """领域层的不可变笔记记录。"""

    id: int
    title: str
    content: str


class NoteRepository(Protocol):
    """HTTP 层依赖的最小仓储合同。"""

    def create(self, *, title: str, content: str) -> Note:
        """持久化一条笔记并返回它。"""

    def list_all(self) -> list[Note]:
        """返回按编号排序的稳定快照。"""

    def get(self, note_id: int) -> Note:
        """返回笔记；缺失时抛 `NoteNotFoundError`。"""


class NoteStore:
    """教学用进程内存存储；锁保护创建与读取快照的一致性。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._notes: dict[int, Note] = {}
        self._next_id = 1

    def create(self, *, title: str, content: str) -> Note:
        """创建一条笔记，并在同一临界区内分配唯一编号。"""
        with self._lock:
            note = Note(id=self._next_id, title=title, content=content)
            self._notes[note.id] = note
            self._next_id += 1
            return note

    def list_all(self) -> list[Note]:
        """返回按编号排序的稳定快照。"""
        with self._lock:
            return [self._notes[note_id] for note_id in sorted(self._notes)]

    def get(self, note_id: int) -> Note:
        """读取一条笔记；缺失时不返回模糊的 None。"""
        with self._lock:
            note = self._notes.get(note_id)
        if note is None:
            raise NoteNotFoundError(note_id)
        return note


class SqliteNoteRepository:
    """以 SQLite 保存笔记的仓储。

    每个公共操作独立打开和关闭连接。写入显式执行 `BEGIN IMMEDIATE`，成功时
    提交，异常时回滚；所有数据值都通过 `?` 占位符传入，绝不拼接用户 SQL。
    这适合本课程的单节点、小规模教学服务，不是多节点高并发写入方案。
    """

    _SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 100),
        content TEXT NOT NULL CHECK (length(trim(content)) BETWEEN 1 AND 2000)
    )
    """

    def __init__(self, database_path: str | Path, *, timeout_seconds: float = 2.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("SQLite 锁等待时间必须大于零。")
        self.database_path = Path(database_path)
        self.timeout_seconds = timeout_seconds
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self) -> None:
        """以幂等 DDL 创建当前已审查的最小 schema。"""
        connection = self._connect()
        try:
            connection.execute(self._SCHEMA_SQL)
            connection.commit()
        except sqlite3.DatabaseError as exc:
            connection.rollback()
            raise StorageError("无法初始化笔记数据库。") from exc
        finally:
            connection.close()

    def create(self, *, title: str, content: str) -> Note:
        """在显式事务中插入一条笔记，并返回数据库分配的编号。"""
        try:
            with self._write_transaction() as connection:
                cursor = connection.execute(
                    "INSERT INTO notes (title, content) VALUES (?, ?)",
                    (title, content),
                )
                note_id = cursor.lastrowid
                if not isinstance(note_id, int) or note_id < 1:
                    raise StorageError("数据库未返回有效的笔记编号。")
                return Note(id=note_id, title=title, content=content)
        except sqlite3.DatabaseError as exc:
            raise StorageError("无法保存笔记。") from exc

    def list_all(self) -> list[Note]:
        """读取按主键排序的笔记快照。"""
        try:
            with self._read_connection() as connection:
                rows = connection.execute(
                    "SELECT id, title, content FROM notes ORDER BY id ASC"
                ).fetchall()
        except sqlite3.DatabaseError as exc:
            raise StorageError("无法读取笔记列表。") from exc
        return [self._row_to_note(row) for row in rows]

    def get(self, note_id: int) -> Note:
        """按参数化 ID 查询单条笔记。"""
        try:
            with self._read_connection() as connection:
                row = connection.execute(
                    "SELECT id, title, content FROM notes WHERE id = ?", (note_id,)
                ).fetchone()
        except sqlite3.DatabaseError as exc:
            raise StorageError("无法读取笔记。") from exc
        if row is None:
            raise NoteNotFoundError(note_id)
        return self._row_to_note(row)

    def backup_to(self, destination: str | Path) -> Path:
        """创建一个一致的本地 SQLite 备份；调用方负责保留、加密和恢复演练。"""
        destination_path = Path(destination)
        if self.database_path.resolve() == destination_path.resolve():
            raise ValueError("备份目标不能与源数据库相同。")
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        source = self._connect()
        target: sqlite3.Connection | None = None
        try:
            target = sqlite3.connect(destination_path)
            source.backup(target)
            target.commit()
        except sqlite3.DatabaseError as exc:
            raise StorageError("无法创建笔记数据库备份。") from exc
        finally:
            if target is not None:
                target.close()
            source.close()
        return destination_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=self.timeout_seconds)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _read_connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def _write_transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _row_to_note(row: sqlite3.Row) -> Note:
        raw_id = row["id"]
        raw_title = row["title"]
        raw_content = row["content"]
        if (
            not isinstance(raw_id, int)
            or not isinstance(raw_title, str)
            or not isinstance(raw_content, str)
        ):
            raise StorageError("笔记数据库包含不符合当前模式的记录。")
        return Note(id=raw_id, title=raw_title, content=raw_content)
