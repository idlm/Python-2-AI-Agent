"""受控 RAG CLI 的无网络合同测试。"""

from __future__ import annotations

import json
import sys

import pytest

from rag_contract_workbench import cli


def run_cli(
    monkeypatch: pytest.MonkeyPatch,
    *arguments: str,
) -> tuple[int, str, str]:
    monkeypatch.setattr(sys, "argv", ["course-rag-contract", *arguments])
    with pytest.raises(SystemExit) as exit_info:
        cli.main()
    captured = pytest.CaptureFixture[str]  # type: ignore[misc]
    del captured
    return int(exit_info.value.code), "", ""


def test_status_does_not_build_index_or_require_query(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["course-rag-contract", "--status"])

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert exit_info.value.code == 0
    assert payload["embedding_mode"] == "deterministic_hashing_test_double"
    assert payload["source_bound_answer_contract"] is True
    assert "external_embedding_calls" in payload["not_supported"]
    assert "real_model_answer_generation" in payload["not_supported"]


def test_query_only_searches_builtin_public_documents(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["course-rag-contract", "--query", "函数 返回值"])

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert exit_info.value.code == 0
    assert payload["collection"] == "course-public"
    assert payload["results"][0]["document_id"] == "functions"
    assert "函数" in payload["results"][0]["text"]
    assert "query" not in payload


def test_invalid_top_k_is_a_controlled_public_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["course-rag-contract", "--query", "函数", "--top-k", "6"])

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert exit_info.value.code == 2
    assert payload["error"]["code"] == "invalid_query"
    assert "函数" not in payload["error"]["message"]


def test_status_cannot_be_combined_with_query(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["course-rag-contract", "--status", "--query", "函数"])

    with pytest.raises(SystemExit, match="不能与 --query") as exit_info:
        cli.main()

    assert exit_info.value.code == "错误：--status 不能与 --query 一起使用。"
