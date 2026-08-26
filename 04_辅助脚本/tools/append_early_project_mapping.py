"""为模块 0–4 早期章节追加主题化、可运行的项目映射。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]
MAPPINGS: dict[str, tuple[str, str, str, str]] = {
    "module_00_chapter_0_1.md": ("examples/module_00/", "从 `reverse_design.py` 的目标反推输入、步骤、输出和验证条件。", "python3 -m unittest discover -s tests/module_00 -v", "把毕业作品拆成一个可在 15 分钟内验证的最小里程碑，并在学习记录中写出反例。"),
    "module_00_chapter_0_2.md": ("examples/module_00/", "运行环境快照与终端示例，比较脚本路径、当前目录和解释器信息。", "python3 -m unittest discover -s tests/module_00 -v", "修改一个命令使其从错误目录失败，再用绝对/项目根目录方案解释如何恢复可复现性。"),
    "module_00_chapter_0_3.md": ("examples/module_00/traceback_lab.py", "故意传入非数字输入，按“最后一行→自己的代码→输入”顺序读 Traceback。", "python3 -m unittest discover -s tests/module_00 -v", "为同类错误设计一个不打印完整 Traceback 的公开错误摘要，并说明两种输出的读者不同。"),
    "module_00_chapter_0_4.md": ("examples/module_00/", "阅读学习记录和运行快照示例，建立可复现命令、观察和下一步的最小日志。", "python3 -m unittest discover -s tests/module_00 -v", "为本周任一练习创建复现卡：版本、命令、输入类别、预期/实际结果和一个待验证假设。"),
    "module_01_chapter_1_1.md": ("projects/01-task-manager/", "从 README 和 CLI 入口开始，区分交互式探索、安装入口和可复现脚本运行。", "cd projects/01-task-manager && .venv/bin/python -m pytest", "为任务管理器增加一个只打印解释器版本和工作目录的诊断命令，并为其写测试。"),
    "module_01_chapter_1_2.md": ("projects/01-task-manager/", "阅读任务对象创建和更新路径，标出名称绑定、复制和原对象修改的位置。", "cd projects/01-task-manager && .venv/bin/python -m pytest", "构造一次错误的原地修改，再改为返回新值；用断言证明旧任务未被意外改变。"),
    "module_01_chapter_1_3.md": ("projects/01-task-manager/", "阅读 CLI 的 JSON 输出，区分机器可读字段、用户显示文本和内部对象表示。", "cd projects/01-task-manager && .venv/bin/python -m pytest", "新增一个受控格式化函数，使任务标题中的换行或超长文本不会破坏一行摘要。"),
    "module_01_chapter_1_4.md": ("projects/01-task-manager/", "查看待办/完成状态如何进入公开 JSON，而不是直接依赖字符串真假值。", "cd projects/01-task-manager && .venv/bin/python -m pytest", "实现并测试一个显式状态判断函数；拒绝未知状态，避免把非空字符串当作完成。"),
    "module_01_chapter_1_5.md": ("projects/01-task-manager/", "跟踪 CLI 命令分支，说明每个条件的输入、成功输出和受控失败。", "cd projects/01-task-manager && .venv/bin/python -m pytest", "为一个新筛选条件写清优先级和默认分支，并添加正常与边界测试。"),
    "module_01_chapter_1_6.md": ("projects/01-task-manager/", "阅读任务列表输出循环，确认遍历顺序、空集合和终止条件。", "cd projects/01-task-manager && .venv/bin/python -m pytest", "给列表命令增加最大显示数量；测试零、边界值和超过上限的行为。"),
    "module_01_chapter_1_7.md": ("projects/01-task-manager/", "观察任务集合、单个任务记录和 JSON 列表的不同责任。", "cd projects/01-task-manager && .venv/bin/python -m pytest", "设计一个标签索引的最小容器方案，说明为何不把任意嵌套字典直接暴露给 CLI。"),
    "module_01_chapter_1_8.md": ("projects/01-task-manager/", "从命令参数到固定 JSON 输出和退出码，画出用户输入/程序输出合同。", "cd projects/01-task-manager && .venv/bin/python -m pytest", "新增一个只读查询参数；未知值必须受控拒绝并返回稳定退出码。"),
    "module_02_chapter_2_1.md": ("projects/02-text-analyzer/", "阅读 `src/text_analyzer` 中命名函数，标出每个函数负责的单一步骤。", "cd projects/02-text-analyzer && .venv/bin/python -m pytest", "从主流程提取一个纯函数，写出参数、返回值和两个单元测试。"),
    "module_02_chapter_2_2.md": ("projects/02-text-analyzer/", "比较纯文本分析与文件读取边界，找出副作用进入系统的位置。", "cd projects/02-text-analyzer && .venv/bin/python -m pytest", "把文件读取与统计分离；缺失文件应在边界失败，统计函数不接收路径。"),
    "module_02_chapter_2_3.md": ("projects/02-text-analyzer/", "阅读闭包或内部辅助函数时标出哪些名称来自局部、参数和模块作用域。", "cd projects/02-text-analyzer && .venv/bin/python -m pytest", "实现一个返回规范化策略的函数，避免可变全局状态；测试两个独立实例互不影响。"),
    "module_02_chapter_2_4.md": ("projects/02-text-analyzer/", "检查函数签名中的类型注解，比较静态意图和运行时输入验证。", "cd projects/02-text-analyzer && .venv/bin/python -m pytest && .venv/bin/python -m mypy", "为一个公共函数补齐输入/返回类型；对不合法运行时输入保留明确异常或受控错误。"),
    "module_02_chapter_2_5.md": ("projects/02-text-analyzer/", "从 README、CLI、测试和包代码追踪同一个文本输入的完整路径。", "cd projects/02-text-analyzer && .venv/bin/python -m pytest", "增加一个公开指标字段，并同步更新函数、CLI JSON、测试和 README，体验合同变更的影响。"),
    "module_03_chapter_3_1.md": ("projects/03-auto-archive/", "阅读路径验证和归档目标计算，区分用户输入、允许根目录和真实文件系统。", "cd projects/03-auto-archive && .venv/bin/python -m pytest", "为路径遍历或缺失目录添加测试，确保在任何移动前受控拒绝。"),
    "module_03_chapter_3_2.md": ("projects/03-auto-archive/", "从默认 Dry Run 到显式 `--apply` 阅读操作计划，确认何处才允许移动文件。", "cd projects/03-auto-archive && .venv/bin/python -m pytest", "为一个新归档规则先实现 Dry Run 输出，再在显式应用路径中复用同一计划。"),
    "module_03_chapter_3_3.md": ("projects/03-auto-archive/", "检查操作清单 JSON 的字段闭集、版本和原子写入语义。", "cd projects/03-auto-archive && .venv/bin/python -m pytest", "扩展一个非敏感计数字段；未知字段、损坏 JSON 或重复记录必须有测试。"),
    "module_03_chapter_3_4.md": ("projects/03-auto-archive/", "阅读日志和异常映射，比较面向用户的失败摘要与开发者调试信息。", "cd projects/03-auto-archive && .venv/bin/python -m pytest", "新增一个失败类别；CLI 只输出受控错误，日志只保存必要元数据，不保存路径正文或文件内容。"),
    "module_04_chapter_4_1.md": ("projects/04-plugin-system/", "从冻结数据类和 Protocol 开始，观察对象如何同时承载状态和可验证行为。", "cd projects/04-plugin-system && .venv/bin/python -m pytest", "设计一个只读任务对象，写测试保证字段不被原地修改，并说明何时需要新对象。"),
    "module_04_chapter_4_2.md": ("projects/04-plugin-system/", "比较 Protocol、组合对象和允许列表注册表，说明为什么不让继承层级决定权限。", "cd projects/04-plugin-system && .venv/bin/python -m pytest", "用组合增加一个固定格式化能力；不要新增动态导入或让子类自动获得未允许权限。"),
}


def block(path: str, reading: str, command: str, extension: str) -> str:
    return f'''\n\n### 本章项目映射\n\n本章的课后项目应落到 `{path}`，而不是另起一个不可测试的临时脚本。建议先完成：{reading}\n\n```bash\n{command}\n```\n\n**主题化扩展：** {extension}\n\n完成后在项目 README 或学习记录中写明：改动的输入/输出合同、一个失败案例、测试结果，以及为何该改动不扩大未授权的文件、网络、秘密或日志暴露面。\n'''


def main() -> None:
    for filename, values in MAPPINGS.items():
        path = ROOT / "chapters" / filename
        text = path.read_text(encoding="utf-8")
        marker = "### 本章项目映射"
        if marker in text:
            raise RuntimeError(f"mapping already present: {path}")
        reference_marker = "\n## References\n"
        if reference_marker not in text:
            raise RuntimeError(f"missing reference marker: {path}")
        insert = block(*values)
        updated = text.replace(reference_marker, insert + reference_marker, 1)
        path.write_text(updated, encoding="utf-8")
        print(f"updated {filename}")


if __name__ == "__main__":
    main()
