# 项目 8：受控服务工作流

**版本：** 0.1.0  
**兼容性：** Python 3.11+  
**课程位置：** 模块 8——服务工作流、受控后台执行、状态、取消与恢复边界。

本项目实现一个**单进程、短任务**服务工作流教学原型。它将“HTTP 已接受”与“工作已完成”分开：请求先经过允许列表、严格 Schema、幂等键和有界队列，返回 `202 Accepted` 与 `pending`；受控 worker 才能把任务推进到 `running`、`succeeded`、`failed` 或 `cancelled`。生命周期关闭时，仍处于 `running` 的任务会标记为中断恢复候选，而不会被伪装为成功。

> **重要边界：** 该项目不是持久化作业队列、跨进程锁、跨重启投递保证、分布式事务或长期后台 worker。`pending` 只说明服务已接受工作；`cancelled` 不证明第三方副作用已经撤销；进程内恢复候选不等于可安全自动重放。

## 安装与质量门禁

```bash
cd /home/ubuntu/python_private_course/projects/08-workflow-service
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"

.venv/bin/python -m pytest
.venv/bin/python -m mypy
.venv/bin/python -m ruff check src tests
```

当前有 **25 项 pytest**，并通过 mypy 与 Ruff。测试覆盖状态机、允许列表、幂等冲突、容量、状态转换、反压、固定 worker 处理器、TaskGroup、超时、取消清理、并发上限、FastAPI 生命周期、公开错误、请求 ID 和日志正文脱敏。

## HTTP 合同

| 操作 | 路径 | 成功语义 | 公开边界 |
|---|---|---|---|
| 健康检查 | `GET /health` | `200` 与请求 ID。 | 不暴露依赖版本、队列正文或秘密。 |
| 接受任务 | `POST /tasks` | `202`，状态为 `pending`；`Location` 指向任务。 | 必须提供 `Idempotency-Key`；不回显工作引用或幂等键。 |
| 列表 | `GET /tasks` | 返回小规模公开任务视图。 | 不含 `work_reference`。 |
| 查询 | `GET /tasks/{task_id}` | 返回当前公开状态。 | 不存在时稳定 `404 task_not_found`。 |
| 取消 | `POST /tasks/{task_id}/cancel` | 返回 `cancelled`，并取消当前进程持有的处理器 task（如有）。 | 不承诺撤销远端副作用。 |

接受请求的最小示例：

```bash
curl -X POST http://127.0.0.1:8018/tasks \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: catalog-refresh-001' \
  -H 'X-Request-ID: demo-accept' \
  --data '{"task_type":"refresh_catalog","work_reference":"catalog-2026-08"}'
```

响应只承诺接受事实：

```json
{
  "task_id": "task-...",
  "task_type": "refresh_catalog",
  "state": "pending",
  "attempts": 0,
  "recoveries": 0,
  "error_code": null,
  "created_at": "2026-08-26T00:00:00+00:00",
  "updated_at": "2026-08-26T00:00:00+00:00",
  "request_id": "demo-accept"
}
```

## 状态与执行合同

| 状态 | 含义 | 允许下一状态 |
|---|---|---|
| `pending` | 已验证、已接受、已入进程内队列。 | `running`、`cancelled`。 |
| `running` | worker 已开始一次尝试。 | `succeeded`、`failed`、`cancelled`；中断后可标为恢复候选。 |
| `succeeded` | handler 在当前合同内成功返回。 | 无。 |
| `failed` | 以允许错误代码结束，例如 `timeout`、`execution_failed`。 | 无。 |
| `cancelled` | 服务已记录取消；handler 需用 `finally` 清理。 | 无。 |

队列只存 `task_id`，处理器映射必须与任务类型允许列表完全一致。队列满时新任务返回受控 `503 queue_busy`，且不会先注册为无法执行的孤儿任务；同一幂等合同会返回已有任务。`TaskGroup` 管理固定数量 worker，`task_done()/join()` 管理 drain，单任务超时和取消均有明确状态与清理测试。

## 启动本地教学服务

```bash
.venv/bin/course-workflow-service --status
.venv/bin/course-workflow-service --serve --host 127.0.0.1 --port 8018
```

命令只允许绑定 `127.0.0.1` 或 `localhost`，防止教学原型被误作公开服务。它不自动启动长期 worker、定时轮询或外部回调。真实 HTTP 验收已验证健康检查、`202` 接受、任务读取、取消、未知类型 `400` 与响应不含工作引用。

## FastAPI 生命周期与恢复

服务以 `lifespan` 创建和释放进程内运行时；FastAPI 文档说明 `yield` 前的代码在接收请求前运行，后的代码在服务关闭时运行。[2] 关闭时本项目将仍在 `running` 的状态标为 `pending` 恢复候选并增加 `recoveries`，但在没有持久化状态、外部幂等检查和操作清单前，不会自动重跑。

FastAPI 的 `BackgroundTasks` 适合响应后的小型同进程操作；官方同时提示重型或无需共享同一进程内存的工作可能更适合使用消息/作业队列管理器。[1] 本项目因此把 `BackgroundTasks`、内存队列和可靠持久队列明确区分，而不是把任何异步函数称为“可靠后台任务”。

## 目录结构

```text
08-workflow-service/
├── pyproject.toml
├── README.md
├── .gitignore
├── .github/workflows/quality.yml
├── src/workflow_service/
│   ├── __init__.py
│   ├── api.py
│   ├── cli.py
│   ├── core.py
│   └── worker.py
└── tests/
    ├── test_api.py
    ├── test_core.py
    └── test_worker.py
```

## 参考资料

[1]: https://fastapi.tiangolo.com/tutorial/background-tasks/ "FastAPI: Background Tasks"
[2]: https://fastapi.tiangolo.com/advanced/events/ "FastAPI: Lifespan Events"
[3]: https://docs.python.org/3/library/asyncio-queue.html "Python asyncio queues"
[4]: https://docs.python.org/3/library/asyncio-task.html "Python coroutines and tasks documentation"
