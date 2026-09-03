# 项目 4：安全文本插件系统

**版本：** 0.3.0  
**兼容性：** Python 3.11+  
**课程位置：** 模块 4、模块 5——Protocol、组合、装饰器、生成器、上下文管理器、安全加载与工程化迁移

这是一个面向初学者的、**允许列表驱动**的文本转换系统。它不是“从配置中执行任意 Python 代码”的插件平台：配置只能选择代码中已审查的内置 `prefix` 类型，不能给出模块路径、命令、表达式或 callable。这个边界是后续 Agent 工具允许列表的最小原型。

> **安全原则：** “可配置”只表示选择已审查的能力；它不表示配置可以定义或加载任意代码。未知字段、未知类型和未注册名称都默认拒绝。

| 能力 | 已实现 | 明确不做 |
|---|---|---|
| 插件接口 | `TextPlugin` Protocol、不可变 `PrefixPlugin`、显式 `PluginRegistry`。 | 不动态导入不可信模块，不执行配置中的命令。 |
| 配置 | 仅 UTF-8 `.json`；顶层只允许 `plugins`；每项只允许 `type`、`name`、`prefix`。 | 不接受 YAML、任意对象路径或网络下载的插件。 |
| 审计 | JSON Lines 仅记录插件名、输入/输出长度、成功状态和错误类型。 | 不记录 `--text` 正文、token、密码或用户标识。 |
| 命令行 | 安装命令、稳定 stdout、运行日志 stderr、输入拒绝为退出码 `2`。 | 不把 Traceback 或内部对象默认暴露给用户。 |
| 工程质量 | `src` 布局、可编辑安装、pytest、mypy、Ruff、Python 3.11/3.12 CI。 | 不声称教学项目已具备执行恶意第三方代码的沙箱。 |

## 安装与运行

从项目根目录创建隔离环境并以可编辑方式安装。`pyproject.toml` 的 `[project.scripts]` 声明安装后的 `course-safe-plugins` 命令；PyPA 将项目元数据和脚本入口作为标准项目配置的一部分。[1]

```bash
cd "02_可运行项目/projects/04-plugin-system"
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"

.venv/bin/course-safe-plugins --config examples/plugins.json --list
.venv/bin/course-safe-plugins \
  --config examples/plugins.json \
  --plugin task \
  --text "完成第一个安全插件"
```

预期列表和转换结果如下。正常结果只写至标准输出。

```text
agent_note
task
任务：完成第一个安全插件
```

为维持早期教材命令的可追溯性，完成可编辑安装后 `python src/cli.py ...` 仍可运行；它只是一个薄兼容入口，委托 `safe_plugin_system.cli.main`，不包含第二套实现。新代码应使用安装后的 `course-safe-plugins`。

## 配置契约

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

| 字段 | 约束 | 安全理由 |
|---|---|---|
| `plugins` | 必须是数组。 | 防止把任意对象或字符串当成插件清单。 |
| `type` | 当前只能是 `prefix`。 | 防止配置选择任意可执行代码。 |
| `name` | 2–32 个字符；小写字母开头；仅小写字母、数字、`_`、`-`。 | 稳定名称、日志和命名空间边界。 |
| `prefix` | 字符串，最长 200 字符。 | 拒绝类型混乱和无界配置膨胀。 |
| 额外字段 | 一律拒绝。 | 让拼写错误和攻击性扩展早失败。 |

下面的文件将被拒绝，CLI 返回退出码 `2`；它不会尝试导入 `os`。

```json
{
  "plugins": [
    {"type": "python_module", "name": "bad", "module": "os"}
  ]
}
```

## 审计与错误边界

添加 `--audit-log` 会在指定路径创建或追加 JSON Lines 文件。`JsonlAuditLog` 是上下文管理器；即使 `apply()` 抛出异常，`with` 退出时也会关闭文件。Python 将这种进入、退出和异常清理协议称为上下文管理器。[2]

```bash
.venv/bin/course-safe-plugins \
  --config examples/plugins.json \
  --plugin task \
  --text "包含敏感信息的示例文本" \
  --audit-log ./runtime/audit.jsonl
```

一行审计记录类似下面这样。原始文本不会出现。

```json
{"error_type": null, "input_length": 10, "output_length": 13, "plugin": "task", "success": true}
```

| 情况 | 对外结果 | 副作用 |
|---|---|---|
| 配置不存在、JSON 无效、字段或类型不允许 | `PluginConfigurationError`；CLI 退出码 `2`。 | 不注册或执行插件。 |
| 名称未注册 | `UnknownPluginError`；CLI 退出码 `2`。 | 可审计失败元数据；不回退到动态导入。 |
| 输入非字符串 | `TypeError`。 | 保留明确类型诊断。 |
| 内置插件意外失败 | `PluginExecutionError`。 | 原始异常作为异常链保留；日志仅记错误类型。 |
| 审计文件 I/O 失败 | CLI 退出码 `3`。 | 不伪装为配置错误。 |

库使用 `logging.getLogger(__name__)` 创建模块级 logger，CLI 决定日志级别和处理器；Python Logging HOWTO 建议库把日志策略交给应用程序配置。[3]

## 测试与质量门禁

```bash
cd "02_可运行项目/projects/04-plugin-system"
.venv/bin/python -m pytest
.venv/bin/python -m mypy
.venv/bin/python -m ruff check src tests
```

当前套件含 **15 项 pytest**，覆盖注册、重复拒绝、未注册名称、输入类型、生成器顺序、允许列表、未知类型、未知字段、JSON 错误、审计脱敏、安装命令与旧 CLI 兼容入口。`.github/workflows/quality.yml` 在 Python 3.11 和 3.12 上执行相同的可编辑安装、pytest、mypy 和 Ruff 门禁。pytest 使用常规测试文件命名和普通 `assert` 即可发现并运行测试。[4]

## 目录结构

```text
04-plugin-system/
├── pyproject.toml
├── README.md
├── .gitignore
├── examples/plugins.json
├── .github/workflows/quality.yml
├── src/
│   ├── safe_plugin_system/
│   │   ├── __init__.py
│   │   ├── core.py
│   │   └── cli.py
│   ├── plugins.py              # 旧导入兼容层
│   └── cli.py                  # 旧执行兼容层
└── tests/
    ├── test_plugins.py
    └── test_cli.py
```

## 安全边界与演进

允许列表降低了“配置触发任意导入”的风险，但并不把内置插件变成第三方插件沙箱。若未来必须接受外部插件，应另行设计可信发布源、审查或签名、最小文件/网络/密钥权限、进程或容器隔离、超时、资源限制、审计、回滚与升级策略。不要把“动态导入成功”当成可上线的安全证明。

## 参考资料

[1]: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/ "PyPA: Writing your pyproject.toml"
[2]: https://docs.python.org/3/glossary.html#term-context-manager "Python Glossary: context manager"
[3]: https://docs.python.org/3/howto/logging.html "Python Logging HOWTO"
[4]: https://docs.pytest.org/en/stable/getting-started.html "pytest: Get Started"
