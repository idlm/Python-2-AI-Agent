# 项目 1：命令行任务管理器

**版本：** 0.1.0  
**兼容性：** Python 3.11+  
**课程位置：** 模块 1、模块 5——变量、函数、数据结构、文件、异常与工程化质量基线

这是一个面向初学者的本地任务管理器。它实现了任务的创建、查看、修改、完成与删除，但把能力收在一个明确边界内：程序只操作用户通过 `--data` 指定的一个 `.json` 文件，不访问网络、不执行外部命令，也不会扫描用户目录。任务标题属于用户正文；运行日志只记录任务编号和优先级，不记录标题。

> **设计原则：** 文件持久化不是“把字典随手写进文件”。本项目先验证固定 JSON 模式，再写入临时文件并替换目标文件；已有数据会先复制为 `.json.bak` 备份。`pathlib`、`json` 与 `tempfile` 是 Python 标准库提供的路径、JSON 和临时文件工具。[1] [2] [3]

| 能力 | 已实现的边界 | 明确不做 |
|---|---|---|
| CRUD | `add`、`list`、`show`、`update`、`done` 与 `remove`。 | 不解释自然语言、不同步云端、不自动删除目录。 |
| 数据文件 | 仅接受固定字段 `version` 与 `tasks` 的 UTF-8 `.json` 文件。 | 不接受可执行配置、未知字段、重复任务编号或超过 1 MiB 的输入。 |
| 删除 | `remove ID --yes` 必须显式确认；成功写入前保留旧内容备份。 | 不提供批量删除或隐式清空。 |
| 可观察性 | `--verbose` 把任务编号、优先级等元数据输出至标准错误。 | 不在日志中写任务标题或持久化文件正文。 |

## 安装与快速运行

以下命令从项目根目录执行。虚拟环境把本项目的开发依赖与系统 Python 隔离；`pip install -e` 以可编辑方式安装，使命令行入口和源码使用同一个项目。[4]

```bash
cd /home/ubuntu/python_private_course/projects/01-task-manager
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"

.venv/bin/course-tasks --data ./demo-tasks.json add "完成变量练习" --priority 1
.venv/bin/course-tasks --data ./demo-tasks.json list
.venv/bin/course-tasks --data ./demo-tasks.json done 1
.venv/bin/course-tasks --data ./demo-tasks.json --json show 1
```

第一次 `add` 会建立数据文件。成功时，人类可读输出写到标准输出；`--json` 提供适合脚本读取的稳定 JSON。例如最后一条命令将输出：

```json
{"done": true, "id": 1, "priority": 1, "title": "完成变量练习"}
```

## 命令契约

| 命令 | 示例 | 成功结果 | 受控失败 |
|---|---|---|---|
| 创建 | `course-tasks --data tasks.json add "写测试" --priority 2` | 创建递增的任务编号。 | 空标题、超过 200 字符或优先级不在 1–5 时退出码 `2`。 |
| 列表 | `course-tasks --data tasks.json list --all` | 默认仅显示待办；`--all` 包含已完成。 | 无文件时返回空列表，不创建文件。 |
| 查看 | `course-tasks --data tasks.json show 1` | 输出指定任务。 | 编号不存在时退出码 `2`。 |
| 修改 | `course-tasks --data tasks.json update 1 --priority 5` | 更新标题和/或优先级。 | 未提供任一修改字段时退出码 `2`。 |
| 完成 | `course-tasks --data tasks.json done 1` | 将任务设为 `done: true`；重复完成仍成功。 | 编号不存在时退出码 `2`。 |
| 删除 | `course-tasks --data tasks.json remove 1 --yes` | 删除一条任务并先备份旧文件。 | 未给 `--yes` 时退出码 `2`，不改变数据。 |

程序将输入、模式与业务错误映射为退出码 `2`，将无法安全读取或写入文件的操作系统错误映射为退出码 `3`。错误信息写到标准错误，便于终端用户与脚本区分正常结果和诊断信息。

## JSON 数据契约与恢复

任务文件的顶层字段必须恰为 `version` 与 `tasks`。每条任务必须拥有唯一正整数 `id`、非空 `title`、`1–5` 的 `priority` 与布尔 `done`。额外字段会被拒绝，避免“看似被忽略、实际日后生效”的隐式配置扩张。

```json
{
  "tasks": [
    {"done": false, "id": 1, "priority": 1, "title": "完成变量练习"}
  ],
  "version": 1
}
```

当已经存在的文件被成功更新，程序在替换前写入相邻的 `tasks.json.bak`。该备份只用于人工恢复最近一次写入前的状态：应先检查其内容，再在程序未运行时将其复制回原路径。备份不是并发数据库、远程备份或灾难恢复方案；多人并发写入同一文件不在本教学项目的保证范围内。

## 质量门禁

```bash
cd /home/ubuntu/python_private_course/projects/01-task-manager
.venv/bin/python -m pytest
.venv/bin/python -m mypy
.venv/bin/python -m ruff check src tests
```

测试覆盖 CRUD、编号分配、固定 JSON 模式、重复编号拒绝、备份、删除确认、JSON 输出、退出码与日志脱敏。`.github/workflows/quality.yml` 在 Python 3.11 与 3.12 上执行可编辑安装、测试、类型检查和静态检查。pytest 的测试发现和 GitHub Actions 的工作流语法可参考官方文档。[5] [6]

## 目录结构

```text
01-task-manager/
├── pyproject.toml
├── README.md
├── .gitignore
├── .github/workflows/quality.yml
├── src/task_manager/
│   ├── __init__.py
│   ├── core.py
│   └── cli.py
└── tests/
    ├── test_cli.py
    └── test_core.py
```

## 参考资料

[1]: https://docs.python.org/3/library/pathlib.html "Python pathlib documentation"
[2]: https://docs.python.org/3/library/json.html "Python json documentation"
[3]: https://docs.python.org/3/library/tempfile.html "Python tempfile documentation"
[4]: https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/ "PyPA: Installing packages using pip and virtual environments"
[5]: https://docs.pytest.org/en/stable/how-to/usage.html "pytest: How to invoke pytest"
[6]: https://docs.github.com/en/actions/writing-workflows "GitHub Actions: Writing workflows"
