"""补齐模块 4.3 与 4.4 的项目映射。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]
MAPPINGS = {
    "module_04_chapter_4_3.md": """
### 本章项目映射

本章的装饰器、生成器和上下文管理器可在 `examples/module_04/` 与 `projects/04-plugin-system/` 中对照阅读。先运行机制示例测试与安全插件系统测试：

```bash
python3 -m unittest discover -s tests/module_04 -v
cd projects/04-plugin-system
.venv/bin/python -m pytest
.venv/bin/python -m mypy
.venv/bin/python -m ruff check src tests
```

**主题化扩展：** 为一个内置、固定类型的插件转换补充装饰器保留元数据或 `with` 资源清理测试；生成器只消费允许的公开记录。不得通过装饰器动态导入模块、通过生成器无限读取数据，或把上下文管理器当作对文件、网络、秘密或外部副作用的授权。

完成后记录输入/输出合同、资源关闭路径和受控失败。测试通过只说明教学示例和固定插件合同可复现，不代表动态代码加载、任意插件、安全审计或生产资源管理已获验证。
""",
    "module_04_chapter_4_4.md": """
### 本章项目映射

本章直接对应 `projects/04-plugin-system/`。从 `src/safe_plugin_system/`、允许类型配置、CLI 和测试阅读 Protocol、冻结数据、注册表、字段闭集、脱敏审计与受控退出码：

```bash
cd projects/04-plugin-system
.venv/bin/python -m pytest
.venv/bin/python -m mypy
.venv/bin/python -m ruff check src tests
```

**主题化扩展：** 为一个已有的内置允许类型增加字段闭集拒绝测试，并验证审计记录只保存长度和状态。不要新增 `python_module`、可调用对象、动态导入、任意路径、秘密、网络、shell 或真实账户字段；配置文件是数据，不是代码或权限边界。

完成后记录允许列表、输入/输出、异常、日志最小化和回归命令。该项目只验证固定本地插件合同，不构成任意扩展执行、插件供应链安全、真实环境读取或副作用授权。
""",
}


def main() -> None:
    for filename, block in MAPPINGS.items():
        path = ROOT / "chapters" / filename
        text = path.read_text(encoding="utf-8")
        if "### 本章项目映射" in text:
            raise RuntimeError(f"mapping already present: {path}")
        markers = [marker for marker in ("\n## References\n", "\n## 参考资料\n") if marker in text]
        if len(markers) != 1:
            raise RuntimeError(f"expected one reference marker: {path}")
        path.write_text(text.replace(markers[0], "\n" + block.strip() + "\n" + markers[0], 1), encoding="utf-8")
        print(f"updated {path.name}")


if __name__ == "__main__":
    main()
