# 测试状态记录

**环境基线：** Ubuntu 24.04；验证解释器为 Python 3.12；教材代码目标兼容 Python 3.11+；Shell 为 Bash。  
**权威状态更新：** 2026-08-26（GMT+8）

| 范围 | 验证命令或对象 | 状态 | 最新结果 |
|---|---|---|---|
| 模块 0 | `python3 -m unittest discover -s tests/module_00 -v` | 通过 | 7 项测试通过：逆向设计、运行快照、Traceback 受控失败、学习记录。 |
| 模块 1 | `python3 -m unittest discover -s tests/module_01 -p 'test_*.py' -v` | 通过 | 1 项测试通过：名称绑定示例验证复制更新不会修改原任务。 |
| 模块 2 | `tests/module_02/test_text_analyzer.py` | 通过 | 3 项测试通过：规范化、统计与非字符串输入拒绝。 |
| 模块 3 | `projects/03-auto-archive` 的 pytest | 通过 | 7 项测试通过：Dry Run、移动、冲突拒绝、受控 JSON、操作清单、回滚与 CLI 行为。 |
| 模块 3 | 自动归档 CLI 临时目录验收 | 通过 | `--apply` 可真实移动；未加 `--apply` 时保持 Dry Run。 |
| 模块 4 | `projects/04-plugin-system/tests/test_plugins.py` | 通过 | 注册、重复拒绝、未知插件、输入类型、生成器、允许配置、未知类型拒绝、字段拒绝、JSON 错误、审计脱敏共 12 项通过。 |
| 模块 4 | `projects/04-plugin-system/tests/test_cli.py` | 通过 | CLI 列表、转换审计和未知插件受控退出共 3 项通过。 |
| 模块 4 | `python3 -m unittest discover -s tests -v`（项目 4 根目录） | 通过 | 15 项通过，0 项失败，运行约 0.25 秒。 |
| 模块 4 | CLI 手工端到端验收 | 通过 | `--list` 输出允许插件；`--plugin task` 输出带前缀文本；JSON Lines 审计只保存长度与状态。 |
| 模块 5 | `tests/module_05/test_environment_check.py` | 通过 | 2 项测试通过：环境摘要字段完整，当前解释器路径真实存在。 |
| 模块 5 | `projects/05-cli-tool-platform` 可编辑安装与 `pytest` | 通过 | 在隔离 `.venv` 中执行 `pip install --editable ".[dev]"` 后，命令行入口运行成功，9 项 pytest 通过。 |
| 模块 5 | CLI 工具平台 `mypy` 与 Ruff | 通过 | `mypy src` 无问题；`ruff check src tests` 全部通过。 |
| 模块 5 | CLI 工具平台 Git 忽略规则 | 通过 | `git check-ignore -v` 确认 `.venv/`、`__pycache__/`、pytest/mypy/Ruff 缓存与 `*.egg-info/` 均由 `.gitignore` 排除；源码、测试、README 和 CI 保持待跟踪。 |
| 模块 5 | CLI 工具平台受控配置与日志 | 通过 | 新增 TOML 字段白名单、文件大小上限、环境变量覆盖和脱敏日志配置；9 项 pytest、mypy 与 Ruff 全部通过。 |
| 模块 5 | CLI 配置与日志端到端验收 | 通过 | 合法 TOML 产生稳定 JSON；`--verbose` 只在标准错误产生元数据日志；未知 `module` 字段受控拒绝并返回退出码 2。 |
| 模块 5 | 项目 2 文本分析工具工程化迁移 | 通过 | 标准 `src` 布局、可编辑安装、6 项 pytest、mypy、Ruff 均通过；文件 JSON 输出正常，缺失文件以退出码 2 受控拒绝。 |
| 模块 5 | 项目 1 命令行任务管理器工程化实现 | 通过 | 标准包、CRUD、固定 JSON、原子替换、备份、删除确认、17 项 pytest、mypy、Ruff 与 CLI 脱敏验收通过。 |
| 模块 5 | 项目 3 自动归档系统工程化迁移 | 通过 | 标准包、可编辑安装、7 项 pytest、mypy、Ruff 通过；端到端验证默认 Dry Run、显式移动、清单写入和同名冲突退出码 2。 |
| 模块 5 | 项目 4 安全插件系统工程化迁移 | 通过 | 标准包与薄兼容层、15 项 pytest、mypy、Ruff 通过；端到端验证安装命令、旧 CLI、审计正文脱敏和未知类型退出码 2。 |
| 模块 6 | HTTP 契约与异步可靠性示例 | 通过 | 15 项 `unittest`：HTTP 示例 8 项覆盖资源、404/405/422、Schema 和日志脱敏；asyncio 示例 7 项覆盖 TaskGroup、超时、取消、清理、失败联动和日志正文脱敏。 |
| 模块 6 | 项目 6 知识笔记 FastAPI/SQLite 服务 | 通过 | 17 项 pytest、mypy、Ruff 通过；覆盖请求 ID、模型、依赖、404/422、SQLite 跨实例持久化、参数化文本、事务回滚与备份恢复；真实本地服务器通过跨重启读取和 404 验收。 |
| 模块 7 | 项目 7 受控 API 客户端、礼貌并发与 JSONL 存储 | 通过 | 28 项 pytest、mypy、Ruff 通过；MockTransport 覆盖超时/重试/响应边界，确定性协程覆盖 robots、Semaphore、Pacer、TaskGroup 取消，存储覆盖 JSONL、去重、原子快照、恢复、Schema 与日志脱敏；CLI 非 HTTPS 基址受控退出 2，`store_demo.py` 端到端验证写入、去重与恢复。 |
| 模块 8 | 项目 8 受控服务工作流 | 通过 | 25 项 pytest、mypy、Ruff 通过；状态机、幂等、容量、有界队列、TaskGroup、超时、取消清理、并发上限、FastAPI lifespan、202/404/409/422/503 合同、请求 ID、关停恢复与日志脱敏均有测试；真实本地服务验收通过。 |
| 模块 9 | 项目 9 受控 LLM 合同客户端 | 通过 | 33 项无网络 pytest、mypy、Ruff 通过；覆盖文本合同、固定模型/任务、输入/输出边界、严格 JSON Schema、额外字段/枚举/长度拒绝、SDK 严格 `response_format` 形状、拒答/空内容、有限重试、日志脱敏、静态夹具 ID 对齐、质量门失败与原子无正文评测报告。一次真实结构化烟雾调用仅记录脱敏元数据，明确不计入测试数或质量证明。 |
| 模块 10 | 项目 10 受控 RAG 合同工作台 | 通过（局部） | 37 项无网络 pytest、mypy、Ruff 通过；覆盖公开语料/集合与查询预算、稳定切块/指纹、教学嵌入维度、原子索引、来源排序、阈值空结果、注入文本作为数据、CLI 状态、来源级召回/精度/来源完整性、无正文原子检索报告、本地无证据拒答、严格候选 JSON、未知/重复/缺失引用、日志脱敏、固定 `gpt-5-mini` SDK 严格请求形状、拒答/空内容，以及离线回答支持度的状态、引用子集、术语计数、人工复核、案例 ID 对齐与无正文报告，还覆盖索引清除返回版本、错误 collection 保留旧快照、清除后查询失败和清除日志脱敏。4/4 检索夹具和一次脱敏真实公开教学文本烟雾通过，不代表真实 embedding、语义、事实、安全或生产验收。 |
| 当前全量回归 | 模块 0–2、4–6 的 `unittest`，以及项目 1–15 的 pytest | 通过 | 模块测试共 32 项（7 + 1 + 3 + 4 + 2 + 15）；模块 3、7、8、9、10、11、12、13、14、15 当前没有独立 `tests/module_*` 文件。项目测试共 280 项（17 + 6 + 7 + 15 + 9 + 17 + 28 + 25 + 33 + 37 + 23 + 17 + 15 + 14 + 17）；合计 **312 项**测试通过。项目 1–15 均额外通过 mypy 与 Ruff；项目 1、6、7 的示例目录不是既有项目 Ruff 基线，故全量静态门禁遵循各项目的 `src tests` 配置。项目 6、8 的 Starlette/httpx 弃用 warning 为已知第三方依赖 warning，不是失败。模块收束逐范围日志为 `records/module_15_full_regression.log`；出版前最终复核日志为 `records/publication_final_quality.log`，同样通过。 |
| 模块 11 | 项目 11 受限 Agent 核心 | 通过 | 23 项无网络 pytest、mypy、Ruff 通过；覆盖固定纯工具、有限状态、相互独立的步骤/工具调用预算、稳定停止原因及状态一致性、审批暂停/恢复/拒绝、任务 ID/目标/计数边界、原子最小事件报告不落盘正文、静态夹具的纯工具回放、提示注入文本作为数据、未知动作拒绝、默认无执行 CLI、公开静态评测与冲突模式拒绝、固定无正文静态报告 CLI，以及夹具空输入、重复 ID、额外字段和空动作序列受控拒绝；未接入模型、框架或副作用，已纳入模块 0–11 的 249 项官方回归。 |
| 模块 12 | 项目 12 框架采用合同工具包 | 通过 | 17 项无网络 pytest、mypy、Ruff 通过；覆盖固定工具目录、候选字段闭集、最小 checkpoint、候选指纹、审批绑定、跨租户/过期/拒绝受控失败、严格公开静态迁移夹具、重复 ID/额外字段/损坏 JSON/缺失夹具拒绝、原子无正文报告、默认无执行 CLI 和冲突模式拒绝；未安装框架、未调用模型、未实现真实持久化或任何工具执行，已纳入模块 0–12 的 266 项官方回归。 |
| 模块 13 | 项目 13 多 Agent 委派合同工具包 | 通过 | 15 项无网络 pytest、mypy、Ruff 通过；覆盖固定角色策略、角色最小工具集合、字段闭集委派、总量/活跃/角色预算、去重、有限状态迁移、取消传播、稳定汇总、冲突、身份错配、严格公开静态夹具、重复 ID/额外字段/损坏 JSON/缺失夹具拒绝、原子无正文报告、默认无执行 CLI 和冲突模式拒绝；未安装框架、未调用模型、未创建真实 worker、并发或工具执行，已纳入模块 0–13 的 281 项官方回归。 |
| 模块 14 | 项目 14 评测基线与发布门禁工具包 | 通过 | 14 项无网络 pytest、mypy、Ruff 通过；覆盖严格案例、最小 trace、基线/候选闭集、硬阻断、未运行、软回归阈值、基线不匹配、案例覆盖、严格公开夹具、重复 ID/额外字段/损坏 JSON/缺失夹具拒绝、原子无正文报告、默认无执行 CLI 和冲突模式拒绝；未调用模型、追踪平台、外部评测、真实工具或部署服务，已纳入模块 0–14 的 295 项官方回归。 |
| 模块 15 | 项目 15 运行准备与恢复合同工具包 | 通过 | 17 项无网络 pytest、mypy、Ruff 通过；覆盖严格部署 profile、无秘密值元数据、环境边界、秘密过期/撤销/缺失、drain、恢复演练、版本兼容、Runbook 完整度、稳定阻断决定、严格公开夹具、重复 ID/额外字段/损坏 JSON/缺失夹具拒绝、原子无正文报告、默认无执行 CLI 和冲突模式拒绝；不读取真实环境或秘密，不启动服务、端口、云、容器、数据库、遥测、模型、工具或部署，已纳入模块 0–15 的 312 项官方回归。 |
| 文档质量 | 模块 0.1–15.4 固定结构与练习配额核验 | 通过 | 67 章均含 25 个编号教学部分，并通过快测、代码阅读、Debug、编程、逆向设计与课后项目标题复核。模块 0–3、4.1–4.2、5.3 的第 21–25 节已在出版修订中补齐统一配额；模块 11 已纳入 workflow/Agent 边界、有限状态、纯工具、预算、审批、可观察事件、离线静态评测、模型外候选授权、停止条件、最小报告、人工复核与无副作用工具控制；模块 12–15 分别覆盖框架对照、多 Agent、评测发布门禁与运行准备。审计日志为 `records/publication_chapter_structure_reaudit.log`，修订记录为 `records/publication_structure_remediation.md`。 |
| 出版前最终质量 | 结构、练习、引用、链接、代码、索引、ADR、Runbook 与卫生审计 | 可进入下一出版审校阶段 | 67 章结构/练习/References 与行内引用复核通过；链接审计无不可达阻断项；312 项测试、项目 1–15 mypy/Ruff 通过；完整结论及访问受限/占位链接、非 Git 工作树、第三方 warning 等非阻断项见 `records/publication_final_release_check.md`。 |
| 早期模块出版修订 | 模块 0–4 项目映射、模块 0–5 质量复核 | 通过（局部） | 23 个早期章节已补齐直接项目/示例路径、验证命令和主题化扩展任务；映射复核通过。模块 0–5 教材测试 17 项、项目 1–5 pytest 54 项，共 71 项局部复核测试通过，项目 1–5 mypy/Ruff 通过。详见 `records/early_module_revision_release_check.md`；全书 312 项官方计数保持不变，待下一次完整回归时更新。 |
| 语言与术语导航审校 | 术语表—中英索引定位闭环与读者导航 | 通过（文档） | 中英索引新增 102 条补充导航，术语表中文主名在索引中零缺口；本批未修改项目代码或测试，官方 312 项全书回归计数保持不变。详见 `records/language_navigation_release_check.md` 与 `language_navigation_reaudit.log`。 |
| 模块 5–8 工程读者路径修订 | 15 章项目映射、命令、结构与局部项目质量门 | 通过（局部） | 15 章均有主题化项目映射、可复制命令、25 节和 References；项目 5–8 合计 79 项 pytest 通过，mypy/Ruff 4/4 通过。项目 6、8 各有一条既知 Starlette/httpx 弃用 warning，非失败。详见 `records/module_05_08_project_mapping_release_check.md`；该文档批次不修改项目代码，312 项官方全书回归计数保持不变。 |
| 模块 9–15 受控项目映射修订 | 27 章离线映射、命令、结构、边界与局部质量门 | 通过（局部） | 27 章均有仅离线 pytest/mypy/Ruff 的项目映射、主题化扩展、真实能力边界、25 节和 References；项目 9–15 合计 156 项无网络 pytest 通过，mypy/Ruff 7/7 通过。未触发模型、网络、数据库、工具、部署或秘密读取。详见 `records/module_09_15_project_mapping_release_check.md`；该文档批次不修改项目代码，312 项官方全书回归计数保持不变。 |
| 全书项目映射覆盖 | 全部 67 章的结构、References、唯一映射区和项目/示例路径 | 通过（文档） | 初次覆盖审计定位并补齐模块 4.3–4.4 的映射区；最终 67 个章节文件与 67 个映射区一一对应，25 节、References、真实项目/示例路径均无缺口，0 个无效行。详见 `records/all_chapter_mapping_coverage_reaudit.log` 与 `all_chapter_mapping_coverage_summary.log`；这不替代全书 312 项代码回归。 |
| 模块 0–2 读者试读准备抽样 | 开篇解释、前置知识、项目命令、预期输出与失败边界 | 通过（抽样） | 抽样审校 0.2、0.3、1.1、1.8、2.1、2.5；修正 2.5 的非真实导入为 `text_analyzer.core` 并加入项目虚拟环境安装前提/预期输出。项目 2 的 6 项 pytest、mypy、Ruff 通过；章节仍为 25 节且有 References。详见 `records/module_00_02_reader_readiness_check.md` 与 `module_02_5_reader_recheck.log`。文档修订不刷新 312 项官方全书回归。 |
| 模块 3–5 读者试读准备抽样 | 文件副作用、配置/日志、迁移命令与受控失败说明 | 通过（抽样） | 抽样审校 3.1、3.4、4.4、5.1、5.4、5.5；修正 5.5 两个项目目录的文字分隔，避免误读为不存在的单一路径。六章均为 25 节；项目 3–5 合计 31 项 pytest、mypy/Ruff 3/3 通过。详见 `records/module_03_05_reader_readiness_check.md` 与 `module_03_05_reader_recheck.log`。文档修订不刷新 312 项官方全书回归。 |
| 模块 6–8 读者试读准备抽样 | API、异步、礼貌并发、状态机与恢复边界 | 通过（抽样） | 抽样审校 6.1、6.4、7.1、7.3、8.1、8.3；六章均为 25 节。项目 6–8 合计 70 项 pytest、mypy/Ruff 3/3 通过；项目 6、8 各有一条既知 Starlette/httpx 弃用 warning，非失败。详见 `records/module_06_08_reader_readiness_check.md` 与 `module_06_08_reader_recheck.log`。文档审校不刷新 312 项官方全书回归。 |
| 模块 9–15 读者试读准备抽样 | 离线合同、静态夹具、烟雾边界与运行准备说明 | 通过（抽样） | 抽样审校 9.1、9.3、10.1、10.4、11.1、12.4、13.3、14.4、15.4；九章均为 25 节。项目 9–15 合计 156 项无网络 pytest、mypy/Ruff 7/7 通过，未触发模型、网络、工具、部署或秘密读取。详见 `records/module_09_15_reader_readiness_check.md` 与 `module_09_15_reader_recheck.log`。这是局部离线复核，不刷新 312 项官方全书回归。 |
| Markdown 平台排版与可访问性 | H1/H2、References、围栏、表格和链接文本源文件审校 | 通过（源文件） | 67 章均有 1 个主标题、25 节、1 个 References 节和成对代码围栏；表格分隔行缺表头、非 References 裸 URL、空链接文本均为 0。长行仅记录为具体目标阅读器的后续人工折行检查项。详见 `records/markdown_platform_release_check.md`、`markdown_platform_reaudit.log`、`markdown_table_link_reaudit.log`；不刷新 312 项官方全书回归。 |
| 人工试读反馈机制 | 试读包、登记册、门禁与导航交叉引用 | 通过（准备） | 已建立去标识化反馈登记册，含稳定编号、P0/P1/P2、状态枚举、最小证据和禁止信息；协议—试读包—登记册—门禁—目录链接复核通过。当前等待真实人工反馈，不模拟结果。详见 `records/reader_feedback_ledger.md`、`reader_feedback_ledger_check.log`、`reader_feedback_consistency_reaudit.log`。 |

## 受控失败验证

| 范围 | 输入或条件 | 预期结果 | 验证目的 |
|---|---|---|---|
| 模块 0 | `traceback_lab.py` 接收 `not-a-number` | 含 `ValueError` 的完整 Traceback。 | 教授如何阅读错误，不将教学失败视作产品缺陷。 |
| 模块 3 | 目标目录存在同名归档文件 | 拒绝覆盖并保留源文件。 | 验证文件系统安全边界。 |
| 模块 4 | 配置声明 `python_module` 类型 | `PluginConfigurationError`，不执行动态导入。 | 验证允许列表和配置—代码边界。 |
| 模块 4 | 调用未注册插件 | `UnknownPluginError`；CLI 退出码 `2`。 | 验证未知能力默认拒绝。 |
| 模块 4 | 审计开启时输入敏感文本 | 审计文件不含正文，仅含长度和状态。 | 验证日志最小化与脱敏原则。 |
| 模块 6 | `POST /notes` 含未知 `module` 字段 | `422 invalid_request`，且不回显原始字段或正文。 | 验证 API Schema 与公开错误边界。 |
| 模块 6 | `GET /notes/999` | `404 note_not_found` 与请求 ID。 | 验证领域资源缺失到 HTTP 错误的稳定映射。 |
| 模块 6 | SQLite 约束写入失败 | 回滚且抛 `StorageError`，无新笔记。 | 验证数据库约束与事务回滚边界。 |
| 模块 6 | 慢协程超过批处理时间预算 | `BatchTimedOutError`，任务被取消并执行清理。 | 验证超时、取消传播与资源收尾。 |
| 模块 7 | 非 HTTPS 基址 | CLI 输出公开 `collection_failed` JSON 并退出码 `2`，不发请求。 | 验证协议与主机允许边界。 |
| 模块 7 | robots 拒绝固定端点 | `RobotsDeniedError`，在任何 fetch 前失败。 | 验证默认拒绝和礼貌预检。 |
| 模块 7 | 超大/损坏 JSONL、NaN 或重复 ID | 受控 `StorageLimitError` 或 `RecordSchemaError`，不接受损坏记录。 | 验证本地存储资源、格式与去重边界。 |
| 模块 7 | 清单缺失 | `load_manifest()` 受控失败；显式 `recover_manifest()` 从已验证记录重建。 | 验证恢复不静默猜测。 |
| 模块 8 | 同一幂等键对应不同工作引用 | `409 idempotency_conflict`，不创建第二个任务。 | 验证安全重试与业务冲突边界。 |
| 模块 8 | 有界队列已满 | `503 queue_busy`，新任务在注册前被拒绝。 | 验证反压且防止孤儿 pending 任务。 |
| 模块 8 | 运行 handler 超过时间预算 | `failed` 与 `timeout`，handler 的 `finally` 清理执行。 | 验证超时、取消和资源收尾。 |
| 模块 8 | 服务正常关闭时仍有 running 任务 | 标为 `pending`、`interrupted` 与恢复计数；不伪装成功。 | 验证生命周期恢复候选边界。 |
| 模块 9 | 未知模型、超长/空输入或未允许控制字符 | 在传输前以稳定 `LlmRequestError` 拒绝。 | 验证模型/输入允许边界和不必要调用防护。 |
| 模块 9 | 拒答、空内容、无 choices、非法 JSON、额外字段、空/过长数组或未知枚举 | 转为永久传输或结构化输出受控失败；不静默补值、不直接重试。 | 验证严格 JSON Schema 与本地重复验证。 |
| 模块 9 | 短暂传输失败 | 最多两次尝试，耗尽后稳定不可用错误；日志无用户正文和原始异常。 | 验证有限重试与日志最小化。 |
| 模块 9 | 静态夹具 ID 不对齐、非法候选或质量门失败 | 受控夹具/结构化错误或明确 `passed=false`；公开报告不含输入、摘要、关键点、关键词字面量或候选 JSON。 | 验证可复现评测、隐私边界与失败可解释性。 |
| 模块 10 | 非法公开语料、未知 collection、重复文档 ID、空/超预算查询、未建索引、错误向量维度或零向量 | 在构建/查询前以 `DocumentError`、`IndexErrorContract` 或 `QueryError` 稳定拒绝；旧快照不因失败构建被替换。 | 验证语料、资源、索引原子性与向量合同。 |
| 模块 10 | 目标来源遗漏、噪声导致精度不足、重复案例 ID 或未建索引评测 | 明确 `passed=false` 或 `EvaluationFixtureError`；报告不持久化查询、块正文、向量或注入文本。 | 验证检索质量门、夹具合同和报告隐私。 |
| 模块 10 | 空证据、非法 JSON、未知/重复/缺失引用、矛盾状态或超长回答 | 空证据本地 `not_enough_evidence` 且不调用传输；其余转为 `AnswerContractError`，不补值或自动执行来源文本。 | 验证来源约束回答和提示注入不跨越模型外安全边界。 |
| 模块 10 | SDK 模型拒答、空 choices 或空内容 | 转为 `AnswerTransportRejectedError`；固定模型、严格 JSON Schema 和输出预算由无网络请求形状测试验证。 | 验证供应商响应不能绕过本地回答合同；真实烟雾仅检查最小接线。 |

> **当前门禁结论：** 模块 9 已完成当前收束；模块 10 已完成受控 RAG、静态检索评测与来源约束回答的首批实现。模块 0–10 当前官方范围为 226 项测试、项目 1–10 均通过 mypy 与 Ruff；项目 10 的 37 项已纳入全量回归；另有一次不计入测试数的脱敏公开教学文本真实烟雾。后续新增模块、项目或依赖变更必须重新运行对应单元、端到端、mypy 与 Ruff 检查，并更新本表。
