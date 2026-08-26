from __future__ import annotations

import json
from pathlib import Path

import pytest

from delegation_contract_kit import cli
from delegation_contract_kit.evaluation import (
    DelegationFixtureError,
    run_static_delegation_cases,
    write_public_delegation_report,
)


def _case(case_id: str) -> dict[str, object]:
    return {
        "case_id": case_id,
        "requests": [
            {
                "delegation_id": "research-x",
                "role": "public_researcher",
                "task_summary": "fixture-summary",
                "input_ref": "source-x",
                "allowed_tools": ["read_public_fixture"],
                "max_steps": 2,
                "max_tool_calls": 1,
            }
        ],
        "expected": "accepted",
    }


def test_static_delegation_fixture_replays_public_cases() -> None:
    fixture = Path(__file__).parent / "fixtures" / "delegation_cases.json"

    results = run_static_delegation_cases(fixture)

    assert len(results) == 3
    assert all(result.passed for result in results)


def test_fixture_rejects_duplicate_case_ids_and_extra_request_fields(tmp_path: Path) -> None:
    fixture = tmp_path / "invalid.json"
    duplicate = _case("same-case")
    fixture.write_text(json.dumps([duplicate, duplicate]), encoding="utf-8")
    with pytest.raises(DelegationFixtureError, match="不可重复"):
        run_static_delegation_cases(fixture)

    extra = _case("extra-case")
    requests = extra["requests"]
    assert isinstance(requests, list)
    request = requests[0]
    assert isinstance(request, dict)
    request["unexpected"] = "no"
    fixture.write_text(json.dumps([extra]), encoding="utf-8")
    with pytest.raises(DelegationFixtureError, match="固定字段"):
        run_static_delegation_cases(fixture)


@pytest.mark.parametrize("content", ["{not-json", "{}"])
def test_fixture_rejects_invalid_json_or_non_array(tmp_path: Path, content: str) -> None:
    fixture = tmp_path / "invalid.json"
    fixture.write_text(content, encoding="utf-8")

    with pytest.raises(DelegationFixtureError):
        run_static_delegation_cases(fixture)


def test_fixture_missing_file_is_controlled_error(tmp_path: Path) -> None:
    with pytest.raises(DelegationFixtureError, match="不可读取"):
        run_static_delegation_cases(tmp_path / "missing.json")


def test_public_report_excludes_request_summary_and_input_reference(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "delegation_cases.json"
    report = tmp_path / "report.json"

    write_public_delegation_report(run_static_delegation_cases(fixture), report)

    text = report.read_text(encoding="utf-8")
    assert "compare-source-a" not in text
    assert "source-a" not in text
    assert "two-independent-roles" in text


def test_cli_is_default_no_execution_and_static_modes_are_explicit(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    assert cli.main([]) == 0
    status = json.loads(capsys.readouterr().out)
    assert "parallel_workers" in status["not_supported"]

    assert cli.main(["--run-static-delegation"]) == 0
    assert json.loads(capsys.readouterr().out) == {"case_count": 3, "passed_count": 3}

    monkeypatch.chdir(tmp_path)
    assert cli.main(["--write-static-report"]) == 0
    written = json.loads(capsys.readouterr().out)
    report = tmp_path / str(written["report_written"])
    assert report.name == "delegation-contract-report.json"
    assert "compare-source-a" not in report.read_text(encoding="utf-8")


def test_cli_rejects_conflicting_modes() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--run-static-delegation", "--write-static-report"])
    assert exc_info.value.code == 2
