# 模块 8 官方资料核对笔记

**核对日期：** 2026-08-26（GMT+8）  
**用途：** 为模块 8 的服务工作流、后台任务、队列、状态、取消与恢复章节建立可引用事实边界；面向 Python 3.11+ 初学者。

| 主题 | 已核对结论 | 教材使用边界 | 来源 |
|---|---|---|---|
| FastAPI 后台任务 | `BackgroundTasks` 可把函数安排在响应返回后运行；任务函数可为 `def` 或 `async def`，并可通过依赖注入收集任务。 | 仅用于同进程、短小且不需独立可靠投递的后置工作；不能把“已接受”误写成已完成或持久化队列。 | [1] |
| 后台重计算警告 | FastAPI 官方明确指出，重型后台计算或不必在同一进程运行的工作，可能应使用带消息/作业队列管理器的多进程/多服务器工具。 | 教学项目用进程内工作流证明状态机、取消与恢复合同；明确它不是持久化作业队列、跨重启保证或生产 worker。 | [1] |
| 生命周期 | FastAPI `lifespan` 的 `yield` 前在开始接收请求前执行，后在应用关闭时执行；推荐以 `lifespan` 处理共享资源初始化与释放。 | 启动初始化和关停清理放在 lifespan；不混用 `lifespan` 与旧 startup/shutdown 事件，并测试关闭时取消/清理。 | [2] |
| asyncio Queue | `asyncio.Queue(maxsize)` 是面向 async/await 的 FIFO 队列，不线程安全；正 maxsize 时 `put()` 会在队列满时等待，提供反压。`task_done()` 与 `join()` 用于跟踪处理完成。 | 用有界队列展示请求接收与工作执行分离；不把内存队列称作跨进程/跨重启/持久队列。 | [3] |
| 队列超时和关闭版本 | asyncio 队列方法自身无 timeout 参数；可用 `asyncio.wait_for()`。较新的 Python 有 `Queue.shutdown()`，但 Python 3.11 教材不能依赖它。 | 项目兼容 3.11：以显式停止信号、TaskGroup 与取消清理管理 worker，不使用仅 3.13+ 的 Queue.shutdown。 | [3] |
| 任务引用与 TaskGroup | `asyncio.create_task()` 返回的 Task 应保留强引用；TaskGroup 保持相关任务引用、退出时等待，并在非取消失败时取消其余任务、传播异常。 | 不用无引用 fire-and-forget；工作流以 TaskGroup 管理 worker 生命周期，任务状态持久化在边缘层单独设计。 | [4] |
| 取消与超时 | 取消会在下一机会在任务中引发 `CancelledError`；官方建议用 `try/finally` 清理，并通常在显式捕获后继续传播。`asyncio.timeout()` 取消当前任务并在上下文外转换为 `TimeoutError`。 | 取消/超时必须更新受控状态并清理，但本地取消不保证远端副作用撤销；不得吞 `CancelledError`。 | [4] |

## 架构评估（教材原型）

模块 8 的练习属于**进程内、确定性、单进程教学工作流**：读者运行一次 CLI/TestClient 即可验证有界队列、状态迁移、幂等提交、取消与重启恢复决策；不启动长期后台服务、定时任务、轮询或外部回调。故本批采用普通本地可运行项目，不部署自动化。

若以后把它变为长期运行产品，至少有两种路径：一是将受控 API 与持久状态部署为可管理服务，由后台 worker/队列处理短任务；二是采用专用持久队列和多进程 worker 管理重任务、重试与跨重启投递。具体选型需由任务时长、吞吐、管理界面、外部服务、数据地点和成本决定，不能由课堂原型自动推断。

## 初步章节落点

| 候选章节 | 核心问题 | 最小可运行证据 |
|---|---|---|
| 8.1 | HTTP 接受请求后，怎样用状态机而不是“后台已完成”的谎言表达工作流？ | 框架无关任务状态机与非法迁移/幂等测试。 |
| 8.2 | 有界 Queue、worker、TaskGroup、timeout 与取消怎样安全协作？ | 无网络确定性 worker 测试与 shutdown 清理。 |
| 8.3 | FastAPI 如何以 lifespan 管理短任务原型，并在重启时把未完成状态交给恢复策略？ | 项目服务 API、TestClient、状态/取消/恢复验收。 |

## 引用链接

[1]: https://fastapi.tiangolo.com/tutorial/background-tasks/ "FastAPI: Background Tasks"
[2]: https://fastapi.tiangolo.com/advanced/events/ "FastAPI: Lifespan Events"
[3]: https://docs.python.org/3/library/asyncio-queue.html "Python asyncio queues"
[4]: https://docs.python.org/3/library/asyncio-task.html "Python coroutines and tasks documentation"
