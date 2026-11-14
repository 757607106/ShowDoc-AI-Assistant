# Agent 运行组件

本项目直接使用官方开源 SDK，在现有 PostgreSQL 和 ASGI 服务内运行 Harness。不部署生产 Agent Server、Redis 或 Helm，不要求其部署许可。模型和 ContextDB 仍使用用户配置的外部服务。

| 能力 | 实际组件 |
| --- | --- |
| 主代理、子代理和工具调度 | `deepagents==0.7.35` 的 `create_deep_agent` |
| 会话文件、读取、写入、编辑、删除和搜索 | 官方 `StateBackend` 与文件工具 |
| Skills 指令发现 | `SkillsMiddleware`，`skills=['/skills/']` |
| 会话说明 | 官方 `memory=['/AGENTS.md']`；不等于跨会话长期记忆服务 |
| 计划和模型回合预算 | 官方 Todo 与 ModelCallLimit middleware |
| 提问、人工确认与恢复 | 官方 `interrupt`、HITL、`Command(resume=...)` |
| 持久化和历史 | `langgraph==1.2.20`、官方 PostgreSQL checkpointer |
| 前端流状态 | `@langchain/vue==0.4.9`、`@langchain/langgraph-sdk==1.8.12` |

前端保留 WeKnora 的页面与展示组件，使用 `FetchStreamTransport` 访问 `POST /api/v1/harness/sessions/{id}/stream`。服务端直接消费官方 `astream`，只适配认证、业务配置与 JSON/SSE 传输。刷新通过 `GET /api/v1/harness/sessions/{id}/state` 调用官方 `aget_state`。

执行属于当前请求。断开或停止后结束本次执行，不在后台续跑；刷新读取已存 checkpoint，不自动重复工具调用。外部服务已接受的操作不会因为本地取消而自动撤销。并发发送、清空和删除由同一 PostgreSQL advisory lock 互斥，不建立任务队列或第二套运行状态。

Skills 归档只保存内容，上传不执行脚本。官方文件工具可以读取已选择的 UTF-8 内容，但当前 StateBackend 不提供 Shell。静态目录上传受全局 100 MB 请求上限限制；归档内路径、符号链接与大小仍会校验。曾被旧安装记录引用的目录不允许覆盖或删除，以保留历史版本。

旧 Docker、终端、BrowserSkill、自动安装、后台命令、steering、fork/rewind 的自写执行器已删除。它们的旧 HTTP 执行入口返回 410。已有容器、卷、安装记录及历史会话保留，不在升级或读取历史时自动清理、恢复或启动。

新会话通过 `agent_sessions.agent_config.runtime=deepagents` 标识；消息、文件、Todo 与中断状态均由官方 checkpoint 保存。旧 `agent_runs`、事件、steer 表仅用于归档读取，新流不写入这些表。历史 StateBackend 文件按保存的 checkpoint 版本下载；旧沙箱文件需要已停用的执行器，接口会明确返回不可用。

界面能力与运行链对应如下：

| 界面能力 | 当前行为 |
| --- | --- |
| 模型、提示词、知识库及文档范围 | 业务配置和权限校验后装配官方 Harness |
| 工具目录 | 官方固定工具只读展示，仅实际生效的只读业务工具可选择；目录读取失败明确报错，保留原选择 |
| 发送、停止、刷新、工具结果、规划、子代理 | 官方 Vue SDK 与原生 graph 状态 |
| 批准、拒绝、修改参数、回答提问 | 按官方 interrupt ID 一次提交 `Command(resume=...)` |
| MCP OAuth | 在服务设置授权后手动检查状态，或跳过；仍通过官方中断恢复 |
| 文件访问权限 | 只读／确认／自动写入仅作用于会话虚拟文件；知识与外部 MCP 工具当前只读 |
| Skills | 选择已授权的静态指令内容，无安装、升级、脚本执行或沙箱等待流程 |
| 记忆 | 官方 `/AGENTS.md` 会话文件；不同会话隔离，不提供自动跨会话提炼、召回或检索改写 |
| 来源 | 从本轮成功工具结果与服务端授权范围生成展示；不改写保存的回答或流状态 |
| 旧会话 | 读取保存的消息、引用及可用产物，不继续旧执行 |
| Docker、终端、浏览器、旧网络搜索执行 | 停用，历史配置只读，界面不提供启用入口 |

旧自写长期记忆队列、提炼、召回与检索改写代码已删除；此前未注册到实际应用的相关设置页不再展示。已有数据库配置和 ContextDB 记忆数据保持原样。旧多轮开关、历史轮数等未被官方 Harness 消费的控制项不再提供可操作入口；历史由官方 checkpoint 管理。

启动使用 `.venv/bin/python app.py`，其默认入口已为 Uvicorn ASGI。也可运行 `.venv/bin/uvicorn asgi:create_app --factory --host 127.0.0.1 --port 8000`。仅启动 Flask WSGI 无法提供原生 Harness 流接口。
