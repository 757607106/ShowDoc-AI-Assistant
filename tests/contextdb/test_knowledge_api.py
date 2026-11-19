"""知识域与 Wiki 域 API 契约测试(蓝图 × ContextDB 替身)。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import app as app_module
import webapi.material as material_module
from governance.store import Store
from tests.fakes.contextdb_fake import FakeContextDBClient


@pytest.fixture()
def client(monkeypatch, authenticated_client):
    fake = FakeContextDBClient()
    fake.ensure_knowledge_base('knowledge-default', wiki_enabled=True, review_enabled=True)
    app_module.app.extensions['governance_store'] = Store(client=fake, kb_name='_test_governance')
    app_module.app.config['TESTING'] = True
    import webapi.knowledge as knowledge
    monkeypatch.setattr(knowledge, '_client', lambda: fake)
    yield fake, authenticated_client
    app_module.app.extensions.pop('governance_store', None)


def test_kb_bases_lists_visible_knowledge_bases(client):
    fake, http = client
    fake.ensure_knowledge_base('knowledge-web:example.com', wiki_enabled=True)
    resp = http.get('/api/kb/bases')
    names = [base['name'] for base in resp.get_json()['bases']]
    assert 'knowledge-default' in names and 'knowledge-web:example.com' in names


def test_kb_search_requires_question_and_scope(client):
    _, http = client
    resp = http.post('/api/kb/search', json={'kb_ids': ['kb-1']})
    assert resp.status_code == 400
    resp = http.post('/api/kb/search', json={'question': '如何配置'})
    assert resp.status_code == 400


def test_kb_search_proxies_query(client):
    fake, http = client
    kb = fake.ensure_knowledge_base('k1')
    fake.create_text_document(kb['id'], 'doc.md', '如何配置连接池', metadata={'product': 'P'})
    resp = http.post('/api/kb/search', json={'question': '配置', 'kb_ids': [kb['id']], 'view': 'source', 'top_k': 3})
    payload = resp.get_json()
    assert payload['success'] is True and payload['total'] == 1
    assert '配置连接池' in payload['chunks'][0]['content']


def _capture_query(monkeypatch, fake):
    captured = {}
    original = fake.query

    def spy(question, **kwargs):
        captured.update(kwargs)
        return original(question, **kwargs)

    monkeypatch.setattr(fake, 'query', spy)
    return captured


def _cleanup_retrieval_config():
    from governance.database import connection
    with connection() as conn:
        conn.execute("DELETE FROM runtime_records WHERE kind='settings' AND record_key='retrieval-config'")


def test_kb_search_applies_workspace_retrieval_overrides(client, monkeypatch):
    fake, http = client
    captured = _capture_query(monkeypatch, fake)
    kb = fake.ensure_knowledge_base('k1')
    fake.create_text_document(kb['id'], 'doc.md', '如何配置连接池')
    try:
        saved = http.put('/api/v1/tenants/kv/retrieval-config',
                         json={'top_k': 3, 'similarity_threshold': 0.7, 'vector_weight': 0.5, 'query_rewrite': False})
        assert saved.status_code == 200
        resp = http.post('/api/kb/search', json={'question': '配置', 'kb_ids': [kb['id']]})
        assert resp.get_json()['success'] is True
        assert captured['top_k'] == 3 and captured['similarity_threshold'] == 0.7
        assert captured['vector_weight'] == 0.5 and captured['query_rewrite'] is False
    finally:
        _cleanup_retrieval_config()


def test_kb_search_request_params_take_precedence_over_workspace_defaults(client, monkeypatch):
    fake, http = client
    captured = _capture_query(monkeypatch, fake)
    kb = fake.ensure_knowledge_base('k1')
    fake.create_text_document(kb['id'], 'doc.md', '如何配置连接池')
    try:
        saved = http.put('/api/v1/tenants/kv/retrieval-config',
                         json={'top_k': 3, 'vector_weight': 0.5})
        assert saved.status_code == 200
        resp = http.post('/api/kb/search', json={'question': '配置', 'kb_ids': [kb['id']], 'top_k': 5, 'threshold': 0.9})
        assert resp.get_json()['success'] is True
        assert captured['top_k'] == 5 and captured['similarity_threshold'] == 0.9
        assert captured['vector_weight'] == 0.5 and captured['query_rewrite'] is True
    finally:
        _cleanup_retrieval_config()


def test_retrieval_config_kv_rejects_fields_outside_official_contract(client):
    _, http = client
    try:
        assert http.put('/api/v1/tenants/kv/retrieval-config', json={'rrf_k': 60}).status_code == 400
        assert http.put('/api/v1/tenants/kv/retrieval-config', json={'top_k': 11}).status_code == 400
        assert http.put('/api/v1/tenants/kv/retrieval-config', json={'top_k': 0}).status_code == 400
        assert http.put('/api/v1/tenants/kv/retrieval-config', json={'vector_weight': 1.5}).status_code == 400
        assert http.put('/api/v1/tenants/kv/retrieval-config', json={'query_rewrite': 'yes'}).status_code == 400
        saved = http.put('/api/v1/tenants/kv/retrieval-config', json={'top_k': 6, 'query_rewrite': False})
        assert saved.status_code == 200 and saved.get_json()['data']['top_k'] == 6
    finally:
        _cleanup_retrieval_config()


def test_retrieval_overrides_filter_values_outside_official_contract(monkeypatch):
    from agent import registry
    monkeypatch.setattr(registry, 'records', lambda kind, owner, **kwargs: [
        {'id': 'retrieval-config', 'value': {'top_k': 12, 'similarity_threshold': 1.5, 'vector_weight': 'x',
                                             'query_rewrite': 'yes', 'rrf_k': 60}}])
    assert registry.retrieval_overrides('u') == {}
    monkeypatch.setattr(registry, 'records', lambda kind, owner, **kwargs: [
        {'id': 'other-config', 'value': {'top_k': 2}}, {'id': 'retrieval-config', 'value': None}])
    assert registry.retrieval_overrides('u') == {}
    monkeypatch.setattr(registry, 'records', lambda kind, owner, **kwargs: [])
    assert registry.retrieval_overrides('u') == {}


def test_global_search_maps_question_without_expanding_scope(client, monkeypatch):
    from unittest.mock import Mock
    fake, http = client
    fake._request = Mock(return_value={'chunks': []})
    monkeypatch.setattr('webapi.contextdb.client_for_user', lambda: fake)
    body = {'query': '配置', 'knowledge_base_ids': ['kb-a'], 'document_ids': ['doc-a'], 'top_k': 10}
    response = http.post('/api/contextdb/v1/knowledge/query', json=body)
    assert response.status_code == 200
    fake._request.assert_called_once_with('POST', '/v1/knowledge/query',
        json_body={'question': '配置', 'knowledge_base_ids': ['kb-a'], 'document_ids': ['doc-a'], 'top_k': 10}, params={})
    fake._request.reset_mock()
    response = http.post('/api/contextdb/v1/knowledge/query', json={**body, 'question': '另一个问题'})
    assert response.status_code == 400
    fake._request.assert_not_called()


def test_kb_reviews_queue_and_actions(client):
    fake, http = client
    kb = fake.ensure_knowledge_base('k2', review_enabled=True)
    fake.reviews['r-1'] = {'review_id': 'r-1', 'knowledge_base_id': kb['id'],
                            'review_status': 'pending', 'decision': 'pending_review',
                            'document_id': 'doc-1', 'document_name': 'a.md'}
    resp = http.get(f'/api/kb/reviews?kb_id={kb["id"]}')
    assert resp.get_json()['total'] == 1
    resp = http.post('/api/kb/reviews/r-1/action', json={'action': 'confirm'})
    assert resp.get_json()['success'] is True
    resp = http.post('/api/kb/reviews/r-1/action', json={'action': 'explode'})
    assert resp.status_code == 400


def test_kb_review_lifecycle_retract_and_edited_rewrite(client):
    fake, http = client
    kb = fake.ensure_knowledge_base('k3', review_enabled=True)
    fake.reviews['r-2'] = {'review_id': 'r-2', 'knowledge_base_id': kb['id'], 'review_status': 'reviewed',
                            'decision': 'approved', 'lifecycle_state': 'auto_accepted', 'document_id': 'doc-2'}
    resp = http.get(f'/api/kb/reviews?kb_id={kb["id"]}&lifecycle_state=auto_accepted')
    assert resp.get_json()['total'] == 1
    resp = http.get(f'/api/kb/reviews?kb_id={kb["id"]}&lifecycle_state=a&review_status=b')
    assert resp.status_code == 400
    resp = http.get('/api/kb/reviews/r-2?content_page=2')
    assert resp.get_json()['review']['content_page'] == 2
    # 非法状态下的动作由 ContextDB 拒绝,透传 4xx 而非 503
    resp = http.post('/api/kb/reviews/r-2/action', json={'action': 'confirm'})
    assert resp.status_code == 400 and '拒绝' in resp.get_json()['message']
    resp = http.post('/api/kb/reviews/r-2/action', json={'action': 'retract'})
    assert resp.get_json()['review']['lifecycle_state'] == 'pending_human'
    resolutions = [{'conflict_id': 'c-1', 'resolution': 'keep_old'}]
    resp = http.post('/api/kb/reviews/r-2/conflicts', json={'resolutions': [{'conflict_id': 'c-1', 'resolution': 'bad'}]})
    assert resp.status_code == 400
    resp = http.post('/api/kb/reviews/r-2/conflicts', json={'resolutions': resolutions})
    assert resp.get_json()['result']['saved'] == 1
    resp = http.post('/api/kb/reviews/r-2/action', json={
        'action': 'accept_rewrite', 'edited_content': '人工修订正文', 'conflict_resolutions': resolutions})
    review = resp.get_json()['review']
    assert review['lifecycle_state'] == 'approved' and review['edited_content'] == '人工修订正文'


def test_batch_review_returns_individual_failures_and_does_not_rollback_success(client):
    fake, http = client
    kb = fake.ensure_knowledge_base('batch-reviews', review_enabled=True)
    for review_id, state in [('pending', 'pending_human'), ('accepted', 'auto_accepted')]:
        fake.reviews[review_id] = {'review_id': review_id, 'knowledge_base_id': kb['id'],
            'review_status': 'pending', 'lifecycle_state': state, 'decision': 'pending_review'}
    response = http.post('/api/kb/reviews/batch', json={'ids': ['pending', 'accepted'], 'action': 'confirm'})
    assert response.status_code == 200
    assert response.json['succeeded'] == 1 and response.json['failed'] == 1
    assert response.json['results'][0] == {'id': 'pending', 'success': True}
    assert response.json['results'][1]['success'] is False
    assert fake.reviews['pending']['lifecycle_state'] == 'approved'
    assert fake.reviews['accepted']['lifecycle_state'] == 'auto_accepted'


def test_batch_review_missing_item_does_not_block_valid_review(client):
    fake, http = client
    kb = fake.ensure_knowledge_base('partial-batch', review_enabled=True)
    fake.reviews['valid'] = {'review_id': 'valid', 'knowledge_base_id': kb['id'], 'lifecycle_state': 'pending_human'}
    response = http.post('/api/kb/reviews/batch', json={'ids': ['missing', 'valid', 'valid'], 'action': 'confirm'})
    assert response.status_code == 200
    result = response.json
    assert (result['total'], result['succeeded'], result['failed']) == (3, 1, 2)
    assert [item['success'] for item in result['results']] == [False, True, False]
    assert fake.reviews['valid']['lifecycle_state'] == 'approved'


def test_reviews_pass_optional_scope_and_official_score_sorting(client, monkeypatch):
    from unittest.mock import Mock
    fake, http = client
    read = Mock(return_value={'reviews': [], 'total': 0})
    monkeypatch.setattr(fake, 'list_reviews', read)
    response = http.get('/api/kb/reviews?lifecycle_state=pending_human&sort_by=confidence_score&sort_order=asc&page=2&page_size=20')
    assert response.status_code == 200
    read.assert_called_once_with(None, review_status=None, lifecycle_state='pending_human', decision=None,
                                 page=2, page_size=20, sort_by='confidence_score', sort_order='asc')


@pytest.mark.parametrize('payload', [
    {'ids': [], 'action': 'confirm'}, {'ids': ['r'] * 51, 'action': 'confirm'},
    {'ids': [' '], 'action': 'confirm'}, {'ids': ['r'], 'action': 'reject_reupload'},
    {'ids': ['r'], 'action': ['confirm']},
])
def test_batch_review_rejects_invalid_batch(client, payload):
    _, http = client
    assert http.post('/api/kb/reviews/batch', json=payload).status_code == 400


def test_review_settings_persist_explicit_master_switch_and_review_rounds(client):
    fake, http = client
    kb = fake.ensure_knowledge_base('review-settings', review_enabled=True)
    response = http.put('/api/kb/review-settings', json={
        'kb_id': kb['id'], 'review_enabled': False, 'max_rewrite_iterations': 1})
    assert response.status_code == 200
    settings = http.get(f'/api/kb/review-settings?kb_id={kb["id"]}').json['settings']
    assert settings['review_enabled'] is False and settings['max_rewrite_iterations'] == 1


def test_kb_documents_list_read_and_edit(client):
    fake, http = client
    kb = fake.ensure_knowledge_base('k4', review_enabled=True)
    doc = fake.create_text_document(kb['id'], 'doc-a.md', '原始正文')
    fake.documents[doc['id']]['source_type'] = 'text'
    assert http.get('/api/kb/documents').status_code == 400
    resp = http.get(f'/api/kb/documents?kb_id={kb["id"]}')
    assert [item['name'] for item in resp.get_json()['documents']] == ['doc-a.md']
    resp = http.get(f'/api/kb/documents/{doc["id"]}/text?kb_id={kb["id"]}')
    assert resp.get_json()['text'] == '原始正文'
    assert http.put(f'/api/kb/documents/{doc["id"]}', json={'text': '  '}).status_code == 400
    resp = http.put(f'/api/kb/documents/{doc["id"]}', json={'text': '修改后正文', 'kb_id': kb['id']})
    assert resp.get_json()['success'] is True
    assert fake.documents[doc['id']]['text'] == '修改后正文'


@pytest.mark.parametrize('source_type', ['text', 'memory_promotion'])
def test_document_text_update_uses_official_text_channel(client, monkeypatch, source_type):
    from unittest.mock import Mock
    fake, http = client
    detail = {'id': 'text-1', 'source_type': source_type, 'name': 'guide.md',
              'knowledge_base_id': next(iter(fake.knowledge_bases)),
              'mime_type': 'text/markdown', 'metadata': {'team': 'support'}}
    get_document = Mock(return_value=detail)
    update_text = Mock(return_value={**detail, 'id': 'returned-text-id'})
    monkeypatch.setattr(fake, 'get_document', get_document)
    monkeypatch.setattr(fake, 'update_text_document', update_text)
    # The official detail endpoint accepts document_id without a KB hint.
    result = http.put('/api/kb/documents/text-1', json={'text': '# 修订'})
    assert result.status_code == 200 and result.json['document']['id'] == 'returned-text-id'
    assert [entry.args for entry in get_document.call_args_list] == [(None, 'text-1'), (None, 'text-1')]
    update_text.assert_called_once_with('# 修订', document_id='text-1')


@pytest.mark.parametrize('mime_type', ['text/markdown', 'application/octet-stream', None])
def test_document_file_text_update_preserves_file_contract(client, monkeypatch, mime_type):
    from unittest.mock import Mock
    fake, http = client
    fake.knowledge_bases['kb-1'] = {'id': 'kb-1', 'name': '可编辑文件库', 'wiki_enabled': False, 'graph_enabled': False}
    detail = {'id': 'file-1', 'source_type': 'file', 'name': '操作指南.md', 'knowledge_base_id': 'kb-1',
              'mime_type': mime_type, 'metadata': {'team': 'support'}}
    get_document = Mock(return_value=detail)
    monkeypatch.setattr(fake, 'get_document', get_document)
    monkeypatch.setattr(fake, 'update_text_document', Mock(side_effect=AssertionError('file must use PUT files')))
    def update_file(document_id, name, path, *, mime_type=None):
        assert document_id == 'file-1' and name == '操作指南.md'
        assert Path(path).read_bytes() == '# 修订正文'.encode('utf-8')
        assert mime_type == (detail['mime_type'] or 'application/octet-stream')
        return {**detail, 'id': 'returned-file-id'}
    update = Mock(side_effect=update_file)
    monkeypatch.setattr(fake, 'update_file', update)
    response = http.put('/api/kb/documents/file-1', json={'kb_id': 'kb-1', 'text': '# 修订正文'})
    assert response.status_code == 200 and response.json['document']['id'] == 'returned-file-id'
    assert response.json['document']['metadata'] == detail['metadata']
    assert [entry.args for entry in get_document.call_args_list] == [('kb-1', 'file-1'), (None, 'file-1')]
    assert update.call_count == 1


@pytest.mark.parametrize('source_type,name,mime_type', [
    ('file', 'guide.pdf', 'application/pdf'),
    ('file', 'guide.md', 'application/pdf'),
    ('file', 'guide.docx', 'application/octet-stream'),
    ('connector', 'guide.md', 'text/markdown'),
    (None, 'guide.md', 'text/markdown'),
])
def test_document_editor_rejects_binary_and_unknown_sources(client, monkeypatch, source_type, name, mime_type):
    from unittest.mock import Mock
    fake, http = client
    monkeypatch.setattr(fake, 'get_document', Mock(return_value={
        'id': 'd', 'source_type': source_type, 'name': name, 'mime_type': mime_type}))
    download = Mock(side_effect=AssertionError('binary original must not be decoded'))
    write_text = Mock(side_effect=AssertionError('unsupported source must not be written'))
    write_file = Mock(side_effect=AssertionError('unsupported source must not be written'))
    monkeypatch.setattr(fake, 'download_document_text', download)
    monkeypatch.setattr(fake, 'update_text_document', write_text)
    monkeypatch.setattr(fake, 'update_file', write_file)
    assert http.get('/api/kb/documents/d/text?kb_id=kb-1').status_code == 415
    assert http.put('/api/kb/documents/d', json={'kb_id': 'kb-1', 'text': '# 修订'}).status_code == 415
    assert not download.called and not write_text.called and not write_file.called


def test_document_update_propagates_official_file_error(client, monkeypatch):
    from unittest.mock import Mock
    from integrations.contextdb import ContextDBConflictError
    fake, http = client
    fake.knowledge_bases['kb-1'] = {'id': 'kb-1', 'name': '可编辑文件库', 'wiki_enabled': False, 'graph_enabled': False}
    monkeypatch.setattr(fake, 'get_document', Mock(return_value={
        'id': 'd', 'knowledge_base_id': 'kb-1', 'source_type': 'file', 'name': 'guide.md', 'mime_type': 'text/markdown'}))
    update = Mock(side_effect=ContextDBConflictError('same document upload is in progress', status_code=409))
    monkeypatch.setattr(fake, 'update_file', update)
    result = http.put('/api/kb/documents/d', json={'kb_id': 'kb-1', 'text': '# 修订'})
    assert result.status_code == 409 and 'in progress' in result.json['message']
    assert update.call_count == 1


def test_removed_memory_and_promotion_routes_never_access_contextdb(client, monkeypatch):
    from unittest.mock import Mock
    _, http = client
    factory = Mock(side_effect=AssertionError('removed routes must not access ContextDB'))
    monkeypatch.setattr('webapi.knowledge._client', factory)
    for method, path in (
        ('POST', 'memories'), ('POST', 'memories/search'), ('GET', 'memories/event-1'),
        ('GET', 'promotions'), ('POST', 'promotions'), ('POST', 'promotions/p-1/approve'),
        ('POST', 'promotions/p-1/reject'), ('GET', 'promotion-settings'), ('PUT', 'promotion-settings'),
    ):
        response = http.open('/api/kb/' + path, method=method, json={})
        assert response.status_code == 404, (method, path, response.text)
    factory.assert_not_called()


def test_wiki_pages_listing_and_full_page_read(client, monkeypatch):
    fake, http = client
    monkeypatch.setattr('webapi.contextdb.client_for_user', lambda: fake)
    kb = fake.ensure_knowledge_base('k1', wiki_enabled=True)
    page = fake.create_wiki_page(kb['id'], '部署排错', '# 部署排错\n\n内容')
    resp = http.get('/api/contextdb/v1/knowledge/wiki/pages', query_string={'knowledge_base_id': kb['id']})
    items = resp.get_json()['data']['items']
    assert any(item['page_id'] == page['page_id'] for item in items)
    assert all('content' not in item for item in items)
    resp = http.get('/api/contextdb/v1/knowledge/wiki/pages/detail',
                    query_string={'knowledge_base_id': kb['id'], 'page_id': page['page_id']})
    assert resp.get_json()['data']['content'] == page['content']


def test_wiki_page_create_conflict_and_cas_update(client, monkeypatch):
    fake, http = client
    monkeypatch.setattr('webapi.contextdb.client_for_user', lambda: fake)
    monkeypatch.setattr(material_module, 'client_for_user', lambda: fake)
    monkeypatch.setattr(app_module, 'client_for_user', lambda: fake)
    kb = fake.ensure_knowledge_base('k9', wiki_enabled=True)
    path = '/api/contextdb/v1/knowledge/wiki/pages'
    resp = http.post(path, json={'knowledge_base_id': kb['id'], 'title': '速查', 'content': '# 速查'})
    assert resp.get_json()['success'] is True
    resp = http.post(path, json={'knowledge_base_id': kb['id'], 'title': '速查', 'content': '# 重复'})
    assert resp.status_code == 409
    page = next(iter(fake.wiki_pages.values()))
    body = {'knowledge_base_id': kb['id'], 'page_id': page['page_id'], 'content': '# 速查 v2'}
    assert http.put(path, json=body).status_code == 400
    assert page['version'] == 1
    resp = http.put(path, json={**body, 'expected_version': 1})
    assert resp.get_json()['success'] is True
    assert page['version'] == 2
    assert http.put(path, json={**body, 'content': 'stale', 'expected_version': 1}).status_code == 409
    assert page['content'] == '# 速查 v2'


def test_sync_status_reads_governance_job(client):
    fake, http = client
    store = material_module.get_store()
    job = store.create_job('contextdb', {'release_id': 'r1'}, kind='ctxdb_sync', scope='default')
    resp = http.get(f'/api/kb/sync-status?job_id={job["task_id"]}')
    payload = resp.get_json()
    assert payload['job']['kind'] == 'ctxdb_sync' and payload['job']['status'] == 'pending'
