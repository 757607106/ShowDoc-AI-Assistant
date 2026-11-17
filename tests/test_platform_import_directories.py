"""Directory links follow successful delivery, including old task history and retries."""
import json
import os
from pathlib import Path
from zipfile import ZipFile

import pytest

import app as app_module
from governance.contextdb_sync import _save, run_sync
from governance.import_directories import ImportDirectories
from governance.spaces import persist_space
from governance.store import Store
from governance.worker import process_job, publish
from tests.contextdb_fake import FakeContextDBClient


@pytest.fixture()
def environment(authenticated_client, monkeypatch):
    fake = FakeContextDBClient()
    store = Store(client=fake, owner_id=os.environ['TEST_PLATFORM_USER'])
    app_module.app.extensions['governance_store'] = store
    monkeypatch.setattr('webapi.auth.client_for_user', lambda *args: fake)
    yield store, fake, authenticated_client
    app_module.app.extensions.pop('governance_store', None)


def bind_space(store, kb, scope='product'):
    persist_space(store, {'scope': scope, 'name': kb['name'], 'knowledge_base_id': kb['id'],
                         'mode': 'wiki', 'lifecycle': 'active'})


def source_root(store, kb, source_key, name, *, populated=True):
    manager = ImportDirectories(store, kb['id'])
    parent, root = manager.target({'source_key': source_key,
        'metadata': {'import_directory': {'root_name': name, 'path': []}}})
    document = None
    if populated:
        document = store.client.create_text_document(kb['id'], source_key + '.md', '# 原文')
        manager.attach(document['id'], parent)
        manager.populated(root)
    return {'knowledge_base_id': kb['id'], 'node_id': parent, 'root_name': name}, document


def test_task_links_only_include_populated_roots_of_the_capture_source(environment):
    store, fake, http = environment
    kb = fake.create_knowledge_base('业务知识', wiki_enabled=True)
    bind_space(store, kb)
    expected, _ = source_root(store, kb, 'showdoc:399', '云辉煌知识库')
    other, _ = source_root(store, kb, 'showdoc:412', '版本说明')
    source_root(store, kb, 'showdoc:empty', '尚未投递', populated=False)
    capture = store.create_job('showdoc', {'item_id': '399'}, scope='product')
    empty = store.create_job('showdoc', {'item_id': 'empty'}, scope='product')
    assert http.get('/task_status/' + capture['task_id']).json['import_directories'] == [expected]
    assert http.get('/task_status/' + empty['task_id']).json['import_directories'] == []
    sync = store.create_job('contextdb', {'knowledge_base_id': kb['id']}, kind='ctxdb_sync', scope='product')
    payload = http.get('/task_status/' + sync['task_id']).json
    assert {location['node_id'] for location in payload['import_directories']} == {expected['node_id'], other['node_id']}
    assert payload['directory_sync_complete'] is False


def test_legacy_task_links_use_knowledge_sync_without_a_space_record(environment):
    store, fake, http = environment
    kb = fake.create_knowledge_base('历史资料', wiki_enabled=True)
    expected, document = source_root(store, kb, 'showdoc:399', '云辉煌知识库')
    source_root(store, kb, 'showdoc:412', '其他来源')
    capture = store.create_job('showdoc', {'item_id': '399'}, scope='legacy-history')
    assert store._find('knowledge_space', scope='legacy-history') is None
    _save(store.owner_id, 'legacy-history', 'historical-document', 'wiki', kb['id'],
          document_id=document['id'], status='succeeded')
    payload = http.get('/task_status/' + capture['task_id']).json
    assert payload['import_directories'] == [expected]
    listed = next(task for task in http.get('/api/tasks').json['tasks'] if task['task_id'] == capture['task_id'])
    assert listed['import_directories'] == [expected]


def test_custom_root_survives_retry_worker_release_and_pending_delivery(environment, monkeypatch):
    store, fake, http = environment
    kb = fake.create_knowledge_base('资料库', wiki_enabled=True, review_enabled=True)
    bind_space(store, kb)
    uploads = Path(os.environ['GOVERNANCE_DATA_DIR']) / 'uploads'
    uploads.mkdir(parents=True)
    source = uploads / 'guide.md'
    source.write_text('# 业务资料\n\n完整原文。')
    original = store.create_job('file', {'file_paths': [str(source)]}, scope='product',
                                import_directory={'root_name': '自定义资料'})
    store.update_job(original['task_id'], status='failed')
    response = http.post('/tasks/' + original['task_id'] + '/retry')
    assert response.status_code == 200
    retried = store.get_job(response.json['task_id'])
    assert retried['import_directory'] == {'root_name': '自定义资料'}
    assert retried['source_key'] == original['source_key'] == 'file'
    assert retried['params'] == original['params'] and 'import_root_name' not in retried['params']
    monkeypatch.setattr('common.converter.RAGContentPipeline.convert',
                        lambda *args, **kwargs: pytest.fail('Capture must not parse locally'))
    process_job(store, retried)
    captured = store.get_job(retried['task_id'])
    assert captured['status'] == 'completed' and captured['phase'] == 'submitted'
    document = store.get_document(store.list_documents(retried['task_id'])[0]['version_id'])
    assert document['metadata']['import_directory'] == {'root_name': '自定义资料', 'path': []}
    release_record = store._find('release', job_id=retried['task_id'])
    release = store.get_release(release_record['metadata']['release_id'])
    with ZipFile(release['archive_path']) as archive:
        records = [json.loads(line) for line in archive.read('rag_documents.jsonl').decode().splitlines()]
    assert len(records) == 1 and records[0]['source_key'] == 'file'
    assert records[0]['metadata']['import_directory'] == {'root_name': '自定义资料', 'path': []}
    sync = next(job for job in store.list_jobs() if job['kind'] == 'ctxdb_sync')
    before = http.get('/task_status/' + retried['task_id']).json
    assert before['status'] == 'completed' and before['directory_sync_complete'] is False
    assert before['import_directories'] == []
    result = run_sync(store, sync)
    assert result['errors'] == [] and result['uploaded'] == 1
    after = http.get('/task_status/' + retried['task_id']).json
    assert after['directory_sync_complete'] is True
    assert len(after['import_directories']) == 1 and after['import_directories'][0]['root_name'] == '自定义资料'
    assert http.get('/task_status/' + sync['task_id']).json['directory_sync_complete'] is True


def test_changing_root_for_unchanged_saved_capture_renames_without_reupload(environment, monkeypatch):
    store, fake, http = environment
    kb = fake.create_knowledge_base('资料库', wiki_enabled=True, review_enabled=True)
    bind_space(store, kb)
    uploads = Path(os.environ['GOVERNANCE_DATA_DIR']) / 'uploads'
    uploads.mkdir(parents=True)
    source = uploads / 'guide.md'
    source.write_text('# 业务资料\n\n正文保持不变。')
    original = store.create_job('file', {'file_paths': [str(source)]}, scope='product',
                                import_directory={'root_name': '原目录'})
    process_job(store, original)
    first = store.get_document(store.list_documents(original['task_id'])[0]['version_id'])
    sync = next(job for job in store.list_jobs() if job['kind'] == 'ctxdb_sync')
    assert run_sync(store, sync)['errors'] == []
    cloud_ids = set(fake.documents)
    cloud_before = fake.get_document(kb['id'], next(iter(cloud_ids)))
    root_before = http.get('/task_status/' + original['task_id']).json['import_directories'][0]

    changed = store.create_job('file', original['params'], scope='product', retry_of=original['task_id'],
                               import_directory={'root_name': '新目录'})
    monkeypatch.setattr('registry.create_crawler',
                        lambda *args, **kwargs: pytest.fail('Reuse the saved complete capture'))
    process_job(store, changed)
    assert store.get_job(changed['task_id'])['status'] == 'completed'
    second = store.get_document(store.list_documents(changed['task_id'])[0]['version_id'])
    assert second['id'] == first['id'] and second['version_id'] != first['version_id']
    assert second['source']['source_sha256'] == first['source']['source_sha256']
    assert second['metadata']['import_directory'] == {'root_name': '新目录', 'path': []}
    saved_records = [json.loads(line) for line in (Path(changed['output_dir']) / 'rag_documents.jsonl').read_text().splitlines()]
    assert saved_records[0]['metadata']['import_directory']['root_name'] == '原目录'
    release_record = store._find('release', job_id=changed['task_id'])
    with ZipFile(store.get_release(release_record['metadata']['release_id'])['archive_path']) as archive:
        submitted = json.loads(archive.read('rag_documents.jsonl').decode().splitlines()[0])
    assert submitted['metadata']['import_directory'] == {'root_name': '新目录', 'path': []}
    monkeypatch.setattr(fake, 'upload_file', lambda *args, **kwargs: pytest.fail('Do not duplicate unchanged content'))
    monkeypatch.setattr(fake, 'update_file', lambda *args, **kwargs: pytest.fail('Do not resubmit unchanged content'))
    sync = next(job for job in store.list_jobs() if job['kind'] == 'ctxdb_sync' and
                job['params']['release_id'] == release_record['metadata']['release_id'])
    assert run_sync(store, sync)['errors'] == []
    assert set(fake.documents) == cloud_ids
    root_after = http.get('/task_status/' + changed['task_id']).json['import_directories'][0]
    assert root_after['node_id'] == root_before['node_id'] and root_after['root_name'] == '新目录'
    cloud_after = fake.get_document(kb['id'], next(iter(cloud_ids)))
    assert cloud_after.get('latest_ingest_event_id') == cloud_before.get('latest_ingest_event_id')


def test_file_based_revision_keeps_the_original_source_directory(environment):
    store, fake, http = environment
    kb = fake.create_knowledge_base('业务资料', wiki_enabled=True, review_enabled=True)
    bind_space(store, kb)
    directory = {'root_name': '云辉煌知识库', 'path': ['进货管理', '报表']}
    original = store.create_job('showdoc', {'item_id': '399'}, scope='product')
    record = {'id': 'page-one', 'title': '进货统计', 'category': '进货管理/报表',
              'content': '# 旧正文', 'source_format': 'markdown', 'metadata': {'import_directory': directory}}
    store.ingest(original, [record], {'page-one': {**record, 'source_sha256': 'original-source'}}, [])
    store.update_job(original['task_id'], status='completed', capture_complete=True)
    first = store.get_document(store.list_documents(original['task_id'])[0]['version_id'])
    publish(store, original['task_id'])
    sync = next(job for job in store.list_jobs() if job['kind'] == 'ctxdb_sync')
    assert run_sync(store, sync)['errors'] == []
    roots_before = http.get('/task_status/' + original['task_id']).json['import_directories']

    response = http.post('/api/documents/' + first['version_id'] + '/revisions',
                         json={'content': '# 人工修订的新正文', 'reason': '更新操作步骤'})
    assert response.status_code == 200
    revision = store.get_job(response.json['task_id'])
    assert revision['entry'] == 'file' and revision['source_key'] == 'showdoc:399'
    process_job(store, revision)
    assert store.get_job(revision['task_id'])['status'] == 'completed'
    revised = store.get_document(store.list_documents(revision['task_id'])[0]['version_id'])
    assert revised['id'] == first['id'] and revised['version_id'] != first['version_id']
    assert revised['metadata']['import_directory'] == directory
    sync = next(job for job in store.list_jobs() if job['kind'] == 'ctxdb_sync' and
                job['params']['release_id'] != sync['params']['release_id'])
    assert run_sync(store, sync)['errors'] == []
    assert len(fake.documents) == 1
    assert http.get('/task_status/' + revision['task_id']).json['import_directories'] == roots_before


def test_partial_recapture_renames_source_once_and_other_sources_do_not_revert_it(environment, monkeypatch):
    store, fake, http = environment
    kb = fake.create_knowledge_base('多来源资料', wiki_enabled=True, review_enabled=True)
    bind_space(store, kb)
    uploads = Path(os.environ['GOVERNANCE_DATA_DIR']) / 'uploads'
    uploads.mkdir(parents=True)
    files = [uploads / 'one.md', uploads / 'two.md']
    for index, path in enumerate(files):
        path.write_text(f'# 第 {index + 1} 份原文\n\n业务内容。')
    first = store.create_job('file', {'file_paths': [str(path) for path in files]}, scope='product',
                            import_directory={'root_name': '原文件目录'})
    process_job(store, first)
    sync = next(job for job in store.list_jobs() if job['kind'] == 'ctxdb_sync')
    assert run_sync(store, sync)['errors'] == []
    original_cloud_ids = set(fake.documents)
    old_root = http.get('/task_status/' + first['task_id']).json['import_directories'][0]
    uploads_seen, updates_seen = [], []
    upload, update = fake.upload_file, fake.update_file

    def upload_file(*args, **kwargs):
        uploads_seen.append(args[1])
        return upload(*args, **kwargs)

    def update_file(*args, **kwargs):
        updates_seen.append(args[0])
        return update(*args, **kwargs)

    monkeypatch.setattr(fake, 'upload_file', upload_file)
    monkeypatch.setattr(fake, 'update_file', update_file)
    changed = store.create_job('file', {'file_paths': [str(files[0])]}, scope='product',
                              import_directory={'root_name': '新文件目录'})
    process_job(store, changed)
    release_record = store._find('release', job_id=changed['task_id'])
    with ZipFile(store.get_release(release_record['metadata']['release_id'])['archive_path']) as archive:
        records = [json.loads(line) for line in archive.read('rag_documents.jsonl').decode().splitlines()]
    assert {record['metadata']['import_directory']['root_name'] for record in records} == {'原文件目录', '新文件目录'}
    sync = next(job for job in store.list_jobs() if job['kind'] == 'ctxdb_sync' and
                job['params']['release_id'] == release_record['metadata']['release_id'])
    assert run_sync(store, sync)['errors'] == []
    assert uploads_seen == updates_seen == []
    changed_root = http.get('/task_status/' + changed['task_id']).json['import_directories'][0]
    assert changed_root == {**old_root, 'root_name': '新文件目录'}

    other = store.create_job('cyb', {}, scope='product', import_directory={'root_name': '创业版资料'})
    record = {'id': 'cyb-one', 'title': '创业版说明', 'category': '使用教程', 'content': '# 其他来源正文',
              'source_format': 'markdown', 'metadata': {
                  'import_directory': {'root_name': '创业版资料', 'path': ['使用教程']}}}
    store.ingest(other, [record], {'cyb-one': {**record, 'source_sha256': 'other-source'}}, [])
    store.update_job(other['task_id'], status='completed', capture_complete=True)
    release_id = publish(store, other['task_id'])
    sync = next(job for job in store.list_jobs() if job['kind'] == 'ctxdb_sync' and
                job['params']['release_id'] == release_id)
    assert run_sync(store, sync)['errors'] == []
    assert len(uploads_seen) == 1 and updates_seen == []
    assert original_cloud_ids < set(fake.documents)
    assert http.get('/task_status/' + changed['task_id']).json['import_directories'] == [changed_root]
