"""为早期章节补充出版参考资料节；不修改已有 25 个编号部分。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]
REFERENCES: dict[str, tuple[str, str]] = {
    "module_00_chapter_0_1.md": ("Python 教程的学习与交互式使用说明", "https://docs.python.org/3/tutorial/"),
    "module_00_chapter_0_2.md": ("Python 官方文档：使用 Python 解释器", "https://docs.python.org/3/tutorial/interpreter.html"),
    "module_00_chapter_0_3.md": ("Python 官方文档：错误和异常", "https://docs.python.org/3/tutorial/errors.html"),
    "module_00_chapter_0_4.md": ("Python 官方文档：虚拟环境和包", "https://docs.python.org/3/tutorial/venv.html"),
    "module_01_chapter_1_1.md": ("Python 官方文档：使用 Python 解释器", "https://docs.python.org/3/tutorial/interpreter.html"),
    "module_01_chapter_1_2.md": ("Python 官方文档：Python 数据模型", "https://docs.python.org/3/reference/datamodel.html"),
    "module_01_chapter_1_3.md": ("Python 官方文档：基础字符串操作", "https://docs.python.org/3/tutorial/introduction.html"),
    "module_01_chapter_1_4.md": ("Python 官方文档：真值测试", "https://docs.python.org/3/library/stdtypes.html#truth-value-testing"),
    "module_01_chapter_1_5.md": ("Python 官方文档：控制流工具", "https://docs.python.org/3/tutorial/controlflow.html"),
    "module_01_chapter_1_6.md": ("Python 官方文档：控制流工具", "https://docs.python.org/3/tutorial/controlflow.html"),
    "module_01_chapter_1_7.md": ("Python 官方文档：数据结构", "https://docs.python.org/3/tutorial/datastructures.html"),
    "module_01_chapter_1_8.md": ("Python 官方文档：输入和输出", "https://docs.python.org/3/tutorial/inputoutput.html"),
    "module_02_chapter_2_1.md": ("Python 官方文档：定义函数", "https://docs.python.org/3/tutorial/controlflow.html#defining-functions"),
    "module_02_chapter_2_2.md": ("Python 官方文档：函数定义", "https://docs.python.org/3/reference/compound_stmts.html#function-definitions"),
    "module_02_chapter_2_3.md": ("Python 官方文档：命名和绑定", "https://docs.python.org/3/reference/executionmodel.html#naming-and-binding"),
    "module_02_chapter_2_4.md": ("Python 官方文档：类型注解", "https://docs.python.org/3/library/typing.html"),
    "module_02_chapter_2_5.md": ("Python 官方文档：unittest", "https://docs.python.org/3/library/unittest.html"),
    "module_03_chapter_3_1.md": ("Python 官方文档：文件和目录访问", "https://docs.python.org/3/library/filesys.html"),
    "module_03_chapter_3_2.md": ("Python 官方文档：pathlib", "https://docs.python.org/3/library/pathlib.html"),
    "module_03_chapter_3_3.md": ("Python 官方文档：json", "https://docs.python.org/3/library/json.html"),
    "module_03_chapter_3_4.md": ("Python 官方文档：logging", "https://docs.python.org/3/library/logging.html"),
    "module_04_chapter_4_1.md": ("Python 官方文档：类", "https://docs.python.org/3/tutorial/classes.html"),
    "module_04_chapter_4_2.md": ("Python 官方文档：类", "https://docs.python.org/3/tutorial/classes.html"),
    "module_05_chapter_5_3.md": ("Pro Git：Git 基础与提交", "https://git-scm.com/book/en/v2/Git-Basics-Recording-Changes-to-the-Repository"),
}


def main() -> None:
    for filename, (title, url) in REFERENCES.items():
        path = ROOT / "chapters" / filename
        text = path.read_text(encoding="utf-8")
        if "## References" in text or "## 参考资料" in text:
            raise RuntimeError(f"reference section already exists: {path}")
        reference = (
            "\n\n### 出版参考\n\n"
            f"本章涉及的语言、标准库或工程行为以该主题的官方资料为准。[1]\n\n"
            "## References\n\n"
            f"[1]: {url} \"{title}\"\n"
        )
        path.write_text(text.rstrip() + reference, encoding="utf-8")
        print(f"updated {filename}")


if __name__ == "__main__":
    main()
