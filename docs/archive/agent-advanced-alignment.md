# Agent 高级能力原生对接与验收记录

后续[真实运行验收](agent-real-acceptance.md)已发现社区沙箱适配器的权限数字协议缺陷；本页的既有通过数仅覆盖当时列明的用例，不能据此认定新增的 write→edit 场景通过。最新运行结果与待确认项以真实验收记录为准。

核对日期：2026-11-15。本文接续 [核心聊天对齐审计](agent-official-alignment-audit.md)，仅描述 Agent 运行链；知识库模块、知识页面、治理数据与 ContextDB 服务不作修改。

## 1. 差异盘点与最终边界

| 初始差异 | 本轮处理 | 不冒充的能力 |
| --- | --- | --- |
| 固定 StateBackend，无法执行 Shell | 经用户批准接入 `langchain-sandbox-opensandbox` 目录适配器和官方 OpenSandbox SDK，执行环境按 owner/session 分配 | 本机 runc 开发环境不构成 Linux + gVisor 安全验收 |
| 会话文件被称为长期记忆，缺跨会话 Store | 官方 `PostgresStore` 原生异步接口、`StoreBackend`、`CompositeBackend` 与 `MemoryMiddleware` 文件注入 | 不模拟 WeKnora 的结构化记忆条目、提炼、主题、审核或向量召回 |
| 父流丢弃子图正文，独立子任务页缺真实数据 | 从唯一原生流及原生子 checkpoint 投影 `collaboration_status` 和子轨迹读取接口 | 不创建影子 Agent session/run，不重跑子任务，不把子正文混入父回答 |
| fork/rewind 全部拒绝 | 官方 `aupdate_state`、`__copy__`、`END`；按原 WeKnora 选点语义适配 | 新分支是选中状态的新线程，不克隆旧 checkpoint/子图审计；原审计保留原会话 |
| 启动流程没有初始化官方持久化表 | ASGI lifespan 调用幂等的 Saver/Store `setup()` | 不修改知识库 schema，不建立知识检索索引 |
| 后台执行无现成免费官方服务 | 按用户指示暂缓并保留明确拒绝 | async durability、子图并发或 HTTP 取消句柄均不等于后台运行服务 |
| OpenSandbox 当前文件与 WeKnora 按回答版本的产物协议不同 | 用户确认只保留已有 checkpoint 产物，不新增沙箱快照机制；无 checkpoint 版本的沙箱消息产物接口明确 501 | 不凭当前文件伪造历史版本、生成归属或已回滚的工作目录 |

依赖固定为 `deepagents==0.7.35`、`langgraph==1.2.20`、`langgraph-checkpoint-postgres==3.2.0`、`opensandbox==1.2.1`、`langchain-sandbox-opensandbox==0.1.2`。适配器是 Apache-2.0 社区项目，获用户明确许可，不能称为 LangChain 自己维护的实现。`langchain-qwq` 为此前批准的 MIT 社区模型适配例外，用于保留 Qwen `reasoning_content`。

PostgreSQL 保存官方 checkpoint、无向量索引的原生记忆文件以及既有运行支持元数据；不作为知识库或检索源。未接入收费/闭源 Agent Server 或托管沙箱；模型供应商与现有 ContextDB 服务的费用不属于框架免费许可的保证范围。

## 2. WeKnora 源码复用与组件映射

固定上游：[Tencent/WeKnora cbdcebabf48c5ee2d6868b370326aa8341703f62](https://github.com/Tencent/WeKnora/tree/cbdcebabf48c5ee2d6868b370326aa8341703f62/frontend)。Agent 组件、样式与交互保持原源码；继续真实验收时，将 `api/system/index.ts` 额外的 State 枚举及 `SandboxConfigEditorDrawer.vue` 两处自定义选择逻辑恢复上游原文，未添加 UI 或翻译。

| 交互范围 | 直接复用的源码 |
| --- | --- |
| 会话与 Agent 管理 | `src/views/chat/index.vue`、`src/views/createChat/createChat.vue`、`src/views/agent/AgentList.vue`、`AgentEditorModal.vue` |
| 输入、模型与范围选择 | `src/components/Input-field.vue`、`AgentSelector.vue`、`ModelSelector.vue`、`KnowledgeBaseSelector.vue`、附件与提及组件 |
| 正文、工具与计划 | `views/chat/components/botmsg.vue`、`usermsg.vue`、`AgentStreamDisplay.vue`、`ToolResultRenderer.vue`、`tool-results/PlanDisplay.vue` |
| 审批与提问 | `PendingPromptDock.vue`、`ToolApprovalCard.vue`、`AskUserCard.vue`、`McpOAuthCard.vue` |
| 子 Agent 轨迹 | `ChildAgentTabBar.vue`、`ChildAgentStream.vue`、`CollaborationTasks.vue` |
| 沙箱与产物 | `SandboxTerminal.vue`、`SandboxDesktop.vue`、`ChatArtifactsPanel.vue`、`components/chat/SandboxSidePanel.vue` |
| 分支回退与流处理 | `views/chat/forkPoint.ts`、`rewindView.ts`、`rewindNotice.ts`、`api/chat/streame.ts`、`useChatStreamHandler.ts` |
| 字体及布局 | `main.ts`、`App.vue`、`theme.css`、`tdesign-overrides.less`、聊天 Markdown/shared/timeline 样式、`useFont`、`useTheme` |

完整文件及 SHA256 见 `frontend/UPSTREAM-AGENT-UI.json`，门禁 `frontend/src/official-agent-ui.test.ts` 当前核对 113 个 SFC template/style、36 个交互源码和 27 个字体/布局依赖（继续验收新增完整沙箱配置抽屉守卫）。4 个交互源码只允许既定的 Agent 专属官方组件 import 重定位，知识页面共用文件保持原样。字体大小、字重、行高、padding/margin 与 gap 由上游原样式承担，不添加覆盖规则。

源码一致与全场景像素验收是不同证据：本轮对上述源码执行门禁；不能由此声称所有浏览器、字体环境、动态内容截图已做到零差异。

## 3. API、数据流与原生调用

```text
WeKnora 原组件 / 原 useChatStreamHandler
  → 原 HTTP、SSE、WebSocket 契约
  → API Adapter（鉴权、配置、DTO 与事件转换）
  → 唯一 deepagents graph.astream / Command / checkpoint API
  → 官方 PostgreSQL Saver、Store / OpenSandbox SDK
```

### 核心聊天、审批与 Trace

`webapi/harness.py` 使用单个 `graph.astream(..., stream_mode=['messages','updates','values','tasks'], subgraphs=True, version='v2', durability='sync')`；`tasks` 只为 WeKnora 子轨迹投影启用，原 Harness 原生接口保留前三种模式。未为子面板另跑一遍 v3 stream。官方 Python v3 `run.subagents` 已通过实际包探测确认存在，但不需要为了名称一致而重复执行。两种官方接口都提供子 Agent 数据。

| 官方数据 | WeKnora 原协议 |
| --- | --- |
| HumanMessage 与持久消息 ID | `agent_query`；每轮 assistant ID 为 `assistant:<human_id>` |
| AIMessage/Chunk 文本、推理 | `thinking`、`answer`；父子 namespace 分离 |
| 原始 tool_calls、ToolMessage | `tool_call`、`tool_result`，保留原 call ID、参数、结果与错误；原生 `write_todos` 仅在展示上适配 `todo_write`/plan |
| checkpoint interrupts 与逐卡决定 | `tool_approval_required`；续接请求现场调用 `Command(resume={interrupt_id: decisions})` |
| 原生子图 namespace、调用身份、状态 | `collaboration_status` 与签名的只读子轨迹 locator |
| 官方最终状态 | `complete`、`stop`、`error`；待审批/待执行不表示完成 |

`webapi/weknora_traces.py` 的 locator 仅定位父 thread、checkpoint namespace 和真实工具调用，不是独立运行记录。子面板从父请求同源订阅；查看者断开不会取消父请求，父请求结束会释放订阅。队列有上限，不能充当后台事件服务。当前实时订阅依赖单 ASGI worker 或会话粘连：父请求若在另一进程执行，当前进程明确 409，不声称可跨进程附着。刷新读取默认 GP 子代理的原生完整 AgentState checkpoint；当前框架对任意动态、稀疏 DeltaChannel 子图不暴露通用水合入口，该情况明确 501，不自行重建 channel。回退后已脱离当前父状态的子轨迹返回 404。

子图引用继承原生父轮 HumanMessage 内已经验证的知识库范围；子面板的客户端参数不能扩大范围。引用和工具原始结果仍复用现有转换，不修改知识库工具、页面或 API。若第三方工具将来返回 WeKnora 专有 `resource://` 文件句柄，当前没有通用资源目录及 `/messages/{id}/files` 代理；不能假设可由子 locator 自动访问。现有 checkpoint 产物使用原 `source_path/index` 下载协议，不生成该类句柄。

### 沙箱、文件与终端

`agent/sandbox.py` 调用官方 `SandboxSync.create/connect/destroy`、文件 SDK；官方目录适配器 `OpenSandboxBackend` 提供 `execute` 及原生文件工具。执行容器没有宿主工作目录或 Docker socket 挂载，不注入平台/model/ContextDB 密钥，限制 CPU、内存与生命周期，出网默认拒绝。Docker socket 仅用于可信控制平面，不授予执行容器。

用户另行确认：本机仅限**可信单用户开发**。官方 1.2.1 Docker 运行时不支持 `secureAccess`，本机 loopback 执行端口没有应用层鉴权，同机其它进程不在 Web owner/session 隔离保证内。不得将此前 Web 身份隔离测试外推为本机多用户或生产环境安全。生产端点鉴权需要官方支持的 Kubernetes + Gateway 等环境，配合强化容器隔离再验收；本轮不自建鉴权网关。

`CompositeBackend` 默认路由到执行沙箱；`/state/` 路由到原生 StateBackend，前缀剥离后继续读取旧 `/skills/...` 和 `/AGENTS.md` checkpoint key，无需迁移现有文件。Skills 为原生权限保护的只读虚拟目录；`/memories/{agent_id}/` 是独立 Store 虚拟挂载。这两个目录不属于 Shell 的真实文件系统，Shell 不能读取或改写其中的指令和长期记忆。用户工作文件与 execute 位于隔离容器。只读角色不启用执行 backend。

`webapi/terminal.py`、`webapi/sandbox_terminal.py` 仅转换 WeKnora 原 ticket/WebSocket 帧至 OpenSandbox 官方 execd PTY REST/WS：单次短期票据、owner/session 绑定、鉴权撤销检查、尺寸和帧限制，不实现 PTY 引擎。终端由用户主动 provision；普通打开、刷新和历史读取不创建或重建沙箱。销毁/清空会话先调用官方 destroy；失败保留可重试的会话元数据。

沙箱历史产物按用户确认不接入。已有 StateBackend checkpoint 产物仍可列出、下载；沙箱消息没有 checkpoint 文件版本时，按消息列产物/下载入口明确 501。普通聊天历史仍可读取，文件面板不虚构当前沙箱文件的历史归属。对话结束不会自动扫描容器并创建快照或新产物存储。

新分支首次执行可经官方 SDK 从所选 checkpoint 重传虚拟附件；不复制原沙箱工作成果。图片及附件展示仍保留原 owner-scoped 归档引用及原过期规则，源归档删除/到期不因分支而延长。

### 原生文件长期记忆

`agent/checkpointer.py` 使用官方 `PostgresStore` 的 `aget/aput/abatch` 原生异步接口，不建立向量索引。继续验收发现 `AsyncPostgresStore` 官方 context 退出仍残留 batch 任务，故使用这一现成官方替代；不访问私有任务或自建队列。`agent/graph.py` 原生 StoreBackend namespace 为 `(owner_id, 'agents', agent_id, 'memory')`；Agent 限定的挂载路径避免同一 thread 切换 Agent 时误用另一个 Agent 的 MemoryMiddleware 路径缓存。工作空间开关、个人开关和 Agent 开关共同决定是否挂载；工作空间默认关闭。

`/api/v1/agents/{agent_id}/memory-file` 直接读写原生 `/AGENTS.md` FileData，供 API 管理；未添加前端编辑器。新会话读取最新文件，同一 thread 遵循官方首次加载缓存。有效 `write_mode='native_file'`，写入遵循原生工具权限/HITL，不能冒充 WeKnora 的 `explicit_only`/自动提炼策略。没有自定义刷新、自动提炼、结构化审核或检索服务；相关 WeKnora 结构化接口返回明确不支持。启用或切换 Agent 后不强刷已有 thread 缓存；路径隔离保证不会注入其他 Agent 的旧缓存。删除会话保留跨会话记忆，删除 Agent 配置也不擅自销毁其 Store 命名空间。

### 分支与回退

`agent/time_travel.py` 只调用原生 `aget_state` 沿当前 head 的 `parent_config` 选点：用户问题表示该问题之前，assistant 表示该完整回答之后。运行中、待审批、无检查点或外部消息 ID 明确拒绝。

- 新分支：创建新的 owner-scoped 平台会话，将选中已水合状态经 `aupdate_state(..., as_node='model')` 种入空的新 thread，再通过 `END` 清除待执行任务。空线程直接接收原生值；不能把 LastValue 渠道全部包装成 `Overwrite`，否则 Skills 元数据会变成不可迭代的包装对象。排除 `memory_contents`，让新会话加载最新共享记忆；不调用模型或工具。平台会话事务在 seed 成功后才发布，失败清理官方 checkpoint。
- 原会话回退：对选中 checkpoint 调用 `aupdate_state(..., None, as_node='__copy__')`，再以 `END` 清任务，包含第一条问题前的空状态。旧检查点仍保留原审计。产物读取沿当前祖先链，避免回退后的界面混入未来分支文件。
- API 返回 `workspace_reset=false, reason='CHECKPOINT_ONLY'`，触发 WeKnora 原提示。不撤销真实沙箱文件、共享 Store 记忆或已经执行的 MCP 副作用。新分支不继承旧 sandbox handle。

官方 PostgreSQL Saver 的 `copy_thread/acopy_thread` 在当前安装版本抛出 `NotImplementedError`，因此没有调用该空方法后宣称完整克隆，也没有复制数据库 checkpoint 表。

## 4. 验证与待验收项

本轮验证日志与知识冻结散列保存在 `output/verification/agent-advanced-20261115/`，汇总为 `verification.json`。此前核心阶段的通过数不作为本轮高级能力证据。

| 检查 | 本阶段记录（后续真实验收见单独报告） |
| --- | --- |
| 后端全量 `.venv/bin/python -m pytest -q` | **460 passed、2 skipped、57 warnings，107.02 秒**，见 `backend-release.log`。两项 opt-in 跳过为外部网页浏览器与真实 OpenSandbox；后者已单独实际执行。 |
| 真实 OpenSandbox + legacy 精准回归 | **21 passed，14.33 秒**，见 `sandbox-real.txt` / `sandbox-real.json`。包含真实命令、二进制往返、两会话隔离、外部 TCP 样本拒绝、实际容器限制和 PTY 输出；生命周期取消/提交失败/未 ready PTY 清理也有回归。 |
| WeKnora 官方源码门禁 | **1 passed**；112 SFC 模板/样式、35 交互源码、27 字体/布局依赖符合固定上游基线；继续验收仅恢复了具名后端枚举的上游原文。 |
| 知识库冻结 | **180 个既定文件 SHA256 全部不变**，见 `knowledge-freeze-result.json`；未执行 ContextDB 云端写入。 |
| 依赖与差异 | `uv pip check`：**209 个已安装包兼容**；`git diff --check` 通过。 |

真实验收曾遇到官方 Docker 小端口池分配碰撞，第二沙箱创建返回 503；原失败日志保留为 `sandbox-real.failed-port-collision.txt`。恢复上游默认的 40000–60000 候选范围后复验通过，仅降低碰撞概率，没有自写分配器或重试保证。测试执行容器已清理，只保留 loopback 控制服务与原 PostgreSQL。SDK server-proxy 数据通路有官方维护模式弃用提示，后续 Gateway 部署需另验。

本轮使用受控模型/工具 fixture 与真实 PostgreSQL，不将其称为云端模型或业务云端知识检索验收；没有重新执行全场景浏览器像素比较或生产压力测试。执行容器的配置核对及有限网络样本不能证明不存在逃逸或全部网络绕过。

后台续跑继续核验：官方 [Async subagents 文档](https://docs.langchain.com/oss/python/deepagents/async-subagents)要求可执行的 Agent Protocol server；再次核对官方 `agent-protocol` 提交 `820bd30cc8e8f7864310c3dd7f36774ef6fa69c6`，其 [runs](https://github.com/langchain-ai/agent-protocol/blob/820bd30cc8e8f7864310c3dd7f36774ef6fa69c6/server/ap_server/routers/runs.py) 和 [background_runs](https://github.com/langchain-ai/agent-protocol/blob/820bd30cc8e8f7864310c3dd7f36774ef6fa69c6/server/ap_server/routers/background_runs.py) 执行端点仍为生成的空实现。协议仓库不等于现成执行服务；没有拿它启动空服务冒充续跑，也没有据此推断所有第三方实现都不存在。用户已确认仅接受现成官方开源组件，故该项暂缓。

已明确的限制：后台续跑按用户指示暂缓；浏览器/桌面、运行中 steer、结构化记忆、自动 Skill 安装仍按真实能力拒绝，原官方入口及样式保留。自托管 OpenSandbox + runc 仅进行受限开发验证；强化 Linux + gVisor/Kata 部署就绪后还需单独安全验收，不能保证绝对零逃逸。

主要原始资料：[Deep Agents 沙箱](https://docs.langchain.com/oss/python/deepagents/sandboxes)、[文件记忆](https://docs.langchain.com/oss/python/deepagents/memory)、[事件流](https://docs.langchain.com/oss/python/deepagents/event-streaming)、[LangGraph 持久化](https://docs.langchain.com/oss/python/langgraph/persistence)、[Time travel](https://docs.langchain.com/oss/python/langgraph/use-time-travel)、[OpenSandbox 官方 Deep Agents 示例](https://github.com/opensandbox-group/OpenSandbox/blob/main/examples/deep-agents/main.py)、[获准的社区适配器](https://github.com/AyushSonuu/langchain-sandbox-opensandbox)。版本结论以本项目锁定包的实际源码和可复现探测为准。
