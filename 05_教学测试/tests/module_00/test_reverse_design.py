"""第 0.1 章示例的单元测试。支持 Python 3.11+。"""

import unittest

from examples.module_00.reverse_design import capabilities_for, format_plan


class ReverseDesignTests(unittest.TestCase):
    def test_plan_lists_only_missing_capabilities(self) -> None:
        plan = format_plan("调用受控工具并记录过程", ["函数", "日志"])
        self.assertIn("Tool Calling", plan)
        self.assertIn("异常处理", plan)
        self.assertIn("状态管理", plan)
        self.assertNotIn("函数、", plan)

    def test_unknown_feature_has_no_required_capabilities(self) -> None:
        self.assertEqual(capabilities_for("不存在的功能"), [])


if __name__ == "__main__":
    unittest.main()
