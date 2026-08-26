# 项目 12：框架采用合同工具包

**版本：** 0.1.0  
**兼容性：** Python 3.11+  
**课程位置：** 模块 12——在采用图编排或 Agent 框架前，先验证状态、候选、审批恢复和工具边界。

本项目是**框架无关、无网络、无副作用**的教学工具包。它不安装 LangGraph、不调用模型、不执行工具、不访问文件、数据库、shell、MCP、账户或支付。它只实现可独立测试的合同：固定工具目录、候选字段闭集、最小 checkpoint 视图、候选指纹、审批恢复绑定、过期拒绝及执行前再验证。

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
| 纯数据合同、字段闭集、候选摘要、审批绑定、过期检查、跨租户拒绝与无网络测试。 | 任意 callable、动态工具、真实模型、网络、文件、数据库、shell、MCP、支付、账户、自动批准、真实持久化或任何副作用。 |

候选指纹只用于把经验证候选与审批恢复值绑定；它不是加密、身份认证、授权、审计或幂等工具调用实现。完整框架研究依据见 `../../records/module_12_research_notes.md`。


## 静态迁移评测

项目提供 `course-framework-adoption --status`（默认不执行）、`course-framework-adoption --run-static-migration`（回放公开夹具）与 `course-framework-adoption --write-static-report`（在当前目录写入固定名称 `framework-adoption-migration-report.json`）。报告只含案例 ID、期望/实际类别和通过标记，不含夹具参数、目标、提示词、工具结果或密钥；CLI 不接受任意输出路径。

当前 v0.1.0 已通过 **17 项无网络 pytest**、mypy 和 Ruff。测试覆盖固定工具目录、候选字段闭集、最小 checkpoint、候选指纹、审批绑定、跨租户/过期/拒绝失败、严格夹具、重复 ID、额外字段、损坏 JSON、缺失夹具、报告隐私、默认无执行 CLI 与冲突模式拒绝。通过不代表框架、模型、持久化后端或任何现实工具已安全接入。
