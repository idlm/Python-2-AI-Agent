"""补齐早期章节第 21–25 节练习配额；仅用于课程出版修订。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]
TOPICS: dict[str, str] = {
    "module_00_chapter_0_1.md": "从毕业作品反推学习路径与第一行代码",
    "module_00_chapter_0_2.md": "程序、文件、终端与解释器如何协作运行",
    "module_00_chapter_0_3.md": "输出、错误消息与 Traceback 的阅读顺序",
    "module_00_chapter_0_4.md": "学习日志、问题清单与可复现练习环境",
    "module_01_chapter_1_1.md": "交互式解释器、脚本与可复现程序",
    "module_01_chapter_1_2.md": "变量、对象、赋值与类型的名称绑定",
    "module_01_chapter_1_3.md": "字符串、数字与可读输出",
    "module_01_chapter_1_4.md": "布尔值与任务状态",
    "module_01_chapter_1_5.md": "可读条件判断与规则分支",
    "module_01_chapter_1_6.md": "循环、遍历与终止条件",
    "module_01_chapter_1_7.md": "为任务选择合适的数据结构",
    "module_01_chapter_1_8.md": "输入输出与任务管理器对话",
    "module_02_chapter_2_1.md": "把步骤命名为可复用函数",
    "module_02_chapter_2_2.md": "参数、返回值与副作用的函数合同",
    "module_02_chapter_2_3.md": "作用域、名称解析与闭包",
    "module_02_chapter_2_4.md": "Lambda 与类型注解的接口表达",
    "module_02_chapter_2_5.md": "文本分析工具的函数组合、测试与收束",
    "module_03_chapter_3_1.md": "文件系统与路径定位",
    "module_03_chapter_3_2.md": "pathlib 与安全文件操作",
    "module_03_chapter_3_3.md": "CSV、JSON、YAML 的交换与验证",
    "module_03_chapter_3_4.md": "日志、调试与异常处理",
    "module_04_chapter_4_1.md": "类与对象的状态和行为组织",
    "module_04_chapter_4_2.md": "继承与组合的复用取舍",
    "module_05_chapter_5_3.md": "Git 快照、提交边界与可审查协作",
}


def exercise_tail(topic: str) -> str:
    return f'''## 21. 快速测试（5 题）

1. 用一句话说明**{topic}**要解决的核心问题。
2. 写出本章一个最重要的输入、处理和输出边界。
3. 给出一个最小反例，说明忽略该边界会产生什么错误。
4. 说明本章概念与前一章一个概念如何衔接。
5. 判断一句错误说法并改正：只要程序“能运行”，就已经满足本章的工程要求。

## 22. 代码阅读（2 题）

1. 从本章任一可运行示例选取 8–15 行，标注每个变量/对象/函数的输入、变化和输出；说明其中一行为什么不能随意删除。
2. 阅读对应项目或示例中的一个失败分支，画出“输入 → 验证 → 受控结果”的三步链路；指出它没有记录或打印的敏感信息。

## 23. Debug（2 题）

1. 故意把本章一个合法输入改成边界外输入，先记录 Traceback 或受控错误的最后一行，再定位最靠近自己代码的失败点并修复。
2. 制造一个看似能运行、但违反 **{topic}** 合同的小错误；写出复现步骤、预期/实际结果、根因和最小回归测试。

## 24. 编程练习（3 题）

1. 将本章一个重复步骤重写为最小可运行函数或模块，明确参数、返回值和异常/错误边界。
2. 为该实现写至少两个测试：一个正常路径、一个边界或失败路径；断言可观察结果而不是内部实现细节。
3. 增加一个不泄露正文或敏感数据的最小诊断摘要，并验证用户结果与诊断输出职责分离。

## 25. 逆向设计与课后项目

**逆向设计：** 假设一个初学者项目在 **{topic}** 上失败：输入不可复现、状态不清、错误无法定位、数据被静默覆盖或结果难以验证。倒推至少五项缺失的规则、测试、日志、命名或操作边界，并按“先阻止什么风险”排序。

**课后项目：** 在本章已有示例基础上完成一个小型、可运行、可测试的改造。项目必须写明目标、输入、输出、失败案例、运行命令、两个自动化测试和一个逆向设计结论；不得读取真实秘密、执行未经授权的网络/文件副作用，或把用户正文写入日志。
'''


def main() -> None:
    for filename, topic in TOPICS.items():
        path = ROOT / "chapters" / filename
        text = path.read_text(encoding="utf-8")
        marker = "## 21."
        if marker not in text:
            raise RuntimeError(f"missing section 21 marker: {path}")
        prefix = text.split(marker, maxsplit=1)[0]
        path.write_text(prefix + exercise_tail(topic), encoding="utf-8")
        print(f"updated {filename}")


if __name__ == "__main__":
    main()
