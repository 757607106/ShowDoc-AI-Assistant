"""ContextDB-backed Store 契约测试(内存替身):任务/claim/语料/发布全链路。"""
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance.store import Store, StoreError, now
from tests.contextdb_fake import FakeContextDBClient


def make_store():
    client = FakeContextDBClient()
    store = Store(client=client, kb_name='_test_governance')
    store.initialize()
    return store, client


def test_initialize_uses_postgres_without_cloud_knowledge_storage():
    store, client = make_store()
    assert client.knowledge_bases == {}
    from governance.database import connection
    with connection() as conn:
        assert conn.execute('SELECT count(*) FROM runtime_records').fetchone()['count'] == 0


def test_job_lifecycle_and_volatile_fast_path():
    store, _ = make_store()
    job = store.create_job('file', {'file_paths': ['a.md']}, applicability={'product': 'P'})
    assert job['status'] == 'pending' and job['scope'] == 'default'
    store.update_job(job['task_id'], status='running', phase='crawling', progress=30, message='爬取中')
    got = store.get_job(job['task_id'])
    assert got['status'] == 'running' and got['phase'] == 'crawling' and got['progress'] == 30
    store.log(job['task_id'], '日志1')
    store.log(job['task_id'], '日志2', current_item='doc1')
    got = store.get_job(job['task_id'])
    assert [entry['message'] for entry in got['logs']] == ['日志1', '日志2']
    assert got['message'] == '日志2' and got['current_item'] == 'doc1'
    store.update_job(job['task_id'], status='failed', phase='failed', end_time=now())
    got = store.get_job(job['task_id'])
    assert got['status'] == 'failed'


def test_cancel_flips_metadata_only():
    store, client = make_store()
    job = store.create_job('file', {})
    store.cancel(job['task_id'])
    got = store.get_job(job['task_id'])
    assert got['cancel_requested'] is True and got['status'] == 'cancelled' and got['phase'] == 'cancelled'


def test_claim_serializes_and_guards_attempt_token():
    store, _ = make_store()
    first = store.create_job('file', {})
    second = store.create_job('file', {})
    claimed = store.claim()
    assert claimed['task_id'] == first['task_id']
    assert claimed['attempt_token']
    assert store.claim() is None, '运行中存在时不应再 claim'
    store.active_attempt = (first['task_id'], 'wrong')
    with __import__('pytest').raises(StoreError):
        store.update_job(first['task_id'], message='不应写入')
    store.active_attempt = (first['task_id'], claimed['attempt_token'])
    store.update_job(first['task_id'], status='failed', phase='failed', end_time=now())
    store.release_claim(first['task_id'])
    nxt = store.claim()
    assert nxt['task_id'] == second['task_id']


def _generation(store, scope):
    return store._scope_generation(store._scope_doc(scope))


def test_ingest_and_version_flips():
    store, _ = make_store()
    store.create_job('web', {'url': 'https://example.com/docs'}, scope='web:example.com')
    claimed = store.claim()
    documents = [{'id': 's1', 'title': '文档A', 'category': 'C', 'content': '正文A',
                  'metadata': {'conversion': {'fingerprint': 'f1'}}}]
    sources = {'s1': {'source_format': 'html', 'source_sha256': 'sha-a', 'content': '原始A'}}
    chunks = [{'document_id': 's1', 'content': '片段A', 'chunk_index': 0}]
    changed = store.ingest(claimed, documents, sources, chunks)
    assert changed is True
    assert _generation(store, 'web:example.com') == 1
    listing = store.list_documents()
    assert len(listing) == 1 and listing[0]['title'] == '文档A' and listing[0]['is_current']
    version_id = listing[0]['version_id']
    detail = store.get_document(version_id)
    assert detail['is_current'] and detail['content'] == '正文A'
    # 同内容重摄取幂等(changed=False),世代不变
    changed2 = store.ingest(claimed, documents, sources, chunks)
    assert changed2 is False
    assert _generation(store, 'web:example.com') == 1
    # 新版本翻转 is_current
    documents2 = [dict(documents[0], content='正文A v2')]
    store.ingest(claimed, documents2, sources, chunks)
    assert _generation(store, 'web:example.com') == 2
    current = store.list_documents()
    assert len(current) == 1 and store.get_document(current[0]['version_id'])['content'] == '正文A v2'
    assert store.get_document(version_id)['is_current'] is False


def test_ingest_rolls_back_all_records_and_retries_after_midway_failure(monkeypatch):
    from governance.store import data_dir
    store, _ = make_store()
    job = store.create_job('file', {}, scope='atomic')
    documents = [{'id': 's1', 'title': '文档', 'category': '', 'content': 'v1', 'metadata': {}}]
    sources = {'s1': {'source_sha256': 'sha-v1'}}
    assert store.ingest(job, documents, sources, []) is True
    original_version = store.list_documents()[0]['version_id']
    original_generation = _generation(store, 'atomic')
    snapshots_before = set(data_dir().rglob('*.json'))

    update_metadata = store._update_metadata
    should_fail = True

    def fail_scope_generation(metadata, *, document_id, _connection=None):
        if should_fail and metadata.get('type') == 'scope' and metadata.get('generation', 0) > original_generation:
            raise RuntimeError('injected failure before ingest commit')
        return update_metadata(metadata, document_id=document_id, _connection=_connection)

    monkeypatch.setattr(store, '_update_metadata', fail_scope_generation)
    revised = [{**documents[0], 'content': 'v2'}]
    revised_sources = {'s1': {'source_sha256': 'sha-v2'}}
    with pytest.raises(RuntimeError, match='injected failure'):
        store.ingest(job, revised, revised_sources, [])

    current = store.list_documents()
    assert len(current) == 1 and current[0]['version_id'] == original_version
    assert store.get_document(original_version)['content'] == 'v1'
    assert _generation(store, 'atomic') == original_generation
    assert len(store._list({'type': 'version'})) == 1
    assert len(store._list({'type': 'jobdoc', 'job_id': job['task_id']})) == 1
    # A rolled-back insert may leave an orphan snapshot, but no committed row may reference a missing file.
    new_snapshots = set(data_dir().rglob('*.json')) - snapshots_before
    assert len(new_snapshots) == 1 and all(path.is_file() for path in new_snapshots)
    for version in store._list({'type': 'version'}):
        store._body(version['id'])

    should_fail = False
    assert store.ingest(job, revised, revised_sources, []) is True
    assert _generation(store, 'atomic') == original_generation + 1
    current = store.list_documents()
    assert len(current) == 1 and current[0]['version_id'] != original_version
    assert store.get_document(current[0]['version_id'])['content'] == 'v2'
    assert store.get_document(original_version)['is_current'] is False
    assert len(store._list({'type': 'version'})) == 2
    assert len(store._list({'type': 'jobdoc', 'job_id': job['task_id']})) == 2
    for version in store._list({'type': 'version'}):
        store._body(version['id'])


def test_same_source_in_different_spaces_keeps_independent_versions_and_legacy_ids():
    from governance.store import digest
    store, _ = make_store()
    first = store.create_job('web', {'url':'https://example.com/docs'}, scope='a')
    second = store.create_job('web', {'url':'https://example.com/docs'}, scope='b')
    legacy_id = digest([store.owner_id, first['source_key'], 's1'])
    store._create('doc', legacy_id, {'doc_id':legacy_id}, {'doc_id':legacy_id,'scope':'a'})
    documents = [{'id':'s1','title':'Source','content':'Original','metadata':{}}]
    store.ingest(first, documents, {'s1':{}}, [])
    a = store.list_documents(first['task_id'])[0]
    store.ingest(second, documents, {'s1':{}}, [])
    b = store.list_documents(second['task_id'])[0]
    assert a['id'] == legacy_id and b['id'] != a['id']
    assert store.get_document(a['version_id'])['scope'] == 'a'
    assert store.get_document(b['version_id'])['scope'] == 'b'
    store.ingest(second, [{**documents[0], 'content':'Changed in B'}], {'s1':{}}, [])
    assert store.get_document(a['version_id'])['is_current']
    assert not store.get_document(b['version_id'])['is_current']
    assert store.ingest(first, documents, {'s1':{}}, []) is False
    for job in (first, second):
        store.update_job(job['task_id'], status='completed', capture_complete=True)
        scope, _, rows = store.release_inputs(job['task_id'])
        assert scope == job['scope'] and len(rows) == 1


def test_release_flow_and_activation():
    store, client = make_store()
    from governance.spaces import persist_space
    kb = client.create_knowledge_base('发布资料', wiki_enabled=True, graph_enabled=False, review_enabled=True)
    persist_space(store, {'scope': 'default', 'name': kb['name'], 'knowledge_base_id': kb['id'],
        'mode': 'wiki', 'lifecycle': 'active'})
    store.create_job('file', {}, scope='default')
    claimed = store.claim()
    job = claimed
    store.ingest(claimed, [{'id': 's1', 'title': 'T', 'category': '', 'content': 'C',
                            'metadata': {}}], {'s1': {}}, [])
    store.update_job(job['task_id'], capture_complete=True, summary={'total_documents': 1})
    version_id = store.list_documents()[0]['version_id']
    store.update_job(job['task_id'], status='completed', phase='completed', zip_file='x.zip')
    from governance.worker import publish
    release_id = publish(store, job['task_id'])
    listing = store.list_releases()
    assert listing[0]['id'] == release_id and listing[0]['active'] is True
    got = store.get_release(release_id)
    assert got['version_ids'] == [version_id]
    assert publish(store, job['task_id']) == release_id, '重复发布幂等'
    # 发布后应入队 ctxdb_sync 任务
    sync_jobs = [item for item in store.list_jobs() if item['kind'] == 'ctxdb_sync']
    assert sync_jobs and sync_jobs[0]['params']['release_id'] == release_id
    assert sync_jobs[0]['params']['knowledge_base_id'] == kb['id']


def test_concurrent_submissions_keep_one_current_snapshot():
    from concurrent.futures import ThreadPoolExecutor
    store, _ = make_store()
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(lambda index: store.create_release(
            f'job-{index}', 'same-space', index, [], '/tmp/fixture.zip'), range(4)))
    current = [row for row in store.list_releases() if row['active']]
    assert len(current) == 1 and current[0]['id'] in ids
    store.activate_release(ids[0])
    assert [row['id'] for row in store.list_releases() if row['active']] == [ids[0]]


def test_release_blocked_for_empty_content():
    store, _ = make_store()
    store.create_job('file', {}, scope='default')
    claimed = store.claim()
    store.ingest(claimed, [{'id': 's1', 'title': 'T', 'category': '', 'content': '  ',
                            'metadata': {}}], {'s1': {}}, [])
    store.update_job(claimed['task_id'], capture_complete=True, status='completed', phase='completed')
    with __import__('pytest').raises(StoreError) as excinfo:
        store.release_inputs(claimed['task_id'])
    assert '空正文' in str(excinfo.value)


def test_release_inputs_guards():
    store, _ = make_store()
    job = store.create_job('file', {}, scope='default')
    with __import__('pytest').raises(StoreError) as excinfo:
        store.release_inputs(job['task_id'])
    assert '不能提交治理' in str(excinfo.value)


def test_completed_same_collection_supersedes_old_failures_but_not_other_selections():
    import pytest
    store, _ = make_store()
    old = store.create_job('cyb', {}, scope='default')
    store.update_job(old['task_id'],status='partial',capture_complete=False)
    complete = store.create_job('cyb', {}, scope='default')
    store.ingest(complete,[{'id':'s1','title':'来源','content':'原文','metadata':{}}],{'s1':{}},[])
    store.update_job(complete['task_id'],status='completed',capture_complete=True)
    assert len(store.release_inputs(complete['task_id'])[2]) == 1
    separate = store.create_job('cyb', {}, selected_ids=['extra'], scope='default')
    store.update_job(separate['task_id'],status='partial',capture_complete=False)
    with pytest.raises(StoreError,match='未完整采集'):
        store.release_inputs(complete['task_id'])
    assert store.get_job(old['task_id'])['status'] == 'partial'


def test_recover_jobs_resets_orphans():
    store, _ = make_store()
    job = store.create_job('file', {})
    claimed = store.claim()
    assert claimed['task_id'] == job['task_id']
    store.recover_jobs(reset_all=True)
    got = store.get_job(job['task_id'])
    assert got['status'] == 'failed' and got.get('attempt_token') is None


def test_heartbeat_and_worker_alive():
    store, _ = make_store()
    assert store.worker_alive() is False
    store.heartbeat()
    assert store.worker_alive() is True
