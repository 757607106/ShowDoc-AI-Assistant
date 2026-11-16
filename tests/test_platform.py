"""Security and contract boundaries of the ContextDB deployment."""
import os
from pathlib import Path
from unittest.mock import Mock
from io import BytesIO
from zipfile import ZipFile

from governance.database import connection
from governance.store import Store
from integrations.contextdb import ContextDBClient, ContextDBError, ContextDBConflictError, ContextDBAuthError
from webapi.auth import create_user, cipher
import app as app_module



def mock_writable_library(monkeypatch, client, kb_id, mode='wiki'):
    """Keep proxy tests on a real-shaped library while mocking the target operation."""
    client.find_knowledge_base.return_value = None
    client.get_knowledge_base.side_effect = lambda identifier: {
        'id': identifier, 'name': 'Official library', 'wiki_enabled': mode == 'wiki',
        'graph_enabled': mode == 'graph'}
    client.get_document.side_effect = lambda _kb, doc, **kwargs: {
        'id': doc, 'knowledge_base_id': kb_id, 'name': 'source.md'}
    monkeypatch.setattr(app_module, 'client_for_user', lambda: client)


def test_batch_download_preserves_read_only_access_and_safe_distinct_names(authenticated_client, monkeypatch):
    import webapi.contextdb as proxy
    client = Mock()
    client._request.side_effect = [
        {'knowledge_base_id': 'kb', 'name': '../手册.md', 'download_url': 'https://files.example/a'},
        {'knowledge_base_id': 'kb', 'name': '../手册.md', 'download_url': 'https://files.example/b'},
    ]
    upstream = Mock()
    upstream.iter_content.return_value = [b'content']
    client._session.get.return_value = upstream
    monkeypatch.setattr(proxy, 'client_for_user', lambda: client)
    _, reader = login_as('download-reader@example.com')
    response = reader.post('/api/v1/knowledge-bases/kb/knowledge/batch-download', json={'ids': ['a', 'b']})
    assert response.status_code == 200 and response.mimetype == 'application/zip'
    with ZipFile(BytesIO(response.data)) as archive:
        assert len(set(archive.namelist())) == 2
        assert all('/' not in name and archive.read(name) == b'content' for name in archive.namelist())
    assert client._request.call_args_list[0].kwargs['params']['document_id'] == 'a'
    assert upstream.close.call_count == 2


def test_batch_download_validates_ids_before_accessing_cloud(authenticated_client, monkeypatch):
    import webapi.contextdb as proxy
    client = Mock()
    monkeypatch.setattr(proxy, 'client_for_user', lambda: client)
    for ids in ([], ['a'] * 201, ['a', 'a'], [None], 'a', [' ']):
        response = authenticated_client.post('/api/v1/knowledge-bases/kb/knowledge/batch-download', json={'ids': ids})
        assert response.status_code == 400
    client._request.assert_not_called()


def test_batch_download_uses_source_titles_and_original_filenames(authenticated_client, monkeypatch):
    import webapi.contextdb as proxy
    client = Mock()
    client._request.side_effect = [
        {'knowledge_base_id': 'kb', 'name': 'doc-hash.html', 'metadata': {'title': '采购明细'}, 'download_url': 'https://files.example/a'},
        {'knowledge_base_id': 'kb', 'name': 'doc-hash.docx', 'metadata': {'title': '手册', 'filename': '使用手册（完整版）.docx'}, 'download_url': 'https://files.example/b'},
        {'knowledge_base_id': 'kb', 'name': 'original.pdf', 'metadata': {'title': 123, 'filename': False}, 'download_url': 'https://files.example/c'},
    ]
    upstream = Mock()
    upstream.iter_content.return_value = [b'content']
    client._session.get.return_value = upstream
    monkeypatch.setattr(proxy, 'client_for_user', lambda: client)
    response = authenticated_client.post('/api/v1/knowledge-bases/kb/knowledge/batch-download', json={'ids': ['a', 'b', 'c']})
    assert response.status_code == 200
    with ZipFile(BytesIO(response.data)) as archive:
        assert archive.namelist() == ['采购明细.html', '使用手册（完整版）.docx', 'original.pdf']


def test_batch_download_checks_library_and_download_permission_before_fetching(authenticated_client, monkeypatch):
    import webapi.contextdb as proxy
    client = Mock()
    monkeypatch.setattr(proxy, 'client_for_user', lambda: client)
    for detail, status in (({'knowledge_base_id': 'other', 'download_url': 'https://files.example/a'}, 404),
                           ({'knowledge_base_id': 'kb'}, 409)):
        client._request.return_value = detail
        response = authenticated_client.post('/api/v1/knowledge-bases/kb/knowledge/batch-download', json={'ids': ['a']})
        assert response.status_code == status
    client._session.get.assert_not_called()


def test_batch_download_rejects_excess_actual_bytes_without_returning_partial_zip(authenticated_client, monkeypatch):
    import webapi.contextdb as proxy
    client = Mock()
    client._request.return_value = {'knowledge_base_id': 'kb', 'name': 'a.md', 'download_url': 'https://files.example/a'}
    upstream = Mock()
    upstream.iter_content.return_value = [b'123', b'456']
    client._session.get.return_value = upstream
    monkeypatch.setattr(proxy, 'client_for_user', lambda: client)
    monkeypatch.setattr(proxy, 'MAX_BATCH_DOWNLOAD_BYTES', 5)
    response = authenticated_client.post('/api/v1/knowledge-bases/kb/knowledge/batch-download', json={'ids': ['a']})
    assert response.status_code == 413 and response.is_json
    upstream.close.assert_called_once()


def login_as(email, role='viewer'):
    uid=create_user(email,email,'test-password-123',role)
    with connection() as conn:
        conn.execute('UPDATE platform_users SET contextdb_key_encrypted=%s WHERE id=%s',(cipher().encrypt(b'another-member-key').decode(),uid))
    http=app_module.app.test_client()
    token=http.post('/api/v1/auth/login',json={'email':email,'password':'test-password-123'}).json['token']
    http.environ_base['HTTP_AUTHORIZATION']='Bearer '+token
    return uid,http


def test_requires_login_and_does_not_trust_tenant_header(authenticated_client):
    raw=app_module.app.test_client()
    assert raw.get('/api/v1/sessions').status_code==401
    assert raw.post('/api/v1/auth/login',json=[]).status_code==400
    assert authenticated_client.get('/api/v1/sessions',headers={'X-Tenant-ID':'another-company'}).status_code==200
    assert authenticated_client.get('/api/contextdb/v1/not-official').status_code==501


def test_memory_proxy_routes_never_reach_cloud(authenticated_client, monkeypatch):
    import webapi.contextdb as proxy
    factory = Mock(side_effect=AssertionError('removed APIs must not access ContextDB'))
    monkeypatch.setattr(proxy, 'client_for_user', factory)
    for resource in (
        'v3/memories', 'v3/memories/add', 'v3/memories/search', 'v3/knowledge/knowledge_bases',
        'v1/memories/m-1', 'v1/memories/m-1/history', 'v1/memories/evolve', 'v1/memories/dream',
        'v1/memories/session-context', 'v1/memories/facts', 'v1/memories/entities',
        'v1/memories/activities', 'v1/memories/forgetting/batch', 'v1/memory_promotions',
        'v1/memory_promotions/generate', 'v1/memory_promotions/approve', 'v1/memory_promotions/reject',
        'v1/memory_promotions/settings', 'v1/memory_promotions/schedules',
        'v1/memory_promotions/templates/t-1', 'v1/memory_promotions/templates/t-1/set_default',
    ):
        for method in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE'):
            response = authenticated_client.open('/api/contextdb/' + resource, method=method, json={})
            assert response.status_code == 501, (method, resource, response.text)
    factory.assert_not_called()


def test_native_knowledge_and_event_routes_remain_available(authenticated_client, monkeypatch):
    import webapi.contextdb as proxy
    client = Mock()
    client._request.return_value = {'official': True}
    monkeypatch.setattr(proxy, 'client_for_user', lambda: client)
    for resource in ('knowledge/knowledge_bases', 'knowledge/reviews', 'knowledge/wiki/pages',
                     'events', 'event/knowledge-ingest-1'):
        response = authenticated_client.get('/api/contextdb/v1/' + resource)
        assert response.status_code == 200 and response.json['data'] == {'official': True}
        client._request.assert_called_with('GET', '/v1/' + resource, json_body=None, params={})


def test_native_graph_queries_preserve_official_parameters_and_reader_access(authenticated_client, monkeypatch):
    import webapi.contextdb as proxy
    client = Mock()
    mock_writable_library(monkeypatch, client, 'graph-kb', mode='graph')
    client._request.return_value = {'official': True}
    monkeypatch.setattr(proxy, 'client_for_user', lambda: client)
    _, reader = login_as('graph-reader@example.com')
    queries = [
        ('knowledge/entities', {'kb_id': 'graph-kb', 'keyword': '采购明细', 'page': '1', 'page_size': '100'}),
        ('knowledge/graph-visual', {'knowledge_base_id': 'graph-kb', 'document_id': 'doc-1',
                                  'entity_id': '采购明细', 'max_hops': '2', 'max_nodes': '200', 'max_edges': '500'}),
        ('knowledge/entities/detail', {'knowledge_base_id': 'graph-kb', 'entity_id': '采购明细'}),
        ('knowledge/entity-relations/detail', {'knowledge_base_id': 'graph-kb', 'relation_id': 'relation-1'}),
        ('knowledge/entities/chunks', {'knowledge_base_id': 'graph-kb', 'entity_ids': '采购明细', 'limit': '20'}),
    ]
    for resource, params in queries:
        response = reader.get('/api/contextdb/v1/' + resource, query_string=params)
        assert response.status_code == 200 and response.json['data'] == {'official': True}
        client._request.assert_called_with('GET', '/v1/' + resource, json_body=None, params=params)
    client._request.reset_mock()
    response = reader.post('/api/contextdb/v1/knowledge/events',
                           json={'document_id': 'doc-1', 'event_type': 'graph_build'})
    assert response.status_code == 403
    assert reader.post('/api/contextdb/v1/knowledge/graph/consolidate', json={'kb_id': 'graph-kb'}).status_code == 403
    client._request.assert_not_called()
    client._request.return_value = {'dispatched': True, 'event_id': 'graph-merge-1'}
    response = authenticated_client.post('/api/contextdb/v1/knowledge/graph/consolidate', json={'kb_id': 'graph-kb'})
    assert response.status_code == 200 and response.json['data']['event_id'] == 'graph-merge-1'
    client._request.assert_called_once_with('POST', '/v1/knowledge/graph/consolidate',
                                           json_body={'kb_id': 'graph-kb'}, params={})


def test_user_cannot_read_or_stop_another_session(authenticated_client):
    sid=authenticated_client.post('/api/v1/sessions',json={}).json['data']['id']
    _,other=login_as('reader@example.com')
    assert other.get(f'/api/v1/sessions/{sid}').status_code==404
    assert other.post(f'/api/v1/sessions/{sid}/stop',json={}).status_code==404
    assert other.delete(f'/api/v1/sessions/{sid}').status_code==404
    assert other.get('/api/platform/users').status_code==403
    assert other.post('/api/contextdb/v1/knowledge/documents',json={}).status_code==403


def test_credentials_are_encrypted_and_member_binding_unique(authenticated_client,monkeypatch):
    monkeypatch.setattr(ContextDBClient,'current_permissions',lambda self:{'member':{'member_id':'member-new'}})
    payload={'email':'new@example.com','username':'新成员','password':'test-password-123','role':'editor','contextdb_api_key':'ctxdb-member-new'}
    first=authenticated_client.post('/api/platform/users',json=payload)
    assert first.status_code==201
    payload['email']='duplicate@example.com'
    assert authenticated_client.post('/api/platform/users',json=payload).status_code==409
    with connection() as conn:
        encrypted=conn.execute('SELECT contextdb_key_encrypted FROM platform_users WHERE id=%s',(first.json['id'],)).fetchone()['contextdb_key_encrypted']
        assert 'ctxdb-member-new' not in encrypted
        assert cipher().decrypt(encrypted.encode())==b'ctxdb-member-new'
    assert 'ctxdb-member-new' not in authenticated_client.get('/api/platform/users').text


def test_source_server_credentials_are_not_shared_with_other_roles(authenticated_client,monkeypatch):
    login=Mock(side_effect=AssertionError('Must not use server source credentials'))
    monkeypatch.setattr(app_module.showdoc_auth,'auto_login_if_needed',login)
    for role in ('viewer','editor'):
        _,other=login_as(role+'@example.com',role)
        assert other.post('/showdoc/login').status_code==403
        assert other.get('/showdoc/projects').status_code==403
        assert other.get('/showdoc/project/1').status_code==403
        assert other.post('/entries/showdoc/start',json={'auth':True,'item_id':1}).status_code==403
    login.assert_not_called()


def test_official_auth_failure_keeps_platform_session(authenticated_client,monkeypatch):
    import webapi.contextdb as proxy
    client=Mock()
    client._request.side_effect=ContextDBAuthError('member disabled',status_code=403,error_code=4006,request_id='official-request')
    monkeypatch.setattr(proxy,'client_for_user',lambda:client)
    response=authenticated_client.get('/api/contextdb/v1/knowledge/knowledge_bases')
    assert response.status_code==403
    assert response.json['source']=='contextdb' and response.json['request_id']=='official-request'
    assert authenticated_client.get('/api/v1/auth/me').status_code==200


def test_native_wiki_reads_full_page_and_preserves_conflict_version(authenticated_client,monkeypatch):
    import webapi.contextdb as proxy
    client=Mock()
    mock_writable_library(monkeypatch, client, 'kb')
    content='\n'.join(f'## 章节 {n}\n完整正文' for n in range(100))
    client._request.return_value={'content':content,'version':42,'page_id':'page'}
    monkeypatch.setattr(proxy,'client_for_user',lambda:client)
    monkeypatch.setattr(app_module,'client_for_user',lambda:client)
    response=authenticated_client.get('/api/contextdb/v1/knowledge/wiki/pages/detail?knowledge_base_id=kb&page_id=page')
    assert response.json['data']['content']==content and response.json['data']['version']==42
    client._request.reset_mock()
    client._request.side_effect=ContextDBConflictError('stale',status_code=409,error_code=4033,request_id='conflict-request')
    client.get_wiki_page.return_value={'version':43}
    body={'knowledge_base_id':'kb','page_id':'page','content':'稿件','expected_version':42}
    response=authenticated_client.put('/api/contextdb/v1/knowledge/wiki/pages',json=body)
    assert response.status_code==409 and response.json['current_version']==43
    assert response.json['source']=='contextdb' and response.json['request_id']=='conflict-request'
    client._request.assert_called_once_with('PUT','/v1/knowledge/wiki/pages',json_body=body,params={})


def test_native_wiki_reads_preserve_cursors_filters_and_reader_access(authenticated_client,monkeypatch):
    import webapi.contextdb as proxy
    client=Mock()
    result={'items':[], 'next_cursor':'official-next', 'limit':2}
    client._request.return_value=result
    monkeypatch.setattr(proxy,'client_for_user',lambda:client)
    _,reader=login_as('wiki-reader@example.com')
    queries=[
        ('index',{'types':'concept','cursor':'group-next','limit':'2'}),
        ('pages',{'parent_page_id':'directory','page_type':'category','cursor':'tree-next','limit':'2'}),
        ('pages/detail',{'page_id':'page'}),
        ('search',{'query':'连接池','mode':'keyword','limit':'10'}),
        ('summary',{'document_id':'document'}),
        ('revisions',{'page_id':'page','cursor':'older','limit':'2'}),
        ('revisions/diff',{'revision_id':'revision','base_revision_id':'base'}),
        ('compile-runs',{'status':'pending','cursor':'runs-next','limit':'2'}),
        ('issues',{'status':'pending','issue_type':'merge_conflict','severity':'high','cursor':'issues-next','limit':'2'}),
        ('issues/detail',{'issue_id':'issue'}),
        ('issue-tasks/detail',{'event_id':'task-event'}),
    ]
    for path,query in queries:
        params={'knowledge_base_id':'wiki-kb',**query}
        response=reader.get('/api/contextdb/v1/knowledge/wiki/'+path,query_string=params)
        assert response.status_code==200 and response.json['data']==result, path
        client._request.assert_called_with('GET','/v1/knowledge/wiki/'+path,json_body=None,params=params)


def test_native_wiki_writes_preserve_official_payloads_and_block_readers(authenticated_client,monkeypatch):
    import webapi.contextdb as proxy
    client=Mock()
    mock_writable_library(monkeypatch, client, 'wiki-kb')
    client._request.return_value={'event_id':'official-event'}
    monkeypatch.setattr(proxy,'client_for_user',lambda:client)
    _,reader=login_as('wiki-write-reader@example.com')
    writes=[
        ('POST','pages',{'title':'主题','content':'正文','page_type':'concept','parent_page_id':'directory','comment':'创建'}),
        ('PUT','pages',{'page_id':'page','content':'正文','expected_version':42,'comment':'修正'}),
        ('POST','directories',{'title':'目录','parent_page_id':'directory'}),
        ('POST','directories/actions',{'directory_id':'directory','action':'rename','title':'新目录','expected_version':3}),
        ('POST','pages/actions',{'page_id':'page','action':'move','expected_version':42,'parent_page_id':'directory','expected_parent_version':3}),
        ('POST','compile-runs/actions',{'action':'recompile_affected','document_id':'document'}),
        ('POST','issues/actions',{'issue_id':'issue','action':'ignore','expected_version':2,'reason':'已核实'}),
        ('POST','issues/tasks',{'idempotency_key':'decision-key','items':[{'issue_id':'issue','expected_version':2,'choice':'manual_edit','manual_content':'修订'}]}),
    ]
    for method,path,body in writes:
        assert reader.open('/api/contextdb/v1/knowledge/wiki/'+path,method=method,
                           json={'knowledge_base_id':'wiki-kb',**body}).status_code==403
    assert reader.delete('/api/contextdb/v1/knowledge/wiki/pages',
                         query_string={'knowledge_base_id':'wiki-kb','page_id':'page'}).status_code==403
    client._request.assert_not_called()
    for method,path,body in writes:
        payload={'knowledge_base_id':'wiki-kb',**body}
        response=authenticated_client.open('/api/contextdb/v1/knowledge/wiki/'+path,method=method,json=payload)
        assert response.status_code==200 and response.json['data']['event_id']=='official-event', path
        client._request.assert_called_with(method,'/v1/knowledge/wiki/'+path,json_body=payload,params={})
    params={'knowledge_base_id':'wiki-kb','page_id':'page'}
    assert authenticated_client.delete('/api/contextdb/v1/knowledge/wiki/pages',query_string=params).status_code==200
    client._request.assert_called_with('DELETE','/v1/knowledge/wiki/pages',json_body=None,params=params)


def test_native_wiki_rejects_undocumented_http_methods(authenticated_client,monkeypatch):
    import webapi.contextdb as proxy
    client=Mock()
    monkeypatch.setattr(proxy,'client_for_user',lambda:client)
    read_only=('index','pages/detail','search','summary','revisions','revisions/diff','compile-runs',
               'issues','issues/detail','issue-tasks/detail')
    write_only=('directories','directories/actions','pages/actions','compile-runs/actions','issues/actions','issues/tasks')
    for paths,methods in ((read_only,('POST','PUT','PATCH','DELETE')),
                          (write_only,('GET','PUT','PATCH','DELETE')),
                          (('pages',),('PATCH',))):
        for path in paths:
            for method in methods:
                response=authenticated_client.open('/api/contextdb/v1/knowledge/wiki/'+path,method=method,json={})
                assert response.status_code==501, (method,path)
    client._request.assert_not_called()


def test_native_wiki_errors_preserve_official_details_and_platform_session(authenticated_client,monkeypatch):
    import webapi.contextdb as proxy
    client=Mock()
    mock_writable_library(monkeypatch, client, 'wiki-kb')
    monkeypatch.setattr(proxy,'client_for_user',lambda:client)
    cases=[
        ('GET','search',ContextDBError('invalid query',status_code=400,error_code=1001),400),
        ('GET','index',ContextDBAuthError('access denied',status_code=403,error_code=4007),403),
        ('POST','issues/tasks',ContextDBConflictError('stale issue',status_code=409,error_code=4033),409),
        ('GET','compile-runs',ContextDBError('upstream unavailable',status_code=500,error_code=5001),503),
    ]
    for method,path,error,status in cases:
        error.request_id='official-wiki-request'
        client._request.side_effect=error
        response=authenticated_client.open('/api/contextdb/v1/knowledge/wiki/'+path,method=method,
                                          query_string={'knowledge_base_id':'wiki-kb'},json={} if method=='POST' else None)
        assert response.status_code==status and response.json['source']=='contextdb'
        assert response.json['error_code']==error.error_code and response.json['request_id']=='official-wiki-request'
    assert authenticated_client.get('/api/v1/auth/me').status_code==200


def test_wiki_revision_metadata_requires_page_and_preserves_official_result(authenticated_client,monkeypatch):
    import webapi.contextdb as proxy
    client=Mock()
    metadata={'items':[{'revision_id':'revision','page_id':'page','section_id':'section','review_status':'pending'}],
              'next_cursor':'official-cursor','limit':50}
    client._request.return_value=metadata
    monkeypatch.setattr(proxy,'client_for_user',lambda:client)
    for suffix in ('','?page_id=%20'):
        assert authenticated_client.get('/api/contextdb/v1/knowledge/wiki/revisions'+suffix).status_code==400
    client._request.assert_not_called()
    response=authenticated_client.get('/api/contextdb/v1/knowledge/wiki/revisions?knowledge_base_id=kb&page_id=page&cursor=older&limit=50')
    assert response.status_code==200 and response.json['data']==metadata
    client._request.assert_called_once_with('GET','/v1/knowledge/wiki/revisions',json_body=None,
                                          params={'knowledge_base_id':'kb','page_id':'page','cursor':'older','limit':'50'})


def test_unexposed_wiki_writes_never_reach_cloud(authenticated_client,monkeypatch):
    import webapi.contextdb as proxy
    client=Mock()
    monkeypatch.setattr(proxy,'client_for_user',lambda:client)
    for path in ('revisions','revisions/approve','revisions/reject','pages/rollback','publish','directories/rollback'):
        response=authenticated_client.post('/api/contextdb/v1/knowledge/wiki/'+path,json={'page_id':'page'})
        assert response.status_code==501
    client._request.assert_not_called()


def test_removed_legacy_wiki_routes_do_not_access_cloud(authenticated_client,monkeypatch):
    import webapi.contextdb as proxy
    factory=Mock(side_effect=AssertionError('Legacy Wiki must not access ContextDB'))
    monkeypatch.setattr(proxy,'client_for_user',factory)
    for method,path in (('GET','/api/wiki/pages'),('POST','/api/wiki/pages'),
                        ('GET','/api/wiki/pages/page'),('PUT','/api/wiki/pages/page'),
                        ('POST','/api/contextdb/wiki-search')):
        assert authenticated_client.open(path,method=method,json={}).status_code==404
    factory.assert_not_called()


def test_capture_bodies_never_written_to_postgres(tmp_path):
    store=Store(owner_id='capture-owner')
    store._create('version','source-v1',{'content':'SOURCE-BODY-ONLY-IN-ARTIFACT','id':'d'}, {'type':'version','version_id':'source-v1'})
    with connection() as conn:
        row=conn.execute("SELECT payload FROM runtime_records WHERE kind='version'").fetchone()
    assert 'SOURCE-BODY' not in str(row['payload'])
    assert Path(row['payload']['_capture_path']).read_text().find('SOURCE-BODY')>=0
    assert Store(owner_id='different')._list({'type':'version'})==[]


def test_favorites_and_role_revocation_are_scoped(authenticated_client):
    assert authenticated_client.post('/api/v1/user/favorites',json={'type':'kb','id':'kb1'}).status_code==200
    uid,reader=login_as('reader@example.com')
    assert reader.get('/api/v1/user/favorites?type=kb').json['data']==[]
    assert reader.post('/api/v1/user/favorites',json={'type':'kb','id':'kb2'}).status_code==200
    assert [x['resource_id'] for x in authenticated_client.get('/api/v1/user/favorites?type=kb').json['data']]==['kb1']
    assert authenticated_client.patch('/api/platform/users/'+uid,json={'active':False}).status_code==200
    assert reader.get('/api/v1/sessions').status_code==401


def test_platform_collection_preserves_source_without_local_parser(tmp_path):
    from crawlers.base import BaseCrawler, CrawledDocument, DocumentStub
    crawler=BaseCrawler(str(tmp_path));crawler.source_only=True
    crawler.list_documents=lambda:[DocumentStub('1','标题','分类')]
    crawler.fetch_document=lambda stub:CrawledDocument('1','标题','分类','<h1>完整原文</h1>','',{},'html')
    crawler.pipeline.convert=Mock(side_effect=AssertionError('Platform collection must use official parsing'))
    summary=crawler.crawl()
    import json
    record=json.loads(Path(summary.rag_documents_file).read_text().strip())
    assert record['content']=='<h1>完整原文</h1>' and record['source_format']=='html'
    assert Path(summary.rag_chunks_file).read_text()==''
    assert summary.failed_documents==0
    crawler.pipeline.convert.assert_not_called()


def test_public_runtime_assets_are_served_without_spa_html(tmp_path,monkeypatch):
    root=tmp_path/'dist';root.mkdir();(root/'index.html').write_text('<html>SPA</html>')
    (root/'config.js').write_text('window.WEKNORA_CONFIG = {};')
    monkeypatch.setattr(app_module,'FRONTEND_DIST',root)
    raw=app_module.app.test_client()
    assert raw.get('/config.js').text=='window.WEKNORA_CONFIG = {};'
    assert raw.get('/missing.js').status_code==404


def test_sync_status_includes_document_names_and_separate_processing_stages(authenticated_client,monkeypatch):
    import webapi.knowledge as knowledge
    client=Mock()
    detail={'name':'产品手册.md','lifecycle_state':'pending_human','review_status':'pending',
            'ingest_status':'pending_review','wiki_status':'pending','graph_status':'processing',
            'wiki_error_message':'页面生成尚未完成'}
    client.get_document.return_value=detail
    monkeypatch.setattr(knowledge,'_client',lambda:client)
    with connection() as conn:
        conn.execute('''INSERT INTO knowledge_sync(owner_id,scope,source_id,target_mode,knowledge_base_id,document_id,status)
            VALUES (%s,'product','source-a','wiki','kb-a','doc-a','uploading')''',(os.environ['TEST_PLATFORM_USER'],))
    response=authenticated_client.get('/api/kb/sync-mappings')
    assert response.status_code==200
    row=response.json['mappings'][0]
    assert row['status']=='uploading'
    assert row['official']==detail
    assert response.json['total']==1
