# Agent 运行组件

主应用使用固定版官方 Deep Agents SDK，在现有 PostgreSQL 和 ASGI 服务内运行主代理。前端沿用 WeKnora 的页面、聊天流和展示组件，由应用 API 适配原生 graph 状态；当前没有使用 `@langchain/vue` 的 `FetchStreamTransport`。后台异步子代理另由本机 Docker 中的第三方开源 Aegra + Valkey 运行，具体版本、授权、部署和既有验收记录见[异步运行服务指南](async-agent-runtime.md)。Aegra 不是 LangChain 官方 Agent Server，新增组件没有要求 LangSmith 付费账号；模型及 ContextDB 继续使用用户原有配置。

| 能力 | 实际组件 |
| --- | --- |
| 主代理、工具调度、专业及可信编译子代理 | `deepagents==0.7.35` 的 `create_deep_agent`、`SubAgent`、`CompiledSubAgent` |
| 后台异步子代理 | SDK `AsyncSubAgent` / Agent Protocol → Aegra `0.11.0`，使用固定源码 SHA 门禁的兼容补丁 |
| 后台队列与持久化 | Valkey `9.0.7` AOF、Aegra PostgreSQL 线程/run/checkpoint，复用 worker、lease 和 reaper |
| 会话文件及执行环境 | 官方 `StateBackend` 或经本项目适配的 OpenSandbox；实际环境由部署配置决定 |
| Skills 指令与执行副本 | `SkillsMiddleware` 发现授权目录；需要执行时将脚本副本准备到真实沙箱，不建立安装任务 |
| 文件记忆 | 官方 `memory=['/AGENTS.md']`；owner + Agent 范围的 PostgreSQL Store 文件与线程文件分别处理 |
| 计划与模型回合预算 | 官方 Todo 与 ModelCallLimit middleware |
| 提问、人工确认与恢复 | 官方 `interrupt`、HITL、`Command(resume=...)` |
| 主会话持久化与历史 | `langgraph==1.2.20`、官方 PostgreSQL checkpointer / Store |
| 前端流和状态 | WeKnora 聊天组件、应用 SSE / HTTP API；应用投影展示原生 checkpoint 与 interrupt |

聊天页面通过 `POST /api/v1/agent-chat/{id}` 或 `/api/v1/knowledge-chat/{id}` 获取适配后的 SSE，继续流与保存的消息也经现有应用 API 读取。原生 `POST /api/v1/harness/sessions/{id}/stream` 和 `GET /api/v1/harness/sessions/{id}/state` 保留供直接 SDK 契约及验收消费者使用，后者读取官方 `aget_state`。这些入口复用同一 graph 与 checkpoint，不建立第二套 Agent 工具循环。

主请求断开或停止会结束该同步执行；刷新读取保存的状态，不自动重复工具调用。已经提交的异步子代理在独立 Aegra 服务继续执行，须通过该后台任务的取消入口处理；远端完成不会自动唤醒父会话。外部服务已接受的副作用不会因取消或 checkpoint 回退而撤销。主 API 取消句柄仍限单进程，不能据此宣称多副本取消一致；后台服务当前也是单机配置，Valkey AOF `everysec` 不是零丢失保证。

Skills 上传仅保存内容，不执行脚本。目录浏览、选择与上传进度对应真实文件操作，没有自动安装、升级或虚构沙箱等待流程。Shell 只在选用真实可执行 backend 且权限允许时提供；StateBackend 本身不提供 Shell。归档路径、符号链接和大小仍受校验，历史引用的目录保留版本保护。

旧 Docker/终端业务面板、BrowserSkill、浏览器配对、自动安装、后台 Shell、steering 与旧 fork/rewind 执行器已退役。当前原生 checkpoint 分叉和回退是独立能力，不恢复旧执行器，也不回滚沙箱、跨会话记忆或外部副作用。已有容器、卷、安装记录和历史会话保留，不因升级或读取历史自动清理、恢复或启动。

新会话以 `agent_sessions.agent_config.runtime=deepagents` 标识；消息、文件、Todo 和中断状态以官方 checkpoint 为权威。旧 `agent_runs`、事件和 steer 表用于归档读取，新流不写入这些表。历史 StateBackend 文件按保存的 checkpoint 版本下载；依赖已退役旧沙箱执行器的文件明确返回不可用。

OpenSandbox 的交付文件统一保存到 `/workspace/`。主代理的文件、编辑、命令工具及已返回的同步委派在原生工具节点中归档本轮内容变化，原始字节写入现有 checkpoint `files`，聊天、产物库和下载继续使用原接口；后续审批暂停或沙箱回收不影响已归档版本。Skill 副本和内部工具结果不作为交付产物；单次工具归档总量上限为 25 MiB，失败在原工具结果中显示，不自动重执行。旧沙箱未归档的历史文件不做回填。同步子代理自身暂停期间的产物展示不在本次主代理修复范围内。

| 界面能力 | 当前对接方式与边界 |
| --- | --- |
| 模型、提示词、知识库和文档范围 | 业务配置及 owner/权限校验后装配官方 graph；不改 ContextDB 资源身份和 ACL |
| 原生 Agent 配置 | 结构化输出、文件权限、HITL、专业子代理与异步运行方式对应 SDK 配置；不展示未消费的 Go RAG 控件 |
| 发送、停止、刷新、工具结果、计划和子代理 | WeKnora 展示组件读取应用对原生 graph 状态的投影；后台详情观察所属子线程的原生 history/checkpoint，按轮询和刷新更新，不宣称 token 实时流 |
| 子会话产物 | 原 ChatArtifactsDrawer 提供只读预览和下载，无新增产物 CRUD |
| 批准、拒绝、修改参数、回答提问 | 服从实际 `allowed_decisions`，按官方 interrupt ID 提交 `Command(resume=...)`；批量暂存与执行恢复分开 |
| MCP OAuth | 在服务设置授权后检查状态或跳过，经原生中断恢复 |
| 文件权限 | 只读／确认／自动写入作用于配置允许的文件视图；Shell、沙箱隔离和外部工具另有权限边界 |
| Skills | 授权目录、指令与真实执行副本，不提供安装或升级任务 |
| 记忆 | 个人开关及 owner + Agent 文件读写；关闭不删除文件，不恢复旧自写提炼/召回队列；会话缓存遵循原生语义 |
| 来源 | 仅从成功工具结果与授权范围投影，不改写保存的正文或运行状态 |
| 历史与旧书签 | 历史只读；退役页面安全重定向或显示停用，不继续旧执行 |

后台异步能力在上一轮已部署并启用，用户无需另行部署。本轮精准修复针对前后端状态、子会话交互、生命周期互斥和退役调用链；修复后的真实复验结果由[本轮验收台账](../../output/verification/agent-precise-fixes-20261117/validation.json)记录，不能用上一轮服务健康或旧验收结果代替。

主应用启动使用 `.venv/bin/python app.py`，默认入口为 Uvicorn ASGI；也可运行 `.venv/bin/uvicorn asgi:create_app --factory --host 127.0.0.1 --port 8000`。仅启动 Flask WSGI 无法提供原生 Harness 流。异步服务的 Docker Compose 启停与维护命令见[部署指南](async-agent-runtime.md#本机启动)。
