"""Declared subagents and structured output run through the real pinned SDK."""
import asyncio
import json

import pytest
from deepagents import DeepAgentState
from deepagents.backends import StateBackend
from deepagents.backends.protocol import ExecuteResponse, SandboxBackendProtocol
from deepagents.backends.utils import create_file_data
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from agent import config, graph, native_extensions, registry
from governance.store import StoreError
from tests.test_harness_native import Model, call

ANSWER = {'title': 'Answer', 'type': 'object', 'properties': {'answer': {'type': 'integer'}},
          'required': ['answer'], 'additionalProperties': False}


@pytest.fixture
def make_agent(monkeypatch):
    async def no_tools(**kwargs):
        return []
    async def no_mcp(*args):
        return []
    monkeypatch.setattr(graph, 'load_knowledge_mcp_tools', no_tools)
    monkeypatch.setattr(graph, 'make_governance_tools', lambda *args: [])
    monkeypatch.setattr(registry, 'mcp_tools', no_mcp)
    monkeypatch.setattr(native_extensions, '_factories', {})

    async def build(model, *, child_model=None, saver=None, role='admin', backend=None,
                    native_extension=None, **settings):
        monkeypatch.setattr(graph, 'build_model', lambda value, owner: child_model
                            if value['model_id'] == 'child-model' else model)
        return await graph.build_agent(saver, api_key='fake', owner_id='owner', agent_id='agent-one', role=role,
            backend=backend, native_extension=native_extension, agent_config=config.validate_config(settings))
    return build


@pytest.mark.parametrize('settings', [
    {'response_format': {'$ref': 'https://invalid.example/schema'}},
    {'response_format': {'$dynamicRef': 'https://invalid.example/schema'}},
    {'response_format': {'$id': 'file:///etc/passwd'}},
    {'response_format': {'$ref': '#/$defs/missing'}},
    {'response_format': {'type': 'not-a-json-type'}},
    {'response_format': {'description': 'x' * 64_001}},
    {'subagents': [{'name': '../escape', 'description': 'bad'}]},
    {'subagents': [{'name': 'general-purpose', 'description': 'reserved'}]},
    {'subagents': [{'name': 'worker', 'description': 'bad', 'runnable': 'user-code'}]},
    {'subagents': [{'name': 'worker', 'description': 'bad', 'permissions': [
        {'operations': ['write'], 'paths': ['/**'], 'mode': 'allow'}]}]},
    {'interrupt_on': {'execute': {'allowed_decisions': ['approve'], 'when': 'user-code'}}},
    {'interrupt_on': {'execute': {'allowed_decisions': ['approve'], 'args_schema': ANSWER}}},
    {'middleware': ['user-code']},
])
def test_untrusted_native_configuration_is_rejected(settings):
    with pytest.raises(StoreError) as failed:
        config.validate_config(settings)
    assert failed.value.status == 400


def test_json_schema_local_references_and_optional_selection_semantics_survive():
    schema = {'type': 'object', 'properties': {'value': {'$ref': '#/$defs/number'}},
              '$defs': {'number': {'type': 'integer'}}}
    value = config.validate_config({'response_format': schema, 'subagents': [
        {'name': 'inherit', 'description': 'inherit', 'allowed_tools': None},
        {'name': 'empty', 'description': 'empty', 'allowed_tools': [], 'selected_skills': []}]})
    assert value['response_format'] == schema and value['response_format'] is not schema
    assert value['subagents'][0]['allowed_tools'] is None
    assert value['subagents'][1]['allowed_tools'] == []
    assert value['subagents'][1]['selected_skills'] == []


def test_main_structured_output_is_native_state(make_agent):
    model = Model(responses=[call('Answer', {'answer': 42}, 'answer-call')])
    async def run():
        agent = await make_agent(model, response_format=ANSWER)
        return await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Return 42'}]})
    result = asyncio.run(run())
    assert result['structured_response'] == {'answer': 42}
    assert 'Answer' in model.declarations[0]


def test_professional_subagent_uses_its_model_and_native_structured_result(make_agent):
    parent = Model(responses=[call('task', {'subagent_type': 'analyst', 'description': 'Analyze'}),
                              AIMessage(content='parent done')])
    child = Model(responses=[call('Answer', {'answer': 7}, 'child-answer')])
    async def run():
        agent = await make_agent(parent, child_model=child, subagents=[{'name': 'analyst',
            'description': 'Calculate an answer', 'model_id': 'child-model', 'system_prompt': 'CHILD-ONLY',
            'allowed_tools': [], 'selected_skills': [], 'response_format': ANSWER}])
        return await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Delegate'}]})
    result = asyncio.run(run())
    assert result['messages'][-1].content == 'parent done'
    returned = next(message for message in result['messages'] if message.type == 'tool' and message.name == 'task')
    assert json.loads(returned.content) == {'answer': 7}
    assert 'CHILD-ONLY' in str(child.prompts[0][0].content)
    assert 'CHILD-ONLY' not in str(parent.prompts[0][0].content)
    assert 'Answer' in child.declarations[0] and 'Answer' not in parent.declarations[0]


@pytest.mark.parametrize('instructions,inherits', [({}, True), ({'system_prompt': ''}, False)])
def test_subagent_inherits_custom_instructions_only_when_prompt_is_omitted(make_agent, instructions, inherits):
    model = Model(responses=[call('task', {'subagent_type': 'worker', 'description': 'Read'}),
                            AIMessage(content='child done'), AIMessage(content='parent done')])
    async def run():
        agent = await make_agent(model, system_prompt='PARENT-CUSTOM-INSTRUCTIONS', subagents=[{
            'name': 'worker', 'description': 'Read', **instructions}])
        return await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Delegate'}]})
    asyncio.run(run())
    assert 'PARENT-CUSTOM-INSTRUCTIONS' in str(model.prompts[0][0].content)
    assert ('PARENT-CUSTOM-INSTRUCTIONS' in str(model.prompts[1][0].content)) is inherits


def test_subagent_output_format_is_independent_of_parent_format(make_agent):
    parent = Model(responses=[call('task', {'subagent_type': 'worker', 'description': 'Read'}),
                             call('Answer', {'answer': 9}, 'parent-answer')])
    child = Model(responses=[AIMessage(content='ordinary child text')])
    async def run():
        agent = await make_agent(parent, child_model=child, response_format=ANSWER, subagents=[{
            'name': 'worker', 'description': 'Read', 'model_id': 'child-model'}])
        return await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Delegate'}]})
    result = asyncio.run(run())
    assert result['structured_response'] == {'answer': 9}
    assert 'Answer' in parent.declarations[0] and 'Answer' not in child.declarations[0]
    assert any(message.type == 'tool' and message.name == 'task' and message.content == 'ordinary child text'
               for message in result['messages'])


@pytest.mark.parametrize('selection,allowed', [(None, True), ([], False)])
def test_subagent_extra_tools_inherit_only_when_not_explicitly_empty(make_agent, monkeypatch, selection, allowed):
    calls = []
    @tool
    def evidence() -> str:
        """Read controlled evidence."""
        calls.append('read')
        return 'evidence'
    monkeypatch.setattr(graph, 'make_governance_tools', lambda *args: [evidence])
    model = Model(responses=[call('task', {'subagent_type': 'worker', 'description': 'Read'}),
        call('evidence', {}, 'child-read'), AIMessage(content='child done'), AIMessage(content='parent done')])
    async def run():
        agent = await make_agent(model, allowed_tools=['evidence'], subagents=[{'name': 'worker',
            'description': 'Read evidence', 'allowed_tools': selection}])
        return await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Delegate'}]})
    asyncio.run(run())
    assert calls == (['read'] if allowed else [])


def test_child_cannot_disable_parent_confirmation_or_escalate_access(make_agent):
    model = Model(responses=[call('task', {'subagent_type': 'worker', 'description': 'Write'}),
        call('write_file', {'file_path': '/approved.txt', 'content': 'approved'}, 'child-write'),
        AIMessage(content='child done'), AIMessage(content='parent done')])
    async def run():
        agent = await make_agent(model, saver=InMemorySaver(), access_level='confirm', subagents=[{
            'name': 'worker', 'description': 'Write a file', 'access_level': 'auto_write',
            'interrupt_on': {'write_file': False}}])
        selected = {'configurable': {'thread_id': 'child-confirm'}}
        waiting = await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Delegate'}]}, selected)
        pending = waiting['__interrupt__'][0]
        assert pending.value['action_requests'][0]['name'] == 'write_file'
        assert '/approved.txt' not in waiting.get('files', {})
        return await agent.ainvoke(Command(resume={pending.id: {'decisions': [{'type': 'approve'}]}}), selected)
    assert asyncio.run(run())['files']['/approved.txt']['content'] == 'approved'


def test_child_empty_skills_cannot_read_parent_skill_files(make_agent):
    model = Model(responses=[call('task', {'subagent_type': 'worker', 'description': 'Read'}),
        call('read_file', {'file_path': '/skills/private/SKILL.md'}, 'child-read'),
        AIMessage(content='child done'), AIMessage(content='parent done')])
    async def run():
        agent = await make_agent(model, skills_selection_mode='selected', selected_skills=['private'], subagents=[{
            'name': 'worker', 'description': 'No skills', 'selected_skills': []}])
        return await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Delegate'}],
            'files': {'/skills/private/SKILL.md': create_file_data('SECRET-SKILL')}})
    asyncio.run(run())
    reads = [message for messages in model.prompts for message in messages
             if message.type == 'tool' and message.tool_call_id == 'child-read']
    assert reads and all(message.status == 'error' for message in reads)
    assert all('SECRET-SKILL' not in str(message.content) for message in reads)


def test_subagent_skill_subset_loads_only_its_independent_source(make_agent):
    model = Model(responses=[call('task', {'subagent_type': 'worker', 'description': 'Read'}),
                            AIMessage(content='child done'), AIMessage(content='parent done')])
    async def run():
        agent = await make_agent(model, skills_selection_mode='selected', selected_skills=['a', 'b'], subagents=[{
            'name': 'worker', 'description': 'Only A', 'selected_skills': ['a']}])
        a = '---\nname: a\ndescription: ONLY-A\n---\nA'
        b = '---\nname: b\ndescription: PRIVATE-B\n---\nB'
        return await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Delegate'}], 'files': {
            '/skills/a/SKILL.md': create_file_data(a), '/skills/b/SKILL.md': create_file_data(b),
            '/subagent-skills/worker/a/SKILL.md': create_file_data(a)}})
    asyncio.run(run())
    child_prompt = str(model.prompts[1][0].content)
    assert 'ONLY-A' in child_prompt and 'PRIVATE-B' not in child_prompt


def test_trusted_extension_is_server_selected_and_preserves_native_state(make_agent):
    class ExtendedState(DeepAgentState):
        label: str
    contexts = []
    def extension(context):
        contexts.append(context)
        return {'state_schema': ExtendedState, 'name': 'trusted-agent', 'debug': False}
    native_extensions.register_native_extension('trusted', extension)
    model = Model(responses=[AIMessage(content='done')])
    async def run():
        agent = await make_agent(model, native_extension='trusted')
        return await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Question'}], 'label': 'native-state'})
    result = asyncio.run(run())
    assert result['label'] == 'native-state'
    assert contexts[0]['owner_id'] == 'owner' and contexts[0]['access_level'] == 'confirm'
    assert contexts[0]['permissions'] and contexts[0]['interrupt_on']['write_file']
    with pytest.raises(StoreError):
        native_extensions.native_options('not-registered', {})
    native_extensions.register_native_extension('wrong-state', lambda context: {'state_schema': dict})
    with pytest.raises(StoreError):
        native_extensions.native_options('wrong-state', {})


def test_path_specific_native_approval_does_not_pause_unrelated_writes(make_agent):
    model = Model(responses=[call('write_file', {'file_path': '/public.txt', 'content': 'public'}, 'public'),
        call('write_file', {'file_path': '/sensitive/private.txt', 'content': 'private'}, 'private'),
        AIMessage(content='done')])
    async def run():
        agent = await make_agent(model, saver=InMemorySaver(), access_level='auto_write', permissions=[
            {'operations': ['write'], 'paths': ['/sensitive/**'], 'mode': 'interrupt'}])
        selected = {'configurable': {'thread_id': 'conditional-native'}}
        result = await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Write'}]}, selected)
        assert result['files']['/public.txt']['content'] == 'public'
        assert '/sensitive/private.txt' not in result['files']
        pending = result['__interrupt__'][0]
        assert pending.value['action_requests'][0]['args']['file_path'] == '/sensitive/private.txt'
        return await agent.ainvoke(Command(resume={pending.id: {'decisions': [{'type': 'reject', 'message': 'No'}]}}), selected)
    assert '/sensitive/private.txt' not in asyncio.run(run())['files']


@pytest.mark.parametrize('override', [False, {'allowed_decisions': ['approve', 'reject']}])
def test_child_cannot_disable_or_broaden_parent_path_approval(make_agent, override):
    model = Model(responses=[call('task', {'subagent_type': 'worker', 'description': 'Write'}),
        call('write_file', {'file_path': '/public.txt', 'content': 'public'}, 'public'),
        call('write_file', {'file_path': '/sensitive/private.txt', 'content': 'private'}, 'private'),
        AIMessage(content='child done'), AIMessage(content='parent done')])
    async def run():
        agent = await make_agent(model, saver=InMemorySaver(), access_level='auto_write', permissions=[
            {'operations': ['write'], 'paths': ['/sensitive/**'], 'mode': 'interrupt'}],
            subagents=[{'name': 'worker', 'description': 'Write', 'interrupt_on': {'write_file': override}}])
        selected = {'configurable': {'thread_id': 'child-conditional'}}
        waiting = await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Delegate'}]}, selected)
        pending = waiting['__interrupt__'][0]
        assert pending.value['action_requests'][0]['args']['file_path'] == '/sensitive/private.txt'
        result = await agent.ainvoke(Command(resume={pending.id: {'decisions': [{'type': 'reject', 'message': 'No'}]}}), selected)
        assert result['files']['/public.txt']['content'] == 'public'
        assert '/sensitive/private.txt' not in result['files']
    asyncio.run(run())


class Shell(StateBackend, SandboxBackendProtocol):
    def __init__(self):
        self.calls = []
    @property
    def id(self):
        return 'test-shell'
    def execute(self, command, *, timeout=None):
        self.calls.append(command)
        return ExecuteResponse(output='executed', exit_code=0)


def test_readonly_child_has_no_shell_even_with_parent_execution_backend(make_agent):
    backend = Shell()
    model = Model(responses=[call('task', {'subagent_type': 'worker', 'description': 'Try execute'}),
        call('execute', {'command': 'forbidden'}, 'child-execute'),
        AIMessage(content='child done'), AIMessage(content='parent done')])
    async def run():
        agent = await make_agent(model, backend=backend, access_level='auto_write', subagents=[{
            'name': 'worker', 'description': 'Read only', 'access_level': 'read_only'}])
        return await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Delegate'}]})
    asyncio.run(run())
    assert 'execute' in model.declarations[0] and 'execute' not in model.declarations[1]
    assert backend.calls == []


def test_readonly_compiled_child_keeps_virtual_skill_reads_and_denies_writes(make_agent):
    model = Model(responses=[call('task', {'subagent_type': 'reader', 'description': 'Read'}),
        call('read_file', {'file_path': '/state/skills/guide/reference.md'}, 'child-read'),
        call('write_file', {'file_path': '/state/new.txt', 'content': 'bad'}, 'child-write'),
        AIMessage(content='child done'), AIMessage(content='parent done')])
    async def run():
        agent = await make_agent(model, backend=Shell(), access_level='auto_write', subagents=[{
            'name': 'reader', 'description': 'Read skill', 'access_level': 'read_only'}])
        return await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Delegate'}], 'files': {
            '/skills/guide/reference.md': create_file_data('VIRTUAL-SKILL-CONTENT')}})
    result = asyncio.run(run())
    child_tools = [message for messages in model.prompts for message in messages if message.type == 'tool']
    assert any(message.tool_call_id == 'child-read' and 'VIRTUAL-SKILL-CONTENT' in str(message.content)
               for message in child_tools)
    assert any(message.tool_call_id == 'child-write' and message.status == 'error' for message in child_tools)
    assert '/new.txt' not in result['files']


def test_execution_backend_rejects_unsupported_real_filesystem_permissions(make_agent):
    async def run():
        with pytest.raises(StoreError) as failed:
            await make_agent(Model(responses=[]), backend=Shell(), access_level='auto_write', permissions=[
                {'operations': ['write'], 'paths': ['/workspace/**'], 'mode': 'deny'}])
        assert failed.value.status == 501
    asyncio.run(run())


def test_default_subagent_keeps_sdk_skills_prompt_and_real_execution_mapping(make_agent):
    model = Model(responses=[call('task', {'subagent_type': 'general-purpose', 'description': 'Use skill'}),
                            AIMessage(content='child done'), AIMessage(content='parent done')])
    async def run():
        agent = await make_agent(model, backend=Shell(), access_level='auto_write')
        return await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Delegate'}]})
    asyncio.run(run())
    for index in (0, 1):
        system = str(model.prompts[index][0].content)
        assert 'progressive disclosure' in system and '/workspace/skills/' in system
        assert '/state/subagent-skills/' in system


def test_trusted_compiled_child_is_built_with_current_owner_permissions(make_agent):
    from deepagents import create_deep_agent
    parent = Model(responses=[call('task', {'subagent_type': 'compiled', 'description': 'Try write'}),
                              AIMessage(content='parent done')])
    child = Model(responses=[call('write_file', {'file_path': '/forbidden.txt', 'content': 'bad'}, 'compiled-write'),
                             AIMessage(content='child denied')])
    def extension(context):
        assert context['owner_id'] == 'owner' and context['access_level'] == 'read_only'
        runnable = create_deep_agent(child, backend=context['backend'],
            permissions=list(context['permissions']), interrupt_on=context['interrupt_on'])
        return {'subagents': [{'name': 'compiled', 'description': 'Controlled compiled child', 'runnable': runnable}]}
    native_extensions.register_native_extension('compiled-policy', extension)
    async def run():
        agent = await make_agent(parent, access_level='read_only', native_extension='compiled-policy')
        return await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Delegate'}]})
    result = asyncio.run(run())
    assert '/forbidden.txt' not in result.get('files', {})
    assert any(message.type == 'tool' and message.tool_call_id == 'compiled-write' and message.status == 'error'
               for messages in child.prompts for message in messages)
