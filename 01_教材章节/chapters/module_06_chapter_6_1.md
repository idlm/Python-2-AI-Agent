# 第 6.1 章：Web 服务不是函数调用——HTTP、资源与 API 合同

**适用版本：** Python 3.11+  
**项目连接：** `examples/module_06/http_contract.py` 与 `05_教学测试/tests/module_06/test_http_contract.py`

## 1. 本章目标

完成本章后，你能够解释浏览器、脚本或 Agent 工具为何不能直接调用另一台机器上的 Python 函数；能区分 HTTP 方法、路径、请求体、响应体、状态码与日志；能先写出一个可测试的 API 合同，再在下一章把它交给 FastAPI；能避免把用户正文、内部异常和任意配置泄露给调用方。

## 2. 先纠正一个误解：API 不是“远程函数名”

本地函数调用发生在同一进程中：调用者直接传入 Python 对象，并立即得到返回值或异常。HTTP API 则跨越进程与网络边界。调用者只能发送字节形式的请求；服务必须明确接受哪种方法、哪条路径、哪些数据、什么格式和怎样的失败结果。**API 合同（API Contract）**就是双方对这些可观察行为的约定。

## 3. 从生产级 Agent 倒推

Agent 使用工具时也在遵守合同：工具名称像路径，输入 Schema 像请求体，结构化结果像响应体，失败类型和重试条件像状态码。Agent 不是 LangChain、LangGraph 或任一框架；无论以后是否引入框架，它都必须有模型、工具、记忆、状态、工作流和评测的边界。本章的 HTTP 合同是“工具调用合同”的第一个非模型版本。

## 4. 一次 HTTP 交互的最小结构

| 部分 | 示例 | 回答的问题 |
|---|---|---|
| 方法（method） | `GET`、`POST`。 | 调用者想读取还是创建资源？ |
| 路径（path） | `/notes`、`/notes/1`。 | 调用者操作哪个资源集合或实例？ |
| 请求头（headers） | `Content-Type: application/json`。 | 请求如何编码、认证或缓存？ |
| 请求体（body） | `{"title": "HTTP", "content": "定义边界"}`。 | 创建或更新时交给服务的数据是什么？ |
| 状态码（status code） | `200`、`201`、`404`、`422`。 | 结果成功、资源缺失还是输入不合法？ |
| 响应体（response body） | JSON 对象。 | 调用者可安全使用的结果或错误是什么？ |

HTTP 的路径也常被称为 endpoint 或 route；方法与路径一起选择服务端的路径操作（path operation）。FastAPI 官方教程用 `@app.get()`、`@app.post()` 等装饰器把这两件事关联到函数。[1]

## 5. 资源先于 URL

不要先凭感觉写 `/do_task`、`/process` 之类动作路径。先问“系统要保存、读取或管理的名词是什么”。本章选择知识笔记 `note`：集合是 `/notes`，单条是 `/notes/{id}`。资源设计并不禁止动作；当动作确实是领域概念（例如归档计划、评测运行）时，可把它建模成可查询、可审计的资源，而不是隐藏在模糊命令中。

## 6. 用方法表达主要意图

| 方法 | 本章约定 | 典型成功状态 | 不表示什么 |
|---|---|---|---|
| `GET` | 读取 `/notes` 或 `/notes/{id}`。 | `200 OK`。 | 不应创建或修改笔记。 |
| `POST` | 向 `/notes` 创建一条笔记。 | `201 Created`。 | 不应把客户端给的 ID 当成可信主键。 |
| `PUT` / `PATCH` | 后续章节用于完整替换或部分更新。 | 常为 `200` 或 `204`。 | 不是“任何更新都随便选一个”。 |
| `DELETE` | 后续章节用于显式删除。 | 常为 `204`。 | 不应绕过认证、审计或恢复策略。 |

这些是清晰的团队约定，而不是 FastAPI 强制规则。框架允许把任意方法绑定到函数，但可预测的约定会让人、测试和 Agent 工具更容易推理。[1]

## 7. 请求体不是任意字典

创建笔记的请求体只允许两个字段：`title` 与 `content`。标题不能为空且最长 100 字符；正文不能为空且最长 2,000 字符；缺失、额外或类型错误均返回受控错误。这样做同时防止拼写被静默忽略、字段不断膨胀和未审查数据进入业务层。

```python
# 文件：examples/module_06/http_contract.py（完整请求体校验函数）
def parse_note_body(body: object | None) -> tuple[str, str]:
    if not isinstance(body, Mapping):
        raise ContractError(422, "invalid_request", "请求体必须是 JSON 对象。")
    required_fields = {"title", "content"}
    unknown_fields = set(body) - required_fields
    missing_fields = required_fields - set(body)
    if unknown_fields or missing_fields:
        raise ContractError(
            422,
            "invalid_request",
            f"字段必须恰为 {sorted(required_fields)}；缺失={sorted(missing_fields)}，额外={sorted(unknown_fields)}。",
        )
    return (
        _require_nonempty_string(body.get("title"), field="title", maximum=_MAX_TITLE_LENGTH),
        _require_nonempty_string(body.get("content"), field="content", maximum=_MAX_CONTENT_LENGTH),
    )
```

下一章会用 Pydantic 模型表达同一规则。FastAPI 可以根据这类模型读取 JSON、验证数据，并把 JSON Schema 放进自动生成的 OpenAPI 文档。[2]

## 8. 路径参数不是字符串拼接

`/notes/1` 中的 `1` 是资源标识，而不是可直接拼进文件路径、SQL 或命令的字符串。本章只接受十进制正整数；`/notes/zero` 与 `/notes/0` 以 `404` 被拒绝。后续数据库章节仍会把已验证 ID 通过 SQL 参数传入，而不是用 f-string 拼 SQL。

## 9. 响应也有 Schema

创建成功返回：

```json
{"id": 1, "title": "HTTP", "content": "定义边界"}
```

列表成功返回：

```json
{"notes": [{"id": 1, "title": "HTTP", "content": "定义边界"}]}
```

响应 Schema 是安全边界，不是格式装饰。内部字段例如数据库连接、管理员标记、访问 token、原始异常或调试栈不能因“对象恰好有这个属性”而自动序列化。输入模型与输出模型在下一章应分开声明。

## 10. 状态码是机器可读的结果分类

| 状态码 | 本章含义 | 调用方合理下一步 |
|---:|---|---|
| `200` | 已成功读取资源。 | 解析响应 Schema。 |
| `201` | 已成功创建资源。 | 保存返回的资源 ID。 |
| `404` | 路径或指定资源不存在。 | 检查 ID 或停止重试。 |
| `405` | 路径存在但不支持此方法。 | 修正调用合同，不盲目重试。 |
| `422` | JSON 形状或字段值不符合请求合同。 | 修正客户端数据。 |
| `500` | 未预期服务端故障。 | 记录相关 ID，按策略重试或升级；不依赖内部细节。 |

FastAPI 的错误处理文档将 `HTTPException` 作为 API 错误响应的方式，并以 `404` 演示缺失资源；4xx 范围用于客户端错误。[3] 本章不把任意 Python 异常直接当 HTTP 状态码。

## 11. 统一错误载荷

本章所有可预期失败都使用同一响应形状：

```json
{"error": {"code": "invalid_request", "message": "title 不能为空。"}}
```

`code` 适合程序稳定判断，`message` 适合人理解。不要让调用方靠中文句子、Traceback 或 Python 异常类名分支。现实系统还可增加请求 ID、文档链接和字段错误数组，但开始时要保持小而稳定。

## 12. 404 与 405 不要混为一谈

`GET /notes/99` 代表合法路径上的缺失资源，因此返回 `404 note_not_found`。`DELETE /notes` 代表已知资源集合使用了不允许的方法，因此返回 `405 method_not_allowed`。两者对调用者的修复动作不同：前者检查资源，后者检查合同。把所有失败都压成“请求错误”会让 API 和 Agent 工具失去可恢复性。

## 13. 完整可运行示例

本章示例不启动网络监听器，避免把“HTTP 合同”与“端口、进程和框架”一次性混在一起。它在纯 Python 中定义 `Request`、`Response`、`NoteStore` 与 `dispatch()`，并以真实状态码和 JSON 形状表现服务边界。

```bash
cd "$(git rev-parse --show-toplevel)"
python3 examples/module_06/http_contract.py
python3 -m unittest discover -s 05_教学测试/tests/module_06 -p 'test_*.py' -v
```

当前测试覆盖创建、列表、单条读取、`404`、`405`、`422`、精确字段 Schema 与日志脱敏。示例的内存存储会随进程结束消失；这正是第 6.3 章要引入数据库事务的原因。

## 14. 路由分派必须是受控选择

```python
# 文件：examples/module_06/http_contract.py（节选）
if request.path == "/notes":
    if request.method == "GET":
        response = Response(200, {"notes": notes})
    elif request.method == "POST":
        response = Response(201, note.to_record())
    else:
        raise ContractError(405, "method_not_allowed", "该路径不支持此 HTTP 方法。")
```

这里没有根据用户输入导入函数、调用方法名或执行字符串。路由是代码审查过的允许列表。后续 FastAPI 路径装饰器会让写法更简洁，但安全问题仍相同：用户不能通过路径或 JSON 选择任意 Python callable。

## 15. 领域错误与协议错误分层

`NoteStore.get()` 不知道浏览器、端口或 Swagger UI；它只在笔记缺失时表达领域事实。`dispatch()` 决定该事实如何变成 `404` JSON。下一章中，FastAPI 路径操作或异常处理器承担同一适配职责。分层的好处是：核心可由单元测试复用，HTTP 格式可单独更换，Agent 工具也可映射同一领域错误而不依赖 Web 框架。

## 16. 日志记录元数据，不记录正文

本章记录 `method`、`path`、`status` 和错误 `code`，刻意不记录请求 `body`。笔记正文可能是客户数据、提示词、个人信息或将来的检索资料；在错误日志中“方便地打印出来”会扩大泄露面。Python Logging HOWTO 将日志用于运行事件，而普通用户输出和异常处理应使用不同机制。[4]

```text
INFO http_request_completed method=POST path=/notes status=201
```

日志不等于审计系统，也不等于评测数据集。生产服务还需定义访问控制、保留期、加密、采样和删除策略。

## 17. 失败案例：把异常和请求体回显

```python
except Exception as exc:
    return {"error": str(exc), "body": request.body}
```

这段代码看似“调试方便”，实际会把内部类型、文件路径、SQL、token 或用户正文交给客户端。FastAPI 文档同样警告：请求验证异常包含的细节若直接转成字符串或返回，可能泄露系统信息。[3] 正确做法是记录脱敏的错误类型和相关 ID，并向客户端返回稳定的公开错误合同。

## 18. 先测合同，再启动服务器

网络服务器会引入端口占用、进程生命周期、浏览器缓存和操作系统差异。最先应该测试的是确定性合同：给定 `Request` 和空 `NoteStore`，预期得到哪个 `Response`。当这层稳定后，下一章用 FastAPI `TestClient` 验证框架是否正确连接到同一合同；部署测试则留给后续章节。

## 19. API 文档是交付物，不是替代测试

FastAPI 会生成 OpenAPI Schema，`/docs` 与 `/redoc` 会使用它展示交互式文档。[1] 这能减少手写文档漂移，并帮助前端、脚本和 Agent 工具理解输入输出。但是自动文档不会证明权限正确、业务逻辑无误、日志未泄露或数据库事务安全；它必须和测试、审查和质量门禁并存。

## 20. 依赖注入先理解为“明确提供资源”

下一章会出现 `Depends`。它不是神秘的全局变量系统，而是让路径操作声明“我需要什么”，由框架在每个请求中提供结果。适合的依赖包括数据库会话、认证后的当前用户、固定分页参数和经过验证的配置。FastAPI 依赖系统可用于共享数据库连接、认证、授权和公共逻辑，并把相关参数纳入 OpenAPI。[5]

不适合的做法是把所有业务、缓存、配置、网络调用和秘密塞进一个依赖函数，让路径操作无法看出它真正依赖什么。

## 21. 本章验收

在不修改示例的情况下运行第 13 节命令。然后手动构造以下请求并写下状态码与响应 `error.code`：`GET /notes/99`、`DELETE /notes`、`POST /notes` 但没有 `content`、`POST /notes` 含 `command` 字段。最后读取 `test_logs_never_include_request_body`，说明该测试为什么比人工查看一次终端输出更可靠。

## 22. 快速测试（5 题）

1. 本地函数调用与 HTTP API 调用最关键的边界差异是什么？
2. 为什么 `POST /notes` 成功返回 `201` 而列表读取返回 `200`？
3. `404` 与 `405` 分别提示调用者修复什么？
4. 为什么请求体应拒绝未知字段而非静默忽略？
5. 为什么日志不能默认记录请求正文？

**答案要点：** 1. HTTP 跨进程/网络，必须序列化并公开合同；2. 前者创建新资源，后者成功读取已有表示；3. 资源/路径或方法/合同；4. 防拼写漂移、未审查行为和隐藏输入；5. 正文可能含个人数据、提示词、秘密或后续检索资料。

## 23. 代码阅读（2 题）

1. 阅读 `parse_note_body()`，分别指出它检查了对象类型、字段集合、字符串类型、空白和长度的哪些位置；若只保留 Pydantic 或只保留手写检查，下一章的职责会怎样变化？
2. 阅读 `dispatch()` 的 `except ContractError` 块，证明日志没有使用 `request.body`；说明为何 `error.code` 比完整异常对象更适合作为日志字段。

## 24. Debug（2 题）

1. 故意把 `if request.method == "GET"` 改为 `if request.method:`。运行测试，观察 `DELETE /notes` 为何错误返回 `200`；恢复精确比较，并解释允许列表路由的价值。
2. 把 `_error_response()` 改成返回 `{"error": str(error)}`。为它编写测试，指出机器调用方失去的稳定字段；恢复 `code` 与 `message` 的嵌套 Schema。

## 25. 编程练习（3 题）、逆向设计与课后项目

**编程练习：** 1. 为示例增加 `GET /notes?limit=N` 的纯函数分页参数；限制 `1 ≤ N ≤ 100`，为缺失默认值、边界值、非整数和过大值写测试。2. 增加 `PUT /notes/{id}` 的完整替换合同，明确是否保留 ID、怎样处理缺失资源，并新增至少五项测试。3. 为每个响应增加公开的 `request_id` 字段，但绝不从用户输入直接接受该字段；写测试证明错误与成功响应均有该字段且日志仍无正文。

**逆向设计：** 某“知识库 API”把所有请求都设计成 `POST /run`，接收任意字典，捕获所有异常后返回 `200 {"ok": false}`，同时把完整 body 与数据库异常写入日志。请从资源建模、方法语义、状态码、输入 Schema、输出 Schema、注入、隐私、可观测性、重试、Agent 工具调用和评测可复现性至少列出十项问题，并为每项写一个可测试的改进合同。

**课后项目：** 复制本章示例到新的 `mini-notes-contract` 目录，将 `Note` 扩展为含 `tags` 的资源。要求：标签最多五个、每个 1–20 字符、去重且排序；实现创建、列表、单条读取、受控错误响应、脱敏日志和至少十二项单元测试。写 README，列出每条方法/路径的请求与响应 Schema、状态码、失败示例和“哪些字段绝不能进入日志”。下一章再把它迁移到 FastAPI，不能在本章跳过合同测试直接堆框架。


### 本章项目映射

本章建议直接在 `02_可运行项目/projects/06-knowledge-api/` 中完成可运行练习。先执行：从 API 模型和测试读取路径、方法、请求/响应 Schema、状态码与公开错误之间的合同。

```bash
cd 02_可运行项目/projects/06-knowledge-api && .venv/bin/python -m pytest
```

**主题化扩展：** 增加一个只读端点的 Schema 测试；未知字段或错误方法必须落到受控 4xx，而不暴露内部异常。

完成后记录输入/输出合同、受控失败、测试命令和安全边界。不要把项目中的本地替身、测试夹具、回环服务或默认无执行模式误作真实网络、模型、生产数据、秘密、部署或副作用授权。

## 参考资料

[1]: https://fastapi.tiangolo.com/tutorial/first-steps/ "FastAPI: First Steps"
[2]: https://fastapi.tiangolo.com/tutorial/body/ "FastAPI: Request Body"
[3]: https://fastapi.tiangolo.com/tutorial/handling-errors/ "FastAPI: Handling Errors"
[4]: https://docs.python.org/3/howto/logging.html "Python Logging HOWTO"
[5]: https://fastapi.tiangolo.com/tutorial/dependencies/ "FastAPI: Dependencies"
