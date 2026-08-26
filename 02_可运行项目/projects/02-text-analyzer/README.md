# 项目 2：文本分析工具

**版本：** 0.2.0  
**课程位置：** 模块 2（函数与文本处理）→ 模块 5（工程化迁移）  
**兼容性：** Python 3.11+

该项目将模块 2 的单文件交互式脚本迁移为**可安装、可测试、可静态检查、可在 CI 中运行**的命令行工具。迁移保留原有语义：统计原始字符数、按规范化空白统计词数、统计物理行数，并输出中文报告；新增显式命令行输入、UTF-8 文件读取、文件大小上限、JSON 输出、日志和受控错误码。

> **兼容性说明：** 历史文件 `../02-text-analyzer.py` 与其 `unittest` 测试仍保留，用于回顾模块 2。新目录是模块 5 起唯一继续扩展的标准工程版本。二者目前功能重叠，不应在同一自动化流程中混用导入路径。

## 快速开始

```bash
cd projects/02-text-analyzer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --editable ".[dev]"
course-text-analyzer --text "a b
c"
course-text-analyzer --text "a b
c" --json
python -m pytest
python -m mypy src
python -m ruff check src tests
```

预期文本报告为：

```text
字符数：5；词数：3；行数：2
```

## 输入与输出契约

| 输入方式 | 示例 | 成功输出 | 失败边界 |
|---|---|---|---|
| 直接文本 | `--text "a b"` | 中文报告或 `--json` 的稳定 JSON。 | 参数缺失由 argparse 拒绝。 |
| 本地 UTF-8 文件 | `--file examples/sample.txt` | 与直接文本相同的统计结果。 | 缺失路径、目录、非 UTF-8 和超 1 MiB 文件受控拒绝。 |
| JSON | `--json` | 键名排序的 JSON：`characters`、`lines`、`words`。 | 不混入日志。 |
| 诊断 | `--verbose` | 用户结果保持在标准输出。 | 详细日志只写标准错误。 |

输入错误返回退出码 `2`。普通成功返回 `0`。程序不访问网络、不执行文本、不保存用户内容、不递归扫描目录，也不接受远程 URL。

## 文件安全边界

文件输入必须显式提供 `--file` 路径；工具验证路径是常规文件、大小不超过 1 MiB，并用 UTF-8 解码。该限制降低意外读取大文件或二进制文件的风险，但不是操作系统沙箱：运行该命令的用户仍应只对可访问且授权的文件执行它。

工具日志只记录聚合统计值（字符、词、行），不记录原始文本。若文本包含个人信息、密码或业务机密，不要以 `--verbose` 为由假设它已被匿名化；应先判断是否有权处理该文件。

## 目录结构

```text
02-text-analyzer/
├── .github/workflows/quality.yml
├── .gitignore
├── examples/
├── pyproject.toml
├── README.md
├── src/text_analyzer/
│   ├── __init__.py
│   ├── cli.py
│   └── core.py
└── tests/test_core_and_cli.py
```

`src` 布局使测试和脚本通过已安装包导入代码；`pyproject.toml` 声明命令行入口、开发依赖和质量工具。详见 PyPA 的项目元数据指南。[1]

## 质量门禁

```bash
python -m pytest
python -m mypy src
python -m ruff check src tests
```

测试覆盖历史统计语义、非字符串拒绝、UTF-8 文件、缺失文件、非 UTF-8、大小上限、JSON 输出和 CLI 退出码。CI 在 Python 3.11 与 3.12 上执行同一组安装、测试、类型检查和静态检查命令。[2]

## 参考资料

[1]: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/ "PyPA: Writing your pyproject.toml"
[2]: https://docs.github.com/actions/guides/building-and-testing-python "GitHub Docs: Building and testing Python"
