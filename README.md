# ShowDoc AI Assistant

将多个知识库平台的文档转换为 Markdown、RAG JSONL 与大模型微调 JSONL。

工程结构、文件命名和文档归档规则见 [docs/engineering/project-structure.md](docs/engineering/project-structure.md)。

## 支持平台

| 分类键 | 平台 | 登录 | 入口 |
|---|---|---|---|
| `tiantong` | 天通资源管理中心 | 免登录 | `http://117.172.29.67:6067/knowledge` |
| `showdoc` | ShowDoc（云辉煌知识库） | 公开项目免登录；`--login` 或 `--list-projects` 需登录 | `https://yunhelp.gmgrasp.com.cn/server/index.php` |
| `cyb` | 管家婆云辉煌创业版 | 验证码 + 手机号自动登录（同一服务进程复用 token，失效后自动重登） | `https://new.yuncyb.com` |
| `web` | 通用网页 URL | 输入 URL，Crawl4AI 自动提取正文并输出 Markdown | 运行时传入 |

## 安装

需要 Python 3.10 或更高版本，项目推荐使用 `uv`：

```bash
uv venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python -r requirements-dev.txt  # 开发和回归测试
cp .env.example .env
# Crawl4AI 首次使用需要安装浏览器运行时
uv run --python .venv/bin/python crawl4ai-setup
```

在 `.env` 中配置云创业版手机号、密码和 DashScope API Key。内容清洗按源格式
分流：除 ShowDoc 外的 HTML 默认由 Crawl4AI 生成 Markdown；ShowDoc 的 Markdown
原文直接进入规范化管道。`auto` 模式只在单篇转换失败时回退，并在文档元数据中记录
实际引擎、版本和原因；所有入口在落盘前统一校验标题、代码围栏及图片/链接完整性。

## 运行

### 多平台统一入口（推荐）

```bash
python main.py --list-entries                       # 列出全部可用平台入口
python main.py --entry tiantong --list-documents    # 查看分类与文档数量
python main.py --entry tiantong                     # 全量爬取
python main.py --entry tiantong --limit 5           # 小样本试跑
python main.py --entry tiantong --pipeline builtin  # 指定清洗引擎

python main.py --entry showdoc --item 412 --list-documents  # 查看项目目录（公开项目免登录）
python main.py --entry showdoc --item 412                    # 全量爬取项目 412
python main.py --entry showdoc --list-projects               # 列出我的项目（需登录）

python main.py --entry cyb                       # 云创业版全量爬取（自动验证码登录）
python main.py --entry cyb --limit 5            # 小样本试跑
python main.py --entry web --url https://example.com/article  # 当前页正文提取
python main.py --entry web --url https://docs.example.com/guide \
  --crawl-mode site                                             # 同域整站采集
```

`web` 的 `site` 模式按“同一域名下全部可发现 HTML 页面”工作，不受输入 URL
路径限制：合并 `robots.txt`/sitemap、输入页、站点首页、渲染后链接、前端路由与
已捕获的只读分页接口，sitemap 不会阻止继续发现其未列出的页面。默认
`--max-pages 0 --max-depth 0`（不限制）；试跑大型网站时可显式设置非零上限。
整站模式只能发现公开可达或被 sitemap/页面链接公开声明的 URL，不能凭空获得
未链接、需登录或被验证码/反爬保护的内容。
整站结果另含 `crawl_report.json`，记录发现数、实际请求数、保存数以及失败、
拦截、空正文和重复正文 URL，便于核对采集完整性。

结果保存在 `downloads/tiantong/`：

- `<分类>/<标题>.md`：按分类目录组织的单篇文档（同分类同名自动追加 id 前缀防覆盖）。
- `天通资源管理中心知识库.md`：`# 平台 / ## 分类 / ### 文档` 结构的合并汇总。
- `assets/attachments/`：附件（附件下载地址 15 分钟失效，爬取时即时下载落盘）。
- `raw_documents.jsonl`：按源格式转换后的审计 Markdown，用于追溯和重新清洗。
- `source_documents.jsonl`：不可变源正文及哈希；转换失败后仍可审计和重新处理。
- `failed_documents.jsonl`：逐篇采集或转换失败清单；失败文档不会中断整批任务。
- `rag_documents.jsonl`：清洗后正文 + `metadata` 字段全量保留平台原始 16 个字段。
- `rag_chunks.jsonl`：按标题和段落切分的 RAG 分块，metadata 含分类、章节路径和分块序号。
- `quality_report.json`：本次任务的文档完整性、重复内容、标题结构与质量评分报告。

ShowDoc 结果保存在 `downloads/showdoc_<item_id>/`，结构同上；分类来自项目目录树（如 `根目录`、`一级目录/二级目录`）。

云创业版结果保存在 `downloads/cyb/`，结构同上；分类为 `使用教程/<模块>` 与 `常见问题/<业务类型>`，另含 `finetuning_cyb.jsonl`（FAQ 问答微调语料）。

`CYB_CONTENT_PIPELINE` 支持以下模式（`--pipeline` 同参数）：

- `crawl4ai`：仅使用 Crawl4AI。
- `auto`：优先使用 Crawl4AI，依赖不可用或运行失败时回退到内置转换器。
- `builtin`：使用项目内置转换器（支持标题、链接、图片、列表、代码块和 GFM 表格）。

## 回归测试

```bash
# 单元、数据完整性及真实 Chromium 集成回归
RUN_BROWSER_TESTS=1 .venv/bin/python -m pytest -q

# Crawl4AI 安装与浏览器健康检查
.venv/bin/crawl4ai-doctor
```

### 云创业版（兼容入口）

```bash
python cyb_rag_md.py   # 等价于 python main.py --entry cyb --out downloads/cyb
```

## Web UI

```bash
python app.py   # http://127.0.0.1:8000
```

页面分为“采集工作台、任务监控、数据集输出”三个独立工作区。采集工作台提供 5 种数据源用法（ShowDoc 同一站点拆分为公开项目和账号项目）：

| 标签 | 入口 | 登录 | 说明 |
|---|---|---|---|
| 云辉煌知识库 | `showdoc` | 免登录 | 填写公开项目 ID（如 412）后获取页面列表 |
| ShowDoc 登录 | `showdoc` | 用户名+验证码 | 自动识别验证码登录，下拉选择账号下的项目 |
| 云创业版 | `cyb` | 自动 | 验证码+手机号自动登录，免配置操作 |
| 天通 | `tiantong` | 免登录 | 资源管理中心全量 1500+ 文档 |
| 通用网页 URL | `web` | 免登录 | 单页或同域整站采集；自动匹配已验证适配器，其他站点使用 sitemap、渲染链接、动态路由和安全只读 API 分页发现 |

每个数据源支持：配置采集范围（含分类标签与关键词过滤）→ 文档目录选择 → 单篇预览 → 内容清洗 → 质量检查 → RAG 数据集生成 → ZIP 下载（分类目录 + 合并文档 + JSONL + 质量报告）。浏览器会记住当前任务编号，刷新后可恢复进度；同一时间只运行一个治理任务，失败或取消后可以直接重试。

通用网页入口只用于公开网页。系统优先遵守 `robots.txt` 并通过 sitemap 发现页面，不跨域，也不绕过登录、验证码、付费墙或其他访问控制；采集前仍需由使用者确认目标网站的服务条款、版权、隐私与访问频率要求。

同站采集只保留一个入口：输入 URL 后，系统先按域名匹配已验证的薄适配器；未匹配时自动回退增强型通用采集。任务输出额外包含 `crawl_report.json`，用于区分“内容质量”和“采集覆盖率”。当前已验证 `club.cmgrasp.com` 的公开问答、知识、课程、活动和公告分页接口，问答会合并公开回答。

后端为 registry 分发的通用接口，新增平台无需改动路由：

- `GET /api/entries` — 列出全部入口
- `GET /entries/web/inspect?url=` — 识别通用网页采集策略
- `GET /entries/<key>/documents` — 文档列表（`auth=1` 注入 ShowDoc 会话）
- `GET /entries/<key>/preview?doc_id=` — 单篇预览
- `POST /entries/<key>/start` — 启动爬取任务
- `GET /api/tasks` — 最近任务列表（不返回账号令牌等敏感参数）
- `GET /task_status/<task_id>` — 任务阶段、进度、质量指标与日志
- `POST /tasks/<task_id>/cancel` — 在安全检查点取消任务
- `POST /tasks/<task_id>/retry` — 重试失败或已取消任务
