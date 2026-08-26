"""自动归档系统 0.2.0 的核心与 CLI 测试。"""

import json
from pathlib import Path

from auto_archive.cli import main
from auto_archive.core import (
    ArchiveInputError,
    execute_archive,
    load_config,
    plan_archive,
    rollback_from_manifest,
    write_manifest,
)


def build_directories(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    destination = tmp_path / "archive"
    source.mkdir()
    return source, destination


def test_plan_and_dry_run_do_not_move_files(tmp_path: Path) -> None:
    source, destination = build_directories(tmp_path)
    file_path = source / "note.txt"
    file_path.write_text("hello", encoding="utf-8")
    (source / "skip.py").write_text("pass", encoding="utf-8")

    actions = plan_archive(source, destination)
    assert len(actions) == 1
    assert actions[0].source == file_path.resolve()
    completed = execute_archive(actions, dry_run=True)
    assert completed[0].moved is False
    assert file_path.exists()
    assert not (destination / "note.txt").exists()


def test_load_config_rejects_invalid_unknown_and_oversized_inputs(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text('{"suffix": ".md"}', encoding="utf-8")
    assert load_config(config_path) == {"suffix": ".md"}

    config_path.write_text('{"suffix": "txt"}', encoding="utf-8")
    try:
        load_config(config_path)
    except ArchiveInputError as exc:
        assert "suffix" in str(exc)
    else:
        raise AssertionError("无效 suffix 必须被拒绝")

    config_path.write_text('{"suffix": ".txt", "module": "os"}', encoding="utf-8")
    try:
        load_config(config_path)
    except ArchiveInputError as exc:
        assert "不允许字段" in str(exc)
    else:
        raise AssertionError("未知配置字段必须被拒绝")

    config_path.write_text("{", encoding="utf-8")
    try:
        load_config(config_path)
    except ArchiveInputError as exc:
        assert "有效 JSON" in str(exc)
    else:
        raise AssertionError("无效 JSON 必须被拒绝")


def test_manifest_records_actions_and_rollback(tmp_path: Path) -> None:
    source, destination = build_directories(tmp_path)
    file_path = source / "note.txt"
    file_path.write_text("hello", encoding="utf-8")
    moved = execute_archive(plan_archive(source, destination), dry_run=False)
    manifest = tmp_path / "audit" / "manifest.json"
    write_manifest(moved, manifest)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload[0]["source"] == str(file_path.resolve())
    assert payload[0]["moved"] is True

    dry_actions = rollback_from_manifest(manifest, dry_run=True)
    assert dry_actions[0].moved is False
    assert (destination / "note.txt").exists()
    restored = rollback_from_manifest(manifest, dry_run=False)
    assert restored[0].moved is True
    assert file_path.exists()


def test_execute_moves_and_rejects_conflicts(tmp_path: Path) -> None:
    source, destination = build_directories(tmp_path)
    file_path = source / "note.txt"
    file_path.write_text("hello", encoding="utf-8")
    completed = execute_archive(plan_archive(source, destination), dry_run=False)
    assert completed[0].moved is True
    assert not file_path.exists()
    assert (destination / "note.txt").exists()

    file_path.write_text("again", encoding="utf-8")
    try:
        execute_archive(plan_archive(source, destination), dry_run=False)
    except FileExistsError as exc:
        assert "归档目标已存在" in str(exc)
    else:
        raise AssertionError("同名目标不得被覆盖")


def test_missing_or_same_source_directory_is_rejected(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    try:
        plan_archive(missing, tmp_path / "archive")
    except ArchiveInputError as exc:
        assert "找不到源目录" in str(exc)
    else:
        raise AssertionError("缺失源目录必须被拒绝")

    source, _ = build_directories(tmp_path)
    try:
        plan_archive(source, source)
    except ArchiveInputError as exc:
        assert "不能相同" in str(exc)
    else:
        raise AssertionError("同一源归档目录必须被拒绝")


def test_cli_defaults_to_dry_run_and_writes_manifest(tmp_path: Path, capsys) -> None:
    source, destination = build_directories(tmp_path)
    file_path = source / "note.txt"
    file_path.write_text("hello", encoding="utf-8")
    manifest = tmp_path / "manifest.json"

    exit_code = main([str(source), str(destination), "--manifest", str(manifest)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == "计划数量：1；实际移动：0\n"
    assert file_path.exists()
    assert manifest.exists()


def test_cli_rejects_unknown_config_field(tmp_path: Path, capsys) -> None:
    source, destination = build_directories(tmp_path)
    config = tmp_path / "config.json"
    config.write_text('{"suffix": ".txt", "module": "os"}', encoding="utf-8")

    exit_code = main([str(source), str(destination), "--config", str(config)])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "归档被拒绝" in captured.err
