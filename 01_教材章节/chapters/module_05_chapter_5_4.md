# 第 5.4 章：配置与日志——让系统可调整、可诊断而不泄露

**适用版本：** Python 3.11+  
**项目连接：** `02_可运行项目/projects/05-cli-tool-platform/`（版本 0.2.0）

## 1. 本章目标

完成本章后，你能够区分代码、配置、环境变量、日志、用户输出和异常；能设计明确配置优先级；能用 `tomllib` 读取受限 TOML；能用模块级 logger 记录脱敏事件；能解释为什么“能动态配置”不等于“允许配置执行任意代码”。

## 2. 为什么配置与日志要一起学

配置回答“程序在当前环境应怎样运行”，日志回答“程序实际上发生了什么”。若把配置写死在代码中，每次环境改变都要改代码；若把日志和用户输出混在一起，用户会看到无意义的内部细节，开发者又缺少诊断证据。两者都属于系统边界，而非装饰性功能。

## 3. 从生产级 Agent 倒推

Agent 常需配置模型名、超时、工具允许列表、检索阈值和日志级别；还需要记录请求 ID、工具名称、延迟、错误类型和评测版本。配置不能承载用户可执行代码，日志不能默认记录提示词、文件全文、API key 或个人信息。模型、工具、记忆、状态、工作流与评测都应分别配置和观测，不能由一个“万能 config” 混在一起。

## 4. 五类信息不要混用

| 类别 | 示例 | 应放在哪里 | 不应放在哪里 |
|---|---|---|---|
| 源代码 | `load_settings()` 规则 | 版本控制的 `.py` 文件。 | 用户可改的 TOML。 |
| 非敏感运行配置 | `log_level = "INFO"` | 受控 TOML 或环境变量。 | 硬编码在业务函数里。 |
| 密钥 | API key、数据库密码 | 密钥管理系统或运行环境注入。 | Git、日志、示例配置、Traceback。 |
| 用户输出 | CLI 环境摘要。 | `print()` 或 API 响应。 | 日志解析工具。 |
| 诊断事件 | “配置加载成功”、错误类型。 | `logging`。 | 随意的 `print()`。 |

Python Logging HOWTO 明确区分普通 CLI 输出、运行事件、可处理警告和应抛出的错误。[1]

## 5. 本项目的配置优先级

`cli_tool_platform.settings.load_settings()` 使用由低到高的规则：**安全默认值 → 显式指定的受控 TOML 文件 → 显式环境变量**。高优先级只覆盖同名字段，不创建隐藏来源。

```text
内置默认值：app_name=cli-tool-platform，log_level=INFO
        ↓
可选 --config settings.toml
        ↓
COURSE_APP_NAME、COURSE_LOG_LEVEL
        ↓
经验证的 Settings 不可变对象
```

优先级必须写进文档和测试。若用户不知道“到底哪个值生效”，配置就不是可维护性，而是新的不确定性。

## 6. 受控 TOML 配置示例

```toml
# 文件：02_可运行项目/projects/05-cli-tool-platform/examples/settings.toml
app_name = "course-cli"
log_level = "WARNING"
```

项目只允许两个顶层字段；未知字段会被拒绝，而不是静默忽略。Python 3.11 起 `tomllib` 可解析 TOML 1.0.0；`load()` 接收二进制文件对象，且 TOML 无效会抛出 `TOMLDecodeError`。[2]

## 7. 为什么要限制配置大小和字段

即使配置是“数据”，恶意或错误数据也能耗尽资源、改变行为或掩盖拼写错误。标准库文档提醒，解析不可信 TOML 可能消耗大量 CPU 和内存，应限制解析数据规模。[2] 本项目限制配置文件为 64 KiB，并显式拒绝 `module`、`command`、`handler` 等未知字段。限制不是完整沙箱，但它把边界写成可测试契约。

## 8. 真实配置加载代码

```python
# 文件：02_可运行项目/projects/05-cli-tool-platform/src/cli_tool_platform/settings.py（节选）
def load_settings(*, config_path=None, environ=None) -> Settings:
    values = {"app_name": "cli-tool-platform", "log_level": "INFO"}
    if config_path is not None:
        values.update(load_toml_settings(config_path))

    active_environ = os.environ if environ is None else environ
    if "COURSE_APP_NAME" in active_environ:
        values["app_name"] = _validate_app_name(active_environ["COURSE_APP_NAME"])
    if "COURSE_LOG_LEVEL" in active_environ:
        values["log_level"] = normalize_log_level(active_environ["COURSE_LOG_LEVEL"])
    return Settings(app_name=values["app_name"], log_level=values["log_level"])
```

## 9. 逐行解释优先级

先建立默认字典，使缺失配置仍有安全、确定行为；若给出文件路径，读取并验证后覆盖；最后读取环境变量，使部署环境可以不改配置文件地调整名字或级别。`environ` 参数允许测试传入普通字典，而不污染真实进程环境。最后返回冻结 `Settings`，避免运行中某处悄悄修改共享配置。

## 10. 环境变量的边界

`os.environ` 是字符串键和值组成的映射，通常在导入 `os` 时捕获当前进程环境；修改 `os.environ` 会影响随后启动的子进程。[3] 环境变量适合由部署平台注入短期配置和密钥引用，但并不天然安全：同一进程中的库、错误页、子进程或诊断脚本都可能读取它们。绝不要 `print(os.environ)` 或把整个映射写进日志。

## 11. 失败案例：把密钥放进 TOML

```toml
api_key = "<不要在配置文件中保存密钥>"
```

即使该文件被 `.gitignore` 忽略，它仍可能被误上传、备份、复制到工单、显示在编辑器历史或被日志错误打印。修复不是把字段换名，而是从设计上让本项目的 `Settings` 根本不包含密钥。密钥由后续部署模块的专门边界提供，程序只记录“密钥是否存在”之类的非敏感状态。

## 12. 配置错误与 Traceback

`ConfigurationError` 是领域错误，表示文件不存在、TOML 无效、字段未知、名称为空或日志级别非法。CLI 捕获它，向标准错误输出简短诊断并返回退出码 `2`；库函数仍保留异常链，方便开发者查看底层 `FileNotFoundError` 或 `TOMLDecodeError`。不要把所有异常改成“配置错误”，否则权限、磁盘和程序 Bug 会失去差异。

## 13. 日志等级不是装饰文字

| 等级 | 适合记录 | 本项目示例 |
|---|---|---|
| `DEBUG` | 仅用于定位的详细内部路径。 | `logging_configured`。 |
| `INFO` | 正常运行的重要事件。 | `environment_summary_requested`。 |
| `WARNING` | 系统仍能运行但需要关注的异常情况。 | 可选配置被废弃。 |
| `ERROR` | 一个功能无法完成。 | 配置被拒绝。 |
| `CRITICAL` | 进程可能不能继续。 | 必须的安全初始化失败。 |

默认根 logger 级别为 `WARNING`；大型程序通常以 `logging.getLogger(__name__)` 创建模块级 logger，让日志名称反映包层级。[1]

## 14. `print`、日志与异常各司其职

本项目的环境摘要是用户主动请求的结果，使用 `print()` 到标准输出；`environment_summary_requested` 是系统诊断事件，使用 `LOGGER.info()`；配置不合法应终止本次命令，抛出 `ConfigurationError` 并由 CLI 转成退出码。若把三者混用，自动化脚本会无法可靠解析输出，用户会看到内部堆栈，开发者则难以查询事件。

## 15. 脱敏日志原则

记录足以诊断的最少信息：事件名、应用名、日志级别、错误类型、相关 ID、输入长度或配置来源。不要记录原始 token、密码、完整提示词、文件正文、个人身份号码或未审查的第三方响应。脱敏不是把字符串替换成 `***` 后就万事大吉：长度、时间、用户 ID 和组合上下文仍可能敏感，必须定义访问控制、保留期限和删除策略。

## 16. 为什么不加载任意 `logging.config`

`logging.config` 支持字典和文件配置，也可通过特殊字段解析或导入自定义对象；官方文档明确警告，应极其谨慎处理不可信日志配置，因为它可能导入并调用代码。[4] 本项目不用用户提供的 logging 配置文件，也不启用 `logging.config.listen()`；由受控 Python 代码把已验证 `Settings` 映射为固定控制台格式。

## 17. 真实日志配置代码

```python
# 文件：02_可运行项目/projects/05-cli-tool-platform/src/cli_tool_platform/settings.py（节选）
def configure_logging(settings: Settings, *, verbose: bool = False) -> None:
    level_name = "DEBUG" if verbose else settings.log_level
    logging.basicConfig(
        level=getattr(logging, level_name),
        format="%(asctime)s %(levelname)s %(name)s app=%(app_name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        force=True,
    )
```

这里的 `level_name` 已由 `normalize_log_level()` 限制为五个标准名称，因此 `getattr` 不会从用户输入任意取得属性。`--verbose` 是临时诊断开关，覆盖配置级别而不写回文件。真实生产环境还需决定多进程日志、轮转、集中收集和相关 ID 标准。

## 18. 运行演示

```bash
cd 02_可运行项目/projects/05-cli-tool-platform
.venv/bin/course-env-check --json
COURSE_LOG_LEVEL=DEBUG .venv/bin/course-env-check --config examples/settings.toml --verbose
```

预期：标准输出仍只包含环境摘要 JSON；标准错误可出现带时间、等级、logger 名和 `app=` 的日志。配置文件若含 `module = "os"`，命令应退出码 `2`，不得导入模块或执行命令。

## 19. 测试策略

配置测试至少覆盖：默认值、合法 TOML、环境变量覆盖、未知字段、无效 TOML、无效日志等级、缺失文件和大小上限。日志测试应验证事件或格式所需元数据，但不应把真实秘密放进测试夹具。项目当前 9 项 pytest 加上 mypy 和 Ruff，证明了配置行为、类型契约和导入风格；它们不证明密钥管理或日志平台已经生产就绪。

## 20. 本章验收

创建一份临时 TOML：先运行合法配置，确认名称和日志级别生效；再用环境变量覆盖其中一个值；最后加入未知字段，确认程序受控失败。检查日志和标准输出分流；确认 `git status --short` 中没有临时密钥、日志或本地配置。记录命令、退出码与脱敏后的输出。

## 21. 快速测试（5 题）

1. 本项目配置优先级从低到高是什么？
2. 为什么未知 TOML 字段应被拒绝而非静默忽略？
3. 为什么环境变量不是“天然安全的秘密仓库”？
4. `print()`、`logger.info()` 和抛异常分别适合什么？
5. 为什么不能接受用户上传的任意 `logging.config`？

**答案要点：** 1. 默认值、受控 TOML、环境变量；2. 发现拼写错误和攻击扩展；3. 进程、子进程和诊断都可能读取；4. 用户结果、运行事件、无法完成的错误；5. 配置对象解析可能导入或调用代码。

## 22. 代码阅读（2 题）

1. 阅读 `load_settings()`，说明为何 `environ` 允许传入普通映射；这如何提高测试隔离性？
2. 阅读 `configure_logging()`，找出 `--verbose` 如何覆盖 `log_level`，并解释为什么先验证级别再调用 `getattr`。

## 23. Debug（2 题）

1. TOML 写成 `log_level = "trace"` 时程序应怎样失败？修复配置后写一项 pytest，断言错误消息包含允许值。
2. 有人把 `print(os.environ)` 加入错误处理。设计测试或人工检查证明敏感变量会泄露；改为仅记录明确允许的配置来源和错误类型。

## 24. 编程练习（3 题）

1. 为 `Settings` 增加 `request_timeout_seconds`，允许范围 1–120；实现默认值、TOML、环境变量覆盖、类型和范围测试。
2. 为 CLI 增加 `--show-settings`，输出不含秘密的 JSON 配置摘要；确保它不会显示任何以 `KEY`、`TOKEN`、`PASSWORD` 结尾的环境变量。
3. 写 `redact_mapping(mapping)`，只保留允许键，并将敏感键值替换为固定标记；为大小写不同的 `API_KEY`、`token` 和普通键写测试。

## 25. 逆向设计与课后项目

**逆向设计：** 某 Agent 服务将全部环境变量打印到启动日志，允许运营上传 JSON 日志配置，配置里的 `module` 可选择任意导入路径；线上出错时只输出“失败”。请倒推至少八个问题，涵盖配置优先级、Schema、大小限制、秘密管理、日志脱敏、动态导入、错误分类、审计和访问控制。

**课后项目：** 扩展 `05-cli-tool-platform`：加入一个 `config.example.toml`（只能含非敏感字段）、`--show-settings`、配置来源摘要和结构化 JSON 用户输出；保持 `Settings` 不含密钥；新增至少八项 pytest；在 CI 中执行全部检查；更新 README 的配置矩阵与“配置不可信时的拒绝行为”。完成后写复盘：哪些信息应进入日志？哪些信息只能用于本地调试？哪些绝不能离开密钥系统？


### 本章项目映射

本章建议直接在 `02_可运行项目/projects/05-cli-tool-platform/` 中完成可运行练习。先执行：阅读 TOML 字段闭集、环境变量优先级和 stderr 最小诊断，定位配置/日志边界。

```bash
cd 02_可运行项目/projects/05-cli-tool-platform && .venv/bin/python -m pytest
```

**主题化扩展：** 新增一个非敏感设置项；拒绝未知字段，并写测试证明日志不输出完整配置或环境变量。

完成后记录输入/输出合同、受控失败、测试命令和安全边界。不要把项目中的本地替身、测试夹具、回环服务或默认无执行模式误作真实网络、模型、生产数据、秘密、部署或副作用授权。

## 参考资料

[1]: https://docs.python.org/3/howto/logging.html "Python Logging HOWTO"
[2]: https://docs.python.org/3/library/tomllib.html "Python tomllib documentation"
[3]: https://docs.python.org/3/library/os.html#os.environ "Python os.environ documentation"
[4]: https://docs.python.org/3/library/logging.config.html "Python logging.config documentation"
