# DeepAgents 与 ContextDB 最终功能对齐方案

日期：2026 年 11 月 17 日。本文是实施方案，基于当前未提交工作区与实际安装的 DeepAgents 0.7.35、LangChain 1.5.0；分析结论与随后获授权的实施结果分开记录；实现验收见下方“实施结果与剩余门禁”。

**最终方向：ContextDB 知识与治理域保持现状，Agent 采用一套官方 DeepAgents SDK 执行链，WeKnora 作为可复用界面来源，移除其不需要的业务系统。** 保留最小 Web 宿主层负责账户、授权、凭据、文件传输、会话目录与展示协议。SDK 有能力不等于当前 Web 系统已完成该能力。

“完整”按两个验收范围记录：A 为本地 SDK、LangGraph 基础及实际 backend 的对接；B 为依赖 Agent Protocol 运行服务的异步子代理。用户随后明确授权部署并开放 B，因此本次新增免费的自托管 Docker 运行服务；实际状态与证据见下方实施结果。部署前的阻塞结论保留为分析记录，不能用它解释部署后的状态。

本文修正上轮中关于模型槽位删除、技能脚本、审批范围、异步部署和共享模块删除的过宽建议。前面的[设置审计](settings-integration-audit-20261117.md)保留为事实记录；实施取舍与边界以本文为准。

## 已核实的纠正

| 容易得出错误结论的位置 | 本轮事实 | 最终决定 |
| --- | --- | --- |
| VLM、ASR、utility 配置可以直接删 | 图片轮读 vlm_model_id，语音转写读 asr_model_id，标题生成读 utility_model_id，均有真实消费者 | 先迁移消费者/入口，保留旧记录，再移除多余表单与字段 |
| 有 Skills 加载和 execute 就能跑技能脚本 | 当前 Skill 仅注入 StateBackend；沙箱上传桥只接受 attachments/uploads，Shell 看不到虚拟 /state/skills | 补齐技能执行副本与真实路径，完成真实脚本验收后才能取消旧安装业务 |
| 文件 permissions 能限制全部执行 | 0.7.35 的规则只在内置文件工具层生效，不覆盖 Shell/direct backend；子代理还存在覆盖/不继承规则 | 继续保留平台授权、沙箱隔离和独立 execute 审批，并逐类验证子代理 |
| HITL 就是批准/修改/拒绝三按钮 | 实装 LangChain 支持按配置的 respond、条件审批、批量/逐项模式及一般 interrupt | 按服务端允许的决定和响应 schema 适配，不能仅保留旧 WeKnora 卡片 |
| 停止输出等于命令停止 | 当前 stop 取消 HTTP 内存任务；OpenSandbox adapter 使用线程调用远端 run，取消等待不保证远端命令停止 | 按官方命令 ID 中断/状态接口补接；分别验证流、Agent 和命令终止 |
| 自托管异步服务等于免费完整生产服务 | SDK 支持 Agent Protocol；官方生产 Agent Server 有独立许可条件，官方 MIT 示例仅供演示且无生产级持久/取消保证 | 不预设生产服务已解决，不扩写另一套自制运行器；B 范围单独过部署门禁 |
| 删除助手或模型页即可删共享模块 | 知识页仍导入 ModelSelector、页面上下文和数据变更刷新工具 | 先解除/迁移引用，再清理专属代码；ContextDB 页面不受损 |
| 所有最新文档能力都应算作 0.7.35 默认能力 | 此版计划工具是应用显式加官方 TodoListMiddleware；profile 为 Beta，SubAgent fork 为 experimental，未发现此版公开动态创建子代理实现 | 固定版本按源码验收；Beta/实验扩展单列，不用最新文档补造能力 |

## 不变的系统边界

1. ContextDB 的知识库、文档、上传入库、切片、检索、Wiki、图谱、评审、ACL、资料任务与治理 worker 保持现有职责和接口。Agent 仍通过当前成员身份、真实知识库/文档范围访问官方 MCP。
2. 本地执行继续调用 create_deep_agent、astream、aget_state、官方 checkpoint/Store 和 Command。HTTP/SSE、输入、身份和 UI 转换留在 adapter，不重写工具循环、任务调度器、Shell 或第二套执行状态库。
3. 模型继续使用已验证的现有客户端适配，不因界面收敛切换供应商或模型。模型名称、协议、能力和凭据必须真实匹配，不以未知能力填造窗口或输出上限。
4. Agent checkpoint、跨会话文件记忆与知识文档保持分开；保留当前 Agent/平台数据库及账号隔离。ContextDB 不承担 Agent checkpoint 存储。
5. 登录、平台成员、ContextDB Key 绑定、owner/session 隔离、凭据加密/脱敏、请求审计、文件鉴权保留。它们不是可删除的 WeKnora 附加业务。
6. 当前 ContextDB 只读和资源范围限制保持。通用 MCP 需要写工具时另作显式授权与审批映射，不能顺带扩大 ContextDB 权限；本方案不执行该权限变更。

## 原生能力最终矩阵

| 能力 | 最终形态 | 当前应补的内容与验收要求 |
| --- | --- | --- |
| 模型和 system_prompt | 主 Agent 与专业子代理分别选择模型、指令、生成参数 | 修复 status 缺失、默认模型、清空字段/headers；支持清除而非省略保留。错误不能静默换模型 |
| 普通工具与 MCP | 工具来源、选择、认证、资源与调用结果统一 | 保留现有远程 MCP；无实际执行消费者的高级字段移除或正确映射。不把 stdio 暴露为 Web 用户可任意启动宿主进程的配置 |
| 计划与待办 | 原生 todos 状态与官方 LangChain TodoListMiddleware | 保留当前显式接入，不再建设独立 WeKnora 计划/任务数据库 |
| 文件读写、搜索和删除 | 使用官方 backend 文件工具及原生二进制编码 | 保留读取、编辑、glob/grep、删除、上传、下载；不将任意工具返回路径视为已授权文件 |
| 命令与代码执行 | 保留 OpenSandboxBackend 一种实际执行方案，另有无 Shell 的 StateBackend 模式 | 保留隔离、网络策略、会话生命周期、执行结果；执行权限/审批独立于文件权限，默认不注入宿主密钥 |
| Skills 指令与参考资料 | 选择技能包后交官方 SkillsMiddleware 加载 | 包校验、来源文件、二进制资料和用户隔离保留；删除未实现的安装进度假象 |
| Skills 脚本 | 权威技能包与会话内执行副本分离，使用官方沙箱文件 API 写入真实工作目录 | 返回并使用真实执行路径；选定版本一致；依赖进入受控镜像。虚拟 AGENTS.md/Store 不暴露为宿主挂载；执行副本修改不能反写技能目录 |
| 长期记忆 | AGENTS.md 与 StoreBackend，按 owner+Agent namespace 隔离 | 简化成个人/Agent 文件记忆，迁移时保持旧 effective 状态，不自动从默认关闭变开启。区分读取、编辑、删除与关闭 |
| 记忆缓存 | 遵循 MemoryMiddleware 的 thread 缓存语义 | 文件外部编辑后默认新会话生效；如提供“刷新当前会话记忆”，使用明确原生状态操作并单独测试。移除 source 停止注入不等于删除缓存/文件 |
| 同步专业子代理 | 映射 SubAgent 的名称、描述、模型、指令、工具、技能、权限、审批和结构化输出 | 当前只自动有 general-purpose，需补声明式配置与正确继承；并行委派保持真实调用 ID 和子图归属 |
| CompiledSubAgent | 服务端可信 runnable 注册，不做任意 Python 上传页面 | 独立配置权限、状态、审批，不能假定继承父 Agent 的 HITL；用户只能选有权使用的注册项 |
| 异步子代理 | 使用 SDK AsyncSubAgent 与真实 Agent Protocol 服务 | 作为 B 范围，要求启动、查询、更新、取消、列表及等待交互均真实执行；详见部署门禁 |
| 审批和一般 interrupt | 按原生 interrupt ID、当前 checkpoint 和服务端 schema 展示及响应 | 显式允许时支持 approve/edit/reject/respond；未知类型有经验证的通用响应路径。过期、越权、重复、部分决定不误恢复 |
| 文本、工具、子代理流 | 沿用可用 WeKnora 展示，原生事件经 adapter 转换 | 保留 namespace、ToolCall ID、pending ID、真实错误/暂停/取消/完成；父子正文不混入，历史读取不启动执行 |
| 会话 checkpoint 和恢复 | 官方 PostgreSQL checkpointer 为执行状态权威来源 | 普通刷新只读；显式新输入或合法 Command 才执行。不将断线后的状态读取伪装成后台继续 |
| 分支和回退 | 保留当前原生 checkpoint 映射 | 不重放旧工具，不回滚沙箱文件、Store 记忆或外部工具副作用；分支不复制旧沙箱身份，且检查用户归属/并发/待审批状态 |
| 自动压缩和大结果卸载 | 保留 SDK 默认中间件及正确模型 profile | 不建设另一套“历史索引=上下文管理”；主图调用次数限制不宣称覆盖子代理/压缩的总费用 |
| 结构化输出 | 映射 response_format，保留 native structured_response | JSON Schema 可作普通高级配置；Tool/Provider/AutoStrategy 为服务端选择，不靠从回答文本猜 JSON 实现 |
| middleware、state/context schema、cache、debug/name | 服务端可信扩展配置 | state_schema 继承 DeepAgentState，保留原生稀疏/增量通道与 reducer。cache 启用时按身份/授权隔离；不允许普通用户上传任意 Python |
| HarnessProfile、ProviderProfile、RubricMiddleware | 保留固定版公开扩展，标注 Beta/高级选配 | 不能把三种 profile 概念混同；Rubric 与旧 reflection_enabled 不是同一业务。默认不强制启用，也不为其建大型设计器 |
| 动态子代理与实验 fork 模式 | 不作为 0.7.35 稳定默认承诺 | 该版明确支持的 SubAgent fork 单独标实验；运行时动态创建能力需以后固定升级版本另验收，不能把最新网页能力当已安装实现 |

此版 create_deep_agent 的 18 个公开构造参数均有归属：model/tools/system_prompt/subagents/skills/memory/permissions/backend/interrupt_on/response_format 为配置主面；middleware/state_schema/context_schema/cache/debug/name 为服务端高级扩展；checkpointer/store 为平台托管基础设施。不要求每个 Python 对象都有一个 UI 编辑器。

## 设置与界面最终结构

统一为一套设置外壳，保留平台/个人/ContextDB 原有功能；Agent 保留八组设置：模型、指令、工具与 MCP、技能、子代理、运行环境、记忆、权限与审批。结构化输出等放高级项，Python 类/回调只由服务端注册。

| 范围 | 确定的产品决定 |
| --- | --- |
| 模型作用域 | 沿用个人 owner 隔离和部署只读内置模型；“空间默认”更名“个人默认”。Agent/子代理显式配置优先，不新增一套空间共享模型授权系统 |
| 辅助模型 | 新普通表单不单设 utility 槽位；标题生成默认跟随个人主模型，旧绑定先保留兼容或显式迁移，不能先删消费者 |
| 视觉模型 | 新配置优先统一为具备图像能力的主模型；保留已有 VLM 绑定直至迁移，迁移时验证图片实际调用，不擅自静默换模型 |
| ASR | 不列入此次核心设置；移除独立语音入口时再退休转写调用/字段，历史文本保留。将来可作为普通工具选配 |
| 快速问答/智能推理 | 使用同一 DeepAgent；简洁问答作为指令/预算预设，旧配置按明确兼容规则迁移，不再暴露 Go RAG 参数 |
| 页面助手 | 合并到普通 Agent 面板；页面定位上下文可保留。先迁移知识页依赖的上下文/刷新工具，再移除专属 store/配置和重复入口 |
| 会话文件/产物 | 会话内上传、预览、下载与版本/归属校验保留；独立产物库/图片库不是目标必须项，可取消管理入口 |
| 运行环境 | 仅显示无 Shell 模式、已部署 OpenSandbox 的能力/健康/会话状态与必要操作；部署镜像、网络及受控 secret 注入由服务器配置，不复刻供应商平台 |
| 历史兼容 | 旧会话只读查看，停止旧执行，不自动重放；旧书签跳转保留项或显示明确停用结果，不继续挂载坏表单 |

## 删除清单与依赖限制

以下为移除产品功能、专属路由/控件和最终无引用代码的范围；不是立即删除数据库、共享目录或历史资源。

| 可移除的 WeKnora 业务 | 必须留下的边界 |
| --- | --- |
| 结构化记忆条目/主题/兴趣阈值/自动提炼/向量召回/整理 | 文件记忆、Store、namespace、默认关闭语义与可用编辑接口 |
| 消息向量索引、Embedding、索引统计/清空 | 会话消息、checkpoint、恢复、清空/删除与历史只读 |
| 本地 RAG、Embedding/Rerank/向量库/对象存储/DocReader 管理 | ContextDB 知识配置不动；共享 ModelSelector/model API 和聊天附件转换先做引用分析 |
| 多供应商沙箱向导、分配系统、技能安装/升级/重装对话 | 真实 backend/execute、技能包、运行镜像依赖、脚本传输、必要环境变量/secret 注入能力 |
| WeKnora Cloud、Ollama 服务安装启动与模型下载管理 | 模型连接和供应商适配保留；删除服务管理页不禁止以后用正确客户端接本地模型 |
| 浏览器扩展绑定、保险箱、专用浏览器产品和搜索供应商平台 | 普通受控 tools/MCP 扩展仍可接浏览器/搜索，不默认放开宿主浏览器或执行权限 |
| IM、嵌入、WeKnora API 发布/对外 MCP、CLI/Chrome/Claw 宣传页 | 现有 Web 登录及外部 MCP 客户端方向不能连带删除 |
| WeKnora 系统 registry、模型目录发布、Asynq、组织/多空间邀请/配额 | 本地成员、ContextDB 成员绑定/ACL、治理 worker、资料任务、评审及模型能力解析保留 |
| 未消费的并发/超时/重试等设置 | 保留真实运行限制；需要的参数必须实际传入正确客户端，未映射字段明确拒绝而不假保存 |

清理共享模块前检查 callers、imports、路由、测试、fixtures、i18n、CSS、依赖和许可证。文件名包含 weknora 的 adapter 可能正负责 native 文件、子图和审批投影，不按名称删除。

保留原始 upstream manifest、许可证与来源信息。原始 132 个 SFC、32 个依赖的 repository/commit/files/dependencies 基线不可刷新（SHA256 c4f0301d5bb109e94000a9342127ae1e2abc256113048b16540e81dc6b2b04a1）；已改为“保留来源严格 hash + reviewed adaptations/dispositions + 原生能力行为验收”。8 个来源条目已经退休，必须文件真实删除且无导入，其余 124 个 SFC 与 32 个依赖继续严格核对；许可证与原通知逐字保留。适配原因独立记录，不用来源 hash 代替能力测试。

## 异步能力与生产运行服务门禁

本次没有购买、订阅或启用新的收费服务，没有接入 LangSmith 或商业 Agent Server。模型与 ContextDB 沿用原配置，其原有调用仍可能产生费用。新增第三方开源 Aegra 0.11.0（Apache-2.0）与 Valkey 9.0.7（BSD-3-Clause），使用 Docker Compose 自托管；Aegra 不是 LangChain 官方 Agent Server。

用户的新部署授权取代了早期“不新增队列服务”的部署约束。本次实际新增 Valkey，不能再沿用“没有 Redis 类队列”的陈旧描述。执行继续复用 Aegra 官方 PostgreSQL、worker、lease/reaper 与 SDK graph，不另写 Agent 工具循环或第二套运行状态库。

- SDK AsyncSubAgent 对接 Agent Protocol，不要求只能使用 LangSmith 产品；但协议兼容不说明任何具体实现已通过许可、费用、持久化和隔离验收。
- 官方 standalone Agent Server 文档列出 LANGSMITH_API_KEY、LANGGRAPH_CLOUD_LICENSE_KEY 和许可验证/用量报告条件；不可当作 SDK 的免费 MIT 功能直接加入默认部署。
- 固定 0.7.35 仓库有异步服务示例，但 README 明确仅作演示。源码使用内存状态，取消接口也不足以证明真实调用已中止；不能复制示例就宣称完成生产后台执行。

**最终实施选择：保留已完成的 A，并按新增授权部署 B。** Aegra 0.11.0 原版并不能直接满足全部 SDK 契约：实际发现 HITL run 状态、Thread GET 缺少 values/interrupts、multitask 策略执行差异，部署层使用固定源码 SHA 门禁的兼容修补；没有把单纯健康检查当作完整验收。[部署、兼容修补与复现命令](../../guides/async-agent-runtime.md)记录具体版本、授权和实测边界。以下门禁仍是开放入口的条件。

| B 的开启条件 | 必须提供的实证 |
| --- | --- |
| 运行服务与许可 | 固定实现/版本、允许的生产用途及部署条件；不能只引用协议 LICENSE |
| 认证与资源边界 | 当前用户与远端 thread/run 归属、凭据最小化、端点验证、跨用户拒绝 |
| 耐久执行 | 浏览器断开后能执行，服务重启后任务及状态按承诺恢复，不靠进程内 task 字典 |
| 真取消/更新 | cancel 确实中止运行，后续完成不能覆盖取消；update 对执行中的任务有明确策略 |
| 人工交互 | 子代理 waiting/interrupt 可展示与合法恢复，Compiled/Async 不假定继承主审批 |
| 可观测和回收 | 真实 run/parent 关系、错误与终态、沙箱/资源回收；保持 SDK 原生状态权威 |

## 权限和副作用规则

1. 每次执行由服务端绑定 owner、session、Agent、知识范围；不信任前端自报身份、子代理 ID、权限或工具结果。
2. SubAgent 显式 permissions/interrupt_on 可覆盖继承；Compiled/Async 不自动继承父 HITL。配置和执行阶段都不得允许超出宿主用户授权上限。
3. 文件 read/write 规则、execute 审批、沙箱隔离和网络策略各有职责，不以提示词或文件规则代替 Shell 隔离。直接 backend 调用也必须位于已验证的 adapter 边界。
4. stop、断线取消、命令中断、环境销毁是不同动作。优先接 OpenSandbox 官方 execution_id 中断/状态接口；当前 adapter 不能获得 ID 时如实标受限，不返回虚假的“命令已停止”。
5. 当前 HTTP 取消句柄只在单进程内可见；多 API worker/副本上线前须验证取消路由归属或采用真实运行服务，不能直接横向扩容后宣称一致。
6. 回退只恢复 checkpoint。沙箱文件、Store 记忆和外部 API 副作用不自动回滚；UI 明确范围。清空/删除父会话先停止并删除其远端线程及子沙箱，失败保留父会话和授权供重试，再处理原父沙箱、checkpoint 与会话；不删除跨会话记忆。分叉不复制远端 async_tasks 身份，避免把旧父会话的后台任务归给新会话。

## 实施顺序与退出条件

| 阶段 | 实施范围 | 完成条件 |
| --- | --- | --- |
| 1 固定契约 | 固定 SDK/依赖版本、保留/移除矩阵、数据作用域、旧路由与共享模块调用图；调整 UI 来源验收目标 | 每个保留字段有原生参数或明确宿主消费者；每个删除项有引用和历史处理记录 |
| 2 修正现有主链 | 模型 DTO、默认/清空、记忆开关及文件 UI、旧模型/模式/助手消费者迁移；保持全部历史可读 | 合法模型可选，旧字段没有悬空引用，个人/Agent 作用域准确，ContextDB 回归无变化 |
| 3 补齐原生能力 | 专业/可信编译子代理、结构化输出、通用 interrupt/审批、技能真实脚本路径、执行取消与子图展示 | 正常执行、审批、拒绝、恢复、错误和文件结果均经真实 native API 可复现 |
| 4 收敛界面与清理 | 统一设置壳，去掉无实现和不需要的 WeKnora 入口，再清专属调用/配置/测试/依赖 | 不留坏深链接、孤立导入或假保存；完整构建/类型/相关测试通过，知识域不受影响 |
| 5 A 范围验收 | 真沙箱、文件二进制、子代理权限、重启、断线与副作用边界 | 下表 A 项全部过关后才宣布 SDK 主链完成；不能用测试替身代替真实 backend 验收 |
| 6 B 部署门禁 | 仅在具体运行服务满足许可及生产条件后实施 AsyncSubAgent | B 表全部通过后才宣布含异步的全量 SDK 完成；否则保留明确未部署状态 |

迁移只做有据可查的必要转换，不静默改模型、扩大权限、开启记忆、删除凭据或清库。先停止旧功能新写/旧执行，保留只读兼容；物理数据清理不属于本方案实施范围。

## 必须验收的行为

| 编号 | 验收场景 | 通过标准 |
| --- | --- | --- |
| A01 | ContextDB 知识/评审/Wiki/图谱/资料任务/ACL 回归 | 原始接口、资源 ID、引用与用户权限不变；工具失败不能伪造来源 |
| A02 | 账户与跨用户访问 | session、文件、记忆、MCP/模型凭据不能跨 owner；子代理也不能越权 |
| A03 | 模型和默认 | 无 status 合法模型不误排除；个人默认、Agent/子代理覆盖和协议一致；清空限制/header 真正清除 |
| A04 | 图片/标题/语音退休迁移 | 原 VLM/utility 无悬空引用；图片真实进入有图像能力的模型。取消语音入口时历史转写仍可读 |
| A05 | 计划与专业子代理 | todos 更新、专业模型/工具选择、并行调用与子图归属正确；父子文本隔离 |
| A06 | 四类 Agent 权限 | 主图、SubAgent、CompiledSubAgent、已部署 AsyncSubAgent 的身份、权限与审批逐项验证，不靠继承假设 |
| A07 | 审批和提问 | 允许时 approve/edit/reject/respond、条件/批量行为真实；过期/重复/伪造响应不重复执行 |
| A08 | 结构化输出 | SDK 产生且校验 structured_response；结构化结果和普通文本不相互冒充 |
| A09 | Skill 指令与脚本 | 二进制参考资料可读；选定脚本在真实沙箱路径执行，依赖可用，修改执行副本不污染目录 |
| A10 | 记忆 | 重启后文件存在；跨线程共享范围与跨用户/Agent 隔离正确；关闭不删除；新会话/显式刷新生效时机准确 |
| A11 | 流与终态 | 文本、工具、子代理、错误、暂停、取消、完成来自实际原生状态；重连不自动重放副作用 |
| A12 | stop 与远端命令 | HTTP、Agent iterator、远端命令分别验证中止或明确不支持；取消状态不会被稍后完成覆盖 |
| A13 | checkpoint/分支/回退 | 无新模型/工具执行；选定状态正确，新分支不共用旧沙箱；UI不承诺外部回滚 |
| A14 | 文件与环境回收 | 文本/二进制上传下载、版本与过期错误准确；销毁失败可重试，不能先删记录丢失回收能力 |
| A15 | 旧路由与历史 | 旧书签无坏控件，旧会话只读，不自动迁移重放；历史资源和凭据数据保留 |
| A16 | SDK 高级扩展 | state 继承 DeepAgentState，schema/reducer 不损坏原生状态；Beta/预算/模型能力约束真实，未启用扩展不误报支持 |
| A17 | Web 构建和来源 | 共享知识页不受损；保留组件许可证/来源可追溯，实际行为门禁通过，不通过刷新基线掩盖差异 |
| B01 | 异步启动/查询/更新/取消/列表 | 真实 Agent Protocol 服务执行，状态和结果与实际 run 一致 |
| B02 | 异步断线与重启 | 按部署承诺耐久恢复，无进程内假任务；waiting 交互、终态和资源回收正确 |

## 实施结果与剩余门禁

以下是当前代码与验收结果，不将方案表中的“应补”文字当作已经完成的证据。没有删除原业务数据库、历史会话、模型绑定或凭据。

| 范围 | 最终实现 | 验证与限制 |
| --- | --- | --- |
| 设置与模型 | 一套设置壳；个人默认；模型缺省 status、参数/header 清空、utility/VLM/ASR 旧绑定兼容；ContextDB 知识配置不改 | 模型/默认/编辑器实际 HTTP 与组件行为测试；视觉能力按真实模型属性检查，不自动换供应商 |
| 记忆 | 个人开关与 owner+Agent Store 文件；保持原关闭状态，关闭不删除，文件读取失败不允许覆盖 | PostgreSQL 重开、跨用户/Agent、关闭、缓存及草稿保护测试。线程内 AGENTS.md 文件上下文与跨会话 Store 文件分开 |
| 专业子代理 | 声明式模型、指令、工具/技能、权限、HITL、输出结构；可信编译扩展 | 固定 SDK 实测。省略 system_prompt 继承父自定义指令，显式空串清空；子 response_format 省略/null 为普通输出，不强制继承父格式 |
| 只读与沙箱权限 | 只读专业子代理经官方 create_deep_agent 编译为 CompiledSubAgent，使用无 execute 的官方 CompositeBackend 文件视图 | 此版可执行 backend 只支持虚拟挂载路径上的文件规则；真实 /workspace 规则明确拒绝。Shell 权限仍由运行隔离与独立审批承担 |
| 审批与一般中断 | 按原生 ID/schema 支持 approve/edit/reject/respond 与一般 JSON 响应；响应不符合结构、过期、重复、越权均拒绝 | 实际 SDK、PostgreSQL、HTTP 恢复测试覆盖 false/null、批量与逐项响应；respond 不运行原工具。args_schema 在此版 SDK 未使用，配置入口明确拒绝，不假保存 |
| 结构化结果 | SDK structured_response 原值进入 SSE/历史；以官方更新/检查点通道版本区分有效 null 与未产出 | 实际 ProviderStrategy nullable 输出及多轮历史测试；不从正文猜 JSON，不把上一轮结果带到下一轮 |
| Skills | 目录导入、文件浏览、历史引用保护；无虚构安装状态；脚本副本写到 /workspace/skills | 真实 SDK 文件 API、二进制资料、真实脚本与目录不回写测试。依赖由部署镜像提供；子代理技能选择约束注入和虚拟来源，不承诺共享沙箱内的进程文件隔离 |
| 停止执行 | 记录官方命令 ID，停止 HTTP 请求时 interrupt 并核查远端状态；并行命令全部尝试取消，失败不报告停止成功 | 真实沙箱脚本和并行取消、HTTP→Agent→官方执行 ID 停止链验证。仍仅支持单 API 进程取消句柄 |
| 清理与历史 | 删除 46 个退休页面、独占安装依赖及对应页面测试；旧入口显示停用，保留有 caller 的知识、模型、文件组件 | 全量前端回归、类型、生产构建、来源门禁；只读历史不触发模型或工具执行 |
| Beta 高级项 | middleware/state/context/cache/name/debug 等走可信 Python 扩展；无普通用户上传 Python 入口 | Harness/Provider/Rubric 不宣称默认启用。尤其 ProviderProfile 的模型构造钩子不被当前 ChatLiteLLM 实例路径消费，此项为未启用选配，不能用注册说明算验收 |
| 异步 B 范围 | 自托管 Docker Aegra + Valkey；SDK 原生 start/check/update/cancel/list，按当前用户与固定授权快照构建子图 | 真实委派、waiting/审批/恢复、false/null、Shell 与排队取消、SIGKILL 同 thread/run 恢复、36 项 HTTP 隔离已通过。同线程 FIFO、异线程并行、interrupt 真停及 reject=409 均通过，入口已启用并经浏览器确认；单机部署不宣称 HA、零丢失或外部副作用 exactly-once |

最近验收分组及实际命令/结果记录在[实施验收台账](../../../output/verification/deepagents-native-implementation-20261117/validation.json)。最终前端全量 2920 passed、1 skipped；后端核心 184 passed、1 skipped；最终运行组（包含真实 OpenSandbox 和附件解析）49 passed。测试组存在重叠，不相加作为总数。测试中的 ContextDB、模型/OAuth 使用本地契约服务或隔离替身；真实 OpenSandbox 测试连接本机 Docker 服务。它们不等于生产外部供应商、云端 ContextDB 或负载验收。浏览器先只读核实统一设置、文件记忆、运行环境、Skills 与原生配置面板；随后在临时测试会话实际提交子代理审批并读到完成结果，确认后台异步可选，临时配置撤销、临时模型和会话已清理，未保存用户 Agent 或修改其模型、记忆设置。

B 的本次交付证据还包括：[36 项真实 HTTP 隔离](../../../output/verification/deepagents-native-implementation-20261117/async-scope.json)、[审批与更新](../../../output/verification/async-approval-acceptance.json)、[同线程策略及异线程并行](../../../output/verification/deepagents-native-implementation-20261117/async-multitask.json)、[真实取消与服务 SIGKILL 恢复](../../../output/verification/deepagents-native-implementation-20261117/async-recovery.json)。主应用已启用 `agents.async`；入口在“智能体 → 原生智能体配置 → 专业子代理 → 运行方式 → 后台异步”，无需用户另行部署。SDK 原生 `check_async_task` 已实际取回远端完成答案，不仅验证网页展示。

## 本轮精准修复与来源收尾

用户要求按建议精准修复后，再次沿实际调用链复核。本节记录该轮修复范围；上节已执行的验收数字属于此前交付。本轮最终前端全量 2776 passed、1 skipped；后端核心及媒体回归 247 passed、5 skipped，另完成实际 Docker 异步运行、并发与 36 项 HTTP 授权检查。类型检查、构建和来源门禁通过，主应用 API 已重启加载修复，异步服务为 healthy。命令、实际结果和剩余限制统一写入[精准修复验收台账](../../../output/verification/agent-precise-fixes-20261117/validation.json)。

| 范围 | 本轮处理及应验证的边界 |
| --- | --- |
| 原生异步任务状态 | 从真实远端 thread/run 读取 waiting、结果、消息及中断；父任务快照和刷新必须保持 SDK 原生状态语义，不用页面状态伪造完成 |
| 原生恢复校验 | 原始 Harness 与网页响应共用 JSON Schema、原生中断 ID、批量决定及允许操作校验；拒绝不合规响应时保留 checkpoint，可正确重提后恢复 |
| 任务发现与轮询 | 原生 async_tasks 更新投影为现有 work 事件，空列表也能发现新任务；run_id 变化能唤醒观察，全部终态后停止周期请求。浏览器连续约 6 分钟观察未再请求 |
| 同型并发子任务 | 同步 task 按原生 parent_tool_call_id 关联，两个同类子代理不按名称猜测或覆盖 |
| 子会话交互 | 复用现有 AskUserCard、ToolApprovalCard 和本地 NativeInterruptCard；通过可选 transport 绑定所属子线程，保留主会话默认提交路径；按实际 interrupt ID 和 allowed_decisions 响应，批量暂存不冒充已执行恢复 |
| 详情及并发隔离 | ChildAgentStream 的可选刷新标识触发所属子会话更新；观察的是原生 history/checkpoint，按刷新和轮询更新展示，不宣称 token 实时流。提示答案 Map 在对应 dock 内隔离；owner/session 切换时丢弃迟到请求、重置子会话草稿，不污染主会话或其他后台任务 |
| 子会话产物 | 复用原 ChatArtifactsDrawer，只读预览、下载真实产物；base64 非图片媒体从已保存消息只读投影为原产物下载，不宣称内嵌 audio/video 播放器，也不新增产物创建、编辑或删除接口 |
| 生命周期 | 更新、恢复、取消、父会话清空/删除和 checkpoint 回退须互斥；外部清理失败保留授权和父会话供重试；回退不复制旧异步任务身份或撤销外部副作用 |
| 退役业务链 | 删除无实际消费者的集成展示、组织分享、自动化和独立 embed 页面及专属依赖/测试；旧入口安全重定向。Agent 编辑器不再隐藏挂载分享面板或请求旧渠道计数，历史自动化会话保留只读标识 |
| 输入与共享域 | 删除浏览器执行、steering 控件、队列和请求调用；继续保留发送/停止、附件、知识库选择、AssistantPanel 的实际 embeddedMode，以及有真实调用的 ContextDB 组织/用户/ACL、模型、文件、预览和引用 API |
| 运行指南 | 当前链路为 WeKnora 组件 → 应用 API → Deep Agents graph；异步为 SDK → 自托管 Aegra + Valkey。删除“Vue SDK 流主链”“无 Redis 类队列”等旧描述；本轮没有新增服务、修改用户模型/记忆配置或清理用户数据 |

来源核验继续固定 Tencent/WeKnora commit `cbdcebabf48c5ee2d6868b370326aa8341703f62`。原 `files` 132 项和 `dependencies` 32 项的记录、`repository`、`commit` 及合并 SHA256 `c4f0301d5bb109e94000a9342127ae1e2abc256113048b16540e81dc6b2b04a1` 不变，`UPSTREAM-LICENSE` 和项目许可证原文不变。

在这 164 项中，新增退役的 `AgentShareSettings.vue` 与此前 8 项一起使用显式 `retired` disposition；退役文件必须不存在且无残留 import，不能用删除基线记录来绕过门禁。其它本轮删除的业务页面不冒充原基线中的条目。保留组件只为已审查的模板、样式和交互更新 `adaptations`；样式适配路径逐项列明。`usePromptDock`、`suspendedRun`、`collaborationDisplay` 原来未纳入这 164 项，另以 `localSources` 记录固定版本上游原文摘要与当前适配摘要；NativeInterruptCard 明确记为本地原生中断桥接组件，不声称是 WeKnora 官方原样代码。这些记录只用于审查门禁，不引入运行时注册机制。

本轮必须重新验证远端 SDK check/update/cancel、子代理真实中断恢复及父 checkpoint 快照、清理/回退竞争、前端测试/类型/构建和来源门禁。单独的健康检查、源码摘要匹配或组件替身测试均不能代替真实运行链验收；外部模型/OAuth、云端 ContextDB 与生产负载仍以明确执行的验收范围为限。

## 分析阶段基线证据

- 重新读取实际 create_deep_agent 签名，确认公开参数 18 项；检查安装源码的默认 middleware、子代理类型、文件权限和缓存语义，并联网核对固定 tag。
- 最小隔离断言确认：Skill 脚本已存在于虚拟 FileData，但现沙箱附件桥拒绝 /skills 路径；此版 TodoListMiddleware 由本地显式接入，不是 create_deep_agent 默认注入。无真实数据库/配置写入。
- 后端 7 文件：test_harness_native、test_platform_time_travel、test_platform_native_prompt_ids、test_platform_memory_files、test_platform_skill_runtime、test_platform_mcp_policy、test_platform_sandbox：71 passed，1 skipped；跳过真实 OpenSandbox/Docker 项。
- 前端双壳、Agent 编辑、运行配置、资源、工具箱和原生 pending ID 相关 7 文件：37 passed。
- 以上仅是实施前分析阶段的基线，后续实施和异步部署以本文“实施结果”及台账为准。外部模型/OAuth、云端 ContextDB 与生产负载不在本次隔离验收范围。

## 主要原始来源

- [固定版 create_deep_agent 与参数和继承说明](https://github.com/langchain-ai/deepagents/blob/deepagents%3D%3D0.7.35/libs/deepagents/deepagents/graph.py#L292)
- [固定版 SubAgent](https://github.com/langchain-ai/deepagents/blob/deepagents%3D%3D0.7.35/libs/deepagents/deepagents/middleware/subagents.py)
- [固定版 AsyncSubAgent](https://github.com/langchain-ai/deepagents/blob/deepagents%3D%3D0.7.35/libs/deepagents/deepagents/middleware/async_subagents.py#L66)
- [固定版文件工具与权限](https://github.com/langchain-ai/deepagents/blob/deepagents%3D%3D0.7.35/libs/deepagents/deepagents/middleware/filesystem.py)
- [固定版文件记忆](https://github.com/langchain-ai/deepagents/blob/deepagents%3D%3D0.7.35/libs/deepagents/deepagents/middleware/memory.py)
- [固定版技能中间件](https://github.com/langchain-ai/deepagents/blob/deepagents%3D%3D0.7.35/libs/deepagents/deepagents/middleware/skills.py)
- [固定版 HarnessProfile](https://github.com/langchain-ai/deepagents/blob/deepagents%3D%3D0.7.35/libs/deepagents/deepagents/profiles/harness/harness_profiles.py)
- [固定版 RubricMiddleware](https://github.com/langchain-ai/deepagents/blob/deepagents%3D%3D0.7.35/libs/deepagents/deepagents/middleware/rubric.py)
- [官方 HITL 配置与响应机制](https://docs.langchain.com/oss/python/deepagents/human-in-the-loop)
- [官方生产 Agent Server 部署前提](https://docs.langchain.com/langsmith/deploy-standalone-server#prerequisites)
- [固定版异步服务演示的范围声明](https://github.com/langchain-ai/deepagents/blob/deepagents%3D%3D0.7.35/examples/async-subagent-server/README.md)
- [固定版异步演示服务器实现](https://github.com/langchain-ai/deepagents/blob/deepagents%3D%3D0.7.35/examples/async-subagent-server/server.py)

本地重点证据：[原生组装](</Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/agent/graph.py:34>)、[技能准备](</Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/agent/harness_config.py:13>)、[沙箱与文件桥](</Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/agent/sandbox.py:103>)、[记忆作用域](</Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/agent/memory_files.py:6>)、[checkpoint 和 Store](</Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/agent/checkpointer.py:1>)、[状态回退](</Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/agent/time_travel.py:1>)、[标题消费者](</Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/agent/session_titles.py:128>)、[图片模型消费者](</Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/agent/config.py:357>)、[语音消费者](</Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/webapi/chat_resources.py:365>)、[HTTP 执行适配](</Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/webapi/harness.py:177>)、[停止接口](</Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/webapi/agent.py:303>)、[平台鉴权](</Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/webapi/auth.py:101>)、[双壳入口](</Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/frontend/src/views/platform/index.vue:53>)、[现有上游门禁](</Users/pusonglin/PycharmProjects/ShowDoc AI Assistant/frontend/src/official-agent-ui.test.ts:20>)。其它字段与函数可从前述设置审计追溯。
