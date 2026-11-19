# ContextDB Wiki 与 WeKnora 界面的职责

更新日期：2026-11-16（Asia/Shanghai）。平台继续复用 WeKnora 的应用壳、TDesign 组件、现有卡片和聊天界面；知识库相关页面按官方控制台的排版、交互与文案调整，数据使用 **ContextDB 0.0.9 DATA API**。不引入另一套前端框架，不把 WeKnora 的 Wiki 后端模型套到 ContextDB 上。

## 来源与保留范围

前端来源由 [UPSTREAM.json](../../frontend/UPSTREAM.json)记录，固定提交为 [`cbdcebabf48c5ee2d6868b370326aa8341703f62`](https://github.com/Tencent/WeKnora/commit/cbdcebabf48c5ee2d6868b370326aa8341703f62)；[上游许可](../../frontend/UPSTREAM-LICENSE)继续保留。本轮更换 Wiki 界面不改变其他现有组件的来源声明。

| 当前文件 | 职责 |
| --- | --- |
| [ContextDBKnowledge.vue](../../frontend/src/views/knowledge/ContextDBKnowledge.vue) | 以真实知识库 ID 装配文件、知识 Wiki、知识图谱 |
| [ContextDBDocuments.vue](../../frontend/src/views/knowledge/ContextDBDocuments.vue) | 官方文件树、排序、预览、元数据、上传和节点操作 |
| [ContextDBWiki.vue](../../frontend/src/views/knowledge/wiki/ContextDBWiki.vue) | 索引概览、正式正文、搜索、来源、页面链接、编辑与目录/页面整理 |
| [ContextDBWikiDirectory.vue](../../frontend/src/views/knowledge/wiki/ContextDBWikiDirectory.vue) | 按官方父节点及游标展开目录和主题页；整理操作的目标目录选择 |
| [ContextDBWikiRevisions.vue](../../frontend/src/views/knowledge/wiki/ContextDBWikiRevisions.vue) | 指定页面的修订列表及官方正文差异 |
| [ContextDBWikiCompile.vue](../../frontend/src/views/knowledge/wiki/ContextDBWikiCompile.vue) | 编译统计、来源状态、暂停/恢复、定向重编和失败重试 |
| [ContextDBWikiIssues.vue](../../frontend/src/views/knowledge/wiki/ContextDBWikiIssues.vue) | 可见问题、来源证据、处理决定及异步任务结果 |
| [contextdbWiki.ts](../../frontend/src/api/contextdbWiki.ts) | 与 0.0.9 字段和路径对齐的前端接口；不缓存第二份权威知识状态 |
| [ContextDBGraphCanvas.vue](../../frontend/src/views/knowledge/ContextDBGraphCanvas.vue) | 复用项目画布组件呈现官方实体、关系数据及现有缩放、平移、定位交互 |
| [ContextDBPolicies.vue](../../frontend/src/views/knowledge/ContextDBPolicies.vue) | 策略与模板整页、知识库选择与管理权限传递 |
| [ContextDBReviewSettings.vue](../../frontend/src/views/knowledge/ContextDBReviewSettings.vue) | 官方四项评审策略配置、仅提交改动字段与保存后回读 |
| [ContextDBTemplates.vue](../../frontend/src/views/knowledge/ContextDBTemplates.vue) | 官方重写模板列表、详情、章节编辑与 Markdown 预览 |
| [contextdb.py](../../webapi/contextdb.py) | 当前成员鉴权后的官方端点转发、知识库生命周期门禁及同库写锁 |

`ContextDBKnowledge.vue` 与 [KnowledgeBase.vue](../../frontend/src/views/knowledge/KnowledgeBase.vue)装配原生 Wiki 组件。Wiki 内部的“Wiki 阅读”和“Wiki 编译记录”共用知识库上下文，编译区域复用现有编译组件；正文阅读与模板预览复用已有 `DocMarkdown`。页面 ID、版本、游标和状态均使用 ContextDB 的真实值。

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

公开 Wiki 内容问题、修订与整理 API 继续保留。官方主导航没有展示某项能力，不能单凭这一点删除该数据能力；兼容深链与已有来源引用也不能因此指向其他知识库。

内容问题处理不是全库候选修订审批，也没有所有入口强制人工发布的原生保证。文档入库评审与 Wiki 修订发布分属不同阶段，不能相互替代。完整公开契约与测试边界见 [Wiki 支持说明](contextdb-wiki-support.md)。

## 页面链接与实体图谱

Wiki 的 links/backlinks 表示页面之间的链接。当前界面按官方页面详情导航，并保留最多 200 项及截断提示；没有把这些局部链接拼成“完整全库 Wiki 图”的承诺。

[ContextDBGraph.vue](../../frontend/src/views/knowledge/ContextDBGraph.vue)展示所选图谱库的实体关系，数据来自 `knowledge/graph-visual`、`entities/detail`、`entity-relations/detail` 和 `entities/chunks`，并提供查看图谱／实体管理及实体、关系详情。它复用项目已有 `ContextDBGraphCanvas.vue`，已不依赖 `wikiGraphLayout.ts`，不再维持用于 Wiki 页面链接的另一套布局逻辑。已展示节点、关系数量与查询范围总量分开显示，不把局部画布描述为全库完整图谱。

ContextDB 的 Wiki 与 graph 不能在同一库同时开启。创建弹窗默认 Wiki、关闭知识评审；平台不再追加 `0.85` 阈值或固定重写策略，已有配置以官方回读为准。Wiki 模式仅建库时选择；非 Wiki 库可通过官方 `PUT /v1/knowledge/knowledge_bases` 更新 `graph_enabled`，当前 UI 不增加未经实查确认的图谱开关控件。

一个采集范围固定关联一个真实知识库 ID。旧 Wiki、图谱库各自保留其真实 ID 和历史回执，不继续以双目标采集作为新任务的模型。非 Wiki 库的图谱开关变化不会替换目标 ID、重复投递同一来源或让既有回执失效。Wiki 人工修订不会回写采集原件或快照，也不会将修改写入另一个图谱库。

## 评审、策略与模板

知识评审使用官方生命周期、分数排序、分页及单项／批量动作，不保留另一套本地评审队列。“我的评审”省略知识库过滤，“按知识库查看”使用 `knowledge_base_id`。控制台的成员切换属于控制台能力：公开 DATA 0.0.9 未提供 `user_id`、`member_id`、`only_mine` 筛选或切换调用身份接口，因此页面只显示当前 API Key 所属成员并禁用切换，不提交虚构筛选参数。

评审策略与重写模板在独立的“策略与模板”页面中切换，写操作要求知识库管理权限。策略只展示启用知识评审、重写文件自动入库、启用知识重写、自动入库阈值四项；没有将 API 中的其他配置扩展成额外可见控件。更新只发送编辑过的字段，并在保存前后回读。接口不提供版本 CAS，保存前检查不能保证消除之后的并发窗口。

重写模板继续使用既有 TDesign 表单和 `DocMarkdown`，新建弹窗包含官方默认三章节、章节级别、撰写指引及左右编辑／预览区域。编辑读取单篇模板详情；只读门禁、跨库迟到响应保护和重复提交保护不依赖按钮是否隐藏。“AI帮写”缺少已确认的 DATA API，不新增模拟接口或另一个 Agent。

## 验证边界

本轮核对 0.0.9 官方[阅读](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-read)、[编辑](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-edit)、[整理](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-organize)、[编译控制](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-compile)和[问题处理](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-resolve)契约。既有业务库 GET、隔离资源写入和替身验证的历史记录见 [Wiki 支持说明](contextdb-wiki-support.md)；本次官方 UI 对齐未重演云端写入流程，不能混称为本轮全链路验收。

目标缺失时，界面依据服务端 `missing/forbidden/unknown` 分别提示；读取页面不触发自动建库，不将图谱库当作 Wiki 替代，也不按相同名称重绑另一个 ID。采集绑定、来源归档、快照、既有云端知识库与历史回执保留，本轮没有因清理不符官方的 UI 而删除这些数据。

最近一次后端全量结果为 **822 通过、15 跳过**；上次前端全量为 **2876 通过、1 跳过、1 失败**。失败为 pinned Agent UI 对 `docInfo.vue` 的既有固定源码 hash 校验，本任务没有修改该组件或放宽校验。最后调整后，Documents／Metadata／知识评审／Tasks／KnowledgeEntry／styleGuard 的最终相关回归 **94／94 通过**，类型检查与生产构建均 exit 0，构建耗时 38.32 s；没有将这些相关检查描述成重新执行前端全量。API、数据库与 Worker 健康检查均为 `true`。

最终调整修复了单条／批量评审请求在途时分页锁死、编辑稿期间的成员刷新保护，以及 Tasks 旧处理进度入口；任务现在跳转至“查看知识库”。文件列表总数不再重复显示，元数据编辑空态和限制说明按无痕官方页面逐字复核；上述 94 项回归在这些修改之后执行。

浏览器阅读与交互验收已完成：Wiki 阅读、编辑打开后取消、历史 diff、编译来源至 Word 原文；文件原文与 Chunks；本次图谱查询范围的 67 个实体／76 条关系、“采购入库单”的 11 条关联关系／3 个来源片段及来源文件跳转；真实 3 条待人工评审记录、批量勾选与菜单但未提交、拒绝打开后取消、失败状态空态；策略四字段未改动时禁用保存、模板新建打开后取消；创建知识库默认 Wiki 与评审关闭、上传弹窗 1 B～2 MB 及默认评审状态、元数据只读查看与空数据编辑取消。本次采集的浏览器 console error 列表为 `[]`。

截图位于 [output/verification/contextdb-official-ui-20261116](../../output/verification/contextdb-official-ui-20261116/)，包含 `files.jpg`、`graph.jpg`、`review.jpg`、`wiki-read.jpg`、`wiki-compile.jpg`、`wiki-edit.jpg`、`wiki-history.jpg`、`review-settings.jpg`、`rewrite-template.jpg`、`create-knowledge-base.jpg`、`upload.jpg`、`metadata.jpg`。本轮没有提交云端写操作，也没有执行自动像素差异全通过的验证；上述结果不代表真实保存、删除、异步编译或邀测能力的写入验收。

未在本轮真实业务数据上生成或处置 Wiki 内容冲突，也未执行邀测本体 API、生产切换或并发负载验收；替身测试不替代这些边界。完整当前对齐与数据流记录见 [知识库与知识评审对齐记录](../guides/contextdb-knowledge-alignment-20261116.md)。
