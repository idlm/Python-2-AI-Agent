import unittest

from examples.module_01.repl_and_names import build_task_preview, rename_preview


class ReplAndNamesTests(unittest.TestCase):
    def test_rename_returns_new_dictionary(self) -> None:
        original = build_task_preview("学习变量", 1)
        revised = rename_preview(original, "完成变量练习")
        self.assertEqual(original["title"], "学习变量")
        self.assertEqual(revised["title"], "完成变量练习")
        self.assertIsNot(original, revised)


if __name__ == "__main__":
    unittest.main()
