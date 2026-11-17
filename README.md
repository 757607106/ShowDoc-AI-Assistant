# 企业知识治理平台

最新架构边界、整改结果与验收见[2026-11-16 修正总报告](docs/architecture/architecture-remediation-final-20261116.md)。

Agent 前后端配置、模型窗口、问卷恢复与未接能力入口的精准修复见[2026-11-17 对齐记录](docs/architecture/agent-repair-alignment-20261117.md)；上游原始源码哈希和已审查本地适配分别记录，不宣称所有交互逐字一致。

2026-11-17 已按本次授权在本机 Docker 部署第三方开源 **Aegra 0.11.0 + Valkey**，为 Deep Agents 原生异步子代理提供 Agent Protocol 服务。审批恢复、任务更新、真实 Shell/排队任务取消和崩溃恢复已实测；并发策略与最终镜像复验均已通过，主应用已设置 `ASYNC_AGENT_RUNTIME_ENABLED=1`，浏览器已验证可选择“后台异步”，用户无需另行部署。版本、兼容补丁、证据与维护步骤见[异步运行服务说明](docs/guides/async-agent-runtime.md)。组件免费自托管，未新增 LangSmith 或其他收费服务；原模型及 ContextDB 调用费用沿用已有账号。

本轮知识库三模式、单目标投递及评审对齐见[实施与验收记录](docs/guides/contextdb-knowledge-alignment-20261116.md)。

以固定提交 `cbdcebabf48c5ee2d6868b370326aa8341703f62` 的 **WeKnora 前端**为基线，使用 Vue 3、TDesign、原有布局、知识库卡片、文档列表与预览、Wiki Markdown 编辑、对话流及确认卡片。源码与许可记录在 [frontend/UPSTREAM.json](frontend/UPSTREAM.json) 和 [frontend/UPSTREAM-LICENSE](frontend/UPSTREAM-LICENSE)。

知识解析、切片、检索、评审、Wiki、图谱和评审模板全部使用 **ContextDB 官方 REST/MCP**，产品入口聚焦知识库与知识评审。deepagents 的知识工具仅来自官方 MCP，连接失败会停止知识访问。同一 PostgreSQL 服务使用独立数据库和受限账号：平台保存账号、任务、同步映射、会话元数据与操作记录，Agent 专库保存官方 LangGraph checkpoint 和 Store。知识正文不迁入 PostgreSQL；采集原件与发布 ZIP 留在受控产物目录。

## 本机启动

需要 Python 3.12、Node 22+、Docker 和 PostgreSQL 17 镜像。已配置的本机凭据保存在 Git 忽略的 `.env`，请勿提交。首次安装：

```bash
uv venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env  # 仅在 .env 尚不存在时执行
```

填写 `.env` 的 ContextDB、模型和平台配置：`POSTGRES_PASSWORD`、`DATABASE_URL`、`AGENT_DATABASE_URL`、`FLASK_SECRET_KEY`、`CREDENTIAL_ENCRYPTION_KEY`、`PLATFORM_ADMIN_ACCOUNT`、`PLATFORM_ADMIN_PASSWORD`。两个应用 DSN 必须使用不同数据库、不同受限账号，禁止使用 Compose 的引导管理员。已有共享库按[隔离迁移说明](docs/guides/agent-postgres-isolation.md)先备份、盘点再切换。Fernet 密钥可用 `.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'` 生成；平台使用账号和密码登录，无需邮箱格式，密码长度为 8 至 1024 位。默认管理员为 `admin / admin123`，首次引导会创建账号，已有账号不会被启动或引导过程重置；旧配置 `PLATFORM_ADMIN_EMAIL` 仍作为账号配置的兼容别名。数据库连接串中的密码需 URL 编码。

```bash
docker compose -f compose.postgres.yml up -d
.venv/bin/python -m webapi.auth --bootstrap
.venv/bin/python -c 'from dotenv import load_dotenv; load_dotenv(); from agent.checkpointer import initialize_checkpoints; initialize_checkpoints()'
cd frontend
npm ci
npm run type-check
npm run build-only
cd ..
.venv/bin/python app.py                 # http://127.0.0.1:8000
```

另开终端运行 `.venv/bin/python -m governance.worker`。PostgreSQL 默认仅监听 `127.0.0.1:55432`，数据保存在命名卷。已有独立 Docker PostgreSQL 时可直接配置其 `DATABASE_URL`，不必另外启动 Compose 服务。

开发前端：`cd frontend && VITE_DEV_PROXY_TARGET=http://127.0.0.1:8000 npm run dev`。浏览器采集首次需要安装 Chromium：`PLAYWRIGHT_BROWSERS_PATH=downloads/_models/chromium .venv/bin/python -m playwright install chromium --only-shell`。

## 使用

1. **成员与权限**：管理员在设置中创建账号，绑定各自的 ContextDB 成员密钥；服务端验证成员并加密保存。官方成员/密钥开通在 ContextDB 控制台完成。有效权限、用户组和知识库授权使用官方结果；本程序不切换工作空间权限模式。
2. **采集与任务**：支持 ShowDoc、CYB、天瞳、通用网页和文件。平台只采集源内容、整理必要格式并检查完整性；云端承担资料解析和语义治理。失败和取消可重试，原件与来源标识保留。
3. **自动提交治理**：采集和文件上传选择一个真实 ContextDB 知识库，完整采集成功后自动提交到该固定 ID。采集不完整先重试；自动提交失败保留原件，可在资料任务补交。创建时三选一：零编译（原文检索）、图谱编译（原文及实体关系）或 Wiki 编译（原文及主题页），默认 Wiki，创建后本平台不允许切换模式。评审开关独立，默认开启；新库开启重写建议、关闭重写稿自动入库，初始高分阈值 0.85，已有库保持官方策略。同源未变化跳过，变化使用官方更新及评审流程。提交受理、评审通过、正文入库及派生内容完成分别显示。
4. **统一知识库入口**：卡片与列表直接展示官方库名和 ID，提供搜索、排序、分页、真实改名和安全删除。原生库可以直接作为资料目标，无需先关联另一层业务空间。内部 `scope` 仅用于来源、任务和回执；旧 Wiki、图谱库按真实 ID 独立保留，旧地址兼容跳转，不再双投。删除先检查文档和在途任务，非空库需先清理；结果不明确保持待确认，删除或缺失后不自动重建，也不按同名库替换旧 ID。原件、历史任务和回执继续保留。
5. **知识评审**：默认打开官方评审队列，展示原生评审状态与冲突处置、原文/重写稿、确认/拒绝/撤回/重试；完整人工编辑稿通过官方 `edited_content` 提交。决定受理后保留详情，分别刷新文档入库和 Wiki 编译状态，再打开同库 Wiki 核对。修订不回写采集原件、外部站点或另一图谱库。评审策略和模板由 ContextDB 执行。结构化记忆、记忆整理、记忆晋升的页面、接口与 Agent 工具已移除；原生文件记忆、聊天历史、会话恢复及已入库的历史知识文档保留。
6. **Wiki 与 Agent**：编辑器读取完整正文和真实版本，保存携带原版本；冲突保留草稿，比较合并后保存。Agent 后端直接使用官方开源免费的 Python Deep Agents Harness；前端使用 WeKnora 原组件和流处理器，由 API Adapter 转换原生流与状态。没有显式 @ 提及时采用 Agent 默认知识库策略；知识工具通过官方 MCP，文档 ID 校验归属。提问和工具确认使用官方 interrupt/Command。主会话连接断开后结束本次同步请求，刷新只读取 checkpoint；显式异步子代理由独立运行服务执行，可查看结果、追加说明、取消或响应真实中断，远端完成不自动唤醒父会话。

回答引用只采用本轮成功官方工具返回的原文切片，按真实知识库/文档/切片 ID 校验；跨流片段完整输出标签，代码示例保持字面内容。工具错误、停止与恢复使用实际执行状态，停止无需等待卡住的工具再返回事件。

Agent 模型通过 **LiteLLM Python SDK** 接入，继续使用原生 Deep Agents / LangGraph 执行、审批和 checkpoint。模型配置中的供应商可选择 OpenAI、阿里云百炼、DeepSeek、Anthropic、Google Gemini 或 OpenAI 兼容服务；填写该供应商的实际模型名、Base URL 和个人 API Key。前端 Agent 组件及交互沿用固定 WeKnora 版本，模型能力、调试表单与流事件由后端适配。普通连接测试不代表该型号支持思考或工具调用。

思考选项来自固定 SDK 的本地型号目录，可通过现有 `parameters.spec` 覆盖新型号的 `reasoning`、`thinking_levels` 和 token 限制；不支持的强度会明确拒绝。`qwen-max` 不提供思考选项；百炼可使用支持思考的 `qwen-plus`。`auto` 对 Qwen 开启思考，对 DeepSeek/Gemini/支持 adaptive 的 Claude 使用自动模式；OpenAI 无可用自动强度时使用 `medium`。Claude 思考输出预算须大于 1024 tokens。模型测试返回请求选项、实际应用的选项、思考内容和用量；受模型限制的采样参数不会伪装成已应用。OpenAI Responses 可在现有高级配置中选择 `extra_config.api=openai-responses`，保留推理摘要及恢复所需的加密项。

SDK 固定为 `langchain-litellm==0.11.1`、`litellm==1.109.1`。`langchain-litellm 0.11.2` 强制引入 MCP 2.x，与当前 `mcp==1.30.0` 冲突，因此本次不升级该依赖。默认测试使用本地 OpenAI/Qwen/DeepSeek、Anthropic、Gemini 协议服务及隔离 PostgreSQL；真实浏览器与百炼验收分别执行 `RUN_BROWSER_ACCEPTANCE=1 .venv/bin/python -m pytest tests/test_platform_litellm_browser.py -q`（先构建前端，需安装 Chrome）和 `RUN_LLM_ACCEPTANCE=1 .venv/bin/python -m pytest tests/test_platform_litellm_live.py -q`（使用已配置的百炼凭据，产生模型调用费用）。验收仅写入测试 schema 和会话虚拟文件；验收报告不保存思考正文或明文凭据。

Wiki 编译器接管准入结果为 **未通过**：完整受影响页定位、编译来源/链接写入及云端编译隔离仍未确认，继续使用 ContextDB 官方编译。独立切片分页、页面版本冲突与读回实测见[准入报告](docs/architecture/contextdb-wiki-compiler-readiness.md)；未增加本地编译器或 Worker 编译阶段。

**治理格式边界**：开启评审时，TXT、Markdown、PDF、DOC、DOCX 直接使用官方评审；已有单篇 Markdown 直接复用，HTML 复用项目现有 Docling 转为送审 Markdown，原件保留，不执行本地切片或评分。无法生成可评审正文及其他未支持评审的格式阻止投递，并显示原因。关闭评审时，按官方文件格式规则上传原件，不标记为已评审。合并 Markdown 是旧爬虫 CLI 的离线导出产物，不与单篇资料重复入库。

**已确认的限制**：Wiki 搜索单次最多 50 页，页面会说明范围；官方类别列表不能冒充全量页面列表。修订必须按页面读取，返回章节元数据。官方控制台支持候选接受/拒绝和历史查看/比较，但公开 API 未提供审批写入、历史全文/原生回滚及严格人工发布的完整契约，对应入口禁用。当前官方 MCP 未提供 Wiki 修订工具，Agent 不以自建 REST 工具绕过该限制。阈值及关闭重写自动入库不保证全量人工发布。详见[专项核对与实测证据](docs/architecture/contextdb-wiki-support.md)。

## 迁移与验证

```bash
# 只读备份旧 _governance，生成校验和
.venv/bin/python -m scripts.migrate_runtime
# 校验快照后导入指定的已绑定平台账号，不修改/删除旧云端记录
.venv/bin/python -m scripts.migrate_runtime --snapshot downloads/migrations/<timestamp>.json --apply --owner-account admin

.venv/bin/pytest -q
cd frontend && npm run type-check && npm run build-only
```

默认测试不会访问 ContextDB 云端。平台与 Agent 分别在 `showdoc_knowledge_test`、`showdoc_agent_test` 使用独立临时账号和每例 schema，验证双向跨库连接被拒绝；`TEST_DATABASE_URL` 必须指向以 `_test` 结尾的测试库，并有创建临时数据库和账号的权限。单目标知识库的云端验收需显式执行 `.venv/bin/python -m scripts.contextdb_pipeline_smoke --execute`，只操作本次新建且精确记录 ID 的探测资源，并记录清理结果。

新会话在既有 `agent_sessions.agent_config` 标记 `runtime=deepagents`，主会话执行状态保存在 Agent 专库的官方 LangGraph checkpoint；显式异步子代理的线程、运行与 checkpoint 使用独立 `showdoc_async_agent` 库和 Valkey broker。WeKnora 聊天、历史、审批与提问接口由 API Adapter 对接；主会话审批 POST 提交协议决定，随后的续接 GET 调用原生 `Command` 并流式返回；异步子代理按远端真实 interrupt ID 一次提交完整响应，由运行服务恢复。旧会话、运行记录和沙箱卷保留，旧执行入口继续拒绝执行。官方 StateBackend 提供虚拟会话文件；OpenSandbox 提供隔离文件和 Shell，接入步骤及附件解析镜像见[沙箱部署说明](deploy/opensandbox.md)。附件原始字节保存在所属账号的归档记录中，解析在无外网的临时沙箱执行，无沙箱时明确拒绝，不回退宿主解析。原生文件记忆、子代理轨迹、应用层 fork/rewind 已接入；浏览器/桌面、运行中 steering、自动安装及结构化记忆仍明确拒绝。源码核对与验证见 [官方对齐审计](docs/architecture/agent-official-alignment-audit.md)。

旧 `_governance` 保留只读。迁移记录见 `downloads/migrations/`。数据库备份可使用 `docker compose -f compose.postgres.yml exec -T postgres pg_dump -U showdoc showdoc_knowledge > <private-backup.sql>`；同时备份 `.env` 的加密密钥和产物目录。Agent 必须经 ASGI 启动：`app.py` 已默认启动 Uvicorn，也可执行 `.venv/bin/uvicorn asgi:create_app --factory --host 127.0.0.1 --port 8000`。新增 Aegra 是第三方自托管实现，使用固定版本兼容补丁接入官方 SDK，不能称为 LangChain 官方服务器原样兼容。当前为单机、非 HA 部署，Valkey AOF `everysec` 不保证零丢失，checkpoint 恢复不保证外部副作用 exactly-once；主 API 仍为单进程。详见[异步服务限制与实测](docs/guides/async-agent-runtime.md)及[既有 Agent 验证边界](docs/guides/agent-interaction-validation.md)。

原独立爬虫 CLI `main.py` 的逐篇 Markdown、完整合集与 Docling 导出流程保留。平台采集使用 `source_only=True` 保存原件，不运行这套导出及切片流程；只有开启评审的 HTML 投递调用现有转换器生成送审稿。

更多边界与验收状态见 [当前架构与接口清单](docs/architecture/agent-platform.md)。
