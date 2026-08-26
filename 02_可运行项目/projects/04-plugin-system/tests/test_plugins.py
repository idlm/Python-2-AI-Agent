"""安全插件系统测试（Python 3.11+）。"""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "plugins.py"
SPEC = importlib.util.spec_from_file_location("plugin_system_plugins", MODULE_PATH)
assert SPEC and SPEC.loader
plugins = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = plugins
SPEC.loader.exec_module(plugins)


class PluginRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = plugins.PluginRegistry()
        self.registry.register(plugins.PrefixPlugin(name="task", prefix="任务："))

    def test_register_and_apply(self) -> None:
        self.assertEqual(self.registry.apply("task", "学习插件"), "任务：学习插件")

    def test_duplicate_plugin_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "重复插件"):
            self.registry.register(plugins.PrefixPlugin(name="task", prefix="另一前缀："))

    def test_unknown_plugin_is_rejected_without_fallback(self) -> None:
        with self.assertRaisesRegex(plugins.UnknownPluginError, "未知插件"):
            self.registry.apply("not_registered", "安全边界")

    def test_names_are_generated_in_stable_order(self) -> None:
        self.registry.register(plugins.PrefixPlugin(name="agent", prefix="Agent："))
        names = self.registry.names()
        self.assertNotIsInstance(names, list)
        self.assertEqual(list(names), ["agent", "task"])

    def test_non_string_input_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "text 必须是 str"):
            self.registry.apply("task", 42)  # type: ignore[arg-type]


class PluginConfigurationTests(unittest.TestCase):
    def test_allowed_prefix_configuration_builds_registry(self) -> None:
        registry = plugins.build_registry_from_config(
            {"plugins": [{"type": "prefix", "name": "task", "prefix": "任务："}]}
        )
        self.assertEqual(registry.apply("task", "完成测试"), "任务：完成测试")

    def test_unknown_type_is_rejected_instead_of_dynamic_import(self) -> None:
        with self.assertRaisesRegex(plugins.PluginConfigurationError, "不允许的插件类型"):
            plugins.build_registry_from_config(
                {
                    "plugins": [
                        {"type": "python_module", "name": "bad", "module": "os"},
                    ]
                }
            )

    def test_unexpected_configuration_field_is_rejected(self) -> None:
        with self.assertRaisesRegex(plugins.PluginConfigurationError, "不允许字段"):
            plugins.build_registry_from_config(
                {
                    "plugins": [
                        {
                            "type": "prefix",
                            "name": "task",
                            "prefix": "任务：",
                            "command": "rm -rf /",
                        }
                    ]
                }
            )

    def test_json_configuration_is_loaded_from_utf8_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "plugins.json"
            config_path.write_text(
                json.dumps(
                    {"plugins": [{"type": "prefix", "name": "task", "prefix": "任务："}]},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            registry = plugins.load_registry_from_json(config_path)
        self.assertEqual(registry.apply("task", "阅读配置"), "任务：阅读配置")

    def test_invalid_json_reports_controlled_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "plugins.json"
            config_path.write_text("{not json}", encoding="utf-8")
            with self.assertRaisesRegex(plugins.PluginConfigurationError, "有效 JSON"):
                plugins.load_registry_from_json(config_path)


class AuditLogTests(unittest.TestCase):
    def test_audit_log_records_only_metadata_and_closes_file(self) -> None:
        registry = plugins.PluginRegistry()
        registry.register(plugins.PrefixPlugin(name="task", prefix="任务："))
        secret_text = "密码不应出现在审计日志中"
        with tempfile.TemporaryDirectory() as directory:
            audit_path = Path(directory) / "audit.jsonl"
            with plugins.JsonlAuditLog(audit_path) as audit_log:
                transformed = registry.apply("task", secret_text, audit_log=audit_log)
                self.assertEqual(transformed, f"任务：{secret_text}")
            content = audit_path.read_text(encoding="utf-8")
            record = json.loads(content)
        self.assertTrue(record["success"])
        self.assertEqual(record["input_length"], len(secret_text))
        self.assertEqual(record["output_length"], len(f"任务：{secret_text}"))
        self.assertNotIn(secret_text, content)

    def test_unknown_plugin_is_audited(self) -> None:
        registry = plugins.PluginRegistry()
        with tempfile.TemporaryDirectory() as directory:
            audit_path = Path(directory) / "audit.jsonl"
            with plugins.JsonlAuditLog(audit_path) as audit_log:
                with self.assertRaises(plugins.UnknownPluginError):
                    registry.apply("missing", "x", audit_log=audit_log)
            record = json.loads(audit_path.read_text(encoding="utf-8"))
        self.assertFalse(record["success"])
        self.assertEqual(record["error_type"], "UnknownPluginError")


if __name__ == "__main__":
    unittest.main(verbosity=2)
