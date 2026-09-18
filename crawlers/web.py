"""通用网页知识库爬虫。

输入一个 HTTP(S) URL，使用 Crawl4AI 渲染页面并提取正文 Markdown，随后复用
BaseCrawler 的统一落盘、RAG JSONL 和 ZIP 下载流程。
"""
import asyncio
import gzip
import hashlib
import html
import ipaddress
import json
import os
import re
import socket
import urllib.parse
from collections import deque
from datetime import datetime
from xml.etree import ElementTree

import requests

from common.converter import (
    clean_markdown_for_rag,
    extract_html_resources,
    normalize_markdown,
)
from crawlers.base import BaseCrawler, CrawledDocument, DocumentStub


class WebCrawler(BaseCrawler):
    platform = "web"
    display_name = "通用网页"
    entry_url = ""
    requires_auth = False

    def __init__(
        self,
        save_dir,
        url,
        progress_callback=None,
        pipeline_mode=None,
        crawl_mode="page",
        max_pages=0,
        max_depth=0,
    ):
        self.url = self.validate_url(url)
        self.crawl_mode = (crawl_mode or "page").lower()
        if self.crawl_mode not in {"page", "site"}:
            raise ValueError("crawl_mode 必须是 page 或 site")
        # 0 means unlimited. Whole-site mode must not silently truncate a site;
        # callers can still set explicit safety limits for trials or cost control.
        self.max_pages = max(0, int(max_pages))
        self.max_depth = max(0, int(max_depth))
        parsed = urllib.parse.urlsplit(self.url)
        self.site_base_url = urllib.parse.urlunsplit(
            (parsed.scheme, parsed.netloc, "/", "", "")
        )
        self.entry_url = self.url
        self._document_id = hashlib.sha1(self.url.encode("utf-8")).hexdigest()[:16]
        self.discovery_source = "single_page"
        self.discovered_url_count = 1
        super().__init__(
            save_dir,
            progress_callback=progress_callback,
            pipeline_mode=pipeline_mode,
        )
        self.collection_name = "网页知识库"

    @staticmethod
    def validate_url(value):
        """校验 URL，并默认阻止明显的本机/内网目标，降低 SSRF 风险。"""
        url = (value or "").strip()
        if len(url) > 2048:
            raise ValueError("URL 长度不能超过 2048 个字符")

        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme.lower() not in {"http", "https"}:
            raise ValueError("只支持 http:// 或 https:// URL")
        if not parsed.hostname:
            raise ValueError("URL 缺少有效主机名")
        if parsed.username or parsed.password:
            raise ValueError("不支持带用户名或密码的 URL")
        try:
            parsed.port
        except ValueError as exc:
            raise ValueError("URL 端口无效") from exc

        allow_private = os.getenv("WEB_CRAWLER_ALLOW_PRIVATE_URLS", "false").lower()
        if allow_private in {"1", "true", "yes"}:
            return url

        hostname = parsed.hostname.rstrip(".").lower()
        if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(
            ".local"
        ):
            raise ValueError("出于安全原因，不允许访问本机或 .local 域名")

        addresses = set()
        try:
            for result in socket.getaddrinfo(
                hostname, parsed.port or 443, type=socket.SOCK_STREAM
            ):
                addresses.add(result[4][0])
        except socket.gaierror:
            # DNS 失败交给 Crawl4AI 返回更具体的网络错误，不在这里误报 URL 格式。
            addresses = set()

        for address in addresses:
            try:
                ip = ipaddress.ip_address(address)
            except ValueError:
                continue
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise ValueError("出于安全原因，不允许访问本机或内网地址")
        return url

    def list_documents(self):
        parsed = urllib.parse.urlsplit(self.url)
        title = parsed.path.rstrip("/").split("/")[-1] or parsed.netloc
        return [DocumentStub(self._document_id, title, "网页")]

    def _run_config(self, deep_crawl_strategy=None):
        from crawl4ai import CacheMode, CrawlerRunConfig
        from crawl4ai.content_filter_strategy import PruningContentFilter
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=1,
            verbose=False,
            excluded_tags=["nav", "header", "footer", "aside", "form", "script", "style"],
            excluded_selector=(
                "[class*='sidebar'], [id*='sidebar'], "
                "[class*='breadcrumb'], [id*='breadcrumb'], "
                "[class*='navigation'], [id*='navigation'], "
                "[class*='search'], [id*='search']"
            ),
            deep_crawl_strategy=deep_crawl_strategy,
            # These options are generic browser hardening. They improve compatibility
            # with dynamic sites, but do not attempt to bypass interactive challenges.
            simulate_user=True,
            override_navigator=True,
            markdown_generator=DefaultMarkdownGenerator(
                content_filter=PruningContentFilter(
                    threshold=0.35,
                    threshold_type="dynamic",
                    min_word_threshold=1,
                )
            ),
        )

    @staticmethod
    def _browser_config():
        from crawl4ai import BrowserConfig

        return BrowserConfig(
            headless=True,
            enable_stealth=True,
            user_agent_mode="random",
            viewport_width=1440,
            viewport_height=900,
            verbose=False,
        )

    async def _crawl(self):
        from crawl4ai import AsyncWebCrawler

        async with AsyncWebCrawler(config=self._browser_config()) as crawler:
            return await crawler.arun(
                url=self.url,
                config=self._run_config(),
            )

    @staticmethod
    def _sitemap_locs(xml_text):
        root = ElementTree.fromstring(xml_text)
        root_type = root.tag.rsplit("}", 1)[-1].lower()
        locs = [
            (element.text or "").strip()
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] == "loc" and element.text
        ]
        return root_type, locs

    @staticmethod
    def _http_session():
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/140.0.0.0 Safari/537.36"
                )
            }
        )
        session.mount("https://", HTTPAdapter(max_retries=retry))
        session.mount("http://", HTTPAdapter(max_retries=retry))
        return session

    @staticmethod
    def _response_xml(response):
        content = response.content
        if content[:2] == b"\x1f\x8b":
            content = gzip.decompress(content)
        # ElementTree honors the XML declaration when given bytes. Decoding via
        # requests.response.encoding can corrupt non-ASCII sitemap URLs.
        return content

    def _discover_sitemap_urls(self):
        """Discover every same-host page declared by robots.txt/sitemaps."""
        parsed = urllib.parse.urlsplit(self.url)
        origin = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
        sitemap_queue = deque(
            [
                f"{origin}/sitemap.xml",
                f"{origin}/sitemap_index.xml",
            ]
        )
        queued_sitemaps = set(sitemap_queue)
        visited_sitemaps = set()
        page_urls = []
        seen_pages = set()

        session = self._http_session()
        try:
            try:
                robots = session.get(f"{origin}/robots.txt", timeout=20)
                if robots.ok:
                    for match in re.finditer(
                        r"(?im)^\s*sitemap\s*:\s*(\S+)\s*$", robots.text
                    ):
                        sitemap_url = urllib.parse.urljoin(origin, match.group(1))
                        sitemap_parts = urllib.parse.urlsplit(sitemap_url)
                        if (
                            sitemap_parts.netloc.lower() == parsed.netloc.lower()
                            and sitemap_url not in queued_sitemaps
                        ):
                            queued_sitemaps.add(sitemap_url)
                            sitemap_queue.append(sitemap_url)
            except requests.RequestException:
                pass

            while sitemap_queue:
                sitemap_url = sitemap_queue.popleft()
                if sitemap_url in visited_sitemaps:
                    continue
                visited_sitemaps.add(sitemap_url)
                try:
                    response = session.get(sitemap_url, timeout=30)
                    response.raise_for_status()
                    root_type, locs = self._sitemap_locs(
                        self._response_xml(response)
                    )
                except (
                    OSError,
                    requests.RequestException,
                    ElementTree.ParseError,
                    ValueError,
                ):
                    continue

                if root_type == "sitemapindex":
                    for loc in locs:
                        sitemap_parts = urllib.parse.urlsplit(
                            urllib.parse.urljoin(sitemap_url, loc)
                        )
                        nested_url = urllib.parse.urlunsplit(sitemap_parts)
                        if (
                            sitemap_parts.netloc.lower() == parsed.netloc.lower()
                            and nested_url not in queued_sitemaps
                        ):
                            queued_sitemaps.add(nested_url)
                            sitemap_queue.append(nested_url)
                    continue
                if root_type != "urlset":
                    continue

                for loc in locs:
                    normalized = self._normalize_candidate_url(loc)
                    if not normalized or normalized in seen_pages:
                        continue
                    seen_pages.add(normalized)
                    page_urls.append(normalized)
        finally:
            session.close()

        if not page_urls:
            self.discovery_source = "link_crawl"
            self.discovered_url_count = 0
            print("ℹ️ 未发现有效 sitemap，回退同站链接深度爬取")
            return []

        start_url = self._normalize_candidate_url(self.url)
        root_url = self._normalize_candidate_url(origin + "/")
        ordered = []
        ordered_seen = set()
        for candidate in (start_url, root_url, *sorted(page_urls)):
            if candidate and candidate not in ordered_seen:
                ordered_seen.add(candidate)
                ordered.append(candidate)
        self.discovery_source = "sitemap"
        self.discovered_url_count = len(ordered)
        if self.max_pages:
            ordered = ordered[: self.max_pages]
        return ordered

    async def _crawl_site(self):
        from crawl4ai import AsyncWebCrawler

        urls = self._discover_sitemap_urls()
        async with AsyncWebCrawler(config=self._browser_config()) as crawler:
            if urls:
                self._notify(0, len(urls), f"已发现 {len(urls)} 个站内页面，开始批量抓取")
                results = []
                batch_size = max(1, int(os.getenv("WEB_CRAWLER_BATCH_SIZE", "10")))
                for offset in range(0, len(urls), batch_size):
                    batch = urls[offset : offset + batch_size]
                    batch_results = await crawler.arun_many(
                        urls=batch,
                        config=self._run_config(),
                    )
                    results.extend(batch_results)
                    self._notify(
                        min(offset + len(batch), len(urls)),
                        len(urls),
                        f"已抓取 {min(offset + len(batch), len(urls))}/{len(urls)} 个站内页面",
                    )
                return results

            # No usable sitemap: crawl from both the submitted page and site root.
            # Besides normal anchors, inspect generic embedded route strings used by
            # client-rendered applications. No host, product, or path is special-cased.
            results = []
            parsed = urllib.parse.urlsplit(self.url)
            root_url = urllib.parse.urlunsplit(
                (parsed.scheme, parsed.netloc, "/", "", "")
            )
            seeds = [self._normalize_candidate_url(self.url)]
            normalized_root = self._normalize_candidate_url(root_url)
            if normalized_root and normalized_root not in seeds:
                seeds.append(normalized_root)

            queue = deque((url, 0) for url in seeds if url)
            queued = set(url for url in seeds if url)
            batch_size = max(1, int(os.getenv("WEB_CRAWLER_BATCH_SIZE", "10")))
            while queue and (not self.max_pages or len(results) < self.max_pages):
                remaining = (
                    self.max_pages - len(results) if self.max_pages else batch_size
                )
                take = min(batch_size, remaining, len(queue))
                batch_items = [queue.popleft() for _ in range(take)]
                batch_urls = [item[0] for item in batch_items]
                depths = {item[0]: item[1] for item in batch_items}
                batch_results = await crawler.arun_many(
                    urls=batch_urls,
                    config=self._run_config(),
                )

                for result in batch_results:
                    result_url = self._normalize_candidate_url(
                        getattr(result, "url", "")
                    )
                    depth = depths.get(result_url, 0)
                    metadata = getattr(result, "metadata", None)
                    if isinstance(metadata, dict):
                        metadata["depth"] = depth
                    results.append(result)

                    if not getattr(result, "success", False):
                        continue
                    if self.max_depth and depth >= self.max_depth:
                        continue
                    for candidate in self._result_candidate_urls(result):
                        if candidate in queued:
                            continue
                        if self.max_pages and len(queued) >= self.max_pages:
                            break
                        queued.add(candidate)
                        queue.append((candidate, depth + 1))

                total = self.max_pages or max(len(results) + len(queue), len(results))
                self._notify(
                    len(results),
                    total,
                    f"已抓取 {len(results)} 个页面，待处理 {len(queue)} 个",
                )
            self.discovered_url_count = len(queued)
            return results

    @staticmethod
    def _looks_like_page_path(path):
        lower_path = path.lower()
        if lower_path.startswith("/_next/"):
            return False
        return not lower_path.endswith(
            (
                ".xml", ".json", ".txt", ".js", ".css", ".map",
                ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
                ".webp", ".avif", ".woff", ".woff2", ".ttf", ".pdf",
                ".zip", ".gz", ".mp3", ".mp4", ".webm",
            )
        )

    def _normalize_candidate_url(self, value):
        if not value:
            return ""
        parsed_start = urllib.parse.urlsplit(self.url)
        candidate = urllib.parse.urlsplit(urllib.parse.urljoin(self.url, value))
        if candidate.scheme not in {"http", "https"}:
            return ""
        if candidate.netloc.lower() != parsed_start.netloc.lower():
            return ""
        path = candidate.path.rstrip("/") or "/"
        if not self._looks_like_page_path(path):
            return ""
        return urllib.parse.urlunsplit(
            (candidate.scheme, candidate.netloc, path, "", "")
        )

    def _result_candidate_urls(self, result):
        values = []
        links = getattr(result, "links", None) or {}
        for link in links.get("internal", []):
            values.append(link.get("href"))

        raw_html = html.unescape(getattr(result, "html", "") or "")
        raw_html = (
            raw_html.replace("\\/", "/")
            .replace("\\u002F", "/")
            .replace('\\"', '"')
            .replace("\\'", "'")
        )
        values.extend(
            re.findall(
                r"(?i)(?:href|url|path|route)\s*[\"']?\s*[:=]\s*[\"']"
                r"(/(?!/)[A-Za-z0-9][A-Za-z0-9._~!$&()*+,;=:@%/?#\[\]-]*)"
                r"[\"']",
                raw_html,
            )
        )

        candidates = []
        seen = set()
        for value in values:
            normalized = self._normalize_candidate_url(value)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            candidates.append(normalized)
        return candidates

    @staticmethod
    def _markdown_from_result(result):
        markdown_result = getattr(result, "markdown", None)
        if isinstance(markdown_result, str):
            return markdown_result
        if markdown_result is None:
            return ""
        # fit_markdown 是去噪后的正文；为空时回退到 raw_markdown，避免页面内容丢失。
        return (
            getattr(markdown_result, "fit_markdown", "")
            or getattr(markdown_result, "raw_markdown", "")
            or ""
        )

    def _document_from_result(self, result, fallback_url, fallback_title=None):
        result_url = getattr(result, "url", None) or fallback_url
        parsed = urllib.parse.urlsplit(result_url)
        result_id = hashlib.sha1(result_url.encode("utf-8")).hexdigest()[:16]
        path_title = parsed.path.rstrip("/").split("/")[-1] or parsed.netloc
        stub = DocumentStub(result_id, fallback_title or path_title, "网页")

        markdown = normalize_markdown(
            self._markdown_from_result(result),
            heading_offset=0,
            site_base_url=self.site_base_url,
        )
        markdown = clean_markdown_for_rag(markdown)
        cleaned_html = getattr(result, "cleaned_html", "") or ""
        resources = extract_html_resources(
            cleaned_html, site_base_url=self.site_base_url
        )
        metadata = getattr(result, "metadata", None) or {}
        title = metadata.get("title") or stub.title
        depth = metadata.get("depth")
        return CrawledDocument(
            id=stub.id,
            title=title,
            category=stub.category,
            html=cleaned_html,
            updated_at=datetime.now().isoformat(timespec="seconds"),
            metadata={
                "url": result_url,
                "title": title,
                "depth": depth,
                "status_code": getattr(result, "status_code", None),
            },
            markdown=markdown,
            resources=resources,
        )

    @staticmethod
    def _blocked_page_reason(document):
        """Detect short challenge/error shells that browsers often report as success."""
        content = (document.markdown or "").strip()
        if len(content) > 1500:
            return ""

        normalized = " ".join(content.lower().split())
        title = (document.title or "").strip().lower()
        challenge_markers = (
            "环境异常",
            "完成验证后即可继续访问",
            "访问过于频繁",
            "安全验证",
            "请先完成验证",
            "verify you are human",
            "verification required",
            "captcha",
            "access denied",
            "request blocked",
            "just a moment",
            "enable javascript and cookies",
        )
        matched = next(
            (marker for marker in challenge_markers if marker in normalized or marker in title),
            "",
        )
        return f"页面返回验证/拦截提示（{matched}）" if matched else ""

    @classmethod
    def _result_failure_reason(cls, result, document):
        status_code = getattr(result, "status_code", None)
        if status_code and int(status_code) >= 400:
            return f"HTTP {status_code}"
        return cls._blocked_page_reason(document)

    def fetch_document(self, stub):
        """抓取单页并返回已清洗 Markdown，供预览接口复用。"""
        result = asyncio.run(self._crawl())
        if not getattr(result, "success", False):
            message = getattr(result, "error_message", "未知错误")
            raise RuntimeError(f"Crawl4AI 访问失败: {message}")
        document = self._document_from_result(result, self.url, stub.title)
        failure_reason = self._result_failure_reason(result, document)
        if failure_reason:
            raise RuntimeError(f"未提取到有效正文: {failure_reason}")
        return document

    def crawl(self, selected_ids=None, selected_titles=None, limit=0):
        """按单页或整站模式抓取，统一落盘为 Markdown 和 RAG 文件。"""
        if self.crawl_mode == "site":
            results = asyncio.run(self._crawl_site())
            documents = []
            seen_content = set()
            failed_pages = []
            blocked_pages = []
            empty_pages = []
            duplicate_pages = []
            for index, result in enumerate(results, 1):
                if not getattr(result, "success", False):
                    failed_pages.append(
                        {
                            "url": getattr(result, "url", ""),
                            "error": getattr(result, "error_message", "访问失败"),
                        }
                    )
                    continue
                document = self._document_from_result(result, self.url)
                failure_reason = self._result_failure_reason(result, document)
                if failure_reason:
                    print(f"⚠️ 跳过 {document.metadata['url']}: {failure_reason}")
                    blocked_pages.append(
                        {"url": document.metadata["url"], "reason": failure_reason}
                    )
                    continue
                if document.markdown.strip():
                    content_fingerprint = hashlib.sha1(
                        document.markdown.strip().encode("utf-8")
                    ).hexdigest()
                    if content_fingerprint in seen_content:
                        print(f"ℹ️ 跳过重复正文: {document.metadata['url']}")
                        duplicate_pages.append(document.metadata["url"])
                        continue
                    seen_content.add(content_fingerprint)
                    documents.append(document)
                else:
                    empty_pages.append(document.metadata["url"])
                self._notify(index, len(results), f"已处理网页: {document.title}")
            if not documents:
                raise RuntimeError("整站抓取未提取到有效正文")
            self.collection_name = "网页知识库"
            summary = self._save(documents)
            report_path = os.path.join(self.save_dir, "crawl_report.json")
            with open(report_path, "w", encoding="utf-8") as report_file:
                json.dump(
                    {
                        "entry_url": self.entry_url,
                        "scope": "same_host",
                        "discovery_source": self.discovery_source,
                        "discovered_urls": self.discovered_url_count,
                        "attempted_urls": len(results),
                        "saved_documents": len(documents),
                        "max_pages": self.max_pages,
                        "max_depth": self.max_depth,
                        "failed_pages": failed_pages,
                        "blocked_pages": blocked_pages,
                        "empty_pages": empty_pages,
                        "duplicate_pages": duplicate_pages,
                    },
                    report_file,
                    ensure_ascii=False,
                    indent=2,
                )
            print(f"📋 抓取报告: {report_path}")
            return summary

        stubs = self.list_documents()
        self._notify(0, 1, f"正在访问网页: {self.url}")
        document = self.fetch_document(stubs[0])
        self._notify(1, 1, "正文提取与 Markdown 清洗完成")
        return self._save([document])
