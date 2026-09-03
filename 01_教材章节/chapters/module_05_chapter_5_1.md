# 第 5.1 章：工程化的第一条边界——项目、虚拟环境与可复现运行

**适用版本：** Python 3.11+  
**项目连接：** `02_可运行项目/projects/05-cli-tool-platform/`（将在本模块逐步建立）

## 1. 本章目标

理解“能在我的电脑运行”与“任何人能按说明复现运行”的差异；能创建、使用和删除项目专属虚拟环境；能区分 Python 解释器、第三方依赖、项目源代码与运行命令。

## 2. 为什么工程化从环境开始

同一段代码在不同机器失败，常不是算法错误，而是解释器版本、安装位置或依赖版本不同。工程化不是把目录变复杂，而是让输入、版本、命令和输出可以被别人验证。

## 3. 从生产 Agent 倒推

生产 Agent 依赖模型 SDK、数据库客户端、检索库和观测工具。若环境不可复现，部署和评测就无法可信。虚拟环境不能解决密钥、网络和数据问题，但它先把“这个项目使用哪些 Python 包”从机器全局状态中分离出来。

## 4. 核心概念

| 术语 | 含义 | 不要混用 |
|---|---|---|
| 项目根目录 | 包含项目配置、源代码、测试与文档的顶层目录。 | 不等于当前终端一定所在目录。 |
| 虚拟环境 | 项目专属的隔离 Python 与包安装位置。 | 不等于容器或完整操作系统隔离。 |
| 依赖 | 项目运行或开发所需要的外部包。 | 不把标准库当成必须安装的第三方依赖。 |
| 可复现运行 | 他人按明确版本与命令能得到可验证结果。 | 不等于“我以前运行过一次”。 |

## 5. 官方推荐的最小命令

PyPA 文档建议在项目目录中创建 `.venv`，并推荐在使用第三方包时采用虚拟环境。[1]

```bash
cd 02_可运行项目/projects/05-cli-tool-platform
python3 -m venv .venv
source .venv/bin/activate
python -m pip --version
```

预期最后一行的路径包含 `.venv`。退出环境使用 `deactivate`；删除 `.venv` 不会删除项目源代码，却会删除该环境安装的包。

## 6. 为什么使用 `python -m pip`

直接输入 `pip` 可能调用另一个解释器对应的安装器。`python -m pip` 的 `python` 明确指定解释器，因此安装与运行更容易保持一致。即使不激活环境，也可使用 `.venv/bin/python -m pip install ...` 和 `.venv/bin/python -m pytest`。

## 7. 最小可运行环境快照

```python
# 文件：examples/module_05/environment_check.py
# 版本：1.0.0
from __future__ import annotations
import sys
from pathlib import Path


def environment_summary() -> dict[str, str]:
    return {
        "executable": sys.executable,
        "python_version": sys.version.split()[0],
        "cwd": str(Path.cwd()),
    }


if __name__ == "__main__":
    for key, value in environment_summary().items():
        print(f"{key}={value}")
```

## 8. 逐行解释

`sys.executable` 是当前运行这段代码的解释器路径；它比猜测“终端里显示的是哪个 Python”可靠。`Path.cwd()` 显示当前工作目录；相对路径会从这里解析。把这三个值写进 Bug 报告，常能迅速区分环境问题和代码问题。

## 9. 失败案例：全局安装

若你在系统 Python 里执行 `pip install 某包`，项目 A 升级该包可能破坏项目 B。更危险的是，文档写“运行 `python`”，而读者实际调用了另一个 Python。修复不是“再试一次安装”，而是检查 `sys.executable`、`python -m pip --version` 和依赖声明。

## 10. 失败案例：提交 `.venv`

虚拟环境含有机器相关路径和二进制文件，通常不应提交到 Git。应提交的是“如何创建环境”和“需要哪些依赖”的声明；应忽略 `.venv/`。这也是为什么可复现不等于复制整个开发者电脑。

## 11. Traceback 阅读

`ModuleNotFoundError` 首先说明当前解释器找不到模块，不自动证明“没有安装”。先检查 Traceback 中解释器路径，再运行 `python -m pip show 包名`；最后检查项目是否遗漏依赖声明。不要用随机 `pip install` 掩盖版本不一致。

## 12. 项目根目录的最小结构

```text
05-cli-tool-platform/
├── pyproject.toml
├── README.md
├── src/
│   └── cli_tool_platform/
├── tests/
└── .gitignore
```

源代码、测试、配置和文档在同一根目录，使安装、测试和 CI 都有稳定起点。

## 13. `src` 布局的意义

`src/` 布局让测试更倾向于导入已安装的包，而非偶然从当前目录导入源码。它会更早暴露“忘记安装项目”“导入路径写错”等问题。它不是唯一布局，却适合本书后续需要发布 CLI、API 和 Agent 服务的项目。

## 14. `pyproject.toml` 的角色

`pyproject.toml` 可声明构建后端、项目元数据、依赖和工具配置；PyPA 指出 `[build-system]` 说明构建工具，现代新项目应使用 `[project]` 填写基础元数据。[2] 它不是“把所有配置塞进一个文件”，而是给工具一个共同、版本控制的入口。

## 15. 最小元数据示例

```toml
# 文件：pyproject.toml
[build-system]
requires = ["setuptools>=77"]
build-backend = "setuptools.build_meta"

[project]
name = "cli-tool-platform"
version = "0.1.0"
requires-python = ">=3.11"
```

此章先理解含义，后续章节会加入包发现、开发依赖、测试和命令行入口。

## 16. 工程约定

每个项目 README 至少写明：目标、非目标、兼容 Python 版本、创建环境命令、安装命令、运行命令、测试命令、失败边界和安全限制。命令应从项目根目录复制即可执行，不能依赖作者未说明的 IDE 设置。

## 17. 安全边界

虚拟环境不隔离操作系统权限；环境中的包仍可读写你授权的文件、访问网络或读取环境变量。依赖安装也属于供应链边界：优先从受信任来源安装、记录版本与来源，不从陌生说明中复制安装命令。

## 18. 性能与维护

不要为每个脚本创建一个环境，也不要让所有项目共享永久全局依赖堆。环境创建有成本，但换来项目间隔离；缓存可以加快 CI，却不得取代锁定、测试和版本记录。

## 19. 测试策略

环境快照示例应测试字典有 `executable`、`python_version`、`cwd` 且值非空；不要断言开发者机器的绝对路径。项目安装验收应在干净虚拟环境执行，测试“声明是否足够”，而不只是“当前机器恰好装过什么”。

## 20. 本章验收

在一个新目录中创建 `.venv`，运行环境快照，记录解释器路径；退出环境后再次运行，比较路径。然后创建 `.gitignore` 加入 `.venv/`，并用 `git status` 确认环境目录不被跟踪。

## 21. 快速测试（5 题）

1. 虚拟环境隔离的主要对象是什么？
2. 为什么 `python -m pip` 比裸 `pip` 更可追溯？
3. `.venv` 为什么通常不提交？
4. `ModuleNotFoundError` 的第一步诊断是什么？
5. `src` 布局要提前暴露哪类导入错误？

**答案要点：** 1. 项目包安装位置；2. 明确安装器所属解释器；3. 含机器相关安装结果；4. 查当前解释器与安装位置；5. 未安装项目却偶然从根目录导入。

## 22. 代码阅读（2 题）

1. 阅读第 7 节，说明为何不能把 `sys.executable` 写死成自己的路径。
2. 阅读第 15 节，找出构建后端、项目名、版本和最低 Python 版本分别在哪里声明。

## 23. Debug（2 题）

1. 终端提示已安装 `pytest`，但 `python -m pytest` 报模块不存在。写出至少三条检查命令，并解释每条命令验证什么。
2. 一个脚本在 IDE 成功、在终端失败并找不到相对文件。用环境快照和 `Path.cwd()` 定位原因，再把路径处理改为基于项目根目录或显式参数。

## 24. 编程练习（3 题）

1. 实现 `environment_check.py` 并写两项 `unittest` 测试，不断言固定绝对路径。
2. 为任意早期项目写 `.gitignore`，至少忽略 `.venv/`、`__pycache__/` 和测试缓存；解释为什么每项不应提交。
3. 创建最小 `pyproject.toml`，使用 `tomllib` 读取并测试 `project.name` 与 `project.requires-python`。

## 25. 逆向设计与课后项目

**逆向设计：** 某同事说“代码昨天在我电脑上好好的”，CI 却无法导入模块，部署环境又运行了旧版本。倒推解释器、依赖、项目布局、安装步骤、版本声明和 CI 命令分别可能哪里失控。

**课后项目：** 建立 `05-cli-tool-platform` 骨架：创建 `.venv`、`src`、`tests`、README、`.gitignore` 和最小 `pyproject.toml`；写环境检查命令；在全新环境中执行安装和测试。提交一个运行记录，包含命令、解释器路径、输出与一次你主动修复的环境错误。


### 本章项目映射

本章建议直接在 `02_可运行项目/projects/05-cli-tool-platform/` 中完成可运行练习。先执行：从 `pyproject.toml`、`src/` 与 README 的安装步骤验证项目根目录和解释器边界。

```bash
cd 02_可运行项目/projects/05-cli-tool-platform && .venv/bin/python -m pytest
```

**主题化扩展：** 在临时目录复现一次从错误工作目录运行的失败，再在 README 中说明为何项目根目录是合同的一部分。

完成后记录输入/输出合同、受控失败、测试命令和安全边界。不要把项目中的本地替身、测试夹具、回环服务或默认无执行模式误作真实网络、模型、生产数据、秘密、部署或副作用授权。

## 参考资料

[1]: https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/ "PyPA: Install packages in a virtual environment using pip and venv"
[2]: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/ "PyPA: Writing your pyproject.toml"
