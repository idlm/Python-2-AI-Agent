# 《Python私房课》中英索引

**用途：** 本索引帮助读者从中文概念、英文术语或工程主题反向定位首现章节。它是导航材料，不替代正文定义、测试、项目 README 或安全边界。

> **阅读约定：** “首现”指首次系统解释该概念的章节；概念在后续模块可能被扩展。涉及模型、框架、工具、秘密、网络、部署或副作用时，应优先阅读模块 9–15 的边界说明，而不是仅从术语名称推断能力。

## A–D

| 中文 | English | 首现 | 相关主题 |
|---|---|---|---|
| 行动候选 | Action Candidate | 11.1 | 模型或规划器提出、尚未获授权的下一步。 |
| 允许列表 | Allowlist | 4.4 | 明确允许、默认拒绝。 |
| 应用生命周期 | Application Lifespan | 8.3 | 初始化、接收请求、停止与清理。 |
| 原子替换 | Atomic Replacement | 5.5 | 临时写入后单次替换。 |
| 备份 | Backup | 5.5、15.3 | 从局部旧文件到恢复范围的不同层次。 |
| 基线 | Baseline | 14.1 | 版本化评测比较基准。 |
| 断点快照 | Checkpoint | 12.2 | 受控恢复状态，不是完整备份。 |
| 命令行接口 | Command-Line Interface, CLI | 1.8、5.2 | 稳定输入/输出/退出码合同。 |
| 闭包 | Closure | 2.3 | 函数返回后仍引用外部名称。 |
| 组合优先 | Composition over Inheritance | 4.2 | 用协作对象替代深继承链。 |
| 上下文管理器 | Context Manager | 4.3 | `with` 管理进入、退出和清理。 |
| 协程 | Coroutine | 6.4 | `async def` 定义的可等待单元。 |
| 覆盖率 | Coverage | 5.2 | 执行覆盖度指标，不等同于质量证明。 |
| 数据类 | Data Class | 4.1 | 用于承载结构化数据的类工具。 |
| 数据最小化 | Data Minimization | 5.4、11.2 | 只保存任务所必需字段。 |
| 委派 | Delegation | 13.1 | 有界子任务分配，不等于授权。 |
| 依赖注入 | Dependency Injection, DI | 6.2 | 从组合根显式提供依赖。 |
| Dry Run | Dry Run | 3.2 | 只规划/报告，不产生状态改变。 |

## E–L

| 中文 | English | 首现 | 相关主题 |
|---|---|---|---|
| 嵌入 | Embedding | 10.1 | 文本的数值向量表示；项目中仅用教学替身。 |
| 环境 | Environment | 5.1、15.1 | 隔离运行环境或部署配置环境，需上下文区分。 |
| 评测任务 | Evaluation Task | 14.1 | 固定输入、成功条件和评分逻辑的案例。 |
| 失败传播 | Failure Propagation | 6.4、13.2 | 相关任务失败后的受控收尾语义。 |
| 有限状态机 | Finite-State Machine, FSM | 8.1 | 有限状态与允许转换模型。 |
| 框架 | Framework | 6.2、12.1 | 编排/路由工具，不构成权限边界。 |
| 生成器 | Generator | 4.3 | 通过 `yield` 逐项产生值。 |
| Grader | Grader | 14.1 | 对结果或过程施加规则的评分逻辑。 |
| 健康检查 | Health Check | 15.2 | 启动、存活、就绪的受控检查集合。 |
| 幂等 | Idempotence | 7.1 | 重复执行的目标状态等价性。 |
| 幂等键 | Idempotency Key | 8.1、12.2 | 定义重试语义的受控标识。 |
| 事件循环 | Event Loop | 6.4 | 调度协程和回调的运行机制。 |
| 输入 Schema | Input Schema | 6.1 | 对可接受字段、类型与边界的声明。 |
| 索引 | Index | 10.1 | 用于候选查找的受控结构。 |
| 反压 | Backpressure | 8.2 | 将容量压力传回生产者。 |
| JSON Lines | JSONL | 7.3 | 每行独立 JSON 值的记录格式。 |

## M–P

| 中文 | English | 首现 | 相关主题 |
|---|---|---|---|
| 清单 | Manifest | 3.4、7.3 | 版本、计数、标识等派生摘要。 |
| 最小评测报告 | Minimal Evaluation Report | 11.4 | 不含正文的公开评测摘要。 |
| 最小权限 | Least Privilege | 4.4、11.3、15.1 | 仅授予任务所需的最少能力。 |
| 模型拒答 | Model Refusal | 9.2 | 供应商或模型明确拒绝生成。 |
| 多 Agent | Multi-Agent | 13.1 | 多个受限角色之间的协作合同。 |
| 未运行 | Not Run | 14.3 | 未获得受控结果，不能当作通过。 |
| 结果未知 | Outcome Unknown | 13.2、15.2 | 不能断言外部动作是否完成。 |
| 输出 Schema | Output Schema | 6.1 | 对返回字段、类型与结构的承诺。 |
| 公开视图 | Public View | 8.1 | 为 API/CLI 筛选后的内部对象视图。 |
| 纯工具 | Pure Tool | 11.1 | 不改变外部状态的固定工具。 |
| 提示注入 | Prompt Injection | 9.3 | 不可信文本试图改变系统行为的风险。 |
| Protocol | Protocol | 4.1 | 结构化接口约定。 |
| 发布门禁 | Release Gate | 14.3 | 进入下一阶段前的可审计决定规则。 |
| 恢复候选 | Recovery Candidate | 8.1 | 中断后需受控判断的工作摘要。 |
| 恢复点目标 | Recovery Point Objective, RPO | 15.3 | 可接受数据丢失窗口目标。 |
| 恢复时间目标 | Recovery Time Objective, RTO | 15.3 | 恢复到可接受状态的时间目标。 |
| 回归测试 | Regression Test | 5.5 | 验证变更没有破坏既有合同。 |
| 检索增强生成 | Retrieval-Augmented Generation, RAG | 10.1 | 先检索受控语料，再形成候选回答。 |
| Runbook | Operational Runbook | 15.4 | 面向运行、暂停、恢复、升级和复盘的步骤合同。 |

## S–Z

| 中文 | English | 首现 | 相关主题 |
|---|---|---|---|
| 安全标识 | Safety Identifier | 9.1 | 隐私保护的端用户关联标识。 |
| Schema | Schema | 6.1、9.2 | 描述结构、字段、类型和边界的合同。 |
| 秘密元数据 | Secret Metadata | 15.1 | 无秘密值的用途、状态、环境与轮换信息。 |
| 结构化并发 | Structured Concurrency | 6.4 | 共同作用域内的等待、取消与收尾。 |
| 结构化输出 | Structured Output | 9.2 | 按预定义形状返回候选数据。 |
| 步骤预算 | Step Budget | 11.1 | 单次 Agent 任务的最大步骤数。 |
| 停止原因 | Stop Reason | 11.3 | 受控停止枚举，而非任意异常文本。 |
| 测试替身 | Test Double | 5.2、10.1 | 用受控实现替代真实依赖。 |
| 线程标识 | Thread Identifier | 12.2 | 定位受控持久化运行状态的标识。 |
| 工具调用预算 | Tool-Call Budget | 11.3 | 单任务最大工具调用次数。 |
| 工具包装器 | Tool Wrapper | 12.3 | 执行前重新验证权限、预算等的应用层组件。 |
| Traceback | Traceback | 0.2 | Python 未处理异常的调用路径信息。 |
| Trial | Trial | 14.1 | 一个评测任务上的一次独立尝试。 |
| 版本基线 | Versioned Baseline | 14.1 | 经过审查、用于候选比较的版本化结果。 |
| 向量索引 | Vector Index | 10.1 | 按向量相关性返回候选的索引结构。 |
| 工作流 | Workflow | 11.1 | 由应用预定义步骤与分支的过程。 |

## 常见混用快速纠正

| 容易混用的表达 | 正确区分 |
|---|---|
| Agent = LLM = LangChain/LangGraph | LLM 生成候选；Agent 是受控多步系统；框架只提供编排能力。 |
| JSON 可解析 = 输出安全 | JSON、JSON Schema、领域验证、来源验证、权限验证与事实验证是不同层。 |
| 评测通过 = 可以发布 | 评测是发布门禁的输入；还需未运行、隐私、恢复、责任、Runbook 和风险审查。 |
| 备份存在 = 可以恢复 | 还需要范围、兼容性、访问、验证、演练、RPO/RTO 与结果未知对账。 |
| CI 绿灯 = 生产就绪 | CI 只覆盖部分工程门禁；不证明配置、秘密、网络、容量、恢复、值班或真实副作用安全。 |
| 默认无执行 = 生产安全 | 这是教学边界；真实部署仍需独立威胁模型、平台审查和用户批准。 |

## 完整术语补充导航

下表补齐中英索引的长尾术语。定义、禁止混用和完整上下文仍以 `records/glossary.md` 为准；本表仅提供从中文术语到英文名称和首现章节的反向定位。

| 中文术语 | English / 缩写 | 首现章节 |
|---|---|---|
| 毕业作品 | Capstone Project | 0.1 |
| 程序 | Program | 0.2 |
| 源代码 | Source Code | 0.2 |
| 解释器 | Interpreter | 0.2 |
| 终端 | Terminal | 0.2 |
| 命令行解释器 | Shell | 0.2 |
| 当前工作目录 | Current Working Directory，CWD | 0.2 |
| 变量名 | Variable Name | 1.2 |
| 可变对象 | Mutable Object | 1.2 |
| 不可变对象 | Immutable Object | 1.2 |
| 条件分支 | Conditional Branch | 1.5 |
| 迭代 | Iteration | 1.6 |
| 类型注解 | Type Annotation | 2.4 |
| 路径遍历 | Path Traversal | 3.1 |
| 操作清单 | Operation Manifest | 3.4 |
| 协议 | Protocol | 4.1 |
| 装饰器 | Decorator | 4.3 |
| 插件注册表 | Plugin Registry | 4.4 |
| 动态导入 | Dynamic Import | 4.4 |
| 虚拟环境 | Virtual Environment，venv | 5.1 |
| 项目元数据 | Project Metadata | 5.1 |
| 可复现运行 | Reproducible Execution | 5.1 |
| 持续集成 | Continuous Integration，CI | 5.1 |
| `src` 布局 | `src` Layout | 5.1 |
| 可编辑安装 | Editable Install | 5.2 |
| 薄兼容层 | Thin Compatibility Layer | 5.5 |
| 质量门禁 | Quality Gate | 5.5 |
| 备份文件 | Backup File | 5.5 |
| 故障复盘 | Incident Postmortem | 5.5 |
| HTTP 合同 | HTTP Contract | 6.1 |
| 资源 | Resource | 6.1 |
| 请求模式 | Request Schema | 6.1 |
| 响应模式 | Response Schema | 6.1 |
| 状态码 | HTTP Status Code | 6.1 |
| 请求 ID | Request ID | 6.2 |
| 仓储 | Repository | 6.3 |
| 数据库事务 | Database Transaction | 6.3 |
| 参数化查询 | Parameterized Query | 6.3 |
| 任务组 | Task Group，`TaskGroup` | 6.4 |
| 超时 | Timeout | 6.4 |
| HTTP 客户端 | HTTP Client | 7.1 |
| 连接池 | Connection Pool | 7.1 |
| 连接超时 | Connect Timeout | 7.1 |
| 读取超时 | Read Timeout | 7.1 |
| 连接池超时 | Pool Timeout | 7.1 |
| 重试策略 | Retry Policy | 7.1 |
| robots 规则 | robots.txt Rules | 7.2 |
| 信号量 | Semaphore | 7.2 |
| 请求节奏器 | Request Pacer | 7.2 |
| 内容去重 | Content Deduplication | 7.3 |
| 显式恢复 | Explicit Recovery | 7.3 |
| 服务工作流 | Service Workflow | 8.1 |
| 进程内队列 | In-Process Queue | 8.2 |
| Worker | Worker | 8.2 |
| Drain | Drain | 8.2 |
| `202 Accepted` | HTTP 202 Accepted | 8.3 |
| 后台任务 | Background Task | 8.3 |
| 大语言模型 | Large Language Model，LLM | 9.1 |
| Token | Token | 9.1 |
| 系统提示 | System Prompt | 9.1 |
| 本地重复验证 | Local Redundant Validation | 9.2 |
| 幻觉 | Hallucination | 9.2 |
| 静态评测夹具 | Static Evaluation Fixture | 9.3 |
| 模型质量评测 | Model Quality Evaluation | 9.3 |
| 烟雾测试 | Smoke Test | 9.1 |
| 人工复核 | Human Review | 9.3 |
| 切块 | Chunking | 10.1 |
| 重叠 | Overlap | 10.1 |
| 余弦相似度 | Cosine Similarity | 10.1 |
| 检索结果 | Retrieval Result | 10.1 |
| 来源链 | Provenance Chain | 10.1 |
| 检索召回 | Retrieval Recall | 10.2 |
| 检索精度 | Retrieval Precision | 10.2 |
| 证据阈值 | Evidence Threshold | 10.2 |
| 证据不足 | Not Enough Evidence | 10.2 |
| 来源约束回答 | Source-Bound Answer | 10.3 |
| 引用白名单 | Citation Allowlist | 10.3 |
| 审批暂停 | Approval Pause | 11.1 |
| Agent 运行事件 | Agent Run Event | 11.1 |
| 字段闭集 | Closed Field Set | 11.4 |
| 人工复核记录 | Human Review Record | 11.4 |
| 图编排 | Graph Orchestration | 12.1 |
| 重放 | Replay | 12.2 |
| 执行前再验证 | Pre-Execution Revalidation | 12.3 |
| 角色策略 | Role Policy | 13.1 |
| 权限不扩散 | Non-propagation of Privilege | 13.1 |
| 委派去重键 | Delegation Deduplication Key | 13.2 |
| 委派状态机 | Delegation State Machine | 13.2 |
| 稳定汇总 | Stable Aggregation | 13.3 |
| 过程评分 | Process Grading | 14.2 |
| 硬阻断项 | Hard Release Blocker | 14.3 |
| 影子模式 | Shadow Mode | 14.3 |
| 部署 Profile | Deployment Profile | 15.1 |
| 启动检查 | Startup Check | 15.2 |
| 存活检查 | Liveness Check | 15.2 |
| 就绪检查 | Readiness Check | 15.2 |
| Drain | Drain | 15.2 |
| 恢复演练 | Recovery Drill | 15.3 |
| 破窗 | Break-glass Access | 15.3 |
| 运维 Runbook | Operational Runbook | 15.4 |
| 运行准备门禁 | Operational Readiness Gate | 15.4 |
