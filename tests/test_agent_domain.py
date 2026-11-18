"""Official PostgreSQL checkpoints, owner isolation, SSE and human approval."""
import asyncio
import json
import os
from contextlib import contextmanager
from types import SimpleNamespace

import psycopg
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, MessagesState, StateGraph

from agent.checkpointer import make_checkpointer
from agent import sessions
from governance.database import connection
from governance.store import StoreError


def test_checkpoint_survives_new_connection():
    def echo(state):
        return {'messages':[AIMessage('echo:'+state['messages'][-1].content)]}
    graph=StateGraph(MessagesState)
    graph.add_node('echo',echo);graph.add_edge(START,'echo');graph.add_edge('echo',END)
    config={'configurable':{'thread_id':'owner-session'}}
    with make_checkpointer() as saver:
        compiled=graph.compile(checkpointer=saver)
        compiled.invoke({'messages':[HumanMessage('你好')]},config)
    with make_checkpointer() as reopened:
        compiled=graph.compile(checkpointer=reopened)
        compiled.invoke({'messages':[HumanMessage('再次')]},config)
        assert len(compiled.get_state(config).values['messages']) == 4
        assert compiled.get_state({'configurable':{'thread_id':'other-session'}}).values == {}


def test_sessions_lifecycle_and_ownership(authenticated_client):
    http=authenticated_client
    session=http.post('/api/agent/sessions',json={'title':'测试会话'}).json['session']
    sid=session['id']
    assert any(item['id']==sid for item in http.get('/api/v1/sessions').json['data'])
    assert http.get(f'/api/agent/sessions/{sid}').json['messages']==[]
    with pytest.raises(Exception,match='会话不存在'):
        sessions.get_session(sid,'another-user')
    assert http.delete(f'/api/agent/sessions/{sid}').status_code==200
    assert http.delete(f'/api/agent/sessions/{sid}').status_code==404


def test_delete_failure_after_checkpoint_is_hidden_and_retryable(authenticated_client, monkeypatch):
    owner = os.environ['TEST_PLATFORM_USER']
    sid = authenticated_client.post('/api/v1/sessions', json={}).json['data']['id']
    builder = StateGraph(MessagesState)
    builder.add_node('answer', lambda state: {'messages': [AIMessage('Answer')]})
    builder.add_edge(START, 'answer'); builder.add_edge('answer', END)
    config = {'configurable': {'thread_id': sid}}
    with make_checkpointer() as saver:
        builder.compile(checkpointer=saver).invoke({'messages': [HumanMessage('Question')]}, config)
    assert len(sessions.read_messages(sid, owner_id=owner)) == 2

    failures = []

    class FailFinalDelete:
        def __init__(self, connection):
            self.connection = connection

        def execute(self, query, params=None):
            if str(query).lstrip().startswith('DELETE FROM agent_sessions'):
                failures.append(sid)
                raise psycopg.OperationalError('injected platform delete failure')
            return self.connection.execute(query, params)

    @contextmanager
    def fail_final_delete():
        with connection() as conn:
            yield FailFinalDelete(conn)

    monkeypatch.setattr(sessions, 'connection', fail_final_delete)
    with pytest.raises(psycopg.OperationalError, match='injected platform delete failure'):
        sessions.delete_session(sid, owner)
    assert failures == [sid]

    with connection() as conn:
        saved = conn.execute('SELECT agent_config FROM agent_sessions WHERE id=%s', (sid,)).fetchone()['agent_config']
    assert saved['_deleting'] is True
    with make_checkpointer() as saver:
        assert saver.get_tuple(config) is None
    assert sid not in {item['id'] for item in sessions.list_sessions(owner)}
    for operation in (lambda: sessions.get_session(sid, owner), lambda: sessions.read_messages(sid, owner_id=owner)):
        with pytest.raises(StoreError) as error:
            operation()
        assert error.value.status == 404
    assert authenticated_client.get(f'/api/v1/sessions/{sid}').status_code == 404

    monkeypatch.setattr(sessions, 'connection', connection)
    response = authenticated_client.delete('/api/v1/sessions/batch', json={'delete_all': True})
    assert response.status_code == 200, response.text
    with connection() as conn:
        assert conn.execute('SELECT 1 FROM agent_sessions WHERE id=%s', (sid,)).fetchone() is None
    assert authenticated_client.delete(f'/api/v1/sessions/{sid}').status_code == 404


def test_async_cleanup_auth_accepts_a_parent_pending_deletion(authenticated_client, monkeypatch):
    from agent import async_runtime, registry

    owner = os.environ['TEST_PLATFORM_USER']
    sid = authenticated_client.post('/api/v1/sessions', json={}).json['data']['id']
    grant = {'id': 'grant', 'owner_id': owner, 'parent_session_id': sid, 'subagent_name': 'worker'}
    with connection() as conn:
        conn.execute("UPDATE agent_sessions SET agent_config=jsonb_set(agent_config,'{_deleting}','true'::jsonb) WHERE id=%s", (sid,))
    monkeypatch.setattr(registry, 'record', lambda kind, key, current_owner: grant)
    monkeypatch.setattr(async_runtime, '_serializer', lambda: SimpleNamespace(
        loads=lambda token, max_age: {'owner_id': owner, 'grant_id': grant['id']}))
    user, authorized = async_runtime.principal('existing-server-token')
    assert user['id'] == owner and authorized is grant


def test_build_model_preserves_explicit_model_selection(monkeypatch):
    from agent.graph import build_model
    monkeypatch.delenv('BAILIAN_API_KEY',raising=False)
    monkeypatch.setenv('AGENT_MAIN_MODEL','qwen-max')
    assert build_model().model=='qwen-max'
    monkeypatch.setenv('BAILIAN_API_KEY','sk-bailian-test')
    model=build_model()
    assert model.model=='qwen-max' and 'dashscope.aliyuncs.com' in str(model.api_base)


def test_sparse_deepagents_checkpoints_are_hydrated(authenticated_client):
    from deepagents.graph import DeepAgentState
    from agent import sessions
    sid=authenticated_client.post('/api/v1/sessions',json={}).json['data']['id']
    graph=StateGraph(DeepAgentState)
    graph.add_node('echo',lambda state:{'messages':[AIMessage('reply:'+state['messages'][-1].content)]})
    graph.add_edge(START,'echo');graph.add_edge('echo',END)
    config={'configurable':{'thread_id':sid}}
    with make_checkpointer() as saver:
        compiled=graph.compile(checkpointer=saver)
        compiled.invoke({'messages':[HumanMessage('first')]},config)
        compiled.invoke({'messages':[HumanMessage('second')]},config)
    owner=os.environ['TEST_PLATFORM_USER']
    messages=sessions.read_messages(sid,owner_id=owner)
    assert [m['content'] for m in messages]==['first','reply:first','second','reply:second']


def test_selected_knowledge_base_scope_is_enforced():
    from agent.tools import scoped_arguments
    from governance.store import StoreError
    assert scoped_arguments({'query':'x'},['kb1'],{'knowledge_base_ids':{}})['knowledge_base_ids']==['kb1']
    assert scoped_arguments({'document_id':'d'},['kb1'],{'knowledge_base_id':{}})['knowledge_base_id']=='kb1'
    with pytest.raises(StoreError):scoped_arguments({'knowledge_base_ids':['kb2']},['kb1'],{'knowledge_base_ids':{}})
    with pytest.raises(StoreError):scoped_arguments({'knowledge_base_names':['hidden']},['kb1'],{})
    with pytest.raises(StoreError):scoped_arguments({'query':'x'},[],{'knowledge_base_ids':{}})
    with pytest.raises(StoreError):scoped_arguments({},['kb1'],{})


@pytest.mark.parametrize('role', ['viewer', 'contributor', 'admin'])
def test_platform_tools_keep_provenance_without_personal_memory(role, monkeypatch):
    from agent import tools as agent_tools
    store = SimpleNamespace(
        list_releases=lambda: [{'release_id': 'release-1'}],
        get_document=lambda version_id: {'version_id': version_id, 'title': '来源文档', 'content': '原文'},
    )
    monkeypatch.setattr(agent_tools, 'Store', lambda **kwargs: store)
    tools = {item.name: item for item in agent_tools.make_governance_tools('ctxdb-fake', 'owner', role)}
    expected = {'list_governance_releases', 'get_capture_provenance'}
    if role != 'viewer':
        expected.add('rerun_collection')
    assert set(tools) == expected
    assert json.loads(tools['list_governance_releases'].invoke({})) == [{'release_id': 'release-1'}]
    assert json.loads(tools['get_capture_provenance'].invoke({'version_id': 'version-1'})) == {
        'version_id': 'version-1', 'title': '来源文档', 'source_key': None, 'job_id': None, 'is_current': None,
    }


@pytest.fixture
def official_mcp(monkeypatch):
    from langchain_core.tools import StructuredTool
    from langchain_mcp_adapters.interceptors import MCPToolCallRequest
    from agent import tools as agent_tools

    fixture = SimpleNamespace(calls=[], lookups=[], documents={}, clients=[], discovered=[], discovery_error=None)
    specs = [
        ('knowledge.search', {'query': {'type': 'string'}, 'knowledge_base_ids': {'type': 'array', 'items': {'type': 'string'}},
                              'knowledge_base_names': {'type': 'array', 'items': {'type': 'string'}}}, True),
        ('knowledge.get_base', {'knowledge_base_id': {'type': 'string'}}, True),
        ('knowledge.wiki_search', {'knowledge_base_ids': {'type': 'array'}, 'query': {'type': 'string'}}, True),
        ('knowledge.list_graph_entities', {'knowledge_base_id': {'type': 'string'}, 'query': {'type': 'string'}}, True),
        ('knowledge.get_graph', {'knowledge_base_id': {'type': 'string'}, 'entity_ids': {'type': 'array'}, 'depth': {'type': 'integer'}}, True),
        ('knowledge.list_entity_chunks', {'knowledge_base_id': {'type': 'string'}, 'entity_ids': {'type': 'array'}}, True),
        ('knowledge.get_document', {'document_id': {'type': 'string'}}, True),
        ('knowledge.delete_document', {'document_id': {'type': 'string'}}, False),
        ('knowledge.delete_documents', {'document_ids': {'type': 'array', 'items': {'type': 'string'}}}, False),
        ('knowledge.list_bases', {}, True),
        ('knowledge.create_base', {'name': {'type': 'string'}}, False),
        ('knowledge.get_entity', {'entity_id': {'type': 'string'}}, True),
        ('contextdb_connectors__list', {}, True),
        ('memory.search', {'query': {'type': 'string'}, 'knowledge_base_ids': {'type': 'array'}}, True),
        ('memory.add', {'content': {'type': 'string'}, 'knowledge_base_ids': {'type': 'array'}}, False),
    ]

    class FakeClient:
        def __init__(self, connections, *, tool_interceptors):
            self.authorize = tool_interceptors[0]
            fixture.clients.append(self)

        async def get_tools(self):
            if fixture.discovery_error:
                raise fixture.discovery_error
            def candidate(name, properties, read_only):
                async def invoke(**arguments):
                    async def handler(request):
                        fixture.calls.append((request.name, request.args))
                        return json.dumps(request.args)
                    return await self.authorize(MCPToolCallRequest(name, arguments, 'contextdb'), handler)
                return StructuredTool.from_function(coroutine=invoke, name=name, description='Official MCP fixture',
                    args_schema={'type': 'object', 'properties': properties}, metadata={'readOnlyHint': read_only})
            discovered = [candidate(*spec) for spec in specs]
            fixture.discovered.extend(discovered)
            return discovered

    class DocumentClient:
        def __init__(self, *, api_key):
            assert api_key == 'ctxdb-fake'

        def get_document(self, knowledge_base_id, document_id):
            assert knowledge_base_id is None
            fixture.lookups.append(document_id)
            result = fixture.documents.get(document_id, {})
            if isinstance(result, Exception):
                raise result
            return result

    monkeypatch.setattr('langchain_mcp_adapters.client.MultiServerMCPClient', FakeClient)
    monkeypatch.setattr(agent_tools, 'ContextDBClient', DocumentClient)

    async def load(ids, role='admin', owner_id=None):
        tools = await agent_tools.load_knowledge_mcp_tools(api_key='ctxdb-fake', role=role, owner_id=owner_id, knowledge_base_ids=ids)
        return {tool.name: tool for tool in tools}
    fixture.load = load
    return fixture


def test_empty_scope_does_not_discover_mcp_or_expose_knowledge_tools(monkeypatch, official_mcp):
    import deepagents
    from agent import graph
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    monkeypatch.setattr(graph, 'build_model', lambda *args: FakeMessagesListChatModel(responses=[AIMessage('answer')]))
    monkeypatch.setattr(graph, 'make_governance_tools', lambda *args: [])
    native, captured = deepagents.create_deep_agent, {}
    def factory(**kwargs):
        captured.update(kwargs)
        return native(**kwargs)
    monkeypatch.setattr(deepagents, 'create_deep_agent', factory)
    asyncio.run(graph.build_agent(None, api_key='ctxdb-fake', owner_id='owner', knowledge_base_ids=[]))
    assert all(not tool.name.startswith('knowledge.') for tool in captured['tools'])
    assert official_mcp.clients == [] and '未选择知识库' in captured['system_prompt']


def test_mcp_discovery_failure_stops_knowledge_access_without_rest_fallback(official_mcp):
    official_mcp.discovery_error = RuntimeError('MCP unavailable')
    with pytest.raises(RuntimeError, match='MCP unavailable'):
        asyncio.run(official_mcp.load(['kb1']))
    assert official_mcp.calls == official_mcp.lookups == []


def test_official_navigation_and_graph_tools_keep_original_contracts(official_mcp):
    async def exercise():
        loaded = await official_mcp.load(['kb1'])
        discovered = {tool.name: tool for tool in official_mcp.discovered}
        calls = [
            ('knowledge.search', {'query': '连接池', 'knowledge_base_ids': ['kb1']}),
            ('knowledge.wiki_search', {'query': '连接池', 'knowledge_base_ids': ['kb1']}),
            ('knowledge.list_graph_entities', {'query': '连接池', 'knowledge_base_id': 'kb1'}),
            ('knowledge.get_graph', {'entity_ids': ['真实实体/非UUID'], 'depth': 1, 'knowledge_base_id': 'kb1'}),
            ('knowledge.list_entity_chunks', {'entity_ids': ['真实实体/非UUID'], 'knowledge_base_id': 'kb1'}),
        ]
        for name, args in calls:
            assert loaded[name] is discovered[name]
            assert json.loads(await loaded[name].ainvoke(args)) == args
        assert official_mcp.calls == calls
        assert official_mcp.lookups == []
    asyncio.run(exercise())


def test_mcp_interceptor_enforces_single_and_multiple_library_scope(official_mcp):
    from governance.store import StoreError

    async def exercise():
        tools = await official_mcp.load(['kb1', 'kb2'])
        assert not {'knowledge.list_bases', 'knowledge.create_base', 'knowledge.get_entity', 'contextdb_connectors__list',
                    'memory.search', 'memory.add'} & tools.keys()
        result = json.loads(await tools['knowledge.search'].ainvoke({'query': '部署'}))
        assert result['knowledge_base_ids'] == ['kb1', 'kb2']
        result = json.loads(await tools['knowledge.search'].ainvoke({'query': '部署', 'knowledge_base_ids': []}))
        assert result['knowledge_base_ids'] == ['kb1', 'kb2']
        result = json.loads(await tools['knowledge.search'].ainvoke({'query': '部署', 'knowledge_base_ids': ['kb2']}))
        assert result['knowledge_base_ids'] == ['kb2']
        result = json.loads(await tools['knowledge.get_base'].ainvoke({'knowledge_base_id': 'kb2'}))
        assert result['knowledge_base_id'] == 'kb2'
        for name, arguments in [('knowledge.search', {'knowledge_base_ids': ['kb3']}),
                                ('knowledge.search', {'knowledge_base_names': ['other']}),
                                ('knowledge.get_base', {}), ('knowledge.get_base', {'knowledge_base_id': 'kb3'})]:
            with pytest.raises(StoreError):
                await tools[name].ainvoke(arguments)
        assert len(official_mcp.calls) == 4
        single = await official_mcp.load(['kb1'])
        assert json.loads(await single['knowledge.get_base'].ainvoke({}))['knowledge_base_id'] == 'kb1'
    asyncio.run(exercise())


def test_mcp_document_tools_verify_official_ownership_before_calling(official_mcp):
    from governance.store import StoreError
    from integrations.contextdb import ContextDBError
    official_mcp.documents.update({'inside': {'knowledge_base_id': 'kb2'}, 'outside': {'knowledge_base_id': 'kb3'},
                                  'denied': ContextDBError('member permission denied', status_code=403)})

    async def exercise():
        tools = await official_mcp.load(['kb1', 'kb2'])
        assert json.loads(await tools['knowledge.get_document'].ainvoke({'document_id': 'inside'})) == {'document_id': 'inside'}
        for document_id in ('outside', 'unknown'):
            with pytest.raises(StoreError, match='不属于|无法验证'):
                await tools['knowledge.get_document'].ainvoke({'document_id': document_id})
        with pytest.raises(ContextDBError, match='permission denied'):
            await tools['knowledge.get_document'].ainvoke({'document_id': 'denied'})
        with pytest.raises(StoreError):
            await tools['knowledge.delete_documents'].ainvoke({'document_ids': ['inside', 'outside']})
        with pytest.raises(StoreError):
            await tools['knowledge.get_document'].ainvoke({})
        assert official_mcp.calls == [('knowledge.get_document', {'document_id': 'inside'})]
        assert official_mcp.lookups == ['inside', 'outside', 'unknown', 'denied', 'inside', 'outside']
    asyncio.run(exercise())


def test_mcp_scope_does_not_replace_member_permissions(official_mcp):
    from governance.database import connection
    from governance.store import StoreError
    owner = os.environ['TEST_PLATFORM_USER']
    official_mcp.documents['inside'] = {'knowledge_base_id': 'kb1'}

    async def exercise():
        viewer = await official_mcp.load(['kb1'], role='viewer')
        assert 'knowledge.delete_document' not in viewer
        tools = await official_mcp.load(['kb1'], owner_id=owner)
        with connection() as conn:
            conn.execute("UPDATE platform_users SET role='viewer' WHERE id=%s", (owner,))
        await tools['knowledge.search'].ainvoke({'query': '部署'})
        with pytest.raises(StoreError, match='写入权限'):
            await tools['knowledge.delete_document'].ainvoke({'document_id': 'inside'})
        with connection() as conn:
            conn.execute('UPDATE platform_users SET active=false WHERE id=%s', (owner,))
        with pytest.raises(StoreError, match='凭据已变更或账号已停用'):
            await tools['knowledge.search'].ainvoke({'query': '部署'})
        assert len(official_mcp.calls) == 1 and official_mcp.lookups == []
    asyncio.run(exercise())


def test_official_deepagents_interrupt_requires_confirmation():
    from deepagents import create_deep_agent
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.tools import tool
    from langgraph.types import Command
    calls=[]
    class BoundFakeModel(FakeMessagesListChatModel):
        def bind_tools(self,tools,**kwargs):return self
    @tool
    def official_write_fixture(text:str)->str:
        """Fixture for an official write tool requiring confirmation."""
        calls.append(text)
        return 'accepted'
    model=BoundFakeModel(responses=[AIMessage(content='',tool_calls=[{'name':'official_write_fixture','args':{'text':'draft'},'id':'call1','type':'tool_call'}]),AIMessage(content='已完成')])
    with make_checkpointer() as saver:
        graph=create_deep_agent(model=model,tools=[official_write_fixture],checkpointer=saver,
                                interrupt_on={'official_write_fixture':{'allowed_decisions':['approve','reject']}})
        config={'configurable':{'thread_id':'approval-contract'}}
        graph.invoke({'messages':[HumanMessage('修改资料')]},config)
        assert graph.get_state(config).interrupts and calls==[]
        graph.invoke(Command(resume={'decisions':[{'type':'approve'}]}),config)
        assert calls==['draft'] and not graph.get_state(config).interrupts
