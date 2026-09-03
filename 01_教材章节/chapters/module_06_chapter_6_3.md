# 第 6.3 章：数据库不是字典文件——SQLite、事务与持久化边界

**适用版本：** Python 3.11+  
**项目连接：** `02_可运行项目/projects/06-knowledge-api/`（版本 0.2.0）

## 1. 本章目标

完成本章后，你能够解释内存数据为什么在服务重启后消失；能把资源模型映射为最小 SQLite 表；能用 `?` 占位符绑定数据；能区分提交、回滚、关闭、备份与恢复；能把数据库错误限制在仓储层并映射为公开 API 错误；能验证跨进程重启后的真实持久化。

## 2. 先纠正一个误解：数据库不是“更大的字典”

字典是当前 Python 进程的内存对象；进程结束，它通常就消失。数据库是由数据库引擎管理的持久化状态，提供受约束的表、查询、事务和恢复接口。SQLite 是嵌入式、基于磁盘的数据库，不需要额外服务进程，适合本课程单节点、小规模服务的第一步。[1] 它不是分布式数据库，也不会自动解决身份隔离、备份留存、跨节点高可用或任意并发写入。

## 3. 从生产级 Agent 倒推

Agent 的记忆、任务状态、工具调用记录、评测样本和人工审批都需要持久化。但“写入数据库”不等于“已有记忆系统”：必须说明谁能写、什么 Schema 可写、何时提交、如何重试、错误如何暴露、哪些内容不得入日志、如何删除与恢复。本章的笔记表故意很小，目的是先证明**状态边界**，不是把数据库误称为 Agent。

## 4. 从 API 资源到数据表

第 6.1–6.2 章的资源是 `Note(id, title, content)`。项目 6 的最小表如下：

```sql
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 100),
    content TEXT NOT NULL CHECK (length(trim(content)) BETWEEN 1 AND 2000)
)
```

| 层 | 约束 | 目的 |
|---|---|---|
| Pydantic `NoteCreate` | 字段、去空白、长度、拒绝额外字段。 | 尽早向 HTTP 客户端返回 `422`。 |
| SQLite `NOT NULL` / `CHECK` | 标题与正文不可为空且长度受限。 | 防止绕开 API 的调用把明显脏数据写入表。 |
| 仓储对象 | 固定 SQL、参数绑定、事务、行到领域对象映射。 | 避免 HTTP 层直接操作驱动。 |
| API 错误处理器 | `404`、`422`、`503` 的公开合同。 | 不返回 SQL、文件路径、驱动栈或请求正文。 |

重复约束不是浪费：每层面对不同入口和失败时机。

## 5. Schema 是已审查的状态合同

项目把 DDL 固定在 `SqliteNoteRepository._SCHEMA_SQL`，仅使用 `CREATE TABLE IF NOT EXISTS`。这让首次启动能创建当前 schema，重复启动不会删除数据。它不等于通用迁移系统：真实产品的 schema 演进还需要版本号、升级步骤、回退策略、数据迁移、备份和演练。本书在以后章节才增加这些复杂度；不要让应用启动时根据用户输入拼接或执行 DDL。

## 6. 数据值必须通过占位符绑定

```python
# 文件：02_可运行项目/projects/06-knowledge-api/src/knowledge_api/core.py
cursor = connection.execute(
    "INSERT INTO notes (title, content) VALUES (?, ?)",
    (title, content),
)
```

`?` 是 qmark 参数占位符。SQL 文本定义已审查的操作，参数元组提供数据；驱动负责把二者分开。Python 官方文档明确建议始终用占位符而不是字符串格式化绑定 Python 值，以避免 SQL 注入。[1]

```python
# 错误：用户文本改变 SQL 语法，而不是仅作为数据传入。
connection.execute(f"INSERT INTO notes (title) VALUES ('{title}')")
```

占位符不能替代所有验证：表名、列名、`ORDER BY` 方向和 SQL 关键字不能作为 `?` 参数，因此必须由代码中的固定允许列表决定。

## 7. 参数化的真实验收

项目测试将带引号、分号和看似 SQL 的标题作为普通文本保存，然后读取并确认表仍存在：

```python
suspicious_title = "标题'); DROP TABLE notes; --"
created = repository.create(title=suspicious_title, content="它只能作为文本保存。")
assert repository.get(created.id).title == suspicious_title
assert len(repository.list_all()) == 1
```

测试并不是鼓励使用危险字符串，而是验证数据与命令边界没有被破坏。代码审查还应检查没有用 f-string、`%` 或 `.format()` 拼接未验证 SQL。

## 8. 事务回答“要么怎样，要么怎样”

事务（transaction）把一组状态改变作为一个边界：成功时一起提交，失败时回到开始前状态。项目的单条创建虽只有一条 `INSERT`，仍使用显式写入边界，因为以后同一操作可能同时写笔记、标签、审计元数据和状态转换。没有事务，半完成状态会成为未来故障的种子。

| 结果 | 项目行为 | 客户端可见结果 |
|---|---|---|
| `INSERT` 成功且提交成功 | 新 ID 写入数据库。 | `201` 与公开笔记。 |
| 约束或驱动异常 | 回滚当前写事务、关闭连接。 | `503 storage_unavailable`，无 SQL 细节。 |
| 找不到已提交的 ID | 不构成数据库故障。 | `404 note_not_found`。 |
| HTTP 输入不符合模型 | 不应到达写事务。 | `422 invalid_request`。 |

## 9. 显式写入边界

```python
@contextmanager
def _write_transaction(self) -> Iterator[sqlite3.Connection]:
    connection = self._connect()
    try:
        connection.execute("BEGIN IMMEDIATE")
        yield connection
    except Exception:
        connection.rollback()
        raise
    else:
        connection.commit()
    finally:
        connection.close()
```

此处代码做出明确教学选择：先开启写事务，业务代码正常返回才提交，任一异常都回滚，最后无论如何都关闭连接。Python 文档说明 `commit()` 提交待定事务，`rollback()` 回到事务开始处；关闭前是否提交会影响未提交修改的保存。[1] 不要把“代码没有报错”误当作“数据已经持久化”。

## 10. `BEGIN IMMEDIATE` 不是并发魔法

项目显式使用 `BEGIN IMMEDIATE`，让写操作的锁竞争在事务起点暴露，而非在最后一个语句才意外失败。它不让 SQLite 变成多节点写入数据库，也不证明吞吐量。`sqlite3.connect()` 有锁等待 `timeout`；在等待期后锁仍未释放会出现 `OperationalError`。[1] 本仓储把该类底层 `DatabaseError` 包装为 `StorageError`，交由 API 映射为暂不可用的 `503`。

## 11. 连接、事务与关闭是三件事

| 概念 | 它管理什么 | 本项目的规则 |
|---|---|---|
| 连接 | Python 与数据库文件/引擎的一次会话。 | 每个仓储操作新建并 `close()`。 |
| 事务 | 一组读写的提交或回滚边界。 | 写操作显式开始、提交或回滚。 |
| 上下文管理器 | Python 的资源清理语法。 | 自定义上下文管理器确保连接关闭。 |
| 备份 | 另一个可用于恢复的副本。 | `backup_to()` 显式创建，不能取代事务。 |

Python 文档指出，连接对象可作为事务上下文使用，但上下文退出并不自动关闭连接；连接仍应显式关闭。[1] 因此本项目不把 `with connection:` 误写成“自动关闭一切”。

## 12. 为什么不共享全局 SQLite 连接

默认 SQLite 连接有线程限制：跨创建线程使用同一连接会出错；即使允许跨线程，写入仍要由应用自行序列化以避免损坏。[1] FastAPI 的同步路径操作可能运行在不同线程，故项目不创建一个模块级连接给所有请求使用。`get_store()` 为每个请求构造仓储，而仓储的每次公共操作再独立连接、提交/回滚并关闭。

这不是最高性能方案，而是最容易向初学者说明生命周期、测试和错误边界的方案。连接池、异步驱动或外部数据库必须在压测与观测证据支持下引入。

## 13. 仓储协议隔离框架

```python
class NoteRepository(Protocol):
    def create(self, *, title: str, content: str) -> Note: ...
    def list_all(self) -> list[Note]: ...
    def get(self, note_id: int) -> Note: ...
```

路径操作依赖 `NoteRepository`，而非 `sqlite3.Connection`。HTTP 测试可用 `NoteStore` 覆盖依赖；仓储测试直接验证 `SqliteNoteRepository`。这种分层不会让数据库消失，但避免 FastAPI 路由、SQL 字符串、事务和 JSON Schema 被绑成无法替换的一团。

## 14. 从一行数据库记录到领域对象

SQLite 行不应直接变成 API JSON。项目的 `_row_to_note()` 检查 `id`、`title` 和 `content` 的运行时类型，再构造不可变 `Note`；`api.py` 的 `_note_response()` 再选择公开输出字段。这样当数据库 schema 被外部工具修改、迁移不完整或数据损坏时，错误能在仓储边界发生，而不是悄悄把不可信对象传到 HTTP 层。

## 15. 存储错误不是客户端输入错误

`StorageError` 代表锁竞争、磁盘错误、数据库损坏或初始化失败等服务端问题。它的公开映射为：

```json
{
  "error": {
    "code": "storage_unavailable",
    "message": "笔记存储暂时不可用，请稍后重试。"
  },
  "request_id": "..."
}
```

调用方可依据 `503` 采取有限、带退避的重试策略；它不能据此猜测 SQL、磁盘路径或内部异常。服务端日志也应以请求 ID、错误类别和受控元数据关联根因，而非写入笔记正文。

## 16. 备份能做什么，不能做什么

```python
backup_path = repository.backup_to(tmp_path / "backups" / "notes-backup.sqlite3")
restored_repository = SqliteNoteRepository(backup_path)
assert restored_repository.get(created.id) == created
```

`Connection.backup()` 把一个 SQLite 连接的内容复制到另一个连接。[1] 项目将其封装为显式 `backup_to()` 并测试副本可独立读取。它**不能**证明备份按时执行、保存到异地、得到加密、满足保留期、能在事故中恢复，或不受恶意覆盖。生产恢复需要备份策略、访问控制、恢复时间目标和定期恢复演练。

## 17. 数据库路径是配置，不是用户 API 参数

项目只读取 `COURSE_KNOWLEDGE_API_DB` 环境变量来选择本地 SQLite 路径，缺失时使用 `data/knowledge-api.sqlite3`。路径并不由 HTTP 请求决定；客户端不能通过 JSON 指向任意数据库文件。它遵循模块 5 的配置原则：配置只能在代码审查的行为集合中选择，不得变成任意模块、命令、SQL 或 callable 的入口。

```bash
COURSE_KNOWLEDGE_API_DB="./data/notes.sqlite3" \
  .venv/bin/course-notes-api --host 127.0.0.1 --port 8000
```

部署时还应限制进程的文件系统权限，避免默认路径落在不受控或可公开下载的位置。

## 18. 跨重启验收比“本次请求成功”更强

项目的端到端验收按以下顺序执行：以临时数据库路径启动本地 API；创建笔记；停止服务器；以**同一路径**重新启动；读取 `/notes/1`；再读取不存在 ID 并确认 `404`。这证明提交后的数据越过了进程生命周期，而不是仍在全局字典中。它不证明并发压力、磁盘满、损坏恢复或升级迁移已安全。

## 19. 数据库测试金字塔

| 测试层 | 示例 | 主要证明 |
|---|---|---|
| 领域/仓储测试 | `test_sqlite_repository.py`。 | 参数化文本、事务回滚、备份恢复、缺失错误、路径配置。 |
| HTTP 合同测试 | `test_api.py` 加依赖覆盖。 | 201、404、422、请求 ID、公开错误与脱敏日志。 |
| 本地端到端 | 服务器重启后读取同一 SQLite 文件。 | 安装命令、环境变量、进程边界和真实 HTTP 接线。 |
| 未来负载/恢复测试 | 锁竞争、磁盘故障、迁移、备份恢复演练。 | 本章未宣称完成，必须单独设计。 |

当前项目 6 共 17 项 pytest，另通过 mypy 与 Ruff。数字是当前合同的覆盖证据，不是安全、性能或可用性评分。

## 20. 失败案例：把客户端文本拼进 SQL

```python
sql = f"SELECT id, title FROM notes WHERE title = '{query}'"
row = connection.execute(sql).fetchone()
```

问题不只是“有人会输入单引号”。代码把数据与命令混为一体，使调用方可能改变语句结构；日志、调试输出和错误页也可能进一步暴露 SQL。修复不是写更多黑名单，而是固定 SQL 结构、使用占位符绑定数据、限制可选标识符、测试特殊字符，并把驱动异常封装为领域可理解的 `StorageError`。

## 21. 本章验收

```bash
cd "02_可运行项目/projects/06-knowledge-api"
.venv/bin/python -m pytest
.venv/bin/python -m mypy
.venv/bin/python -m ruff check src tests
```

然后以 `COURSE_KNOWLEDGE_API_DB` 指向临时文件启动服务，创建一条笔记，停止并重启服务，读取同一 ID。最后运行 `test_backup_can_be_read_as_an_independent_database`，解释“副本可读”与“已经具备生产灾备”之间还缺少哪些证据。

## 22. 快速测试（5 题）

1. 为什么 SQLite 表的 `CHECK` 约束不能取代 Pydantic 验证？
2. 为什么 SQL 数据值应使用 `?` 占位符，而表名不能直接作为 `?`？
3. `commit()`、`rollback()` 与 `close()` 各解决什么问题？
4. 为什么 API 不共享一个全局 SQLite 连接？
5. 为什么 `backup_to()` 不是完整灾难恢复方案？

**答案要点：** 1. 两层面对不同入口和错误体验；2. 占位符绑定值而非 SQL 语法标识符；3. 成功持久化、失败撤销、释放连接资源；4. 线程和生命周期边界不安全且难测；5. 还缺策略、权限、留存、异地副本和恢复演练。

## 23. 代码阅读（2 题）

1. 阅读 `_write_transaction()`，逐行说明 `try`、`except`、`else` 和 `finally` 怎样区分回滚、提交和关闭；如果把 `connection.commit()` 移到 `finally`，约束失败后会发生什么？
2. 阅读 `get_store()` 与 `SqliteNoteRepository._connect()`，指出数据库路径从哪里来、连接何时创建、何时关闭。说明为何 HTTP JSON 中没有数据库路径字段。

## 24. Debug（2 题）

1. 将 `INSERT ... VALUES (?, ?)` 暂时改为 f-string 拼接，运行特殊字符标题测试并观察失败或风险；恢复占位符，再补一项含双引号和 Unicode 的测试。
2. 在 `_write_transaction()` 中临时注释 `connection.rollback()`，让一个违反 `CHECK` 的写入后继续执行读取测试。记录异常与数据状态，再恢复回滚并说明“碰巧没有脏数据”为什么不是可靠设计。

## 25. 编程练习（3 题）、逆向设计与课后项目

**编程练习：** 1. 为 `notes` 增加 `created_at` 字段。定义由谁生成、时区和公开格式；写 schema 初始化、领域映射、输出模型、至少六项迁移前后/读取排序测试。2. 实现 `DELETE /notes/{id}`：仓储层使用参数化 `DELETE`，以受影响行数判断缺失，HTTP 成功返回恰当状态码；写事务、404、重启后确认删除和日志脱敏测试。3. 实现受控 `GET /notes?limit=N&offset=N`：仅接受整数边界，固定 `ORDER BY id ASC`，参数绑定 `LIMIT` 与 `OFFSET`，测试分页没有重叠且不允许客户端指定任意排序字段。

**逆向设计：** 一份“快速数据库 API”让客户端提交 `{"sql": "..."}`；用 f-string 拼 SQL；每个请求共享全局连接且 `check_same_thread=False`；所有异常原样返回；每晚直接复制数据库文件但从不验证；日志记录完整 body。请从注入、权限、线程、事务、锁、数据损坏、隐私、备份、恢复、审计、Agent 工具边界和评测可重现性至少倒推十二项故障，并为每项提出一个可测试修复。

**课后项目：** 把项目 6 升级为“可恢复笔记服务”。要求：制定 schema 版本表和显式升级函数；为每次迁移记录版本、时间与摘要；实现只允许管理员本地 CLI 调用的备份命令（不能经公开 HTTP 暴露任意路径）；提供一个从备份副本启动测试服务的恢复演练；以 README/Runbook 说明数据库文件权限、备份频率、保留期假设、恢复步骤与未覆盖风险；新增至少十五项测试，并保证 pytest、mypy、Ruff 与 Python 3.11/3.12 CI 通过。


### 本章项目映射

本章建议直接在 `02_可运行项目/projects/06-knowledge-api/` 中完成可运行练习。先执行：追踪 SQLite 仓储、参数化查询、事务与备份恢复测试，理解持久化的提交/回滚边界。

```bash
cd 02_可运行项目/projects/06-knowledge-api && .venv/bin/python -m pytest
```

**主题化扩展：** 为一次写入失败补充回滚断言；不要直接拼接 SQL 或将数据库路径/正文写入公开错误。

完成后记录输入/输出合同、受控失败、测试命令和安全边界。不要把项目中的本地替身、测试夹具、回环服务或默认无执行模式误作真实网络、模型、生产数据、秘密、部署或副作用授权。

## 参考资料

[1]: https://docs.python.org/3/library/sqlite3.html "Python sqlite3 documentation"
[2]: https://sqlite.org/lang_transaction.html "SQLite Transaction documentation"
