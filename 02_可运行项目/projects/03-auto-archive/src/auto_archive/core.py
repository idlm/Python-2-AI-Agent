"""默认 Dry Run 的可审计本地归档核心（版本 0.2.0，Python 3.11+）。

此模块只移动调用者明确提供的本地文件；不递归扫描、不删除文件、不覆盖归档目标。
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TypedDict, cast

LOGGER = logging.getLogger(__name__)
_MAX_CONFIG_BYTES = 64 * 1024


class ArchiveInputError(ValueError):
    """归档配置或路径不符合工具的安全契约。"""


class ManifestItem(TypedDict):
    """经验证的操作清单条目。"""

    source: str
    destination: str
    moved: bool


@dataclass(frozen=True)
class ArchiveAction:
    """一次计划或实际归档动作的不可变记录。"""

    source: Path
    destination: Path
    moved: bool


def load_config(config_path: Path) -> dict[str, str]:
    """读取受限 JSON 配置；当前仅允许文件后缀字段。"""
    try:
        size = config_path.stat().st_size
    except FileNotFoundError as exc:
        raise ArchiveInputError(f"找不到配置文件：{config_path}") from exc
    except OSError as exc:
        raise ArchiveInputError(f"无法访问配置文件：{config_path}") from exc
    if size > _MAX_CONFIG_BYTES:
        raise ArchiveInputError(f"配置文件超过 {_MAX_CONFIG_BYTES} 字节上限。")
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        message = f"配置不是有效 JSON：第 {exc.lineno} 行第 {exc.colno} 列。"
        raise ArchiveInputError(message) from exc
    except UnicodeDecodeError as exc:
        raise ArchiveInputError("配置文件不是有效 UTF-8 文本。") from exc
    except OSError as exc:
        raise ArchiveInputError(f"无法读取配置文件：{config_path}") from exc
    if not isinstance(payload, dict):
        raise ArchiveInputError("配置根节点必须是对象。")
    unknown_keys = set(payload) - {"suffix"}
    if unknown_keys:
        raise ArchiveInputError(f"配置包含不允许字段：{sorted(unknown_keys)}")
    suffix = payload.get("suffix", ".txt")
    if not isinstance(suffix, str) or not suffix.startswith(".") or suffix == ".":
        raise ArchiveInputError("配置 suffix 必须是以点开头的非空字符串。")
    return {"suffix": suffix}


def plan_archive(source_dir: Path, archive_dir: Path, suffix: str = ".txt") -> list[ArchiveAction]:
    """计划当前目录的匹配文件归档，不执行任何移动。"""
    _validate_suffix(suffix)
    source_root = _require_existing_directory(source_dir, label="源目录")
    archive_root = archive_dir.resolve()
    if archive_root == source_root:
        raise ArchiveInputError("源目录与归档目录不能相同。")

    actions: list[ArchiveAction] = []
    for path in sorted(source_root.iterdir(), key=lambda item: item.name):
        if path.is_file() and path.suffix == suffix:
            actions.append(
                ArchiveAction(source=path, destination=archive_root / path.name, moved=False)
            )
    LOGGER.info("archive_plan_created candidates=%s suffix=%s", len(actions), suffix)
    return actions


def write_manifest(actions: list[ArchiveAction], manifest_path: Path) -> None:
    """以 UTF-8 JSON 写入操作清单，不包含文件正文。"""
    payload = [
        {
            **asdict(action),
            "source": str(action.source),
            "destination": str(action.destination),
        }
        for action in actions
    ]
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    LOGGER.info("archive_manifest_written actions=%s", len(actions))


def rollback_from_manifest(manifest_path: Path, dry_run: bool = True) -> list[ArchiveAction]:
    """根据已完成清单回滚；默认只计划，不移动文件。"""
    payload = _load_manifest(manifest_path)
    completed: list[ArchiveAction] = []
    for item in payload:
        source = Path(item["source"])
        destination = Path(item["destination"])
        if not item.get("moved", False):
            continue
        if not destination.exists() or source.exists():
            raise FileNotFoundError("回滚前置条件不满足")
        if not dry_run:
            source.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(destination), str(source))
        completed.append(ArchiveAction(source=destination, destination=source, moved=not dry_run))
    LOGGER.info("archive_rollback_planned actions=%s dry_run=%s", len(completed), dry_run)
    return completed


def execute_archive(actions: list[ArchiveAction], dry_run: bool = True) -> list[ArchiveAction]:
    """执行或模拟已计划动作；真实执行时绝不覆盖既有目标。"""
    completed: list[ArchiveAction] = []
    for action in actions:
        LOGGER.info(
            "archive_candidate source=%s destination=%s dry_run=%s",
            action.source,
            action.destination,
            dry_run,
        )
        if dry_run:
            completed.append(action)
            continue
        if not action.source.is_file():
            raise FileNotFoundError(f"源文件不可用：{action.source}")
        if action.destination.exists():
            raise FileExistsError(f"归档目标已存在：{action.destination}")
        action.destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(action.source), str(action.destination))
        completed.append(ArchiveAction(action.source, action.destination, moved=True))
    return completed


def _load_manifest(manifest_path: Path) -> list[ManifestItem]:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ArchiveInputError(f"找不到操作清单：{manifest_path}") from exc
    except json.JSONDecodeError as exc:
        message = f"操作清单不是有效 JSON：第 {exc.lineno} 行第 {exc.colno} 列。"
        raise ArchiveInputError(message) from exc
    if not isinstance(payload, list):
        raise ArchiveInputError("操作清单根节点必须是数组。")

    validated: list[ManifestItem] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ArchiveInputError("操作清单项目必须是对象。")
        source = item.get("source")
        destination = item.get("destination")
        moved = item.get("moved")
        valid_item = (
            isinstance(source, str)
            and isinstance(destination, str)
            and isinstance(moved, bool)
        )
        if not valid_item:
            raise ArchiveInputError("操作清单项目必须含字符串 source、destination 和布尔 moved。")
        validated.append(
            {
                "source": cast(str, source),
                "destination": cast(str, destination),
                "moved": cast(bool, moved),
            }
        )
    return validated


def _require_existing_directory(path: Path, *, label: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ArchiveInputError(f"找不到{label}：{path}") from exc
    if not resolved.is_dir():
        raise ArchiveInputError(f"{label}不是目录：{path}")
    return resolved


def _validate_suffix(suffix: object) -> None:
    if not isinstance(suffix, str) or not suffix.startswith(".") or suffix == ".":
        raise ArchiveInputError("suffix 必须是以点开头的非空字符串。")
