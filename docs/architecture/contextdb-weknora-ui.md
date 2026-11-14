# ContextDB Wiki 与 WeKnora 界面的职责

更新日期：2026-11-14（Asia/Shanghai）。平台继续复用 WeKnora 的应用壳、TDesign 组件和聊天界面；Wiki 已切换为按 **ContextDB 0.0.9 DATA API** 实现的页面，不再把 WeKnora 的 Wiki 后端模型套到 ContextDB 上。

## 来源与保留范围

前端来源由 [UPSTREAM.json](../../frontend/UPSTREAM.json)记录，固定提交为 [`cbdcebabf48c5ee2d6868b370326aa8341703f62`](https://github.com/Tencent/WeKnora/commit/cbdcebabf48c5ee2d6868b370326aa8341703f62)；[上游许可](../../frontend/UPSTREAM-LICENSE)继续保留。本轮更换 Wiki 界面不改变其他现有组件的来源声明。

| 当前文件 | 职责 |
| --- | --- |
| [ContextDBWiki.vue](../../frontend/src/views/knowledge/wiki/ContextDBWiki.vue) | 索引概览、正式正文、搜索、来源、页面链接、编辑与目录/页面整理 |
| [ContextDBWikiDirectory.vue](../../frontend/src/views/knowledge/wiki/ContextDBWikiDirectory.vue) | 按官方父节点及游标展开目录和主题页；整理操作的目标目录选择 |
| [ContextDBWikiRevisions.vue](../../frontend/src/views/knowledge/wiki/ContextDBWikiRevisions.vue) | 指定页面的修订列表及官方正文差异 |
| [ContextDBWikiCompile.vue](../../frontend/src/views/knowledge/wiki/ContextDBWikiCompile.vue) | 编译统计、来源状态、暂停/恢复、定向重编和失败重试 |
| [ContextDBWikiIssues.vue](../../frontend/src/views/knowledge/wiki/ContextDBWikiIssues.vue) | 可见问题、来源证据、处理决定及异步任务结果 |
| [contextdbWiki.ts](../../frontend/src/api/contextdbWiki.ts) | 与 0.0.9 字段和路径对齐的前端接口；不缓存第二份权威知识状态 |
| [contextdb.py](../../webapi/contextdb.py) | 当前成员鉴权后的精确路径/HTTP 方法转发 |

[ContextDBKnowledge.vue](../../frontend/src/views/knowledge/ContextDBKnowledge.vue)与 [KnowledgeBase.vue](../../frontend/src/views/knowledge/KnowledgeBase.vue)装配原生 Wiki 组件。正文阅读复用平台已有 Markdown 组件；页面 ID、版本、游标和状态均使用 ContextDB 的真实值。

旧 `WikiBrowser.vue`、`WikiFolderActions.vue`、`WikiRevisionDrawer.vue`、`api/wiki/index.ts` 及其专用目录/反链兼容逻辑和测试已清理。旧 `WikiView.vue`、`api/backend.ts` 中的 `/api/wiki/...` 调用、后端 `webapi/wiki.py` 以及 `/api/contextdb/wiki-search` 桥接一并移除。平台 Wiki 不再请求上游 `/api/v1/knowledgebase/{kbId}/wiki/...`，也不再使用最多 50 条搜索结果代替完整目录。

Agent 保留官方 MCP `knowledge.wiki_search`。前端迁移为 REST 搜索并不删除或重新包装 Agent 的官方知识工具；旧引用中的 slug 通过新接口在当前知识库中定位，不能据此跳过成员权限或转向 WeKnora 后端。

## 当前行为与边界

- 索引按 entity、concept、synthesis、comparison 分组并逐组分页；目录按根层/直接子项及游标展开。搜索最多 50 项，只用于导航，不推算全库数量。
- 页面详情决定正式正文可读性。`published=false` 不展示缓存旧正文；相关页与反链显示官方截断状态，来源操作继续打开原始文档。
- 人工编辑使用 `expected_version`。409 时保留草稿、读取最新版本供手工合并；受理后核对正文，不仅依据版本号提示成功。
- 创建与整理使用官方页面、目录和事件 ID。移动携带自身及目标目录的版本；归档保留历史，删除不可恢复，空目录删除与主题页删除使用各自接口。
- 版本历史使用 `revision_id` 和可选 `base_revision_id` 调用官方 diff。超过 800 行的截断结果明确提示，不能称作完整历史全文；没有原生历史回滚入口。
- 编译暂停只影响新摄取触发的编译，不停止在途任务；恢复不自动补派积压。状态及事件回读用于核对受理结果，不能保证第三方编译器已隔离。
- 内容问题处理使用问题版本和幂等键。证据不确定时只接受人工编辑；提交事件不等于正文已经发布或问题已经关闭。

内容问题处理不是全库候选修订审批，也没有所有入口强制人工发布的原生保证。文档入库评审与 Wiki 修订发布分属不同阶段，不能相互替代。完整公开契约与测试边界见 [Wiki 支持说明](contextdb-wiki-support.md)。

## 页面链接与实体图谱

Wiki 的 links/backlinks 表示页面之间的链接。当前界面按官方页面详情导航，并保留最多 200 项及截断提示；没有把这些局部链接拼成“完整全库 Wiki 图”的承诺。

[ContextDBGraph.vue](../../frontend/src/views/knowledge/ContextDBGraph.vue)展示独立图谱库的实体关系，数据来自 `knowledge/graph-visual`、`entities/detail`、`entity-relations/detail` 和 `entities/chunks`。它继续复用 [wikiGraphLayout.ts](../../frontend/src/views/knowledge/wiki/wikiGraphLayout.ts)中的布局算法，因此该文件和相应测试保留。保留布局代码不表示保留旧 WeKnora Wiki 服务或其页面图 API。

ContextDB 的 Wiki 与 graph 是不同建库模式。业务空间关联 Wiki 库及可选图谱库；两次资料投递具有独立的入库和治理状态，Wiki 人工修订不会回写原始资料、采集快照或图谱库。

## 验证边界

本轮已核对 0.0.9 官方[阅读](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-read)、[编辑](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-edit)、[整理](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-organize)、[编译控制](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-compile)和[问题处理](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-resolve)文档。业务库的初次 GET 核验、后端替身测试与后续隔离资源验证分别记录在 [Wiki 支持说明](contextdb-wiki-support.md)，不相互代替。

用户曾删除原默认 Wiki 库，随后由用户或并行任务恢复新库。目标缺失时，界面依据服务端 `missing/forbidden/unknown` 分别提示；读取页面不触发自动建库，不将图谱库当作 Wiki 替代。恢复后保留旧库 ID 历史，当前页面使用新的可用目标；不逐篇读取已删除库的旧文档。

本轮另用未绑定业务空间的临时真实 Wiki 库完成浏览器验收：索引/目录、深链接、草稿切页保护、保存后正文逐字核对、修订 diff、编译暂停/恢复的真实状态及问题空集均通过。验收库及其页/目录已精确删除，现有图谱库 ID 保留。后端代理与缺失恢复等相关回归 **161 项通过**。原业务库的删除前读取、隔离 API 写验证、浏览器交互验证分别保留证据，不混为同一环境的全链路结果。

最终前端全量测试 **2866 通过、1 跳过、0 失败**，Vue 类型检查和生产构建通过。

未在真实业务数据上生成内容冲突，问题证据与处理任务的所有异步失败分支尚未完成云端验收；替身测试不替代这一边界。
