"""发布→ContextDB 知识库同步契约测试(替身)。"""
import json
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance.contextdb_sync import enqueue_sync, knowledge_kb_name, run_sync
from governance.store import Store
from tests.contextdb_fake import FakeContextDBClient


def make_release_zip(path, documents):
    with ZipFile(path, 'w') as archive:
        archive.writestr('rag_documents.jsonl',
                         '\n'.join(json.dumps(doc, ensure_ascii=False) for doc in documents) + '\n')
    return str(path)


@pytest.fixture()
def environment(tmp_path):
    client = FakeContextDBClient()
    store = Store(client=client, kb_name='_test_governance')
    release_path = make_release_zip(tmp_path / 'rel.zip', [
        {'id': 'doc-1', 'version_id': 'v1', 'title': '标题A', 'content': '# 正文A'},
        {'id': 'doc-2', 'version_id': 'v2', 'title': '标题B', 'content': '# 正文B'},
    ])
    release_id = store.create_release('job-1', 'default', 1, ['v1', 'v2'], release_path)
    return store, client, release_id


def test_knowledge_kb_name_respects_env(monkeypatch):
    assert knowledge_kb_name('web:example.com').startswith('knowledge-')
    monkeypatch.setenv('CONTEXTDB_KB_ID', 'unified-kb')
    assert knowledge_kb_name('web:example.com') == 'unified-kb'


def test_enqueue_sync_creates_ctxdb_job(environment):
    store, _, release_id = environment
    job = enqueue_sync(store, release_id, 'default')
    assert job['kind'] == 'ctxdb_sync' and job['params']['release_id'] == release_id


def test_run_sync_uploads_cleaned_documents(environment):
    store, client, release_id = environment
    job = enqueue_sync(store, release_id, 'default')
    claimed = store.claim()
    store.active_attempt = (claimed['task_id'], claimed['attempt_token'])
    result = run_sync(store, claimed)
    assert result['uploaded'] == 4 and set(result['targets']) == {'wiki', 'graph'}
    kb = client.find_knowledge_base('knowledge-default')
    assert kb['wiki_enabled'] is True and kb['review_enabled'] is True
    settings = client.get_review_settings(kb['id'])
    assert settings['high_threshold'] == 0.85 and settings['rewrite_auto_ingest_enabled'] is False
    docs = client.list_documents(kb['id'])['documents']
    assert len(docs) == 2
    by_id = {doc['name']: doc for doc in docs}
    assert by_id['doc-doc-1.md']['metadata']['source_version'] == 'v1'
    updated = store.get_job(job['task_id'])
    assert updated['status'] == 'completed' and updated['progress'] == 100
    assert '评审' in updated['message']


def test_run_sync_republish_updates_existing_documents(environment):
    store, client, release_id = environment
    job = enqueue_sync(store, release_id, 'default')
    claimed = store.claim()
    store.active_attempt = (claimed['task_id'], claimed['attempt_token'])
    run_sync(store, claimed)
    job2 = enqueue_sync(store, release_id, 'default')
    claimed2 = store.claim()
    store.active_attempt = (claimed2['task_id'], claimed2['attempt_token'])
    result = run_sync(store, claimed2)
    kb = client.find_knowledge_base('knowledge-default')
    docs = client.list_documents(kb['id'])['documents']
    assert result['uploaded'] == 0 and result['skipped'] == 4 and len(docs) == 2, '重复发布应更新而非新增'


def test_run_sync_preserves_original_filename_without_changing_document_identity(environment, tmp_path):
    store, client, _ = environment
    release_path = make_release_zip(tmp_path / 'named.zip', [{
        'id': 'uploaded-file', 'version_id': 'file-v1', 'title': '使用手册',
        'metadata': {'filename': '使用手册（完整版）.docx'}, 'archive_source': 'originals/file.docx',
    }])
    with ZipFile(release_path, 'a') as archive:
        archive.writestr('originals/file.docx', 'source bytes')
    release_id = store.create_release('job-file', 'files', 1, ['file-v1'], release_path)
    result = run_sync(store, enqueue_sync(store, release_id, 'files'))
    assert result['errors'] == []
    for kb_id in result['targets'].values():
        doc = client.list_documents(kb_id)['documents'][0]
        assert doc['name'] == 'doc-uploaded-file.docx'
        assert doc['metadata']['filename'] == '使用手册（完整版）.docx'
        assert doc['metadata']['title'] == '使用手册'


def test_metadata_changes_sync_without_reupload_and_preserve_custom_fields(environment, tmp_path, monkeypatch):
    store, client, _ = environment
    source_url = 'https://example.com/docs/' + 'a' * 250
    record = {'id': 'scoped', 'version_id': 'v1', 'title': '适用范围', 'content': '# 正文',
              'metadata': {'scope': {'product': 'ERP', 'version': '1.0', 'role': '管理员'}, 'url': source_url}}
    release_path = make_release_zip(tmp_path / 'scoped.zip', [record])
    release_id = store.create_release('scope-v1', 'default', 2, ['v1'], release_path)
    initial = run_sync(store, enqueue_sync(store, release_id, 'default'))
    assert initial['errors'] == []
    document_ids = set(client.documents)
    for doc in client.documents.values():
        assert {key: doc['metadata'][key] for key in ('product', 'version', 'role', 'url')} == {
            'product': 'ERP', 'version': '1.0', 'role': '管理员', 'url': source_url}
        doc['metadata']['labels'] = ['人工标注', '重要']

    record.update(version_id='v2')
    record['metadata'] = {'scope': {'product': 'ERP', 'version': '2.0'}, 'url': 'https://example.com/v2'}
    release_path = make_release_zip(tmp_path / 'scoped-v2.zip', [record])
    release_id = store.create_release('scope-v2', 'default', 3, ['v2'], release_path)
    writes = []
    update_metadata = client.update_document_metadata
    def write_metadata(metadata, **kwargs):
        writes.append(kwargs['document_id'])
        return update_metadata(metadata, **kwargs)
    def must_not_reupload(*args, **kwargs):
        raise AssertionError('Metadata-only changes must not resubmit source content')
    monkeypatch.setattr(client, 'update_document_metadata', write_metadata)
    monkeypatch.setattr(client, 'upload_file', must_not_reupload)
    monkeypatch.setattr(client, 'update_file', must_not_reupload)
    result = run_sync(store, enqueue_sync(store, release_id, 'default'))
    assert result['errors'] == [] and result['uploaded'] == 2 and len(writes) == 2
    assert set(client.documents) == document_ids
    for kb_id in result['targets'].values():
        doc = client.list_documents(kb_id, metadata_condition={'product': 'ERP', 'version': '2.0'})['documents'][0]
        assert doc['metadata']['source_version'] == 'v2'
        assert doc['metadata']['url'] == 'https://example.com/v2'
        assert doc['metadata']['labels'] == ['人工标注', '重要']
        assert 'role' not in doc['metadata']
    repeated = run_sync(store, enqueue_sync(store, release_id, 'default'))
    assert repeated['errors'] == [] and repeated['skipped'] == 2 and len(writes) == 2


def test_content_updates_keep_remote_custom_metadata(environment, tmp_path):
    store, client, release_id = environment
    run_sync(store, enqueue_sync(store, release_id, 'default'))
    for doc in client.documents.values():
        doc['metadata']['approved'] = True
    release_path = make_release_zip(tmp_path / 'changed.zip', [
        {'id': 'doc-1', 'version_id': 'v3', 'title': '新标题', 'content': '# 新正文'}])
    release_id = store.create_release('content-v3', 'default', 2, ['v3'], release_path)
    result = run_sync(store, enqueue_sync(store, release_id, 'default'))
    assert result['errors'] == [] and result['uploaded'] == 2
    for kb_id in result['targets'].values():
        doc = next(doc for doc in client.list_documents(kb_id)['documents'] if doc['name'] == 'doc-doc-1.md')
        assert doc['metadata']['approved'] is True
        assert doc['metadata']['source_version'] == 'v3'


def test_metadata_response_loss_is_reconciled_before_retry(environment, tmp_path, monkeypatch):
    from integrations.contextdb import ContextDBError
    store, client, release_id = environment
    run_sync(store, enqueue_sync(store, release_id, 'default'))
    release_path = make_release_zip(tmp_path / 'metadata.zip', [
        {'id': 'doc-1', 'version_id': 'v3', 'title': '标题A', 'content': '# 正文A',
         'metadata': {'scope': {'version': '3.0'}}}])
    release_id = store.create_release('metadata-v3', 'default', 2, ['v3'], release_path)
    update_metadata = client.update_document_metadata
    def lost_response(metadata, **kwargs):
        update_metadata(metadata, **kwargs)
        raise ContextDBError('Response lost after metadata was accepted')
    def must_not_write(*args, **kwargs):
        raise AssertionError('Read-back confirmed this metadata; no write is needed')
    monkeypatch.setattr(client, 'update_document_metadata', lost_response)
    monkeypatch.setattr(client, 'upload_file', must_not_write)
    monkeypatch.setattr(client, 'update_file', must_not_write)
    failed = run_sync(store, enqueue_sync(store, release_id, 'default'))
    assert len(failed['errors']) == 2
    monkeypatch.setattr(client, 'update_document_metadata', must_not_write)
    repeated = run_sync(store, enqueue_sync(store, release_id, 'default'))
    assert repeated['errors'] == [] and repeated['uploaded'] == 0 and repeated['skipped'] == 2
    for kb_id in repeated['targets'].values():
        assert len(client.list_documents(kb_id, metadata_condition={'version': '3.0'})['documents']) == 1


def test_run_sync_missing_archive_fails_job(environment):
    store, _, release_id = environment
    release = store.get_release(release_id)
    Path(release['archive_path']).unlink()
    job = enqueue_sync(store, release_id, 'default')
    claimed = store.claim()
    store.active_attempt = (claimed['task_id'], claimed['attempt_token'])
    with pytest.raises(Exception):
        run_sync(store, claimed)


def test_partial_failure_does_not_claim_both_targets_complete(environment, monkeypatch):
    store,client,release_id=environment
    upload=client.upload_file
    def fail_graph(kb,name,path,**kwargs):
        if client.get_knowledge_base(kb)['graph_enabled']:
            raise RuntimeError('graph delivery failed')
        return upload(kb,name,path,**kwargs)
    monkeypatch.setattr(client,'upload_file',fail_graph)
    job=enqueue_sync(store,release_id,'default')
    result=run_sync(store,job)
    assert result['uploaded']==2 and len(result['errors'])==2
    assert store.get_job(job['task_id'])['status']=='partial'
    from governance.database import connection
    with connection() as conn:
        states=conn.execute('SELECT target_mode,status FROM knowledge_sync').fetchall()
    assert [r['status'] for r in states if r['target_mode']=='graph']==['uncertain','uncertain']
    assert all(r['status']=='succeeded' for r in states if r['target_mode']=='wiki')


def test_unchanged_pending_review_is_not_resubmitted(environment, monkeypatch):
    store,client,release_id=environment
    job=enqueue_sync(store,release_id,'default');run_sync(store,job)
    for doc in client.documents.values():
        doc['ingest_status']='pending_review'
        doc['metadata']={}
    def must_not_write(*args,**kwargs):
        raise AssertionError('Known accepted hash must not be uploaded again while review is pending')
    monkeypatch.setattr(client,'upload_file',must_not_write)
    monkeypatch.setattr(client,'update_file',must_not_write)
    result=run_sync(store,enqueue_sync(store,release_id,'default'))
    assert result['uploaded']==4 and result['errors']==[]
    assert all(doc['ingest_status']=='pending_review' and doc['metadata']['source_content_hash']
               for doc in client.documents.values())
    repeated=run_sync(store,enqueue_sync(store,release_id,'default'))
    assert repeated['uploaded']==0 and repeated['skipped']==4 and repeated['errors']==[]


def test_deleted_environment_target_is_recreated_under_a_name_not_the_retired_id(environment, monkeypatch):
    from governance.spaces import get_space
    store, client, release_id = environment
    monkeypatch.setenv('CONTEXTDB_KB_ID', 'retired-knowledge-base-id')
    job = enqueue_sync(store, release_id, 'default')
    assert job['params']['target_ids']['wiki'] is None
    result = run_sync(store, job)
    assert result['errors'] == [] and result['uploaded'] == 4
    replacement = client.get_knowledge_base(result['targets']['wiki'])
    assert replacement['name'] == 'knowledge-default'
    assert get_space(store, 'default')['wiki_kb_id'] == replacement['id']
    assert client.find_knowledge_base('retired-knowledge-base-id') is None


def test_a_healthy_previous_mapping_is_never_automatically_migrated(environment):
    from governance.spaces import get_space, persist_space
    store, client, release_id = environment
    initial = run_sync(store, enqueue_sync(store, release_id, 'default'))
    replacement = client.create_knowledge_base('different-healthy-target', wiki_enabled=True)
    # Simulate an independently changed routing record; the delivery guard must still hold.
    persist_space(store, {**get_space(store, 'default'), 'wiki_kb_id': replacement['id']})
    result = run_sync(store, enqueue_sync(store, release_id, 'default'))
    assert result['errors'] and client.list_documents(replacement['id'])['documents'] == []
    assert store._list({'type': 'knowledge_sync_history'}) == []
    assert len(client.list_documents(initial['targets']['wiki'])['documents']) == 2
