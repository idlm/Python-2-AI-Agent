# 第 7.2 章：并发不等于轰炸——礼貌采集、限速与可收尾任务组

**适用版本：** Python 3.11+  
**项目连接：** `projects/07-polite-api-collector/`（版本 0.1.0）

## 1. 本章目标

完成本章后，你能够区分连接池限制、任务并发限制、请求间隔与服务器配额；能用 `asyncio.Semaphore` 限制本地并发；能以 `TaskGroup` 收束一批相关采集任务；能先检查 robots 技术规则；能理解 robots 不是法律授权；能让结果顺序、失败、取消和日志边界成为可测试合同。

## 2. 先纠正一个误解：速度不是唯一指标

并发采集的正确目标不是“尽可能快地发更多请求”，而是在已获授权、明确配额和可恢复失败的前提下，控制本地资源、尊重目标服务并获得可解释结果。对一个站点的过量请求会伤害对方服务，也可能触发封禁、成本、法律或隐私问题。若业务没有明确许可、数据目的、保留期限和限额，技术并发能力不应被启用。

## 3. 从生产级 Agent 倒推

研究 Agent 常要并发调用搜索、检索、网页、数据库和工具。但 Agent 不是“更多并发请求”：它还需要工具允许列表、记忆状态、工作流、评测、审计和人工介入。采集器只负责受控读取；它不决定一个站点是否可用于训练、是否可保存个人数据、是否有版权限制，或一个模型能否信任返回内容。

## 4. 四种不同的限制

| 限制 | 控制的对象 | 项目 7 实现 | 不能替代 |
|---|---|---|---|
| 连接池限制 | HTTP 客户端同时持有的连接。 | HTTPX `Limits`。 | 站点请求频率和业务任务量。 |
| 并发限制 | 同时进入 `fetcher.get_json()` 的本地任务数。 | `asyncio.Semaphore`。 | robots、许可或服务器配额。 |
| 请求间隔 | 同一站点相邻请求开始的最短时间。 | `RequestPacer`。 | 连接超时和全局速率策略。 |
| 重试预算 | 某次读取重新尝试的次数与延时。 | `RetryPolicy`。 | 幂等、授权或无限可用性。 |

将它们混成一个“并发数”会导致错误配置：连接够用不代表可多发请求，等一秒也不代表可以同时开一千任务。

## 5. robots.txt 只回答一个技术问题

Python 标准库 `urllib.robotparser.RobotFileParser` 可解析已获得的 robots.txt，并以 `can_fetch(useragent, url)` 回答该文件规则下指定 User-Agent 是否允许访问 URL；还可读取 `crawl_delay` 和 `request_rate` 信息。[1] 项目把 robots 文本作为输入，先在内存预检所有已审查端点：

```python
if not robots_guard.allows(request.endpoint):
    raise RobotsDeniedError(...)
```

robots.txt 不等于法律许可、合同授权、版权许可、隐私同意、绕过登录/付费墙的许可或对敏感数据的处理授权。它只是一个应尊重的技术信号。

## 6. 为什么 robots 预检在发请求之前

项目在创建任何采集 Task 前遍历请求列表；只要一项不被 robots 允许，就抛 `RobotsDeniedError`，并且测试确认 `fetcher.calls == []`。这是一种**默认拒绝**策略：不先访问“允许的几页，再发现其中一页禁止”。真实系统还要决定 robots 下载失败、缓存过期、特定 User-Agent、站点条款和人工审批的策略，不能悄悄默认允许。

## 7. 固定采集请求，不接受 URL 发现

```python
@dataclass(frozen=True)
class PageRequest:
    name: str
    endpoint: str
    params: Mapping[str, str] | None = None
```

`PageRequest.endpoint` 必须是单个基址下以 `/` 开头的路径。协调器不从网页内容、模型输出或不可信配置“发现”下一跳 URL；路径的跨主机控制仍由第 7.1 章 `SafeApiClient` 负责。这一层减少 SSRF、无限爬行、意外跳转和难以评测的采集范围。

## 8. Semaphore 限制本地并发

```python
semaphore = asyncio.Semaphore(crawl_policy.max_concurrency)

async with semaphore:
    payload = await fetcher.get_json(...)
```

`asyncio.Semaphore` 维护一个不能低于零的计数；计数为零时，后续任务等待。Python 文档建议使用 `async with semaphore`，以确保退出时释放。[2] 项目测试启动三项慢任务而最大并发为二，断言任何时刻活动 fetch 不超过二。Semaphore 是本地资源控制，不是对远端站点做出的请求许可。

## 9. Semaphore 不保证请求节奏

若最大并发为二，两个任务可以在同一瞬间开始；若每个任务很快结束，短时间内仍可产生很多请求。因此项目还引入 `RequestPacer`：单个异步锁保护“下一次允许开始”的时间槽。它只在安排起始时持锁，网络等待发生在锁外，避免一个慢请求把节奏器本身锁死。

## 10. 起始间隔合同

```python
async with self._lock:
    now = self._clock()
    wait_seconds = max(0.0, self._next_allowed_at - now)
    if wait_seconds > 0:
        await self._sleep(wait_seconds)
    self._next_allowed_at = max(now, self._next_allowed_at) + interval
```

该逻辑限制的是**请求开始时间**，不是每个响应结束后的间隔。这样能够解释并测试“第一请求开始于 0 秒、下一请求最早 1 秒开始”。项目以假 clock 和假 sleep 断言第二次等待 0.7 秒，而不让测试真的等待一秒。

## 11. robots Crawl-delay 如何与本地策略合并

`CrawlPolicy.minimum_interval_seconds` 是项目自己的保守下限；若 robots 给当前 User-Agent 声明了 `Crawl-delay`，项目取两者较大值。这样本地配置不会降低站点已声明的延时。`crawl_delay()` 返回缺失或不适用时可能为 `None`，因此不能假定每个站点都提供这个字段。[1]

这仍不替代 API 文档中更严格的速率配额，尤其当站点规定每分钟请求数、按 token 计费或要求使用官方 SDK 时。

## 12. TaskGroup 让批次有共同结局

```python
async with asyncio.TaskGroup() as group:
    for request in requests:
        tasks.append(group.create_task(_collect_one(...), name=request.name))
```

第 6.4 章已说明，`TaskGroup` 会在离开作用域前等待相关任务；一个任务出现非取消异常时，其他任务会被取消并最终以 `ExceptionGroup` 传播。[3] 对“所有页面共同构成一个一致采集批次”的场景，这比裸 `create_task()` 更可推理：成功、失败、取消和清理有同一边界。

## 13. 结果顺序不等于完成顺序

慢页面可先创建、快页面后创建并先完成；项目仍按输入的 `PageRequest` 顺序返回 `CollectedPage` 列表。输出顺序是调用方合同，不应由网络偶然决定。若需要流式交付，必须另行定义事件 Schema（例如 `started`、`page`、`error`、`complete`），并考虑部分失败和断线恢复。

## 14. 一个页面失败时发生什么

项目当前选择“批次原子性”：一个 fetcher 抛未处理异常时，TaskGroup 取消兄弟任务；测试确认慢兄弟记录到取消。这适合不能用不完整数据继续的目录快照。另一种策略是“尽量收集”：每页封装成功或错误结果，并让批次完成。两者都可以正确，关键是把策略、错误类型、重试预算、持久化和调用方行为写成合同，而不是让异常处理偶然决定。

## 15. 取消后的清理责任

协调器使用 `async with semaphore`，因此任务被取消时会释放并发名额；底层 `SafeApiClient` 用响应/客户端上下文管理器关闭连接。Python 的异步同步原语不是线程安全工具，也不提供自带 timeout 参数；等待上限应以 `asyncio.timeout()` 或显式策略管理。[2] 取消只停止本地工作，不保证远端服务器未开始处理请求。

## 16. `CollectedPage` 为什么不直接写文件

```python
@dataclass(frozen=True)
class CollectedPage:
    name: str
    endpoint: str
    payload: dict[str, object]
```

协调器返回明确结果，但不负责保存正文。并发调度、HTTP 合同和持久化失败有不同生命周期；把它们塞进一个函数会使回滚、断点续跑、去重、审计和敏感数据控制无法测试。下一章将以固定 JSONL 记录、原子写入和恢复清单接住这些结果。

## 17. 日志只有元数据

```text
INFO collector_page_started name=public path=/public
INFO collector_page_completed name=public path=/public
```

测试让查询值含模拟敏感正文，断言日志不含它。协调器不记录 `payload`、`params` 或 headers。日志可用于解释任务名称、已审查路径和阶段；它不应成为采集内容的旁路数据库。若路径本身含个人标识，生产系统还需进一步哈希、分级或限制可见性。

## 18. 并发采集的失败矩阵

| 条件 | 当前行为 | 后续需要的策略 |
|---|---|---|
| robots 拒绝 | 预检失败，无网络请求。 | robots 获取失败、缓存与人工审批。 |
| 上游 503 | 客户端有限重试后失败。 | `Retry-After`、抖动、熔断与全局预算。 |
| 一页异常 | TaskGroup 取消兄弟，批次失败。 | 是否允许部分结果、如何保存失败。 |
| 网络慢 | 客户端超时；协调器释放名额。 | 端到端批次时间预算和用户通知。 |
| 响应过大 | 客户端拒绝，不保存。 | 上游分页、流式解析和内容配额。 |
| 进程中断 | 当前内存结果丢失。 | 下一章的持久化、恢复与去重。 |

## 19. 连接数、并发数与站点节奏的组合

设连接池最多四个连接、业务并发二个任务、站点间隔一秒：同一批最多二项进入 fetch；即使两项都可用连接，节奏器仍安排它们在不同起始槽。若改为多站点采集，应该为每个允许主机维护独立的 Pacer 和策略；不能用一个站点慢速规则无意压低所有站点，也不能让一个站点配额被其他站点绕过。

## 20. 失败案例：只用 `gather()` 加一千 URL

```python
results = await asyncio.gather(*(client.get(url) for url in urls))
```

这段代码没有主机允许列表、robots、并发上限、连接池配置、超时分类、响应大小、重试边界、取消清理、结果顺序、日志脱敏或持久化策略。即便它在小样本上“很快”，也无法说明它对目标系统礼貌、对自身资源安全、对用户结果可解释。正确做法是先缩小采集范围，再逐层加入可测控制。

## 21. 本章验收

```bash
cd /home/ubuntu/python_private_course/projects/07-polite-api-collector
.venv/bin/python -m pytest
.venv/bin/python -m mypy
.venv/bin/python -m ruff check src tests
```

阅读 `test_robots_denial_happens_before_any_fetch` 和 `test_semaphore_limits_active_fetches`，说明它们分别证明什么。再阅读 `test_pacer_waits_before_second_request_start`，解释为什么 fake clock/sleeper 让节奏测试比真实 sleep 更可靠。最后说明 robots `Allow` 通过后，为什么仍需要 API 许可、条款和隐私审查。

## 22. 快速测试（5 题）

1. 连接池上限与 Semaphore 上限分别控制什么？
2. 为什么 Semaphore 不能取代每站请求间隔？
3. robots.txt 能否替代网站条款或授权？
4. 为什么协调器在创建 Task 前预检 robots？
5. 为什么批次结果保持输入顺序而不是完成顺序？

**答案要点：** 1. 网络连接资源与业务活动任务；2. 多项任务仍可同时开始；3. 不能，它只给技术规则信号；4. 默认拒绝且防止部分请求已发出；5. 为调用方提供确定性合同。

## 23. 代码阅读（2 题）

1. 阅读 `RequestPacer.wait_turn()`，指出锁保护的状态是什么、`await sleep()` 发生在何处、为何网络 fetch 不在该锁内。若把 fetch 放进锁中会怎样？
2. 阅读 `collect_pages()`，追踪 robots 预检、合并间隔、Semaphore、TaskGroup、`tasks` 引用与 `task.result()` 的顺序。说明每一步如何减少一个不同类别的故障。

## 24. Debug（2 题）

1. 把 `async with semaphore:` 临时删掉，运行三项慢任务的并发测试，观察 `max_active` 如何超过二；恢复后解释连接池限制为何不能总是捕捉该错误。
2. 把 robots 预检移入 `_collect_one()`。构造列表中第一项允许、第二项拒绝的测试，观察是否有请求先发出；恢复批次预检，并讨论部分采集策略需要怎样显式建模。

## 25. 编程练习（3 题）、逆向设计与课后项目

**编程练习：** 1. 实现按主机分组的 `PacerRegistry`，为每个允许主机独立保持间隔；用两个假站点证明 A 的等待不阻塞 B。2. 实现“部分成功”采集模式：每项返回 `CollectedPage` 或受控错误记录，保持输入顺序；明确 robots 拒绝是批次失败还是单项失败，并写十项测试。3. 增加总批次超时和每页超时，说明二者如何与 HTTPX connect/read/pool 超时不同；写取消清理和不泄露 payload 的日志测试。

**逆向设计：** 某数据 Agent 从模型输出抽取 URL，直接 `gather()` 全部请求；禁用超时与 TLS 检查；不读 robots；遇到 429 无限重试；把 URL、headers、页面正文写日志；结果按完成顺序混合并写入共享文件。请从 SSRF、目标站压力、秘密、顺序、取消、文件损坏、授权、隐私、成本、评测与人工审查至少倒推十二项问题，并给出对应可测试合同。

**课后项目：** 构建“受控目录批量采集器”。要求：目录中的每个来源须包含主机允许列表、User-Agent、robots 缓存摘要、最大并发、最小间隔、最大页数和响应大小；采集器支持拒绝、部分成功和全批失败三种明确模式；每页结果携带来源名称、路径、采集时间与公开错误码；日志不含正文/参数/秘密；对 robots、Semaphore、每站 Pacer、TaskGroup、超时、取消、分页上限和日志脱敏写至少二十项测试；将结果交给下一章的受控持久化层。


### 本章项目映射

本章建议直接在 `projects/07-polite-api-collector/` 中完成可运行练习。先执行：阅读 robots、Semaphore、Pacer 与 TaskGroup 测试，区分并发上限、节奏和站点规则。

```bash
cd projects/07-polite-api-collector && .venv/bin/python -m pytest
```

**主题化扩展：** 设计一个来源级预算；测试 robots 拒绝时不会启动 fetch，也不将 robots 视为法律或访问授权。

完成后记录输入/输出合同、受控失败、测试命令和安全边界。不要把项目中的本地替身、测试夹具、回环服务或默认无执行模式误作真实网络、模型、生产数据、秘密、部署或副作用授权。

## 参考资料

[1]: https://docs.python.org/3/library/urllib.robotparser.html "Python urllib.robotparser documentation"
[2]: https://docs.python.org/3/library/asyncio-sync.html "Python asyncio synchronization primitives"
[3]: https://docs.python.org/3/library/asyncio-task.html "Python coroutines and tasks documentation"
