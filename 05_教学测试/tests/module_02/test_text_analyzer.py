import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[3] / "02_可运行项目" / "projects" / "02-text-analyzer.py"
SPEC = importlib.util.spec_from_file_location("text_analyzer", MODULE_PATH)
assert SPEC and SPEC.loader
text_analyzer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(text_analyzer)


class TextAnalyzerTests(unittest.TestCase):
    def test_normalize_and_count_words(self) -> None:
        self.assertEqual(text_analyzer.normalize_text("  a   b  "), "a b")
        self.assertEqual(text_analyzer.count_words("  a   b  "), 2)

    def test_analyze_text(self) -> None:
        self.assertEqual(text_analyzer.analyze_text("a b\nc"), {"characters": 5, "words": 3, "lines": 2})

    def test_report_and_invalid_input(self) -> None:
        self.assertEqual(text_analyzer.format_report("a b"), "字符数：3；词数：2；行数：1")
        with self.assertRaises(TypeError):
            text_analyzer.analyze_text(123)


if __name__ == "__main__":
    unittest.main()
