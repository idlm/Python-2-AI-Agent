"""FastAPI 工作流服务边缘合同测试。"""

import logging

import pytest
from fastapi.testclient import TestClient

from workflow_service.api import WorkflowRuntime, create_app
from workflow_service.core import TaskRecord, TaskRequest, TaskState, WorkflowRegistry
from workflow_service.worker import WorkflowWorkerEngine


async def no_op_handler(record: TaskRecord) -> None:
    assert record.task_type == "refresh_catalog"


def runtime(*, queue_maxsize: int = 10) -> WorkflowRuntime:
    registry = WorkflowRegistry(allowed_task_types={"refresh_catalog"})
    engine = WorkflowWorkerEngine(
        registry,
        handlers={"refresh_catalog": no_op_handler},
        queue_maxsize=queue_maxsize,
    )
    return WorkflowRuntime(registry=registry, engine=engine)


def test_health_accept_read_and_request_id_without_work_reference() -> None:
    service_runtime = runtime()
    app = create_app(runtime=service_runtime)

    with TestClient(app) as client:
        health = client.get("/health", headers={"X-Request-ID": "health-001"})
        accepted = client.post(
            "/tasks",
            headers={"Idempotency-Key": "accept-001", "X-Request-ID": "task-001"},
            json={"task_type": "refresh_catalog", "work_reference": "private-catalog-reference"},
        )
        task_id = accepted.json()["task_id"]
        read = client.get(f"/tasks/{task_id}", headers={"X-Request-ID": "read-001"})

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "request_id": "health-001"}
    assert health.headers["X-Request-ID"] == "health-001"
    assert accepted.status_code == 202
    assert accepted.headers["Location"] == f"/tasks/{task_id}"
    assert accepted.json()["state"] == "pending"
    assert accepted.json()["request_id"] == "task-001"
    assert "work_reference" not in accepted.json()
    assert "private-catalog-reference" not in accepted.text
    assert read.status_code == 200
    assert read.json()["task_id"] == task_id
    assert read.json()["request_id"] == "read-001"


def test_same_idempotency_key_returns_same_task_but_changed_work_conflicts() -> None:
    app = create_app(runtime=runtime())

    with TestClient(app) as client:
        headers = {"Idempotency-Key": "same-key"}
        first = client.post(
            "/tasks",
            headers=headers,
            json={"task_type": "refresh_catalog", "work_reference": "catalog-001"},
        )
        repeated = client.post(
            "/tasks",
            headers=headers,
            json={"task_type": "refresh_catalog", "work_reference": "catalog-001"},
        )
        conflict = client.post(
            "/tasks",
            headers=headers,
            json={"task_type": "refresh_catalog", "work_reference": "catalog-002"},
        )

    assert first.status_code == 202
    assert repeated.status_code == 202
    assert repeated.json()["task_id"] == first.json()["task_id"]
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"
    assert "catalog-002" not in conflict.text


def test_rejects_unknown_type_unknown_fields_missing_header_and_unknown_task() -> None:
    app = create_app(runtime=runtime())

    with TestClient(app) as client:
        unknown_type = client.post(
            "/tasks",
            headers={"Idempotency-Key": "unknown-type"},
            json={"task_type": "arbitrary_callable", "work_reference": "catalog-001"},
        )
        unknown_field = client.post(
            "/tasks",
            headers={"Idempotency-Key": "bad-field"},
            json={"task_type": "refresh_catalog", "work_reference": "catalog-001", "module": "bad"},
        )
        missing_header = client.post(
            "/tasks",
            json={"task_type": "refresh_catalog", "work_reference": "catalog-001"},
        )
        missing_task = client.get("/tasks/task-missing")

    assert unknown_type.status_code == 400
    assert unknown_type.json()["error"]["code"] == "task_request_rejected"
    assert unknown_field.status_code == 422
    assert unknown_field.json()["error"]["code"] == "invalid_request"
    assert "module" not in unknown_field.text
    assert missing_header.status_code == 422
    assert missing_task.status_code == 404
    assert missing_task.json()["error"]["code"] == "task_not_found"


def test_queue_capacity_and_cancel_have_stable_public_contract() -> None:
    service_runtime = runtime(queue_maxsize=1)
    app = create_app(runtime=service_runtime)

    with TestClient(app) as client:
        first = client.post(
            "/tasks",
            headers={"Idempotency-Key": "first"},
            json={"task_type": "refresh_catalog", "work_reference": "catalog-001"},
        )
        busy = client.post(
            "/tasks",
            headers={"Idempotency-Key": "second"},
            json={"task_type": "refresh_catalog", "work_reference": "catalog-002"},
        )
        cancelled = client.post(f"/tasks/{first.json()['task_id']}/cancel")
        repeated_cancel = client.post(f"/tasks/{first.json()['task_id']}/cancel")

    assert busy.status_code == 503
    assert busy.json()["error"]["code"] == "queue_busy"
    assert cancelled.status_code == 200
    assert cancelled.json()["state"] == "cancelled"
    assert repeated_cancel.status_code == 409
    assert repeated_cancel.json()["error"]["code"] == "task_state_conflict"


def test_lifespan_marks_running_task_as_recovery_candidate_on_shutdown() -> None:
    service_runtime = runtime()
    accepted = service_runtime.registry.accept(
        TaskRequest(
            task_type="refresh_catalog",
            work_reference="catalog-001",
            idempotency_key="interrupted-task",
        )
    )
    service_runtime.registry.start(accepted.task_id)
    app = create_app(runtime=service_runtime)

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200

    restored = service_runtime.registry.get(accepted.task_id)
    assert restored.state is TaskState.PENDING
    assert restored.recoveries == 1
    assert restored.error_code == "interrupted"


def test_api_logs_do_not_include_request_body_or_idempotency_key(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_reference = "工作正文不应进入 API 日志"
    secret_key = "private-idempotency-key"
    app = create_app(runtime=runtime())

    with TestClient(app) as client, caplog.at_level(logging.INFO, logger="workflow_service.api"):
        response = client.post(
            "/tasks",
            headers={"Idempotency-Key": secret_key},
            json={"task_type": "refresh_catalog", "work_reference": secret_reference},
        )

    assert response.status_code == 202
    assert "workflow_api_request_completed method=POST path=/tasks status=202" in caplog.text
    assert secret_reference not in caplog.text
    assert secret_key not in caplog.text
