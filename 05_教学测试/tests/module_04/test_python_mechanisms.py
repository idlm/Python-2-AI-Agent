"""第 4.3 章可运行示例测试（Python 3.11+）。"""

import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest


EXAMPLES = Path(__file__).resolve().parents[2] / "examples" / "module_04"


def load_module(stem: str):
    path = EXAMPLES / f"{stem}.py"
    spec = importlib.util.spec_from_file_location(f"module_04_{stem}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DecoratorExampleTests(unittest.TestCase):
    def test_decorator_keeps_result_and_function_name(self) -> None:
        module = load_module("decorator_basics")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = module.add_task_prefix("测试")
        self.assertEqual(result, "任务：测试")
        self.assertEqual(module.add_task_prefix.__name__, "add_task_prefix")
        self.assertEqual(output.getvalue().splitlines(), ["开始：add_task_prefix", "结束：add_task_prefix"])


class GeneratorExampleTests(unittest.TestCase):
    def test_generator_resumes_from_previous_yield(self) -> None:
        module = load_module("generator_basics")
        names = module.plugin_names()
        self.assertEqual(next(names), "agent_note")
        self.assertEqual(list(names), ["task", "summarize"])
        self.assertEqual(list(names), [])


class ContextManagerExampleTests(unittest.TestCase):
    def test_context_manager_closes_file_after_normal_exit(self) -> None:
        module = load_module("context_manager_basics")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "lines.log"
            with module.LineWriter(path) as writer:
                writer.write("你好")
                self.assertIsNotNone(writer.file)
            self.assertIsNone(writer.file)
            self.assertEqual(path.read_text(encoding="utf-8"), "你好\n")

    def test_context_manager_closes_file_and_preserves_exception(self) -> None:
        module = load_module("context_manager_basics")
        with tempfile.TemporaryDirectory() as directory:
            writer = module.LineWriter(Path(directory) / "lines.log")
            with self.assertRaisesRegex(ValueError, "预期失败"):
                with writer:
                    writer.write("先写入")
                    raise ValueError("预期失败")
            self.assertIsNone(writer.file)


if __name__ == "__main__":
    unittest.main(verbosity=2)
