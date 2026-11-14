"""Official PostgreSQL checkpoints, owner isolation, SSE and human approval."""
import asyncio
import json
import os
import threading
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, MessagesState, StateGraph

from agent.checkpointer import make_checkpointer
from agent import sessions


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


class FakeAgent:
    def __init__(self,events,pending=False,messages=()):
        self.events=events;self.pending=pending;self.resumed=False;self.messages=messages
    async def aget_state(self,config):
        value={'action_requests':[{'name':'knowledge.update_wiki_page','args':{'page_id':'p','content':'new'}}],
               'review_configs':[{'action_name':'knowledge.update_wiki_page','allowed_decisions':['approve','reject']}]}
        return SimpleNamespace(interrupts=[SimpleNamespace(value=value)] if self.pending and self.resumed else [],
                               values={'messages': self.messages})
    async def astream_events(self,inputs,config=None,version=None):
        if not isinstance(inputs,dict):
            assert inputs.resume['decisions'][0]['type'] in ('approve','reject')
            self.pending=False
        self.resumed=True
        for event in self.events:
            yield event


def frames(response):
    return [json.loads(line[6:]) for line in response.get_data(as_text=True).splitlines() if line.startswith('data: ')]


def test_chat_sse_and_persisted_transcript(authenticated_client,monkeypatch):
    from agent import service
    agent=FakeAgent([{'event':'on_chat_model_stream','data':{'chunk':AIMessage('你好')}},
                     {'event':'on_tool_start','name':'knowledge.search','run_id':'tool1','data':{'input':{'query':'部署'}}},
                     {'event':'on_tool_end','name':'knowledge.search','run_id':'tool1',
                      'data':{'output':ToolMessage(content='{"results": []}',tool_call_id='tool1')}}])
    async def build(*args,**kwargs):return agent
    monkeypatch.setattr(service,'build_agent',build)
    http=authenticated_client
    sid=http.post('/api/v1/sessions',json={}).json['data']['id']
    response=http.post(f'/api/v1/agent-chat/{sid}',json={'query':'部署怎么做'},headers={'X-Request-ID':'unique-question'})
    events=frames(response)
    assert [item['response_type'] for item in events]==['agent_query','answer','tool_call','tool_result','complete']
    assert events[1]['content']=='你好'
    history=http.get(f'/api/v1/messages/{sid}/load').json['data']
    assert [m['content'] for m in history]==['部署怎么做','你好']
    assert http.post(f'/api/v1/agent-chat/{sid}',json={'query':'部署怎么做'},headers={'X-Request-ID':'unique-question'}).status_code==409
    replay=frames(http.get(f'/api/v1/sessions/continue-stream/{sid}?message_id={events[0]["id"]}'))
    assert replay[1]['content']=='你好'


def test_official_citations_keep_document_names_and_ids(authenticated_client,monkeypatch):
    from agent import service
    agent=FakeAgent([{'event':'on_tool_end','name':'knowledge.search','run_id':'tool1','data':{
        'output':SimpleNamespace(content=json.dumps({'results':[{'chunk_id':'chunk-1','document_id':'document-1','knowledge_base_id':'kb-1',
                             'document_name':'来源文档.md','content':'完整官方出处'}]}))}}])
    async def build(*args,**kwargs):return agent
    monkeypatch.setattr(service,'build_agent',build)
    sid=authenticated_client.post('/api/v1/sessions',json={}).json['data']['id']
    events=frames(authenticated_client.post(f'/api/v1/agent-chat/{sid}',json={'query':'查出处','knowledge_base_ids':['kb-1']}))
    ref=next(event for event in events if event['response_type']=='references')['data']['references'][0]
    assert ref['knowledge_title']=='来源文档.md' and ref['knowledge_filename']=='来源文档.md'
    assert (ref['id'],ref['knowledge_id'],ref['knowledge_base_id'])==('chunk-1','document-1','kb-1')
    history=authenticated_client.get(f'/api/v1/messages/{sid}/load').json['data']
    assert history[-1]['knowledge_references'][0]==ref


def test_citations_are_current_scoped_evidence_in_stream_history_and_reconnect(authenticated_client, monkeypatch):
    from agent import service
    from langchain_mcp_adapters.tools import MCPToolArtifact
    chunk = {'chunk_id': 'doc-1_chunk_2', 'document_id': 'doc-1', 'knowledge_base_id': 'kb-1',
             'document_name': '官方手册.md', 'content': '连接池上限为 50。'}
    native = {'chunks': [chunk, {**chunk, 'chunk_id': 'outside', 'knowledge_base_id': 'kb-2'}],
              'truncated': True, 'note': '仅返回部分出处'}
    output = ToolMessage(content='native', tool_call_id='tool1', artifact=MCPToolArtifact(structured_content=native))
    text = '上限为 50。<kb chunk_id="doc-1_chunk_2" kb_id="kb-1" doc="模型伪造标题" />'
    text += '未知<kb chunk_id="invented" kb_id="kb-1" />越界<kb chunk_id="outside" kb_id="kb-2" />'
    text += '\n示例：`<kb chunk_id="literal" />`\n```html\n<kb chunk_id="literal" />\n```'
    agent = FakeAgent([
        {'event': 'on_tool_start', 'name': 'knowledge.list_entity_chunks', 'run_id': 'tool1', 'data': {'input': {'entity_ids': ['e1']}}},
        {'event': 'on_tool_end', 'name': 'knowledge.list_entity_chunks', 'run_id': 'tool1', 'data': {'output': output}},
        *[{'event': 'on_chat_model_stream', 'data': {'chunk': AIMessage(c)}} for c in text],
    ])
    async def build(*args, **kwargs): return agent
    monkeypatch.setattr(service, 'build_agent', build)
    http = authenticated_client
    sid = http.post('/api/v1/sessions', json={}).json['data']['id']
    events = frames(http.post(f'/api/v1/agent-chat/{sid}', json={'query': '连接池上限', 'knowledge_base_ids': ['kb-1']}))
    answer = ''.join(event['content'] for event in events if event['response_type'] == 'answer')
    assert '官方手册.md' in answer and '模型伪造标题' not in answer
    assert 'invented' not in answer and 'outside' not in answer
    assert answer.count('本轮官方结果已截断') == 1
    assert '`<kb chunk_id="literal" />`' in answer and '```html\n<kb chunk_id="literal" />\n```' in answer
    assert len(next(event for event in events if event['response_type'] == 'references')['data']['references']) == 1
    result = next(event for event in events if event['response_type'] == 'tool_result')['data']
    assert result['output'] == native and result['success'] is True
    history = http.get(f'/api/v1/messages/{sid}/load').json['data']
    assert history[-1]['content'] == answer
    replay = frames(http.get(f'/api/v1/sessions/continue-stream/{sid}?message_id={events[0]["id"]}'))
    assert next(event for event in replay if event['response_type'] == 'answer')['content'] == answer
    assert next(event for event in replay if event['response_type'] == 'tool_result')['data'] == result
    agent.events = [{'event': 'on_chat_model_stream', 'data': {'chunk': AIMessage('<kb chunk_id="doc-1_chunk_2" kb_id="kb-1" />')}}]
    next_turn = frames(http.post(f'/api/v1/agent-chat/{sid}', json={'query': '沿用旧引用'}))
    assert not any(event['response_type'] in ('references', 'answer') for event in next_turn)


@pytest.mark.parametrize('failed_native,status', [
    ({'isError': True}, 'success'), ({'success': False}, 'success'),
    ({'errorCode': 4007, 'errorMessage': '当前操作不可用'}, 'success'), ({}, 'error'),
])
def test_failed_official_result_never_registers_evidence(authenticated_client, monkeypatch, failed_native, status):
    from agent import service
    native = {'results': [{'chunk_id': 'c', 'document_id': 'd', 'knowledge_base_id': 'kb',
                           'document_name': '不能引用', 'content': '失败响应中的内容'}], **failed_native}
    agent = FakeAgent([
        {'event': 'on_tool_start', 'name': 'knowledge.search', 'run_id': 't', 'data': {'input': {'query': 'x'}}},
        {'event': 'on_tool_end', 'name': 'knowledge.search', 'run_id': 't',
         'data': {'output': ToolMessage(content=json.dumps(native), tool_call_id='t', status=status)}},
        {'event': 'on_chat_model_stream', 'data': {'chunk': AIMessage('证据不足<kb chunk_id="c" kb_id="kb" />')}},
    ])
    async def build(*args, **kwargs): return agent
    monkeypatch.setattr(service, 'build_agent', build)
    sid = authenticated_client.post('/api/v1/sessions', json={}).json['data']['id']
    events = frames(authenticated_client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'x', 'knowledge_base_ids': ['kb']}))
    assert next(event for event in events if event['response_type'] == 'tool_result')['data']['success'] is False
    assert not any(event['response_type'] == 'references' for event in events)
    assert ''.join(event['content'] for event in events if event['response_type'] == 'answer') == '证据不足'


@pytest.mark.parametrize('failure,terminal', [(RuntimeError('上游连接中断'), 'error'), (asyncio.CancelledError(), 'stop')])
def test_tool_interruption_finishes_steps_and_replays_terminal_state(authenticated_client, monkeypatch, failure, terminal):
    from agent import service
    class InterruptedAgent(FakeAgent):
        async def astream_events(self, *args, **kwargs):
            yield {'event': 'on_tool_start', 'name': 'knowledge.search', 'run_id': 't', 'data': {'input': {'query': 'x'}}}
            raise failure
    async def build(*args, **kwargs): return InterruptedAgent([])
    monkeypatch.setattr(service, 'build_agent', build)
    http = authenticated_client
    sid = http.post('/api/v1/sessions', json={}).json['data']['id']
    events = frames(http.post(f'/api/v1/agent-chat/{sid}', json={'query': 'x'}))
    assert events[-1]['response_type'] == terminal
    result = next(event for event in events if event['response_type'] == 'tool_result')['data']
    assert result['success'] is False and '未收到工具结果' in result['error']
    history = http.get(f'/api/v1/messages/{sid}/load').json['data'][-1]
    assert history['agent_steps'][0]['tool_calls'][0]['result']['success'] is False
    replay = frames(http.get(f'/api/v1/sessions/continue-stream/{sid}?message_id={events[0]["id"]}'))
    assert replay[-1]['response_type'] == terminal
    assert next(event for event in replay if event['response_type'] == 'tool_result')['data'] == result


def test_stop_cancels_a_tool_that_produces_no_more_events(authenticated_client, monkeypatch):
    from agent import service
    started, cancelled, finished = threading.Event(), threading.Event(), threading.Event()
    captured = []
    class BlockedAgent(FakeAgent):
        async def astream_events(self, *args, **kwargs):
            yield {'event': 'on_tool_start', 'name': 'knowledge.search', 'run_id': 'blocked', 'data': {'input': {'query': 'x'}}}
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()
    async def build(*args, **kwargs): return BlockedAgent([])
    monkeypatch.setattr(service, 'build_agent', build)
    http = authenticated_client
    sid = http.post('/api/v1/sessions', json={}).json['data']['id']
    generator = service.stream_chat(sid, 'x', owner_id=os.environ['TEST_PLATFORM_USER'], api_key='ctxdb-fake', role='admin')
    def collect():
        captured.extend(generator)
        finished.set()
    threading.Thread(target=collect, daemon=True).start()
    assert started.wait(5)
    assert http.post(f'/api/v1/sessions/{sid}/stop').status_code == 200
    assert cancelled.wait(3) and finished.wait(3)
    events = [json.loads(frame[6:]) for frame in captured]
    assert events[-1]['response_type'] == 'stop'
    assert next(e for e in events if e['response_type'] == 'tool_result')['data']['success'] is False
    history = http.get(f'/api/v1/messages/{sid}/load').json['data'][-1]
    assert history['run_state'] == 'cancelled' and history['is_completed']
    replay = frames(http.get(f'/api/v1/sessions/continue-stream/{sid}?message_id={events[0]["id"]}'))
    assert replay[-1]['response_type'] == 'stop'


def test_human_confirmation_resumes_once(authenticated_client,monkeypatch):
    from agent import service
    agent=FakeAgent([],pending=True)
    async def build(*args,**kwargs):return agent
    monkeypatch.setattr(service,'build_agent',build)
    http=authenticated_client
    sid=http.post('/api/v1/sessions',json={}).json['data']['id']
    result=frames(http.post(f'/api/v1/agent-chat/{sid}',json={'query':'修改 Wiki'}))
    pending=next(e for e in result if e['response_type']=='tool_approval_required')['data']['pending_id']
    assert http.post(f'/api/v1/agent/tool-approvals/{pending}',json={'decision':'approve'}).status_code==200
    replay=frames(http.get(f'/api/v1/sessions/continue-stream/{sid}?message_id={pending}&resume_pending_id={pending}'))
    assert replay[-1]['response_type']=='complete'
    assert http.post(f'/api/v1/agent/tool-approvals/{pending}',json={'decision':'approve'}).status_code==409


def test_confirmation_restores_only_successful_evidence_from_the_same_turn(authenticated_client, monkeypatch):
    from agent import service
    from langchain_mcp_adapters.tools import MCPToolArtifact
    def evidence(chunk_id, status='success'):
        return ToolMessage(content='native', name='knowledge.search', tool_call_id=chunk_id, status=status,
            artifact=MCPToolArtifact(structured_content={'truncated': True, 'results': [{
                'knowledge_base_id': 'kb', 'document_id': 'doc', 'chunk_id': chunk_id,
                'document_name': '官方来源', 'content': '原文'}]}))
    agent = FakeAgent([], pending=True, messages=[
        HumanMessage('历史问题'), evidence('old'), HumanMessage('本轮问题'),
        evidence('current'), evidence('failed', 'error'),
    ])
    async def build(*args, **kwargs): return agent
    monkeypatch.setattr(service, 'build_agent', build)
    http = authenticated_client
    sid = http.post('/api/v1/sessions', json={}).json['data']['id']
    first = frames(http.post(f'/api/v1/agent-chat/{sid}', json={'query': '本轮问题', 'knowledge_base_ids': ['kb']}))
    pending = next(e for e in first if e['response_type'] == 'tool_approval_required')['data']['pending_id']
    agent.events = [{'event': 'on_chat_model_stream', 'data': {'chunk': AIMessage(
        '当前<kb chunk_id="current" />历史<kb chunk_id="old" />失败<kb chunk_id="failed" />')}}]
    assert http.post(f'/api/v1/agent/tool-approvals/{pending}', json={'decision': 'approve'}).status_code == 200
    replay = frames(http.get(f'/api/v1/sessions/continue-stream/{sid}?message_id={pending}'))
    assert replay[-1]['response_type'] == 'complete'
    answer = next(e for e in replay if e['response_type'] == 'answer')['content']
    assert 'chunk_id="current"' in answer and 'chunk_id="old"' not in answer and 'chunk_id="failed"' not in answer
    assert answer.count('本轮官方结果已截断') == 1
    refs = next(e for e in replay if e['response_type'] == 'references')['data']['references']
    assert [r['id'] for r in refs] == ['current']


def test_chat_requires_session_and_message(authenticated_client):
    assert authenticated_client.post('/api/agent/chat',json={'message':'x'}).status_code==400
    assert authenticated_client.post('/api/agent/chat',json={'session_id':'s'}).status_code==400


def test_build_model_routes_bailian_or_fallback(monkeypatch):
    from agent.graph import build_model
    monkeypatch.delenv('BAILIAN_API_KEY',raising=False)
    monkeypatch.setenv('AGENT_MAIN_MODEL','qwen-max')
    assert build_model().model_name=='qwen-plus'
    monkeypatch.setenv('BAILIAN_API_KEY','sk-bailian-test')
    model=build_model()
    assert model.model_name=='qwen-max' and 'dashscope.aliyuncs.com' in str(model.openai_api_base)


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
    from agent import graph
    monkeypatch.setattr(graph, 'build_model', lambda: object())
    monkeypatch.setattr(graph, 'make_governance_tools', lambda *args: [])
    monkeypatch.setattr('deepagents.create_deep_agent', lambda **kwargs: kwargs)
    agent = asyncio.run(graph.build_agent(None, api_key='ctxdb-fake', owner_id='owner', knowledge_base_ids=[]))
    assert agent['tools'] == [] and official_mcp.clients == []
    assert '未选择知识库' in agent['system_prompt']


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


@pytest.mark.parametrize('legacy', [False, True])
def test_chat_omitted_scope_keeps_selection_and_explicit_empty_clears_it(authenticated_client, monkeypatch, legacy):
    from agent import service
    selected = []
    async def build(*args, **kwargs):
        selected.append(kwargs['knowledge_base_ids'])
        return FakeAgent([])
    monkeypatch.setattr(service, 'build_agent', build)
    sid = authenticated_client.post('/api/v1/sessions', json={}).json['data']['id']
    url = '/api/agent/chat' if legacy else f'/api/v1/agent-chat/{sid}'
    body = {'session_id': sid, 'message': '问题'} if legacy else {'query': '问题'}
    for extra in ({'knowledge_base_ids': ['kb1', 'kb2']}, {}, {'knowledge_base_ids': []}, {}):
        events = frames(authenticated_client.post(url, json={**body, **extra}))
        assert events[-1]['response_type'] == 'complete'
    assert selected == [['kb1', 'kb2'], ['kb1', 'kb2'], [], []]
    assert authenticated_client.get(f'/api/v1/sessions/{sid}').json['data']['agent_config']['knowledge_base_ids'] == []


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
