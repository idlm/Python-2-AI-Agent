"""受控 JSONL 采集记录存储测试。"""

import json
import logging
import math
from pathlib import Path

import pytest

from polite_api_collector.crawler import CollectedPage
from polite_api_collector.store import (
    CollectionStore,
    RecordSchemaError,
    StorageError,
    StorageLimitError,
    StoragePathError,
)

FIXED_TIME = "2026-08-26T00:00:00+00:00"


def page(name: str, endpoint: str, payload: dict[str, object]) -> CollectedPage:
    return CollectedPage(name=name, endpoint=endpoint, payload=payload)


def test_append_creates_jsonl_manifest_and_cross_instance_read(tmp_path: Path) -> None:
    store = CollectionStore(tmp_path)
    result = store.append_pages(
        [page("first", "/records/1", {"title": "第一条"})],
        source="catalog",
        collected_at=FIXED_TIME,
    )

    assert result.added == 1
    assert result.skipped_duplicates == 0
    assert result.total_records == 1
    raw_lines = store.records_path.read_text(encoding="utf-8").splitlines()
    assert len(raw_lines) == 1
    raw = json.loads(raw_lines[0])
    assert set(raw) == {"id", "source", "name", "endpoint", "collected_at", "payload"}
    assert raw["payload"] == {"title": "第一条"}

    loaded = CollectionStore(tmp_path).load_records()
    manifest = CollectionStore(tmp_path).load_manifest()
    assert loaded[0].source == "catalog"
    assert loaded[0].payload == {"title": "第一条"}
    assert manifest["record_count"] == 1


def test_duplicate_page_is_not_written_twice(tmp_path: Path) -> None:
    store = CollectionStore(tmp_path)
    pages = [page("first", "/records/1", {"title": "same"})]

    first = store.append_pages(pages, source="catalog", collected_at=FIXED_TIME)
    second = store.append_pages(pages, source="catalog", collected_at=FIXED_TIME)

    assert first.added == 1
    assert second.added == 0
    assert second.skipped_duplicates == 1
    assert second.total_records == 1
    assert len(store.load_records()) == 1


def test_atomic_snapshot_leaves_no_temporary_files_after_success(tmp_path: Path) -> None:
    store = CollectionStore(tmp_path)
    store.append_pages(
        [page("one", "/one", {"ok": True})], source="catalog", collected_at=FIXED_TIME
    )

    temporary_files = [path for path in tmp_path.iterdir() if path.name.startswith(".")]
    assert temporary_files == []
    assert store.records_path.exists()
    assert store.manifest_path.exists()


def test_recover_manifest_from_valid_records_after_manifest_loss(tmp_path: Path) -> None:
    store = CollectionStore(tmp_path)
    store.append_pages(
        [page("one", "/one", {"ok": True})], source="catalog", collected_at=FIXED_TIME
    )
    store.manifest_path.unlink()

    with pytest.raises(StorageError, match="不存在"):
        store.load_manifest()

    recovered = store.recover_manifest()

    assert recovered["record_count"] == 1
    assert store.load_manifest()["record_ids"] == recovered["record_ids"]


def test_rejects_schema_damage_duplicate_ids_and_invalid_json(tmp_path: Path) -> None:
    store = CollectionStore(tmp_path)
    record = {
        "id": "same",
        "source": "catalog",
        "name": "one",
        "endpoint": "/one",
        "collected_at": FIXED_TIME,
        "payload": {"ok": True},
    }
    duplicated_lines = "\n".join((json.dumps(record, ensure_ascii=False),) * 2) + "\n"
    store.records_path.write_text(duplicated_lines, encoding="utf-8")

    with pytest.raises(RecordSchemaError, match="重复 ID"):
        store.load_records()

    store.records_path.write_text("{bad json}\n", encoding="utf-8")
    with pytest.raises(RecordSchemaError, match="有效 JSON"):
        store.load_records()


def test_rejects_non_finite_payload_and_non_object_payload(tmp_path: Path) -> None:
    store = CollectionStore(tmp_path)

    with pytest.raises(RecordSchemaError, match="NaN"):
        store.append_pages(
            [page("nan", "/nan", {"value": math.nan})], source="catalog", collected_at=FIXED_TIME
        )
    with pytest.raises(RecordSchemaError, match="payload"):
        store.append_pages(
            [page("list", "/list", ["not", "object"])], source="catalog", collected_at=FIXED_TIME
        )


def test_enforces_file_line_and_record_limits(tmp_path: Path) -> None:
    store = CollectionStore(tmp_path, max_file_bytes=100, max_line_bytes=50, max_records=1)

    with pytest.raises(StorageLimitError, match="写入后的记录"):
        store.append_pages(
            [page("large", "/large", {"text": "x" * 80})], source="catalog", collected_at=FIXED_TIME
        )

    oversized_line = (
        '{"id":"x","source":"s","name":"n",'
        '"endpoint":"/x","collected_at":"t","payload":{}}\n'
    )
    store.records_path.write_text(oversized_line, encoding="utf-8")
    with pytest.raises(StorageLimitError, match="行超过"):
        store.load_records()

    roomy_store = CollectionStore(tmp_path / "roomy", max_records=1)
    with pytest.raises(StorageLimitError, match="记录总数"):
        roomy_store.append_pages(
            [page("one", "/one", {}), page("two", "/two", {})],
            source="catalog",
            collected_at=FIXED_TIME,
        )


def test_log_does_not_include_payload_content(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    secret = "采集正文绝不写入存储运行日志"
    store = CollectionStore(tmp_path)

    caplog.set_level(logging.INFO, logger="polite_api_collector.store")
    result = store.append_pages(
        [page("one", "/one", {"body": secret})], source="catalog", collected_at=FIXED_TIME
    )

    assert result.added == 1
    assert "collection_records_written added=1 skipped=0 total=1" in caplog.text
    assert secret not in caplog.text


def test_store_rejects_file_as_output_root(tmp_path: Path) -> None:
    file_root = tmp_path / "not-a-directory"
    file_root.write_text("x", encoding="utf-8")

    with pytest.raises(StoragePathError):
        CollectionStore(file_root)
