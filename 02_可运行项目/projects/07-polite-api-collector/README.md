# 项目 7：受控 API 采集器

**版本：** 0.1.0  
**兼容性：** Python 3.11+  
**课程位置：** 模块 7——HTTP 客户端、超时、有限重试、连接池、礼貌并发采集、JSONL 记录与恢复

本项目实现了一个小而可审查的异步 JSON API 采集器。它只允许已声明 HTTPS 基址下的 `GET` 路径，使用明确连接/读取/写入/连接池超时，限制连接数与响应字节数，只对有限的可重试状态或传输失败重试，并把 HTTPX 细节映射为公开的采集错误。第二阶段增加 robots 技术预检、Semaphore、本地请求起始间隔、TaskGroup、固定 JSONL 快照、去重与可重建清单。

> **安全与礼貌边界：** 它不接受任意 HTTP 方法、任意协议、跨主机重定向、无限重试、无限响应、认证 token 命令行参数或日志正文。它当前不是通用爬虫、认证 SDK、浏览器自动化工具或绕过访问控制的手段。

| 合同项 | 当前行为 | 不做什么 |
|---|---|---|
| 目标 | `ClientPolicy` 要求 HTTPS 基址和主机允许列表。 | 不接受 `http`、任意绝对 URL 或跨主机路径。 |
| 请求 | 仅 `GET` JSON。 | 不向上游写入、删除或执行命令。 |
| 超时 | 显式 connect/read/write/pool 超时。 | 不用 `timeout=None` 掩盖卡死。 |
| 重试 | 仅 GET，最多有限次数；仅传输错误和 `408/429/500/502/503/504`。 | 不盲目重试 4xx、格式错误或本地配置错误。 |
| 响应 | 检查 JSON 内容类型、对象根节点和字节上限。 | 不无界读入内存或假定所有 `200` 都可解析。 |
| 日志 | 记录主机、路径、状态、重试尝试与错误类型。 | 不记录查询参数值、token、响应正文或秘密头。 |
| robots | 先在内存中以明确 User-Agent 预检固定端点。 | 不把 robots 当作授权、条款或隐私同意。 |
| 并发与节奏 | Semaphore 限制本地活动任务；Pacer 限制单站请求起始间隔。 | 不把本地并发上限等同于远端配额。 |
| 持久化 | 固定 `records.jsonl` 与 `manifest.json`；同目录临时写入、`fsync`、`os.replace`、去重和恢复。 | 不承诺多进程协调、跨设备原子性或灾难恢复。 |

## 安装与质量门禁

```bash
cd /home/ubuntu/python_private_course/projects/07-polite-api-collector
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"

.venv/bin/python -m pytest
.venv/bin/python -m mypy
.venv/bin/python -m ruff check src tests
```

当前有 **28 项 pytest**，并通过 mypy 与 Ruff。HTTP 客户端测试以 `httpx.MockTransport` 模拟上游行为，不访问公网；并发测试覆盖 robots 拒绝、Semaphore 上限、节奏、TaskGroup 失败联动和日志脱敏；存储测试覆盖固定 JSONL、去重、跨实例读取、清单恢复、严格 Schema、大小边界与临时文件清理。

## 单端点命令行运行

```bash
.venv/bin/course-api-collect \
  --base-url https://api.example.com \
  --endpoint /v1/records \
  --param page=1 \
  --verbose
```

成功时 JSON 只写到标准输出。日志只写标准错误。失败时程序输出下列公开错误并退出码为 `2`：

```json
{
  "error": {
    "code": "collection_failed",
    "message": "上游服务返回状态码 404。"
  }
}
```

命令行示例仅展示合同，不要求或建议对未知服务执行请求。使用真实 API 前，应取得授权，阅读其文档、条款、配额和隐私要求；不得用此项目绕过登录、付费墙、限流、访问控制或机器人限制。

## 客户端生命周期与超时

```python
policy = ClientPolicy(
    base_url="https://api.example.com",
    allowed_hosts=frozenset({"api.example.com"}),
    user_agent="my-reviewed-collector/1.0",
)
async with build_async_client(policy) as client:
    result = await SafeApiClient(client, policy).get_json("/v1/records")
```

HTTPX 建议在异步场景以 `async with httpx.AsyncClient()` 管理客户端；不要在热循环中建立多个客户端，否则无法充分复用连接池。[1] HTTPX 的超时分为 connect、read、write 和 pool 四类，默认网络不活动超时为五秒；本项目显式配置它们并将传输故障映射为受控错误。[2] HTTPX 的连接池大小可通过 `Limits` 限制，业务并发上限将在下一章以 `asyncio.Semaphore` 另行控制。[3]

## 重试边界

重试只是一种针对暂时性失败的策略，绝不是“请求失败就再发一次”。本项目只重试幂等的 GET 读取，并且仅处理 HTTPX 传输错误与可审查的 `408/429/500/502/503/504` 状态。`404`、未经允许的端点、非 JSON 内容、过大响应和格式错误会立即失败。HTTPX 将传输、超时和 HTTP 状态错误分为不同异常类别；`response.raise_for_status()` 会把 4xx/5xx 作为 `HTTPStatusError`。[4]

生产系统还应考虑 `Retry-After`、抖动、请求配额、幂等键、熔断、队列和人工升级；它们不能靠增加尝试次数替代。

## 路径、秘密与日志

`SafeApiClient` 在构造请求前检查端点必须是基址下以 `/` 开头的路径，拒绝协议相对路径和绝对跨主机 URL。它设置 `follow_redirects=False`，防止一次原本允许的请求因重定向悄悄越过主机边界。查询参数的键和值可用于 API 合同，但值从不写日志；token 应由受控秘密管理或环境注入提供，而不是放进 CLI、URL、README 或调试输出。

## 礼貌并发采集

`RobotsGuard` 只解析已获取的 robots 文本，并以 `can_fetch()` 预检固定路径；Python 标准库还可读取 `crawl_delay()`。[5] 项目把本地最小起始间隔与该值取较大者。`asyncio.Semaphore` 通过 `async with` 限制同一批次中活动读取数；它不用于线程同步，也不替代服务端配额或访问许可。[6]

```python
pages = await collect_pages(
    [PageRequest("catalog", "/v1/catalog")],
    fetcher=collector,
    crawl_policy=CrawlPolicy(max_concurrency=2, minimum_interval_seconds=1.0),
    robots_guard=guard,
)
```

相关页面在 `TaskGroup` 内运行；一页发生未处理错误时，兄弟任务会被取消并形成结构化失败。该默认“全批失败”策略适合完整目录快照；需要部分成功时，必须另外定义每项结果与错误 Schema。

## JSONL、去重与恢复

JSON 不是带帧协议：对同一文件重复调用 `json.dump()` 会形成无效 JSON。项目因此使用“一行一个完整对象”的 `records.jsonl`，并以固定字段 `id/source/name/endpoint/collected_at/payload` 读取和验证。[7] 相同来源、名称、端点与规范 payload 产生同一 SHA-256 记录 ID；重复批次只统计跳过，不重复写入。

写入先在输出根目录同一目录创建临时文件、写入、`flush`、`fsync`，随后用 `os.replace()` 更新固定记录/清单路径。该方法降低主文件半写入风险，但不保证磁盘耗尽、多进程同时写、跨文件系统或灾难恢复。清单缺失时，调用方必须显式运行 `recover_manifest()`，由已验证 JSONL 重建它；不会静默猜测损坏数据。

```python
store = CollectionStore(Path("collected"))
result = store.append_pages(pages, source="approved-catalog")
# result 只含 added、skipped_duplicates、total_records，不含正文日志。
```

## 目录结构

```text
07-polite-api-collector/
├── pyproject.toml
├── README.md
├── .gitignore
├── .github/workflows/quality.yml
├── src/polite_api_collector/
│   ├── __init__.py
│   ├── client.py
│   ├── crawler.py
│   ├── store.py
│   └── cli.py
└── tests/
    ├── test_client.py
    ├── test_crawler.py
    └── test_store.py
```

## 参考资料

[1]: https://www.python-httpx.org/async/ "HTTPX: Async Support"
[2]: https://www.python-httpx.org/advanced/timeouts/ "HTTPX: Timeouts"
[3]: https://www.python-httpx.org/advanced/resource-limits/ "HTTPX: Resource Limits"
[4]: https://www.python-httpx.org/exceptions/ "HTTPX: Exceptions"
[5]: https://docs.python.org/3/library/urllib.robotparser.html "Python urllib.robotparser documentation"
[6]: https://docs.python.org/3/library/asyncio-sync.html "Python asyncio synchronization primitives"
[7]: https://docs.python.org/3/library/json.html "Python json documentation"
