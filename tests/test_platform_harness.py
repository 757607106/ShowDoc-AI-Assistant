"""The HTTP adapter against real Deep Agents, PostgreSQL checkpoints and auth."""
import asyncio
import base64
import io
import json
import os
from datetime import datetime

import psycopg
import pytest
from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from langchain.agents.middleware import TodoListMiddleware
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from starlette.testclient import TestClient

from agent import sessions
from governance.database import connection


class Model(FakeMessagesListChatModel):
    def bind_tools(self, *args, **kwargs):
        return self


def call(name, args, identifier='tool-1'):
    return {'name': name, 'args': args, 'id': identifier, 'type': 'tool_call'}


def frames(response):
    assert response.status_code == 200, response.text
    events = []
    for frame in response.text.replace('\r\n', '\n').split('\n\n'):
        lines = frame.splitlines()
        kind = next((line[7:] for line in lines if line.startswith('event: ')), None)
        data = next((line[6:] for line in lines if line.startswith('data: ')), None)
        if kind and data:
            events.append((kind, json.loads(data)))
    return events


@pytest.fixture
def original_prepare(monkeypatch):
    monkeypatch.setattr('agent.sandbox.enabled', lambda: True)
    monkeypatch.setattr('webapi.chat_resources._parse_attachment', lambda name, content: content.decode('utf-8'))
    from webapi.harness import _prepare
    return _prepare


@pytest.fixture
def harness(monkeypatch, authenticated_client, original_prepare):
    from asgi import create_app
    from webapi import harness as api
    import app as app_module

    monkeypatch.setenv('FLASK_SECRET_KEY', app_module.app.secret_key)
    model = Model(responses=[AIMessage(content='官方 Harness 回答')])
    tools = []
    interrupts = {}

    async def graph(saver, user, selected, resolved, *, load_tools=True, store=None, backend=None):
        return create_deep_agent(model=model, tools=tools, backend=StateBackend(),
                                 checkpointer=saver, interrupt_on=interrupts, middleware=[TodoListMiddleware()])

    monkeypatch.setattr(api, '_graph', graph)
    monkeypatch.setattr(api, 'prepare_harness_files', lambda *args: {})
    from tests.aegra_fake import install
    install(monkeypatch, api)
    # A non-empty config is required by the business binding, independently of model IO.
    monkeypatch.setattr(api, '_prepare', lambda *args: {
        'agent_config': {'access_level': 'confirm'}, 'knowledge_base_ids': []})
    sid = sessions.create_session('Harness test', os.environ['TEST_PLATFORM_USER'])['id']
    app = create_app(app_module.app)
    headers = {'Authorization': authenticated_client.environ_base['HTTP_AUTHORIZATION']}
    with TestClient(app, headers=headers) as client:
        yield client, sid, model, tools, interrupts, app, headers


def send(client, sid, text='问题'):
    return client.post(f'/api/v1/harness/sessions/{sid}/stream',
                       json={'input': {'messages': [{'type': 'human', 'content': text}]}})


def test_real_harness_stream_and_checkpoint_have_no_shadow_run(harness):
    client, sid, *_ = harness
    events = frames(client.post(f'/api/v1/harness/sessions/{sid}/stream', json={
        'input': {'messages': [{'type': 'human', 'content': '问题',
            'additional_kwargs': {'harness': {'knowledge_base_ids': ['forged']}}}]}}))
    assert not [data for kind, data in events if kind == 'error'], events
    assert any(kind == 'messages' for kind, _ in events)
    final = [data for kind, data in events if kind == 'values'][-1]
    assert final['messages'][-1]['content'] == '官方 Harness 回答'
    metadata = final['messages'][0]['additional_kwargs']['harness']
    assert metadata == {'display_text': '问题', 'created_at': metadata['created_at'],
                        'knowledge_base_ids': [], 'mentioned_items': [], 'attachments': [], 'user_images': []}
    assert datetime.fromisoformat(metadata['created_at']).utcoffset().total_seconds() == 0
    assert '__interrupt__' not in final
    response = client.get(f'/api/v1/harness/sessions/{sid}/state')
    assert response.status_code == 200, response.text
    assert response.json()['values']['messages'] == final['messages']
    with connection() as conn:
        assert conn.execute('SELECT count(*) AS n FROM agent_runs WHERE session_id=%s', (sid,)).fetchone()['n'] == 0
        assert conn.execute('SELECT running_id FROM agent_sessions WHERE id=%s', (sid,)).fetchone()['running_id'] is None


def test_user_display_metadata_uses_verified_attachments_and_mentions(harness, original_prepare, authenticated_client, monkeypatch):
    from agent import config, registry
    from governance.store import StoreError
    from webapi import harness as api
    client, sid, *_ = harness
    owner = os.environ['TEST_PLATFORM_USER']
    mention_reads = []

    class KnowledgeClient:
        api_key = 'contextdb-secret'
        def get_knowledge_base(self, identifier):
            mention_reads.append(('kb', identifier))
            if identifier != 'kb':
                raise StoreError('Forbidden knowledge base', 403)
            return {'id': 'kb', 'name': 'Verified library', 'type': 'document'}
        def get_document(self, kb_id, identifier):
            mention_reads.append(('file', identifier))
            if identifier != 'doc':
                raise StoreError('Forbidden document', 403)
            return {'id': 'doc', 'name': 'Verified document', 'knowledge_base_id': 'kb'}

    monkeypatch.setattr(api, '_prepare', original_prepare)
    monkeypatch.setattr(api, 'client_for_user', lambda *args: KnowledgeClient())
    vision = registry.save_model({'name': 'Vision fixture', 'type': 'VLLM',
        'parameters': {'base_url': 'https://fixture.invalid/v1', 'api_key': 'model-secret'}}, owner)
    service = registry.save_mcp({'name': 'Verified MCP', 'transport_type': 'http-streamable',
        'url': 'https://mcp.invalid/mcp', 'auth_config': {'auth_type': 'bearer', 'token': 'mcp-secret'}}, owner)
    registry.save_skill('guide', {'SKILL.md': '---\nname: guide\ndescription: Guidance\n---\nRead sources'}, owner)
    agent = config.save_agent({'name': 'Display fixture', 'config': {
        'kb_selection_mode': 'none', 'image_upload_enabled': True, 'vlm_model_id': vision['id'],
        'mcp_selection_mode': 'selected', 'mcp_services': [service['id']],
        'skills_selection_mode': 'selected', 'selected_skills': ['guide']}}, owner)
    uploaded = authenticated_client.post(f'/api/v1/sessions/{sid}/attachments',
        data={'file': (io.BytesIO('附件原文'.encode()), '说明.txt')}).json['data']
    png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6HqkAAAAASUVORK5CYII=')
    picture = authenticated_client.post(f'/api/v1/sessions/{sid}/attachments',
        data={'file': (io.BytesIO(png), 'picture.png')}).json['data']
    mentions = [{'id': 'kb', 'type': 'kb', 'name': 'Forged library', 'api_key': 'client-secret'},
                {'id': 'doc', 'type': 'file', 'name': 'Forged document'},
                {'id': service['id'], 'type': 'mcp', 'name': 'Forged MCP'},
                {'id': 'catalog-id', 'skill_name': 'guide', 'type': 'skill', 'name': 'Forged skill'},
                {'id': 'unknown', 'type': 'runtime', 'name': 'Unverified'}]
    context = {'agent_id': agent['id'], 'attachment_ids': [uploaded['id'], picture['id']],
               'mcp_service_ids': [service['id']], 'skill_names': ['guide'], 'mentioned_items': mentions * 2,
               'attachments': [{'id': 'forged', 'path': '/private/secret'}],
               'user_images': [{'url': 'https://untrusted.invalid/image'}]}
    with connection() as conn:
        before = conn.execute('SELECT * FROM runtime_records ORDER BY id').fetchall()
    text = '  请解释附件与图片  '
    response = client.post(f'/api/v1/harness/sessions/{sid}/stream', json={
        'context': context, 'input': {'messages': [{'type': 'human', 'content': text,
            'additional_kwargs': {'harness': {'display_text': 'Forged text', 'created_at': 'forged',
                'api_key': 'client-secret', 'attachments': [{'id': 'forged'}]}}}]}})
    events = frames(response)
    assert not [value for kind, value in events if kind == 'error'], events
    values = [value for kind, value in events if kind == 'values'][-1]
    human = next(message for message in values['messages'] if message['type'] == 'human')
    metadata = human['additional_kwargs']['harness']
    assert metadata['display_text'] == text
    assert datetime.fromisoformat(metadata['created_at']).utcoffset().total_seconds() == 0
    assert metadata['knowledge_base_ids'] == ['kb']
    assert metadata['attachments'] == [{key: uploaded[key] for key in
        ('id', 'file_name', 'file_size', 'file_type', 'mime_type', 'status')}]
    image_url = f'/api/v1/sessions/{sid}/attachments/{picture["id"]}/preview'
    assert metadata['user_images'] == [{'id': picture['id'], 'url': image_url, 'file_name': 'picture.png'}]
    assert metadata['mentioned_items'] == [
        {'id': 'kb', 'type': 'kb', 'name': 'Verified library', 'kb_type': 'document'},
        {'id': 'doc', 'type': 'file', 'name': 'Verified document'},
        {'id': service['id'], 'type': 'mcp', 'name': 'Verified MCP'},
        {'id': 'guide', 'type': 'skill', 'name': 'guide'}]
    # Once for authorization, once for the display name, regardless of repeats.
    assert mention_reads.count(('kb', 'kb')) == 2
    assert mention_reads.count(('file', 'doc')) == 2
    assert human['content'][0] == {'type': 'text', 'text': text}
    assert any(block.get('type') == 'image_url' for block in human['content'])
    assert any('read_file' in block.get('text', '') for block in human['content'])
    assert 'read_file' not in metadata['display_text']
    assert not any(secret in json.dumps(metadata) for secret in
                   ('model-secret', 'contextdb-secret', 'mcp-secret', 'client-secret', '/private/secret'))
    restored = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']
    assert restored['messages'] == values['messages']
    assert authenticated_client.get(image_url).data == png
    assert authenticated_client.get(f'/api/v1/sessions/{sid}/attachments/{uploaded["id"]}/preview').data == '附件原文'.encode()
    with connection() as conn:
        rows = conn.execute('SELECT * FROM runtime_records ORDER BY id').fetchall()
        assert [row for row in rows if row['kind'] != 'main_run'] == before
        assert conn.execute('SELECT count(*) AS n FROM agent_runs WHERE session_id=%s', (sid,)).fetchone()['n'] == 0


def test_foreign_session_attachment_cannot_create_user_metadata(harness, original_prepare, authenticated_client, monkeypatch):
    from types import SimpleNamespace
    from webapi import harness as api
    client, sid, *_ = harness
    monkeypatch.setattr(api, '_prepare', original_prepare)
    monkeypatch.setattr(api, 'client_for_user', lambda *args: SimpleNamespace(
        api_key='fixture', list_knowledge_bases=lambda **kwargs: {'knowledge_bases': [], 'total': 0}))
    other_sid = sessions.create_session('Other attachment session', os.environ['TEST_PLATFORM_USER'])['id']
    uploaded = authenticated_client.post(f'/api/v1/sessions/{other_sid}/attachments',
        data={'file': (io.BytesIO(b'Other session data'), 'private.txt')}).json['data']
    with connection() as conn:
        before = conn.execute('SELECT * FROM runtime_records ORDER BY id').fetchall()
    response = client.post(f'/api/v1/harness/sessions/{sid}/stream', json={
        'context': {'attachment_ids': [uploaded['id']]},
        'input': {'messages': [{'type': 'human', 'content': 'Read private attachment'}]}})
    assert response.status_code == 404
    assert client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']['messages'] == []
    with connection() as conn:
        rows = conn.execute('SELECT * FROM runtime_records ORDER BY id').fetchall()
        assert [row for row in rows if row['kind'] != 'main_run'] == before
        assert conn.execute('SELECT count(*) AS n FROM agent_runs WHERE session_id=%s', (sid,)).fetchone()['n'] == 0


def test_embedded_assistant_search_permission_uses_agent_config(harness, original_prepare, monkeypatch):
    from types import SimpleNamespace
    from webapi import harness as api
    client, sid, *_ = harness
    monkeypatch.setattr(api, '_prepare', original_prepare)
    monkeypatch.setattr(api, 'client_for_user', lambda *args: SimpleNamespace(
        api_key='fixture', list_knowledge_bases=lambda **kwargs: {'knowledge_bases': [], 'total': 0}))
    response = client.post(f'/api/v1/harness/sessions/{sid}/stream', json={
        'context': {'agent_id': 'builtin-weknora-assistant', 'web_search_enabled': True},
        'input': {'messages': [{'type': 'human', 'content': '页面助手问题'}]}})
    events = frames(response)
    assert not [value for kind, value in events if kind == 'error'], events
    assert [value for kind, value in events if kind == 'values'][-1]['messages'][-1]['content'] == '官方 Harness 回答'
    saved = sessions.get_session(sid, os.environ['TEST_PLATFORM_USER'])['agent_config']['agent_config']
    assert saved['web_search_enabled'] is False


@pytest.mark.parametrize('decision', ['approve', 'reject', 'edit'])
def test_native_file_approval_resume_and_duplicate_rejection(harness, decision):
    client, sid, model, _, approvals, *_ = harness
    model.responses = [AIMessage(content='', tool_calls=[call('write_file', {'file_path': '/draft.txt', 'content': 'original'})]),
                       AIMessage(content='处理完成')]
    approvals['write_file'] = {'allowed_decisions': ['approve', 'reject', 'edit']}
    events = frames(send(client, sid))
    assert not [value for kind, value in events if kind == 'error'], events
    state = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']
    user_metadata = state['messages'][0]['additional_kwargs']
    pending = state['__interrupt__']
    assert len(pending) == 1
    assert '/draft.txt' not in state.get('files', {})
    value = {'type': decision}
    if decision == 'edit':
        value['edited_action'] = {'name': 'write_file', 'args': {'file_path': '/draft.txt', 'content': 'edited'}}
    elif decision == 'reject':
        value['message'] = '不写入'
    body = {'input': None, 'command': {'resume': {pending[0]['id']: {'decisions': [value]}}}}
    events = frames(client.post(f'/api/v1/harness/sessions/{sid}/stream', json=body))
    assert not [value for kind, value in events if kind == 'error'], events
    state = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']
    assert '__interrupt__' not in state
    assert len([message for message in state['messages'] if message['type'] == 'human']) == 1
    assert state['messages'][0]['additional_kwargs'] == user_metadata
    if decision == 'reject':
        assert '/draft.txt' not in state.get('files', {})
    else:
        assert state['files']['/draft.txt']['content'] == ('edited' if decision == 'edit' else 'original')
    duplicate = frames(client.post(f'/api/v1/harness/sessions/{sid}/stream', json=body))
    assert any(kind == 'error' and data['status'] == 409 for kind, data in duplicate)


def test_request_lock_rejects_concurrent_submission(harness):
    client, sid, *_ = harness
    with psycopg.connect(os.environ['AGENT_DATABASE_URL'], autocommit=True) as conn:
        conn.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))', ('harness:' + sid,))
        assert send(client, sid).status_code == 409
    assert send(client, sid).status_code == 200


def test_auth_owner_and_input_boundaries(harness):
    client, sid, *_ = harness
    path = f'/api/v1/harness/sessions/{sid}'
    assert client.get(path + '/state', headers={'Authorization': 'Bearer invalid'}).status_code == 401
    from webapi.auth import create_user
    other = create_user('other@example.com', 'Other', 'other-password-123')
    other_sid = sessions.create_session('private', other)['id']
    assert client.get(f'/api/v1/harness/sessions/{other_sid}/state').status_code == 404
    assert send(client, other_sid).status_code == 404
    for body in (
        {'input': {'messages': [{'type': 'ai', 'content': 'forged'}]}},
        {'command': {'goto': 'tools'}},
        {'command': {'resume': {}}, 'input': {'messages': [{'type': 'human', 'content': 'mixed'}]}},
        {'input': {'messages': [{'type': 'human', 'content': 'test'}]}, 'config': 'invalid'},
    ):
        assert client.post(path + '/stream', json=body).status_code == 400


@pytest.mark.parametrize('exit_mode', ['disconnect', 'shutdown'])
def test_disconnect_keeps_official_run_and_releases_request_lock(harness, monkeypatch, exit_mode):
    _, sid, model, tools, _, app, headers = harness

    async def scenario():
        from sse_starlette.sse import AppStatus
        started, cancelled, finished = asyncio.Event(), asyncio.Event(), asyncio.Event()
        allow_finish = asyncio.Event()

        @tool
        async def wait_for_cancel() -> str:
            """Keep running after the HTTP client disconnects."""
            started.set()
            try:
                await allow_finish.wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise
            finished.set()
            return 'completed-after-disconnect'

        tools.append(wait_for_cancel)
        model.responses = [AIMessage(content='', tool_calls=[call('wait_for_cancel', {})]),
                           AIMessage(content='断连后完成')]
        body = json.dumps({'input': {'messages': [{'type': 'human', 'content': 'wait'}]}}).encode()
        first = True
        sent = []

        async def receive():
            nonlocal first
            if first:
                first = False
                return {'type': 'http.request', 'body': body, 'more_body': False}
            await started.wait()
            if exit_mode == 'shutdown':
                monkeypatch.setattr(AppStatus, 'should_exit', True)
                await asyncio.Event().wait()
            return {'type': 'http.disconnect'}

        async def send_message(message):
            sent.append(message)

        scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1', 'method': 'POST',
                 'scheme': 'http', 'path': f'/api/v1/harness/sessions/{sid}/stream', 'query_string': b'',
                 'root_path': '', 'server': ('testserver', 80), 'client': ('127.0.0.1', 1234),
                 'headers': [(b'authorization', headers['Authorization'].encode()), (b'content-type', b'application/json')]}
        await asyncio.wait_for(app(scope, receive, send_message), timeout=10)
        # The official run is detached from the HTTP connection: the tool is not cancelled.
        assert not cancelled.is_set(), sent
        allow_finish.set()
        await asyncio.wait_for(finished.wait(), timeout=5)
        deadline = asyncio.get_running_loop().time() + 5
        content = ''
        while asyncio.get_running_loop().time() < deadline:
            from agent.checkpointer import async_checkpointer
            async with async_checkpointer() as saver:
                graph = create_deep_agent(model=model, tools=tools, checkpointer=saver)
                state = await graph.aget_state({'configurable': {'thread_id': sid}})
            content = state.values['messages'][-1].content if state.values['messages'] else ''
            if content == '断连后完成':
                break
            await asyncio.sleep(0.02)
        assert content == '断连后完成', state.values['messages']

    asyncio.run(scenario())
    with psycopg.connect(os.environ['AGENT_DATABASE_URL'], autocommit=True) as conn:
        assert conn.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0))', ('harness:' + sid,)).fetchone()[0]


def _stream_scope(sid, headers):
    return {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1', 'method': 'POST',
            'scheme': 'http', 'path': f'/api/v1/harness/sessions/{sid}/stream', 'query_string': b'',
            'root_path': '', 'server': ('testserver', 80), 'client': ('127.0.0.1', 1234),
            'headers': [(b'authorization', headers['Authorization'].encode()), (b'content-type', b'application/json')]}


def test_header_send_failure_releases_lock_before_events_start(harness, monkeypatch):
    from webapi import harness as api
    _, sid, _, _, _, app, headers = harness
    graph_started = False
    native_graph = api._graph

    async def graph(*args, **kwargs):
        nonlocal graph_started
        graph_started = True
        return await native_graph(*args, **kwargs)

    monkeypatch.setattr(api, '_graph', graph)

    class HeaderSendError(RuntimeError):
        pass

    async def scenario():
        body = json.dumps({'input': {'messages': [{'type': 'human', 'content': 'header failure'}]}}).encode()
        first = True

        async def receive():
            nonlocal first
            if first:
                first = False
                return {'type': 'http.request', 'body': body, 'more_body': False}
            await asyncio.Event().wait()

        async def send_message(message):
            assert message['type'] == 'http.response.start' and message['status'] == 200
            raise HeaderSendError('client closed before response headers')

        existing_tasks = asyncio.all_tasks()
        with pytest.raises(HeaderSendError, match='before response headers'):
            await asyncio.wait_for(app(_stream_scope(sid, headers), receive, send_message), timeout=5)
        from sse_starlette.sse import _shutdown_watcher
        # The SDK owns one server shutdown watcher per event loop.
        assert all(task.get_coro().cr_code is _shutdown_watcher.__code__
                   for task in asyncio.all_tasks() - existing_tasks)

    asyncio.run(scenario())
    assert not graph_started
    with psycopg.connect(os.environ['AGENT_DATABASE_URL'], autocommit=True) as conn:
        assert conn.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0))', ('harness:' + sid,)).fetchone()[0]
        assert conn.execute('SELECT count(*) FROM checkpoints WHERE thread_id=%s', (sid,)).fetchone()[0] == 0


def test_disconnect_immediately_after_body_releases_lock_without_execution(harness):
    _, sid, model, tools, _, app, headers = harness
    tool_calls = []

    @tool
    async def unexpected_execution() -> str:
        """Record a tool invocation that must not outlive an already closed request."""
        tool_calls.append('called')
        return 'unexpected'

    tools.append(unexpected_execution)
    model.responses = [AIMessage(content='', tool_calls=[call('unexpected_execution', {})])]

    async def scenario():
        body = json.dumps({'input': {'messages': [{'type': 'human', 'content': 'disconnect'}]}}).encode()
        first, disconnected = True, False

        async def receive():
            nonlocal first, disconnected
            if first:
                first = False
                return {'type': 'http.request', 'body': body, 'more_body': False}
            disconnected = True
            return {'type': 'http.disconnect'}

        async def send_message(message):
            pass

        existing_tasks = asyncio.all_tasks()
        await asyncio.wait_for(app(_stream_scope(sid, headers), receive, send_message), timeout=5)
        assert disconnected
        assert tool_calls == []
        from sse_starlette.sse import _shutdown_watcher
        # The SDK owns one server shutdown watcher per event loop.
        assert all(task.get_coro().cr_code is _shutdown_watcher.__code__
                   for task in asyncio.all_tasks() - existing_tasks)

    asyncio.run(scenario())
    with psycopg.connect(os.environ['AGENT_DATABASE_URL'], autocommit=True) as conn:
        assert conn.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0))', ('harness:' + sid,)).fetchone()[0]
    with connection() as conn:
        assert conn.execute('SELECT count(*) AS n FROM agent_runs WHERE session_id=%s', (sid,)).fetchone()['n'] == 0


@pytest.mark.parametrize('missing_decision', [False, True])
def test_native_multi_file_approval_requires_complete_decisions(harness, missing_decision):
    client, sid, model, _, approvals, *_ = harness
    model.responses = [AIMessage(content='', tool_calls=[
        call('write_file', {'file_path': '/approved.txt', 'content': 'approved content'}, 'write-approved'),
        call('write_file', {'file_path': '/rejected.txt', 'content': 'rejected content'}, 'write-rejected'),
    ]), AIMessage(content='两项审批已处理')]
    approvals['write_file'] = {'allowed_decisions': ['approve', 'reject', 'edit']}
    initial = frames(send(client, sid))
    assert not [value for kind, value in initial if kind == 'error'], initial
    state_url = f'/api/v1/harness/sessions/{sid}/state'
    state = client.get(state_url).json()['values']
    pending = state['__interrupt__']
    assert len(pending) == 1
    actions = pending[0]['value']['action_requests']
    assert [action['args']['file_path'] for action in actions] == ['/approved.txt', '/rejected.txt']
    assert state.get('files', {}) == {}
    decisions = [{'type': 'approve'}, {'type': 'reject', 'message': '不要创建第二个文件'}]
    body = {'command': {'resume': {pending[0]['id']: {'decisions': decisions[:1] if missing_decision else decisions}}}}
    events = frames(client.post(f'/api/v1/harness/sessions/{sid}/stream', json=body))
    state = client.get(state_url).json()['values']
    assert len([message for message in state['messages'] if message['type'] == 'human']) == 1
    if missing_decision:
        errors = [data for kind, data in events if kind == 'error']
        assert len(errors) == 1
        assert errors[0]['status'] == 400
        assert errors[0]['message'] == '工具审批响应无效或超出允许范围'
        assert state.get('files', {}) == {}
        assert not [message for message in state['messages'] if message['type'] == 'tool']
        assert state['__interrupt__'] == pending
        body['command']['resume'][pending[0]['id']]['decisions'] = decisions
        events = frames(client.post(f'/api/v1/harness/sessions/{sid}/stream', json=body))
        state = client.get(state_url).json()['values']
    assert not [value for kind, value in events if kind == 'error'], events
    assert '__interrupt__' not in state
    assert set(state['files']) == {'/approved.txt'}
    assert state['files']['/approved.txt']['content'] == 'approved content'
    assert state['messages'][-1]['content'] == '两项审批已处理'
    duplicate = frames(client.post(f'/api/v1/harness/sessions/{sid}/stream', json=body))
    assert any(kind == 'error' and data['status'] == 409 for kind, data in duplicate)
    assert client.get(state_url).json()['values'] == state
