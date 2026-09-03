# 第 4.3 章：装饰器、生成器与上下文管理器——在不改核心逻辑时增加能力

**适用版本：** Python 3.11+  
**项目连接：** `02_可运行项目/projects/04-plugin-system/`（安全文本插件系统，版本 0.2.0）

## 1. 本章目标

本章完成后，你能在不复制业务代码的前提下为函数增加日志；能用 `yield` 逐项产生数据；能用 `with` 管理文件等资源；并能从 Traceback 区分包装层、业务层和资源清理层的错误。

## 2. 前置知识

你已经学习了函数、类型注解、数据类、协议和组合。接下来要把它们连接到真实项目：插件注册表执行转换；装饰器记录调用；生成器逐项产生插件名；上下文管理器关闭审计文件。

## 3. 从 Agent 倒推能力

生产级 Agent 不只是“模型调用工具”。它还要能记录工具调用、流式处理结果、在失败时释放连接，并避免把用户原文写进日志。装饰器、生成器和上下文管理器不是某一框架的功能，而是实现工具、状态、工作流和可观测性边界的 Python 基础。

## 4. 三个概念

**装饰器（decorator）**是接收一个函数并返回另一个函数的函数；`@` 语法是函数变换的简写。[1] **生成器（generator）**是含有 `yield` 的函数，调用后返回可逐步消费的迭代器。**上下文管理器（context manager）**用 `__enter__()` 和 `__exit__()` 控制 `with` 块的进入、退出和清理；即使块内抛出异常，也会执行退出逻辑。[2]

| 机制 | 适合解决的问题 | 项目中的位置 |
|---|---|---|
| 装饰器 | 给多个操作添加相同日志、计时或权限边界。 | `log_transform_call` 包装 `apply()`。 |
| 生成器 | 一次产生一个值，避免无条件暴露或复制整个集合。 | `PluginRegistry.names()`。 |
| 上下文管理器 | 打开、刷新和关闭审计文件。 | `JsonlAuditLog`。 |

## 5. 为什么不能复制日志代码

若每个插件函数都手写“开始”“结束”“失败”日志，格式会逐渐不一致，错误路径也容易遗漏。加前缀是业务规则；记录调用边界是横切关注点。横切行为应放在清晰的小包装层，不应混入每一个业务函数。

## 6. 装饰器最小示例

```python
# 文件：examples/module_04/decorator_basics.py
# 版本：1.0.0
from functools import wraps


def announce(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        print(f"开始：{function.__name__}")
        result = function(*args, **kwargs)
        print(f"结束：{function.__name__}")
        return result
    return wrapper


@announce
def add_task_prefix(text: str) -> str:
    return f"任务：{text}"


if __name__ == "__main__":
    print(add_task_prefix("阅读输出"))
```

运行 `python3 examples/module_04/decorator_basics.py` 的预期输出：

```text
开始：add_task_prefix
结束：add_task_prefix
任务：阅读输出
```

## 7. 逐行解释装饰器

`announce` 接收原函数。`wrapper` 用 `*args` 和 `**kwargs` 原样接收调用参数，避免装饰器意外限制原函数的调用形式。`result = function(...)` 执行业务逻辑，`return result` 保留原函数的返回值契约。`@wraps(function)` 保留原函数名称和文档，调试与测试时不会只看到 `wrapper`。`@announce` 等价于 `add_task_prefix = announce(add_task_prefix)`。[1]

## 8. 项目中的脱敏日志装饰器

项目的 `log_transform_call` 只记录插件名和输入/输出长度，不记录文本正文。库通过 `logging.getLogger(__name__)` 创建模块级记录器，而命令行程序决定日志级别和输出位置；这是标准库推荐的分层日志模式。[3]

```python
# 文件：02_可运行项目/projects/04-plugin-system/src/plugins.py（节选，版本 0.2.0）
@log_transform_call
def apply(self, name: str, text: str, *, audit_log=None) -> str:
    _validate_plugin_name(name)
    _validate_text(text)
    plugin = self._plugins.get(name)
    if plugin is None:
        raise UnknownPluginError(f"未知插件：{name}")
    return plugin.transform(text)
```

装饰器不能替代业务校验。它负责可观测性与统一异常边界；`apply()` 仍必须检查输入、查找允许插件并执行转换。

## 9. 装饰器失败案例与 Traceback

下面的包装器遗漏了返回值。

```python
def broken_trace(function):
    def wrapper(*args, **kwargs):
        print("开始")
        function(*args, **kwargs)  # 错误：丢掉了结果。
    return wrapper
```

下游若调用 `len(convert("学习"))`，会得到 `TypeError: object of type 'NoneType' has no len()`。Traceback 中会出现调用点和 `wrapper`；根因不是“有 wrapper”，而是包装层没有把原函数的结果交还给调用者。修复是保存 `result` 并返回它。

## 10. 生成器最小示例

```python
# 文件：examples/module_04/generator_basics.py
# 版本：1.0.0
from collections.abc import Generator


def plugin_names() -> Generator[str, None, None]:
    for name in ("agent_note", "task", "summarize"):
        yield name


if __name__ == "__main__":
    names = plugin_names()
    print(next(names))
    print(list(names))
```

预期输出为：

```text
agent_note
['task', 'summarize']
```

## 11. 逐行解释生成器

调用 `plugin_names()` 不会立刻执行完整循环，而是返回生成器对象。每到 `yield`，函数产生一个名称并暂停；下次迭代从暂停处继续。因此第一次 `next(names)` 已经消费 `agent_note`，随后 `list(names)` 只得到剩余值。若要重新开始，应再次调用 `plugin_names()`。

## 12. 项目中的名称生成器

```python
# 文件：02_可运行项目/projects/04-plugin-system/src/plugins.py（节选，版本 0.2.0）
def names(self):
    """按稳定排序逐个产生插件名，而非暴露内部字典。"""
    yield from sorted(self._plugins)
```

这里先排序是为了得到稳定、可测试的命令行输出。对极大注册表，排序会占用额外时间和内存；若不需要稳定顺序，可遍历字典键。优化前先测量真实规模，不能把“生成器”误解为自动更快的魔法。

## 13. 生成器常见错误

```python
names = plugin_names()
print(list(names))
print(list(names))  # []：生成器已被消费完。
```

这不是 Python 出错，而是流的位置已经到达末尾。需要多次遍历时，保存源数据或每次重新创建生成器。不要为了可重用而盲目把大数据流全部转成列表。

## 14. 上下文管理器最小示例

```python
# 文件：examples/module_04/context_manager_basics.py
# 版本：1.0.0
from pathlib import Path


class LineWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.file = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open("a", encoding="utf-8")
        return self

    def write(self, text: str) -> None:
        if self.file is None:
            raise RuntimeError("请在 with 语句中调用 write。")
        self.file.write(text + "\n")
        self.file.flush()

    def __exit__(self, exc_type, exc, traceback) -> bool:
        if self.file is not None:
            self.file.close()
            self.file = None
        return False


if __name__ == "__main__":
    with LineWriter(Path("runtime/example.log")) as writer:
        writer.write("离开 with 后文件将关闭")
```

## 15. 逐行解释 `with`

进入 `with` 时会调用 `__enter__()`，其返回值绑定给 `as writer`。无论代码块正常结束还是抛出异常，退出时都会调用 `__exit__()`。本例关闭文件后返回 `False`，表示不压制异常；调用者仍能收到真实 Traceback。上下文管理器通常使用 `try`/`finally` 的同一思想确保资源释放。[2]

## 16. 项目中的审计上下文管理器

`JsonlAuditLog` 以 JSON Lines 写入一次调用的一行元数据。项目测试验证在 `with` 退出后可读取文件，并确认敏感文本不出现在审计内容中。

```python
# 文件：02_可运行项目/projects/04-plugin-system/src/cli.py（调用模式）
with JsonlAuditLog(audit_path) as audit_log:
    print(registry.apply("task", "包含敏感信息的文本", audit_log=audit_log))
```

可能写入：

```json
{"error_type": null, "input_length": 10, "output_length": 13, "plugin": "task", "success": true}
```

记录长度不是“绝对匿名化”。长度、时间、插件名和用户身份上下文仍可能具有敏感性；生产系统还要单独设计保留期限、访问控制和删除策略。

## 17. 三种机制如何协作

| 顺序 | 机制 | 行为 | 验收证据 |
|---:|---|---|---|
| 1 | 上下文管理器 | 打开审计文件。 | 文件可写。 |
| 2 | 装饰器 | 记录调用开始，不含正文。 | 应用日志。 |
| 3 | 业务函数 | 校验名称、查找允许插件、执行转换。 | 转换输出。 |
| 4 | 上下文管理器 | 写入成功或失败的审计元数据。 | 一行 JSON。 |
| 5 | 装饰器 | 记录结束或异常类型。 | 统一诊断事件。 |
| 6 | 上下文管理器 | 退出时刷新并关闭文件。 | 退出后可读取审计文件。 |

## 18. 工程与性能取舍

装饰器应短小、明确，不能偷偷修改业务结果或把“重试”塞进不可见包装层。生成器适合一次性流处理，不适合随机访问或必须反复遍历的界面。上下文管理器只处理资源生命周期，不应承担复杂业务决策。每一种抽象都要有可观察输入、输出、错误和测试。

## 19. 安全边界

| 风险 | 不恰当做法 | 本项目的做法 |
|---|---|---|
| 日志泄露 | 记录完整 `text`。 | 仅记录长度与状态。 |
| 资源泄露 | 手工打开文件并依赖记忆关闭。 | 用 `with JsonlAuditLog(...)`。 |
| 错误吞没 | `__exit__()` 返回真值。 | 返回 `False`，保留异常。 |
| 内存膨胀 | 无条件把流转成列表。 | 用生成器按需产生值。 |
| 诊断混乱 | 将所有错误改为笼统 `Exception`。 | 区分输入错误、未知插件和插件执行错误。 |

## 20. 单元测试与运行证据

执行以下命令：

```bash
cd 02_可运行项目/projects/04-plugin-system
python3 -m unittest discover -s tests -v
```

当前项目有 15 项测试，覆盖生成器顺序、输入类型、审计脱敏、未知插件审计、受控配置和 CLI 行为。测试的是行为证据，而不是私有字典等实现细节。

## 21. 快速测试（5 题）

1. `@announce` 等价于哪种赋值？
2. 为什么 `wrapper` 必须返回 `result`？
3. 为什么第二次 `list(names)` 得到空列表？
4. `__exit__()` 返回 `False` 时异常如何处理？
5. 为什么长度日志通常比原文日志更安全？它仍有什么局限？

**答案要点：** 1. `f = announce(f)`；2. 保持返回值契约；3. 生成器已被消费；4. 异常向外传播；5. 少暴露内容，但元数据仍可能敏感。

## 22. 代码阅读（2 题）

1. 阅读 `log_transform_call`，说明它对 `PluginError`、`TypeError` 和其他异常为什么采用不同路径。
2. 阅读 `names()`。将 `yield from sorted(self._plugins)` 改成 `return sorted(self._plugins)` 后，函数还是否是生成器？请用 `list(...)` 验证并解释。

## 23. Debug（2 题）

1. 修复第 9 节 `broken_trace` 的遗漏返回值，并为修复前后各写一个断言。
2. 修改第 14 节的 `LineWriter`，故意让 `write()` 在写入前抛出 `ValueError`；验证 `__exit__()` 仍关闭文件，且 `ValueError` 未被吞掉。

## 24. 编程练习（3 题）

1. 创建 `timing_decorator.py`：用 `time.perf_counter()` 写耗时装饰器，保留返回值且不记录参数正文；写两项测试。
2. 创建 `chunked_lines.py`：写生成器 `read_nonempty_lines(path)`，逐项产生非空行；让 `FileNotFoundError` 自然传播，并写三项测试。
3. 创建 `temporary_setting.py`：写上下文管理器，在 `with` 内临时改一个字典键，正常或异常退出均恢复旧值；写两项测试。

## 25. 逆向设计与课后项目

**逆向设计：** 某 Agent 把提示词、身份证号和检索内容全写进日志；长文档一次读入内存；网络异常后连接未关闭。请从结果倒推至少六项缺陷，并映射到日志脱敏、生成器、上下文管理器、输入校验、数据最小化和测试证据。

**课后项目：** 为项目 4 增加冻结 `SuffixPlugin`，且只通过显式允许列表配置 `suffix` 类型。你必须拒绝未知字段、支持 CLI 调用、保持审计不记录正文，并新增至少五项测试：成功、重复名称、错误字段、错误类型和审计脱敏。README 必须解释：为什么允许列表并不等于运行不可信第三方插件的安全沙箱。

### 本章项目映射

本章的装饰器、生成器和上下文管理器可在 `examples/module_04/` 与 `02_可运行项目/projects/04-plugin-system/` 中对照阅读。先运行机制示例测试与安全插件系统测试：

```bash
python3 -m unittest discover -s 05_教学测试/tests/module_04 -v
cd 02_可运行项目/projects/04-plugin-system
.venv/bin/python -m pytest
.venv/bin/python -m mypy
.venv/bin/python -m ruff check src tests
```

**主题化扩展：** 为一个内置、固定类型的插件转换补充装饰器保留元数据或 `with` 资源清理测试；生成器只消费允许的公开记录。不得通过装饰器动态导入模块、通过生成器无限读取数据，或把上下文管理器当作对文件、网络、秘密或外部副作用的授权。

完成后记录输入/输出合同、资源关闭路径和受控失败。测试通过只说明教学示例和固定插件合同可复现，不代表动态代码加载、任意插件、安全审计或生产资源管理已获验证。

## 参考资料

[1]: https://docs.python.org/3/glossary.html#term-decorator "Python Glossary: decorator"
[2]: https://docs.python.org/3/glossary.html#term-context-manager "Python Glossary: context manager"
[3]: https://docs.python.org/3/library/logging.html "Python logging documentation"
