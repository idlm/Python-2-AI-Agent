# 模块 6 官方资料核对笔记

**核对日期：** 2026-08-26（GMT+8）  
**用途：** 为模块 6 的 HTTP/API、数据库与异步服务章节建立可引用的事实边界；面向 Python 3.11+ 初学者。

| 主题 | 已核对结论 | 教材使用边界 | 来源 |
|---|---|---|---|
| FastAPI 路径操作 | `FastAPI()` 实例以 `@app.get()`、`@app.post()` 等装饰器把 HTTP 方法和 URL 路径关联到 Python 函数；框架可生成 OpenAPI JSON、`/docs` 和 `/redoc` 文档。 | 先讲 HTTP 方法、路径、输入、输出和状态码，再引入框架；不把自动文档误写成安全或业务正确性证明。 | [1] |
| 请求体与模型 | 请求体是客户端发送给 API 的数据；使用 Pydantic `BaseModel` 声明后，FastAPI 读取 JSON、验证数据并把模型 Schema 放进 OpenAPI。 | 对每个输入模型限定字段、长度和范围；输出模型与输入模型可分开，避免把内部字段或秘密回显给客户端。 | [2] |
| HTTP 错误 | `HTTPException` 应以 `raise` 终止当前请求并产生 HTTP 错误响应；4xx 表示客户端请求存在问题。 | 领域层抛受控业务异常，边缘层映射为稳定状态码和无敏感细节的 `detail`；不把 Traceback 或原始请求体返回给客户端。 | [3] |
| 依赖注入 | FastAPI 依赖可共享数据库连接、认证、权限、公共查询参数等逻辑，且其输入要求会纳入 OpenAPI。 | 依赖只提供明确资源或校验，不把业务规则、全局状态和任意配置混成“万能 Depends”。 | [4] |
| SQLite 连接与参数化 | `sqlite3.connect()` 打开数据库；写入须提交；`?` 占位符绑定 Python 值，官方明确建议始终用占位符而不是字符串格式化以防 SQL 注入。 | 模块 6 先以受控 SQLite 演示表、事务和参数化查询；表名和排序字段不从未验证用户输入拼接。 | [5] |
| SQLite 事务与锁 | `commit()` 提交待定事务；若关闭前未提交可能丢失改动。连接默认遇到锁会等待，默认约 5 秒后抛 `OperationalError`；跨线程共享连接时写入需由用户序列化。 | 单进程教学项目的每请求连接/事务边界必须明确；不把 SQLite 说成任意高并发写入场景的完整方案。 | [5] |
| asyncio 并发 | asyncio 用 `async`/`await` 写并发 I/O；直接调用协程不会执行，需 `await`、`asyncio.run()` 或任务调度。 | 先解释等待 I/O 与 CPU 计算的差异；不可用 `async` 包装阻塞文件、数据库或 CPU 工作后就宣称已并发。 | [6] [7] |
| 结构化并发与超时 | Python 3.11 的 `asyncio.TaskGroup` 在退出时等待子任务，并在非取消失败时取消剩余任务并组合异常；`asyncio.timeout()` 会在超时后把内部取消转换为可在上下文外捕获的 `TimeoutError`。 | 模块 6 需要有明确超时、取消和清理语义；不要吞掉 `CancelledError`，不做无引用的“fire-and-forget”任务。 | [6] |

## 初步章节落点

| 候选章节 | 核心问题 | 最小可运行证据 |
|---|---|---|
| 6.1 | HTTP、资源、路径、方法、状态码与 JSON 边界是什么？ | 一个不依赖网络的请求/响应模型示例与测试。 |
| 6.2 | FastAPI 如何把输入模型、路径操作、错误映射和 API 文档组合起来？ | 一个小型 API 的 `TestClient` 测试，不要求启动长期服务器。 |
| 6.3 | 为什么 JSON 文件不再适合并发服务；SQLite 的表、事务、参数化和连接边界怎样设计？ | SQLite 临时数据库 CRUD、回滚与注入防护测试。 |
| 6.4 | `async`、并发、超时、取消和 TaskGroup 如何不被神化？ | 可控协程、超时与取消测试；不使用真实公网依赖。 |

## 引用链接

[1]: https://fastapi.tiangolo.com/tutorial/first-steps/ "FastAPI: First Steps"
[2]: https://fastapi.tiangolo.com/tutorial/body/ "FastAPI: Request Body"
[3]: https://fastapi.tiangolo.com/tutorial/handling-errors/ "FastAPI: Handling Errors"
[4]: https://fastapi.tiangolo.com/tutorial/dependencies/ "FastAPI: Dependencies"
[5]: https://docs.python.org/3/library/sqlite3.html "Python sqlite3 documentation"
[6]: https://docs.python.org/3/library/asyncio-task.html "Python asyncio coroutines and tasks documentation"
[7]: https://docs.python.org/3/library/asyncio.html "Python asyncio overview"

## SQLite 持久化补充核对

| 主题 | 已核对结论 | 教材使用边界 | 来源 |
|---|---|---|---|
| 参数占位符 | `sqlite3` 支持 `?`（qmark）和命名占位符；官方明确要求用占位符绑定 Python 值，而不是用字符串格式化 SQL，以避免 SQL 注入。 | 用户提供的标题、正文、ID、查询值必须作为参数元组或映射传给 `execute()`；表名、列名与排序方向仍须由代码固定允许列表选择。 | [5] |
| 提交、回滚与关闭 | 写入需要明确 `commit()` 才持久化；未提交变更在特定事务模式下关闭连接会回滚。`Connection.close()` 不能替代明确事务设计。 | 项目 6 将一条仓储写操作置于明确事务中；异常路径回滚，成功路径提交并关闭连接。 | [5] |
| 连接上下文 | `Connection` 可作为事务上下文使用，但不自动关闭连接；较新的 Python 还会在未关闭连接被删除时产生 `ResourceWarning`。 | 教材使用自定义上下文管理器或 `try/finally` 负责关闭连接，不把 `with connection:` 误教成自动关闭。 | [5] |
| 线程与锁 | 默认 `check_same_thread=True`，跨线程使用同一连接会引发 `ProgrammingError`；设为 `False` 后写入仍须用户自行序列化。连接默认在表被锁时等待，默认约五秒后抛 `OperationalError`。 | API 不共享一个全局 SQLite 连接；每次仓储操作创建和关闭独立连接，并把锁/磁盘错误转为受控服务端错误而非客户端细节。 | [5] |
| 备份 | `sqlite3.Connection.backup()` 可把一个连接的数据库复制到另一个连接；备份属于恢复机制的一部分，不替代事务、访问控制或异地灾备。 | 课内仓储提供显式本地备份方法和测试；不承诺生产灾难恢复、加密或多节点一致性。 | [5] |

> **版本提醒：** Python 3.12 的 `sqlite3.connect()` 增加了 `autocommit` 参数，默认仍处于旧式事务控制，且官方说明未来默认会改变。教材不依赖默认值：项目代码显式界定每个写入的提交、回滚与关闭。[5]
