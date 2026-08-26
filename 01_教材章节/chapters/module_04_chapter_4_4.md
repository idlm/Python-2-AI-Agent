# 第 4.4 章：插件配置、加载与项目收束——让扩展能力可控上线

**适用版本：** Python 3.11+  
**项目连接：** `projects/04-plugin-system/`（安全文本插件系统，版本 0.2.0）

## 1. 本章目标

本章将插件注册、JSON 配置、允许列表、命令行、审计日志、错误处理与测试收束为一个可运行项目。完成后，你能解释“配置化”与“允许配置任意执行代码”的根本差异，并能为 Agent 的工具配置建立最小安全边界。

## 2. 前置知识

你已完成对象、数据类、协议、组合、装饰器、生成器和上下文管理器。本章不新增神秘框架，而是把这些普通 Python 能力组合为一个明确的工程边界：配置只选择已经审查的能力，不能直接决定要运行哪段代码。

## 3. 从 Agent 倒推能力

在 Agent 中，插件可对应工具、检索器、记忆后端或后处理器。若用户或配置能直接指定模块路径、命令或表达式，系统就可能把“选择工具”变成“执行任意代码”。因此 Agent 不等于工具列表：它还必须具有允许列表、输入校验、权限、可观测性、失败策略和评测。本项目只讲其中的受控插件加载，不把它夸大成完整沙箱。

## 4. 核心词汇与边界

**插件注册表（plugin registry）**是允许能力的受控映射；**允许列表（allowlist）**表示明确允许、其余默认拒绝；**配置契约（configuration contract）**规定字段、类型和范围；**动态导入（dynamic import）**是在运行时按名字装载代码。动态导入本身是 Python 合法功能，但对不可信配置直接启用，会扩大执行边界；本项目故意不这样做。

| 问题 | 受控答案 | 不接受的捷径 |
|---|---|---|
| 能用哪些插件？ | 代码中明确允许的 `prefix` 工厂。 | 配置任意写模块路径。 |
| 传什么参数？ | Schema 检查 `type`、`name`、`prefix`。 | 把未知字段悄悄忽略。 |
| 名称不存在怎么办？ | `UnknownPluginError`，停止执行。 | 回退导入同名模块。 |
| 怎样追踪执行？ | 日志和脱敏 JSON Lines 审计。 | 写入用户完整文本。 |

## 5. 威胁建模：先问“谁能改配置”

学习项目常把 JSON 当成“只是数据”。现实中配置可能来自用户上传、环境变量、版本库、后台管理页或被入侵的存储。只要攻击者能改变配置，他就会尝试把它变成代码执行、路径访问、网络请求或密钥泄露。故本项目的威胁模型是假设配置**不自动可信**；程序必须先验证结构，再映射到代码中预先允许的类型。

## 6. 不安全的反例

```python
# 文件：examples/module_04/unsafe_dynamic_import.py
# 仅用于识别风险；不要在项目中运行或模仿。
import importlib


def build_from_config(config: dict):
    module = importlib.import_module(config["module"])
    factory = getattr(module, config["factory"])
    return factory(**config["arguments"])
```

它看起来“扩展性很强”，实际把模块名、属性名和参数交给配置。配置一旦被篡改，代码审查就无法只看仓库源代码来判断实际执行范围。问题不在 `importlib` 这个工具本身，而在**不可信输入跨越了代码执行边界**。

## 7. 安全的最小配置

项目的示例配置位于 `projects/04-plugin-system/examples/plugins.json`：

```json
{
  "plugins": [
    {
      "type": "prefix",
      "name": "task",
      "prefix": "任务："
    }
  ]
}
```

此 JSON 只表达“创建已经内置的 `prefix` 插件，使用给定名称和前缀”。它不能表达“导入某个模块”“调用某条命令”或“运行一段 Python”。

## 8. 配置加载的真实代码

```python
# 文件：projects/04-plugin-system/src/plugins.py（节选，版本 0.2.0）
def build_registry_from_config(config):
    allowed_top_level = {"plugins"}
    unknown_keys = set(config) - allowed_top_level
    if unknown_keys:
        raise PluginConfigurationError(f"配置包含不允许的顶级字段：{sorted(unknown_keys)}")

    registry = PluginRegistry()
    for position, raw_plugin in enumerate(config["plugins"]):
        plugin_type = raw_plugin["type"]
        if plugin_type != "prefix":
            raise PluginConfigurationError("当前仅允许固定内置类型 'prefix'。")
        allowed_fields = {"type", "name", "prefix"}
        if set(raw_plugin) - allowed_fields:
            raise PluginConfigurationError("插件配置包含不允许字段。")
        registry.register(PrefixPlugin(name=raw_plugin["name"], prefix=raw_plugin["prefix"]))
    return registry
```

## 9. 逐行解释配置边界

`allowed_top_level` 明确顶层允许字段；集合差集找出未知字段。未知字段被拒绝而非忽略，因为拼写错误或攻击字段都不应该悄悄生效。循环中先检查 `type`，当前只映射到内置 `PrefixPlugin`；没有读取模块路径，也没有调用 `eval`、`exec` 或动态导入。`registry.register()` 再次检查名称重复与接口形状，形成防御纵深。

## 10. 配置 Schema 不是“漂亮格式”

Schema 是对输入的可执行契约。它把“我以为有这个字段”变成“程序证明确实允许这个字段”。当前项目没有引入第三方 Schema 库，改用小而显式的函数检查对象、字符串、字段集合和长度；目的不是逃避专业工具，而是让零基础读者看清每个拒绝点。

| 字段 | 规则 | 失败示例 |
|---|---|---|
| 根对象 | 必须是 JSON 对象。 | 顶层写成字符串或数组。 |
| `plugins` | 必须是数组。 | `"plugins": "task"`。 |
| `type` | 只能为 `prefix`。 | `python_module`。 |
| `name` | 以小写字母开头，长度 2–32，仅含允许字符。 | `../../escape`、`A`。 |
| `prefix` | 字符串，最长 200 字符。 | 数字、对象或极长字符串。 |
| 额外字段 | 一律拒绝。 | `command`、`module`、拼错的 `prefxi`。 |

## 11. 受控失败与 Traceback

坏 JSON、缺失文件、未知字段和未知插件不是同一种错误。项目用 `PluginConfigurationError` 表示配置契约失败，用 `UnknownPluginError` 表示调用了未注册名称，用 `PluginExecutionError` 包装插件运行时非预期失败。CLI 将预期插件错误映射为退出码 `2`，将文件层 `OSError` 映射为 `3`。保留异常链可让开发者回到原始根因，而用户仍得到清晰、稳定的边界信息。

## 12. 失败案例：未知类型不会回退导入

以下配置必然被拒绝：

```json
{
  "plugins": [
    {
      "type": "python_module",
      "name": "danger",
      "module": "os"
    }
  ]
}
```

预期诊断是“当前仅允许固定内置类型 `prefix`”，而不是尝试导入 `os`。这一点由单元测试固定。请注意，拒绝“类型名”不是证明所有安全问题都解决了；真正运行外部插件还需要发布源审查、签名、权限最小化、隔离、资源限制和监控。

## 13. 命令行接口

从项目目录运行：

```bash
cd projects/04-plugin-system
python3 src/cli.py --config examples/plugins.json --list
python3 src/cli.py --config examples/plugins.json --plugin task --text "完成验收"
```

预期输出：

```text
agent_note
task
任务：完成验收
```

CLI 的 `--list` 与 `--plugin/--text` 互斥。转换操作只输出结果，不会修改原始配置；如果指定 `--audit-log`，程序使用上下文管理器写入脱敏记录并关闭文件。

## 14. CLI 输入契约

| 命令形态 | 结果 | 原因 |
|---|---|---|
| `--config ... --list` | 列出允许插件，退出码 0。 | 仅观察当前允许能力。 |
| `--config ... --plugin task --text x` | 转换文本，退出码 0。 | 名称和文本齐全。 |
| 只有 `--plugin` | 退出码 2。 | 缺少输入文本。 |
| `--list --plugin task` | 退出码 2。 | 读操作与执行操作不能混用。 |
| `--plugin missing --text x` | 退出码 2。 | 未知能力默认拒绝。 |

## 15. 日志、审计和隐私

标准库日志适合诊断程序流程；JSON Lines 审计适合让每次调用形成机器可读记录。两者都不应默认保存敏感正文。Python 日志系统推荐库以模块级 `getLogger(__name__)` 参与分层记录，应用程序负责配置处理器和级别。[1] 审计记录仅保存插件名、长度、成功状态和错误类型；这降低暴露面，却不等于不再有隐私风险。

## 16. 资源管理与失败路径

CLI 在需要审计时使用：

```python
with JsonlAuditLog(args.audit_log) as audit_log:
    print(registry.apply(args.plugin, args.text, audit_log=audit_log))
```

若 `apply()` 抛出异常，`JsonlAuditLog.__exit__()` 仍关闭文件，然后返回 `False` 让异常向上传播。Python 的上下文管理协议正是为这种“无论块内结果如何，退出时执行清理”的资源边界而设计。[2]

## 17. 项目目录与职责

```text
projects/04-plugin-system/
├── README.md                 # 运行、安全边界与验收说明
├── examples/plugins.json     # 仅含允许类型的样例配置
├── src/plugins.py            # 协议、插件、注册表、配置、审计
├── src/cli.py                # 输入解析、日志配置、退出码边界
└── tests/
    ├── test_plugins.py       # 单元与安全边界测试
    └── test_cli.py           # 子进程端到端测试
```

每个文件只承担一种主要职责。`cli.py` 不实现插件业务，`plugins.py` 不解析命令行，测试不靠手工观察。这种分离将使模块 5 的打包、CI、类型检查和替换实现更容易。

## 18. 测试策略与运行证据

运行：

```bash
cd projects/04-plugin-system
python3 -m unittest discover -s tests -v
```

当前版本的 15 项测试覆盖：注册和重复拒绝、未知名称、输入类型、生成器顺序、允许类型、未知类型、额外字段、无效 JSON、审计脱敏、上下文退出后的读取，以及 CLI 的列表、转换、审计和退出码。端到端测试通过 `subprocess` 运行真实命令行，而不是只测试内部函数。

## 19. 工程与性能取舍

本项目每次 CLI 调用都读取 JSON 并构造注册表，适合小型教学工具。长期运行的服务可以缓存已验证配置，但必须定义配置变更后的重新加载、一致性和回滚策略。不要用缓存掩盖配置校验，也不要为“性能”跳过允许列表。优化只在测量到瓶颈、且不破坏安全语义后进行。

## 20. 模块 4 验收清单

完成下表中的操作并保存终端输出：

| 检查 | 命令或动作 | 通过证据 |
|---|---|---|
| 允许列表 | 运行 `--list`。 | 只列出 `agent_note`、`task`。 |
| 转换 | 调用 `task` 插件。 | 输出带“任务：”前缀。 |
| 安全拒绝 | 将类型改为 `python_module`。 | 退出码 2，未执行导入。 |
| 审计脱敏 | 用敏感测试文本和 `--audit-log`。 | 文件不含原文。 |
| 自动化 | 运行完整测试。 | 15 项通过，0 项失败。 |

## 21. 快速测试（5 题）

1. 为什么配置中的 `type` 只能选择固定字符串，而不能是模块路径？
2. “未知字段忽略”为什么比“未知字段拒绝”更危险？
3. `UnknownPluginError` 与 `PluginConfigurationError` 分别代表什么边界失败？
4. 为什么 `--list` 不应同时执行 `--plugin`？
5. 审计记录不含正文后，仍需考虑哪些元数据风险？

**答案要点：** 1. 防止数据跨越到任意代码执行；2. 拼写和攻击字段会悄悄生效或掩盖配置错误；3. 前者是运行时名称不在注册表，后者是配置不符合契约；4. 保持命令意图清晰、可预测；5. 长度、时间、插件名、用户上下文与保留期限。

## 22. 代码阅读（2 题）

1. 阅读 `build_registry_from_config()`。指出顶层字段、插件字段、类型和名称分别在哪一步被验证；若删除“额外字段拒绝”，哪个测试应失败？
2. 阅读 `cli.py` 的 `main()`。说明为什么把 `PluginError` 与 `OSError` 映射为不同退出码，脚本调用者如何利用这个差异自动处理失败。

## 23. Debug（2 题）

1. 某同学把 `if plugin_type != "prefix"` 改成 `if plugin_type == "prefix"`，导致正确配置被拒绝。写出最小复现、修复和回归测试。
2. 某同学在 `JsonlAuditLog.__exit__()` 中写 `return True`。创建一个会触发 `UnknownPluginError` 的 `with` 块，观察错误为何消失；修复后验证文件仍关闭但异常可见。

## 24. 编程练习（3 题）

1. 实现 `config_summary(config)`，只返回插件类型和名称的摘要，绝不返回 `prefix` 正文；为正常、空列表和未知字段各写测试。
2. 为 CLI 增加 `--check-config`，只验证并列出允许插件，不转换文本；它必须与 `--list`、`--plugin` 的组合规则清晰且有测试。
3. 实现 `AuditEvent` 的时间戳字段，使用 UTC ISO 8601 格式；更新测试，确保日志仍不含用户正文。说明时间戳为什么也需要保留策略。

## 25. 逆向设计与课后项目

**逆向设计：** 某 Agent 后台允许运营人员填写 `module`、`function` 和 `arguments`，上线后有人修改配置使服务执行了非预期文件操作。请逆推至少八个缺陷，覆盖：信任边界、允许列表、Schema、部署权限、审计内容、代码审查、测试、告警和回滚。

**课后项目：** 在项目 4 中安全实现 `SuffixPlugin`。要求：使用冻结数据类；仅允许 `suffix` 类型；拒绝多余字段和未知类型；CLI 能列出、转换并审计；至少新增五项自动化测试；README 增加版本迁移说明与“本系统不是不可信代码沙箱”的明确限制。完成后运行全套测试并记录命令、结果与一次受控失败的输出。

### 本章项目映射

本章直接对应 `projects/04-plugin-system/`。从 `src/safe_plugin_system/`、允许类型配置、CLI 和测试阅读 Protocol、冻结数据、注册表、字段闭集、脱敏审计与受控退出码：

```bash
cd projects/04-plugin-system
.venv/bin/python -m pytest
.venv/bin/python -m mypy
.venv/bin/python -m ruff check src tests
```

**主题化扩展：** 为一个已有的内置允许类型增加字段闭集拒绝测试，并验证审计记录只保存长度和状态。不要新增 `python_module`、可调用对象、动态导入、任意路径、秘密、网络、shell 或真实账户字段；配置文件是数据，不是代码或权限边界。

完成后记录允许列表、输入/输出、异常、日志最小化和回归命令。该项目只验证固定本地插件合同，不构成任意扩展执行、插件供应链安全、真实环境读取或副作用授权。

## 参考资料

[1]: https://docs.python.org/3/library/logging.html "Python logging documentation"
[2]: https://docs.python.org/3/glossary.html#term-context-manager "Python Glossary: context manager"
[3]: https://docs.python.org/3/library/json.html "Python json documentation"
