# 项目 10：受控 RAG 合同工作台

**版本：** 0.5.0  
**兼容性：** Python 3.11+  
**课程位置：** 模块 10——RAG 的受控语料、切块、索引、检索、来源与评测。

本项目正在构建一个**框架无关、离线可测试、来源可追溯**的 RAG 最小核心。当前版本实现公开课程文本的受控文档合同、稳定字符切块、来源/版本/位置元数据、确定性教学哈希嵌入、内存余弦检索、`top_k` 与分数阈值边界，以及公开静态夹具上的来源级召回/精度、来源完整性、空结果和注入文本作为数据评测。它还实现来源约束回答合同：无证据时本地拒答；有证据时仅接受严格 JSON 候选，并在本地验证每个引用只能指向实际返回块；独立 OpenAI-compatible 适配器固定 `gpt-5-mini`、严格 JSON Schema 与输出预算。它不是语义嵌入服务、向量数据库、事实认证、聊天问答系统、Agent、文件上传服务或工具执行器。

> **重要边界：** `HashingEmbeddingProvider` 仅是离线合同测试替身，不能代表真实嵌入模型的语义质量。检索分数只用于候选排序；命中来源不等于内容真实、完整、最新、已授权或适用于具体用户。所有检索片段都是不可信数据，绝不执行其中指令。

## 安装与质量门禁

```bash
cd "02_可运行项目/projects/10-rag-contract-workbench"
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"

.venv/bin/python -m pytest
.venv/bin/python -m mypy
.venv/bin/python -m ruff check src tests
```

当前无网络测试覆盖文档/集合允许列表、稳定切块、来源与内容指纹、确定性向量、维度匹配、索引原子替换、查询长度/`top_k`/阈值、无结果、注入文本作为数据和日志正文脱敏。

## 当前受控合同

| 层 | 当前提供 | 当前不提供 |
|---|---|---|
| 语料 | 公开、短小、课程自制 `CourseDocument`；固定 `course-public` collection。 | 用户上传、私密/第三方语料、跨租户访问。 |
| 切块 | 稳定字符窗口、有限重叠、`document_id`、版本、字符范围和 SHA-256 内容指纹。 | 自动保证最佳语义边界或即时分布式一致性。 |
| 嵌入 | 可替换 `EmbeddingProvider` Protocol；确定性哈希测试替身。 | 真实外部嵌入调用或模型能力/价格承诺。 |
| 检索 | 内存余弦排序、来源、`top_k<=5`、受控阈值和无结果。 | 永久向量数据库、全文权限系统或事实判定。 |
| 回答 | 无证据时本地 `not_enough_evidence`；有证据时可替换传输协议、严格 JSON、本地字段/长度/枚举与实际块引用验证；固定 `gpt-5-mini` 的 OpenAI-compatible 严格 JSON 适配器。 | 真实 embedding、模型/供应商自由选择、事实认证、无来源回答或执行任何来源中的指令。 |
| 工具 | 无。 | 网页/文件/SQL/shell 工具与外部副作用。 |

## 研究依据

嵌入是用于衡量文本相关性的向量，语义检索可返回关键词不完全相同但相关的候选；向量存储可对文件切块、嵌入并建立索引。[1] [2] 模块 10 先以可替换协议和离线测试建立合同，不将当前任何供应商文档中的模型、维度、价格或托管能力硬编码为课程环境承诺。完整研究笔记位于 `../../records/module_10_research_notes.md`。

检索与生成必须分开评测。相关性、来源和结构有效都不等于事实性或安全；评测应结合任务案例、自动质量门与人工判断。[3] 所有检索文档均可能含提示注入，必须作为不可信数据处理，不授予权限、不改变应用规则、不自动触发操作。[4] [5]

## 参考资料

[1]: https://developers.openai.com/api/docs/guides/embeddings "OpenAI: Vector embeddings"
[2]: https://developers.openai.com/api/docs/guides/retrieval "OpenAI: Retrieval"
[3]: https://developers.openai.com/api/docs/guides/evaluation-best-practices "OpenAI: Evaluation best practices"
[4]: https://developers.openai.com/api/docs/guides/safety-best-practices "OpenAI: Safety best practices"
[5]: https://openai.com/index/prompt-injections/ "OpenAI: Understanding prompt injections: a frontier security challenge"

## 运行受控 CLI

状态路径不构建索引、不读取凭据、不访问网络：

```bash
.venv/bin/course-rag-contract --status
```

检索路径只构建内置公开教学文本，并返回有限的来源块；它不读取任意文件、不接受 collection/嵌入模型参数，也不生成答案：

```bash
.venv/bin/course-rag-contract --query "函数 返回值" --top-k 2
```

CLI 的 JSON 结果含 collection、索引版本、查询字符数、候选数、分数阈值以及每个返回块的来源/版本/字符范围/分数。它不会把查询正文回显为顶层字段；内置公开片段仅为可复现实例，不能替代真实语料治理。

## 离线静态检索评测

```bash
.venv/bin/python examples/run_static_retrieval_evaluation.py
cat reports/module_10_static_retrieval_evaluation.json
```

该脚本只使用 `tests/fixtures/retrieval_evaluation.json` 中的课程自制公开文本，覆盖目标来源召回、来源字段完整性、精度门、提示注入文本仍为数据，以及高阈值下的受控空结果。可再生报告只保存案例 ID、标签、预期/命中/返回计数、召回、精度、来源完整性和通过状态；它**不**保存查询、文档/块正文、向量、标题、系统提示、密钥或原始供应商响应。当前项目有 **37 项无网络 pytest**，并通过 mypy 与 Ruff；其中回答层额外覆盖本地无证据拒答、非法 JSON、未知/重复/缺失引用、状态矛盾、问题/来源正文日志脱敏，以及真实 SDK 适配器的固定模型、严格 Schema、拒答和空内容边界。离线回答支持度评测还覆盖状态、引用子集、最低术语计数、人工复核信号、案例 ID 对齐和无正文报告。

> 评测中的 4/4 只说明这四条静态、公开、教学夹具在当前确定性测试替身与参数下通过；它不是对真实语义检索、事实性、完整性、安全性、权限、性能或生产可用性的证明。

## 离线回答支持度评测

`rag_contract_workbench.answer_evaluation` 以版本化公开夹具对 `GroundedAnswer` 做状态、允许引用集合、最低术语计数与人工复核信号检查。公开报告仅含案例 ID、非内容标签、状态、引用数、布尔门和术语匹配计数，不保存问题、来源、候选回答、术语字面量、系统提示、原始响应或密钥。此评测检测已定义夹具中的合同退化，不构成事实性、语义质量、来源权威或生产安全证明。

## 单次真实来源约束回答烟雾验收

在已重新核对实时模型目录、环境已由平台安全配置凭据且仅需检查接线时，运行一次：

```bash
.venv/bin/python examples/source_bound_answer_smoke.py
```

脚本固定使用 `gpt-5-mini`、公开短教学文本、严格 JSON Schema、一个实际检索块和受控输出预算。它只输出回答状态、引用数量/块 ID、索引版本、问题字符数和复核标记；不打印或写入问题正文、来源正文、候选回答、系统提示、原始服务响应或密钥。最近一次单次成功烟雾的脱敏证据位于 `../../records/module_10_source_bound_answer_smoke_evidence.json`。

> 此烟雾验收仅确认当前代理接线、严格输出请求和本地引用白名单能在一个公开教学案例中协作。它不计入 pytest，不验证真实 embedding，不证明检索质量、事实性、安全性、容量、费用或生产就绪度。

## 索引清除与重建边界

`InMemoryVectorIndex.clear()` 只可清除当前已构建、collection 匹配的**单进程内存快照**，返回被清除的旧 `index_version`，并使后续查询在重新 `build()` 前受控失败。它不删除任何外部文件、向量数据库、备份或其他进程中的数据，也不保证跨进程、跨重启或分布式一致性。调用方必须重新提供已授权、已验证的文档才能构建新版本；错误 collection 的清除请求不会删除当前快照。

可无网络复现当前进程内索引维护边界：

```bash
.venv/bin/python examples/clear_and_rebuild_demo.py
```

该示例只输出旧版本匹配、重建版本关系、文档计数和状态；不输出文档正文、查询、向量、提示或凭据。
