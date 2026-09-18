# ShowDoc AI Assistant

将多个知识库平台的文档转换为 Markdown、RAG JSONL 与大模型微调 JSONL。

## 支持平台

| 分类键 | 平台 | 登录 | 入口 |
|---|---|---|---|
| `tiantong` | 天通资源管理中心 | 免登录 | `http://117.172.29.67:6067/knowledge` |
| `showdoc` | ShowDoc（云辉煌知识库） | 公开项目免登录；`--login` 或 `--list-projects` 需登录 | `https://yunhelp.gmgrasp.com.cn/server/index.php` |
| `cyb` | 管家婆云辉煌创业版 | 验证码 + 手机号自动登录 | `https://new.yuncyb.com` |

## 安装

需要 Python 3.10 或更高版本：

```bash
python -m pip install -r requirements.txt
cp .env.example .env
```

在 `.env` 中配置云创业版手机号、密码和 DashScope API Key。需要启用完整的
`Crawl4AI -> Firecrawl` 流水线时，再配置 `FIRECRAWL_API_KEY`。

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
```

结果保存在 `downloads/tiantong/`：

- `<分类>/<标题>.md`：按分类目录组织的单篇文档（同分类同名自动追加 id 前缀防覆盖）。
- `天通资源管理中心知识库.md`：`# 平台 / ## 分类 / ### 文档` 结构的合并汇总。
- `assets/attachments/`：附件（附件下载地址 15 分钟失效，爬取时即时下载落盘）。
- `rag_documents.jsonl`：清洗后正文 + `metadata` 字段全量保留平台原始 16 个字段。
- `rag_chunks.jsonl`：按段落切分并保留重叠上下文的 RAG 分块（metadata 含分类）。

ShowDoc 结果保存在 `downloads/showdoc_<item_id>/`，结构同上；分类来自项目目录树（如 `根目录`、`一级目录/二级目录`）。

云创业版结果保存在 `downloads/cyb/`，结构同上；分类为 `使用教程/<模块>` 与 `常见问题/<业务类型>`，另含 `finetuning_cyb.jsonl`（FAQ 问答微调语料）。

`CYB_CONTENT_PIPELINE` 支持以下模式（`--pipeline` 同参数）：

- `auto`：使用 Crawl4AI；存在 Firecrawl Key 时追加 Firecrawl Parse。
- `crawl4ai_firecrawl`：强制两阶段处理，缺少 Key 或调用失败时终止。
- `crawl4ai`：仅使用 Crawl4AI。
- `builtin`：使用项目内置的轻量转换器。

### 云创业版（兼容入口）

```bash
python cyb_rag_md.py   # 等价于 python main.py --entry cyb --out downloads/cyb
```

## Web UI

```bash
python app.py   # http://127.0.0.1:8000
```

页面顶部 4 个平台标签对应注册表的三个入口（ShowDoc 同一站点拆分为匿名/登录两种用法）：

| 标签 | 入口 | 登录 | 说明 |
|---|---|---|---|
| 云辉煌知识库 | `showdoc` | 免登录 | 填写公开项目 ID（如 412）后获取页面列表 |
| ShowDoc 登录 | `showdoc` | 用户名+验证码 | 自动识别验证码登录，下拉选择账号下的项目 |
| 云创业版 | `cyb` | 自动 | 验证码+手机号自动登录，免配置操作 |
| 天通 | `tiantong` | 免登录 | 资源管理中心全量 1500+ 文档 |

每个标签支持：获取页面列表（含分类标签与关键词过滤）→ 单篇预览 → 全量/选择性爬取 → 进度轮询 → ZIP 下载（分类目录 + 合并文档 + JSONL）。

后端为 registry 分发的通用接口，新增平台无需改动路由：

- `GET /api/entries` — 列出全部入口
- `GET /entries/<key>/documents` — 文档列表（`auth=1` 注入 ShowDoc 会话）
- `GET /entries/<key>/preview?doc_id=` — 单篇预览
- `POST /entries/<key>/start` — 启动爬取任务
