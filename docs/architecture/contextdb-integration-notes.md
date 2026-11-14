> 历史探测记录：其中“零 PostgreSQL”、云端任务/checkpoint、单 Wiki 库及猜测版本重试已被替换。当前实现与验证范围以 [agent-platform.md](agent-platform.md) 和机器可读契约报告为准，本文不再作为运行操作指南。

# ContextDB 接入与能力探测结论(Phase 0 定稿)

日期:2026-11-12 · 工作空间「测试」/成员「蒲松林」/ApiKey「default」 · CLI `@aliyunrds/ctxdb@1.1.0` · 域名双通:`https://context-database.aliyuncs.com`(client 默认)与 `https://api.cn-hangzhou.agentcontext.aliyuncs.com`(CLI 数据面,行为一致)。

鉴权(官方):REST 与 MCP 均推荐 `X-API-Key: <ApiKey>` 请求头(`Authorization: Bearer <ApiKey>` 亦可用),每次请求都需认证;工作空间与成员由密钥决定。官方环境变量:`CONTEXTDB_BASE_URL`(client 已沿用)+ `CONTEXTDB_API_KEY`。错误体两种:`{errorCode, errorMessage, requestId, data}`(1003=冲突/版本过期;4006/4007/4008=成员/权限/空间锁定→HTTP 403)与 FastAPI 风格 `{detail: 文本或校验数组}`(同一接口失败时也可能返回 detail);400 也可能表示资源不存在,勿只认 404。

**运行时通道分工**:**平台后端(webapi)→ 官方 REST**;**Agent 知识库访问 → ContextDB MCP(/v1/mcp 原生 knowledge.* 工具,langchain-mcp-adapters 挂载)**;ctxdb CLI 仅开发诊断(安装期 setup/status),不进平台运行时。

官方 API 文档共 154 个接口章节(完整参考已从文档页解出存于 /tmp/ctxdb-api-docs/,核心契约见下表;异步统一走 `GET /v1/event/<event_id>`,状态 PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED)。

## 1. REST 契约(全部实测通过)

| 能力 | 请求 | 语义 |
|---|---|---|
| KB 创建 | `POST /v1/knowledge/knowledge_bases` {name, description?, wiki_enabled?, graph_enabled?, review_enabled?, chunk_size?(默认800), chunk_overlap?(默认120)} | 响应裸 KB 对象(id/status/wiki_enabled/profile_config);**wiki 与 graph 互斥(400)** |
| KB 列表 | `GET /v1/knowledge/knowledge_bases` | `{"knowledge_bases":[...], "total"}` |
| KB 详情 | `GET /v1/knowledge/knowledge_bases/detail?knowledge_base_id=` | 裸 KB 对象 |
| KB 更新 | `PUT /v1/knowledge/knowledge_bases` {knowledge_base_id, name?/description?/graph_enabled?/review_enabled?} | 至少一个字段;不改切片参数 |
| KB 删除 | `DELETE /v1/knowledge/knowledge_bases?knowledge_base_id=` | |
| 文档创建 | `POST /v1/knowledge/documents` {knowledge_base_id, name, text≤200KB, file_path?, metadata?≤32键, mime_type?, review_enabled?} | 响应为**完整文档对象**(键名 `id`/ingest_status/metadata/graph_status...);同 file_path+name=同一逻辑文档,**重复逻辑名 create→1003 冲突「use the corresponding PUT update API」= insert-if-absent(claim 原语成立)**;`.md` 走 Markdown 解析器+图片引用 |
| 文档列表 | `GET /v1/knowledge/documents` query: knowledge_base_id/page/page_size/**metadata_condition=<JSON串>**/with_download_url? | metadata_condition 等值 AND(扁平 {k:v},数组=任一);分页过滤后集合 |
| 文档详情 | `GET /v1/knowledge/documents/detail` query: knowledge_base_id/document_id/with_download_url? | 只返元数据;`with_download_url` 给源文件预签名 URL(≤55min)→**读正文走该 URL** |
| 文档更新 | `PUT /v1/knowledge/documents` {document_id(或逻辑键,互斥), **text(必填)**, metadata?, file_path?} | id 稳定不变;**无 metadata-only 通道**(PATCH/batch 均未声明)→状态翻转=全量替换;触发重 ingest+**新一轮评审**(旧评审 superseded);**同身份 in-flight 上传中→1003「same document upload is in progress」**(并发防护/串行化原语) |
| 批量删除 | `DELETE /v1/knowledge/documents/batch` {knowledge_base_id, **ids**:[...]} | 响应含逐项 success/error;**ingest 未终态(processing/pending_review)的文档不可删**;评审已解决的文档才可删 |
| 检索 | `POST /v1/knowledge/query` {**question**(必填), knowledge_base_ids/names?, document_ids?, knowledge_view: source\|auto\|wiki, metadata_condition?(全运算符 is/is not/contains/empty/>/</>=/<=), top_k≤20(默认6), similarity_threshold?, rerank?, context_token_budget?} | 响应 {chunks, doc_aggs, wiki_items, context_usage, evidence_layer, returned_count, total};wiki_items 为 section 级合成内容(content/revision_id/section_id/source_document_ids 溯源) |
| Wiki 页树 | `GET /v1/knowledge/wiki/pages?knowledge_base_id=&cursor?&limit?` | 返回 **category 结构树**(cursor 分页;项含 page_id/title/slug/page_type/parent_page_id/depth/version);entity 页不在树中 |
| Wiki 页创建 | `POST /v1/knowledge/wiki/pages` {knowledge_base_id, title, content} | 响应 `{page_id, revision_id, version:1, slug:entity/<slug>, page_type:entity, review_status:published, run_state}`;**同 title 再创建→409「identity 已存在」** |
| Wiki 页更新 | `PUT /v1/knowledge/wiki/pages` {knowledge_base_id, page_id, content, **expected_version**} | expected_version=**当前版本**(CAS);成功响应返回**新版本**;不符→403/4033「page version stale」;更新后 review_status=validating(异步) |
| 评审列表 | `GET /v1/knowledge/reviews` query: knowledge_base_id/review_status(pending\|reviewed\|rejected\|superseded) **或** lifecycle_state(pending_human\|auto_accepted\|approved\|rejected\|failed,二者互斥)/decision?/page/page_size | `{data:{reviews:[...]}}`;项含 review_id/document_id/document_name/decision/confidence_score/review_status/lifecycle_state/rewrite_needed/has_conflicts/has_contradictions/human_action/can_approve_review |
| 评审详情 | `GET /v1/knowledge/reviews/detail?review_id=&content_page=` | logic/noise/contradiction/confidence 评分、decision_reason、quality_details(JSON 串:logic_issues/noise_segments)、conflicts、contradictions、original_content{text,page,total_pages,total_chars}(正文前缀文档名)、rewritten_content/rewrite_strategy/rewrite_reason、human_* 审计字段 |
| 评审动作 | `POST /v1/knowledge/reviews/action` {review_id, action, edited_content?, conflict_resolutions?} | pending_human:confirm\|force_accept\|accept_rewrite(edited_content 优先,否则 rewritten_content)\|reject\|reject_reupload;approved/auto_accepted:**retract**(回 pending_human,检索排除);failed:**retry_review**。已处置报 1001「Review already actioned」,已取代报 1001「superseded」 |
| 冲突处置 | `POST /v1/knowledge/reviews/resolve-conflicts` {review_id, resolutions:{conflict_id: use_new\|keep_old\|merge\|annotate_divergence}} | 仅保存草稿,随后仍需执行评审动作 |
| 评审设置 | `GET /v1/knowledge/review_settings?knowledge_base_id=` · `PATCH /v1/knowledge/review_settings` {knowledge_base_id, review_enabled?, high_threshold?, rewrite_enabled?, rewrite_auto_ingest_enabled?, max_rewrite_iterations?, conflict_detection_enabled?} | 平台新建 scope 库设 high_threshold=0.85、rewrite_auto_ingest_enabled=false |
| 文档元数据编辑 | `PUT /v1/knowledge/documents/metadata` {document_id(或逻辑键), metadata(**全量覆盖**,空对象清空)} | 统一信封 data=文档对象;**不重传正文、不触发重 ingest——治理状态翻转专用通道**(此前误判不存在,系 PATCH/batch 试错) |
| 记忆写入 | `POST /v3/memories/add` {messages[{role,content}], user_id/agent_id/app_id/run_id 至少一项, metadata?, infer?(默认true), memory_type?, source_type?, custom_instructions?, timestamp?} | 裸 JSON `{message, status:PENDING, event_id}` → `GET /v1/event/<id>` 等待;此前 POST /v1/memories 失败即因记忆在 **/v3** 前缀 |
| 记忆检索 | `POST /v3/memories/search` {query, filters 或顶层业务字段(二选一), top_k?(默认10), threshold?(默认0.5), method?(semantic/agentic), rerank?(默认true)} | 裸 JSON `{results:[{id,memory,hash,score,ranking_score,created_at,categories,metadata}]}` |
| 记忆列表/单条 | `POST /v3/memories`(filters/page/page_size/sort)· `GET/PUT/DELETE /v1/memories/<id>` | PUT 单条替换正文;DELETE 返回 event_id |
| 记忆整理 | `POST /v1/memories/evolve`(业务范围) | 异步事件 |
| 记忆晋升(REST) | `POST /v1/memory_promotions/generate`(topic≤512,kb 可选)/`approve`(promotion_id+kb_id)/`reject`;`GET /v1/memory_promotions`(status/page/sort_by=quality_score) | 治理沿用通道,平台 webapi 代理 |
| 事件轮询 | `GET /v1/event/<event_id>` | 事件对象(event_type/status/payload/results/resource_id);终态 SUCCEEDED/FAILED/CANCELLED |
| Wiki 页搜索 | **无 REST 等价 → MCP tools/call**(`knowledge.wiki_search`) | keyword(IK 分词 BM25)/regex(term 级整词,对齐 WeKnora `~*`);regex `.+` 可全列页面;返回 slim 命中(page_id/slug/title/page_type/summary/heading_path/match_snippet),无整页正文 |
| MCP 工具面 | `POST /v1/mcp` JSON-RPC(initialize/tools/list/tools/call) | 原生 `knowledge.*` 14 工具(create_base/create_text_document/delete_*/get_*/list_*/search/update_base/wiki_search)+ `contextdb_connectors__*`;可挂 langchain-mcp-adapters |

## 2. 关键行为

1. **KB 模式互斥**:wiki XOR graph。wiki 模式 = 检索(source 切片+wiki 合成章节)+ 实体页体系;graph 模式 = 显式实体/关系 API(实测 wiki 库 entities/graph 返回空)。**平台 scope 库统一 wiki 模式**(「知识图谱基于 Wiki」=实体页组织);graph 模式库留作后续扩展。
2. **Wiki 形态**:编译器生成 entity 页(page_type=entity,slug=entity/<slug>,LLM summary)、category 树、Index 页;`knowledge.search(knowledge_view=wiki)` 返 section 合成内容含溯源;页面树 GET(category)+ wiki_search regex 全列(entity/Index)。
3. **评审准入闭环**:upload→processing→ai_reviewing→pending_review(**检索排除**,thr 0.2 仍空)→人工 confirm→succeeded(**检索命中**)。文档更新→旧评审 superseded→新评审。graph_status 独立推进(queued→processing)。**语义诊断全部由此评审承担**(平台已移除本地千问语义复核与向量缓存,本地只保留规则格式检查)。2026-11-13 真实云端实测:pending_human 期间检索 0 命中 → accept_rewrite+edited_content 后 approved 且正文被替换 → 对已处置评审再 confirm 返回 400「Review already actioned」→ retract 回 pending_human 且检索 0 命中 → confirm 后检索命中 → PUT 正文生成新评审(pending_human)。**对已入库文档的修订评审执行 reject 不删除文档**(首次入库的 reject 才删除),需显式批量删除。
4. **治理建模**:metadata 32 键即时可见(评审关库验证:创建→读 v1→PUT→读 v2→metadata 翻转 v3,读后写即时);状态翻转=专用 `PUT /v1/knowledge/documents/metadata`;正文替换=PUT(id 稳定,**写-写之间需等 ingest 落定**,否则 1003「not in a stable state for update」);**claim 原语=同逻辑名 create 1003(insert-if-absent,实测重复即拒绝而非自动替换)**,锁释放=DELETE,崩溃残留锁按 claimed_at 超时抢占。评审**开**的库:源文件快照在评审确认后才交换(下载 URL pending_review 期间为旧快照);已删除文档的读回返回 4007(400 也表示不存在,勿只认 404)。
5. **版本读取缺口**:entity 页无 version 只读端点(树仅 category;wiki_search 无版本)→client 记录写响应版本 + stale 时有界重试(+1..+5)。
6. **写入纪律(治理存储实测)**:①纯易变字段翻转(status/phase/progress/message)走 `PUT /v1/knowledge/documents/metadata` 快通道,即时生效无成本;②正文写入(text PUT)后必须**等 ingest 落定再做 metadata 编辑**——meta 编辑落在 ingest 进行中会触发长不稳窗(后续正文 PUT 连续 1003,可超 15s);③正文内容大对象(版本载荷)>150KB 走官方 multipart 文件上传(≤20MB);④下载正文必须按 UTF-8 显式解码(预签名响应无 charset,requests 默认 Latin-1 会 mojibake);⑤新建文档的列表索引秒级可见(创建即可列出),复合过滤的值更新投影同样即时;任务读取带 3s 重试兜底即可。
7. **正文读回**:document-get 无正文;`with_download_url=true` → 预签名 URL HTTP GET(checkpointer/治理详情读取路径);评审开的库中源文件快照在评审确认后才交换。
8. **云端切片**:chunk_size/chunk_overlap 按 KB 配置;document-chunks 可列;本地 Docling 分块仅保留治理复核用途。
9. **本机环境坑(实现必防)**:①NO_PROXY 含 IPv6 字面量 `[::1]`/`::1` 会令 httpx(httpx2)URLPattern 解析崩溃——app 启动时净化 NO_PROXY;②`openai` 必须 <3(langchain-openai 1.7.4 兼容 2.x;3.x 构造 AsyncOpenAI 报缺凭证);③uv 解析无上界时会把 openai 升到 3.x——requirements 钉 `openai<3`。
9. CLI hooks/skills 已装(`~/.qoder/skills/contextdb-*`);**完全重启 Qoder 后 auto-capture/recall hooks 生效**。

## 3. 平台设计落点(v5 计划)

- 治理知识库 `_governance`(graph/wiki/review 全关——纯状态库,免评审门);scope 知识库 wiki 模式(review 开=准入门)。
- 发布→`kind=ctxdb_sync`:上传清洗文档(.md)→评审→批准→检索/Wiki 编译生效。
- Wiki 在线编辑:POST 创建(人工页)/PUT CAS 更新;页面树 GET + wiki_search regex 全列。
- Agent 知识库访问:**ContextDB MCP 直挂**(langchain-mcp-adapters,/v1/mcp 原生 knowledge.* 工具:检索/文档/实体/wiki 页导航);memory_add 走官方 REST(/v3/memories/add)+事件轮询;治理溯源工具走 client REST。
- checkpointer:thread 状态=治理库文档(file_path=agent/checkpoints,name=thread_id),put=update-text,get=detail+download_url。

## 4. 残留物与未尽事项

- 探测 KB `_probe_governance`、`_probe_wiki`、`_probe_state` 已于 2026-11-13 全部删除;云端仅保留 `knowledge-default` 与 `_governance`。删除含 pending_review 文档的 KB 需先对评审执行 reject 解锁文档,再清空文档、等删除异步落定后删库。
- 未实测(实现时验证):`memory promotion generate` 实际产出形状(避免空记忆耗云端算力);治理库全关模式下 PUT 重 ingest 的时延;review 模板端点(`review_templates`)。
- 已否决通道:PATCH/batch 元数据编辑(未声明);memories REST(未声明);wiki_search REST(未声明)。
