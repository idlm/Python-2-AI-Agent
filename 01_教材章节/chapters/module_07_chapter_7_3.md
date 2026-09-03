# 第 7.3 章：采到数据不等于保存成功——JSONL、去重、原子替换与恢复

**适用版本：** Python 3.11+  
**项目连接：** `02_可运行项目/projects/07-polite-api-collector/`（版本 0.1.0）

## 1. 本章目标

完成本章后，你能够区分采集结果、运行日志、JSONL 记录、清单与备份；能解释为什么普通 JSON 文件不能直接追加多个对象；能用固定 Schema、严格 JSON、去重 ID、大小限制和受控路径保存采集结果；能说明同目录临时文件、`fsync`、`os.replace()` 降低什么风险；能设计清单恢复而不是静默猜测。

## 2. 先纠正一个误解：写入返回不代表可恢复

`file.write()` 返回字节数，只说明当前进程曾把数据交给文件对象；它不说明 JSON 合法、字段完整、磁盘持久、清单一致、进程未中断、下一次能读取，或敏感内容没有扩散到日志。采集系统的输出必须有一个明确合同：写什么、在哪写、如何验证、怎样去重、失败后恢复什么、绝不记录什么。

## 3. 从生产级 Agent 倒推

Agent 的检索、工具和模型结果若无记录，会无法复现实验、定位失败或评测；若无边界地记录，又会积累用户隐私、秘密和不可信网页内容。Agent 不是一个 JSONL 文件或框架调用；它需要受控记忆、状态、工具、工作流和评测。本章的存储层只是“受控采集结果记录”的最小原理，不能直接充当长期用户记忆库、向量数据库、审计系统或合规归档。

## 4. 三类文件不要混用

| 文件/数据 | 目的 | 项目 7 的位置 | 不应承担 |
|---|---|---|---|
| 采集记录 | 保存固定 Schema 的成功页面结果。 | `records.jsonl` | 调试日志、任意 Python 对象、秘密备份。 |
| 清单 | 记录版本、计数、记录 ID 和更新时间。 | `manifest.json` | 替代真实记录正文或灾难恢复。 |
| 运行日志 | 说明阶段、计数和错误类型。 | stderr/日志系统 | 保存 payload、查询参数、token。 |
| 临时文件 | 在切换正式文件前承载完整新快照。 | 同一输出目录、短暂存在。 | 给用户直接读取或永久积累。 |

当“数据、清单、日志”全部写进一个文本文件时，读取、恢复、访问控制和测试都会变得模糊。

## 5. JSON 与 JSONL 的区别

Python 文档明确提醒 JSON 不是带帧协议：向同一文件反复调用 `json.dump()` 会形成无效 JSON。[1] 因此以下做法错误：

```python
with open("records.json", "a", encoding="utf-8") as handle:
    json.dump({"id": "one"}, handle)
    json.dump({"id": "two"}, handle)  # 两对象连在一起，不是一个 JSON 文档。
```

**JSON Lines（JSONL）**约定每一行是一个完整 JSON 对象。它并非让数据天然安全；它只是给追加/逐行读取一种明确边界。项目 7 的 `records.jsonl` 将每行限制为固定 Schema，读取时逐行验证，空行、损坏 JSON、字段多缺和重复 ID 都受控拒绝。

## 6. 固定 Schema 比“存字典”更可靠

```python
{
  "id": "sha256...",
  "source": "approved-catalog",
  "name": "catalog",
  "endpoint": "/v1/catalog",
  "collected_at": "2026-08-26T00:00:00+00:00",
  "payload": {"items": ["one", "two"]}
}
```

`CollectionStore` 要求字段集合**恰好**是上述六项。它不接受未声明字段、缺少字段、非字符串 ID、非 `/` 开头端点或非对象 payload。固定 Schema 的意义是提前暴露版本变化、数据污染和开发者误用；它不是让数据自动可信，payload 仍来自上游，后续业务必须继续验证其领域含义。

## 7. JSON 输入也要有限制

Python `json` 文档警告，不可信 JSON 可能消耗大量 CPU 和内存，建议限制解析数据大小。[1] 第 7.1 章已在网络边缘限制响应字节数；本章仍在本地层限制总文件、单行、记录总数与嵌套深度。两层都需要：网络入口防止大响应进程，文件入口防止被手工修改、旧版本、磁盘残留或其他程序写入的异常内容进入恢复流程。

## 8. 严格 JSON，不允许 NaN 和无穷

Python 的默认 JSON 编码器可接受并输出 `NaN`、`Infinity` 和 `-Infinity`，这不符合严格 JSON 规范；`allow_nan=False` 会在遇到这些值时抛 `ValueError`。[1] `CollectionStore` 先递归验证浮点有限性，再用：

```python
json.dumps(value, ensure_ascii=False, sort_keys=True,
           separators=(",", ":"), allow_nan=False)
```

这让测试、摘要和散列有稳定表示，也避免“Python 能写、其他系统不能读”的延迟故障。

## 9. 为什么 payload 只接受 JSON 对象

上游 API 可能返回对象、数组、字符串或数字。项目 7 客户端只接受对象根节点；存储层同样要求 `payload` 是对象。这样记录顶层语义稳定，未来可以安全加入经过审查的 `schema_version`、分页信息或内容摘要。若业务确实需要数组，应把数组放到明确对象字段，例如 `{ "items": [...] }`，不要在不同记录中随意改变根类型。

## 10. 去重 ID 需要可解释输入

项目以来源、名称、端点和规范化 payload 的字符串计算 SHA-256：

```python
canonical_payload = self._strict_json(payload)
digest_input = "\n".join((source, page.name, page.endpoint, canonical_payload))
record_id = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()
```

因此相同来源的相同页面结果会得到相同 ID，第二次写入被统计为 `skipped_duplicates`。这是一种**内容标识**，不是身份认证、加密、签名或证明来源真实性；不同时间的相同内容也会合并，若业务必须保留每次快照，ID 合同必须明确加入采集时间或版本号。

## 11. 去重不是更新策略

| 情况 | 当前项目行为 | 可能的业务替代 |
|---|---|---|
| 内容相同 | 跳过重复记录。 | 记录“再次看见”时间。 |
| 内容改变 | 新 ID、新记录。 | 建立版本链或更新当前快照。 |
| 来源名称改变 | 新 ID。 | 建立来源映射或迁移规则。 |
| 端点改变 | 新 ID。 | 记录重定向/目录版本。 |
| 重复 ID 文件损坏 | 拒绝读取。 | 人工修复或从可信备份重建。 |

不要把“去重”误说成“增量同步已完成”。同步还需要删除、更新时间、冲突、分页、失败重试和来源权威性规则。

## 12. 输出目录是安全边界

`CollectionStore` 接受一个输出根目录，而不是每次调用接受任意文件名。它创建并 `resolve()` 根目录，再由固定文件名得到 `records.jsonl` 和 `manifest.json`。Python `pathlib` 文档指出，纯路径不会随意折叠 `..` 或双前导斜杠，因为它们可能改变符号链接或 UNC 语义；若要检查真实路径，应使用会访问文件系统的 `resolve()`。[2]

字符串前缀检查如 `str(path).startswith("output")` 不足以防住同名前缀或符号链接。项目仍是单进程教学实现；生产环境还需目录权限、用户隔离、所有权、配额和跨平台策略。

## 13. 为什么写临时文件

直接打开 `records.jsonl` 并覆盖时，进程崩溃、磁盘错误或异常可能留下半个文件。项目先把完整新快照写到正式目标**同一目录**的临时文件：

```python
handle.write(text)
handle.flush()
os.fsync(handle.fileno())
os.replace(temporary_name, destination)
```

同目录是有意选择：替换操作应在同一文件系统内进行，避免把跨设备移动误当成同一语义。Python `os` 接口在路径/设备错误时会抛 `OSError`，项目将其包装为 `StorageError`。[3]

## 14. `os.replace()` 降低什么风险

`os.replace(src, dst)` 用新的完整文件替换目标路径。它使读者通常看到旧完整快照或新完整快照，而不是写入过程中的中间文本；但这不是万能“原子且永不丢数据”的承诺。文件系统、目录元数据持久化、跨设备路径、多个进程同时写、硬件故障、网络文件系统和灾难恢复都有额外条件。教材必须说“降低半写入主文件风险”，而不是“解决所有持久化问题”。

## 15. 为什么 JSONL 仍采用快照替换

JSONL 经常被用于追加，但项目为了简化去重和一致性，读取全部已验证记录、加入新记录后重新写入完整 JSONL 快照。这在 `max_file_bytes` 和 `max_records` 小的教学范围内可读、可测试；它不适合无限增长或高吞吐系统。数据变大后，应选择数据库、分区、批处理、日志压缩、对象存储或专用队列，而不是不断提高上限。

## 16. 清单是什么

`manifest.json` 是一个单一 JSON 文档：

```json
{
  "schema_version": 1,
  "record_count": 3,
  "record_ids": ["..."],
  "updated_at": "2026-08-26T00:00:00+00:00"
}
```

它快速说明当前记录集版本、数量、ID 与更新时间，不复制正文。它有独立严格 Schema：字段不能多缺、ID 不能重复、计数必须匹配列表。清单是派生信息，真正权威记录仍是经过验证的 JSONL。

## 17. 为什么清单恢复必须显式

两次文件替换之间进程可能中断：记录已切换、清单未切换。项目的 `load_manifest()` 遇到清单缺失直接报错；调用方必须显式执行 `recover_manifest()`，它从已验证记录重建清单并写入新快照。显式恢复让操作员知道发生了什么，也避免程序把损坏或未验证的文件“猜成正常状态”。

## 18. 端到端示例

```bash
cd "02_可运行项目/projects/07-polite-api-collector"
.venv/bin/python examples/store_demo.py
```

输出摘要如下，不含 payload 正文：

```json
{
  "duplicate_skipped": 1,
  "first_added": 1,
  "loaded_record_count": 1,
  "manifest_exists": true,
  "records_exists": true,
  "recovered_record_count": 1
}
```

该示例创建临时根目录，写入一页、重复写入、跨实例读取、删除清单、显式恢复，最后删除临时目录。它不访问网络、不使用真实秘密。

## 19. 日志与记录的隐私边界

```text
INFO collection_records_written added=1 skipped=0 total=1
INFO collection_manifest_recovered record_count=1
```

日志只记录计数与阶段；`payload` 不进入日志。存储文件本身包含数据，仍必须考虑来源是否允许保存、是否存在个人信息、保留多久、谁能读取、怎样删除、备份在哪里。脱敏日志不等于数据本身自动合规。

## 20. 失败矩阵

| 条件 | 当前行为 | 调用方下一步 |
|---|---|---|
| payload 含 NaN/任意对象 | `RecordSchemaError`，不写文件。 | 修正领域转换或拒绝上游。 |
| 单行/总文件过大 | `StorageLimitError`。 | 分页、分区、数据库或缩小范围。 |
| 记录 JSON 损坏 | 拒绝整个读取。 | 从可信备份/来源重新采集，或人工审查。 |
| 重复 ID | 拒绝现有损坏文件；新批次重复则跳过。 | 修复文件或定义版本策略。 |
| 清单缺失 | `StorageError`。 | 显式 `recover_manifest()`。 |
| 临时/替换 I/O 失败 | `StorageError`。 | 检查磁盘、权限、配额、文件系统；不可假装成功。 |

## 21. 测试是恢复设计的证据

项目当前的存储测试覆盖：写入并跨实例读取；第二次写入跳过相同记录；成功后无临时文件残留；清单丢失后的显式恢复；损坏 JSON 与重复 ID；NaN/非对象 payload；文件、单行、记录数量限制；日志不含正文；输出根目录不是目录时受控拒绝。这些测试并不证明硬盘永不坏，而是固定了程序在已建模故障下的可观察合同。

## 22. 快速测试（5 题）

1. 为什么不能向同一 `.json` 文件连续两次 `json.dump()` 后仍称其为有效单一 JSON 文档？
2. JSONL 的“一行一个对象”解决了什么边界，又没有解决什么安全问题？
3. 记录 ID 中为何包含 source、name、endpoint 和规范 payload？
4. 临时文件与 `os.replace()` 降低的具体风险是什么？
5. 为什么清单缺失时应显式恢复而不是自动静默重建？

**答案要点：** 1. JSON 不是带帧协议；2. 解决逐行边界，不解决可信、权限和资源限制；3. 让去重合同可解释；4. 降低主文件半写入风险；5. 避免把异常状态伪装成正常并保留操作痕迹。

## 23. 代码阅读（2 题）

1. 阅读 `_validate_json_value()` 与 `_strict_json()`，列出其对嵌套、键、浮点、列表、字典和未知 Python 对象的规则。为什么“`json.dumps()` 能跑”不能替代事前验证？
2. 阅读 `_atomic_write_text()` 的 `try/except/finally`。临时文件在成功、`os.replace()` 失败和清理失败时各处于什么状态？日志为何只写 cleanup 失败而不写文件内容？

## 24. Debug（2 题）

1. 手工向 `records.jsonl` 增加空行或缺少 `payload` 的对象，运行 `load_records()`；记录受控错误。恢复文件后说明为何读取器不应跳过“坏行继续读”。
2. 暂时删除 `_strict_json()` 中的 `allow_nan=False` 和有限浮点检查，写入 `math.nan`，再尝试用另一严格 JSON 工具读取。恢复严格检查，解释跨系统互操作性为何是存储合同的一部分。

## 25. 编程练习（3 题）、逆向设计与课后项目

**编程练习：** 1. 为记录增加固定 `content_type` 和 `schema_version`，设计向后兼容读取策略；写出未知版本、缺失版本和迁移后写回的测试。2. 增加“删除墓碑”记录，不直接删历史；定义同一 ID 的新增/删除冲突规则并写恢复测试。3. 实现只保存 payload 摘要、长度和经过审查字段的模式，保留可追溯 ID 但不持久化原文；证明日志与 JSONL 均不含原文。

**逆向设计：** 某采集器把所有响应 `repr()` 追加到一个 `.json` 文件；没有大小限制、字段验证、去重、临时文件或清单；错误时吞掉 `OSError` 并打印“已保存”；将 token、URL 参数、payload 写入日志；恢复时忽略无法解析行。请从 JSON 有效性、半写入、重复、隐私、来源、路径、容量、恢复、并发、版本、审计和 Agent 记忆污染至少倒推十二项风险，并为每项给出可测试合同。

**课后项目：** 完成“可恢复采集档案”。要求：为每个受审查来源建立固定根目录和 Schema；实现 JSONL 分区、清单、版本迁移、去重、删除墓碑和显式恢复计划；所有写入采用同目录临时文件、`fsync` 与替换策略；配置文件不能指定任意 Python callable、命令或输出路径；提供 Dry Run、备份、恢复 Runbook 和 ADR；为损坏 JSON、断点模拟、重复、容量、路径遍历、NaN、隐私字段与恢复操作写至少二十项测试；明确其仍不取代数据库事务、加密密钥管理或异地灾备。


### 本章项目映射

本章建议直接在 `02_可运行项目/projects/07-polite-api-collector/` 中完成可运行练习。先执行：追踪 JSONL、去重、清单、原子快照和显式恢复路径。

```bash
cd 02_可运行项目/projects/07-polite-api-collector && .venv/bin/python -m pytest
```

**主题化扩展：** 为损坏清单新增受控失败和显式恢复测试；报告只输出计数和状态，不输出采集正文。

完成后记录输入/输出合同、受控失败、测试命令和安全边界。不要把项目中的本地替身、测试夹具、回环服务或默认无执行模式误作真实网络、模型、生产数据、秘密、部署或副作用授权。

## 参考资料

[1]: https://docs.python.org/3/library/json.html "Python json documentation"
[2]: https://docs.python.org/3/library/pathlib.html "Python pathlib documentation"
[3]: https://docs.python.org/3/library/os.html#os.replace "Python os.replace documentation"
