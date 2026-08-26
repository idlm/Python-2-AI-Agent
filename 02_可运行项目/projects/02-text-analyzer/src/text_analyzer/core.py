"""文本分析核心（版本 0.2.0，Python 3.11+）。

该模块只处理文本与显式给定的本地文件；不访问网络、不执行输入内容、不持久化用户文本。
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

_MAX_TEXT_BYTES = 1_000_000


class TextReport(TypedDict):
    """文本分析结果的稳定字段契约。"""

    characters: int
    words: int
    lines: int


class TextInputError(ValueError):
    """文本或文件输入不符合应用处理范围。"""


def normalize_text(text: str) -> str:
    """合并连续空白，但不修改原始文本对象。"""
    _require_text(text)
    return " ".join(text.split())


def count_words(text: str) -> int:
    """按规范化后的空白分隔文本计算词数。"""
    normalized = normalize_text(text)
    return 0 if not normalized else len(normalized.split(" "))


def analyze_text(text: str) -> TextReport:
    """返回原始字符数、规范化词数和物理行数。"""
    _require_text(text)
    return {
        "characters": len(text),
        "words": count_words(text),
        "lines": len(text.splitlines()) or 1,
    }


def format_report(text: str) -> str:
    """将分析结果格式化为稳定、面向用户的中文报告。"""
    report = analyze_text(text)
    return f"字符数：{report['characters']}；词数：{report['words']}；行数：{report['lines']}"


def read_text_file(path: Path, *, max_bytes: int = _MAX_TEXT_BYTES) -> str:
    """以 UTF-8 读取受限大小的常规文本文件。"""
    if not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ValueError("max_bytes 必须是正整数。")
    try:
        metadata = path.stat()
    except FileNotFoundError as exc:
        raise TextInputError(f"找不到输入文件：{path}") from exc
    except OSError as exc:
        raise TextInputError(f"无法访问输入文件：{path}") from exc
    if not path.is_file():
        raise TextInputError(f"输入路径不是常规文件：{path}")
    if metadata.st_size > max_bytes:
        raise TextInputError(f"输入文件超过 {max_bytes} 字节上限。")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise TextInputError("输入文件不是有效 UTF-8 文本。") from exc
    except OSError as exc:
        raise TextInputError(f"无法读取输入文件：{path}") from exc


def _require_text(text: object) -> None:
    if not isinstance(text, str):
        raise TypeError("text 必须是字符串")
