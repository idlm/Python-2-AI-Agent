# 模块 14 研究笔记：Agent 评测、追踪与发布门禁

**核对日期：** 2026-08-26（GMT+8）  
**用途：** 为模块 14 的离线评测、最小可观察性、人工复核、发布与回滚教学提供一手资料依据。以下为设计约束，不是对真实追踪、模型、外部评测平台或生产部署的接线说明。

## 一手资料与可教学结论

| 主题 | 一手资料结论 | 教材设计结论 |
|---|---|---|
| Trace 与调试 | OpenAI 将 trace 定义为一次运行中模型调用、工具调用、guardrail 与 handoff 的端到端记录；trace grading 可按结构化条件发现工作流级问题。[1] [2] | 先用最小事件/状态摘要和离线夹具验证不变量；生产 trace 不能默认记录提示、正文、原始响应或密钥。 |
| 可重复评测 | OpenAI 建议在理解“好”的行为后，以数据集和 eval run 做可重复基准、提示比较和长期回归。[1] | 为每个合同保留版本化静态案例、固定 grader、公开最小报告与明确基线；不要把单次烟雾或演示当质量证明。 |
| 过程与结果 | Anthropic 将 trial、grader、transcript/trace、outcome、evaluation harness 和 agent harness 分开定义；Agent 需要同时考察过程与最终环境状态。[4] | 课程要分开评估候选/状态/工具调用路径（过程）和公开结果类别（结果）；一段最终文本不是全面成功证明。 |
| Grader 组合 | Anthropic 归纳代码型、模型型和人工型 grader：代码型快速可复现但可能脆弱；模型型灵活但需校准；人工型更贴近专家判断但成本高。[4] | 优先建立确定性离线不变量与 Schema/状态测试；开放性质量才考虑受控模型 rubric，且需人工校准与数据治理。 |
| 能力与回归 | Anthropic 区分 capability eval（探索当前能力、允许较低初始通过率）与 regression eval（保护既有行为、应接近满通过）。[4] | 明确区分实验案例与发布阻断案例；能力提升不能牺牲已验证安全/权限/隐私不变量。 |
| 非确定性 | Anthropic 提醒 Agent 行为跨 trial 变化，pass@k 与 pass^k 回答不同可靠性问题。[4] | 不混用“至少一次成功”与“每次稳定成功”；风险高的用户路径应定义一致性要求、次数、阈值和人工复核。 |
| 提示注入与数据泄露 | OpenAI 将注入、私有数据泄露、工具风险列为持续威胁，建议结构化输出、隔离、批准和 trace/eval 组合，而非单一防线。[3] | 安全负向案例必须进入回归集；不可信文本永远作为数据，且评测/追踪报告也实行数据最小化。 |
| 发布与回滚 | Anthropic 指出评测能在用户受影响前发现退化，版本化基线与持续回归支持模型、提示、工具或编排升级的比较。[4] | 每次变更应有版本、差异报告、门禁、暂停/回滚条件、责任人和 Runbook；通过率不代表可自动扩大权限。 |

## 模块 14 的非目标

模块 14 **不**调用模型、追踪平台、外部评测 API、网络、MCP、数据库、shell、账户、支付或真实工具。先实现离线案例字段闭集、基线比较、确定性门禁、最小公开报告与人工复核模板。任何生产 trace、模型 grader、真实工具或部署都需独立的隐私、权限、保留、成本、批准、审计、评测和事件响应设计。

## 参考资料

[1]: https://developers.openai.com/api/docs/guides/agent-evals "OpenAI: Evaluate agent workflows"
[2]: https://developers.openai.com/api/docs/guides/trace-grading "OpenAI: Trace grading"
[3]: https://developers.openai.com/api/docs/guides/agent-builder-safety "OpenAI: Safety in building agents"
[4]: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents "Anthropic: Demystifying evals for AI agents"
