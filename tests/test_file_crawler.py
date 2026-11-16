import json
import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from crawlers.base import BaseCrawler, CrawledDocument, DocumentStub
from crawlers.file import FileCrawler
from crawlers.web import WebCrawler
from common.upload_names import upload_name


def records(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def test_uploaded_file_becomes_independent_task_source(tmp_path, monkeypatch):
    monkeypatch.setenv('GOVERNANCE_DATA_DIR', str(tmp_path))
    source = tmp_path / 'uploads' / 'revision' / 'policy.md'
    source.parent.mkdir(parents=True)
    source.write_text('# 上传政策\n\n付款期限为三十天。')
    crawler = FileCrawler(str(tmp_path / 'job'), [str(source)])
    summary = crawler.crawl()
    saved = records(summary.source_documents_file)[0]
    artifact = Path(summary.output_dir) / saved['source_path']
    assert artifact.read_bytes() == source.read_bytes()
    source.write_text('后续修改')
    assert artifact.read_text() == '# 上传政策\n\n付款期限为三十天。'
    assert '三十天' in records(summary.rag_documents_file)[0]['content']
    assert (Path(summary.output_dir) / 'collection_complete.json').is_file()


def test_upload_path_rejects_external_files_and_symlinks(tmp_path, monkeypatch):
    monkeypatch.setenv('GOVERNANCE_DATA_DIR', str(tmp_path))
    external = tmp_path / 'secret.md'
    external.write_text('secret')
    uploads = tmp_path / 'uploads'
    uploads.mkdir()
    link = uploads / 'link.md'
    link.symlink_to(external)
    for value in (external, link):
        with pytest.raises(ValueError, match='上传目录'):
            FileCrawler(str(tmp_path / 'job'), [str(value)])


def test_same_file_upload_has_stable_identity(tmp_path, monkeypatch):
    monkeypatch.setenv('GOVERNANCE_DATA_DIR', str(tmp_path))
    sources = [tmp_path / 'uploads' / run / 'policy.md' for run in ('one', 'two')]
    for source in sources:
        source.parent.mkdir(parents=True)
        source.write_text('# 政策\n\n相同正文。')
    assert FileCrawler(str(tmp_path / 'job1'), [str(sources[0])]).list_documents()[0].id == FileCrawler(str(tmp_path / 'job2'), [str(sources[1])]).list_documents()[0].id


@pytest.mark.parametrize('path,index,expected', [
    ('uploads/11111111-1111-4111-8111-111111111111/001-guide.md', 0, 'guide.md'),
    ('uploads/11111111-1111-4111-8111-111111111111/001-001-guide.md', 0, '001-guide.md'),
    ('uploads/11111111-1111-4111-8111-111111111111/002-guide.md', 0, '002-guide.md'),
    ('uploads/11111111-1111-4111-8111-111111111111/002-guide.md', 1, 'guide.md'),
    ('uploads/manual/001-guide.md', 0, '001-guide.md'),
    ('outside/11111111-1111-4111-8111-111111111111/001-guide.md', 0, '001-guide.md'),
    ('uploads/11111111111141118111111111111111/001-guide.md', 0, '001-guide.md'),
    ('uploads/11111111-1111-4111-8111-111111111111/001-', 0, '001-'),
])
def test_legacy_upload_names_strip_only_a_proven_platform_prefix(path, index, expected):
    assert upload_name(path, index) == expected


def test_explicit_upload_names_preserve_natural_numbering():
    assert upload_name('uploads/legacy/001-001-guide.md', 0, '001-guide.md') == '001-guide.md'


@pytest.mark.parametrize('mapped', [False, True])
def test_upload_display_names_preserve_source_identity_paths_and_duplicate_files(tmp_path, monkeypatch, mapped):
    monkeypatch.setenv('GOVERNANCE_DATA_DIR', str(tmp_path))
    directory = tmp_path / 'uploads' / '11111111-1111-4111-8111-111111111111'
    directory.mkdir(parents=True)
    names = ['001-guide.md', '同名.md', '同名.md']
    paths = [directory / f'{index + 1:03d}-{name}' for index, name in enumerate(names)]
    for path in paths:
        path.write_bytes(b'# unchanged source')
    crawler = FileCrawler(str(tmp_path / 'job'), [str(path) for path in paths], file_names=names if mapped else None)
    stubs = crawler.list_documents()
    assert [stub.title for stub in stubs] == ['001-guide', '同名', '同名']
    assert len({stub.id for stub in stubs}) == 3
    for stub, path, name in zip(stubs, paths, names):
        assert stub.id == hashlib.sha256(path.name.encode() + b'\0' + path.read_bytes()).hexdigest()[:24]
        document = crawler.fetch_document(stub)
        assert document.metadata['filename'] == name
        assert document.source_path == f'sources/{stub.id}_{path.name}'
        assert (Path(crawler.save_dir) / document.source_path).read_bytes() == path.read_bytes()


def test_upload_name_mapping_must_align_with_paths(tmp_path):
    with pytest.raises(ValueError, match='名称数量不一致'):
        FileCrawler(str(tmp_path / 'job'), ['unused.md'], file_names=[])


def test_failed_binary_conversion_keeps_exact_source(tmp_path, monkeypatch):
    monkeypatch.setenv('GOVERNANCE_DATA_DIR', str(tmp_path))
    source = tmp_path / 'uploads' / 'unsupported.zip'
    source.parent.mkdir()
    source.write_bytes(b'PK\x03\x04unsupported binary source\x00\xff')
    summary = FileCrawler(str(tmp_path / 'job'), [str(source)]).crawl()
    assert summary.failed_documents == 1 and summary.total_documents == 0
    failure = records(summary.failed_documents_file)[0]
    assert failure['error']
    assert (Path(summary.output_dir) / failure['source_path']).read_bytes() == source.read_bytes()


def test_attachment_is_parsed_with_parent_provenance(tmp_path):
    crawler = BaseCrawler(str(tmp_path))
    crawler.list_documents = lambda: [DocumentStub('parent', '采购指南', '指南')]
    crawler.fetch_document = lambda _: CrawledDocument('parent', '采购指南', '指南', '<p>请参考附件政策。</p>', '', {}, 'html')
    attachment = tmp_path / 'assets' / 'attachments' / 'policy.md'
    attachment.parent.mkdir(parents=True)
    attachment.write_text('# 附件政策\n\n采购必须经过主管审批。')
    crawler.supplement_resources = lambda doc, resources: {'images': [], 'links': [{'text': '采购政策', 'url': 'assets/attachments/policy.md'}]}
    summary = crawler.crawl()
    documents = records(summary.rag_documents_file)
    child = next(record for record in documents if record['metadata'].get('parent_document_id'))
    assert child['metadata']['parent_document_id'] == 'parent'
    assert child['source_path'] == 'assets/attachments/policy.md'
    assert '主管审批' in child['content']
    assert child['nodes'] and child['docling_path']
    assert len(records(summary.source_documents_file)) == 2


def test_resume_reuses_converted_source_and_fetches_only_failed_or_missing(tmp_path):
    crawler = BaseCrawler(str(tmp_path))
    first = CrawledDocument('1', '已采集', '指南', '# 已采集\n\n已保存的业务正文。', '', {}, 'markdown')
    failed = CrawledDocument('2', '曾失败', '指南', '', '', {'fetch_error': 'timeout'}, 'html')
    crawler._journal_source(first)
    crawler._journal_source(failed)
    crawler.convert_document(first)
    crawler.list_documents = lambda: [DocumentStub(str(i), f'文档{i}', '指南') for i in range(1, 4)]
    fetched = []
    def fetch(stub):
        fetched.append(stub.id)
        return CrawledDocument(stub.id, stub.title, stub.category, f'# 文档{stub.id}\n\n本次采集的业务正文。', '', {}, 'markdown')
    crawler.fetch_document = fetch
    original = crawler.pipeline._converter.convert_string
    def parse(content, **kwargs):
        assert '已保存' not in content
        return original(content, **kwargs)
    with patch.object(crawler.pipeline._converter, 'convert_string', side_effect=parse):
        summary = crawler.reprocess_sources(tmp_path / 'source_documents.jsonl', resume_collection=True)
    assert fetched == ['2', '3']
    assert summary.total_documents == 3 and summary.failed_documents == 0
    assert {item['id'] for item in records(summary.source_documents_file)} == {'1', '2', '3'}
    assert (tmp_path / 'collection_complete.json').is_file()


def test_site_resume_uses_persisted_frontier(tmp_path):
    with patch('crawlers.web.socket.getaddrinfo', return_value=[]):
        crawler = WebCrawler(str(tmp_path), 'https://example.test/docs', crawl_mode='site')
    first = {'url': crawler.url, 'success': True, 'html': '<p>已经采集的页面。</p>', 'metadata': {}, 'status_code': 200}
    (tmp_path / 'crawl_results.jsonl').write_text(json.dumps(first) + '\n')
    next_url = 'https://example.test/next'
    (tmp_path / 'crawl_state.json').write_text(json.dumps({'pending': [[next_url, 1]], 'queued': [crawler.url, next_url], 'count': 1}))
    class Browser:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def arun_many(self, *, urls, config):
            assert urls == [next_url]
            return [SimpleNamespace(url=next_url, success=True, html='<p>新采集的页面。</p>', metadata={}, status_code=200)]
    crawler._guard_browser = AsyncMock()
    crawler._discover_sitemap_urls = lambda: []
    crawler._discover_api_documents = lambda *args: []
    with patch('crawl4ai.AsyncWebCrawler', Browser):
        summary = crawler.reprocess_sources(tmp_path / 'source_documents.jsonl', resume_collection=True)
    assert summary.total_documents == 2
    assert len(records(tmp_path / 'crawl_results.jsonl')) == 2
    assert json.loads((tmp_path / 'crawl_state.json').read_text())['pending'] == []
    assert (tmp_path / 'collection_complete.json').is_file()


def test_site_retry_keeps_incomplete_api_gate_when_network_capture_disappears(tmp_path):
    with patch('crawlers.web.socket.getaddrinfo', return_value=[]):
        crawler = WebCrawler(str(tmp_path), 'https://example.test/docs', crawl_mode='site')
    first = {'url': crawler.url, 'success': True, 'html': '<p>已有完整正文。</p>', 'metadata': {}, 'status_code': 200}
    (tmp_path / 'crawl_results.jsonl').write_text(json.dumps(first) + '\n')
    report = {'endpoint': 'https://example.test/api/list', 'page_url': crawler.url, 'complete': False,
              'reported_total': 10, 'documents_created': 0, 'stop_reason': 'total_mismatch'}
    (tmp_path / 'crawl_state.json').write_text(json.dumps({'pending': [], 'queued': [crawler.url], 'count': 1,
        'discovery_details': {'api_endpoints': [report]}}))
    class Browser:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def arun_many(self, *, urls, config):
            assert urls == [crawler.url]
            return [SimpleNamespace(**first)]
    crawler._guard_browser = AsyncMock()
    crawler._discover_sitemap_urls = lambda: []
    crawler._discover_api_documents = lambda *args: []
    with patch('crawl4ai.AsyncWebCrawler', Browser):
        summary = crawler.reprocess_sources(tmp_path / 'source_documents.jsonl', resume_collection=True)
    assert summary.error_count >= 1
    assert summary.coverage_score == 0
    assert json.loads(Path(summary.coverage_report_file).read_text())['discovery_details']['api_endpoints'][0]['complete'] is False


def test_partial_journal_tail_is_recoverable_but_complete_corruption_is_not(tmp_path):
    crawler = BaseCrawler(str(tmp_path))
    source = CrawledDocument('1', '已保存', '指南', '# 已保存\n\n原文证据。', '', {}, 'markdown')
    crawler._journal_source(source)
    journal = tmp_path / 'source_documents.jsonl'
    with journal.open('ab') as stream:
        stream.write(b'{"id":"partial","content":"\xe4\xb8')
    summary = crawler.reprocess_sources(journal)
    assert summary.total_documents == 1
    with journal.open('ab') as stream:
        stream.write(b'{bad complete record}\n')
    with pytest.raises(ValueError):
        crawler.reprocess_sources(journal)


def test_cyb_cli_displays_retained_source_artifact(monkeypatch, capsys):
    import cyb_rag_md
    from crawlers.base import CrawlSummary
    summary = CrawlSummary('cyb', 1, 0, 1, '/output', source_documents_file='/output/source_documents.jsonl')
    monkeypatch.setattr(cyb_rag_md, 'create_crawler', lambda *args, **kwargs: SimpleNamespace(
        display_name='云创业版', crawl=lambda: summary))
    assert cyb_rag_md.crawl_and_process() is summary
    assert '/output/source_documents.jsonl' in capsys.readouterr().out
