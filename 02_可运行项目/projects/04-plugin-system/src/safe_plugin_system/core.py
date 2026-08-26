"""安全插件系统核心（版本 0.3.0，Python 3.11+）。

配置只能选择本模块中显式注册的内置类型。它不能提供模块路径、命令或
callable，因此配置能力不会变成执行任意代码的能力。
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Generator, Mapping, Sequence
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Literal, ParamSpec, Protocol, TextIO, cast

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
P = ParamSpec("P")


class PluginError(Exception):
    """所有可预期插件系统错误的基类。"""


class PluginConfigurationError(PluginError):
    """配置结构、字段或允许类型不符合要求。"""


class UnknownPluginError(PluginError):
    """调用了未注册的插件名称。"""


class PluginExecutionError(PluginError):
    """插件运行失败，且原始异常已被记录。"""


class TextPlugin(Protocol):
    """文本插件的最小结构化接口。"""

    @property
    def name(self) -> str:
        """返回稳定的插件名称。"""

    def transform(self, text: str) -> str:
        """将输入文本转换为输出文本。"""


def _validate_plugin_name(name: str) -> None:
    if not isinstance(name, str) or not _NAME_PATTERN.fullmatch(name):
        raise PluginConfigurationError(
            "插件名称必须以小写字母开头，只能包含小写字母、数字、下划线或连字符，长度为 2–32。"
        )


def _validate_text(text: str, *, field: str = "text") -> None:
    if not isinstance(text, str):
        raise TypeError(f"{field} 必须是 str，实际为 {type(text).__name__}。")


def log_transform_call(function: Callable[P, str]) -> Callable[P, str]:
    """记录调用元数据；日志只记录长度，永不记录用户正文。"""

    @wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> str:
        name: object | None = kwargs.get("name")
        if name is None and len(args) >= 2:
            name = args[1]
        text: object | None = kwargs.get("text")
        if text is None and len(args) >= 3:
            text = args[2]
        text_length: int | str = len(text) if isinstance(text, str) else "invalid"
        LOGGER.info("plugin_apply_started plugin=%s input_length=%s", name, text_length)
        try:
            result = function(*args, **kwargs)
        except (PluginError, TypeError):
            LOGGER.warning("plugin_apply_rejected plugin=%s", name)
            raise
        except Exception as exc:
            LOGGER.exception(
                "plugin_apply_failed plugin=%s error_type=%s", name, type(exc).__name__
            )
            raise PluginExecutionError(f"插件 {name!r} 执行失败。") from exc
        LOGGER.info("plugin_apply_finished plugin=%s output_length=%s", name, len(result))
        return result

    return cast(Callable[P, str], wrapper)


@dataclass(frozen=True)
class PrefixPlugin:
    """安全的内置前缀插件。"""

    name: str
    prefix: str

    def __post_init__(self) -> None:
        _validate_plugin_name(self.name)
        _validate_text(self.prefix, field="prefix")
        if len(self.prefix) > 200:
            raise PluginConfigurationError("prefix 最长为 200 个字符。")

    def transform(self, text: str) -> str:
        _validate_text(text)
        return f"{self.prefix}{text}"


@dataclass(frozen=True)
class AuditEvent:
    """一次插件调用的脱敏审计记录。"""

    plugin: str
    input_length: int
    output_length: int
    success: bool
    error_type: str | None = None

    def to_json_line(self) -> str:
        return json.dumps(
            {
                "plugin": self.plugin,
                "input_length": self.input_length,
                "output_length": self.output_length,
                "success": self.success,
                "error_type": self.error_type,
            },
            ensure_ascii=False,
            sort_keys=True,
        )


class JsonlAuditLog:
    """以 ``with`` 管理的 JSON Lines 审计日志，不记录用户文本正文。"""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._file: TextIO | None = None

    def __enter__(self) -> JsonlAuditLog:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self._path.open("a", encoding="utf-8")
        return self

    def record(self, event: AuditEvent) -> None:
        if self._file is None:
            raise RuntimeError("审计日志尚未打开；请在 with 语句中调用 record。")
        self._file.write(event.to_json_line() + "\n")
        self._file.flush()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> Literal[False]:
        if self._file is not None:
            self._file.close()
            self._file = None
        return False


class PluginRegistry:
    """保存显式注册的插件；默认拒绝未知名称。"""

    def __init__(self) -> None:
        self._plugins: dict[str, TextPlugin] = {}

    def register(self, plugin: TextPlugin) -> None:
        _validate_plugin_name(plugin.name)
        if not callable(getattr(plugin, "transform", None)):
            raise TypeError("插件必须提供可调用的 transform(text) 方法。")
        if plugin.name in self._plugins:
            raise ValueError(f"重复插件：{plugin.name}")
        self._plugins[plugin.name] = plugin
        LOGGER.info("plugin_registered plugin=%s", plugin.name)

    def names(self) -> Generator[str, None, None]:
        """按稳定排序逐个产生插件名，而非暴露内部字典。"""
        yield from sorted(self._plugins)

    @log_transform_call
    def apply(self, name: str, text: str, *, audit_log: JsonlAuditLog | None = None) -> str:
        _validate_plugin_name(name)
        _validate_text(text)
        plugin = self._plugins.get(name)
        if plugin is None:
            event = AuditEvent(name, len(text), 0, False, "UnknownPluginError")
            if audit_log is not None:
                audit_log.record(event)
            raise UnknownPluginError(f"未知插件：{name}")
        try:
            result = plugin.transform(text)
        except Exception as exc:
            event = AuditEvent(name, len(text), 0, False, type(exc).__name__)
            if audit_log is not None:
                audit_log.record(event)
            raise PluginExecutionError(f"插件 {name!r} 执行失败。") from exc
        _validate_text(result, field="插件输出")
        if audit_log is not None:
            audit_log.record(AuditEvent(name, len(text), len(result), True))
        return result


def _require_mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise PluginConfigurationError(f"{field} 必须是对象。")
    return value


def _require_str(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise PluginConfigurationError(f"{field} 必须是字符串。")
    return value


def build_registry_from_config(config: Mapping[str, object]) -> PluginRegistry:
    """仅从固定允许列表创建插件，绝不根据配置动态导入模块。"""
    allowed_top_level = {"plugins"}
    unknown_keys = set(config) - allowed_top_level
    if unknown_keys:
        raise PluginConfigurationError(f"配置包含不允许的顶级字段：{sorted(unknown_keys)}")

    raw_plugins = config.get("plugins")
    if not isinstance(raw_plugins, Sequence) or isinstance(raw_plugins, (str, bytes, bytearray)):
        raise PluginConfigurationError("plugins 必须是插件配置列表。")

    registry = PluginRegistry()
    for position, raw_plugin in enumerate(raw_plugins):
        item = _require_mapping(raw_plugin, field=f"plugins[{position}]")
        plugin_type = _require_str(item.get("type"), field=f"plugins[{position}].type")
        if plugin_type != "prefix":
            raise PluginConfigurationError(
                f"不允许的插件类型：{plugin_type!r}；当前仅允许固定内置类型 'prefix'。"
            )
        allowed_fields = {"type", "name", "prefix"}
        item_unknown_keys = set(item) - allowed_fields
        if item_unknown_keys:
            raise PluginConfigurationError(
                f"plugins[{position}] 包含不允许字段：{sorted(item_unknown_keys)}"
            )
        registry.register(
            PrefixPlugin(
                name=_require_str(item.get("name"), field=f"plugins[{position}].name"),
                prefix=_require_str(item.get("prefix"), field=f"plugins[{position}].prefix"),
            )
        )
    return registry


def load_registry_from_json(path: Path) -> PluginRegistry:
    """读取 UTF-8 JSON 配置并构造受限注册表。"""
    if path.suffix.lower() != ".json":
        raise PluginConfigurationError("插件配置必须使用 .json 扩展名。")
    try:
        with path.open("r", encoding="utf-8") as config_file:
            raw_config: object = json.load(config_file)
    except FileNotFoundError as exc:
        raise PluginConfigurationError(f"找不到配置文件：{path}") from exc
    except json.JSONDecodeError as exc:
        message = f"配置不是有效 JSON：第 {exc.lineno} 行第 {exc.colno} 列。"
        raise PluginConfigurationError(message) from exc
    return build_registry_from_config(_require_mapping(raw_config, field="配置根对象"))


__all__ = [
    "AuditEvent",
    "JsonlAuditLog",
    "PluginConfigurationError",
    "PluginError",
    "PluginExecutionError",
    "PluginRegistry",
    "PrefixPlugin",
    "TextPlugin",
    "UnknownPluginError",
    "build_registry_from_config",
    "load_registry_from_json",
]
