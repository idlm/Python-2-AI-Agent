# 模块 12 研究笔记：框架对照、持久化与生产边界

**核对日期：** 2026-08-26（GMT+8）  
**用途：** 为模块 12 的框架对照教学建立一手资料依据。本文只记录稳定设计结论；不把框架文档示例当作默认生产配置或安全认证。

## 一手资料与可教学结论

| 主题 | 一手资料结论 | 教材设计结论 |
|---|---|---|
| 框架定位 | LangGraph 将自身定位为长运行、有状态 Agent 的低层编排框架/运行时，可混合确定性步骤与 LLM 驱动步骤。[1] | Agent 不是 LangGraph；框架不定义业务权限、Schema、工具允许列表或风险接受线。先画合同，再决定是否采用图运行时。 |
| 持久化 | LangGraph 区分短期、线程范围状态 checkpoint 与跨线程 store；内存保存器会在进程重启后丢失状态，生产需采用持久保存器，并需要控制 checkpoint 增长。[2] | 持久化不是可靠性魔法。必须定义 thread/任务身份、版本、保留期限、删除、加密/访问控制、恢复语义、幂等与失败测试。 |
| 中断与恢复 | `interrupt()` 暂停图并依赖 checkpoint 保存状态；恢复必须使用相同 `thread_id`。恢复时含中断的节点会从节点开头重放，因此中断前代码会再次运行。[3] | 将副作用放在经验证审批之后；中断前不能有不可重放、非幂等动作。审批恢复值本身仍应通过应用 Schema、身份与权限验证。 |
| 人工审批 | LangGraph 可在节点或工具附近暂停并让调用方批准、编辑或取消；其示例仍要求开发者实现实际工具和流程。[3] | “有 interrupt”不等于已安全审批。审批负载最小化、审批人身份、资源范围、过期/撤销、审计、幂等键和执行前再验证必须由应用定义。 |
| 提示注入与工具 | OpenAI 将提示注入描述为不可信文本试图改变行为、泄露数据或诱导下游工具调用；建议使用结构化输出、避免把不可信变量置入高优先级指令、保持工具批准、执行评测。[4] | 不可信文本仅是数据。模型候选、框架状态和恢复 payload 都不能绕过枚举、字段闭集、授权、预算、来源、人工批准或工具包装器。 |
| 评测与追踪 | OpenAI 建议评测与 trace graders 检查决策、工具调用或推理步骤以发现错误；LangGraph 将可观察性作为运行时生态能力。[1] [4] | 追踪不是自动合规。先定义最小事件、脱敏、用途、访问、保留与删除；离线回放和负向案例是上线之前的基础门禁。 |

## 模块 12 的非目标

模块 12 **不**默认安装 LangGraph，不连接模型、不提供任意工具注册、不连通 MCP、网络、shell、文件、SQL、账户或支付，也不将一次框架演示宣称为生产部署。任何真实副作用必须先具备固定 Schema、最小权限、工具包装器、超时、幂等/重放语义、审批、审计、离线评测和人工发布门禁。

## 参考资料

[1]: https://docs.langchain.com/oss/python/langgraph/overview "LangGraph overview"
[2]: https://docs.langchain.com/oss/python/langgraph/persistence "LangGraph persistence"
[3]: https://docs.langchain.com/oss/python/langgraph/interrupts "LangGraph interrupts"
[4]: https://developers.openai.com/api/docs/guides/agent-builder-safety "OpenAI: Safety in building agents"
