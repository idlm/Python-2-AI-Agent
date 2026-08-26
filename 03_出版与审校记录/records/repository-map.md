# 教材仓库映射

**权威状态更新：** 2026-08-26（GMT+8）

| 路径 / 模式 | 用途 | 当前状态 | 关联模块 |
|---|---|---|---|
| `chapters/module_00_chapter_0_1.md`–`module_00_chapter_0_4.md` | 学习路线、运行环境、Traceback、可复现练习正文。 | 出版结构/练习/引用复核通过；四章各有 25 节、完整练习配额与官方参考资料。 | 0 |
| `chapters/module_01_chapter_1_1.md`–`module_01_chapter_1_8.md` | Python 语法、控制流、数据结构和输入输出正文。 | 出版结构/练习/引用复核通过；八章各有 25 节、完整练习配额与官方参考资料。 | 1 |
| `chapters/module_02_chapter_2_1.md`–`module_02_chapter_2_5.md` | 函数、作用域、类型注解和文本分析工具正文。 | 出版结构/练习/引用复核通过；五章各有 25 节、完整练习配额与官方参考资料。 | 2 |
| `chapters/module_03_chapter_3_1.md`–`module_03_chapter_3_4.md` | 文件、路径、结构化数据、日志与异常正文。 | 出版结构/练习/引用复核通过；四章各有 25 节、完整练习配额与官方参考资料。 | 3 |
| `chapters/module_04_chapter_4_1.md`–`module_04_chapter_4_4.md` | 类、组合、Python 机制、插件配置和安全加载正文。 | 出版项目映射复核通过；四章各有 25 节、完整练习配额、项目/示例路径、可运行命令、边界提示与参考资料。 | 4 |
| `chapters/module_05_chapter_5_1.md` | 虚拟环境、项目根目录、`src` 布局、可复现运行与最小 `pyproject.toml` 正文。 | 出版映射复核通过；25 节、References、项目路径和可运行验证命令已核验。 | 5.1 |
| `chapters/module_05_chapter_5_2.md` | 项目元数据、依赖、脚本入口、pytest、mypy、Ruff 与 CI 正文。 | 出版映射复核通过；25 节、References、项目路径和可运行验证命令已核验。 | 5.2 |
| `chapters/module_05_chapter_5_3.md` | Git 快照、暂存区、提交边界、忽略规则、分支和 CI 协作正文。 | 出版映射复核通过；25 节、完整练习配额、References、项目路径和可运行验证命令已核验。 | 5.3 |
| `chapters/module_05_chapter_5_4.md` | 配置优先级、TOML、环境变量、日志职责、脱敏和错误边界正文。 | 出版映射复核通过；25 节、References、项目路径和可运行验证命令已核验。 | 5.4 |
| `chapters/module_05_chapter_5_5.md` | 遗留脚本迁移、`src` 布局、兼容层、回归、CI、依赖升级与故障复盘正文。 | 出版映射复核通过；25 节、References、项目路径和可运行验证命令已核验。 | 5.5 |
| `chapters/module_06_chapter_6_1.md`–`module_06_chapter_6_4.md` | HTTP/API 合同、FastAPI、SQLite 事务与 asyncio 可靠性正文。 | 出版映射复核通过；四章各有 25 节、练习配额、可运行项目命令和官方参考资料。 | 6 |
| `chapters/module_07_chapter_7_1.md`–`module_07_chapter_7_3.md` | 受控 HTTP 客户端、礼貌并发采集与 JSONL 记录/恢复正文。 | 出版映射复核通过；三章各有 25 节、练习配额、项目路径/命令和官方参考资料。 | 7 |
| `chapters/module_08_chapter_8_1.md`–`module_08_chapter_8_3.md` | 服务工作流状态机、有界队列/worker 与 FastAPI 生命周期/恢复正文。 | 出版映射复核通过；三章各有 25 节、练习配额、项目路径/命令和官方参考资料。 | 8 |
| `chapters/module_09_chapter_9_1.md`–`module_09_chapter_9_3.md` | 无框架最小 LLM 客户端、严格结构化输出、本地验证、离线评测、提示注入与人工复核正文。 | 出版映射复核通过；三章均有 25 节、References、仅离线项目命令、主题化扩展和真实能力边界。 | 9 |
| `chapters/module_10_chapter_10_1.md`–`module_10_chapter_10_4.md` | 受控 RAG 语料/切块/索引、检索评测/来源质量、来源约束回答与回答支持度评测正文。 | 出版映射复核通过；四章均有 25 节、References、仅离线项目命令、主题化扩展和真实能力边界。 | 10 |
| `examples/module_00/` | 模块 0 可运行示例：逆向设计、运行快照、Traceback 实验、学习记录。 | 已运行，受 7 项测试覆盖。 | 0 |
| `examples/module_01/repl_and_names.py` | 名称绑定与交互式运行示例。 | 已运行，受对应测试覆盖。 | 1 |
| `examples/module_04/decorator_basics.py` | 装饰器保留返回值和函数元数据的可运行示例。 | 已运行，受模块 4 测试覆盖。 | 4.3 |
| `examples/module_04/generator_basics.py` | 生成器逐项消费与状态前进的可运行示例。 | 已运行，受模块 4 测试覆盖。 | 4.3 |
| `examples/module_04/context_manager_basics.py` | `with` 资源关闭与异常传播的可运行示例。 | 已运行，受模块 4 测试覆盖。 | 4.3 |
| `examples/module_05/environment_check.py` | 当前解释器、Python 版本和工作目录的诊断示例。 | 已运行，受模块 5 测试覆盖。 | 5.1 |
| `examples/module_06/http_contract.py` | 框架无关的 HTTP 资源、方法、Schema、状态码、错误与日志边界示例。 | 已运行，受 8 项模块 6 测试覆盖。 | 6.1 |
| `examples/module_06/async_reliability.py` | TaskGroup、超时、取消、清理、失败传播与日志最小化示例。 | 已运行，受 7 项模块 6 异步测试覆盖。 | 6.4 |
| `tests/module_00/` | 模块 0 `unittest`。 | 7 项通过。 | 0 |
| `tests/module_01/test_repl_and_names.py` | 模块 1 名称绑定测试。 | 已通过。 | 1 |
| `tests/module_02/test_text_analyzer.py` | 文本分析工具测试；通过动态模块加载导入历史连字符文件名。 | 3 项通过；模块 5 迁移。 | 2 |
| `tests/module_04/test_python_mechanisms.py` | 装饰器、生成器和上下文管理器示例测试。 | 4 项通过。 | 4.3 |
| `tests/module_05/test_environment_check.py` | 环境快照示例测试。 | 2 项通过。 | 5.1 |
| `tests/module_06/test_http_contract.py` 与 `test_async_reliability.py` | HTTP 合同与 asyncio 可靠性示例测试。 | 共 15 项 `unittest` 通过。 | 6.1、6.4 |
| `projects/01-task-manager/` | `task_manager` 标准包、CRUD CLI、固定 JSON、原子替换、备份、删除确认、pytest、mypy、Ruff 与 CI。 | 初步完成；17 项 pytest、静态检查和 CLI 脱敏验收通过。 | 1、5 |
| `projects/02-text-analyzer.py` 与 `projects/02-text-analyzer.README.md` | 文本分析工具的历史最小实现。 | 保留为兼容参考；新标准项目位于 `projects/02-text-analyzer/`。 | 2、5 |
| `projects/02-text-analyzer/` | `text_analyzer` 标准包、显式文本/文件 CLI、JSON、日志、大小限制、pytest、mypy、Ruff 与 CI。 | 初步完成；6 项 pytest 与端到端验收通过。 | 2、5 |
| `projects/03-auto-archive/` | `auto_archive` 标准包、默认 Dry Run、显式移动、清单、回滚、CLI、薄兼容层、pytest、mypy、Ruff 与 CI。 | 初步完成；7 项 pytest 与端到端安全验收通过。 | 3、5 |
| `projects/04-plugin-system/src/safe_plugin_system/` | `safe_plugin_system` 标准包：Protocol、冻结数据类、允许列表注册表、配置校验、装饰器、生成器、审计与 CLI。 | 初步完成；15 项 pytest、mypy、Ruff 与端到端验收通过。 | 4、5 |
| `projects/04-plugin-system/src/plugins.py` 与 `src/cli.py` | 旧教材导入和直接执行路径的薄兼容层，仅重导出或委托标准包。 | 已验证；不含第二套业务逻辑。 | 4、5 |
| `projects/04-plugin-system/examples/plugins.json` | 仅含内置允许类型的示例配置。 | 已验证。 | 4.4 |
| `projects/04-plugin-system/tests/test_plugins.py` 与 `tests/test_cli.py` | 插件系统单元、安全与 CLI 端到端测试。 | 15 项 pytest 通过；兼容入口和安装命令均被覆盖。 | 4、5 |
| `projects/04-plugin-system/README.md` | 运行说明、威胁边界、配置契约、审计限制与参考资料。 | 已完成。 | 4 |
| `projects/05-cli-tool-platform/` | 标准 `src` 布局、`pyproject.toml`、CLI、受控 TOML 设置、日志、pytest、mypy、Ruff、README 与 `.gitignore`。 | 在新 `.venv` 中可编辑安装后，命令行、配置测试、mypy 和 Ruff 均已通过。 | 5 |
| `projects/05-cli-tool-platform/.github/workflows/quality.yml` | Python 3.11/3.12 的安装、测试、类型检查与静态检查 CI。 | 已写入，等待远程仓库触发。 | 5 |
| `projects/06-knowledge-api/` | `knowledge_api` 标准包：FastAPI 模型、固定路径、请求 ID、公开错误、SQLite 仓储、参数化查询、事务、备份恢复、pytest、mypy、Ruff 与 CI。 | v0.2.0；17 项 pytest、跨重启 HTTP 持久化验收与静态门禁通过。 | 6.2、6.3 |
| `projects/07-polite-api-collector/` | `polite_api_collector` 标准包：HTTPS/主机允许列表、GET JSON、超时、连接池、有限重试、robots、Semaphore、Pacer、TaskGroup、固定 JSONL、去重、清单恢复、CLI、pytest、mypy、Ruff 与 CI。 | v0.1.0；28 项 pytest、CLI 协议拒绝与 JSONL 写入/去重/恢复端到端验收通过。 | 7.1–7.3 |
| `projects/07-polite-api-collector/examples/store_demo.py` | 无网络 JSONL 写入、重复跳过、跨实例读取、清单丢失与显式恢复示例。 | 已运行；只输出计数与文件存在性摘要，不输出 payload。 | 7.3 |
| `projects/08-workflow-service/` | `workflow_service` 标准包：允许列表状态机、幂等、有界 Queue、TaskGroup、超时、取消、FastAPI lifespan、202 API、请求 ID、受控错误、回环 CLI、pytest、mypy、Ruff 与 CI。 | v0.1.0；25 项 pytest、真实本地 API 验收与静态门禁通过。 | 8.1–8.3 |
| `projects/08-workflow-service/src/workflow_service/core.py` | 框架无关任务状态机、公开视图、幂等、合法迁移与恢复候选。 | 10 项核心测试覆盖。 | 8.1 |
| `projects/08-workflow-service/src/workflow_service/worker.py` | 有界进程内队列、反压、固定 handler、TaskGroup、超时、取消和 drain。 | 9 项异步工作器测试覆盖。 | 8.2 |
| `projects/08-workflow-service/src/workflow_service/api.py` | FastAPI lifespan、202 接受、查询/取消、请求 ID 与统一公开错误。 | 6 项 API/生命周期测试和回环 HTTP 验收覆盖。 | 8.3 |
| `projects/09-llm-contract-client/` | `src` 布局的受控 LLM 合同客户端：固定模型/任务、OpenAI-compatible 传输隔离、严格 JSON Schema、本地重复验证、有限重试、脱敏 CLI、离线评测、README、`.gitignore` 与 Python 3.11/3.12 CI。 | v0.3.0；33 项无网络 pytest、mypy、Ruff、离线 4/4 夹具评测、CLI 状态路径与一次脱敏真实结构化烟雾验收通过。 | 9.1–9.3 |
| `projects/09-llm-contract-client/src/llm_contract_client/structured.py` | 固定摘要 JSON Schema、结构化传输 Protocol、本地领域验证、有限重试与脱敏日志。 | 覆盖额外字段、长度、枚举、拒答、空内容和重试边界。 | 9.2 |
| `projects/09-llm-contract-client/src/llm_contract_client/evaluation.py` | 离线夹具加载、生产路径 Schema 复用、关键词计数/覆盖率、复核/预算质量门及原子无正文报告。 | 无网络；报告只含 ID、标签、计数/覆盖率和门结果。 | 9.3 |
| `projects/09-llm-contract-client/tests/fixtures/` | 课程自制公开评测案例与假结构化候选。 | 四条可复现的正常、信息不足、提示注入和资源边界样例；非生产数据。 | 9.3 |
| `projects/09-llm-contract-client/examples/structured_smoke.py` 与 `run_static_evaluation.py` | 明确单次的脱敏真实 JSON Schema 烟雾脚本，以及无凭据/无网络静态评测脚本。 | 前者不保存正文；后者写可再生无正文报告。 | 9.2、9.3 |
| `projects/10-rag-contract-workbench/` | `src` 布局的受控 RAG 合同工作台：公开语料合同、稳定切块、教学哈希嵌入、内存余弦索引、有限检索、来源、静态评测、来源约束回答、固定模型严格 JSON 适配器、README、`.gitignore` 与 Python 3.11/3.12 CI。 | v0.5.0；37 项无网络 pytest、mypy、Ruff、CLI 状态、4/4 公开静态检索评测、离线回答支持度评测、索引清除/重建边界与一次脱敏真实来源约束回答烟雾通过；真实 embedding 未接入。 | 10.1–10.4 |
| `projects/10-rag-contract-workbench/src/rag_contract_workbench/core.py` | `CourseDocument`、`Chunk`、测试嵌入 Protocol/替身、原子内存索引、余弦检索、来源、受控清除/重建边界与无正文日志。 | 覆盖语料/查询预算、维度、稳定排序、阈值、空结果、注入文本作为数据、清除后查询失败与错误 collection 保留快照。 | 10.1 |
| `projects/10-rag-contract-workbench/src/rag_contract_workbench/evaluation.py` | 静态检索案例、来源级召回/精度、来源完整性和原子无正文报告。 | 评测复用生产检索路径，不持久化查询或块正文。 | 10.2 |
| `projects/10-rag-contract-workbench/src/rag_contract_workbench/answer_evaluation.py` | 离线回答支持度夹具、状态/引用/术语计数/人工复核质量门及原子无正文报告。 | 只评估已定义公开夹具合同，不认证事实或来源权威。 | 10.4 |
| `projects/10-rag-contract-workbench/src/rag_contract_workbench/answering.py` | 来源约束回答 Protocol、本地无证据拒答、严格候选 JSON 和实际检索块引用白名单。 | 不提供事实认证或工具执行。 |
| `projects/10-rag-contract-workbench/src/rag_contract_workbench/openai_answer_transport.py` | 固定 `gpt-5-mini` 的 OpenAI-compatible 严格 JSON 回答适配器、输出预算与受控 SDK 失败映射。 | 不实现真实 embedding、自由模型选择、工具或自动重试策略。 |
| `projects/10-rag-contract-workbench/examples/source_bound_answer_smoke.py` | 单次公开教学文本的真实来源约束回答烟雾脚本。 | 只输出状态、引用元数据、长度与索引版本；不输出或落盘正文、提示、原始响应或密钥。 | 10.3 |
| `projects/10-rag-contract-workbench/examples/clear_and_rebuild_demo.py` | 无网络内存索引清除、版本返回与重建示例。 | 只输出版本关系、文档计数与状态；不输出正文、查询、向量、提示或凭据。 | 10 维护 |
| `projects/10-rag-contract-workbench/tests/fixtures/retrieval_evaluation.json` 与 `examples/run_static_retrieval_evaluation.py` | 课程自制公开检索夹具和离线评测脚本。 | 4 条来源/空结果/注入案例；可再生报告仅保存 ID、标签、计数和指标。 | 10.2 |
| `records/progress.md` | 章节权威进度和技术债。 | 已清理并同步。 | 全书 |
| `records/project-status.md` | 项目权威状态与验收边界。 | 已清理并同步。 | 全书 |
| `records/module_07_research_notes.md` | HTTPX、robots、Semaphore、JSON、路径与文件替换的模块 7 官方资料核对。 | 已完成并供 7.1–7.3 引用。 | 7 |
| `records/module_08_research_notes.md` | FastAPI 后台任务/生命周期、asyncio Queue、TaskGroup、取消与超时的模块 8 官方资料核对。 | 已完成并供 8.1–8.3 引用。 | 8 |
| `records/module_09_research_notes.md` 与 `module_09_live_model_catalog.json` | 模块 9 的结构化输出、速率限制、安全资料核对及每次真实调用前刷新使用的实时模型目录。 | 已完成；目录会变化，不作为永久模型/价格承诺。 | 9 |
| `records/module_09_structured_smoke_evidence.json` | 单次真实严格 JSON Schema 烟雾验收的脱敏元数据。 | 不含 prompt、响应正文或密钥；不是质量/安全/容量证明。 | 9.2 |
| `records/module_09_full_regression.log` | 模块 0–9 unittest/pytest 与项目 1–9 mypy/Ruff 的逐范围回归日志。 | 当前 189 项测试与全部静态门禁通过；含项目 6、8 已知第三方 warning。 | 9 |
| `records/module_10_research_notes.md` 与 `module_10_live_model_catalog.json` | 嵌入、检索、切块、来源、评测、提示注入和数据安全的一手资料与实时模型目录核对。 | 目录确认严格 JSON 聊天能力，但未列出 embedding 模型/能力；真实 embedding 未接入。 | 10 |
| `records/module_11_research_notes.md` | Agent/workflow 区别、状态、受控工具、审批、追踪、评测与提示注入安全的一手资料核对。 | 已完成，供模块 11 无框架实现与正文引用。 | 11 |
| `records/module_10_source_bound_answer_smoke_evidence.json` | 单次真实来源约束回答烟雾验收的脱敏元数据。 | 不含问题、来源、回答、提示或密钥；不构成质量、安全、容量或事实证明。 | 10 |
| `chapters/module_11_chapter_11_1.md`–`module_11_chapter_11_4.md` | Agent/workflow 边界、有限状态、固定纯工具、相互独立预算、审批、事件、候选授权、离线评测、最小报告与人工复核正文。 | 当前收束完成；四章各有 25 个固定部分与练习配额。 | 11 |
| `projects/11-bounded-agent-core/` | 无框架受限 Agent 标准项目：有限状态、固定纯工具、独立步骤/工具调用预算、受控停止原因、审批暂停、最小事件、严格静态夹具、固定无正文报告 CLI、人工复核模板、pytest、mypy 与 Ruff。 | v0.2.0；23 项无网络 pytest、mypy、Ruff 通过；不含模型、框架、动态工具或副作用。 | 11 |
| `projects/11-bounded-agent-core/src/bounded_agent_core/core.py` | 任务状态、固定动作、纯工具、独立步骤/工具调用预算、受控停止原因、审批暂停/恢复和最小事件合同。 | 单进程教学原型；不持久、不执行外部动作。 | 11 |
| `projects/11-bounded-agent-core/src/bounded_agent_core/evaluation.py`、`events.py` 与 `cli.py` | 严格静态夹具回放、无正文原子事件/评测报告与默认无执行 CLI；报告模式固定名称且不接收路径参数。 | 只处理公开教学夹具；不接收任意目标、工具、模型、凭据、审批或输出路径参数。 | 11.2、11.4 |
| `projects/11-bounded-agent-core/docs/human_review_template.csv` | 最小人工复核记录模板。 | 仅含案例、版本、状态、决定、理由类别、复核者和时间；禁止正文、参数、工具结果、提示词和密钥。 | 11.4 |
| `chapters/module_12_chapter_12_1.md`–`module_12_chapter_12_4.md` | 框架对照、图编排、持久化/恢复、幂等、工具包装、审批重验证、追踪最小化与采用门禁正文。 | 当前收束完成；四章各有 25 个固定部分与练习配额；不安装框架或真实工具。 | 12 |
| `projects/12-framework-adoption-kit/` | 无框架的框架采用合同项目：固定工具目录、候选字段闭集、最小 checkpoint、候选指纹、审批恢复绑定、公开静态迁移夹具、无正文报告、CLI、CI、pytest、mypy 与 Ruff。 | v0.1.0；14 项无网络 pytest、mypy、Ruff 通过；不安装框架、不调用模型、不实现真实持久化或工具执行。 | 12 |
| `projects/12-framework-adoption-kit/src/framework_adoption_kit/contracts.py` | 最小 checkpoint、固定工具目录、候选摘要、审批恢复与执行前再验证的纯数据合同。 | 无 callable、无凭据、无副作用。 | 12.2、12.3 |
| `projects/12-framework-adoption-kit/src/framework_adoption_kit/evaluation.py` 与 `cli.py` | 严格静态迁移夹具回放、原子无正文报告与默认无执行 CLI。 | 仅处理公开教学夹具，不接受任意工具、模型、目标、参数或输出路径。 | 12.4 |
| `records/module_12_research_notes.md` | LangGraph 编排、持久化、中断重放与工具安全的一手资料核对。 | 已完成；框架能力不构成权限或生产安全证明。 | 12 |
| `chapters/module_13_chapter_13_1.md`–`module_13_chapter_13_4.md` | 多 Agent 任务分割、角色权限、委派 Schema、预算、故障传播、汇总、冲突、人工复核与采用门禁正文。 | 当前收束完成；四章各有 25 个固定部分与练习配额；不连接模型、框架、网络或真实工具。 | 13 |
| `projects/13-delegation-contract-kit/` | 无框架多 Agent 委派合同项目：固定角色策略、最小工具集合、字段闭集委派、独立预算、去重、状态、取消、最小汇总、静态夹具、无正文报告、CLI、CI、pytest、mypy 与 Ruff。 | v0.1.0；15 项无网络 pytest、mypy、Ruff 通过；不创建真实 worker、并发或工具执行。 | 13 |
| `projects/13-delegation-contract-kit/src/delegation_contract_kit/core.py` | 角色策略、委派请求、最小结果、状态迁移、预算/去重、取消传播与稳定汇总的纯数据合同。 | 无模型、无 callable、无凭据、无副作用。 | 13.1–13.3 |
| `projects/13-delegation-contract-kit/src/delegation_contract_kit/evaluation.py` 与 `cli.py` | 严格静态委派夹具回放、原子无正文报告与默认无执行 CLI。 | 仅处理公开教学夹具，不接受任意任务、角色、工具、模型、凭据或输出路径。 | 13.4 |
| `records/module_13_research_notes.md` | 多 Agent 委派、并发、工具权限、协调故障、评测与注入安全的一手资料核对。 | 已完成；协作不构成权限或生产安全证明。 | 13 |
| `chapters/module_14_chapter_14_1.md`–`module_14_chapter_14_4.md` | 离线评测、版本基线、最小追踪、过程评分、隐私、人工校准、发布门禁、回滚和评测工程化正文。 | 当前收束完成；四章各有 25 个固定部分与练习配额；不调用模型、追踪平台、外部评测 API 或真实工具。 | 14 |
| `projects/14-evaluation-gate-kit/` | 无框架离线评测基线项目：严格案例、最小 trace、基线/候选结果、硬阻断、未运行、软回归阈值、发布决定、静态夹具、无正文报告、复核模板、CLI、CI、pytest、mypy 与 Ruff。 | v0.1.0；14 项无网络 pytest、mypy、Ruff 通过；不执行 Agent、不调用模型、追踪平台、外部评测或部署。 | 14 |
| `projects/14-evaluation-gate-kit/src/evaluation_gate_kit/core.py` | 案例、最小 trace、离线结果、基线/候选比较与发布门禁的纯数据合同。 | 无模型、无凭据、无外部执行。 | 14.1–14.3 |
| `projects/14-evaluation-gate-kit/src/evaluation_gate_kit/evaluation.py` 与 `cli.py` | 严格静态门禁夹具回放、原子无正文报告与默认无执行 CLI。 | 仅处理公开教学夹具，不接受任意案例、版本、模型、凭据或输出路径。 | 14.4 |
| `records/module_14_research_notes.md` | Agent 评测、trace 评分、基线、人工校准、安全和发布回滚的一手资料核对。 | 已完成；离线门禁不构成生产安全或权限证明。 | 14 |
| `chapters/module_15_chapter_15_1.md`–`module_15_chapter_15_4.md` | 配置/环境/秘密元数据、健康与停止、恢复/备份/事故响应、运行准备与 Runbook 正文。 | 当前收束完成；四章各有 25 个固定部分与练习配额；不启动服务或连接真实部署平台。 | 15 |
| `projects/15-operational-readiness-kit/` | 无框架运行准备合同项目：部署 profile、无秘密值元数据、drain、恢复演练、版本兼容、Runbook、静态夹具、无正文报告、CLI、CI、pytest、mypy 与 Ruff。 | v0.1.0；17 项无网络 pytest、mypy、Ruff 通过；不读取真实环境/秘密，不启动服务、端口、云、容器、数据库、遥测或部署。 | 15 |
| `projects/15-operational-readiness-kit/src/operational_readiness_kit/core.py` | 部署 profile、秘密元数据、恢复计划、Runbook 与稳定运行准备阻断决定的纯数据合同。 | 无秘密值、无环境读取、无网络、无部署。 | 15.1–15.3 |
| `projects/15-operational-readiness-kit/src/operational_readiness_kit/evaluation.py` 与 `cli.py` | 严格静态运行准备夹具回放、原子无正文报告与默认无执行 CLI。 | 仅处理公开教学夹具，不接受任意配置、秘密、端点、模型或输出路径。 | 15.4 |
| `projects/15-operational-readiness-kit/docs/operational_runbook_template.md` | 最小运维 Runbook：暂停、结果未知、恢复、回滚、升级与复盘字段。 | 明确禁止秘密、用户正文、提示词、完整配置、生产端点和原始 trace。 | 15.4 |
| `records/module_15_research_notes.md` | 健康检查、优雅停止、配置、秘密、遥测、备份恢复和 Runbook 的一手资料核对。 | 已完成；运行准备合同不构成真实部署或安全证明。 | 15 |
| `records/glossary.md` | 术语、首现章节和避免混用规则。 | 已补齐模块 1–15 当前关键术语；与中英索引相互补充。 | 全书 |
| `records/bilingual_index.md` | 中文—英文术语与主题导航。 | 已完成；含主题精选区和 102 条补充术语导航，全部术语表中文主名均可定位到首现章节。 | 全书 |
| `records/language_navigation_release_check.md` 与 `language_navigation_*audit.log` | 术语首现、导航闭环与高风险能力表述审校证据。 | 已完成；本批不改动项目代码。 | 全书 |
| `records/module_05_08_mapping_reaudit.log` 与 `module_05_08_project_mapping_release_check.md` | 模块 5–8 的 15 章项目路径、命令、25 节/References 审计，以及项目 5–8 的局部质量门结论。 | 已完成；79 项 pytest、mypy/Ruff 4/4 通过；这是局部文档修订证据，不替代 312 项全书回归。 | 5–8 |
| `records/module_09_15_mapping_reaudit.log` 与 `module_09_15_quality_gate*.log` | 模块 9–15 的 27 章仅离线项目命令、映射区、25 节/References 审计，以及项目 9–15 的局部质量门。 | 已完成；156 项无网络 pytest、mypy/Ruff 7/7 通过；不触发模型、网络、数据库、工具或部署，不替代 312 项全书回归。 | 9–15 |
| `records/all_chapter_mapping_coverage_reaudit.log` 与 `all_chapter_mapping_coverage_summary.log` | 全书章节的 25 节、References、唯一项目映射与真实代码/示例路径覆盖审计。 | 已完成；67 个章节文件、67 个映射区、0 个无效行。 | 全书 |
| `records/traceback_index.md` | 教学 Traceback、受控失败、退出码和公开错误导航。 | 已完成；不包含秘密、正文或原始响应。 | 全书 |
| `records/adr/` | 跨模块架构决策记录与总览。 | 已完成 ADR-001–004：模型权限、离线评测、副作用隔离、恢复/运行准备。 | 全书 |
| `records/runbook.md` | 本地验证、静态评测、失败处置、停止条件与真实部署前检查。 | 已完成；不含真实部署或秘密操作。 | 全书 |
| `records/reader_review_protocol.md` | 零基础、工程和 Agent 读者的试读任务、问题分类与最小反馈模板。 | 已完成；反馈不应包含秘密、用户正文、prompt、真实端点或原始响应。 | 全书 |
| `records/reader_review_pilot_packet.md` | 首轮人工试读的角色—章节—命令分配、最小流程、已知基线与去标识化反馈边界。 | 已完成；等待实际人类试读和反馈整合，不模拟或代替人工反馈。 | 全书 |
| `records/markdown_platform_release_check.md` 与 `markdown_platform_*audit.log` | GFM 源文件级标题、围栏、表格、链接文本与长行审校。 | 已完成；仍需在具体阅读器中人工确认呈现和辅助技术行为。 | 全书 |
| `records/publication_quality_gate.md` | 出版结构、代码、引用、链接、隐私、索引、ADR 和 Runbook 门禁。 | 已完成。 | 全书 |
| `records/publication_*audit*.log`、`publication_*summary.md` 与 `publication_structure_remediation.md` | 出版结构、引用、链接审计及早期练习配额修订证据。 | 67 章结构/练习/引用复核通过；链接审计无不可达阻断项。 | 全书 |
| `records/publication_final_release_check.md` 与 `publication_final_quality.log` | 出版前最终质量结论和项目 1–15 的最终代码回归证据。 | 可进入下一出版审校阶段；312 项测试、mypy、Ruff 通过，例外/非目标已记录。 | 全书 |
| `records/test-status.md` | 示例、项目和回归测试状态。 | 已同步模块 0–15、项目 1–15、312 项当前全量回归和 67 章出版结构复核。 | 全书 |
| `records/continuous_completion_manifest.md` | 面向连续执行的简要工作位置。 | 模块 15 当前收束完成，后续进入全书出版质量阶段。 | 全书 |

## 命名约定

| 对象 | 约定 |
|---|---|
| 章节 | `chapters/module_<两位编号>_chapter_<章号>.md`。 |
| 示例 | 使用语义化小写下划线命名，可作为 Python 模块导入。 |
| 项目 | `projects/<两位编号>-<短横线名称>/`，包含 `src/`、`tests/`、README 和工程配置。 |
| 测试 | 使用 `test_` 前缀，并和被测模块保持可追溯对应。 |
| 正文引用 | 每个代码路径必须与本表或相应项目目录完全一致。 |

> **迁移原则：** 保留历史路径只为使既有章节和测试可追溯；从模块 5 起，新项目必须采用标准目录项目布局。
