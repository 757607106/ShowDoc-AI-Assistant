"""File bodies, upload tickets and fixed target guards survive the native proxy."""
import hashlib
import os
from io import BytesIO
from unittest.mock import Mock

import pytest

import app as app_module
from governance.database import connection
from governance.knowledge_bases import create_base
from governance.store import Store
from integrations.contextdb import ContextDBClient
from tests.contextdb_fake import FakeContextDBClient
from tests.test_contextdb_client import FakeResponse, FakeSession


@pytest.fixture
def library(monkeypatch, authenticated_client):
    fake = FakeContextDBClient()
    fake.base_url, fake.timeout = 'https://files.invalid', 5
    fake._headers = lambda: {'X-API-Key': 'test'}
    fake._payload = ContextDBClient()._payload
    store = Store(client=fake, owner_id=os.environ['TEST_PLATFORM_USER'])
    monkeypatch.setattr(app_module, 'get_store', lambda: store)
    monkeypatch.setattr('webapi.contextdb.client_for_user', lambda: fake)
    base = create_base(store, {'name': '文件库', 'mode': 'source', 'review_enabled': False})
    return store, fake, authenticated_client, base['id']


def test_native_file_create_update_preserve_body_metadata_and_final_id(library):
    _, fake, http, kb = library
    response = http.post('/api/contextdb/v1/knowledge/files', data={
        'knowledge_base_id': kb, 'file': (BytesIO('# 原文\n正文'.encode()), '原件.md'),
        'metadata': '{"tag":"original"}'})
    assert response.status_code == 200
    doc = response.json['data']
    assert doc['text'] == '# 原文\n正文' and doc['metadata'] == {'tag': 'original'}
    response = http.put('/api/contextdb/v1/knowledge/files', data={
        'document_id': doc['id'], 'file': (BytesIO('完整替换正文'.encode()), '替换.md')})
    assert response.status_code == 200
    assert fake.get_document(kb, response.json['data']['id'])['text'] == '完整替换正文'


@pytest.mark.parametrize('fields,status', [({'metadata': '[]'}, 400),
    ({'metadata': '{bad'}, 400), ({'review_enabled': 'FALSE'}, 400)])
def test_native_file_validates_policy_and_metadata_before_upload(library, monkeypatch, fields, status):
    _, fake, http, kb = library
    fake.update_knowledge_base(kb, review_enabled=True)
    upload = Mock(side_effect=AssertionError('invalid upload must not reach upstream'))
    monkeypatch.setattr(fake, 'upload_file', upload)
    response = http.post('/api/contextdb/v1/knowledge/files', data={
        'knowledge_base_id': kb, 'file': (BytesIO(b'# text'), 'source.md'), **fields})
    assert response.status_code == status
    upload.assert_not_called()


@pytest.mark.parametrize('base_enabled,override', [(True, False), (False, True)])
def test_single_upload_review_override_is_forwarded_without_changing_library(library, monkeypatch, base_enabled, override):
    _, fake, http, kb = library
    fake.update_knowledge_base(kb, review_enabled=base_enabled)
    upload = Mock(wraps=fake.upload_file)
    monkeypatch.setattr(fake, 'upload_file', upload)
    response = http.post('/api/contextdb/v1/knowledge/files', data={
        'knowledge_base_id': kb, 'review_enabled': str(override).lower(),
        'file': (BytesIO(b'# source'), 'source.md')})
    assert response.status_code == 200
    assert upload.call_args.kwargs['review_enabled'] is override
    assert fake.get_knowledge_base(kb)['review_enabled'] is base_enabled


def test_single_review_override_controls_format_gate_for_create_and_update(library, monkeypatch):
    _, fake, http, kb = library
    fake.update_knowledge_base(kb, review_enabled=True)
    response = http.post('/api/contextdb/v1/knowledge/files', data={
        'knowledge_base_id': kb, 'review_enabled': 'false', 'file': (BytesIO(b'a,b\n1,2'), 'data.csv')})
    assert response.status_code == 200 and response.json['data']['text'] == 'a,b\n1,2'
    update = Mock(wraps=fake.update_file)
    monkeypatch.setattr(fake, 'update_file', update)
    response = http.put('/api/contextdb/v1/knowledge/files', data={
        'document_id': response.json['data']['id'], 'review_enabled': 'false',
        'file': (BytesIO(b'a,b\n2,3'), 'data.csv')})
    assert response.status_code == 200 and update.call_args.kwargs['review_enabled'] is False
    fake.update_knowledge_base(kb, review_enabled=False)
    response = http.post('/api/contextdb/v1/knowledge/files', data={
        'knowledge_base_id': kb, 'review_enabled': 'true', 'file': (BytesIO(b'a,b\n1,2'), 'data.csv')})
    assert response.status_code == 422


@pytest.mark.parametrize('enabled', [True, False])
def test_multipart_init_rejects_unsupported_review_parameter_before_upstream(library, monkeypatch, enabled):
    _, fake, http, kb = library
    upstream = Mock(side_effect=AssertionError('unsupported fields must not reach upstream'))
    monkeypatch.setattr(fake, '_request', upstream)
    response = http.post('/api/contextdb/v1/knowledge/files/init-upload', json={
        'knowledge_base_id': kb, 'file_name': 'source.md', 'review_enabled': enabled})
    assert response.status_code == 400 and '不支持单次评审开关' in response.json['message']
    upstream.assert_not_called()


def test_automatic_multipart_review_rejection_remains_a_validation_error(library, monkeypatch):
    _, fake, http, kb = library
    monkeypatch.setattr(fake, 'upload_file', Mock(side_effect=ValueError('分片上传不支持 review_enabled')))
    response = http.post('/api/contextdb/v1/knowledge/files', data={
        'knowledge_base_id': kb, 'review_enabled': 'false', 'file': (BytesIO(b'# source'), 'large.md')})
    assert response.status_code == 400 and '不支持 review_enabled' in response.json['message']


def test_native_review_gate_blocks_unsupported_but_review_off_preserves_original(library):
    _, fake, http, kb = library
    fake.update_knowledge_base(kb, review_enabled=True)
    def upload():
        return http.post('/api/contextdb/v1/knowledge/files', data={
            'knowledge_base_id': kb, 'file': (BytesIO(b'a,b\n1,2'), 'data.csv')})
    assert upload().status_code == 422
    assert not fake.documents
    fake.update_knowledge_base(kb, review_enabled=False)
    result = upload()
    assert result.status_code == 200 and result.json['data']['text'] == 'a,b\n1,2'


def init_parts(library, monkeypatch):
    store, fake, http, kb = library
    fake._request = Mock(return_value={'knowledge_base_id': kb, 'document_id': 'placeholder',
                                      'chunk_size': 4, 'upload_ticket': 'test-ticket'})
    response = http.post('/api/contextdb/v1/knowledge/files/init-upload', json={
        'knowledge_base_id': kb, 'file_name': 'test.md', 'metadata': {'tag': 'parts'}})
    assert response.status_code == 200
    assert fake._request.call_args.kwargs['params']['metadata'] == '{"tag": "parts"}'
    with connection() as conn:
        row = conn.execute("SELECT payload,metadata FROM runtime_records WHERE kind='knowledge_upload'").fetchone()
    assert 'test-ticket' not in str(row)
    assert row['metadata']['upload_key'] == hashlib.sha256(b'test-ticket').hexdigest()
    return store, fake, http, kb


def test_native_parts_forward_bytes_ticket_and_complete_final_id(library, monkeypatch):
    store, fake, http, kb = init_parts(library, monkeypatch)
    fake._session = FakeSession([FakeResponse(payload={'part_number': 1, 'etag': 'etag-1'}),
                                FakeResponse(payload={'document_id': 'final-id', 'knowledge_base_id': kb})])
    post_part = fake._session.post
    def capture_part(url, **kwargs):
        filename, stream, mime_type = kwargs['files']['data']
        assert stream.read() == b'abcd'
        kwargs['files']['data'] = (filename, b'abcd', mime_type)
        return post_part(url, **kwargs)
    monkeypatch.setattr(fake._session, 'post', capture_part)
    headers = {'X-Upload-Ticket': 'test-ticket'}
    response = http.post('/api/contextdb/v1/knowledge/files/chunks', headers=headers,
        data={'part_number': '1', 'data': (BytesIO(b'abcd'), 'part')})
    assert response.status_code == 200
    sent = fake._session.requests[0]
    assert sent['headers']['X-Upload-Ticket'] == 'test-ticket' and sent['data'] == {'part_number': 1}
    response = http.post('/api/contextdb/v1/knowledge/files/complete', headers=headers,
                         json={'parts': [{'part_number': 1, 'etag': 'etag-1'}]})
    assert response.status_code == 200 and response.json['data']['document_id'] == 'final-id'
    row = store._find('knowledge_upload', upload_key=hashlib.sha256(b'test-ticket').hexdigest())
    assert store._body(row['id'])['state'] == 'completed'
    assert store._body(row['id'])['document_id'] == 'final-id'
    assert http.post('/api/contextdb/v1/knowledge/files/complete', headers=headers,
                     json={'parts': [{'part_number': 1, 'etag': 'etag-1'}]}).status_code == 409


def test_native_parts_require_owner_receipt_and_allow_abort(library, monkeypatch):
    store, fake, http, kb = init_parts(library, monkeypatch)
    fake._session = FakeSession([FakeResponse(payload={'document_id': 'placeholder', 'status': 'aborted'})])
    path = '/api/contextdb/v1/knowledge/files/abort'
    assert http.post(path).status_code == 400
    assert http.post(path, headers={'X-Upload-Ticket': 'unknown'}).status_code == 409
    with connection() as conn:
        conn.execute("UPDATE runtime_records SET owner_id='another-owner',metadata=jsonb_set(metadata,'{owner_id}','\"another-owner\"') WHERE kind='knowledge_upload'")
    assert http.post(path, headers={'X-Upload-Ticket': 'test-ticket'}).status_code == 409
    assert not fake._session.requests
    with connection() as conn:
        conn.execute("UPDATE runtime_records SET owner_id=%s,metadata=jsonb_set(metadata,'{owner_id}',to_jsonb(%s::text)) WHERE kind='knowledge_upload'", (store.owner_id, store.owner_id))
    assert http.post(path, headers={'X-Upload-Ticket': 'test-ticket'}).status_code == 200


@pytest.mark.parametrize('result', [{'status': 'processing'}, {'document_id': 123},
                                  {'document_id': 'doc', 'knowledge_base_id': 'another-kb'}])
def test_native_parts_unknown_complete_keeps_receipt_and_does_not_abort(library, monkeypatch, result):
    store, fake, http, _ = init_parts(library, monkeypatch)
    fake._session = FakeSession([FakeResponse(payload=result)])
    headers = {'X-Upload-Ticket': 'test-ticket'}
    response = http.post('/api/contextdb/v1/knowledge/files/complete', headers=headers,
                         json={'parts': [{'part_number': 1, 'etag': 'etag-1'}]})
    assert response.status_code == 502
    row = store._find('knowledge_upload', upload_key=hashlib.sha256(b'test-ticket').hexdigest())
    assert store._body(row['id'])['state'] == 'completing'
    assert len(fake._session.requests) == 1
    assert http.post('/api/contextdb/v1/knowledge/files/abort', headers=headers).status_code == 409


def test_native_file_methods_and_multipart_id_locator_are_validated(library):
    _, fake, http, kb = library
    assert http.get('/api/contextdb/v1/knowledge/files').status_code == 405
    assert http.put('/api/contextdb/v1/knowledge/files/complete').status_code == 405
    doc = fake.create_text_document(kb, 'source.md', 'source')
    response = http.put('/api/contextdb/v1/knowledge/files/init-upload', json={
        'document_id': doc['id'], 'name': 'logical-name.md', 'file_name': 'physical.md'})
    assert response.status_code == 400


def test_deleted_target_capture_cannot_be_retried_but_history_remains_readable(library):
    store, fake, http, kb = library
    from governance.knowledge_bases import delete_base
    from governance.spaces import ensure_base_space
    space = ensure_base_space(store, kb)
    job = store.create_job('showdoc', {'item_id': 1}, scope=space['scope'])
    store.update_job(job['task_id'], status='failed')
    assert delete_base(store, kb)['lifecycle'] == 'deleted'
    assert http.post('/tasks/' + job['task_id'] + '/retry').status_code == 409
    response = http.get('/api/tasks?space_scope=' + space['scope'])
    assert response.status_code == 200
    assert [item['task_id'] for item in response.json['tasks']] == [job['task_id']]


def test_old_pending_dual_target_job_is_cancelled_with_history_without_delivery(library, monkeypatch):
    store, fake, _, kb = library
    from governance.spaces import ensure_base_space
    from governance.worker import process_job
    scope = ensure_base_space(store, kb)['scope']
    job = store.create_job('contextdb', {'release_id': 'kept-original-release',
        'target_modes': ['wiki', 'graph'], 'target_ids': {'wiki': kb, 'graph': 'old-graph'}},
        kind='ctxdb_sync', scope=scope)
    monkeypatch.setattr('webapi.auth.client_for_user', lambda _: fake)
    process_job(store, job)
    cancelled = store.get_job(job['task_id'])
    assert cancelled['status'] == 'cancelled' and '请选择一个知识库' in cancelled['message']
    assert cancelled['params'] == job['params'] and not fake.documents


@pytest.mark.parametrize('method,batch', [('PATCH', False), ('DELETE', False), ('POST', True), ('DELETE', True)])
def test_node_mutations_verify_kb_and_forward_original_batch_under_library_lock(library, monkeypatch, method, batch):
    from contextlib import contextmanager
    _, fake, http, kb = library
    locked, calls = [], []
    @contextmanager
    def lock(kb_id):
        locked.append(kb_id)
        try:
            yield
        finally:
            locked.pop()
    monkeypatch.setattr('governance.knowledge_bases.base_write_lock', lock)
    def upstream(verb, path, **kwargs):
        assert locked == [kb]
        calls.append((verb, path, kwargs))
        if verb == 'GET':
            assert kwargs['params']['knowledge_base_id'] == kb
            return {'parent_node': {'node_id': kwargs['params']['parent_node_id']}}
        return {'results': [{'id': 'parent', 'success': True}, {'id': 'child', 'success': False, 'error': 'stale version'}]} if batch else {'deleted': True}
    monkeypatch.setattr(fake, '_request', upstream)
    params = {'knowledge_base_id': kb}
    if batch:
        path = '/api/contextdb/v1/knowledge/nodes/batch'
        body = {'ids': ['parent', 'child'], 'expected_tree_versions': {'parent': 2, 'child': 3}}
        if method == 'POST':
            body.update(action='move', parent_node_id='target')
    else:
        path = '/api/contextdb/v1/knowledge/nodes'
        body = {'node_id': 'parent', 'expected_tree_version': 2, 'display_name': '新名'} if method == 'PATCH' else None
        if method == 'DELETE':
            params.update(node_id='parent', expected_tree_version='2', recursive='false')
    response = http.open(path, method=method, query_string=params, json=body)
    assert response.status_code == 200
    expected = ['parent', 'child'] if batch else ['parent']
    if method == 'POST':
        expected.append('target')
    assert [call[2]['params']['parent_node_id'] for call in calls[:-1]] == expected
    assert calls[-1] == (method, '/v1/knowledge/nodes' + ('/batch' if batch else ''),
                         {'json_body': body, 'params': {key: value for key, value in params.items() if key != 'knowledge_base_id'}})
    if batch:
        assert response.json['data']['results'][1]['error'] == 'stale version'


def test_node_mutations_reject_missing_context_wrong_ownership_and_deleting_library(library, monkeypatch):
    from governance.spaces import ensure_base_space, persist_space
    store, fake, http, kb = library
    upstream = Mock(return_value={'parent_node': {'node_id': 'another-node'}})
    monkeypatch.setattr(fake, '_request', upstream)
    path = '/api/contextdb/v1/knowledge/nodes/batch'
    body = {'ids': ['parent', 'child'], 'expected_tree_versions': {'parent': 1, 'child': 1}}
    assert http.delete(path, json=body).status_code == 400
    upstream.assert_not_called()
    response = http.delete(path, query_string={'knowledge_base_id': kb}, json=body)
    assert response.status_code == 409 and all(call.args[0] == 'GET' for call in upstream.call_args_list)
    upstream.reset_mock()
    space = ensure_base_space(store, kb)
    persist_space(store, {**space, 'lifecycle': 'deleting'})
    assert http.delete(path, query_string={'knowledge_base_id': kb}, json=body).status_code == 409
    upstream.assert_not_called()
