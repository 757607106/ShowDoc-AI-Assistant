"""Losslessness regressions: assert source meaning, not implementation details."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from markdown_it import MarkdownIt

import app as app_module
from common.converter import (
    MarkdownValidationError,
    RAGContentPipeline,
    clean_markdown_for_rag,
    extract_markdown_resources,
    normalize_document_markdown,
    normalize_resource_url,
    split_markdown_sections_for_rag,
    validate_canonical_markdown,
)
from common.quality import assess_documents
from crawlers.base import BaseCrawler, CrawlCancelled, CrawledDocument, DocumentStub
from crawlers.tiantong import TiantongCrawler
from crawlers.web import WebCrawler
from crawlers.web_discovery import PaginationPlan, paginate_plan, pair_network_exchanges


def doc(identifier='1', content='<p>有效业务正文。</p>', title='测试', category='目录'):
    return CrawledDocument(identifier, title, category, content, '', {}, 'html')


def convert(content, source='markdown', mode='builtin', resources=None):
    return RAGContentPipeline(mode=mode, site_base_url='https://example.test/docs/page').convert([
        dict(id='1', title='文档', content=content, source_format=source, resources=resources or {})
    ])['1'].markdown


def web(tmp_path, **kwargs):
    with patch('crawlers.web.socket.getaddrinfo', return_value=[]):
        return WebCrawler(str(tmp_path), 'https://example.test/docs/start', **kwargs)


@pytest.mark.parametrize('mode', ['builtin', 'crawl4ai', 'auto'])
def test_html_literal_dash_does_not_create_setext_heading(mode):
    # Reduced from the real incident: an image/text paragraph followed by a literal '-'.
    source = '<p><img src="https://example.test/a.png">123456</p><p><span>-</span></p><p>下一步</p>'
    result = convert(source, source='html', mode=mode)
    assert '123456' in result and '下一步' in result
    assert not any(t.type == 'heading_open' for t in MarkdownIt().parse(result))
    validate_canonical_markdown(result)


def test_native_setext_and_nested_headings_are_legal():
    result = convert('章节\n====\n\n正文\n\n> ## 引用内标题\n> 引用内容')
    assert '## 章节' in result
    assert '> ## 引用内标题' in result


def test_nested_fence_code_and_indented_code_are_unchanged():
    source = '````markdown\n```python\n# 示例\n[x](relative)\n```\n````\n\n    # 缩进代码'
    assert convert(source) == source
    chunks = split_markdown_sections_for_rag(source, 200, 10)
    assert all(not c.section_path for c in chunks)


def test_hardbreak_and_code_trailing_spaces_survive():
    source = '第一行  \n第二行\n\n```text\nline  \n\n\nend\n```'
    assert clean_markdown_for_rag(source) == source


def test_sibling_heading_relationship_survives_gap_repair():
    result = normalize_document_markdown('## A\n\n#### B\n\nB内容\n\n#### C\n\nC内容')
    assert '### B' in result and '### C' in result
    assert '#### C' not in result
    assert split_markdown_sections_for_rag(result)[-1].section_path == ('A', 'C')


def test_relative_urls_use_document_directory_and_preserve_encoded_slash():
    assert normalize_resource_url('images/a.png', 'https://example.test/docs/guide/') == 'https://example.test/docs/guide/images/a.png'
    assert normalize_resource_url('a%2Fb', 'https://example.test/docs/') == 'https://example.test/docs/a%2Fb'
    result = convert('[阅读][ref]\n\n[ref]: next.html')
    assert extract_markdown_resources(result)['links'][0]['url'] == 'https://example.test/docs/next.html'


@pytest.mark.parametrize('mode', ['builtin', 'crawl4ai'])
def test_spanning_table_keeps_cell_relationships(mode):
    result = convert('<table><tr><th>区域</th><th>项目</th></tr><tr><td rowspan="2">华东</td><td>A</td></tr><tr><td>B</td></tr></table>', 'html', mode)
    assert 'rowspan="2"' in result and '<td>B</td>' in result


def test_builtin_quote_preserves_both_paragraphs():
    result = convert('<blockquote><p>第一段</p><p>第二段</p></blockquote>', 'html')
    assert '> 第一段' in result and '> 第二段' in result


def test_long_fenced_code_chunks_are_independently_parseable():
    source = '## 示例\n\n```python\n' + 'print(1)\n' * 40 + '```'
    chunks = split_markdown_sections_for_rag(source, max_chars=100, overlap=10)
    assert len(chunks) > 1
    assert all(len(c.content) <= 100 for c in chunks)
    assert sum(c.content.count('print(1)') for c in chunks) == 40
    for chunk in chunks:
        validate_canonical_markdown(chunk.content)


def test_long_tables_repeat_headers_and_preserve_all_rows():
    source = '| 编号 | 值 |\n| --- | --- |\n' + '\n'.join(f'| {i} | 业务数据 |' for i in range(30))
    chunks = split_markdown_sections_for_rag(source, max_chars=100, overlap=10)
    assert len(chunks) > 1
    assert all(c.content.startswith('| 编号 | 值 |') for c in chunks)
    assert sum(c.content.count('业务数据') for c in chunks) == 30


def test_invalid_fence_still_rejected():
    with pytest.raises(MarkdownValidationError):
        validate_canonical_markdown('## 示例\n\n```python\nx=1')


def test_resource_in_code_does_not_satisfy_actual_link():
    result = convert('`https://example.test/image.png`', resources={'images': [{'url': 'https://example.test/image.png', 'alt': '图'}]})
    assert extract_markdown_resources(result)['images']


def test_category_collision_cannot_overwrite_documents(tmp_path):
    c = BaseCrawler(str(tmp_path), pipeline_mode='builtin')
    docs = [doc('1', category='A/B'), doc('2', category='A_B')]
    c._convert_all(docs)
    c._save(docs)
    assert len(list((tmp_path / 'A_B').glob('*.md'))) == 2


def test_invalid_document_isolated_and_raw_source_retained(tmp_path):
    c = BaseCrawler(str(tmp_path), pipeline_mode='builtin')
    docs = [doc('ok'), doc('empty', '<div></div>')]
    c._convert_all(docs)
    summary = c._save(docs)
    assert summary.total_documents == 1 and summary.failed_documents == 1
    sources = [json.loads(x) for x in Path(summary.source_documents_file).read_text().splitlines()]
    assert {d['id'] for d in sources} == {'ok', 'empty'}
    assert next(d for d in sources if d['id'] == 'empty')['content'] == '<div></div>'
    assert Path(tmp_path / 'failed_documents.jsonl').read_text()


def test_progress_cancellation_is_not_swallowed(tmp_path):
    def cancel(*args):
        raise CrawlCancelled('cancel')
    c = BaseCrawler(str(tmp_path), pipeline_mode='auto', progress_callback=cancel)
    with pytest.raises(CrawlCancelled):
        c._convert_all([doc()])


def test_fallback_is_per_document_and_auditable():
    from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
    original = DefaultMarkdownGenerator.generate_markdown
    def generate(self, html, **kw):
        if '降级样例' in html:
            raise RuntimeError('engine test error')
        return original(self, html, **kw)
    records = [dict(id=str(i),title='例子',content=f'<p>{body}</p>',source_format='html',resources={}) for i,body in enumerate(['正常正文', '降级样例'])]
    with patch.object(DefaultMarkdownGenerator, 'generate_markdown', generate):
        result = RAGContentPipeline(mode='auto').convert(records)
    assert result['0'].engine == 'crawl4ai'
    assert result['1'].engine == 'builtin' and result['1'].fallback_reason


def test_empty_quality_is_zero():
    assert assess_documents([])['summary']['quality_score'] == 0
    assert assess_documents([doc()])['summary']['quality_score'] == 0


@pytest.mark.parametrize('key', ['tiantong','cyb'])
def test_platform_preview_uses_current_content_contract(tmp_path, key):
    c = BaseCrawler(str(tmp_path), pipeline_mode='builtin')
    c.list_documents = lambda: [DocumentStub('1', '测试', '目录')]
    c.fetch_document = lambda _: doc()
    with patch('app.create_crawler', return_value=c):
        response = app_module.app.test_client().get(f'/entries/{key}/preview?doc_id=1')
    assert response.status_code == 200
    assert '有效业务正文' in response.json['content']


def test_url_identity_preserves_pagination_language_and_hash_routes(tmp_path):
    c = web(tmp_path)
    for first, second in [('/list?page=1','/list?page=2'),('/doc?lang=en','/doc?lang=zh'),('/#/doc/1','/#/doc/2')]:
        assert c._normalize_candidate_url(first) != c._normalize_candidate_url(second)
    assert c._normalize_candidate_url('/doc?utm_source=abc&id=1') == 'https://example.test/doc?id=1'


def test_discovered_relative_link_resolves_against_current_page(tmp_path):
    c = web(tmp_path)
    result = SimpleNamespace(url='https://example.test/other/page', links={'internal':[{'href':'child'}]},html='')
    assert c._result_candidate_urls(result) == ['https://example.test/other/child']


def test_unpruned_markdown_is_canonical(tmp_path):
    c = web(tmp_path)
    result = SimpleNamespace(markdown=SimpleNamespace(raw_markdown='权限限制及正文', fit_markdown='正文'))
    assert c._markdown_from_result(result)[1] == '权限限制及正文'
    assert c._run_config().check_robots_txt


def test_real_engine_does_not_delete_research_content(tmp_path):
    from crawl4ai import AsyncWebCrawler
    from crawl4ai.async_crawler_strategy import AsyncHTTPCrawlerStrategy
    c = web(tmp_path)
    async def run():
        async with AsyncWebCrawler(crawler_strategy=AsyncHTTPCrawlerStrategy()) as engine:
            cfg = c._run_config().clone(check_robots_txt=False)
            return await engine.arun(url='raw:<article><section class="research-content"><h2>限制</h2><p>仅管理员可删除</p></section><p>其他正文</p></article>', config=cfg)
    result = asyncio.run(run())
    assert '仅管理员可删除' in result.markdown.raw_markdown


def test_known_total_empty_page_is_incomplete():
    plan = PaginationPlan('https://example.test/api/list?page=1','GET',{}, {},'page',None,('data',),('total',),[{'id':1}],100)
    session = SimpleNamespace(get=lambda *a,**k:SimpleNamespace(raise_for_status=lambda:None,json=lambda:{'data':[],'total':100}))
    result = paginate_plan(session,plan)
    assert not result.complete and result.stop_reason == 'total_mismatch'


def test_network_capture_does_not_pair_ambiguous_post_requests():
    events = [{'event_type':'request','url':'https://example.test/list','post_data':str(i)} for i in range(2)]
    events += [{'event_type':'response','url':'https://example.test/list','status':200,'body':{'text':'{}'}} for _ in range(2)]
    assert not pair_network_exchanges(events)


def test_redirect_request_is_validated_before_send():
    import requests
    session = WebCrawler._http_session()
    with patch.object(WebCrawler,'validate_url',side_effect=ValueError('private')), patch.object(requests.Session,'send') as send:
        with pytest.raises(ValueError):
            session.send(requests.Request('GET','http://127.0.0.1/').prepare())
        send.assert_not_called()
    session.close()


def test_partial_tasks_are_downloadable_and_retryable(tmp_path):
    task = app_module.CrawlerTask('partial-test','tiantong')
    task.status='partial'; task.zip_file=str(tmp_path/'data.zip')
    app_module.tasks.clear(); app_module.tasks[task.task_id]=task
    try:
        assert app_module.task_payload(task)['download_available']
        with patch.object(app_module.threading.Thread,'start'):
            assert app_module.app.test_client().post('/tasks/partial-test/retry').status_code == 200
    finally:
        app_module.tasks.clear()


def test_full_task_packages_valid_documents_and_reports_partial(tmp_path, monkeypatch):
    import zipfile
    monkeypatch.chdir(tmp_path)
    def factory(entry, save_dir, progress_callback, **kwargs):
        c = BaseCrawler(save_dir, progress_callback, pipeline_mode='crawl4ai')
        c.list_documents = lambda: [DocumentStub('ok','有效','目录'), DocumentStub('empty','空源','目录')]
        c.fetch_document = lambda stub: doc(stub.id, '<p>业务流程正文。</p>' if stub.id == 'ok' else '')
        return c
    task = app_module.CrawlerTask('packaging-regression','tiantong')
    with patch.object(app_module, 'create_crawler', factory):
        app_module.run_crawler_task(task)
    assert task.status == 'partial' and task.failed_pages == 1
    assert app_module.task_payload(task)['successful_pages'] == 1
    with zipfile.ZipFile(task.zip_file) as archive:
        assert archive.testzip() is None
        assert len(archive.read('rag_documents.jsonl').splitlines()) == 1
        assert len(archive.read('source_documents.jsonl').splitlines()) == 2
        assert len(archive.read('failed_documents.jsonl').splitlines()) == 1


def test_tiantong_short_pages_continue_until_reported_total(tmp_path):
    responses = [
        {'code':200,'data':{'total':2,'list':[{'id':'1','title':'一'}]}},
        {'code':200,'data':{'total':2,'list':[{'id':'2','title':'二'}]}},
    ]
    c = TiantongCrawler(str(tmp_path),page_size=50)
    with patch('crawlers.tiantong.requests.get',side_effect=[SimpleNamespace(raise_for_status=lambda:None,json=lambda p=p:p) for p in responses]) as get:
        assert len(c.list_documents()) == 2
        assert get.call_count == 2


def test_tiantong_duplicate_page_stops_with_explicit_failure(tmp_path):
    payload = {'code':200,'data':{'total':2,'list':[{'id':'1','title':'一'}]}}
    c = TiantongCrawler(str(tmp_path))
    with patch('crawlers.tiantong.requests.get',return_value=SimpleNamespace(raise_for_status=lambda:None,json=lambda:payload)):
        with pytest.raises(RuntimeError,match='分页重复'):
            c.list_documents()


def test_downloaded_attachment_is_referenced_from_category_directory(tmp_path):
    c = TiantongCrawler(str(tmp_path),pipeline_mode='builtin')
    document = doc()
    document.metadata['attachments'] = [{'fileId':'full-file-id','name':'说明.pdf'}]
    with patch.object(c,'_download_attachment',return_value='assets/attachments/full-file-id_说明.pdf'):
        c._convert_all([document])
        c._save([document])
    markdown = next((tmp_path / '目录').glob('*.md')).read_text()
    assert '../assets/attachments/' in markdown


def test_web_empty_result_does_not_abort_other_pages(tmp_path):
    c = web(tmp_path, crawl_mode='site')
    def result(url, markdown):
        return SimpleNamespace(success=True,url=url,metadata={'title':'网页'},markdown=markdown,html='<p>原始内容</p>',cleaned_html='<p>原始内容</p>',status_code=200)
    c._crawl_site = AsyncMock(return_value=[result('https://example.test/empty',''),result('https://example.test/ok','有效业务正文。')])
    summary = c.crawl()
    assert summary.total_documents == 1 and summary.failed_documents == 1
    assert json.loads(Path(summary.coverage_report_file).read_text())['failed_pages']
    failures = [json.loads(line) for line in Path(summary.failed_documents_file).read_text().splitlines()]
    assert failures[0]['metadata']['url'] == 'https://example.test/empty'


def test_atomic_jsonl_failure_keeps_previous_artifact(tmp_path):
    from common.converter import write_jsonl
    target = tmp_path / 'data.jsonl'
    write_jsonl(target,[{'id':1}])
    with pytest.raises(TypeError):
        write_jsonl(target,[{'id':2}, {'invalid': object()}])
    assert json.loads(target.read_text()) == {'id':1}
