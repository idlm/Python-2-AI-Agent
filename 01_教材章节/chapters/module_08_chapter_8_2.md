# 第 8.2 章：把任务交给 worker 前，先定义边界——有界队列、反压、取消与结构化执行

**适用版本：** Python 3.11+  
**项目连接：** `02_可运行项目/projects/08-workflow-service/`（版本 0.1.0）

## 1. 本章目标

完成本章后，你能够解释为什么“收到请求就 `create_task()`”不是可靠执行；能使用有界 `asyncio.Queue` 表达反压；能让固定处理器允许列表与任务类型对应；能以 `TaskGroup` 管理 worker 生命周期；能为超时、取消、失败和清理写出稳定状态合同；并能诚实说明进程内队列不具备跨重启投递保证。

## 2. 状态机之后还缺什么

第 8.1 章只回答“任务处于什么状态”。它尚未回答：谁领取 `pending` 任务？同时最多处理多少？队列满时怎样拒绝？处理器失败后状态如何收束？取消时怎样等待清理？worker 退出前如何证明队列已处理？这些是执行协调问题。

队列不是魔法邮箱。它只是暂时存放工作项，并将生产者与消费者解耦；若没有容量、生命周期、失败与取消合同，队列会把问题藏起来而不是解决它。

## 3. 从生产级 Agent 倒推

Agent 调用工具时也会产生工作项：检索、生成、调用内部服务、写入审计记录。若 Agent “看到请求就后台执行”，却没有状态、反压、取消和追踪，就无法评测成功率、识别重复工具调用或安全停止。Agent 不是 `asyncio.Queue`、不是 FastAPI、也不是某个编排框架；这些机制只实现它所需的受控工作流底座。

## 4. 生产者、队列、worker 与状态机

```text
API/CLI（生产者）
    │ 受控 TaskRequest
    ▼
WorkflowWorkerEngine.submit()
    │ 幂等查询 + 容量检查
    ▼
有界 asyncio.Queue
    │ task_id，不含任意 callable
    ▼
TaskGroup 中的固定数量 worker
    │ begin → handler → succeed/fail/cancel
    ▼
WorkflowRegistry（状态事实）
```

生产者只提交受控请求；队列只保存 `task_id`；worker 只从代码注册的处理器表取函数；状态机才是对调用方可见的任务事实。每一层的职责不同，因而可以分别测试。

## 5. `asyncio.Queue` 的适用范围

Python 官方将 `asyncio.Queue` 设计为用于 async/await 代码的 FIFO 队列，并明确它不是线程安全对象。[1] 它适合在同一事件循环中分配工作；不适合当作线程间、进程间或跨机器消息系统。项目只在一次 Python 进程生命周期内创建队列，因此 README 明确不承诺跨重启、跨进程或崩溃后的投递。

## 6. 为什么队列必须有上限

```python
queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=10)
```

`maxsize > 0` 时，队列达到上限后 `put()` 会等待可用空间；`put_nowait()` 在没有空间时抛 `QueueFull`。[1] 项目在接受新任务**之前**检查 `queue.full()`，满时抛 `QueueCapacityError`：

```text
当前进程内工作队列已满，请稍后重试。
```

这叫**反压（backpressure）**：系统把自身处理能力不足的事实传回生产者，而不是继续接收直至内存耗尽。

## 7. 为什么要在注册前拒绝满队列

错误顺序如下：先把任务记录为 `pending`，随后发现队列满，最后告诉用户失败。这样会留下一个已经接受、却永远没有入队的“孤儿任务”。项目正确顺序是：

1. 用幂等键查询是否已有任务；若有，直接返回。
2. 若是新任务且队列满，拒绝，**不**注册任务。
3. 若有容量，接受任务，立刻把其 `task_id` 放入队列。

这仍是单进程教学原型；生产级系统需要把状态记录和入队放进同一持久事务或采用 outbox 等模式。不要把本地两行代码说成分布式原子提交。

## 8. 幂等提交优先于反压

如果队列已满，用户因网络超时重发**同一个**请求，不应被当成新工作拒绝。`submit()` 先调用：

```python
existing = registry.lookup_idempotency(request)
if existing is not None:
    return existing
```

只有没有既有任务的新工作才检查容量。这使重复提交得到同一 `task_id`；相同幂等键但不同引用仍是冲突。顺序体现业务含义，而不仅是性能优化。

## 9. 队列中只放任务 ID

队列可以存任意 Python 对象，但项目只放 `str` 形式的 `task_id`。不放用户 payload、任意函数、模块路径、shell 命令、数据库连接或秘密。worker 领取 ID 后到 `WorkflowRegistry.begin()` 获取内部记录，再从固定处理器表按已验证 `task_type` 取得 handler。

这把“不可信输入”与“可执行代码”隔离：请求只能选已有能力，不能创建新能力。

## 10. 处理器允许列表

```python
handlers = {"refresh_catalog": refresh_catalog_handler}
engine = WorkflowWorkerEngine(registry, handlers=handlers)
```

构造器要求 `handlers` 的键集合与 `registry.allowed_task_types` **完全一致**。少一个键会让可接受任务无人处理；多一个键可能暴露未审查能力；动态 `importlib` 或 `getattr` 会把任务输入扩展为代码选择器。项目以 `WorkerConfigurationError` 在启动前拒绝不一致配置。

## 11. worker 数不是吞吐承诺

`worker_count=2` 表示同一进程中最多启动两个 worker 循环。它不是上游 API 配额、CPU 核数、数据库连接池大小、跨服务并发或“系统必定更快”。项目测试让三个任务阻塞在处理器内，并证明最大活动数为 2；该测试固定了本地并发上限，而非性能基准。

## 12. `TaskGroup` 给 worker 生命周期边界

```python
async with asyncio.TaskGroup() as group:
    for number in range(worker_count):
        group.create_task(self._worker_loop(number))
    await self._queue.join()
    for _ in range(worker_count):
        self._queue.put_nowait(None)
```

`TaskGroup` 是 Python 3.11 引入的结构化并发工具；退出上下文时会等待成员任务，任一非取消异常会取消其余任务并以异常组传播。[2] 因此 worker 不再是无人引用的“后台幽灵”，而是有共同开始、等待和收尾边界的一组任务。

## 13. 为什么不直接 `create_task()` 后忘掉

Python 文档提示事件循环只弱引用任务；未在别处保存引用的任务可能在完成前被垃圾回收。[2] 更糟的是，未等待的任务失败后异常可能只留下“Task exception was never retrieved”警告。项目创建具体处理器 task 后保存到 `_running_handlers`，并在 `finally` 移除；worker 生命周期则由 `TaskGroup` 管理。

这并不意味着所有 `create_task()` 都错误，而是说明“fire-and-forget”必须有任务引用、错误处理、取消策略和生命周期所有者。

## 14. `join()` 与 `task_done()` 是一对合同

队列每次 `put()` 都增加未完成计数；消费者对每次 `get()` 必须恰好调用一次 `task_done()`；`join()` 在计数归零时解除等待。[1] 项目的 worker 把 `task_done()` 放入 `finally`：

```python
item = await queue.get()
try:
    await process(item)
finally:
    queue.task_done()
```

若遗漏 `task_done()`，drain 永远等待；若调用多次，Python 抛 `ValueError`。这类卡死需要测试，而不是依赖“看起来能跑”。

## 15. 哨兵值如何让 worker 停止

Python 3.11 没有可用的 `Queue.shutdown()`；该 API 是较新 Python 版本才添加的，不能作为本书 3.11 基线。[1] 项目用 `None` 作为类型明确的停止哨兵：当当前工作 `join()` 完成后，为每个 worker 入队一个 `None`。worker 取到它就返回，并仍在 `finally` 调用 `task_done()`。

哨兵只适用于受控队列类型 `str | None`；如果队列允许任意对象，`None` 可能与业务数据混淆。

## 16. 处理器开始与状态转换

worker 领取 ID 后先读公开状态。如果已取消，记录“跳过”并不调用 handler；否则调用 `registry.begin()`，将 `pending` 原子切为 `running` 并增加尝试次数。若其他路径已把状态改变，`InvalidTransitionError` 使 worker 跳过而非重复执行。

这不是跨进程租约：两个不同进程各有内存注册表仍可能重复执行。它只是单进程内的一致边界。

## 17. 单任务超时

```python
async with asyncio.timeout(task_timeout_seconds):
    await handler_task
```

`asyncio.timeout()` 在超时后取消当前等待并在上下文外转换为 `TimeoutError`。[2] 项目将其映射为 `failed` 与 `error_code="timeout"`。超时是本地时间预算，不说明远端 HTTP 服务、数据库或文件操作没有发生；若 handler 已发出不可逆请求，仍要通过幂等键、操作清单和目标系统查询处理不确定性。

## 18. 取消和 `finally` 清理

当调用 `engine.cancel(task_id)` 时，状态机先记录 `cancelled`，若当前进程有对应 handler task，再调用 `.cancel()`。处理器应这样写：

```python
async def handler(record: TaskRecord) -> None:
    resource = acquire_resource()
    try:
        await do_work(resource)
    finally:
        release_resource(resource)
```

Python 建议协程用 `try/finally` 完成清理；显式捕获 `CancelledError` 后通常应继续传播。[2] 项目测试证明取消会进入 handler 的 `finally`，并保持最终状态为 `cancelled`。

## 19. 失败不会泄露异常正文

处理器抛出任意异常时，engine 只标记 `execution_failed` 并记录任务类型与 worker 编号：

```text
WARNING workflow_task_execution_failed task_type=refresh_catalog worker=0
```

它不把 `repr(exception)`、工作引用、payload 或栈回显给调用方。这并不意味着应丢弃诊断：生产系统需要受控访问的结构化错误事件、请求 ID、采样与审计策略；公共状态接口仍应最小化。

## 20. 取消与状态竞争

执行者可能刚成功，调用方同时请求取消；超时可能先发生，handler 又抛异常。项目的 `_mark_failed_if_active()` 与 `_mark_cancelled_if_active()` 使用 `suppress(InvalidTransitionError)`：若状态已是终结状态，不再用第二次转换覆盖它。

这种“忽略已终结”只适用于明确预期的竞态。不要滥用 `except Exception: pass`；它会吞掉配置错误、编程错误和真正的数据损坏。

## 21. 当前原型的真实限制

| 能力 | 当前实现 | 不应夸大的保证 |
|---|---|---|
| 排队 | 单事件循环内存 `asyncio.Queue`。 | 跨重启持久、跨进程共享或消息不丢。 |
| 反压 | 队列满时拒绝新任务。 | 全局流量控制、租户配额或分布式限速。 |
| worker | 固定数量、TaskGroup 管理。 | 自动扩缩容或多主机负载均衡。 |
| 超时 | 取消本地等待并标记失败。 | 撤销远端已发生副作用。 |
| 取消 | 取消本进程保留的 handler task。 | 杀死任意进程或撤销第三方任务。 |
| drain | 当前入队项完成后停止 worker。 | 永不漏任务的优雅关机。 |

在第 8.3 章，我们会把这些限制写进 FastAPI 生命周期和 API 响应，而不是让使用者从源码猜测。

## 22. 快速测试（5 题）

1. 为什么 `maxsize=0` 不适合作为默认服务队列？
2. 为什么新任务要在注册前检查队列容量，而重复幂等提交要优先返回既有任务？
3. `queue.join()` 依赖消费者遵守哪一对方法合同？
4. `TaskGroup` 相比无人引用的 `create_task()` 提供了什么生命周期优势？
5. 为什么超时后不能直接宣称外部副作用未发生？

**答案要点：** 1. 它无界，无法表达反压；2. 防孤儿任务，同时允许安全重试；3. 每个 `get()` 对应一次 `task_done()`；4. 保留任务、等待收尾、传播失败；5. 本地取消无法回溯远端已发送/已提交操作。

## 23. 代码阅读（2 题）

1. 阅读 `WorkflowWorkerEngine.submit()`。指出它处理“同键重复”“队列满的新任务”“可入队新任务”的先后顺序，并解释为什么不能交换前两步。
2. 阅读 `_worker_loop()` 的 `try/finally` 与 `_process()` 的 `finally`。前者保证什么队列不变量？后者为何删除 `_running_handlers` 中的强引用？

## 24. Debug（2 题）

1. 故意将 `_worker_loop()` 的 `task_done()` 从 `finally` 移到成功路径。让 handler 抛异常，调用 `run_until_idle()`；说明为什么它会等待，并恢复正确结构。
2. 故意把 `queue_maxsize` 改为 0，连续提交大量任务。设计一个测试证明内存队列增长不受约束；恢复正上限，并定义 API 的 `429` 或 `503` 拒绝语义（第 8.3 章实现）。

## 25. 编程练习（3 题）、逆向设计与课后项目

**编程练习：** 1. 增加每个任务类型独立的并发上限，不能只靠一个总 worker 数；为两个类型分别写公平性和上限测试。2. 实现受控的延迟重试计划，限制最大尝试、总时间和错误类别；不能在队列中无限自我入队。3. 增加 drain 截止时间：若优雅停止超时，记录哪些任务仍 `running` 并交给显式恢复策略，不伪造成功。

**逆向设计：** 某 API 对每次请求调用 `asyncio.create_task(any_function(payload))`，队列无上限、没有任务 ID、不保留 task 引用、没有 `task_done()`、没有超时、异常打印全部输入、取消吞掉 `CancelledError`、进程停止就忘记工作。请从内存、执行权限、异常、重复、停止、恢复、隐私、观测、上游副作用、容量与调用方语义至少倒推十一项风险，并给每项补一个自动化门禁。

**课后项目：** 为第 8.1 的目录刷新工作流接入可恢复执行协调器。要求：固定处理器允许列表；有界队列、拒绝语义和幂等重试；结构化 worker、`TaskGroup`、强引用、`join/task_done`、超时、取消和资源清理；公开状态与日志不含正文；为队列满、重复、handler 失败、超时、正在运行取消、并发上限、停止哨兵和 worker 故障写至少十六项测试。README 必须把进程内原型与持久队列的差异写成表格，不能以“后台”一词掩盖可靠性缺口。


### 本章项目映射

本章建议直接在 `02_可运行项目/projects/08-workflow-service/` 中完成可运行练习。先执行：阅读有界队列、反压、TaskGroup、超时、取消和 drain 的测试，定位“接受”与“完成”的差异。

```bash
cd 02_可运行项目/projects/08-workflow-service && .venv/bin/python -m pytest
```

**主题化扩展：** 为队列满的路径添加断言，确保新任务在注册前被拒绝且不会留下孤儿 pending 项。

完成后记录输入/输出合同、受控失败、测试命令和安全边界。不要把项目中的本地替身、测试夹具、回环服务或默认无执行模式误作真实网络、模型、生产数据、秘密、部署或副作用授权。

## 参考资料

[1]: https://docs.python.org/3/library/asyncio-queue.html "Python asyncio queues"
[2]: https://docs.python.org/3/library/asyncio-task.html "Python coroutines and tasks documentation"
