# 多平台爬虫架构与重构记录

> 状态：第 1、2、3、4 阶段全部实施完成，并已完成工程目录与命名规范整理。
> 日期：2026-09-19

## 1. 背景与目标

项目需要同时支持三个知识库入口的爬取与下载，运行时按"平台分类 + 入口"选择目标：

| 入口 | 平台 | 地址 |
|---|---|---|
| 天通资源管理中心 | 免登录分页 API | `http://117.172.29.67:6067/knowledge` |
| 管家婆云创业版 | 手机号+验证码登录 REST | `https://new.yuncyb.com/aicyberp-api` |
| ShowDoc 文档站 | 用户名+验证码登录（目录树） | `https://yunhelp.gmgrasp.com.cn` |

**硬性约束**：

1. 爬取的数据结构与内容不能丢失——API 返回的所有字段必须完整保留；
2. 内容与分类一一对应——每个文档恰好归属一个分类，落盘目录、合并文档、JSONL 三处分组一致；
3. 新增平台时只需新增一个子类并在注册表登记一行。

## 2. 三入口实测记录（2026-09-18 探测）

### 2.1 天通资源管理中心（新增）

- 形态：Vite 构建的 SPA（IIS 7.5 托管），前端路由 `/knowledge`，数据接口前缀 `/api`。
- 列表接口：`GET /api/knowledge?page=N&pageSize=M`，**无需登录**，返回结构：

```json
{
  "code": 200,
  "data": {
    "list": [{
      "id": "uuid", "title": "...", "content": "<p>...</p>",
      "contentFileIds": null, "categoryId": "uuid", "categoryName": "V1\\V3\\A8做单提示",
      "keywords": "", "authorId": "uuid", "authorName": "小管",
      "attachments": "[]",           // JSON 字符串: [{fileId, name, isExternal}]
      "visibility": "all", "viewCount": 0, "status": 1,
      "createdAt": "2026-09-03T16:24:22.013", "updatedAt": "2026-09-18T10:07:06.513"
    }],
    "total": 1582, "page": 1, "pageSize": 100
  }
}
```

- 全量数据实测：**1582 条、120 个分类、16 页（100 条/页）**；`status` 全部为 `1`、`visibility` 全部为 `all`，无需按状态过滤。
- 列表接口**直接内联全文 HTML**，无需逐条二次请求。
- 正文图片为相对路径 `/uploads/knowledge/*.png`，须按站点根绝对化。
- 附件下载机制：`GET /api/upload/{fileId}/token` → `{downloadUrl, expiresIn: 900}`（**临时地址，15 分钟失效**），因此爬虫必须在抓取时直接下载附件落盘，不能记录临时 URL。全库仅 1 条记录带 1 个附件。
- 存在 **2 组同分类同标题** 的记录，文件名需按 id 去重，防止静默覆盖。
- 标题与分类名含反斜杠（`V1\V3\A8`），需文件名清洗。

### 2.2 云创业版（现有 `cyb_rag_md.py`）

- 登录：`/auth/captcha` → 千问 VL 识别 → `/auth/phone/login`，token 每次运行重新获取。
- 数据：`/tutorials`（含 category、coverImage、videoUrl）与 `/faqs`（faqTypeId → 中文分类映射），平铺列表。
- 产出：合并 MD、rag_documents.jsonl、rag_chunks.jsonl、finetuning_faq.jsonl。

### 2.3 ShowDoc（现有 `crawlers/showdoc.py` 与 `integrations/showdoc/`）

- 登录：`/api/common/createCaptcha` → 图片 → 千问 VL 识别 → `/api/user/loginByVerify`，认证实现位于 `integrations/showdoc/auth.py`。
- 数据：`/api/item/myList` → `/api/item/info`（目录树 catalogs + 根 pages）→ `/api/page/info`（逐页正文）。

## 3. 现有代码问题分析

1. **同一平台两套实现（历史问题）**：早期 `crawler.py` 的 `YunHuiHuangCrawler` 与 `showdoc_crawler.py` 的 `ShowDocCrawler` 调用同一批接口并重复实现 `crawl()`；当前已合并为 `crawlers/showdoc.py`。
2. **两套验证码识别**：ShowDoc 走 dashscope SDK（`integrations/showdoc/auth.py`），CYB 用 urllib 裸调，能力边界相近。
3. **清洗管道曾被锁死**：早期 `cyb_rag_md.py` 的 `RAGContentPipeline` 只服务 CYB，且内部硬编码 `new.yuncyb.com`。当前已统一为 Crawl4AI → Markdown 结构规范化 → 标题感知 RAG 分块，并由内置转换器提供离线回退。
4. **入口无法选择**：`app.py` 按路由硬编码平台，`cyb_rag_md.py` 只能跑 CYB，没有统一的"分类 → 入口"选择机制。

## 4. 目标架构设计

### 4.1 目录结构

```
common/
  __init__.py
  converter.py    通用清洗管道：HTML→MD、资源提取/回补、RAGContentPipeline、分块、JSONL
crawlers/
  __init__.py
  base.py         BaseCrawler 模板基类 + DocumentStub/CrawledDocument 规范结构
  tiantong.py     天通爬虫（第 1 阶段）
  showdoc.py      ShowDoc 爬虫（第 2 阶段，合并现有两套实现）
  cyb.py          云创业版爬虫（第 3 阶段，从 cyb_rag_md.py 拆出）
  web.py          通用网页爬虫
  web_adapters.py 已验证站点适配器
  web_discovery.py 通用动态链接与只读分页发现
integrations/
  showdoc/
    auth.py       ShowDoc 验证码和登录
    project.py    ShowDoc 项目列表与缓存
registry.py       入口注册表：分类键 → 爬虫类（新增平台只改这里）
main.py           CLI 入口：--entry 选择平台
app.py            Web 端（第 4 阶段改走 registry）
cyb_rag_md.py     历史启动入口（薄委托，等价 python main.py --entry cyb）
```

### 4.2 核心抽象（crawlers/base.py）

```python
@dataclass
class DocumentStub:          # 目录/选择阶段的最小单元
    id: str
    title: str
    category: str

@dataclass
class CrawledDocument:       # 抓取完成的规范结构
    id: str
    title: str
    category: str
    content: str             # 原始正文，语法由 source_format 明确声明
    updated_at: str
    metadata: dict           # 平台原始字段全量保留（数据不丢失的关键）
    source_format: str       # html / markdown；禁止按正文内容猜测
    raw_markdown: str = ""   # 转换后的审计原文
    markdown: str = ""       # 清洗后的正文
    resources: dict = ...    # {images: [...], links: [...]}

class BaseCrawler:
    platform / display_name / entry_url / site_base_url / requires_auth  # 类属性

    # 子类必须实现
    def authenticate(self): ...            # 免登录平台不覆写
    def list_documents(self) -> list[DocumentStub]: ...
    def fetch_document(self, stub) -> CrawledDocument: ...

    # 可选钩子
    def supplement_resources(self, doc, resources): ...   # 附件等 HTML 外资源并入
    def build_finetuning_records(self, docs): ...         # 仅问答型平台（FAQ）

    # 模板方法（子类不覆写）
    def crawl(self, selected_ids=None, selected_titles=None) -> CrawlSummary:
        authenticate → list_documents → 选择过滤 → 逐条 fetch →
        按 source_format 分流 → 提取对应语法资源 → RAGContentPipeline.convert →
        按分类落盘（单文件 + 合并文档 + JSONL）
```

### 4.3 数据保真设计（约束 1）

- **原始字段全量入 JSONL**：`rag_documents.jsonl` 每行的 `metadata` 字段保存该条记录 API 返回的**全部原始字段**（天通 16 个字段一个不少），`content` 为清洗后的 Markdown，`html` 不入库但 `metadata` 中的原始结构与 ID 均在。
- **源格式是数据契约**：`CrawledDocument.source_format` 必须由采集器明确给出。HTML 进入 HTML 转换通道；ShowDoc 等 Markdown 原文直接进入 Markdown 规范化通道，禁止再包装成 HTML 后二次转换。
- **资源按源语法提取**：HTML 使用标签解析器，Markdown 使用 `markdown-it-py` AST；图片和链接在规范化后逐 URL 核对，缺失资源会被回补并再次校验。
- **落盘前强校验**：所有入口在 `_save` 前统一验证非空正文，包括正文 H1、标题跳级、未闭合代码围栏、解析器标题数不一致、单行结构压平、图片/链接遗漏。校验失败直接终止任务，不生成伪合格 RAG 语料。
- **HTML 离线转换不降级结构**：内置转换器原生处理标题、段落、链接、图片、嵌套列表、围栏代码块和 GFM 表格；代码块内部空白原样保留。
- **附件落盘**：天通附件在抓取时通过 token 接口下载到 `assets/attachments/`，Markdown 中以相对路径引用；下载失败仅告警，metadata 仍保留原始 `attachments` 字符串。
- **同名不覆盖**：同分类同标题的文档在生成文件名时追加 id 前 8 位，杜绝静默覆盖丢数据。

### 4.4 分类一一对应设计（约束 2）

天通的 `categoryName` 为单一值（每个文档恰好一个分类），以它为唯一分组键：

1. **单文件**：`downloads/tiantong/<分类>/<标题>.md`，文件头显式写明 `- **分类**: <categoryName>`；
2. **合并文档**：`downloads/tiantong/天通资源管理中心知识库.md`，结构固定为 `# 平台` → `## 分类` → `### 文档标题` → 正文；
3. **JSONL**：每条记录带 `category` 字段；分块 `rag_chunks.jsonl` 的 metadata 同样带 `category`。

三处分组来自同一个 `docs_by_category`（OrderedDict，保持 API 返回顺序），结构上不可能不一致。验证脚本核对：API 分类计数 == 分类目录文件数 == 合并文档章节数 == JSONL 分类计数。

### 4.5 内容管道参数化（消除硬编码）

`cyb_rag_md.py` 增加可选参数 `site_base_url`（默认 None → 沿用 `CYB_API_BASE_URL`，行为完全不变）：

- `normalize_resource_url(url, site_base_url=None)`
- `normalize_markdown(markdown, heading_offset=0, site_base_url=None)`
- `normalize_document_markdown(markdown, title, base_heading_level=2)`
- `extract_html_resources(html_content, site_base_url=None)`
- `ensure_markdown_resources(markdown, resources, heading_offset=0, site_base_url=None)`
- `split_markdown_sections_for_rag(markdown, max_chars, overlap)`
- `RAGContentPipeline(mode, asset_dir, site_base_url)`，其中 `CrawlerRunConfig.base_url` 与回补逻辑均使用注入值

天通注入 `http://117.172.29.67:6067` 后，正文相对路径图片/链接自动绝对化，Crawl4AI 也能正确解析相对资源。

### 4.6 入口选择（registry.py + main.py）

```bash
python main.py --list-entries                      # 列出全部可用入口
python main.py --entry tiantong --list-documents   # 查看分类与数量（不落盘）
python main.py --entry tiantong                    # 全量爬取
python main.py --entry tiantong --limit 5          # 小样本试跑
python main.py --entry tiantong --page-size 100 --pipeline builtin
```

注册表条目：`key / crawler_class / display_name / entry_url / requires_auth / description`。Web 端（第 4 阶段）与 CLI 共用同一注册表。

## 5. 分阶段实施计划

| 阶段 | 内容 | 状态 |
|---|---|---|
| 1 | registry + BaseCrawler + 天通爬虫 + CLI + 管道参数化 | ✅ 已完成 |
| 2 | 合并 ShowDoc 两套实现迁入基类 + app.py 迁移到统一爬虫（`/get_pages`、`/preview_page`、`/start_crawl`、`/showdoc/*`） | ✅ 已完成 |
| 3 | CYB 从 cyb_rag_md.py 拆出爬虫类，清洗管道独立成 common/converter.py | ✅ 已完成 |
| 4 | app.py 收敛为 registry 分发，前端平台选择器与注册表对齐 | ✅ 已完成 |

选择"天通先行"的原因：免登录、结构最简单，用它先把抽象跑通并验证，风险最低且立刻有新入口产出。

## 6. 验证方案与记录

### 第 1 阶段验证（2026-09-18，全量 1582 条实测）

- [x] `--list-entries` 正常列出入口；`--list-documents` 列出 120 分类 1582 条
- [x] 数量一致：API 1582 = 单文件 MD 1582 = JSONL 1582 = 合并文档标题 1582；分块 1862
- [x] 分类一一对应：API 分类计数 == 磁盘分类目录文件数 == JSONL 分类计数 == 合并文档章节数（120 个分类逐一核对全部一致）
- [x] 字段保真：JSONL metadata 含全部 16 个原始字段；空正文 16 条如实标记
- [x] 图片 URL 全部绝对化（`/uploads/...` → `http://117.172.29.67:6067/uploads/...`），残留相对路径 0 条
- [x] 资源列表无重复 URL；资源回补区块仅 1 条（真实漏图场景）
- [x] 同名文档去重生效（2 组同名追加 id 前缀）
- [x] 附件下载落盘（`assets/attachments/0bed6a68_Gp_ImportAc_IniAccount.sql`）

验证中发现并修复的两个数据保真缺陷：

1. `normalize_markdown` 的链接正则不容忍 alt 含裸 `]`（标题"…【采购退货总额]"做图片说明时失配），导致相对路径未绝对化且回补机制重复追加资源；改为懒惰匹配最近的 `](url)`（行为与原正则在正常场景一致）。
2. `extract_html_resources` 按 (alt, url) 去重，同一图片不同 alt 会重复记录；改为按 URL 去重（首次 alt 保留）。

两个修复均通过 CYB 默认行为回归测试（`new.yuncyb.com` 路径不受影响）。

### Markdown 原生管道根治验证（2026-09-19，ShowDoc 真实存量回放）

历史 ShowDoc 管道把 `page_content`（Markdown）误放进 HTML 字段，再包装为 HTML 交给转换器，导致章节换行被压平；资源提取器同时只识别 `<img>/<a>`，因此质量报告会错误地给出高分。

本次改造删除了这个错误的数据模型：正文统一使用 `content + source_format`，ShowDoc 明确声明 `markdown` 并直接规范化。对项目 412 的 19 条真实 API 原文回放结果：

- [x] 19/19 正文非空，行首标题 1087 个，`markdown-it-py` 识别标题同为 1087 个
- [x] 图片资源 896 个、链接资源 96 个，正文缺失资源 0 个
- [x] 单行结构压平 0 篇，残留 `<center>/<video>` 展示标签 0 篇
- [x] 标题感知 RAG 分块 1051 个，质量错误 0、警告 0
- [x] 全量单元测试 37 项通过，覆盖源格式强制声明、Markdown 原生分流、HTML 表格/代码块、空转换拒绝、资源对应和标题层级修复

### 第 2 阶段验证（2026-09-18，项目 412 全量 + Web UI 浏览器实测）

**实现内容：** `crawlers/showdoc.py` 已合并早期两套 ShowDoc 爬虫实现，认证与项目管理分别归档到 `integrations/showdoc/auth.py` 和 `integrations/showdoc/project.py`。`app.py` 通过 `registry.py` 统一分发文档列表、预览和任务执行接口。

**单元测试：**
- [x] 目录树路径：根目录页面 / 一级目录 / 一级/二级嵌套目录生成的 `category` 路径全部正确
- [x] 标题降级 `_demote_headings`：代码块内标题不动，正文标题统一降级到文档标题（###）之下

**CLI 全量爬取（`python main.py --entry showdoc --item 412`，匿名访问公开项目）：**
- [x] 数量一致：API 菜单 19 = MD 文件 19 = JSONL 19 = 合并文档标题 19；分块 406
- [x] 字段保真：JSONL metadata 含全部 16 个原始字段；空正文 0 条
- [x] 分类一一对应：全部 19 条归入"根目录"，目录/合并文档/JSONL 一致
- [x] 单文件标题去重：文档首行 H1 与元信息标题重复时自动去除（`re.MULTILINE` 修复）

**Web UI 浏览器实测（Playwright，Flask 端口 8000）：**
- [x] `/get_pages?item_id=412`：匿名列出 19 个页面，前端复选框列表渲染正常
- [x] 选择性爬取：勾选 2 页 → 后台任务完成（"共 2 个页面，1 个分类"）→ 下载 ZIP
- [x] ZIP 内容：`根目录/` 分类目录 2 个 MD + 合并文档 `云辉煌 AI.md`（`## 根目录` → `### 文档`）+ 两个 JSONL（metadata 16 字段完整）
- [x] 预览：`/preview_page` 渲染完整文档内容（含 38 张内嵌图片）
- [x] ShowDoc 面板：未登录时项目下拉/下载模式/开始按钮全部正确禁用
- [x] 错误处理：不存在的页面 ID 预览显示"加载失败"提示而非崩溃；修正模板中过期的默认页 ID（8653 → 8652）

**已知限制补充记录（2026-09-18 密钥更新后已闭环）：**
- 第 2 阶段验证时 DASHSCOPE_API_KEY / QWEN_API_KEY 过期（401 InvalidApiKey）导致登录流程无法实测；用户更新密钥后已补测：ShowDoc 验证码登录 + `--list-projects` 成功（13 个项目），CYB 验证码登录成功（见第 3 阶段验证）。

### 第 3 阶段验证（2026-09-18，CYB 全量 102 条实测）

**实现内容：** 清洗管道（HTMLToMarkdown、prepare_html_content、normalize/ensure 资源系列、RAGContentPipeline、split_markdown_for_rag、write_jsonl）原样迁移到 `common/converter.py`（AST 逐函数比对一致）；`crawlers/cyb.py` 提供 CYBAuthenticator（验证码 + 千问 VL + 手机号登录）与 CYBCrawler；`registry.py` 登记 `cyb`；`cyb_rag_md.py` 改为薄兼容入口（委托统一框架，等价 `python main.py --entry cyb`）。

**真实登录实测：**
- [x] 千问 VL 验证码识别 + 手机号登录成功（约 1-2 次尝试，属概率性识别，失败自动刷新重试）
- [x] API 实测：/tutorials 42 条（13 字段，15 条纯视频教程无 content）、/faqs 60 条（16 字段）

**分类设计：** 教程 `使用教程/<模块>`（基础/采购/销售/库存/财务/资料管理/财务管理/销售管理/采购管理/库存管理），FAQ `常见问题/<业务类型>`（FAQ_TYPE_MAPPING，faqTypeId=0 归入其他常见问题），两类内容不混分类。

**全量爬取验证（102 条 / 18 分类）：**
- [x] 数量一致：JSONL 102 = MD 文件 102 = 合并文档标题 102；分块 104；微调 60（全部 FAQ，结构完整）
- [x] 分类一一对应：JSONL 分类数 = 磁盘目录数 = 合并文档章节数（18），逐分类数量全部一致
- [x] 字段保真：metadata 并集与 API 实测字段完全一致（教程 13 字段、FAQ 16 字段）；逐条缺失键均为 API 侧行为（纯视频教程无 content、文本教程无 videoUrl、部分 FAQ 省略 null 字段），非爬虫丢失
- [x] 视频教程 15 条：封面图与视频链接全部进入正文与 resources
- [x] 正文相对路径残留 0 条；正文 H1 与文档标题重复 0 条
- [x] 回归：showdoc（3 条）与 tiantong（3 条）冒烟测试通过，`assemble_html` 钩子对默认实现无副作用

验证中发现并修复的一个缺陷：

1. 旧 CYB 流程先对正文做首部 H1 去重、再前置封面图；迁入统一框架时封面在 `fetch_document` 就拼到正文前，破坏了 `prepare_html_content` 的 `^<h1>` 锚定去重（"商品信息"教程正文 H1 未去重）。修复：BaseCrawler 新增 `assemble_html` 钩子（`prepare_html_content` 之后、资源提取之前调用），CYB 把封面/视频链接的拼接移入该钩子。

### 第 4 阶段验证（2026-09-18，registry 分发接口 + 前端四标签实测）

**实现内容：**

- app.py 删除按平台硬编码的任务函数与路由（`/get_pages`、`/preview_page`、`/start_crawl`、`/showdoc/pages`、`/showdoc/start_crawl`），收敛为 registry 分发的通用接口：
  - `GET /api/entries`：列出注册表全部入口
  - `GET /entries/<key>/documents`：文档列表（`auth=1` 时注入 ShowDoc 会话 token）
  - `GET /entries/<key>/preview?doc_id=`：单篇预览
  - `POST /entries/<key>/start`：启动爬取任务
  - 保留 `/showdoc/login`、`/showdoc/projects`（登录与项目选择属平台特有能力）
- 前端平台选择器由 2 按钮扩展为 4 标签：云辉煌知识库（`yun`，匿名公开项目）/ ShowDoc 登录（`showdoc`）/ 云创业版（`cyb`）/ 天通（`tiantong`），每个标签内含独立的下载模式、页面选择（全选/过滤/预览）、进度与下载控件；cyb/tiantong 走通用 `entryState` 控制器，新增平台只需注册表加一行 + 前端加一个 section。
- 预览管道统一：HTML 站点（cyb/tiantong）先 `prepare_html_content` + `assemble_html` 钩子，检测到块级标签再转 Markdown 并 `normalize_markdown(site_base_url=...)` 绝对化相对图片地址；ShowDoc 直接返回 Markdown 源文。

**curl 接口实测：**

- [x] `/api/entries` 返回 3 个入口；`/entries/showdoc/documents?item_id=412` 匿名 19 页、`?auth=1&item_id=13` 登录后 280 页
- [x] `/entries/tiantong/documents` 1584 页（实时拉取，上游偶发 503 重试即恢复）；`/entries/cyb/documents` 102 页（自动验证码登录）
- [x] 三平台 preview 均返回可渲染内容；天通预览图片经站点根绝对化后在模态框内正常加载
- [x] 三平台 start → /task_status 轮询 → /download 全周期完成，ZIP 含分类目录 + 合并文档 + JSONL（cyb 另含 finetuning_cyb.jsonl）

**浏览器实测（Playwright，Flask 端口 8000，四标签全量回归）：**

- [x] 天通：切标签 → 列表 1584 页 → 过滤定位 → 预览（图片加载成功）→ 选择性爬取 1 页 → 完成 → ZIP 含 `V1_V3_A8登录提示/` 分类目录 + 合并文档 + 2 个 JSONL
- [x] 云创业版：列表 102 页（分类 chip 显示 `使用教程/基础` 等）→ 视频教程预览（封面图 + 可点的"打开视频教程"链接）→ 选择性爬取 2 页 → ZIP 含 `使用教程_基础/4.仓库信息.md`、`常见问题_销售业务/销售单折扣在哪查看？.md`、合并文档及 3 个 JSONL（finetuning 的 system prompt 与图片 URL 正确）
- [x] ShowDoc 登录：立即登录（验证码自动识别）→ 项目下拉 13 个项目 → 选择项目 13 → 获取 280 页（含分类标签）→ 预览"产品简介" → 选择性爬取 1 页 → ZIP 含 `根目录/产品简介.md` + 合并文档
- [x] 云辉煌（匿名）：默认项目 412 → 列表 19 页正常渲染

验证中发现并修复的三个缺陷：

1. **视频教程预览 404**：纯视频教程正文为空，封面图与视频链接由 `assemble_html` 钩子补齐，而预览路径原实现跳过空正文。修复：预览统一先跑 `prepare_html_content` + `assemble_html` 再做 HTML 检测，空正文文档也能拼出可预览内容。
2. **预览相对图片不加载**：天通正文 `/uploads/...` 相对路径在模态框内无法解析。修复：预览转换后追加 `normalize_markdown(heading_offset=0, site_base_url=crawler.site_base_url)` 绝对化。
3. **前端 Markdown 链接渲染错乱**：链接 `[text](url)` 转换若放在段落包裹之前，`<p>` 会插入 `<a>` 开标签内，触发浏览器 adoption agency 重构出空链接 + 文本重复。修复：链接转换移到段落包裹与空段清理之后（最末执行）。

已知限制：云创业版封面图直链（`new.yuncyb.com/tutorial/video/cover/...`）在预览模态框内不显示——站点对静态资源请求返回 SPA 回退 HTML，属平台侧限制，URL 本身正确（下载后的 Markdown 中可正常访问）。

## 7. 风险与注意事项

- 天通站点为 HTTP 明文 + 公开列表接口，爬取需控制分页节奏（默认 50/页，串行请求），避免对生产环境造成压力。
- 附件 token 15 分钟失效，附件必须在列表抓取后立即下载（当前实现为逐条即时下载）。
- `attachments` 是 JSON 字符串而非数组，解析失败时保留原始字符串并告警，不中断整体流程。
- 第 2 阶段合并 ShowDoc 时需保留 `progress_callback` 与 `selected_titles` 的 Web 前端契约。
