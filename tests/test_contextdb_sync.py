"""发布→ContextDB 知识库同步契约测试(替身)。"""
import json
import hashlib
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance.contextdb_sync import enqueue_sync, knowledge_kb_name, run_sync
from governance.store import Store, StoreError
from governance.spaces import get_space, persist_space
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
    kb = client.create_knowledge_base('knowledge-default', wiki_enabled=True, graph_enabled=False, review_enabled=True)
    persist_space(store, {'scope': 'default', 'name': kb['name'], 'knowledge_base_id': kb['id'],
                          'mode': 'wiki', 'lifecycle': 'active'})
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
    assert job['kind'] == 'ctxdb_sync' and job['params'] == {
        'release_id': release_id, 'knowledge_base_id': get_space(store, 'default')['knowledge_base_id'], 'target_mode': 'wiki'}


def test_run_sync_uploads_cleaned_documents(environment):
    store, client, release_id = environment
    job = enqueue_sync(store, release_id, 'default')
    claimed = store.claim()
    store.active_attempt = (claimed['task_id'], claimed['attempt_token'])
    result = run_sync(store, claimed)
    assert result['uploaded'] == 2 and set(result['targets']) == {'wiki'}
    kb = client.find_knowledge_base('knowledge-default')
    assert kb['wiki_enabled'] is True and kb['review_enabled'] is True
    assert len(client.knowledge_bases) == 1, '同步不创建第二个目标库'
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
    assert result['uploaded'] == 0 and result['skipped'] == 2 and len(docs) == 2, '重复发布不重复上传'


def test_run_sync_preserves_original_filename_without_changing_document_identity(environment, tmp_path):
    store, client, _ = environment
    release_path = make_release_zip(tmp_path / 'named.zip', [{
        'id': 'uploaded-file', 'version_id': 'file-v1', 'title': '使用手册',
        'metadata': {'filename': '使用手册（完整版）.docx'}, 'archive_source': 'originals/file.docx',
    }])
    with ZipFile(release_path, 'a') as archive:
        archive.writestr('originals/file.docx', 'source bytes')
    release_id = store.create_release('job-file', 'default', 2, ['file-v1'], release_path)
    result = run_sync(store, enqueue_sync(store, release_id, 'default'))
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
    assert result['errors'] == [] and result['uploaded'] == 1 and len(writes) == 1
    assert set(client.documents) == document_ids
    for kb_id in result['targets'].values():
        doc = client.list_documents(kb_id, metadata_condition={'product': 'ERP', 'version': '2.0'})['documents'][0]
        assert doc['metadata']['source_version'] == 'v2'
        assert doc['metadata']['url'] == 'https://example.com/v2'
        assert doc['metadata']['labels'] == ['人工标注', '重要']
        assert 'role' not in doc['metadata']
    repeated = run_sync(store, enqueue_sync(store, release_id, 'default'))
    assert repeated['errors'] == [] and repeated['skipped'] == 1 and len(writes) == 1


def test_content_updates_keep_remote_custom_metadata(environment, tmp_path):
    store, client, release_id = environment
    run_sync(store, enqueue_sync(store, release_id, 'default'))
    for doc in client.documents.values():
        doc['metadata']['approved'] = True
    release_path = make_release_zip(tmp_path / 'changed.zip', [
        {'id': 'doc-1', 'version_id': 'v3', 'title': '新标题', 'content': '# 新正文'}])
    release_id = store.create_release('content-v3', 'default', 2, ['v3'], release_path)
    result = run_sync(store, enqueue_sync(store, release_id, 'default'))
    assert result['errors'] == [] and result['uploaded'] == 1
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
    assert len(failed['errors']) == 1
    monkeypatch.setattr(client, 'update_document_metadata', must_not_write)
    repeated = run_sync(store, enqueue_sync(store, release_id, 'default'))
    assert repeated['errors'] == [] and repeated['uploaded'] == 0 and repeated['skipped'] == 1
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


def test_partial_failure_keeps_successful_documents_and_official_states(environment, monkeypatch):
    store,client,release_id=environment
    upload=client.upload_file
    def fail_one(kb,name,path,**kwargs):
        if name == 'doc-doc-2.md':
            raise RuntimeError('delivery failed')
        return upload(kb,name,path,**kwargs)
    monkeypatch.setattr(client,'upload_file',fail_one)
    job=enqueue_sync(store,release_id,'default')
    result=run_sync(store,job)
    assert result['uploaded']==1 and len(result['errors'])==1
    assert store.get_job(job['task_id'])['status']=='partial'
    from governance.database import connection
    with connection() as conn:
        states=conn.execute('SELECT source_id,target_mode,status FROM knowledge_sync ORDER BY source_id').fetchall()
    assert [r['status'] for r in states]==['succeeded','uncertain']
    assert all(r['target_mode']=='wiki' for r in states)


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
    assert result['uploaded']==2 and result['errors']==[]
    assert all(doc['ingest_status']=='pending_review' and doc['metadata']['source_content_hash']
               for doc in client.documents.values())
    repeated=run_sync(store,enqueue_sync(store,release_id,'default'))
    assert repeated['uploaded']==0 and repeated['skipped']==2 and repeated['errors']==[]


def test_missing_target_never_recreates_a_library_or_submits_a_document(environment, monkeypatch):
    store, client, release_id = environment
    job = enqueue_sync(store, release_id, 'default')
    client.delete_knowledge_base(job['params']['knowledge_base_id'])
    monkeypatch.setattr(client, 'create_knowledge_base', lambda *a, **kw: pytest.fail('missing targets must not be recreated'))
    with pytest.raises(StoreError, match='删除|知识库'):
        run_sync(store, job)
    with pytest.raises(StoreError, match='删除|知识库'):
        enqueue_sync(store, release_id, 'default')
    assert not client.knowledge_bases and not client.documents


def test_a_healthy_previous_mapping_is_never_automatically_migrated(environment):
    store, client, release_id = environment
    initial = run_sync(store, enqueue_sync(store, release_id, 'default'))
    replacement = client.create_knowledge_base('different-healthy-target', wiki_enabled=True)
    # Simulate an independently changed routing record; the delivery guard must still hold.
    persist_space(store, {**get_space(store, 'default'), 'knowledge_base_id': replacement['id']})
    result = run_sync(store, enqueue_sync(store, release_id, 'default'))
    assert result['errors'] and client.list_documents(replacement['id'])['documents'] == []
    assert store._list({'type': 'knowledge_sync_history'}) == []
    assert len(client.list_documents(initial['targets']['wiki'])['documents']) == 2


@pytest.mark.parametrize('mode', ['source', 'graph', 'wiki'])
def test_each_mode_delivers_once_and_reads_authoritative_ingest_state(tmp_path, monkeypatch, mode):
    client = FakeContextDBClient()
    store = Store(client=client)
    kb = client.create_knowledge_base('业务资料', wiki_enabled=mode == 'wiki',
        graph_enabled=mode == 'graph', review_enabled=True)
    persist_space(store, {'scope': 'business', 'name': kb['name'], 'mode': mode,
        'knowledge_base_id': kb['id'], 'lifecycle': 'active'})
    archive = make_release_zip(tmp_path / 'release.zip', [
        {'id': 'first', 'content': '# 第一篇', 'source_format': 'markdown'},
        {'id': 'second', 'content': '# 第二篇', 'source_format': 'markdown'}])
    with ZipFile(archive, 'a') as output:
        output.writestr('业务资料合集.md', '# 第一篇\n\n# 第二篇')
    release_id = store.create_release('capture', 'business', 1, [], archive)
    calls = []
    upload = client.upload_file
    def upload_with_async_review(kb_id, name, path, **kwargs):
        calls.append((kb_id, name))
        accepted = upload(kb_id, name, path, **kwargs)
        client.documents[accepted['id']]['ingest_status'] = 'pending_review'
        return {**accepted, 'ingest_status': 'processing'}
    monkeypatch.setattr(client, 'upload_file', upload_with_async_review)
    job = enqueue_sync(store, release_id, 'business')
    assert job['params'] == {'release_id': release_id, 'knowledge_base_id': kb['id'], 'target_mode': mode}
    result = run_sync(store, job)
    assert result['errors'] == [] and result['total'] == result['uploaded'] == 2
    assert calls == [(kb['id'], 'doc-first.md'), (kb['id'], 'doc-second.md')]
    assert len(client.knowledge_bases) == 1 and len(client.documents) == 2
    from governance.database import connection
    with connection() as conn:
        rows = conn.execute('SELECT target_mode,status FROM knowledge_sync').fetchall()
    assert all(row['target_mode'] == mode and row['status'] == 'pending_review' for row in rows)


def test_old_single_target_job_is_accepted_but_double_target_is_blocked(environment):
    store, client, release_id = environment
    kb_id = get_space(store, 'default')['knowledge_base_id']
    dual = store.create_job('contextdb', {'release_id': release_id,
        'target_modes': ['wiki', 'graph'], 'target_ids': {'wiki': kb_id, 'graph': 'another'}},
        kind='ctxdb_sync', scope='default')
    with pytest.raises(StoreError, match='旧双目标任务'):
        run_sync(store, dual)
    assert not client.documents
    single = store.create_job('contextdb', {'release_id': release_id,
        'target_modes': ['wiki'], 'target_ids': {'wiki': kb_id}}, kind='ctxdb_sync', scope='default')
    result = run_sync(store, single)
    assert result['errors'] == [] and result['uploaded'] == 2


@pytest.mark.parametrize('lifecycle', ['deleted', 'deleting'])
def test_deleted_binding_cannot_be_reactivated_by_a_queued_job(environment, lifecycle):
    store, client, release_id = environment
    job = enqueue_sync(store, release_id, 'default')
    persist_space(store, {**get_space(store, 'default'), 'lifecycle': lifecycle})
    with pytest.raises(StoreError, match='删除'):
        run_sync(store, job)
    with pytest.raises(StoreError, match='删除'):
        enqueue_sync(store, release_id, 'default')
    assert not client.documents


def test_html_review_is_markdown_and_resubmission_preserves_adopted_text(environment, tmp_path, monkeypatch):
    store, client, _ = environment
    html = '<h1>配置手册</h1><p>端口为 8080。</p><img src="images/step.png" alt="配置截图">'
    path = make_release_zip(tmp_path / 'html.zip', [{'id': 'html', 'version_id': 'html-v1',
        'title': '配置手册', 'content': html, 'source_format': 'html',
        'metadata': {'url': 'https://example.test/manual/'}}])
    release_id = store.create_release('html-capture', 'default', 2, ['html-v1'], path)
    first = run_sync(store, enqueue_sync(store, release_id, 'default'))
    assert first['errors'] == [] and first['uploaded'] == 1
    doc = next(iter(client.documents.values()))
    assert doc['name'] == 'doc-html.md' and '<h1>' not in doc['text']
    assert '端口为 8080' in doc['text'] and 'https://example.test/manual/images/step.png' in doc['text']
    assert doc['metadata']['source_content_hash'] == hashlib.sha256(html.encode()).hexdigest()
    assert doc['metadata']['submitted_content_hash'] == hashlib.sha256(doc['text'].encode()).hexdigest()
    assert doc['metadata']['source_content_hash'] != doc['metadata']['submitted_content_hash']
    from governance.database import connection
    with connection() as conn:
        receipt = conn.execute('SELECT source_hash,conversion_fingerprint FROM knowledge_sync').fetchone()
    assert receipt['source_hash'] == doc['metadata']['source_content_hash']
    assert receipt['conversion_fingerprint'] == doc['metadata']['source_conversion_fingerprint']
    doc['text'] = '# 经人工采纳的重写稿\n端口改为经核实的 9090。'
    doc['ingest_status'] = 'pending_review'
    # While a new review is pending the official metadata snapshot may still be old.
    doc['metadata'] = {}
    def no_content_write(*args, **kwargs):
        pytest.fail('同一份原件不得覆盖已采纳稿或重新触发评审')
    monkeypatch.setattr(client, 'upload_file', no_content_write)
    monkeypatch.setattr(client, 'update_file', no_content_write)
    repeated = run_sync(store, enqueue_sync(store, release_id, 'default'))
    assert repeated['errors'] == [] and doc['text'].endswith('9090。')
    third = run_sync(store, enqueue_sync(store, release_id, 'default'))
    assert third['skipped'] == 1 and third['errors'] == []
    with ZipFile(path) as archive:
        assert json.loads(archive.read('rag_documents.jsonl'))['content'] == html


def test_html_resource_base_change_updates_derived_content(environment, tmp_path):
    store, client, _ = environment
    record = {'id': 'html', 'version_id': 'v1', 'content': '<p>查看截图</p><img src="image.png">',
              'source_format': 'html', 'metadata': {'url': 'https://example.test/v1/'}}
    archive = make_release_zip(tmp_path / 'first.zip', [record])
    first = store.create_release('first', 'default', 2, ['v1'], archive)
    assert not run_sync(store, enqueue_sync(store, first, 'default'))['errors']
    doc = next(iter(client.documents.values()))
    original_hash = doc['metadata']['source_content_hash']
    fingerprint = doc['metadata']['source_conversion_fingerprint']
    record.update(version_id='v2', metadata={'url': 'https://example.test/v2/'})
    second = store.create_release('second', 'default', 3, ['v2'], make_release_zip(tmp_path / 'second.zip', [record]))
    result = run_sync(store, enqueue_sync(store, second, 'default'))
    assert result['uploaded'] == 1 and result['errors'] == []
    assert 'https://example.test/v2/image.png' in doc['text']
    assert doc['metadata']['source_content_hash'] == original_hash
    assert doc['metadata']['source_conversion_fingerprint'] != fingerprint


@pytest.mark.parametrize('name,content', [('slides.pptx', b'slides'), ('empty.html', b'<div></div>')])
def test_review_blocks_sources_without_supported_review_body(environment, tmp_path, name, content):
    store, client, _ = environment
    archive = make_release_zip(tmp_path / 'unsupported.zip', [{'id': 'unsupported', 'archive_source': name}])
    with ZipFile(archive, 'a') as output:
        output.writestr(name, content)
    release_id = store.create_release('unsupported', 'default', 2, [], archive)
    result = run_sync(store, enqueue_sync(store, release_id, 'default'))
    assert result['uploaded'] == 0 and len(result['errors']) == 1 and not client.documents


def test_review_off_sends_original_html_to_official_parser(environment, tmp_path, monkeypatch):
    store, client, _ = environment
    client.update_knowledge_base(get_space(store, 'default')['knowledge_base_id'], review_enabled=False)
    html = '<h1>原始 HTML</h1><p>交给官方解析。</p>'
    archive = make_release_zip(tmp_path / 'raw.zip', [{'id': 'raw', 'content': html, 'source_format': 'html'}])
    release_id = store.create_release('raw', 'default', 2, [], archive)
    monkeypatch.setattr('common.converter.RAGContentPipeline.convert_record', lambda *a, **kw: pytest.fail('review-off must not convert'))
    result = run_sync(store, enqueue_sync(store, release_id, 'default'))
    assert result['errors'] == []
    doc = next(iter(client.documents.values()))
    assert doc['name'] == 'doc-raw.html' and doc['text'] == html
    assert doc['metadata']['source_conversion_fingerprint'] == ''


def test_previously_exported_markdown_is_reused_with_original_source_hash(environment, tmp_path, monkeypatch):
    store, client, _ = environment
    original = '<h1>历史原件</h1><pre><code>line = "____________"</code></pre>'
    markdown = '# 历史原件\n\n```python\nline = "____________"\n```'
    record = {'id': 'exported', 'source_format': 'html', 'content_format': 'markdown',
        'source_content': original, 'content': markdown, 'metadata': {'conversion': {'fingerprint': 'saved-conversion'}}}
    archive = make_release_zip(tmp_path / 'exported.zip', [record])
    release_id = store.create_release('exported', 'default', 2, [], archive)
    monkeypatch.setattr('common.converter.RAGContentPipeline.convert_record', lambda *a, **kw: pytest.fail('existing Markdown must not be parsed again'))
    result = run_sync(store, enqueue_sync(store, release_id, 'default'))
    assert result['errors'] == [] and result['uploaded'] == 1
    doc = next(iter(client.documents.values()))
    assert doc['name'] == 'doc-exported.md' and doc['text'] == markdown
    assert doc['metadata']['source_content_hash'] == hashlib.sha256(original.encode()).hexdigest()
    assert doc['metadata']['source_conversion_fingerprint'] == 'saved-conversion'


def test_lost_upload_response_recovers_without_overwriting_adopted_content(environment, monkeypatch):
    from integrations.contextdb import ContextDBError
    store, client, release_id = environment
    upload = client.upload_file
    def lost_response(kb_id, name, path, **kwargs):
        result = upload(kb_id, name, path, **kwargs)
        if name == 'doc-doc-1.md':
            client.documents[result['id']]['text'] = '已采纳的官方正文'
            raise ContextDBError('response lost after server accepted upload')
        return result
    monkeypatch.setattr(client, 'upload_file', lost_response)
    first = run_sync(store, enqueue_sync(store, release_id, 'default'))
    assert len(first['errors']) == 1 and len(client.documents) == 2
    monkeypatch.setattr(client, 'upload_file', lambda *a, **kw: pytest.fail('retry must reconcile the receipt'))
    monkeypatch.setattr(client, 'update_file', lambda *a, **kw: pytest.fail('retry must not overwrite adopted content'))
    repeated = run_sync(store, enqueue_sync(store, release_id, 'default'))
    assert repeated['errors'] == [] and repeated['skipped'] == 2
    assert next(doc for doc in client.documents.values() if doc['name'] == 'doc-doc-1.md')['text'] == '已采纳的官方正文'


def test_changing_review_policy_does_not_replace_an_adopted_html_capture(environment, tmp_path, monkeypatch):
    store, client, _ = environment
    archive = make_release_zip(tmp_path / 'html-policy.zip', [{'id': 'html', 'version_id': 'v1',
        'source_format': 'html', 'content': '<p>原始资料</p>'}])
    release_id = store.create_release('html-policy', 'default', 2, ['v1'], archive)
    run_sync(store, enqueue_sync(store, release_id, 'default'))
    doc = next(iter(client.documents.values()))
    doc['text'] = '已采纳的人工完整稿'
    fingerprint = doc['metadata']['source_conversion_fingerprint']
    client.update_knowledge_base(doc['knowledge_base_id'], review_enabled=False)
    monkeypatch.setattr('common.converter.prepare_review_file', lambda *a, **kw: pytest.fail('same capture must skip policy reprocessing'))
    monkeypatch.setattr(client, 'update_file', lambda *a, **kw: pytest.fail('review policy must not replace adopted text'))
    repeated = run_sync(store, enqueue_sync(store, release_id, 'default'))
    assert repeated['errors'] == [] and repeated['skipped'] == 1
    assert doc['text'] == '已采纳的人工完整稿'
    assert doc['metadata']['source_conversion_fingerprint'] == fingerprint
