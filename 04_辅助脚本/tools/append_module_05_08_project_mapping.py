"""为模块 5–8 各章节追加工程项目映射。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]
MAPPINGS: dict[str, tuple[str, str, str, str]] = {
    "module_05_chapter_5_1.md": ("projects/05-cli-tool-platform/", "从 `pyproject.toml`、`src/` 与 README 的安装步骤验证项目根目录和解释器边界。", "cd projects/05-cli-tool-platform && .venv/bin/python -m pytest", "在临时目录复现一次从错误工作目录运行的失败，再在 README 中说明为何项目根目录是合同的一部分。"),
    "module_05_chapter_5_2.md": ("projects/05-cli-tool-platform/", "阅读控制台入口、pytest、mypy、Ruff 与 CI 的相互关系，区分开发依赖和运行依赖。", "cd projects/05-cli-tool-platform && .venv/bin/python -m pytest && .venv/bin/python -m mypy && .venv/bin/python -m ruff check src tests", "为一个纯函数增加测试、类型注解和静态检查通过证据；不要以跳过类型检查换取短期绿色。"),
    "module_05_chapter_5_3.md": ("projects/05-cli-tool-platform/", "结合 `.gitignore`、README 和 CI 阅读哪些文件应提交、哪些只应在本地存在。", "cd projects/05-cli-tool-platform && .venv/bin/python -m pytest", "起草一次只包含单一合同变更的提交说明，列出应随之更新的测试、文档与 CI 证据。"),
    "module_05_chapter_5_4.md": ("projects/05-cli-tool-platform/", "阅读 TOML 字段闭集、环境变量优先级和 stderr 最小诊断，定位配置/日志边界。", "cd projects/05-cli-tool-platform && .venv/bin/python -m pytest", "新增一个非敏感设置项；拒绝未知字段，并写测试证明日志不输出完整配置或环境变量。"),
    "module_05_chapter_5_5.md": ("projects/01-task-manager/ 与 projects/05-cli-tool-platform/", "比较历史脚本与 `src` 布局迁移后的安装、兼容层、测试和入口职责。", "cd projects/01-task-manager && .venv/bin/python -m pytest && cd ../05-cli-tool-platform && .venv/bin/python -m pytest", "为一个旧入口设计薄兼容层，只委托新包逻辑；写回归测试避免两套实现分叉。"),
    "module_06_chapter_6_1.md": ("projects/06-knowledge-api/", "从 API 模型和测试读取路径、方法、请求/响应 Schema、状态码与公开错误之间的合同。", "cd projects/06-knowledge-api && .venv/bin/python -m pytest", "增加一个只读端点的 Schema 测试；未知字段或错误方法必须落到受控 4xx，而不暴露内部异常。"),
    "module_06_chapter_6_2.md": ("projects/06-knowledge-api/", "阅读请求 ID、依赖注入与公开错误转换，区分 API 层、领域层和日志责任。", "cd projects/06-knowledge-api && .venv/bin/python -m pytest", "为一个领域错误增加稳定错误代码与请求 ID；测试响应不回显请求正文或内部堆栈。"),
    "module_06_chapter_6_3.md": ("projects/06-knowledge-api/", "追踪 SQLite 仓储、参数化查询、事务与备份恢复测试，理解持久化的提交/回滚边界。", "cd projects/06-knowledge-api && .venv/bin/python -m pytest", "为一次写入失败补充回滚断言；不要直接拼接 SQL 或将数据库路径/正文写入公开错误。"),
    "module_06_chapter_6_4.md": ("projects/06-knowledge-api/ 与 examples/module_06/async_reliability.py", "对照异步示例与服务测试，识别 TaskGroup、超时、取消和 finally 清理的不同责任。", "python3 -m unittest discover -s tests/module_06 -v && cd projects/06-knowledge-api && .venv/bin/python -m pytest", "增加一个有限超时测试；结果未知时只报告状态类别，不假设远端或后台工作未发生。"),
    "module_07_chapter_7_1.md": ("projects/07-polite-api-collector/", "阅读 HTTPS/主机允许列表、连接池、超时和有限重试，区分请求安全与业务许可。", "cd projects/07-polite-api-collector && .venv/bin/python -m pytest", "增加一个不允许的基址测试，验证在发请求前受控拒绝且不输出认证信息。"),
    "module_07_chapter_7_2.md": ("projects/07-polite-api-collector/", "阅读 robots、Semaphore、Pacer 与 TaskGroup 测试，区分并发上限、节奏和站点规则。", "cd projects/07-polite-api-collector && .venv/bin/python -m pytest", "设计一个来源级预算；测试 robots 拒绝时不会启动 fetch，也不将 robots 视为法律或访问授权。"),
    "module_07_chapter_7_3.md": ("projects/07-polite-api-collector/", "追踪 JSONL、去重、清单、原子快照和显式恢复路径。", "cd projects/07-polite-api-collector && .venv/bin/python -m pytest", "为损坏清单新增受控失败和显式恢复测试；报告只输出计数和状态，不输出采集正文。"),
    "module_08_chapter_8_1.md": ("projects/08-workflow-service/", "阅读核心状态机、幂等键和公开视图，绘制 pending/running/completed/failed/cancelled 的允许转换。", "cd projects/08-workflow-service && .venv/bin/python -m pytest", "新增一个非法状态转换测试；重复键若引用不同工作必须返回冲突而不是覆盖旧记录。"),
    "module_08_chapter_8_2.md": ("projects/08-workflow-service/", "阅读有界队列、反压、TaskGroup、超时、取消和 drain 的测试，定位“接受”与“完成”的差异。", "cd projects/08-workflow-service && .venv/bin/python -m pytest", "为队列满的路径添加断言，确保新任务在注册前被拒绝且不会留下孤儿 pending 项。"),
    "module_08_chapter_8_3.md": ("projects/08-workflow-service/", "阅读 FastAPI lifespan、关停恢复候选、请求 ID 和 API 合同，理解服务停止并不等于外部结果已知。", "cd projects/08-workflow-service && .venv/bin/python -m pytest", "为优雅关停后的 interrupted 任务增加恢复候选测试；不得自动标记成功或无限制重放。"),
}


def block(path: str, reading: str, command: str, extension: str) -> str:
    return f'''\n\n### 本章项目映射\n\n本章建议直接在 `{path}` 中完成可运行练习。先执行：{reading}\n\n```bash\n{command}\n```\n\n**主题化扩展：** {extension}\n\n完成后记录输入/输出合同、受控失败、测试命令和安全边界。不要把项目中的本地替身、测试夹具、回环服务或默认无执行模式误作真实网络、模型、生产数据、秘密、部署或副作用授权。\n'''


def main() -> None:
    for filename, values in MAPPINGS.items():
        path = ROOT / "chapters" / filename
        text = path.read_text(encoding="utf-8")
        if "### 本章项目映射" in text:
            raise RuntimeError(f"mapping already present: {path}")
        matches = [marker for marker in ("\n## References\n", "\n## 参考资料\n") if marker in text]
        if len(matches) != 1:
            raise RuntimeError(f"expected one reference marker: {path}")
        marker = matches[0]
        path.write_text(text.replace(marker, block(*values) + marker, 1), encoding="utf-8")
        print(f"updated {filename}")


if __name__ == "__main__":
    main()
