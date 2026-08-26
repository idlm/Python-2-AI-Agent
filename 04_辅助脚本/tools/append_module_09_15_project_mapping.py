"""为模块 9–15 追加离线项目映射；不触发模型、网络或任何副作用。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]
SPECS: dict[int, tuple[str, str, list[str]]] = {
    9: (
        "09-llm-contract-client",
        "从固定模型/任务、严格 JSON Schema、本地重复验证、静态夹具和最小报告读取“模型只提议、应用才验证”的合同。",
        ["为一个无效候选补充本地 Schema 拒绝测试；不得把提示词、模型输出或一次烟雾当作权限边界或质量证明。", "追踪拒答、空内容和非法 JSON 的受控错误；测试日志只保存元数据，绝不记录提示词、正文、秘密或完整原始响应。", "运行静态夹具评测并记录门结果；离线覆盖率不是事实性、模型安全、成本、容量或生产可用性认证。"],
    ),
    10: (
        "10-rag-contract-workbench",
        "从公开语料合同、稳定切块、教学嵌入替身、内存检索、来源约束与离线评测读取 RAG 的证据边界。",
        ["为一个文档/切块合同错误添加静态测试；哈希嵌入只是教学替身，不得推断真实 embedding 能力、维度、费用或语义质量。", "对来源级检索结果补充空结果或注入文本夹具；不把检索命中、来源名或引用格式误写成事实认证。", "为无证据路径补充稳定拒答断言；候选回答只能引用实际检索到的块，且不得执行工具或泄露查询/正文。", "扩展离线支持度案例并记录人工复核；不调用模型、端点或真实向量服务，也不将离线门禁称为生产验收。"],
    ),
    11: (
        "11-bounded-agent-core",
        "从有限状态、固定纯工具、独立预算、审批暂停、最小事件和静态回放理解无框架受限 Agent。",
        ["为非法状态转换或越过步骤预算增加夹具；Agent 状态机不是框架、模型调用或真实工具执行。", "为未知工具或参数错误增加默认拒绝测试；工具目录必须固定且纯函数，不得接入文件、网络、shell 或账户。", "对审批暂停/拒绝路径增加断言；批准只是教学合同字段，不是对真实副作用的授权。", "运行静态回放与报告路径；事件和报告不得保存任务正文、提示词、秘密、完整 trace 或原始响应。"],
    ),
    12: (
        "12-framework-adoption-kit",
        "从候选字段闭集、工具目录、最小 checkpoint、审批恢复绑定、迁移夹具和无正文报告学习框架采用前合同。",
        ["为额外字段或工具目录漂移添加迁移夹具；不得安装、导入或假定真实编排框架能力。", "验证 checkpoint 与候选指纹绑定；该纯数据示例不实现真实持久化、恢复重放或跨进程状态。", "为审批主体/租户错配补充拒绝案例；审批合同不授予真实账户、工具或数据权限。", "运行静态迁移质量门；报告只含公开 ID/计数/门结果，不含正文、秘密、端点或生产 trace。"],
    ),
    13: (
        "13-delegation-contract-kit",
        "从固定角色、最小工具集合、字段闭集委派、预算、去重、取消和稳定汇总理解权限不扩散。",
        ["为不属于角色的工具或超预算委派添加拒绝夹具；角色名不是执行账户或权限升级机制。", "验证重复键和身份错配处理；不得创建真实 worker、并发任务、网络调用或工具执行。", "为取消传播或冲突汇总添加稳定断言；取消不等于已经撤销外部副作用或已知最终结果。", "运行静态汇总/报告门；只保留最小公共字段，禁止写入委派正文、提示词、秘密或完整 trace。"],
    ),
    14: (
        "14-evaluation-gate-kit",
        "从离线案例、最小 trace、基线/候选比较、硬阻断、软阈值与人工复核学习评测发布门禁。",
        ["为缺失案例或基线不匹配增加硬阻断夹具；评测分数不是事实、可靠性、安全或部署认证。", "为软回归阈值与未运行状态增加测试；不要把未运行/不足证据自动解释为通过。", "检查最小 trace 字段与数据最小化；不得记录输入正文、提示词、秘密、模型响应或完整追踪。", "运行离线门禁报告并安排人工复核；不调用真实模型、追踪平台、外部评测 API 或发布服务。"],
    ),
    15: (
        "15-operational-readiness-kit",
        "从离线部署 profile、无秘密值元数据、drain、恢复演练、版本兼容和 Runbook 学习运行准备合同。",
        ["为不完整或含秘密值的 profile 增加拒绝夹具；配置元数据不是环境读取、秘密接线或部署授权。", "为 drain/停止中断状态补充测试；结果未知必须明确建模，不得伪装为完成或自动重试外部动作。", "为恢复演练或版本不兼容增加硬阻断；教学恢复候选不证明备份、恢复或业务连续性成功。", "运行静态 Runbook/报告门；不得启动服务、端口、云、容器、数据库、遥测、模型、工具或真实部署。"],
    ),
}
COUNTS = {9: 3, 10: 4, 11: 4, 12: 4, 13: 4, 14: 4, 15: 4}


def mapping_block(project: str, reading: str, extension: str) -> str:
    return f'''\n\n### 本章项目映射\n\n本章对应 `{project}`。先在项目根目录阅读 README、`src/`、`tests/` 与公开静态夹具：{reading}\n\n```bash\ncd projects/{project}\n.venv/bin/python -m pytest\n.venv/bin/python -m mypy\n.venv/bin/python -m ruff check src tests\n```\n\n**主题化扩展：** {extension}\n\n上述命令只运行项目内的离线测试和静态检查；不要设置凭据、运行真实烟雾、调用网络/模型/数据库/文件系统/工具/账户，或把通过结果理解为真实能力、生产安全、部署、恢复、成本、容量、合规或副作用授权。\n'''


def main() -> None:
    for module, (project, reading, extensions) in SPECS.items():
        for chapter_no in range(1, COUNTS[module] + 1):
            path = ROOT / "chapters" / f"module_{module:02d}_chapter_{module}_{chapter_no}.md"
            text = path.read_text(encoding="utf-8")
            if "### 本章项目映射" in text:
                raise RuntimeError(f"mapping already present: {path}")
            markers = [marker for marker in ("\n## References\n", "\n## 参考资料\n") if marker in text]
            if len(markers) != 1:
                raise RuntimeError(f"expected one reference marker: {path}")
            path.write_text(text.replace(markers[0], mapping_block(project, reading, extensions[chapter_no - 1]) + markers[0], 1), encoding="utf-8")
            print(f"updated {path.name}")


if __name__ == "__main__":
    main()
