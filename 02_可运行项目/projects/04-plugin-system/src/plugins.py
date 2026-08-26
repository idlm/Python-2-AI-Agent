"""历史兼容入口（版本 0.3.0）。

新代码请导入 :mod:`safe_plugin_system`。本文件仅保留早期教材
``import plugins`` 与基于文件路径的测试；它不包含第二套实现。
"""

from safe_plugin_system.core import (
    AuditEvent,
    JsonlAuditLog,
    PluginConfigurationError,
    PluginError,
    PluginExecutionError,
    PluginRegistry,
    PrefixPlugin,
    TextPlugin,
    UnknownPluginError,
    build_registry_from_config,
    load_registry_from_json,
)

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
