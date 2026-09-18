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
            "https://docs.example.test/unrelated/section",
        )
        self.assertEqual(crawler._normalize_candidate_url("https://other.test/x"), "")

    def test_short_challenge_shell_is_rejected(self):
        document = CrawledDocument(
            id="1",
            title="s",
            category="网页",
            html="",
            updated_at="",
            metadata={},
            markdown="环境异常，完成验证后即可继续访问。去验证",
        )
        self.assertIn("验证/拦截", WebCrawler._blocked_page_reason(document))


if __name__ == "__main__":
    unittest.main()
