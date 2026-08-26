"""知识笔记 API 的 HTTP 合同测试。"""

import logging
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from knowledge_api.api import app, get_store
from knowledge_api.core import NoteStore


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """每个测试使用独立内存存储，不依赖模块级共享数据。"""
    store = NoteStore()

    def override_store() -> Generator[NoteStore, None, None]:
        yield store

    app.dependency_overrides[get_store] = override_store
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_returns_public_status_and_request_id(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "health-123"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "request_id": "health-123"}
    assert response.headers["X-Request-ID"] == "health-123"


def test_create_list_and_read_note(client: TestClient) -> None:
    created = client.post("/notes", json={"title": "HTTP", "content": "先写合同。"})
    listed = client.get("/notes")
    read = client.get("/notes/1")

    assert created.status_code == 201
    assert created.json()["id"] == 1
    assert created.json()["request_id"]
    assert listed.status_code == 200
    assert [note["title"] for note in listed.json()["notes"]] == ["HTTP"]
    assert read.status_code == 200
    assert read.json()["content"] == "先写合同。"


def test_not_found_is_stable_public_error(client: TestClient) -> None:
    response = client.get("/notes/999", headers={"X-Request-ID": "missing-456"})

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "note_not_found", "message": "找不到编号为 999 的笔记。"},
        "request_id": "missing-456",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "  ", "content": "正文"},
        {"title": "标题", "content": "  "},
        {"title": "标题", "content": "正文", "command": "rm -rf /"},
        {"title": "标题"},
    ],
)
def test_invalid_body_uses_unified_422_without_echoing_input(
    client: TestClient, payload: dict[str, str]
) -> None:
    response = client.post("/notes", json=payload, headers={"X-Request-ID": "invalid-789"})

    assert response.status_code == 422
    assert response.json() == {
        "error": {"code": "invalid_request", "message": "请求格式或字段值不符合笔记 API 合同。"},
        "request_id": "invalid-789",
    }
    assert "command" not in response.text


def test_path_type_validation_uses_unified_422(client: TestClient) -> None:
    response = client.get("/notes/not-a-number")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_request_log_never_contains_note_content(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    secret = "不应出现在服务日志的用户正文"
    caplog.set_level(logging.INFO, logger="knowledge_api.api")

    response = client.post("/notes", json={"title": "标题", "content": secret})

    assert response.status_code == 201
    assert "api_request_completed" in caplog.text
    assert secret not in caplog.text
