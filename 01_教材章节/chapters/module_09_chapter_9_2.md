# 第 9.2 章：把“看起来像 JSON”变成合同——严格结构化输出、本地验证与失败边界

**适用版本：** Python 3.11+  
**项目连接：** `02_可运行项目/projects/09-llm-contract-client/`（版本 0.3.0）
  
**前置章节：** 第 9.1 章的固定任务、模型允许列表、输入/输出上限、有限重试与最小日志。

## 1. 本章目标

完成本章后，你能够说明“模型返回 JSON”与“应用得到可信业务对象”的区别；能为一个窄任务设计固定 JSON Schema；能把供应商调用关在传输适配器中；能对拒答、空内容、非法 JSON、额外字段、错误枚举、过长文本和短暂失败分别处理；还能用假传输在不调用模型的情况下验证这些边界。

> **本章结论：** 严格结构化输出把模型的候选结果收紧成可检查的数据形状，却不能把概率性模型输出变成事实、授权或可执行命令。

## 2. 为什么自由文本不够用

假设摘要的下一步要显示标题、列出关键点，并根据不确定性决定是否人工复核。若模型只返回一段自由文字，程序只能猜测哪些句子是关键点、猜测“可能”是否代表不确定，或用脆弱的正则表达式拆分。这会让展示、评测、数据库和后续工作流共享一个没有边界的字符串。

结构化输出的目标不是“让回复更漂亮”，而是让程序知道**期待哪些字段、允许哪些值、最多多少项，以及不满足时如何失败**。OpenAI 将遵循 JSON Schema 的 Structured Outputs 与只保证 JSON 语法可解析的 JSON mode 区分；前者用于约束模型返给应用的数据形状。[1]

## 3. 先从下游倒推字段

本项目不让读者设计一个万能“模型答案”对象，而是从课程摘要页面倒推最小对象：一段摘要、若干关键点、一个明确表示不确定程度的枚举。字段越少，测试、评测、隐私审查和变更控制越容易。

| 字段 | 类型 | 本地领域边界 | 下游用途 | 不是它的含义 |
|---|---|---|---|---|
| `summary` | 字符串 | 非空，1–500 字符。 | 面向读者的简短概述。 | 经事实核验的结论。 |
| `key_points` | 字符串数组 | 1–5 项；每项 1–160 字符。 | 可逐项显示与评测。 | 可直接执行的步骤。 |
| `uncertainty` | 枚举字符串 | 仅 `low`、`medium`、`high`。 | 触发人工复核策略的候选信号。 | 数学概率、风险批准或真伪证明。 |

这就是**小而固定的输出合同**。如果将来要加“来源”字段，必须先定义来源如何被验证；不能因为模型能生成网址就把网址当证据。

## 4. JSON Schema 是什么

JSON Schema 是描述 JSON 数据结构的一套规则。对象可以要求固定属性、字段类型、必填字段和数组项目类型。它不是 Python 类，也不是数据库表；它是应用与生成端之间的一个可交换、可验证的结构说明。

项目的 `structured.py` 把 Schema 写成普通 Python 字典，这使其既能作为远端 `response_format` 的输入，也能被无网络测试检查：

```python
SUMMARY_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "minLength": 1, "maxLength": 500},
        "key_points": {
            "type": "array",
            "minItems": 1,
            "maxItems": 5,
            "items": {"type": "string", "minLength": 1, "maxLength": 160},
        },
        "uncertainty": {"type": "string", "enum": ["low", "medium", "high"]},
    },
    "required": ["summary", "key_points", "uncertainty"],
    "additionalProperties": False,
}
```

这里的数字不是模型能力声明，而是本课程应用的资源和界面边界。应根据评测、产品需求和数据分类调整，而不是照抄。

## 5. `required` 与 `additionalProperties: false`

`required` 表示三个字段都必须出现。`additionalProperties: false` 则表示顶层对象不可夹带未审查字段，例如 `command`、`sql`、`confidence_score` 或巨大调试文本。代理的结构化输出调用要求使用 `strict: true` 与 `additionalProperties: false`。[1]

但要注意，禁止未知字段不是“安全万能药”。攻击者或模型仍可把不合适内容塞进允许的 `summary` 字段。因此字段收紧必须和内容限制、权限控制、输出验证和人工复核配合。

## 6. 枚举为何比自由标签可靠

若要求模型生成“一个不确定性标签”，自由文本可能得到 `较低`、`low risk`、`几乎确定`、空字符串或一个段落。程序不得不猜这些词是否等价。枚举把可接受状态写成有限集合：

```python
{"type": "string", "enum": ["low", "medium", "high"]}
```

枚举适用于后续分支有限且可审查的场景，例如页面上的复核提示。它不适用于把复杂现实压成伪精确评分；`low` 也不表示“内容一定正确”。

## 7. 远端严格 Schema 与本地验证都需要

有些初学者会问：“既然服务端已经 `strict: true`，为什么还要本地再检查？”因为应用最终承担下游行为的责任。网络适配器可能变更，SDK 类型可能升级，代理配置可能错误，测试假传输也可返回任意字符串，而且 Schema 只处理结构，不处理业务语义。

项目执行两层验证：远端调用请求严格 Schema；收到 JSON 文本后，`StructuredSummaryClient._parse_reply()` 再解析并检查顶层对象、字段集合、字符串、数组长度、每项长度和枚举。第二层并非不信任某一家服务，而是不给任何外部边界以“唯一防线”的地位。

## 8. 不用“解析成功”冒充“合同成功”

`json.loads()` 成功只能说明字节序列符合 JSON 语法。例如 `[]`、`{"summary": "x"}` 和 `{"summary":"x","key_points":["y"],"uncertainty":"unknown"}` 都能解析，却不符合本项目合同。代码因此按顺序执行四类检查：

| 检查层 | 示例失败 | 受控结果 |
|---|---|---|
| JSON 语法 | `not json`。 | `StructuredOutputError`。 |
| 顶层形状 | 数组、数字或字符串。 | `StructuredOutputError`。 |
| 字段闭集 | 缺字段或含 `extra`。 | `StructuredOutputError`。 |
| 领域边界 | 空摘要、六个关键点、未知枚举。 | `StructuredOutputError`。 |

这种由宽到窄的验证路径可读、可测试，也便于日后把错误类别映射到 API 的稳定公开错误码。

## 9. 类型化结果不是原始供应商响应

项目把成功数据收敛为冻结的 `StructuredSummary`：

```python
@dataclass(frozen=True)
class StructuredSummary:
    request_id: str
    model: str
    summary: str
    key_points: tuple[str, ...]
    uncertainty: Literal["low", "medium", "high"]
    attempts: int
    input_chars: int
    input_tokens: int | None
    output_tokens: int | None
```

它不保存用户原文、系统提示、完整 SDK 响应或隐含请求头。`tuple` 表示成功对象生成后不应被调用者随意追加关键点；`Literal` 把枚举约束暴露给类型检查器。类型不会取代运行时验证，但能让错误更早暴露。

## 10. 为什么仍然使用传输 Protocol

第 9.1 章的关键架构原则在结构化输出中继续适用：高层合同依赖能力，而不是依赖 SDK。`StructuredTransport` 只要求一个 `complete_json()` 方法，输入包括固定模型、固定系统指令、用户文本、token 上限和 Schema；输出只有 JSON 文本与可选 token 摘要。

```python
class StructuredTransport(Protocol):
    def complete_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_text: str,
        max_output_tokens: int,
        schema_name: str,
        schema: Mapping[str, object],
    ) -> StructuredTransportReply: ...
```

测试中的 `RecordingStructuredTransport` 回放 JSON 或异常，不访问网络。生产中的 `OpenAiChatTransport` 才负责 SDK 细节。于是“模型返回未知枚举”或“第一次超时、第二次成功”可在不到一秒的本地测试中重复验证。

## 11. 真实适配器只做请求翻译

`OpenAiChatTransport.complete_json()` 将课程合同翻译为 Chat Completions 的 `response_format`：

```python
response_format={
    "type": "json_schema",
    "json_schema": {
        "name": schema_name,
        "strict": True,
        "schema": dict(schema),
    },
}
```

它仍使用 GPT 系列适用的 `max_completion_tokens`，并只提取 `prompt_tokens` 与 `completion_tokens`。它不决定哪些字段合乎课程业务，不重写模型结果，不保存完整响应，也不把 SDK 对象泄露给核心层。当前实时目录是一次调用前的唯一模型能力依据；模型 ID、价格和能力不能凭记忆硬编码。[2]

## 12. 拒答、空内容与非法 JSON 是不同失败

一次 HTTP `200` 并不保证应用得到可用对象。模型可能拒答，消息内容可能是 `None`，也可能返回一段非 JSON 文本。适配器先把拒答和空内容转换为 `PermanentTransportError`；核心在解析失败时抛出 `StructuredOutputError`。

| 现象 | 所在层 | 默认是否重试 | 原因 |
|---|---|---|---|
| 连接故障、超时、临时服务错误 | 传输。 | 有限重试。 | 之后可能恢复。 |
| 认证、权限、无效请求、模型拒答、空内容 | 传输。 | 不重试。 | 重发不能修正稳定条件。 |
| JSON 语法错误、字段缺失、额外字段、未知枚举 | 本地输出验证。 | 不自动重试。 | 需要修正合同、模型配置或人工处理。 |
| 事实不实或不适合业务 | 评测/领域层。 | 不由本章自动修复。 | 格式合规不能证明语义。 |

速率限制可能按请求和 token 等指标生效，失败请求也可能消耗配额。因此任何重试都必须有次数和时间上限。[3]

## 13. 有限重试只包住短暂失败

`StructuredSummaryClient` 最多尝试两次。只有 `TransientTransportError` 触发一次受控退避；`PermanentTransportError` 立即成为稳定的 `LlmRequestError`；`StructuredOutputError` 直接交给上层，不被伪装成网络问题。

这条边界防止三个常见错误：把错误 Schema 一遍遍消耗配额；把模型拒答隐藏为“系统繁忙”；把非法 JSON 悄悄删字段后继续运行。清晰失败比悄悄修复更有利于评测、审计和安全。

## 14. 日志记录元数据，不记录结构化正文

结构化结果看似“字段化”，但 `summary` 和 `key_points` 仍可能包含用户的私人内容。因此成功日志只有模型、尝试数、请求 ID、输入字符数、关键点数量、不确定性和可选 token 计数。它不写入用户文本、系统提示、JSON 正文、API key、Authorization 头或原始异常。

> **隐私原则：** “已经是 JSON”不等于“可以记录”。数据最小化取决于内容和用途，不取决于序列化格式。

官方安全建议也建议限制输入/输出、进行红队测试，并在高风险情境采用人工复核。[4]

## 15. 面向调用者的 stdout 与内部日志

CLI 的 `--structured` 模式将结构化结果打印到 stdout，因为它是用户主动请求的调用结果；`--verbose` 的日志走 stderr 且不含正文。这不是授权调用者将输出随意持久化：上层产品仍须按自己的数据分类、保留期和访问控制政策处理。

```bash
.venv/bin/course-llm-contract \
  --structured \
  --request-id lesson-9-structured \
  --text 'Python 函数把重复步骤封装为可调用单元。'
```

此命令不接受 `--model`、`--api-key`、`--system-prompt` 或自定义 `--schema`。受控 CLI 的价值恰恰在于拒绝这些看似“灵活”的入口。

## 16. 一次真实烟雾验收说明了什么

在刷新 `03_出版与审校记录/records/module_09_live_model_catalog.json` 后，项目以固定 `gpt-5-mini`、47 个输入字符、128 个输出 token 上限和一次尝试执行了一次严格 Schema 调用。它记录模型、请求 ID、token 摘要、关键点数量、不确定性和“已本地验证”结论，但不保存 prompt 或响应正文；证据文件为 `records/module_09_structured_smoke_evidence.json`。[2]

这证明“当前环境的 SDK 接线、`response_format` 请求形状和本地解析链路”曾经工作。它不证明模型对其他文本准确、始终抗注入、价格稳定、能够并发服务，或已通过安全评测。单次成功是烟雾测试，不是质量报告。

## 17. 结构化输出不等于事实性

模型可以返回格式完美却内容错误的对象，例如把不存在的概念列为关键点，或对一篇含糊文本给出 `low` 不确定性。Schema 无法验证事实来源、时间敏感性、专业资格、用户权限或业务后果。

后续章节会建立固定评测集、长度与字段检查、注入样例和人工预期。对于医疗、法律、金融、招聘、信贷、教育评分或访问控制等高风险用途，结构化结果最多是候选信息，不能替代适用的领域程序和人工责任。

## 18. 结构化输出不等于工具调用

Structured Outputs 的目标是约束**返回给应用的数据**；工具调用的目标是让模型提出一个受定义约束的**外部功能调用**。[1] 两者都需要 Schema，但风险不同：工具调用还涉及授权、参数验证、幂等、超时、审计和副作用。

因此本项目只生成摘要对象，不注册文件、HTTP、SQL、shell 或支付工具。Agent 也不是“模型加 JSON”：它需要模型、工具、记忆、状态、工作流、评测和权限边界的组合；这些会在后续模块按顺序建立。

## 19. 从反例学习：禁止“宽松兼容”

下面的做法看似提高成功率，实际破坏合同：

```python
payload = json.loads(reply.json_text)
payload.setdefault("key_points", [])
payload.setdefault("uncertainty", "low")
return payload
```

它把模型漏字段伪装成一个看似成功的对象，把未知不确定性偷偷降为 `low`，还把可变字典交给下游。正确做法是明确失败并保留脱敏请求 ID，随后在测试、评测或人工复核中决定应修提示、修 Schema、扩大合同还是拒绝该类输入。

## 20. 当前版本明确不做什么

| 能力 | 当前提供 | 当前不提供 |
|---|---|---|
| 输出形状 | 一个固定摘要 Schema。 | 任意用户上传 Schema、动态字段或自由函数参数。 |
| 质量保证 | 语法、字段、长度、枚举与无网络合同测试。 | 事实核验、来源追踪、偏差审计或 SLA。 |
| 运行方式 | 同步单请求、有限重试、最小日志。 | 流式、批量扇出、后台队列、无限重试。 |
| 安全 | 输入/token 上限、无工具、本地验证、日志最小化。 | 完整鉴权、DLP、内容审核、沙箱或组织级治理。 |
| Agent 能力 | 无。 | 记忆、检索、规划、工具执行或自主循环。 |

明确边界是工程能力，不是功能缺失。它让读者能精确描述原型何时安全、何时必须继续设计。

## 21. 快速测试（5 题）

1. `json.loads()` 成功为什么仍不足以接受模型输出？
2. `additionalProperties: false` 能阻止什么，又不能阻止什么？
3. 为什么同一份长度限制既写入远端 Schema 又在本地再次验证？
4. 模型返回 `uncertainty="unknown"` 时，本项目应重试、降级为 `low`，还是受控失败？
5. 一次真实严格 Schema 调用成功，为什么不能证明摘要内容真实？

**答案要点：** 1. 它只证明 JSON 语法，不能证明顶层形状、字段、长度和枚举；2. 它禁止未知顶层字段，不能证明允许字段里的内容安全或真实；3. 远端节约资源且约束形状，本地保护下游并验证所有传输/测试路径；4. 受控失败；5. 它只验证当次接线和格式链路，不代表事实性、鲁棒性或覆盖率。

## 22. 代码阅读（2 题）

1. 阅读 `src/llm_contract_client/structured.py` 中的 `SUMMARY_SCHEMA` 与 `_parse_reply()`。逐项标出哪些规则由 Schema 表达，哪些规则由本地 Python 表达；说明为什么两者不能只留一个。
2. 阅读 `src/llm_contract_client/openai_transport.py` 中的 `complete_json()`。指出 `response_format`、`refusal`、`content`、usage 提取和供应商异常映射的位置；若更换 SDK，为什么修改应留在这个适配器而不是散落到核心和 CLI？

## 23. Debug（2 题）

1. 将 `SUMMARY_SCHEMA` 的 `additionalProperties` 改成 `True`，然后让假传输返回带 `extra` 字段的 JSON。观察本地字段闭集测试仍应失败；解释“远端约束被放宽”时为什么本地防线仍有效，并恢复严格 Schema。
2. 故意在 `structured_completion_succeeded` 日志中加入 `summary.summary` 或在异常日志中写 `str(exc)`。运行脱敏测试，确认其应失败；恢复代码，并写出结构化正文和原始异常可能泄露的三类信息。

## 24. 编程练习（3 题）

1. 设计一个固定的“课程概念提取”对象，只含 `term`、`definition` 和 `needs_human_review`。为每个字段写最小 JSON Schema 与本地验证，并至少测试缺字段、额外字段、未知布尔类型和超长定义。
2. 为 `StructuredSummaryClient` 增加一个只记录整数毫秒的 `latency_ms` 元数据字段。使用可注入时钟完成测试；不得记录 prompt、结果正文或完整时间戳来替代延迟指标。
3. 为失败输出建立一个只含请求 ID、稳定错误码、模型、尝试数和结果类别的 JSONL 事件写入器。要求原子追加、测试中可复现，且显式证明用户原文、系统提示、API key、JSON 正文和原始异常均未写入文件。

## 25. 逆向设计与课后项目

**逆向设计：** 某“AI 提取器”让用户上传任意 JSON Schema、传任意模型和系统提示；收到回复后只做 `json.loads()`；缺字段时默认补空值；日志保存完整 prompt、完整 JSON 和 SDK 异常；遇到拒答或非法字段就无限重试；最后把 `action` 字段传给 shell。请从 Schema 演化、额外字段、类型欺骗、事实性、提示注入、密钥、日志、成本、重试、拒答、权限、命令执行、测试隔离和审计至少倒推十四项失败点，并为每项给出一个可测试的控制措施。

**课后项目：** 将“课程摘要助手 v0.1”升级为 **v0.2 严格结构化摘要助手**。要求：固定 Schema 名称和受控模型；`strict: true`、`required` 与 `additionalProperties: false`；对字段、数组、长度和枚举实施本地重复验证；传输 Protocol 与无网络假传输；拒答、空内容、非法 JSON、永久失败、短暂失败的稳定错误合同；stdout 与 stderr 分流；至少一次明确标注为烟雾测试的真实验收且不保存正文；README 说明 Schema 合规不等于事实、授权或 Agent。下一章将为这条受控边界构建小型、可追溯的评测和提示注入安全测试。


### 本章项目映射

本章对应 `09-llm-contract-client`。先在项目根目录阅读 README、`src/`、`tests/` 与公开静态夹具：从固定模型/任务、严格 JSON Schema、本地重复验证、静态夹具和最小报告读取“模型只提议、应用才验证”的合同。

```bash
cd 02_可运行项目/projects/09-llm-contract-client
.venv/bin/python -m pytest
.venv/bin/python -m mypy
.venv/bin/python -m ruff check src tests
```

**主题化扩展：** 追踪拒答、空内容和非法 JSON 的受控错误；测试日志只保存元数据，绝不记录提示词、正文、秘密或完整原始响应。

上述命令只运行项目内的离线测试和静态检查；不要设置凭据、运行真实烟雾、调用网络/模型/数据库/文件系统/工具/账户，或把通过结果理解为真实能力、生产安全、部署、恢复、成本、容量、合规或副作用授权。

## 参考资料

[1]: https://developers.openai.com/api/docs/guides/structured-outputs "OpenAI: Structured model outputs"
[2]: `03_出版与审校记录/records/module_09_live_model_catalog.json`（2026-08-26 刷新的受控实时目录）与 `records/module_09_structured_smoke_evidence.json`（脱敏单次烟雾验收元数据）。
[3]: https://developers.openai.com/api/docs/guides/rate-limits "OpenAI: Rate limits"
[4]: https://developers.openai.com/api/docs/guides/safety-best-practices "OpenAI: Safety best practices"
