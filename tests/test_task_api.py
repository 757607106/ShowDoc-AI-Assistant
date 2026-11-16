"""任务生命周期 API 契约测试(app 路由 × ContextDB 治理存储替身)。"""
import json
import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as app_module
from governance.store import Store, StoreError
from governance.worker import write_json
from tests.contextdb_fake import FakeContextDBClient


@pytest.fixture()
def client(authenticated_client):
    app_module.app.extensions['governance_store'] = Store(client=FakeContextDBClient(),
                                                          kb_name='_test_governance')
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
    checked = []
    def get_space(store, scope):
        checked.append(scope)
        if scope != 'product-a':
            raise StoreError('知识空间不存在', 404)
        return {'scope': scope}
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
    assert checked == ['product-a', 'product-a', 'product-a']
    assert client.post('/api/uploads', data={'files':(io.BytesIO(b'x'),'x.md'),'space_scope':'missing'}).status_code == 404
    assert client.post('/entries/web/start', json={'url':'https://example.test','space_scope':[]}).status_code == 400


def test_upload_name_mapping_keeps_natural_prefixes_and_duplicate_names_without_overwriting(client, monkeypatch):
    import governance.spaces as spaces
    monkeypatch.setattr(spaces, 'get_space', lambda store, scope: {'scope': scope})
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
