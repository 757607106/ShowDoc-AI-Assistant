"""Keep the source tree through capture, attachments and saved-source recovery."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from common.source_directories import import_directory, validate_import_root_name
from crawlers.base import CrawledDocument, DocumentStub
from crawlers.cyb import CYBCrawler
from crawlers.file import FileCrawler
from crawlers.showdoc import ShowDocCrawler
from crawlers.tiantong import TiantongCrawler
from crawlers.web import WebCrawler


def records(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


@pytest.mark.parametrize('value', ['', '  ', '.', '..', 'a/b', 'a\\b', 'a\x00b', 'a' * 201, None])
def test_invalid_custom_root_is_rejected(value):
    with pytest.raises(ValueError):
        validate_import_root_name(value)


def test_custom_root_trims_space_and_explicit_segments_do_not_split_literal_slashes():
    assert validate_import_root_name(' 云辉煌知识库 ') == '云辉煌知识库'
    assert import_directory('来源', path=['进货/销售'])['path'] == ['进货/销售']


def test_showdoc_capture_keeps_project_and_nested_directories(tmp_path):
    crawler = ShowDocCrawler(str(tmp_path), item_id='399')
    crawler.source_only = True
    menu = {'pages': [{'page_id': 'root', 'page_title': '项目说明'}], 'catalogs': [{
        'cat_name': '进货管理', 'catalogs': [{'cat_name': '报表', 'catalogs': [{
            'cat_name': '进货统计', 'pages': [{'page_id': 'nested', 'page_title': '统计说明'}]}]}]}]}
    crawler._post = lambda api, extra: {'error_code': 0, 'data': (
        {'item_name': '云辉煌知识库', 'menu': menu} if api == '/api/item/info'
        else {'page_id': extra['page_id'], 'page_title': extra['page_id'], 'page_content': '# 完整原文'})}
    crawler.pipeline.convert = Mock(side_effect=AssertionError('No local parsing'))
    stubs = crawler.list_documents()
    assert [stub.directory_path for stub in stubs] == [[], ['进货管理', '报表', '进货统计']]
    result = records(crawler.crawl().rag_documents_file)
    assert {row['id']: row['metadata']['import_directory'] for row in result} == {
        'root': {'root_name': '云辉煌知识库', 'path': []},
        'nested': {'root_name': '云辉煌知识库', 'path': ['进货管理', '报表', '进货统计']}}
    crawler.pipeline.convert.assert_not_called()
    recovered = ShowDocCrawler(str(tmp_path), item_id='399')
    recovered.source_only = True
    recovered.import_root_name = '产品资料'
    recovered._post = Mock(side_effect=AssertionError('Saved directories need no project lookup'))
    again = records(recovered.reprocess_sources(tmp_path / 'source_documents.jsonl').rag_documents_file)
    assert {row['metadata']['import_directory']['root_name'] for row in again} == {'产品资料'}
    assert again[1]['metadata']['import_directory']['path'] == ['进货管理', '报表', '进货统计']


def test_old_showdoc_journal_distinguishes_root_pages_from_a_directory_named_root(tmp_path):
    crawler = ShowDocCrawler(str(tmp_path), item_id='399')
    crawler.source_only = True
    crawler.project_name = '云辉煌知识库'
    crawler._post = Mock(side_effect=AssertionError('The saved source already has its catalog ID'))
    journal = tmp_path / 'source_documents.jsonl'
    raw = [{'id': str(cat_id), 'title': '说明', 'category': '根目录', 'content': '# 完整正文',
            'updated_at': '', 'source_format': 'markdown', 'metadata': {'cat_id': cat_id}}
           for cat_id in (0, '29')]
    journal.write_text('\n'.join(json.dumps(row, ensure_ascii=False) for row in raw) + '\n')
    captured = records(crawler.reprocess_sources(journal).rag_documents_file)
    assert [row['metadata']['import_directory'] for row in captured] == [
        {'root_name': '云辉煌知识库', 'path': []},
        {'root_name': '云辉煌知识库', 'path': ['根目录']}]


def test_failed_old_showdoc_page_reuses_the_refreshed_directory_stub(tmp_path):
    crawler = ShowDocCrawler(str(tmp_path), item_id='399')
    crawler.source_only = True
    journal = tmp_path / 'source_documents.jsonl'
    journal.write_text(json.dumps({'id': 'one', 'title': '说明', 'category': '根目录', 'content': '',
        'updated_at': '', 'source_format': 'markdown', 'metadata': {'cat_id': '29', 'fetch_error': 'timeout'}},
        ensure_ascii=False) + '\n')
    crawler._post = lambda api, extra: {'error_code': 0, 'data': (
        {'item_name': '云辉煌知识库', 'menu': {'catalogs': [{'cat_name': '根目录',
            'pages': [{'page_id': 'one', 'page_title': '说明'}]}]}} if api == '/api/item/info'
        else {'page_id': 'one', 'page_title': '说明', 'cat_id': '29', 'page_content': '# 完整正文'})}
    summary = crawler.reprocess_sources(journal)
    assert summary.failed_documents == 0
    assert records(summary.rag_documents_file)[0]['metadata']['import_directory'] == {
        'root_name': '云辉煌知识库', 'path': ['根目录']}


def test_old_showdoc_root_without_a_catalog_id_is_not_guessed(tmp_path):
    crawler = ShowDocCrawler(str(tmp_path), item_id='399')
    doc = CrawledDocument('one', '说明', '根目录', '# 正文', '', {}, 'markdown')
    with pytest.raises(ValueError, match='缺少目录标识'):
        crawler._source_record(doc)


def test_cyb_and_tiantong_keep_source_categories_and_attachment_directory(tmp_path):
    cyb = CYBCrawler(str(tmp_path / 'cyb'))
    doc = CrawledDocument('one', '业务问答', '常见问题/库存业务', '<p>正文</p>', '', {}, 'html')
    assert cyb._source_record(doc)['metadata']['import_directory'] == {
        'root_name': '管家婆云辉煌创业版', 'path': ['常见问题', '库存业务']}
    crawler = TiantongCrawler(str(tmp_path / 'tiantong'))
    crawler.source_only = True
    crawler._items = {'parent': {'content': '<p>正文</p>', 'attachments': [{'fileId': 'file', 'name': '说明.sql'}]}}
    crawler.list_documents = lambda: [DocumentStub('parent', '说明', '数据库', directory_path=['数据库'])]
    attachment = Path(crawler.save_dir) / 'assets/attachments/说明.sql'
    attachment.parent.mkdir(parents=True)
    attachment.write_text('SELECT 1;')
    crawler._download_attachment = Mock(return_value='assets/attachments/说明.sql')
    captured = records(crawler.crawl().rag_documents_file)
    assert len(captured) == 2
    assert [row['metadata']['import_directory'] for row in captured] == [
        {'root_name': '天通资源管理中心', 'path': ['数据库']}] * 2


def test_cyb_catalog_does_not_promote_fallback_labels_to_source_directories(tmp_path):
    crawler = CYBCrawler(str(tmp_path))
    crawler._fetch_list = lambda endpoint: ([{'id': 'one', 'category': '安装/升级'}, {'id': 'two'}]
                                          if endpoint == '/tutorials' else [{'id': 'three', 'faqTypeId': 'unknown'}])
    assert [stub.directory_path for stub in crawler.list_documents()] == [
        ['使用教程', '安装/升级'], ['使用教程'], ['常见问题']]


def test_uploaded_file_does_not_get_a_duplicate_placeholder_directory(tmp_path):
    uploads = Path(os.environ['GOVERNANCE_DATA_DIR']) / 'uploads'
    uploads.mkdir(parents=True)
    source = uploads / 'guide.txt'
    source.write_text('原始资料')
    crawler = FileCrawler(str(tmp_path / 'file'), [str(source)])
    crawler.source_only = True
    captured = records(crawler.crawl().rag_documents_file)
    assert captured[0]['metadata']['import_directory'] == {'root_name': '上传文件', 'path': []}


@pytest.mark.parametrize('mode', ['page', 'site'])
def test_web_overridden_crawl_keeps_domain_root_without_web_placeholder(tmp_path, mode):
    with patch('crawlers.web.socket.getaddrinfo', return_value=[]):
        crawler = WebCrawler(str(tmp_path), 'https://docs.example.test/guide/start', crawl_mode=mode)
    crawler.source_only = True
    crawler.pipeline.convert = Mock(side_effect=AssertionError('Platform capture must not parse locally'))
    result = SimpleNamespace(success=True, url=crawler.url, html='<h1>业务说明</h1><p>完整原文</p>',
                             metadata={'title': '业务说明'}, status_code=200)
    crawler._crawl = AsyncMock(return_value=result)
    crawler._crawl_site = AsyncMock(return_value=[result])
    captured = records(crawler.crawl().rag_documents_file)
    assert captured[0]['metadata']['import_directory'] == {'root_name': 'docs.example.test', 'path': []}
    crawler.pipeline.convert.assert_not_called()


def test_web_adapter_preserves_its_real_categories(tmp_path):
    with patch('crawlers.web.socket.getaddrinfo', return_value=[]):
        crawler = WebCrawler(str(tmp_path), 'https://docs.example.test/', crawl_mode='site')
    crawler.source_only = True
    document = CrawledDocument('one', '操作说明', '使用教程/上手', '<p>正文</p>', '', {}, 'html')
    crawler.adapter = SimpleNamespace(key='test', display_name='站点适配器', stats={},
                                      crawl_documents=lambda *args: [document])
    captured = records(crawler.crawl().rag_documents_file)
    assert captured[0]['metadata']['import_directory'] == {
        'root_name': 'docs.example.test', 'path': ['使用教程', '上手']}


def test_web_adapter_source_only_coverage_uses_saved_source_content(tmp_path):
    with patch('crawlers.web.socket.getaddrinfo', return_value=[]):
        crawler = WebCrawler(str(tmp_path), 'https://club.cmgrasp.com/', crawl_mode='site')
    crawler.source_only = True
    document = CrawledDocument('question:1', '问题', '社区问答', '<p>完整正文</p>', '', {}, 'html')
    crawler.adapter = SimpleNamespace(
        key='club_cmgrasp', display_name='社区',
        stats={'question': {'reported_total': 1, 'complete': True}},
        crawl_documents=lambda *args: [document],
    )

    summary = crawler.crawl()
    report = json.loads(Path(summary.coverage_report_file).read_text())

    assert summary.total_documents == 1 and summary.error_count == 0
    assert report['saved_documents'] == 1
    assert report['coverage_percent'] == 100.0


def test_web_source_capture_still_rejects_challenge_shells(tmp_path):
    with patch('crawlers.web.socket.getaddrinfo', return_value=[]):
        crawler = WebCrawler(str(tmp_path), 'https://docs.example.test/')
    crawler.source_only = True
    crawler._crawl = AsyncMock(return_value=SimpleNamespace(success=True, url=crawler.url,
        html='<p>环境异常，完成验证后即可继续访问</p>', metadata={'title': 's'}, status_code=200))
    summary = crawler.crawl()
    assert summary.total_documents == 0 and summary.failed_documents == 1
    failed = records(summary.failed_documents_file)[0]
    assert '验证/拦截' in failed['error']
    assert failed['metadata']['import_directory'] == {'root_name': 'docs.example.test', 'path': []}
