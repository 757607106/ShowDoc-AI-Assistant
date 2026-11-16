# Agent 真实运行验收

日期：2026-11-15（Asia/Shanghai）。本轮接续[原生能力对齐](agent-advanced-alignment.md)，使用实际模型、实际 PostgreSQL、实际 ContextDB 只读接口、实际 OpenSandbox 与 Chrome，不将 FakeMessages 或网络替身的结果计作真实验收。

## 环境与数据边界

- 新建 `showdoc_knowledge_test` 的独立 `real_accept_*` schema 与临时账号；后端只绑定 `127.0.0.1:18765`，前端独立 `18766`，官方参考前端 `18767`。原有 8000/5173 服务不操作。
- 模型使用项目原配置 `agent-main / qwen-max` 和原端点；没有切换供应商或使用收费 Agent Server。凭据仅在私有临时目录及测试数据库中使用，报告不包含 token、密码、API key 或带签名的资源地址。
- 知识库仅进行原有成员权限下的列举与检索，不写入云端资产；ContextDB/知识页面及既定 180 个冻结文件继续保持不变。
- 沙箱保持此前确认的可信单用户开发范围；生产 Kubernetes/Gateway、gVisor/Kata 安全验收不在本机结果的证明范围内。

## 当前实际结果

| 链路 | 权威证据 | 结果 |
| --- | --- | --- |
| 默认真实模型与原生 Graph | `agent-real-20261115/model-native.json` | 实际生成聊天、`write_file` tool call；审批前未写入；销毁 Graph/Saver/Store 后重建，interrupt 与 call ID 不变；批准后恰一份工具结果，再次重连核对文件与 31 个 checkpoint。 |
| HTTP → SSE → 模型 → ContextDB MCP | `http-knowledge.json` | 34 个实际 SSE 帧，16.602 秒；实际 `knowledge.search`，1 条授权知识库引用；实时与历史引用一致，ToolMessage call ID 与请求对应。资源签名地址已从报告脱敏。 |
| 真实 HTTP 身份隔离 | `http-isolation.json` | 10 个检查通过：外部账号会话/状态/历史/执行/分支/终端/记忆拒绝，viewer 终端拒绝，真实 token 撤销及非法签名拒绝；源 checkpoint 数不变，未创建 viewer 沙箱。 |
| 原 UI 创建与普通问答 | `agent-real-acceptance-20261115/phase1-real-browser.json`、截图 02–09 | 原编辑器创建真实 Agent，原模型发出唯一测试回答；刷新读取历史没有重复发送。 |
| 原 UI 审批跨 API 进程重启 | `process-restart.json`、截图 10–12 | 真实停止旧 API PID 并起新进程；完整原生状态 SHA256 不变；原卡恢复同一 interrupt/call ID；点击批准后真实沙箱 stdout 包含测试 nonce，恰一次结果，没有多生用户消息。 |
| 原 UI 子任务、记忆、分支和回退 | 浏览器 phase2–3、截图 17–26 | 真实默认子 Agent 的工具历史、父子回答分离；Store 写入后新 thread 的问题未含口令，模型仍读取正确；用户问题分支排除原问题并预填，独立回答不污染源会话；回退返回 `CHECKPOINT_ONLY` 并按原 UI 预填。 |
| 独立沙箱生命周期 | `sandbox-lifecycle.json` | 8 项实际能力通过，包括官方 SDK 正确 mode 后的原生文件工具、256 KiB 二进制、双会话隔离、客户端重连、同 PTY 重接、短 TTL 与失败环境清理。此项明确不包含下述适配器 write 缺陷。 |
| 修正后的原 UI 沙箱写入/编辑 | `sandbox-mode-fix-real.json`、`ui-sandbox-final-file.json`、浏览器 phase4 | 新环境、新路径经真实模型生成 write/edit 两次原生调用并逐次审批。独立官方 SDK 最终读取字节精确为 `REAL_EDIT_1115_B84D`，实际权限 `0644`，没有 chmod 或扩大权限。 |
| 原 UI 刷新令牌与后续聊天 | `auth-refresh-fixed.json`、浏览器 phase4 | 原 `refreshAccessTokenShared()` 未注入替代函数，官方 camel 请求 200、两个真实 token 更新，`/auth/me` 200；原 UI 后续实际模型回答完整，刷新历史不重复执行。 |
| 官方“不启用”及真实检查点下载 | 浏览器 phase5、`checkpoint-artifact-final.json` | 保存并重新加载后无 State 原始翻译 key；新 thread 问题未含口令但实际读取正确记忆。普通文件经原生审批写入，原抽屉实际 Chrome 下载与独立 HTTP 下载逐字节一致，57 B，SHA256 `0b3a820d81a23e712a3c59937781e55dabb381bad13202604fb01563393b4d54`。 |
| 真实运行中子面板 | 浏览器 phase6、截图 39–40 | 原 `ChildAgentStream` GET 200，65 个非空回答/工具帧先于父 complete；首个非空回答提前 7.80972 秒。仅执行原生 task/ls。实际响应总字节与被动 CDP chunk 累计相等，未包装 fetch、未注入延迟或替代模型；首次未证实尝试保留。 |
| 官方 UI 样式对照 | `computed-style-comparison.json`、`screenshot-comparison.json` | 固定上游实际页面、同后端/浏览器/会话；6 个组件的 22 项计算样式无差异。输入框 960×98、正文 960×73 两对 PNG 裁剪逐像素相同。仅证明这些实际样本，不外推为全站/全状态验收。 |
| Qwen 显式推理内容 | `model-reasoning.json` | 原配置接受 `enable_thinking=true`，7 帧、正常回答及 usage；未观察到非空 `reasoning_content`，不能称该模型的显式推理输出已实测通过。未保存推理正文。 |

证据目录为 `output/verification/agent-real-20261115/`；浏览器脚本、截图及样式对照在 `output/verification/agent-real-acceptance-20261115/`。

## 真实测试发现并修正的缺陷

社区 `langchain-sandbox-opensandbox==0.1.2` 将 `DEFAULT_FILE_MODE=0o644` 传给 SDK，即 Python 数值 420。官方 SDK 的参数是权限数字（[示例使用 `mode=644`](https://github.com/opensandbox-group/OpenSandbox/blob/main/docs/sdks/python.md)），服务将 420 解释为 `0420`。实际 owner 与执行用户同为 root，但该文件 owner 无写权限；在保持 `CapDrop=ALL` 的配置下，原生 `edit` 正确返回 `permission_denied`。本项目附件 helper 的同类参数也需要纠正。

证据：`sandbox-mode-contract-finding.json`、`sandbox-native-file-identity.json`、`sandbox-lifecycle.failed-native-edit.json`。当前上游 main 与 PyPI 最新仍是同一错误；没有原生构造参数可覆盖。用户已明确批准限定修正：仅版本 0.1.2 且原常量为 420 时，将模块常量设为 SDK 要求的 644；本项目附件 SDK 参数也改为 644。没有更换 Backend、增加权限、chmod 绕过或暗改安装包。修正后社区 Backend 原生写入→编辑→读取→删除以及附件的 0644/256 KiB 字节验收通过，旧失败证据保留。

登录刷新还有双向协议不匹配：官方前端发送 `refreshToken`、读取 `access_token`，原后端只读取 `refresh_token`、只返回 `token`。真实新签发凭据年龄不足一秒仍复现 camel 请求 401。API 现接受官方字段并保留旧字段兼容，签名、会话、撤销与期限检查不变；异常输入现在为 400/401，避免原来的 500。19 项真实 PG 契约回归及实际 HTTP/原前端共享函数均通过。

官方 `AsyncPostgresStore` 的 context 退出后仍残留 batch 任务，与[上游问题 #6367](https://github.com/langchain-ai/langgraph/issues/6367)一致；读取和写入本身成功。现改用官方 `PostgresStore` 的原生异步接口，由标准线程资源桥接打开/关闭连接；未编写 runner、队列或访问私有任务。真实 PG 与真实新 thread 模型读取均验证数据不变、连接关闭且 batch 任务为 0。

StateBackend 作为额外具名沙箱导致原组件显示未翻译 key。用户确认后，前端具名类型恢复固定上游 `cube/e2b/docker`；API 将内部 `state-backend` 投影为官方“不启用沙箱”的空值，输入空值仍归一到原生 StateBackend。没有新增组件/文案或把虚拟文件系统冒充 Docker；原有 Skills 环境选择遵循官方交互限制。内部 schema、namespace 与 checkpoint 不变。

最终类型检查还发现 `SandboxConfigEditorDrawer.vue` 的两处旧自定义筛选/默认选择逻辑。已直接恢复固定上游原文；整个文件现在与官方逐字一致，并加入完整 template/style/source 门禁。当前门禁扩大为 113 个 SFC、36 个交互源码和 27 个字体/布局依赖，没有降低旧断言。

## 最终门禁与清理

- 后端全量：**488 passed、2 skipped、57 warnings，95.94 秒**。两项默认 opt-in 跳过是外部爬虫浏览器与真实沙箱用例；本轮 Agent 浏览器和沙箱在上述独立真实脚本中执行，不将默认 skip 算作通过。
- 前端类型检查通过；当前源码在独立临时 outDir 生产构建通过（20.80 秒），未覆盖日常服务的 `frontend/dist`。仅保留原有大 chunk 提示，没有为消除提示改写 UI。
- 扩大后的官方源码门禁通过，固定上游 `main` 再核对仍为 `cbdcebabf48c5ee2d6868b370326aa8341703f62`；知识库既定 180 文件 SHA256 全部不变。
- 209 个已安装 Python 包依赖兼容，差异检查、Python 编译检查通过。
- 40 张浏览器截图、phase1–6、被动网络时间线及实际下载保留并归档 SHA256；临时浏览器、18765/18766/18767 服务均已退出。
- 临时 owner 的沙箱和句柄均为 0；独立测试 schema 已删除（删除前包含 1 个临时用户、8 个会话、228 个 checkpoint 和 1 个记忆文件），私有凭据目录已删除。最终 API 关闭没有残留 batch-task 告警。仅保留此前控制服务与原 PG；原 8000/5173 业务服务未操作/重启。

## 验收限界

原 UI 的用户消息分支/回退入口在刷新获得持久 ID 后出现，这是固定上游行为；没有伪造 steering 注入事件或新增组件逻辑。官方参考页有辅助 API 的泛 Object 错误，当前集成页最终无 pageerror；因此样式对照不等于参考站全部业务 API 已兼容。两个指定裁剪像素一致，也不等于全站、全部状态或全部浏览器的像素验收。

本机还观察到宿主/controller 的 wall clock 与 monotonic elapsed 显著分离：旧实例的 UTC `expires_at` 已过，执行容器仍曾存活，随后官方日志出现自动资源清理。短 TTL 的成功不消除此长实例的计时边界；原因和计时样本独立留证，不自建清理 worker 或承诺 UTC 硬截止。

后台续跑、沙箱历史产物、结构化记忆和生产强化隔离继续遵守此前已确认的范围；没有借本轮真实测试改造这些功能。
