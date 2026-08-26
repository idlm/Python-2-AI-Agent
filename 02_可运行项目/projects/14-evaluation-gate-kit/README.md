# 项目 14：评测基线与发布门禁工具包

**版本：** 0.1.0  
**兼容性：** Python 3.11+  
**课程位置：** 模块 14——先用离线案例、最小 trace 和确定性发布门禁验证 Agent 质量，再讨论真实生产部署。

本项目是**框架无关、无网络、无副作用**的教学工具包。它不调用模型、追踪平台、外部评测 API、网络、数据库、shell、MCP、账户、支付、真实工具或部署服务。

项目只实现可离线验证的合同：严格评测案例、基线/候选结果、硬阻断项、未运行项、阈值比较、发布决定、最小 trace 事件、原子无正文报告和人工复核模板。它不会执行被评测 Agent，也不会自动更新基线。

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

| 当前验证 | 明确不提供 |
|---|---|
| 纯数据案例、确定性结果比较、硬阻断、未运行拒绝、发布决定、最小 trace、无正文报告与人工复核字段。 | 模型调用、LLM grader、真实 trace、生产数据、外部评测平台、部署、动态工具、账户或任何副作用。 |

通过发布门禁只说明此工具包上的固定离线合同成立；它不证明真实模型、工具、数据、追踪平台或生产部署安全。模块 14 的一手研究依据见 `../../records/module_14_research_notes.md`。


## 静态门禁评测

项目提供 `course-evaluation-gate --status`（默认不执行）、`course-evaluation-gate --run-static-gates`（回放公开夹具）与 `course-evaluation-gate --write-static-report`（在当前目录写入固定名称 `evaluation-gate-report.json`）。报告只含案例 ID、期望/实际发布决定、通过标记和阻断计数，不含案例细节、任务正文、提示、参数、trace 原文、工具结果或密钥；CLI 不接受任意输出路径。

`docs/human_review_template.csv` 只包含受控案例/版本/风险/决定和理由类别字段，明确禁止正文与敏感运行数据。当前 v0.1.0 已通过 **14 项无网络 pytest**、mypy 和 Ruff。测试覆盖硬阻断、未运行、软回归阈值、基线不匹配、案例覆盖、最小 trace、严格公开夹具、重复 ID、额外字段、损坏 JSON、缺失夹具、报告隐私、默认无执行 CLI 与冲突模式拒绝。通过不代表模型、trace 平台、外部评测、生产数据、真实工具或部署已经安全接入。
