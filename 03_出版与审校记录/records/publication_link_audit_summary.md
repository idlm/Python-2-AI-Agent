# 出版参考链接复核结论

**日期：** 2026-08-26（GMT+8）  
**审计脚本：** `tools/audit_chapter_links.sh`  
**逐 URL 证据：** `records/publication_link_audit.log`  
**结果：** 通过，无“unreachable-*”阻断项。

## 分类结果

| 分类 | 含义 | 发布处理 |
|---|---|---|
| `reachable` | 自动 HTTP 检查得到 2xx 或 3xx。 | 可作为当前可访问的参考链接继续保留。 |
| `access-restricted` | 公开页面存在，但自动 HTTP 请求得到 401、403 或 429。 | 保留引用并在审校时以浏览器/人工复核可访问性；不将其误报为内容不存在。 |
| `illustrative` | `127.0.0.1`、`localhost`、`example.com`、`example.test` 等教学示例或本地地址。 | 不作为外部权威来源；保留以解释示例输入，正文必须标明其为占位或本地地址。 |

## 本次例外

| URL | 分类 | 说明 |
|---|---|---|
| `https://openai.com/index/prompt-injections/` | `access-restricted` | 自动请求被访问策略拒绝；该页面仍作为公开提示注入安全资料保留，后续发布前应人工复核。 |
| `http://127.0.0.1:*`、`http://localhost:*` | `illustrative` | 模块 6/8 本地服务示例，不应在离线链接审查时要求可达。 |
| `https://api.example.com`、`https://other.example.test/` | `illustrative` | 教学占位域名，不构成事实或生产端点引用。 |

> 链接可达性只说明在本次检查条件下 URL 可访问；它不证明页面内容正确、长期稳定、适合读者所在地区、满足许可要求或足以支持某条具体事实。外部事实仍须保留相邻数字引用并优先使用一手资料。
