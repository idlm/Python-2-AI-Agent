# 第 6.2 章：FastAPI 不是魔法——把 HTTP 合同变成可测试服务

**适用版本：** Python 3.11+  
**项目连接：** `02_可运行项目/projects/06-knowledge-api/`（版本 0.1.0）

## 1. 本章目标

完成本章后，你能够把第 6.1 章的路径、方法、请求、响应、状态码与错误合同交给 FastAPI 实现；能用 Pydantic 模型验证输入和限制输出；能理解依赖注入为何比隐藏全局状态更可测；能用 `TestClient` 验证 HTTP 合同；能解释请求 ID、日志和异常处理各自负责什么。

## 2. 先把框架放在正确位置

FastAPI 不是 API 设计本身，也不是生产质量的自动保证。它负责把 Python 类型、路径操作函数和 HTTP 请求/响应连接起来；资源模型、字段边界、状态码、权限、事务、日志、评测和运维策略仍必须由你设计。第 6.1 章先以纯 Python 固定合同，项目 6 再让框架实现同一合同，因此框架替换不会迫使领域规则重写。

## 3. 从生产级 Agent 倒推

将来 Agent 的工具服务器同样需要输入 Schema、输出 Schema、错误合同、超时、认证、请求追踪和可测试依赖。一个“能调模型”的端点若把提示词、密钥、工具调用和数据库异常随意混在一起，模型越强只会越快放大错误。本章的知识笔记 API 不含模型调用，正是为了先建立模型之外同样不可省略的服务边界。

## 4. 项目结构与责任

```text
02_可运行项目/projects/06-knowledge-api/
├── pyproject.toml
├── src/knowledge_api/
│   ├── core.py       # Note、NoteStore、领域缺失异常
│   ├── api.py        # FastAPI 模型、路由、中间件、异常映射、依赖
│   └── cli.py        # 本地 Uvicorn 启动命令
├── tests/test_api.py # TestClient HTTP 合同测试
└── .github/workflows/quality.yml
```

| 文件 | 应知道什么 | 不应负责什么 |
|---|---|---|
| `core.py` | 笔记领域对象与存储操作。 | HTTP 状态码、Pydantic、请求头。 |
| `api.py` | HTTP 到领域层的适配、输入输出模型、公开错误与观测。 | 直接拼接 SQL、运行任意用户代码。 |
| `cli.py` | 受控本地服务器启动参数。 | 业务路由或数据库逻辑。 |
| `tests/test_api.py` | 外部 HTTP 合同。 | 依赖真实公网、长期运行的服务器。 |

## 5. 创建 FastAPI 应用对象

```python
# 文件：src/knowledge_api/api.py
from fastapi import FastAPI

app = FastAPI(title="Course Knowledge API", version="0.1.0")
```

`FastAPI()` 创建应用对象；`@app.get()`、`@app.post()` 等装饰器随后把方法和路径关联到函数。官方入门文档还说明，应用会生成 OpenAPI Schema，并默认提供 `/docs`、`/redoc` 与 `/openapi.json`。[1] 这些元数据应反映真实合同，而不是用夸张标题掩盖未实现的安全能力。

## 6. 输入模型把“任意 JSON”缩成合同

```python
# 文件：src/knowledge_api/api.py
class NoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=2_000)
```

`extra="forbid"` 拒绝未声明字段，`str_strip_whitespace=True` 先去除首尾空白，`Field` 声明长度边界。每一个规则都必须能解释业务或安全目的，并有测试。FastAPI 使用 Pydantic 模型读取 JSON、执行验证、提供带类型的参数，并将模型 Schema 纳入 OpenAPI。[2]

## 7. 输出模型是第二道边界

```python
class NoteResponse(BaseModel):
    id: int
    title: str
    content: str
    request_id: str

@app.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteCreate, store: StoreDependency) -> NoteResponse:
    note = store.create(title=payload.title, content=payload.content)
    return _note_response(note)
```

输入与输出不应该默认共享同一个模型。创建请求没有可信 `id` 或 `request_id`；响应需要服务分配的 ID 和观测 ID。若后续领域对象增加 `owner_id`、内部标志、检索向量或密钥引用，输出模型可以继续只暴露明确字段。

## 8. 路径操作函数是 HTTP 适配器

`create_note()` 的 `payload` 是已经验证的 `NoteCreate`，`store` 是被注入的领域依赖；函数调用核心层创建笔记，再将 `Note` 映射为 `NoteResponse`。路径操作函数不应重新检查 Pydantic 已保证的类型，不应直接访问全局字典，也不应把领域异常变成字符串。它越薄，单元测试、HTTP 测试和未来 Agent 工具适配越容易复用。

## 9. 依赖注入并不等于隐藏依赖

```python
# 文件：src/knowledge_api/api.py

def get_store() -> Generator[NoteStore, None, None]:
    yield _STORE

StoreDependency = Annotated[NoteStore, Depends(get_store)]
```

依赖注入（dependency injection）表示路径操作声明自己需要的资源，框架在请求处理中提供结果。FastAPI 文档将数据库连接、认证、授权和共享逻辑列为典型用法。[3] 本项目把 `NoteStore` 作为显式依赖，所以测试可覆盖它；后续数据库章节可把它换成“每请求会话”而不改 HTTP 路径合同。

## 10. 测试如何替换依赖

```python
# 文件：tests/test_api.py（节选）
store = NoteStore()

def override_store() -> Generator[NoteStore, None, None]:
    yield store

app.dependency_overrides[get_store] = override_store
```

每个测试夹具创建独立内存存储，再把 `get_store` 覆盖为该存储。这样测试互不依赖 ID 顺序，也不会污染开发服务器中的数据。依赖覆盖不是让测试绕过业务规则；它只是替换外部资源提供者，HTTP 模型、路由、异常映射和日志边界仍由真实应用执行。

## 11. 领域异常不是 HTTPException

`core.NoteStore.get()` 在编号缺失时抛 `NoteNotFoundError`，只陈述领域事实。`api.py` 中的异常处理器再把它映射为 `404`：

```python
@app.exception_handler(NoteNotFoundError)
async def note_not_found_handler(_: Request, exc: NoteNotFoundError) -> JSONResponse:
    return _error_response(
        status_code=status.HTTP_404_NOT_FOUND,
        code="note_not_found",
        message=f"找不到编号为 {exc.note_id} 的笔记。",
    )
```

FastAPI 支持以 `HTTPException` 直接形成 HTTP 错误，也支持为自定义异常注册处理器。[4] 本项目选择领域异常加处理器，是为了让核心层不依赖 Web 框架；简单端点中直接 `raise HTTPException` 也可能合适，但不要让两种策略随意混用。

## 12. 验证错误不能回显原始 body

Pydantic/ FastAPI 会在输入不合法时产生 `RequestValidationError`。项目捕获它并返回稳定载荷：

```json
{
  "error": {
    "code": "invalid_request",
    "message": "请求格式或字段值不符合笔记 API 合同。"
  },
  "request_id": "..."
}
```

原始请求体可能包含提示词、用户数据、错误命令或秘密；内部字段定位也可能透露实现细节。FastAPI 文档特别提示，验证异常包含的信息若直接转换或返回可能泄露系统信息。[4] 因此详细诊断只应在经审查、脱敏且受访问控制的服务端日志中出现。

## 13. 请求 ID 的作用

请求 ID 是一次请求的相关标识，不是用户身份、授权凭证或秘密。项目优先接受 `X-Request-ID`，若缺失则生成 UUID 十六进制值；它同时出现于响应头、成功载荷、错误载荷和脱敏日志。用户报告“接口失败”时，支持人员能用 ID 关联同一次调用，而无需要求用户提供正文。

| 位置 | 本项目包含什么 | 不包含什么 |
|---|---|---|
| 请求头 | 客户端提供或服务生成的 `X-Request-ID`。 | API key、用户全文或调试对象。 |
| 成功响应 | `request_id`。 | 存储锁、进程 ID、数据库 DSN。 |
| 错误响应 | `request_id`、公开 `code`、公开 `message`。 | Traceback、原始 JSON、SQL。 |
| 日志 | 方法、路径、状态、请求 ID。 | 标题、正文、认证头。 |

## 14. 中间件是横切边界，不是万能钩子

项目的 `@app.middleware("http")` 在路径操作前设置 `ContextVar` 请求 ID，在响应后添加 `X-Request-ID` 并记录元数据。中间件适合相关 ID、统一安全头、计时和访问日志；它不适合处理每个资源的业务规则，更不能通过读取完整 body 偷偷实现审计。若需要读取 body，必须先设计大小限制、隐私、失败策略和测试。

## 15. 同步路径操作为何仍可作为教学起点

项目的路径操作使用普通 `def`，核心存储使用快速的进程内存锁。`async def` 不是“更现代”的标记：若在协程中执行阻塞数据库驱动、文件 I/O 或 CPU 密集循环，事件循环仍会被阻塞。Python `asyncio` 适合 I/O 密集的并发结构；下一节和后续章节会明确任务、超时与取消，而不是把每个函数机械改为 `async`。[5]

## 16. 本地启动是开发验收，不是部署方案

```bash
cd "02_可运行项目/projects/06-knowledge-api"
.venv/bin/course-notes-api --host 127.0.0.1 --port 8000
```

默认 `127.0.0.1` 仅监听本机，防止初学者无意把教学服务暴露到局域网。`uvicorn.run()` 只负责本地开发运行；生产进程数、反向代理、TLS、认证、数据库迁移、限流、监控和告警将在后续章节单独设计。启动成功不是“已安全上线”。

## 17. 真实 HTTP 验收

```bash
curl -i http://127.0.0.1:8000/health
curl -i \
  -H 'Content-Type: application/json' \
  -H 'X-Request-ID: e2e-001' \
  -d '{"title":"真实服务验收","content":"HTTP 合同与框架接线一致。"}' \
  http://127.0.0.1:8000/notes
curl -i http://127.0.0.1:8000/notes/1
```

本项目已在临时本地服务器中验证上述健康、创建与读取路径，并验证含未知 `module` 字段的请求被统一以 `422 invalid_request` 拒绝。真实运行验收补充 `TestClient`，但它不替代自动测试：任何可复现发现都应转成测试。

## 18. TestClient 测什么，不测什么

| `TestClient` 擅长验证 | 还不能验证 |
|---|---|
| 路由、模型验证、状态码、响应 JSON、异常处理、依赖覆盖和中间件。 | 真实端口、DNS、TLS、反向代理、跨进程存储、生产负载。 |
| 公开错误不回显输入，日志不含正文。 | 集中日志权限、保留策略和安全事件响应。 |
| OpenAPI 路径接线。 | 文档是否符合所有业务语义或用户需求。 |

本项目 9 项 pytest 覆盖健康、创建、列表、读取、404、422、请求 ID 和日志脱敏。任何数量都不是安全评级；测试清单应随合同扩大而扩大。

## 19. 自动文档要与测试共同演进

启动本地服务器后访问 `http://127.0.0.1:8000/docs`，可以查看交互式文档。每次改变模型、路径、状态码或响应模型时，应同时检查：自动文档是否更新、HTTP 测试是否表达了变化、README 示例是否仍可运行、日志和错误是否没有扩大泄露范围。OpenAPI 是共享合同的机器可读版本，适合未来生成客户端或工具定义；它不是授权策略和评测方案的替代物。[1]

## 20. 失败案例：把领域对象直接返回

```python
@app.post("/notes")
def unsafe_create(payload: dict) -> object:
    return store.create(**payload)
```

问题至少有五个：任意字典没有受控 Schema；未知字段可能触发 Python 调用错误；内部对象新增字段会意外暴露；错误格式不稳定；测试无法判断 `201`、`422` 或 `404`。修复是使用 `NoteCreate`、`NoteResponse`、领域方法、异常处理器和 TestClient 合同测试，而不是在 `except` 中把错误字符串返回。

## 21. 本章验收

在隔离 `.venv` 运行：

```bash
.venv/bin/python -m pytest
.venv/bin/python -m mypy
.venv/bin/python -m ruff check src tests
```

再启动本地服务，完成第 17 节三个 `curl` 请求；提交一个额外字段并确认 `422` 响应不包含该字段名、正文或内部 Pydantic 细节。检查响应头 `X-Request-ID` 与响应载荷一致；查看日志确认只含方法、路径、状态和 ID。

## 22. 快速测试（5 题）

1. 为什么输入模型和输出模型不应默认相同？
2. `Depends` 在本项目中提供什么，测试又如何替换它？
3. 为什么 `NoteNotFoundError` 不在核心层直接变成 `HTTPException`？
4. 为什么验证错误不应回显原始 body？
5. 为什么本项目仍选择同步 `def` 路径操作？

**答案要点：** 1. 输入和公开输出字段及信任边界不同；2. 提供 `NoteStore`，通过 `app.dependency_overrides` 以独立存储替换；3. 保持领域层不依赖框架；4. body 可能含秘密、个人数据或实现探针；5. 内存操作短小且不阻塞，`async` 不能自动解决阻塞 I/O。

## 23. 代码阅读（2 题）

1. 阅读 `request_context()`，标出 `ContextVar` 设置、`call_next()`、响应头写入、日志与 `finally` 重置的顺序。若在异常后忘记重置，跨请求污染会怎样出现？
2. 阅读 `validation_error_handler()` 与 `tests/test_api.py::test_invalid_body_uses_unified_422_without_echoing_input`，说明测试如何同时证明状态码、错误 Schema、请求 ID 和未回显未知字段。

## 24. Debug（2 题）

1. 暂时删除 `NoteCreate.model_config = ConfigDict(extra="forbid", ...)`。提交含 `module` 字段的 JSON，观察它为什么被接受；恢复设置并将该行为固定为测试。解释配置 Schema 与 API Schema 的共同安全原则。
2. 将 `_note_response()` 改为 `return NoteResponse(..., request_id="fixed")`。运行请求 ID 测试，说明为何固定 ID 破坏排障；恢复从 `ContextVar` 读取，并测试客户端提供的 ID 原样回传。

## 25. 编程练习（3 题）、逆向设计与课后项目

**编程练习：** 1. 为 API 增加 `GET /notes?limit=N`，默认 20、范围 1–100；把参数纳入 OpenAPI 并为默认、边界、过大和非整数写测试。2. 为 `NoteCreate` 增加 `tags`，限制最多五个、去空白、去重、每项最多 20 字符；明确响应字段，并写至少六项验证测试。3. 为所有公开错误加 `docs_url` 固定字段，指向本地 API 错误说明；确认其不是由客户端提供，也不拼接未验证路径。

**逆向设计：** 某 Agent 工具 API 使用 `POST /execute` 接受任意 JSON，允许 `{"tool": "module.function"}` 动态导入；`except Exception` 时返回完整 Traceback 和请求 body；所有调用共享一个全局数据库连接；日志记录 Authorization 头；成功与失败都返回 `200`。请从输入 Schema、工具允许列表、状态码、依赖生命周期、并发、认证、秘密、日志、错误、可重试性、评测和人工介入至少倒推十二项问题，并为每项提出一个可测试的服务合同。

**课后项目：** 在 `06-knowledge-api` 中实现 `PUT /notes/{id}` 的完整替换和 `DELETE /notes/{id}` 的显式删除。要求：输入、输出与错误模型完整；不存在资源为 `404`；删除成功使用适当状态码且不回显正文；每条请求均有请求 ID；日志不含标题、正文和认证头；新增至少十项 pytest；mypy、Ruff 与 Python 3.11/3.12 CI 全部通过；README 增加 cURL、状态码矩阵和恢复/审计限制。完成后写复盘：哪些规则属于 HTTP 边缘，哪些属于领域层，哪些必须等到数据库事务章节才能正确实现？


### 本章项目映射

本章建议直接在 `02_可运行项目/projects/06-knowledge-api/` 中完成可运行练习。先执行：阅读请求 ID、依赖注入与公开错误转换，区分 API 层、领域层和日志责任。

```bash
cd 02_可运行项目/projects/06-knowledge-api && .venv/bin/python -m pytest
```

**主题化扩展：** 为一个领域错误增加稳定错误代码与请求 ID；测试响应不回显请求正文或内部堆栈。

完成后记录输入/输出合同、受控失败、测试命令和安全边界。不要把项目中的本地替身、测试夹具、回环服务或默认无执行模式误作真实网络、模型、生产数据、秘密、部署或副作用授权。

## 参考资料

[1]: https://fastapi.tiangolo.com/tutorial/first-steps/ "FastAPI: First Steps"
[2]: https://fastapi.tiangolo.com/tutorial/body/ "FastAPI: Request Body"
[3]: https://fastapi.tiangolo.com/tutorial/dependencies/ "FastAPI: Dependencies"
[4]: https://fastapi.tiangolo.com/tutorial/handling-errors/ "FastAPI: Handling Errors"
[5]: https://docs.python.org/3/library/asyncio.html "Python asyncio overview"
