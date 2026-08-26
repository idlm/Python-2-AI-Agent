# 第 8.3 章：服务关闭时，任务去了哪里——FastAPI 生命周期、202 合同与恢复边界

**适用版本：** Python 3.11+  
**项目连接：** `projects/08-workflow-service/`（版本 0.1.0）

## 1. 本章目标

完成本章后，你能够用 FastAPI `lifespan` 管理服务级资源；能设计诚实的 `202 Accepted` 任务 API；能把状态机和 worker 通过可注入运行时组合；能区分短小的 `BackgroundTasks`、进程内队列和持久化作业系统；能在关闭时形成中断恢复候选；并能为请求 ID、公开错误、日志脱敏和本地服务器验收建立稳定合同。

## 2. 服务不是一个导入时运行的全局字典

以下写法看似简单：

```python
registry = WorkflowRegistry(...)
engine = WorkflowWorkerEngine(...)
app = FastAPI()
```

它的问题不是语法，而是生命周期不清楚：测试导入模块时是否已创建资源？服务开始接收请求前是否完成初始化？关闭时谁释放资源、停止 worker、记录中断？是否能为每个测试注入独立状态？生产服务不能把这些问题留给“进程恰好怎样启动”。

## 3. 从生产级 Agent 倒推

未来 Agent 服务会拥有模型客户端、工具注册表、记忆存储、评测追迹和工作流状态。它们都需要明确的创建、使用、关闭和恢复边界。Agent 不是 FastAPI 应用对象；FastAPI 只是 HTTP 边缘。若模型客户端、队列或任务状态在导入时悄悄启动，就很难测试、升级、限流、停机或审计。

## 4. 生命周期是什么

FastAPI 文档说明，应用开始接收请求前可以运行一次初始化逻辑，关闭时可以运行一次清理逻辑；它们覆盖整个应用生命周期。[1] 适合的资源包括共享连接池、只读模型、受控注册表和关闭清理器。项目 8 把 `WorkflowRegistry` 与 `WorkflowWorkerEngine` 组合成 `WorkflowRuntime`，由应用生命周期拥有，而非由某个路径函数临时拼装。

## 5. `lifespan` 的 `yield` 边界

```python
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    LOGGER.info("workflow_service_started")
    try:
        yield
    finally:
        recovered = runtime.registry.mark_interrupted_for_recovery()
        LOGGER.info("workflow_service_stopped recovery_candidates=%s", len(recovered))
```

`yield` 前运行于开始接收请求前，后运行于停止时。[1] `try/finally` 保证即使关闭路径有取消或异常，恢复候选逻辑仍有机会运行。日志只写计数，不能写任务工作引用、payload 或幂等键。

## 6. 不要混用生命周期模型

FastAPI 推荐 `lifespan` 参数处理启动与关闭；文档还指出，一旦提供 lifespan，旧的 startup/shutdown event handlers 不会被调用。[1] 项目选一种模型并坚持到底。混用两种初始化通道会导致资源重复创建、关闭顺序不确定或测试与生产行为不同。

## 7. 可注入 runtime 让测试可信

```python
def create_app(*, runtime: WorkflowRuntime | None = None) -> FastAPI:
    selected_runtime = runtime or _default_runtime()
    app = FastAPI(lifespan=lifespan)
    app.state.workflow_runtime = selected_runtime
    return app
```

生产可调用 `create_app()` 得到默认受控原型；测试可传入自己的 registry 和 engine，精确构造队列满、任务 running、关闭恢复或特殊 handler 情况。可注入不是为了“随便替换任何代码”，而是让有明确协议的依赖可替换和可验证。

## 8. 为什么返回 `202 Accepted`

当服务验证输入、建立任务、放入进程内队列，却没有完成外部工作时，最诚实的 HTTP 状态是 `202 Accepted`。FastAPI 的后台任务文档也用“先返回已接受，再处理慢操作”说明这种场景。[2] 响应应包含任务 ID、当前 `pending` 状态和查询地址，而不是 `{"done": true}`。

```http
POST /tasks
Idempotency-Key: catalog-refresh-001

HTTP/1.1 202 Accepted
Location: /tasks/task-...
```

## 9. 接受响应的最小 Schema

```json
{
  "task_id": "task-...",
  "task_type": "refresh_catalog",
  "state": "pending",
  "attempts": 0,
  "recoveries": 0,
  "error_code": null,
  "created_at": "...+00:00",
  "updated_at": "...+00:00",
  "request_id": "demo-accept"
}
```

响应刻意不包含 `work_reference`、`Idempotency-Key`、内部 handler 名称、队列大小、Python 对象或异常正文。调用者能安全地轮询任务状态，却无法把服务 API 当作内部数据转储通道。

## 10. 请求 Schema 和请求头是不同合同

项目的 JSON 请求体仅允许：

```json
{"task_type": "refresh_catalog", "work_reference": "catalog-2026-08"}
```

Pydantic 以 `extra="forbid"` 拒绝未知字段；幂等键在 `Idempotency-Key` 头中，并限制长度。把“要做什么”放进正文，把“这是否为同一次接受重试”放进专门头字段，能让语义和日志脱敏规则更清楚。两者都不等于认证；鉴权将在服务安全阶段单独设计。

## 11. 请求 ID 的作用

中间件读取调用方提供的 `X-Request-ID`，或生成随机 ID；它把 ID 放回响应头与公开响应字段：

```text
INFO workflow_api_request_completed method=POST path=/tasks status=202 request_id=...
```

请求 ID 用于关联一次 HTTP 调用的公开结果与脱敏服务日志；它不是用户 ID、登录令牌、幂等键或永久跟踪标识。项目的测试确认健康、接受和查询都保留请求 ID。

## 12. 统一公开错误，不回显输入

| 条件 | HTTP 状态 | `error.code` | 公开信息 |
|---|---:|---|---|
| 未知任务 | 404 | `task_not_found` | 找不到任务。 |
| 同键不同工作 | 409 | `idempotency_conflict` | 幂等键已用于不同请求。 |
| 非法状态取消 | 409 | `task_state_conflict` | 当前状态不允许该操作。 |
| 不允许任务类型 | 400 | `task_request_rejected` | 不符合服务合同。 |
| Schema/未知字段/缺少头 | 422 | `invalid_request` | 格式或字段不符合合同。 |
| 内存队列满 | 503 | `queue_busy` | 当前不能接受新任务。 |

这些错误不回显原始 JSON、工作引用、幂等键、异常信息或内部字段定位。日志和受控诊断系统可以有更多细节，但必须有访问控制与保留策略。

## 13. `BackgroundTasks` 能做什么

FastAPI 的 `BackgroundTasks` 允许在响应返回后运行函数，函数可以是普通 `def` 或 `async def`，并可通过依赖注入在多层收集任务。[2] 对于短小的同进程后置操作，例如写非敏感通知或轻量记录，它很方便。

```python
@app.post("/send")
async def send(background_tasks: BackgroundTasks) -> dict[str, str]:
    background_tasks.add_task(write_notification)
    return {"status": "accepted"}
```

它解决的是“响应后执行函数”，不是通用工作流状态系统。

## 14. `BackgroundTasks` 不做什么

FastAPI 官方明确警示：重型计算或无需与同一进程共享内存的工作，可能应使用有消息/作业队列管理器的更大工具，以在多进程、多服务器执行。[2] `BackgroundTasks` 不自动给你：持久化投递、全局幂等、任务查询、进度、取消、租约、重试计划、跨重启恢复、分布式锁、权限或审计。

项目 8 因此不把 `BackgroundTasks` 当作“可靠后台作业”的同义词。先用状态机与有界队列说明原理，再让读者根据真实需求选择架构。

## 15. 三种实现的比较

| 方案 | 适合什么 | 主要缺口/代价 |
|---|---|---|
| `BackgroundTasks` | 很短小、同进程、响应后可做的工作。 | 无可靠队列和跨重启保证。 |
| 本项目进程内 `asyncio.Queue` | 教学、一次进程内批处理、确定性测试、明确反压。 | 内存状态；重启/崩溃丢工作。 |
| 持久化队列与独立 worker | 长任务、重试、跨进程、多主机、需要投递保证的产品。 | 需数据库/消息系统、监控、权限、成本与运维设计。 |

选择取决于任务时长、失败成本、吞吐、是否需跨重启、是否需管理界面和数据位置；不能因为某方案代码更短就假定它可靠。

## 16. 关闭时的“中断恢复候选”

服务关闭时，项目把仍为 `running` 的任务改为 `pending`，增加 `recoveries`，并标记 `error_code="interrupted"`。测试在关闭 `TestClient` 后验证这条合同。它回答的是“本进程最后看到任务在运行”，而非“工作没有发生”。

若任务调用了外部系统，恢复前必须问：目标是否已成功？该操作是否幂等？是否有操作清单？是否需要人工批准？没有这些证据时，自动重放可能比停止更危险。

## 17. 进程崩溃与正常关闭不同

`lifespan` 的 finally 适用于框架有机会执行关闭流程的情况。断电、强制终止、内核崩溃、进程被立即杀死时，finally 可能根本来不及运行。项目的内存 registry 也会随进程消失。因此不能把本章的关闭恢复候选宣传成崩溃安全。

真正的恢复至少需要持久状态、事务边界、租约/心跳、外部幂等与过期策略；这些会在后续工程化和部署模块中讨论。

## 18. 取消与生命周期关闭的区别

调用方取消一个任务时，服务可取消当前进程持有的 handler task，并记录 `cancelled`。服务关闭时，不应简单把所有任务改为 `cancelled`：有些已经完成外部操作，有些需要恢复，有些是正常 drain。项目选择把仍运行的任务标为恢复候选，让后续策略显式判断。

> **规则：** “用户请求取消”“本地协程被取消”“服务正在关闭”“远端操作取消成功”是四个不同事实。

## 19. 本地服务器运行证据

```bash
cd /home/ubuntu/python_private_course/projects/08-workflow-service
.venv/bin/course-workflow-service --serve --host 127.0.0.1 --port 8018
```

命令只允许 `127.0.0.1` 或 `localhost`，避免教学原型暴露到网络。真实本地验收覆盖：健康检查返回调用方请求 ID；`POST /tasks` 返回 `202`、`pending` 和 Location；读取同一任务；取消任务；未知任务类型返回受控 `400`；公开响应不包含工作引用。验收结束后必须停止服务，不能把 sandbox 中的临时进程当部署。

## 20. 测试生命周期，而不是只测路径函数

FastAPI 生命周期不会在所有测试写法中自动触发；项目使用：

```python
with TestClient(app) as client:
    assert client.get("/health").status_code == 200
# 离开上下文后断言 running 已变为恢复候选
```

测试先建立 `running` 任务，进入客户端触发启动，退出客户端触发关闭，再验证 `pending/recoveries/error_code`。这比只调用 `create_app()` 更接近服务实际边界。

## 21. API 层的最小安全清单

| 边界 | 项目措施 | 后续仍需补充 |
|---|---|---|
| 输入 | 固定模型、未知字段拒绝、任务允许列表。 | 身份认证、授权、租户隔离。 |
| 执行 | 有界队列、固定 handler、超时与取消。 | 持久队列、租约、独立 worker。 |
| 数据 | 公开视图不含工作引用。 | 加密、保留/删除、审计访问控制。 |
| 错误 | 稳定代码与最小消息。 | 受控诊断、告警、错误预算。 |
| 生命周期 | lifespan 与恢复候选。 | 崩溃恢复、部署 drain、健康/readiness。 |

## 22. 快速测试（5 题）

1. 为什么 `202 Accepted` 不应被客户端理解为任务成功？
2. `lifespan` 的 `yield` 前后各适合什么工作？
3. 为什么 `BackgroundTasks` 不能自动替代持久化作业队列？
4. 正常关闭时把 `running` 标为恢复候选，为什么比标为 `succeeded` 更诚实？
5. 请求 ID 与幂等键在用途上有什么不同？

**答案要点：** 1. 仅表示接受；2. 前初始化、后清理/关闭记录；3. 缺持久投递、跨重启、状态等保证；4. 外部进度未知；5. 前者关联一次请求，后者关联同一提交重试。

## 23. 代码阅读（2 题）

1. 阅读 `create_app()` 与嵌套 `lifespan()`。为什么 `selected_runtime` 在闭包中而不是每个请求重新创建？`app.state` 在此承担什么角色？
2. 阅读 `RequestValidationError`、`TaskRequestError` 和 `WorkflowError` 的处理器。它们为什么需要不同状态码？为何都返回同一 `ErrorEnvelope`？

## 24. Debug（2 题）

1. 把 `accept_task()` 的状态码改成 `200` 并把响应 `state` 写成 `succeeded`，运行 API 测试。说明这会怎样误导轮询客户端和监控；恢复 `202/pending` 合同。
2. 暂时删除 lifespan 的 finally，构造 running 任务后退出 `TestClient`。恢复测试并解释为何进程内测试通过不等于实际崩溃安全。

## 25. 编程练习（3 题）、逆向设计与课后项目

**编程练习：** 1. 增加受控 `GET /tasks/{id}/events` 轮询摘要，返回状态变化编号但不引入 WebSocket；定义分页和保留上限。2. 设计 `Retry-After` 响应头用于 `queue_busy`，并证明它只是建议，不保证容量何时释放。3. 为 `task_type` 增加权限依赖接口；写一个测试替身证明未授权调用在入队前被拒绝。

**逆向设计：** 某服务把全局 worker 在模块导入时启动；每个请求用 `BackgroundTasks` 执行任意 payload；返回 `200 done`；异常回显；关闭时杀死进程；没有请求 ID、幂等、队列容量、状态查询或身份边界。请从测试隔离、部署多 worker、重启、重复、权限、秘密、停止、观测、错误、成本与 Agent 工具执行至少倒推十一项风险，并写出逐项门禁。

**课后项目：** 完成“目录刷新工作流 API”。要求：以 lifespan 管理 runtime；`POST` 返回真实 `202`；通过请求头幂等；任务查询/取消、公开错误和请求 ID；本地回环 CLI；队列满、生命周期中断、无效输入、同键冲突和日志脱敏集成测试；README 比较 `BackgroundTasks`、进程内队列与持久队列。加分项是设计持久化 schema、租约和 outbox，但不得在未实现前声称跨重启可靠。


### 本章项目映射

本章建议直接在 `projects/08-workflow-service/` 中完成可运行练习。先执行：阅读 FastAPI lifespan、关停恢复候选、请求 ID 和 API 合同，理解服务停止并不等于外部结果已知。

```bash
cd projects/08-workflow-service && .venv/bin/python -m pytest
```

**主题化扩展：** 为优雅关停后的 interrupted 任务增加恢复候选测试；不得自动标记成功或无限制重放。

完成后记录输入/输出合同、受控失败、测试命令和安全边界。不要把项目中的本地替身、测试夹具、回环服务或默认无执行模式误作真实网络、模型、生产数据、秘密、部署或副作用授权。

## 参考资料

[1]: https://fastapi.tiangolo.com/advanced/events/ "FastAPI: Lifespan Events"
[2]: https://fastapi.tiangolo.com/tutorial/background-tasks/ "FastAPI: Background Tasks"
[3]: https://docs.python.org/3/library/asyncio-queue.html "Python asyncio queues"
[4]: https://docs.python.org/3/library/asyncio-task.html "Python coroutines and tasks documentation"
