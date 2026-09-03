# 项目 5：CLI 工具平台

**版本：** 0.2.0  
**课程位置：** 模块 5——工程化、包、依赖、Git、配置、日志和持续集成  
**兼容性：** Python 3.11+

本项目将早期一次性脚本迁移为**可安装、可测试、可审查、可在持续集成中运行**的 Python 工程骨架。它提供一个小而完整的环境检查 CLI，用真实代码演示 `pyproject.toml`、`src` 布局、虚拟环境、受控 TOML 配置、环境变量覆盖、脱敏日志、pytest、mypy、Ruff、Git 忽略规则和 CI。

> **边界声明：** 该项目的目标是工程质量基线，而不是通用配置框架或秘密管理系统。它不保存 API key、不读取 `.env` 文件、不加载用户上传的日志配置，也不自动部署。

## 快速开始

在项目根目录创建项目专属虚拟环境并进行可编辑安装。PyPA 建议在使用第三方包时采用项目专属虚拟环境，并指出 `.venv` 应排除在版本控制之外。[1]

```bash
cd "02_可运行项目/projects/05-cli-tool-platform"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --editable ".[dev]"
course-env-check
python -m pytest -q
python -m mypy src
python -m ruff check src tests
```

也可以在不激活环境时显式使用 `.venv/bin/python -m pytest`，从而避免误用另一个 Python。首次安装完成后，`course-env-check` 应输出当前解释器、Python 版本和工作目录。

## 目录结构

```text
05-cli-tool-platform/
├── .github/workflows/quality.yml
├── .gitignore
├── examples/settings.toml
├── pyproject.toml
├── README.md
├── src/cli_tool_platform/
│   ├── __init__.py
│   ├── cli.py
│   └── settings.py
└── tests/
    ├── test_cli.py
    └── test_settings.py
```

`pyproject.toml` 声明构建后端、项目元数据、最低 Python 版本、开发依赖、命令行入口和工具配置。PyPA 将 `[build-system]` 与 `[project]` 作为现代项目的核心声明位置；`[project.scripts]` 可将可导入函数安装为命令行工具。[2]

## 命令契约

| 命令 | 输入 | 标准输出 | 标准错误 | 退出码 |
|---|---|---|---|---|
| `course-env-check` | 无。 | 三行环境摘要。 | 正常情况下无。 | `0` |
| `course-env-check --json` | 无。 | 稳定排序的一行 JSON 环境摘要。 | 正常情况下无。 | `0` |
| `course-env-check --config examples/settings.toml` | 受控、非敏感 TOML。 | 环境摘要。 | 按配置等级记录运行事件。 | `0` |
| `course-env-check --verbose` | 无。 | 环境摘要。 | `DEBUG` 级别诊断日志。 | `0` |
| `course-env-check --config invalid.toml` | 缺失或不合规配置。 | 无保证。 | 简短、脱敏的配置拒绝原因。 | `2` |

## 配置契约

配置优先级从低到高为：**内置默认值 → `--config` 指定的受控 TOML → 显式环境变量**。只有 `app_name` 和 `log_level` 可以出现于 TOML；未知字段会被拒绝，文件大小上限是 64 KiB。`tomllib` 自 Python 3.11 起在标准库中提供 TOML 解析，但文档提示对不可信 TOML 应限制资源使用。[3]

```toml
# examples/settings.toml
app_name = "course-cli"
log_level = "WARNING"
```

支持的日志等级为 `DEBUG`、`INFO`、`WARNING`、`ERROR` 和 `CRITICAL`。部署环境可覆盖非敏感设置：

```bash
COURSE_APP_NAME=local-course COURSE_LOG_LEVEL=DEBUG \
  course-env-check --config examples/settings.toml --json
```

环境变量是进程可读配置渠道，不是秘密保险箱。真实 token、密码和私钥应由受控的秘密管理机制提供，绝不能写入示例 TOML、Git、日志、测试夹具或标准输出。

## 日志与安全边界

用户主动请求的结果由 `print()` 输出；运行事件由模块级 logger 写到标准错误；不能完成命令的配置错误转化为退出码 `2`。标准库日志指南区分普通 CLI 输出、运行事件和应抛出的异常。[4]

日志目前只包含时间、等级、logger 名、应用名和固定事件名称。不要记录完整环境变量、配置正文、秘密、提示词、用户文件全文或未经审查的工具响应。项目不采用用户提供的 `logging.config`，因为官方文档警告其动态对象解析可能带来任意代码执行风险。[5]

## Git 与质量门禁

`.gitignore` 排除 `.venv/`、Python 缓存、pytest/mypy/Ruff 缓存、构建元数据与 `.env`。使用 `git check-ignore -v` 验证规则；已经被跟踪的敏感文件不会因后来加入 `.gitignore` 自动从历史移除。[6]

`.github/workflows/quality.yml` 在 Python 3.11 和 3.12 上执行可编辑安装、pytest、mypy 与 Ruff。CI 只运行与本地相同的质量命令；它不自动发布、不读取密钥、也不替代人工审查。

## 本地验收清单

```bash
course-env-check --json
course-env-check --config examples/settings.toml --verbose
COURSE_LOG_LEVEL=ERROR course-env-check --config examples/settings.toml
python -m pytest -q
python -m mypy src
python -m ruff check src tests
git check-ignore -v .venv/ .pytest_cache/ src/cli_tool_platform.egg-info/
```

验收时还应故意给 TOML 加入未知字段，确认命令返回 `2` 且不会导入模块、执行命令或显示配置正文。

## 参考资料

[1]: https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/ "PyPA: Install packages in a virtual environment using pip and venv"
[2]: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/ "PyPA: Writing your pyproject.toml"
[3]: https://docs.python.org/3/library/tomllib.html "Python `tomllib` documentation"
[4]: https://docs.python.org/3/howto/logging.html "Python Logging HOWTO"
[5]: https://docs.python.org/3/library/logging.config.html "Python `logging.config` documentation"
[6]: https://git-scm.com/docs/gitignore "Git documentation: gitignore"
