"""Legacy endpoints never run or repair execution; native sessions keep SDK persistence."""
import base64
import os
import subprocess
from pathlib import Path

import psycopg
import pytest
from psycopg.types.json import Jsonb
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, MessagesState, StateGraph

from agent import registry, sessions
from agent.checkpointer import make_checkpointer
from governance.database import connection


def legacy_session(owner):
    sid = sessions.create_session(owner_id=owner)['id']
    with connection() as conn:
        conn.execute("UPDATE agent_sessions SET agent_config='{}' WHERE id=%s", (sid,))
    return sid


def no_execution(*args, **kwargs):
    raise AssertionError('History must not start an executor or change saved records')


def test_retired_execution_routes_are_gone_without_creating_runtime_records(authenticated_client, monkeypatch):
    http = authenticated_client
    sid = legacy_session(os.environ['TEST_PLATFORM_USER'])
    monkeypatch.setattr(subprocess, 'Popen', no_execution)
    routes = [
        ('POST', '/api/agent/chat'), ('POST', '/api/v1/agent-chat'),
        ('POST', f'/api/v1/agent-chat/{sid}'), ('POST', f'/api/v1/knowledge-chat/{sid}'),
        ('POST', f'/api/v1/sessions/{sid}/stop'),
        ('GET', '/api/v1/sessions/continue-stream'), ('GET', f'/api/v1/sessions/continue-stream/{sid}'),
        ('POST', f'/api/v1/sessions/{sid}/steer'), ('DELETE', f'/api/v1/sessions/{sid}/steer/steer'),
        ('POST', f'/api/v1/sessions/{sid}/steer/steer/inject'),
        ('POST', f'/api/v1/sessions/{sid}/fork'), ('POST', f'/api/v1/sessions/{sid}/rewind'),
        ('POST', f'/api/v1/sessions/{sid}/background-work/job/cancel'),
        ('DELETE', '/api/v1/agent/grants/grant'),
        ('POST', '/api/v1/me/browser'), ('GET', '/api/v1/me/browser'),
        ('GET', f'/api/v1/sessions/{sid}/local-browser'), ('POST', f'/api/v1/sessions/{sid}/local-browser'),
        ('POST', f'/api/v1/sessions/{sid}/sandbox/terminal-ticket'),
        ('POST', '/api/v1/system/sandbox-check'), ('POST', '/api/v1/sandbox-configs'),
        ('PUT', '/api/v1/sandbox-configs/docker'), ('DELETE', '/api/v1/sandbox-configs/docker'),
        ('POST', '/api/v1/skills/catalog/catalog/install'),
        ('POST', '/api/v1/sandbox-configs/docker/skills'),
        ('PATCH', '/api/v1/sandbox-configs/docker/skills/install'),
        ('DELETE', '/api/v1/sandbox-configs/docker/skills/install'),
        ('POST', '/api/v1/sandbox-configs/docker/skills/install/reinstall'),
        ('POST', '/api/v1/sandbox-configs/docker/skills/install/stop'),
        ('POST', '/api/v1/sandbox-configs/docker/skills/install/guidance'),
        ('DELETE', f'/api/v1/sessions/{sid}'), ('DELETE', f'/api/v1/sessions/{sid}/messages'),
        ('PUT', f'/api/v1/sessions/{sid}'), ('POST', f'/api/v1/sessions/{sid}/pin'),
        ('POST', f'/api/v1/sessions/{sid}/generate_title'),
        ('DELETE', f'/api/v1/sessions/{sid}/messages/run/artifacts/0'),
        ('POST', f'/api/v1/sessions/{sid}/attachments'),
    ]
    for method, path in routes:
        response = http.open(path, method=method, json={})
        assert response.status_code == 410, (method, path, response.status_code, response.json)
    assert http.delete('/api/v1/artifacts').status_code == 400
    for path, status in [('/api/v1/agent/tool-approvals/pending', 400), ('/api/v1/agent/prompts/pending', 400),
                         ('/api/v1/agent/mcp-oauth-resolutions/pending', 501),
                         ('/api/v1/agent/mcp-oauth-resolutions/pending/cancel', 501)]:
        assert http.post(path, json={}).status_code == status
    with connection() as conn:
        for table in ('agent_runs', 'agent_run_events', 'agent_steers', 'runtime_records'):
            assert conn.execute(f'SELECT count(*) AS n FROM {table}').fetchone()['n'] == 0
        assert conn.execute('SELECT id FROM agent_sessions WHERE id=%s', (sid,)).fetchone()


def test_history_and_extension_gets_are_read_only_even_for_interrupted_workers(authenticated_client, monkeypatch):
    http = authenticated_client
    owner = os.environ['TEST_PLATFORM_USER']
    sid = legacy_session(owner)
    metadata = [{'index': 0, 'file_name': 'report.txt', 'source_path': '/report.txt', 'file_type': 'txt', 'file_size': 6}]
    sources = [{'path': '/report.txt', 'version_key': 'frozen', 'config_id': 'docker', 'workspace': {'volume': 'preserved-volume'}}]
    with connection() as conn:
        conn.execute("INSERT INTO agent_runs(id,session_id,owner_id,status,query,answer,artifacts_json,artifact_sources,updated_at) VALUES ('archived',%s,%s,'running','Question','Stored answer',%s,%s,now()-interval '1 day')", (sid, owner, Jsonb(metadata), Jsonb(sources)))
        conn.execute("UPDATE agent_sessions SET running_id='archived' WHERE id=%s", (sid,))
    registry.save_record('sandbox', {'id': 'docker', 'name': 'Saved Docker', 'sandbox_type': 'docker'}, owner)
    registry.save_record('sandbox_job', {'id': 'job', 'session_id': sid, 'config_id': 'docker', 'command': 'saved command', 'status': 'running'}, owner)
    registry.save_record('skill', {'id': 'catalog', 'name': 'saved', 'files': {'SKILL.md': 'saved text'}}, owner)
    registry.save_record('skill_install', {'id': 'install', 'catalog_id': 'catalog', 'sandbox_config_id': 'docker', 'status': 'installing', '_worker_epoch': 'old-process', 'install_message_id': 'archived'}, owner)
    with connection() as conn:
        before = {table: conn.execute(f'SELECT * FROM {table} ORDER BY id').fetchall() for table in ('agent_runs', 'agent_sessions', 'runtime_records')}
    monkeypatch.setattr(subprocess, 'Popen', no_execution)
    monkeypatch.setattr(registry, 'save_record', no_execution)
    assert http.get(f'/api/v1/messages/{sid}/load').json['data'][-1]['content'] == 'Stored answer'
    assert http.get(f'/api/v1/sessions/{sid}').json['data']['read_only'] is True
    assert http.get(f'/api/v1/sessions/{sid}/background-work').json['data'][0]['state'] == 'lost'
    assert http.get(f'/api/v1/sessions/{sid}/background-work/job').json['data']['result']['output_available'] is False
    assert http.get(f'/api/v1/sessions/{sid}/messages/archived/artifacts').json['data'] == metadata
    assert http.get(f'/api/v1/sessions/{sid}/messages/archived/artifacts/0/download').status_code == 410
    assert http.get(f'/api/v1/sessions/{sid}/artifacts').status_code == 200
    assert http.get('/api/v1/artifacts').status_code == 200
    assert http.get('/api/v1/sandbox-configs/docker/sandboxes').json['data']['unverifiable'] is True
    for path in ('/api/v1/skills/catalog', '/api/v1/skills/catalog/catalog',
                 '/api/v1/sandbox-configs/docker/skills', '/api/v1/sandbox-configs/docker/skills/install',
                 '/api/v1/sandbox-configs/docker/skills/install/guidance',
                 '/api/v1/sandbox-configs/docker/skills/install/files',
                 '/api/v1/sandbox-configs/docker/skills/install/install-events',
                 '/api/v1/sandbox-configs/docker/skills/install/transcript'):
        assert http.get(path).status_code == 200, path
    with connection() as conn:
        after = {table: conn.execute(f'SELECT * FROM {table} ORDER BY id').fetchall() for table in before}
    assert before == after


@pytest.mark.parametrize('has_queued', [False, True], ids=['empty', 'queued'])
def test_legacy_queued_steers_keep_items_and_data_contract_without_mutation(authenticated_client, has_queued):
    owner = os.environ['TEST_PLATFORM_USER']
    sid = legacy_session(owner)
    with connection() as conn:
        if has_queued:
            conn.execute("INSERT INTO agent_runs(id,session_id,owner_id,status) VALUES ('saved-run',%s,%s,'running')", (sid, owner))
            for identifier, status in [('queued-steer', 'queued'), ('delivered-steer', 'injected')]:
                conn.execute('''INSERT INTO agent_steers(id,session_id,owner_id,run_id,content,delivery,status)
                    VALUES (%s,%s,%s,'saved-run','Saved follow-up','after',%s)''', (identifier, sid, owner, status))
        before = conn.execute('SELECT * FROM agent_steers ORDER BY id').fetchall()
    response = authenticated_client.get(f'/api/v1/sessions/{sid}/steer')
    assert response.status_code == 200, response.json
    body = response.json
    assert body['success'] is True and body['read_only'] is True
    assert body['items'] == body['data']
    assert [item['steer_id'] for item in body['items']] == (['queued-steer'] if has_queued else [])
    if has_queued:
        assert body['items'][0]['content'] == 'Saved follow-up'
        assert body['items'][0]['expected_assistant_message_id'] == 'saved-run'
    with connection() as conn:
        assert conn.execute('SELECT * FROM agent_steers ORDER BY id').fetchall() == before


def test_session_metadata_and_native_clear_delete_obey_stream_lock(authenticated_client):
    http = authenticated_client
    owner = os.environ['TEST_PLATFORM_USER']
    created = http.post('/api/v1/sessions', json={'title': 'Native', 'agent_config': {'runtime': 'legacy'}}).json['data']
    sid = created['id']
    assert created['runtime'] == 'deepagents' and created['agent_config']['runtime'] == 'deepagents'
    assert http.put(f'/api/v1/sessions/{sid}', json={'title': 'Renamed'}).json['data']['title'] == 'Renamed'
    assert http.post(f'/api/v1/sessions/{sid}/pin').status_code == 200
    builder = StateGraph(MessagesState)
    builder.add_node('answer', lambda state: {'messages': [AIMessage('Native answer')]})
    builder.add_edge(START, 'answer'); builder.add_edge('answer', END)
    config = {'configurable': {'thread_id': sid}}
    with make_checkpointer() as saver:
        graph = builder.compile(checkpointer=saver)
        graph.invoke({'messages': [HumanMessage('Question')]}, config)
    with psycopg.connect(os.environ['AGENT_DATABASE_URL'], autocommit=True) as lock:
        assert lock.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0))', ('harness:' + sid,)).fetchone()[0]
        assert http.delete(f'/api/v1/sessions/{sid}/messages').status_code == 409
        assert http.delete(f'/api/v1/sessions/{sid}').status_code == 409
    assert len(sessions.read_messages(sid, owner_id=owner)) == 2
    assert http.delete(f'/api/v1/sessions/{sid}/messages').status_code == 200
    assert sessions.read_messages(sid, owner_id=owner) == []
    with connection() as conn:
        for table in ('agent_runs', 'agent_run_events', 'agent_steers'):
            assert conn.execute(f'SELECT count(*) AS n FROM {table}').fetchone()['n'] == 0
    assert http.delete(f'/api/v1/sessions/{sid}').status_code == 200
    assert http.get(f'/api/v1/sessions/{sid}').status_code == 404


def test_static_skill_catalog_crud_never_installs_and_preserves_referenced_history(authenticated_client, monkeypatch):
    http = authenticated_client
    owner = os.environ['TEST_PLATFORM_USER']
    monkeypatch.setattr(subprocess, 'Popen', no_execution)
    payload = {'files': {'SKILL.md': '---\nname: content-only\ndescription: Instructions\n---\nRead the reference.',
                         'run.py': 'raise RuntimeError("must not execute")'}}
    uploaded = http.post('/api/v1/skills/catalog', json=payload)
    assert uploaded.status_code == 201, uploaded.json
    item = uploaded.json['data']
    assert item['execution_mode'] == 'native_middleware' and item['dependency_status'] == 'not_managed'
    base = '/api/v1/skills/catalog/' + item['id']
    assert http.get(base + '/files/content?path=run.py').json['data']['content'] == payload['files']['run.py']
    assert registry.records('skill_install', owner) == []
    assert sessions.list_sessions(owner_id=owner) == []
    assert http.post(base + '/install', json={'sandbox_config_ids': ['state-backend']}).status_code == 410
    assert http.delete(base).status_code == 200
    assert http.get(base).status_code == 404
    second = http.post('/api/v1/skills/catalog', json=payload).json['data']
    registry.save_record('skill_install', {'id': 'preserved', 'catalog_id': second['id'], 'sandbox_config_id': 'docker', 'status': 'ready'}, owner)
    assert http.delete('/api/v1/skills/catalog/' + second['id']).status_code == 409
    assert registry.record('skill_install', 'preserved', owner)['status'] == 'ready'
    assert http.post('/api/v1/skills/catalog', json=payload).status_code == 409
    with connection() as conn:
        conn.execute("UPDATE platform_users SET role='viewer' WHERE id=%s", (owner,))
    assert http.post('/api/v1/skills/catalog', json=payload).status_code == 403


def test_archive_ownership_and_no_registered_browser_or_terminal_routes(authenticated_client):
    from asgi import create_app
    from starlette.routing import WebSocketRoute
    from webapi.auth import create_user
    owner = create_user('other-archive@example.com', 'Other', 'test-password-123', 'admin')
    sid = legacy_session(owner)
    for path in (f'/api/v1/sessions/{sid}', f'/api/v1/messages/{sid}/load',
                 f'/api/v1/sessions/{sid}/artifacts', f'/api/v1/sessions/{sid}/background-work'):
        assert authenticated_client.get(path).status_code == 404
    retired = [
        ('POST', f'/api/v1/sessions/{sid}/stop'),
        ('POST', f'/api/v1/agent-chat/{sid}'), ('POST', f'/api/v1/knowledge-chat/{sid}'),
        ('GET', f'/api/v1/sessions/continue-stream/{sid}'),
        ('POST', f'/api/v1/sessions/{sid}/steer'),
        ('DELETE', f'/api/v1/sessions/{sid}/steer/steer'),
        ('POST', f'/api/v1/sessions/{sid}/steer/steer/inject'),
        ('POST', f'/api/v1/sessions/{sid}/fork'), ('POST', f'/api/v1/sessions/{sid}/rewind'),
        ('POST', f'/api/v1/sessions/{sid}/background-work/job/cancel'),
        ('GET', f'/api/v1/sessions/{sid}/local-browser'),
        ('POST', f'/api/v1/sessions/{sid}/local-browser'),
        ('POST', f'/api/v1/sessions/{sid}/sandbox/terminal-ticket'),
        ('DELETE', f'/api/v1/sessions/{sid}/messages/run/artifacts/0'),
    ]
    for method, path in retired:
        response = authenticated_client.open(path, method=method, json={})
        assert response.status_code == 404, (method, path, response.status_code)
    for path in ('/api/agent/chat', '/api/v1/agent-chat'):
        assert authenticated_client.post(path, json={'session_id': sid}).status_code == 404
        assert authenticated_client.post(path, json={'session_id': 42}).status_code == 400
    assert authenticated_client.delete('/api/v1/artifacts', query_string={'session_id': sid}).status_code == 404
    assert [route.path for route in create_app().routes if isinstance(route, WebSocketRoute)] == [
        '/api/v1/sessions/{session_id}/sandbox/terminal']
    root = Path(__file__).parents[1]
    for filename in ('service', 'events', 'browser', 'skill_runtime', 'terminal'):
        assert not (root / 'agent' / f'{filename}.py').exists()


@pytest.mark.parametrize('content,encoding,expected', [
    ('保留报告', 'utf-8', '保留报告'.encode()),
    (['line one', 'line two'], 'utf-8', b'line one\nline two'),
    (base64.b64encode(b'\x00\xff\x89PNG').decode('ascii'), 'base64', b'\x00\xff\x89PNG'),
])
def test_archived_state_file_download_reads_published_checkpoint_without_reindexing(authenticated_client, content, encoding, expected):
    from deepagents.backends.utils import create_file_data
    from deepagents.middleware.filesystem import FilesystemState
    from agent.artifacts import artifact_key
    owner = os.environ['TEST_PLATFORM_USER']
    sid = legacy_session(owner)
    item = create_file_data(content, encoding=encoding)
    builder = StateGraph(FilesystemState)
    builder.add_node('write', lambda state: {'files': {'/report.txt': item}})
    builder.add_edge(START, 'write'); builder.add_edge('write', END)
    config = {'configurable': {'thread_id': sid}}
    with make_checkpointer() as saver:
        graph = builder.compile(checkpointer=saver)
        graph.invoke({}, config)
        checkpoint = graph.get_state(config).config['configurable']['checkpoint_id']
    metadata = [{'index': 0, 'source_path': '/report.txt', 'file_name': 'report.txt', 'file_type': 'txt'}]
    source = {'path': '/report.txt', 'checkpoint_id': checkpoint,
              'version_key': artifact_key(sid, '/report.txt', item).split(':', 1)[1]}
    with make_checkpointer() as saver, connection() as conn:
        conn.execute("INSERT INTO agent_runs(id,session_id,owner_id,status,artifacts_json,artifact_sources) VALUES ('files',%s,%s,'completed',%s,%s)",
                     (sid, owner, Jsonb(metadata), Jsonb([source])))
        before = conn.execute("SELECT * FROM agent_runs WHERE id='files'").fetchone()
        count = saver.conn.execute('SELECT count(*) AS n FROM checkpoints').fetchone()['n']
    response = authenticated_client.get(f'/api/v1/sessions/{sid}/messages/files/artifacts/0/download')
    assert response.status_code == 200 and response.data == expected
    with make_checkpointer() as saver, connection() as conn:
        assert conn.execute("SELECT * FROM agent_runs WHERE id='files'").fetchone() == before
        assert saver.conn.execute('SELECT count(*) AS n FROM checkpoints').fetchone()['n'] == count


@pytest.mark.parametrize('item', [{'content': '%%%', 'encoding': 'base64'}, {'content': 'text', 'encoding': 'unknown'}])
def test_archived_file_download_rejects_invalid_encoding(monkeypatch, item):
    from agent import artifacts
    from governance.store import StoreError
    monkeypatch.setattr(artifacts, 'deleted_for', lambda *args: {})
    with pytest.raises(StoreError, match='编码无效') as error:
        artifacts.download('owner', 'session', '/file.bin', item)
    assert error.value.status == 409


def test_native_file_memory_does_not_run_or_modify_legacy_structured_memory(authenticated_client, monkeypatch):
    owner = os.environ['TEST_PLATFORM_USER']
    for kind in ('memory', 'memory_job', 'memory_topic', 'settings'):
        registry.save_record(kind, {'id': 'memory-config' if kind == 'settings' else 'saved-' + kind,
            'value': {'enabled': True}, 'status': 'pending', 'content': 'Preserved historical data'}, owner)
    with connection() as conn:
        before = conn.execute('SELECT * FROM runtime_records ORDER BY id').fetchall()
    monkeypatch.setattr('integrations.contextdb.ContextDBClient._request', no_execution)
    monkeypatch.setattr(subprocess, 'Popen', no_execution)
    personal = authenticated_client.get('/api/v1/memory/settings')
    assert personal.status_code == 200 and personal.json['data']['workspace_enabled'] is True
    assert personal.json['data']['effective'] is True and personal.json['data']['item_count'] == 0
    assert personal.json['data']['storage_mode'] == 'agents_md'
    assert personal.json['data']['structured_memory_supported'] is False
    workspace = authenticated_client.get('/api/v1/tenants/kv/memory-config')
    assert workspace.status_code == 200 and workspace.json['data']['enabled'] is True
    assert workspace.json['data']['supported'] is True
    assert authenticated_client.put('/api/v1/tenants/kv/memory-config', json={'enabled': True, 'write_mode': 'auto'}).status_code == 501
    for method, path in [('GET', '/api/v1/memory/items'), ('POST', '/api/v1/memory/items'),
                         ('DELETE', '/api/v1/memory/items/saved'), ('POST', '/api/v1/memory/consolidate'),
                         ('GET', '/api/v1/memory/topics'), ('GET', '/api/v1/memory/export')]:
        response = authenticated_client.open(path, method=method, json={})
        assert response.status_code == 501, (method, path, response.status_code)
    with connection() as conn:
        assert conn.execute('SELECT * FROM runtime_records ORDER BY id').fetchall() == before
    root = Path(__file__).parents[1]
    assert not (root / 'agent/memory_runtime.py').exists()
    assert not (root / 'webapi/memory.py').exists()


def test_capabilities_match_native_harness_and_disabled_extensions(authenticated_client):
    capabilities = authenticated_client.get('/api/v1/system/capabilities').json['data']['capabilities']
    for key in ('agents', 'settings.mcp', 'settings.sandbox', 'settings.sandbox.state'):
        assert capabilities[key]['supported'] is True
    for key in ('organizations', 'settings.assistant', 'settings.websearch', 'settings.sandbox.docker', 'settings.sandbox.host',
                'settings.sandbox.remote', 'settings.sandbox.user_allocation', 'agents.steering', 'agents.browser'):
        assert capabilities[key]['supported'] is False
