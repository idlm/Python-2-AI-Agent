# 项目 3：自动归档系统

**版本：** 0.2.0  
**课程位置：** 模块 3（文件、路径、异常）→ 模块 5（工程化迁移）  
**兼容性：** Python 3.11+

自动归档系统在一个明确的源目录中查找指定后缀的**当前层级普通文件**，生成归档计划，并且默认只执行 **Dry Run**。只有显式传入 `--apply` 才会移动文件；真实移动前一旦发现同名目标，工具立即失败，绝不覆盖。每次操作可写出 UTF-8 JSON 清单，供后续受控回滚。

> **安全声明：** 此工具不是通用文件管理器、备份系统或不可信路径沙箱。它不递归扫描、不删除、不覆盖、不上传文件。请只对你有权处理的本地目录执行它，并在真实移动前检查 Dry Run 结果。

## 快速开始

```bash
cd "02_可运行项目/projects/03-auto-archive"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --editable ".[dev]"

mkdir -p /tmp/archive-demo/source /tmp/archive-demo/archive
printf 'hello\n' > /tmp/archive-demo/source/note.txt
course-auto-archive /tmp/archive-demo/source /tmp/archive-demo/archive
course-auto-archive /tmp/archive-demo/source /tmp/archive-demo/archive --apply \
  --manifest /tmp/archive-demo/manifest.json
python -m pytest
python -m mypy src
python -m ruff check src tests
```

第一次命令只输出 `计划数量：1；实际移动：0`，源文件仍存在。第二次命令显式使用 `--apply` 后才移动文件，并将实际执行结果写到清单。

## 命令契约

| 参数 | 作用 | 默认行为与边界 |
|---|---|---|
| `source` | 需要扫描的本地目录。 | 必须存在；只扫描当前层级。 |
| `destination` | 归档目标目录。 | 不能与源目录相同；目标目录可在执行时创建。 |
| `--apply` | 允许真实移动。 | 未提供时仅 Dry Run。 |
| `--config FILE` | 受控 JSON 配置。 | 仅允许 `suffix` 字段，最大 64 KiB。 |
| `--manifest FILE` | 写入操作清单。 | UTF-8 JSON，不含文件正文。 |
| `--verbose` | 记录诊断日志。 | 日志写标准错误，用户结果写标准输出。 |

输入、配置、路径、冲突或回滚前置条件错误返回退出码 `2`。成功返回 `0`。真实移动必须显式 `--apply`，并且永不覆盖已有目标。

## 配置契约

```json
{
  "suffix": ".md"
}
```

没有配置时仅归档 `.txt` 文件。配置必须是 UTF-8 JSON 对象，且只允许 `suffix`；例如 `{"module": "os"}` 会受控拒绝，而不会导入模块或执行代码。配置文件大小限制为 64 KiB，防止错误或不可信输入导致不必要资源消耗。

## 清单与回滚

`--manifest` 写出的清单记录源路径、目标路径和是否已移动，不保存文件内容。库函数 `rollback_from_manifest(manifest_path, dry_run=True)` 默认同样只模拟回滚；只有 `dry_run=False` 才会执行移动。回滚前会检查目标仍存在且原位置尚未被占用，避免盲目覆盖。

清单不能替代备份：它只描述一次工具操作，不保存文件副本。重要数据仍需要由组织的备份、版本控制和恢复策略保护。

## 迁移说明

版本 0.2.0 将原有 `src/archive.py` 和 `src/cli.py` 迁移为可安装包 `auto_archive`，同时保留它们作为兼容导入入口。所有新代码应使用：

```python
from auto_archive.core import plan_archive, execute_archive
```

或命令行入口 `course-auto-archive`。项目使用 `src` 布局、`pyproject.toml`、pytest、mypy、Ruff、`.gitignore` 和 Python 3.11/3.12 CI。

## 质量与安全门禁

测试覆盖：计划和 Dry Run、合法与非法配置、操作清单、模拟与真实回滚、冲突拒绝、路径验证、CLI 默认 Dry Run 与未知字段受控拒绝。CI 只运行与本地相同的安装、pytest、mypy 和 Ruff 命令；它不保存密钥、不自动部署。

## 参考资料

[1]: https://docs.python.org/3/library/pathlib.html "Python `pathlib` documentation"
[2]: https://docs.python.org/3/library/json.html "Python `json` documentation"
[3]: https://docs.python.org/3/howto/logging.html "Python Logging HOWTO"
[4]: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/ "PyPA: Writing your pyproject.toml"
