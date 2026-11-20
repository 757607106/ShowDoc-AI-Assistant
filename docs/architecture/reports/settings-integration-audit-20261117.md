# 全部设置功能对接核查

核查日期：2026 年 11 月 17 日。对象是当前工作区和 `http://localhost:5173/platform/settings`，包含未提交的现有改动。

**结论：前端 WeKnora 与后端 DeepAgents 尚未全部对接。** 核心模型、远程 MCP、会话 checkpoint、原生技能指令和 AGENTS.md 文件记忆已有真实调用链；消息索引、结构化记忆、部分默认配置、沙箱管理、空间设置及原版系统管理存在缺口。还存在“保存了但运行不读取”的字段。

WeKnora 固定基线是 `cbdcebabf48c5ee2d6868b370326aa8341703f62`（本地清单标为 0.9.0）；DeepAgents 实际安装及依赖锁定为 `0.7.35`。官方对照使用固定提交或 tag，最新文档仅补充机制说明。WeKnora 的 HTTP 和 Go 业务服务，与 DeepAgents 的 Python harness 参数不是同一套契约；本项目需要通过本地 API adapter 映射，复制界面并不会自动接通业务逻辑。[WeKnora 官方设置][W01]、[DeepAgents 固定版组装源码][D01]

本文“已接通”表示有完整代码消费链，不能自动解释为线上供应商、云端知识库、真实沙箱均已端到端验证。“未接通”指接口拒绝、缺少消费或业务语义不一致；“已关闭”指当前部署明确关闭。

## 入口范围

页面存在两套设置外壳，由 [平台布局][L01] 的 `contextdbSettings` 决定。`section` 为 account、members、permissions、runtime 时走自定义壳；其它显式 section 走 WeKnora 壳。无 section 的知识库页面和 `/platform/settings` 走自定义壳。

| 入口 | 实际功能范围 | 浏览器核实 |
| --- | --- | --- |
| 默认 `/platform/settings` | 当前账号、成员管理、知识库权限、运行状态、常规设置、个人资料、页面助手、模型配置、默认配置、对话历史、会话文件、工具箱，共 12 项 | 已读取全部导航；读取了上述设置内容及工具箱技能、MCP 两页 |
| 显式 `?section=memory` 等 WeKnora 设置壳 | 常规、用户信息、助手、我的记忆、空间信息、成员、默认、消息管理、长期记忆、模型、Ollama、Cloud、CLI、Chrome 插件、Claw Skill、解析引擎、版本信息 | 已核实导航和长期记忆、我的记忆页面；其它页按代码/API 核查 |
| 能力或角色关闭的项 | 网络搜索、向量、存储、远程沙箱设置、个人环境变量、凭据保险箱、浏览器连接、四类服务端发布集成、系统管理员设置 | 依据后端 capability、身份 DTO、前端门控逐项核查，不将隐藏视为已实现 |

浏览器结束时已返回用户原始设置地址。未修改真实账号配置、凭据或权限。

## 当前默认设置功能清单

| 功能及子项 | 官方处理方式 | 本地对接结果及差异 |
| --- | --- | --- |
| 当前账号：显示名、账号、平台角色 | WeKnora 的用户与空间成员角色分开；DeepAgents 使用宿主应用身份 | **读取已接。** 本地 admin 被投影成 WeKnora owner，导致当前账号显示“所有者”，成员表同账号显示“管理员”；这是角色展示口径差异。[身份映射][L02] |
| 成员管理：添加、角色、启停、重置密码、绑定 ContextDB 成员 Key | WeKnora 有空间 membership、邀请及系统用户管理；DeepAgents 不提供账户系统 | **本地平台管理链已接。** 调 `/api/platform/users`，管理本地平台用户和其 ContextDB 凭据绑定，不等同 WeKnora 邀请/多空间 membership。真实写入本轮未操作。[自定义设置][L03]、[账户 API][L04] |
| 知识库权限：有效/预计/直接权限、ACL 授予撤销、用户组、组成员和组内角色 | WeKnora 自身资源权限；本项目改用 ContextDB 原生 workspace/ACL API | **转发链已接。** 高级模式才提供管理控件，服务端继续校验 ContextDB 返回的 action。浏览器确认页面加载；ACL 写入、切换权限模式未实测。[权限页][L05] |
| 运行状态：数据库、治理 worker、模型列表 | WeKnora 自有运行系统；DeepAgents SDK 本身不包含本项目治理 worker | **读取已接。** 浏览器显示数据库可用、任务处理服务运行中、qwen-max/qwen-plus。不能由此推出外部模型调用或全部 Agent 服务健康。[自定义设置][L03] |
| 常规：六种语言、浅深/系统主题、界面字体、代码字体、字号 | 官方 WeKnora 前端偏好；DeepAgents 无对应后端业务 | **前端链已接。** 语言用 locale 存储，主题/字体按用户存本机偏好并应用 CSS。跨设备同步未提供；Lite 的自动更新和宿主审批默认项在当前 Web 版不显示。[常规设置][L06]、[官方同页][W02] |
| 个人资料：ID、名称、账号、注册时间、修改密码 | WeKnora 用户资料/改密；DeepAgents 不处理用户密码 | **资料读取和改密 API 链已接。** 前端改密要求字母和数字且不同旧密码，后端主要校验长度 8–1024；策略不一致。真实改密未执行。[个人资料][L07]、[账户 API][L04] |
| 页面助手个人偏好：入口位置、固定/悬浮、个人权限等级 | WeKnora 保存本机偏好并将请求权限压到空间上限；DeepAgents 可用权限和 HITL 实现执行限制 | **部分接通。** 布局本机生效；个人权限会传入 Agent，后端限制不超过 Agent 权限，viewer 只读，文件写/execute 使用原生审批。知识库/外部 MCP 仍强制只读，不能据“自动执行”推断支持页面写操作。[助手页][L08]、[Agent 权限][L09] |
| 页面助手空间设置：名称、最高权限 | 官方 assistant-config KV 及服务端上限 | **未接。** GET/PUT `/tenants/kv/assistant-config` 返回 404；前端加载错误退回默认 confirm，不能修改空间名称/上限。[KV 实现][L10] |
| 模型：增删改复制、使用保护、供应商、协议、URL、模型名、Key、请求头、能力覆盖、上下文/输出、推理参数、测试与调试 | WeKnora 模型服务构造实际客户端；DeepAgents 接收 LangChain 模型对象 | **主体已接，支持集合收窄。** 本地 `registry → build_model_record → ChatLiteLLM → create_deep_agent`。本地模型/Ollama、部分特殊厂商签名和兼容字段不支持时显式拒绝。模型本身按用户隔离，非空间共享。下表列出未生效字段。[模型 API][L11]、[模型构造][L12]、[官方工厂][W03] |
| 默认对话、轻量生成模型 | 官方按类型投影空间默认，并由业务消费者读取；DeepAgents 自身只接受传入模型 | **对话和标题生成消费链已接，但默认页有缺陷。** 后端缺 status，前端严格 `status === active` 排掉合法模型，浏览器显示 agent-main 不可用；“空间级”实际只影响当前用户。[默认页][L13]、[注册表][L14] |
| 默认视觉、默认语音识别 | 官方 ApplyModelDefaults 投影 default_for/is_default | **只保存，默认选择未接。** 本地只投影 chat 默认，新建 Agent 的 VLM/ASR 会退到其它候选；Agent 单独明确选 VLM/ASR 是已接的另一条链。Embedding/Rerank 默认在 ContextDB 版隐藏。[官方默认模型][W04] |
| 对话历史：自动消息向量索引、Embedding、统计、清空、语义搜索 | 官方将问答写入聊天历史 KB，支持关键词/向量检索及清空；DeepAgents checkpoint 保存执行状态 | **未接。** 配置和统计 404，浏览器已显示“无法加载消息索引配置或统计信息”。已有 checkpoint 历史不是消息向量索引。[历史前端契约][L15]、[官方消息索引][W05] |
| 会话文件：沙箱列表、创建/编辑/删除、脚本总开关、供应商配置 | WeKnora 有 Docker/Cube/E2B/Host 等沙箱管理；DeepAgents 通过 backend/provider 获得文件与执行能力 | **列表已接，管理未接。** 页面实际渲染 SandboxSettings，OpenSandbox 被标 Docker，显示 Docker 未启用。记录 read_only=true，但仍露添加/编辑/删除和脚本开关；写请求 410。服务端托管 OpenSandbox 执行链单独存在，不能以管理接口失败断定没有 Shell。[沙箱界面][L16]、[沙箱 API][L17]、[执行后端][L18] |
| 工具箱技能：目录、上传、文件、启用和选择、加载指令 | WeKnora 含目录和沙箱安装生命周期；DeepAgents SkillsMiddleware 读取技能源 | **指令/参考文件加载已接。** 本地目录注入 StateBackend input.files，官方中间件加载；安装、升级、重装、卸载、安装对话和脚本生命周期仍为 410/只读投影。页面安装说明与 instructions_only 实际模式不一致。[技能 API][L19]、[原生组装][L09] |
| 工具箱 MCP：远程服务 CRUD、SSE/HTTP、认证/OAuth、发现工具/资源、启用与审批、高级参数 | WeKnora 自有 MCP 服务，DeepAgents 接收由官方 LangChain MCP adapter 提供的工具 | **远程基本链已接。** stdio 停用；只允许 readOnlyHint=true 的外部工具，非只读工具启用会 403。超时、重试次数/间隔虽然保存但运行未读取。外部 OAuth 提供商未实测；聊天内 OAuth 恢复另有未接边界。[MCP 实现][L20] |

## 其它可进入设置及关闭功能

| 设置及子功能 | 官方行为与本地对应 | 对接结果 |
| --- | --- | --- |
| 长期记忆：空间总开关、提炼模式/模型/指令/间隔、条数、兴趣阈值、向量召回和检索调优 | WeKnora 为结构化个人记忆业务；DeepAgents 原生 memory 为文件内容注入，持久化需 StoreBackend | **语义未对齐。** 本地后端只接受精确 `{enabled}`，WeKnora 页面提交完整 config，因此连总开关也 501；结构化设置均未接。所谓空间开关还按个人 owner 保存。[空间记忆页][L21]、[文件策略][L22]、[官方记忆类型][W06] |
| 我的记忆：个人开关、条目增改删、确认/归档、主题、资料关联、整理、导出 | 官方结构化条目生命周期；本地是 owner+Agent 的 AGENTS.md | **个人文件记忆开关已接；条目管理均 501。** 原生 AGENTS.md 编辑在 Agent 编辑器，PostgresStore 跨会话持久化，不能把空条目列表解释为不存在文件记忆。[文件 API][L23]、[原生 backend][D01] |
| Ollama：服务状态/地址、模型列表、下载及进度 | 官方 Ollama 服务真实启动/探测/下载；DeepAgents 可接受合适的模型客户端 | **显式设置壳可达，未接。** 本地对应管理路由缺失，source=local/interface=ollama 明确 501；这不是 DeepAgents 框架不支持本地模型。[官方路由][W07] |
| WeKnora Cloud：AppID/AppSecret、状态、自动添加云模型 | 官方先签名 health 校验，再保存 tenant 凭据，模型工厂读取 | **显式设置壳可达，未接。** 本地无对应 credentials/status 及云工厂；前端 catch 返回“未配置”不能当服务正常。[官方 Cloud][W08] |
| 解析：DocReader 地址/transport/重连、引擎测试、MinerU/PaddleOCR 配置 | 官方持久化 ParserEngineConfig 并传给 DocReader/解析引擎 | **可进入面板，但配置未接。** 本地只返回聊天附件解析元信息；parser-engine-config 404，check/reconnect 缺路由。聊天附件隔离解析和 ContextDB 永久文档解析是另一条实现。[解析 API][L24]、[官方系统处理][W09] |
| 空间信息：基础资料、名称/描述、配额/使用量、退出/删除 | 官方 tenant 读写、统计和删除 | **读取仅兼容投影，写入未接。** 本地固定 tenant=1，从环境/当前身份合成；不能视为真实多空间管理。[身份映射][L02]、[平台 API][L25] |
| WeKnora 壳成员管理：成员/邀请/改角色/移除/移交 | 官方 tenant membership 和 invitation 服务 | **未接官方完整流程。** 默认壳有独立本地平台成员管理，不应把两种成员页混为一个已实现功能。 |
| CLI | 官方命令行使用 WeKnora 服务端 API | **说明页可达。** 复制/文档链接可用，不证明官方 CLI 登录、上传、检索、聊天均兼容本后端；API Key 认证未接。 |
| Chrome 插件、Claw Skill | 官方说明页依赖服务端 API Key/集成配置 | **说明页可达，完整集成未接。** 当前 integrations.api=false，不能按页面指引取得并使用完整原版集成。不要与 Codex 使用的浏览器插件混淆。 |
| 版本信息：版本/版本检查、引擎信息 | 官方构建/部署信息 | **仅本地简化信息接通。** 返回本项目 0.1.0、contextdb 和 ContextDB 引擎信息；这不是 WeKnora 源码基线版本，完整发布检查未接。 |
| 网络搜索：provider/凭据/引擎、CRUD/复制/测试、默认 provider | 官方根据实例构造 searcher 并执行 Search | **能力明确关闭。** 旧记录强制 disabled/read_only，写与测试 410，Agent 没有该搜索工具。[能力接口][L25]、[官方搜索][W10] |
| 向量数据库：实例/连接/索引字段、连接测试、使用保护、环境实例 | 官方 vector store registry 与 KB 绑定 | **关闭且无对应管理路由。** 永久知识检索由 ContextDB 管理，不是设置页接入了原版 ES/Qdrant/Milvus 等管理。[官方向量服务][W11] |
| 存储后端：provider、endpoint/region/bucket/凭据、路径、SSL、测试、默认实例 | 官方 ResolveFileService 供业务存取文件 | **关闭且无管理路由。** 永久知识在 ContextDB；聊天附件 local 展示不等于可配置对象存储。[官方存储服务][W12] |
| 环境变量：个人技能/沙箱变量 | 官方存储并注入执行环境 | **入口隐藏，API 410。** 本地 OpenSandbox env={}，不能认为变量已注入。 |
| 凭据保险箱：网站账号密码增改删、自动填写 | 官方 credential-vault 与沙箱浏览器链 | **入口隐藏，无路由。** 模型/MCP Key 加密存储不等于网页登录保险箱。 |
| 浏览器连接：扩展状态、绑定、请求和预览 | 官方浏览器服务与 Agent 工具链；DeepAgents 可通过外部工具实现 | **能力关闭，API 410，执行请求 501。** execute/Shell 不等于浏览器自动化。 |
| 发布集成 IM、嵌入渠道、API、对外 MCP Server | 官方分别有渠道配置、嵌入 token、API principal/key、MCP Server auth/tools | **四项全部 capability=false。** 本地没有原版管理契约；“接入外部 MCP”与“发布本平台为 MCP Server”方向相反，前者接通不能证明后者接通。 |
| 系统全局设置：访问/注册/密码、系统用户、空间默认与配额、runtime、安全及其它动态项 | 官方 system_settings 和各实际业务消费者 | **系统组不可达，原版 API 未接。** 当前身份始终 is_system_admin=false；不是缺少几个输入框。 |
| 系统模型目录：查询、预览、发布、覆盖与历史回滚 | 官方目录 compiler、版本/基线冲突检查及模型服务 | **原版管理未接。** 模型编辑器的单模型 catalog/resolve 能力解析是已接的另一功能。 |
| 任务队列：队列统计、任务、重试/取消/归档清理 | 官方运行队列 API | **原版队列管理未接。** 本地治理 worker/资料任务并非同一运行系统。 |
| 平台 API Key：签发、列表、撤销、身份映射 | 官方系统 API key 服务/认证中间件 | **原版 API 未接。** 当前认证使用本地 Bearer 会话 token。 |
| 系统审计日志：查询、按操作/结果过滤 | 官方审计服务与 API | **原版页面/API 未接。** 本地写请求已有 platform_audit 记录，并不代表系统审计查询页已接。[审计写入][L02] |

上述未实现项不应归因于“DeepAgents 官方没有能力”。SDK 提供模型、工具、backend、memory、skills、middleware、checkpoint 等扩展点，账户、空间、引擎管理、发布渠道和运行队列仍需宿主业务系统实现。

系统全局设置的字段也已逐项核对。官方 registry 共 19 键，本地保留的 UI 有对应分组，后台整组未接；另有系统用户管理和批量配额操作。[官方设置 registry][W13]

| 分组 | 官方字段或动作 | 本地结果 |
| --- | --- | --- |
| 访问与注册 | auth.registration_mode、auth.complex_password_enabled、auth.default_tenant_mode、tenant.self_service_creation_enabled、tenant.max_owned_per_user | 全部未从系统设置接入；本地固定邀请制、不开放注册，OIDC 关闭 |
| 系统用户 | 查询、创建、启停、重置密码、授予/撤销系统管理员 | 原版合同未接；独立 platform/users 替代其中一部分 |
| 空间默认 | tenant.default_storage_quota_gb、tenant.default_storage_quota_mb、tenant.auto_create_api_key、tenant.auto_accept_invitation；将默认配额应用现有空间 | 全部未接 |
| 运行时 | asynq.core_concurrency、asynq.enrichment_concurrency、asynq.postprocess_concurrency、asynq.maintenance_concurrency、asynq.shared_concurrency、asynq.wiki_concurrency、model.max_concurrency | 全部未接；官方前六项需重启，最后一项可热更新后台模型限流 |
| 安全 | ssrf.whitelist、sandbox.docker_enabled | 未从原版系统设置接入；不据此断言本地所有安全边界缺失，本地有自身网络/凭据/权限约束 |
| 其它 | gallery.policy | 未接原版 registry |

## 关键差异及修复边界

| 编号 | 优先级 | 已核实差异 | 影响及最小修复方向 |
| --- | --- | --- | --- |
| S01 | P1 | “空间级”默认模型/记忆开关实际按 g.user.id 存取 | 同空间其他成员不受影响。先明确共享模型的访问范围，再对齐设置作用域；不能直接取消 owner 隔离。 |
| S02 | P1 | 默认页严格筛选 active，但合法模型 DTO 无 status | 页面误报已删除/不可用，影响选择。统一 DTO 与前端可用性契约。 |
| S03 | P1 | 默认 VLM/ASR 只保存、不投影 default_for/is_default | 新建 Agent 可能选错默认；修 S02 后本问题仍存在。补齐默认槽位的真实消费者。 |
| S04 | P1 | 消息索引配置/统计 404 | 当前入口报错，语义搜索/清空未接；需要实现索引业务或准确停止提供该功能。 |
| S05 | P1 | 助手名称/空间权限上限 404 | 不能配置全空间上限；实际仍受 Agent/平台只读限制，不能据此断言已越权。 |
| S06 | P1 | WeKnora 结构化记忆 UI 对接原生文件记忆 | 完整配置 501，条目/整理/导出 501。保留文件记忆和结构化业务的区别，不能把两者当同一数据模型。 |
| S07 | P2 | 沙箱只读 DTO 未被 UI 使用，双壳门控不同 | 一个壳显示“会话文件”并允许尝试编辑，另一个壳隐藏；写 410。应统一可见性与只读行为，并准确展示 OpenSandbox 类型。 |
| S08 | P2 | 模型 max_concurrency、MCP timeout/retry_count/retry_delay 保存后无消费者 | 配置看似有效但不起作用；官方 WeKnora 有对应后台模型限流链。当前本地 ModelCallLimitMiddleware 限模型调用次数，与并发上限不同。 |
| S09 | P2 | 清空模型上下文/输出/并发限制或最后一个请求头，前端省略字段，后端保留旧值 | 旧限制/旧 header 继续生效。用明确清除契约处理，避免将省略解释为清空；spec={} 已有独立清除兼容。 |
| S10 | P2 | 技能安装生命周期 UI 与 instructions_only 模式不一致 | 指令加载接通不代表脚本安装/执行接通。需要按实际执行模式呈现。 |
| S11 | P2 | 可达 Ollama/Cloud/解析/空间/成员/集成说明页超出本地能力 | 不能仅检查默认 12 项导航就声称所有设置无坏入口。 |
| S12 | P2 | 平台/空间角色标签及前后端密码策略不一致 | 角色展示会混淆权限来源，密码要求不一致影响直接 API 与界面行为；未发现该标签差异本身扩大权限的证据。 |

模型补充边界：Embedding/Rerank 的测试与调试真实调用已接，永久 KB 入库/检索仍由 ContextDB 管理；ASR 除测试外有聊天转写消费。普通模型 Key/请求头加密链已接，app_secret 可存不代表所有官方特殊厂商签名协议已实现。[模型构造][L12]

上下文压缩另有独立原生链：DeepAgents 0.7.35 默认组装 SummarizationMiddleware；有整数 max_input_tokens profile 时按 85% 触发、保留约 10%，无 profile 时为 170000 tokens/保留 6 messages。当前设置没有可配置此阈值的专用入口，聊天历史索引页和 utility_model_id 不控制该压缩。此处确认的是官方组装/配置链，未触发真实长对话压缩。[固定版本压缩实现][D02]

## 验证结果

| 验证 | 实际结果与范围 |
| --- | --- |
| 浏览器只读检查 | 核实双壳导航；复现消息索引错误、默认模型误报、沙箱类型/只读操作不一致；读取账号/成员/权限/健康/个人/助手/技能/MCP/记忆界面。未点击真实保存、删除或权限变更。 |
| 官方版本 | DeepAgents 0.7.35 官方 graph.py 与 summarization.py 联网下载后，与安装文件 SHA256 一致；WeKnora 按固定 commit 读取官方前后端源码。 |
| 前端设置相关 11 个测试文件 | **67 passed**；包括双壳路由、角色/capability、默认配置、历史、助手、沙箱、存储偏好。多数 UI 测试使用替身，未覆盖上述真实契约缺陷。 |
| 本地 PostgreSQL 后端 4 个测试文件 | `test_platform_memory_files.py`、`test_platform_sandbox_projection.py`、`test_platform_model_usage.py`、`test_platform_skill_runtime.py`：**31 passed**。隔离测试库，不写真实业务设置。 |
| 模型 runtime/LiteLLM/profile 3 文件 | **50 passed**，本机 HTTP fixture 验证实际 SDK 请求、协议、凭据隔离与 profile；非线上模型供应商验收。 |
| 原生 Harness | `test_harness_native.py`：**19 passed**。 |
| 文件记忆/沙箱/MCP policy 3 文件 | **30 passed，1 skipped**；与前述文件记忆测试重叠，不相加计算独立通过数。真实 OpenSandbox/Docker 端到端项被跳过。 |
| 平台管理相关测试 | 前端 ContextDBSettings/TenantInfo/TenantMembers **45 passed**；后端账号及绑定/身份隔离相关 **14 passed**。与前述 ContextDBSettings 有重叠，不能相加；保留组件的替身测试不能证明缺失后台已经实现。 |
| API/默认模型/作用域断言探针 | **13 项通过**；隔离 Flask、模拟记录存储，确认 404/410/501、只读响应、status 缺失、默认投影缺失和同空间两用户配置隔离。写请求在落库前拒绝。 |
| 模型清空断言探针 | 生产 save_model 合并逻辑、数据库/加密替身：确认省略字段保留旧限制和最后一个 header，显式空 headers 可清除。 |
| ContextDB 知识库背景检索 | 对“通用事业部”执行定向检索及降阈值复检，均无文档 chunks；没有将图谱或既有审计记录当官方证据。 |

断言探针和结果保存在 [验证目录](../../../output/verification/settings-integration-20261117/)。断言“通过”包括确认未实现接口确实拒绝，不表示这些功能可用。

## 官方和本地证据索引

进一步的逐字段调用链、固定行号和官方服务文件见同次核查明细：[资源与模型](../../../output/verification/settings-integration-20261117/resources.md)、[Agent 运行时](../../../output/verification/settings-integration-20261117/agent-runtime.md)、[平台与集成](../../../output/verification/settings-integration-20261117/admin-integrations.md)。明细中代码位置为仓库相对路径，本文的本地证据链接使用完整路径。

未改业务代码和真实设置。未验证线上供应商、外部 OAuth、真实 Docker 沙箱整链、CLI/Chrome/Claw 客户端兼容、真实 ACL 写入和生产负载；这些限制不能覆盖或消除已复现的契约缺口。

[L01]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/frontend/src/views/platform/index.vue:53>
[L02]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/webapi/auth.py:101>
[L03]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/frontend/src/views/settings/ContextDBSettings.vue:26>
[L04]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/webapi/auth.py:252>
[L05]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/frontend/src/views/settings/ContextDBPermissions.vue:25>
[L06]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/frontend/src/views/settings/GeneralSettings.vue:142>
[L07]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/frontend/src/views/settings/UserProfile.vue:1>
[L08]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/frontend/src/views/settings/AssistantSettings.vue:129>
[L09]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/agent/graph.py:34>
[L10]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/webapi/runtime_settings.py:468>
[L11]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/webapi/runtime_settings.py:23>
[L12]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/agent/models.py:190>
[L13]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/frontend/src/views/settings/DefaultSettings.vue:136>
[L14]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/agent/registry.py:162>
[L15]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/frontend/src/api/chat-history.ts:48>
[L16]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/frontend/src/views/settings/SandboxSettings.vue:27>
[L17]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/webapi/runtime_settings.py:350>
[L18]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/agent/sandbox.py:103>
[L19]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/webapi/skill_runtime.py:104>
[L20]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/agent/registry.py:232>
[L21]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/frontend/src/views/settings/MemoryWorkspaceSettings.vue:258>
[L22]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/agent/memory_files.py:6>
[L23]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/webapi/runtime_settings.py:510>
[L24]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/webapi/chat_resources.py:40>
[L25]: </Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/webapi/platform.py:19>
[W01]: https://github.com/Tencent/WeKnora/blob/cbdcebabf48c5ee2d6868b370326aa8341703f62/frontend/src/views/settings/Settings.vue
[W02]: https://github.com/Tencent/WeKnora/blob/cbdcebabf48c5ee2d6868b370326aa8341703f62/frontend/src/views/settings/GeneralSettings.vue
[W03]: https://github.com/Tencent/WeKnora/blob/cbdcebabf48c5ee2d6868b370326aa8341703f62/internal/application/service/model.go#L595
[W04]: https://github.com/Tencent/WeKnora/blob/cbdcebabf48c5ee2d6868b370326aa8341703f62/internal/types/default_settings.go#L62
[W05]: https://github.com/Tencent/WeKnora/blob/cbdcebabf48c5ee2d6868b370326aa8341703f62/internal/application/service/message.go#L389
[W06]: https://github.com/Tencent/WeKnora/blob/cbdcebabf48c5ee2d6868b370326aa8341703f62/internal/types/memory.go#L329
[W07]: https://github.com/Tencent/WeKnora/blob/cbdcebabf48c5ee2d6868b370326aa8341703f62/internal/router/routes_infra.go#L119
[W08]: https://github.com/Tencent/WeKnora/blob/cbdcebabf48c5ee2d6868b370326aa8341703f62/internal/application/service/weknoracloud.go#L37
[W09]: https://github.com/Tencent/WeKnora/blob/cbdcebabf48c5ee2d6868b370326aa8341703f62/internal/handler/system.go#L429
[W10]: https://github.com/Tencent/WeKnora/blob/cbdcebabf48c5ee2d6868b370326aa8341703f62/internal/application/service/web_search.go#L46
[W11]: https://github.com/Tencent/WeKnora/blob/cbdcebabf48c5ee2d6868b370326aa8341703f62/internal/application/service/vectorstore.go#L54
[W12]: https://github.com/Tencent/WeKnora/blob/cbdcebabf48c5ee2d6868b370326aa8341703f62/internal/application/service/storagebackend.go#L293
[W13]: https://github.com/Tencent/WeKnora/blob/cbdcebabf48c5ee2d6868b370326aa8341703f62/internal/application/service/system_setting.go#L103
[D01]: https://github.com/langchain-ai/deepagents/blob/deepagents%3D%3D0.7.35/libs/deepagents/deepagents/graph.py
[D02]: https://github.com/langchain-ai/deepagents/blob/deepagents%3D%3D0.7.35/libs/deepagents/deepagents/middleware/summarization.py#L294
