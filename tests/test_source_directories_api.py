"""Preview uses the same source tree as capture; custom roots stay out of identity."""
import os
from unittest.mock import Mock

import pytest

import app as app_module
from crawlers.showdoc import ShowDocCrawler
from crawlers.web import WebCrawler
from governance.store import Store, source_scope
from governance.import_directories import ImportDirectories
from integrations.contextdb import ContextDBError
from tests.contextdb_fake import FakeContextDBClient


@pytest.fixture()
def client(authenticated_client):
    fake = FakeContextDBClient()
    fake.create_knowledge_base('knowledge-default', wiki_enabled=True)
    app_module.app.extensions['governance_store'] = Store(client=fake, owner_id=os.environ['TEST_PLATFORM_USER'])
    yield authenticated_client
    app_module.app.extensions.pop('governance_store', None)


def test_showdoc_preview_has_project_root_and_relative_tree(client, tmp_path, monkeypatch):
    crawler = ShowDocCrawler(str(tmp_path), item_id='399')
    crawler._post = Mock(return_value={'error_code': 0, 'data': {
        'item_name': '云辉煌知识库', 'menu': {
            'pages': [{'page_id': 'root', 'page_title': '说明'}],
            'catalogs': [{'cat_name': '进货管理', 'catalogs': [{'cat_name': '报表',
                         'pages': [{'page_id': 'nested', 'page_title': '统计'}]}]}]}}})
    monkeypatch.setattr(app_module, 'create_crawler', lambda *args, **kwargs: crawler)
    result = client.get('/entries/showdoc/documents?item_id=399').get_json()
    assert result['directory'] == {'root_name': '云辉煌知识库', 'source_key': 'showdoc:399', 'preview_complete': True}
    assert [page['directory_path'] for page in result['pages']] == [[], ['进货管理', '报表']]


def test_unknown_web_site_preview_is_explicitly_incomplete(client, tmp_path, monkeypatch):
    monkeypatch.setattr(WebCrawler, 'validate_url', staticmethod(lambda value: value))
    crawler = WebCrawler(str(tmp_path), 'https://docs.example.test/start', crawl_mode='site')
    crawler._crawl_site = Mock(side_effect=AssertionError('Preview must not run a full site crawl'))
    monkeypatch.setattr(app_module, 'create_crawler', lambda *args, **kwargs: crawler)
    result = client.get('/entries/web/documents?url=https://docs.example.test/start&crawl_mode=site').get_json()
    assert result['directory'] == {'root_name': 'docs.example.test', 'source_key': 'web:docs.example.test', 'preview_complete': False}
    assert result['pages'][0]['directory_path'] == []
    crawler._crawl_site.assert_not_called()


def test_custom_root_is_job_metadata_and_does_not_change_source_params(client, monkeypatch):
    store = app_module.get_store()
    create = Mock(return_value={'task_id': 'new-task'})
    monkeypatch.setattr(store, 'create_job', create)
    result = client.post('/entries/showdoc/start', json={'item_id': '399', 'import_root_name': ' 产品资料 '})
    assert result.status_code == 200
    assert create.call_args.kwargs['import_directory'] == {'root_name': '产品资料'}
    params = create.call_args.args[1]
    assert params == {'item_id': '399'}
    assert source_scope('showdoc', params) == 'showdoc:399'


@pytest.mark.parametrize('name', ['', 'a/b', '..', 'a\x00b', None])
def test_invalid_root_is_rejected_before_a_job_is_created(client, monkeypatch, name):
    create = Mock(side_effect=AssertionError('Invalid directory must not queue work'))
    monkeypatch.setattr(app_module.get_store(), 'create_job', create)
    result = client.post('/entries/showdoc/start', json={'item_id': '399', 'import_root_name': name})
    assert result.status_code == 400
    create.assert_not_called()


def test_preview_reuses_current_node_label_for_the_same_source_only(client, tmp_path, monkeypatch):
    store = app_module.get_store()
    kb = next(iter(store.client.knowledge_bases.values()))
    manager = ImportDirectories(store, kb['id'])
    node_id, _ = manager.target({'source_key': 'showdoc:399', 'metadata': {
        'import_directory': {'root_name': '用户自定义目录', 'path': []}}})
    node = store.client.list_nodes(kb['id'], parent_node_id=node_id)['parent_node']
    store.client.rename_node(kb['id'], node_id, '人工更名后的目录', node['tree_version'])
    manager.target({'source_key': 'showdoc:412', 'metadata': {
        'import_directory': {'root_name': '同名项目的另一目录', 'path': []}}})
    other_owner = Store(client=store.client, owner_id='another-owner')
    ImportDirectories(other_owner, kb['id']).target({'source_key': 'showdoc:500', 'metadata': {
        'import_directory': {'root_name': '其他账号的目录', 'path': []}}})

    def crawler(key, **params):
        assert 'knowledge_base_id' not in params
        result = ShowDocCrawler(str(tmp_path), item_id=params['item_id'])
        result._post = Mock(return_value={'error_code': 0, 'data': {
            'item_name': '云辉煌知识库', 'menu': {'pages': [{'page_id': 'one', 'page_title': '说明'}]}}})
        return result

    monkeypatch.setattr(app_module, 'create_crawler', crawler)
    names = []
    for item_id in ('399', '412', '500', 'unmapped'):
        response = client.get('/entries/showdoc/documents', query_string={
            'item_id': item_id, 'knowledge_base_id': kb['id']})
        assert response.status_code == 200
        names.append(response.json['directory']['root_name'])
    assert names == ['人工更名后的目录', '同名项目的另一目录', '云辉煌知识库', '云辉煌知识库']


def test_preview_checks_library_access_before_reading_the_source(client, monkeypatch):
    monkeypatch.setattr(app_module.get_store().client, 'get_knowledge_base',
                        Mock(side_effect=ContextDBError('Forbidden', status_code=403)))
    crawler = Mock(side_effect=AssertionError('Do not fetch a source for an unreadable destination'))
    monkeypatch.setattr(app_module, 'create_crawler', crawler)
    response = client.get('/entries/showdoc/documents', query_string={
        'item_id': '399', 'knowledge_base_id': 'private-library'})
    assert response.status_code == 403
    crawler.assert_not_called()
