"""多平台爬虫抽象基类与规范数据结构。

统一"登录 → 列目录 → 选择 → 取正文 → 清洗 → 按分类落盘"流程；
数据保真约束见 `docs/architecture/multi-platform-crawler-refactor.md` 第 4.3/4.4 节。
"""
import json
import os
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from collections import OrderedDict
from dataclasses import dataclass, field

from common.converter import RAGContentPipeline, clean_filename, write_jsonl, truncate_incomplete_jsonl
from common.quality import assess_documents


class CrawlCancelled(RuntimeError):
    """Cancellation must never be downgraded to a document error."""


@dataclass
class DocumentStub:
    """目录/选择阶段的最小文档单元。"""

    id: str
    title: str
    category: str
    source_url: str = ""


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
    source_path: str = ""
    docling_path: str = ""
    nodes: list = field(default_factory=list)
    chunks: list = field(default_factory=list)
    preview_html: str = ""
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
    video_reference_documents: int = 0


class BaseCrawler:
    """爬取模板基类，子类只需实现平台差异部分。"""

    platform = ""            # 注册键，子类必填
    display_name = ""        # 展示名称
    entry_url = ""           # 人类可读的入口地址
    site_base_url = ""       # 站点根地址，图片/链接绝对化的基准
    requires_auth = True     # 是否需要登录
    source_only = False

    def __init__(self, save_dir, progress_callback=None):
        self.save_dir = save_dir
        self.progress_callback = progress_callback
        self.asset_dir = os.path.join(save_dir, "assets")
        # 合并汇总文档的标题/文件名；按项目爬取的平台可在获取项目名后覆盖。
        self.collection_name = f"{self.display_name}知识库"
        self.pipeline = RAGContentPipeline(
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
        """把 API 的封面、视频等字段映射为 Docling 可解析的源 HTML。"""
        return prepared_html

    def build_finetuning_records(self, documents):
        """仅问答型平台覆写，返回微调 JSONL 记录列表。"""
        return []

    # ---------- 模板方法 ----------

    def crawl(self, selected_ids=None, selected_titles=None, limit=0):
        """执行完整爬取流程并落盘，返回 CrawlSummary。"""
        (Path(self.save_dir) / "collection_complete.json").unlink(missing_ok=True)
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
        self._mark_collection_complete(documents)
        self._convert_all(documents)
        self._notify(len(documents), len(documents), "正在检查来源完整性..." if self.source_only else "正在执行质量检查...")
        quality_report = None if self.source_only else assess_documents(documents)
        self._notify(len(documents), len(documents), "正在保存来源资料..." if self.source_only else "质量检查完成，正在生成数据集...")
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
                raise ValueError(f"有 {len(missing)} 个指定文档 ID 未找到，采集范围不完整: {preview}")
            return selected
        if selected_titles:
            wanted = set(selected_titles)
            selected = [stub for stub in stubs if stub.title in wanted]
            missing = wanted - {stub.title for stub in selected}
            if missing:
                preview = ", ".join(sorted(missing)[:5])
                raise ValueError(f"有 {len(missing)} 个指定文档标题未找到，采集范围不完整: {preview}")
            return selected
        return stubs

    def _fetch_all(self, stubs):
        documents = []
        for index, stub in enumerate(stubs, 1):
            self._notify(index - 1, len(stubs), f"正在抓取: {stub.title}")
            try:
                document = self.fetch_document(stub)
                document.resources = self.supplement_resources(document, document.resources)
            except CrawlCancelled:
                raise
            except Exception as exc:
                document = CrawledDocument(
                    stub.id, stub.title, stub.category, "", "",
                    {"fetch_error": str(exc), "url": stub.source_url}, "html"
                )
            documents.append(document)
            self._journal_source(document)
            for resource in document.resources.get("links", []):
                local = resource["url"]
                if not local.startswith("assets/attachments/"):
                    continue
                path = (Path(self.save_dir) / local).resolve()
                if not path.is_relative_to(Path(self.save_dir).resolve()) or not path.is_file():
                    continue
                child = CrawledDocument(
                    f"{document.id}:attachment:{path.name}", resource.get("text") or path.name,
                    document.category, "", document.updated_at,
                    {"parent_document_id": document.id, "filename": path.name,
                     "url": document.metadata.get("url", self.entry_url)},
                    "file", source_path=local,
                )
                documents.append(child)
                self._journal_source(child)
            self._notify(index, len(stubs), f"已抓取: {stub.title}")
        return documents

    def _source_record(self, doc):
        content = self.assemble_html(doc, doc.content) if self.source_only and doc.source_format == 'html' else doc.content
        if doc.source_path:
            path = (Path(self.save_dir) / doc.source_path).resolve()
            if not path.is_relative_to(Path(self.save_dir).resolve()):
                raise ValueError("源文件不在当前任务目录中")
            source = path.read_bytes()
        else:
            source = content.encode("utf-8")
        return {
            "id": doc.id, "title": doc.title, "category": doc.category,
            "content": content, "source_format": doc.source_format, "source_path": doc.source_path,
            "updated_at": doc.updated_at, "metadata": doc.metadata, "resources": doc.resources,
            "source_sha256": hashlib.sha256(source).hexdigest(),
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }

    def _journal_source(self, doc):
        os.makedirs(self.save_dir, exist_ok=True)
        path = Path(self.save_dir) / "source_documents.jsonl"
        truncate_incomplete_jsonl(path)
        with path.open("a", encoding="utf-8") as out:
            out.write(json.dumps(self._source_record(doc), ensure_ascii=False) + "\n")
            out.flush()
            os.fsync(out.fileno())

    def _mark_collection_complete(self, documents):
        write_jsonl(Path(self.save_dir) / "collection_complete.json", [{
            "document_ids": [doc.id for doc in documents], "completed_at": datetime.now(timezone.utc).isoformat(),
        }])

    def reprocess_sources(self, source_file, *, resume_collection=False, selected_ids=None, selected_titles=None):
        documents = []
        if resume_collection:
            (Path(self.save_dir) / "collection_complete.json").unlink(missing_ok=True)
        truncate_incomplete_jsonl(source_file)
        journal = Path(source_file).read_text(encoding="utf-8")
        lines = journal.splitlines()
        records = {}
        for index, line in enumerate(lines):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError:
                if index == len(lines) - 1 and not journal.endswith("\n"):
                    break
                raise
            records[record["id"]] = record
        for record in records.values():
            documents.append(CrawledDocument(
                id=record["id"], title=record["title"], category=record["category"],
                content=record["content"], updated_at=record["updated_at"], metadata=record["metadata"],
                source_format=record["source_format"], source_path=record.get("source_path", ""),
                resources=record.get("resources", {"images": [], "links": []}),
            ))
        failed = [DocumentStub(doc.id, doc.title, doc.category, doc.metadata.get("url", ""))
                  for doc in documents if doc.metadata.get("fetch_error") or
                  (not doc.source_path and not self._source_record(doc)['content'].strip())]
        if resume_collection or failed:
            self.authenticate()
            stubs = self._filter_selection(self.list_documents(), selected_ids, selected_titles)
        if resume_collection:
            existing = {doc.id for doc in documents}
            failed.extend(stub for stub in stubs if stub.id not in existing)
        if failed:
            replaced = {stub.id for stub in failed}
            documents = [doc for doc in documents if doc.id not in replaced] + self._fetch_all(failed)
        if resume_collection:
            self._mark_collection_complete(documents)
        self._convert_all(documents)
        return self._save(documents)

    def _prepare_record(self, doc):
        base_url = doc.metadata.get("resource_base_url") or doc.metadata.get("url") or self.site_base_url
        source_path = ""
        if doc.source_path:
            path = (Path(self.save_dir) / doc.source_path).resolve()
            if not path.is_relative_to(Path(self.save_dir).resolve()):
                raise ValueError("源文件不在当前任务目录中")
            source_path = str(path)
        content = self.assemble_html(doc, doc.content) if doc.source_format == "html" else doc.content
        return {"id": doc.id, "title": doc.title, "content": content,
                "source_format": doc.source_format, "source_path": source_path, "base_url": base_url}

    def convert_document(self, doc):
        conversion = self.pipeline.convert([self._prepare_record(doc)])[doc.id]
        self._apply_conversion(doc, conversion)
        return doc

    @staticmethod
    def _apply_conversion(doc, conversion):
        doc.markdown = conversion.markdown
        doc.docling_path = conversion.docling_path
        doc.preview_html = conversion.preview_html
        doc.nodes, doc.chunks = conversion.nodes, conversion.chunks
        for kind, resources in conversion.resources.items():
            doc.resources.setdefault(kind, []).extend(item for item in resources if item not in doc.resources.get(kind, []))
        doc.metadata.pop("conversion_error", None)
        doc.metadata["conversion"] = {
            "engine": conversion.engine, "version": conversion.engine_version,
            "fingerprint": conversion.fingerprint, "status": conversion.status,
            "confidence": conversion.confidence,
        }

    def _convert_all(self, documents):
        if self.source_only:
            return
        for index, doc in enumerate(documents, 1):
            self._notify(index - 1, len(documents), f"正在清洗: {doc.title}")
            try:
                if not doc.metadata.get("fetch_error"):
                    self.convert_document(doc)
            except CrawlCancelled:
                raise
            except Exception as exc:
                doc.metadata["conversion_error"] = f"{type(exc).__name__}: {exc}"
            self._notify(index, len(documents), f"已清洗: {doc.title}")

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

    def _save_sources(self, documents):
        """Preserve crawler output; parsing and chunking belong to ContextDB."""
        records, failed = [], []
        for doc in documents:
            record = self._source_record(doc)
            if doc.metadata.get('fetch_error') or (not record['content'].strip() and not doc.source_path):
                failed.append({**record, 'error': doc.metadata.get('fetch_error') or '源正文为空'})
            else:
                records.append(record)
        root = Path(self.save_dir)
        root.mkdir(parents=True, exist_ok=True)
        write_jsonl(root / 'source_documents.jsonl', [*records, *failed])
        write_jsonl(root / 'rag_documents.jsonl', records)
        write_jsonl(root / 'rag_chunks.jsonl', [])
        write_jsonl(root / 'failed_documents.jsonl', failed)
        video_references = sum(record['metadata'].get('source_kind') == 'video_reference' for record in records)
        return CrawlSummary(platform=self.platform, total_documents=len(records), empty_documents=len(failed),
            category_count=len({doc.category for doc in documents}), output_dir=str(root),
            rag_documents_file=str(root / 'rag_documents.jsonl'), rag_chunks_file=str(root / 'rag_chunks.jsonl'),
            failed_documents=len(failed), error_count=len(failed),
            video_reference_documents=video_references, warning_count=video_references,
            failed_documents_file=str(root / 'failed_documents.jsonl'),
            source_documents_file=str(root / 'source_documents.jsonl'))

    def _save(self, documents, quality_report=None):
        if self.source_only:
            return self._save_sources(documents)
        os.makedirs(self.save_dir, exist_ok=True)
        all_documents = list(documents)
        source_documents_file = os.path.join(self.save_dir, "source_documents.jsonl")
        sources = {}
        if os.path.exists(source_documents_file):
            truncate_incomplete_jsonl(source_documents_file)
            with open(source_documents_file, encoding="utf-8") as stream:
                for line in stream:
                    record = json.loads(line)
                    sources[record["id"]] = record
        for doc in all_documents:
            sources[doc.id] = self._source_record(doc)
        write_jsonl(source_documents_file, sources.values())
        valid = [doc for doc in all_documents if doc.docling_path
                 and not doc.metadata.get("conversion_error") and not doc.metadata.get("fetch_error")]
        quality_report = assess_documents(all_documents)
        failed_documents = len(all_documents) - len(valid)
        valid_ids = {id(doc) for doc in valid}
        failed_documents_file = os.path.join(self.save_dir, "failed_documents.jsonl")
        write_jsonl(
            failed_documents_file,
            (
                {
                    **self._source_record(doc),
                    "phase": "fetch" if doc.metadata.get("fetch_error") else "conversion",
                    "error": doc.metadata.get("fetch_error") or doc.metadata.get("conversion_error"),
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
                with open(file_path, "w", encoding="utf-8") as output_file:
                    output_file.write("\n".join(header) + "\n" + body)

                rag_documents.append({
                    "id": doc.id,
                    "type": self.platform,
                    "title": doc.title,
                    "category": doc.category,
                    "updated_at": doc.updated_at,
                    "content": doc.markdown,
                    "docling_path": doc.docling_path,
                    "nodes": doc.nodes,
                    "preview_html": doc.preview_html,
                    "source_path": doc.source_path,
                    "resources": doc.resources,
                    "source": {
                        "entry_url": document_source,
                        "record_id": doc.id,
                    },
                    "metadata": doc.metadata,
                    "content_format": "markdown",
                })

        # Chunks come from the same Docling document used for the preview.
        rag_chunks = []
        for doc in documents:
            for index, chunk in enumerate(doc.chunks, 1):
                rag_chunks.append({
                    "id": f"{doc.id}-chunk-{index:04d}", "document_id": doc.id,
                    "content": chunk["content"],
                    "metadata": {**chunk["metadata"], "type": self.platform, "title": doc.title,
                                 "category": doc.category, "source": doc.metadata.get("url", self.entry_url),
                                 "source_sha256": sources[doc.id]["source_sha256"], "updated_at": doc.updated_at,
                                 "conversion": doc.metadata.get("conversion", {})},
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
                merged_lines.append(doc.markdown)
        merged_file = os.path.join(
            self.save_dir, f"{clean_filename(self.collection_name)}.md"
        )
        with open(merged_file, "w", encoding="utf-8") as output_file:
            output_file.write(
                "\n\n".join(merged_lines) + "\n"
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
