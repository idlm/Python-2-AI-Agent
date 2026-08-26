"""CLI 工具平台基础测试。"""

from cli_tool_platform.cli import environment_summary, main


def test_environment_summary_has_nonempty_expected_fields() -> None:
    summary = environment_summary()
    assert set(summary) == {"executable", "python_version", "cwd"}
    assert all(isinstance(value, str) and value for value in summary.values())


def test_main_prints_environment_summary(capsys) -> None:
    exit_code = main([])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "executable=" in captured.out
    assert "python_version=" in captured.out
    assert "cwd=" in captured.out
