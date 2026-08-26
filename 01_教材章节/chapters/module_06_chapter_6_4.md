# 第 6.4 章：异步不是加速咒语——并发、超时、取消与结构化收尾

**适用版本：** Python 3.11+  
**项目连接：** `examples/module_06/async_reliability.py` 与 `tests/module_06/test_async_reliability.py`

## 1. 本章目标

完成本章后，你能够区分同步、并发、并行、协程、Task 与 Future；能解释直接调用协程为什么不会执行；能以 `TaskGroup` 管理一组相关任务；能用 `asyncio.timeout()` 给出时间预算；能正确传播 `CancelledError` 并在 `finally` 清理；能避免“fire-and-forget”任务和日志泄露结果正文。

## 2. 先纠正一个误解：`async` 不等于更快

`async def` 只定义协程函数。它可能提升多个**等待 I/O**任务的重叠能力，但不会让 CPU 密集计算自动并行，也不会把阻塞的文件、数据库或第三方同步调用变成非阻塞。Python 官方将 asyncio 定位为以 `async`/`await` 写并发 I/O 的库，特别适合 I/O 密集的结构化网络代码。[1] 性能结论必须来自工作负载、测量与瓶颈分析，而非关键字数量。

## 3. 从生产级 Agent 倒推

Agent 会等待模型、工具、检索、数据库、审批和网络。任何一个慢调用都可能占住用户请求；任何一个失败的并行任务都可能留下半完成状态；任何一个无追踪后台任务都可能产生不可见异常。Agent 不是一个异步框架名称，而是有模型、工具、记忆、状态、工作流和评测边界的系统。异步只处理其中“等待与协调”的部分，不能替代状态机、工具允许列表或评测。

## 4. 四个容易混淆的词

| 术语 | 简明定义 | 本章例子 |
|---|---|---|
| 同步 | 当前操作完成前，调用流程不能继续。 | 逐条等待两个任务，总耗时为延时之和。 |
| 并发 | 多个任务在等待点交替推进。 | 两个 `asyncio.sleep()` 共同等待。 |
| 并行 | 多个计算在多个 CPU 核或执行单元同时运行。 | 本章不把协程误称为并行 CPU 计算。 |
| 协程 | 由 `async def` 定义、可在 `await` 处挂起和恢复的可等待对象。 | `run_job()`。 |
| Task | 由事件循环调度的协程执行单元。 | `TaskGroup.create_task()` 返回的任务。 |
| 取消 | 向任务请求停止，通常在下一可取消等待点注入 `CancelledError`。 | 超时取消慢任务。 |

## 5. 调用协程不会运行它

```python
async def fetch() -> str:
    return "结果"

fetch()             # 只得到协程对象，未安排执行。
await fetch()       # 在另一协程中等待执行。
asyncio.run(fetch())  # 在顶层启动一次事件循环运行。
```

Python 官方文档明确说明，直接调用协程不会把它安排执行；顶层可用 `asyncio.run()`，协程内部可 `await`，也可以创建 Task。[2] 漏掉 `await` 往往得到“coroutine was never awaited”警告，而不是可靠的后台工作。

## 6. `await` 是礼让点，不是线程切换

当协程执行 `await asyncio.sleep(...)`、等待网络响应或等待受支持的异步库时，它暂停自己，让事件循环运行其他就绪任务。若协程在 `await` 之间执行长循环、同步 HTTP 请求、大量 JSON 处理或同步 SQLite 调用，其他协程仍会饥饿。项目 6 的 SQLite 仓储是同步的，因此没有被机械塞进 `async def`；下一阶段应在真实负载和驱动能力下决定线程池、异步驱动或队列策略。

## 7. 本章可运行示例

```bash
cd /home/ubuntu/python_private_course
python3 examples/module_06/async_reliability.py
python3 -m unittest discover -s tests/module_06 -p 'test_*.py' -v
```

示例不依赖公网、模型或真实数据库。每个 `TimedJob` 的延时、结果与失败由数据明确描述，因此测试可确定性验证成功、超时、失败和取消。结果可返回给显式调用方，但日志只记录任务名称与阶段，不记录 `result_value`。

## 8. 为什么不能无约束 `create_task()`

`asyncio.create_task()` 会调度协程并返回 Task。官方文档提醒，事件循环只保留 Task 的弱引用；没有其他强引用的任务可能在完成前被垃圾回收。[2] 更重要的是，未等待的任务会让异常无人处理、请求结束后仍运行、日志难关联、资源难清理。若确实需要脱离请求的后台工作，必须另行设计队列、持久化、重试、状态、限额与观测；不要把它伪装成一行 `create_task()`。

## 9. TaskGroup 给相关任务一个共同生命线

```python
async with asyncio.TaskGroup() as group:
    task_a = group.create_task(run_job(job_a), name=job_a.name)
    task_b = group.create_task(run_job(job_b), name=job_b.name)
# 退出块前会等待所有任务收尾。
```

Python 3.11 的 `TaskGroup` 是结构化并发工具：退出上下文前会等待子任务；一个任务以非取消异常失败时，其余任务被取消，异常会组合为 `ExceptionGroup`。[2] 它适合“这组检索/工具调用共同构成一个请求”的情况，因为成功、失败和收尾不再散落在全局任务集合。

## 10. 结果顺序与完成顺序不同

示例让 `slow` 先创建、`fast` 后创建；`fast` 先完成，但 `run_batch()` 按创建任务列表返回结果，所以结果顺序仍为 `[slow, fast]`。这是一个明确 API 合同。调用方不能仅因用了并发就假设结果按完成时间排列；若需要流式结果，应设计带序号、事件类型、错误和最终汇总的单独协议。

## 11. 失败为何会取消兄弟任务

```python
async with asyncio.TaskGroup() as group:
    group.create_task(run_job(broken))
    group.create_task(run_job(sibling))
```

若 `broken` 抛 `JobExecutionError`，`TaskGroup` 取消仍在等待的 `sibling`。这不是“所有并发都必须失败即停止”的绝对规则，而是本组任务的原子工作流语义：不能生成完整答案时，不应让无意义的兄弟工具继续消耗资源或留下错误状态。若业务允许部分成功，应显式定义每项结果与错误的聚合 Schema，而不是依赖偶然行为。

## 12. ExceptionGroup 需要被认真对待

多个任务可能在同一收尾窗口失败，结构化并发会以 `ExceptionGroup` 汇总异常。测试使用 `assertRaises(ExceptionGroup)` 并检查其中存在 `JobExecutionError`，而不是假装只会有一个异常。真实服务应选择合适策略：将某些已知错误转为每项受控结果、取消不再需要的工作、记录去敏元数据，并把不可恢复故障映射为稳定 API 合同。

## 13. 时间预算比“尽量快”更可操作

```python
try:
    async with asyncio.timeout(timeout_seconds):
        async with asyncio.TaskGroup() as group:
            ...
except TimeoutError as exc:
    raise BatchTimedOutError("批任务超过时间预算。") from exc
```

`asyncio.timeout()` 是异步上下文管理器，用于限制等待时间。官方文档说明，超时会取消当前任务，并在上下文外将内部 `CancelledError` 转换为可处理的 `TimeoutError`。[2] 本例将其再映射为领域可读的 `BatchTimedOutError`；HTTP 边缘层未来可把它映射为公开超时/暂不可用响应。

## 14. 超时不是保证远端停止

本地取消表示“本协程不再等待或继续处理”；它不必然撤销已经发送给远端模型、支付系统或第三方工具的请求。对可能产生副作用的远端操作，还需要幂等键、状态查询、补偿动作、审计与人工介入。超时处理只能减少本地资源泄露和等待，不可伪装成全球原子回滚。

## 15. `CancelledError` 应清理后继续传播

```python
except asyncio.CancelledError:
    event_log.append(f"cancelled:{job.name}")
    LOGGER.info("async_job_cancelled name=%s", job.name)
    raise
finally:
    event_log.append(f"cleaned:{job.name}")
```

取消通常会在任务下一个等待机会以 `CancelledError` 出现。官方文档建议协程用 `try/finally` 做清理；若显式捕获取消，通常应在清理后重新抛出，因为 `TaskGroup` 与 `asyncio.timeout()` 依赖取消语义。[2] 吞掉取消会让调用方误判任务成功，也可能破坏结构化并发的收尾。

## 16. `finally` 是释放资源的最后防线

示例无论任务成功、受控失败或被取消，都记录 `cleaned:<name>`。真实系统的 `finally` 可以关闭流、释放文件句柄、归还连接、删除临时文件或结束可撤销会话；它不应在其中执行长时间、不可取消、无超时的网络操作。清理本身若失败也需要可观测的受控策略，不能覆盖原始失败而毫无记录。

## 17. 取消安全不等于结果安全

| 问题 | 本章示例证明 | 仍需在业务中设计 |
|---|---|---|
| 本地协程停止 | `CancelledError` 传播且有清理事件。 | 远端请求是否已执行。 |
| 相关任务收尾 | `TaskGroup` 取消兄弟任务。 | 副作用补偿和最终一致性。 |
| 时间上限 | 超时映射为公开领域错误。 | 调用方重试、退避、配额与熔断。 |
| 日志隐私 | 不记录 `result_value`。 | 访问控制、留存、审计和数据删除。 |

可靠性不是一个 `try/except`；它是一组关于状态、失败、时间和恢复的明确合同。

## 18. 日志记录任务元数据，不记录结果正文

```text
INFO async_job_started name=fast
INFO async_job_completed name=fast
INFO async_job_cleaned name=fast
```

`result_value` 可含用户提问、检索片段、工具输出或秘密，因此示例刻意不在日志里放它。测试 `test_logs_do_not_include_result_value` 先让任务返回敏感字符串，再断言日志不含该字符串。对于生产 Agent，还应定义请求 ID、任务 ID、模型/工具名、耗时、结果长度、错误类别、权限和保留策略；不要以“方便排错”为由默认记录提示词全文。

## 19. 超时、失败与成功的测试矩阵

| 场景 | 测试断言 | 证明的边界 |
|---|---|---|
| 两任务不同延时 | 输出按输入顺序，值正确。 | 并发不改变公开结果合同。 |
| 超时慢任务 | `BatchTimedOutError`、取消与清理事件。 | 时间预算能停止本地等待。 |
| 一个任务失败 | `ExceptionGroup` 中含领域错误，兄弟被取消。 | 结构化失败传播。 |
| 手动取消 | `CancelledError` 继续抛出，清理已执行。 | 不吞取消。 |
| 日志检查 | 结果值不在日志中。 | 观测不扩大正文泄露面。 |

当前异步示例有 7 项 `IsolatedAsyncioTestCase` 测试。测试不使用 `sleep(10)` 或真实网络，因此快速而稳定；应把发现的真实事故再浓缩为这种可复现测试。

## 20. 失败案例：裸后台任务

```python
asyncio.create_task(call_model(prompt))
return {"accepted": True}
```

这段代码至少没有回答：任务引用在哪里？失败谁接收？请求结束后它能否继续？超时与取消是什么？模型实际执行了吗？如何重试？如何写入状态？日志会不会记录 prompt？用户怎样查询结果？正确设计可能是结构化并发，也可能是持久化任务队列；取决于是否需要脱离请求生命周期，而不是开发者是否想“马上返回”。

## 21. 本章验收

运行第 7 节命令。阅读超时测试，解释为何 `cancelled:slow` 和 `cleaned:slow` 都必须出现。接着故意删除 `except asyncio.CancelledError` 中的 `raise`，观察手动取消测试为何失败；恢复重新抛出。最后让 `result_value` 包含一段模拟用户正文，确认返回值保留而日志不出现它。

## 22. 快速测试（5 题）

1. 为什么调用 `async def` 函数本身不等于运行它？
2. 并发与并行在本章中分别是什么意思？
3. `TaskGroup` 中一个非取消异常发生后，为何兄弟任务会停止？
4. 为什么不能随意吞掉 `CancelledError`？
5. 本地超时为何不能证明远端副作用没有发生？

**答案要点：** 1. 只创建协程对象，需等待或调度；2. 并发重叠 I/O 等待，并行是多执行单元同时计算；3. 结构化任务组的共同工作流失败传播；4. 取消和超时的控制语义会失真；5. 远端可能已收到或执行请求，需要幂等与状态协议。

## 23. 代码阅读（2 题）

1. 阅读 `run_batch()`，标出 `tasks` 列表何时获得强引用、`TaskGroup` 何时等待、`TimeoutError` 在哪里被转换，以及 `task.result()` 为什么放在组退出后。
2. 阅读 `run_job()` 的 `try/except/finally`，列出成功、`JobExecutionError` 和 `CancelledError` 三条路径各自写入哪些事件；证明任何路径都不会把 `result_value` 放进 `LOGGER` 调用。

## 24. Debug（2 题）

1. 把 `asyncio.TaskGroup()` 暂时替换为连续的 `await run_job(...)`。运行不同延时测试，测量为何任务不再重叠；恢复 TaskGroup，并解释“更快”只在等待可重叠时成立。
2. 在 `except asyncio.CancelledError` 中删除 `raise`。运行显式取消与超时测试，记录取消为什么被误判为普通完成；恢复 `raise`，再解释超时上下文为何依赖取消传播。

## 25. 编程练习（3 题）、逆向设计与课后项目

**编程练习：** 1. 为 `TimedJob` 增加公开但非敏感的 `kind` 允许列表（例如 `fetch`、`summarize`）；记录 kind 与时长，绝不记录 value，并写非法 kind 与日志脱敏测试。2. 实现 `run_batch_collecting_errors()`：每项返回结构化 `success` 或受控 `error_code`，但仍给整个批次时间预算；解释它为何不同于 TaskGroup 的“全组失败”策略，并为两种策略各写测试。3. 让 `run_job()` 接受一个可取消的资源协议，在 `finally` 调用 `aclose()`；用假的资源对象测试成功、失败与取消时均恰好关闭一次。

**逆向设计：** 某研究 Agent 同时启动十个模型和工具调用，全部用裸 `create_task()`；没有任务引用；超时后只返回“已取消”；捕获并忽略所有异常；把完整 prompt、检索内容和工具输出写日志；把同步 SQLite 连接塞进 `async def`；成功与失败没有状态记录。请从协程调度、引用、取消、远端副作用、事务、隐私、重试、幂等、可观测性、用户状态、评测和人工接管至少倒推十二项风险，并为每项给出可测试合同。

**课后项目：** 实现“受控批处理协调器”。要求：任务输入模型固定、每项有任务 ID 和允许 kind；使用 `TaskGroup`；全组时间预算、单项超时和取消政策明确；任何取消都执行资源清理；返回结构化公开结果而不回显秘密；日志含请求 ID、任务 ID、kind、阶段与耗时但无正文；写至少十五项异步测试（包括并发、部分失败、全组失败、超时、取消、重复取消、日志脱敏）；写 README 的失败矩阵和 Runbook，说明哪些远端副作用无法由本地取消自动撤销。


### 本章项目映射

本章建议直接在 `projects/06-knowledge-api/ 与 examples/module_06/async_reliability.py` 中完成可运行练习。先执行：对照异步示例与服务测试，识别 TaskGroup、超时、取消和 finally 清理的不同责任。

```bash
python3 -m unittest discover -s tests/module_06 -v && cd projects/06-knowledge-api && .venv/bin/python -m pytest
```

**主题化扩展：** 增加一个有限超时测试；结果未知时只报告状态类别，不假设远端或后台工作未发生。

完成后记录输入/输出合同、受控失败、测试命令和安全边界。不要把项目中的本地替身、测试夹具、回环服务或默认无执行模式误作真实网络、模型、生产数据、秘密、部署或副作用授权。

## 参考资料

[1]: https://docs.python.org/3/library/asyncio.html "Python asyncio overview"
[2]: https://docs.python.org/3/library/asyncio-task.html "Python coroutines and tasks documentation"
