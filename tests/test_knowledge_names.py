"""Display-only compatibility for cloud identities and older local captures."""
import os
from copy import deepcopy
from unittest.mock import Mock

import pytest

from governance.database import connection
from governance.knowledge_names import KnowledgeNames, captured_filename, document_name, download_name
from governance.store import Store
from tests.contextdb_fake import FakeContextDBClient


@pytest.mark.parametrize('document,expected', [
    ({'name': 'doc-id.docx', 'metadata': {'filename': ' 原始手册.docx ', 'title': '手册'}}, '原始手册.docx'),
    ({'name': 'doc-id.HTML', 'metadata': {'title': ' 采购明细 '}}, '采购明细.HTML'),
    ({'name': 'doc-id.PDF', 'metadata': {'title': '手册.pdf'}}, '手册.pdf'),
    ({'name': '历史原件.md', 'metadata': {'title': 123}}, '历史原件.md'),
    ({'document_name': '手动重命名.md'}, '手动重命名.md'),
    ({'docnm_kwd': 'doc-id.html', 'doc_metadata': {'title': '云端标题'}}, '云端标题.html'),
])
def test_document_label_fallbacks(document, expected):
    original = deepcopy(document)
    assert document_name(document) == expected
    assert document == original


@pytest.mark.parametrize('document,expected', [
    ({'name': 'doc-hash.md', 'metadata': {'filename': '业务手册.html'}}, '业务手册.md'),
    ({'name': 'doc-hash.md', 'display_name': '历史采购明细.html'}, '历史采购明细.md'),
    ({'name': 'doc-hash.md', 'document_display_name': '操作手册', 'metadata': {'filename': '原件.html'}}, '操作手册.md'),
    ({'name': 'doc-hash.docx', 'metadata': {'filename': '原始手册.docx'}}, '原始手册.docx'),
    ({'name': 'doc-hash.pdf', 'metadata': {'filename': '手册.PDF'}}, '手册.PDF'),
    ({'name': 'source', 'display_name': '无扩展名原件'}, '无扩展名原件'),
    ({'name': 'doc-hash.md', 'metadata': {'filename': '长' * 200 + '.html'}}, '长' * 157 + '.md'),
])
def test_download_name_uses_actual_source_extension_without_changing_display_or_identity(document, expected):
    original = deepcopy(document)
    assert download_name(document) == expected
    assert document == original


@pytest.mark.parametrize('record,expected', [
    ({'title': '单位进货排行榜', 'source_format': 'markdown'}, '单位进货排行榜.md'),
    ({'title': '手册.html', 'source_format': 'html'}, '手册.html'),
    ({'title': '业务标题', 'metadata': {'filename': '原件.PDF'}, 'archive_source': 'originals/hash.pdf'}, '原件.PDF'),
    ({'title': '配置说明', 'source_format': 'html', 'content_format': 'markdown'}, '配置说明.html'),
    ({'title': '', 'source_format': 'markdown'}, ''),
])
def test_captured_filename_preserves_business_name_and_original_format(record, expected):
    assert captured_filename(record) == expected


@pytest.fixture()
def names_data(authenticated_client):
    owner = os.environ['TEST_PLATFORM_USER']
    store = Store(client=FakeContextDBClient(), owner_id=owner)
    store._create('knowledge_space', 'default', {'scope': 'default', 'name': '默认知识空间',
        'wiki_kb_id': 'wiki-id', 'graph_kb_id': 'graph-id', 'graph_enabled': True}, {'scope': 'default'})
    store._create('doc', 'source-id', {'doc_id': 'source-id'},
                  {'doc_id': 'source-id', 'scope': 'default', 'title': '历史采购明细'})
    with connection() as conn:
        conn.execute("INSERT INTO knowledge_sync(owner_id,scope,source_id,target_mode,knowledge_base_id,document_id,status) VALUES (%s,'default','source-id','wiki','wiki-id','cloud-doc','succeeded')", (owner,))
    return owner, authenticated_client


def test_space_aliases_keep_cloud_identity_and_are_owner_scoped(names_data):
    owner, _ = names_data
    raw = {'id': 'graph-id', 'name': 'knowledge-default-graph', 'graph_enabled': True}
    result = KnowledgeNames(owner).base(raw)
    assert result == {**raw, 'display_name': raw['name'], 'space_name': raw['name'],
                      'space_scope': 'default', 'space_mode': 'graph'}
    assert 'display_name' not in raw
    hidden = KnowledgeNames('another-owner').base({'id': 'graph-id', 'name': 'unbound-graph'})
    assert hidden['display_name'] == 'unbound-graph' and 'space_scope' not in hidden


def test_current_binding_wins_over_history_and_ambiguous_history_is_not_editable(names_data):
    owner, _ = names_data
    store = Store(client=FakeContextDBClient(), owner_id=owner)
    for scope in ('old-one', 'old-two'):
        store._create('knowledge_space', scope, {'scope': scope, 'name': scope, 'wiki_kb_id': scope,
            'previous_knowledge_base_ids': {'wiki': ['wiki-id', 'ambiguous']}}, {'scope': scope})
    names = KnowledgeNames(owner)
    current = names.base({'id': 'wiki-id', 'name': 'internal'})
    assert current['space_scope'] == 'default' and current['display_name'] == 'internal'
    assert names.base({'id': 'ambiguous', 'name': 'old-internal'}) == {
        'id': 'ambiguous', 'name': 'old-internal', 'display_name': 'old-internal'}


def test_legacy_title_restored_without_writes_or_cross_owner_leak(names_data):
    owner, _ = names_data
    raw = {'document_id': 'cloud-doc', 'knowledge_base_id': 'wiki-id', 'document_name': 'doc-source.html'}
    with connection() as conn:
        before = conn.execute('SELECT id,payload,metadata,updated_at FROM runtime_records ORDER BY id').fetchall()
    assert KnowledgeNames(owner).document(raw, reference=True)['document_display_name'] == '历史采购明细.html'
    assert KnowledgeNames('another-owner').document(raw, reference=True)['document_display_name'] == 'doc-source.html'
    assert KnowledgeNames(owner).document({**raw, 'knowledge_base_id': 'other-base'}, reference=True)['document_display_name'] == 'doc-source.html'
    assert KnowledgeNames(owner).document({**raw, 'metadata': {'filename': '云端原文件.docx'}}, reference=True)['document_display_name'] == '云端原文件.docx'
    assert KnowledgeNames(owner).document({**raw, 'metadata': {'title': ' ', 'filename': None}}, reference=True)['document_display_name'] == '历史采购明细.html'
    assert 'document_display_name' not in raw
    with connection() as conn:
        assert conn.execute('SELECT id,payload,metadata,updated_at FROM runtime_records ORDER BY id').fetchall() == before


def test_native_and_business_read_apis_add_labels_without_renaming(names_data, monkeypatch):
    owner, http = names_data
    raw = {'id': 'cloud-doc', 'name': 'doc-source.html', 'knowledge_base_id': 'wiki-id',
           'metadata': {'title': '采购明细'}}
    fake = FakeContextDBClient()
    fake.knowledge_bases['wiki-id'] = {'id': 'wiki-id', 'name': 'knowledge-default', 'wiki_enabled': True,
                                       'graph_enabled': False}
    fake.documents['cloud-doc'] = raw
    fake._request = Mock(return_value={'documents': [raw], 'total': 1})
    monkeypatch.setattr('webapi.contextdb.client_for_user', lambda: fake)
    monkeypatch.setattr('app.get_store', lambda: Store(client=fake, owner_id=owner))
    response = http.get('/api/contextdb/v1/knowledge/documents?knowledge_base_id=wiki-id')
    document = response.json['data']['documents'][0]
    assert document['name'] == raw['name'] and document['display_name'] == '采购明细.html'
    assert 'display_name' not in raw
    fake._request.return_value = {'reviews': [{'document_id': 'cloud-doc', 'document_name': raw['name']}]}
    response = http.get('/api/contextdb/v1/knowledge/reviews?knowledge_base_id=wiki-id')
    review = response.json['data']['reviews'][0]
    assert review['document_name'] == raw['name'] and review['document_display_name'] == '历史采购明细.html'
    fake._request.return_value = {'knowledge_bases': [{'id': 'wiki-id', 'name': 'knowledge-default'}]}
    base = http.get('/api/contextdb/v1/knowledge/knowledge_bases').json['data']['knowledge_bases'][0]
    assert base['name'] == 'knowledge-default' and base['display_name'] == 'knowledge-default'
    fake._request.return_value = raw
    response = http.put('/api/contextdb/v1/knowledge/documents', json={'document_id': 'cloud-doc', 'text': 'new'})
    assert response.json['data'] == raw


def test_query_and_directory_keep_original_fields_and_graph_context(names_data):
    owner, _ = names_data
    names = KnowledgeNames(owner)
    chunk = {'doc_id': 'cloud-doc', 'doc_name': 'doc-source.html', 'kb_id': 'wiki-id', 'content': '证据'}
    graph = {'type': 'graph_context', 'doc_name': 'graph', 'citation_eligible': False, 'content': '关系'}
    result = names.present('knowledge/query', {'chunks': [chunk, graph]})
    assert result['chunks'][0] == {**chunk, 'document_display_name': '历史采购明细.html'}
    assert result['chunks'][1] == graph
    native = {'doc_id': 'external-doc', 'kb_id': 'wiki-id', 'docnm_kwd': 'doc-native.html',
              'doc_metadata': {'title': '直接上传标题'}, 'content_with_weight': '证据'}
    assert names.present('knowledge/query', {'chunks': [native]})['chunks'][0] == {
        **native, 'document_display_name': '直接上传标题.html'}
    node = {'node_type': 'file', 'document_id': 'cloud-doc', 'display_name': '用户目录名称.html'}
    result = names.present('knowledge/nodes', {'items': [node]}, kb_id='wiki-id')['items'][0]
    assert result['display_name'] == node['display_name']
    assert result['document_display_name'] == '历史采购明细.html'


def test_historical_upload_prefix_restored_only_from_its_exact_job_and_natural_numbering_kept(names_data):
    from governance.store import data_dir
    owner, _ = names_data
    store = Store(client=FakeContextDBClient(), owner_id=owner)
    path = data_dir() / 'uploads' / '7d3e8fc4-a205-45d4-b557-0f010326b030' / '001-001-用户手册.md'
    store._create('job', 'upload-job', {'entry': 'file', 'params': {'file_paths': [str(path)]}}, {})
    store._create('version', 'upload-version', {}, {'job_id': 'upload-job', 'title': path.stem})
    record = store._find('doc', doc_id='source-id')
    store._update_metadata({**record['metadata'], 'title': path.stem, 'current_version': 'upload-version'}, document_id=record['id'])
    with connection() as conn:
        conn.execute("UPDATE knowledge_sync SET source_version='upload-version' WHERE owner_id=%s", (owner,))
    raw = {'id': 'cloud-doc', 'knowledge_base_id': 'wiki-id', 'name': 'doc-source.md',
           'metadata': {'filename': path.name, 'title': path.stem}}
    names = KnowledgeNames(owner)
    assert names.document(raw)['display_name'] == '001-用户手册.md'
    assert names.document({**raw, 'metadata': {'filename': '自行重命名.md'}})['display_name'] == '自行重命名.md'
    assert raw['metadata']['filename'] == path.name
    history = {'source_id': 'source-id', 'knowledge_base_id': 'retained-old-kb', 'document_id': 'old-doc',
               'source_version': 'upload-version'}
    store._create('knowledge_sync_history', 'old-receipt', history, {'scope': 'default'})
    old = {'id': 'old-doc', 'knowledge_base_id': 'retained-old-kb', 'name': 'doc-source.md'}
    assert KnowledgeNames(owner).document(old)['display_name'] == '001-用户手册.md'


def test_compile_rows_without_a_cloud_name_keep_the_captured_source_extension(names_data):
    owner, _ = names_data
    store = Store(client=FakeContextDBClient(), owner_id=owner)
    store._create('version', 'html-version', {}, {'title': '历史采购明细', 'source_format': 'html'})
    with connection() as conn:
        conn.execute("UPDATE knowledge_sync SET source_version='html-version' WHERE owner_id=%s", (owner,))
    raw = {'document_id': 'cloud-doc', 'run_state': 'compiled'}
    row = KnowledgeNames(owner).present('knowledge/wiki/compile-runs', {'items': [raw]}, kb_id='wiki-id')['items'][0]
    assert row == {**raw, 'document_display_name': '历史采购明细.html'}


def test_tiantong_attachment_legacy_prefix_uses_capture_provenance_without_rewriting_it(names_data):
    owner, _ = names_data
    store = Store(client=FakeContextDBClient(), owner_id=owner)
    original = '001-清理脚本.sql'
    physical = 'dec0e211-77d6-405c-bd4a-b806a181e37b_' + original
    capture = {'title': original, 'source_path': 'assets/attachments/' + physical,
               'metadata': {'parent_document_id': 'parent', 'filename': physical}}
    store._create('job', 'tiantong-job', {'entry': 'tiantong', 'params': {}}, {})
    version = store._create('version', 'attachment-version', capture,
                            {'title': original, 'source_format': 'file', 'job_id': 'tiantong-job'})
    with connection() as conn:
        conn.execute("UPDATE knowledge_sync SET source_version='attachment-version' WHERE owner_id=%s", (owner,))
    raw = {'id': 'cloud-doc', 'knowledge_base_id': 'wiki-id', 'name': 'doc-id.sql',
           'metadata': {'filename': physical, 'title': original}}
    assert KnowledgeNames(owner).document(raw)['display_name'] == original
    assert KnowledgeNames(owner).document({**raw, 'metadata': {'filename': '手动改名.sql'}})['display_name'] == '手动改名.sql'
    assert store._body(version['id']) == capture
    assert raw['metadata']['filename'] == physical


@pytest.mark.parametrize('change', [
    {'source_path': 'other/attachments/dec0e211-77d6-405c-bd4a-b806a181e37b_脚本.sql'},
    {'title': '其他标题.sql'},
    {'metadata': {'filename': 'dec0e211-77d6-405c-bd4a-b806a181e37b_脚本.sql'}},
])
def test_attachment_prefix_is_not_guessed_without_exact_provenance(change):
    from governance.knowledge_names import _captured_attachment_name
    capture = {'title': '脚本.sql', 'source_path': 'assets/attachments/dec0e211-77d6-405c-bd4a-b806a181e37b_脚本.sql',
               'metadata': {'parent_document_id': 'parent', 'filename': 'dec0e211-77d6-405c-bd4a-b806a181e37b_脚本.sql'}}
    assert _captured_attachment_name({**capture, **change}) is None


def test_generated_wiki_and_toc_labels_use_exact_scoped_source_names_without_changing_evidence():
    source = 'a' * 64
    technical = 'doc-' + source + '.html'
    names = KnowledgeNames('owner')
    names._documents = {('wiki-id', 'cloud-doc'): {'doc_id': source, 'title': '采购单'}}
    summary = {'title': technical + ' - Summary', 'knowledge_base_id': 'wiki-id',
               'source_document_ids': ['cloud-doc'], 'content': technical + ' 保留证据原文',
               'heading_path': technical + ' - Summary/新增采购'}
    chunk = {'doc_id': 'cloud-doc', 'kb_id': 'wiki-id', 'docnm_kwd': technical,
             'toc_path': technical + '/新增采购', 'content': technical + ' 原始切片'}
    native = {'wiki_items': [summary], 'chunks': [chunk]}
    original = deepcopy(native)
    view = names.present('knowledge/query', native)
    assert view['wiki_items'][0]['display_title'] == '采购单.html - Summary'
    assert view['wiki_items'][0]['display_heading_path'] == '采购单.html - Summary/新增采购'
    assert view['chunks'][0]['display_toc_path'] == '采购单.html/新增采购'
    assert view['wiki_items'][0]['content'] == summary['content']
    assert view['chunks'][0]['content'] == chunk['content']
    assert native == original
    assert names.wiki_page({**summary, 'source_document_ids': ['other-doc']})['display_title'] == summary['title']
    assert names.wiki_page({**summary, 'knowledge_base_id': 'other-kb'})['display_title'] == summary['title']
    assert names.wiki_page({**summary, 'title': '采购单业务说明'})['display_title'] == '采购单业务说明'
    assert names.wiki_page({**summary, 'title': technical + ' - 自定义标题'})['display_title'] == technical + ' - 自定义标题'
    page = names.present('knowledge/wiki/pages/detail', {'title': '采购单', 'ancestors': [summary]}, kb_id='wiki-id')
    assert page['title'] == '采购单' and page['ancestors'][0]['display_title'] == '采购单.html - Summary'
    index = names.present('knowledge/wiki/index', {'groups': [{'type': 'summary', 'items': [summary]}]}, kb_id='wiki-id')
    assert index['groups'][0]['items'][0]['display_title'] == '采购单.html - Summary'


def _native_chat():
    import json
    from types import SimpleNamespace
    native = {'results': [{'knowledge_base_id': 'wiki-id', 'document_id': 'cloud-doc',
        'document_name': 'doc-source.html', 'chunk_id': 'cloud-doc:1', 'content': '原始证据'}]}
    human = {'type': 'human', 'id': 'human-1', 'content': '采购说明',
             'additional_kwargs': {'harness': {'knowledge_base_ids': ['wiki-id']}}}
    assistant = {'type': 'ai', 'id': 'answer-1', 'content': '', 'tool_calls': [
        {'name': 'knowledge.search', 'id': 'search-1', 'args': {'knowledge_base_ids': ['wiki-id']}}]}
    message = {'type': 'tool', 'id': 'native-1', 'tool_call_id': 'search-1', 'name': 'knowledge.search',
               'content': json.dumps(native), 'artifact': {'structured_content': native}}
    return SimpleNamespace(values={'messages': [human, assistant, message]}, next=(), interrupts=()), assistant, message


def test_chat_stream_and_history_add_readable_names_without_mutating_native_messages(names_data):
    from webapi.weknora_adapter import StreamProjection, history
    owner, _ = names_data
    state, assistant, message = _native_chat()
    original = deepcopy(state.values)
    projection = StreamProjection('chat-1', 'answer-1', ['wiki-id'], owner_id=owner)
    projection.feed({'ns': (), 'type': 'updates', 'data': {'model': {'messages': [assistant]}}})
    events = projection.feed({'ns': (), 'type': 'updates', 'data': {'tools': {'messages': [message]}}})
    result = next(event['data'] for event in events if event['response_type'] == 'tool_result')
    saved = history(state, 'chat-1', owner_id=owner)[-1]
    assert result['output'] == message['content']
    assert result['data']['results'][0]['document_name'] == 'doc-source.html'
    assert result['data']['results'][0]['document_display_name'] == '历史采购明细.html'
    assert saved['agent_steps'][0]['tool_calls'][0]['result']['data']['results'] == result['data']['results']
    references = next(event['data']['references'] for event in events if event['response_type'] == 'references')
    assert references == saved['knowledge_references']
    assert references[0]['id'] == 'cloud-doc:1' and references[0]['knowledge_id'] == 'cloud-doc'
    assert references[0]['knowledge_title'] == '历史采购明细.html'
    assert references[0]['document_display_name'] == '历史采购明细.html'
    assert state.values == original


def test_projection_without_request_owner_keeps_native_fallback_and_never_reads_database(monkeypatch):
    from webapi.weknora_adapter import StreamProjection, history
    monkeypatch.setattr('governance.knowledge_names.connection', lambda: pytest.fail('ownerless projection must not read a database'))
    state, assistant, message = _native_chat()
    projection = StreamProjection('chat-1', 'answer-1', ['wiki-id'])
    projection.feed({'ns': (), 'type': 'updates', 'data': {'model': {'messages': [assistant]}}})
    events = projection.feed({'ns': (), 'type': 'updates', 'data': {'tools': {'messages': [message]}}})
    result = next(event['data'] for event in events if event['response_type'] == 'tool_result')
    assert result['data'] == message['artifact']['structured_content']
    assert 'document_display_name' not in history(state, 'chat-1')[-1]['knowledge_references'][0]


def test_chat_citation_uses_cloud_metadata_when_no_local_capture_exists(names_data):
    from webapi.weknora_adapter import history
    owner, _ = names_data
    state, _, message = _native_chat()
    chunk = message['artifact']['structured_content']['results'][0]
    chunk.update(document_id='cloud-only', metadata={'title': '云端采购规范'})
    reference = history(state, 'chat-1', owner_id=owner)[-1]['knowledge_references'][0]
    assert reference['document_display_name'] == '云端采购规范.html'
    assert reference['knowledge_title'] == '云端采购规范.html'
    assert reference['knowledge_id'] == 'cloud-only'


def test_document_picker_searches_readable_and_native_names_without_renaming(names_data, monkeypatch):
    _, http = names_data
    raw = {'id': 'cloud-doc', 'name': 'doc-source.html', 'ingest_status': 'succeeded'}
    fake = Mock()
    fake.list_knowledge_bases.return_value = {'knowledge_bases': [{'id': 'wiki-id', 'name': 'knowledge-default'}]}
    fake.list_documents.return_value = {'documents': [raw]}
    monkeypatch.setattr('webapi.chat_resources.client_for_user', lambda: fake)
    for keyword in ('历史采购', 'doc-source'):
        response = http.get('/api/v1/knowledge/search', query_string={'keyword': keyword})
        assert response.status_code == 200
        item = response.json['data'][0]
        assert item['name'] == raw['name'] and item['id'] == raw['id']
        assert item['title'] == item['file_name'] == '历史采购明细.html'
        assert item['knowledge_base_name'] == 'knowledge-default'
    assert 'display_name' not in raw
