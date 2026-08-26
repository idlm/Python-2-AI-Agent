# 模块 9 官方资料与实时模型目录核对笔记

**核对日期：** 2026-08-26（GMT+8）  
**教材兼容性：** Python 3.11+；项目只用本课程环境提供的 OpenAI-compatible Chat Completions 代理。  
**实时目录快照：** `records/module_09_live_model_catalog.json`，由受控 `/models` 接口在本次写作开始时获取；模型 ID、价格、能力必须以该快照和后续重新获取的实时目录为准，不能凭记忆硬编码。

## 1. 当前可用模型与教学选择

| 目的 | 本次目录中的候选 | 课程默认选择 | 理由与边界 |
|---|---|---|---|
| 最小文本分类/提取/改写 | `gpt-5-nano`、`gpt-5-mini` | `gpt-5-mini` | 实时目录将其描述为适合多数任务的低成本快速默认；模块 9 用单请求、小输入、小输出和注入假客户端测试，不做批量调用。 |
| 复杂推理/代码 | `gpt-5`、`gpt-5.5`、`claude-sonnet-4-6`、`claude-opus-*` | 不作为最小项目默认 | 教学先理解消息、输入/输出 Schema、失败与成本；复杂模型选择应由评测和实际预算决定。 |
| 长上下文/多模态 | `gemini-3-flash-preview`、`gemini-3.1-pro-preview` | 不在 9.1 最小文字项目启用 | 不让“更长上下文”掩盖输入边界、隐私和评测问题。 |
| 严格结构化输出 | 实时目录中所有模型均声明 `supports_response_format_json_schema=true` | `gpt-5-mini` + `response_format` JSON Schema | 代理技能要求 `strict: true` 与 `additionalProperties: false`；客户端仍须在本地解析、验证并处理拒答/空输出。 |

本次实时目录同时显示：模型均声明 tools、vision、JSON Schema、thinking 能力，但 `supports_streaming=false`。因此模块 9 初期不承诺流式响应。GPT-5 系列的 thinking 参数为 `reasoning`；若未做评测，最小分类/提取项目不启用思考预算，以免增加成本和延迟。

## 2. 结构化输出

OpenAI 官方说明 Structured Outputs 可令模型响应遵循提供的 JSON Schema，并与只保证合法 JSON 的 JSON mode 区分；结构化输出适用于希望约束模型回给应用的数据，工具调用适用于把模型连接到应用功能。[1]

**教材边界：** 模型符合 Schema 不等于语义真实、来源可信、任务安全或业务操作已获授权。项目必须继续做长度、枚举、领域规则、拒答和空内容检查；不要把模型文本直接视为 SQL、shell、文件路径、权限决定或工具参数。

## 3. 速率限制、重试与成本

OpenAI 官方将速率限制描述为按请求、token 等指标、按模型/组织/项目生效的访问限制；响应可能含 `Retry-After`。官方 SDK 会自动重试符合条件的速率限制错误并遵守该头；应用层若再加重试，必须避免与 SDK 重叠，并限制次数与总时间。[2]

**教材边界：** 最小客户端只对明确短暂的传输/服务不可用失败实施有限重试；不重试请求 Schema、认证、配额/账单或本地输入错误；日志记录模型、尝试、结果类别和 token 计数（若有），不记录用户正文、系统提示、API key 或完整响应。所有请求应限制输入字符数和输出 token 预算；失败请求也会消耗速率限制，不能通过无限重发解决问题。[2]

## 4. 安全与提示注入

OpenAI 官方建议限制用户输入及输出 token 以降低提示注入和滥用风险；建议红队测试、在高风险场景保留人工复核，并明确模型会出现幻觉、偏差和其他限制。[3]

**教材边界：** 用户内容是数据，不是模型系统规则的替代品；系统提示只是行为约束，不能视为权限系统；项目 9 不开放工具调用、不执行模型输出、不请求用户秘密、不把输出用于高风险决定。若未来需要安全标识，应使用稳定、隐私保护的标识而非直接发送用户名或邮箱；泄露或怀疑泄露的 API key 应立即撤销并替换。[3]

## 5. 最小项目架构

| 层 | 职责 | 禁止事项 |
|---|---|---|
| `PromptRequest` | 限制任务类型、输入长度、输出预算与模型允许列表。 | 任意模型 ID、任意系统提示、秘密直传。 |
| `LlmTransport` Protocol | 隔离 SDK/网络调用，可由固定假客户端测试。 | 在测试中真实消耗模型调用。 |
| `LlmClient` | 构造固定 messages、有限重试、解析/验证 JSON Schema、最小日志。 | 执行模型文本、把输出当事实。 |
| CLI/API 边缘 | 提供明确输入输出和受控错误。 | 日志正文、API key 参数、任意 tool/function。 |
| 评测/人工复核 | 比较输入、预期和判定证据。 | 宣称一次成功示例等于可靠性。 |

## 参考资料

[1]: https://developers.openai.com/api/docs/guides/structured-outputs "OpenAI: Structured model outputs"
[2]: https://developers.openai.com/api/docs/guides/rate-limits "OpenAI: Rate limits"
[3]: https://developers.openai.com/api/docs/guides/safety-best-practices "OpenAI: Safety best practices"
