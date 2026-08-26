# 模块 13 研究笔记：多 Agent 协作、委派与权限边界

**核对日期：** 2026-08-26（GMT+8）  
**用途：** 为模块 13 的多 Agent 教学建立一手资料依据。以下是设计约束，不是对真实模型、框架、多 Agent API 或副作用权限的接线说明。

## 一手资料与可教学结论

| 主题 | 一手资料结论 | 教材设计结论 |
|---|---|---|
| 适用性 | OpenAI 将多 Agent 描述为根 Agent 委派可并行子任务、再综合结果的模式；独立有界工作适合并行，而强顺序依赖、共享可变资源或小任务更适合单 Agent。[1] | 先拆解任务依赖图，再增加 Agent。多 Agent 不是性能默认值，不能用来掩盖未定义的状态、预算或权限。 |
| 并发与成本 | OpenAI 说明并发子 Agent 可以缩短独立工作的墙钟时间，但增加 token 使用；Anthropic 报告多 Agent 协调复杂度快速增长，成本也显著上升。[1] [2] | 每个委派必须有上限：子任务数、并发数、步骤/工具/成本预算、截止条件和可取消语义。 |
| 工具权限 | OpenAI 文档指出多 Agent 树中的 Agent 都可访问该请求配置的工具；LangChain 的 supervisor 示例将不同工具按专长分区给 worker。[1] [3] | 绝不能因“子 Agent”自动继承全部工具。工具应按角色和子任务最小授权；监督者与 worker 的权限、输入和输出 Schema 分离。 |
| 委派合同 | Anthropic 指出子 Agent 任务需要目标、输出格式、工具/来源指导与明确边界，否则会重复、遗漏或偏离。[2] | 委派消息必须是字段闭集：委派 ID、父 ID、角色、受控目标摘要、允许工具集合、预算、截止条件、输出 Schema。禁止转发完整高权限提示或不可信正文。 |
| 协调故障 | Anthropic 记录过度生成子 Agent、无尽搜索、重复工作和过度更新等失败；异步协作还带来状态一致性和错误传播问题。[2] | 设计重复检测、结果去重、汇总等待、超时/取消、局部失败类别和“结果未知”状态；不要默认所有 worker 成功。 |
| 注入与数据泄露 | OpenAI 将提示注入与私有数据泄露列为 Agent 风险，建议结构化输出、隔离不可信输入、工具批准和 trace/eval。[4] | Agent 间消息与工具结果同样是不可信数据。任何 Agent 输出都不能改变角色权限、工具目录、预算、审批或高优先级策略。 |
| 评测与可观察性 | Anthropic 强调小规模评测、可观察性和人工测试在多 Agent 系统的协作行为调优中重要；OpenAI 建议 trace graders 与 evals 检查决策和工具调用。[2] [4] | 评测不只看最终答案；还要测委派边界、权限不扩散、重复/漏做、预算、消息字段闭集、故障传播和无正文报告。 |

## 模块 13 的非目标

模块 13 **不**连接真实多 Agent API、模型、网络、MCP、数据库、shell、文件、账户、支付或真实工具。先使用纯数据委派合同和静态夹具证明角色、消息、预算、状态和权限边界；任何后续副作用仍需独立 Schema、最小权限、幂等、审批、审计、评测和 Runbook。

## 参考资料

[1]: https://developers.openai.com/api/docs/guides/responses-multi-agent "OpenAI: Multi-agent"
[2]: https://www.anthropic.com/engineering/multi-agent-research-system "Anthropic: How we built our multi-agent research system"
[3]: https://docs.langchain.com/oss/python/langchain/multi-agent/subagents-personal-assistant "LangChain: Build a personal assistant with subagents"
[4]: https://developers.openai.com/api/docs/guides/agent-builder-safety "OpenAI: Safety in building agents"
