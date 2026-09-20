import asyncio
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from crawlers.base import CrawledDocument
from crawlers.web import WebCrawler


class WebCrawlerTests(unittest.TestCase):
    def make_crawler(self, **kwargs):
        with patch("crawlers.web.socket.getaddrinfo", return_value=[]):
            return WebCrawler(
                tempfile.mkdtemp(),
                "https://docs.example.test/guide/start",
                **kwargs,
            )

    def test_zero_limits_mean_unlimited(self):
        crawler = self.make_crawler(crawl_mode="site", max_pages=0, max_depth=0)
        self.assertEqual(crawler.max_pages, 0)
        self.assertEqual(crawler.max_depth, 0)

    def test_sitemap_parser_preserves_unicode_urls(self):
        sitemap = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://docs.example.test/中文</loc></url>
        </urlset>""".encode("utf-8")
        root_type, urls = WebCrawler._sitemap_locs(sitemap)
        self.assertEqual(root_type, "urlset")
        self.assertEqual(urls, ["https://docs.example.test/中文"])

    def test_route_discovery_is_same_host_and_field_based(self):
        crawler = self.make_crawler()
        result = SimpleNamespace(
            links={
                "internal": [
                    {"href": "https://docs.example.test/guide/from-anchor"}
                ]
            },
            html=(
                '<script>{\\"href\\":\\"/guide/from-route\\",'
                '\\"url\\":\\"https://other.example/page\\"}</script>'
                "</header><svg></svg><p>/not-a-route</p>"
            ),
        )
        self.assertEqual(
            crawler._result_candidate_urls(result),
            [
                "https://docs.example.test/guide/from-anchor",
                "https://docs.example.test/guide/from-route",
            ],
        )

    def test_normalization_keeps_all_same_host_paths(self):
        crawler = self.make_crawler()
        self.assertEqual(
            crawler._normalize_candidate_url("/unrelated/section?q=1#part"),
            "https://docs.example.test/unrelated/section?q=1",
        )
        self.assertEqual(crawler._normalize_candidate_url("https://other.test/x"), "")

    def test_normalization_keeps_identity_query_and_drops_tracking(self):
        crawler = self.make_crawler()
        self.assertEqual(
            crawler._normalize_candidate_url(
                "/question/list?id=123&utm_source=test&q=ignored#answer"
            ),
            "https://docs.example.test/question/list?id=123&q=ignored",
        )

    def test_nested_javascript_route_results_are_discovered(self):
        crawler = self.make_crawler()
        result = SimpleNamespace(
            links={"internal": []},
            content="",
            js_execution_result={
                "results": [{"result": {"routes": ["/question/list?id=7"]}}]
            },
        )
        self.assertEqual(
            crawler._result_candidate_urls(result),
            ["https://docs.example.test/question/list?id=7"],
        )

    def test_short_challenge_shell_is_rejected(self):
        document = CrawledDocument(
            id="1",
            title="s",
            category="网页",
            content="",
            updated_at="",
            metadata={},
            source_format="html",
            markdown="环境异常，完成验证后即可继续访问。去验证",
        )
        self.assertIn("验证/拦截", WebCrawler._blocked_page_reason(document))

    def test_browser_guard_allows_document_local_urls_and_blocks_file_urls(self):
        crawler = self.make_crawler()

        class Strategy:
            def set_hook(self, name, hook):
                self.name = name
                self.hook = hook

        class Context:
            async def route(self, pattern, handler):
                self.pattern = pattern
                self.handler = handler

        class Route:
            def __init__(self, url):
                self.request = SimpleNamespace(url=url)
                self.action = None

            async def continue_(self):
                self.action = "continue"

            async def abort(self):
                self.action = "abort"

        strategy = Strategy()
        browser = SimpleNamespace(crawler_strategy=strategy)
        asyncio.run(crawler._guard_browser(browser))
        context = Context()
        asyncio.run(strategy.hook(object(), context))

        data_route = Route("data:image/png;base64,AAAA")
        file_route = Route("file:///etc/passwd")
        asyncio.run(context.handler(data_route))
        asyncio.run(context.handler(file_route))

        self.assertEqual(strategy.name, "on_page_context_created")
        self.assertEqual(context.pattern, "**/*")
        self.assertEqual(data_route.action, "continue")
        self.assertEqual(file_route.action, "abort")

    def test_structured_api_html_uses_markdown_tables_and_code_blocks(self):
        crawler = self.make_crawler(pipeline_mode="crawl4ai")
        document = CrawledDocument(
            id="table-1",
            title="字段说明",
            category="接口内容",
            content=(
                "<h2>字段</h2><table><tr><th>名称</th><th>值</th></tr>"
                "<tr><td>状态</td><td>启用</td></tr></table>"
                "<pre><code>select 1;</code></pre>"
            ),
            updated_at="",
            metadata={},
            source_format="html",
        )

        converted = crawler._convert_html_document(document)

        self.assertIn("| 名称 | 值 |", converted.markdown)
        self.assertIn("```", converted.markdown)


if __name__ == "__main__":
    unittest.main()
