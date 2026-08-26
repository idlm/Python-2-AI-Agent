# 项目 13：多 Agent 委派合同工具包

**版本：** 0.1.0  
**兼容性：** Python 3.11+  
**课程位置：** 模块 13——先以纯数据合同约束多 Agent 委派、预算、权限和汇总，再讨论任何真实并发。

本项目是**框架无关、无网络、无副作用**的教学工具包。它不安装多 Agent 框架，不调用模型，不创建并发 worker，不访问网络、数据库、文件、shell、MCP、账户、支付或真实工具。

项目只实现可离线验证的合同：固定角色策略、最小工具集合、字段闭集委派、独立总量/活跃/角色预算、去重、有限状态迁移、取消传播、最小 worker 结果及稳定汇总。结果中不含自由正文、提示词或工具返回。

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
| 角色—工具最小权限、委派字段闭集、预算、去重、状态迁移、取消传播、无正文结果与稳定汇总。 | 模型、Agent 框架、真实并发、动态角色、动态工具、网络、数据库、持久化、真实输入、工具执行、自动审批或副作用。 |

多 Agent 委派是工作分配，不是授权传播。每个未来真实工具仍需固定 Schema、最小权限、预算、审批、幂等、审计、评测与 Runbook。模块 13 的一手研究依据见 `../../records/module_13_research_notes.md`。


## 静态委派评测

项目提供 `course-delegation-contract --status`（默认不执行）、`course-delegation-contract --run-static-delegation`（回放公开夹具）与 `course-delegation-contract --write-static-report`（在当前目录写入固定名称 `delegation-contract-report.json`）。报告只含案例 ID、期望/实际类别和通过标记，不含任务摘要、输入引用、参数、worker 正文、提示词、工具结果或密钥；CLI 不接受任意输出路径。

当前 v0.1.0 已通过 **15 项无网络 pytest**、mypy 和 Ruff。测试覆盖角色最小权限、委派去重、总量/活跃/角色预算、有限状态、取消传播、稳定汇总、冲突、身份错配、严格公开夹具、重复 ID、额外字段、损坏 JSON、缺失夹具、报告隐私、默认无执行 CLI 与冲突模式拒绝。通过不代表模型、多 Agent 框架、并发运行时、持久化后端或任何真实工具已安全接入。
