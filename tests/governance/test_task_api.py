"""任务生命周期 API 契约测试(app 路由 × ContextDB 治理存储替身)。"""
import json
import io
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import app as app_module
from governance.store import Store, StoreError
from governance.worker import write_json
from tests.fakes.contextdb_fake import FakeContextDBClient


@pytest.fixture()
def client(authenticated_client):
    fake = FakeContextDBClient()
    fake.create_knowledge_base('knowledge-default', wiki_enabled=True, review_enabled=True)
    app_module.app.extensions['governance_store'] = Store(client=fake, kb_name='_test_governance')
    app_module.app.config['TESTING'] = True
    yield authenticated_client
    app_module.app.extensions.pop('governance_store', None)


def make_crawl_documents(job, store):
    documents = [{'id': 's1', 'title': '标题A', 'category': '分类', 'content': '# 正文A',
                  'metadata': {'conversion': {'fingerprint': 'f1'}}}]
    sources = {'s1': {'source_format': 'md', 'source_sha256': 'sha', 'content': '原始'}}
    chunks = [{'document_id': 's1', 'content': '片段', 'chunk_index': 0}]
    store.ingest(job, documents, sources, chunks)
    store.update_job(job['task_id'], capture_complete=True, summary={'total_documents': 1})


def test_task_start_status_and_cancel(client):
    store = app_module.get_store()
    task_id = store.create_job('file', {'file_paths': ['a.md']})['task_id']
    resp = client.get(f'/task_status/{task_id}')
    payload = resp.get_json()
    assert payload['status'] == 'pending' and payload['entry'] == 'file'
    resp = client.post(f'/tasks/{task_id}/cancel')
    assert resp.get_json()['success'] is True
    resp = client.get(f'/task_status/{task_id}')
    assert resp.get_json()['status'] == 'cancelled'
    resp = client.get('/api/tasks')
    assert any(task['task_id'] == task_id for task in resp.get_json()['tasks'])


def test_task_retry_requires_terminal_state(client):
    store = app_module.get_store()
    task_id = store.create_job('file', {'file_paths': ['a.md']})['task_id']
    resp = client.post(f'/tasks/{task_id}/retry')
    assert resp.status_code == 400


def test_sync_retry_must_select_failed_target_in_space(client):
    store = app_module.get_store()
    job = store.create_job('contextdb', {'release_id':'r','target_modes':['wiki','graph']}, kind='ctxdb_sync')
    store.update_job(job['task_id'], status='failed')
    response = client.post(f"/tasks/{job['task_id']}/retry")
    assert response.status_code == 409
    assert len(store.list_jobs()) == 1


def test_documents_listing_and_detail(client):
    store = app_module.get_store()
    job = store.create_job('file', {'file_paths': ['a.md']})
    make_crawl_documents(job, store)
    resp = client.get('/api/documents')
    documents = resp.get_json()['documents']
    assert documents and documents[0]['title'] == '标题A'
    version_id = documents[0]['version_id']
    resp = client.get(f'/api/documents/{version_id}')
    detail = resp.get_json()
    assert detail['document']['title'] == '标题A'
    assert 'issues' not in detail


def test_task_details_split_queue_time_and_show_only_failure_fields(client):
    store = app_module.get_store()
    job = store.create_job('cyb', {})
    output = Path(job['output_dir']); output.mkdir(parents=True)
    (output/'failed_documents.jsonl').write_text(json.dumps({
        'id':'empty-1','title':'空正文','error':'源正文为空','metadata':{'token':'PRIVATE-METADATA'},
    })+'\n')
    store.update_job(job['task_id'],status='partial',failed_pages=1,completed_pages=3,total_pages=3,
        start_time='2026-11-13T04:00:00+00:00',attempt_started_at='2026-11-13T04:30:00+00:00',
        end_time='2026-11-13T04:30:13+00:00',summary={'video_reference_documents':1})
    response = client.get(f"/task_status/{job['task_id']}")
    payload = response.get_json()
    assert payload['queued_seconds'] == 1800 and payload['processing_seconds'] == 13
    assert payload['elapsed_seconds'] == 1813
    assert payload['failure_details'] == [{'id':'empty-1','title':'空正文','error':'源正文为空'}]
    assert payload['metrics']['video_references'] == 1
    assert 'PRIVATE-METADATA' not in response.text
    listing = next(row for row in client.get('/api/tasks').json['tasks'] if row['task_id'] == job['task_id'])
    assert listing['queued_seconds'] == 1800 and 'failure_details' not in listing


def test_publish_flow_enqueues_contextdb_sync(client):
    store = app_module.get_store()
    job = store.create_job('file', {'file_paths': ['a.md']})
    make_crawl_documents(job, store)
    store.update_job(job['task_id'], status='completed', phase='completed', zip_file='x.zip')
    resp = client.post(f"/tasks/{job['task_id']}/publish")
    assert resp.status_code == 200
    release_id = resp.get_json()['release_id']
    resp = client.get('/api/releases')
    assert any(item['id'] == release_id for item in resp.get_json()['releases'])
    resp = client.post(f'/api/releases/{release_id}/activate')
    assert resp.get_json()['success'] is True
    sync_jobs = [item for item in store.list_jobs() if item['kind'] == 'ctxdb_sync']
    assert sync_jobs and sync_jobs[0]['params']['release_id'] == release_id


def test_submit_alias_is_idempotent_and_exposes_submission_separately(client):
    store = app_module.get_store()
    job = store.create_job('file', {'file_paths': ['a.md']}, scope='default')
    make_crawl_documents(job, store)
    store.update_job(job['task_id'], status='completed', phase='completed')
    before = client.get(f"/task_status/{job['task_id']}").get_json()
    assert before['scope'] == 'default' and before['submit_available']
    first = client.post(f"/tasks/{job['task_id']}/submit")
    assert first.status_code == 200
    second = client.post(f"/tasks/{job['task_id']}/publish")
    assert first.get_json()['release_id'] == second.get_json()['release_id']
    assert len([j for j in store.list_jobs() if j['kind'] == 'ctxdb_sync']) == 1
    after = client.get(f"/task_status/{job['task_id']}").get_json()
    assert not after['submit_available'] and after['submission_id'] == first.get_json()['release_id']


def test_crawl_and_file_upload_use_the_same_selected_space(client, monkeypatch):
    import governance.spaces as spaces
    monkeypatch.setattr(app_module.get_entry('web').crawler_class, 'validate_url', lambda url: None)
    spaces.save_space(app_module.get_store(), {'scope': 'product-a', 'name': '产品 A', 'mode': 'wiki'})
    checked = []
    original_get_space = spaces.get_space
    def get_space(store, scope):
        checked.append(scope)
        return original_get_space(store, scope)
    monkeypatch.setattr(spaces, 'get_space', get_space)
    crawl = client.post('/entries/web/start', json={'url':'https://example.test/docs','space_scope':'product-a'})
    upload = client.post('/api/uploads', data={'files':(io.BytesIO(b'name,value\nx,1'), 'source.csv'),'space_scope':'product-a'})
    assert crawl.status_code == upload.status_code == 200
    store = app_module.get_store()
    assert store.get_job(crawl.get_json()['task_id'])['scope'] == 'product-a'
    file_job = store.get_job(upload.get_json()['task_id'])
    assert file_job['scope'] == 'product-a' and file_job['entry'] == 'file'
    assert Path(file_job['params']['file_paths'][0]).read_bytes() == b'name,value\nx,1'
    assert file_job['params']['file_names'] == ['source.csv']
    store.create_job('web', {}, scope='other')
    tasks = client.get('/api/tasks?space_scope=product-a').get_json()['tasks']
    assert len(tasks) == 2 and all(task['scope'] == 'product-a' for task in tasks)
    assert checked and set(checked) == {'product-a'}
    assert client.post('/api/uploads', data={'files':(io.BytesIO(b'x'),'x.md'),'space_scope':'missing'}).status_code == 404
    assert client.post('/entries/web/start', json={'url':'https://example.test','space_scope':[]}).status_code == 400


def test_upload_name_mapping_keeps_natural_prefixes_and_duplicate_names_without_overwriting(client, monkeypatch):
    import governance.spaces as spaces
    spaces.save_space(app_module.get_store(), {'scope': 'product', 'name': '产品', 'mode': 'wiki'})
    response = client.post('/api/uploads', data={'space_scope': 'product', 'files': [
        (io.BytesIO(b'first'), '001-guide.md'), (io.BytesIO(b'second'), 'same.md'),
        (io.BytesIO(b'third'), 'same.md'), (io.BytesIO(b'fourth'), 'folder/Use:Guide.MD'),
    ]})
    assert response.status_code == 200
    job = app_module.get_store().get_job(response.json['task_id'])
    paths = [Path(value) for value in job['params']['file_paths']]
    assert job['params']['file_names'] == ['001-guide.md', 'same.md', 'same.md', 'Use_Guide.md']
    assert [path.name for path in paths] == ['001-001-guide.md', '002-same.md', '003-same.md', '004-Use_Guide.md']
    assert [path.read_bytes() for path in paths] == [b'first', b'second', b'third', b'fourth']


def test_publish_blocked_until_job_completed(client):
    store = app_module.get_store()
    job = store.create_job('file', {'file_paths': ['a.md']})
    make_crawl_documents(job, store)
    resp = client.post(f"/tasks/{job['task_id']}/publish")
    assert resp.status_code == 409
    assert '不能提交治理' in resp.get_json()['message']


def test_health_reports_contextdb_state(client):
    resp = client.get('/api/health')
    payload = resp.get_json()
    assert payload['contextdb'] is True and payload['database'] is True
    assert 'semantic' not in payload


def test_video_preview_uses_the_same_reference_content_as_collection(client, tmp_path, monkeypatch):
    from crawlers.cyb import CYBCrawler
    from crawlers.base import DocumentStub
    crawler = CYBCrawler(str(tmp_path))
    crawler._items = {'tutorial-1':{'videoUrl':'https://www.bilibili.com/video/example/','content':''}}
    monkeypatch.setattr(crawler,'authenticate',lambda:None)
    monkeypatch.setattr(crawler,'list_documents',lambda:[DocumentStub('tutorial-1','视频教程','教程')])
    monkeypatch.setattr(app_module,'create_crawler',lambda *args,**kwargs:crawler)
    response = client.get('/entries/cyb/preview?doc_id=tutorial-1')
    assert response.status_code == 200
    assert '尚未采集或解析视频内容' in response.json['content']
    assert response.json['source_kind'] == 'video_reference'
    assert response.json['media_content_captured'] is False


def test_write_json_atomic(tmp_path):
    target = tmp_path / 'nested' / 'out.json'
    write_json(target, {'a': 1})
    assert json.loads(target.read_text()) == {'a': 1}
    assert not target.with_suffix('.json.part').exists()


def test_task_links_use_release_ids_and_expose_only_the_latest_public_submission(client):
    store = app_module.get_store()
    capture = store.create_job('file', {'file_paths': ['/private/PRIVATE-PATH/source.md'],
        'file_names': ['安装说明.pdf', '更新记录.md'], 'user_token': 'PRIVATE-TOKEN'})
    release_id = store.create_release(capture['task_id'], 'default', 1, [], 'archive.zip')
    old = store.create_job('contextdb', {'release_id': release_id}, kind='ctxdb_sync')
    latest = store.create_job('contextdb', {'release_id': release_id, 'secret': 'PRIVATE-SYNC'}, kind='ctxdb_sync')
    store.update_job(latest['task_id'], status='running', phase='uploading', progress=42,
                     message='正在提交', logs=[{'message': 'PRIVATE-LOG'}])
    response = client.get(f"/task_status/{capture['task_id']}")
    capture_payload = response.json
    assert capture_payload['source_name'] == '安装说明.pdf 等 2 份'
    assert capture_payload['submission_id'] == release_id
    assert capture_payload['sync_task_id'] == latest['task_id'] != old['task_id']
    summary = capture_payload['submission_task']
    assert summary['task_id'] == latest['task_id'] and summary['source_task_id'] == capture['task_id']
    assert summary['status'] == 'running' and summary['phase'] == 'uploading' and summary['progress'] == 42
    assert 'logs' not in summary and 'params' not in summary
    assert all(secret not in response.text for secret in ('PRIVATE-PATH', 'PRIVATE-TOKEN', 'PRIVATE-SYNC', 'PRIVATE-LOG'))
    submitted = client.get(f"/task_status/{latest['task_id']}").json
    assert submitted['release_id'] == release_id and submitted['source_task_id'] == capture['task_id']
    assert submitted['submission_task'] is None
    standalone = store.create_job('contextdb', {'release_id': 'missing'}, kind='ctxdb_sync')
    assert client.get(f"/task_status/{standalone['task_id']}").json['source_task_id'] is None
    named = store.create_job('showdoc', {'user_token': 'PRIVATE-TOKEN'}, import_directory={'root_name': '产品手册'})
    assert client.get(f"/task_status/{named['task_id']}").json['source_name'] == '产品手册'


def test_task_pagination_filters_before_limiting_and_keeps_owners_separate(client):
    fake = app_module.get_store().client
    store = Store(client=fake, owner_id=os.environ['TEST_PLATFORM_USER'])
    app_module.app.extensions['governance_store'] = store
    target = store.create_job('file', {}, scope='older-target')
    for _ in range(53):
        store.create_job('file', {}, scope='recent')
    other = Store(client=fake, owner_id='another-owner')
    other.create_job('file', {}, scope='foreign-only')
    other.create_job('file', {}, scope='recent')
    default = client.get('/api/tasks').json
    assert default['total'] == 54 and len(default['tasks']) == 50
    assert default['page'] == 1 and default['page_size'] == 50
    scoped = client.get('/api/tasks?space_scope=older-target').json
    assert scoped['total'] == 1 and [row['task_id'] for row in scoped['tasks']] == [target['task_id']]
    pages = [client.get(f'/api/tasks?page={page}&page_size=20').json for page in (1, 2, 3)]
    ids = [row['task_id'] for page in pages for row in page['tasks']]
    assert [len(page['tasks']) for page in pages] == [20, 20, 14]
    assert len(set(ids)) == len(ids) == 54 and target['task_id'] in ids
    assert client.get('/api/tasks?page=999999999999999999999999999999').json['tasks'] == []
    assert client.get('/api/tasks?space_scope=foreign-only').status_code == 404
    for query in ('page=0', 'page=-1', 'page=no', 'page_size=0', 'page_size=101', 'page_size=no'):
        assert client.get('/api/tasks?' + query).status_code == 400


def test_material_task_groups_fold_and_filter_before_paging(client):
    fake = app_module.get_store().client
    store = Store(client=fake, owner_id=os.environ['TEST_PLATFORM_USER'])
    app_module.app.extensions['governance_store'] = store

    def create(status, phase, *, scope='target', release_id=None):
        params = {'release_id': release_id} if release_id else {}
        kind = 'ctxdb_sync' if release_id else 'crawl'
        task = store.create_job('contextdb' if release_id else 'file', params, scope=scope, kind=kind)
        store.update_job(task['task_id'], status=status, phase=phase)
        return task['task_id']

    first = create('failed', 'failed')
    parent = create('completed', 'submitted')
    release = store.create_release(parent, 'target', 1, [], 'archive.zip')
    old_attempt = create('failed', 'failed', release_id=release)
    submission = create('partial', 'failed', release_id=release)
    cancelled = create('cancelled', 'submitted')
    queued = create('completed', 'submitted')
    auto_failed = create('completed', 'submission_failed')
    done = create('completed', 'submitted', release_id='unlinked')
    other_scope = create('failed', 'failed', scope='other')
    other = Store(client=fake, owner_id='another-owner')
    other.update_job(other.create_job('file', {}, scope='target')['task_id'], status='failed')

    def listing(group, page=1, size=2, scope='target'):
        response = client.get('/api/tasks', query_string={
            'space_scope': scope, 'status_group': group, 'page': page, 'page_size': size})
        assert response.status_code == 200
        return response.json

    all_first = listing('all')
    assert all_first['total'] == 7  # The latest linked attempt has no separate row.
    assert [row['task_id'] for row in all_first['tasks']] == [done, auto_failed]
    needs_action = [listing('action', page) for page in (1, 2, 3)]
    assert [page['total'] for page in needs_action] == [4, 4, 4]
    assert [page['page'] for page in needs_action] == [1, 2, 3]
    action_rows = [row for page in needs_action for row in page['tasks']]
    assert [row['task_id'] for row in action_rows] == [auto_failed, old_attempt, parent, first]
    parent_row = action_rows[2]
    assert parent_row['sync_task_id'] == parent_row['submission_task']['task_id'] == submission
    assert parent_row['submission_task']['status'] == 'partial'
    assert [row['task_id'] for row in listing('active')['tasks']] == [queued]
    assert [row['task_id'] for row in listing('done')['tasks']] == [done, cancelled]
    assert [row['task_id'] for row in listing('action', scope='other')['tasks']] == [other_scope]
    assert listing('action', 999999999999999999999999)['tasks'] == []
    assert client.get('/api/tasks?status_group=failed').status_code == 400
    assert client.get('/api/tasks?space_scope=target').json['total'] == 8  # Legacy raw listing.


def test_material_task_group_leaves_a_mismatched_scope_submission_standalone(client):
    store = app_module.get_store()
    parent = store.create_job('file', {}, scope='parent')
    store.update_job(parent['task_id'], status='completed', phase='completed')
    release = store.create_release(parent['task_id'], 'parent', 1, [], 'archive.zip')
    child = store.create_job('contextdb', {'release_id': release}, scope='different', kind='ctxdb_sync')
    store.update_job(child['task_id'], status='failed', phase='failed')

    actions = client.get('/api/tasks?status_group=action').json
    assert [row['task_id'] for row in actions['tasks']] == [child['task_id']]
    assert actions['tasks'][0]['source_task_id'] is None
    done = client.get('/api/tasks?status_group=done').json
    assert [row['task_id'] for row in done['tasks']] == [parent['task_id']]
    assert done['tasks'][0]['submission_task'] is None


def test_release_scope_filter_precedes_the_recent_fifty_limit(client):
    store = app_module.get_store()
    for index in range(53):
        scope = 'older-target' if index == 0 else 'recent'
        store._create('release', f'release-{index}', {'version_ids': [], 'job_id': 'capture', 'scope': scope},
            {'release_id': f'release-{index}', 'job_id': 'capture', 'scope': scope, 'active': False})
    assert len(client.get('/api/releases').json['releases']) == 50
    scoped = client.get('/api/releases?space_scope=older-target')
    assert scoped.status_code == 200 and [row['id'] for row in scoped.json['releases']] == ['release-0']


def test_document_status_scope_filter_uses_the_same_scope_before_pagination(client):
    from governance.database import connection
    from governance.spaces import save_space
    fake = app_module.get_store().client
    owner = os.environ['TEST_PLATFORM_USER']
    store = Store(client=fake, owner_id=owner)
    app_module.app.extensions['governance_store'] = store
    save_space(store, {'scope': 'target', 'name': '目标库', 'mode': 'wiki'})
    with connection() as conn:
        for scope, count, record_owner in (('target', 23, owner), ('other', 21, owner), ('target', 2, 'another-owner')):
            conn.execute('''INSERT INTO knowledge_sync(owner_id,scope,source_id,target_mode,knowledge_base_id,status)
                SELECT %s,%s,'source-' || value,'wiki','kb','pending' FROM generate_series(1,%s) AS value''',
                (record_owner, scope, count))
    response = client.get('/api/kb/sync-mappings?space_scope=target&page=2&page_size=20')
    assert response.status_code == 200 and response.json['total'] == 23
    assert len(response.json['mappings']) == 3 and all(row['scope'] == 'target' for row in response.json['mappings'])
    assert client.get('/api/kb/sync-mappings').json['total'] == 44
    assert client.get('/api/kb/sync-mappings?space_scope=unknown').status_code == 404
