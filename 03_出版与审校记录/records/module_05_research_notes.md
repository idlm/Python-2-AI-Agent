# 模块 5 官方资料核对笔记

**核对日期：** 2026-08-26（GMT+8）  
**用途：** 支撑模块 5 的虚拟环境、`pyproject.toml`、测试与 CI 正文和项目模板。

| 主题 | 已核对结论 | 教材使用边界 | 来源 |
|---|---|---|---|
| 虚拟环境 | `python3 -m venv .venv` 可在项目目录创建隔离环境；激活后该环境的 Python 与 pip 位于命令路径；环境目录应排除在版本控制之外。 | 教材以 `.venv` 作为推荐本地目录，但强调可直接调用 `.venv/bin/python`，不把激活当作唯一运行方式。 | [1] |
| 项目元数据 | `pyproject.toml` 可包含 `[build-system]`、`[project]` 和工具专用表；新项目应使用 `[project]`，`[build-system]` 定义构建后端。 | 项目 5 用最小 `setuptools` 配置，避免让初学者同时学习多个打包工具。 | [2] |
| 命令行入口 | `[project.scripts]` 能声明安装后可用的命令，入口指向可导入的函数。 | 后续将把项目 CLI 从直接运行 `src/cli.py` 迁移到包入口。 | [2] |
| pytest | pytest 发现 `test_*.py` 和 `*_test.py`，可用普通 `assert` 与 `pytest.raises`；`tmp_path` 提供每个测试独有的临时目录。 | 模块 5 新测试会采用函数式断言与临时目录；历史 `unittest` 会保留并由 pytest 兼容运行。 | [3] |
| GitHub Actions | 建议使用 `actions/setup-python` 显式选择 Python 版本，之后用与本地一致的命令安装依赖、运行测试和 lint。 | 教学工作流只做测试、类型检查和 lint；不自动发布，不在 CI 中存放密钥。 | [4] |

## 引用链接

[1]: https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/ "PyPA: Install packages in a virtual environment using pip and venv"
[2]: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/ "PyPA: Writing your pyproject.toml"
[3]: https://docs.pytest.org/en/stable/getting-started.html "pytest: Get Started"
[4]: https://docs.github.com/actions/guides/building-and-testing-python "GitHub Docs: Building and testing Python"

## Git 与忽略规则补充核对

| 主题 | 已核对结论 | 教材使用边界 | 来源 |
|---|---|---|---|
| Git 快照与三状态 | Git 将提交视为项目快照；工作区修改、暂存区和本地提交是不同状态。 | 课程用它解释为什么先检查 `git status`、再选择性暂存、最后提交；不把提交等同于远程备份。 | [5] |
| `.gitignore` | `.gitignore` 用于忽略尚未被跟踪的、应在团队间共享的生成文件模式；已被跟踪文件不受其影响，需先从索引移除。 | `.venv/`、缓存、构建产物和本地 `.env` 应在项目规则中明确；不以忽略文件代替密钥轮换。 | [6] |

[5]: https://git-scm.com/book/en/v2/Getting-Started-What-is-Git%3F "Pro Git: What is Git?"
[6]: https://git-scm.com/docs/gitignore "Git documentation: gitignore"

## 配置与日志补充核对

| 主题 | 已核对结论 | 教材使用边界 | 来源 |
|---|---|---|---|
| 环境变量 | `os.environ` 是字符串键值映射，通常在 `os` 导入时捕获；用 `os.environ` 修改会映射到进程环境。 | 仅用环境变量注入短期运行配置和密钥引用；不在日志、配置文件或 Git 中记录真实密钥。 | [7] |
| TOML 解析 | Python 3.11 起标准库 `tomllib` 可解析 TOML；`load()` 需要二进制文件对象，解析无效文档会抛出 `TOMLDecodeError`；它不支持写入。 | 用于读取受限、可信的本地应用配置；对不可信 TOML 限制大小并做 Schema 校验。 | [8] |
| 日志选择 | 普通 CLI 输出使用 `print()`；运行事件用 logger；需终止操作的错误应抛异常；`logger.exception()` 仅在异常处理器中记录 Traceback。 | 项目日志只记录脱敏事件与相关 ID；日志不替代用户输出、异常、指标或评测。 | [9] |
| 日志配置安全 | `logging.config` 可从字典或文件配置；其自定义对象和文本到对象转换可能执行代码，应极谨慎对待不可信配置。 | 教学项目从受控 Python 配置开始，不允许用户上传任意 logging 配置或启用 socket `listen()`。 | [10] |

[7]: https://docs.python.org/3/library/os.html#os.environ "Python os.environ documentation"
[8]: https://docs.python.org/3/library/tomllib.html "Python tomllib documentation"
[9]: https://docs.python.org/3/howto/logging.html "Python Logging HOWTO"
[10]: https://docs.python.org/3/library/logging.config.html "Python logging.config documentation"
