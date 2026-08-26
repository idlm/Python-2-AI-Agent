from __future__ import annotations

import json
from pathlib import Path

import pytest

from operational_readiness_kit import cli
from operational_readiness_kit.evaluation import (
    ReadinessFixtureError,
    run_static_readiness_cases,
    write_public_readiness_report,
)


def _case(case_id: str) -> dict[str, object]:
    return {
        "case_id": case_id,
        "environment": "staging",
        "app_version": "v1",
        "required_secret_states": ["active"],
        "drain_supported": True,
        "drill_state": "verified",
        "compatible_versions": ["v1"],
        "runbook_complete": True,
        "expected": "approved",
    }


def test_static_readiness_fixture_replays_public_cases() -> None:
    fixture = Path(__file__).parent / "fixtures" / "readiness_cases.json"

    results = run_static_readiness_cases(fixture)

    assert len(results) == 4
    assert all(result.passed for result in results)


def test_fixture_rejects_duplicate_ids_and_extra_fields(tmp_path: Path) -> None:
    fixture = tmp_path / "invalid.json"
    duplicate = _case("same-case")
    fixture.write_text(json.dumps([duplicate, duplicate]), encoding="utf-8")
    with pytest.raises(ReadinessFixtureError, match="不可重复"):
        run_static_readiness_cases(fixture)

    extra = _case("extra-case")
    extra["unexpected"] = "no"
    fixture.write_text(json.dumps([extra]), encoding="utf-8")
    with pytest.raises(ReadinessFixtureError, match="固定字段"):
        run_static_readiness_cases(fixture)


@pytest.mark.parametrize("content", ["{not-json", "{}"])
def test_fixture_rejects_invalid_json_or_non_array(tmp_path: Path, content: str) -> None:
    fixture = tmp_path / "invalid.json"
    fixture.write_text(content, encoding="utf-8")

    with pytest.raises(ReadinessFixtureError):
        run_static_readiness_cases(fixture)


def test_fixture_missing_file_is_controlled_error(tmp_path: Path) -> None:
    with pytest.raises(ReadinessFixtureError, match="不可读取"):
        run_static_readiness_cases(tmp_path / "missing.json")


def test_public_report_excludes_case_configuration_and_secret_categories(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "readiness_cases.json"
    report = tmp_path / "report.json"

    write_public_readiness_report(run_static_readiness_cases(fixture), report)

    text = report.read_text(encoding="utf-8")
    assert "all-controls-complete" in text
    assert "required_secret_states" not in text
    assert "drill_state" not in text
    assert "compatible_versions" not in text
    assert "runbook_complete" not in text


def test_cli_is_default_no_execution_and_static_modes_are_explicit(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    assert cli.main([]) == 0
    status = json.loads(capsys.readouterr().out)
    assert "cloud_deployment" in status["not_supported"]

    assert cli.main(["--run-static-readiness"]) == 0
    assert json.loads(capsys.readouterr().out) == {"case_count": 4, "passed_count": 4}

    monkeypatch.chdir(tmp_path)
    assert cli.main(["--write-static-report"]) == 0
    written = json.loads(capsys.readouterr().out)
    report = tmp_path / str(written["report_written"])
    assert report.name == "operational-readiness-report.json"
    assert "required_secret_states" not in report.read_text(encoding="utf-8")


def test_cli_rejects_conflicting_modes() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--run-static-readiness", "--write-static-report"])
    assert exc_info.value.code == 2
