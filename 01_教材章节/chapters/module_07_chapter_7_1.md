# 第 7.1 章：调用 API 不是“请求一下”——受控客户端、超时与有限重试

**适用版本：** Python 3.11+  
**项目连接：** `projects/07-polite-api-collector/`（版本 0.1.0）

## 1. 本章目标

完成本章后，你能够解释 API 客户端的职责；能为 HTTPS 主机、方法、路径、超时、连接池、响应大小和 JSON 形状写出合同；能区分传输错误、上游状态错误和本地输入错误；能只对审查过的幂等读取执行有限重试；能避免 URL、查询参数、token 和响应正文进入日志。

## 2. 先纠正一个误解：HTTP 客户端不是一行 `get()`

`httpx.get(url)` 可以用于一次实验，但可维护客户端还需要回答：允许访问哪个主机？用哪种协议与方法？请求可以等多久？连接数多少？失败哪些可重试？结果多大？内容是什么类型？日志记录什么？谁关闭连接？这些问题的答案共同构成**出站 API 合同**，而不是某个库的默认设置。

## 3. 从生产级 Agent 倒推

Agent 的工具调用常常就是出站 HTTP：模型请求、搜索、企业系统、网页提取、向量服务和人工审批都可能在网络另一端。Agent 不是 HTTPX、LangChain 或任何框架；它需要模型、工具、记忆、状态、工作流与评测。若工具客户端允许任意 URL、无限重试或泄露 token，后续接入模型只会扩大攻击面和成本。本章先让一个普通 API 客户端具备可审查边界。

## 4. 项目 7 的最小合同

| 合同维度 | `07-polite-api-collector` 当前规则 | 被拒绝的做法 |
|---|---|---|
| 协议与主机 | HTTPS 基址，主机必须在 `allowed_hosts`。 | `http`、跨主机绝对 URL、协议相对 URL。 |
| 方法 | 仅 `GET` JSON。 | 未审查的 `POST`、`DELETE` 或任意动词。 |
| 生命周期 | 一个批次复用一个 `AsyncClient` 并以 `async with` 关闭。 | 热循环中每 URL 新建客户端。 |
| 超时 | connect/read/write/pool 均显式设置。 | 把 `timeout=None` 当成修复。 |
| 重试 | 有限次数；仅 GET 的传输失败与约定状态。 | 对所有异常、所有 4xx 或所有写入盲目重试。 |
| 响应 | JSON 内容类型、对象根节点和最大字节数。 | 无界读内存、假定 `200` 必定是所需数据。 |
| 日志 | 主机、路径、状态、尝试与错误类型。 | 查询值、token、响应正文或秘密头。 |

## 5. 从基址到端点

```python
policy = ClientPolicy(
    base_url="https://api.example.com",
    allowed_hosts=frozenset({"api.example.com"}),
    user_agent="my-reviewed-collector/1.0",
)
```

基址不是用户请求中随意提交的 URL。`ClientPolicy` 在构造时检查协议必须为 HTTPS、主机非空且在允许列表中。具体端点还必须是基址下以 `/` 开头的路径；`//other.example.test/...` 和 `https://other.example.test/...` 都会被拒绝。这样，调用方只能在代码审查过的目标范围内选择资源，不能让配置或上游数据变成服务端请求伪造（SSRF）入口。

## 6. 路径、查询参数与秘密的不同责任

路径选择一个已审查资源，例如 `/v1/records`；查询参数表达该资源合同允许的筛选、分页或格式，例如 `page=1`。两者都不是认证秘密。token、cookie、私钥和客户数据不应出现在 URL、命令行、README、异常信息或普通日志中。下一章会加入分页和限速；认证则必须等到有明确秘密管理与权限模型时再设计。

## 7. 为什么复用 `AsyncClient`

```python
async with build_async_client(policy) as client:
    collector = SafeApiClient(client, policy)
    result = await collector.get_json("/v1/records")
```

HTTPX 提供 `AsyncClient` 进行异步请求，并建议以异步上下文管理器管理关闭。[1] 其文档特别提醒，不要在热循环中创建多个客户端，否则无法获得连接池复用收益。[1] 因此客户端是批次或服务生命周期的资源，不是每个 URL 的临时对象；但它也不能变成没有关闭时机、跨不相干权限边界的永久全局对象。

## 8. 连接池和业务并发不是同一个限制

HTTPX 的 `Limits` 控制连接池中最大连接数、保持连接数和空闲过期时间。[2] 这限制客户端所持有的网络资源；它不等于你对目标系统承诺的请求频率，也不等于同时处理的业务任务数。下一章会用 `asyncio.Semaphore` 限制本地任务并发，并单独讨论 robots、站点条款、速率与重试预算。

## 9. 超时必须具体

HTTPX 区分 connect、read、write 和 pool 超时：建立连接、接收响应块、发送请求块与等待连接池各有不同失败含义。[3] HTTPX 默认会在网络不活动五秒后超时，但项目显式设定四类预算，避免把库默认当作业务 SLA。

| 超时 | 失败问题 | 调试方向 |
|---|---|---|
| connect | 多久未连接到主机？ | DNS、网络、证书、目标可达性。 |
| read | 多久未收到下一响应数据块？ | 上游慢、流式响应、代理或网络。 |
| write | 多久未发出下一请求数据块？ | 上传、网络或背压。 |
| pool | 多久未拿到可用连接？ | 客户端并发、连接上限或泄露。 |

## 10. `stream()` 让大小限制发生在内存失控之前

```python
async with self._client.stream("GET", endpoint, params=params) as response:
    body = await self._read_bounded_body(response)
```

项目以流式响应逐块累计字节数，一旦超过 `max_response_bytes` 立即抛 `ResponseTooLargeError`。这比先读取全部正文再检查长度更安全。HTTPX 文档说明异步流式响应应以异步上下文管理器使用；退出块会关闭响应。[1] 若使用手工流式模式，开发者必须自行 `aclose()`，否则会泄露连接。[1]

## 11. 成功状态码不保证可用数据

`200` 可能带 HTML 错误页、空字节、巨大文件、JSON 数组或与预期不同的对象。项目依次检查：状态不为错误；`Content-Type` 是 `application/json` 或 `+json`；正文未超限；JSON 能解析；根节点是对象。每一步失败都有不同的受控异常，便于调用方决定停止、记录或人工检查，而不是在后续业务逻辑里得到模糊 `KeyError`。

## 12. HTTPX 错误分类要被保留

HTTPX 将请求相关异常分为传输、超时、网络、协议与 HTTP 状态等类别；调用 `raise_for_status()` 时 4xx/5xx 会成为 `HTTPStatusError`。[4] 项目不把原始异常直接交给上层，而是映射为 `UpstreamTransportError`、`UpstreamResponseError`、`UnexpectedContentTypeError` 等领域错误。这样日志可保留脱敏的错误类型，API/CLI 可输出稳定合同，测试也能精确说明预期。

## 13. 重试是风险控制，不是可靠性开关

```python
_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})
```

项目只重试两类情况：HTTPX `TransportError`，以及这组经审查状态。它只执行 GET，因此读取在合同上不改变上游状态。`404`、端点拒绝、非 JSON、大小超限、JSON 格式错误和本地策略错误不会重试。即使是 `429` 或 `503`，重试也有最大次数和最大延时，不能无限消耗目标资源。

## 14. 确定性指数退避

```python
RetryPolicy(max_attempts=3, base_delay_seconds=0.1, max_delay_seconds=1.0)
```

第一次失败等待 0.1 秒，第二次等待 0.2 秒，随后被最大值封顶。项目使用确定性退避，便于零基础读者测试；生产大规模客户端通常还要引入随机抖动、`Retry-After`、全局预算、熔断和队列，避免大量客户端同时重试形成雪崩。不要把“重试次数更大”误当成可用性更高。

## 15. 重试与幂等性

**幂等（idempotent）**表示重复执行在目标状态上具有与执行一次相同的效果。GET 通常用于读取，适合作为本项目的有限重试对象；创建、支付、发送消息或触发工具的 POST 是否可重试，取决于服务端是否有幂等键、状态查询和明确协议。客户端不能仅靠 HTTP 方法名猜测副作用不存在。

## 16. 日志只记录能排障的最小元数据

```text
INFO collector_retry_scheduled attempt=1 delay_seconds=0.1 reason=status_503
WARNING collector_upstream_retryable_status host=api.example.test path=/records status=503
```

`SafeApiClient` 从不记录查询参数值、响应 body 或认证头。测试让查询参数带模拟 token，并断言日志不含 token。日志为运维提供“何时、哪个主机、哪个路径、哪个错误类别”的线索；它不是用户数据仓库、提示词备份、模型输出档案或秘密调试台。

## 17. 一次完整调用的控制流

| 步骤 | 责任 | 失败时 |
|---:|---|---|
| 1 | 验证端点仍在 HTTPS 允许列表内。 | `EndpointRejectedError`，不发网络请求。 |
| 2 | 从连接池获取连接并执行 GET。 | 传输错误按有限策略重试。 |
| 3 | 检查可重试状态。 | 未耗尽时退避；耗尽后公开状态错误。 |
| 4 | 检查其他 4xx/5xx。 | 立即 `UpstreamResponseError`。 |
| 5 | 检查内容类型与流式大小。 | 内容或大小错误，不重试。 |
| 6 | 解码 JSON 对象。 | `InvalidJsonResponseError`。 |
| 7 | 返回对象给调用方。 | 由上层再做领域 Schema 验证。 |

## 18. MockTransport 让网络失败可测试

项目不在 CI 中调用未知公网 API。`httpx.MockTransport` 以本地函数模拟 `200`、`404`、`503`、`ConnectError`、超大响应和错误内容类型。这样可以验证次数、延时、日志和异常类型，而不会受到 DNS、配额、第三方改版或真实秘密影响。真实网络端到端验收仍有价值，但应使用获授权的测试环境和独立凭据。

## 19. CLI 的边界

```bash
.venv/bin/course-api-collect \
  --base-url https://api.example.com \
  --endpoint /v1/records \
  --param page=1 \
  --verbose
```

CLI 只读取一次 GET JSON；成功 JSON 写标准输出，脱敏日志写标准错误，受控失败输出 JSON 错误并返回退出码 `2`。它不接受认证 token 参数，也不提供“忽略 HTTPS”“无限超时”或“执行任意方法”开关。命令行方便不应以扩大攻击面为代价。

## 20. 失败案例：日志中打印完整 URL

```python
LOGGER.info("fetching url=%s", response.request.url)
```

这会把 `?api_key=...`、会话 ID、个人筛选条件或内部资源标识写进日志。修复不是希望所有调用者永远不把秘密放 URL，而是日志只写 `host` 和 `path`，并设计认证走秘密头/受控配置。即使如此，路径也可能敏感，生产系统仍要定义访问权限与保留期。

## 21. 本章验收

```bash
cd /home/ubuntu/python_private_course/projects/07-polite-api-collector
.venv/bin/python -m pytest
.venv/bin/python -m mypy
.venv/bin/python -m ruff check src tests
```

阅读 `test_retries_retryable_status_with_bounded_backoff`，说明为何它用假 sleeper 而非真实 `sleep`。再阅读 `test_retry_log_does_not_include_query_value`，找出日志中保留了哪些排障信息、拒绝了哪些敏感数据。最后用非 HTTPS 基址调用 CLI，确认程序以退出码 `2` 受控拒绝，而不发网络请求。

## 22. 快速测试（5 题）

1. 为什么 `AsyncClient` 不应在每条 URL 的循环中重新创建？
2. connect、read、write、pool 超时分别限制什么？
3. 为什么 `503` 可能重试而 `404` 不应默认重试？
4. 为什么响应是 `200` 仍要检查内容类型和 JSON 形状？
5. 为什么日志只写路径而不写完整 URL？

**答案要点：** 1. 无法有效复用连接池且资源生命周期混乱；2. 连接、接收、发送、等待连接的不同阶段；3. 前者可能暂时不可用，后者通常代表资源/路径问题；4. 状态成功不保证契约数据；5. 查询可能含 token、个人数据或内部标识。

## 23. 代码阅读（2 题）

1. 阅读 `ClientPolicy.__post_init__()` 与 `_validate_endpoint()`，列出构造期和请求期分别检查哪些协议/主机/路径条件；解释为何两层都需要。
2. 阅读 `_request_once()`、`_read_bounded_body()` 与 `_decode_json_object()`，按顺序画出从状态码到 JSON 对象的验证流程。若把大小检查放到 `json.loads()` 后，风险是什么？

## 24. Debug（2 题）

1. 暂时把 `follow_redirects=False` 改为 `True`，用 MockTransport 构造从允许主机跳到不允许主机的重定向；说明请求期允许列表为何不能只在初始 URL 检查。恢复默认拒绝重定向，后续如需支持必须逐跳检查。
2. 将 `RetryPolicy.max_attempts` 设为非常大并用 `503` handler 运行测试。记录测试耗时/尝试变化，恢复有限次数，并说明重试预算为什么也是资源和礼貌边界。

## 25. 编程练习（3 题）、逆向设计与课后项目

**编程练习：** 1. 支持受控 `Retry-After` 秒数：只接受整数秒、最大 60、只用于 429/503；为缺失、非法、过大和日志脱敏写测试。2. 为成功 JSON 定义 `RecordPage` Pydantic 模型，明确 `items`、`next_cursor` 与未知字段策略；将解码后的字典交给模型验证，并映射为受控 schema 错误。3. 增加每次请求的随机请求 ID，写入日志和返回的内部结果元数据；证明它不是 token，也不含查询参数。

**逆向设计：** 某“万能数据工具”接受任意 URL、方法、headers 和 body；跟随所有重定向；关闭超时；每次失败立即无限重试；创建新客户端；把完整 URL、headers 与响应写日志；把任何 4xx/5xx 当 JSON 解析。请从 SSRF、秘密、上游压力、连接泄露、重试副作用、内存、内容验证、可观测性、Agent 工具权限、测试和成本至少倒推十二项风险，并写出每项可执行的合同或测试。

**课后项目：** 将本章项目扩展成“受控目录 API 客户端”。要求：端点只能由审查过的名称映射选择，不能直接接受路径；每个名称有固定 Schema、分页规则、最大大小和重试策略；支持 CLI 读取名称和非秘密参数；输出结构化 JSONL；不记录正文或 token；为超时、429、503、404、跨主机重定向、内容超限、schema 错误和日志脱敏写至少十五项 MockTransport 测试；README 写出服务授权、配额、数据保留与人工审查边界。


### 本章项目映射

本章建议直接在 `projects/07-polite-api-collector/` 中完成可运行练习。先执行：阅读 HTTPS/主机允许列表、连接池、超时和有限重试，区分请求安全与业务许可。

```bash
cd projects/07-polite-api-collector && .venv/bin/python -m pytest
```

**主题化扩展：** 增加一个不允许的基址测试，验证在发请求前受控拒绝且不输出认证信息。

完成后记录输入/输出合同、受控失败、测试命令和安全边界。不要把项目中的本地替身、测试夹具、回环服务或默认无执行模式误作真实网络、模型、生产数据、秘密、部署或副作用授权。

## 参考资料

[1]: https://www.python-httpx.org/async/ "HTTPX: Async Support"
[2]: https://www.python-httpx.org/advanced/resource-limits/ "HTTPX: Resource Limits"
[3]: https://www.python-httpx.org/advanced/timeouts/ "HTTPX: Timeouts"
[4]: https://www.python-httpx.org/exceptions/ "HTTPX: Exceptions"
