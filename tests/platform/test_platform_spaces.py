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
from tests.fakes.contextdb_fake import FakeContextDBClient


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


def test_create_space_immediately_creates_one_wiki_library(spaces):
    store, fake, http, _ = spaces
    response = http.post('/api/kb/spaces', json={'name': '产品资料'})
    assert response.status_code == 201
    space = response.json['space']
    assert space['scope'].startswith('space-') and space['mode'] == 'wiki'
    assert space['knowledge_base_id'] == space['wiki_kb_id'] and len(fake.knowledge_bases) == 1
    assert fake.get_knowledge_base(space['knowledge_base_id'])['name'] == '产品资料'
    assert http.get('/api/kb/spaces').json['spaces'][0]['scope'] == space['scope']
    assert http.get('/api/kb/spaces/unknown').status_code == 404
    assert http.patch('/api/kb/spaces/' + space['scope'], json={'graph_enabled': 'false'}).status_code == 400


def test_file_capture_auto_submits_to_fixed_wiki_and_repetition_preserves_document(spaces, monkeypatch):
    from governance.worker import process_job
    store, fake, http, _ = spaces
    monkeypatch.setattr('webapi.auth.client_for_user', lambda *args: fake)
    space = http.post('/api/kb/spaces', json={'name':'完整流程'}).json['space']
    scope = space['scope']
    source = b'# Components\nAPI depends on Database.\n'
    response = http.post('/api/uploads', data={'space_scope':scope, 'files':(io.BytesIO(source),'dependencies.md')})
    assert response.status_code == 200
    capture = store.claim()
    assert capture['task_id'] == response.json['task_id'] and capture['attempt_token']
    process_job(Store(client=fake, owner_id=store.owner_id), capture)
    assert store.get_job(capture['task_id'])['status'] == 'completed' and fake.documents == {}
    status = http.get(f"/task_status/{capture['task_id']}").json
    assert status['phase'] == 'submitted' and not status['submit_available'] and status['submission_id']
    sync_jobs = [job for job in store.list_jobs() if job['kind'] == 'ctxdb_sync']
    assert len(sync_jobs) == 1
    assert sync_jobs[0]['params']['target_mode'] == 'wiki'
    result = run_sync(store, sync_jobs[0])
    assert result['uploaded'] == 1 and len(fake.documents) == 1
    wiki_doc = next(iter(fake.documents.values()))
    assert wiki_doc['text'].encode() == source
    assert http.patch('/api/kb/spaces/' + scope, json={'graph_enabled':True}).status_code == 409
    response = http.post('/api/kb/spaces/' + scope + '/submit')
    assert response.status_code == 200
    again = run_sync(store, store.get_job(response.json['result']['task_id']))
    assert again['uploaded'] == 0 and again['skipped'] == 1 and len(fake.documents) == 1
    rows = http.get('/api/kb/spaces/' + scope + '/progress').json['mappings']
    assert len(rows) == 1 and rows[0]['document_id'] == wiki_doc['id']


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


def test_legacy_pair_is_listed_as_independent_official_libraries_without_cloud_mutation(spaces):
    store, fake, _, _ = spaces
    wiki = fake.create_knowledge_base('knowledge-default', wiki_enabled=True, graph_enabled=False)
    graph = fake.create_knowledge_base('knowledge-default-graph', wiki_enabled=False, graph_enabled=True)
    extra = fake.create_knowledge_base('another-wiki', wiki_enabled=True, graph_enabled=False)
    spaces_list, available = list_spaces(store)
    assert {item['knowledge_base_id'] for item in spaces_list} == {wiki['id'], graph['id'], extra['id']}
    default = next(item for item in spaces_list if item['scope'] == 'default')
    assert default['wiki_kb_id'] == wiki['id'] and default['graph_kb_id'] is None
    assert default['legacy_targets']['graph'] == graph['id'] and available == []
    assert store._list({'type': 'knowledge_space'}) == []
    changed = save_space(store, {'graph_enabled': False}, 'default')
    assert changed['knowledge_base_id'] == wiki['id'] and graph['id'] in fake.knowledge_bases


def test_binding_validates_mode_and_cannot_replace_existing_ids(spaces):
    store, fake, http, _ = spaces
    graph = fake.create_knowledge_base('graph', graph_enabled=True)
    wiki = fake.create_knowledge_base('wiki', wiki_enabled=True)
    other = fake.create_knowledge_base('other', wiki_enabled=True)
    assert http.post('/api/kb/spaces', json={'name': '错误', 'wiki_kb_id': graph['id']}).status_code == 409
    response = http.post('/api/kb/spaces', json={'name': '绑定', 'wiki_kb_id': wiki['id']})
    scope = response.json['space']['scope']
    assert http.patch('/api/kb/spaces/' + scope, json={'wiki_kb_id': other['id']}).status_code == 409
    again = http.post('/api/kb/spaces', json={'name': '重复绑定', 'wiki_kb_id': wiki['id']})
    assert again.status_code == 201 and again.json['space']['scope'] == scope
    assert get_space(store, scope)['wiki_kb_id'] == wiki['id']
    with pytest.raises(StoreError, match='不存在'):
        get_space(Store(client=fake, owner_id='another-user'), scope)


def test_target_snapshot_rejects_mode_switch_and_keeps_existing_library(spaces):
    store, fake, _, tmp_path = spaces
    space = save_space(store, {'name': 'Wiki 固定目标'})
    scope = space['scope']
    release_id = release(store, tmp_path, scope)
    first = enqueue_sync(store, release_id, scope)
    assert first['params']['target_mode'] == 'wiki'
    assert first['params']['knowledge_base_id'] == space['knowledge_base_id']
    with pytest.raises(StoreError, match='不能切换'):
        save_space(store, {'graph_enabled': True}, scope)
    assert run_sync(store, first)['uploaded'] == 1
    second = enqueue_sync(store, release_id, scope)
    result = run_sync(store, second)
    assert result['uploaded'] == 0 and result['skipped'] == 1
    assert len(fake.knowledge_bases) == len(fake.documents) == 1


def test_upload_retry_pins_single_failed_library_and_rejects_duplicate_active_job(spaces, monkeypatch):
    store, fake, _, tmp_path = spaces
    space = save_space(store, {'name': '图谱', 'mode': 'graph'})
    scope = space['scope']
    upload = fake.upload_file
    def fail_upload(*args, **kwargs):
        raise ContextDBError('quota exceeded', status_code=429)
    monkeypatch.setattr(fake, 'upload_file', fail_upload)
    job = enqueue_sync(store, release(store, tmp_path, scope), scope)
    result = run_sync(store, job)
    assert result['uploaded'] == 0 and len(result['errors']) == 1
    with pytest.raises(StoreError, match='模式不一致'):
        retry(store, scope, {'stage': 'upload', 'target_mode': 'wiki', 'task_id': job['task_id']})
    queued = retry(store, scope, {'stage': 'upload', 'target_mode': 'graph', 'task_id': job['task_id']})
    with pytest.raises(StoreError, match='已有重试'):
        retry(store, scope, {'stage': 'upload', 'target_mode': 'graph', 'task_id': job['task_id']})
    monkeypatch.setattr(fake, 'upload_file', upload)
    retried = store.get_job(queued['task_id'])
    assert retried['params']['target_mode'] == 'graph'
    assert retried['params']['knowledge_base_id'] == space['knowledge_base_id']
    assert run_sync(store, retried)['uploaded'] == 1 and len(fake.documents) == 1


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
    assert save_space(store, {'graph_enabled': False}, space['scope'])['mode'] == 'source'
    with pytest.raises(StoreError, match='未启用图谱'):
        retry(store, space['scope'], {'stage': 'graph', 'target_mode': 'graph', 'source_id': 'source-1'})
    save_space(store, {'graph_enabled': True}, space['scope'])
    with pytest.raises(StoreError, match='结果未知'):
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


def test_non_wiki_graph_switch_preserves_queued_upload_and_existing_receipts(spaces, monkeypatch):
    store, fake, _, tmp_path = spaces
    space = save_space(store, {'name': '图谱开关', 'mode': 'source'})
    scope, kb_id = space['scope'], space['knowledge_base_id']
    release_id = release(store, tmp_path, scope)
    queued = enqueue_sync(store, release_id, scope)
    fake.update_knowledge_base(kb_id, graph_enabled=True)
    current = get_space(store, scope)
    assert current['mode'] == 'graph' and current['targets']['graph']['status'] == 'available'
    assert run_sync(store, queued)['uploaded'] == 1
    assert run_sync(store, enqueue_sync(store, release_id, scope))['skipped'] == 1
    rows = progress(store, scope)['mappings']
    assert len(rows) == 1 and rows[0]['target_mode'] == 'source'
    document_id = rows[0]['document_id']
    fake.documents[document_id].update(ingest_status='succeeded', graph_status='skipped', latest_graph_event_id=None)
    assert progress(store, scope)['mappings'][0]['retry_stages'] == ['graph']
    calls = []
    monkeypatch.setattr(fake, '_request', lambda method, path, **kwargs:
        calls.append(kwargs['json_body']) or {'event_id': 'graph-new', 'status': 'queued'})
    assert retry(store, scope, {'stage': 'graph', 'source_id': 'source-1'})['status'] == 'queued'
    assert calls == [{'document_id': document_id, 'event_type': 'graph_build'}]
    save_space(store, {'graph_enabled': False}, scope)
    assert run_sync(store, enqueue_sync(store, release_id, scope))['skipped'] == 1
    assert len(progress(store, scope)['mappings']) == len(fake.documents) == 1
    assert get_space(store, scope)['knowledge_base_id'] == kb_id


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


def test_legacy_default_cannot_be_shadowed_and_idempotent_binding_reuses_scope(spaces):
    store, fake, http, _ = spaces
    original = fake.create_knowledge_base('knowledge-default', wiki_enabled=True)
    other = fake.create_knowledge_base('other', wiki_enabled=True)
    assert http.post('/api/kb/spaces', json={'scope': 'default', 'name': '覆盖', 'wiki_kb_id': other['id']}).status_code == 409
    response = http.post('/api/kb/spaces', json={'name': '重复', 'wiki_kb_id': original['id']})
    assert response.status_code == 201 and response.json['space']['scope'] == 'default'
    assert get_space(store, 'default')['wiki_kb_id'] == original['id']


def test_current_submission_reuses_fixed_library_without_recapture(spaces):
    store, fake, http, tmp_path = spaces
    space = save_space(store, {'name': '重提资料'})
    assert space['has_submission'] is False
    scope = space['scope']
    assert http.post(f'/api/kb/spaces/{scope}/submit').status_code == 409
    run_sync(store, enqueue_sync(store, release(store, tmp_path, scope), scope))
    assert get_space(store, scope)['has_submission'] is True
    with pytest.raises(StoreError, match='不能切换'):
        save_space(store, {'graph_enabled': True}, scope)
    queued = submit_current(store, scope)
    with pytest.raises(StoreError, match='已有同步'):
        submit_current(store, scope)
    result = run_sync(store, store.get_job(queued['task_id']))
    assert result['uploaded'] == 0 and result['skipped'] == 1 and len(fake.documents) == 1


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
    assert all(not isinstance(result, StoreError) for result in results)
    assert results[0]['scope'] == results[1]['scope']
    assert len(store._list({'type': 'knowledge_space'})) == 1


def test_deleted_target_is_reconciled_without_deleting_configuration_or_history(spaces, monkeypatch):
    store, fake, http, tmp_path = spaces
    space, doc = mapped_document(store, fake)
    release_id = release(store, tmp_path, space['scope'])
    original = space['wiki_kb_id']
    fake.delete_knowledge_base(original)
    monkeypatch.setattr(fake, 'get_document', lambda *args: pytest.fail('deleted targets must not be polled per document'))
    current = http.get(f"/api/kb/spaces/{space['scope']}").json['space']
    assert current['wiki_kb_id'] == original and current['lifecycle'] == 'missing'
    assert current['targets']['wiki']['status'] == 'missing'
    assert current['targets']['wiki']['missing_knowledge_base_id'] == original
    assert http.get('/api/kb/spaces').json['spaces'][0]['targets']['wiki']['status'] == 'missing'
    state = progress(store, space['scope'])
    assert state['mappings'][0]['document_id'] == doc['id']
    assert state['mappings'][0]['target_status'] == 'missing'
    assert state['mappings'][0]['retry_stages'] == []
    record = store._find('knowledge_space', scope=space['scope'])
    assert store._body(record['id'])['knowledge_base_id'] == original
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
    with pytest.raises(StoreError):
        enqueue_sync(store, release_id, scope)
    assert len(fake.knowledge_bases) == 1
    assert store._list({'type': 'knowledge_sync_history'}) == []
    assert store._body(store._find('knowledge_space', scope=scope)['id'])['knowledge_base_id'] == original


def test_deleted_wiki_never_rebuilds_and_preserves_other_library_and_receipts(spaces):
    from pathlib import Path
    store, fake, _, tmp_path = spaces
    space = save_space(store, {'name': '已删主库'})
    graph = fake.create_knowledge_base('独立图谱', graph_enabled=True)
    graph_doc = fake.create_text_document(graph['id'], 'graph.md', '# retained graph')
    scope = space['scope']; release_id = release(store, tmp_path, scope)
    first_job = enqueue_sync(store, release_id, scope)
    initial = run_sync(store, first_job)
    original = initial['targets']['wiki']
    old_doc = next(doc for doc in fake.documents.values() if doc['knowledge_base_id'] == original)
    fake.delete_knowledge_base(original)
    with pytest.raises(StoreError):
        submit_current(store, scope)
    assert get_space(store, scope)['knowledge_base_id'] == original
    assert progress(store, scope)['mappings'][0]['document_id'] == old_doc['id']
    assert fake.get_document(graph['id'], graph_doc['id'])
    assert len(fake.knowledge_bases) == 1
    assert store.get_job(first_job['task_id'])['status'] == 'completed'
    assert store.get_release(release_id)['active'] and Path(store.get_release(release_id)['archive_path']).is_file()


def test_missing_target_cannot_rebind_even_after_active_jobs_stop(spaces):
    from governance.spaces import ensure_base_space
    store, fake, _, tmp_path = spaces
    space = save_space(store, {'name': '活动任务保护'})
    scope = space['scope']; release_id = release(store, tmp_path, scope)
    original = run_sync(store, enqueue_sync(store, release_id, scope))['targets']['wiki']
    active = enqueue_sync(store, release_id, scope)
    fake.delete_knowledge_base(original)
    replacement = fake.create_knowledge_base('new-target', wiki_enabled=True)
    with pytest.raises(StoreError):
        submit_current(store, scope)
    with pytest.raises(StoreError):
        save_space(store, {'wiki_kb_id': replacement['id']}, scope)
    store.update_job(active['task_id'], status='failed')
    with pytest.raises(StoreError):
        save_space(store, {'wiki_kb_id': replacement['id']}, scope)
    new = ensure_base_space(store, replacement['id'])
    assert new['scope'] != scope and get_space(store, scope)['knowledge_base_id'] == original


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


def test_deleted_wiki_progress_does_not_read_or_resubmit_independent_graph(spaces, monkeypatch):
    store, fake, http, tmp_path = spaces
    space = save_space(store, {'name': '仅 Wiki'})
    scope = space['scope']; release_id = release(store, tmp_path, scope)
    original = run_sync(store, enqueue_sync(store, release_id, scope))['targets']['wiki']
    graph = fake.create_knowledge_base('separate-graph', graph_enabled=True)
    graph_doc = fake.create_text_document(graph['id'], 'graph.md', 'retained')
    fake.delete_knowledge_base(original)
    monkeypatch.setattr(fake, 'get_document', lambda *args: pytest.fail('Missing library progress must not fetch any document'))
    response = http.get(f'/api/kb/spaces/{scope}/progress')
    assert response.status_code == 200 and response.json['mappings'][0]['target_status'] == 'missing'
    assert http.post(f'/api/kb/spaces/{scope}/submit', json={'target_modes': ['wiki']}).status_code == 409
    assert graph_doc['id'] in fake.documents and graph['id'] in fake.knowledge_bases


@pytest.mark.parametrize('rebind_existing', [True, False])
def test_missing_target_replacement_attempt_preserves_old_receipts(spaces, monkeypatch, rebind_existing):
    from governance.database import connection
    store, fake, _, _ = spaces
    space, old_document = mapped_document(store, fake, ingest_status='failed', recovery_actions=['retry'])
    scope, original = space['scope'], space['knowledge_base_id']
    fake.delete_knowledge_base(original)
    replacement = fake.create_knowledge_base('replacement', wiki_enabled=True)['id'] if rebind_existing else None
    with pytest.raises(StoreError):
        save_space(store, {'wiki_kb_id': replacement}, scope)
    monkeypatch.setattr(fake, 'get_document', lambda *args: pytest.fail('Missing targets must not read old documents'))
    row = progress(store, scope)['mappings'][0]
    assert row['knowledge_base_id'] == original and row['document_id'] == old_document['id']
    assert row['target_status'] == 'missing' and row['retry_stages'] == [] and 'official' not in row
    with connection() as conn:
        stored = conn.execute('SELECT * FROM knowledge_sync WHERE owner_id=%s AND knowledge_base_id=%s',
                              (store.owner_id, original)).fetchone()
    assert stored['document_id'] == old_document['id'] and store._list({'type': 'knowledge_sync_history'}) == []


@pytest.mark.parametrize('target_modes', [[], 'wiki', ['other'], {'wiki': True}, True])
def test_submission_rejects_invalid_target_selection_without_queuing(spaces, target_modes):
    store, _, http, tmp_path = spaces
    scope = save_space(store, {'name': '校验恢复目标'})['scope']
    release(store, tmp_path, scope)
    response = http.post(f'/api/kb/spaces/{scope}/submit', json={'target_modes': target_modes})
    assert response.status_code == 400 and 'target_modes' in response.json['message']
    assert store._list({'type': 'job'}) == []


def test_missing_ids_and_replacement_ids_keep_independent_scopes_and_owner_history(spaces):
    from governance.spaces import ensure_base_space
    store, fake, _, _ = spaces
    original = fake.create_knowledge_base('retired-empty-wiki', wiki_enabled=True)['id']
    replacement = fake.create_knowledge_base('replacement-wiki', wiki_enabled=True)['id']
    unrelated = fake.create_knowledge_base('unrelated-wiki', wiki_enabled=True)['id']
    first = ensure_base_space(store, original)
    second = ensure_base_space(store, unrelated)
    fake.delete_knowledge_base(original)
    assert get_space(store, first['scope'])['targets']['wiki']['missing_knowledge_base_id'] == original
    replacement_space = ensure_base_space(store, replacement)
    _save('another-owner', first['scope'], 'foreign-source', 'wiki', 'foreign-library-id', status='succeeded')
    items = list_spaces(store)[0]
    ids = {space['knowledge_base_id']: space['scope'] for space in items}
    assert ids[original] == first['scope'] and ids[unrelated] == second['scope']
    assert ids[replacement] == replacement_space['scope'] != first['scope']
    assert 'foreign-library-id' not in ids
