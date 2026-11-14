# ContextDB 能力与本项目需求对照

核对日期：2026-11-14（Asia/Shanghai）。核心需求可由 ContextDB 现有 API 与官方 MCP 满足：上传或采集资料后，使用官方治理检测与评审；源资料的歧义通过 `edited_content` 修订并重新入库，Wiki 主题页的表述通过当前页带版本编辑修复，再由 deepagents 调用官方 MCP 回答并引用来源。两种修订分别保存，不宣称 Wiki 编辑会回写源文档或采集原件。0.0.9 已公开 Wiki 阅读、编辑、差异、整理、编译控制和问题处置契约；原生候选审批、历史回滚与强制人工发布仍不在本平台支持范围内。

本地仅保留已有采集器、WeKnora REST/SSE 适配、任务编排、权限及会话状态；解析、切片、知识检索、语义治理、Wiki 编译和图谱交给 ContextDB。Agent 使用 LangChain 官方 deepagents，知识访问直接装载 ContextDB 官方 MCP，界面继续适配已经复制的 WeKnora 前端。

## 依据与验证范围

此前核查下载的是 [ContextDB 0.0.8 官方文档](https://g.alicdn.com/rdsai/contextdb-doc/0.0.8/contextdb-documentation.html#/api-overview)，HTML SHA256 为 `beb049f44247f13b5980987f51c73259dc64bdf981a2a32c0e1d86dcdff6d34f`；其中没有 Wiki API 专章属于旧版材料事实。当前 Wiki 契约以 [0.0.9 阅读与导航](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-read)及 [Wiki 专项说明](contextdb-wiki-support.md)为准，不能沿用“未公开 Wiki API”的旧结论。其他领域的旧版核查与实测范围不因此扩大。

分析阶段使用官方文档与代码静态对照；随后本轮实施已恢复真实云端联调，用独立临时资源验证平台文件上传、单 Wiki 投递、官方人工修订、修订正文检索、Wiki 编译及版本冲突，结果与清理记录见 [本轮验证记录](../guides/governance-validation.md)。此前报告保留为历史证据，不能替代本轮结果： [API 契约报告](contextdb-capabilities.json)、[双库链路报告](contextdb-pipeline-smoke.json)及 [Wiki 边界核查](contextdb-wiki-support.md)。

本轮 0.0.9 Wiki 及云端目标删除/恢复相关后端回归 **161 项通过**。独立临时库的官方 API 写入和真实浏览器阅读/编辑/差异/编译控制已分别验收并清理，现有图谱库保留；用户删除的原默认 Wiki 后续已恢复新目标，旧库 ID 及投递回执作为历史保留。当前读取不自动建库或逐篇访问已删除库，真实内容问题写入仍无冲突案例，详见 [Wiki 支持说明](contextdb-wiki-support.md)。

## 核心链路与职责

| 用户需求 | ContextDB 可复用能力 | 本项目适配与当前文件 |
| --- | --- | --- |
| 上传各类文件 | 官方 `POST /v1/knowledge/files`，由云端解析、评审与入库；大文件提供初始化、分片、完成及中止接口 | [文件来源](../../crawlers/file.py)、[采集 API](../../webapi/platform.py)、[同步投递](../../governance/contextdb_sync.py)保留原件、来源身份及提交记录；[REST 客户端](../../integrations/contextdb/client.py)调用官方接口 |
| 爬取已有文档系统 | 官方云端 Connector 支持指定平台；未覆盖的系统继续用本项目采集器 | [ShowDoc](../../crawlers/showdoc.py)、[CYB](../../crawlers/cyb.py)、[天瞳](../../crawlers/tiantong.py)、[通用 Web](../../crawlers/web.py)负责登录与取得原资料，平台链路不再本地重新解析和语义分块 |
| 检测质量、矛盾及知识冲突 | 官方 `knowledge/reviews`、`reviews/detail`、`reviews/action`、`reviews/resolve-conflicts` 和 `review_settings` | [知识 API](../../webapi/knowledge.py)与 [治理界面](../../frontend/src/views/KnowledgeView.vue)展示官方诊断、重写稿、冲突及人工决策，不自行计算治理结论 |
| 在线修订并继续入库 | 官方评审动作 `accept_rewrite` 接受 `edited_content`；文本和文件分别有官方 PUT 更新通道 | 编辑器提交完整正文，保留官方文档 ID 和状态；文件不能用文本接口替换，二进制原件不能按 UTF-8 当作评审正文 |
| Wiki 浏览与编辑 | 0.0.9 公开索引、树、详情、带版本编辑、修订差异及整理接口 | [原生 Wiki API](../../frontend/src/api/contextdbWiki.ts)、[官方转发](../../webapi/contextdb.py)、[ContextDBWiki](../../frontend/src/views/knowledge/wiki/ContextDBWiki.vue)读取真实版本、使用官方游标并保留冲突草稿；旧 WeKnora Wiki API 与组件已移除 |
| 基于知识库问答与来源定位 | 官方 MCP `knowledge.search`、`knowledge.get_document`、图谱和来源切片工具；`knowledge.wiki_search` 导航 Wiki | [deepagents 构建](../../agent/graph.py)、[MCP 装载](../../agent/tools.py)、[执行服务](../../agent/service.py)、[Agent API](../../webapi/agent.py)及 WeKnora 对话组件负责交互、流式事件和出处展示 |

公开接口依据：[上传文件](https://g.alicdn.com/rdsai/contextdb-doc/0.0.8/contextdb-documentation.html#/api-uploadKnowledgeFile)、[分片上传](https://g.alicdn.com/rdsai/contextdb-doc/0.0.8/contextdb-documentation.html#/api-initializeKnowledgeFileUpload)、[评审详情](https://g.alicdn.com/rdsai/contextdb-doc/0.0.8/contextdb-documentation.html#/api-getKnowledgeReview)、[评审动作](https://g.alicdn.com/rdsai/contextdb-doc/0.0.8/contextdb-documentation.html#/api-performKnowledgeReviewAction)、[冲突处理](https://g.alicdn.com/rdsai/contextdb-doc/0.0.8/contextdb-documentation.html#/api-resolveKnowledgeReviewConflicts)、[评审设置](https://g.alicdn.com/rdsai/contextdb-doc/0.0.8/contextdb-documentation.html#/api-updateKnowledgeBaseReviewSettings)、[MCP 接入](https://g.alicdn.com/rdsai/contextdb-doc/0.0.8/contextdb-documentation.html#/integrate-mcp)。

## 来源接入优先复用官方能力

[官方数据导入](https://g.alicdn.com/rdsai/contextdb-doc/0.0.8/contextdb-documentation.html#/data-import-overview)覆盖钉钉、飞书、乐享、语雀、企业微信和腾讯文档，已有云端运行、持续计划、来源变更检查、跨任务来源复用及排除清单。接入这些平台时优先使用官方 Connector，不另写同类爬虫或同步引擎。各平台仍有表格、附件和格式限制，不能将支持“文档平台”理解为支持其中全部资料类型。

ShowDoc、CYB、天瞳及任意登录网站未出现在该支持表中，保留当前采集器有实际必要。采集结果通过统一文件接口交给 ContextDB，来源 ID、内容哈希和投递状态用于避免重复提交及覆盖新资料，不承担云端知识治理。

云端 Connector 的产品支持不等于本平台已经接通其管理接口：公开目录未给出完整导入任务 CRUD 契约；项目的 Agent 也明确只装载 `knowledge.*`，没有启用 `contextdb_connectors__*`。取得可用 Schema 与权限后再决定是否增加入口，不猜测控制台内部 API。

上传与治理支持范围分别展示：[官方使用限制](https://g.alicdn.com/rdsai/contextdb-doc/0.0.8/contextdb-documentation.html#/usage-limits)明确知识评审格式为 TXT、Markdown、PDF、DOC、DOCX。HTML、图片、音视频、PPT、Excel 等虽可使用官方解析和检索，不据此承诺治理；本期按已确认范围提示，不增加本地格式转换或治理算法。

## 治理与 Wiki 修复的能力边界

文档评审和 Wiki 修订是不同阶段，分别保存修订结果。评审解决入库资料的逻辑、噪音、内部矛盾和已有知识冲突；`resolve-conflicts` 保存 `[{conflict_id, resolution}]` 决策草稿，最终仍需评审动作。`accept_rewrite` 通过 `edited_content` 提交源资料的人工全文修订并重新入库，之后必须等待实际入库终态，不能将 HTTP 200 或 `processing` 当成完成。Wiki 带版本编辑修复主题页本身的表述，不表示源文档或采集原件同时被改写。

评审编辑的正文来自官方 `rewritten_content` 或 `reviews/detail?content_page=...` 的完整原文分页；原件下载可能是 PDF、Word 等二进制。普通正文更新也要区分 [`PUT /v1/knowledge/documents`](https://g.alicdn.com/rdsai/contextdb-doc/0.0.8/contextdb-documentation.html#/api-updateKnowledgeDocument)与 [`PUT /v1/knowledge/files`](https://g.alicdn.com/rdsai/contextdb-doc/0.0.8/contextdb-documentation.html#/api-updateKnowledgeFile)，不能按文件扩展名绕过 `source_type` 约束。元数据单独使用 [`PUT /v1/knowledge/documents/metadata`](https://g.alicdn.com/rdsai/contextdb-doc/0.0.8/contextdb-documentation.html#/api-updateKnowledgeDocumentMetadata)，不为状态修改重传正文。

[0.0.9 Wiki 编辑](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-edit)、[编译控制](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-compile)与[问题处理](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-resolve)已经给出可接入接口。当前边界如下：

| 能力 | 证据等级 | 实施结论 |
| --- | --- | --- |
| Wiki 模式、自动编译、页面阅读维护 | 官方产品说明；当前页读写另有项目既有实测 | 复用官方服务。Wiki 与 graph 互斥，现有业务空间通过 Wiki 库及可选图谱库聚合，不在本地重建 |
| Wiki 索引、目录树、详情、人工创建和编辑 | 0.0.9 公开 DATA API；项目有真实读取及既有独立写入实测 | 原生前端与精确方法代理；目录分页不依赖搜索上限，编辑保留 CAS 和正文回读 |
| 修订历史、正文差异 | 0.0.9 公开 `revisions`、`revisions/diff`；真实修订差异 GET 已验证 | 修订 ID 比较及 800 行截断提示，不当作原生回滚或全库审批队列 |
| 目录/页面整理、编译控制、内容问题处置 | 0.0.9 公开 actions、tasks、事件/任务读取接口 | 接入官方参数、版本与幂等键；pause 只阻止新编译，不证明在途任务已隔离 |
| 全库候选审批、原生回滚、所有入口强制人工发布 | 未取得相应公开可执行契约或覆盖保证 | 不实现伪回滚/本地发布门禁，不用问题处理或文档评审动作替代；旧正文 PUT 只是新编辑 |

具体既有响应与限制见 [Wiki 专项核查](contextdb-wiki-support.md)。

## deepagents、官方 MCP 与 WeKnora

Agent Harness 直接使用 `deepagents.create_deep_agent`，由官方 LangGraph PostgreSQL checkpointer 保存执行状态；本项目只维护账号、会话归属、运行记录及来源映射。知识问答通过 `langchain-mcp-adapters` 装载 `POST /v1/mcp` 官方工具，使用当前成员的 `X-API-Key`，按平台角色裁剪写操作并限制会话所选知识库。知识写工具采用 deepagents 中断和批准/拒绝恢复，不再开发一套 Agent 调度循环，也不以自建 REST 检索工具绕开 MCP。

[官方 MCP 协议](https://g.alicdn.com/rdsai/contextdb-doc/0.0.8/contextdb-documentation.html#/mcp-reference)要求按工具发现结果构造参数；工具集合受密钥权限影响，HTTP 200 也可能包含工具业务错误。API Key 绑定工作空间和成员，平台身份或提示词不能替代服务端权限。知识答案使用官方文档/切片证据，Wiki 与图谱合成结果保留来源，不编造文档引用。

前端已包含 WeKnora `0.9.0` 源码，固定提交为 `cbdcebabf48c5ee2d6868b370326aa8341703f62`，记录见 [UPSTREAM.json](../../frontend/UPSTREAM.json)，上游许可保留在 [UPSTREAM-LICENSE](../../frontend/UPSTREAM-LICENSE)。继续复用现有壳、知识库、聊天、工具过程和引用预览组件；Wiki 改用 [ContextDB 原生接口](../../frontend/src/api/contextdbWiki.ts)和组件，移除旧 WeKnora Wiki API。其他适配沿用 [ContextDB API](../../frontend/src/api/contextdb.ts)与 [平台 API](../../frontend/src/api/backend.ts)，不复制 WeKnora 后端及其解析、向量、RAG 或 Agent 引擎。

## 不再单独实现与待验证项

不增加本地向量库、全文知识库、语义切片、Embedding、重排、知识冲突评分、自动重写、Wiki 编译或图谱抽取。上述能力已由官方提供；PostgreSQL 和原件归档用于应用运行及采集恢复。既有独立爬虫 CLI 的离线导出不因此扩展成平台的第二套知识处理链路。

当前必要适配是来源采集、官方接口转发、权限绑定、幂等投递记录、编辑器、官方状态展示、对话恢复和引用定位。官方 API 的格式与大小范围不等于平台入口已支持相同上限：现平台一次50文件、总请求100 MB，超出范围的支持需单独接通官方分片流程，不能宣称已经支持任意大小的音视频。

真实上传、评审全文修订、Wiki CAS 编辑及 deepagents→官方 MCP→引用原文分别记录验收结果；未执行项不得由本地模拟测试推定通过。Wiki 修订差异及问题处置已有 0.0.9 契约；未提供的原生回滚和强制人工发布继续保持明确边界，当前验证见 [Wiki 支持说明](contextdb-wiki-support.md)。
