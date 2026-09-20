"""Real Crawl4AI/Chromium regression against a deterministic local HTTP fixture.

Run with RUN_BROWSER_TESTS=1 pytest -q tests/test_web_browser_integration.py.
No external accounts or target-site state are required.
"""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from crawlers.web import WebCrawler


@pytest.mark.skipif(os.getenv('RUN_BROWSER_TESTS') != '1', reason='explicit browser integration run')
def test_sitemap_is_augmented_by_links_and_query_pages(tmp_path, monkeypatch):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            port = self.server.server_port
            pages = {
                '/robots.txt': ('text/plain', 'User-agent: *\nAllow: /\n'),
                '/sitemap.xml': ('application/xml', f'<urlset><url><loc>http://127.0.0.1:{port}/</loc></url></urlset>'),
                '/': ('text/html', '<h1>入口</h1><section class="research-content"><p>仅管理员可删除。</p></section><a href="/detail?page=1">一</a><a href="/detail?page=2">二</a>'),
                '/detail?page=1': ('text/html', '<h1>采购</h1><p>采购单先保存后审核。</p>'),
                '/detail?page=2': ('text/html', '<h1>入库</h1><p>审核后允许入库。</p>'),
            }
            mime, body = pages.get(self.path, ('text/plain', 'not found'))
            if mime == 'text/html':
                # Realistic body size: the engine flags tiny shells as bot blocks.
                body = '<html><article>' + body + '<p>' + ('业务操作应遵循权限控制和审核流程。' * 40) + '</p></article></html>'
            self.send_response(200 if self.path in pages else 404)
            self.send_header('Content-Type', mime + ';charset=utf-8')
            self.end_headers()
            self.wfile.write(body.encode())

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    monkeypatch.setenv('WEB_CRAWLER_ALLOW_PRIVATE_URLS', 'true')
    monkeypatch.setenv('WEB_CRAWLER_LOAD_MORE_CLICKS', '0')
    monkeypatch.setenv('WEB_CRAWLER_DISCOVERY_WAIT', '0.1')
    try:
        crawler = WebCrawler(str(tmp_path), f'http://127.0.0.1:{server.server_port}/', crawl_mode='site', max_pages=3)
        summary = crawler.crawl()
        records = [json.loads(line) for line in Path(summary.rag_documents_file).read_text().splitlines()]
        assert len(records) == 3 and summary.failed_documents == 0
        assert any('仅管理员可删除' in record['content'] for record in records)
        assert {record['metadata']['url'].split('/')[-1] for record in records} >= {'detail?page=1', 'detail?page=2'}
        assert summary.discovery_strategy == 'sitemap_and_links'
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
