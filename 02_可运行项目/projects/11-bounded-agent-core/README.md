# 项目 11：受限 Agent 核心

**版本：** 0.2.0  
**兼容性：** Python 3.11+  
**课程位置：** 模块 11——在框架之前理解 Agent 的状态、工具、停止条件、审批与可观察性。

本项目将从一个**无框架、无副作用、可测试**的最小 Agent 合同开始。它不会接收任意工具、执行 shell、读写用户文件、访问网络、调用数据库、处理支付或自动代表用户行动。模型或规划器只能产生受限的下一步候选；应用将在模型外验证状态、动作、参数、预算和批准条件。

> **当前边界：** 此目录已实现有限状态、固定纯工具、最多五步预算、审批暂停/明确恢复或拒绝、最小事件、严格静态夹具与无正文评测报告；仍不讨论模型、框架、动态工具或任何真实副作用。

## 质量门禁

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest
.venv/bin/python -m mypy
.venv/bin/python -m ruff check src tests examples
```

## 安全边界

| 当前允许 | 当前不允许 |
|---|---|
| 固定状态、纯函数工具、有限预算、脱敏事件、离线假规划器与单元测试。 | 任意 callable、动态导入、shell/SQL/文件/网络、用户提供的工具名、秘密、自动审批、无限循环与真实副作用。 |

完整研究依据位于 `../../records/module_11_research_notes.md`。

当前 v0.2.0 已通过 **23 项无网络 pytest**、mypy、Ruff，并附有 Python 3.11/3.12 CI。测试覆盖任务 ID/目标/计数输入边界、固定纯工具、有限状态、相互独立的步骤/工具调用预算、稳定停止原因及状态一致性、审批暂停/恢复/拒绝、最小事件脱敏、未知动作、严格夹具解析及无正文报告；它们不构成真实模型质量、外部工具安全或生产可用性证明。

项目提供 `course-bounded-agent --status`（默认不执行任务）、`course-bounded-agent --run-static-evaluation`（仅回放公开教学夹具）和 `course-bounded-agent --write-static-report`（在当前工作目录写入固定名称 `bounded-agent-static-evaluation.json`）。最后一项不接受任意输出路径，报告仅含案例 ID、期望/实际状态和通过标记，不含任务目标、参数、工具结果或注入文本。任何模式均不会调用模型、网络、文件工具或其他副作用工具。


## 人工复核边界

`docs/human_review_template.csv` 是用于教学的最小复核记录模板。它仅保留案例 ID、夹具版本、预期/实际状态、复核决定、理由类别、复核者标识和时间；禁止填写任务目标、工具参数、工具结果、提示词、注入文本、用户正文或密钥。人工复核只评价既有离线案例和发布门禁，不会打开工具权限、改变预算或批准现实副作用。
