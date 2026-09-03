# 第 5.5 章：从遗留脚本到可维护项目——迁移、回归与发布门禁

**适用版本：** Python 3.11+  
**项目连接：** `02_可运行项目/projects/01-task-manager/`、`02_可运行项目/projects/02-text-analyzer/`、`02_可运行项目/projects/03-auto-archive/`、`02_可运行项目/projects/04-plugin-system/`、`02_可运行项目/projects/05-cli-tool-platform/`

## 1. 本章目标

完成本章后，你能够把一个可运行的单文件脚本迁移为可安装、可测试的 `src` 布局项目；能决定何时保留兼容层；能解释单元测试、命令行端到端测试、类型检查、静态检查和 CI 各自防止什么失败；能建立不自动发布、不接触密钥的最小质量门禁。

## 2. 为什么“脚本能跑”还不够

脚本能在作者电脑运行，只证明一个特定路径、解释器、输入和当时环境曾经成功。它没有说明其他人如何安装，如何避免本地缓存遮蔽导入错误，如何复现失败，如何验证重构未改变行为，也没有说明配置和日志是否泄露数据。工程化并非给目录套一层复杂工具，而是把这些隐含前提改成**可执行、可审查的契约**。

## 3. 从生产级 Agent 倒推

Agent 服务最终要组合模型、工具、记忆、状态、工作流和评测。任何一个单文件原型若没有导入边界、接口、测试和可观察性，都会在接入模型调用或外部工具时放大成不可定位的故障。本章的迁移规则因此不是“为了使用某个框架”，而是为后续把可替换工具、状态存储、模型适配器和评测器装进同一系统准备骨架。

## 4. 迁移不是重写：先保护行为

开始前先写下旧程序的外部契约：接受哪些输入、产生哪些输出、创建或移动哪些文件、怎样失败、退出码是什么、日志是否含敏感信息。然后用测试固定这些行为，再改变目录。若一边“顺手优化”一边迁移，就无法区分新 Bug 是旧逻辑、重构还是新功能引入的。

| 问题 | 迁移前的回答 | 迁移后的可验证证据 |
|---|---|---|
| 用户怎样运行？ | `python script.py ...`。 | `[project.scripts]` 声明安装后的命令。 |
| 核心逻辑在哪里？ | CLI、文件读写和计算混在一起。 | 包内 `core.py`，CLI 仅解析参数和映射退出码。 |
| 输入不合法会怎样？ | 可能出现 Traceback。 | 领域异常、稳定错误消息和受控退出码。 |
| 改动会不会破坏旧用法？ | 只能人工猜测。 | 兼容层与回归测试。 |
| 新机器如何复现？ | 依赖作者口头说明。 | `pyproject.toml`、`.venv`、可编辑安装和 CI。 |

## 5. 反向设计一个迁移目标

不要从“我要建几个目录”开始，而要从失败后必须回答的问题倒推。若用户说“自动归档把文件移动错了”，你至少需要知道：计划是否默认 Dry Run、真实移动是否显式确认、清单是否已写、冲突是否拒绝、命令和版本是什么。`03-auto-archive` 因而把计划、执行、清单和回滚放进 `auto_archive.core`，把参数解析放进 `auto_archive.cli`。

## 6. 最小标准项目结构

```text
my-project/
├── pyproject.toml
├── README.md
├── .gitignore
├── .github/workflows/quality.yml
├── src/
│   └── my_package/
│       ├── __init__.py
│       ├── core.py
│       └── cli.py
└── tests/
    ├── test_core.py
    └── test_cli.py
```

`pyproject.toml` 集中项目元数据、构建后端、命令入口和工具配置；`[project.scripts]` 把命令名映射到可导入函数。PyPA 文档将 `[build-system]` 与 `[project]` 作为项目配置的重要表，并说明脚本入口由项目元数据声明。[1]

## 7. 为什么采用 `src` 布局

`src` 布局迫使测试从已安装包导入，而不是偶然从项目根目录导入同名源码。这能暴露“打包漏掉模块”“导入路径依赖当前目录”等问题。它不自动修复逻辑 Bug，但会把安装边界提前暴露。项目 2、3、4 分别以 `text_analyzer`、`auto_archive`、`safe_plugin_system` 作为可安装包；项目 1 使用 `task_manager`。

## 8. 第一步：抽出无界面的核心

下面是任务管理器真实设计的缩小版。函数不读取 `sys.argv`，不 `print()`，不配置全局日志；它只接收已验证的数据并返回领域对象。这样的边界使核心能被 pytest、CLI 和未来 API 共同调用。

```python
# 文件：src/task_manager/core.py（接口节选）
@dataclass(frozen=True)
class Task:
    id: int
    title: str
    priority: int
    done: bool = False

class TaskStore:
    def add(self, title: object, priority: object = 3) -> Task:
        tasks = self.list_tasks()
        task = Task(
            id=max((item.id for item in tasks), default=0) + 1,
            title=_require_title(title),
            priority=_require_priority(priority),
        )
        self._save([*tasks, task])
        return task
```

完整实现还校验 `.json` 路径、固定 Schema、文件大小、重复 ID、原子替换与 `.bak` 备份，位于 `02_可运行项目/projects/01-task-manager/src/task_manager/core.py`。阅读代码时要分清“教学节选”与真实可运行文件；不要把节选复制后误以为已经具备完整文件安全性。

## 9. 第二步：把 CLI 缩到边缘

CLI 的职责是解析参数、创建依赖、调用核心、向标准输出呈现结果，并把可预期异常映射为退出码。它不应重新实现 JSON 解析、业务校验或文件移动。下面的完整兼容入口也说明：迁移后，旧路径不应保留第二套逻辑。

```python
# 文件：src/cli.py
"""历史 CLI 兼容入口。新代码使用安装后的命令。"""

from safe_plugin_system.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

`04-plugin-system/src/cli.py` 使用上述模式。完成可编辑安装后，推荐入口是 `course-safe-plugins`；旧的 `python src/cli.py` 仍委托同一个 `main()`。这样迁移既可逐步进行，也不会让两套安全策略随时间漂移。

## 10. 兼容层的价值与寿命

兼容层是为已有读者、脚本或测试提供的**窄适配器**，不是永久复制粘贴。项目 3 保留 `src/archive.py` 和 `src/cli.py`；项目 4 保留 `src/plugins.py` 和 `src/cli.py`。它们只再导出或委托标准包，不能包含第二份核心实现。兼容层应在 README 标注新入口、旧入口、淘汰条件和计划移除版本；当使用方迁完后应删除它，并用一次明确的主版本变更说明。

## 11. 失败案例：复制而非委托

假设 `src/plugins.py` 与 `src/safe_plugin_system/core.py` 各有一份 `PluginRegistry`。后来一份修复了未知 `type` 的拒绝，另一份仍允许动态导入。测试若只覆盖新命令，旧教材入口就可能绕过安全边界。正确修复不是“两个文件都再改一次”，而是删除重复逻辑，让旧文件只导入唯一实现，并让测试覆盖两种入口。

## 12. 固定数据契约，再谈迁移

项目 1 的任务文件只接受 `version` 与 `tasks`；任务记录只接受 `id`、`title`、`priority`、`done`。项目 3 的 JSON 配置只选择已审查的后缀和目录规则；项目 4 的 JSON 配置只选择固定 `prefix` 类型。**配置只能选择被代码审查的行为，不能给出模块路径、命令或 callable。** 这同样是未来 Agent 工具允许列表的原型。

## 13. 测试金字塔不是测试数量竞赛

| 层级 | 快、定位性强的问题 | 项目中的例子 | 不替代什么 |
|---|---|---|---|
| 核心单元测试 | 字段校验、排序、状态转换、错误类型。 | 任务重复 ID、插件未知字段、归档冲突。 | 不替代真实命令参数与进程退出码。 |
| 组件/文件测试 | JSON Schema、备份、清单、上下文管理器。 | 任务 `.bak`、审计 JSONL、归档 manifest。 | 不替代安装后的命令入口。 |
| CLI 端到端测试 | 参数解析、stdout/stderr、退出码、安装入口。 | `course-tasks` 删除确认、`course-safe-plugins` 审计脱敏。 | 不替代远程部署、权限与真实第三方服务。 |
| 静态检查 | 类型不一致、未使用导入、危险风格变化。 | mypy `TypedDict`、Ruff 导入排序。 | 不证明业务需求正确。 |

pytest 能发现符合默认命名模式的测试文件，也支持普通 `assert`、异常断言及每测试独立的 `tmp_path` 临时目录。[2] 但“17 项测试通过”仍只意味着这 17 个契约通过，不能被写成“系统完全安全”。

## 14. 把一次真实故障转化为类型契约

迁移项目 3 时，JSON 经 `json.load()` 进入程序后本质上是未知数据。运行时已检查 `source`、`destination`、`moved`，但 mypy 仍把它们视为 `Any | None`，拒绝写入 `ManifestItem`。修复不是关闭检查，而是在验证后明确收窄：

```python
if not valid_item:
    raise ArchiveInputError("操作清单项目必须含字符串 source、destination 和布尔 moved。")
validated.append(
    {
        "source": cast(str, source),
        "destination": cast(str, destination),
        "moved": cast(bool, moved),
    }
)
```

这里的 `cast` 只在已有运行时验证之后使用；它不会在运行时转换数据。顺序不可颠倒：先验证不可信输入，再告诉静态检查器该事实。类型检查的价值正在于迫使你说清这种边界。

## 15. 日志、用户输出与测试夹具的隐私边界

项目 4 的审计记录只含插件名、输入/输出长度、成功状态和错误类型；项目 1 的 `--verbose` 只含任务 ID 与优先级。测试刻意使用“正文不应入审计”“不应出现在日志的任务正文”来断言泄露不会发生。日志框架适合运行事件，用户结果应走标准输出，无法完成的操作应通过异常与退出码说明；Python Logging HOWTO 也将这几类使用情形区分开来。[3]

## 16. CI 的最小职责

CI 不负责替你设计功能，也不是部署或密钥系统。最小工作流应在干净环境中选择明确 Python 版本，安装项目与开发依赖，并运行与本地相同的检查。GitHub 的 Python 工作流指南说明了使用 `setup-python` 选择运行时并执行测试的基本模式。[4]

```yaml
# 文件：.github/workflows/quality.yml（完整核心步骤）
- uses: actions/setup-python@v5
  with:
    python-version: ${{ matrix.python-version }}
- name: Install project and quality tools
  run: python -m pip install --upgrade pip && python -m pip install -e ".[dev]"
- name: Run tests
  run: python -m pytest
- name: Type check
  run: python -m mypy
- name: Lint
  run: python -m ruff check src tests
```

项目 1–5 都把这四个命令作为本地与 CI 的共同门禁；当前矩阵覆盖 Python 3.11 和 3.12。工作流不自动发布，也不读取生产 token。

## 17. Git 提交应表达可回退的意图

Git 把提交保存为快照，工作区、暂存区与提交是不同状态。[5] 迁移时一个健康的提交边界可以是“先增加 `pyproject.toml` 与包骨架”“再移动核心并保留兼容层”“再迁移测试与 CI”“最后更新 README”。避免把依赖升级、目录重排、业务新增和格式化全部塞进一条提交；否则回归失败时无法快速缩小原因。

## 18. `.gitignore` 是卫生规则，不是保密方案

`.venv/`、缓存、构建产物、本地任务数据、审计 JSONL 和 `.bak` 应按项目情况加入 `.gitignore`。Git 文档说明，忽略规则主要作用于未追踪文件；已经被追踪的文件不会仅因新增规则而停止跟踪。[6] 因此若密钥已提交，修复步骤不是“加 `.gitignore`”，而是撤销暴露、轮换密钥、清理历史与审查访问日志。

## 19. 依赖升级的安全过程

依赖升级要被当作一次可验证变更，而不是“看到新版本就更新”。先记录当前可复现的质量命令；再阅读上游变更与 Python 支持范围；在独立分支提高约束；重新安装；运行单元、端到端、mypy、Ruff；最后检查 CLI 输出、退出码、配置与日志是否保持契约。`pyproject.toml` 的版本范围应反映你实际测试过的兼容区间，而不是盲目写无限上界。

| 步骤 | 必须产物 | 若失败应做什么 |
|---|---|---|
| 建立基线 | 当前测试、类型、静态检查记录。 | 先修复已有红灯，不在红灯上升级。 |
| 阅读变化 | 上游版本说明与支持矩阵。 | 标记破坏性变更和受影响入口。 |
| 隔离升级 | 单独提交或分支、明确版本约束。 | 不混入重构或功能新增。 |
| 全量验证 | 本地与 CI 同构命令、关键 CLI 验收。 | 定位为依赖、代码或环境问题。 |
| 复盘 | 升级范围、结果、回滚方式。 | 未能解释的行为变化不得发布。 |

## 20. 故障复盘模板

复盘的目的不是找替罪羊，而是让下一次失败更早、更可观测、更可恢复。每一次数据移动、配置拒绝、CI 失败或依赖升级都可使用下表。

| 字段 | 要写什么 |
|---|---|
| 事实 | 何时、哪个版本、哪条命令、哪个输入与退出码；不要混入猜测。 |
| 影响 | 哪些用户、文件、任务、工具调用或评测结果受影响。 |
| 检测 | 测试、日志、用户报告还是 CI 首先发现；为何没有更早发现。 |
| 根因 | 直接技术原因与允许其发生的缺失契约。 |
| 处置 | 已执行的停止、回滚、恢复、密钥轮换或数据核对步骤。 |
| 防复发 | 新增的测试、类型、Schema、文档、门禁或告警及负责人。 |

## 21. 本章验收

在隔离临时目录中完成一次可重复迁移验收：为项目 1 创建任务、修改、完成、尝试不带 `--yes` 的删除，再带 `--yes` 删除；检查 `.bak` 是否存在，检查 verbose 日志不含任务标题。随后在项目 2–5 分别运行 pytest、mypy 和 Ruff。最后故意把项目 4 配置的 `type` 改成 `python_module`，确认命令以退出码 `2` 拒绝且不导入模块。

## 22. 快速测试（5 题）

1. 为什么迁移前要先固定旧脚本的外部行为？
2. `src` 布局主要帮助暴露哪类问题？
3. 兼容层为什么应委托而不是复制核心逻辑？
4. 为什么 mypy 通过不等于不再需要端到端测试？
5. `.gitignore` 为什么不能补救已提交的密钥？

**答案要点：** 1. 防止把业务变化和迁移 Bug 混为一谈；2. 未安装导入、漏打包与路径偶然性；3. 唯一实现避免修复漂移；4. 它不验证参数解析、进程、stdout/stderr 与文件副作用；5. 它通常只影响未追踪文件，暴露后的密钥必须轮换和清理。

## 23. 代码阅读（2 题）

1. 阅读 `02_可运行项目/projects/03-auto-archive/src/auto_archive/core.py` 的 `_load_manifest()`，标出数据从 `json.load()` 到 `ManifestItem` 的每个验证与类型收窄点，并解释为何 `cast` 出现在运行时检查之后。
2. 阅读 `02_可运行项目/projects/04-plugin-system/src/plugins.py` 与 `src/safe_plugin_system/core.py`，证明兼容文件没有复制注册表逻辑。若未来要删除兼容层，哪些测试和 README 文字必须一并改变？

## 24. Debug（2 题）

1. 某同学把 `tests/` 中的导入改成项目根目录的相对路径，CI 里的可编辑安装仍通过，但发布 wheel 后命令找不到包。请重建该故障，恢复从安装包导入的测试，并解释 `src` 布局如何提前暴露它。
2. 把项目 1 的日志改为 `LOGGER.info("task=%s", task.title)`，写一项失败测试证明正文泄露，再恢复只记录 `id` 和 `priority` 的实现。说明为什么仅靠人工“不要泄露”不够。

## 25. 编程练习（3 题）、逆向设计与课后项目

**编程练习：** 1. 为项目 1 增加 `export` 子命令，只输出由固定字段组成的 JSON，禁止将本地文件路径或备份路径放进输出；新增至少四项测试。2. 为项目 2 增加 `--version`，版本来自包元数据或明确常量，并在 CI 中验证命令存在；不要在 CLI 内复制版本字符串。3. 为项目 3 加入受控 `--check-manifest`，只验证 manifest 的结构而不移动、回滚或删除任何文件，并为错误 JSON、未知字段和合法清单各写测试。

**逆向设计：** 一个团队把五个教学项目合为“万能 Agent CLI”：它从 YAML 读取任意 Python 模块路径，用 `eval` 选择函数，把用户全文和 API key 写进 DEBUG 日志，CI 只运行一条冒烟命令，发布前不运行回归。请从失败、攻击、隐私、可维护性、可回滚性和评测六个角度倒推至少十二项设计缺陷，并为每项指向本章的一条具体改进措施。

**课后项目：** 选择一个你已有的单文件脚本，按本章完成迁移包。必须交付 `pyproject.toml`、`src` 包、`[project.scripts]` 命令、薄兼容层或明确破坏性变更说明、README、`.gitignore`、pytest、mypy、Ruff、Python 3.11/3.12 CI 和一份故障复盘。至少包含八项核心/文件测试、三项 CLI 子进程测试、一次错误输入的受控退出码验收，以及一项日志或审计脱敏断言。提交前运行本章四个质量门禁，并记录完整命令与结果。


### 本章项目映射

本章建议在 `02_可运行项目/projects/01-task-manager/` 与 `02_可运行项目/projects/05-cli-tool-platform/` 中对照完成可运行练习。先执行下列命令，比较历史脚本与 `src` 布局迁移后的安装、兼容层、测试和入口职责。

```bash
cd 02_可运行项目/projects/01-task-manager && .venv/bin/python -m pytest && cd ../../../02_可运行项目/projects/05-cli-tool-platform && .venv/bin/python -m pytest
```

**主题化扩展：** 为一个旧入口设计薄兼容层，只委托新包逻辑；写回归测试避免两套实现分叉。

完成后记录输入/输出合同、受控失败、测试命令和安全边界。不要把项目中的本地替身、测试夹具、回环服务或默认无执行模式误作真实网络、模型、生产数据、秘密、部署或副作用授权。

## 参考资料

[1]: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/ "PyPA: Writing your pyproject.toml"
[2]: https://docs.pytest.org/en/stable/getting-started.html "pytest: Get Started"
[3]: https://docs.python.org/3/howto/logging.html "Python Logging HOWTO"
[4]: https://docs.github.com/actions/guides/building-and-testing-python "GitHub Docs: Building and testing Python"
[5]: https://git-scm.com/book/en/v2/Getting-Started-What-is-Git%3F "Pro Git: What is Git?"
[6]: https://git-scm.com/docs/gitignore "Git documentation: gitignore"
