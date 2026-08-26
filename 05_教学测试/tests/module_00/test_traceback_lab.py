"""第 0.3 章示例的单元测试。支持 Python 3.11+。"""

import unittest

from examples.module_00.traceback_lab import format_square, square_from_text


class TracebackLabTests(unittest.TestCase):
    def test_valid_text_is_squared(self) -> None:
        self.assertEqual(format_square("12"), "12 的平方是 144")

    def test_invalid_text_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            square_from_text("not-a-number")


if __name__ == "__main__":
    unittest.main()
