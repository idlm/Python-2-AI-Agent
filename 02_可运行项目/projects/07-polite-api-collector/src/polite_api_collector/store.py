"""采集记录的受控 JSONL 存储与恢复（版本 0.1.0）。

记录文件是固定名称的 JSONL；每一行是一个经过验证的对象。写入时先在同一目录
写临时文件并 fsync，再以 os.replace() 切换。该策略降低半写入主文件风险，但不
承诺跨设备原子性、多进程写入协调、磁盘耗尽恢复或完整灾难恢复。
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, TypeAlias

from .crawler import CollectedPage

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
_SCHEMA_VERSION: Final = 1
_RECORD_FIELDS: Final[frozenset[str]] = frozenset(
    {"id", "source", "name", "endpoint", "collected_at", "payload"}
)
_MANIFEST_FIELDS: Final[frozenset[str]] = frozenset(
    {"schema_version", "record_count", "record_ids", "updated_at"}
)
JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


class StorageError(Exception):
    """采集记录存储的公开受控失败基类。"""


class RecordSchemaError(StorageError):
    """记录不是本项目允许的严格 JSONL Schema。"""


class StorageLimitError(StorageError):
    """文件、行、记录或 JSON 嵌套超过当前教学项目的边界。"""


class StoragePathError(StorageError):
    """输出根目录不可用，或固定输出路径不能安全创建。"""


@dataclass(frozen=True)
class StoredRecord:
    """被持久化的一条固定采集结果记录。"""

    record_id: str
    source: str
    name: str
    endpoint: str
    collected_at: str
    payload: dict[str, JsonValue]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "id": self.record_id,
            "source": self.source,
            "name": self.name,
            "endpoint": self.endpoint,
            "collected_at": self.collected_at,
            "payload": self.payload,
        }


@dataclass(frozen=True)
class WriteResult:
    """一次受控批量写入的公开计数，不含正文。"""

    added: int
    skipped_duplicates: int
    total_records: int


class CollectionStore:
    """只在一个明确根目录下维护 records.jsonl 和 manifest.json。"""

    def __init__(
        self,
        output_root: Path,
        *,
        max_file_bytes: int = 5_000_000,
        max_line_bytes: int = 250_000,
        max_records: int = 10_000,
    ) -> None:
        if max_file_bytes < 1 or max_line_bytes < 1 or max_records < 1:
            raise ValueError("存储大小和记录上限必须大于零。")
        if max_line_bytes > max_file_bytes:
            raise ValueError("单行上限不能超过文件上限。")
        try:
            output_root.mkdir(parents=True, exist_ok=True)
            root = output_root.resolve(strict=True)
        except OSError as exc:
            raise StoragePathError("无法创建或解析输出根目录。") from exc
        if not root.is_dir():
            raise StoragePathError("输出根目录必须是目录。")
        self._root = root
        self._records_path = self._safe_child("records.jsonl")
        self._manifest_path = self._safe_child("manifest.json")
        self._max_file_bytes = max_file_bytes
        self._max_line_bytes = max_line_bytes
        self._max_records = max_records

    @property
    def records_path(self) -> Path:
        """返回固定的 JSONL 记录路径。"""
        return self._records_path

    @property
    def manifest_path(self) -> Path:
        """返回固定的 JSON 快照清单路径。"""
        return self._manifest_path

    def append_pages(
        self,
        pages: Sequence[CollectedPage],
        *,
        source: str,
        collected_at: str | None = None,
    ) -> WriteResult:
        """去重后原子替换 JSONL 快照，再写入可由 records 重建的清单。"""
        if not source.strip():
            raise ValueError("来源名称不能为空。")
        timestamp = collected_at or datetime.now(UTC).isoformat()
        if not timestamp.strip():
            raise ValueError("采集时间不能为空。")
        existing = self.load_records()
        record_ids = {record.record_id for record in existing}
        combined = list(existing)
        added = 0
        skipped = 0
        for page in pages:
            record = self._record_from_page(page, source=source, collected_at=timestamp)
            if record.record_id in record_ids:
                skipped += 1
                continue
            combined.append(record)
            record_ids.add(record.record_id)
            added += 1
        if len(combined) > self._max_records:
            raise StorageLimitError("记录总数超过当前存储上限。")
        self._write_jsonl_snapshot(combined)
        self._write_manifest(combined, updated_at=timestamp)
        LOGGER.info(
            "collection_records_written added=%s skipped=%s total=%s",
            added,
            skipped,
            len(combined),
        )
        return WriteResult(added=added, skipped_duplicates=skipped, total_records=len(combined))

    def load_records(self) -> list[StoredRecord]:
        """读取并严格验证完整 JSONL；空文件代表零条记录。"""
        if not self._records_path.exists():
            return []
        self._enforce_file_limit(self._records_path)
        records: list[StoredRecord] = []
        seen_ids: set[str] = set()
        try:
            with self._records_path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if len(line.encode("utf-8")) > self._max_line_bytes:
                        raise StorageLimitError("记录行超过当前字节上限。")
                    if not line.strip():
                        raise RecordSchemaError(f"第 {line_number} 行不能为空。")
                    record = self._parse_record_line(line, line_number=line_number)
                    if record.record_id in seen_ids:
                        raise RecordSchemaError("记录文件含有重复 ID。")
                    seen_ids.add(record.record_id)
                    records.append(record)
        except UnicodeDecodeError as exc:
            raise RecordSchemaError("记录文件不是 UTF-8 文本。") from exc
        except OSError as exc:
            raise StorageError("无法读取记录文件。") from exc
        if len(records) > self._max_records:
            raise StorageLimitError("记录总数超过当前存储上限。")
        return records

    def recover_manifest(self) -> dict[str, JsonValue]:
        """从已验证记录重建 manifest；用于清单缺失或在两次替换间中断后的恢复。"""
        records = self.load_records()
        updated_at = datetime.now(UTC).isoformat()
        manifest = self._manifest_for(records, updated_at=updated_at)
        self._atomic_write_text(self._manifest_path, self._strict_json(manifest) + "\n")
        LOGGER.info("collection_manifest_recovered record_count=%s", len(records))
        return manifest

    def load_manifest(self) -> dict[str, JsonValue]:
        """读取并严格验证当前清单；缺失时调用方应显式选择恢复。"""
        if not self._manifest_path.exists():
            raise StorageError("清单文件不存在；请显式执行恢复。")
        self._enforce_file_limit(self._manifest_path)
        try:
            content = self._manifest_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise StorageError("无法读取清单文件。") from exc
        try:
            raw: object = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RecordSchemaError("清单不是有效 JSON。") from exc
        if not isinstance(raw, dict) or set(raw) != _MANIFEST_FIELDS:
            raise RecordSchemaError("清单字段不符合固定 Schema。")
        schema_version = raw["schema_version"]
        record_count = raw["record_count"]
        record_ids = raw["record_ids"]
        updated_at = raw["updated_at"]
        if schema_version != _SCHEMA_VERSION or not isinstance(record_count, int):
            raise RecordSchemaError("清单版本或记录数无效。")
        has_string_record_ids = isinstance(record_ids, list) and all(
            isinstance(item, str) for item in record_ids
        )
        if not has_string_record_ids:
            raise RecordSchemaError("清单记录 ID 无效。")
        if not isinstance(updated_at, str) or not updated_at:
            raise RecordSchemaError("清单更新时间无效。")
        if record_count != len(record_ids) or len(set(record_ids)) != len(record_ids):
            raise RecordSchemaError("清单计数与 ID 列表不一致。")
        return {
            "schema_version": schema_version,
            "record_count": record_count,
            "record_ids": list(record_ids),
            "updated_at": updated_at,
        }

    def _record_from_page(
        self, page: CollectedPage, *, source: str, collected_at: str
    ) -> StoredRecord:
        if not page.name.strip() or not page.endpoint.startswith("/"):
            raise RecordSchemaError("采集页面名称或端点不符合记录合同。")
        payload = self._validated_payload(page.payload)
        canonical_payload = self._strict_json(payload)
        digest_input = "\n".join((source, page.name, page.endpoint, canonical_payload))
        record_id = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()
        return StoredRecord(
            record_id=record_id,
            source=source,
            name=page.name,
            endpoint=page.endpoint,
            collected_at=collected_at,
            payload=payload,
        )

    def _parse_record_line(self, line: str, *, line_number: int) -> StoredRecord:
        try:
            raw: object = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RecordSchemaError(f"第 {line_number} 行不是有效 JSON。") from exc
        if not isinstance(raw, dict) or set(raw) != _RECORD_FIELDS:
            raise RecordSchemaError(f"第 {line_number} 行字段不符合固定 Schema。")
        record_id = raw["id"]
        source = raw["source"]
        name = raw["name"]
        endpoint = raw["endpoint"]
        collected_at = raw["collected_at"]
        payload_raw = raw["payload"]
        required_strings = (record_id, source, name, collected_at)
        if not all(isinstance(value, str) and value for value in required_strings):
            raise RecordSchemaError(f"第 {line_number} 行字符串字段无效。")
        if not isinstance(endpoint, str) or not endpoint.startswith("/"):
            raise RecordSchemaError(f"第 {line_number} 行端点无效。")
        if not isinstance(payload_raw, dict):
            raise RecordSchemaError(f"第 {line_number} 行 payload 必须是对象。")
        payload = self._validated_payload(payload_raw)
        return StoredRecord(
            record_id=record_id,
            source=source,
            name=name,
            endpoint=endpoint,
            collected_at=collected_at,
            payload=payload,
        )

    def _validated_payload(self, payload: object) -> dict[str, JsonValue]:
        value = self._validate_json_value(payload, depth=0)
        if not isinstance(value, dict):
            raise RecordSchemaError("payload 必须是 JSON 对象。")
        return value

    def _validate_json_value(self, value: object, *, depth: int) -> JsonValue:
        if depth > 20:
            raise StorageLimitError("JSON 嵌套超过当前深度上限。")
        if value is None or isinstance(value, (str, bool, int)):
            return value
        if isinstance(value, float):
            if not math.isfinite(value):
                raise RecordSchemaError("JSON 不允许 NaN 或无穷数值。")
            return value
        if isinstance(value, list):
            return [self._validate_json_value(item, depth=depth + 1) for item in value]
        if isinstance(value, dict):
            checked: dict[str, JsonValue] = {}
            for key, item in value.items():
                if not isinstance(key, str):
                    raise RecordSchemaError("JSON 对象键必须是字符串。")
                checked[key] = self._validate_json_value(item, depth=depth + 1)
            return checked
        raise RecordSchemaError("payload 含有不可 JSON 序列化的类型。")

    def _write_jsonl_snapshot(self, records: Sequence[StoredRecord]) -> None:
        lines = [self._strict_json(record.as_dict()) for record in records]
        text = "\n".join(lines)
        if text:
            text += "\n"
        if len(text.encode("utf-8")) > self._max_file_bytes:
            raise StorageLimitError("写入后的记录文件超过当前字节上限。")
        self._atomic_write_text(self._records_path, text)

    def _write_manifest(self, records: Sequence[StoredRecord], *, updated_at: str) -> None:
        manifest = self._manifest_for(records, updated_at=updated_at)
        self._atomic_write_text(self._manifest_path, self._strict_json(manifest) + "\n")

    def _manifest_for(
        self, records: Sequence[StoredRecord], *, updated_at: str
    ) -> dict[str, JsonValue]:
        record_ids: list[JsonValue] = []
        record_ids.extend(sorted(record.record_id for record in records))
        return {
            "schema_version": _SCHEMA_VERSION,
            "record_count": len(records),
            "record_ids": record_ids,
            "updated_at": updated_at,
        }

    def _atomic_write_text(self, destination: Path, text: str) -> None:
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self._root, prefix=f".{destination.name}.", delete=False
            ) as handle:
                temporary_name = handle.name
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, destination)
        except OSError as exc:
            raise StorageError("无法原子更新采集记录或清单。") from exc
        finally:
            if temporary_name is not None:
                temporary_path = Path(temporary_name)
                if temporary_path.exists():
                    try:
                        temporary_path.unlink()
                    except OSError:
                        LOGGER.warning("collection_temporary_cleanup_failed")

    def _safe_child(self, filename: str) -> Path:
        candidate = (self._root / filename).resolve(strict=False)
        if candidate.parent != self._root:
            raise StoragePathError("固定输出文件不在输出根目录内。")
        return candidate

    def _enforce_file_limit(self, path: Path) -> None:
        try:
            if path.stat().st_size > self._max_file_bytes:
                raise StorageLimitError("存储文件超过当前字节上限。")
        except OSError as exc:
            raise StorageError("无法读取存储文件大小。") from exc

    @staticmethod
    def _strict_json(value: object) -> str:
        try:
            return json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise RecordSchemaError("记录包含不可写入的 JSON 内容。") from exc
