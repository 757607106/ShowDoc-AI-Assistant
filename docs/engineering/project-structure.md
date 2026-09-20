# 工程结构与命名规范

## 目标

项目采用“根目录只放启动入口，业务代码按职责分包，文档按用途归档”的结构。整理只改变文件归属和引用路径，不改变现有功能与启动命令。

## 当前结构

```text
.
├── app.py                         # Flask Web 入口，启动命令保持不变
├── main.py                        # 统一 CLI 入口
├── cyb_rag_md.py                  # 云创业版历史启动入口，功能委托给统一 CLI
├── registry.py                    # 平台注册与爬虫工厂
├── requirements.txt               # 运行时依赖
├── .env.example                   # 环境变量模板
├── common/                        # 跨平台内容转换、RAG 分块、质量检查
│   ├── converter.py
│   └── quality.py
├── crawlers/                      # 平台爬虫和通用网页发现能力
│   ├── base.py
│   ├── showdoc.py
│   ├── cyb.py
│   ├── tiantong.py
│   ├── web.py
│   ├── web_adapters.py
│   └── web_discovery.py
├── integrations/                  # 外部平台认证、项目管理等集成
│   └── showdoc/
│       ├── auth.py
│       └── project.py
├── templates/                     # Jinja 页面模板
├── static/                        # 前端静态资源
│   ├── css/
│   └── js/
├── tests/                         # unittest / pytest 均可执行的自动化测试
└── docs/                          # 工程、架构、操作和需求文档
    ├── architecture/
    ├── engineering/
    ├── guides/
    ├── requirements/
    └── archive/
```

运行时生成的 `downloads/`、缓存和 Python 字节码不属于源代码结构，统一由 `.gitignore` 排除。

## 命名规则

| 对象 | 规则 | 示例 |
|---|---|---|
| Python 文件 | 小写 `snake_case`，一个文件表达一个清晰职责 | `web_discovery.py` |
| Python 包 | 小写单词或 `snake_case`，按业务边界分组 | `crawlers/`、`integrations/` |
| 类 | `PascalCase` | `WebCrawler`、`ShowDocAuthenticator` |
| 函数和变量 | 小写 `snake_case` | `infer_pagination_plans` |
| 常量 | `UPPER_SNAKE_CASE` | `DEFAULT_BASE_URL` |
| 测试文件 | `test_<module>.py` | `test_web_discovery.py` |
| 文档目录 | 小写英文目录名，按用途分类 | `docs/architecture/` |
| Markdown 文档 | 小写英文 `kebab-case` | `multi-platform-crawler-refactor.md` |
| 前端资源 | 小写英文，按类型进入 `static/css` 或 `static/js` | `app.css`、`app.js` |
| 运行输出 | 固定输出目录，不与源码混放 | `downloads/<task_id>/` |

## 入口约定

以下启动方式保持不变：

```bash
python app.py
python main.py --list-entries
python main.py --entry cyb
python cyb_rag_md.py
```

`showdoc_auth.py` 和 `showdoc_project.py` 已不再作为根目录模块保留；它们的正式实现分别位于 `integrations/showdoc/auth.py` 和 `integrations/showdoc/project.py`。业务代码必须从规范路径导入，不再新增根目录兼容文件。

## 新增文件放置原则

1. 新平台爬虫放到 `crawlers/`，并通过 `registry.py` 注册。
2. 外部平台认证、SDK、项目管理等连接器放到 `integrations/<platform>/`。
3. 可被多个平台复用的内容处理逻辑放到 `common/`，不得复制到平台爬虫。
4. 新测试放到 `tests/`，文件名必须以 `test_` 开头。
5. 新需求或方案文档先判断用途，再放入 `docs/requirements` 或 `docs/architecture`，根目录不新增随意命名的文档。
