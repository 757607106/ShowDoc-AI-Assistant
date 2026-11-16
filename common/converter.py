"""Docling is the only document parser, serializer and chunker used by the app."""
import hashlib
import json
import mimetypes
import os
import re
import tempfile
from dataclasses import dataclass, field
from importlib.metadata import version
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
CYB_API_BASE_URL = os.getenv("CYB_API_BASE_URL", "https://new.yuncyb.com/aicyberp-api").rstrip("/")
PIPELINE_REVISION = "docling-governance-2"


def clean_filename(filename):
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', str(filename)).strip(' .')
    return value[:160] or 'untitled'


def write_jsonl(path, records):
    """Replace only after every record was serialized successfully."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as out:
            temporary = out.name
            for record in records:
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def truncate_incomplete_jsonl(path):
    """Only an interrupted final append may be discarded; complete records remain strict."""
    path = Path(path)
    if not path.exists() or not path.stat().st_size:
        return
    with path.open('r+b') as stream:
        stream.seek(-1, os.SEEK_END)
        if stream.read(1) != b'\n':
            stream.seek(0)
            data = stream.read()
            stream.truncate(data.rfind(b'\n') + 1)


def prepare_review_file(client, kb_id, name, path, *, base_url='', pipeline=None, review_enabled=None):
    """Keep originals intact; normalize HTML only when the official review gate is enabled."""
    from governance.store import StoreError
    path = Path(path)
    if review_enabled is None:
        review_enabled = client.get_knowledge_base(kb_id).get('review_enabled')
    if not review_enabled:
        return name, path, ''
    suffix = Path(name).suffix.lower()
    if not path.stat().st_size or (suffix in ('.txt', '.md', '.markdown') and not path.read_bytes().strip()):
        raise StoreError(f'源正文为空: {name}', 422)
    if suffix == '.markdown':
        return str(Path(name).with_suffix('.md')), path, ''
    if suffix in ('.txt', '.md', '.pdf', '.doc', '.docx'):
        return name, path, ''
    if suffix not in ('.html', '.htm'):
        raise StoreError(f'知识评审不支持 {suffix or "未知格式"}，请提供 TXT、Markdown、PDF、DOC 或 DOCX', 422)
    pipeline = pipeline or RAGContentPipeline(path.parent / 'assets')
    try:
        result = pipeline.convert_record({'id': name, 'title': name, 'source_format': 'html',
            'content': path.read_text(encoding='utf-8-sig'), 'base_url': base_url}, chunk=False)
    except ValueError as exc:
        raise StoreError(f'HTML 无法生成可评审正文: {exc}', 422) from exc
    if not result.markdown.strip() or not result.nodes:
        raise StoreError(f'HTML 未提取到可评审正文: {name}', 422)
    converted = path.with_name(path.name + '.review.md')
    converted.write_text(result.markdown, encoding='utf-8')
    fingerprint = hashlib.sha256(json.dumps({'pipeline': result.fingerprint, 'base_url': base_url},
        sort_keys=True).encode()).hexdigest()
    return str(Path(name).with_suffix('.md')), converted, fingerprint


@dataclass
class DocumentConversion:
    markdown: str
    preview_html: str
    docling_path: str
    nodes: list
    chunks: list
    resources: dict
    fingerprint: str
    status: str
    confidence: dict = field(default_factory=dict)
    engine: str = "docling"
    engine_version: str = ""


def _backend_classes():
    from docling.backend.html_backend import HTMLDocumentBackend
    from docling.backend.md_backend import MarkdownDocumentBackend
    from docling_core.types.doc import ImageRef, Size
    from pydantic import AnyUrl

    def image_reference(uri):
        # Preserve references without making additional network requests during parsing.
        if urlsplit(str(uri)).scheme in {"http", "https"}:
            return ImageRef(uri=AnyUrl(str(uri)), mimetype=mimetypes.guess_type(urlsplit(str(uri)).path)[0] or "application/octet-stream", dpi=72, size=Size())
        return None

    class SourceHTMLBackend(HTMLDocumentBackend):
        def _create_image_ref(self, src_url):
            return image_reference(src_url) or super()._create_image_ref(src_url)

    class SourceMarkdownBackend(MarkdownDocumentBackend):
        # Docling 2.150.0 applies these repairs even inside fenced code.
        def _shorten_underscore_sequences(self, markdown_text, max_length=10):
            return markdown_text

        def _shorten_leading_dash_sequences(self, markdown_text, max_length=10):
            return markdown_text

        def _iterate_elements(self, **kwargs):
            import marko
            from docling.utils.code_language import detect_code_language
            element = kwargs["element"]
            if isinstance(element, (marko.block.CodeBlock, marko.block.FencedCode)):
                if element in kwargs["visited"]:
                    return
                kwargs["visited"].add(element)
                # The upstream rstrip removes significant spaces from code literals.
                text = element.children[0].children.removesuffix("\n") if element.children else ""
                kwargs["doc"].add_code(parent=kwargs.get("parent_item"), text=text,
                    code_language=detect_code_language(text, hint=getattr(element, "lang", "")),
                    formatting=kwargs.get("formatting"), hyperlink=kwargs.get("hyperlink"))
                return
            return super()._iterate_elements(**kwargs)

        def _load_image_ref(self, dest):
            uri = urljoin(str(self.options.source_uri or ""), dest)
            return image_reference(uri) or super()._load_image_ref(dest)

    return SourceHTMLBackend, SourceMarkdownBackend


class RAGContentPipeline:
    def __init__(self, asset_dir, site_base_url=""):
        self.output_dir = Path(asset_dir).parent.resolve()
        self.site_base_url = site_base_url
        self.max_tokens = int(os.getenv("RAG_CHUNK_TOKENS", "512"))
        if not 64 <= self.max_tokens <= 8192:
            raise ValueError("RAG_CHUNK_TOKENS 必须在 64 到 8192 之间")
        self._converter = None
        self._chunker = None

    @property
    def fingerprint(self):
        settings = {
            "pipeline": PIPELINE_REVISION,
            "docling": version("docling-slim"),
            "core": version("docling-core"),
            "langchain_docling": version("langchain-docling"),
            "tokenizer": "cl100k_base", "max_tokens": self.max_tokens,
        }
        return hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()

    @property
    def markdown_fingerprint(self):
        settings = {"pipeline": PIPELINE_REVISION, "export": "markdown-only",
                    "docling": version("docling-slim"), "core": version("docling-core")}
        return hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()

    def _initialize(self):
        if self._converter is not None:
            return
        from docling.document_converter import DocumentConverter, HTMLFormatOption, MarkdownFormatOption, PdfFormatOption, ImageFormatOption
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.backend_options import HTMLBackendOptions, MarkdownBackendOptions
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        model_root = Path(os.getenv("GOVERNANCE_DATA_DIR", Path(__file__).resolve().parents[1] / "downloads")) / "_models"
        artifacts_path = Path(os.getenv("DOCLING_ARTIFACTS_PATH", model_root / "docling"))

        html_backend, md_backend = _backend_classes()
        pdf_options = PdfPipelineOptions(document_timeout=300, artifacts_path=artifacts_path, generate_picture_images=True)
        self._converter = DocumentConverter(format_options={
            InputFormat.HTML: HTMLFormatOption(backend=html_backend, backend_options=HTMLBackendOptions(
                infer_furniture=False, add_title=False, fetch_images=True)),
            InputFormat.MD: MarkdownFormatOption(backend=md_backend, backend_options=MarkdownBackendOptions(fetch_images=True)),
            InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
            InputFormat.IMAGE: ImageFormatOption(pipeline_options=pdf_options),
        })

    def _initialize_chunker(self):
        if self._chunker is not None:
            return
        from docling.chunking import HybridChunker
        from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer
        import tiktoken
        model_root = Path(os.getenv("GOVERNANCE_DATA_DIR", Path(__file__).resolve().parents[1] / "downloads")) / "_models"
        os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(model_root / "tiktoken"))
        self._chunker = HybridChunker(tokenizer=OpenAITokenizer(
            tokenizer=tiktoken.get_encoding("cl100k_base"), max_tokens=self.max_tokens))

    def convert(self, records, *, errors=None, progress_callback=None):
        converted = {}
        for index, record in enumerate(records, 1):
            if progress_callback:
                progress_callback(index - 1, len(records), f"正在清洗: {record['title']}")
            try:
                converted[record["id"]] = self.convert_record(record)
            except Exception as exc:
                if errors is None:
                    raise
                errors[record["id"]] = f"{type(exc).__name__}: {exc}"
            if progress_callback:
                progress_callback(index, len(records), f"已清洗: {record['title']}")
        return converted

    def convert_record(self, record, *, chunk=True):
        self._initialize()
        from docling.datamodel.base_models import InputFormat, ConversionStatus
        from docling_core.types.doc import DoclingDocument, ImageRefMode, ContentLayer
        from pydantic import AnyUrl

        source_path = record.get("source_path")
        content = record.get("content", "")
        source = Path(source_path).read_bytes() if source_path else content.encode("utf-8")
        if not source.strip():
            raise ValueError("源正文为空")
        fingerprint = self.fingerprint if chunk else self.markdown_fingerprint
        source_url = record.get("base_url") or self.site_base_url
        source_identity = json.dumps({"id": record["id"], "format": record["source_format"],
            "filename": Path(source_path).name if source_path else "", "url": source_url}, sort_keys=True)
        digest = hashlib.sha256(source + fingerprint.encode() + source_identity.encode()).hexdigest()
        artifact = self.output_dir / "docling" / f"{digest}.json"
        result_path = artifact.with_suffix(".result.json")
        artifact.parent.mkdir(parents=True, exist_ok=True)
        if artifact.exists() and result_path.exists():
            doc = DoclingDocument.load_from_json(artifact)
            details = json.loads(result_path.read_text())
        else:
            for fmt in (InputFormat.HTML, InputFormat.MD):
                self._converter.format_to_options[fmt].backend_options.source_uri = source_url or None
            if source_path:
                result = self._converter.convert(Path(source_path))
            else:
                fmt = {"html": InputFormat.HTML, "markdown": InputFormat.MD}.get(record["source_format"])
                if fmt is None:
                    raise ValueError(f"不支持的源格式: {record['source_format']}")
                result = self._converter.convert_string(content, format=fmt, name=f"{record['id']}.{'html' if fmt == InputFormat.HTML else 'md'}")
            if result.status != ConversionStatus.SUCCESS:
                raise ValueError(f"Docling 未完整转换: {result.status.value}; {result.errors}")
            doc = result.document
            for item, _ in doc.iterate_items(traverse_pictures=True):
                link = getattr(item, "hyperlink", None)
                if link and source_url and not urlsplit(str(link)).scheme:
                    item.hyperlink = AnyUrl(urljoin(source_url, str(link)))
            details = {"status": result.status.value, "confidence": json.loads(result.confidence.model_dump_json()), "fingerprint": fingerprint}
            # export_to_dict preserves image references without fetching their bytes.
            temporary = artifact.with_suffix(".json.part")
            temporary.write_text(json.dumps(doc.export_to_dict(), ensure_ascii=False), encoding="utf-8")
            os.replace(temporary, artifact)
            result_path.write_text(json.dumps(details, ensure_ascii=False), encoding="utf-8")
        markdown = doc.export_to_markdown(image_mode=ImageRefMode.REFERENCED, included_content_layers={ContentLayer.BODY})
        nodes, resources = self._nodes_and_resources(doc, source_url)
        if not nodes and not doc.pictures:
            raise ValueError("Docling 未提取到正文或图片")
        chunks = []
        if chunk:
            from langchain_docling import DoclingLoader
            from langchain_docling.loader import ExportType
            self._initialize_chunker()
            documents = DoclingLoader(file_path=str(artifact), export_type=ExportType.DOC_CHUNKS, chunker=self._chunker).load()
            for index, document in enumerate(documents, 1):
                meta = document.metadata.get("dl_meta", {})
                chunks.append({"content": document.page_content, "metadata": {
                    "dl_meta": meta, "section_path": meta.get("headings", []), "chunk_index": index,
                    "node_refs": [item["self_ref"] for item in meta.get("doc_items", [])],
                    "size_unit": "tokens", "token_count": self._chunker.tokenizer.count_tokens(document.page_content),
                }})
        return DocumentConversion(
            markdown=markdown, preview_html=doc.export_to_html(image_mode=ImageRefMode.REFERENCED,
                                                              included_content_layers={ContentLayer.BODY}),
            docling_path=str(artifact.relative_to(self.output_dir)), nodes=nodes, chunks=chunks,
            resources=resources, fingerprint=fingerprint, status=details["status"],
            confidence=details["confidence"], engine_version=version("docling-slim"),
        )

    @staticmethod
    def _nodes_and_resources(doc, source_url):
        from docling_core.types.doc import TableItem, ContentLayer
        nodes, headings = [], {}
        resources = {"images": [], "links": []}
        for item, _ in doc.iterate_items(traverse_pictures=True, included_content_layers={ContentLayer.BODY}):
            text = getattr(item, "text", "")
            if isinstance(item, TableItem):
                text = item.export_to_markdown(doc=doc)
            label = item.label.value
            if label in {"section_header", "title"}:
                level = 0 if label == "title" else getattr(item, "level", 1)
                headings = {key: value for key, value in headings.items() if key < level}
                headings[level] = text
            prov = item.prov[0] if item.prov else None
            if text:
                nodes.append({"ref": item.self_ref, "text": text, "headings": list(headings.values()),
                              "label": label, "page_no": prov.page_no if prov else None,
                              "bbox": prov.bbox.model_dump(mode="json") if prov else None})
            link = getattr(item, "hyperlink", None)
            if link:
                resources["links"].append({"text": text, "url": urljoin(source_url, str(link))})
            image = getattr(item, "image", None)
            if image:
                resources["images"].append({"text": text, "url": str(image.uri)})
        return nodes, resources
