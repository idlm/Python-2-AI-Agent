# 项目 6：知识笔记 API

**版本：** 0.2.0  
**兼容性：** Python 3.11+  
**课程位置：** 模块 6——HTTP、API 合同、FastAPI、SQLite、输入输出模型、错误边界、依赖与服务测试

本项目把第 6.1 章的框架无关 HTTP 契约交给 FastAPI 实现。它以 SQLite 持久化知识笔记，提供健康检查、创建、列表和单条读取；每次仓储操作独立建立、提交或回滚并关闭连接。它仍刻意**不**在此版本实现认证用户、文件上传、任意工具执行、跨节点高并发写入或生产灾难恢复。先固定边界，再逐步增加异步、鉴权和 Agent 能力。

> **服务边界：** API 接受且只接受审查过的路径、方法和 Pydantic 请求模型；响应只返回公开字段；错误不回显原始请求体或 Traceback；日志不记录笔记正文。

| 路径与方法 | 成功结果 | 可预期拒绝 |
|---|---|---|
| `GET /health` | `200` 与公开 `status`、`request_id`。 | 不暴露依赖版本、配置或秘密。 |
| `POST /notes` | `201` 与新笔记。 | 空白、过长、缺字段或额外字段返回统一 `422 invalid_request`。 |
| `GET /notes` | `200` 与按编号排序的笔记列表。 | 当前为空也返回合法空数组。 |
| `GET /notes/{id}` | `200` 与笔记。 | 缺失资源返回 `404 note_not_found`；非整数 ID 返回统一 `422`。 |
| 任意笔记读写 | SQLite 事务提交后持久化。 | 锁、磁盘或数据库故障映射为不含内部细节的 `503 storage_unavailable`。 |

## 安装与测试

```bash
cd "02_可运行项目/projects/06-knowledge-api"
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"

.venv/bin/python -m pytest
.venv/bin/python -m mypy
.venv/bin/python -m ruff check src tests
```

测试使用 FastAPI `TestClient`，不要求长期启动网络服务。当前 17 项 pytest 验证输入、输出、状态码、请求 ID、404、422、日志脱敏、SQLite 跨实例持久化、参数化文本、回滚与备份恢复。FastAPI 可依据路径操作与 Pydantic 模型生成 OpenAPI Schema 和交互式文档；自动文档有助于减少合同漂移，但不替代业务、权限、隐私或数据库测试。[1] [2]

## 本地开发运行

```bash
COURSE_KNOWLEDGE_API_DB="./data/notes.sqlite3" \
  .venv/bin/course-notes-api --host 127.0.0.1 --port 8000
```

另开一个终端后可执行：

```bash
curl -i http://127.0.0.1:8000/health
curl -i \
  -H 'Content-Type: application/json' \
  -H 'X-Request-ID: local-demo-001' \
  -d '{"title":"HTTP","content":"先定义合同。"}' \
  http://127.0.0.1:8000/notes
curl -i http://127.0.0.1:8000/notes/1
```

FastAPI 的请求体模型会验证 JSON，`extra="forbid"` 拒绝未定义字段；`RequestValidationError` 被映射为稳定公开的 `422` 载荷。FastAPI 文档说明，Pydantic 模型用于读取和验证请求体，而 `HTTPException` 和异常处理器用于形成 HTTP 错误响应。[2] [3]

## 请求与响应示例

```http
POST /notes
Content-Type: application/json
X-Request-ID: local-demo-001

{"title":"HTTP","content":"先定义合同。"}
```

```json
{
  "id": 1,
  "title": "HTTP",
  "content": "先定义合同。",
  "request_id": "local-demo-001"
}
```

错误响应统一为：

```json
{
  "error": {
    "code": "invalid_request",
    "message": "请求格式或字段值不符合笔记 API 合同。"
  },
  "request_id": "local-demo-001"
}
```

每个请求会使用客户端提供的 `X-Request-ID` 或服务生成的新 ID，并在响应头和载荷中返回该 ID。日志只记录方法、路径、状态和 ID；笔记标题与正文均不会进入运行日志。

## 依赖与存储边界

`get_store()` 是 FastAPI 依赖。路径操作声明需要 `NoteRepository`，框架按请求提供指向 `COURSE_KNOWLEDGE_API_DB` 的 `SqliteNoteRepository`；测试通过 `app.dependency_overrides` 替换为独立内存存储。依赖注入适合提供数据库会话、认证结果或受控配置，不能变成隐式全局垃圾桶。[4]

`SqliteNoteRepository` 的每个公共操作都创建并关闭独立 SQLite 连接。写入显式 `BEGIN IMMEDIATE`，成功时提交、异常时回滚；所有标题、正文和 ID 均以 `?` 占位符绑定，绝不由字符串格式化 SQL。Python 官方文档明确建议以占位符绑定值来避免 SQL 注入。[5] 仓储提供 `backup_to()` 以创建本地数据库副本，测试验证该副本可独立读取；它不替代加密、留存、异地备份、恢复演练或多节点可用性。

SQLite 适合本课程的单节点、小规模教学服务。默认连接不应跨线程共享；锁等待、磁盘与损坏错误会被包装成 `StorageError` 并映射为公开的 `503`，但详细根因只应经脱敏运维日志处理。不要把本项目宣称为高并发、分布式或生产灾难恢复方案。[5]

## 目录结构

```text
06-knowledge-api/
├── pyproject.toml
├── README.md
├── .gitignore
├── .github/workflows/quality.yml
├── src/knowledge_api/
│   ├── __init__.py
│   ├── api.py
│   ├── cli.py
│   └── core.py
└── tests/
    ├── test_api.py
    └── test_sqlite_repository.py
```

## 参考资料

[1]: https://fastapi.tiangolo.com/tutorial/first-steps/ "FastAPI: First Steps"
[2]: https://fastapi.tiangolo.com/tutorial/body/ "FastAPI: Request Body"
[3]: https://fastapi.tiangolo.com/tutorial/handling-errors/ "FastAPI: Handling Errors"
[4]: https://fastapi.tiangolo.com/tutorial/dependencies/ "FastAPI: Dependencies"
[5]: https://docs.python.org/3/library/sqlite3.html "Python sqlite3 documentation"
