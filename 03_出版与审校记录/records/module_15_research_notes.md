# 模块 15 研究笔记：部署准备、运行、恢复与运维

**核对日期：** 2026-08-26（GMT+8）  
**用途：** 为模块 15 的部署配置、健康检查、优雅停止、秘密、可观察性、备份恢复与 Runbook 教学提供一手资料依据。本文只定义生产准备前的设计约束；不构成真实云、容器、Kubernetes、遥测平台或密钥系统的接线方案。

## 一手资料与可教学结论

| 主题 | 一手资料结论 | 教材设计结论 |
|---|---|---|
| 生命周期、健康与停止 | Kubernetes 将 Pod 置于明确生命周期中，由 kubelet 管理容器并执行探针；终止需有优雅关闭窗口，应用必须处理停止而非假设请求永远完成。[1] | 将存活、就绪、启动、drain、停止、结果未知和恢复设计为不同状态；健康端点不是业务授权、数据正确性或安全证明。 |
| 配置显式启用 | OpenTelemetry 配置中，定义组件并不等于启用；需要在 service pipeline 中明确引用，且配置可独立验证。[3] | 配置采用字段闭集、允许列表、版本、默认拒绝和离线验证；“存在于文件”不等于“获准运行”。 |
| 监听面与遥测 | OpenTelemetry 文档提示，所有客户端均为本机时应优先绑定 localhost；示例 `0.0.0.0` 只是便利展示，并提醒考虑 DoS 防护。[3] | 默认最小暴露面；运维端点、trace、指标、调试端点必须独立鉴权、网络限制、数据最小化和显式启用。 |
| Secrets 并非天然安全 | Kubernetes Secret 用于与代码分离的敏感数据，但默认 etcd 存储未加密，且能访问 API/命名空间者可能读取；文档建议静态加密、最小 RBAC、限制容器访问和外部 secret store。[2] | 不把 Base64 当加密；秘密不进源码、日志、报告、镜像、公开夹具或 CI 输出。定义用途、最小权限、版本/轮换、撤销、过期、审计与破窗流程。 |
| 秘密生命周期 | OWASP 建议秘密管理覆盖集中化、访问控制、自动化/轮换、审计、创建、轮换、撤销、过期、备份恢复和事故响应。[4] | 不存储秘密值；只在离线合同中验证秘密标识、用途、访问角色、轮换与到期元数据是否完整。 |
| 观测管道 | OpenTelemetry 将 receiver、processor、exporter、connector 与 service pipeline 分离；处理器可过滤/删除属性，顺序会改变处理结果。[3] | 将“采集什么、脱敏什么、可导出到哪里、保留多久”写成可审查合同；trace/日志管道也是敏感数据处理链。 |
| 备份与恢复 | OWASP 把 downtime、break-glass、backup and restore 纳入秘密管理；Kubernetes 生命周期与状态存储说明停止/恢复不能假设内存仍在。[1] [4] | 备份范围、版本、加密、访问、保留、恢复演练、RPO/RTO、兼容性和结果未知需预先定义；“有备份”不等于“能恢复”。 |
| 运行边界 | 已研读持久计算技能：默认沙箱会休眠，不能作为长期服务；若将来真正需要 Web 服务、持久进程或后台任务，应先按工作负载选择 WebDev、用户本地环境或受限持久计算，并在真实部署前进行独立安全审查。 | 本模块只做部署准备合同和本地离线验证，不启动守护进程、不暴露端口、不创建 Docker/云/Kubernetes 资源、不发布服务。 |

## 模块 15 的非目标

模块 15 **不**启动或部署任何真实服务，不暴露端口，不连接云、Kubernetes、Docker、遥测、秘密平台、数据库、模型、MCP、网络、账户、支付或工具。先实现纯数据配置清单、健康/停止状态、秘密元数据、恢复计划、运行准备门禁、最小报告和 Runbook 模板。将来真实部署仍需独立威胁建模、平台选择、权限、成本、数据保留、备份恢复演练、监控、事件响应与用户批准。

## 参考资料

[1]: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/ "Kubernetes: Pod Lifecycle"
[2]: https://kubernetes.io/docs/concepts/configuration/secret/ "Kubernetes: Secrets"
[3]: https://opentelemetry.io/docs/collector/configuration/ "OpenTelemetry: Configuration"
[4]: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html "OWASP: Secrets Management Cheat Sheet"
