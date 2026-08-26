from __future__ import annotations

import json
from pathlib import Path

import pytest

from framework_adoption_kit import cli
from framework_adoption_kit.evaluation import (
    MigrationFixtureError,
    run_static_migration_cases,
    write_public_migration_report,
)


def _case(case_id: str) -> dict[str, object]:
    return {
        "case_id": case_id,
        "candidate": {
            "tool_name": "notify_preview",
            "arguments": {"recipient_id": "fixture-user", "template_id": "fixture-template"},
        },
        "resume_decision": "approved",
        "resume_tenant_id": "tenant-1",
        "expected": "accepted",
    }


def test_static_migration_fixture_replays_public_cases() -> None:
    fixture = Path(__file__).parent / "fixtures" / "migration_cases.json"

    results = run_static_migration_cases(fixture)

    assert len(results) == 3
    assert all(result.passed for result in results)


def test_fixture_rejects_duplicate_case_ids_and_extra_fields(tmp_path: Path) -> None:
    duplicate = _case("same-case")
    fixture = tmp_path / "invalid.json"
    fixture.write_text(json.dumps([duplicate, duplicate]), encoding="utf-8")

    with pytest.raises(MigrationFixtureError, match="不可重复"):
        run_static_migration_cases(fixture)

    extra = _case("extra-case")
    extra["unexpected"] = "no"
    fixture.write_text(json.dumps([extra]), encoding="utf-8")
    with pytest.raises(MigrationFixtureError, match="字段闭集"):
        run_static_migration_cases(fixture)


def test_public_migration_report_excludes_fixture_arguments(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "migration_cases.json"
    report = tmp_path / "report.json"

    write_public_migration_report(run_static_migration_cases(fixture), report)

    text = report.read_text(encoding="utf-8")
    assert "fixture-user" not in text
    assert "fixture-template" not in text
    assert "approved-exact-binding" in text


def test_cli_is_default_no_execution_and_static_modes_are_explicit(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    assert cli.main([]) == 0
    status = json.loads(capsys.readouterr().out)
    assert "tool_execution" in status["not_supported"]

    assert cli.main(["--run-static-migration"]) == 0
    assert json.loads(capsys.readouterr().out) == {"case_count": 3, "passed_count": 3}

    monkeypatch.chdir(tmp_path)
    assert cli.main(["--write-static-report"]) == 0
    written = json.loads(capsys.readouterr().out)
    report = tmp_path / str(written["report_written"])
    assert report.name == "framework-adoption-migration-report.json"
    assert "fixture-user" not in report.read_text(encoding="utf-8")


def test_cli_rejects_conflicting_modes() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--run-static-migration", "--write-static-report"])
    assert exc_info.value.code == 2


@pytest.mark.parametrize(
    "content",
    ["{not-json", "{}"],
)
def test_fixture_rejects_invalid_json_or_non_array(tmp_path: Path, content: str) -> None:
    fixture = tmp_path / "invalid.json"
    fixture.write_text(content, encoding="utf-8")

    with pytest.raises(MigrationFixtureError):
        run_static_migration_cases(fixture)


def test_fixture_missing_file_is_controlled_error(tmp_path: Path) -> None:
    with pytest.raises(MigrationFixtureError, match="不可读取"):
        run_static_migration_cases(tmp_path / "missing.json")
