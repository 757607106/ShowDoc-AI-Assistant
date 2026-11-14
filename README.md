# 企业知识治理平台

以固定提交 `cbdcebabf48c5ee2d6868b370326aa8341703f62` 的 **WeKnora 前端**为基线，使用 Vue 3、TDesign、原有布局、知识库卡片、文档列表与预览、Wiki Markdown 编辑、对话流及确认卡片。源码与许可记录在 [frontend/UPSTREAM.json](frontend/UPSTREAM.json) 和 [frontend/UPSTREAM-LICENSE](frontend/UPSTREAM-LICENSE)。

知识解析、切片、检索、评审、Wiki、图谱和评审模板全部使用 **ContextDB 官方 REST/MCP**，产品入口聚焦知识库与知识评审。deepagents 的知识工具仅来自官方 MCP，连接失败会停止知识访问。Docker PostgreSQL 仅保存账号、加密成员凭据、平台任务、同步映射、会话、官方 LangGraph checkpoint 和操作记录；采集原件与发布 ZIP 留在受控产物目录。

## 本机启动

需要 Python 3.12、Node 22+、Docker 和 PostgreSQL 17 镜像。已配置的本机凭据保存在 Git 忽略的 `.env`，请勿提交。首次安装：

```bash
uv venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env  # 仅在 .env 尚不存在时执行
```

填写 `.env` 的 ContextDB、模型和平台配置：`POSTGRES_PASSWORD`、`DATABASE_URL`、`FLASK_SECRET_KEY`、`CREDENTIAL_ENCRYPTION_KEY`、`PLATFORM_ADMIN_EMAIL`、`PLATFORM_ADMIN_PASSWORD`。Fernet 密钥可用 `.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'` 生成；账号密码至少 12 位，邮箱须有有效域名。数据库连接串中的密码需 URL 编码。

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
3. **自动提交治理**：采集和文件上传统一选择业务知识库，完整采集成功后自动创建 ContextDB 提交任务。采集不完整先重试；自动提交失败保留原件，可在资料任务补交。新建默认只启用 Wiki，实体图谱按需开启；既有范围保留原双库关联。分别记录文档 ID、源版本、上传及官方处理状态，未变化资料跳过，失败按目标重试。提交完成不等于官方治理或 Wiki 发布完成。
4. **统一知识库入口**：WeKnora 卡片展示业务知识库，默认打开 Wiki，文档、图谱和治理进度在同一详情查看。独立“来源资料”入口已移除，旧 URL 转到知识库；本地原件及历史快照仍供恢复与追溯，任务支持下载资料包，Wiki 保留官方文档引用。内部 `space/scope` 只是官方库的关联及采集范围，不保存另一份知识正文。未绑定的官方库在“关联已有库”中查看或关联，原库 ID 和引用深链保留。图谱启用后会分别投递两库，形成独立评审状态；关闭仅影响后续提交，不删除已有库。
5. **知识评审**：默认打开官方评审队列，展示原生评审状态与冲突处置、原文/重写稿、确认/拒绝/撤回/重试；完整人工编辑稿通过官方 `edited_content` 提交。决定受理后保留详情，分别刷新文档入库和 Wiki 编译状态，再打开同库 Wiki 核对。修订不回写采集原件、外部站点或另一图谱库。评审策略和模板由 ContextDB 执行。长期记忆、记忆整理、记忆晋升的页面、接口与 Agent 工具已移除；聊天历史、会话恢复及已入库的历史知识文档保留。
6. **Wiki 与 Agent**：编辑器读取完整正文和真实版本，保存携带原版本；冲突保留草稿，比较合并后保存。Agent 后端直接使用官方开源免费的 Python Deep Agents Harness；前端使用 WeKnora 原组件和流处理器，由 API Adapter 转换原生流与状态。没有显式 @ 提及时采用 Agent 默认知识库策略；知识工具通过官方 MCP，文档 ID 校验归属。提问和工具确认使用官方 interrupt/Command；连接断开后结束本次请求，刷新读取 checkpoint，不在后台续跑或重放旧执行。

回答引用只采用本轮成功官方工具返回的原文切片，按真实知识库/文档/切片 ID 校验；跨流片段完整输出标签，代码示例保持字面内容。工具错误、停止与恢复使用实际执行状态，停止无需等待卡住的工具再返回事件。

Wiki 编译器接管准入结果为 **未通过**：完整受影响页定位、编译来源/链接写入及云端编译隔离仍未确认，继续使用 ContextDB 官方编译。独立切片分页、页面版本冲突与读回实测见[准入报告](docs/architecture/contextdb-wiki-compiler-readiness.md)；未增加本地编译器或 Worker 编译阶段。

**治理格式边界**：官方明确支持 TXT、Markdown、PDF、DOC、DOCX 的知识评审。HTML、PPT、Excel、图片和音视频等使用官方现有上传、解析与检索能力，治理支持未确认；不将上传或入库成功显示为完成治理，不增加本地格式转换。

**已确认的限制**：Wiki 搜索单次最多 50 页，页面会说明范围；官方类别列表不能冒充全量页面列表。修订必须按页面读取，返回章节元数据。官方控制台支持候选接受/拒绝和历史查看/比较，但公开 API 未提供审批写入、历史全文/原生回滚及严格人工发布的完整契约，对应入口禁用。当前官方 MCP 未提供 Wiki 修订工具，Agent 不以自建 REST 工具绕过该限制。阈值及关闭重写自动入库不保证全量人工发布。详见[专项核对与实测证据](docs/architecture/contextdb-wiki-support.md)。

## 迁移与验证

```bash
# 只读备份旧 _governance，生成校验和
.venv/bin/python -m scripts.migrate_runtime
# 校验快照后导入指定的已绑定平台账号，不修改/删除旧云端记录
.venv/bin/python -m scripts.migrate_runtime --snapshot downloads/migrations/<timestamp>.json --apply --owner-email admin@knowledge.local

.venv/bin/pytest -q
cd frontend && npm run type-check && npm run build-only
```

默认测试不会访问 ContextDB 云端，平台测试在 Docker 的 `showdoc_knowledge_test` 中使用每例独立 schema；指定 `TEST_DATABASE_URL` 时库名必须以 `_test` 结尾。真实云端验证需显式执行 `.venv/bin/python -m scripts.contextdb_probe --write` 或 `.venv/bin/python -m scripts.contextdb_pipeline_smoke`，仅操作新建探测资源并记录清理结果。

新会话在既有 `agent_sessions.agent_config` 标记 `runtime=deepagents`，执行状态只保存在官方 LangGraph checkpoint。WeKnora 聊天、历史、审批与提问接口由 API Adapter 对接；审批 POST 只提交协议决定，随后的续接 GET 调用原生 `Command` 并流式返回。旧会话、运行记录、上传文件和沙箱卷保留，只读展示；旧执行入口继续拒绝执行。官方 StateBackend 提供会话文件、Skills 指令与工具调用，Docker 命令、终端、BrowserSkill、自动安装、steering 和应用层 fork/rewind 尚未接入。原组件没有能力开关的入口保留，API 明确拒绝，不伪装成功。源码核对与验证见 [官方对齐审计](docs/architecture/agent-official-alignment-audit.md)。

旧 `_governance` 保留只读。迁移记录见 `downloads/migrations/`。数据库备份可使用 `docker compose -f compose.postgres.yml exec -T postgres pg_dump -U showdoc showdoc_knowledge > <private-backup.sql>`；同时备份 `.env` 的加密密钥和产物目录。Agent 必须经 ASGI 启动：`app.py` 已默认启动 Uvicorn，也可执行 `.venv/bin/uvicorn asgi:create_app --factory --host 127.0.0.1 --port 8000`。本方案不部署生产 Agent Server、Redis 或 Helm，也不需要其部署许可；模型及 ContextDB 服务仍使用已配置账号。详见 [Agent 验证边界](docs/guides/agent-interaction-validation.md)。

原独立爬虫 CLI `main.py` 的 Docling 导出流程继续保留，供离线导出；平台 Worker 不调用该解析与切片链路。

更多边界与验收状态见 [当前架构与接口清单](docs/architecture/agent-platform.md)。
