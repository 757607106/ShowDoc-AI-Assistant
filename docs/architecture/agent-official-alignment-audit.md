# Agent 官方实现对齐审计与执行方案

日期：2026-11-14（Asia/Shanghai）。审计对象是当前工作树，包括已有未提交改动；本次不撤销或覆盖这些改动。

初查结论：后端核心已经使用官方 Deep Agents 与 PostgreSQL；前端当时仍有自定义聊天模板和交互分叉。第 1 节保留这些初始问题的证据。随后已按用户确认的核心范围恢复官方源码并实施 API Adapter；最新落地结果见本文末尾，不能把初查状态或此前截图当作最终实现。

本轮已确认的范围与约束：

1. 先对齐核心聊天与 Agent 管理。未接能力使用上游已有开关；无法隐藏的保留原入口，由 API 明确拒绝，不伪装成功。
2. 只使用官方开源免费的 Python Deep Agents Harness。收费 Agent Server、闭源运行时和托管执行服务排除，未安装相关依赖。
3. ContextDB 是唯一知识库及检索源。用户明确允许账号、Agent 配置、采集元数据、投递回执等运行支持记录与 checkpoint 同处 PostgreSQL；不迁移或删除现有数据。原件快照在文件目录，PostgreSQL 不建立知识索引；ToolMessage 中的原文属于运行上下文，不是另建知识库。
4. 最新红线覆盖此前较宽的共享适配范围：ContextDB 模块、页面及交互冻结。仅保留 Agent 自身 DTO 的真实托管检索标记，不更改知识库 API 或伪造 embedding/rerank 模型 ID；知识页共享依赖中的本轮改动需撤回，Agent 需要另一版本时直接复制官方组件并仅重定位 Agent 的 import。
5. 用户明确批准保留 MIT 社区 `langchain-qwq` 模型适配这一例外，以保留 Qwen 的推理字段；它不是 Agent 运行时，也不能称为 LangChain 官方模型客户端。

固定基线与证据：

- WeKnora：[cbdcebabf48c5ee2d6868b370326aa8341703f62](https://github.com/Tencent/WeKnora/tree/cbdcebabf48c5ee2d6868b370326aa8341703f62/frontend)。本次通过 GitHub API 核实 `main` 指向该提交，与 `frontend/UPSTREAM.json` 一致；比较副本 `/private/tmp/weknora-src` 的 HEAD 为该提交，工作树干净。
- Deep Agents：项目声明和实际安装均为 `deepagents 0.7.35`、`langgraph 1.2.20`、`langgraph-checkpoint-postgres 3.2.0`。按 [0.7.35 官方 graph.py](https://github.com/langchain-ai/deepagents/blob/deepagents%3D%3D0.7.35/libs/deepagents/deepagents/graph.py)核对，未因官方主分支已更新而擅自升级。
- 初查时前端使用 `@langchain/vue 0.4.9`、`@langchain/langgraph-sdk 1.8.12` 等 SDK 构建另一套展示层；本轮已删除这条展示链及其前端依赖，恢复 WeKnora 原流处理器。
- ContextDB 保持现状。本次检索 `knowledge-default` 和 `knowledge-default-graph`，返回 chunks 与该工程问题无关，未作为结论依据；没有修改云端知识、检索管线或数据。

## 1. 差异盘点清单（初查快照）

### 1.1 已对齐的能力

| 能力 | 当前证据 | 判断 |
| --- | --- | --- |
| Agent 构建、规划、文件、子代理、权限、Skills | `agent/graph.py:134` 直接调用 `create_deep_agent`，配置原生 backend、middleware、permissions、interrupt_on | 属于官方扩展点，无需重写 Agent 框架 |
| PostgreSQL 持久化 | `agent/checkpointer.py:4` 使用 `PostgresSaver/AsyncPostgresSaver` | 满足当前技术栈要求；未用 PostgresStore 本身不构成缺陷 |
| 原生状态和流 | `webapi/harness.py:74,248` 使用 `aget_state/astream`，`version='v2'`、`subgraphs=True`、`durability='sync'` | 是官方支持的流接口，不应因新文档推荐另一种流 API 就认定违规 |
| 中断恢复 | `webapi/harness.py:232` 核验 checkpoint interrupt IDs，传入 `Command(resume=...)` | 不需要自写审批调度器 |
| ContextDB/MCP | `agent/tools.py`、`agent/registry.py` 使用 `MultiServerMCPClient` 与官方工具 schema；拦截器负责归属和范围验证 | 保留知识库及文档权限，不为追求源码一致而删除信任边界 |
| MCP OAuth | `agent/mcp_auth.py:20` 使用 `OAuthClientProvider` | 平台 TokenStorage、加密和浏览器回调不等于重写 OAuth 协议 |

LangGraph 将线程状态持久化与跨线程 Store 区分为两类能力；当前 StateBackend 文件经 checkpoint 保存，仍然是会话内记忆。[官方持久化说明](https://docs.langchain.com/oss/python/langgraph/persistence)

### 1.2 源码比较结果

使用 `@vue/compiler-sfc` 解析比较所有 style 块及 template，包含 scoped/lang/src 属性。下表是实施前的初查结果，不包含上游有而本地已删除的文件；`components` 范围包含非 Agent 的共享组件。实施后的门禁结果见末节。

| 目录 | 当前 SFC 数 | 完全相同 | 修改 | 官方无对应文件 | 模板相同 | 样式相同 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `frontend/src/components` | 96 | 79 | 14 | 3 | 86 | 92 |
| `frontend/src/views/chat` | 54 | 34 | 16 | 4 | 38 | 48 |
| `frontend/src/views/agent` | 2 | 0 | 2 | 0 | 0 | 2 |
| `frontend/src/views/creatChat` | 1 | 0 | 1 | 0 | 0 | 0 |

聊天目录中官方无对应文件的 SFC：`HarnessChatPage.vue`、`LegacyChatHistory.vue`、`RetiredAgentFeature.vue`、`tool-results/ContextDBToolResult.vue`。不能仅根据“新增文件”判断应全部删除：旧历史是否迁移仍需确认；但自定义 Agent 结果渲染不能作为最终对齐方案保留。

### 1.3 已证实的偏差与缺陷

以下行号除标注修复项外，以审计时工作树为准。

| 编号 | 优先级 | 当前证据 | 影响与处置 |
| --- | --- | --- | --- |
| A01 | P1 | `views/chat/index.vue:1-251`、`router/index.ts:207` | 官方约 2500 行聊天页改为独立 SDK 页面，路由经过新增 HarnessChatPage。当前页面新增空子任务、错误重开、返回主对话等交互，缺失官方部分结构。应恢复原页面，将转换移到 API 层。 |
| A02 | P1 | `AgentStreamDisplay.vue:274,691,787` | 使用官方不存在的 ContextDBToolResult；另有自定义 StructuredFields。应将结果转换为上游已有 renderer 的协议，无法表达时使用官方通用结果呈现或等待确认，不再新增组件。 |
| A03 | P1 | `AgentStreamDisplay.vue:310-319` | 新增停止卡片；样式虽相同，模板和交互仍非官方。应恢复官方终态呈现。 |
| A04 | P1 | `views/chat/harness.ts:14-16`、`harnessDisplay.ts:159-161` | state 接口返回 `next`，前端只取 values；无请求且无 interrupt 就标 completed。真实消息复现：未得到 ToolMessage 的 write_file 调用仍 pending，但显示 completed。完成状态须由官方状态/任务结果适配，不能用连接是否活跃推断。 |
| A05 | P1 | `webapi/agent.py:259-292` 对官方聊天、stop、审批、prompt、OAuth resolution、continue-stream 路径返回 410 | WeKnora 原生数据层不能直接调用当前后端。不是复制几份 Vue 文件即可运行；需要完整 API 契约 Adapter。 |
| A06 | P1 | `AgentEditorModal.vue:139-144,1119-1138,4539` | 改写记忆区域、新增固定工具区、强制 state-backend；AgentList 隐藏部分操作及图标。应恢复官方模板，能力差距在服务端明确处理，不能靠改 UI 掩盖。 |
| A07 | P1 | `Input-field.vue:2263-2276`；`webapi/chat_interactions.py:36-42` | 运行中 steer 改为拒绝；fork/rewind/后台取消被停用。WeKnora 已有这些前端交互，缺口在本项目运行链及适配，不是上游 UI 缺失。 |
| A08 | P2 | `McpOAuthCard.vue:80-82` 设置 secondsLeft=-1 | 模板及样式相同但倒计时/超时行为不同。必须核对实际 OAuth 有效期和上游取消/超时契约。 |
| A09 | P1 | `agent/graph.py:80,90,127,136` | ContextDB 强制只读，外部 MCP 仅暴露 readOnlyHint 工具，固定 StateBackend 无 Shell；完整官方权限、脚本、沙箱交互无法按现状全部恢复。不得擅自扩大写权限。 |
| A10 | P2 | `agent/config.py:20-21,50-73` | 部分历史开关/字段可保存但运行链不消费；部分检索参数明确 501。恢复完整官方编辑器时会暴露契约差距，应逐项原生映射或明确拒绝，不能用“保存成功”表示已生效。 |
| A11 | P2 | `agent/registry.py:135-162` 对比 `webapi/model_runtime.py:62-67` | 模型保存路径和连接测试的能力校验不同；原生供应商接口/extra_config 可保存，但执行仅接当前兼容客户端。应统一现有校验；增加供应商需使用对应官方客户端。 |
| A12 | P1 | `agent/harness_config.py`、`agent/artifacts.py`、`utils/sessionArtifacts.ts` | Skill 非 UTF-8 资产被跳过，文件下载/大小未完整识别官方 base64 encoding。属于官方已有能力的适配缺陷，本轮按原生 FileData 修复；验证结果见末节。历史下载问题不代表此前所有现用文件均已损坏。 |

断线状态问题的最小复现使用真实 `HumanMessage/AIMessage`，工具调用没有对应 ToolMessage，传入当前 `weknoraMessages(messages, false, false)` 后得到：

```json
{"run_state":"completed","is_completed":true,"tool_pending":true,"answer":""}
```

## 2. 前端源码落地与组件对齐方案

### 2.1 直接复用的依赖闭包

| 范围 | 从固定 WeKnora 提交恢复的文件/组件 | 落地要求 |
| --- | --- | --- |
| 页面及输入 | `views/chat/index.vue`、`views/creatChat/creatChat.vue`、`views/agent/AgentList.vue`、`AgentEditorModal.vue`、`components/Input-field.vue` | 恢复原模板、脚本交互和全部样式块；路由返回官方页面。 |
| 回答及工具 | `botmsg`、`usermsg`、`AgentStreamDisplay`、`ToolResultRenderer` 及官方 SearchResults/GraphQueryResults/McpToolResult/PlanDisplay 等 | 删除 nativeMode/harnessMode 导致的 UI 分叉和自定义结果组件，服务端输出官方接受的数据。 |
| 交互卡片 | `PendingPromptDock`、`AskUserCard`、`ToolApprovalCard`、`McpOAuthCard`、`SecureFormCard` | 保留官方的倒计时、批量待审批、修改参数、取消与回调行为。安全表单全链路未接通前不能假装支持。 |
| 子代理 | `ChildAgentTabBar`、`ChildAgentStream`、`CollaborationTasks` | 由官方子图/工具调用身份适配，上下文和消息不得混入父回答。 |
| 引用、附件、产物 | `docInfo`、`ChatReferencesDrawer`、附件上传/预览、`ChatArtifactsDrawer`、`ChatHeader` | API 返回真实引用及经过权限验证的文件内容/地址；保持原工具栏和抽屉交互。 |
| 数据层 | `api/chat/streame.ts`、`streamTypes.ts`、`useChatStreamHandler.ts` 和相关 composables/stores/API 模块 | 上游组件继续调用原有接口，不让组件自行识别 LangGraph 专用数据。 |
| 已恢复源码、执行未接 | `HostApprovalCard`、`BackgroundWorkChip/Results`、`BrowserTaskPreview`、`SandboxDesktop/Terminal`、`HostApprovalModeSelect`、`SandboxSidePanel`、`SandboxSkillsPanel`、`SkillInstallTimeline`，以及 steer/fork/rewind 模块 | 为编译官方页面的静态依赖闭包保留原源码；按用户明确选择，有原生开关则隐藏，其余保留官方入口并由 API 明确拒绝。 |

恢复官方 SSE 数据层需要其原有 `@microsoft/fetch-event-source ^2.0.1`。noVNC 与 xterm 依赖只在确认恢复官方桌面/终端后按同一上游 lock 恢复；不替换现有 UI 库或引入另一套样式系统。

### 2.2 字体与样式核验

- `main.ts`、`App.vue`、`theme.css`、`tdesign-overrides.less`、`chat-message-shared.less`、`chat-markdown.less`、timeline/theme/loading、`markdown.less`、`useFont/useTheme` 当前均与官方逐字相同。TDesign 1.19.2、Icons 0.4.4、Vue 3.5.34、Less 4.6.4、vue-i18n 11.4.2 的锁定版本也相同。
- 官方字号 token `10/11/12/13/14/15/16/18/20/24px`、间距 token `4/8/12/16/20/24/32/40px` 当前保持一致。AgentStreamDisplay 全部样式块一致，正文 `14px/1.55/400`，摘要 `13px`，部分摘要行高 `1.6`。没有证据支持“全局字号已被任意修改”。
- `chat-layout.less` 除新增版权注释外，与官方聊天页第一个 scoped Less 块一致；官方另一个非 scoped rewind 确认框样式被省略。
- Input-field 差异主要是删除 steer 队列：官方文字 `13px/1.5`，行 gap `8px`、padding `4px 12px`，操作按钮 `26×26px`、字号 `16px`。保留输入内容的字体等没有证实变化。
- creatChat 删除项目目录控件及样式：原按钮 `12px`、高 `28px`、gap `6px`、padding `0 10px`；保留标题仍为 `28px`，页面 gap 仍为 `24px`。
- McpToolResult 将字面 `12px` 改成当前同值 token，属于源码差异，不能仅据此推断当前像素差异。

验收必须分两层：①恢复范围内 SFC 的 template/style/script 与固定上游逐字对比，允许变化仅留在明确的 API 适配边界；②同浏览器、视口、缩放、字体、主题、语言和确定性数据下，对官方页与集成页比较截图及 computed styles，并实际操作发送、停止、审批、子代理、引用与文件。既有单页截图不足以证明像素一致。

## 3. 前后端适配实现方案

### 3.1 边界与数据流

```text
WeKnora 原页面 / 原组件 / 原 useChatStreamHandler
  → WeKnora 原 HTTP + SSE 契约
  → 服务端 API Adapter（鉴权、业务配置、协议转换）
  → deepagents create_deep_agent / astream / aget_state / Command
  → 官方 PostgreSQL checkpoint
  → ContextDB 官方 MCP（保持现有知识库与权限）
```

保留已对齐的 graph、checkpoint、MCP、成员隔离和可信范围校验。Adapter 负责数据格式，不新增第二套 Agent 循环、工具执行器或运行事件数据库。原 `harnessDisplay.ts` 及自写 UI 已删除，转换由 `webapi/weknora_adapter.py`、`weknora_prompts.py`、`weknora_artifacts.py` 完成。逐卡决定仅作为 API 协议请求暂存，执行进度仍由官方 checkpoint/interrupt 判定。

### 3.2 必须对接的接口

| WeKnora 契约 | 原生执行/存储依据 | 关键边界 |
| --- | --- | --- |
| `POST /api/v1/agent-chat/{sid}`、knowledge-chat | 将 query 等业务字段经现有 resolve_request 校验，转原生 HumanMessage/files；服务端绑定 thread_id | 不信任前端自报的 thread_id、owner、工具结果或已授权资源。 |
| sessions、agents、models、skills、MCP 配置 API | 保留当前业务记录；模型、权限、知识范围逐项映射 | 不支持参数明确返回原契约可处理的错误，不静默保存无效配置。 |
| `GET /api/v1/messages/{sid}/load` | `aget_state/aget_state_history` 投影为官方 ChatHistoryMessage/agent_steps/pending_prompt | 保留真实消息和工具 ID、时间与分页；旧历史不启动执行。 |
| tool-approvals、prompts | 当前 checkpoint 的 interrupt ID 与 action index → `Command(resume=...)` | 原卡片逐项 POST，收齐后续接 GET 现场调用原生 Command 并流式返回。防止过期、跨用户、重复或不完整决定；edit 仅允许官方 review config 授权的操作。聊天 OAuth 恢复未接，明确 501，须先在 MCP 设置授权。 |
| stop、continue-stream | 当前进程 HTTP 取消句柄、官方 interrupt 和 checkpoint | 普通重连只读状态并明确 stop，不伪造后台继续；仅待审批且已收齐决定时现场恢复。没有独立后台运行服务，不能声称具有后台续跑。 |
| 文件/附件/引用 API | 原生 files、ToolMessage、原始证据以及成员归属 | 原生二进制 encoding 必须保留；不得把工具返回的任意路径当授权下载路径。 |
| fork/rewind、steer/background | 框架有部分原生基础，本轮未接完整业务语义 | 原官方入口保留，API 明确拒绝；不将普通 invoke 或刷新读取冒充运行中注入、队列或后台运行。 |

### 3.3 SSE 与 Tool Call 映射

WeKnora 消费的是 JSON 事件信封 `response_type/id/content/done/data`，以及 session/assistant 等标识；当前 Harness 发出原生 SSE `messages/updates/values` 和子图 namespace。二者不是同一种协议。[上游 StreamResponse 类型](https://github.com/Tencent/WeKnora/blob/cbdcebabf48c5ee2d6868b370326aa8341703f62/internal/types/chat.go#L341)、[上游 SSE 消费器](https://github.com/Tencent/WeKnora/blob/cbdcebabf48c5ee2d6868b370326aa8341703f62/frontend/src/api/chat/streame.ts)

| 原生数据 | 转为上游事件 | 不可省略的语义 |
| --- | --- | --- |
| 已受理的用户输入、稳定消息标识 | agent_query | 标识必须可从持久状态重新定位，不能每次重连重新编造。 |
| AIMessageChunk 文本/推理及模型元数据 | thinking / progress / answer | 使用官方消息合并规则处理分块；工具前的中间文本与最终回答分开，不因网络断开补 complete。 |
| AI tool_call_chunks 与完整 tool_calls | tool_call | 保留原 tool_call_id、完整参数和 namespace；不执行未完成的 JSON 参数。 |
| 同 ID 的 ToolMessage、status、content/artifact | tool_result | 执行错误、拒绝、未执行和成功要区分；展示字段可转换，ContextDB 官方工具名称/schema 不改。 |
| write_todos / todos | 原 plan renderer 的 tool_data | 仅在展示协议中映射 todo_write；执行工具仍是原生 write_todos。 |
| 子图 namespace、task 工具和子代理状态 | 当前只映射真实 task 调用、结果和子任务审批；独立 collaboration/child trace 面板未接 | 父子正文隔离，使用真实子工具 ID；不能把动态子图伪造为独立平台 session/run。 |
| 官方 interrupt 快照 | tool_approval_required / agent_prompt_required / mcp_oauth_required；run_suspended | pending_id 只作为 API 对 interrupt ID/action index 的可验证映射，不复制审批状态机。 |
| 完成后的官方状态、错误、取消结果 | complete / error / stop | 有待执行节点/任务或待审批时，不能用 isLoading=false 表示已完成。 |
| ContextDB 原始文档 chunks | references | 保留库/文档/chunk ID；graph_context 和 Wiki 合成内容不能伪装原文证据，失败工具不能产生有效引用。 |

`astream` 及多模式/子图事件本身均受官方支持，无需因对齐而重写。[LangGraph 官方流接口](https://docs.langchain.com/oss/python/langgraph/streaming)、[Deep Agents 子代理流](https://docs.langchain.com/oss/python/deepagents/streaming)

### 3.4 实施顺序与成功标准

1. 固定基线、完成接口/组件/能力矩阵 → 已执行，保留无关未提交工作及历史数据。
2. 修复官方 FileData 编码适配 → 已执行，Skill 资产和后端下载保留原生 encoding；前端恢复原文件 API，不留下另一套 checkpoint 下载组件。
3. 确认能力组合、费用和存储边界 → 用户已明确接受核心范围、未接 API 拒绝、运行支持元数据同库、纯数据就绪适配，以及 MIT 社区 Qwen 模型适配例外。
4. 实施 WeKnora API Adapter 并恢复原页面 → 已执行，保留原工具和审批卡片，移除自定义 native/harness UI 分支；运行仅调用免费官方 Harness。
5. 源码、集成、浏览器和真实 PostgreSQL 回归 → 本轮结果见末节。云端模型、生产负载与全部传递依赖单独验收，不沿用旧报告数字。

## 4. 缺口风险提示与已确认边界

下表区分“官方没有直接对应业务语义”和“本项目尚未接入官方已有能力”。根据用户明确的缺口暂停规则，未擅自补造这些能力。

| 后续事项 | 准确的缺口 | 本轮处理与后续条件 |
| --- | --- | --- |
| 完整交互范围 | 上游已有浏览器、终端、steer、fork/rewind、后台工作；本轮未接完整运行语义 | 已确认先交付核心聊天和 Agent 管理；已有开关则隔离，否则保留官方入口并明确拒绝，不宣称全量功能一致。 |
| Shell/浏览器/Skill 脚本 | StateBackend 无 execute；官方存在 SandboxBackendProtocol 等扩展点 | 采用哪个官方支持的 Sandbox/provider，以及实际可用的部署资源。不能自写 Shell 或浏览器执行器。 |
| 重连/后台运行 | 当前流与 HTTP 请求绑定，断开取消；不提供持久后台运行 | 审批/提问续接已用请求内原生 Command 实现，普通重连只读并明确停止。收费运行服务已排除；后续不能以 checkpoint 冒充后台执行。 |
| 长期记忆 | 当前仅会话内 StateBackend；WeKnora 跨会话记忆/自动提炼的业务语义不等于普通文件持久化 | 是否需要跨会话、按用户还是按 Agent 隔离、能否共享/删除。需要时用官方 PostgresStore + StoreBackend/CompositeBackend，不重写记忆提炼系统。0.7.35 的 StoreBackend 用 namespace 工厂，不能照旧版本示例构造。 |
| Agent 的检索配置 | 部分 WeKnora 本地 RAG 选项无法映射当前 Harness | 只在 Agent 配置 API 明确拒绝不支持选项；ContextDB 模块、参数和检索行为保持原样，不能为适配 Agent 修改知识库。 |
| 写权限 | 当前知识库与外部 MCP 工具只读；auto_write/confirm 主要作用于虚拟文件 | 是否允许扩大到官方知识/MCP 写工具及授权范围；扩大前保持现有安全约束。 |
| 安全表单 | WeKnora 有 SecureFormCard，但 native prompt 仅映射 ask_user/mcp_oauth/HITL | 是否仍需要凭据收集、加密、注入沙箱和恢复完整链路；不只补一个表单 payload。 |
| OAuth helper | 原 OAuth 使用官方 SDK，但官方聊天卡片与当前请求内续接协议不同 | 聊天内授权恢复明确 501，先在现有 MCP 设置授权。未新增等待器或修改官方卡片。 |
| 历史记录 | 旧会话当前只读，部分历史沙箱文件不可下载 | 是否接受历史只读；不能为消除 LegacyChatHistory 文件而删除历史或自动重放旧操作。 |
| 模型接口 | 当前兼容 API 与 Qwen 客户端不足以覆盖上游全部供应商配置 | 是否只接当前供应商；新增供应商必须用官方客户端，保存和执行校验要一致。 |

上述问题已经用户明确收敛为本轮核心范围；不是等待授权去引入收费运行服务。长期记忆、后台运行、浏览器/终端、分支回退、安全表单和独立子任务 trace 等仍是后续缺口。更改这些边界时需再次核实原生支持并澄清，不以当前验收外推全量功能已对齐。

本轮不实现跨会话自动记忆。workspace/personal memory 状态接口如实返回 disabled，修改返回 501，旧数据保留；Agent 的 `memory_enabled=true` 按上游语义仅允许继承 workspace，不等于激活一个记忆服务。原生检索历史目前保留，官方类型预设设置 `retain_retrieval_history:true`；请求关闭而要求另一套按轮清理行为会明确拒绝。smart 模式中上游本就不执行的 RAG 字段保留为 dormant 配置；quick 模式尚未映射的本地 RAG/history/template 选项明确拒绝。

依赖证据：[`dependency-licenses.json`](../../output/verification/agent-official-alignment-20261114/dependency-licenses.json) 核对 22 个核心包；[`direct-dependency-license-inventory.json`](../../output/verification/agent-official-alignment-20261114/direct-dependency-license-inventory.json) 覆盖 30 项 Python 直接依赖与 31 项 npm 生产依赖。61 项均有开放许可证表达式，无 unknown/uninstalled。Deep Agents/LangGraph 为 MIT，noVNC 为 MPL-2.0，psycopg 为 LGPL；不能说所有包都是 MIT。已核查的 Agent 运行链没有引入收费/闭源运行服务；这不是所有传递依赖、捆绑资产、模型或 ContextDB 服务计费的完整审计。

### 本轮验证与交付边界

- 后端全量 `.venv/bin/python -m pytest -q`：**419 passed、1 skipped、57 warnings，82.83 秒**。随后补齐原生 todos 到官方 PlanData 的字段转换，并对有效/无效原生计划、历史及原有 Harness/Adapter 完整复核：**31 passed，9.68 秒**。测试图补入生产本就使用的官方 TodoListMiddleware，没有放宽断言。跳过原有外部网页浏览器测试；警告来自既有 Docling/NumPy 与 Starlette WSGI 弃用提示。日志在 `output/verification/agent-official-alignment-20261114/backend-full.log`、`backend-final-adapter.log`。
- 使用真实官方图与隔离 PostgreSQL schema，模型和 ContextDB 为受控 fixture；默认测试禁止云端 ContextDB 请求。没有用假 SSE 替代真实 graph 执行。
- 新回归覆盖：原聊天协议、历史、真实 tool IDs、逐卡批准/拒绝/修改、ask_user、子代理审批、父子正文隔离、跨用户/会话、重复续接、首帧断线、取消与锁释放、文件按 turn 版本和二进制原字节。没有写新 `agent_runs/agent_run_events` 或文件索引表。
- 首次全量的旧历史分页 fixture 将新建原生会话手工填入旧运行记录，已明确改为 legacy fixture，保留原审批链、分页和非法游标断言；上述最终全量已通过。
- 适配自审修复了“审批先标已消费但 native 尚未执行”的卡死问题：不存 Adapter consumed 布尔，以官方 interrupt 进度判断；SSE yield 不跨 CancelScope；恢复流补发当前 turn 未完成的真实工具调用，让原组件能匹配工具结果。
- 知识页冻结恢复后的最终前端全量 **2825 passed、1 skipped**，类型检查通过，生产构建通过（48.09 秒）。跳过需显式浏览器环境的上游 handoff 测试。结果见 [`frontend-validation.json`](../../output/verification/agent-official-alignment-20261114/frontend-validation.json)。
- 固定上游门禁覆盖 **112 个 SFC 的模板/样式、35 个完整交互源码、27 个字体/布局依赖**；31 个交互文件逐字一致，另外 4 个仅允许明确的 import 重定位。根代理独立将 manifest 与干净官方副本核对，零不一致。
- ContextDB 共享依赖中的本轮改动已按明确逆补丁撤回，5 个从未修改的共享组件原样保留。知识页使用原图谱/图片组件；Agent 单独直接复制官方 `WeKnoraGraphQueryResults/WeKnoraPicturePreview`，只重绑定 Agent 的 import，未设计新 UI。恢复证据见 [`knowledge-freeze-restoration.json`](../../output/verification/agent-official-alignment-20261114/knowledge-freeze-restoration.json)。没有完整任务起点快照，因此不宣称做过所有知识文件与完整初始快照的逐字比较。
- 已在隔离本机浏览器验证登录、Agent 列表与创建、普通发送、刷新不重发、真实工具行/引用抽屉、ask_user 刷新恢复、文件审批后不刷新即出现工具时间线、文件预览和实际浏览器下载（36 字节逐字匹配），刷新后仍可预览，无 pageerror。最终结果见 [`final-browser-summary.json`](../../output/verification/agent-official-alignment-20261114/final-browser-summary.json)，旧中间失败记录已标记被最终结果取代。
- 隔离服务、临时 PostgreSQL schema 和私有测试凭据均已清理，Playwright/context 已关闭。没有操作生产知识库。
- 没有执行官方站点与集成页在同条件下的完整逐像素差异度量、真实云端模型或生产负载验收；不宣称全部功能或 100% 像素验收。

此前 `agent-interaction-validation.md` 和 output 中的通过数字、截图是相应阶段的记录，不证明本次严格官方 UI 对齐；本报告的源码比较结论优先用于本次迁移决策。
