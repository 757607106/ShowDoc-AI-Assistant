"""Source capture keeps media references without pretending to transcribe them."""
import json
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from crawlers.base import DocumentStub
from crawlers.cyb import CYBCrawler
from crawlers.tiantong import TiantongCrawler


def records(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def crawler(tmp_path):
    result = CYBCrawler(str(tmp_path))
    result.source_only = True
    result.authenticate = Mock()
    result.pipeline.convert = Mock(side_effect=AssertionError('Capture must not parse content locally'))
    result._items = {
        'tutorial-1': {'title':'视频教程','content':'','contentType':1,'videoUrl':'https://www.bilibili.com/video/example/','coverImage':'tutorial/cover.png'},
        'tutorial-2': {'title':'文字教程','content':'<p>完整操作说明</p>'},
        'tutorial-3': {'title':'真实空文档','content':'','coverImage':'tutorial/empty.png'},
    }
    result.list_documents = lambda: [DocumentStub(key,item['title'],'教程') for key,item in result._items.items()]
    return result


def test_video_reference_survives_source_capture_but_empty_cover_still_fails(tmp_path):
    c = crawler(tmp_path)
    summary = c.crawl()
    assert summary.total_documents == 2 and summary.failed_documents == 1
    assert summary.video_reference_documents == summary.warning_count == 1
    video = next(row for row in records(summary.rag_documents_file) if row['id'] == 'tutorial-1')
    assert 'https://www.bilibili.com/video/example/' in video['content']
    assert c.site_base_url + '/tutorial/cover.png' in video['content']
    assert '尚未采集或解析视频内容' in video['content']
    assert video['metadata']['source_kind'] == 'video_reference'
    assert video['metadata']['media_content_captured'] is False
    assert video['metadata']['content'] == ''
    assert [row['id'] for row in records(summary.failed_documents_file)] == ['tutorial-3']
    assert Path(summary.rag_chunks_file).read_text() == ''
    c.pipeline.convert.assert_not_called()


def test_saved_video_references_recover_without_login_or_source_fetch(tmp_path):
    c = crawler(tmp_path)
    raw = []
    for key in ('tutorial-1','tutorial-2'):
        item = c._items[key]
        raw.append({'id':key,'title':item['title'],'category':'教程','content':item['content'],
                    'metadata':item,'source_format':'html','updated_at':'','source_path':''})
    source = tmp_path / 'source_documents.jsonl'
    source.write_text('\n'.join(json.dumps(row,ensure_ascii=False) for row in raw)+'\n')
    c.authenticate.side_effect = AssertionError('Saved complete capture must not log in again')
    c.fetch_document = Mock(side_effect=AssertionError('Saved source must not be fetched again'))
    summary = c.reprocess_sources(source)
    assert summary.failed_documents == 0 and summary.total_documents == 2
    assert summary.video_reference_documents == 1
    c.authenticate.assert_not_called(); c.fetch_document.assert_not_called()
    again = c.reprocess_sources(source)
    first = next(row for row in records(summary.rag_documents_file) if row['id'] == 'tutorial-1')
    assert first['content'].count('尚未采集或解析视频内容') == 1
    assert again.total_documents == 2


def test_retry_refetches_genuinely_empty_sources_only(tmp_path):
    c = crawler(tmp_path)
    c.crawl()
    original = c.fetch_document
    c._items['tutorial-3']['content'] = '<p>源站补齐的正文</p>'
    c.fetch_document = Mock(wraps=original)
    summary = c.reprocess_sources(tmp_path/'source_documents.jsonl')
    assert summary.failed_documents == 0 and summary.total_documents == 3
    assert [call.args[0].id for call in c.fetch_document.call_args_list] == ['tutorial-3']


@pytest.mark.parametrize('url',['javascript:alert(1)','https://','https://[invalid'])
def test_invalid_video_link_does_not_make_an_empty_source_valid(tmp_path,url):
    c = crawler(tmp_path)
    c._items['tutorial-1']['videoUrl'] = url
    summary = c.crawl(selected_ids=['tutorial-1'])
    assert summary.total_documents == 0 and summary.failed_documents == 1


def test_video_link_changes_affect_source_identity_but_view_counts_do_not(tmp_path):
    c = crawler(tmp_path)
    stub = DocumentStub('tutorial-1','视频教程','教程')
    first = c._source_record(c.fetch_document(stub))
    c._items['tutorial-1']['viewCount'] = 9999
    assert c._source_record(c.fetch_document(stub))['source_sha256'] == first['source_sha256']
    c._items['tutorial-1']['videoUrl'] = 'https://www.bilibili.com/video/updated/'
    assert c._source_record(c.fetch_document(stub))['source_sha256'] != first['source_sha256']


def test_tiantong_attachment_keeps_original_name_and_exact_stored_identity(tmp_path):
    c = TiantongCrawler(str(tmp_path))
    c.source_only = True
    c.pipeline.convert = Mock(side_effect=AssertionError('Capture must not parse or execute an attachment'))
    c._items = {'parent': {'title': '数据库提示说明', 'content': '<p>安装附件中的数据库函数后重试。</p>',
                          'attachments': [{'fileId': 'dec0e211-77d6-405c-bd4a-b806a181e37b', 'name': 'ClearZeroDirect.sql'}]}}
    c.list_documents = lambda: [DocumentStub('parent', '数据库提示说明', '常见提示')]
    stored = 'dec0e211-77d6-405c-bd4a-b806a181e37b_ClearZeroDirect.sql'
    attachment = tmp_path / 'assets' / 'attachments' / stored
    attachment.parent.mkdir(parents=True)
    original = b'-- retained source, never executed\nSELECT 1;'
    attachment.write_bytes(original)
    c._download_attachment = Mock(return_value=f'assets/attachments/{stored}')
    summary = c.crawl()
    child = next(row for row in records(summary.rag_documents_file) if row['metadata'].get('parent_document_id'))
    assert child['id'] == f'parent:attachment:{stored}'
    assert child['source_path'] == f'assets/attachments/{stored}'
    assert child['title'] == child['metadata']['filename'] == 'ClearZeroDirect.sql'
    assert child['metadata']['parent_document_id'] == 'parent'
    assert attachment.read_bytes() == original
    c.pipeline.convert.assert_not_called()


def test_tiantong_attachment_failure_is_partial_and_retry_replaces_old_children(tmp_path):
    c = TiantongCrawler(str(tmp_path))
    c.source_only = True
    c._items = {'parent': {'title': '带附件正文', 'content': '<p>正文</p>', 'attachments': [
        {'fileId': 'a', 'name': 'a.sql'}, {'fileId': 'b', 'name': 'b.sql'}]}}
    c.list_documents = lambda: [DocumentStub('parent', '带附件正文', '常见提示')]
    stored = {key: f'assets/attachments/{key}_{key}.sql' for key in ('a', 'b')}
    for relative in stored.values():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('SELECT 1;')
    attempts = iter([stored['a'], None, stored['a'], stored['b']])
    c._download_attachment = Mock(side_effect=lambda attachment: next(attempts))

    first = c.crawl()
    assert first.total_documents == 1 and first.failed_documents == 1
    assert '附件下载失败' in records(first.failed_documents_file)[0]['error']

    second = c.reprocess_sources(first.source_documents_file)
    captured = records(second.rag_documents_file)
    assert second.failed_documents == 0 and second.total_documents == 3
    assert len({row['id'] for row in captured}) == 3
    assert sum(row['id'] == 'parent:attachment:a_a.sql' for row in captured) == 1
    assert c._download_attachment.call_count == 4


def test_tiantong_malformed_attachment_metadata_is_not_silently_ignored(tmp_path):
    c = TiantongCrawler(str(tmp_path))
    c.source_only = True
    c._items = {'parent': {'title': '正文', 'content': '<p>正文</p>', 'attachments': '{broken'}}
    c.list_documents = lambda: [DocumentStub('parent', '正文', '未分类')]

    summary = c.crawl()

    assert summary.total_documents == 0 and summary.failed_documents == 1
    assert '附件字段不是有效 JSON' in records(summary.failed_documents_file)[0]['error']


def test_failed_attachment_retry_preserves_previous_valid_file(tmp_path):
    c = TiantongCrawler(str(tmp_path))
    existing = tmp_path / 'assets' / 'attachments' / 'a_a.sql'
    existing.parent.mkdir(parents=True)
    existing.write_text('previous-valid-content')
    token = Mock(raise_for_status=Mock(), json=Mock(return_value={
        'code': 200, 'data': {'downloadUrl': 'https://example.test/a.sql'}}))
    download = MagicMock()
    download.__enter__.return_value = Mock(
        raise_for_status=Mock(side_effect=RuntimeError('network failed')), headers={})
    c.session.get = Mock(side_effect=[token, download])

    assert c._download_attachment({'fileId': 'a', 'name': 'a.sql'}) is None

    assert existing.read_text() == 'previous-valid-content'
    assert not Path(str(existing) + '.part').exists()


def test_interrupted_attachment_stream_preserves_previous_valid_file(tmp_path):
    c = TiantongCrawler(str(tmp_path))
    existing = tmp_path / 'assets' / 'attachments' / 'a_a.sql'
    existing.parent.mkdir(parents=True)
    existing.write_text('previous-valid-content')
    token = Mock(raise_for_status=Mock(), json=Mock(return_value={
        'code': 200, 'data': {'downloadUrl': 'https://example.test/a.sql'}}))
    response = MagicMock(headers={}, raise_for_status=Mock())
    def chunks():
        yield b'new-partial-content'
        raise RuntimeError('stream interrupted')
    response.iter_content = Mock(side_effect=lambda _size: chunks())
    download = MagicMock()
    download.__enter__.return_value = response
    c.session.get = Mock(side_effect=[token, download])

    assert c._download_attachment({'fileId': 'a', 'name': 'a.sql'}) is None

    assert existing.read_text() == 'previous-valid-content'
    assert not Path(str(existing) + '.part').exists()
