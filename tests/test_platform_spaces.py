"""Business-space routing and native retries, using isolated Docker PostgreSQL and no cloud writes."""
import json
import io
import os
from zipfile import ZipFile

import pytest

import app as app_module
from governance.contextdb_sync import _save, enqueue_sync, run_sync
from governance.spaces import get_space, list_spaces, progress, retry, retry_stages, save_space, submit_current
from governance.store import Store, StoreError
from integrations.contextdb import ContextDBError
from tests.contextdb_fake import FakeContextDBClient


@pytest.fixture
def spaces(tmp_path, authenticated_client):
    fake = FakeContextDBClient()
    store = Store(client=fake, owner_id=os.environ['TEST_PLATFORM_USER'])
    app_module.app.extensions['governance_store'] = store
    yield store, fake, authenticated_client, tmp_path
    app_module.app.extensions.pop('governance_store', None)


def release(store, tmp_path, scope):
    path = tmp_path / (scope + '.zip')
    with ZipFile(path, 'w') as archive:
        archive.writestr('rag_documents.jsonl', json.dumps({'id': 'source-1', 'version_id': 'v1', 'content': '# Source'}))
    return store.create_release('capture-1', scope, 1, ['v1'], str(path))


def mapped_document(store, fake, mode='wiki', **fields):
    kb = fake.create_knowledge_base('source-' + mode, wiki_enabled=mode == 'wiki', graph_enabled=mode == 'graph')
    space = save_space(store, {'name': '业务知识', 'graph_enabled': mode == 'graph', mode + '_kb_id': kb['id']})
    doc = fake.create_text_document(kb['id'], 'source.md', 'source')
    fake.documents[doc['id']].update(fields)
    _save(store.owner_id, space['scope'], 'source-1', mode, kb['id'], document_id=doc['id'], status='succeeded')
    return space, doc


def test_create_space_is_metadata_only_and_defaults_to_wiki(spaces):
    store, fake, http, _ = spaces
    response = http.post('/api/kb/spaces', json={'name': '产品资料'})
    assert response.status_code == 201
    space = response.json['space']
    assert space['scope'].startswith('space-') and space['graph_enabled'] is False
    assert space['wiki_kb_id'] is None and fake.knowledge_bases == {}
    assert http.get('/api/kb/spaces').json['spaces'][0]['scope'] == space['scope']
    assert http.get('/api/kb/spaces/unknown').status_code == 404
    assert http.patch('/api/kb/spaces/' + space['scope'], json={'graph_enabled': 'false'}).status_code == 400


def test_file_capture_auto_submits_and_later_graph_enable_shares_the_same_source(spaces, monkeypatch):
    from governance.worker import process_job
    store, fake, http, _ = spaces
    monkeypatch.setattr('webapi.auth.client_for_user', lambda *args: fake)
    space = http.post('/api/kb/spaces', json={'name':'完整流程'}).json['space']
    scope = space['scope']
    source = b'component,depends_on\nAPI,Database\n'
    response = http.post('/api/uploads', data={'space_scope':scope, 'files':(io.BytesIO(source),'dependencies.csv')})
    assert response.status_code == 200
    capture = store.claim()
    assert capture['task_id'] == response.json['task_id'] and capture['attempt_token']
    process_job(Store(client=fake, owner_id=store.owner_id), capture)
    assert store.get_job(capture['task_id'])['status'] == 'completed'
    assert fake.documents == {}, 'capture completion only queues delivery; cloud ingestion is asynchronous'
    status = http.get(f"/task_status/{capture['task_id']}").json
    assert status['phase'] == 'submitted' and not status['submit_available'] and status['submission_id']
    assert len([job for job in store.list_jobs() if job['kind'] == 'ctxdb_sync']) == 1
    sync_job = next(job for job in store.list_jobs() if job['kind'] == 'ctxdb_sync')
    assert sync_job['params']['target_modes'] == ['wiki']
    result = run_sync(store, sync_job)
    assert result['uploaded'] == 1 and len(fake.documents) == 1
    wiki_doc = next(iter(fake.documents.values()))
    assert wiki_doc['text'].encode() == source
    assert http.patch('/api/kb/spaces/' + scope, json={'graph_enabled':True}).status_code == 200
    response = http.post('/api/kb/spaces/' + scope + '/submit')
    assert response.status_code == 200
    result = run_sync(store, store.get_job(response.json['result']['task_id']))
    assert result['uploaded'] == 1 and result['skipped'] == 1 and len(fake.documents) == 2
    rows = http.get('/api/kb/spaces/' + scope + '/progress').json['mappings']
    assert {row['target_mode'] for row in rows} == {'wiki','graph'}
    assert len({row['source_version'] for row in rows}) == 1
    assert wiki_doc['id'] == next(row['document_id'] for row in rows if row['target_mode'] == 'wiki')


def test_auto_submission_failure_preserves_capture_and_retries_existing_release(spaces, monkeypatch):
    from governance import worker
    store, fake, http, _ = spaces
    monkeypatch.setattr('webapi.auth.client_for_user', lambda *args: fake)
    scope = http.post('/api/kb/spaces', json={'name': '提交恢复'}).json['space']['scope']
    response = http.post('/api/uploads', data={'space_scope': scope, 'files': (io.BytesIO(b'# source'), 'source.md')})
    job = store.get_job(response.json['task_id'])
    enqueue = worker.enqueue_sync
    def fail_enqueue(*args, **kwargs):
        raise RuntimeError('queue unavailable')
    monkeypatch.setattr(worker, 'enqueue_sync', fail_enqueue)
    worker.process_job(store, job)
    captured = store.get_job(job['task_id'])
    assert captured['status'] == 'completed' and captured['capture_complete']
    assert captured['phase'] == 'submission_failed' and 'queue unavailable' in captured['message']
    before = http.get(f"/task_status/{job['task_id']}").json
    assert before['submit_available'] and before['submission_id'] and before['download_available']
    assert len(store.list_documents(job['task_id'])) == 1 and fake.documents == {}
    monkeypatch.setattr(worker, 'enqueue_sync', enqueue)
    first = http.post(f"/tasks/{job['task_id']}/submit")
    second = http.post(f"/tasks/{job['task_id']}/submit")
    assert first.status_code == second.status_code == 200
    assert first.json['release_id'] == second.json['release_id'] == before['submission_id']
    sync_jobs = [row for row in store.list_jobs() if row['kind'] == 'ctxdb_sync']
    assert len(sync_jobs) == 1
    after = http.get(f"/task_status/{job['task_id']}").json
    assert not after['submit_available'] and after['phase'] == 'submitted'
    assert run_sync(store, sync_jobs[0])['uploaded'] == 1


def test_partial_file_capture_waits_for_successful_retry_before_auto_submission(spaces, monkeypatch):
    from crawlers.file import FileCrawler
    from governance.worker import process_job
    store, fake, http, _ = spaces
    monkeypatch.setattr('webapi.auth.client_for_user', lambda *args: fake)
    scope = http.post('/api/kb/spaces', json={'name': '部分失败恢复'}).json['space']['scope']
    response = http.post('/api/uploads', data={'space_scope': scope,
        'files': [(io.BytesIO(b'# good'), 'good.md'), (io.BytesIO(b'# bad'), 'bad.md')]})
    job = store.get_job(response.json['task_id'])
    fetch = FileCrawler.fetch_document
    def fail_one(crawler, stub):
        if stub.title.endswith('bad'):
            raise RuntimeError('temporary source failure')
        return fetch(crawler, stub)
    monkeypatch.setattr(FileCrawler, 'fetch_document', fail_one)
    process_job(store, job)
    partial = store.get_job(job['task_id'])
    assert partial['status'] == 'partial' and not partial['capture_complete']
    assert len(store.list_documents(job['task_id'])) == 1
    assert store.list_releases() == [] and fake.documents == {}
    assert not any(row['kind'] == 'ctxdb_sync' for row in store.list_jobs())
    monkeypatch.setattr(FileCrawler, 'fetch_document', fetch)
    response = http.post(f"/tasks/{job['task_id']}/retry")
    assert response.status_code == 200
    retried = store.get_job(response.json['task_id'])
    process_job(store, retried)
    assert store.get_job(retried['task_id'])['phase'] == 'submitted'
    sync_jobs = [row for row in store.list_jobs() if row['kind'] == 'ctxdb_sync']
    assert len(sync_jobs) == 1 and run_sync(store, sync_jobs[0])['uploaded'] == 2


def test_auto_submission_keeps_queued_result_when_status_write_fails(spaces, monkeypatch):
    from governance.worker import process_job
    store, fake, http, _ = spaces
    monkeypatch.setattr('webapi.auth.client_for_user', lambda *args: fake)
    scope = http.post('/api/kb/spaces', json={'name': '状态恢复'}).json['space']['scope']
    response = http.post('/api/uploads', data={'space_scope': scope, 'files': (io.BytesIO(b'# source'), 'source.md')})
    update = store.update_job
    failed = False
    def fail_status_once(job_id, **changes):
        nonlocal failed
        if changes.get('phase') == 'submitted' and not failed:
            failed = True
            raise RuntimeError('temporary status write failure')
        return update(job_id, **changes)
    monkeypatch.setattr(store, 'update_job', fail_status_once)
    process_job(store, store.get_job(response.json['task_id']))
    task = http.get(f"/task_status/{response.json['task_id']}").json
    assert failed and task['phase'] == 'submitted' and not task['submit_available']
    assert '自动提交失败' not in task['message']
    assert len([row for row in store.list_jobs() if row['kind'] == 'ctxdb_sync']) == 1


def test_legacy_space_preserves_existing_ids_without_cloud_mutation(spaces):
    store, fake, _, _ = spaces
    wiki = fake.create_knowledge_base('knowledge-default', wiki_enabled=True, graph_enabled=False)
    graph = fake.create_knowledge_base('knowledge-default-graph', wiki_enabled=False, graph_enabled=True)
    extra = fake.create_knowledge_base('another-wiki', wiki_enabled=True, graph_enabled=False)
    spaces_list, available = list_spaces(store)
    assert len(spaces_list) == 1 and spaces_list[0]['graph_enabled'] is True
    assert spaces_list[0]['wiki_kb_id'] == wiki['id'] and spaces_list[0]['graph_kb_id'] == graph['id']
    assert [item['id'] for item in available] == [extra['id']]
    assert store._list({'type': 'knowledge_space'}) == []
    changed = save_space(store, {'graph_enabled': False}, 'default')
    assert changed['graph_kb_id'] == graph['id'] and graph['id'] in fake.knowledge_bases


def test_binding_validates_mode_and_cannot_replace_existing_ids(spaces):
    store, fake, http, _ = spaces
    graph = fake.create_knowledge_base('graph', graph_enabled=True)
    wiki = fake.create_knowledge_base('wiki', wiki_enabled=True)
    other = fake.create_knowledge_base('other', wiki_enabled=True)
    assert http.post('/api/kb/spaces', json={'name': '错误', 'wiki_kb_id': graph['id']}).status_code == 409
    response = http.post('/api/kb/spaces', json={'name': '绑定', 'wiki_kb_id': wiki['id']})
    scope = response.json['space']['scope']
    assert http.patch('/api/kb/spaces/' + scope, json={'wiki_kb_id': other['id']}).status_code == 409
    assert http.post('/api/kb/spaces', json={'name': '重复绑定', 'wiki_kb_id': wiki['id']}).status_code == 409
    assert get_space(store, scope)['wiki_kb_id'] == wiki['id']
    with pytest.raises(StoreError, match='不存在'):
        get_space(Store(client=fake, owner_id='another-user'), scope)


def test_target_snapshot_respects_scope_toggle_and_keeps_existing_libraries(spaces):
    store, fake, _, tmp_path = spaces
    space = save_space(store, {'name': 'Wiki 优先'})
    scope = space['scope']
    release_id = release(store, tmp_path, scope)
    first = enqueue_sync(store, release_id, scope)
    assert first['params']['target_modes'] == ['wiki']
    save_space(store, {'graph_enabled': True}, scope)
    assert run_sync(store, first)['uploaded'] == 1
    assert not any(kb.get('graph_enabled') for kb in fake.knowledge_bases.values())
    second = enqueue_sync(store, release_id, scope)
    save_space(store, {'graph_enabled': False}, scope)
    result = run_sync(store, second)
    assert result['uploaded'] == 1 and result['skipped'] == 1
    graph_id = get_space(store, scope)['graph_kb_id']
    assert graph_id in fake.knowledge_bases
    assert enqueue_sync(store, release_id, scope)['params']['target_modes'] == ['wiki']


def test_upload_retry_targets_failed_side_and_rejects_duplicate_active_job(spaces, monkeypatch):
    store, fake, _, tmp_path = spaces
    space = save_space(store, {'name': '双库', 'graph_enabled': True})
    scope = space['scope']
    upload = fake.upload_file
    def fail_graph(kb_id, *args, **kwargs):
        if fake.get_knowledge_base(kb_id).get('graph_enabled'):
            raise ContextDBError('quota exceeded', status_code=429)
        return upload(kb_id, *args, **kwargs)
    monkeypatch.setattr(fake, 'upload_file', fail_graph)
    job = enqueue_sync(store, release(store, tmp_path, scope), scope)
    result = run_sync(store, job)
    assert result['uploaded'] == 1 and len(result['errors']) == 1
    with pytest.raises(StoreError, match='提交成功'):
        retry(store, scope, {'stage': 'upload', 'target_mode': 'wiki', 'task_id': job['task_id']})
    queued = retry(store, scope, {'stage': 'upload', 'target_mode': 'graph', 'task_id': job['task_id']})
    with pytest.raises(StoreError, match='已有重试'):
        retry(store, scope, {'stage': 'upload', 'target_mode': 'graph', 'task_id': job['task_id']})
    monkeypatch.setattr(fake, 'upload_file', upload)
    retried = store.get_job(queued['task_id'])
    assert retried['params']['target_modes'] == ['graph']
    assert run_sync(store, retried)['uploaded'] == 1
    assert len(fake.documents) == 2


def test_native_ingest_retry_requires_official_recovery_hint_and_deduplicates(spaces, monkeypatch):
    store, fake, http, _ = spaces
    space, doc = mapped_document(store, fake, ingest_status='failed', latest_ingest_event_id='failed-event')
    path = '/api/kb/spaces/' + space['scope']
    body = {'stage': 'ingest', 'target_mode': 'wiki', 'source_id': 'source-1'}
    assert http.post(path + '/retry', json=body).status_code == 409
    fake.documents[doc['id']]['recovery_actions'] = ['retry']
    calls = []
    monkeypatch.setattr(fake, 'retry_document', lambda doc_id: calls.append(doc_id) or {'event_id': 'retry-event', 'status': 'processing'}, raising=False)
    assert http.get(path + '/progress').json['mappings'][0]['retry_stages'] == ['ingest']
    assert http.post(path + '/retry', json=body).json['result']['status'] == 'processing'
    assert http.post(path + '/retry', json=body).status_code == 409
    assert calls == [doc['id']]
    fake.documents[doc['id']].update(ingest_status='pending_review', recovery_actions=['retry'])
    assert http.get(path + '/progress').json['mappings'][0]['retry_stages'] == []


def test_graph_retry_calls_only_official_build_and_requires_scope_enabled(spaces, monkeypatch):
    store, fake, _, _ = spaces
    space, doc = mapped_document(store, fake, 'graph', graph_status='failed', latest_graph_event_id='graph-old')
    calls = []
    def request(method, path, **kwargs):
        calls.append((method, path, kwargs['json_body']))
        return {'event_id': 'graph-new', 'status': 'queued'}
    monkeypatch.setattr(fake, '_request', request, raising=False)
    result = retry(store, space['scope'], {'stage': 'graph', 'target_mode': 'graph', 'source_id': 'source-1'})
    assert result['status'] == 'queued'
    assert calls == [('POST', '/v1/knowledge/events', {'document_id': doc['id'], 'event_type': 'graph_build'})]
    save_space(store, {'graph_enabled': False}, space['scope'])
    assert progress(store, space['scope'])['mappings'][0]['retry_stages'] == []
    with pytest.raises(StoreError, match='关闭'):
        retry(store, space['scope'], {'stage': 'graph', 'target_mode': 'graph', 'source_id': 'source-1'})


@pytest.mark.parametrize('graph_status', ['skipped', None, ''])
def test_unbuilt_ingested_graph_documents_can_build_once(spaces, monkeypatch, graph_status):
    store, fake, http, _ = spaces
    space, doc = mapped_document(store, fake, 'graph', graph_status=graph_status, latest_graph_event_id=None)
    path = '/api/kb/spaces/' + space['scope']
    calls = []
    monkeypatch.setattr(fake, '_request', lambda method, path, **kwargs:
        calls.append((method, path, kwargs['json_body'])) or {'event_id': 'graph-new', 'status': 'queued'}, raising=False)
    assert http.get(path + '/progress').json['mappings'][0]['retry_stages'] == ['graph']
    body = {'stage': 'graph', 'target_mode': 'graph', 'source_id': 'source-1'}
    response = http.post(path + '/retry', json=body)
    assert response.status_code == 200 and response.json['result']['status'] == 'queued'
    assert http.post(path + '/retry', json=body).status_code == 409
    assert calls == [('POST', '/v1/knowledge/events', {'document_id': doc['id'], 'event_type': 'graph_build'})]
    assert fake.documents[doc['id']]['graph_status'] == graph_status, 'acceptance is not graph completion'


def test_graph_build_requires_known_unbuilt_state_and_completed_ingest():
    for state in ('pending', 'queued', 'processing', 'succeeded', 'unknown'):
        assert retry_stages({'ingest_status': 'succeeded', 'graph_status': state}, 'graph') == []
    for detail in ({}, {'graph_status': None}, {'latest_graph_event_id': None},
                   {'graph_status': '', 'latest_graph_event_id': 'in-flight-event'}):
        assert retry_stages({'ingest_status': 'succeeded', **detail}, 'graph') == []
    for state in ('pending_review', 'processing', 'failed'):
        assert retry_stages({'ingest_status': state, 'graph_status': 'skipped'}, 'graph') == []
    assert retry_stages({'ingest_status': 'succeeded', 'graph_status': 'skipped'}, 'wiki') == []


def test_unbuilt_graph_cannot_build_when_official_library_disabled(spaces, monkeypatch):
    store, fake, http, _ = spaces
    space, doc = mapped_document(store, fake, 'graph', graph_status='skipped')
    fake.knowledge_bases[doc['knowledge_base_id']]['graph_enabled'] = False
    calls = []
    monkeypatch.setattr(fake, '_request', lambda *args, **kwargs: calls.append(args), raising=False)
    response = http.post('/api/kb/spaces/' + space['scope'] + '/retry', json={
        'stage': 'graph', 'target_mode': 'graph', 'source_id': 'source-1'})
    assert response.status_code == 409 and '官方知识库未启用图谱' in response.json['message']
    assert calls == []


@pytest.mark.parametrize('stage', ['ingest', 'graph'])
def test_unknown_native_retry_result_is_not_blindly_repeated(spaces, monkeypatch, stage):
    store, fake, _, _ = spaces
    mode = 'graph' if stage == 'graph' else 'wiki'
    fields = {'graph_status': 'skipped'} if stage == 'graph' else {'ingest_status': 'failed', 'recovery_actions': ['retry']}
    space, doc = mapped_document(store, fake, mode, **fields)
    calls = []
    def timeout(*args, **kwargs):
        calls.append(doc['id'])
        raise ContextDBError('connection lost')
    monkeypatch.setattr(fake, '_request' if stage == 'graph' else 'retry_document', timeout, raising=False)
    body = {'stage': stage, 'target_mode': mode, 'source_id': 'source-1'}
    with pytest.raises(ContextDBError):
        retry(store, space['scope'], body)
    with pytest.raises(StoreError, match='结果未知'):
        retry(store, space['scope'], body)
    assert calls == [doc['id']]


def test_progress_preserves_official_unknown_states_and_no_wiki_retry(spaces):
    store, fake, _, _ = spaces
    space, doc = mapped_document(store, fake, wiki_status='failed')
    row = progress(store, space['scope'])['mappings'][0]
    assert row['official']['wiki_status'] == 'failed' and row['retry_stages'] == []
    assert 'graph_status' not in row['official']
    with pytest.raises(StoreError, match='已支持'):
        retry(store, space['scope'], {'stage': 'wiki', 'target_mode': 'wiki', 'source_id': 'source-1'})
    assert fake.documents[doc['id']]['ingest_status'] == 'succeeded'


def test_legacy_default_cannot_be_shadowed_or_bound_twice(spaces):
    store, fake, http, _ = spaces
    original = fake.create_knowledge_base('knowledge-default', wiki_enabled=True)
    other = fake.create_knowledge_base('other', wiki_enabled=True)
    assert http.post('/api/kb/spaces', json={'scope': 'default', 'name': '覆盖', 'wiki_kb_id': other['id']}).status_code == 409
    assert http.post('/api/kb/spaces', json={'name': '重复', 'wiki_kb_id': original['id']}).status_code == 409
    assert get_space(store, 'default')['wiki_kb_id'] == original['id']


def test_current_submission_can_fill_new_graph_target_without_recapture(spaces):
    store, fake, http, tmp_path = spaces
    space = save_space(store, {'name': '补全图谱'})
    assert space['has_submission'] is False
    scope = space['scope']
    assert http.post(f'/api/kb/spaces/{scope}/submit').status_code == 409
    job = enqueue_sync(store, release(store, tmp_path, scope), scope)
    run_sync(store, job)
    save_space(store, {'graph_enabled': True}, scope)
    assert get_space(store, scope)['has_submission'] is True
    queued = submit_current(store, scope)
    with pytest.raises(StoreError, match='已有同步'):
        submit_current(store, scope)
    result = run_sync(store, store.get_job(queued['task_id']))
    assert result['uploaded'] == 1 and result['skipped'] == 1
    assert len(fake.documents) == 2


def test_obsolete_submission_cannot_retry_or_run_after_newer_batch(spaces):
    store, fake, _, tmp_path = spaces
    space = save_space(store, {'name': '版本隔离'})
    scope = space['scope']
    old = enqueue_sync(store, release(store, tmp_path, scope), scope)
    store.update_job(old['task_id'], status='failed')
    release(store, tmp_path, scope)
    with pytest.raises(StoreError, match='更新的提交'):
        retry(store, scope, {'stage': 'upload', 'target_mode': 'wiki', 'task_id': old['task_id']})
    with pytest.raises(StoreError, match='更新批次'):
        run_sync(store, old)
    assert fake.documents == {}


def test_uncertain_update_reads_back_before_attempting_another_put(spaces, monkeypatch):
    store, fake, _, tmp_path = spaces
    space = save_space(store, {'name': '未知更新'})
    scope = space['scope']
    run_sync(store, enqueue_sync(store, release(store, tmp_path, scope), scope))
    changed = tmp_path / 'changed.zip'
    with ZipFile(changed, 'w') as archive:
        archive.writestr('rag_documents.jsonl', json.dumps({'id': 'source-1', 'version_id': 'v2', 'content': '# Changed'}))
    changed_id = store.create_release('capture-2', scope, 2, ['v2'], str(changed))
    calls = []
    def uncertain_update(*args, **kwargs):
        calls.append(args[0])
        raise ContextDBError('lost update response')
    monkeypatch.setattr(fake, 'update_file', uncertain_update)
    first = run_sync(store, enqueue_sync(store, changed_id, scope))
    second = run_sync(store, enqueue_sync(store, changed_id, scope))
    assert first['errors'] and second['errors'] and len(calls) == 1
    assert '结果未知' in second['errors'][0]
    assert next(iter(fake.documents.values()))['text'] == '# Source'


def test_distinct_scopes_with_same_sanitized_name_do_not_share_cloud_library(spaces):
    store, fake, _, tmp_path = spaces
    ids = []
    for scope in ('product:a', 'product_a'):
        save_space(store, {'scope': scope, 'name': scope})
        result = run_sync(store, enqueue_sync(store, release(store, tmp_path, scope), scope))
        ids.append(result['targets']['wiki'])
    assert ids[0] != ids[1] and len(fake.documents) == 2


def test_concurrent_bindings_cannot_attach_one_library_to_two_spaces(spaces):
    from concurrent.futures import ThreadPoolExecutor
    store, fake, _, _ = spaces
    wiki = fake.create_knowledge_base('exclusive-wiki', wiki_enabled=True)
    def bind(name):
        try:
            return save_space(store, {'name': name, 'wiki_kb_id': wiki['id']})
        except StoreError as exc:
            return exc
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(bind, ['first', 'second']))
    assert sum(isinstance(result, StoreError) for result in results) == 1
    assert len(store._list({'type': 'knowledge_space'})) == 1


def test_deleted_target_is_reconciled_without_deleting_configuration_or_history(spaces, monkeypatch):
    store, fake, http, tmp_path = spaces
    space, doc = mapped_document(store, fake)
    release_id = release(store, tmp_path, space['scope'])
    original = space['wiki_kb_id']
    fake.delete_knowledge_base(original)
    monkeypatch.setattr(fake, 'get_document', lambda *args: pytest.fail('deleted targets must not be polled per document'))
    current = http.get(f"/api/kb/spaces/{space['scope']}").json['space']
    assert current['wiki_kb_id'] is None
    assert current['targets']['wiki']['status'] == 'missing'
    assert current['targets']['wiki']['missing_knowledge_base_id'] == original
    assert http.get('/api/kb/spaces').json['spaces'][0]['targets']['wiki']['status'] == 'missing'
    state = progress(store, space['scope'])
    assert state['mappings'][0]['document_id'] == doc['id']
    assert state['mappings'][0]['target_status'] == 'missing'
    assert state['mappings'][0]['retry_stages'] == []
    record = store._find('knowledge_space', scope=space['scope'])
    assert store._body(record['id'])['wiki_kb_id'] == original
    assert store.get_release(release_id)['active']
    assert store._list({'type': 'knowledge_sync_history'}) == []
    assert fake.knowledge_bases == {}


@pytest.mark.parametrize('error,expected', [
    (ContextDBError('access denied', status_code=403, error_code=4007), 'forbidden'),
    (ContextDBError('network request failed'), 'unknown'),
    (ContextDBError('COMMON_BAD_REQUEST: knowledge base not found or not accessible', status_code=400, error_code=1001), 'unknown'),
    (ContextDBError('upstream unavailable', status_code=503), 'unknown'),
])
def test_unconfirmed_target_failure_never_unbinds_or_creates_a_replacement(spaces, monkeypatch, error, expected):
    store, fake, _, tmp_path = spaces
    space = save_space(store, {'name': '保留绑定'})
    scope = space['scope']
    release_id = release(store, tmp_path, scope)
    original = run_sync(store, enqueue_sync(store, release_id, scope))['targets']['wiki']
    def unavailable(_kb):
        raise error
    monkeypatch.setattr(fake, 'get_knowledge_base', unavailable)
    current = get_space(store, scope)
    assert current['wiki_kb_id'] == original and current['targets']['wiki']['status'] == expected
    result = run_sync(store, enqueue_sync(store, release_id, scope))
    assert result['errors'] and len(fake.knowledge_bases) == 1
    assert store._list({'type': 'knowledge_sync_history'}) == []
    assert store._body(store._find('knowledge_space', scope=scope)['id'])['wiki_kb_id'] == original


def test_rebuilding_deleted_wiki_reuploads_sources_and_preserves_graph_and_old_receipts(spaces):
    from pathlib import Path
    from governance.database import connection
    store, fake, _, tmp_path = spaces
    space = save_space(store, {'name': '恢复已删主库', 'graph_enabled': True})
    scope = space['scope']; release_id = release(store, tmp_path, scope)
    first_job = enqueue_sync(store, release_id, scope)
    initial = run_sync(store, first_job)
    original, graph = initial['targets']['wiki'], initial['targets']['graph']
    old = enqueue_sync(store, release_id, scope)
    store.update_job(old['task_id'], status='failed')
    old_doc = next(doc for doc in fake.documents.values() if doc['knowledge_base_id'] == original)
    fake.delete_knowledge_base(original)
    queued = submit_current(store, scope)
    recovery = store.get_job(queued['task_id'])
    assert recovery['params']['target_ids'] == {'wiki': None, 'graph': graph}
    restored = run_sync(store, recovery)
    replacement = restored['targets']['wiki']
    assert replacement != original and restored['targets']['graph'] == graph
    assert restored['uploaded'] == 1 and restored['skipped'] == 1 and restored['errors'] == []
    archives = store._list({'type': 'knowledge_sync_history'})
    assert len(archives) == 1
    receipt = store._body(archives[0]['id'])
    assert receipt['knowledge_base_id'] == original and receipt['document_id'] == old_doc['id']
    assert receipt['source_hash'] and receipt['source_version'] == 'v1'
    with connection() as conn:
        row = conn.execute("SELECT * FROM knowledge_sync WHERE owner_id=%s AND scope=%s AND target_mode='wiki'", (store.owner_id, scope)).fetchone()
    assert row['knowledge_base_id'] == replacement and row['document_id'] != old_doc['id']
    assert store.get_job(first_job['task_id'])['status'] == 'completed'
    assert store.get_release(release_id)['active'] and Path(store.get_release(release_id)['archive_path']).is_file()
    stale = run_sync(store, old)
    assert stale['errors'] and 'wiki' not in stale['targets']
    again = run_sync(store, store.get_job(submit_current(store, scope)['task_id']))
    assert again['uploaded'] == 0 and again['skipped'] == 2 and again['errors'] == []
    assert len(fake.knowledge_bases) == 2 and len(store._list({'type': 'knowledge_sync_history'})) == 1


def test_missing_target_recovery_waits_for_active_jobs_and_only_missing_bindings_can_be_replaced(spaces):
    store, fake, _, tmp_path = spaces
    space = save_space(store, {'name': '活动任务保护'})
    scope = space['scope']; release_id = release(store, tmp_path, scope)
    original = run_sync(store, enqueue_sync(store, release_id, scope))['targets']['wiki']
    active = enqueue_sync(store, release_id, scope)
    fake.delete_knowledge_base(original)
    replacement = fake.create_knowledge_base('new-target', wiki_enabled=True)
    with pytest.raises(StoreError, match='已有同步任务'):
        submit_current(store, scope)
    with pytest.raises(StoreError, match='已有同步任务'):
        save_space(store, {'wiki_kb_id': replacement['id']}, scope)
    store.update_job(active['task_id'], status='failed')
    updated = save_space(store, {'wiki_kb_id': replacement['id']}, scope)
    assert updated['wiki_kb_id'] == replacement['id']
    another = fake.create_knowledge_base('another-target', wiki_enabled=True)
    with pytest.raises(StoreError, match='不能直接替换'):
        save_space(store, {'wiki_kb_id': another['id']}, scope)


def test_stale_delivery_cannot_overwrite_a_new_target_mapping(spaces):
    from governance.database import connection
    store, fake, _, _ = spaces
    original = fake.create_knowledge_base('old', wiki_enabled=True)
    replacement = fake.create_knowledge_base('new', wiki_enabled=True)
    _save(store.owner_id, 'scope', 'source', 'wiki', replacement['id'], document_id='new-doc', status='succeeded')
    with pytest.raises(StoreError, match='旧任务不能覆盖'):
        _save(store.owner_id, 'scope', 'source', 'wiki', original['id'], document_id='old-doc', status='succeeded')
    with connection() as conn:
        row = conn.execute('SELECT * FROM knowledge_sync WHERE owner_id=%s', (store.owner_id,)).fetchone()
    assert row['knowledge_base_id'] == replacement['id'] and row['document_id'] == 'new-doc'


def test_deleted_wiki_can_be_rebuilt_without_reading_or_resubmitting_graph_documents(spaces, monkeypatch):
    from governance.database import connection
    store, fake, http, tmp_path = spaces
    scope = save_space(store, {'name': '仅恢复 Wiki', 'graph_enabled': True})['scope']
    release_id = release(store, tmp_path, scope)
    initial = run_sync(store, enqueue_sync(store, release_id, scope))
    original, graph = initial['targets']['wiki'], initial['targets']['graph']
    with connection() as conn:
        graph_receipt = conn.execute("SELECT * FROM knowledge_sync WHERE owner_id=%s AND scope=%s AND target_mode='graph'",
                                     (store.owner_id, scope)).fetchone()
    get_document = fake.get_document
    def wiki_documents_only(kb_id, document_id):
        assert kb_id != graph, 'Wiki recovery must leave graph documents untouched'
        return get_document(kb_id, document_id)
    monkeypatch.setattr(fake, 'get_document', wiki_documents_only)
    fake.delete_knowledge_base(original)
    response = http.post(f'/api/kb/spaces/{scope}/submit', json={'target_modes': ['wiki']})
    assert response.status_code == 200
    job = store.get_job(response.json['result']['task_id'])
    assert job['params']['target_modes'] == ['wiki'] and job['params']['target_ids'] == {'wiki': None}
    assert get_space(store, scope)['targets']['wiki']['status'] == 'missing'
    assert store._list({'type': 'knowledge_sync_history'}) == []
    restored = run_sync(store, job)
    assert restored['errors'] == [] and restored['uploaded'] == 1 and restored['skipped'] == 0
    assert set(restored['targets']) == {'wiki'} and restored['targets']['wiki'] != original
    current_space = get_space(store, scope)
    assert current_space['graph_kb_id'] == graph
    assert current_space['targets']['wiki']['previous_knowledge_base_ids'] == [original]
    with connection() as conn:
        current = conn.execute("SELECT * FROM knowledge_sync WHERE owner_id=%s AND scope=%s AND target_mode='graph'",
                               (store.owner_id, scope)).fetchone()
    assert current == graph_receipt
    history = store._list({'type': 'knowledge_sync_history'})
    assert len(history) == 1 and store._body(history[0]['id'])['knowledge_base_id'] == original


@pytest.mark.parametrize('rebind_existing', [True, False])
def test_explicit_missing_target_recovery_preserves_old_receipts_until_sources_are_delivered(spaces, monkeypatch, rebind_existing):
    from governance.database import connection
    store, fake, _, tmp_path = spaces
    space, old_document = mapped_document(store, fake, ingest_status='failed', recovery_actions=['retry'])
    scope, original = space['scope'], space['wiki_kb_id']
    release(store, tmp_path, scope)
    fake.delete_knowledge_base(original)
    replacement = fake.create_knowledge_base('replacement', wiki_enabled=True)['id'] if rebind_existing else None
    updated = save_space(store, {'wiki_kb_id': replacement}, scope)
    assert updated['wiki_kb_id'] == replacement
    assert updated['targets']['wiki']['status'] == ('available' if replacement else 'unbound')
    assert updated['targets']['wiki']['previous_knowledge_base_ids'] == [original]
    get_document = fake.get_document
    def no_old_document(kb_id, document_id):
        assert kb_id != original, 'A retired receipt is not a current target document'
        return get_document(kb_id, document_id)
    monkeypatch.setattr(fake, 'get_document', no_old_document)
    row = progress(store, scope)['mappings'][0]
    assert row['knowledge_base_id'] == original and row['document_id'] == old_document['id']
    assert row['target_status'] == 'pending_submission' and row['retry_stages'] == [] and 'official' not in row
    assert store._list({'type': 'knowledge_sync_history'}) == []
    with pytest.raises(StoreError, match='重新提交最近批次'):
        retry(store, scope, {'stage': 'ingest', 'target_mode': 'wiki', 'source_id': 'source-1'})
    result = run_sync(store, store.get_job(submit_current(store, scope, target_modes=['wiki'])['task_id']))
    assert result['uploaded'] == 1 and result['errors'] == []
    if replacement:
        assert result['targets']['wiki'] == replacement
    with connection() as conn:
        current = conn.execute("SELECT * FROM knowledge_sync WHERE owner_id=%s AND scope=%s AND target_mode='wiki'",
                               (store.owner_id, scope)).fetchone()
    assert current['knowledge_base_id'] == result['targets']['wiki'] and current['document_id'] != old_document['id']
    assert len(store._list({'type': 'knowledge_sync_history'})) == 1


@pytest.mark.parametrize('target_modes', [[], 'wiki', ['other'], {'wiki': True}, True])
def test_submission_rejects_invalid_target_selection_without_queuing(spaces, target_modes):
    store, _, http, tmp_path = spaces
    scope = save_space(store, {'name': '校验恢复目标'})['scope']
    release(store, tmp_path, scope)
    response = http.post(f'/api/kb/spaces/{scope}/submit', json={'target_modes': target_modes})
    assert response.status_code == 400 and 'target_modes' in response.json['message']
    assert store._list({'type': 'job'}) == []


def test_recovered_target_aliases_resolve_only_the_original_owner_and_space_even_without_documents(spaces):
    store, fake, _, _ = spaces
    original = fake.create_knowledge_base('retired-empty-wiki', wiki_enabled=True)['id']
    replacement = fake.create_knowledge_base('replacement-wiki', wiki_enabled=True)['id']
    unrelated = fake.create_knowledge_base('unrelated-wiki', wiki_enabled=True)['id']
    first = save_space(store, {'name': '原空间', 'wiki_kb_id': original})
    second = save_space(store, {'name': '另一空间', 'wiki_kb_id': unrelated})
    before = get_space(store, first['scope'])
    assert before['wiki_kb_id'] == original and before['targets']['wiki']['previous_knowledge_base_ids'] == []
    fake.delete_knowledge_base(original)
    missing = get_space(store, first['scope'])
    assert missing['targets']['wiki']['missing_knowledge_base_id'] == original
    save_space(store, {'wiki_kb_id': replacement}, first['scope'])
    _save('another-owner', first['scope'], 'foreign-source', 'wiki', 'foreign-library-id', status='succeeded')
    items = list_spaces(store)[0]
    def resolve(kb_id):
        return [space['scope'] for space in items if kb_id == space['wiki_kb_id'] or
                kb_id in space['targets']['wiki']['previous_knowledge_base_ids']]
    assert resolve(original) == resolve(replacement) == [first['scope']]
    assert resolve(unrelated) == [second['scope']]
    assert resolve('foreign-library-id') == []
