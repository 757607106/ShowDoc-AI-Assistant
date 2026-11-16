"""ContextDBClient 契约测试:请求形状、认证头、错误映射、信封解包(离线 mock)。"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from integrations.contextdb.client import (
    ContextDBClient,
    ContextDBConflictError,
    ContextDBError,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None, text=''):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {'Content-Type': 'application/json'}
        self.text = text or (json.dumps(payload) if payload is not None else '')

    def json(self):
        if self._payload is None:
            raise ValueError('no json')
        return self._payload


class FakeSession:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.requests = []

    def request(self, method, url, json=None, params=None, headers=None, timeout=None, **kwargs):
        self.requests.append({'method': method, 'url': url, 'json': json, 'params': params,
                              'headers': headers, 'files': kwargs.get('files'), 'data': kwargs.get('data')})
        return self.responses.pop(0)

    def post(self, url, json=None, data=None, files=None, headers=None, timeout=None):
        return self.request('POST', url, json=json, params=None, headers=headers, timeout=timeout,
                            files=files, data=data)

    def put(self, url, data=None, files=None, headers=None, timeout=None):
        return self.request('PUT', url, headers=headers, timeout=timeout, files=files, data=data)

    def get(self, url, timeout=None):
        return self.request('GET', url, timeout=timeout)


def make_client(responses):
    client = ContextDBClient(base_url='https://context-database.aliyuncs.com', api_key='ctxdb-test')
    client._session = FakeSession(responses)
    return client, client._session


def test_request_uses_x_api_key_header():
    client, session = make_client([FakeResponse(200, {'status': 'ok'})])
    client.ping()
    headers = session.requests[0]['headers']
    assert headers['X-API-Key'] == 'ctxdb-test'
    assert 'Authorization' not in headers


def test_unified_envelope_unwrapped_to_data():
    client, _ = make_client([FakeResponse(200, {'errorCode': 0, 'errorMessage': None, 'requestId': 'r1', 'data': {'total': 3}})])
    assert client.list_reviews('kb') == {'total': 3}


def test_bare_payload_passthrough():
    client, _ = make_client([FakeResponse(200, {'knowledge_bases': [], 'total': 0})])
    assert client.list_knowledge_bases() == {'knowledge_bases': [], 'total': 0}


def test_library_lookup_uses_one_complete_official_list_without_pagination():
    bases = [{'id': str(index), 'name': str(index)} for index in range(105)]
    client, session = make_client([FakeResponse(200, {'knowledge_bases': bases, 'total': len(bases)})])
    assert client.find_knowledge_base('104') == bases[-1]
    assert len(session.requests) == 1 and session.requests[0]['params'] is None


@pytest.mark.parametrize('method', ['upload', 'update'])
def test_client_does_not_silently_drop_review_override_when_switching_to_multipart(monkeypatch, method):
    client, session = make_client([])
    monkeypatch.setattr('integrations.contextdb.client.os.path.getsize', lambda _: 501 * 1024 * 1024)
    with pytest.raises(ValueError, match='不支持 review_enabled'):
        if method == 'upload':
            client.upload_file('kb', 'large.md', 'unused', review_enabled=False)
        else:
            client.update_file('doc', 'large.md', 'unused', review_enabled=False)
    assert session.requests == []


def test_rename_uses_documented_query_identity_and_name_field():
    client, session = make_client([FakeResponse(200, {'id': 'kb', 'name': '新名称'})])
    assert client.update_knowledge_base('kb', name='新名称')['name'] == '新名称'
    request = session.requests[0]
    assert request['params'] == {'knowledge_base_id': 'kb'}
    assert request['json'] == {'knowledge_base_name': '新名称'}


def test_conflict_error_code_1003():
    client, _ = make_client([FakeResponse(200, {'errorCode': 1003, 'errorMessage': 'COMMON_CONFLICT: boom', 'requestId': 'r2'})])
    try:
        client.create_text_document('kb', 'a.md', 'text')
        raise AssertionError('应当抛出冲突')
    except ContextDBConflictError as exc:
        assert 'COMMON_CONFLICT' in str(exc)
        assert exc.error_code == 1003


def test_http_409_mapped_to_conflict():
    client, _ = make_client([FakeResponse(409, {'detail': 'conflict'})])
    try:
        client.create_text_document('kb', 'a.md', 'text')
        raise AssertionError('应当抛出冲突')
    except ContextDBConflictError:
        pass


def test_fastapi_detail_error_surfaced():
    client, _ = make_client([FakeResponse(401, {'detail': 'X-API-Key header is required.'})])
    try:
        client.ping()
        raise AssertionError('应当抛出错误')
    except ContextDBError as exc:
        assert 'X-API-Key' in str(exc)
        assert exc.status_code == 401


def test_list_documents_serializes_metadata_condition():
    client, session = make_client([FakeResponse(200, {'documents': [], 'total': 0})])
    client.list_documents('kb', metadata_condition={'type': 'job', 'status': 'pending'})
    params = session.requests[0]['params']
    assert json.loads(params['metadata_condition']) == {'type': 'job', 'status': 'pending'}


def test_query_requires_kb_scope():
    client, _ = make_client([])
    try:
        client.query('问题')
        raise AssertionError('未限定知识库应当报错')
    except ValueError:
        pass


def test_query_body_shape():
    client, session = make_client([FakeResponse(200, {'chunks': [], 'total': 0})])
    client.query('固件升级', knowledge_base_ids=['kb1'], top_k=5, knowledge_view='wiki',
                similarity_threshold=0.3, query_rewrite=True)
    body = session.requests[0]['json']
    assert body['question'] == '固件升级'
    assert body['knowledge_base_ids'] == ['kb1']
    assert body['top_k'] == 5 and body['knowledge_view'] == 'wiki'
    assert body['similarity_threshold'] == 0.3 and body['query_rewrite'] is True


def test_review_action_validates_enum():
    client, _ = make_client([])
    try:
        client.review_action('r1', 'explode')
        raise AssertionError('非法 action 应当报错')
    except ValueError:
        pass


def test_batch_review_uses_official_endpoint_and_preserves_partial_results():
    result = {'total': 2, 'succeeded': 1, 'failed': 1, 'results': [
        {'id': 'r1', 'success': True}, {'id': 'r2', 'success': False, 'error': 'state changed'}]}
    client, session = make_client([FakeResponse(200, {'errorCode': 0, 'data': result})])
    assert client.batch_review_action(['r1', 'r2'], 'confirm') == result
    assert session.requests[0]['method'] == 'POST'
    assert session.requests[0]['url'].endswith('/v1/knowledge/reviews/batch')
    assert session.requests[0]['json'] == {'action': 'confirm', 'ids': ['r1', 'r2']}


@pytest.mark.parametrize('ids,action', [
    ([], 'confirm'), (['r'] * 51, 'confirm'), ('r', 'confirm'), ([1], 'confirm'),
    ([' '], 'confirm'), (['r'], 'reject_reupload'), (['r'], ['confirm']),
])
def test_batch_review_rejects_invalid_input_without_requests(ids, action):
    client, session = make_client([])
    with pytest.raises(ValueError):
        client.batch_review_action(ids, action)
    assert session.requests == []


def test_wiki_page_update_sends_original_version():
    client, session = make_client([FakeResponse(200, {'version': 43})])
    assert client.update_wiki_page('kb', 'page', 'content', 42) == {'version': 43}
    assert session.requests[0]['json'] == {
        'knowledge_base_id': 'kb', 'page_id': 'page', 'content': 'content', 'expected_version': 42}


def test_wiki_tree_preserves_parent_filter_and_cursor():
    response = {'items': [{'page_id': 'topic', 'page_type': 'concept'}], 'next_cursor': 'next', 'limit': 2}
    client, session = make_client([FakeResponse(200, response)])
    assert client.list_wiki_pages('kb', parent_page_id='parent', page_type='category', cursor='cursor', limit=2) == response
    assert session.requests[0]['params'] == {'knowledge_base_id': 'kb', 'parent_page_id': 'parent',
                                           'page_type': 'category', 'cursor': 'cursor', 'limit': 2}


def test_mcp_tool_call_parses_text_content():
    inner = json.dumps({'pages': [{'page_id': 'p1', 'title': 'T'}], 'total': 1})
    client, session = make_client([FakeResponse(200, {
        'jsonrpc': '2.0', 'id': 1,
        'result': {'isError': False, 'content': [{'type': 'text', 'text': inner}]},
    })])
    result = client.wiki_search(['kb'], '安装')
    assert result['pages'][0]['page_id'] == 'p1'
    request = session.requests[0]
    assert request['url'].endswith('/v1/mcp')
    assert request['json']['method'] == 'tools/call'
    assert request['json']['params']['name'] == 'knowledge.wiki_search'
    assert request['json']['params']['arguments']['knowledge_base_ids'] == ['kb']
    assert request['headers']['X-API-Key'] == 'ctxdb-test'


def test_upload_file_uses_multipart():
    from tempfile import NamedTemporaryFile
    client, session = make_client([FakeResponse(200, {'id': 'doc-1', 'ingest_status': 'processing'})])
    with NamedTemporaryFile(suffix='.json', delete=False) as handle:
        handle.write(b'{"v": 1}')
        path = handle.name
    try:
        result = client.upload_file('kb', 'big.json', path, file_path='governance/versions',
                                    metadata={'type': 'version'})
        assert result['id'] == 'doc-1'
        request = session.requests[0]
        assert request['files'] is not None and 'file' in request['files']
        assert request['data']['knowledge_base_id'] == 'kb'
        assert json.loads(request['data']['metadata']) == {'type': 'version'}
    finally:
        Path(path).unlink(missing_ok=True)


def test_get_document_accepts_document_id_without_kb_hint():
    client, session = make_client([FakeResponse(200, {'id': 'doc-1', 'source_type': 'text'})])
    client.get_document(None, 'doc-1')
    assert session.requests[0]['params'] == {'document_id': 'doc-1'}


def test_update_file_keeps_name_mime_and_inherits_metadata(tmp_path):
    client, session = make_client([FakeResponse(200, {'id': 'returned-id', 'source_type': 'file'})])
    path = tmp_path / 'source.md'
    path.write_text('# 修订', encoding='utf-8')
    result = client.update_file('doc-1', '原件.md', path, mime_type='text/markdown')
    assert result['id'] == 'returned-id'
    request = session.requests[0]
    assert request['method'] == 'PUT' and request['url'].endswith('/v1/knowledge/files')
    assert request['data'] == {'document_id': 'doc-1'}
    assert request['files']['file'][0] == '原件.md'
    assert request['files']['file'][2] == 'text/markdown'
    assert request['headers']['X-API-Key'] == 'ctxdb-test'


@pytest.mark.parametrize('update', [False, True])
def test_large_file_parts_preserve_bytes_and_use_final_document_id(tmp_path, monkeypatch, update):
    final_id = 'old' if update else 'final'
    client, session = make_client(([FakeResponse(payload={'id': 'old', 'knowledge_base_id': 'kb'})] if update else []) + [
        FakeResponse(200, {'document_id': 'placeholder', 'knowledge_base_id': 'kb',
                           'chunk_size': 4, 'upload_ticket': 'private-ticket'}),
        FakeResponse(200, {'part_number': 1, 'etag': 'one'}),
        FakeResponse(200, {'part_number': 2, 'etag': 'two'}),
        FakeResponse(200, {'document_id': final_id, 'knowledge_base_id': 'kb', 'status': 'processing'}),
        FakeResponse(200, {'id': final_id, 'knowledge_base_id': 'kb', 'ingest_status': 'processing'}),
    ])
    path = tmp_path / 'video.mp4'
    path.write_bytes(b'1234567')
    monkeypatch.setattr('integrations.contextdb.client.os.path.getsize', lambda _: 501 * 1024 * 1024)
    result = (client.update_file('old', path.name, path) if update else
              client.upload_file('kb', path.name, path))
    assert result['id'] == final_id
    sent = session.requests[int(update):]
    init = sent[0]
    assert init['method'] == ('PUT' if update else 'POST')
    assert init['params']['file_name'] == 'video.mp4'
    assert init['params'].get('document_id') == ('old' if update else None)
    assert sent[1]['files']['data'][1] + sent[2]['files']['data'][1] == b'1234567'
    assert sent[3]['json'] == {'parts': [
        {'part_number': 1, 'etag': 'one'}, {'part_number': 2, 'etag': 'two'}]}
    assert sent[3]['headers']['X-Upload-Ticket'] == 'private-ticket'
    assert sent[4]['params']['document_id'] == final_id


@pytest.mark.parametrize('completion_started', [False, True])
def test_multipart_failure_aborts_only_before_completion(tmp_path, completion_started):
    path = tmp_path / 'source.md'
    path.write_text('# source')
    responses = [FakeResponse(payload={'upload_ticket': 'ticket', 'chunk_size': 20, 'knowledge_base_id': 'kb'})]
    if completion_started:
        responses.extend([FakeResponse(payload={'part_number': 1, 'etag': 'one'}),
                          FakeResponse(503, {'detail': 'uncertain complete'})])
    else:
        responses.extend([FakeResponse(400, {'detail': 'invalid part'}),
                          FakeResponse(payload={'status': 'aborted'})])
    client, session = make_client(responses)
    with pytest.raises(ContextDBError):
        client._multipart_file(path.name, path, knowledge_base_id='kb')
    assert len(session.requests) == 3
    assert session.requests[-1]['url'].endswith('/complete' if completion_started else '/abort')


@pytest.mark.parametrize('final', [{'document_id': 123, 'knowledge_base_id': 'kb'},
                                 {'document_id': 'doc', 'knowledge_base_id': 'another-kb'}])
def test_multipart_does_not_accept_unverifiable_completion_identity(tmp_path, final):
    path = tmp_path / 'source.md'
    path.write_text('# source')
    client, session = make_client([
        FakeResponse(payload={'upload_ticket': 'ticket', 'chunk_size': 20, 'knowledge_base_id': 'kb'}),
        FakeResponse(payload={'part_number': 1, 'etag': 'one'}), FakeResponse(payload=final)])
    with pytest.raises(ContextDBError, match='最终文档 ID'):
        client._multipart_file(path.name, path, knowledge_base_id='kb')
    assert len(session.requests) == 3 and session.requests[-1]['url'].endswith('/complete')


@pytest.mark.parametrize('raw', ['# 中文原文'.encode('utf-8'), b'\xff\xfe\x00a', b'\x00binary'])
def test_download_document_text_never_replaces_invalid_original_bytes(raw):
    from unittest.mock import Mock
    response = Mock(content=raw)
    client, session = make_client([
        FakeResponse(200, {'id': 'doc-1', 'download_url': 'https://signed.example/source'}), response])
    if raw.startswith(b'#'):
        assert client.download_document_text('kb-1', 'doc-1') == '# 中文原文'
    else:
        with pytest.raises(ContextDBError) as error:
            client.download_document_text('kb-1', 'doc-1')
        assert error.value.status_code == 415
    response.raise_for_status.assert_called_once()
    assert session.requests[1]['url'] == 'https://signed.example/source'


def test_retry_on_5xx_then_success():
    client, session = make_client([FakeResponse(503, {'detail': 'busy'}), FakeResponse(200, {'status': 'ok'})])
    assert client.ping() == {'status': 'ok'}
    assert len(session.requests) == 2


def test_knowledge_event_polling_keeps_official_status_and_event_id():
    client, session = make_client([
        FakeResponse(200, {'id': 'event-1', 'status': 'RUNNING', 'event_type': 'KNOWLEDGE_INGEST'}),
        FakeResponse(200, {'id': 'event-1', 'status': 'SUCCEEDED', 'event_type': 'KNOWLEDGE_INGEST'}),
    ])
    result = client.wait_event('event-1', poll_interval=0)
    assert result['status'] == 'SUCCEEDED' and result['event_type'] == 'KNOWLEDGE_INGEST'
    assert all(request['method'] == 'GET' and request['url'].endswith('/v1/event/event-1')
               for request in session.requests)
