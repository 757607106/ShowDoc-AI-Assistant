# DeepAgents / WeKnora 精准修复与对齐记录

日期：2026-11-17。修复对象是当前工作树；保留任务开始前的 11 个未提交文件，不迁移历史配置、不修改第三方 SDK、不升级依赖。

## 固定依据与运行边界

- DeepAgents 固定 `0.7.35`，官方源码提交为 [`18930b5463c8a0a432353db5299af280f879973f`](https://github.com/langchain-ai/deepagents/tree/18930b5463c8a0a432353db5299af280f879973f/libs/deepagents)。
- WeKnora 前端原始基线为 [`cbdcebabf48c5ee2d6868b370326aa8341703f62`](https://github.com/Tencent/WeKnora/tree/cbdcebabf48c5ee2d6868b370326aa8341703f62/frontend)。补充核对上游 Go 业务语义的快照为 `7d064bc3a259f87634840199f565ec4dd644ba1e`，不以当前 main 自动替换本地基线。
- `quick-answer` / `smart-reasoning` 是项目业务模式，不是 DeepAgents 原生模式。quick 的 8 步、0.3 温度、`allowed_tools=null` 来自本项目静态 `BUILTINS`，不能称为官方默认。
- ContextDB 保持唯一知识检索源；权限、成员凭据、知识库及文档作用域继续由现有信任边界校验。没有添加本地 RAG、重排、Wiki 全文读取或 REST 检索兜底。

```text
WeKnora 原有页面 / 流处理器
  → 业务 HTTP / SSE Adapter：鉴权、配置解析、卡片与事件投影
  → create_deep_agent / astream / aget_state / interrupt / Command
  → 官方 PostgreSQL checkpoint / Store
  → 当前成员可使用的 ContextDB 官方 MCP 工具
```

## 修复清单与实际语义

| 项目 | 后端 | 前端 | 验收证据位置 |
| --- | --- | --- | --- |
| 运行默认配置 | `/agents/type-presets` 保留 `data`，追加来自静态配置的 `runtime_defaults` 和 quick 控制范围列表，不包含用户模型 ID | 新建和主动切换采用当前运行设置；不再把 Go RAG 的 `[]/1/context_template` 默认注入本 Harness | `test_agent_configuration.py`、`AgentEditorModal.runtime.test.ts` |
| 历史配置 | GET 保留真实 `retain_retrieval_history=false`；`config_issues` 与执行拒绝复用按值校验 | 原样展示不兼容值，列出修改前后差异，显式采用仅修改草稿，保存才落库；失败重试保留用户输入 | 同上；旧配置读前后持久记录不变 |
| 系统模板引用 | 保存时验证 owner/category；新轮解析有效正文写入 resolved config；resume 使用本轮快照 | 未改模板保存引用，修改正文后保存完整文本并清除陈旧引用 | 配置测试覆盖缺失、重复、跨用户、类别及本轮快照 |
| 未接能力 | 能力接口明确关闭 `agents.steering`、`agents.browser`，原拒绝路由保留；历史队列 GET 同时返回 `items` 与兼容字段 `data` | 缺失/false/探测失败均关闭发送与轮询；历史队列可读不可写，输入与附件保留 | deploymentCapabilities / Input-field / Toolbox / steerInteraction、legacy queued API 测试 |
| 问卷 ID | `ToolRuntime.tool_call_id` 写入原生 interrupt；不再用根图工具候选集合拒绝子图原生 ID；旧数据仍仅接受唯一可验证匹配 | 保留原卡片、时间线及恢复逻辑 | `test_platform_native_prompt_ids.py`、`useChatStreamHandler.nativePromptIds.test.ts` |
| 子图恢复投影 | 官方恢复工具节点的 `tasks.input` 是 ToolCall 列表，不作为消息 state 初始化；模型任务的字典 state 仍投影完整子图消息 | 原子代理界面不变 | 主图/子图并行问卷 HTTP→history→逐项回答→resume 回归 |
| 模型窗口 | 有效 C/O 映射标准 `profile.max_input_tokens/max_output_tokens`；C 为 `spec > raw > 未知`，O 保留 `spec > raw > 精确目录 > 未知`；不把 SDK 输入上限当作总 C | 只读显示 effective capabilities，编辑保留 raw；预览请求包含当前 C/O；六语言说明和占位提示保持一致 | `test_model_profile.py`、模型编辑及 contextWindow 测试 |
| 调用超时 | 缺省和 0 的运行兜底为 120 秒，显式正值（含 180）保留，null 仍非法；沿用客户端 timeout | 六语言明确持续流可能超过该时长，不承诺总时长强制中止 | 配置、模型构建及本地 HTTP stream 测试 |
| 工具目录 | 不再自动加入当前 MCP 目录没有的 `wiki_read_page`；历史 alias 保留 | 自动选择依据真实目录，保留历史展示；不把元数据查询宣称为正文读取 | 配置 alias、工具目录及编辑器回归 |
| 源码来源 | 原始上游哈希保留，适配项另记精确本地哈希、原因与本记录链接 | 不改变现有视觉系统，不把必要适配称为逐字一致 | `UPSTREAM-AGENT-UI.json`、`official-agent-ui.test.ts` |

Agent 与检索时间线的思考和工具步骤复用本地 Kubai SVG 图标。图标沿用 18 px 的尺寸，运行中轻微位移，历史步骤和开启减少动态效果时显示静态图标。
原生工具按语义归入现有图标，未知工具使用工具箱。等待子任务显示时钟，等待审批显示静态盾牌。

`null` 表示平台默认业务工具集合，显式 `[]` 表示不选择这些业务工具；二者不等价，也不代表移除了所有 DeepAgents 中间件工具。旧 quick 的 `max_iterations=1`、显式 `[]`、关闭的改写开关及 `fallback_strategy=model` 仍合法，显式修复不覆盖这些受支持选择。

默认配置首次加载失败时，编辑旧记录不混入 Go 表单默认值；重试仅补缺省、未编辑的原生字段，保留等待期间填写的迭代数、权限和提示词。旧 quick 的不支持沙箱值也列入差异预览，仅明确采用后切回规范 StateBackend；空值、StateBackend 与已接入的 OpenSandbox 保持原值。界面历史工具项只显示目录外名称说明，实际 MCP 工具使用目录原描述；`knowledge.get_document` 不承诺正文或分页读取。

## 复核后本轮修复的五项问题

本轮只处理下列已复现问题。先补失败回归，再修改共享根因；此前全量测试通过并未覆盖这些边界，不能据此称所有组合均已对齐。

1. **父图和子代理并行提问 501**：动态子图 interrupt 会冒泡到根 snapshot，但子图的工具调用不一定出现在根 messages。`webapi/weknora_prompts.py` 仅移除这项跨命名空间候选匹配，仍验证原生 ID 非空字符串。答案继续按 interrupt ID 经官方 `Command(resume=...)` 恢复；owner、session、checkpoint 和旧数据唯一匹配校验保留。同文/异文两项真实 HTTP 回归覆盖 SSE、刷新历史、逐卡回答及父子分别恢复。
2. **清空正文仍执行旧模板**：系统提示词真实 input 事件清除旧 `system_prompt_id`，现有必填校验拒绝空串及空白；初始化、未编辑的未解析引用、主动模板选择仍保留引用。真实 Chrome 验证清空时无 PUT、数据库不变；重新输入后 PUT 200 且旧 ID 删除。本轮 resume 仍使用冻结正文，新轮重新解析模板。
3. **输入上限误当总上下文窗口**：LiteLLM 的 `max_input_tokens` 不足以证明总 C，所有供应商统一只采用现有 `parameters.spec.context_window` 或 `parameters.context_window`，否则未知；不新增目录或硬编码型号表，不改写历史配置。目录中的输出上限和其他能力继续可用。LangChain [标准 profile](https://github.com/langchain-ai/langchain/blob/a4b4a7b9a6d8b5eb2352e26e110f1b7beffc6f62/libs/core/langchain_core/language_models/model_profile.py#L49) 将其同名字段定义为总上下文窗口，不能直接复用另一目录的字段语义。[阿里云官方表](https://help.aliyun.com/en/model-studio/qwen-plus) 分别列出输入长度与总窗口；`qwen-plus-2025-01-25`、`qwen-plus-2025-04-28` 的总 C 均为 131072。通过现有字段显式设置该 C 后，4096 输出预算得到原生输入预算 120422；缺 C 时走官方未知窗口策略。
4. **超时说明承诺不成立**：仅修正六语言说明，说明实际行为由模型客户端决定、持续流可能超过配置时长。保持现有 120 秒默认和显式值，不新增全局计时中止器。本地兼容链路实测 1 秒 timeout 下持续流超过 1 秒仍完成，流间隔超时则报错。
5. **旧排队消息刷新消失**：既有 UI hydration 读取 `items`，GET 以前只返回 `data`。现在同一批 rows 同时返回两字段，对齐 [WeKnora ListSteerMessages](https://github.com/Tencent/WeKnora/blob/cbdcebabf48c5ee2d6868b370326aa8341703f62/internal/handler/session/steer.go#L736-L773) 的 `items` 契约并保留旧调用方。只读标识、写接口 410 和能力关闭不变，不伪造活跃 assistant ID、不恢复旧执行器。

兼容性影响：未显式配置 C 的模型将显示未知，并采用 DeepAgents 原生未知窗口策略；不会自动采用 SDK 输入上限，也不会推算 `I + O`。已保存的显式值不迁移，准确性仍取决于填写的厂商数据。

## 保留官方机制，不扩展执行功能

官方 [摘要源码](https://github.com/langchain-ai/deepagents/blob/18930b5463c8a0a432353db5299af280f879973f/libs/deepagents/deepagents/middleware/summarization.py) 在已知窗口时使用原生比例阈值，并计算 `max(0, int(C * 0.95) - 实际输出预算)`。传入完整 C，不提前扣减 O；32768 窗口与 4096 输出预算的输入预算为 27033。没有准确窗口时仍采用官方未知窗口策略，不承诺真实容量。

摘要、溢出恢复及 ToolMessage artifact 保留；`retain_retrieval_history=true` 不等于工具正文永不压缩。主图最大步数不等于主图、子代理、摘要和重试的供应商请求总数，本次没有增加全局额度系统。默认 general-purpose 子代理的上下文与记忆继承按官方构建规则，不自动复制父级全部提示词或历史。

原生 StateBackend 会话文件与受 owner/Agent 命名空间约束的 StoreBackend 文件记忆保留。没有增加结构化记忆、整理/晋升服务，也没有扩建浏览器、steering、后台续跑或新的审批调度器。120 秒是本项目统一的默认策略，与 [WeKnora 默认值](https://github.com/Tencent/WeKnora/blob/7d064bc3a259f87634840199f565ec4dd644ba1e/internal/agent/const.go#L31) 一致，不是 DeepAgents 强制值；本地流测试仅证明当前安装适配链路的超时语义。

问卷修复的原问题是 tool_call_id 绑定错误影响展示。既有复现中回答按 interrupt ID 正确恢复，不能将其描述成已证实的答案串线。聊天图片未做像素解码与最大步数不限制全部供应商请求，也不作为本次官方对齐缺陷扩展生产逻辑。

## 源码适配账本的审查范围

原始 `files` / `dependencies` 哈希仍指向固定上游。额外 `adaptations` 只允许已审查文件的准确内容，后续任何未登记变更继续失败：

- 本轮：Agent 表单的运行默认与显式兼容修复、steering/browser 能力门禁、模型 effective/unknown 展示。
- 既有 ContextDB 适配：引用使用真实切片、显示文档名称与附件、结果弹层保留原始资源、预览请求代际隔离及上传 HTML 的清理与 iframe 隔离。
- 既有 `ChatArtifactsPanel` 保留后端真实错误说明，不能覆盖任务开始前的改动。
- 旧 `tool-results/DocMarkdown.vue` 已迁移到共享 `src/components/DocMarkdown.vue`，组件参数为 `content` 并承担现有资源/附件渲染。其 template、source、styles 均登记为明确既有差异，不能称为纯 import 重定位。
- 外部来源正文预览可传入源站基础地址。共享渲染器在净化阶段将相对图片地址解析到源站，ContextDB 原件的受保护资源沿用现有加载路径。
- 桌面工作区和停靠助手共用外框圆角及留白。助手给页面浮层预留的宽度包含右侧外框留白，聊天输入框及内层标签使用同一圆角尺度。
- 样式例外仅有上述共享 DocMarkdown 和 Agent 编辑器必要的兼容问题提示块；其他登记文件继续比较原始 styles。

没有为通过门禁回退既有知识库功能，没有批量刷新上游期望值，没有新增另一套源码验证平台。

2026-11-19 补充审查了聊天、附件与设置相关的响应式和键盘适配。推荐问题先填入输入框，新对话创建成功后才清理草稿，切换会话时按账号、工作区与会话保留当前标签页的草稿。此批适配只更新相关组件的本地哈希，来源基线仍指向原上游版本。

同日复核了 `01e1295` 的三处适配。Agent 编辑器新增默认关闭的 `use_custom_system_prompt` 开关，保存时沿用现有 Agent 配置通道。开启后用自定义提示词替换默认人格，运行约束仍由后端拼接。该提交也调整了停靠助手面板的圆角，以及亮暗主题的五级圆角令牌。三处差异对应各自的本地适配记录。

## 验证与限制

默认测试使用本地模型协议服务、真实官方 Harness 与隔离 PostgreSQL。模型图片调试契约测试隔离 parser 启动依赖，并验证格式失败 400、服务不可用 503 及失败不调用模型；真实沙箱解析集成另有现有显式门禁。

最终源代码对应的验证结果：

| 检查 | 实际结果 |
| --- | --- |
| 后端默认全量：`.venv/bin/python -m pytest -q -p no:cacheprovider` | 1068 passed，20 skipped，279.54 秒；其中 4 项 opt-in Chrome 用例另行执行 |
| 前端全量：`cd frontend && npm test` | 3048 passed，1 skipped，0 failed，41.80 秒 |
| 类型检查：`cd frontend && npm run type-check` | exit 0 |
| 生产构建：`cd frontend && npm run build-only` | exit 0，52.78 秒；既有 chunk 体积提示保留，未为此扩展打包优化 |
| 新增失败回归先红后绿 | 父子问卷/旧队列 4 项先失败；模型窗口 8 项先 4 失败；前端清空/编辑 3 项先失败；修复后全部通过并包含在全量中 |
| 官方 UI 来源门禁 | 5 项通过，遍历 132 个 SFC 和 32 个依赖；原始哈希不变，24 项精确适配；本轮只更新 AgentEditorModal、ModelEditorDialog 两项适配哈希 |
| 真实 Chrome：`RUN_BROWSER_ACCEPTANCE=1 .venv/bin/python -m pytest tests/test_platform_agent_alignment_browser.py -q -p no:cacheprovider` | 4 passed，18.08 秒；实际 API、隔离数据库、本地模型替身，新增真实 textarea 清空/重新输入保存 |
| 独立 API → UI 与模板快照复核 | 2 passed，8.20 秒；真实旧队列 GET 经过现有 hydration 后保留一条消息；HTTP 本轮恢复/新轮实际 system 为 `[OLD, OLD, NEW]` |
| 安装包完整性 | DeepAgents 0.7.35、langchain-litellm 0.11.1、LiteLLM 1.109.1、langgraph-prebuilt 1.1.1 的 3096 个 Python/目录文件与安装 RECORD 哈希一致 |
| `git diff --check` | 通过 |

Chrome 实际验证 quick 创建 201、max=8、默认工具 null、无需上下文模板；旧配置读取、取消、采用后放弃均不落库，明确保存后保留原 max=1、显式 []、知识范围和提示词。普通智能推理与嵌入助手运行中 Enter / Meta+Enter 保留草稿，仅有一次聊天发送；浏览器账号/任务请求为 0，steering 写请求为 0，历史 GET 读取保留。

新增 Chrome 用例还验证模板正文正确加载，真实清空后显示必填提示、无 PUT 且数据库整条记录不变；重新输入后唯一 PUT 返回 200，保存新正文且移除旧模板引用。

本轮日志位于 `/tmp/showdoc-five-fixes-20261117/`：`backend.log`、`frontend.log`、`type-check.log`、`build.log`、`browser.log`、`api-ui-bridge.log`。默认全量收集 1088 个后端用例，执行 1068 个；另行执行上述 4 个浏览器用例，其余 16 个默认跳过项未执行。

真实云/付费模型与非空云端引用展示不包含在上述结论中。ContextDB 本次定向工程知识搜索无命中文档，未作为实现证据。
