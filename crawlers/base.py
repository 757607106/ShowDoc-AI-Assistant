"""多平台爬虫抽象基类与规范数据结构。

统一"登录 → 列目录 → 选择 → 取正文 → 清洗 → 按分类落盘"流程；
数据保真约束见《多平台爬虫重构方案.md》第 4.3/4.4 节。
"""
import os
import re
from collections import OrderedDict
from dataclasses import dataclass, field

from common.converter import (
    RAGContentPipeline,
    clean_filename,
    clean_markdown_for_rag,
    extract_html_resources,
    prepare_html_content,
    split_markdown_for_rag,
    write_jsonl,
)


@dataclass
class DocumentStub:
    """目录/选择阶段的最小文档单元。"""

    id: str
    title: str
    category: str


@dataclass
class CrawledDocument:
    """抓取完成的规范结构；metadata 全量保留平台原始字段，不清洗、不删减。"""

    id: str
    title: str
    category: str
    html: str
    updated_at: str
    metadata: dict
    markdown: str = ""
    resources: dict = field(
        default_factory=lambda: {"images": [], "links": []}
    )


@dataclass
class CrawlSummary:
    platform: str
    total_documents: int
    empty_documents: int
    category_count: int
    output_dir: str
    merged_file: str = ""
    rag_documents_file: str = ""
    rag_chunks_file: str = ""
    finetuning_file: str = ""


class BaseCrawler:
    """爬取模板基类，子类只需实现平台差异部分。"""

    platform = ""            # 注册键，子类必填
    display_name = ""        # 展示名称
    entry_url = ""           # 人类可读的入口地址
    site_base_url = ""       # 站点根地址，图片/链接绝对化的基准
    requires_auth = True     # 是否需要登录

    def __init__(self, save_dir, progress_callback=None, pipeline_mode=None):
        self.save_dir = save_dir
        self.progress_callback = progress_callback
        self.asset_dir = os.path.join(save_dir, "assets")
        # 合并汇总文档的标题/文件名；按项目爬取的平台可在获取项目名后覆盖。
        self.collection_name = f"{self.display_name}知识库"
        self.pipeline = RAGContentPipeline(
            mode=pipeline_mode,
            asset_dir=self.asset_dir,
            site_base_url=self.site_base_url,
        )

    # ---------- 子类接口 ----------

    def authenticate(self):
        """需要登录的平台覆写；免登录平台保持默认空实现。"""

    def list_documents(self):
        """返回全部文档的 DocumentStub 列表。"""
        raise NotImplementedError

    def fetch_document(self, stub):
        """返回 stub 对应的 CrawledDocument（原始 HTML + 全量 metadata）。"""
        raise NotImplementedError

    def supplement_resources(self, doc, resources):
        """把 HTML 之外的资源（如附件）并入 resources；默认原样返回。"""
        return resources

    def assemble_html(self, doc, prepared_html):
        """标题去重后的内容拼接钩子（如封面图、视频链接）；默认原样返回。

        拼接发生在 prepare_html_content 之后，因此不会破坏首部 H1 与
        文档标题的去重逻辑。
        """
        return prepared_html

    def build_finetuning_records(self, documents):
        """仅问答型平台覆写，返回微调 JSONL 记录列表。"""
        return []

    # ---------- 模板方法 ----------

    def crawl(self, selected_ids=None, selected_titles=None, limit=0):
        """执行完整爬取流程并落盘，返回 CrawlSummary。"""
        self._notify(
            0, 0, "正在登录..." if self.requires_auth else "免登录平台，跳过登录"
        )
        self.authenticate()

        stubs = self.list_documents()
        if limit and limit > 0:
            stubs = stubs[:limit]
            print(f"🔢 试跑模式：仅处理前 {limit} 条")
        stubs = self._filter_selection(stubs, selected_ids, selected_titles)

        documents = self._fetch_all(stubs)
        self._convert_all(documents)
        return self._save(documents)

    # ---------- 内部实现 ----------

    def _notify(self, current, total, message):
        if self.progress_callback:
            self.progress_callback(current, total, message)

    @staticmethod
    def _filter_selection(stubs, selected_ids, selected_titles):
        if selected_ids:
            wanted = {str(item) for item in selected_ids}
            selected = [stub for stub in stubs if stub.id in wanted]
            missing = wanted - {stub.id for stub in selected}
            if missing:
                preview = ", ".join(sorted(missing)[:5])
                print(f"⚠️ 有 {len(missing)} 个指定 id 未匹配到文档: {preview}")
            return selected
        if selected_titles:
            wanted = set(selected_titles)
            selected = [stub for stub in stubs if stub.title in wanted]
            missing = wanted - {stub.title for stub in selected}
            if missing:
                preview = ", ".join(sorted(missing)[:5])
                print(f"⚠️ 有 {len(missing)} 个指定标题未匹配到文档: {preview}")
            return selected
        return stubs

    def _fetch_all(self, stubs):
        documents = []
        for index, stub in enumerate(stubs, 1):
            self._notify(index, len(stubs), f"正在抓取: {stub.title}")
            documents.append(self.fetch_document(stub))
        return documents

    def _convert_all(self, documents):
        records = []
        for doc in documents:
            prepared = prepare_html_content(
                doc.html,
                doc.title,
                asset_dir=self.asset_dir,
                document_id=doc.id,
            )
            prepared = self.assemble_html(doc, prepared)
            resources = extract_html_resources(
                prepared, site_base_url=self.site_base_url
            )
            doc.resources = self.supplement_resources(doc, resources)
            if prepared:
                records.append({
                    "id": doc.id,
                    "title": doc.title,
                    "html": prepared,
                    "resources": doc.resources,
                })

        if not records:
            print("⚠️ 没有可清洗的正文内容")
            return

        print(f"\n🧹 开始内容清洗，处理引擎: {self._engine_name()}")
        converted = self.pipeline.convert(records)
        for doc in documents:
            doc.markdown = converted.get(doc.id, "")

    def _engine_name(self):
        if self.pipeline.use_firecrawl:
            return "Crawl4AI + Firecrawl"
        if self.pipeline.mode == "builtin":
            return "内置 HTML 转换器"
        return "Crawl4AI"

    def _unique_filename(self, category, filename, document_id, used):
        """同分类同名文档追加 id 前缀，避免静默覆盖丢数据。"""
        key = (category, filename)
        if key not in used:
            used[key] = True
            return filename

        stem, ext = os.path.splitext(filename)
        suffix = clean_filename(str(document_id))[:8]
        candidate = f"{stem}_{suffix}{ext}"
        counter = 2
        while (category, candidate) in used:
            candidate = f"{stem}_{suffix}_{counter}{ext}"
            counter += 1
        used[(category, candidate)] = True
        print(f"⚠️ 同名文档重命名: {filename} -> {candidate}")
        return candidate

    @staticmethod
    def _demote_headings(markdown, offset=3):
        """下调正文标题层级，保证合并文档中正文位于文档标题（###）之下。"""
        if not markdown:
            return markdown
        result = []
        in_code_block = False
        for line in markdown.split("\n"):
            stripped = line.lstrip()
            if stripped.startswith(("```", "~~~")):
                in_code_block = not in_code_block
                result.append(line)
                continue
            if not in_code_block:
                heading = re.match(r'^(#{1,6})(\s+.*)$', line)
                if heading:
                    level = min(6, len(heading.group(1)) + offset)
                    result.append("#" * level + heading.group(2))
                    continue
            result.append(line)
        return "\n".join(result)

    def _save(self, documents):
        os.makedirs(self.save_dir, exist_ok=True)
        docs_by_category = OrderedDict()
        for doc in documents:
            docs_by_category.setdefault(doc.category, []).append(doc)

        used_filenames = {}
        empty_count = 0
        rag_documents = []

        # 1. 按分类落盘单文件
        for category, cat_docs in docs_by_category.items():
            category_dir = os.path.join(self.save_dir, clean_filename(category))
            os.makedirs(category_dir, exist_ok=True)
            for doc in cat_docs:
                base_name = clean_filename(doc.title) + ".md"
                filename = self._unique_filename(
                    category, base_name, doc.id, used_filenames
                )
                file_path = os.path.join(category_dir, filename)
                document_source = (
                    doc.metadata.get("url")
                    if isinstance(doc.metadata, dict)
                    else None
                ) or self.entry_url

                header = [
                    f"# {doc.title}\n",
                    f"- **分类**: {doc.category}",
                    f"- **更新时间**: {doc.updated_at}",
                    f"- **来源**: {document_source}",
                    "---\n",
                ]
                body = doc.markdown
                if not body:
                    empty_count += 1
                    body = "*暂无内容*\n"
                body = body.replace("](assets/", "](../assets/")
                with open(file_path, "w", encoding="utf-8") as output_file:
                    output_file.write("\n".join(header) + "\n" + body)

                rag_documents.append({
                    "id": doc.id,
                    "type": self.platform,
                    "title": doc.title,
                    "category": doc.category,
                    "updated_at": doc.updated_at,
                    "content": doc.markdown,
                    "resources": doc.resources,
                    "source": {
                        "entry_url": document_source,
                        "record_id": doc.id,
                    },
                    "metadata": doc.metadata,
                })

        # 2. RAG 分块
        chunk_size = int(os.getenv("RAG_CHUNK_SIZE", "1600"))
        chunk_overlap = int(os.getenv("RAG_CHUNK_OVERLAP", "180"))
        rag_chunks = []
        for record in rag_documents:
            if not record["content"]:
                continue
            chunk_metadata = {
                "type": record["type"],
                "title": record["title"],
                "category": record["category"],
                "updated_at": record["updated_at"],
                "source": record["source"],
                "resources": record["resources"],
            }
            for index, chunk in enumerate(
                split_markdown_for_rag(
                    record["content"],
                    max_chars=chunk_size,
                    overlap=chunk_overlap,
                ),
                1,
            ):
                rag_chunks.append({
                    "id": f"{record['id']}-chunk-{index:04d}",
                    "document_id": record["id"],
                    "content": f"# {record['title']}\n\n{chunk}",
                    "metadata": chunk_metadata,
                })

        # 3. 合并汇总文档：# 合集 / ## 分类 / ### 文档
        merged_lines = [f"# {self.collection_name}"]
        for category, cat_docs in docs_by_category.items():
            merged_lines.append(f"## {category}")
            for doc in cat_docs:
                merged_lines.append(f"### {doc.title}")
                merged_lines.append(f"**更新时间：** {doc.updated_at}")
                merged_lines.append(
                    self._demote_headings(doc.markdown)
                    if doc.markdown else "*暂无内容*"
                )
        merged_file = os.path.join(
            self.save_dir, f"{clean_filename(self.collection_name)}.md"
        )
        with open(merged_file, "w", encoding="utf-8") as output_file:
            output_file.write(
                clean_markdown_for_rag("\n\n".join(merged_lines)) + "\n"
            )

        # 4. 结构化输出
        rag_documents_file = os.path.join(self.save_dir, "rag_documents.jsonl")
        rag_chunks_file = os.path.join(self.save_dir, "rag_chunks.jsonl")
        write_jsonl(rag_documents_file, rag_documents)
        write_jsonl(rag_chunks_file, rag_chunks)

        summary = CrawlSummary(
            platform=self.platform,
            total_documents=len(documents),
            empty_documents=empty_count,
            category_count=len(docs_by_category),
            output_dir=self.save_dir,
            merged_file=merged_file,
            rag_documents_file=rag_documents_file,
            rag_chunks_file=rag_chunks_file,
        )

        # 5. 问答型平台的微调数据
        finetuning_records = self.build_finetuning_records(documents)
        if finetuning_records:
            finetuning_file = os.path.join(
                self.save_dir, f"finetuning_{self.platform}.jsonl"
            )
            write_jsonl(finetuning_file, finetuning_records)
            summary.finetuning_file = finetuning_file

        return summary
