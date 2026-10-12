"""多平台爬虫抽象基类与规范数据结构。

统一"登录 → 列目录 → 选择 → 取正文 → 清洗 → 按分类落盘"流程；
数据保真约束见 `docs/architecture/multi-platform-crawler-refactor.md` 第 4.3/4.4 节。
"""
import json
import os
import hashlib
from datetime import datetime, timezone
from collections import OrderedDict
from dataclasses import dataclass, field

from common.converter import (
    RAGContentPipeline,
    clean_filename,
    clean_markdown_for_rag,
    extract_html_resources,
    extract_markdown_resources,
    normalize_document_markdown,
    normalize_resource_url,
    prepare_html_content,
    prepare_markdown_content,
    split_markdown_sections_for_rag,
    validate_canonical_markdown,
    write_jsonl,
)
from common.quality import assess_documents


class CrawlCancelled(RuntimeError):
    """Cancellation must never be downgraded to a document error."""


@dataclass
class DocumentStub:
    """目录/选择阶段的最小文档单元。"""

    id: str
    title: str
    category: str


@dataclass
class CrawledDocument:
    """抓取完成的规范结构；source_format 明确源正文语法，禁止猜测。"""

    id: str
    title: str
    category: str
    content: str
    updated_at: str
    metadata: dict
    source_format: str
    markdown: str = ""
    raw_markdown: str = ""
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
    raw_documents_file: str = ""
    rag_documents_file: str = ""
    rag_chunks_file: str = ""
    finetuning_file: str = ""
    quality_report_file: str = ""
    failed_documents_file: str = ""
    quality_score: float = 0.0
    chunk_count: int = 0
    duplicate_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    discovery_strategy: str = ""
    coverage_score: float | None = None
    coverage_report_file: str = ""
    failed_documents: int = 0
    source_documents_file: str = ""


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
        """返回 stub 对应的 CrawledDocument（原文 + 明确格式 + 全量 metadata）。"""
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
        stubs = self._filter_selection(stubs, selected_ids, selected_titles)
        if limit and limit > 0:
            stubs = stubs[:limit]
            print(f"🔢 试跑模式：仅处理前 {limit} 条")

        documents = self._fetch_all(stubs)
        self._convert_all(documents)
        self._notify(len(documents), len(documents), "正在执行质量检查...")
        quality_report = assess_documents(documents)
        self._notify(len(documents), len(documents), "质量检查完成，正在生成数据集...")
        summary = self._save(documents, quality_report)
        self._notify(len(documents), len(documents), "数据集文件生成完成")
        return summary

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
            self._notify(index - 1, len(stubs), f"正在抓取: {stub.title}")
            try:
                document = self.fetch_document(stub)
            except CrawlCancelled:
                raise
            except Exception as exc:
                document = CrawledDocument(
                    stub.id, stub.title, stub.category, "", "", {"fetch_error": str(exc)}, "html"
                )
            documents.append(document)
            self._journal_source(document)
            self._notify(index, len(stubs), f"已抓取: {stub.title}")
        return documents

    def _source_record(self, doc):
        return {
            "id": doc.id, "title": doc.title, "category": doc.category,
            "content": doc.content, "source_format": doc.source_format,
            "updated_at": doc.updated_at, "metadata": doc.metadata,
            "source_sha256": hashlib.sha256(doc.content.encode("utf-8")).hexdigest(),
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }

    def _journal_source(self, doc):
        # Durable raw evidence survives conversion errors and task cancellation.
        os.makedirs(self.save_dir, exist_ok=True)
        with open(os.path.join(self.save_dir, "source_documents.jsonl"), "a", encoding="utf-8") as out:
            out.write(json.dumps(self._source_record(doc), ensure_ascii=False) + "\n")

    def _prepare_record(self, doc, include_attachments=True):
        base_url = doc.metadata.get("resource_base_url") or doc.metadata.get("url") or self.site_base_url
        if doc.source_format == "markdown":
            prepared = prepare_markdown_content(doc.content, doc.title)
            resources = extract_markdown_resources(prepared, site_base_url=base_url)
        elif doc.source_format == "html":
            prepared = prepare_html_content(doc.content, doc.title, asset_dir=self.asset_dir, document_id=doc.id)
            prepared = self.assemble_html(doc, prepared)
            resources = extract_html_resources(prepared, site_base_url=base_url)
        else:
            raise ValueError(f"文档 {doc.id} 的 source_format 无效: {doc.source_format}")
        resources = self.supplement_resources(doc, resources) if include_attachments else resources
        doc.resources = {kind: [{**item, "url": normalize_resource_url(item["url"], base_url)} for item in items]
                         for kind, items in resources.items()}
        return {"id": doc.id, "title": doc.title, "content": prepared,
                "source_format": doc.source_format, "resources": doc.resources, "base_url": base_url}

    def convert_document(self, doc, include_attachments=True):
        conversion = self.pipeline.convert([self._prepare_record(doc, include_attachments)])[doc.id]
        self._apply_conversion(doc, conversion)
        return doc

    @staticmethod
    def _apply_conversion(doc, conversion):
        doc.raw_markdown, doc.markdown = conversion.raw_markdown, conversion.markdown
        doc.metadata["conversion"] = {
            "engine": conversion.engine, "version": conversion.engine_version,
            "fallback_reason": conversion.fallback_reason,
        }

    def _convert_all(self, documents):
        records, errors = [], {}
        for doc in documents:
            self._notify(0, len(documents), f"正在准备清洗: {doc.title}")
            try:
                records.append(self._prepare_record(doc))
            except CrawlCancelled:
                raise
            except Exception as exc:
                errors[doc.id] = str(exc)
        converted = self.pipeline.convert(records, errors=errors, progress_callback=self._notify)
        for doc in documents:
            if doc.id in converted:
                self._apply_conversion(doc, converted[doc.id])
            else:
                doc.metadata["conversion_error"] = errors.get(doc.id, "正文为空")
        self._notify(len(records), len(records), "内容清洗完成")

    def _engine_name(self):
        if self.pipeline.mode == "builtin":
            return "内置 HTML 转换器"
        return "Crawl4AI"

    def _unique_filename(self, category, filename, document_id, used):
        """同分类同名文档追加 id 前缀，避免静默覆盖丢数据。"""
        key = (clean_filename(category).casefold(), filename.casefold())
        if key not in used:
            used[key] = True
            return filename

        stem, ext = os.path.splitext(filename)
        suffix = clean_filename(str(document_id))[:8]
        candidate = f"{stem}_{suffix}{ext}"
        counter = 2
        while (key[0], candidate.casefold()) in used:
            candidate = f"{stem}_{suffix}_{counter}{ext}"
            counter += 1
        used[(key[0], candidate.casefold())] = True
        print(f"⚠️ 同名文档重命名: {filename} -> {candidate}")
        return candidate

    def _save(self, documents, quality_report=None):
        os.makedirs(self.save_dir, exist_ok=True)
        all_documents = list(documents)
        source_documents_file = os.path.join(self.save_dir, "source_documents.jsonl")
        sources = {}
        if os.path.exists(source_documents_file):
            with open(source_documents_file, encoding="utf-8") as stream:
                for line in stream:
                    try:
                        record = json.loads(line)
                    except ValueError:
                        continue  # An interrupted final journal write is recoverable.
                    sources[record["id"]] = record
        for doc in all_documents:
            sources[doc.id] = self._source_record(doc)
        write_jsonl(source_documents_file, sources.values())
        valid = []
        for doc in all_documents:
            try:
                validate_canonical_markdown(doc.markdown, doc.resources, title=doc.title)
                valid.append(doc)
            except ValueError as exc:
                doc.metadata["conversion_error"] = str(exc)
        quality_report = assess_documents(all_documents)
        failed_documents = len(all_documents) - len(valid)
        valid_ids = {id(doc) for doc in valid}
        failed_documents_file = os.path.join(self.save_dir, "failed_documents.jsonl")
        write_jsonl(
            failed_documents_file,
            (
                {
                    **self._source_record(doc),
                    "phase": "conversion",
                    "error": doc.metadata.get("conversion_error"),
                }
                for doc in all_documents
                if id(doc) not in valid_ids
            ),
        )
        documents = valid
        docs_by_category = OrderedDict()
        for doc in documents:
            docs_by_category.setdefault(doc.category, []).append(doc)

        used_filenames = {}
        # The report is based on all captured documents, including failed
        # ones.  Previously this counter was incremented only while writing
        # valid documents, so it was always zero for the exact records that
        # had been rejected as empty.
        empty_count = quality_report["summary"].get("empty_documents", 0)
        raw_documents = []
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
                    body = "*暂无内容*\n"
                body = body.replace("](assets/", "](../assets/").replace("](<assets/", "](<../assets/")
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
                    "content_format": "markdown",
                })
                raw_documents.append({
                    "id": doc.id,
                    "type": self.platform,
                    "title": doc.title,
                    "category": doc.category,
                    "content": doc.raw_markdown or doc.markdown,
                    "source_format": doc.source_format,
                    "conversion": doc.metadata.get("conversion", {}),
                    "source": {
                        "entry_url": document_source,
                        "record_id": doc.id,
                    },
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
                split_markdown_sections_for_rag(
                    record["content"],
                    max_chars=max(32, chunk_size - len(record["title"]) - 4),
                    overlap=min(chunk_overlap, max(0, chunk_size - len(record["title"]) - 5)),
                ),
                1,
            ):
                rag_chunks.append({
                    "id": f"{record['id']}-chunk-{index:04d}",
                    "document_id": record["id"],
                    "content": f"# {record['title']}\n\n{chunk.content}",
                    "metadata": {
                        **chunk_metadata,
                        "oversized": len(f"# {record['title']}\n\n{chunk.content}") > chunk_size,
                        "size_unit": "characters",
                        "section_path": list(chunk.section_path),
                        "chunk_index": index,
                    },
                })

        quality_report = quality_report or assess_documents(documents)
        quality_report["summary"]["chunks"] = len(rag_chunks)
        quality_report_file = os.path.join(self.save_dir, "quality_report.json")
        with open(quality_report_file, "w", encoding="utf-8") as report_file:
            json.dump(quality_report, report_file, ensure_ascii=False, indent=2)

        # 3. 合并汇总文档：# 合集 / ## 分类 / ### 文档
        merged_lines = [f"# {self.collection_name}"]
        for category, cat_docs in docs_by_category.items():
            merged_lines.append(f"## {category}")
            for doc in cat_docs:
                merged_lines.append(f"### {doc.title}")
                merged_lines.append(f"**更新时间：** {doc.updated_at}")
                merged_lines.append(
                    normalize_document_markdown(
                        doc.markdown,
                        title=doc.title,
                        base_heading_level=4,
                    )
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
        raw_documents_file = os.path.join(self.save_dir, "raw_documents.jsonl")
        rag_documents_file = os.path.join(self.save_dir, "rag_documents.jsonl")
        rag_chunks_file = os.path.join(self.save_dir, "rag_chunks.jsonl")
        write_jsonl(raw_documents_file, raw_documents)
        write_jsonl(rag_documents_file, rag_documents)
        write_jsonl(rag_chunks_file, rag_chunks)

        summary = CrawlSummary(
            platform=self.platform,
            total_documents=len(documents),
            empty_documents=empty_count,
            category_count=len(docs_by_category),
            output_dir=self.save_dir,
            merged_file=merged_file,
            raw_documents_file=raw_documents_file,
            rag_documents_file=rag_documents_file,
            rag_chunks_file=rag_chunks_file,
            quality_report_file=quality_report_file,
            failed_documents_file=failed_documents_file,
            quality_score=quality_report["summary"]["quality_score"],
            chunk_count=len(rag_chunks),
            duplicate_count=quality_report["summary"]["duplicate_documents"],
            # UI counters represent affected documents.  The report also
            # keeps issue_counts for occurrence-level diagnostics and exposes
            # issue_document_counts when the two need to be compared.
            error_count=quality_report["summary"]["error_documents"],
            warning_count=quality_report["summary"]["warning_documents"],
            failed_documents=failed_documents,
            source_documents_file=source_documents_file,
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
