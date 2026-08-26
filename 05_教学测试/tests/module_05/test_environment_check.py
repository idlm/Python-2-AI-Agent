"""第 5.1 章环境检查示例测试。"""

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[2] / "examples" / "module_05" / "environment_check.py"
SPEC = importlib.util.spec_from_file_location("module_05_environment_check", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class EnvironmentCheckTests(unittest.TestCase):
    def test_summary_has_nonempty_diagnostic_fields(self) -> None:
        summary = module.environment_summary()
        self.assertEqual(set(summary), {"executable", "python_version", "cwd"})
        self.assertTrue(all(isinstance(value, str) and value for value in summary.values()))

    def test_summary_reports_an_existing_interpreter_path(self) -> None:
        summary = module.environment_summary()
        self.assertTrue(Path(summary["executable"]).exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
