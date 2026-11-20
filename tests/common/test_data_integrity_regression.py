"""Losslessness regressions: assert source meaning, not implementation details."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

import app as app_module
from common.quality import assess_documents
from crawlers.base import BaseCrawler, CrawlCancelled, CrawledDocument, DocumentStub
from crawlers.showdoc import ShowDocCrawler
from crawlers.tiantong import TiantongCrawler
from crawlers.web import WebCrawler
from crawlers.web_discovery import PaginationPlan, paginate_plan, pair_network_exchanges


def doc(identifier='1', content='<p>有效业务正文。</p>', title='测试', category='目录'):
    return CrawledDocument(identifier, title, category, content, '', {}, 'html')




def web(tmp_path, **kwargs):
    with patch('crawlers.web.socket.getaddrinfo', return_value=[]):
        return WebCrawler(str(tmp_path), 'https://example.test/docs/start', **kwargs)


























def test_category_collision_cannot_overwrite_documents(tmp_path):
    c = BaseCrawler(str(tmp_path))
    docs = [doc('1', category='A/B'), doc('2', category='A_B')]
    c._convert_all(docs)
    c._save(docs)
    assert len(list((tmp_path / 'A_B').glob('*.md'))) == 2, [d.metadata.get('conversion_error') for d in docs]


def test_invalid_document_isolated_and_raw_source_retained(tmp_path):
    c = BaseCrawler(str(tmp_path))
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
    c = BaseCrawler(str(tmp_path), progress_callback=cancel)
    with pytest.raises(CrawlCancelled):
        c._convert_all([doc()])


@pytest.mark.parametrize('ids,titles', [(['missing'], None), (['1', 'missing'], None), (None, ['测试', '不存在的标题'])])
def test_missing_selected_document_fails_before_partial_collection(tmp_path, ids, titles):
    crawler = BaseCrawler(str(tmp_path))
    crawler.list_documents = lambda: [DocumentStub('1', '测试', '目录')]
    (tmp_path / 'collection_complete.json').write_text('{"previous_run": true}\n')
    with patch.object(crawler, 'fetch_document') as fetch:
        with pytest.raises(ValueError, match='采集范围不完整'):
            crawler.crawl(selected_ids=ids, selected_titles=titles)
        fetch.assert_not_called()
    assert not (tmp_path / 'collection_complete.json').exists()




def test_empty_quality_is_zero():
    assert assess_documents([])['summary']['quality_score'] == 0
    assert assess_documents([doc()])['summary']['quality_score'] == 0


@pytest.mark.parametrize('key', ['tiantong','cyb'])
def test_platform_preview_uses_current_content_contract(tmp_path, key, authenticated_client):
    c = BaseCrawler(str(tmp_path))
    c.list_documents = lambda: [DocumentStub('1', '测试', '目录')]
    c.fetch_document = lambda _: doc()
    with patch('webapi.material.create_crawler', return_value=c):
        response = authenticated_client.get(f'/entries/{key}/preview?doc_id=1')
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




def test_showdoc_detail_field_fallback_is_recorded(tmp_path):
    crawler = ShowDocCrawler(str(tmp_path), item_id="412")
    crawler._post = lambda path, extra: {
        "error_code": 0,
        "data": {
            "page_id": "p1",
            "page_title": "字段回退",
            "content": "## 正文\n\n字段回退正文。",
        },
    }

    document = crawler.fetch_document(DocumentStub("p1", "字段回退", "目录"))

    assert document.content == "## 正文\n\n字段回退正文。"
    assert document.source_format == "markdown"
    assert document.metadata["content_source_field"] == "content"
    assert document.metadata["content_fetch_status"] == "ok"




def test_tiantong_short_pages_continue_until_reported_total(tmp_path):
    responses = [
        {'code':200,'data':{'total':2,'list':[{'id':'1','title':'一'}]}},
        {'code':200,'data':{'total':2,'list':[{'id':'2','title':'二'}]}},
    ]
    c = TiantongCrawler(str(tmp_path),page_size=50)
    with patch('crawlers.tiantong.requests.Session.get',side_effect=[SimpleNamespace(raise_for_status=lambda:None,json=lambda p=p:p) for p in responses]) as get:
        assert len(c.list_documents()) == 2
        assert get.call_count == 2


def test_tiantong_empty_list_row_fetches_detail_content(tmp_path):
    c = TiantongCrawler(str(tmp_path))
    c._items["empty-row"] = {
        "id": "empty-row",
        "title": "详情正文",
        "categoryName": "教程",
        "content": "",
    }
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {
            "code": 200,
            "data": {
                "id": "empty-row",
                "content": "<p>详情接口返回的正文。</p>",
            },
        },
    )
    with patch("crawlers.tiantong.requests.Session.get", return_value=response) as get:
        document = c.fetch_document(DocumentStub("empty-row", "详情正文", "教程"))

    assert get.call_count == 1
    assert document.content == "<p>详情接口返回的正文。</p>"
    assert document.metadata["content_source"] == "detail"
    assert document.metadata["content_fetch_status"] == "ok"


def test_tiantong_preview_can_fetch_detail_without_listing_entire_directory(tmp_path):
    c = TiantongCrawler(str(tmp_path))
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {'code': 200, 'data': {
            'id': 'direct', 'title': '直接预览', 'categoryName': '教程', 'content': '<p>正文</p>'}},
    )
    with patch('crawlers.tiantong.requests.Session.get', return_value=response) as get:
        document = c.fetch_document(DocumentStub('direct', '占位', '未分类'))

    assert get.call_count == 1
    assert document.title == '直接预览' and document.category == '教程'
    assert document.content == '<p>正文</p>'


def test_tiantong_duplicate_page_stops_with_explicit_failure(tmp_path):
    payload = {'code':200,'data':{'total':2,'list':[{'id':'1','title':'一'}]}}
    c = TiantongCrawler(str(tmp_path))
    with patch('crawlers.tiantong.requests.Session.get',return_value=SimpleNamespace(raise_for_status=lambda:None,json=lambda:payload)):
        with pytest.raises(RuntimeError,match='分页重复'):
            c.list_documents()




def test_web_empty_result_does_not_abort_other_pages(tmp_path):
    c = web(tmp_path, crawl_mode='site')
    def result(url, markdown):
        return SimpleNamespace(success=True,url=url,metadata={'title':'网页'},markdown=markdown,html=f'<p>{markdown}</p>',status_code=200)
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
