"""Exercise the real official harness without model or MCP network requests."""
import asyncio
import base64
import hashlib
import io
import zipfile

import pytest
from deepagents.backends.utils import create_file_data
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from pydantic import Field

from agent import graph, registry
from agent.config import validate_config
from agent.harness_config import prepare_harness_files
from governance.store import StoreError, data_dir


class Model(FakeMessagesListChatModel):
    declarations: list = Field(default_factory=list)
    prompts: list = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        self.declarations.append({value.name if not isinstance(value, dict) else value['name'] for value in tools})
        return self

    def _generate(self, messages, *args, **kwargs):
        self.prompts.append(messages)
        return super()._generate(messages, *args, **kwargs)


def call(name, args, call_id='call'):
    return AIMessage(content='', tool_calls=[{'name': name, 'args': args, 'id': call_id, 'type': 'tool_call'}])


@pytest.fixture
def build(monkeypatch):
    async def no_tools(**kwargs):
        assert kwargs['agent_config']['access_level'] == 'read_only'
        return []

    async def no_mcp(*args):
        return []

    monkeypatch.setattr(graph, 'load_knowledge_mcp_tools', no_tools)
    monkeypatch.setattr(graph, 'make_governance_tools', lambda *args: [])
    monkeypatch.setattr(registry, 'mcp_tools', no_mcp)

    async def factory(model, *, saver=None, role='admin', load_tools=True, **config):
        monkeypatch.setattr(graph, 'build_model', lambda settings, owner: model)
        return await graph.build_agent(saver, api_key='test-key', owner_id='owner', role=role,
            agent_config=validate_config(config), load_tools=load_tools)
    return factory


def test_native_todos_files_and_no_process_tools(build):
    model = Model(responses=[call('write_todos', {'todos': [{'content': 'Read source', 'status': 'in_progress'}]}),
        call('write_file', {'file_path': '/notes.txt', 'content': 'draft'}, 'write'),
        call('edit_file', {'file_path': '/notes.txt', 'old_string': 'draft', 'new_string': 'final'}, 'edit'),
        call('read_file', {'file_path': '/notes.txt'}, 'read'), AIMessage(content='done')])

    async def exercise():
        agent = await build(model, access_level='auto_write')
        return await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Prepare notes'}]})
    result = asyncio.run(exercise())
    assert result['files']['/notes.txt']['content'] == 'final'
    assert result['todos'] == [{'content': 'Read source', 'status': 'in_progress'}]
    assert any('final' in str(message.content) for message in result['messages'] if message.type == 'tool')
    assert {'write_todos', 'task', 'read_file', 'write_file', 'edit_file'} <= model.declarations[0]
    assert not {'execute', 'run_background', 'browser', 'install_skill'} & set.union(*model.declarations)


@pytest.mark.parametrize('role,access', [('viewer', 'auto_write'), ('admin', 'read_only')])
def test_native_permissions_block_file_writes_even_in_subagents(build, role, access):
    model = Model(responses=[call('task', {'description': 'Try writing a file', 'subagent_type': 'general-purpose'}),
        call('write_file', {'file_path': '/forbidden.txt', 'content': 'forbidden'}, 'child-write'),
        AIMessage(content='write denied'), AIMessage(content='done')])

    async def exercise():
        agent = await build(model, role=role, access_level=access)
        return await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Delegate'}]})
    result = asyncio.run(exercise())
    assert '/forbidden.txt' not in result.get('files', {})
    assert not result.get('__interrupt__')
    assert any('write denied' in str(message.content) for message in result['messages'] if message.type == 'tool')
    assert any(message.type == 'tool' and message.status == 'error'
               for messages in model.prompts for message in messages)


def test_native_hitl_subagent_history_reads_without_mcp_and_resumes(build, monkeypatch):
    model = Model(responses=[call('task', {'description': 'Write notes', 'subagent_type': 'general-purpose'}),
        call('write_file', {'file_path': '/approved.txt', 'content': 'approved'}, 'child-write'),
        AIMessage(content='saved'), AIMessage(content='done')])

    async def exercise():
        saver = InMemorySaver()
        agent = await build(model, saver=saver, access_level='confirm')
        config = {'configurable': {'thread_id': 'subagent-approval'}}
        waiting = await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Delegate'}]}, config)
        pending = waiting['__interrupt__'][0]
        assert pending.value['action_requests'][0]['name'] == 'write_file'
        assert '/approved.txt' not in waiting.get('files', {})

        async def offline(*args, **kwargs):
            pytest.fail('history must not discover MCP tools')
        monkeypatch.setattr(graph, 'load_knowledge_mcp_tools', offline)
        monkeypatch.setattr(registry, 'mcp_tools', offline)
        reader = await build(model, saver=saver, access_level='confirm', load_tools=False)
        state = await reader.aget_state(config, subgraphs=True)
        assert state.interrupts and state.interrupts[0].id == pending.id
        history = [value async for value in reader.aget_state_history(config)]
        assert history and history[0].interrupts
        result = await agent.ainvoke(Command(resume={pending.id: {'decisions': [{'type': 'approve'}]}}), config)
        assert result['files']['/approved.txt']['content'] == 'approved'
        assert not result.get('__interrupt__')
    asyncio.run(exercise())


def test_native_ask_user_resumes_without_presentation_state(build):
    model = Model(responses=[call('ask_user', {'question': 'Which source?', 'options': ['A', 'B']}), AIMessage(content='received')])

    async def exercise():
        agent = await build(model, saver=InMemorySaver())
        config = {'configurable': {'thread_id': 'ask'}}
        waiting = await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Ask'}]}, config)
        pending = waiting['__interrupt__'][0]
        assert pending.value['kind'] == 'ask_user'
        result = await agent.ainvoke(Command(resume={pending.id: {'answer': 'A'}}), config)
        assert any('"answer": "A"' in message.content for message in result['messages'] if message.type == 'tool')
    asyncio.run(exercise())


@pytest.mark.parametrize('decision', ['approve', 'reject'])
def test_native_delete_waits_for_official_approval_and_preserves_rejection(build, decision):
    model = Model(responses=[call('delete', {'file_path': '/notes.txt'}), AIMessage(content='done')])

    async def exercise():
        saver = InMemorySaver()
        agent = await build(model, saver=saver, access_level='confirm')
        config = {'configurable': {'thread_id': 'delete-' + decision}}
        waiting = await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Delete notes'}],
            'files': {'/notes.txt': create_file_data('original')}}, config)
        pending = waiting['__interrupt__'][0]
        assert pending.value['action_requests'][0]['name'] == 'delete'
        assert pending.value['action_requests'][0]['args'] == {'file_path': '/notes.txt'}
        assert waiting['files']['/notes.txt']['content'] == 'original'
        reader = await build(model, saver=saver, access_level='confirm', load_tools=False)
        snapshot = await reader.aget_state(config)
        assert snapshot.interrupts[0].id == pending.id
        assert snapshot.values['files']['/notes.txt']['content'] == 'original'
        result = await agent.ainvoke(Command(resume={pending.id: {'decisions': [{'type': decision}]}}), config)
        assert not result.get('__interrupt__')
        if decision == 'approve':
            assert '/notes.txt' not in result['files']
            assert any(message.type == 'tool' and message.name == 'delete' and message.status == 'success'
                       for message in result['messages'])
        else:
            assert result['files']['/notes.txt']['content'] == 'original'
    asyncio.run(exercise())


@pytest.mark.parametrize('role,access,path', [
    ('viewer', 'auto_write', '/notes.txt'),
    ('admin', 'read_only', '/notes.txt'),
    ('admin', 'auto_write', '/skills/guide/reference.md'),
])
def test_native_permissions_prevent_delete_without_offering_approval(build, role, access, path):
    model = Model(responses=[call('delete', {'file_path': path}), AIMessage(content='done')])

    async def exercise():
        agent = await build(model, role=role, access_level=access)
        result = await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Delete the file'}],
            'files': {path: create_file_data('protected')}})
        assert result['files'][path]['content'] == 'protected'
        assert not result.get('__interrupt__')
        assert any(message.type == 'tool' and message.name == 'delete' and message.status == 'error'
                   for message in result['messages'])
    asyncio.run(exercise())


def test_skills_and_thread_memory_use_native_state_files(build, monkeypatch):
    catalog = {'name': 'guide', 'enabled': True, 'files': {
        'SKILL.md': '---\nname: guide\ndescription: Verify sources\n---\nRead reference.md',
        'reference.md': 'trusted reference'}}
    monkeypatch.setattr(registry, 'records', lambda kind, owner: [catalog] if kind == 'skill' and owner == 'owner' else [])
    model = Model(responses=[call('read_file', {'file_path': '/skills/guide/reference.md'}), AIMessage(content='done')])

    async def exercise():
        agent = await build(model, skills_selection_mode='selected', selected_skills=['guide'])
        files = prepare_harness_files('owner', {'skills_selection_mode': 'selected', 'selected_skills': ['guide']},
            {'/skills/old/SKILL.md': create_file_data('old'), '/notes.txt': create_file_data('keep')})
        assert files['/skills/old/SKILL.md'] is None and '/notes.txt' not in files
        files['/AGENTS.md'] = create_file_data('Always report verified source names.')
        result = await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Read selected guide'}], 'files': files})
        assert any('trusted reference' in str(message.content) for message in result['messages'] if message.type == 'tool')
        system = str(model.prompts[0][0].content)
        assert 'Verify sources' in system and 'Always report verified source names.' in system
    asyncio.run(exercise())
    with pytest.raises(StoreError, match='无权访问'):
        prepare_harness_files('another-owner', {'skills_selection_mode': 'selected', 'selected_skills': ['guide']})


def test_native_memory_persists_only_in_its_thread_without_legacy_lifecycle(build, monkeypatch):
    def no_memory_records(kind, *args):
        assert not kind.startswith('memory'), 'legacy configuration must not load cross-session memory'
        return []
    monkeypatch.setattr(registry, 'records', no_memory_records)
    model = Model(responses=[AIMessage(content='done')])
    note = 'Thread A only: use the verified violet document.'

    async def exercise():
        agent = await build(model, saver=InMemorySaver(), memory_enabled=True)
        first = {'configurable': {'thread_id': 'memory-a'}}
        other = {'configurable': {'thread_id': 'memory-b'}}
        await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Read my notes'}],
            'files': {'/AGENTS.md': create_file_data(note)}}, first)
        continued = await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Continue'}]}, first)
        separate = await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Start fresh'}]}, other)
        assert continued['files']['/AGENTS.md']['content'] == note
        assert '/AGENTS.md' not in separate.get('files', {})
        assert note in str(model.prompts[0][0].content)
        assert note in str(model.prompts[1][0].content)
        assert note not in str(model.prompts[2][0].content)
        assert not {'search_memory', 'remember_memory', 'forget_memory'} & set.union(*model.declarations)
    asyncio.run(exercise())


def test_skill_archives_cannot_read_another_owner_directory(monkeypatch, tmp_path):
    other = data_dir() / 'skill-bundles' / hashlib.sha256(b'other').hexdigest() / 'bundle.zip'
    monkeypatch.setattr(registry, 'records', lambda *args: [{'name': 'guide', '_bundle_path': str(other)}])
    with pytest.raises(StoreError, match='不属于当前用户'):
        prepare_harness_files('owner', {'skills_selection_mode': 'all'})


def test_skill_binary_assets_reach_native_state_files(build, monkeypatch):
    raw = b'\x00\xff\x89PNG\r\n'
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as bundle:
        bundle.writestr('SKILL.md', '---\nname: guide\ndescription: Read supporting assets\n---\nRead asset.bin')
        bundle.writestr('asset.bin', raw)
    directory = data_dir() / 'skill-bundles' / hashlib.sha256(b'owner').hexdigest()
    directory.mkdir(parents=True)
    path = directory / 'guide.zip'
    path.write_bytes(archive.getvalue())
    monkeypatch.setattr(registry, 'records', lambda *args: [{'name': 'guide', '_bundle_path': str(path)}])
    files = prepare_harness_files('owner', {'skills_selection_mode': 'all'})
    model = Model(responses=[AIMessage(content='done')])

    async def exercise():
        agent = await build(model, skills_selection_mode='all')
        return await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Load guide'}], 'files': files})
    result = asyncio.run(exercise())
    asset = result['files']['/skills/guide/asset.bin']
    assert asset['encoding'] == 'base64' and base64.b64decode(asset['content'], validate=True) == raw
    assert result['files']['/skills/guide/SKILL.md']['encoding'] == 'utf-8'


def test_external_mcp_writes_are_not_exposed_or_executed(build, monkeypatch):
    executions = []
    @tool
    def readonly_tool() -> str:
        """Read a remote source."""
        return 'source'
    @tool
    def delete_remote() -> str:
        """Delete a remote source."""
        executions.append('deleted')
        return 'deleted'
    readonly_tool.metadata = {'readOnlyHint': True}
    delete_remote.metadata = {'readOnlyHint': False}
    async def remote(*args):
        return [readonly_tool, delete_remote]
    monkeypatch.setattr(registry, 'mcp_tools', remote)
    model = Model(responses=[call('delete_remote', {}), AIMessage(content='done')])

    async def exercise():
        agent = await build(model, access_level='auto_write')
        return await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Try remote write'}]})
    result = asyncio.run(exercise())
    assert 'readonly_tool' in model.declarations[0] and 'delete_remote' not in model.declarations[0]
    assert executions == []
    assert any(message.type == 'tool' and message.status == 'error' for message in result['messages'])


def test_external_read_approval_can_be_read_without_tool_discovery(build, monkeypatch):
    @tool
    def protected_read() -> str:
        """Read a source that requires user review."""
        return 'source'
    protected_read.metadata = {'readOnlyHint': True, 'require_approval': True}

    async def remote(*args):
        return [protected_read]
    monkeypatch.setattr(registry, 'mcp_tools', remote)
    model = Model(responses=[call('protected_read', {}), AIMessage(content='done')])

    async def exercise():
        saver = InMemorySaver()
        config = {'configurable': {'thread_id': 'remote-approval'}}
        agent = await build(model, saver=saver, role='viewer')
        result = await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Read source'}]}, config)
        pending = result['__interrupt__'][0]
        async def offline(*args, **kwargs):
            pytest.fail('reading checkpoints must not connect to MCP')
        monkeypatch.setattr(registry, 'mcp_tools', offline)
        reader = await build(model, saver=saver, role='viewer', load_tools=False)
        assert set(reader.nodes) == set(agent.nodes)
        state = await reader.aget_state(config)
        assert state.interrupts[0].id == pending.id
        assert state.interrupts[0].value['action_requests'][0]['name'] == 'protected_read'
    asyncio.run(exercise())


def test_stdio_discovery_is_blocked_before_starting_a_process(monkeypatch):
    monkeypatch.setattr(registry, 'records', lambda *args: [{'id': 'local', 'enabled': True, 'transport_type': 'stdio'}])
    async def forbidden(*args):
        pytest.fail('stdio discovery must not launch a process')
    monkeypatch.setattr('langchain_mcp_adapters.client.MultiServerMCPClient.get_tools', forbidden)
    with pytest.raises(StoreError) as error:
        asyncio.run(registry.mcp_tools('owner', {'mcp_selection_mode': 'selected', 'mcp_services': ['local']}))
    assert error.value.status == 501


def test_selected_model_name_never_silently_falls_back(monkeypatch):
    monkeypatch.delenv('BAILIAN_API_KEY', raising=False)
    monkeypatch.setenv('DASHSCOPE_API_KEY', 'test-key')
    monkeypatch.setenv('AGENT_MAIN_MODEL', 'configured-max-model')
    monkeypatch.setenv('AGENT_FALLBACK_MODEL', 'must-not-use')
    assert registry.environment_model()['parameters']['model_name'] == 'configured-max-model'
    assert graph.build_model({'model_id': 'agent-main'}, 'owner').model == 'configured-max-model'


def test_history_survives_deleted_model_and_missing_credentials(build, monkeypatch):
    model = Model(responses=[call('write_todos', {'todos': [{'content': 'Read later', 'status': 'pending'}]}),
        call('write_file', {'file_path': '/notes.txt', 'content': 'kept'}, 'write'), AIMessage(content='saved')])

    async def exercise():
        saver = InMemorySaver()
        config = {'configurable': {'thread_id': 'deleted-model-history'}}
        agent = await build(model, saver=saver, model_id='deleted-model', access_level='auto_write')
        expected = await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Save notes'}]}, config)

        def forbidden(*args, **kwargs):
            pytest.fail('history must not resolve models, credentials, or call a model')

        async def offline(*args, **kwargs):
            pytest.fail('history must not call a model or discover MCP tools')

        monkeypatch.setattr(graph, 'build_model', forbidden)
        monkeypatch.setattr(registry, 'model_config', forbidden)
        monkeypatch.setattr(registry, 'default_model_id', forbidden)
        monkeypatch.setattr(graph.ChatOpenAI, '_agenerate', offline)
        monkeypatch.setattr(graph.ChatOpenAI, '_generate', forbidden)
        monkeypatch.setattr(graph, 'load_knowledge_mcp_tools', offline)
        monkeypatch.setattr(registry, 'mcp_tools', offline)
        for variable in ('OPENAI_API_KEY', 'BAILIAN_API_KEY', 'DASHSCOPE_API_KEY'):
            monkeypatch.delenv(variable, raising=False)
        reader = await graph.build_agent(saver, api_key='', owner_id='owner', role='admin',
            agent_config={'model_id': 'deleted-model', 'access_level': 'auto_write'}, load_tools=False)
        state = await reader.aget_state(config)
        assert state.values['messages'] == expected['messages']
        assert state.values['files'] == expected['files']
        assert state.values['todos'] == expected['todos']
        assert [value async for value in reader.aget_state_history(config)]
        assert model.i == 0  # Exactly the three execution responses were consumed.

    asyncio.run(exercise())
