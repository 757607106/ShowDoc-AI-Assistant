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
from types import SimpleNamespace
from pathlib import Path
from importlib.metadata import version
from xml.etree import ElementTree

import requests

from common.converter import (
    ensure_markdown_resources,
    extract_html_resources,
    write_jsonl,
    validate_canonical_markdown,
)
from common.quality import assess_documents
from crawlers.base import BaseCrawler, CrawledDocument, DocumentStub, CrawlCancelled
from crawlers.web_adapters import describe_web_strategy, resolve_web_adapter
from crawlers.web_discovery import infer_pagination_plans, paginate_plan


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
        self.discovery_details = {}
        self._api_documents = []
        self._validated_network_origins = set()
        self._structured_markdown_generator = None
        super().__init__(
            save_dir,
            progress_callback=progress_callback,
            pipeline_mode=pipeline_mode,
        )
        self.collection_name = "网页知识库"
        self.adapter = resolve_web_adapter(
            self.url,
            max_documents=self.max_pages,
            progress_callback=self._notify,
        )

    def strategy_info(self):
        return describe_web_strategy(self.url)

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
        except socket.gaierror as exc:
            raise ValueError("目标域名无法解析，已阻止访问") from exc

        for address in addresses:
            try:
                ip = ipaddress.ip_address(address)
            except ValueError:
                continue
            if not ip.is_global:
                raise ValueError("出于安全原因，不允许访问本机或内网地址")
        return url

    def list_documents(self):
        if self.crawl_mode == "site" and self.adapter:
            return self.adapter.list_documents()
        parsed = urllib.parse.urlsplit(self.url)
        title = parsed.path.rstrip("/").split("/")[-1] or parsed.netloc
        return [DocumentStub(self._document_id, title, "网页")]

    def _run_config(self, deep_crawl_strategy=None, dynamic_discovery=False):
        from crawl4ai import CacheMode, CrawlerRunConfig
        from crawl4ai.content_filter_strategy import PruningContentFilter
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=1,
            verbose=False,
            check_robots_txt=True,
            excluded_tags=["nav", "script", "style"],
            excluded_selector=(
                "[role='navigation'], [role='search'], "
                ".sidebar, #sidebar, .breadcrumb, #breadcrumb"
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
        if dynamic_discovery:
            config.capture_network_requests = True
            config.delay_before_return_html = float(
                os.getenv("WEB_CRAWLER_DISCOVERY_WAIT", "1.2")
            )
            click_limit = max(
                0, int(os.getenv("WEB_CRAWLER_LOAD_MORE_CLICKS", "6"))
            )
            config.js_code = f"""
                (async () => {{
                    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
                    const labels = /^(加载更多|显示更多|继续加载|load more|show more)$/i;
                    let clicked = 0;
                    for (let round = 0; round < {click_limit}; round += 1) {{
                        window.scrollTo(0, document.body.scrollHeight);
                        await sleep(350);
                        const candidates = Array.from(document.querySelectorAll(
                            'button, a, [role="button"]'
                        ));
                        const target = candidates.find((element) => {{
                            const text = (element.textContent || '').trim();
                            const style = window.getComputedStyle(element);
                            return labels.test(text) && style.display !== 'none' &&
                                style.visibility !== 'hidden' && !element.disabled;
                        }});
                        if (!target) break;
                        const before = document.body.innerText.length;
                        target.click();
                        clicked += 1;
                        await sleep(700);
                        if (document.body.innerText.length <= before && round > 0) break;
                    }}
                    return {{
                        clicked,
                        routes: Array.from(new Set(window.__crawlerRoutes || [])),
                    }};
                }})()
            """
        return config

    @staticmethod
    def _browser_config():
        from crawl4ai import BrowserConfig

        return BrowserConfig(
            headless=True,
            enable_stealth=True,
            user_agent_mode="random",
            viewport_width=1440,
            viewport_height=900,
            init_scripts=[
                """
                (() => {
                    if (window.__crawlerRouteCaptureInstalled) return;
                    window.__crawlerRouteCaptureInstalled = true;
                    window.__crawlerRoutes = window.__crawlerRoutes || [];
                    const record = (value) => {
                        if (typeof value !== 'string' || !value.trim()) return;
                        try {
                            const url = new URL(value, window.location.href);
                            if (url.origin === window.location.origin) {
                                window.__crawlerRoutes.push(url.href);
                            }
                        } catch (_) {}
                    };
                    const originalOpen = window.open;
                    window.open = function(url, ...args) {
                        record(url);
                        return originalOpen.call(this, url, ...args);
                    };
                    for (const method of ['pushState', 'replaceState']) {
                        const original = history[method];
                        history[method] = function(state, title, url) {
                            record(url);
                            return original.call(this, state, title, url);
                        };
                    }
                    document.addEventListener('click', (event) => {
                        const element = event.target && event.target.closest
                            ? event.target.closest('[href], [data-href], [data-url], [data-route], [to]')
                            : null;
                        if (!element) return;
                        record(
                            element.getAttribute('href') ||
                            element.getAttribute('data-href') ||
                            element.getAttribute('data-url') ||
                            element.getAttribute('data-route') ||
                            element.getAttribute('to')
                        );
                    }, true);
                })();
                """
            ],
            verbose=False,
        )

    async def _guard_browser(self, crawler):
        async def guard(page, context, **kwargs):
            if getattr(context, "_knowledge_network_guard", False):
                return page
            async def route_request(route):
                url = route.request.url
                scheme = urllib.parse.urlsplit(url).scheme.lower()
                if scheme in {"about", "blob", "data"}:
                    await route.continue_()
                    return
                if scheme not in {"http", "https"}:
                    await route.abort()
                    return
                parts = urllib.parse.urlsplit(url)
                origin = (parts.scheme.lower(), (parts.hostname or "").lower(), parts.port)
                if origin in self._validated_network_origins:
                    await route.continue_()
                    return
                try:
                    await asyncio.to_thread(self.validate_url, url)
                except ValueError:
                    await route.abort()
                    return
                self._validated_network_origins.add(origin)
                await route.continue_()
            await context.route("**/*", route_request)
            context._knowledge_network_guard = True
            return page
        crawler.crawler_strategy.set_hook("on_page_context_created", guard)

    async def _crawl(self):
        from crawl4ai import AsyncWebCrawler

        async with AsyncWebCrawler(config=self._browser_config()) as crawler:
            await self._guard_browser(crawler)
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
        class PublicSession(requests.Session):
            def send(self, request, **kwargs):
                # Session redirects pass through send again, including API replay.
                WebCrawler.validate_url(request.url)
                return super().send(request, **kwargs)

        session = PublicSession()
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

        sitemap_urls = await asyncio.to_thread(self._discover_sitemap_urls)
        seeds = [self.url, self.site_base_url, *sitemap_urls]
        queue, queued = deque(), set()
        def enqueue(value, depth):
            url = self._normalize_candidate_url(value)
            if not url or url in queued or (self.max_depth and depth > self.max_depth):
                return
            queued.add(url)
            queue.append((url, depth))
        for seed in seeds:
            enqueue(seed, 0)
        os.makedirs(self.save_dir, exist_ok=True)
        spool = Path(self.save_dir) / "crawl_results.jsonl"
        count, api_seen = 0, set()
        self._api_documents = []
        batch_size = max(1, int(os.getenv("WEB_CRAWLER_BATCH_SIZE", "10")))
        async with AsyncWebCrawler(config=self._browser_config()) as crawler:
            await self._guard_browser(crawler)
            with spool.open("w", encoding="utf-8") as output:
                while queue and (not self.max_pages or count + len(self._api_documents) < self.max_pages):
                    remaining = self.max_pages - count - len(self._api_documents) if self.max_pages else batch_size
                    batch = [queue.popleft() for _ in range(min(batch_size, remaining, len(queue)))]
                    self._notify(count, self.max_pages or count + len(queue) + len(batch), "正在抓取站内页面...")
                    results = await crawler.arun_many(
                        urls=[url for url, _ in batch], config=self._run_config(dynamic_discovery=True),
                    )
                    depths = dict(batch)
                    for result_index, result in enumerate(results):
                        count += 1
                        result_url = getattr(result, "url", "")
                        depth = depths.get(result_url, 0)
                        metadata = getattr(result, "metadata", None) or {}
                        metadata["depth"] = depth
                        raw, _ = self._markdown_from_result(result)
                        payload = {"url": result_url, "success": bool(getattr(result, "success", False)),
                                   "error_message": getattr(result, "error_message", ""),
                                   "status_code": getattr(result, "status_code", None), "metadata": metadata,
                                   "html": getattr(result, "html", "") or "",
                                   "cleaned_html": getattr(result, "cleaned_html", "") or "", "markdown": raw}
                        output.write(json.dumps(payload, ensure_ascii=False) + "\n")
                        output.flush()
                        if not payload["success"]:
                            continue
                        for candidate in self._result_candidate_urls(result):
                            enqueue(candidate, depth + 1)
                        remaining = self.max_pages - count - (len(results) - result_index - 1) - len(self._api_documents) if self.max_pages else 0
                        if not self.max_pages or remaining > 0:
                            docs = await asyncio.to_thread(self._discover_api_documents, result, remaining)
                            for doc in docs:
                                if doc.id not in api_seen:
                                    api_seen.add(doc.id)
                                    self._api_documents.append(doc)
                                # Summary/list records can point to real detail pages.
                                if doc.metadata.get("content_completeness") == "summary":
                                    enqueue(doc.metadata.get("url"), depth + 1)
                        self._notify(count, self.max_pages or count + len(queue), f"已抓取 {count} 个页面，待处理 {len(queue)} 个")
        self.discovery_source = "sitemap_and_links" if sitemap_urls else ("dynamic_api" if self._api_documents else "dynamic_link_crawl")
        self.discovered_url_count = len(queued) + len(self._api_documents)
        self.discovery_details.update(rendered_pages=count, api_documents=len(self._api_documents), pending_urls=len(queue))
        def read_results():
            with spool.open(encoding="utf-8") as stream:
                for line in stream:
                    yield SimpleNamespace(**json.loads(line))
        return read_results()

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
        path = candidate.path or "/"
        if not self._looks_like_page_path(path):
            return ""
        tracking_keys = {"fbclid", "gclid", "msclkid", "dclid"}
        query = [(key, value) for key, value in urllib.parse.parse_qsl(candidate.query, keep_blank_values=True)
                 if not key.lower().startswith("utm_") and key.lower() not in tracking_keys]
        fragment = candidate.fragment if candidate.fragment.startswith(("/", "!/")) else ""
        return urllib.parse.urlunsplit((candidate.scheme, candidate.netloc, path,
                                       urllib.parse.urlencode(query), fragment))

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

        execution_result = getattr(result, "js_execution_result", None)

        def append_execution_routes(value):
            if isinstance(value, dict):
                routes = value.get("routes")
                if isinstance(routes, list):
                    values.extend(routes)
                for child in value.values():
                    append_execution_routes(child)
            elif isinstance(value, list):
                for child in value:
                    append_execution_routes(child)

        append_execution_routes(execution_result)

        candidates = []
        seen = set()
        for value in values:
            normalized = self._normalize_candidate_url(urllib.parse.urljoin(getattr(result, "url", None) or self.url, value or ""))
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            candidates.append(normalized)
        return candidates

    @staticmethod
    def _record_value(record, names):
        key_map = {str(key).lower(): key for key in record}
        for name in names:
            original = key_map.get(name.lower())
            value = record.get(original) if original is not None else None
            if value not in (None, "", [], {}):
                return value
        return None

    def _api_record_document(self, record, plan, index):
        title = self._record_value(
            record,
            ("title", "name", "subject", "question", "heading", "label"),
        )
        content_values = []
        for names in (
            ("content", "body", "html", "text", "description"),
            ("summary", "abstract", "excerpt"),
            ("answer", "solution", "detail"),
        ):
            value = self._record_value(record, names)
            if value not in (None, "") and value not in content_values:
                content_values.append(value)
        if not title or not content_values:
            return None

        record_id = self._record_value(
            record, ("id", "uuid", "key", "slug", "document_id", "article_id")
        )
        if record_id in (None, ""):
            encoded = json.dumps(record, ensure_ascii=False, sort_keys=True, default=str)
            record_id = hashlib.sha1(encoded.encode("utf-8")).hexdigest()[:16]
        endpoint_parts = [
            part
            for part in urllib.parse.urlsplit(plan.url).path.rstrip("/").split("/")
            if part
        ]
        endpoint_name = "-".join(endpoint_parts[-2:]) or "data"
        document_id = f"api:{endpoint_name}:{record_id}"
        html_parts = []
        for value in content_values:
            if isinstance(value, (dict, list)):
                escaped = html.escape(
                    json.dumps(value, ensure_ascii=False, indent=2, default=str)
                )
                html_parts.append(f"<pre>{escaped}</pre>")
            else:
                text = str(value)
                html_parts.append(
                    text if re.search(r"<\w+[\s>]", text) else f"<p>{html.escape(text)}</p>"
                )
        source_url = self._record_value(record, ("url", "link", "href")) or plan.url
        source_url = urllib.parse.urljoin(self.site_base_url, str(source_url))
        updated = self._record_value(
            record, ("updated_at", "update_time", "updateTime", "created_at", "createTime")
        )
        return CrawledDocument(
            id=document_id,
            title=str(title).strip(),
            category=f"接口内容/{endpoint_name or '数据'}",
            content="".join(html_parts),
            updated_at=str(updated or datetime.now().isoformat(timespec="seconds")),
            metadata={
                **record,
                "url": source_url,
                "discovery": "captured_api",
                "content_completeness": "unknown" if self._record_value(record, ("content", "body", "html", "text", "answer", "solution", "detail")) else "summary",
                "api_endpoint": plan.url,
                "api_record_index": index,
            },
            source_format="html",
        )

    def _convert_html_document(self, document):
        return self.convert_document(document)

    def _discover_api_documents(self, result, remaining_limit=0):
        events = getattr(result, "network_requests", None) or []
        plans = infer_pagination_plans(events, self.url)
        documents = []
        reports = []
        session = self._http_session()
        if not hasattr(self, "_visited_api_plans"):
            self._visited_api_plans = set()
        try:
            for plan in plans:
                parts = urllib.parse.urlsplit(plan.url)
                query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if k != plan.page_key]
                key = (plan.method, parts.netloc, parts.path, tuple(query),
                       json.dumps({k: v for k, v in plan.body.items() if k != plan.page_key}, sort_keys=True))
                if key in self._visited_api_plans:
                    continue
                self._visited_api_plans.add(key)
                remaining = remaining_limit - len(documents) if remaining_limit else 0
                if remaining_limit and remaining <= 0:
                    break
                try:
                    pagination = paginate_plan(
                        session,
                        plan,
                        max_records=remaining,
                        max_api_pages=max(
                            1, int(os.getenv("WEB_CRAWLER_MAX_API_PAGES", "200"))
                        ),
                    )
                except (requests.RequestException, ValueError, TypeError) as error:
                    reports.append(
                        {
                            "endpoint": plan.url,
                            "reported_total": plan.total,
                            "records_fetched": 0,
                            "documents_created": 0,
                            "requests_made": 0,
                            "complete": False,
                            "stop_reason": f"request_failed: {error}",
                        }
                    )
                    continue
                saved = 0
                for index, record in enumerate(pagination.records, 1):
                    document = self._api_record_document(record, plan, index)
                    if not document:
                        continue
                    self._journal_source(document)
                    try:
                        documents.append(self._convert_html_document(document))
                        saved += 1
                    except CrawlCancelled:
                        raise
                    except Exception as exc:
                        reports.append({"endpoint": plan.url, "document_id": document.id,
                                        "complete": False, "stop_reason": f"conversion_failed: {exc}"})
                reports.append(
                    {
                        "endpoint": plan.url,
                        "reported_total": plan.total,
                        "records_fetched": len(pagination.records),
                        "documents_created": saved,
                        "requests_made": pagination.requests_made,
                        "complete": pagination.complete,
                        "stop_reason": pagination.stop_reason,
                    }
                )
        finally:
            session.close()
        existing_reports = self.discovery_details.setdefault("api_endpoints", [])
        existing_reports.extend(reports)
        return documents

    @staticmethod
    def _markdown_from_result(result):
        markdown_result = getattr(result, "markdown", None)
        if isinstance(markdown_result, str):
            return markdown_result, markdown_result
        if markdown_result is None:
            return "", ""
        raw_markdown = getattr(markdown_result, "raw_markdown", "") or ""
        return raw_markdown, raw_markdown

    def _document_from_result(self, result, fallback_url, fallback_title=None):
        result_url = getattr(result, "url", None) or fallback_url
        parsed = urllib.parse.urlsplit(result_url)
        result_id = hashlib.sha1(result_url.encode("utf-8")).hexdigest()[:16]
        path_title = parsed.path.rstrip("/").split("/")[-1] or parsed.netloc
        stub = DocumentStub(result_id, fallback_title or path_title, "网页")

        metadata = getattr(result, "metadata", None) or {}
        title = metadata.get("title") or stub.title
        original_html = getattr(result, "html", "") or getattr(result, "cleaned_html", "") or ""
        document = CrawledDocument(
            id=stub.id, title=title, category=stub.category, content=original_html,
            updated_at=str(metadata.get("article:modified_time") or metadata.get("dateModified") or "未知"),
            metadata={"url": result_url, "title": title, "depth": metadata.get("depth"),
                      "status_code": getattr(result, "status_code", None),
                      "crawled_at": datetime.now().isoformat(timespec="seconds")},
            source_format="html",
        )
        self._journal_source(document)
        # Use the engine's unpruned Markdown; preserve raw HTML separately.
        raw, _ = self._markdown_from_result(result)
        from common.converter import preserve_html_paragraph_markers
        document.resources = extract_html_resources(getattr(result, "cleaned_html", "") or "", site_base_url=result_url)
        document.raw_markdown = raw
        document.markdown = ensure_markdown_resources(preserve_html_paragraph_markers(raw), document.resources,
                                                      site_base_url=result_url, title=title)
        validate_canonical_markdown(document.markdown, document.resources, title=title)
        document.metadata["conversion"] = {"engine": "crawl4ai", "version": version("crawl4ai")}
        return document

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
        if self.crawl_mode == "site" and self.adapter:
            self.adapter.list_documents()
            if stub.id in self.adapter.record_by_id:
                return self._convert_html_document(self.adapter.fetch_document(stub))
        result = asyncio.run(self._crawl())
        if not getattr(result, "success", False):
            message = getattr(result, "error_message", "未知错误")
            raise RuntimeError(f"Crawl4AI 访问失败: {message}")
        document = self._document_from_result(result, self.url, stub.title)
        failure_reason = self._result_failure_reason(result, document)
        if failure_reason:
            raise RuntimeError(f"未提取到有效正文: {failure_reason}")
        return document

    def _write_crawl_report(self, payload):
        report_path = os.path.join(self.save_dir, "crawl_report.json")
        with open(report_path, "w", encoding="utf-8") as report_file:
            json.dump(payload, report_file, ensure_ascii=False, indent=2)
        print(f"📋 抓取报告: {report_path}")
        return report_path

    @staticmethod
    def _extend_failure_manifest(summary, records):
        existing = []
        if os.path.exists(summary.failed_documents_file):
            with open(summary.failed_documents_file, encoding="utf-8") as stream:
                existing.extend(json.loads(line) for line in stream if line.strip())
        write_jsonl(summary.failed_documents_file, [*existing, *records])

    def _crawl_with_adapter(self, selected_ids=None, selected_titles=None, limit=0):
        info = self.strategy_info()
        self.discovery_source = "adapter"
        self._notify(0, 0, info["message"])
        documents = self.adapter.crawl_documents(selected_ids, selected_titles)
        if limit and limit > 0:
            documents = documents[:limit]
        converted = documents
        for document in documents:
            self._journal_source(document)
        self._convert_all(converted)
        if not converted:
            raise RuntimeError("站点适配器未提取到有效正文")

        reported_total = sum(
            int(stats["reported_total"])
            for stats in self.adapter.stats.values()
            if stats.get("reported_total") is not None
        )
        selected_count = len(selected_ids or selected_titles or [])
        requested_total = (
            selected_count
            or (min(reported_total, self.max_pages) if self.max_pages else reported_total)
        )
        site_coverage = (
            round(min(100.0, sum(bool(doc.markdown) for doc in converted) / reported_total * 100), 2)
            if reported_total
            else None
        )
        scope_completion = (
            round(min(100.0, sum(bool(doc.markdown) for doc in converted) / requested_total * 100), 2)
            if requested_total
            else None
        )
        report = {
            "entry_url": self.entry_url,
            "scope": "same_host_public_content",
            "discovery_source": "adapter",
            "adapter": self.adapter.key,
            "adapter_name": self.adapter.display_name,
            "reported_documents": reported_total,
            "requested_documents": requested_total,
            "saved_documents": sum(bool(doc.markdown) for doc in converted),
            "coverage_percent": site_coverage,
            "requested_scope_completion_percent": scope_completion,
            "max_pages": self.max_pages,
            "categories": self.adapter.stats,
            "notes": [
                "仅采集无需登录即可访问的公开内容",
                "问答正文包含公开回答分页",
            ],
        }
        summary = self._save(converted, assess_documents(converted))
        report_path = self._write_crawl_report(report)
        summary.discovery_strategy = f"adapter:{self.adapter.key}"
        summary.coverage_score = site_coverage
        summary.coverage_report_file = report_path
        return summary

    def crawl(self, selected_ids=None, selected_titles=None, limit=0):
        """按单页或整站模式抓取，统一落盘为 Markdown 和 RAG 文件。"""
        if limit and limit > 0:
            self.max_pages = min(self.max_pages, limit) if self.max_pages else limit
            if self.adapter:
                self.adapter.max_documents = self.max_pages
        if self.crawl_mode == "site":
            if self.adapter:
                return self._crawl_with_adapter(
                    selected_ids=selected_ids,
                    selected_titles=selected_titles,
                    limit=limit,
                )
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
                try:
                    document = self._document_from_result(result, self.url)
                except CrawlCancelled:
                    raise
                except Exception as exc:
                    failed_pages.append({"url": getattr(result, "url", ""), "error": str(exc)})
                    continue
                if selected_ids and document.id not in {str(item) for item in selected_ids}:
                    continue
                if selected_titles and document.title not in set(selected_titles):
                    continue
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
                self._notify(index, self.discovery_details.get("rendered_pages", index), f"已处理网页: {document.title}")

            for document in self._api_documents:
                if selected_ids and document.id not in {str(item) for item in selected_ids}:
                    continue
                if selected_titles and document.title not in set(selected_titles):
                    continue
                content_fingerprint = hashlib.sha1(
                    document.markdown.strip().encode("utf-8")
                ).hexdigest()
                if content_fingerprint in seen_content:
                    duplicate_pages.append(document.metadata.get("url") or document.id)
                    continue
                seen_content.add(content_fingerprint)
                documents.append(document)
            if not documents:
                raise RuntimeError("整站抓取未提取到有效正文")
            self.collection_name = "网页知识库"
            summary = self._save(documents)
            api_reports = self.discovery_details.get("api_endpoints") or []
            api_expected = sum(
                int(item["reported_total"])
                for item in api_reports
                if item.get("reported_total") is not None
            )
            api_saved = sum(int(item.get("documents_created") or 0) for item in api_reports)
            api_saved = sum(doc.id.startswith("api:") for doc in documents)
            coverage = (
                round(min(100.0, api_saved / api_expected * 100), 2)
                if api_expected
                else None
            )
            report_path = self._write_crawl_report(
                {
                    "entry_url": self.entry_url,
                    "scope": "same_host",
                    "discovery_source": self.discovery_source,
                    "discovered_urls": self.discovered_url_count,
                    "attempted_urls": self.discovery_details.get("rendered_pages", 0),
                    "saved_documents": len(documents),
                    "coverage_percent": coverage,
                    "max_pages": self.max_pages,
                    "max_depth": self.max_depth,
                    "discovery_details": self.discovery_details,
                    "failed_pages": failed_pages,
                    "blocked_pages": blocked_pages,
                    "empty_pages": empty_pages,
                    "duplicate_pages": duplicate_pages,
                }
            )
            failure_records = []
            for item in failed_pages:
                failure_records.append({
                    "id": hashlib.sha1(item.get("url", "").encode()).hexdigest()[:16],
                    "title": item.get("url") or "未知网页",
                    "category": "网页",
                    "source_format": "html",
                    "phase": "fetch_or_conversion",
                    "error": item.get("error") or "访问失败",
                    "metadata": {"url": item.get("url")},
                })
            for item in blocked_pages:
                failure_records.append({
                    "id": hashlib.sha1(item["url"].encode()).hexdigest()[:16],
                    "title": item["url"],
                    "category": "网页",
                    "source_format": "html",
                    "phase": "blocked",
                    "error": item["reason"],
                    "metadata": {"url": item["url"]},
                })
            for url in empty_pages:
                failure_records.append({
                    "id": hashlib.sha1(url.encode()).hexdigest()[:16],
                    "title": url,
                    "category": "网页",
                    "source_format": "html",
                    "phase": "conversion",
                    "error": "正文为空",
                    "metadata": {"url": url},
                })
            self._extend_failure_manifest(summary, failure_records)
            summary.failed_documents += len(failed_pages) + len(blocked_pages) + len(empty_pages)
            summary.error_count += sum(not item.get("complete", False) for item in api_reports)
            summary.discovery_strategy = self.discovery_source
            summary.coverage_score = coverage
            summary.coverage_report_file = report_path
            return summary

        stubs = self.list_documents()
        self._notify(0, 1, f"正在访问网页: {self.url}")
        document = self.fetch_document(stubs[0])
        self._notify(1, 1, "正文提取与 Markdown 清洗完成")
        return self._save([document])
