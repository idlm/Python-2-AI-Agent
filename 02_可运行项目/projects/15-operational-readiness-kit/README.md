# 项目 15：运行准备与恢复合同工具包

**版本：** 0.1.0  
**兼容性：** Python 3.11+  
**课程位置：** 模块 15——先验证配置、秘密、健康、停止、恢复和 Runbook 合同，再考虑任何真实部署。

本项目是**框架无关、无网络、无副作用**的教学工具包。它不启动服务，不监听端口，不读取真实环境变量或秘密值，不连接云、Docker、Kubernetes、数据库、遥测、模型、MCP、账户、支付、网络或真实工具。

项目只实现可离线验证的合同：严格部署 profile、秘密元数据、默认拒绝能力、运行阶段、健康/drain、恢复计划、版本兼容、运行准备阻断项、公开静态夹具、最小报告和运维模板。它不会创建真实备份、恢复数据、轮换秘密或部署服务。

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
| 纯数据配置 profile、秘密元数据、运行阶段、恢复计划、准备门禁、静态夹具、无正文报告和 Runbook 字段。 | 真实环境变量、秘密值、端口、HTTP 服务、容器、云、Kubernetes、数据库、备份、恢复、遥测、模型、工具或部署。 |

通过运行准备门禁只说明固定离线合同成立；它不证明真实服务、网络、秘密、备份、恢复或生产环境安全。模块 15 的一手研究依据见 `../../records/module_15_research_notes.md`。


## 静态运行准备评测与运维模板

项目提供 `course-operational-readiness --status`（默认不执行）、`course-operational-readiness --run-static-readiness`（回放公开夹具）与 `course-operational-readiness --write-static-report`（在当前目录写入固定名称 `operational-readiness-report.json`）。报告只包含案例 ID、期望/实际决定、通过标记和阻断计数，不含配置正文、秘密值或类别、端点、trace、恢复详情或 Runbook 正文；CLI 不接受任意输出路径。

`docs/operational_runbook_template.md` 提供暂停、结果未知、恢复、回滚、升级与复盘的最小字段，并明确禁止记录秘密、用户正文、提示词、完整配置、生产端点和原始 trace。当前 v0.1.0 已通过 **17 项无网络 pytest**、mypy 和 Ruff。测试覆盖部署 profile、秘密元数据不含值字段、环境边界、秘密过期/撤销/缺失、drain、恢复演练、版本兼容、Runbook 完整度、严格夹具、重复 ID、额外字段、损坏 JSON、缺失夹具、公开报告隐私、默认无执行 CLI 与冲突模式拒绝。
