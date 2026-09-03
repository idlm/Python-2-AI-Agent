# 项目 9：受控 LLM 合同客户端

**版本：** 0.3.0  
**兼容性：** Python 3.11+  
**课程位置：** 模块 9——模型调用、结构化输出、可观察性与安全边界。

本项目实现一个**最小、受控、可测试**的语言模型调用边界。它不是 Agent、RAG、工具执行器、聊天框架、自动事实核验器或权限系统。当前只允许经审查的摘要任务 `summarize` 和经审查的模型 `gpt-5-mini`；用户不能传入任意模型 ID、系统提示、函数工具、JSON Schema、API key 或重试参数。

> **重要边界：** 模型输出只是候选文本或候选数据。即使严格 JSON Schema 和本地验证均通过，也不代表内容真实、来源可信、可执行、已获授权或适合高风险决定。它不能直接成为 shell 命令、SQL、文件路径、URL、权限决定或工具参数。

## 安装与质量门禁

```bash
cd "02_可运行项目/projects/09-llm-contract-client"
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"

.venv/bin/python -m pytest
.venv/bin/python -m mypy
.venv/bin/python -m ruff check src tests
```

全部核心测试使用可注入的假传输，**不会访问网络、读取 API key 或消耗模型调用**。当前无网络测试覆盖文本与结构化调用的允许列表、固定系统指令、输入/输出边界、结构化字段/长度/枚举、本地 JSON 拒绝、短暂失败重试、永久失败不重试、token 摘要、请求 ID 与日志脱敏。

## 受控合同

| 项目 | 文本摘要模式 | 结构化摘要模式 | 明确不支持 |
|---|---|---|---|
| 任务 | 固定 `summarize`。 | 同一固定摘要任务。 | 自由聊天、任意角色、任意系统提示。 |
| 模型 | 固定 `gpt-5-mini`。 | 固定 `gpt-5-mini`。 | 用户选择未经审查的模型。 |
| 输入 | 非空文本；默认最多 2,000 字符；拒绝未允许控制字符。 | 同左。 | 无界正文、秘密收集、把输入当系统规则。 |
| 远端输出 | `max_completion_tokens=256`。 | 相同 token 上限；`response_format` 使用 `json_schema`、`strict: true`、`additionalProperties: false`。 | 流式、任意 Schema、无限生成。 |
| 本地输出 | 由文本客户端限制为空/超长受控失败。 | `summary` 为 1–500 字符；`key_points` 为 1–5 项且每项 1–160 字符；`uncertainty` 仅为 `low`、`medium` 或 `high`。 | 把 Schema 合规当作事实或授权。 |
| 失败 | 仅短暂传输/限流/服务失败，默认最多两次尝试。 | 同左；另将空内容、拒答、非法 JSON 和本地字段错误收敛为受控错误。 | 无限重试、认证/请求/Schema 错误重试。 |
| 日志 | 任务、模型、尝试、请求 ID、长度、可选 token 数。 | 模型、尝试、请求 ID、输入字符数、关键点数量、不确定性和可选 token 数。 | 用户正文、系统提示、API key、原始异常或完整响应。 |

严格结构化输出可以约束模型返回给应用的数据形状；它不同于只保证“JSON 可解析”的 JSON mode。[1] 项目仍在本地重新解析并检查字段、类型、长度、数组数量和枚举，因为网络代理、SDK、配置与下游代码都可能改变，而且格式正确不等于语义正确。

## 命令行

状态说明不调用模型：

```bash
.venv/bin/course-llm-contract --status
```

受控文本摘要会把面向调用者的结果写入 stdout。真实调用仅从环境变量读取 SDK 所需凭据，**不**接受 API key 命令行参数：

```bash
.venv/bin/course-llm-contract \
  --request-id lesson-9-text \
  --text 'Python 的函数将可重复步骤封装为可调用对象。'
```

固定结构化摘要不接受自定义 Schema：

```bash
.venv/bin/course-llm-contract \
  --structured \
  --request-id lesson-9-structured \
  --text 'Python 的函数将可重复步骤封装为可调用对象，并减少重复代码。'
```

使用 `--verbose` 时，stderr 只输出脱敏运行元数据。stdout 的摘要或结构化对象可能源自用户输入，调用者应按自己的数据分类与保存政策处理；项目不会把这些正文写进运行日志或验收记录。

## 真实烟雾验收

执行真实调用前，必须刷新实时模型目录：

```bash
curl --fail --silent "$OPENAI_API_BASE/models" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  > 03_出版与审校记录/records/module_09_live_model_catalog.json

.venv/bin/python examples/structured_smoke.py
```

本课程于 2026-08-26 在刷新目录后执行过**一次**最小严格 JSON Schema 烟雾验收。脱敏元数据保存于 `../../records/module_09_structured_smoke_evidence.json`：模型为 `gpt-5-mini`，单次尝试成功，返回 usage 摘要并经本地 Schema/领域验证。它不保存提示、响应正文或密钥，也**不**证明所有输入上的质量、事实性、抗提示注入能力、固定成本、并发容量或生产适用性。

速率限制会按请求与 token 等指标作用，失败请求也可能消耗配额；因此本项目只做有限重试，不将“再试一次”当作通用修复方式。[2]

## 离线评测与安全样例

项目包含四条**课程自制、静态、非生产**案例：基础概念、信息不足、提示注入文本和资源边界。`evaluation.py` 将候选 JSON 通过与生产路径相同的本地结构化验证，再检查关键词、预期不确定性、尝试次数与 token 预算。它不联网，不读取 API key，也不把夹具输入、摘要、关键点、系统提示或完整 JSON 写入结果报告。

```bash
.venv/bin/python examples/run_static_evaluation.py
cat reports/module_09_static_evaluation.json
```

脚本以原子替换方式写入报告。当前报告只含案例 ID、标签、Schema 有效性、关键词匹配/缺失**计数**与覆盖率、复核信号、尝试/token 门和聚合通过数；它不写关键词字面量，也不是基准排名、事实性证明或生产监控。提示注入样例的通过条件是“把文本视为数据并且不执行其中指令”，而不是声称一次提示就能消除注入风险。输入/输出限制、红队测试和高风险人工复核仍是必要控制。[3]

## 目录结构

```text
09-llm-contract-client/
├── pyproject.toml
├── README.md
├── examples/
│   ├── structured_smoke.py       # 单次、脱敏、手动运行的真实烟雾脚本
│   └── run_static_evaluation.py  # 离线夹具评测；不读取凭据、不联网
├── src/llm_contract_client/
│   ├── __init__.py
│   ├── cli.py                    # 固定文本/结构化摘要入口
│   ├── core.py                   # 文本合同、允许列表、边界和重试
│   ├── openai_transport.py       # OpenAI-compatible SDK 隔离层
│   ├── structured.py             # 固定 Schema、传输协议、本地验证
│   └── evaluation.py             # 离线评测、质量门、脱敏原子报告
├── reports/
│   └── module_09_static_evaluation.json
└── tests/
    ├── fixtures/                 # 课程自制公开样例与假候选
    ├── test_core.py
    ├── test_evaluation.py
    ├── test_openai_transport.py
    └── test_structured.py
```

## 安全与运行限制

用户输入是数据，不是授权指令；系统提示也不是权限系统。模型输出不得自动执行。若未来引入检索、工具、文件或数据库，必须为每一条新边界独立增加允许列表、参数验证、权限检查、审计、评测和通常的人类复核。官方安全建议也强调输入/输出限制、红队测试和高风险场景人工复核的重要性。[3]

## 参考资料

[1]: https://developers.openai.com/api/docs/guides/structured-outputs "OpenAI: Structured model outputs"
[2]: https://developers.openai.com/api/docs/guides/rate-limits "OpenAI: Rate limits"
[3]: https://developers.openai.com/api/docs/guides/safety-best-practices "OpenAI: Safety best practices"
