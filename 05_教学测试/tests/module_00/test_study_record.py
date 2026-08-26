"""第 0.4 章示例的单元测试。支持 Python 3.11+。"""

import unittest

from examples.module_00.study_record import build_record, format_record


class StudyRecordTests(unittest.TestCase):
    def test_record_contains_required_fields(self) -> None:
        record = build_record("环境", "Python 在哪里运行？")
        self.assertEqual(record["topic"], "环境")
        self.assertIn("python_version", record)
        self.assertIn("working_directory", record)

    def test_formatted_record_contains_topic(self) -> None:
        record = build_record("日志", "如何记录问题？")
        self.assertIn("- topic: 日志", format_record(record))


if __name__ == "__main__":
    unittest.main()
