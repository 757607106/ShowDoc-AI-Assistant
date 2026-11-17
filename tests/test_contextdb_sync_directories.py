"""Crawler file-tree placement and non-destructive repair against real platform state."""
from copy import deepcopy
from unittest.mock import Mock

import pytest

from governance.database import connection
from governance.contextdb_sync import enqueue_sync, run_sync
from governance.import_directories import ImportDirectories, imported_locations, repair_documents, repair_plan
from governance.spaces import persist_space
from governance.store import Store, StoreError
from integrations.contextdb import ContextDBConflictError, ContextDBError
from tests.contextdb_fake import FakeContextDBClient
from tests.test_contextdb_sync import make_release_zip


@pytest.fixture()
def environment():
    client = FakeContextDBClient()
    store = Store(client=client)
    base = client.create_knowledge_base('通用事业部', wiki_enabled=True, review_enabled=True)
    return store, client, base['id']


def capture(key='showdoc:399', path=(), name='云辉煌知识库'):
    return {'source_key': key, 'metadata': {'import_directory': {'root_name': name, 'path': list(path)}}}


def plan_item(document_id, key='showdoc:399', path=(), name='云辉煌知识库'):
    return {'document_id': document_id, 'source_key': key, 'directory': capture(key, path, name)['metadata']['import_directory']}


def test_same_name_source_roots_are_distinct_and_repeated_captures_reuse_nodes(environment):
    store, client, kb = environment
    first = ImportDirectories(store, kb)
    a, root_a = first.target(capture())
    b, root_b = first.target(capture('showdoc:412'))
    assert a != b
    assert root_a[1]['display_name'] == root_b[1]['display_name'] == '云辉煌知识库'
    assert len(client.list_nodes(kb)['items']) == 2
    second = ImportDirectories(store, kb)
    assert second.target(capture())[0] == a
    assert second.target(capture('showdoc:412'))[0] == b
    assert len(client.list_nodes(kb)['items']) == 2


def test_root_pages_and_multilevel_paths_have_real_nodes_and_locations_only_after_placement(environment):
    store, client, kb = environment
    manager = ImportDirectories(store, kb)
    parent, root = manager.target(capture())
    assert parent == root[1]['node_id']
    assert imported_locations(store, kb) == []
    nested, same_root = manager.target(capture(path=['进货管理', '报表', '进货统计']))
    assert same_root[1]['node_id'] == parent
    breadcrumbs = client.list_nodes(kb, parent_node_id=nested)['breadcrumbs']
    assert [node['display_name'] for node in breadcrumbs] == ['通用事业部', '云辉煌知识库', '进货管理', '报表', '进货统计']
    assert manager.target(capture(path=['进货管理', '报表', '进货统计']))[0] == nested
    assert ImportDirectories(store, kb).target(capture(path=['进货管理', '报表', '进货统计']))[0] == nested
    assert len([node for node in client.nodes.values() if node['node_type'] == 'folder']) == 4
    doc = client.create_text_document(kb, '根页.md', '根页')
    assert manager.attach(doc['id'], parent)
    manager.populated(root)
    assert imported_locations(store, kb, 'showdoc:399') == [
        {'knowledge_base_id': kb, 'node_id': parent, 'root_name': '云辉煌知识库'}]


def test_new_root_label_renames_mapped_directory_without_changing_identity(environment):
    store, client, kb = environment
    parent, root = ImportDirectories(store, kb).target(capture())
    doc = client.create_text_document(kb, '手册.md', '正文', parent_node_id=parent)
    before = client.get_document(kb, doc['id'])
    ImportDirectories(store, kb).populated(root)
    explicit = ImportDirectories(store, kb, root_names={'showdoc:399': '云辉煌产品手册'})
    renamed, _ = explicit.target(capture())
    assert renamed == parent
    assert client.list_nodes(kb, parent_node_id=parent)['parent_node']['display_name'] == '云辉煌产品手册'
    assert len(client.list_nodes(kb)['items']) == 1
    assert client.get_document(kb, doc['id']) == before
    assert imported_locations(store, kb)[0]['root_name'] == '云辉煌产品手册'
    historical, _ = ImportDirectories(store, kb).target(capture())
    assert historical == parent
    assert client.list_nodes(kb, parent_node_id=parent)['parent_node']['display_name'] == '云辉煌产品手册'
    assert imported_locations(store, kb)[0]['root_name'] == '云辉煌产品手册'
    assert client.get_document(kb, doc['id']) == before


def test_existing_child_directories_are_read_across_pages_before_creation(environment, monkeypatch):
    store, client, kb = environment
    parent, _ = ImportDirectories(store, kb).target(capture())
    children = [client.create_directory(kb, f'目录{index}', parent_node_id=parent)['node'] for index in range(101)]
    listing = Mock(wraps=client.list_nodes)
    monkeypatch.setattr(client, 'list_nodes', listing)
    selected, _ = ImportDirectories(store, kb).target(capture(path=['目录100']))
    assert selected == children[-1]['node_id']
    assert any(call.kwargs.get('page') == 2 for call in listing.call_args_list)
    assert len(client.nodes) == 103


@pytest.mark.parametrize(('key', 'category', 'root', 'expected'), [
    ('file', '上传文件', '上传文件', []),
    ('tiantong', '未分类', '天通资源管理中心', []),
    ('tiantong', '产品/配置', '天通资源管理中心', ['产品', '配置']),
    ('cyb', '使用教程/库存', '管家婆云辉煌创业版', ['使用教程', '库存']),
    ('web:example.com', '网页', 'example.com', []),
])
def test_legacy_sources_use_the_same_root_and_relative_path_rules(environment, key, category, root, expected):
    store, _, kb = environment
    source, directory = ImportDirectories(store, kb).source({'source_key': key, 'category': category})
    assert source == key
    assert directory == {'root_name': root, 'path': expected}


def test_legacy_showdoc_recovers_project_name_from_original_job_and_keeps_root_page_direct(environment, monkeypatch):
    store, _, kb = environment
    job = store.create_job('showdoc', {'item_id': '399'})
    crawler = Mock(project_name='云辉煌知识库')
    create = Mock(return_value=crawler)
    monkeypatch.setattr('registry.create_crawler', create)
    source, directory = ImportDirectories(store, kb).source({
        'source_key': 'showdoc:399', 'job_id': job['task_id'], 'category': '根目录', 'metadata': {'cat_id': 0}})
    assert source == 'showdoc:399' and directory == {'root_name': '云辉煌知识库', 'path': []}
    create.assert_called_once()
    assert create.call_args.kwargs['item_id'] == '399'
    crawler.authenticate.assert_called_once()
    crawler.fetch_item_info.assert_called_once()


@pytest.mark.parametrize(('cat_id', 'path'), [(0, []), ('0', []), (12, ['根目录']), ('12', ['根目录'])])
def test_legacy_showdoc_uses_catalog_id_to_distinguish_root_page_from_real_root_named_folder(environment, cat_id, path):
    store, _, kb = environment
    ImportDirectories(store, kb).target(capture())
    _, directory = ImportDirectories(store, kb).source({
        'source_key': 'showdoc:399', 'category': '根目录', 'metadata': {'cat_id': cat_id}})
    assert directory == {'root_name': '云辉煌知识库', 'path': path}


def test_legacy_showdoc_missing_catalog_id_does_not_guess_root_named_folder(environment):
    store, _, kb = environment
    ImportDirectories(store, kb).target(capture())
    with pytest.raises(StoreError, match='缺少目录标识'):
        ImportDirectories(store, kb).source({'source_key': 'showdoc:399', 'category': '根目录'})


def test_legacy_source_reuses_mapped_root_without_requesting_expired_origin_credentials(environment, monkeypatch):
    store, client, kb = environment
    parent, _ = ImportDirectories(store, kb).target(capture(name='已确认的项目目录'))
    forbidden = Mock(side_effect=AssertionError('已知来源目录不应重新登录'))
    monkeypatch.setattr('registry.create_crawler', forbidden)
    selected, root = ImportDirectories(store, kb).target({
        'source_key': 'showdoc:399', 'job_id': 'expired-job', 'category': '进货管理/报表', 'metadata': {'cat_id': 9}})
    assert root[1]['node_id'] == parent and root[1]['display_name'] == '已确认的项目目录'
    assert [node['display_name'] for node in client.list_nodes(kb, parent_node_id=selected)['breadcrumbs']] == [
        '通用事业部', '已确认的项目目录', '进货管理', '报表']
    forbidden.assert_not_called()


def test_legacy_file_revisions_recursively_keep_original_showdoc_job_and_directory(environment, monkeypatch):
    store, _, kb = environment
    original = store.create_job('showdoc', {'item_id': '399', 'user_token': 'original-token'})
    page = {'id': 'page-1', 'title': '部门业务统计', 'category': '钱流管理/报表',
            'content': '原始正文', 'metadata': {'cat_id': 9}}
    store.ingest(original, [page], {'page-1': {'source_format': 'markdown'}}, [])
    previous = store.list_documents(original['task_id'])[0]
    for index in range(2):
        revision = store.create_job('file', {'file_paths': [f'修订{index}.md']},
            version_id=previous['version_id'], document_id=previous['id'])
        store.ingest(revision, [{**page, 'metadata': {}, 'content': f'修订正文{index}'}],
                     {'page-1': {'source_format': 'markdown', 'source_sha256': str(index)}}, [])
        previous = store.list_documents(revision['task_id'])[0]
    crawler = Mock(project_name='云辉煌知识库')
    create = Mock(return_value=crawler)
    monkeypatch.setattr('registry.create_crawler', create)
    key, directory = ImportDirectories(store, kb).source(store.get_document(previous['version_id']))
    assert key == 'showdoc:399'
    assert directory == {'root_name': '云辉煌知识库', 'path': ['钱流管理', '报表']}
    assert create.call_args.args[0] == 'showdoc'
    assert create.call_args.kwargs['item_id'] == '399'
    assert create.call_args.kwargs['user_token'] == 'original-token'
    assert 'file_paths' not in create.call_args.kwargs
    create.assert_called_once()


def test_repair_preserves_document_identity_metadata_review_events_and_wiki(environment, monkeypatch):
    store, client, kb = environment
    doc = client.create_text_document(kb, '手册.md', '人工已采纳的正文', file_path='space-internal',
        metadata={'approved': True, 'platform_source_id': 'capture-1'})
    client.documents[doc['id']].update(ingest_status='pending_review', latest_ingest_event_id='ingest-original')
    client.reviews['review-original'] = {'document_id': doc['id'], 'status': 'pending_review'}
    client.events['ingest-original'] = {'document_id': doc['id'], 'status': 'PENDING'}
    client.wiki_pages['page-original'] = {'id': 'page-original', 'parent_page_id': 'wiki-directory', 'title': '主题'}
    before = deepcopy((client.documents, client.reviews, client.events, client.wiki_pages))
    forbidden = Mock(side_effect=AssertionError('目录整理不能改写正文或评审'))
    for method in ('upload_file', 'update_file', 'update_document_metadata', 'delete_documents'):
        monkeypatch.setattr(client, method, forbidden)
    progress = []
    plan = [plan_item(doc['id'], path=['进货管理', '报表'])]
    first = repair_documents(store, kb, plan, progress=progress.append)
    assert first[0]['moved'] is True and progress == first
    assert (client.documents, client.reviews, client.events, client.wiki_pages) == before
    count = len(client.nodes)
    second = repair_documents(store, kb, plan)
    assert second[0]['moved'] is False and len(client.nodes) == count
    assert first[0]['parent_node_id'] == second[0]['parent_node_id']
    assert (client.documents, client.reviews, client.events, client.wiki_pages) == before
    forbidden.assert_not_called()


def test_partial_repair_keeps_successful_moves_and_does_not_delete_failed_documents(environment, monkeypatch):
    store, client, kb = environment
    docs = [client.create_text_document(kb, f'{index}.md', f'正文{index}') for index in range(2)]
    fail_node = docs[1]['node_id']
    move = client.move_node
    def fail_one(knowledge_base_id, node_id, parent_node_id, expected_tree_version):
        if node_id == fail_node:
            raise ContextDBError('temporary failure')
        return move(knowledge_base_id, node_id, parent_node_id, expected_tree_version)
    monkeypatch.setattr(client, 'move_node', fail_one)
    before = deepcopy(client.documents)
    result = repair_documents(store, kb, [plan_item(doc['id']) for doc in docs])
    assert result[0]['moved'] is True
    assert result[1]['error'] == 'temporary failure'
    assert client.documents == before
    assert client.ensure_document_node(docs[0]['id'])['node']['parent_node_id'] == result[0]['parent_node_id']
    assert client.ensure_document_node(docs[1]['id'])['node']['parent_node_id'] != result[0]['parent_node_id']


def test_concurrent_tree_conflict_is_reported_without_retrying_or_changing_document(environment, monkeypatch):
    store, client, kb = environment
    doc = client.create_text_document(kb, '手册.md', '正文')
    before = deepcopy(client.documents)
    move = Mock(side_effect=ContextDBConflictError('concurrent tree change', status_code=409))
    monkeypatch.setattr(client, 'move_node', move)
    result = repair_documents(store, kb, [plan_item(doc['id'])])
    assert result == [{'document_id': doc['id'], 'error': 'concurrent tree change'}]
    assert move.call_count == 1 and client.documents == before
    assert imported_locations(store, kb) == []


def test_lost_root_create_response_keeps_unresolved_mapping_instead_of_creating_another(environment, monkeypatch):
    store, client, kb = environment
    create = client.create_directory
    def lose_response(*args, **kwargs):
        create(*args, **kwargs)
        raise ContextDBError('create response lost')
    monkeypatch.setattr(client, 'create_directory', lose_response)
    with pytest.raises(ContextDBError, match='response lost'):
        ImportDirectories(store, kb).target(capture())
    monkeypatch.setattr(client, 'create_directory', Mock(side_effect=AssertionError('不能重复创建')))
    with pytest.raises(StoreError, match='未确认'):
        ImportDirectories(store, kb).target(capture())
    assert len(client.list_nodes(kb)['items']) == 1


def test_deleted_documents_are_skipped_and_still_report_progress(environment):
    store, client, kb = environment
    doc = client.create_text_document(kb, '已删除.md', '旧正文')
    client.documents[doc['id']]['ingest_status'] = 'deleted'
    progress = []
    result = repair_documents(store, kb, [plan_item(doc['id'])], progress=progress.append)
    assert result == [{'document_id': doc['id'], 'skipped': 'deleted'}] == progress
    assert imported_locations(store, kb) == []


def test_repair_plan_uses_only_synced_capture_mappings_and_reports_missing_versions(environment):
    store, client, kb = environment
    job = store.create_job('cyb')
    record = {'id': 'source-1', 'title': '使用教程', 'category': '使用教程/库存', 'content': '正文',
              'metadata': capture('cyb', ['使用教程', '库存'], '管家婆云辉煌创业版')['metadata']}
    store.ingest(job, [record], {'source-1': {'source_format': 'html'}}, [])
    version = store.list_documents(job['task_id'])[0]
    linked = client.create_text_document(kb, '已同步.md', '正文')
    client.create_text_document(kb, '手动上传.md', '不能自动整理')
    with connection() as conn:
        for source_id, version_id, doc_id in [
            (version['id'], version['version_id'], linked['id']), ('missing', 'missing-version', 'missing-document')]:
            conn.execute('''INSERT INTO knowledge_sync(owner_id,scope,source_id,target_mode,knowledge_base_id,
                document_id,source_version,status) VALUES ('','default',%s,'wiki',%s,%s,%s,'succeeded')''',
                (source_id, kb, doc_id, version_id))
    plan, errors = repair_plan(store, kb)
    assert len(plan) == 1 and plan[0]['document_id'] == linked['id']
    assert plan[0]['source_key'] == 'cyb'
    assert plan[0]['directory'] == {'root_name': '管家婆云辉煌创业版', 'path': ['使用教程', '库存']}
    assert len(errors) == 1 and errors[0]['document_id'] == 'missing-document'


def test_sync_attaches_uploads_to_source_directories_and_republish_reuses_tree(environment, tmp_path):
    store, client, kb = environment
    persist_space(store, {'scope': 'default', 'name': '通用事业部', 'knowledge_base_id': kb,
                          'mode': 'wiki', 'lifecycle': 'active'})
    records = [
        {**capture(path=[]), 'id': 'source-root', 'version_id': 'root-v1', 'title': '项目简介', 'content': '# 简介'},
        {**capture(path=['进货管理', '报表']), 'id': 'source-report', 'version_id': 'report-v1',
         'title': '进货统计', 'content': '# 统计'},
    ]
    archive = make_release_zip(tmp_path / 'directories.zip', records)
    release = store.create_release('capture-job', 'default', 1, ['root-v1', 'report-v1'], archive)
    first = run_sync(store, enqueue_sync(store, release, 'default'))
    assert first['errors'] == [] and first['uploaded'] == 2
    nodes = deepcopy(client.nodes)
    docs = deepcopy(client.documents)
    for doc in docs.values():
        node = client.ensure_document_node(doc['id'])['node']
        names = [ancestor['display_name'] for ancestor in client.list_nodes(kb, parent_node_id=node['parent_node_id'])['breadcrumbs']]
        assert names == (['通用事业部', '云辉煌知识库'] if doc['metadata']['platform_source_id'] == 'source-root'
                         else ['通用事业部', '云辉煌知识库', '进货管理', '报表'])
    assert len(imported_locations(store, kb)) == 1
    repeated = run_sync(store, enqueue_sync(store, release, 'default'))
    assert repeated['errors'] == [] and repeated['uploaded'] == 0 and repeated['skipped'] == 2
    assert client.nodes == nodes and client.documents == docs


def test_sync_unchanged_capture_moves_existing_file_without_resubmitting_review(environment, tmp_path, monkeypatch):
    store, client, kb = environment
    persist_space(store, {'scope': 'default', 'name': '通用事业部', 'knowledge_base_id': kb,
                          'mode': 'wiki', 'lifecycle': 'active'})
    record = {**capture(path=['钱流管理', '报表']), 'id': 'source-1', 'version_id': 'v1',
              'title': '部门业务统计', 'content': '# 原始正文'}
    archive = make_release_zip(tmp_path / 'unchanged.zip', [record])
    release = store.create_release('capture-job', 'default', 1, ['v1'], archive)
    assert run_sync(store, enqueue_sync(store, release, 'default'))['errors'] == []
    doc = next(iter(client.documents.values()))
    proper_parent = client.ensure_document_node(doc['id'])['node']['parent_node_id']
    root_id = client.list_nodes(kb)['parent_node']['node_id']
    node = client.ensure_document_node(doc['id'])['node']
    client.move_node(kb, node['node_id'], root_id, node['tree_version'])
    doc.update(text='人工已采纳改写正文', ingest_status='pending_review', latest_ingest_event_id='original-event')
    client.reviews['original-review'] = {'document_id': doc['id'], 'status': 'pending_review'}
    before = deepcopy((client.documents, client.reviews))
    forbidden = Mock(side_effect=AssertionError('同一捕获不能重新提交正文或评审'))
    monkeypatch.setattr(client, 'upload_file', forbidden)
    monkeypatch.setattr(client, 'update_file', forbidden)
    second = run_sync(store, enqueue_sync(store, release, 'default'))
    assert second['errors'] == []
    assert client.ensure_document_node(doc['id'])['node']['parent_node_id'] == proper_parent
    assert (client.documents, client.reviews) == before
    forbidden.assert_not_called()


def test_repair_report_snapshots_include_all_document_and_review_pages():
    from scripts.repair_import_directories import document_ids, review_snapshot
    client = Mock()
    docs = [{'id': f'doc-{index:03d}'} for index in range(103)]
    reviews = [{'review_id': f'review-{index:03d}', 'document_id': row['id'], 'created_at': '2026-11-17'}
               for index, row in enumerate(docs)]
    client.list_documents.side_effect = [{'documents': docs[:100]}, {'documents': docs[100:]}]
    client.list_reviews.side_effect = [{'reviews': reviews[:100], 'total': 103}, {'reviews': reviews[100:], 'total': 103}]
    assert document_ids(client, 'kb') == [row['id'] for row in docs]
    assert review_snapshot(client, 'kb') == reviews
    assert [call.kwargs['page'] for call in client.list_documents.call_args_list] == [1, 2]
    assert [call.kwargs['page'] for call in client.list_reviews.call_args_list] == [1, 2]


def test_repair_report_wiki_snapshot_walks_every_directory_and_cursor_page():
    from scripts.repair_import_directories import wiki_directories
    client = Mock()
    def read(kb_id, *, parent_page_id, page_type, cursor):
        assert kb_id == 'kb' and page_type == 'category'
        children = {
            (None, None): {'items': [{'page_id': 'root-a', 'title': 'A', 'parent_page_id': None}], 'next_cursor': 'next'},
            (None, 'next'): {'items': [{'page_id': 'root-b', 'title': 'B', 'parent_page_id': None}]},
            ('root-a', None): {'items': [{'page_id': 'child', 'title': '子目录', 'parent_page_id': 'root-a', 'sort_order': 2}]},
        }
        return children.get((parent_page_id, cursor), {'items': []})
    client.list_wiki_pages.side_effect = read
    result = wiki_directories(client, 'kb')
    assert [row['page_id'] for row in result] == ['child', 'root-a', 'root-b']
    assert result[0]['parent_page_id'] == 'root-a' and result[0]['sort_order'] == 2
    assert client.list_wiki_pages.call_count == 5
