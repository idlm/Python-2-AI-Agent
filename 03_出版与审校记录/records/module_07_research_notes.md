# 模块 7 官方资料核对笔记

**核对日期：** 2026-08-26（GMT+8）  
**用途：** 为模块 7 的 API 客户端、重试、限速、分页、并发采集与数据持久化章节建立可引用事实边界；面向 Python 3.11+ 初学者。

| 主题 | 已核对结论 | 教材使用边界 | 来源 |
|---|---|---|---|
| HTTPX 异步客户端 | HTTPX 同时支持同步 API 与 `AsyncClient`；异步请求方法须以 `await` 调用。`AsyncClient` 可作为异步上下文管理器，负责关闭客户端资源。 | 一次采集批次复用一个受控 `AsyncClient`，在其外层 `async with` 关闭；不在热循环中反复新建客户端。 | [1] |
| 连接池 | HTTPX 客户端复用底层 TCP 连接；官方特别提醒，为获得连接池收益不要在热循环中建立多个客户端。 | 客户端生命周期与批次/服务生命周期一致；要用并发限制，而不是“每 URL 一个新客户端”。 | [1] [4] |
| 网络超时 | HTTPX 默认在网络不活动五秒后抛 `TimeoutException`；可分别设置 connect、read、write 与 pool 超时。 | 代码显式设置时间预算，分别记录超时类别；不写 `timeout=None` 作为“解决失败”的方式。 | [2] |
| 资源限制 | `httpx.Limits` 可设 `max_connections`、`max_keepalive_connections` 与 keep-alive 到期时间；文档的默认连接上限为 100、保持连接默认 20、空闲到期默认 5 秒。 | 连接池限制与业务并发限制分开教学；采集器将明确配置保守上限，而不依赖默认或无限制。 | [3] |
| HTTPX 异常 | `TimeoutException`、`NetworkError`、`ProtocolError` 等属于请求/传输问题；调用 `response.raise_for_status()` 后 4xx/5xx 为 `HTTPStatusError`。 | 重试只针对经定义的短暂失败类别；4xx、格式错误、robots 拒绝和大小超限不可盲目重试。 | [5] |
| Semaphore | `asyncio.Semaphore` 维护不能低于零的计数；为零时获取者等待。推荐以 `async with semaphore` 确保释放。异步同步原语不用于 OS 线程同步。 | 每个采集批次使用 `async with` 保护并发配额；它限制本地并发，不等于对目标站的法律许可或礼貌策略。 | [6] |
| robots.txt | `urllib.robotparser.RobotFileParser` 可解析 robots 文件；`can_fetch(useragent, url)` 给出该文件规则下是否允许；还可读取 `crawl_delay`、`request_rate` 与站点地图。 | 抓取器先以明确 User-Agent 检查规则；robots 规则是技术许可信号，不替代网站条款、版权、隐私、认证、付费墙或访问控制审查。 | [7] |

## 初步章节落点

| 候选章节 | 核心问题 | 最小可运行证据 |
|---|---|---|
| 7.1 | 怎样设计不会盲目重试、不会泄露 token 的 HTTP 客户端合同？ | 以 `httpx.MockTransport` 测试状态、超时、重试和日志脱敏。 |
| 7.2 | 怎样在并发采集时同时管理连接池、Semaphore、限速、响应大小、robots 和分页？ | 使用确定性假 transport 的受控采集器测试。 |
| 7.3 | 采集结果怎样以受控 JSONL/SQLite 记录，支持恢复、去重和审计？ | 固定 Schema、原子写入、恢复与失败测试。 |

## 引用链接

[1]: https://www.python-httpx.org/async/ "HTTPX: Async Support"
[2]: https://www.python-httpx.org/advanced/timeouts/ "HTTPX: Timeouts"
[3]: https://www.python-httpx.org/advanced/resource-limits/ "HTTPX: Resource Limits"
[4]: https://www.python-httpx.org/advanced/clients/ "HTTPX: Clients"
[5]: https://www.python-httpx.org/exceptions/ "HTTPX: Exceptions"
[6]: https://docs.python.org/3/library/asyncio-sync.html "Python asyncio synchronization primitives"
[7]: https://docs.python.org/3/library/urllib.robotparser.html "Python urllib.robotparser documentation"

## 持久化与恢复补充核对

| 主题 | 已核对结论 | 教材使用边界 | 来源 |
|---|---|---|---|
| JSON 资源边界 | Python `json` 文档警告：解析不可信 JSON 可能消耗大量 CPU 和内存，建议限制待解析数据大小。 | 项目 7 在网络边缘限制响应字节数；本地记录读取仍限制单行和文件大小，并验证固定 Schema。 | [8] |
| JSON 不是多对象文件格式 | Python 文档明确指出 JSON 不是带帧协议；对同一文件重复调用 `json.dump()` 会形成无效 JSON 文件。 | 追加记录使用“一行一个完整对象”的 JSONL 合同；快照清单仍使用单一完整 JSON 文档并原子替换。 | [8] |
| JSON 严格输出 | `json.dumps(..., allow_nan=False)` 会对 NaN、Infinity、-Infinity 抛 `ValueError`，避免默认 JavaScript 扩展值。 | 采集记录要求严格 JSON、字符串键、固定字段与受限标量/容器；不能把任意 Python 对象直接序列化。 | [8] |
| 文件替换 | Python `os` 文档说明操作系统接口可能因不可访问路径等抛 `OSError`；`os.replace()` 是替换目标路径的接口。 | 先在同目录写入、flush 与 `fsync` 临时文件，再以 `os.replace` 更新快照；捕获并包装 I/O 错误。该策略降低半写入风险，但不保证跨设备、并发多进程或灾难恢复。 | [9] |
| 路径词法边界 | `pathlib.PurePath` 对 `..` 和双前导斜杠不会随意折叠，因为会改变符号链接或 UNC 等语义；`Path.resolve()` 才访问文件系统并解析。 | 输出根目录以 `resolve()` 后的祖先关系验证；不使用字符串前缀或简单拼接判断文件是否在受控目录内。 | [10] |

[8]: https://docs.python.org/3/library/json.html "Python json documentation"
[9]: https://docs.python.org/3/library/os.html#os.replace "Python os.replace documentation"
[10]: https://docs.python.org/3/library/pathlib.html "Python pathlib documentation"
