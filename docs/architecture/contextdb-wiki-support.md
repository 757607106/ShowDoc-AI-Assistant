# ContextDB Wiki 接入能力与验证边界

更新日期：2026-11-14（Asia/Shanghai）。当前接入依据为 **ContextDB 0.0.9**。旧版“未公开 Wiki API”的结论已过时；[0.0.8 审计 JSON](reports/contextdb-wiki-audit.json)保留为历史证据，不代表当前服务能力。

## 官方契约与本平台实现

ContextDB 保存来源、正式正文、修订和处理状态，并负责 Wiki 编译。平台只维护业务空间映射、身份鉴权和操作界面，不增加本地 Wiki 编译器、正文库或发布状态。

| 能力 | 0.0.9 DATA API | 本平台接入 |
| --- | --- | --- |
| 主题索引 | `GET /v1/knowledge/wiki/index`，按 entity / concept / synthesis / comparison 分组，各组有 `total` 和 `next_cursor` | 分组浏览和继续加载；总量来自索引，不从搜索结果推算 |
| 目录与主题树 | `GET .../pages`，省略父节点读根层，指定 `parent_page_id` 读直接子项；`page_type=category` 只列目录 | 逐层展开，保留官方游标 |
| 页面搜索 | `GET .../search`，单次最多 50 条，不支持游标 | 用于定位页面；`total` 只是本次返回数，不是全部匹配数量 |
| 正式正文与文档摘要 | `GET .../pages/detail`、`GET .../summary` | 使用真实 `page_id` 导航，读取 `published/version/run_state`、来源、祖先与页面链接 |
| 人工创建与编辑 | `POST / PUT .../pages` | 创建 entity/concept 页，编辑提交读取时的 `expected_version`，保留冲突草稿并回读正式正文 |
| 修订历史与差异 | `GET .../revisions`、`GET .../revisions/diff` | 按页读取修订，使用修订 ID 比较；差异超过 800 行时显示截断提示 |
| 目录和页面整理 | `POST .../directories`、`POST .../directories/actions`、`POST .../pages/actions`、`DELETE .../pages` | 新建目录、重命名、移动、归档和删除；按官方版本及异步事件语义处理 |
| 编译进度与控制 | `GET .../compile-runs`、`POST .../compile-runs/actions` | 展示来源状态和全库计数，提供暂停、恢复、来源重编和失败重试 |
| 内容问题处理 | `GET .../issues`、`GET .../issues/detail`、`POST .../issues/actions`、`POST .../issues/tasks`、`GET .../issue-tasks/detail` | 查看证据、忽略/重开、提交处理决定与逐项查询任务结果 |

前端契约见 [contextdbWiki.ts](../../frontend/src/api/contextdbWiki.ts)，后端在 [contextdb.py](../../webapi/contextdb.py)按 **17 个精确路径及各自 HTTP 方法**放行，并使用当前登录用户的 ContextDB 成员凭据转发。只读账号可以读取索引、搜索和编译进度，不能写入。未知路径、错误方法和虚构审批/回滚接口不会转发到云端。Agent 的知识访问继续使用官方 MCP；这里的 DATA API 界面接入不增加或替换 Agent 工具。

## 必须保留的状态与并发语义

- `published=false` 时不能展示或引用缓存旧正文。页面详情中的来源与链接以服务端本次结果为准；`links/backlinks` 各最多 200 项，应保留 `*_total`、`*_truncated` 提示。
- 编辑受理生成新修订，返回新版本号不代表正式正文已更新。保存后核对正式正文及修订状态；409 后重读再合并，不默认取最新版本强行覆盖。
- 移动页面或目录需提交自身 `expected_version`；指定目标目录还需其 `expected_parent_version`。目录不能移入自身或后代，目录删除只适用于没有直接子项的目录。
- 页面归档退出检索并保留历史；删除会清理修订和旧证据，并阻止自动编译恢复同一页，属于不可恢复操作。DELETE 的库 ID 和页面 ID 位于查询参数。
- `wiki_compile_paused=true` 仅暂停新摄取触发的编译，**不会停止在途任务**。恢复也不会自动补派暂停期间积压的来源；暂停不是第三方编译器的隔离保证。
- 问题操作提交的是**问题版本**，不能使用页面版本。处理任务必须携带 `idempotency_key`；同键同请求可复用，同键不同请求返回 409。`body.recheck_uncertain=true` 时只能选择 `manual_edit`。
- `event_id` 表示请求受理；事件完成也不能代替正式正文与最终问题状态核对。

## 仍未提供的能力

0.0.9 的公开 Wiki 契约没有原生历史回滚、取消编译或“每次修订必须经人工审批后发布”的保证。本平台不提供虚构 rollback/publish/approve 接口，不把旧正文重新 PUT 说成原生回滚，也不把文档入库评审当作 Wiki 修订发布审批。

内容问题任务是针对可见问题提交处理决定，不等于全库候选修订审批队列。阈值设置、关闭重写自动入库或暂停新编译均不能替代强制人工发布。第三方编译器的来源、目录和链接写入及云端隔离仍需独立验证，见[编译器准入核查](contextdb-wiki-compiler-readiness.md)。

## 本轮实际验证

2026-11-14 仅对用户指定业务库执行 GET，并通过数据库只读事务确认 `default` 的 Wiki 绑定与该库一致；没有业务库写入、编译控制或策略变更。

| 只读检查 | 实际结果 |
| --- | --- |
| 索引 `limit=1` | HTTP 200；entity 总数 4、concept 总数 73；两组各返回 1 项并有下一页游标。这是本次读取快照，不是固定产品数量。 |
| 根层树 `limit=2` | HTTP 200；2 项并有下一页游标 |
| 编译记录 `limit=1` | HTTP 200；返回记录、游标、`summary` 和 `wiki_compile_paused` |
| 问题列表 `limit=1` | HTTP 200；本次可见问题数为 0，未取得真实问题详情或处置任务样例 |
| 索引页正式详情与修订 | HTTP 200；正文可读、状态 active；修订列表返回 2 项并有游标 |
| 真实修订差异 | HTTP 200；返回行差异及新增/删除计数，样例未截断 |

同日后续验收时，原库详情和索引返回 `COMMON_BAD_REQUEST: knowledge base not found`。用户随后确认已删除原默认 Wiki 库。本地 `default` 映射仍指向原 ID，平台没有自动重建或换绑现有图谱库；先前成功的 GET 记录保留其时间范围，不能作为删除后仍可用的证明。后续写验证仅使用新建隔离库。

为此补充目标库可用性处理：只有明确的官方不存在响应才标记 `missing`；权限拒绝和网络错误分别保留为 `forbidden/unknown`，不当作删除。缺失目标不再逐篇读取旧库文档，原投递回执及历史库 ID 保留；重新关联或提交恢复仍需明确操作，有在途同步时阻止换绑。页面读取不会自动重建目标库。

随后用户或并行任务恢复了默认 Wiki。最终以有效平台会话只读 GET 运行中 8000 服务，`default.targets.wiki.status=available`，新库 ID 为 `61055604-801a-4a28-9fcb-f8eb79d47f7e`；原删除库 ID 仍在 `previous_knowledge_base_ids`。独立图谱目标仍为 `available`，官方详情 HTTP 200。当前已不再处于缺失状态；missing、恢复及历史别名边界由隔离回归测试覆盖，不能把此前不可用快照当成当前状态。

读取只记录可用性、字段、计数和游标是否存在，没有保存密钥、正文、来源引用内容或预签名地址。两个抽样页的 links/backlinks 为空，不能据此验证非空链接的全部字段形状。

后端离线与隔离 PostgreSQL 测试：

```bash
.venv/bin/pytest -q tests/test_contextdb_client.py tests/test_contextdb_probe.py tests/test_knowledge_api.py tests/test_platform.py
```

本轮实际结果 **81 passed**，覆盖参数与游标、CAS、写请求字段、幂等参数透传、只读角色、错误方法、未知路径及 400/403/409/503 错误传播。代理权限和请求形状使用替身测试，不以其代替真实云端或浏览器流程验收。

随后加入云端目标缺失、恢复、旧投递回执和历史别名处理，相关后端回归扩展为 **161 passed**。测试仍使用官方契约替身及独立测试数据库/schema，不修改真实业务数据库或调用业务库写接口。

随后按用户授权，新建独立临时 Wiki 库直接验证 0.0.9 DATA API，未绑定业务空间，也未修改现有图谱库。真实通过的操作包括：

- 创建两个目录和概念页，核对可读正式正文；修改正文并回读，旧版本再次提交被 HTTP 409 拒绝。
- 读取修订和真实差异；目录与页面重命名、携带自身及目标目录版本移动，回读名称和父节点核对。
- 读取索引、子树游标和编译统计；暂停/恢复后回读 `wiki_compile_paused`。
- 归档前确认搜索命中、归档后确认不再命中；删除页面后详情返回 HTTP 400；删除空目录后确认其退出对应树。
- 对有 `event_id` 的操作查询到成功终态后再读资源；问题列表为空，仅验证读取，未制造冲突或真实调用问题处置写接口。

最终临时报告为 `/tmp/contextdb-wiki-ui-smoke.json`，结果 `passed`，临时库已删除且原有可读库 ID 集合保留。报告只保存请求方法、路径、HTTP 状态、字段名及检查结果，不保存正文和凭据。首轮自检误将归档理解为 `published=false`，已保留 `/tmp/contextdb-wiki-ui-smoke-first.json`；按官方“退出检索、保留历史”语义修正后重测通过。实测归档详情仍可读，`published=true/run_state=archived`，不能把归档与来源失效混为一谈。

另建未绑定任何业务空间的临时 Wiki 库，以平台直接知识库路径完成真实浏览器验收：索引/目录、深链接、草稿切页保护、保存后正文逐字核对、修订差异、编译暂停/恢复状态回读及问题空集均通过。该浏览器库及包含的页面/目录已精确删除，`/tmp/contextdb-wiki-browser-fixture.json` 记录 `cleanup=deleted`，并确认既有图谱库 ID 仍在；没有按初始资源列表差集清理其他新库。

最终前端全量测试 **2866 passed / 1 skipped / 0 failed**，类型检查与生产构建通过；后端相关回归 **161 passed**。这些结果不扩大以下真实冲突验证范围。

恢复后的默认空间再次完成只读浏览器验收：按分组游标加载到末页，实际呈现 **7/7 个实体、63/63 个概念**，超过 50 页仍可完整浏览。

未刻意生成真实内容冲突，因此问题证据详情和问题处理任务写操作仍仅由替身覆盖，不能由空集页面或普通编辑验收推定通过。

## 官方来源与历史证据

- [0.0.9 Wiki 阅读与导航](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-read)
- [0.0.9 Wiki 编辑与修订差异](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-edit)
- [0.0.9 Wiki 目录与页面整理](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-organize)
- [0.0.9 Wiki 编译控制](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-compile)
- [0.0.9 Wiki 内容问题处理](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-resolve)

[旧审计 JSON](reports/contextdb-wiki-audit.json)、[旧能力报告](reports/contextdb-capabilities.json)和[旧编译器准入 JSON](reports/contextdb-wiki-compiler-readiness.json)保留原始时间及响应，不覆写为本轮结果。它们基于 0.0.8 的“未声明”或“未公开”描述不能覆盖以上 0.0.9 契约；旧路径 `/wiki/pages/revisions`、`/wiki/revisions/pending` 被拒绝，也不代表新的 `/wiki/revisions/diff` 等正确路径不可用。
