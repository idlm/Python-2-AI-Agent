# 第 5.2 章：项目元数据、依赖与质量门禁——把“能运行”变成“可验证”

**适用版本：** Python 3.11+  
**项目连接：** `projects/05-cli-tool-platform/`

## 1. 本章目标

读懂 `pyproject.toml` 中构建、项目元数据、开发依赖、命令行入口和工具配置的职责；能在新虚拟环境中可编辑安装项目；能用 pytest、mypy 和 Ruff 建立不同层面的质量证据。

## 2. 为什么需要质量门禁

测试通过不代表类型正确、风格一致或安装后可导入。质量门禁不是为了让工具变多，而是把不同失败尽早分开：运行行为由测试检查，类型契约由类型检查检查，明显静态问题由 lint 检查，安装与入口由干净环境验收检查。

## 3. 从 Agent 倒推能力

Agent 服务将调用模型、数据库、工具和网络。一次“看似成功”的本地运行无法证明依赖齐全、接口稳定或部署入口存在。工程门禁让模型工具调用、评测脚本和部署工作流共享同一组可验证命令，而非依赖口头记忆。

## 4. `pyproject.toml` 的三类信息

| 区域 | 回答的问题 | 本项目示例 |
|---|---|---|
| `[build-system]` | 用什么构建后端构建项目？ | `setuptools.build_meta`。 |
| `[project]` | 项目叫什么、支持什么 Python、运行依赖是什么？ | 名称、版本、`requires-python`。 |
| `[tool.*]` | pytest、mypy、Ruff 等工具怎样执行？ | 测试目录、严格类型检查、目标版本。 |

PyPA 将 `pyproject.toml` 说明为打包工具和 lint、类型检查等工具共享的配置文件；新项目应使用 `[project]` 声明基础元数据。[1]

## 5. 真实项目配置

```toml
# 文件：projects/05-cli-tool-platform/pyproject.toml（节选）
[project]
name = "cli-tool-platform"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8.0,<10", "mypy>=1.10,<2", "ruff>=0.8,<1"]

[project.scripts]
course-env-check = "cli_tool_platform.cli:main"
```

## 6. 逐行解释

`dependencies` 放运行所必需的包；当前为空，因为环境检查只用标准库。`dev` 是可选开发依赖，测试、类型检查和 lint 不应强迫最终用户安装。`course-env-check` 将安装后的命令映射到包内 `main` 函数，避免文档要求用户记住 `python src/cli.py` 的相对路径。[1]

## 7. 可编辑安装

```bash
python -m pip install --editable ".[dev]"
course-env-check
python -m pytest -q
```

可编辑安装使解释器导入项目源目录，修改源码后无需每次重装；它仍会验证构建元数据与入口是否可解析。[2] 不要把“可编辑”理解为跳过测试或省略版本声明。

## 8. pytest 的职责

pytest 自动发现 `test_*.py`，使用普通 `assert` 展示失败表达式，并可用 `raises` 验证异常。[3] 本项目测试 `environment_summary()` 的字段契约以及 `main()` 的退出码和输出。测试应断言稳定行为，不断言某台机器固定的绝对路径。

## 9. mypy 的职责

类型注解让人和工具知道函数输入、输出和可空性预期。`mypy src` 在运行前发现不一致，例如声明返回 `str` 却返回数字。类型检查不能证明网络响应正确、文件存在或模型输出真实；它只覆盖类型相关的一层风险。

## 10. Ruff 的职责

Ruff 可发现导入排序、未使用名称和其他静态问题。本项目的 `ruff check src tests` 曾发现导入顺序错误；修正后测试没有变化，但静态门禁更一致。格式、lint 和类型检查是互补层，不应把任一工具误称为“代码完全正确”。

## 11. 失败案例：开发依赖混入运行依赖

若把 `pytest` 放进普通 `dependencies`，最终只想运行命令行工具的用户也会安装测试框架。反过来，若运行时确实需要 `httpx` 却只放在 `dev`，部署环境将失败。判断标准是：用户运行已发布功能时是否需要该包，而不是“作者电脑上是否装过”。

## 12. 失败案例：只运行源码

若始终执行 `python src/cli_tool_platform/cli.py`，你可能绕过了已安装包、入口点和打包配置。`src` 布局的价值在于迫使测试和命令从安装后的包导入，从而更早发现元数据或包发现错误。

## 13. Traceback 诊断

安装后 `course-env-check: command not found` 时，检查当前虚拟环境是否激活、`python -m pip show cli-tool-platform` 是否指向正确环境、`[project.scripts]` 的函数路径是否可导入。若 pytest 报 `ModuleNotFoundError`，先确认执行的是同一环境的 `python -m pytest`。

## 14. 本地质量命令

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m mypy src
.venv/bin/python -m ruff check src tests
```

把命令写进 README、CI 和 Runbook；同一工作不应在三处使用不同命令。GitHub 建议在工作流中显式使用 `setup-python` 选择版本，再执行本地等价的安装和测试步骤。[4]

## 15. CI 工作流

`projects/05-cli-tool-platform/.github/workflows/quality.yml` 在 Python 3.11 与 3.12 的矩阵中执行：检出代码、设置解释器、可编辑安装、pytest、mypy、Ruff。工作流不自动发布，也不读取密钥。CI 的任务是尽早阻止不符合已声明契约的提交，而不是替代代码审查。

## 16. 版本与依赖范围

`pytest>=8.0,<10` 表示允许兼容主版本范围内的更新，但阻止未来主版本自动进入；范围并非保证绝对可复现。真正需要逐字节重建时，还应使用锁文件或受控制品来源。课程后续会讨论部署与供应链边界；本章不假装一个版本范围就是完整锁定策略。

## 17. 安全边界

开发依赖也能执行代码，因此安装它们同样属于供应链操作。CI 只应使用经过审查的工作流与最小权限；不要把生产密钥放进测试日志或 `pyproject.toml`。依赖声明提高透明度，不自动使每个依赖安全。

## 18. 性能与维护

类型检查和 lint 增加少量时间，却能节省回归排查。将依赖缓存用于 CI 可以加速，但缓存键必须随依赖声明变化；过期缓存不能替代干净环境验收。

## 19. 测试策略

至少保留三种验证：函数行为单测、安装后入口验收、静态质量门禁。对错误路径写测试，例如 CLI 解析错误或缺失配置；对工具自身失败也保留可读输出，避免“CI 红了”成为唯一信息。

## 20. 本章验收

在删除 `.venv` 后重新创建环境，执行可编辑安装、`course-env-check`、pytest、mypy 和 Ruff。若其中一步失败，不要跳过它；记录命令、解释器路径、完整错误和修复后的回归结果。

## 21. 快速测试（5 题）

1. `[build-system]` 和 `[project]` 分别解决什么问题？
2. 为什么 pytest 通常不放入运行依赖？
3. `project.scripts` 的价值是什么？
4. mypy 能证明 HTTP 请求一定成功吗？
5. 为什么 CI 要显式选择 Python 版本？

**答案要点：** 1. 构建后端与项目元数据；2. 最终用户运行功能不必测试；3. 安装后稳定命令入口；4. 不能；5. 避免运行器默认版本变化。

## 22. 代码阅读（2 题）

1. 阅读项目 `pyproject.toml`，指出哪些依赖属于运行时、哪些属于开发期，并说明依据。
2. 阅读 `quality.yml`，解释 Python 版本矩阵如何使同一命令在两个解释器版本下执行。

## 23. Debug（2 题）

1. 将 `course-env-check = "cli_tool_platform.cli:main"` 故意改成不存在的函数，执行安装后命令并解读错误；恢复后写回归步骤。
2. 在测试中故意把 `assert exit_code == 0` 改为 `== 1`，阅读 pytest 的断言报告；修复后再次运行全套门禁。

## 24. 编程练习（3 题）

1. 为 CLI 增加 `--json`，输出稳定排序的 JSON 环境摘要；写两项 pytest 测试。
2. 在 `pyproject.toml` 新增一个空的 `docs` optional dependency group，并在 README 解释何时应使用 optional dependency。
3. 为 CI 增加 `python -m compileall src` 步骤，说明它能发现什么、不能发现什么。

## 25. 逆向设计与课后项目

**逆向设计：** 某团队本地测试通过，CI 失败，生产又因找不到命令入口而中断。倒推项目元数据、虚拟环境、运行与开发依赖、入口点、Python 版本和 CI 命令可能有哪些缺陷。

**课后项目：** 把项目 4 或项目 3 复制到新的标准 `src` 布局中；写 `pyproject.toml`、可编辑安装入口、pytest 兼容测试、mypy 与 Ruff 配置、README 和 CI。完成后，在全新环境运行全部质量命令，并记录一次迁移引入的导入错误及修复。


### 本章项目映射

本章建议直接在 `projects/05-cli-tool-platform/` 中完成可运行练习。先执行：阅读控制台入口、pytest、mypy、Ruff 与 CI 的相互关系，区分开发依赖和运行依赖。

```bash
cd projects/05-cli-tool-platform && .venv/bin/python -m pytest && .venv/bin/python -m mypy && .venv/bin/python -m ruff check src tests
```

**主题化扩展：** 为一个纯函数增加测试、类型注解和静态检查通过证据；不要以跳过类型检查换取短期绿色。

完成后记录输入/输出合同、受控失败、测试命令和安全边界。不要把项目中的本地替身、测试夹具、回环服务或默认无执行模式误作真实网络、模型、生产数据、秘密、部署或副作用授权。

## 参考资料

[1]: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/ "PyPA: Writing your pyproject.toml"
[2]: https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/ "PyPA: Install packages in a virtual environment using pip and venv"
[3]: https://docs.pytest.org/en/stable/getting-started.html "pytest: Get Started"
[4]: https://docs.github.com/actions/guides/building-and-testing-python "GitHub Docs: Building and testing Python"
