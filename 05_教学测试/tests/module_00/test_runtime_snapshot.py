"""第 0.2 章示例的单元测试。支持 Python 3.11+。"""

import unittest

from examples.module_00.runtime_snapshot import describe_runtime


class RuntimeSnapshotTests(unittest.TestCase):
    def test_snapshot_contains_four_runtime_facts(self) -> None:
        lines = describe_runtime()
        self.assertEqual(len(lines), 4)
        self.assertTrue(lines[0].startswith("Python 可执行文件："))
        self.assertTrue(lines[1].startswith("Python 版本："))
        self.assertTrue(lines[2].startswith("当前工作目录："))
        self.assertEqual(lines[3], "脚本文件名：runtime_snapshot.py")


if __name__ == "__main__":
    unittest.main()
