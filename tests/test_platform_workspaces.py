"""Personal workspace lifecycle and byte quotas against isolated platform and Agent databases."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import io
import os
from pathlib import Path

import pytest
from deepagents.backends.utils import create_file_data

from agent import registry, sessions
from governance.database import connection
from governance.store import Store, StoreError, data_dir
from tests.contextdb_fake import FakeContextDBClient
from tests.test_platform_account_auth import sign_in
from tests.test_platform_skill_runtime import manifest
from webapi.auth import cipher, create_user

QUOTA = 10 * 1024**3


def workspace(client):
    return client.get('/api/v1/auth/me').json['data']['tenant']


def upload(client, data):
    return client.post('/api/uploads', data={'files': (io.BytesIO(data), 'original.md')})


@pytest.fixture
def shared_kb(monkeypatch):
    kb = FakeContextDBClient()
    base = kb.create_knowledge_base('Shared reference')
    kb.create_text_document(base['id'], 'team.md', 'Shared team document')
    monkeypatch.setattr('webapi.auth.ContextDBClient', lambda **_: kb)
    return kb


def test_two_accounts_delete_only_their_workspace_and_keep_shared_knowledge(authenticated_client, shared_kb):
    a = authenticated_client
    b_id = create_user('workspace-b', 'Workspace B', 'password-b', 'viewer')
    with connection() as conn:
        conn.execute("UPDATE platform_users SET contextdb_key_encrypted=%s WHERE id=%s", (cipher().encrypt(b'kb-b').decode(), b_id))
    b, _ = sign_in('workspace-b', 'password-b')
    wa, wb = workspace(a), workspace(b)
    assert wa['id'] != wb['id'] and wa['storage_quota'] == wb['storage_quota'] == QUOTA
    assert wa['storage_used'] == wb['storage_used'] == 0
    a_url, b_url = (f"/api/v1/tenants/{w['id']}" for w in (wa, wb))
    assert b.put(b_url, json={'name': 'Beta', 'description': 'My workspace'}).status_code == 200
    assert b.put(b_url, json={'description': ''}).json['data']['description'] == ''
    assert b.get('/api/platform/users').status_code == 403
    for body in ({'name': ' '}, {'name': 'x'*65}, {'description': 'x'*513}, {'storage_quota': QUOTA * 2}):
        assert a.put(a_url, json=body).status_code == 400
    for method in ('get', 'put', 'delete'):
        assert getattr(b, method)(a_url, headers={'X-Tenant-ID': str(wa['id'])}).status_code == 404
    assert [i['id'] for i in b.get('/api/v1/tenants/all').json['data']['items']] == [wb['id']]
    assert b.get(b_url + '/members').json['data']['members'][0]['user_id'] == b_id
    assert a.get(b_url + '/members').status_code == 404
    shared = a.get('/api/kb/bases').json['bases']
    assert shared and b.get('/api/kb/bases').json['bases'] == shared
    documents = '/api/kb/documents?kb_id=' + shared[0]['id']
    shared_doc = a.get(documents).json['documents'][0]
    assert b.get(documents).json['documents'][0]['id'] == shared_doc['id']
    a.post('/api/v1/user/favorites', json={'type':'kb', 'id':shared[0]['id']})
    job = upload(a, b'alpha').json['task_id']
    assert workspace(a)['storage_used'] == 5
    sid = sessions.create_session(owner_id=b_id)['id']
    item = b.post(f'/api/v1/sessions/{sid}/attachments', data={'file': (io.BytesIO(b'beta-data'), 'beta.png')}).json['data']
    preview = f"/api/v1/sessions/{sid}/attachments/{item['id']}/preview"
    assert workspace(b)['storage_used'] == 9 and a.get(preview).status_code == 404
    assert a.delete(a_url).status_code == 200
    assert workspace(a) is None and a.get('/task_status/' + job).status_code == 403
    assert a.get('/api/kb/bases').json['bases'] == shared
    assert workspace(b)['name'] == 'Beta' and workspace(b)['storage_used'] == 9
    assert b.get(preview).data == b'beta-data' and b.get('/api/kb/bases').json['bases'] == shared
    assert b.get(documents).json['documents'][0]['id'] == shared_doc['id']
    assert shared_kb.download_document_text(shared[0]['id'], shared_doc['id']) == 'Shared team document'
    a, login = sign_in('test@example.com', 'test-password-123')
    assert login.json['tenant_required'] and login.json['memberships'] == []
    fresh = a.post('/api/v1/tenants', json={'name':'Fresh'}).json['data']
    assert fresh['id'] != wa['id'] and fresh['storage_used'] == 0
    assert a.get('/task_status/' + job).status_code == 404
    assert a.post('/api/v1/tenants', json={'name':'Extra'}).status_code == 409
    assert workspace(b)['id'] == wb['id'] and b.get(preview).data == b'beta-data'
    assert a.get('/api/kb/bases').json['bases'] == shared
    assert a.get('/api/v1/user/favorites?type=kb').json['data'][0]['resource_id'] == shared[0]['id']


def test_exact_10_gib_and_concurrent_uploads(authenticated_client, shared_kb):
    owner = os.environ['TEST_PLATFORM_USER']
    path = data_dir() / 'uploads' / 'pre-existing' / 'large.bin'
    path.parent.mkdir(parents=True)
    with path.open('wb') as f:
        f.truncate(QUOTA - 1)  # A sparse file has the real logical byte length without allocating 10 GiB.
    store = Store(client=shared_kb, owner_id=owner)
    for _ in range(2):
        store.create_job('file', {'file_paths':[str(path)]})
    assert workspace(authenticated_client)['storage_used'] == QUOTA - 1
    clients = [sign_in('test@example.com', 'test-password-123')[0] for _ in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda c: upload(c, b'x'), clients))
    assert sorted(r.status_code for r in results) == [200, 413]
    assert workspace(authenticated_client)['storage_used'] == QUOTA
    assert upload(authenticated_client, b'!').status_code == 413
    assert len(list((data_dir() / 'uploads').iterdir())) == 2


def test_skill_memory_and_checkpoint_sizes_replacements_and_rollback(authenticated_client):
    from agent.checkpointer import async_checkpointer
    from agent.graph import build_agent
    a = authenticated_client
    owner = os.environ['TEST_PLATFORM_USER']
    sid = sessions.create_session(owner_id=owner)['id']
    file = create_file_data('报告')
    async def write(item):
        async with async_checkpointer() as saver:
            graph = await build_agent(saver, api_key='', owner_id=owner, load_tools=False)
            config = {'configurable': {'thread_id': sid}}
            await graph.aupdate_state(config, {'files': {'/report.txt': item, '/attachments/a/input': file}}, as_node='model')
            return (await graph.aget_state(config)).values['files']['/report.txt']
    assert asyncio.run(write(file)) == file
    assert asyncio.run(write(file)) == file
    assert workspace(a)['storage_used'] == 6
    memory_url = '/api/v1/agents/builtin-smart-reasoning/memory-file'
    assert a.put(memory_url, json={'content':'好'}).status_code == 200
    assert a.put(memory_url, json={'content':'ok'}).status_code == 200
    assert workspace(a)['storage_used'] == 8
    url = '/api/v1/skills/catalog'
    skill = a.post(url, json={'files':{'SKILL.md':manifest()}}).json['data']
    saved = registry.record('skill', skill['id'], owner)
    old = Path(saved['_bundle_path'])
    assert workspace(a)['storage_used'] == 8 + old.stat().st_size
    assert a.post(url, json={'files':{'SKILL.md':manifest(), 'extra':'file'}}).json['data']['id'] == skill['id']
    new = Path(registry.record('skill', skill['id'], owner)['_bundle_path'])
    assert not old.exists() and workspace(a)['storage_used'] == 8 + new.stat().st_size
    assert a.delete(url + '/' + skill['id']).status_code == 200 and not new.exists()
    assert workspace(a)['storage_used'] == 8
    with connection() as conn:
        conn.execute('UPDATE platform_workspaces SET storage_quota=8 WHERE principal_id=%s', (owner,))
    with pytest.raises(StoreError, match='配额'):
        asyncio.run(write(create_file_data('too large')))
    assert a.put(memory_url, json={'content':'three'}).status_code == 413
    assert a.get(memory_url).json['data']['content'] == 'ok'
    assert a.post(url, json={'files':{'SKILL.md':manifest()}}).status_code == 413
    assert not list(new.parent.glob('*.zip'))
    assert workspace(a)['storage_used'] == 8
    sessions.clear_session(sid, owner)
    assert workspace(a)['storage_used'] == 2


def test_capture_archives_and_existing_account_inventory(authenticated_client, shared_kb):
    from governance.worker import process_job
    from agent.checkpointer import sync_store
    from agent.memory_files import namespace
    owner = os.environ['TEST_PLATFORM_USER']
    store = Store(client=shared_kb, owner_id=owner)
    job_id = upload(authenticated_client, b'# source\narchived body').json['task_id']
    job = store.get_job(job_id)
    process_job(store, job)
    capture = store.get_job(job_id)
    assert capture['status'] == 'completed', capture['message']
    assert Path(capture['zip_file']).is_file()
    disk = sum(p.stat().st_size for p in data_dir().rglob('*') if p.is_file())
    assert disk > 20 and workspace(authenticated_client)['storage_used'] == disk
    with sync_store() as native:
        native.put(namespace(owner, 'builtin-smart-reasoning'), '/note.txt', create_file_data('12345'))
    sid = sessions.create_session(owner_id=owner)['id']
    item = authenticated_client.post(f'/api/v1/sessions/{sid}/attachments', data={'file': (io.BytesIO(b'old'), 'image.png')})
    assert item.status_code == 200
    with connection() as conn:
        conn.execute('DELETE FROM workspace_storage WHERE principal_id=%s', (owner,))
        conn.execute('UPDATE platform_workspaces SET storage_indexed=false WHERE principal_id=%s', (owner,))
    assert workspace(authenticated_client)['storage_used'] == disk + 8
    with connection() as conn:
        assert conn.execute('SELECT storage_indexed FROM platform_workspaces WHERE principal_id=%s', (owner,)).fetchone()['storage_indexed']


def test_delegated_native_file_is_charged_to_parent_workspace(authenticated_client):
    from uuid import uuid4
    from deepagents import create_deep_agent
    from langchain_core.messages import AIMessage
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from langgraph.constants import CONFIG_KEY_CHECKPOINTER
    from agent.checkpointer import async_checkpointer, database_url
    from tests.test_platform_harness import Model, call

    owner = os.environ['TEST_PLATFORM_USER']
    parent = sessions.create_session(owner_id=owner)['id']
    async def run():
        model = Model(responses=[AIMessage(content='', tool_calls=[
            call('write_file', {'file_path':'/output.txt', 'content':'child bytes'})]), AIMessage(content='done')])
        async with async_checkpointer() as quota, AsyncPostgresSaver.from_conn_string(database_url()) as native:
            quota.parent_session_id = parent
            graph = create_deep_agent(model=model).with_config(configurable={CONFIG_KEY_CHECKPOINTER: quota})
            # Aegra attaches the service-wide saver after invoking the per-request graph factory.
            graph = graph.copy(update={'checkpointer': native})
            result = await graph.ainvoke({'messages': [{'role':'user', 'content':'save'}]},
                                         {'configurable': {'thread_id': str(uuid4())}}, durability='sync')
            assert result['files']['/output.txt']['content'] == 'child bytes'
    asyncio.run(run())
    assert workspace(authenticated_client)['storage_used'] == 11
    sessions.clear_session(parent, owner)
    assert workspace(authenticated_client)['storage_used'] == 0
