# 工程结构与命名规范

## 目标

项目采用“根目录只放启动入口，业务代码按职责分包，部署资产统一归 `deploy/`，测试按域分子包，文档按用途归档”的结构。整理只改变文件归属和引用路径，不改变现有功能与启动命令。

## 当前结构

```text
.
├── app.py                         # 应用工厂 + 静态托管；__main__ 启动 Uvicorn ASGI，路由全部由 webapi/ 提供
├── asgi.py                        # ASGI 入口（create_app 工厂，供 uvicorn --factory）
├── main.py                        # 统一 CLI 入口
├── registry.py                    # 平台注册与爬虫工厂
├── requirements.txt / requirements-dev.txt / pytest.ini   # 运行时依赖、开发依赖与 pytest 配置
├── .env.example                   # 环境变量模板
├── agent/                         # DeepAgents 运行时：图、会话、模型传输、MCP、技能打包、model_catalog 目录数据（内部结构由 deploy/async-agent/aegra.json 的 graph 文件路径钉死，不重组）
├── webapi/                        # 全部 HTTP 路由（Blueprint 按域拆分）
│   ├── contextdb/                 # ContextDB 官方 API 转发域（__init__ 转发核心 + files / preview / source_images）
│   ├── weknora/                   # WeKnora 协议兼容层（adapter / agents / artifacts / async_views / prompts / sandbox_terminal / terminal / traces），命名保留协议语义
│   ├── chat/                      # 聊天域（chat_interactions / chat_resources / chat_suggestions）
│   ├── runtime/                   # 运行时配置域（mcp_runtime / model_runtime / skill_runtime / runtime_settings + mcp_usage_prompt.txt 资产）
│   └── agent / auth / browser / harness / knowledge / material / platform / retired_runtime  # 根级域模块
├── common/                        # 跨平台内容转换、RAG 分块、质量检查
├── crawlers/                      # 平台爬虫和通用网页发现能力
├── governance/                    # ContextDB 治理存储、任务 worker、发布与知识库同步
├── integrations/                  # 外部平台认证、项目管理等集成（showdoc / contextdb）
├── frontend/                      # Vue 3 + TDesign 前端源码，构建产物 dist 由 Flask 托管
│   ├── src/                       # 应用源码；npm run build 生成 dist/（git 忽略）
│   ├── e2e / scripts / tests      # 端到端用例、构建辅助脚本与前端自测
├── scripts/
│   ├── ops/                       # 运维与迁移脚本（migrate / isolate / repair / configure_contextdb_dev）
│   ├── smoke/                     # 冒烟与探针（会被测试 import 的脚本）
│   └── verify_*.py / acceptance_real_*.py 等   # 手动验证与真实环境验收套件（dev_api.sh 开发启动）
├── tests/                         # 自动化测试，按域分子包
│   ├── conftest.py                # 共享 fixture，仅保留根级一个
│   ├── fakes/                     # 测试替身（aegra_fake / contextdb_fake）
│   ├── agent/                     # agent 域
│   ├── platform/                  # 平台集成域：同一 ASGI 面的集成测试（43 个），经 test_platform_harness 夹具集线，刻意保持单层不二次分层；非集成性质的域测试已按域归入对应子包
│   ├── contextdb/                 # ContextDB 与知识库域
│   ├── crawlers/                  # 爬虫域
│   ├── governance/                # 治理存储域
│   └── common/                    # 公共工具域
├── deploy/                        # 唯一部署根
│   ├── compose/                   # postgres / opensandbox / agent-runtime 三个 compose 文件
│   ├── async-agent/               # Aegra 异步 Agent 镜像构建上下文（Dockerfile 全套）
│   ├── attachment-parser/         # 附件解析镜像
│   └── opensandbox.local.toml / sandbox-pty-prompt.sh / opensandbox*.md  # 沙箱本地配置、PTY 提示与说明
└── docs/                          # 工程、架构、操作与归档文档
    ├── architecture/              # 架构决策与能力边界
    │   └── reports/               # 日期后缀的验证报告（审计机器快照 JSON 已清理，仅存 md 报告）
    ├── engineering/              # 结构与命名规范
    ├── guides/                    # 操作指南
    └── archive/                  # 已退役文档与历史验证日志
```

运行时产物不属于源代码结构：`downloads/`（运行时数据根，由 `GOVERNANCE_DATA_DIR` 重定向）、`output/`（验证报告根）、`logs/`、`.runtime/`（运行时凭据与探活状态）统一由 `.gitignore` 排除，不得纳入源码清理或迁移范围。

`deploy/async-agent/` 是宿主机路径；镜像内刻意保留 `/app/deployment/async-agent/` 容器路径（Dockerfile COPY 目标、`AEGRA_CONFIG` 与 `start.py` 均指向容器路径）。这一不对称是为零行为变化保留的既定差异，改动它必须重建镜像并做运行冒烟。`registry.py` 留在根目录是本规范文档化的例外（爬虫注册表被 `app.py` 与 CLI 直接导入）。

## 命名规则

| 对象 | 规则 | 示例 |
|---|---|---|
| Python 文件 | 小写 `snake_case`，一个文件表达一个清晰职责 | `web_discovery.py` |
| Python 包 | 小写单词或 `snake_case`，按业务边界分组 | `crawlers/`、`integrations/` |
| 类 | `PascalCase` | `WebCrawler`、`ShowDocAuthenticator` |
| 函数和变量 | 小写 `snake_case` | `infer_pagination_plans` |
| 常量 | `UPPER_SNAKE_CASE` | `DEFAULT_BASE_URL` |
| 测试文件 | `test_<module>.py`，按域放对应子包 | `tests/crawlers/test_web_crawler.py` |
| 文档目录 | 小写英文目录名，按用途分类 | `docs/architecture/` |
| Markdown 文档 | 小写英文 `kebab-case` | `multi-platform-crawler-refactor.md` |
| 前端文件 | 小写英文，Vue 组件 `PascalCase.vue`，按视图/组件分目录 | `KnowledgeView.vue`、`backend.ts` |
| 运行输出 | 固定输出目录，不与源码混放 | `downloads/<task_id>/` |

## 入口约定

以下启动方式保持不变：

```bash
python app.py
python main.py --list-entries
python main.py --entry cyb
```

云创业版旧入口 `cyb_rag_md.py` 已删除，等价命令为 `python main.py --entry cyb`。

`showdoc_auth.py` 和 `showdoc_project.py` 已不再作为根目录模块保留；它们的正式实现分别位于 `integrations/showdoc/auth.py` 和 `integrations/showdoc/project.py`。业务代码必须从规范路径导入，不再新增根目录兼容文件。

## 手动验证脚本登记

`scripts/` 根下的手动验证与真实环境验收脚本没有自动化调用方，用途登记如下：

| 脚本 | 用途 |
|---|---|
| `acceptance_real_agent.py` / `acceptance_real_http.py` / `acceptance_real_isolation.py` | 真实 provider/HTTP 的验收与授权检查（按需手动执行） |
| `verify_async_agent_runtime.py` / `verify_async_multitask.py` | 异步运行服务健康与并发策略核验（容器名对齐 compose 项目名） |
| `verify_async_scope.py` | 异步服务 HTTP 授权范围实时核验 |
| `verify_crawler_names.py` / `verify_knowledge_names.py` | 知识/爬虫命名核对（测试在用） |
| `dev_api.sh` | 开发 API 启动（watchfiles 热重载） |

## 新增文件放置原则

1. 新平台爬虫放到 `crawlers/`，并通过 `registry.py` 注册。
2. 外部平台认证、SDK、项目管理等连接器放到 `integrations/<platform>/`。
3. 可被多个平台复用的内容处理逻辑放到 `common/`，不得复制到平台爬虫。
4. HTTP 路由一律进 `webapi/` 对应模块，根目录 `app.py` 不再新增内联路由。
5. 部署相关资产（compose 文件、Dockerfile、镜像构建上下文、部署配置）一律进 `deploy/`，根目录不再新增 compose 文件。
6. 新测试按域放 `tests/<domain>/`，测试替身放 `tests/fakes/`，文件名以 `test_` 开头；`conftest.py` 仅保留根级一个。
7. 运维/迁移脚本放 `scripts/ops/`；会被测试 import 的冒烟/探针脚本放 `scripts/smoke/`；一次性手动验证脚本放 `scripts/` 根。
8. 审计快照 JSON 与日期后缀的验证报告放 `docs/architecture/reports/`；正式方案文档放 `docs/architecture/` 或 `docs/requirements/`。
9. 根目录不新增随意命名的文档或临时文件。
