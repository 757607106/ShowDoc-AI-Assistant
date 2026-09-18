"""通用内容清洗管道：HTML → Markdown 转换、资源提取/回补、RAG 分块。

从 cyb_rag_md.py 拆出（第 3 阶段），供各平台爬虫共用；
站点根地址通过 site_base_url 注入，缺省沿用云创业版配置以保持原行为。
"""
import asyncio
import base64
import hashlib
import json
import os
import re
import urllib.parse
from html import escape
from html.parser import HTMLParser

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

CYB_API_BASE_URL = os.getenv(
    "CYB_API_BASE_URL", "https://new.yuncyb.com/aicyberp-api"
).rstrip("/")


class HTMLToMarkdown(HTMLParser):
    """
    一个轻量级且不依赖第三方库的 HTML 转 Markdown 解析器。
    能够正确提取段落、标题、加粗以及图片，并处理它们之间的排版间距。
    """

    def __init__(self):
        super().__init__()
        self.result = []
        self.list_stack = []
        self.list_index = 1
        self.link_stack = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            # 汇总结构占用 H1~H4，正文原有标题从 H5 开始，避免层级冲突。
            level = int(tag[1]) + 4
            if level > 6:
                level = 6
            self.result.append(f'\n\n{"#" * level} ')
        elif tag == 'p':
            self.result.append('\n\n')
        elif tag == 'br':
            self.result.append('\n')
        elif tag == 'img':
            src = attrs_dict.get('src', '')
            alt = attrs_dict.get('alt', '图片')
            self.result.append(f'\n\n![{alt}]({src})\n\n')
        elif tag in ['strong', 'b']:
            self.result.append(' **')
        elif tag in ['em', 'i']:
            self.result.append(' *')
        elif tag == 'a':
            href = attrs_dict.get('href', '')
            self.result.append('[' if href else '')
            self.link_stack.append(href)
        elif tag == 'ul':
            self.list_stack.append('ul')
            self.result.append('\n')
        elif tag == 'ol':
            self.list_stack.append('ol')
            self.list_index = 1
            self.result.append('\n')
        elif tag == 'li':
            if self.list_stack and self.list_stack[-1] == 'ol':
                self.result.append(f'\n{self.list_index}. ')
                self.list_index += 1
            else:
                self.result.append('\n- ')

    def handle_endtag(self, tag):
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.result.append('\n\n')
        elif tag == 'p':
            self.result.append('\n\n')
        elif tag in ['strong', 'b']:
            self.result.append('** ')
        elif tag in ['em', 'i']:
            self.result.append('* ')
        elif tag == 'a':
            href = self.link_stack.pop() if self.link_stack else ''
            self.result.append(f']({href})' if href else '')
        elif tag in ['ul', 'ol']:
            if self.list_stack:
                self.list_stack.pop()
            self.result.append('\n')

    def handle_data(self, data):
        self.result.append(data)

    def get_markdown(self):
        content = ''.join(self.result)
        content = re.sub(r'\n{3,}', '\n\n', content)

        lines = [line.rstrip() for line in content.split('\n')]
        formatted_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('![') or stripped.startswith('<!--'):
                if formatted_lines and formatted_lines[-1] != '':
                    formatted_lines.append('')
                formatted_lines.append(line)
                formatted_lines.append('')
            else:
                formatted_lines.append(line)

        final_content = '\n'.join(formatted_lines)
        final_content = re.sub(r'\n{3,}', '\n\n', final_content)
        return final_content.strip()


def clean_filename(filename):
    """
    过滤文件名及锚点链接中的非法字符
    """
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.strip()
    return filename


def _externalize_embedded_image(data_url, asset_dir, document_id):
    """将 Base64/URL 编码的内嵌图片落盘，并返回稳定的 Markdown 资源地址。"""
    if not asset_dir or not data_url.lower().startswith("data:image/"):
        return data_url

    try:
        header, payload = data_url.split(",", 1)
        mime_type = header[5:].split(";", 1)[0].lower()
        if ";base64" in header.lower():
            image_bytes = base64.b64decode(re.sub(r"\s+", "", payload))
        else:
            image_bytes = urllib.parse.unquote_to_bytes(payload)
        if not image_bytes:
            return data_url
    except (ValueError, TypeError, base64.binascii.Error):
        # 无法解码时保留原始 data URI，不能因为清洗而丢图。
        return data_url

    extensions = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/webp": "webp",
        "image/svg+xml": "svg",
        "image/avif": "avif",
        "image/x-icon": "ico",
        "image/vnd.microsoft.icon": "ico",
    }
    extension = extensions.get(mime_type, "img")
    digest = hashlib.sha256(image_bytes).hexdigest()[:16]
    safe_document_id = clean_filename(str(document_id)) or "document"
    filename = f"{safe_document_id}-{digest}.{extension}"
    os.makedirs(asset_dir, exist_ok=True)
    asset_path = os.path.join(asset_dir, filename)
    if not os.path.exists(asset_path):
        with open(asset_path, "wb") as asset_file:
            asset_file.write(image_bytes)

    # 绝对占位地址可避免 Crawl4AI/Firecrawl 将本地相对路径改成站点 URL。
    return f"https://rag.local/assets/{urllib.parse.quote(filename)}"


def prepare_html_content(html_content, title, asset_dir=None, document_id="document"):
    """去除重复标题、补全图片说明，并把内嵌图片无损外置。

    兼容正文为 Markdown 源码的平台（如 ShowDoc）：首行 "# 标题" 与文档
    标题一致时同样去重，避免与文档头重复。
    """
    if not html_content:
        return ""

    pattern = rf'^\s*<h1[^>]*>\s*{re.escape(title)}\s*</h1>'
    cleaned_html = re.sub(pattern, '', html_content, flags=re.IGNORECASE)

    # MULTILINE 下 $ 匹配行尾；\s* 前缀只允许跳过空白行，
    # 即仅当首个非空行是标题且与文档标题一致时才去重。
    first_heading = re.match(r'\s*#\s+(.+?)\s*$', cleaned_html, flags=re.MULTILINE)
    if first_heading:
        heading_compact = re.sub(r'\s+', '', first_heading.group(1)).casefold()
        if heading_compact == re.sub(r'\s+', '', title).casefold():
            cleaned_html = cleaned_html[first_heading.end():].lstrip('\n')

    def replace_data_image(match):
        source = _externalize_embedded_image(
            match.group("source"), asset_dir, document_id
        )
        return f'{match.group("prefix")}{match.group("quote")}{source}{match.group("quote")}'

    cleaned_html = re.sub(
        r'(?P<prefix><img\b[^>]*?\bsrc\s*=\s*)'
        r'(?P<quote>["\'])(?P<source>data:image/[^"\']+)(?P=quote)',
        replace_data_image,
        cleaned_html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    image_index = 0

    def enrich_image_alt(match):
        nonlocal image_index
        image_index += 1
        image_tag = match.group(0)
        alt_match = re.search(
            r'\balt\s*=\s*(["\'])(.*?)\1',
            image_tag,
            flags=re.IGNORECASE | re.DOTALL,
        )
        current_alt = alt_match.group(2).strip() if alt_match else ""
        if current_alt.lower() not in {"", "图片", "image", "img"}:
            return image_tag

        meaningful_alt = escape(f"{title} - 步骤图 {image_index}", quote=True)
        if alt_match:
            return (
                image_tag[:alt_match.start()]
                + f'alt="{meaningful_alt}"'
                + image_tag[alt_match.end():]
            )
        closing_index = image_tag.rfind("/>")
        if closing_index < 0:
            closing_index = image_tag.rfind(">")
        return (
            image_tag[:closing_index]
            + f' alt="{meaningful_alt}"'
            + image_tag[closing_index:]
        )

    cleaned_html = re.sub(
        r'<img\b[^>]*>',
        enrich_image_alt,
        cleaned_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return cleaned_html


def convert_html_to_markdown(
    html_content, title, asset_dir=None, document_id="document"
):
    """内置 HTML 转 Markdown，作为外部处理流水线不可用时的回退。"""
    cleaned_html = prepare_html_content(
        html_content,
        title,
        asset_dir=asset_dir,
        document_id=document_id,
    )
    if not cleaned_html:
        return ""

    parser = HTMLToMarkdown()
    parser.feed(cleaned_html)
    return parser.get_markdown()


def normalize_markdown(markdown, heading_offset=4, site_base_url=None):
    """清理 Markdown 并下调正文标题，避免破坏汇总文档的标题层级。"""
    markdown = (markdown or "").replace("\u200b", "").replace("\ufeff", "")
    markdown = markdown.replace("https://rag.local/assets/", "assets/")
    markdown = re.sub(
        # alt 文本可能含裸 "]"（如标题"…【采购退货总额] - 步骤图 1"做图片说明）。
        # 用懒惰匹配到最近的 "](url)" 才能取到正确 URL，否则相对路径无法绝对化，
        # 并触发 ensure_markdown_resources 误判缺失而重复追加资源。
        # 行为与旧正则在正常 alt（无 ]）场景完全一致。
        r'(?P<prefix>!?\[(?:[^\]\n]|\][^\(\n])*?\]\()'
        r'(?P<url>[^)\s]+)(?P<suffix>\))',
        lambda match: (
            match.group("prefix")
            + normalize_resource_url(match.group("url"), site_base_url)
            + match.group("suffix")
        ),
        markdown,
    )
    # Crawl4AI 可能把连续图片拼在同一行；拆成独立块方便云端逐图解析。
    markdown = re.sub(r'\)(?=!\[[^\]\n]+\]\()', ')\n\n', markdown)

    lines = []
    in_code_block = False
    for line in markdown.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            in_code_block = not in_code_block
        if not in_code_block:
            heading = re.match(r'^(#{1,6})(\s+.*)$', line)
            outline_line = line.strip()
            if heading:
                level = min(6, len(heading.group(1)) + heading_offset)
                line = f"{'#' * level}{heading.group(2)}"
            elif re.match(r'^[一二三四五六七八九十]+、\S', outline_line):
                line = f"##### {outline_line}"
            elif re.match(
                r'^[（(][一二三四五六七八九十]+[）)]\S', outline_line
            ):
                line = f"###### {outline_line}"
            else:
                numbered_step = re.match(r'^(\d+)[、．]\s*(.+)$', outline_line)
                if numbered_step:
                    line = f"{numbered_step.group(1)}. {numbered_step.group(2)}"
        lines.append(line.rstrip())

    def is_heading(line):
        return bool(re.match(r'^#{1,6}\s+\S', line))

    def is_image(line):
        return bool(re.match(r'^!\[[^\]]+\]\(.+\)$', line))

    def is_list_item(line):
        return bool(re.match(r'^\s*(?:[-*+] |\d+\. )\S', line))

    # 显式分隔块级元素，兼容依赖空行识别章节、列表和图片的云端解析器。
    formatted_lines = []
    in_code_block = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            in_code_block = not in_code_block

        previous = lines[index - 1] if index > 0 else ""
        following = lines[index + 1] if index + 1 < len(lines) else ""
        block_line = not in_code_block and (is_heading(line) or is_image(line))
        list_start = (
            not in_code_block
            and is_list_item(line)
            and not is_list_item(previous)
        )
        if (block_line or list_start) and formatted_lines and formatted_lines[-1] != "":
            formatted_lines.append("")

        formatted_lines.append(line)

        list_end = (
            not in_code_block
            and is_list_item(line)
            and not is_list_item(following)
        )
        if (block_line or list_end) and following and following.strip():
            formatted_lines.append("")

    return re.sub(r'\n{3,}', '\n\n', '\n'.join(formatted_lines)).strip()


class HTMLResourceExtractor(HTMLParser):
    """提取源 HTML 中的图片与链接，供转换完整性检查和结构化输出。"""

    def __init__(self):
        super().__init__()
        self.images = []
        self.links = []
        self._anchors = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "img" and attrs_dict.get("src"):
            self.images.append({
                "alt": attrs_dict.get("alt", "图片").strip() or "图片",
                "url": attrs_dict["src"],
            })
        elif tag == "a" and attrs_dict.get("href"):
            self._anchors.append({"url": attrs_dict["href"], "text": []})

    def handle_data(self, data):
        if self._anchors:
            self._anchors[-1]["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._anchors:
            anchor = self._anchors.pop()
            self.links.append({
                "text": " ".join("".join(anchor["text"]).split()) or anchor["url"],
                "url": anchor["url"],
            })


def normalize_resource_url(url, site_base_url=None):
    """将图片和链接转换为云端知识库可访问的规范 URL。

    site_base_url 为站点根地址；缺省时沿用云创业版配置，保持原行为。
    """
    url = url.replace("https://rag.local/assets/", "assets/")
    if url.startswith(("assets/", "data:", "#")):
        return url

    api_parts = urllib.parse.urlsplit(site_base_url or CYB_API_BASE_URL)
    base_url = urllib.parse.urlunsplit(
        (api_parts.scheme, api_parts.netloc, "/", "", "")
    )
    absolute_url = urllib.parse.urljoin(base_url, url)
    parts = urllib.parse.urlsplit(absolute_url)
    encoded_path = urllib.parse.quote(
        urllib.parse.unquote(parts.path), safe="/:@-._~!$&'()*+,;="
    )
    encoded_query = urllib.parse.quote(parts.query, safe="=&%/:;+?,")
    encoded_fragment = urllib.parse.quote(parts.fragment, safe="=&%/:;+?,")
    return urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, encoded_path, encoded_query, encoded_fragment)
    )


def extract_html_resources(html_content, site_base_url=None):
    extractor = HTMLResourceExtractor()
    extractor.feed(html_content or "")

    def unique(resources):
        seen_urls = set()
        result = []
        for resource in resources:
            normalized = {
                **resource,
                "url": normalize_resource_url(resource["url"], site_base_url),
            }
            # 以 URL 去重：同一图片多次引用只记一条；首次出现的 alt 保留。
            if normalized["url"] in seen_urls:
                continue
            seen_urls.add(normalized["url"])
            result.append(normalized)
        return result

    return {"images": unique(extractor.images), "links": unique(extractor.links)}


def ensure_markdown_resources(markdown, resources, heading_offset=4, site_base_url=None):
    """若转换器漏掉图片或链接，则补回资源，保证源内容不因清洗而丢失。"""
    markdown = normalize_markdown(
        markdown, heading_offset=heading_offset, site_base_url=site_base_url
    )
    missing_images = [
        item for item in resources.get("images", []) if item["url"] not in markdown
    ]
    missing_links = [
        item for item in resources.get("links", []) if item["url"] not in markdown
    ]
    if not missing_images and not missing_links:
        return markdown

    additions = ["##### 相关资源"]
    additions.extend(
        f'![{item["alt"]}]({item["url"]})' for item in missing_images
    )
    additions.extend(
        f'- [{item["text"]}]({item["url"]})' for item in missing_links
    )
    return "\n\n".join([markdown, "\n".join(additions)]).strip()


def clean_markdown_for_rag(markdown):
    """只规范空白与不可见字符，不删除图片、链接或业务正文。"""
    markdown = (markdown or "").replace("\u200b", "").replace("\ufeff", "")
    markdown = markdown.replace("\xa0", " ")
    lines = [line.rstrip() for line in markdown.splitlines()]
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()


class RAGContentPipeline:
    """Crawl4AI 清洗 HTML，并可选交给 Firecrawl Parse 生成 Markdown。"""

    VALID_MODES = {"auto", "builtin", "crawl4ai", "crawl4ai_firecrawl"}

    def __init__(self, mode=None, asset_dir=None, site_base_url=None):
        self.mode = (mode or os.getenv("CYB_CONTENT_PIPELINE", "auto")).lower()
        self.asset_dir = asset_dir
        if self.mode not in self.VALID_MODES:
            valid_modes = ", ".join(sorted(self.VALID_MODES))
            raise ValueError(f"CYB_CONTENT_PIPELINE 必须是: {valid_modes}")

        # 站点根地址：其他平台爬虫注入自己的入口；缺省沿用云创业版配置。
        api_parts = urllib.parse.urlsplit(site_base_url or CYB_API_BASE_URL)
        self.site_base_url = urllib.parse.urlunsplit(
            (api_parts.scheme, api_parts.netloc, "/", "", "")
        )

        self.firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY", "")
        self.firecrawl_client = None
        self._firecrawl_disabled = False

        if self.mode == "crawl4ai_firecrawl" and not self.firecrawl_api_key:
            raise RuntimeError(
                "使用 crawl4ai_firecrawl 模式需要配置 FIRECRAWL_API_KEY"
            )

    @property
    def use_firecrawl(self):
        return (
            not self._firecrawl_disabled
            and bool(self.firecrawl_api_key)
            and self.mode in {"auto", "crawl4ai_firecrawl"}
        )

    def _fallback_convert(self, records):
        converted = {}
        for record in records:
            markdown = convert_html_to_markdown(
                record["html"],
                record["title"],
                asset_dir=self.asset_dir,
                document_id=record["id"],
            )
            converted[record["id"]] = ensure_markdown_resources(
                markdown,
                record.get("resources", {}),
                heading_offset=0,
                site_base_url=self.site_base_url,
            )
        return converted

    @staticmethod
    def _crawl4ai_markdown(result):
        markdown_result = getattr(result, "markdown", None)
        if isinstance(markdown_result, str):
            return markdown_result

        # fit_markdown 是相关性裁剪结果，可能删除图片或链接；无损语料使用 raw。
        return getattr(markdown_result, "raw_markdown", "") or ""

    def _parse_with_firecrawl(self, html_content, record):
        if self.firecrawl_client is None:
            from firecrawl import Firecrawl

            self.firecrawl_client = Firecrawl(api_key=self.firecrawl_api_key)

        filename = f"{clean_filename(record['id'])}.html"
        document = self.firecrawl_client.parse(
            html_content.encode("utf-8"),
            filename=filename,
            content_type="text/html",
        )
        return getattr(document, "markdown", None) or ""

    async def _convert_with_crawl4ai(self, records):
        from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
        from crawl4ai.async_crawler_strategy import AsyncHTTPCrawlerStrategy
        from crawl4ai.content_filter_strategy import PruningContentFilter
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

        pruning_filter = PruningContentFilter(
            threshold=0.35,
            threshold_type="dynamic",
            min_word_threshold=1,
        )
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            base_url=self.site_base_url,
            verbose=False,
            markdown_generator=DefaultMarkdownGenerator(
                content_filter=pruning_filter,
            ),
        )
        converted = {}
        strategy = AsyncHTTPCrawlerStrategy()

        async with AsyncWebCrawler(crawler_strategy=strategy) as crawler:
            for index, record in enumerate(records, 1):
                prepared_html = prepare_html_content(
                    record["html"],
                    record["title"],
                    asset_dir=self.asset_dir,
                    document_id=record["id"],
                )
                wrapped_html = (
                    '<!doctype html><html><head><meta charset="utf-8">'
                    f'<title>{escape(record["title"])}</title></head>'
                    f'<body><article>{prepared_html}</article></body></html>'
                )
                result = await crawler.arun(
                    url=f"raw:{wrapped_html}",
                    config=run_config,
                )
                if not result.success:
                    error = getattr(result, "error_message", "未知错误")
                    raise RuntimeError(f"Crawl4AI 处理失败: {error}")

                markdown = self._crawl4ai_markdown(result)
                cleaned_html = getattr(result, "cleaned_html", "") or wrapped_html

                if self.use_firecrawl:
                    try:
                        firecrawl_markdown = await asyncio.to_thread(
                            self._parse_with_firecrawl,
                            cleaned_html,
                            record,
                        )
                        if not firecrawl_markdown:
                            raise RuntimeError("Firecrawl 未返回 Markdown")
                        markdown = firecrawl_markdown
                    except Exception as exc:
                        if self.mode == "crawl4ai_firecrawl":
                            raise RuntimeError(
                                f"Firecrawl 处理 {record['title']} 失败: {exc}"
                            ) from exc
                        self._firecrawl_disabled = True
                        print(f"⚠️ Firecrawl 不可用，后续改用 Crawl4AI: {exc}")

                converted[record["id"]] = ensure_markdown_resources(
                    markdown,
                    record.get("resources", {}),
                    site_base_url=self.site_base_url,
                )
                print(
                    f"🧹 内容清洗进度: {index}/{len(records)} - {record['title']}"
                )

        return converted

    def convert(self, records):
        records = [record for record in records if record.get("html")]
        if not records:
            return {}
        if self.mode == "builtin":
            return self._fallback_convert(records)

        try:
            return asyncio.run(self._convert_with_crawl4ai(records))
        except ImportError as exc:
            if self.mode != "auto":
                raise RuntimeError(
                    "缺少内容流水线依赖，请执行 pip install -r requirements.txt"
                ) from exc
            print(f"⚠️ Crawl4AI 未安装，改用内置转换器: {exc}")
            return self._fallback_convert(records)
        except Exception as exc:
            if self.mode != "auto":
                raise
            print(f"⚠️ Crawl4AI 运行失败，改用内置转换器: {exc}")
            return self._fallback_convert(records)


def split_markdown_for_rag(markdown, max_chars=1600, overlap=180):
    """按段落边界切分 Markdown，并保留少量重叠上下文。"""
    if max_chars <= 0 or overlap < 0 or overlap >= max_chars:
        raise ValueError("RAG 分块参数要求 max_chars > overlap >= 0")

    text = (markdown or "").strip()
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        if end < len(text):
            paragraph_end = text.rfind("\n\n", start + max_chars // 2, end)
            line_end = text.rfind("\n", start + max_chars // 2, end)
            boundary = max(paragraph_end, line_end)
            if boundary > start:
                end = boundary

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)

    return chunks


def write_jsonl(path, records):
    """以 UTF-8 JSONL 写出结构化语料。"""
    with open(path, "w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
