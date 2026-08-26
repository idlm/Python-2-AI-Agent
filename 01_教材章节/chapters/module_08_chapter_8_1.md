# 第 8.1 章：接受任务不等于完成任务——服务工作流、状态机与幂等提交

**适用版本：** Python 3.11+  
**项目连接：** `projects/08-workflow-service/`（版本 0.1.0）

## 1. 本章目标

完成本章后，你能够把“用户提交一项工作”拆成接受、等待、执行、成功、失败、取消和恢复候选；能用有限状态机写出允许与禁止的转换；能解释幂等键如何防止重复提交；能区分进程内原型、可靠作业队列和跨重启恢复；并能用不含工作正文的公开状态和日志建立可观察边界。

## 2. 一个常见但危险的回答

某 API 收到“刷新目录”的请求，立刻返回：

```json
{"message": "刷新完成"}
```

实际代码却只是把协程塞进进程内变量，甚至根本没有启动 worker。这个响应把三件不同的事混成一件：**请求已被验证**、**任务已被接受**、**外部工作已成功完成**。网络断开、进程重启、worker 失败、上游写入只做了一半时，调用方没有任何可靠信息。

本章首先建立诚实的语义：如果系统只完成了接受，就返回 `pending`；只有受控执行者报告成功，才进入 `succeeded`。

## 3. 从生产级 Agent 倒推

未来的 Agent 会调用模型、检索器、工具和工作流。每一次工具执行都有状态：尚未开始、已开始、成功、失败、被取消、需要恢复。Agent **不是**某个工作流框架或一条“后台任务”语句；它需要可观察状态、受控工具、记忆边界、明确错误和评测证据。项目 8 的状态机不运行 LLM，也不做自动决策；它先给任何后续 Agent 工作流提供最小、可测试的任务事实。

## 4. 工作流的最小词汇

| 术语 | 本章含义 | 不代表什么 |
|---|---|---|
| 接受（accept） | 输入已通过验证，任务获得 ID 与 `pending` 状态。 | 已开始、已完成或永久保存。 |
| 执行（start） | 一个受控 worker 开始某次尝试。 | 外部副作用一定成功。 |
| 成功（succeed） | worker 在合同内报告成功。 | 所有下游系统永久一致。 |
| 失败（fail） | worker 用受控错误码结束。 | 向客户端暴露 Traceback 或秘密。 |
| 取消（cancel） | 状态机请求任务停止。 | 远端请求一定被撤销。 |
| 恢复候选（recovery candidate） | 中断时 `running` 的任务被标为可重新决策。 | 自动、安全地重放任何操作。 |

先说清术语，才能讨论代码与测试。

## 5. 有限状态机是什么

**有限状态机（finite-state machine，FSM）**把对象限制在有限多个状态，并规定状态间哪些边是合法的。项目 8 使用：

```text
pending ──start──> running ──succeed──> succeeded
   │                    │
   │                    ├─fail──> failed
   │                    └─cancel─> cancelled
   └────cancel─────────> cancelled

running ──process interruption──> pending (recovery candidate)
```

终结状态 `succeeded`、`failed`、`cancelled` 没有下一状态。没有“随便把字符串改成任何值”的后门，调用者必须经过受审查的操作。

## 6. 状态不是布尔值

初学者常用 `done: bool`。它无法回答：任务从未开始还是正在运行？失败还是被取消？失败能否安全重试？中断后要不要恢复？状态机把这些业务区别写成可验证的领域模型：

```python
class TaskState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

`StrEnum` 让状态以字符串方式序列化，但仍提供枚举约束。字符串能传输，并不意味着用户可以提交任意状态。

## 7. 不可变记录降低状态漂移

项目用冻结数据类保存内部任务：

```python
@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    task_type: str
    work_reference: str
    idempotency_key: str
    state: TaskState
    attempts: int
    recoveries: int
    error_code: str | None
    created_at: str
    updated_at: str
```

每次转换以 `dataclasses.replace()` 创建新记录，再在注册表中替换旧记录。不可变记录不能自动解决并发或持久化，却能防止多个函数随手修改同一对象字段；状态变化集中在少数可审计方法中。

## 8. 内部记录与公开视图必须分开

`work_reference` 可能是目录、客户编号、查询条件或含敏感语义的业务引用；`idempotency_key` 也可能被用来关联调用重试。它们不应默认回显。项目单独定义：

```python
@dataclass(frozen=True)
class PublicTask:
    task_id: str
    task_type: str
    state: TaskState
    attempts: int
    recoveries: int
    error_code: str | None
    created_at: str
    updated_at: str
```

> **设计原则：** 公开响应是一份有意缩小的信息合同，不是把内部对象转成 JSON 的偶然结果。

## 9. 任务类型必须是允许列表

以下 API 设计危险：

```json
{"task_type": "python -c '...'", "argument": "..."}
```

它把配置或请求变成任意代码执行入口。项目在构造 `WorkflowRegistry` 时接收固定集合，例如 `refresh_catalog`、`rebuild_index`；未知任务类型立即抛 `TaskRequestError`。任务类型只选择**已写进代码、已测试**的业务行为，不能选择模块路径、shell 命令或任意 callable。

## 10. 工作引用也需要输入合同

允许任务类型不够；工作引用同样需要约束。项目要求它是 1–160 个字符的非空字符串且没有控制字符：

```python
TaskRequest(
    task_type="refresh_catalog",
    work_reference="catalog-2026-08",
    idempotency_key="accept-catalog-001",
)
```

这只是最小文本边界。真实系统应进一步使用领域 ID、受控路径、数据库外键或 URL 允许列表验证引用，不应把任意 URL、文件路径或用户正文直接交给后台执行者。

## 11. 幂等：重发不是重复执行

网络客户端经常遇到超时：请求可能已经到达服务器，响应却在途中丢失。若客户端直接重新提交，系统可能创建两份工作、发送两封邮件或发起两次扣费。**幂等键（idempotency key）**把“同一业务提交”的重试关联起来。

项目以幂等键索引任务；若任务类型与工作引用也相同，则返回原任务；若相同键对应不同工作，则抛 `IdempotencyConflictError`。它不默默选一条，更不覆盖旧工作。

## 12. 幂等的正确边界

| 调用情况 | 项目行为 | 原因 |
|---|---|---|
| 同一键、同一类型、同一引用 | 返回同一 `task_id`。 | 允许安全重试“接受”步骤。 |
| 同一键、不同引用 | 冲突错误。 | 调用方逻辑不一致，不能猜测。 |
| 不同键、相同引用 | 新任务。 | 是否去重执行是另一条业务规则。 |
| 同一任务被调用 `start()` 两次 | 第二次非法转换。 | 一次尝试必须有清楚边界。 |
| 已成功任务再 `start()` | 非法转换。 | 状态机不让终结状态回到运行。 |

幂等不是万能去重；它只保证**由同一键定义的接受合同**。外部副作用是否可安全重试，还要看目标系统、事务和业务设计。

## 13. 接受操作的实现

```python
public = registry.accept(
    TaskRequest(
        task_type="refresh_catalog",
        work_reference="catalog-2026-08",
        idempotency_key="accept-catalog-001",
    )
)
assert public.state is TaskState.PENDING
```

`accept()` 首先验证任务类型和文本边界，在锁内检查已有幂等合同、检查容量、生成不可预测任务 ID、创建 `pending` 记录并返回公开视图。日志只写：

```text
INFO workflow_task_accepted task_type=refresh_catalog
```

它不写工作引用、幂等键、请求正文或调用者秘密。

## 14. 为什么需要容量上限

无界注册表会在错误客户端、重试风暴或恶意请求下无限占用内存。项目构造时要求 `max_tasks > 0`，达到上限后以 `CapacityExceededError` 拒绝新任务。容量上限不是完整流量治理；生产系统还需认证、授权、速率限制、持久化配额、监控和过期清理，但它先使“无限增长”不能成为默认行为。

## 15. `start()` 与尝试次数

`start()` 只能把 `pending` 转为 `running`，并将 `attempts` 加一。为什么不在 `accept()` 时加一？因为接受请求不代表 worker 真的获得工作。`attempts` 是执行边界事实：它帮助调用方和运维人员区分“排队太久”与“已经尝试并失败”。

当前原型没有 worker，因此测试直接调用 `start()` 模拟受控执行者。下一章会把“谁可以调用 start”交给有界队列和结构化 worker。

## 16. 成功与失败必须是不同操作

```python
registry.succeed(task_id)
registry.fail(task_id, error_code="upstream_failed")
```

失败使用白名单风格错误代码，如 `execution_failed`、`timeout`、`upstream_failed`，而不是 `str(exception)` 或 Traceback。调用方可据此选择重试、展示提示或人工升级；秘密主机名、SQL、token、原始页面和内部栈信息仍留在受控诊断系统，不进入公共响应。

## 17. 取消是请求，不是时间机器

状态机允许将 `pending` 或 `running` 任务标为 `cancelled`。运行中的协程还必须在下一个可取消点响应 `CancelledError`，通过 `try/finally` 清理，再继续传播取消；Python 官方不建议吞掉取消，因为 `TaskGroup` 和超时机制都依赖它。[1] 即使本地任务已取消，之前发出的 HTTP 请求、文件写入或远端 API 副作用也未必能撤销。

因此 API 文案应说“已请求/已记录取消”，不要承诺“世界恢复到未发生”。

## 18. 中断恢复候选不是自动重放

进程在 `running` 时崩溃或被停止，内存中没有可靠证据说明外部工作做到哪一步。项目提供：

```python
candidates = registry.mark_interrupted_for_recovery()
```

它把仍在运行的任务标回 `pending`，增加 `recoveries` 并写入 `error_code="interrupted"`。这表示“需要恢复策略判断”，不是“必定重跑”。如果任务会发送邮件、扣费、移动文件或写第三方数据，重跑前必须结合幂等键、外部查询、操作清单和人工审批。

## 19. 进程内原型的诚实限制

| 能力 | 项目 8 当前提供 | 尚未提供 |
|---|---|---|
| 状态 | 单进程、带锁的内存注册表。 | 跨进程共享、数据库持久化。 |
| 幂等 | 当前进程内同键重试返回同任务。 | 跨重启全局幂等保证。 |
| 恢复 | 将内存中的 running 标为候选。 | 崩溃后从磁盘恢复运行中任务。 |
| 并发 | 保护注册表字典的一把 `RLock`。 | 多 worker 领取、租约、分布式锁。 |
| 执行 | 测试模拟显式转换。 | 持久队列、重试调度、长期 worker。 |

准确说出“不提供什么”不是削弱项目，而是可靠性设计的起点。

## 20. 为什么不用 FastAPI `BackgroundTasks` 代替状态机

FastAPI 的 `BackgroundTasks` 可安排函数在响应返回后执行，适合客户端无需等待的短小后置操作；任务函数可为同步或异步函数。[2] 官方同时提示：重型工作或不需要同进程共享内存的工作，可能更适合带消息/作业队列管理器的多进程或多服务器工具。[2]

`BackgroundTasks` 解决“响应后调用函数”的框架接线，不自动定义任务状态、幂等、容量、取消、结果、跨重启恢复或外部副作用合同。因此我们先实现框架无关状态机，再在第 8.3 章审慎接入服务生命周期。

## 21. 测试给状态语义作证

项目 `tests/test_core.py` 当前覆盖十项合同：公开视图不含工作引用；相同幂等合同返回同一任务；同键不同工作冲突；未知类型、控制字符和容量拒绝；开始—成功路径；失败错误码；取消；中断恢复；未知任务；日志不含工作引用。测试不证明分布式可靠性，却能防止未来改动悄悄把 `pending` 当作成功、泄露工作引用或允许非法状态跳跃。

## 22. 快速测试（5 题）

1. `pending` 与 `running` 在调用方可观察语义上有什么不同？
2. 为什么同一幂等键、不同工作引用必须报冲突，而不是创建新任务？
3. 为什么公开任务视图不直接返回 `work_reference`？
4. 取消一个 `running` 任务为何不能证明远端副作用已撤销？
5. `mark_interrupted_for_recovery()` 为什么不应自动重新执行任务？

**答案要点：** 1. 前者仅接受，后者已有 worker 开始尝试；2. 不能猜测重复请求的业务意图；3. 最小化泄露与耦合；4. 本地取消与远端已发生操作不同；5. 中断时未知外部进度，可能造成重复副作用。

## 23. 代码阅读（2 题）

1. 阅读 `WorkflowRegistry.accept()` 中 `_idempotency` 的三元组。它为什么保存任务类型、工作引用和任务 ID，而不只保存任务 ID？请说明同键冲突如何被检测。
2. 阅读 `_transition()`、`_replace()` 和 `TaskRecord(frozen=True)`。哪个方法检查旧状态？哪个方法更新时间？如果把状态字段直接设为任意字符串，会失去哪些测试能力？

## 24. Debug（2 题）

1. 故意把 `succeed()` 的 `expected={TaskState.RUNNING}` 改成 `{TaskState.PENDING, TaskState.RUNNING}`，运行测试。它会允许什么谎言？恢复代码并新增一个测试，明确拒绝“未开始即成功”。
2. 故意将 `PublicTask` 增加 `work_reference`，运行脱敏日志/公开视图测试。设计一条 API 集成测试，证明响应 JSON 和日志都不会包含该引用。

## 25. 编程练习（3 题）、逆向设计与课后项目

**编程练习：** 1. 增加 `retryable` 字段和固定的失败分类，定义哪些失败可重试，并防止终结任务直接被 `start()` 重放。2. 设计“优先级”字段，但只允许三个预定义等级；说明优先级改变能否影响已运行任务。3. 为任务增加受控过期时间，写测试证明过期的 `pending` 任务进入明确状态，而非无限堆积。

**逆向设计：** 某服务收到请求后调用 `asyncio.create_task(do_anything(payload))` 并返回 `{"done": true}`；不保存 Task 引用、不验证任务类型、不限制内存、不提供任务 ID、允许客户端传任意状态、异常只打印 Traceback、重启后忽略任务。请从接受/完成语义、引用生命周期、状态图、幂等、输入、容量、取消、隐私、重启、外部副作用和可观测性至少倒推十一项风险，并为每项写出可测试的公开合同。

**课后项目：** 构建“可审计目录刷新工作流”。要求：固定任务类型允许列表；字段严格 Schema；幂等接受；状态机、尝试次数、受控失败码、取消请求与恢复候选；公开响应/日志不得回显来源正文、token 或原始错误；所有转换有单元测试；为中断、同键冲突、容量、非法状态、取消清理和外部重复副作用写故障矩阵。下一章再接入有界队列；在完成持久化、权限、速率限制和外部幂等前，README 必须明确不能部署为生产作业系统。


### 本章项目映射

本章建议直接在 `projects/08-workflow-service/` 中完成可运行练习。先执行：阅读核心状态机、幂等键和公开视图，绘制 pending/running/completed/failed/cancelled 的允许转换。

```bash
cd projects/08-workflow-service && .venv/bin/python -m pytest
```

**主题化扩展：** 新增一个非法状态转换测试；重复键若引用不同工作必须返回冲突而不是覆盖旧记录。

完成后记录输入/输出合同、受控失败、测试命令和安全边界。不要把项目中的本地替身、测试夹具、回环服务或默认无执行模式误作真实网络、模型、生产数据、秘密、部署或副作用授权。

## 参考资料

[1]: https://docs.python.org/3/library/asyncio-task.html "Python coroutines and tasks documentation"
[2]: https://fastapi.tiangolo.com/tutorial/background-tasks/ "FastAPI: Background Tasks"
