"""通用内容清洗管道：按源格式规范化 Markdown、资源校验与 RAG 分块。

从 cyb_rag_md.py 拆出（第 3 阶段），供各平台爬虫共用；
站点根地址通过 site_base_url 注入，缺省沿用云创业版配置以保持原行为。
"""
import base64
import hashlib
import json
import os
import re
import urllib.parse
from importlib.metadata import version
from bs4 import BeautifulSoup
from dataclasses import dataclass
from html import escape, unescape
from html.parser import HTMLParser

from markdown_it import MarkdownIt

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

CYB_API_BASE_URL = os.getenv(
    "CYB_API_BASE_URL", "https://new.yuncyb.com/aicyberp-api"
).rstrip("/")


_MARKDOWN_PARSER = MarkdownIt("commonmark", {"html": True}).enable("table")


class MarkdownValidationError(ValueError):
    """源内容无法无损规范化为结构化 Markdown。"""


def _protected_lines(markdown):
    """Use the parser's source ranges, including nested/indented code and HTML."""
    protected = set()
    for token in _MARKDOWN_PARSER.parse(markdown or ""):
        if token.type in {"fence", "code_block", "html_block"} and token.map:
            protected.update(range(*token.map))
    return protected


def _normalize_markdown_whitespace(markdown):
    lines = (markdown or "").splitlines()
    protected = _protected_lines(markdown)
    result = []
    for index, line in enumerate(lines):
        if index in protected:
            result.append(line)
        elif line.strip():
            # Two trailing spaces are a CommonMark hard break, not noise.
            result.append(line.rstrip() + ("  " if line.endswith("  ") else ""))
        elif result and result[-1] != "":
            result.append("")
    return "\n".join(result).strip("\n")


def preserve_html_paragraph_markers(markdown):
    """HTML paragraphs containing '-' must not become accidental Setext headings.

    HTML heading tags are emitted as ATX by both supported converters. Apply this
    only to HTML output; native Markdown Setext headings remain genuine headings.
    """
    lines = markdown.splitlines()
    for token in _MARKDOWN_PARSER.parse(markdown):
        if token.type == "heading_open" and token.markup in {"-", "="} and token.map:
            index = token.map[1] - 1
            lines[index] = "\\" + lines[index].lstrip()
    return "\n".join(lines)


class HTMLToMarkdown(HTMLParser):
    """
    确定性的 HTML 转 Markdown 解析器。

    覆盖 RAG 文档常见的标题、段落、链接、图片、嵌套列表、代码块与表格；
    转换失败时由后续规范校验阻止落盘，避免生成看似成功但结构损坏的语料。
    """

    def __init__(self):
        super().__init__()
        self.result = []
        self.list_stack = []
        self.link_stack = []
        self.pre_buffer = None
        self.pre_language = ""
        self.table_rows = None
        self.table_row = None
        self.table_cell = None
        self.table_cell_is_header = False

    def _append(self, value):
        if self.table_cell is not None:
            self.table_cell.append(value)
        else:
            self.result.append(value)

    @staticmethod
    def _language_from_attrs(attrs_dict):
        candidates = " ".join(
            filter(None, [attrs_dict.get("class", ""), attrs_dict.get("data-language", "")])
        )
        match = re.search(r"(?:language-|lang-)([\w#+.-]+)", candidates)
        return match.group(1) if match else attrs_dict.get("data-language", "")

    def _render_table(self):
        rows = [row for row in (self.table_rows or []) if row]
        if not rows:
            return ""
        width = max(len(row) for row in rows)

        def cell_text(cell):
            text = re.sub(r"\s+", " ", cell["text"]).strip()
            return text.replace("\\", "\\\\").replace("|", "\\|")

        normalized = [
            [cell_text(cell) for cell in row] + [""] * (width - len(row))
            for row in rows
        ]
        first_row_has_header = any(cell["header"] for cell in rows[0])
        if first_row_has_header:
            header, body = normalized[0], normalized[1:]
        else:
            header, body = [""] * width, normalized
        table_lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join("---" for _ in range(width)) + " |",
        ]
        table_lines.extend("| " + " | ".join(row) + " |" for row in body)
        return "\n".join(table_lines)

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs_dict = dict(attrs)
        if self.pre_buffer is not None:
            if tag == "br":
                self.pre_buffer.append("\n")
            elif tag == "code" and not self.pre_language:
                self.pre_language = self._language_from_attrs(attrs_dict)
            return

        if tag == "pre":
            self.pre_buffer = []
            self.pre_language = self._language_from_attrs(attrs_dict)
            return

        if tag == "table":
            self.table_rows = []
            return
        if self.table_rows is not None:
            if tag == "tr":
                self.table_row = []
            elif tag in {"th", "td"}:
                self.table_cell = []
                self.table_cell_is_header = tag == "th"
            elif tag == "br" and self.table_cell is not None:
                self.table_cell.append("<br>")
            elif tag == "a" and self.table_cell is not None:
                href = attrs_dict.get("href", "")
                self._append("[" if href else "")
                self.link_stack.append(href)
            elif tag == "img" and self.table_cell is not None:
                src = attrs_dict.get("src", "")
                alt = attrs_dict.get("alt", "图片")
                self._append(f"![{alt}]({src})")
            elif tag in {"strong", "b"}:
                self._append("**")
            elif tag in {"em", "i"}:
                self._append("*")
            elif tag == "code":
                self._append("`")
            return

        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            # 保留源文档层级；写出单篇文档和合并文档时再统一调整一次。
            level = int(tag[1])
            self.result.append(f'\n\n{"#" * level} ')
        elif tag == 'p':
            self.result.append('\n\n')
        elif tag in {'div', 'section', 'article', 'main', 'header', 'footer', 'aside'}:
            self.result.append('\n\n')
        elif tag == 'br':
            self.result.append('\n')
        elif tag == 'img':
            src = attrs_dict.get('src', '')
            alt = attrs_dict.get('alt', '图片')
            self.result.append(f'\n\n![{alt}]({src})\n\n')
        elif tag in ['strong', 'b']:
            self.result.append('**')
        elif tag in ['em', 'i']:
            self.result.append('*')
        elif tag in ['del', 's', 'strike']:
            self.result.append('~~')
        elif tag == 'code':
            self.result.append('`')
        elif tag == 'blockquote':
            self.result.append('\n\n> ')
        elif tag == 'hr':
            self.result.append('\n\n---\n\n')
        elif tag == 'a':
            href = attrs_dict.get('href', '')
            self.result.append('[' if href else '')
            self.link_stack.append(href)
        elif tag == 'ul':
            self.list_stack.append({"type": "ul", "index": 1})
            self.result.append('\n')
        elif tag == 'ol':
            try:
                start = max(1, int(attrs_dict.get("start", "1")))
            except ValueError:
                start = 1
            self.list_stack.append({"type": "ol", "index": start})
            self.result.append('\n')
        elif tag == 'li':
            indent = "  " * max(0, len(self.list_stack) - 1)
            if self.list_stack and self.list_stack[-1]["type"] == 'ol':
                item = self.list_stack[-1]
                self.result.append(f'\n{indent}{item["index"]}. ')
                item["index"] += 1
            else:
                self.result.append(f'\n{indent}- ')

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.pre_buffer is not None:
            if tag == "pre":
                code = "".join(self.pre_buffer).rstrip("\n")
                longest = max((len(run) for run in re.findall(r"`+", code)), default=0)
                fence = "`" * max(3, longest + 1)
                self.result.append(
                    f"\n\n{fence}{self.pre_language}\n{code}\n{fence}\n\n"
                )
                self.pre_buffer = None
                self.pre_language = ""
            return

        if self.table_rows is not None:
            if tag in {"th", "td"} and self.table_cell is not None:
                if self.table_row is None:
                    self.table_row = []
                self.table_row.append({
                    "text": "".join(self.table_cell),
                    "header": self.table_cell_is_header,
                })
                self.table_cell = None
                self.table_cell_is_header = False
            elif tag == "tr" and self.table_row is not None:
                self.table_rows.append(self.table_row)
                self.table_row = None
            elif tag == "table":
                rendered = self._render_table()
                if rendered:
                    self.result.append(f"\n\n{rendered}\n\n")
                self.table_rows = None
                self.table_row = None
                self.table_cell = None
            elif tag in {"strong", "b"}:
                self._append("**")
            elif tag in {"em", "i"}:
                self._append("*")
            elif tag == "code":
                self._append("`")
            elif tag == "a":
                href = self.link_stack.pop() if self.link_stack else ""
                self._append(f"]({href})" if href else "")
            return

        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.result.append('\n\n')
        elif tag == 'p':
            self.result.append('\n\n')
        elif tag in {'div', 'section', 'article', 'main', 'header', 'footer', 'aside'}:
            self.result.append('\n\n')
        elif tag in ['strong', 'b']:
            self.result.append('**')
        elif tag in ['em', 'i']:
            self.result.append('*')
        elif tag in ['del', 's', 'strike']:
            self.result.append('~~')
        elif tag == 'code':
            self.result.append('`')
        elif tag == 'a':
            href = self.link_stack.pop() if self.link_stack else ''
            self.result.append(f']({href})' if href else '')
        elif tag in ['ul', 'ol']:
            if self.list_stack:
                self.list_stack.pop()
            self.result.append('\n')

    def handle_data(self, data):
        if self.pre_buffer is not None:
            self.pre_buffer.append(data)
        else:
            self._append(data)

    def get_markdown(self):
        content = _normalize_markdown_whitespace(''.join(self.result))

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

        return _normalize_markdown_whitespace('\n'.join(formatted_lines))


def clean_filename(filename):
    """
    过滤文件名及锚点链接中的非法字符
    """
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.strip().rstrip(".")
    if not filename:
        return "untitled"
    # Reserve space for extensions and disambiguation suffixes on common filesystems.
    if len(filename.encode("utf-8")) > 180:
        digest = hashlib.sha256(filename.encode()).hexdigest()[:12]
        filename = filename.encode("utf-8")[:160].decode("utf-8", errors="ignore") + "_" + digest
    return filename


def _strip_presentational_markdown_html(markdown):
    """移除只负责排版的居中标签，保留标签内部的 Markdown 内容。"""
    markdown = re.sub(
        r"(?i)&lt;\s*/?\s*center(?:\s+[^&]*?)?\s*&gt;",
        "",
        markdown,
    )
    return re.sub(r"(?i)<\s*/?\s*center(?:\s+[^>]*)?>", "", markdown)


def _transform_outside_fenced_code(markdown, transform):
    result, pending = [], []
    protected = _protected_lines(markdown)
    for index, line in enumerate((markdown or "").splitlines(keepends=True)):
        if index in protected:
            if pending:
                result.append(transform("".join(pending)))
                pending.clear()
            result.append(line)
        else:
            pending.append(line)
    if pending:
        result.append(transform("".join(pending)))
    return "".join(result)


def prepare_markdown_content(markdown, title):
    """规范 Markdown 源文，不经过 HTML 转换器，避免段落和标题被压平。"""
    markdown = (markdown or "").replace("\r\n", "\n").replace("\r", "\n")
    markdown = markdown.replace("\u200b", "").replace("\ufeff", "")
    video_pattern = re.compile(
        r"(?is)<video\b(?P<attrs>[^>]*)>(?P<body>.*?)</video\s*>"
    )

    def normalize_editor_html(segment):
        # ShowDoc 会把编辑器插入的 video 标签实体化。只还原已知展示标签，
        # 不能全局 unescape，否则代码示例会被误当作 HTML。
        segment = _strip_presentational_markdown_html(segment)
        segment = re.sub(r"(?i)&lt;br\s*/?&gt;", "\n", segment)
        segment = re.sub(r"(?i)<br\s*/?>", "\n", segment)
        segment = re.sub(
            r"(?is)&lt;video\b.*?&lt;/video\s*&gt;",
            lambda match: unescape(match.group(0)),
            segment,
        )

        def replace_video(match):
            attrs = match.group("attrs")
            source = re.search(r"(?i)\bsrc\s*=\s*([\"'])(.*?)\1", attrs)
            if not source:
                return clean_markdown_for_rag(match.group("body"))
            url = source.group(2).strip()
            # ShowDoc 常同时保存“全屏播放”链接和 video 标签；同一 URL 只保留一次。
            previous_line = segment[:match.start()].rstrip().rsplit("\n", 1)[-1]
            if url and url in previous_line:
                return ""
            label = (
                re.sub(r"<[^>]+>", "", match.group("body")).strip()
                or "播放视频"
            )
            return f"[{label}]({url})"

        return video_pattern.sub(replace_video, segment)

    markdown = _transform_outside_fenced_code(markdown, normalize_editor_html)

    lines = markdown.splitlines()
    first_content_index = next(
        (index for index, line in enumerate(lines) if line.strip()),
        None,
    )
    if first_content_index is not None and title:
        first_heading = re.match(
            r"^#\s+(.+?)\s*$", lines[first_content_index].strip()
        )
        if first_heading:
            source_title = re.sub(r"\s+", "", first_heading.group(1)).casefold()
            expected_title = re.sub(r"\s+", "", title).casefold()
            if source_title == expected_title:
                del lines[first_content_index]

    image_index = 0
    prepared = []
    protected = _protected_lines("\n".join(lines))
    for index, line in enumerate(lines):
        if index not in protected:
            # ShowDoc 把 Markdown 链接的可选 title 引号编码为实体；只在链接
            # 目标尾部还原引号，避免影响正文和代码示例中的 HTML 实体。
            line = re.sub(
                r"(?<=\s)(?:&quot;|&#34;)(.*?)(?:&quot;|&#34;)(?=\s*\))",
                lambda match: f'"{match.group(1)}"',
                line,
            )
            # 空 alt 在语法上合法，但不利于 RAG；只补说明，不改变图片地址和位置。
            def replace_empty_alt(match):
                nonlocal image_index
                image_index += 1
                return f"![{title} - 步骤图 {image_index}]("

            line = re.sub(r"!\[\s*\]\(", replace_empty_alt, line)
        prepared.append(line)

    return clean_markdown_for_rag("\n".join(prepared))


def _rewrite_markdown_inline_urls(markdown, site_base_url=None):
    """重写标准内联链接目标，支持 URL 中括号及可选 title。"""
    output = []
    protected = _protected_lines(markdown)

    for line_index, line in enumerate(markdown.splitlines(keepends=True)):
        if line_index in protected:
            output.append(line)
            continue

        definition = re.match(r"^( {0,3}\[[^\]]+\]:\s*)(<[^>]+>|\S+)(.*)$", line)
        if definition:
            dest = definition.group(2)
            target = normalize_resource_url(dest.strip("<>"), site_base_url)
            line = definition.group(1) + "<" + target + ">" + definition.group(3) + ("\n" if line.endswith("\n") else "")
            output.append(line)
            continue
        replacements = []
        index = 0
        code_span_marker = ""
        while index < len(line):
            if line[index] == "`":
                run = re.match(r"`+", line[index:]).group()
                if not code_span_marker:
                    code_span_marker = run
                elif run == code_span_marker:
                    code_span_marker = ""
                index += len(run)
                continue
            if code_span_marker or line[index] != "[":
                index += 1
                continue

            close = index + 1
            while close < len(line):
                if line[close] == "]" and line[close - 1] != "\\":
                    break
                close += 1
            if close >= len(line) or close + 1 >= len(line) or line[close + 1] != "(":
                index += 1
                continue

            cursor = close + 2
            while cursor < len(line) and line[cursor] in " \t":
                cursor += 1
            if cursor >= len(line):
                break

            if line[cursor] == "<":
                destination_start = cursor + 1
                destination_end = line.find(">", destination_start)
                if destination_end < 0:
                    index = close + 2
                    continue
            else:
                destination_start = cursor
                depth = 0
                while cursor < len(line):
                    character = line[cursor]
                    if character == "\\":
                        cursor += 2
                        continue
                    if character == "(":
                        depth += 1
                    elif character == ")":
                        if depth == 0:
                            break
                        depth -= 1
                    elif character in " \t\n" and depth == 0:
                        break
                    cursor += 1
                destination_end = cursor

            destination = line[destination_start:destination_end]
            if destination:
                replacements.append(
                    (
                        destination_start,
                        destination_end,
                        normalize_resource_url(destination, site_base_url),
                    )
                )
            index = max(destination_end, close + 2)

        for start, end, replacement in reversed(replacements):
            line = line[:start] + replacement + line[end:]
        output.append(line)

    return "".join(output)


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

    # 绝对占位地址可避免 Crawl4AI 将本地相对路径改成站点 URL。
    return f"https://rag.local/assets/{urllib.parse.quote(filename)}"


def prepare_html_content(html_content, title, asset_dir=None, document_id="document"):
    """去除重复 HTML 标题、补全图片说明，并把内嵌图片无损外置。"""
    if not html_content:
        return ""

    pattern = rf'^\s*<h1[^>]*>\s*{re.escape(title)}\s*</h1>'
    cleaned_html = re.sub(pattern, '', html_content, flags=re.IGNORECASE)

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

    soup = BeautifulSoup(cleaned_html, "html.parser")
    quotes = {}
    for quote in list(soup.find_all("blockquote")):
        if quote.parent is None or quote.find_parent("blockquote"):
            continue
        marker = "QUOTE" + hashlib.sha256(str(quote).encode()).hexdigest()
        inner = convert_html_to_markdown(quote.decode_contents(), "")
        quotes[marker] = "\n".join("> " + line if line else ">" for line in inner.splitlines())
        quote.replace_with(marker)
    parser = HTMLToMarkdown()
    parser.feed(str(soup))
    markdown = parser.get_markdown()
    for marker, quote in quotes.items():
        markdown = markdown.replace(marker, quote)
    return markdown


def normalize_markdown(markdown, heading_offset=0, site_base_url=None):
    """规范 Markdown 块、资源地址与常见中文提纲，保留原始标题关系。"""
    markdown = (markdown or "").replace("\u200b", "").replace("\ufeff", "")
    markdown = markdown.replace("https://rag.local/assets/", "assets/")
    markdown = _rewrite_markdown_inline_urls(markdown, site_base_url)
    # Crawl4AI 可能把连续图片拼在同一行；拆成独立块方便云端逐图解析。
    markdown = _transform_outside_fenced_code(markdown, lambda text: re.sub(r'\)(?=!\[[^\]\n]+\]\()', ')\n\n', text))

    lines = []
    protected = _protected_lines(markdown)
    for index, line in enumerate(markdown.splitlines()):
        if index not in protected:
            heading = re.match(r'^(#{1,6})(\s+.*)$', line)
            outline_line = line.strip()
            if heading:
                level = min(6, len(heading.group(1)) + heading_offset)
                line = f"{'#' * level}{heading.group(2)}"
            elif re.match(r'^[一二三四五六七八九十]+、\S', outline_line):
                line = f"## {outline_line}"
            elif re.match(
                r'^[（(][一二三四五六七八九十]+[）)]\S', outline_line
            ):
                line = f"### {outline_line}"
            else:
                numbered_step = re.match(r'^(\d+)[、．]\s*(.+)$', outline_line)
                if numbered_step:
                    line = f"{numbered_step.group(1)}. {numbered_step.group(2)}"
        lines.append(line)

    def is_heading(line):
        return bool(re.match(r'^#{1,6}\s+\S', line))

    def is_image(line):
        return bool(re.match(r'^!\[[^\]]+\]\(.+\)$', line))

    def is_list_item(line):
        return bool(re.match(r'^\s*(?:[-*+] |\d+\. )\S', line))

    # 显式分隔块级元素，兼容依赖空行识别章节、列表和图片的云端解析器。
    formatted_lines = []
    for index, line in enumerate(lines):
        in_code_block = index in protected

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

    return _normalize_markdown_whitespace('\n'.join(formatted_lines))


def normalize_document_markdown(markdown, title="", base_heading_level=2):
    """Normalize actual top-level headings using CommonMark source ranges.

    A stack of original levels preserves sibling relationships when closing gaps.
    Code, quotes, list content and HTML blocks are never mistaken for headings.
    """
    if not 1 <= base_heading_level <= 6:
        raise ValueError("base_heading_level 必须在 1 到 6 之间")
    markdown = clean_markdown_for_rag(markdown)
    lines = markdown.splitlines()
    tokens = _MARKDOWN_PARSER.parse(markdown)
    headings = [(i, t) for i, t in enumerate(tokens)
                if t.type == "heading_open" and t.level == 0 and t.map]
    edits, stack = [], []
    first = next((i for i, line in enumerate(lines) if line.strip()), None)
    for i, token in headings:
        start, end = token.map
        inline = tokens[i + 1]
        content = inline.content
        if start == first and title and re.sub(r"\s+", "", content).casefold() == re.sub(r"\s+", "", title).casefold():
            edits.append((start, end, []))
            continue
        original = int(token.tag[1:])
        while stack and stack[-1][0] >= original:
            stack.pop()
        level = min(6, stack[-1][1] + 1) if stack else base_heading_level
        stack.append((original, level))
        # Setext can span multiple lines; keep its text while changing syntax.
        edits.append((start, end, ["#" * level + " " + content.replace("\n", " ")]))
    for start, end, replacement in reversed(edits):
        lines[start:end] = replacement
    return clean_markdown_for_rag("\n".join(lines))


class HTMLResourceExtractor(HTMLParser):
    """提取源 HTML 中的图片与链接，供转换完整性检查和结构化输出。"""

    def __init__(self):
        super().__init__()
        self.images = []
        self.links = []
        self._anchors = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "img":
            src = attrs_dict.get("data-src") or attrs_dict.get("data-original") or attrs_dict.get("src")
            if src:
                self.images.append({"alt": (attrs_dict.get("alt") or "图片").strip() or "图片", "url": src})
        elif tag in {"video", "audio", "source", "iframe"} and attrs_dict.get("src"):
            self.links.append({"text": tag, "url": attrs_dict["src"]})
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
    url = unescape(url.strip()).replace("https://rag.local/assets/", "assets/")
    if url.startswith(("assets/", "#")):
        return urllib.parse.quote(url, safe="/%#:@-._~!$&'()*+,;=?")
    if url.startswith("data:"):
        return url

    base_url = site_base_url or CYB_API_BASE_URL.rsplit("/", 1)[0] + "/"
    absolute_url = urllib.parse.urljoin(base_url, url)
    parts = urllib.parse.urlsplit(absolute_url)
    encoded_path = urllib.parse.quote(
        parts.path, safe="%/:@-._~!$&'()*+,;="
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


def extract_markdown_resources(markdown, site_base_url=None):
    """使用 Markdown AST 提取图片和链接，并兼容正文中的原生 HTML。"""
    markdown = markdown or ""
    images = []
    links = []
    link_stack = []
    html_fragments = []

    def token_attr(token, name):
        value = token.attrGet(name)
        return value or ""

    def walk(tokens):
        for token in tokens or []:
            if token.type == "html_block":
                html_fragments.append(token.content)
            elif token.type == "inline" and token.children:
                html_fragments.append("".join(
                    child.content
                    for child in token.children
                    if child.type in {"html_inline", "text"}
                ))
            if token.type == "image":
                images.append({
                    "alt": (token.content or "图片").strip() or "图片",
                    "url": token_attr(token, "src"),
                })
            elif token.type == "link_open":
                link_stack.append({"url": token_attr(token, "href"), "text": []})
            elif token.type == "link_close" and link_stack:
                link = link_stack.pop()
                links.append({
                    "text": " ".join("".join(link["text"]).split()) or link["url"],
                    "url": link["url"],
                })
            elif link_stack and token.type in {"text", "code_inline"}:
                link_stack[-1]["text"].append(token.content)
            if token.children:
                walk(token.children)

    walk(_MARKDOWN_PARSER.parse(markdown))

    # 仅解析 Markdown AST 标记为 HTML 的正文片段；代码示例中的 <a>/<img>
    # 不是文档资源，不能进入资源清单或被追加到“相关资源”。
    html_resources = extract_html_resources(
        "\n".join(html_fragments), site_base_url=site_base_url
    )
    images.extend(html_resources["images"])
    links.extend(html_resources["links"])

    def unique(resources):
        result = []
        seen = set()
        for resource in resources:
            url = resource.get("url") or ""
            if not url:
                continue
            normalized = {
                **resource,
                "url": normalize_resource_url(url, site_base_url),
            }
            if normalized["url"] in seen:
                continue
            seen.add(normalized["url"])
            result.append(normalized)
        return result

    return {"images": unique(images), "links": unique(links)}


def ensure_markdown_resources(
    markdown,
    resources,
    heading_offset=0,
    site_base_url=None,
    title="",
    base_heading_level=2,
):
    """若转换器漏掉图片或链接，则补回资源，保证源内容不因清洗而丢失。"""
    resources = {kind: [{**item, "url": normalize_resource_url(item["url"], site_base_url)} for item in items]
                 for kind, items in resources.items()}
    markdown = normalize_markdown(
        markdown, heading_offset=heading_offset, site_base_url=site_base_url
    )
    markdown = normalize_document_markdown(
        markdown,
        title=title,
        base_heading_level=base_heading_level,
    )
    actual = extract_markdown_resources(markdown, site_base_url=site_base_url)
    present = {item["url"] for items in actual.values() for item in items}
    missing_images = [item for item in resources.get("images", []) if item["url"] not in present]
    missing_links = [item for item in resources.get("links", []) if item["url"] not in present]
    if not missing_images and not missing_links:
        return markdown

    additions = ["## 相关资源"]
    def resource_link(item, image=False):
        label = item.get("alt" if image else "text") or item["url"]
        label = re.sub(r"([\\\[\]])", r"\\\1", str(label)).replace("\n", " ")
        url = item["url"].replace("<", "%3C").replace(">", "%3E").replace(" ", "%20")
        return ("!" if image else "- ") + f"[{label}](<{url}>)"
    additions.extend(resource_link(item, True) for item in missing_images)
    additions.extend(resource_link(item) for item in missing_links)
    return "\n\n".join([markdown, "\n".join(additions)]).strip()


def validate_canonical_markdown(markdown, resources=None, title=""):
    """验证面向 RAG 的 Markdown 结构；不合格时阻止静默落盘。"""
    markdown = clean_markdown_for_rag(markdown)
    if not markdown:
        prefix = f"文档《{title}》" if title else "文档"
        raise MarkdownValidationError(prefix + "不是规范 Markdown：正文为空")

    issues = []
    lines = markdown.splitlines()
    tokens = _MARKDOWN_PARSER.parse(markdown)
    previous_heading_level = 0
    has_collapsed_heading_line = False
    for token in tokens:
        if token.type == "fence" and token.map:
            last = lines[token.map[1] - 1].strip()
            # Nested fences may have quote/list prefixes; use parser indentation.
            closing = re.search(r"(?:^|[ >])(" + re.escape(token.markup[0]) + r"{" + str(len(token.markup)) + r",})\s*$", last)
            if token.map[1] - token.map[0] < 2 or not closing:
                issues.append("代码围栏未闭合")
        if token.type != "heading_open" or token.level != 0:
            continue
        level = int(token.tag[1:])
        if level == 1:
            issues.append("正文中出现 H1，H1 只允许用于文档标题")
        if previous_heading_level and level > previous_heading_level + 1:
            issues.append(f"标题层级从 H{previous_heading_level} 跳到 H{level}")
        previous_heading_level = level
        line = lines[token.map[0]]
        if len(line) > 500 and re.search(r"\S[ \t]+#{1,6}\s+\S", line):
            has_collapsed_heading_line = True

    # 旧故障会把整篇文档压成一行；出现内联标题标记时直接拒绝。
    if has_collapsed_heading_line:
        issues.append("正文疑似被压缩成单行，章节标题已退化为普通文本")

    parsed_resources = extract_markdown_resources(markdown)
    resource_urls = {item["url"] for items in parsed_resources.values() for item in items}
    for kind, items in (resources or {}).items():
        for item in items:
            url = item.get("url") or ""
            if url and normalize_resource_url(url) not in resource_urls:
                issues.append(f"{kind} 资源未出现在正文中: {url}")

    if issues:
        prefix = f"文档《{title}》" if title else "文档"
        raise MarkdownValidationError(prefix + "不是规范 Markdown：" + "；".join(issues))


def clean_markdown_for_rag(markdown):
    """只规范空白与不可见字符，不删除图片、链接或业务正文。"""
    markdown = _transform_outside_fenced_code(
        markdown or "", lambda text: text.replace("\u200b", "").replace("\ufeff", "").replace("\xa0", " ")
    )
    return _normalize_markdown_whitespace(markdown)


@dataclass(frozen=True)
class MarkdownConversion:
    """同一文档的审计原文与面向检索的规范正文。"""

    raw_markdown: str
    markdown: str
    engine: str = ""
    engine_version: str = ""
    fallback_reason: str = ""


class RAGContentPipeline:
    """按声明的源格式生成结构稳定、资源完整的 Markdown。"""

    VALID_MODES = {"auto", "builtin", "crawl4ai"}

    def __init__(self, mode=None, asset_dir=None, site_base_url=None):
        self.mode = (mode or os.getenv("CYB_CONTENT_PIPELINE", "auto")).lower()
        self.asset_dir = asset_dir
        if self.mode not in self.VALID_MODES:
            valid_modes = ", ".join(sorted(self.VALID_MODES))
            raise ValueError(f"CYB_CONTENT_PIPELINE 必须是: {valid_modes}")

        # 站点根地址：其他平台爬虫注入自己的入口；缺省沿用云创业版配置。
        self.site_base_url = site_base_url or CYB_API_BASE_URL.rsplit("/", 1)[0] + "/"

    def _html_markdown(self, record):
        content = record["content"]
        # GFM cannot express spans or nested tables. Keep these losslessly as HTML.
        soup = BeautifulSoup(content, "html.parser")
        preserved = {}
        for table in list(soup.find_all("table")):
            if table.parent is None or table.find_parent("table"):
                continue
            if table.select("[rowspan], [colspan], table"):
                marker = "TABLE" + hashlib.sha256(str(table).encode()).hexdigest()
                preserved[marker] = str(table)
                replacement = soup.new_tag("p")
                replacement.string = marker
                table.replace_with(replacement)
        content = str(soup)
        reason = ""
        engine = "builtin"
        engine_version = "1"
        if self.mode != "builtin":
            try:
                from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
                if not hasattr(self, "_generator"):
                    self._generator = DefaultMarkdownGenerator(options={"body_width": 0})
                raw = self._generator.generate_markdown(
                    content,
                    base_url=record.get("base_url") or self.site_base_url,
                    citations=False,
                ).raw_markdown
                engine, engine_version = "crawl4ai", version("crawl4ai")
            except Exception as exc:
                if self.mode != "auto":
                    raise
                reason = f"{type(exc).__name__}: {exc}"
                raw = convert_html_to_markdown(content, record["title"])
        else:
            raw = convert_html_to_markdown(content, record["title"])
        raw = preserve_html_paragraph_markers(raw or "")
        for marker, table in preserved.items():
            raw = raw.replace(marker, table)
        return raw, engine, engine_version, reason

    def convert(self, records, *, errors=None, progress_callback=None):
        """Convert each document independently; callers may collect failures.

        HTML already fetched from an API needs only Crawl4AI's generator, not a
        second crawler/browser lifecycle. Cancellation callbacks stay outside the
        exception handler and always propagate to the task owner.
        """
        converted = {}
        for index, record in enumerate(records, 1):
            if progress_callback:
                progress_callback(index - 1, len(records), f"正在清洗: {record['title']}")
            try:
                source_format = record.get("source_format")
                if source_format == "markdown":
                    raw = record["content"]
                    engine, engine_version, reason = "markdown-it-py", version("markdown-it-py"), ""
                elif source_format == "html":
                    raw, engine, engine_version, reason = self._html_markdown(record)
                else:
                    raise ValueError(f"不支持的源内容格式: {source_format}")
                markdown = ensure_markdown_resources(
                    raw,
                    record.get("resources", {}),
                    site_base_url=record.get("base_url") or self.site_base_url,
                    title=record["title"],
                )
                validate_canonical_markdown(markdown, record.get("resources", {}), title=record["title"])
                converted[record["id"]] = MarkdownConversion(
                    raw_markdown=raw, markdown=markdown, engine=engine,
                    engine_version=engine_version, fallback_reason=reason,
                )
            except Exception as exc:
                if errors is None:
                    raise
                errors[record["id"]] = f"{type(exc).__name__}: {exc}"
            if progress_callback:
                progress_callback(index, len(records), f"已清洗: {record['title']}")
        return converted


@dataclass(frozen=True)
class RAGMarkdownChunk:
    """带章节路径的 Markdown 检索分块。"""

    content: str
    section_path: tuple[str, ...] = ()


def _split_long_text(text, max_chars, overlap):
    """只在单个超长块中按自然换行切分，作为结构切分的最后回退。"""
    chunks = []
    start = 0
    safe_overlap = min(overlap, max_chars // 4)
    while start < len(text):
        end = min(len(text), start + max_chars)
        if end < len(text):
            paragraph_end = text.rfind("\n\n", start + max_chars // 2, end)
            line_end = text.rfind("\n", start + max_chars // 2, end)
            sentence_end = max(
                text.rfind("。", start + max_chars // 2, end),
                text.rfind("！", start + max_chars // 2, end),
                text.rfind("？", start + max_chars // 2, end),
            )
            boundary = max(paragraph_end, line_end, sentence_end)
            if boundary > start:
                end = boundary + (1 if boundary == sentence_end else 0)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(start + 1, end - safe_overlap)
    return chunks


def _markdown_blocks(text):
    """CommonMark block ranges keep nested lists, fences and HTML intact."""
    lines = (text or "").splitlines()
    blocks = []
    covered = 0
    for token in _MARKDOWN_PARSER.parse(text or ""):
        if token.level != 0 or not token.map or token.nesting == -1:
            continue
        start, end = token.map
        if start < covered:
            continue
        block = "\n".join(lines[start:end]).strip("\n")
        if block:
            blocks.append(block)
        covered = end
    return blocks


def _split_atomic_block(block, max_chars):
    tokens = _MARKDOWN_PARSER.parse(block)
    if tokens and tokens[0].type == "fence":
        token = tokens[0]
        fence = token.markup
        opening = fence + token.info
        available = max_chars - len(opening) - len(fence) - 2
        if available <= 0:
            return [block]
        lines = token.content.splitlines(keepends=True)
        chunks, current = [], ""
        for line in lines:
            if current and len(current) + len(line) > available:
                chunks.append(opening + "\n" + current.rstrip("\n") + "\n" + fence)
                current = ""
            # A single oversized code line stays intact and is flagged on export.
            current += line
        if current:
            chunks.append(opening + "\n" + current.rstrip("\n") + "\n" + fence)
        return chunks
    if tokens and tokens[0].type == "table_open":
        lines = block.splitlines()
        header = "\n".join(lines[:2])
        chunks, current = [], header
        for line in lines[2:]:
            if current != header and len(current) + len(line) + 1 > max_chars:
                chunks.append(current)
                current = header
            current += "\n" + line
        return chunks + [current]
    return [block]


def _is_atomic_markdown_block(block):
    stripped = block.strip()
    fenced_code = stripped.startswith(("```", "~~~"))
    table = bool(re.search(r'^\s*\|?.+\|.+$', stripped, flags=re.MULTILINE)) and bool(
        re.search(r'^\s*\|?\s*:?-{3,}', stripped, flags=re.MULTILINE)
    )
    return fenced_code or table or bool(_MARKDOWN_PARSER.parse(block) and _MARKDOWN_PARSER.parse(block)[0].type == "html_block")


def _split_markdown_body(text, max_chars, overlap):
    blocks = _markdown_blocks(text)
    if not blocks:
        return []

    chunks = []
    current = []

    def size(items):
        return len("\n\n".join(items))

    def flush():
        if current:
            chunks.append("\n\n".join(current).strip())

    for block in blocks:
        if len(block) > max_chars:
            flush()
            current = []
            if _is_atomic_markdown_block(block):
                # 表格和代码块宁可略微超长，也不切出无法解析的半块结构。
                chunks.extend(_split_atomic_block(block, max_chars))
            else:
                chunks.extend(_split_long_text(block, max_chars, overlap))
            continue

        if not current or size(current + [block]) <= max_chars:
            current.append(block)
            continue

        previous = list(current)
        flush()
        carry = []
        carry_size = 0
        for previous_block in reversed(previous):
            projected = carry_size + len(previous_block) + (2 if carry else 0)
            if projected > overlap:
                break
            carry.insert(0, previous_block)
            carry_size = projected
        if carry and size(carry + [block]) > max_chars:
            carry = []
        current = carry + [block]

    flush()
    return chunks


def split_markdown_sections_for_rag(markdown, max_chars=1600, overlap=180):
    """先按 Markdown 标题切章节，再按完整段落切分并携带章节路径。"""
    if max_chars <= 0 or overlap < 0 or overlap >= max_chars:
        raise ValueError("RAG 分块参数要求 max_chars > overlap >= 0")

    text = (markdown or "").strip()
    if not text:
        return []

    sections = []
    heading_stack = []
    lines = text.splitlines()
    headings = [(i, t) for i, t in enumerate(_MARKDOWN_PARSER.parse(text)) if t.type == "heading_open" and t.level == 0]
    tokens = _MARKDOWN_PARSER.parse(text)
    cursor = 0
    for i, token in headings:
        start, end = token.map
        body = clean_markdown_for_rag("\n".join(lines[cursor:start]))
        if body:
            sections.append((tuple(heading_stack), body))
        level, title = int(token.tag[1:]), tokens[i + 1].content
        while heading_stack and heading_stack[-1][0] >= level:
            heading_stack.pop()
        heading_stack.append((level, title))
        cursor = end
    body = clean_markdown_for_rag("\n".join(lines[cursor:]))
    if body:
        sections.append((tuple(heading_stack), body))
    elif heading_stack:
        return [RAGMarkdownChunk(text, tuple(title for _, title in heading_stack))]

    chunks = []
    for headings, body in sections:
        prefix = "\n\n".join(f"{'#' * level} {title}" for level, title in headings)
        available = max(32, max_chars - len(prefix) - (2 if prefix else 0))
        section_overlap = min(overlap, available // 4)
        for body_chunk in _split_markdown_body(body, available, section_overlap):
            content = "\n\n".join(part for part in (prefix, body_chunk) if part).strip()
            chunks.append(
                RAGMarkdownChunk(
                    content=content,
                    section_path=tuple(title for _, title in headings),
                )
            )
    return chunks


def split_markdown_for_rag(markdown, max_chars=1600, overlap=180):
    """兼容旧调用：返回标题感知分块的正文字符串列表。"""
    return [
        chunk.content
        for chunk in split_markdown_sections_for_rag(
            markdown,
            max_chars=max_chars,
            overlap=overlap,
        )
    ]


def write_jsonl(path, records):
    """以 UTF-8 JSONL 写出结构化语料。"""
    import tempfile
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=os.path.dirname(os.path.abspath(path)), delete=False) as output_file:
            temporary = output_file.name
            for record in records:
                output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.remove(temporary)
