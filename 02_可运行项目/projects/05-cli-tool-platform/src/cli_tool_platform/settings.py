"""CLI 工具平台运行配置（版本 0.2.0，Python 3.11+）。

配置优先级从低到高为：内置安全默认值、受控 TOML 文件、显式环境变量。
此模块不读取 `.env` 文件，不打印密钥，也不接受不可信配置指定代码路径。
"""

from __future__ import annotations

import logging
import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

_ALLOWED_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
_DEFAULT_APP_NAME = "cli-tool-platform"
_DEFAULT_LOG_LEVEL = "INFO"
_MAX_CONFIG_BYTES = 64 * 1024


class ConfigurationError(ValueError):
    """配置文件、环境变量或字段不符合应用契约。"""


@dataclass(frozen=True)
class Settings:
    """经验证的运行设置；不包含任何秘密值。"""

    app_name: str
    log_level: str


def _validate_app_name(value: object) -> str:
    if not isinstance(value, str):
        raise ConfigurationError("app_name 必须是字符串。")
    normalized = value.strip()
    if not normalized or len(normalized) > 64:
        raise ConfigurationError("app_name 必须是 1–64 个非空白字符。")
    return normalized


def normalize_log_level(value: object) -> str:
    """将日志级别规范化为允许的标准名称。"""
    if not isinstance(value, str):
        raise ConfigurationError("log_level 必须是字符串。")
    normalized = value.upper().strip()
    if normalized not in _ALLOWED_LOG_LEVELS:
        allowed = ", ".join(sorted(_ALLOWED_LOG_LEVELS))
        raise ConfigurationError(f"不支持的 log_level：{value!r}；允许值为 {allowed}。")
    return normalized


def load_toml_settings(path: Path) -> dict[str, str]:
    """读取小型可信 TOML 文件，并只接受应用允许的两个字段。"""
    try:
        file_size = path.stat().st_size
    except FileNotFoundError as exc:
        raise ConfigurationError(f"找不到配置文件：{path}") from exc
    if file_size > _MAX_CONFIG_BYTES:
        raise ConfigurationError(f"配置文件超过 {_MAX_CONFIG_BYTES} 字节上限。")
    try:
        with path.open("rb") as config_file:
            data = tomllib.load(config_file)
    except tomllib.TOMLDecodeError as exc:
        # `lineno` 与 `colno` 是较新 Python 版本提供的属性；教学项目仍兼容 3.11/3.12。
        line = getattr(exc, "lineno", "未知")
        column = getattr(exc, "colno", "未知")
        raise ConfigurationError(f"配置不是有效 TOML：第 {line} 行第 {column} 列。") from exc
    except OSError as exc:
        raise ConfigurationError(f"无法读取配置文件：{path}") from exc

    unknown_keys = set(data) - {"app_name", "log_level"}
    if unknown_keys:
        raise ConfigurationError(f"配置包含不允许字段：{sorted(unknown_keys)}")

    result: dict[str, str] = {}
    if "app_name" in data:
        result["app_name"] = _validate_app_name(data["app_name"])
    if "log_level" in data:
        result["log_level"] = normalize_log_level(data["log_level"])
    return result


def load_settings(
    *, config_path: Path | None = None, environ: Mapping[str, str] | None = None
) -> Settings:
    """按默认值、TOML、显式环境变量的优先级返回已验证设置。"""
    values: dict[str, str] = {
        "app_name": _DEFAULT_APP_NAME,
        "log_level": _DEFAULT_LOG_LEVEL,
    }
    if config_path is not None:
        values.update(load_toml_settings(config_path))

    active_environ = os.environ if environ is None else environ
    if "COURSE_APP_NAME" in active_environ:
        values["app_name"] = _validate_app_name(active_environ["COURSE_APP_NAME"])
    if "COURSE_LOG_LEVEL" in active_environ:
        values["log_level"] = normalize_log_level(active_environ["COURSE_LOG_LEVEL"])

    return Settings(app_name=values["app_name"], log_level=values["log_level"])


def configure_logging(settings: Settings, *, verbose: bool = False) -> None:
    """配置控制台日志；用户可读输出仍由 CLI 的 print 负责。"""
    level_name = "DEBUG" if verbose else settings.log_level
    logging.basicConfig(
        level=getattr(logging, level_name),
        format="%(asctime)s %(levelname)s %(name)s app=%(app_name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        force=True,
    )
    logging.getLogger(__name__).debug("logging_configured", extra={"app_name": settings.app_name})
