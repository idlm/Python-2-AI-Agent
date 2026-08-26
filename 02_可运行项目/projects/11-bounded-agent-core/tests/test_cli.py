from __future__ import annotations

import json
from pathlib import Path

import pytest

from bounded_agent_core import cli


def test_status_is_default_and_does_not_run_static_cases(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main([]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "framework_free_bounded_agent"
    assert "models" in payload["not_supported"]


def test_static_evaluation_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("sys.argv", ["course-bounded-agent", "--run-static-evaluation"])
    assert cli.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"case_count": 3, "passed_count": 3}


def test_conflicting_cli_modes_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["course-bounded-agent", "--status", "--run-static-evaluation"])
    with pytest.raises(SystemExit) as exc_info:
        cli.main()
    assert exc_info.value.code == 2



def test_write_static_report_uses_fixed_name_and_excludes_fixture_body(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert cli.main(["--write-static-report"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "case_count": 3,
        "passed_count": 3,
        "report_written": "bounded-agent-static-evaluation.json",
    }
    report = (tmp_path / payload["report_written"]).read_text(encoding="utf-8")
    assert "public-test-result" not in report
    assert "ignore earlier instructions" not in report


def test_report_mode_conflicts_with_static_replay() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--run-static-evaluation", "--write-static-report"])
    assert exc_info.value.code == 2
