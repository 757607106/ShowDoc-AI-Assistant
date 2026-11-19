# 免费 Harness 验证边界

> 2026-11-14 严格对齐复核：下列记录是本次恢复官方源码之前的阶段证据。其后已恢复 WeKnora 核心页面和原流处理器，删除自写 Harness UI，并在服务端适配官方开源 Python Harness。112 个 SFC 的模板/样式、35 个核心交互源码（4 处仅重定位 import）及 27 个字体/布局依赖已加入固定上游哈希门禁。知识页共享改动已撤回。最新实现、用户确认的范围和验证结果见 [官方对齐审计](../architecture/agent-official-alignment-audit.md)，不能据下文旧数字宣称本次像素或所有功能验收。

当前链路为官方 `deepagents 0.7.35`、`langgraph 1.2.20`、PostgreSQL checkpoint，以及官方 LTS `@langchain/vue 0.4.9` / `@langchain/langgraph-sdk 1.8.12`。WeKnora 固定提交 `cbdcebabf48c5ee2d6868b370326aa8341703f62` 提供展示基线。运行不依赖生产 Agent Server、Redis 或 Helm。

## 运行链路迁移阶段记录

下列浏览器记录来自展示组件再次适配之前，不代表新版页面已完成浏览器验收。

主要检查：

- `tests/platform/test_platform_harness.py`：实际 ASGI、登录与归属、官方图、PostgreSQL checkpoint、原生流和中断恢复，以及并发与取消边界。
- `tests/agent/test_harness_native.py`：官方图构建、文件/Skills、原生工具与权限边界。
- `tests/platform/test_platform_legacy_agent_readonly.py`：旧执行入口返回 410；历史、产物、后台任务及安装记录的 GET 不改变保存状态、不启动进程；原生会话清空/删除与流请求互斥；静态 Skill 内容管理与归档文件下载。
- `tests/agent/test_agent_domain.py`、`tests/agent/test_agent_configuration.py`：官方 checkpoint、成员隔离、模型配置、知识范围与 MCP 契约。
- `tests/platform/test_platform_mcp_runtime.py`：真实 MCP 协议测试服务与官方客户端、授权与恢复。
- 保留下来的附件、Skill 归档、浏览器偏好及推荐业务测试，不再依赖已删除的自写运行器。

2026-11-14 最终完整后端测试结果：**382 passed、1 skipped**（66.21 秒）。跳过的是原有、需显式启用的外部网页采集浏览器测试；旧流式正文改写器、未接入的自写长期记忆及其专属测试随功能退役删除，保留来源过滤的业务测试。覆盖同一检查点两项文件审批：一项批准、一项拒绝时只写入获批文件；缺失决定由官方 SDK 拒绝，工具不执行。测试使用真实 SDK、隔离 `*_test` PostgreSQL schema 和受控模型/MCP fixture；默认禁止访问 ContextDB 云端。

前端完整测试 **2541/2541 通过**，类型检查通过，生产构建通过；最后一处创建成功提示修正另有 **22/22 定向测试通过**并重新构建。此前两项 memory 失败已处理：关闭实际不可用的设置入口，将不合理的“禁止历史翻译存在”断言移至真实能力验证，保留通用翻译完整性和历史字段检查，没有删除已有数据来满足测试。

本轮真实浏览器连接隔离 ASGI 服务和生产前端构建，模型由官方测试模型提供确定的工具调用；文件、规划、子代理、中断和 checkpoint 均运行实际 Deep Agents。没有使用伪造 SSE 驱动页面。

| 浏览器场景 | 观察结果 |
| --- | --- |
| 发送、刷新历史 | 问题与回答保持一致，刷新不重新提交问题 |
| 文件审批、刷新待审批、修改参数 | 待审批状态恢复；修改后执行官方文件工具，文件名与内容来自批准后的参数 |
| 批准后发起下一轮 | 已解决审批不再从初始快照复活 |
| 停止长工具、继续普通对话 | 取消后未显示工具成功；后续对话可正常执行 |
| 规划、子代理 | Todo 来自官方状态；子代理内容位于独立卡片 |
| 原文引用与工具预览 | 引用与真实工具返回内容一致，未验证的网页引用不显示为证据 |
| 新建、保存和重开智能体 | 必填校验有效，配置实际保存；九项原生工具只读展示，可选业务工具单独列出 |
| 设置与工具箱 | 不再提供无效长期记忆、网络搜索、Docker、浏览器、分享和执行队列入口；工具箱仅显示静态 Skills 与 MCP |
| 文件下载 | 文件已生成；浏览器下载未获得授权，本轮不声称完成下载验收 |

后端另外验证未登录/跨用户访问、双请求并发拒绝、批准/拒绝/修改、重复审批、连接立即断开、工具执行中断开、服务关闭和响应头发送失败。各取消路径会释放请求锁，未建立后台运行记录。真实 MCP 目录与官方图的九项固定工具已核对一致；原生 `delete` 的批准、拒绝及只读权限单独验证；官方会话记忆不会跨线程继承。仍有既有 Docling/NumPy 提示及 Starlette WSGI 适配弃用提示。

```sh
.venv/bin/python -m pytest -q tests/platform/test_platform_legacy_agent_readonly.py tests/platform/test_platform_harness.py tests/agent/test_harness_native.py tests/platform/test_platform_mcp_runtime.py
cd frontend
npm test
npm run type-check
npm run build-only
```

这些结果证明本地接口、实际 Harness 与界面接线；未验证真实云端模型回答质量、生产负载、外部服务故障或部署环境。不得把旧验证报告中的 Docker、BrowserSkill、后台续跑、事件重放或 fork/rewind 结果当作当前功能；这些自写执行器已删除。

原 `output/verification/weknora-agent-20261114/` 产物作为旧方案记录保留，本轮不复用其通过数字或云端验收结论。新会话消息、文件、Todo 与中断状态只由官方 checkpoint 保存；停止/断开结束当前请求，刷新读取已保存状态。

本轮日志、结果汇总与浏览器截图保存于 `output/verification/deepagents-harness-20261114/`。隔离浏览器服务及其测试数据库 schema 已清理。

## 直接使用 WeKnora 原组件（2026-11-14，最终修正）

此前只拼接部分组件的页面不满足用户要求，已被替换。当前使用 `frontend/UPSTREAM.json` 登记的 WeKnora 源码基线 `cbdcebabf48c5ee2d6868b370326aa8341703f62`，保留上游许可证和已有业务修复。

| 页面部分 | 实际代码与 API 适配 |
| --- | --- |
| 聊天页 | 恢复原路径 `views/chat/index.vue` 和上游 `chat / chat_thread / chat_scroll_box / chat_scroll_content / msg_list / chat_composer / input-container` 结构；`chat-layout.less` 保存原布局样式全文 |
| 输入框 | 原 `Input-field.vue`；原样恢复被误删的 `.rich-input-container` 宽度、背景、边框、阴影和聚焦样式。删除额外 880px 宽度、36px 内边距及自写定位覆盖 |
| 消息、步骤和计划 | 原 `usermsg.vue`、`botmsg.vue`、完整 `AgentStreamDisplay.vue`，由原组件调用 `PlanDisplay`、`ToolResultRenderer` 和 `ContextDBToolResult`。没有另一套自写工具卡或时间线 |
| 子任务 | 原 `ChildAgentTabBar`、`CollaborationTasks`，跳转回调读取官方 SDK subagents；刷新后显示 SDK 保存的任务结果 |
| 审批与授权 | 原 `PendingPromptDock`、`ToolApprovalCard`、`AskUserCard`、`McpOAuthCard`。回调收齐当前 checkpoint 的全部决定后，一次提交官方 interrupt ID map；无旧审批 API、轮询恢复或后台执行器 |
| 引用、附件和文件 | 原 `docInfo`、引用抽屉、附件上传/预览组件、`ChatArtifactsDrawer`。文件读取回调使用已授权的官方 checkpoint，不拼造服务端 artifact ID |
| 页头 | 原 `ChatHeader`；重命名、删除继续调用业务 session API，Markdown 导出使用 SDK 当前消息 |

已物理删除自写 `HarnessConversation.vue`、`HarnessTranscript.vue`、`HarnessAnswer.vue`、`HarnessApprovals.vue`、`NativeToolResult.vue` 和抽取时间线 `harness-timeline.less`，相关组件专用测试随替代删除，并补充原组件与 API 字段适配验证。`HarnessChatPage` 只负责会话归属信息及 checkpoint 加载，实际聊天布局来自原 `index.vue`。

保留的新增逻辑是必要的 API 装配：官方 `useStream` / `FetchStreamTransport`、SDK 快照到原组件 props 的纯字段映射、业务附件上传、官方中断 ID 响应，以及 checkpoint 文件读取回调。不解析 SSE、不积累另一份运行状态。发送时使用 SDK 的 `optimisticValues` 提供新 Human 消息边界；原生分块即时显示，关闭原组件的第二次打字动画；审批暂停显示等待，不显示工具仍在执行。

源码比较确认：聊天布局 CSS 原文完整保留，AgentStreamDisplay、botmsg、usermsg、ChatHeader、PendingPromptDock 和 McpOAuthCard 的样式块与上游一致。模板中的变化限于 API 数据/回调绑定、原生资源权限，以及不具备后端能力的入口隔离；未覆盖此前已有的知识库权限和精确引用修复。

本次最终前端全量 **2571/2571 通过**（22.40 秒），完整类型检查通过，生产构建通过（38.28 秒），`git diff --check` 通过。本轮没有修改后端；前阶段后端全量结果仍为 **384 passed、1 skipped**，最后的提及去重修复另通过 **30 项定向回归**。

浏览器连接隔离 ASGI 服务、真实 PostgreSQL checkpoint 和实际官方 Deep Agents 图；官方受控模型生成确定的工具调用，没有用手工 SSE 喂页面。已实际验证：

- 输入框宽度、边框、背景、阴影与原页面布局；工具及计划展开。
- 原回答复制、会话 Markdown 导出与重命名。
- 子任务切换、刷新历史及已保存结果。
- 原审批卡批准后恢复真实文件写入；原文件抽屉预览显示实际内容。
- 原附件组件上传、解析完成、发送后的文件卡及实际文本预览。
- 工具来源列表与引用片段；工具返回和列表内容一致。
- 停止长工具后无伪造最终回答；测试工具 finally 取消标记更新时间与操作一致，之后可继续发送。

限制：隔离 fake ContextDB 不实现完整原文文档 chunks 路由，因此本次验证了引用列表/片段，没有将完整知识库原文件预览宣称通过。未调用收费云端模型、未进行生产负载验收；此前未获授权的浏览器下载未重试，文件 Blob 字节与原下载回调通过组件测试验证。文件按钮沿用原回答工具栏的显示时机。

最终记录位于 `output/verification/weknora-harness-ui-20261114/verification.json`，截图为 `direct-weknora-*-browser.jpg`。此前 `upstream-*` 截图属于中间版本，不作为最终原组件验收证明。隔离测试服务及其 schema 已清理。
