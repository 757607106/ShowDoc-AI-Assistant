"""Official knowledge-base CRUD with isolated PostgreSQL routing receipts."""
import os

import pytest

import app as app_module
from governance.knowledge_bases import create_base, delete_base, update_base
from governance.spaces import ensure_base_space, get_space, list_spaces, require_writable_space
from governance.store import Store, StoreError
from integrations.contextdb import ContextDBError
from tests.contextdb_fake import FakeContextDBClient


@pytest.fixture
def library(monkeypatch, authenticated_client):
    fake = FakeContextDBClient()
    store = Store(client=fake, owner_id=os.environ['TEST_PLATFORM_USER'])
    app_module.app.extensions['governance_store'] = store
    monkeypatch.setattr('webapi.contextdb.client_for_user', lambda: fake)
    monkeypatch.setattr('webapi.knowledge._client', lambda: fake)
    yield store, fake, authenticated_client
    app_module.app.extensions.pop('governance_store', None)


@pytest.mark.parametrize('mode', ['source', 'graph', 'wiki'])
def test_native_creation_readbacks_one_official_id_without_overriding_review_policy(library, monkeypatch, mode):
    from unittest.mock import Mock
    store, fake, http = library
    update_policy = Mock(side_effect=AssertionError('Creation must not replace the official review policy'))
    monkeypatch.setattr(fake, 'update_review_settings', update_policy)
    response = http.post('/api/contextdb/v1/knowledge/knowledge_bases', json={
        'name': '业务资料', 'wiki_enabled': mode == 'wiki', 'graph_enabled': mode == 'graph'})
    assert response.status_code == 200
    kb_id = response.json['data']['id']
    binding = http.post(f'/api/kb/bases/{kb_id}/binding')
    assert binding.status_code == 200
    space = binding.json['space']
    assert space['knowledge_base_id'] == kb_id and space['mode'] == mode and space['lifecycle'] == 'active'
    assert [target for target, info in space['targets'].items() if info['enabled']] == [mode]
    assert len(fake.knowledge_bases) == 1
    assert fake.get_knowledge_base(kb_id)['review_enabled'] is False
    update_policy.assert_not_called()
    assert ensure_base_space(store, kb_id)['scope'] == space['scope']


def test_existing_base_binding_keeps_its_official_policy_and_name(library):
    store, fake, http = library
    base = fake.create_knowledge_base('已有正式名称', graph_enabled=True, review_enabled=False)
    fake.update_review_settings(base['id'], review_enabled=False, high_threshold=0.7)
    binding = http.post(f'/api/kb/bases/{base["id"]}/binding')
    assert binding.status_code == 200
    assert binding.json['space']['name'] == '已有正式名称'
    assert fake.get_review_settings(base['id'])['high_threshold'] == 0.7
    assert fake.get_review_settings(base['id'])['review_enabled'] is False


def test_rename_and_non_wiki_graph_switch_use_official_authority(library):
    store, fake, http = library
    base = create_base(store, {'name': '原名', 'mode': 'source'})
    before = ensure_base_space(store, base['id'])
    path = '/api/contextdb/v1/knowledge/knowledge_bases'
    response = http.put(path, json={'knowledge_base_id': base['id'], 'name': '新名'})
    assert response.status_code == 200
    assert fake.get_knowledge_base(base['id'])['name'] == '新名'
    assert get_space(store, before['scope'])['name'] == '新名'
    assert get_space(store, before['scope'])['knowledge_base_id'] == base['id']
    assert http.put(path, json={'knowledge_base_id': base['id'], 'graph_enabled': True}).status_code == 200
    assert get_space(store, before['scope'])['mode'] == 'graph'
    assert http.patch('/api/kb/spaces/' + before['scope'], json={'graph_enabled': False}).status_code == 200
    assert get_space(store, before['scope'])['mode'] == 'source'
    assert http.patch('/api/kb/spaces/' + before['scope'], json={'mode': 'wiki'}).status_code == 409
    fake.update_knowledge_base(base['id'], name='控制台改名')
    assert get_space(store, before['scope'])['name'] == '控制台改名'


def test_delete_requires_empty_base_and_stopped_capture_then_tombstones_without_resurrection(library):
    store, fake, http = library
    base = create_base(store, {'name': '待删除库', 'mode': 'wiki'})
    space = ensure_base_space(store, base['id'])
    path = '/api/contextdb/v1/knowledge/knowledge_bases?knowledge_base_id=' + base['id']
    document = fake.create_text_document(base['id'], 'source.md', '# source')
    assert http.delete(path).status_code == 409
    assert fake.get_document(base['id'], document['id'])
    fake.delete_documents(base['id'], [document['id']])
    job = store.create_job('showdoc', {'item_id': 1}, scope=space['scope'])
    assert http.delete(path).status_code == 409
    store.cancel(job['task_id'])
    response = http.delete(path)
    assert response.status_code == 200 and response.json['data']['lifecycle'] == 'deleted'
    assert get_space(store, space['scope'])['lifecycle'] == 'deleted'
    with pytest.raises(StoreError):
        require_writable_space(store, space['scope'])
    assert http.post(f'/api/kb/bases/{base["id"]}/binding').status_code == 409
    assert http.delete(path).json['data']['lifecycle'] == 'deleted'
    assert fake.knowledge_bases == {}
    assert store.get_job(job['task_id'])['status'] == 'cancelled'


def test_external_deletion_preserves_bound_id_and_refuses_same_named_replacement(library):
    store, fake, _ = library
    base = create_base(store, {'name': '外部删除', 'mode': 'source'})
    space = ensure_base_space(store, base['id'])
    fake.delete_knowledge_base(base['id'])
    replacement = fake.create_knowledge_base('外部删除')
    missing = get_space(store, space['scope'])
    assert missing['knowledge_base_id'] == base['id'] and missing['lifecycle'] == 'missing'
    with pytest.raises(StoreError):
        require_writable_space(store, space['scope'])
    assert ensure_base_space(store, replacement['id'])['scope'] != space['scope']


def test_unknown_delete_is_read_back_and_not_repeated_when_already_gone(library, monkeypatch):
    store, fake, _ = library
    base = create_base(store, {'name': '删除结果回读', 'mode': 'source'})
    calls = []
    def lost_response(kb_id):
        calls.append(kb_id)
        fake.knowledge_bases.pop(kb_id)
        raise ContextDBError('response lost')
    monkeypatch.setattr(fake, 'delete_knowledge_base', lost_response)
    assert delete_base(store, base['id'])['lifecycle'] == 'deleted'
    assert delete_base(store, base['id'])['lifecycle'] == 'deleted'
    assert calls == [base['id']]


def test_uncertain_delete_keeps_write_block_and_does_not_claim_deleted(library, monkeypatch):
    store, fake, _ = library
    base = create_base(store, {'name': '删除结果未知', 'mode': 'source'})
    scope = ensure_base_space(store, base['id'])['scope']
    def failed(kb_id):
        raise ContextDBError('network lost')
    monkeypatch.setattr(fake, 'delete_knowledge_base', failed)
    with pytest.raises(ContextDBError):
        delete_base(store, base['id'])
    assert get_space(store, scope)['lifecycle'] == 'deleting'
    with pytest.raises(StoreError):
        require_writable_space(store, scope)


def test_failed_creation_readback_retains_exact_cloud_id_instead_of_recreating(library, monkeypatch):
    store, fake, _ = library
    def failed(*args, **kwargs):
        raise ContextDBError('detail unavailable')
    read = fake.get_knowledge_base
    monkeypatch.setattr(fake, 'get_knowledge_base', failed)
    with pytest.raises(StoreError, match='勿重复创建'):
        create_base(store, {'name': '策略未就绪', 'mode': 'source'})
    assert len(fake.knowledge_bases) == 1
    base = next(iter(fake.knowledge_bases.values()))
    monkeypatch.setattr(fake, 'get_knowledge_base', read)
    space = ensure_base_space(store, base['id'])
    assert space['lifecycle'] == 'active'
    assert require_writable_space(store, space['scope'])['knowledge_base_id'] == base['id']


def test_legacy_pair_lists_as_two_ids_and_preserves_graph_receipts(library):
    store, fake, _ = library
    wiki = fake.create_knowledge_base('旧Wiki', wiki_enabled=True)
    graph = fake.create_knowledge_base('旧图谱', graph_enabled=True)
    store._create('knowledge_space', 'business', {'scope': 'business', 'name': '旧别名',
        'wiki_kb_id': wiki['id'], 'graph_kb_id': graph['id'], 'graph_enabled': True}, {'scope': 'business'})
    spaces, _ = list_spaces(store)
    assert {item['knowledge_base_id'] for item in spaces} == {wiki['id'], graph['id']}
    assert get_space(store, 'business')['mode'] == 'wiki'
    graph_space = ensure_base_space(store, graph['id'])
    assert graph_space['scope'] != 'business' and graph_space['legacy_origin_scope'] == 'business'
    assert graph_space['mode'] == 'graph'
    assert fake.get_knowledge_base(wiki['id'])['name'] == '旧Wiki'


def test_delete_blocks_other_members_unfinished_upload_until_aborted(library):
    store, fake, _ = library
    base = create_base(store, {'name': '上传中禁止删库', 'mode': 'source'})
    other = Store(client=fake, owner_id='another-member')
    receipt = other._create('knowledge_upload', 'ticket-hash',
        {'knowledge_base_id': base['id'], 'state': 'uploading'}, {'upload_key': 'ticket-hash'})
    with pytest.raises(StoreError, match='分片上传会话'):
        delete_base(store, base['id'])
    assert base['id'] in fake.knowledge_bases
    other._write(receipt['id'], {'knowledge_base_id': base['id'], 'state': 'aborted'})
    assert delete_base(store, base['id'])['lifecycle'] == 'deleted'
    assert other._body(receipt['id'])['state'] == 'aborted'


def test_document_id_cannot_bypass_its_library_lifecycle_with_another_id(library):
    from governance.knowledge_bases import require_writable_base
    store, fake, _ = library
    first = create_base(store, {'name': '库一', 'mode': 'source'})
    second = create_base(store, {'name': '库二', 'mode': 'source'})
    document = fake.create_text_document(second['id'], 'source.md', 'source')
    with pytest.raises(StoreError, match='不属于'):
        require_writable_base(store, first['id'], document['id'])
    assert require_writable_base(store, document_id=document['id'])['knowledge_base_id'] == second['id']


def test_cloud_creation_survives_local_binding_failure_with_exact_id_for_recovery(library, monkeypatch):
    store, fake, _ = library
    def failed(*args, **kwargs):
        raise RuntimeError('database unavailable')
    monkeypatch.setattr('governance.spaces.persist_space', failed)
    with pytest.raises(StoreError, match='本地绑定未保存') as error:
        create_base(store, {'name': '创建结果保留', 'mode': 'wiki'})
    assert len(fake.knowledge_bases) == 1
    assert next(iter(fake.knowledge_bases)) in str(error.value)


def test_deleting_lifecycle_blocks_another_member_of_same_official_base(library):
    from governance.spaces import persist_space
    store, fake, _ = library
    base = create_base(store, {'name': '跨成员删除锁', 'mode': 'wiki'})
    space = ensure_base_space(store, base['id'])
    other = Store(client=fake, owner_id='another-member')
    other_space = ensure_base_space(other, base['id'])
    persist_space(store, {**space, 'lifecycle': 'deleting'})
    with pytest.raises(StoreError, match='正在删除'):
        require_writable_space(other, other_space['scope'])


def test_legacy_pending_creation_recovers_by_official_id_without_overriding_policy(library, monkeypatch):
    from unittest.mock import Mock
    store, fake, _ = library
    base = fake.create_knowledge_base('配置恢复', wiki_enabled=True, review_enabled=False)
    store._create('knowledge_space', 'legacy-creating', {'scope': 'legacy-creating', 'knowledge_base_id': base['id'],
        'mode': 'wiki', 'lifecycle': 'creating', 'review_policy': {'high_threshold': .85}}, {'scope': 'legacy-creating'})
    write = Mock(side_effect=AssertionError('Recovery must not replace policy'))
    monkeypatch.setattr(fake, 'update_review_settings', write)
    assert ensure_base_space(store, base['id'])['lifecycle'] == 'active'
    assert fake.get_knowledge_base(base['id'])['review_enabled'] is False
    write.assert_not_called()
    assert len(fake.knowledge_bases) == 1


def test_delete_blocks_capture_owned_by_another_bound_member(library):
    store, fake, _ = library
    base = create_base(store, {'name': '共享资料库', 'mode': 'source'})
    other = Store(client=fake, owner_id='another-member')
    other_space = ensure_base_space(other, base['id'])
    job = other.create_job('showdoc', {'item_id': 9}, scope=other_space['scope'])
    with pytest.raises(StoreError, match='采集或同步任务'):
        delete_base(store, base['id'])
    assert base['id'] in fake.knowledge_bases
    other.cancel(job['task_id'])
    assert delete_base(store, base['id'])['lifecycle'] == 'deleted'


def test_expired_upload_ticket_does_not_permanently_block_empty_library_deletion(library):
    from governance.database import connection
    store, fake, _ = library
    base = create_base(store, {'name': '过期上传票据', 'mode': 'source'})
    receipt = store._create('knowledge_upload', 'expired-ticket-hash',
        {'knowledge_base_id': base['id'], 'state': 'uploading'}, {'upload_key': 'expired-ticket-hash'})
    with connection() as conn:
        conn.execute("UPDATE runtime_records SET created_at=now()-interval '61 minutes' WHERE id=%s", (receipt['id'],))
    assert delete_base(store, base['id'])['lifecycle'] == 'deleted'
    assert store._body(receipt['id'])['state'] == 'uploading'


def test_uncertain_completion_receipt_blocks_deletion_during_official_ticket_lifetime(library):
    store, fake, _ = library
    base = create_base(store, {'name': '完成上传结果待确认', 'mode': 'source'})
    store._create('knowledge_upload', 'completion-ticket-hash',
        {'knowledge_base_id': base['id'], 'state': 'completing'}, {'upload_key': 'completion-ticket-hash'})
    with pytest.raises(StoreError, match='分片上传会话'):
        delete_base(store, base['id'])
    assert base['id'] in fake.knowledge_bases


def test_official_delete_permission_denial_preserves_library_and_lifecycle(library, monkeypatch):
    from integrations.contextdb import ContextDBAuthError
    store, fake, http = library
    base = create_base(store, {'name': '云端拒绝删除', 'mode': 'source'})
    space = ensure_base_space(store, base['id'])
    def forbidden(kb_id):
        raise ContextDBAuthError('not allowed to delete', status_code=403, error_code=4007)
    monkeypatch.setattr(fake, 'delete_knowledge_base', forbidden)
    response = http.delete('/api/contextdb/v1/knowledge/knowledge_bases', query_string={'knowledge_base_id': base['id']})
    assert response.status_code == 403 and response.json['source'] == 'contextdb'
    assert get_space(store, space['scope'])['lifecycle'] == 'active'
    assert fake.get_knowledge_base(base['id'])['name'] == '云端拒绝删除'


def test_library_write_lock_serializes_deletion_with_document_creation(library):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from governance.knowledge_bases import base_write_lock
    store, fake, _ = library
    base = create_base(store, {'name': '删除与上传串行', 'mode': 'source'})
    inside, finish = Event(), Event()
    def write_document():
        with base_write_lock(base['id']):
            inside.set()
            assert finish.wait(5)
            fake.create_text_document(base['id'], 'source.md', 'source')
    with ThreadPoolExecutor(max_workers=2) as pool:
        writer = pool.submit(write_document)
        assert inside.wait(5)
        deletion = pool.submit(delete_base, store, base['id'])
        assert not deletion.done()
        finish.set()
        writer.result(timeout=5)
        with pytest.raises(StoreError, match='非空'):
            deletion.result(timeout=5)
    assert base['id'] in fake.knowledge_bases


def test_review_only_id_cannot_bypass_library_deletion_guard(library, monkeypatch):
    from unittest.mock import Mock
    from governance.spaces import persist_space
    store, fake, http = library
    base = create_base(store, {'name': '评审动作删除门禁', 'mode': 'wiki'})
    space = ensure_base_space(store, base['id'])
    fake.reviews['r-guard'] = {'review_id': 'r-guard', 'knowledge_base_id': base['id'],
        'document_id': 'd', 'lifecycle_state': 'pending_human', 'review_status': 'pending'}
    write = Mock(side_effect=AssertionError('Deleting libraries must not accept review actions'))
    monkeypatch.setattr(fake, 'review_action', write)
    persist_space(store, {**space, 'lifecycle': 'deleting'})
    for path in ('/api/kb/reviews/r-guard/action', '/api/contextdb/v1/knowledge/reviews/action'):
        response = http.post(path, json={'review_id': 'r-guard', 'action': 'confirm'})
        assert response.status_code == 409
    write.assert_not_called()


def test_knowledge_base_name_uses_official_255_character_limit(library):
    store, fake, http = library
    name = '知' * 255
    base = create_base(store, {'name': '  ' + name + '  ', 'mode': 'source'})
    assert base['name'] == name
    path = '/api/contextdb/v1/knowledge/knowledge_bases'
    assert http.post(path, json={'name': name + '识'}).status_code == 400
    assert http.put(path, json={'knowledge_base_id': base['id'], 'name': name + '识'}).status_code == 400
    assert fake.get_knowledge_base(base['id'])['name'] == name and len(fake.knowledge_bases) == 1


def test_native_creation_uses_official_graph_and_review_defaults(library):
    _, fake, http = library
    response = http.post('/api/contextdb/v1/knowledge/knowledge_bases', json={'name': '官方默认开关'})
    assert response.status_code == 200
    base = fake.get_knowledge_base(response.json['data']['id'])
    assert base['graph_enabled'] is True and base['review_enabled'] is False


def test_library_list_reads_all_bases_once_without_name_hiding(library, monkeypatch):
    from unittest.mock import Mock
    store, fake, _ = library
    for index in range(100):
        fake.create_knowledge_base(str(index))
    base = fake.create_knowledge_base('_governance')
    read = Mock(wraps=fake.list_knowledge_bases)
    monkeypatch.setattr(fake, 'list_knowledge_bases', read)
    spaces, _ = list_spaces(store)
    assert len(spaces) == 101 and base['id'] in {space['knowledge_base_id'] for space in spaces}
    read.assert_called_once_with()


def test_native_batch_delete_needs_ids_without_an_action(library, monkeypatch):
    from unittest.mock import Mock
    store, fake, http = library
    base = create_base(store, {'name': '评审记录', 'mode': 'source'})
    fake.reviews['r-delete'] = {'review_id': 'r-delete', 'knowledge_base_id': base['id'],
        'lifecycle_state': 'approved'}
    write = Mock(return_value={'total': 1, 'succeeded': 1, 'failed': 0,
        'results': [{'id': 'r-delete', 'success': True}]})
    monkeypatch.setattr(fake, '_request', write)
    response = http.delete('/api/contextdb/v1/knowledge/reviews/batch', json={'ids': ['r-delete']})
    assert response.status_code == 200 and response.json['data']['succeeded'] == 1
    write.assert_called_once_with('DELETE', '/v1/knowledge/reviews/batch',
                                 json_body={'ids': ['r-delete']}, params={})
    assert fake.get_knowledge_base(base['id'])['name'] == '评审记录'


@pytest.mark.parametrize('method', ['POST', 'DELETE'])
def test_native_batch_preserves_valid_items_when_another_library_is_deleting(library, monkeypatch, method):
    from unittest.mock import Mock
    from governance.spaces import persist_space
    store, fake, http = library
    for review_id in ('blocked', 'valid'):
        base = create_base(store, {'name': review_id, 'mode': 'source'})
        fake.reviews[review_id] = {'review_id': review_id, 'knowledge_base_id': base['id'],
            'lifecycle_state': 'pending_human'}
        if review_id == 'blocked':
            space = ensure_base_space(store, base['id'])
            persist_space(store, {**space, 'lifecycle': 'deleting'})
    write = Mock(return_value={'results': [{'id': 'valid', 'success': True}]})
    monkeypatch.setattr(fake, '_request', write)
    body = {'ids': ['blocked', 'missing', 'valid']}
    if method == 'POST':
        body['action'] = 'confirm'
    response = http.open('/api/contextdb/v1/knowledge/reviews/batch', method=method, json=body)
    assert response.status_code == 200
    result = response.json['data']
    assert (result['total'], result['succeeded'], result['failed']) == (3, 1, 2)
    assert [item['success'] for item in result['results']] == [False, False, True]
    assert '正在删除' in result['results'][0]['error']
    assert 'not found' in result['results'][1]['error']
    write.assert_called_once_with(method, '/v1/knowledge/reviews/batch',
                                 json_body={**body, 'ids': ['valid']}, params={})
