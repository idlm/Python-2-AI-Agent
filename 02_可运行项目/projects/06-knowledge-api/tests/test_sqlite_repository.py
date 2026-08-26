"""SQLite 知识笔记仓储测试。"""

from pathlib import Path

import pytest

from knowledge_api.core import NoteNotFoundError, SqliteNoteRepository, StorageError


def repository_at(tmp_path: Path) -> SqliteNoteRepository:
    return SqliteNoteRepository(tmp_path / "notes.sqlite3")


def test_create_persists_across_repository_instances(tmp_path: Path) -> None:
    first_repository = repository_at(tmp_path)
    created = first_repository.create(title="事务", content="显式提交才可持久化。")

    second_repository = repository_at(tmp_path)

    assert created.id == 1
    assert second_repository.get(1) == created


def test_list_all_orders_by_database_primary_key(tmp_path: Path) -> None:
    repository = repository_at(tmp_path)
    repository.create(title="第一条", content="一")
    repository.create(title="第二条", content="二")

    assert [note.id for note in repository.list_all()] == [1, 2]


def test_missing_note_raises_domain_error(tmp_path: Path) -> None:
    repository = repository_at(tmp_path)

    with pytest.raises(NoteNotFoundError) as error:
        repository.get(99)

    assert error.value.note_id == 99


def test_user_text_is_bound_as_data_not_executed_sql(tmp_path: Path) -> None:
    repository = repository_at(tmp_path)
    suspicious_title = "标题'); DROP TABLE notes; --"

    created = repository.create(title=suspicious_title, content="它只能作为文本保存。")

    assert repository.get(created.id).title == suspicious_title
    assert len(repository.list_all()) == 1


def test_constraint_failure_rolls_back_write(tmp_path: Path) -> None:
    repository = repository_at(tmp_path)

    with pytest.raises(StorageError):
        repository.create(title=" ", content="违反数据库约束。")

    assert repository.list_all() == []


def test_backup_can_be_read_as_an_independent_database(tmp_path: Path) -> None:
    repository = repository_at(tmp_path)
    created = repository.create(title="备份", content="恢复需要可验证副本。")
    backup_path = repository.backup_to(tmp_path / "backups" / "notes-backup.sqlite3")

    restored_repository = SqliteNoteRepository(backup_path)

    assert backup_path.exists()
    assert restored_repository.get(created.id) == created


def test_backup_refuses_to_overwrite_source_database(tmp_path: Path) -> None:
    repository = repository_at(tmp_path)

    with pytest.raises(ValueError, match="备份目标"):
        repository.backup_to(repository.database_path)


def test_timeout_must_be_positive(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="锁等待时间"):
        SqliteNoteRepository(tmp_path / "notes.sqlite3", timeout_seconds=0)
