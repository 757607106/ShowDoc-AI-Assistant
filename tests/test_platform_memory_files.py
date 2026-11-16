"""Real PostgreSQL native file memory, isolated by authenticated owner and Agent."""
import asyncio
import os

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langgraph.types import Command
from pydantic import Field

from agent import config, graph, registry
from agent.checkpointer import async_runtime, async_store, make_checkpointer
from agent.memory_files import namespace
from governance.database import connection
from webapi.auth import create_user


class Model(FakeMessagesListChatModel):
    prompts: list = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, *args, **kwargs):
        self.prompts.append(str(messages[0].content))
        return super()._generate(messages, *args, **kwargs)


def enable(client):
    assert client.put('/api/v1/tenants/kv/memory-config', json={'enabled': True}).status_code == 200


@pytest.fixture
def agent_id(authenticated_client):
    return config.save_agent({'name': 'Memory Agent'}, os.environ['TEST_PLATFORM_USER'])['id']


def test_postgres_memory_shares_only_owner_agent_and_keeps_native_thread_cache(authenticated_client, agent_id, monkeypatch):
    owner = os.environ['TEST_PLATFORM_USER']
    model = Model(responses=[AIMessage(content='done')])
    monkeypatch.setattr(graph, 'build_model', lambda *args: model)
    monkeypatch.setattr('integrations.contextdb.ContextDBClient._request', lambda *args, **kwargs: pytest.fail('Memory must not call ContextDB'))
    enable(authenticated_client)
    path = f'/api/v1/agents/{agent_id}/memory-file'
    assert authenticated_client.put(path, json={'content': 'MEMORY-VIOLET'}).status_code == 200

    async def exercise():
        async with async_runtime() as (saver, store):
            saved = config.load_agent(agent_id, owner)['config']
            agent = await graph.build_agent(saver, store=store, api_key='fake', owner_id=owner,
                agent_id=agent_id, role='admin', agent_config=saved)
            first = {'configurable': {'thread_id': 'memory-first'}}
            await agent.ainvoke({'messages': [{'role': 'user', 'content': 'start'}]}, first)
            assert 'MEMORY-VIOLET' in model.prompts[-1]
            source = await agent.aget_state(first)
            from deepagents.backends import StoreBackend
            backend = StoreBackend(namespace=lambda _rt: namespace(owner, agent_id), store=store)
            assert (await backend.aedit('/AGENTS.md', 'VIOLET', 'GREEN')).error is None
            await agent.ainvoke({'messages': [{'role': 'user', 'content': 'continue'}]}, first)
            assert 'MEMORY-VIOLET' in model.prompts[-1] and 'MEMORY-GREEN' not in model.prompts[-1]
            await agent.ainvoke({'messages': [{'role': 'user', 'content': 'fresh'}]}, {'configurable': {'thread_id': 'memory-new'}})
            assert 'MEMORY-GREEN' in model.prompts[-1]
            from agent.time_travel import seed
            await seed(agent, source, 'memory-fork')
            forked = {'configurable': {'thread_id': 'memory-fork'}}
            assert 'memory_contents' not in (await agent.aget_state(forked)).values
            await agent.ainvoke({'messages': [{'role': 'user', 'content': 'continue new fork'}]}, forked)
            assert 'MEMORY-GREEN' in model.prompts[-1] and 'MEMORY-VIOLET' not in model.prompts[-1]
            other_agent = await graph.build_agent(saver, store=store, api_key='fake', owner_id=owner,
                agent_id='builtin-smart-reasoning', role='admin', agent_config=saved)
            await other_agent.ainvoke({'messages': [{'role': 'user', 'content': 'other agent'}]},
                {'configurable': {'thread_id': 'memory-other-agent'}})
            assert 'MEMORY-GREEN' not in model.prompts[-1]
            await other_agent.ainvoke({'messages': [{'role': 'user', 'content': 'switch agent in same conversation'}]}, first)
            assert 'MEMORY-VIOLET' not in model.prompts[-1] and 'MEMORY-GREEN' not in model.prompts[-1]
            other = create_user('memory-other@example.com', 'Other', 'other-password-123', 'admin')
            registry.save_record('settings', {'id': 'memory-config', 'value': {'enabled': True}}, other)
            isolated = await graph.build_agent(saver, store=store, api_key='fake', owner_id=other,
                agent_id=agent_id, role='admin', agent_config=saved)
            await isolated.ainvoke({'messages': [{'role': 'user', 'content': 'other owner'}]},
                {'configurable': {'thread_id': 'memory-other-owner'}})
            assert 'MEMORY-GREEN' not in model.prompts[-1]
        async with async_store() as reopened:
            assert (await reopened.aget(namespace(owner, agent_id), '/AGENTS.md')).value['content'] == 'MEMORY-GREEN'
    asyncio.run(exercise())
    with make_checkpointer() as saver, connection() as conn:
        assert saver.conn.execute('SELECT to_regclass(current_schema() || %s) AS name', ('.store_vectors',)).fetchone()['name'] is None


@pytest.mark.parametrize('disabled', ['workspace', 'personal', 'agent'])
def test_each_native_memory_gate_disables_prompt_loading_without_deleting_file(authenticated_client, agent_id, monkeypatch, disabled):
    owner = os.environ['TEST_PLATFORM_USER']
    model = Model(responses=[AIMessage(content='done')])
    monkeypatch.setattr(graph, 'build_model', lambda *args: model)
    enable(authenticated_client)
    path = f'/api/v1/agents/{agent_id}/memory-file'
    authenticated_client.put(path, json={'content': 'PRIVATE-NATIVE-MEMORY'})
    saved = config.load_agent(agent_id, owner)['config']
    if disabled == 'workspace':
        authenticated_client.put('/api/v1/tenants/kv/memory-config', json={'enabled': False})
    elif disabled == 'personal':
        authenticated_client.put('/api/v1/memory/settings', json={'enabled': False})
    else:
        saved['memory_enabled'] = False
    async def exercise():
        async with async_runtime() as (saver, store):
            agent = await graph.build_agent(saver, store=store, api_key='fake', owner_id=owner,
                agent_id=agent_id, role='admin', agent_config=saved)
            await agent.ainvoke({'messages': [{'role': 'user', 'content': 'read context'}]},
                {'configurable': {'thread_id': 'disabled-memory'}})
    asyncio.run(exercise())
    assert 'PRIVATE-NATIVE-MEMORY' not in model.prompts[-1]
    assert authenticated_client.get(path).json['data']['content'] == 'PRIVATE-NATIVE-MEMORY'


def test_memory_file_keeps_native_hitl_and_readonly_permissions(authenticated_client, agent_id, monkeypatch):
    owner = os.environ['TEST_PLATFORM_USER']
    enable(authenticated_client)
    path = f'/api/v1/agents/{agent_id}/memory-file'
    authenticated_client.put(path, json={'content': 'old note'})
    call = AIMessage(content='', tool_calls=[{'name': 'edit_file', 'args': {
        'file_path': f'/memories/{agent_id}/AGENTS.md', 'old_string': 'old note', 'new_string': 'new note'},
        'id': 'memory-edit', 'type': 'tool_call'}])
    model = Model(responses=[call, AIMessage(content='done')])
    monkeypatch.setattr(graph, 'build_model', lambda *args: model)
    async def exercise():
        async with async_runtime() as (saver, store):
            agent = await graph.build_agent(saver, store=store, api_key='fake', owner_id=owner,
                agent_id=agent_id, role='admin', agent_config={'access_level': 'confirm'})
            selected = {'configurable': {'thread_id': 'memory-approval'}}
            waiting = await agent.ainvoke({'messages': [{'role': 'user', 'content': 'remember new note'}]}, selected)
            assert waiting['__interrupt__']
            assert (await store.aget(namespace(owner, agent_id), '/AGENTS.md')).value['content'] == 'old note'
            await agent.ainvoke(Command(resume={waiting['__interrupt__'][0].id: {'decisions': [{'type': 'approve'}]}}), selected)
            assert (await store.aget(namespace(owner, agent_id), '/AGENTS.md')).value['content'] == 'new note'
            model.responses = [AIMessage(content='', tool_calls=[{'name': 'edit_file', 'args': {
                'file_path': f'/memories/{agent_id}/AGENTS.md', 'old_string': 'new note', 'new_string': 'forbidden'},
                'id': 'forbidden-edit', 'type': 'tool_call'}]), AIMessage(content='done')]
            model.i = 0
            readonly = await graph.build_agent(saver, store=store, api_key='fake', owner_id=owner,
                agent_id=agent_id, role='viewer', agent_config={'access_level': 'auto_write'})
            result = await readonly.ainvoke({'messages': [{'role': 'user', 'content': 'try edit'}]},
                {'configurable': {'thread_id': 'memory-readonly'}})
            assert any(message.type == 'tool' and message.status == 'error' for message in result['messages'])
            assert (await store.aget(namespace(owner, agent_id), '/AGENTS.md')).value['content'] == 'new note'
    asyncio.run(exercise())


def test_native_file_api_is_owned_and_rejects_structured_memory_workflows(authenticated_client, agent_id):
    owner = os.environ['TEST_PLATFORM_USER']
    registry.save_record('memory', {'id': 'legacy', 'content': 'keep legacy structured memory'}, owner)
    enable(authenticated_client)
    path = f'/api/v1/agents/{agent_id}/memory-file'
    assert authenticated_client.put(path, json={'content': 'my native file'}).json['data']['effective'] is True
    assert authenticated_client.get('/api/v1/memory/settings').json['data']['write_mode'] == 'native_file'
    assert authenticated_client.put(path, json={'content': 3}).status_code == 400
    assert authenticated_client.put('/api/v1/tenants/kv/memory-config', json={'enabled': 'yes'}).status_code == 400
    assert authenticated_client.put('/api/v1/tenants/kv/memory-config', json={'enabled': True, 'vector_recall': True}).status_code == 501
    assert authenticated_client.get('/api/v1/memory/items').status_code == 501
    assert registry.record('memory', 'legacy', owner)['content'] == 'keep legacy structured memory'
    from app import app
    create_user('memory-reader@example.com', 'Reader', 'reader-password-123', 'viewer')
    other = app.test_client()
    token = other.post('/api/v1/auth/login', json={'email': 'memory-reader@example.com', 'password': 'reader-password-123'}).json['token']
    other.environ_base['HTTP_AUTHORIZATION'] = 'Bearer ' + token
    assert other.get(path).status_code == 404
    assert other.put('/api/v1/agents/builtin-smart-reasoning/memory-file', json={'content': 'blocked'}).status_code == 403
    assert other.get('/api/v1/agents/builtin-smart-reasoning/memory-file').json['data']['content'] == ''


def test_native_state_mount_keeps_skill_keys_and_readonly_rules_with_execute_backend(monkeypatch):
    from deepagents.backends.protocol import SandboxBackendProtocol
    from deepagents.backends.utils import create_file_data
    class Sandbox(SandboxBackendProtocol):
        @property
        def id(self):
            return 'test-execution-backend'
        def execute(self, command, *, timeout=None):
            pytest.fail('Virtual Skills must not access the execution backend')
    model = Model(responses=[AIMessage(content='', tool_calls=[{'name': 'read_file', 'args': {
        'file_path': '/state/skills/guide/reference.md'}, 'id': 'read-skill', 'type': 'tool_call'}]),
        AIMessage(content='', tool_calls=[{'name': 'edit_file', 'args': {
            'file_path': '/state/skills/guide/reference.md', 'old_string': 'trusted', 'new_string': 'modified'},
            'id': 'edit-skill', 'type': 'tool_call'}]), AIMessage(content='done')])
    monkeypatch.setattr(graph, 'build_model', lambda *args: model)
    async def exercise():
        agent = await graph.build_agent(None, api_key='fake', owner_id='owner', role='admin',
            agent_config={'access_level': 'auto_write'}, backend=Sandbox())
        result = await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Read selected guide'}], 'files': {
            '/skills/guide/SKILL.md': create_file_data('---\nname: guide\ndescription: Verify original files\n---\nRead reference.md'),
            '/skills/guide/reference.md': create_file_data('trusted'), '/AGENTS.md': create_file_data('LOCAL-THREAD-CONTEXT')}})
        assert result['files']['/skills/guide/reference.md']['content'] == 'trusted'
        assert any(message.type == 'tool' and message.tool_call_id == 'read-skill' and 'trusted' in message.content
                   for message in result['messages'])
        assert any(message.type == 'tool' and message.tool_call_id == 'edit-skill' and message.status == 'error'
                   for message in result['messages'])
        assert 'LOCAL-THREAD-CONTEXT' in model.prompts[0]
    asyncio.run(exercise())


@pytest.mark.parametrize('decision', ['approve', 'reject'])
def test_confirm_mode_requires_native_approval_before_execute(monkeypatch, decision):
    from deepagents.backends.protocol import ExecuteResponse, SandboxBackendProtocol
    executions = []
    class Sandbox(SandboxBackendProtocol):
        @property
        def id(self):
            return 'test-command-approval'
        def execute(self, command, *, timeout=None):
            executions.append(command)
            return ExecuteResponse(output='checked', exit_code=0)
    model = Model(responses=[AIMessage(content='', tool_calls=[{'name': 'execute',
        'args': {'command': 'echo checked'}, 'id': 'shell-call', 'type': 'tool_call'}]), AIMessage(content='done')])
    monkeypatch.setattr(graph, 'build_model', lambda *args: model)
    async def exercise():
        async with async_runtime() as (saver, store):
            agent = await graph.build_agent(saver, api_key='fake', owner_id=os.environ['TEST_PLATFORM_USER'],
                role='admin', agent_config={'access_level': 'confirm'}, backend=Sandbox())
            selected = {'configurable': {'thread_id': 'execute-' + decision}}
            waiting = await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Run shell'}]}, selected)
            assert waiting['__interrupt__'][0].value['action_requests'][0]['name'] == 'execute'
            assert executions == []
            await agent.ainvoke(Command(resume={waiting['__interrupt__'][0].id: {
                'decisions': [{'type': decision}]}}), selected)
            assert executions == (['echo checked'] if decision == 'approve' else [])
    asyncio.run(exercise())
