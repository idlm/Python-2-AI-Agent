"""任务管理器 CLI 端到端测试。"""

import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI = PROJECT_ROOT / ".venv" / "bin" / "course-tasks"


def run_cli(data_path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(CLI), "--data", str(data_path), *arguments],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_add_list_done_and_show_json(tmp_path: Path) -> None:
    data_path = tmp_path / "tasks.json"

    added = run_cli(data_path, "--json", "add", "实现第一个工具", "--priority", "2")
    listed = run_cli(data_path, "--json", "list")
    finished = run_cli(data_path, "--json", "done", "1")
    pending = run_cli(data_path, "--json", "list")
    shown = run_cli(data_path, "--json", "show", "1")

    assert added.returncode == 0, added.stderr
    assert json.loads(added.stdout)["title"] == "实现第一个工具"
    assert json.loads(listed.stdout)["tasks"][0]["done"] is False
    assert json.loads(finished.stdout)["done"] is True
    assert json.loads(pending.stdout) == {"tasks": []}
    assert json.loads(shown.stdout)["priority"] == 2


def test_cli_remove_requires_explicit_confirmation(tmp_path: Path) -> None:
    data_path = tmp_path / "tasks.json"
    run_cli(data_path, "add", "先创建")

    refused = run_cli(data_path, "remove", "1")
    removed = run_cli(data_path, "--json", "remove", "1", "--yes")

    assert refused.returncode == 2
    assert "--yes" in refused.stderr
    assert removed.returncode == 0, removed.stderr
    assert json.loads(removed.stdout)["id"] == 1


def test_cli_rejects_missing_task_with_exit_two(tmp_path: Path) -> None:
    result = run_cli(tmp_path / "tasks.json", "show", "99")

    assert result.returncode == 2
    assert "找不到" in result.stderr


def test_verbose_log_has_metadata_not_task_title(tmp_path: Path) -> None:
    data_path = tmp_path / "tasks.json"
    secret_title = "不应出现在日志的任务正文"

    result = run_cli(data_path, "--verbose", "add", secret_title)

    assert result.returncode == 0, result.stderr
    assert "task_added id=1 priority=3" in result.stderr
    assert secret_title not in result.stderr
