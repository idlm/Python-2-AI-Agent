"""任务管理器核心测试。"""

import json
from pathlib import Path

import pytest

from task_manager import TaskNotFoundError, TaskStore, TaskValidationError


def test_add_assigns_ids_and_persists_versioned_document(tmp_path: Path) -> None:
    store = TaskStore(tmp_path / "tasks.json")

    first = store.add("完成变量练习", 1)
    second = store.add("阅读测试章节", 4)

    assert (first.id, second.id) == (1, 2)
    assert [task.title for task in store.list_tasks()] == ["完成变量练习", "阅读测试章节"]
    document = json.loads(store.path.read_text(encoding="utf-8"))
    assert document["version"] == 1
    assert document["tasks"][0]["done"] is False


def test_second_write_creates_backup_before_atomic_replacement(tmp_path: Path) -> None:
    store = TaskStore(tmp_path / "tasks.json")
    store.add("旧内容")

    updated = store.update(1, title="新内容", priority=None)

    assert updated.title == "新内容"
    backup = json.loads(store.backup_path.read_text(encoding="utf-8"))
    assert backup["tasks"][0]["title"] == "旧内容"
    assert store.get(1).title == "新内容"


def test_update_complete_and_remove_are_explicit_crud_operations(tmp_path: Path) -> None:
    store = TaskStore(tmp_path / "tasks.json")
    created = store.add("先写测试", 2)

    changed = store.update(created.id, title=None, priority=5)
    completed = store.complete(created.id)
    removed = store.remove(created.id)

    assert changed.priority == 5
    assert completed.done is True
    assert removed.id == created.id
    assert store.list_tasks() == []


def test_complete_is_idempotent(tmp_path: Path) -> None:
    store = TaskStore(tmp_path / "tasks.json")
    task = store.add("不重复改变", 3)

    assert store.complete(task.id).done is True
    assert store.complete(task.id).done is True


@pytest.mark.parametrize(
    ("title", "priority", "message"),
    [
        ("   ", 3, "不能为空"),
        ("x" * 201, 3, "最长"),
        ("正常", 6, "1–5"),
        ("正常", True, "1–5"),
    ],
)
def test_add_rejects_invalid_task_fields(
    tmp_path: Path, title: object, priority: object, message: str
) -> None:
    store = TaskStore(tmp_path / "tasks.json")

    with pytest.raises(TaskValidationError, match=message):
        store.add(title, priority)


def test_update_requires_an_actual_field_change(tmp_path: Path) -> None:
    store = TaskStore(tmp_path / "tasks.json")
    task = store.add("保持边界")

    with pytest.raises(TaskValidationError, match="必须提供"):
        store.update(task.id, title=None, priority=None)


def test_missing_task_is_rejected(tmp_path: Path) -> None:
    store = TaskStore(tmp_path / "tasks.json")

    with pytest.raises(TaskNotFoundError, match="找不到"):
        store.remove(1)


def test_document_with_unknown_field_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "tasks.json"
    path.write_text('{"version": 1, "tasks": [], "command": "rm -rf /"}', encoding="utf-8")

    with pytest.raises(TaskValidationError, match="额外"):
        TaskStore(path).list_tasks()


def test_document_with_duplicate_ids_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "tasks.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "tasks": [
                    {"id": 1, "title": "甲", "priority": 1, "done": False},
                    {"id": 1, "title": "乙", "priority": 2, "done": False},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(TaskValidationError, match="不能重复"):
        TaskStore(path).list_tasks()


def test_non_json_path_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(TaskValidationError, match=".json"):
        TaskStore(tmp_path / "tasks.txt")
