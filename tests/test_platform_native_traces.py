"""Native tool subgraphs over the unchanged WeKnora child stream contract."""
import asyncio
import json

import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from governance.database import connection
from tests.test_platform_harness import call, frames, harness, original_prepare


def events(response):
    return [value for _, value in frames(response)]


def delegate(model, parent_call='native-parent-call'):
    model.responses = [AIMessage(content='', tool_calls=[call('task', {
        'description': 'Read native files', 'subagent_type': 'general-purpose'}, parent_call)]),
        AIMessage(content='', tool_calls=[call('ls', {'path': '/'}, 'native-child-call')]),
        AIMessage(content='child trace answer'), AIMessage(content='parent final answer')]


def test_native_child_messages_tools_survive_reload_without_shadow_sessions(harness, monkeypatch):
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    client, sid, model, *_ = harness
    delegate(model)
    wire = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Delegate'}))
    assert not [item for item in wire if item['response_type'] == 'error'], wire
    live = [item['data'] for item in wire if item['response_type'] == 'collaboration_status']
    assert live and live[0]['tasks'][0]['status'] == 'running'
    assert live[-1]['tasks'][0]['status'] == 'succeeded'
    assert all('child trace answer' not in item['content'] for item in wire if item['response_type'] == 'answer')
    monkeypatch.setattr(AsyncPostgresSaver, 'alist', lambda *_args, **_kwargs: pytest.fail(
        'A completed task with a native namespace should not scan checkpoints'))
    rows = client.get(f'/api/v1/messages/{sid}/load').json()['data']
    task = rows[-1]['collaboration_status']['tasks'][0]
    assert task['status'] == 'succeeded' and task['name'] == 'general-purpose'
    assert task['run_id'] == ''  # A namespace view is not an independent run.
    view = task['session_id']
    child = client.get(f'/api/v1/messages/{view}/load')
    assert child.status_code == 200, child.text
    child_rows = child.json()['data']
    assert [item['role'] for item in child_rows] == ['user', 'assistant']
    assert child_rows[0]['content'] == 'Read native files'
    assert child_rows[-1]['content'] == 'child trace answer'
    tool = child_rows[-1]['agent_steps'][0]['tool_calls'][0]
    assert tool['id'] == 'native-child-call' and tool['name'] == 'ls'
    assert tool['args'] == {'path': '/'}
    assert tool['result']['success'] is True and tool['result']['output'] == 'No files found'
    model_index = model.i
    replay = events(client.get(f'/api/v1/sessions/continue-stream/{view}', params={'message_id': child_rows[-1]['id']}))
    assert next(item['data'] for item in replay if item['response_type'] == 'tool_call')['tool_call_id'] == 'native-child-call'
    assert replay[-1]['response_type'] == 'stop' and model.i == model_index
    with connection() as conn:
        assert conn.execute('SELECT count(*) AS n FROM agent_sessions').fetchone()['n'] == 1
        assert conn.execute('SELECT count(*) AS n FROM agent_runs').fetchone()['n'] == 0
        assert conn.execute('SELECT count(*) AS n FROM agent_run_events').fetchone()['n'] == 0


def test_child_view_is_authenticated_read_only_and_bound_to_real_namespace(harness):
    from webapi.auth import create_user
    from webapi import weknora_traces
    client, sid, model, *_ = harness
    delegate(model)
    events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Delegate'}))
    task = client.get(f'/api/v1/messages/{sid}/load').json()['data'][-1]['collaboration_status']['tasks'][0]
    view = task['session_id']
    assert client.get(f'/api/v1/messages/{view}/load', headers={'Authorization': 'Bearer invalid'}).status_code == 401
    from agent import sessions
    other = create_user('other-trace@example.com', 'Other', 'other-password-123')
    other_token = client.post('/api/v1/auth/login', json={
        'email': 'other-trace@example.com', 'password': 'other-password-123'}).json()['token']
    assert client.get(f'/api/v1/messages/{view}/load', headers={
        'Authorization': 'Bearer ' + other_token}).status_code == 404
    foreign = sessions.create_session('Other', other)['id']
    parent, namespace, call_id = weknora_traces.decode(view)
    forged = weknora_traces.locator(foreign, namespace, call_id)
    assert client.get(f'/api/v1/messages/{forged}/load').status_code == 404
    assert client.get(f'/api/v1/messages/{view}tampered/load').status_code == 404
    unknown = weknora_traces.locator(parent, 'tools:unknown', call_id)
    assert client.get(f'/api/v1/messages/{unknown}/load').status_code == 404
    wrong_call = weknora_traces.locator(parent, namespace, 'another-call')
    assert client.get(f'/api/v1/messages/{wrong_call}/load').status_code == 501
    identifier = client.get(f'/api/v1/messages/{view}/load').json()['data'][-1]['id']
    assert client.get(f'/api/v1/sessions/continue-stream/{view}', params={
        'message_id': identifier, 'resume_pending_id': 'forged'}).status_code == 409
    assert client.post(f'/api/v1/agent-chat/{view}', json={'query': 'Execute forged view'}).status_code == 404


def test_dynamic_delta_child_history_is_explicitly_unsupported(harness, monkeypatch):
    from deepagents import create_deep_agent
    from deepagents.graph import DeepAgentState
    from webapi import harness as api
    client, sid, model, *_ = harness
    async def graph(saver, user, selected, resolved, **kwargs):
        return create_deep_agent(model=model, checkpointer=saver, state_schema=DeepAgentState)
    monkeypatch.setattr(api, '_graph', graph)
    delegate(model)
    wire = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Delegate'}))
    task = next(item['data']['tasks'][0] for item in wire if item['response_type'] == 'collaboration_status')
    response = client.get(f'/api/v1/messages/{task["session_id"]}/load')
    assert response.status_code == 501 and 'DeltaChannel' in response.json()['message']
    assert client.get(f'/api/v1/messages/{sid}/load').status_code == 501


def test_reused_child_tool_ids_in_separate_parent_turns_keep_native_namespace_lineage(harness):
    client, sid, model, *_ = harness
    delegate(model)
    first = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'First delegation'}))
    delegate(model, parent_call='second-parent-call')
    second = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Second delegation'}))
    assert not [e for e in first + second if e['response_type'] == 'error']
    rows = client.get(f'/api/v1/messages/{sid}/load').json()['data']
    children = [row['collaboration_status']['tasks'] for row in rows if row['role'] == 'assistant']
    assert [len(group) for group in children] == [1, 1]
    assert children[0][0]['session_id'] != children[1][0]['session_id']
    for group in children:
        child = client.get(f'/api/v1/messages/{group[0]["session_id"]}/load').json()['data']
        assert child[-1]['agent_steps'][0]['tool_calls'][0]['id'] == 'native-child-call'


def test_child_tool_error_remains_failure_in_live_restored_tool_result(harness):
    client, sid, model, *_ = harness
    model.responses = [AIMessage(content='', tool_calls=[call('task', {
        'description': 'Read missing file', 'subagent_type': 'general-purpose'}, 'parent-read')]),
        AIMessage(content='', tool_calls=[call('read_file', {'file_path': '/missing'}, 'child-read')]),
        AIMessage(content='No file'), AIMessage(content='Explained missing file')]
    wire = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Read'}))
    task = [e['data']['tasks'][0] for e in wire if e['response_type'] == 'collaboration_status'][-1]
    rows = client.get(f'/api/v1/messages/{task["session_id"]}/load').json()['data']
    result = rows[-1]['agent_steps'][0]['tool_calls'][0]['result']
    assert result['success'] is False and result['error']
    restored = events(client.get(f'/api/v1/sessions/continue-stream/{task["session_id"]}',
        params={'message_id': rows[-1]['id']}))
    assert next(e['data'] for e in restored if e['response_type'] == 'tool_result')['success'] is False


def test_child_hitl_history_waits_and_parent_approval_resumes_same_namespace(harness):
    client, sid, model, _, approvals, *_ = harness
    model.responses = [AIMessage(content='', tool_calls=[call('task', {
        'description': 'Write approved file', 'subagent_type': 'general-purpose'}, 'parent-write')]),
        AIMessage(content='', tool_calls=[call('write_file', {
            'file_path': '/child-proof.txt', 'content': 'approved'}, 'child-write')]),
        AIMessage(content='Child wrote file'), AIMessage(content='Parent confirmed')]
    approvals['write_file'] = True
    wire = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Approve child write'}))
    card = next(e['data'] for e in wire if e['response_type'] == 'tool_approval_required')
    task = client.get(f'/api/v1/messages/{sid}/load').json()['data'][-1]['collaboration_status']['tasks'][0]
    assert task['status'] == 'waiting'
    child = client.get(f'/api/v1/messages/{task["session_id"]}/load').json()['data'][-1]
    assert child['run_state'] == 'awaiting_input' and child['is_completed'] is False
    assert client.post('/api/v1/agent/tool-approvals/' + card['pending_id'], json={'decision': 'approve'}).json()['resumed']
    resumed = events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params={
        'message_id': wire[0]['assistant_message_id'], 'resume_pending_id': card['pending_id']}))
    assert resumed[-1]['response_type'] == 'complete', resumed
    task_after = client.get(f'/api/v1/messages/{sid}/load').json()['data'][-1]['collaboration_status']['tasks'][0]
    assert task_after['session_id'] == task['session_id'] and task_after['status'] == 'succeeded'
    child = client.get(f'/api/v1/messages/{task["session_id"]}/load').json()['data'][-1]
    assert child['content'] == 'Child wrote file' and child['is_completed'] is True
    assert child['agent_steps'][0]['tool_calls'][0]['id'] == 'child-write'


@pytest.mark.parametrize('exit_mode', ['complete', 'child_disconnect', 'parent_disconnect', 'child_header_failure', 'other_worker', 'references'])
def test_live_child_observes_the_single_native_request_and_releases_subscriptions(harness, exit_mode, monkeypatch):
    from urllib.parse import urlencode
    from webapi import weknora_traces
    client, sid, model, tools, _, app, headers = harness
    if exit_mode == 'references':
        from webapi import harness as api
        monkeypatch.setattr(api, '_prepare', lambda *args: {
            'agent_config': {'access_level': 'confirm'}, 'knowledge_base_ids': ['allowed-kb']})

    async def scenario():
        started, release, cancelled = asyncio.Event(), asyncio.Event(), asyncio.Event()
        parent_disconnect, child_disconnect = asyncio.Event(), asyncio.Event()
        first_child_frame = asyncio.Event()
        invocations = []

        tool_name = 'knowledge.search' if exit_mode == 'references' else 'child_wait'
        @tool(tool_name)
        async def child_wait() -> str:
            """Wait inside the native child for this verification."""
            invocations.append('native child executed')
            started.set()
            try:
                await release.wait()
            finally:
                cancelled.set()
            if exit_mode == 'references':
                return json.dumps({'proof': 'native child tool result', 'results': [
                    {'knowledge_base_id': 'allowed-kb', 'document_id': 'allowed-doc',
                     'chunk_id': 'allowed-chunk', 'document_name': 'doc-source.html',
                     'metadata': {'title': '子图采购说明'}, 'content': 'Original allowed source'},
                    {'knowledge_base_id': 'foreign-kb', 'document_id': 'foreign-doc',
                     'chunk_id': 'foreign-chunk', 'content': 'Out of authorized scope'}]})
            return 'native child tool result'

        tools.append(child_wait)
        model.responses = [AIMessage(content='', tool_calls=[call('task', {
            'description': 'Observe one native child', 'subagent_type': 'general-purpose'}, 'live-parent')]),
            AIMessage(content='', tool_calls=[call(tool_name, {}, 'live-child-tool')]),
            AIMessage(content='live child answer'), AIMessage(content='live parent answer')]
        parent_sent, child_sent = [], []
        first = True

        def scope(path, method='GET', query=b''):
            return {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1', 'method': method,
                'scheme': 'http', 'path': path, 'query_string': query, 'root_path': '',
                'server': ('testserver', 80), 'client': ('127.0.0.1', 1234),
                'headers': [(b'authorization', headers['Authorization'].encode()), (b'content-type', b'application/json')]}

        async def parent_receive():
            nonlocal first
            if first:
                first = False
                return {'type': 'http.request', 'body': b'{"query":"Delegate live","knowledge_base_ids":["foreign-kb"]}', 'more_body': False}
            await parent_disconnect.wait()
            return {'type': 'http.disconnect'}

        async def parent_send(message):
            parent_sent.append(message)

        execution = asyncio.create_task(app(scope(f'/api/v1/agent-chat/{sid}', 'POST'), parent_receive, parent_send))
        await asyncio.wait_for(started.wait(), 5)
        trace = weknora_traces.active[sid]
        namespace, node = next(iter(trace.nodes.items()))
        if exit_mode == 'other_worker':
            # Another worker sees the same PG checkpoint and request lock, but no local transport.
            weknora_traces.active.pop(sid)
            try:
                unavailable = await asyncio.to_thread(client.get, f'/api/v1/messages/{node["view"]}/load')
                assert unavailable.status_code == 409 and '另一 API 进程' in unavailable.json()['message']
                assert invocations == ['native child executed'] and not cancelled.is_set()
            finally:
                weknora_traces.active[sid] = trace
        response = await asyncio.to_thread(client.get, f'/api/v1/messages/{node["view"]}/load')
        assert response.status_code == 200, response.text
        target = response.json()['data'][-1]
        assert target['is_completed'] is False

        async def child_receive():
            await child_disconnect.wait()
            return {'type': 'http.disconnect'}

        class ClosedHeaders(RuntimeError):
            pass

        async def child_send(message):
            if exit_mode == 'child_header_failure' and message['type'] == 'http.response.start':
                raise ClosedHeaders('child closed before headers')
            child_sent.append(message)
            if b'live-child-tool' in message.get('body', b''):
                first_child_frame.set()

        observation = asyncio.create_task(app(scope(f'/api/v1/sessions/continue-stream/{node["view"]}',
            query=urlencode({'message_id': target['id']}).encode()), child_receive, child_send))
        if exit_mode == 'child_header_failure':
            with pytest.raises(ClosedHeaders):
                await asyncio.wait_for(observation, 5)
            assert not trace.subscribers[namespace]
        else:
            await asyncio.wait_for(first_child_frame.wait(), 5)
        if exit_mode == 'child_disconnect':
            child_disconnect.set()
            await asyncio.wait_for(observation, 5)
            assert not trace.subscribers[namespace]
            assert not cancelled.is_set() and not execution.done()
        if exit_mode == 'parent_disconnect':
            parent_disconnect.set()
            await asyncio.wait_for(execution, 5)
            # The official run keeps executing after the parent HTTP disconnect.
            assert not cancelled.is_set() and invocations == ['native child executed']
        release.set()
        await asyncio.wait_for(execution, 5)
        if exit_mode not in ('child_disconnect', 'child_header_failure'):
            await asyncio.wait_for(observation, 5)
        from webapi import harness as api
        # A detached parent keeps live traces until its run bookkeeping finishes.
        await asyncio.wait_for(asyncio.gather(*api._followers), 5)
        assert cancelled.is_set() and invocations == ['native child executed']
        assert sid not in weknora_traces.active
        assert all(not subscribers for subscribers in trace.subscribers.values())
        if exit_mode in ('complete', 'references'):
            child_wire = b''.join(m.get('body', b'') for m in child_sent).decode()
            assert 'live child answer' in child_wire and 'native child tool result' in child_wire
            assert 'live parent answer' not in child_wire
            parent_wire = b''.join(m.get('body', b'') for m in parent_sent).decode()
            parent_answers = [json.loads(line[6:])['content'] for line in parent_wire.splitlines()
                if line.startswith('data: ') and json.loads(line[6:]).get('response_type') == 'answer']
            assert 'live child answer' not in parent_answers
            if exit_mode == 'references':
                child_events = [json.loads(line[6:]) for line in child_wire.splitlines() if line.startswith('data: ')]
                citations = next(item['data']['references'] for item in child_events if item['response_type'] == 'references')
                assert [item['id'] for item in citations] == ['allowed-chunk']
                assert citations[0]['document_display_name'] == '子图采购说明.html'
                saved = await asyncio.to_thread(client.get, f'/api/v1/messages/{node["view"]}/load')
                assert [item['id'] for item in saved.json()['data'][-1]['knowledge_references']] == ['allowed-chunk']
                assert saved.json()['data'][-1]['knowledge_references'][0]['document_display_name'] == '子图采购说明.html'
                model_index = model.i
                replay = events(await asyncio.to_thread(client.get, f'/api/v1/sessions/continue-stream/{node["view"]}',
                    params={'message_id': saved.json()['data'][-1]['id']}))
                result = next(item['data'] for item in replay if item['response_type'] == 'tool_result')
                source = result['data']['results'][0]
                assert source['document_name'] == 'doc-source.html'
                assert source['document_display_name'] == '子图采购说明.html'
                assert model.i == model_index
        if exit_mode == 'parent_disconnect':
            saved = await asyncio.to_thread(client.get, f'/api/v1/messages/{node["view"]}/load')
            assert saved.status_code == 200
            # The detached run finishes instead of staying interrupted.
            assert saved.json()['data'][-1].get('run_state') != 'interrupted', saved.json()
            assert saved.json()['data'][-1]['is_completed'] is True, saved.json()
    asyncio.run(scenario())


def test_child_subscriber_overflow_is_bounded_and_requests_history_refresh():
    from webapi.weknora_adapter import StreamProjection
    from webapi.weknora_traces import LiveTraces
    trace = LiveTraces('parent', StreamProjection('parent', 'turn'))
    trace.nodes['native-ns'] = {'projection': StreamProjection('view', 'child')}
    queue = trace.subscribe('native-ns')
    for _ in range(129):
        trace.publish('native-ns', {'response_type': 'answer'})
    assert queue.qsize() == 2
    assert queue.get_nowait()['response_type'] == 'error'
    assert queue.get_nowait() is None
    assert not trace.subscribers['native-ns']


def test_nested_full_state_children_use_their_own_native_parent_scope(harness, monkeypatch):
    from deepagents import create_deep_agent
    from deepagents.backends import StateBackend
    from deepagents.middleware.subagents import SubAgentMiddleware
    from webapi import harness as api
    client, sid, model, *_ = harness
    @tool
    def leaf_read() -> str:
        """Read a deterministic original source."""
        return 'leaf tool proof'
    async def graph(saver, user, selected, resolved, **kwargs):
        leaf = {'name': 'leaf', 'description': 'Read sources', 'model': model, 'tools': [leaf_read]}
        branch = {'name': 'branch', 'description': 'Delegate source reads', 'model': model, 'tools': [],
                  'middleware': [SubAgentMiddleware(subagents=[leaf], backend=StateBackend())]}
        return create_deep_agent(model=model, checkpointer=saver, subagents=[branch])
    monkeypatch.setattr(api, '_graph', graph)
    model.responses = [AIMessage(content='', tool_calls=[call('task', {
        'description': 'Branch assignment', 'subagent_type': 'branch'}, 'root-to-branch')]),
        AIMessage(content='', tool_calls=[call('task', {
            'description': 'Leaf assignment', 'subagent_type': 'leaf'}, 'branch-to-leaf')]),
        AIMessage(content='', tool_calls=[call('leaf_read', {}, 'leaf-source-call')]),
        AIMessage(content='Leaf answer'), AIMessage(content='Branch answer'), AIMessage(content='Root answer')]
    wire = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Nested delegation'}))
    assert not [item for item in wire if item['response_type'] == 'error'], wire
    root = client.get(f'/api/v1/messages/{sid}/load')
    assert root.status_code == 200, root.text
    branch = root.json()['data'][-1]['collaboration_status']['tasks']
    assert len(branch) == 1 and branch[0]['name'] == 'branch'
    branch_rows = client.get(f'/api/v1/messages/{branch[0]["session_id"]}/load')
    assert branch_rows.status_code == 200, branch_rows.text
    leaf = branch_rows.json()['data'][-1]['collaboration_status']['tasks']
    assert len(leaf) == 1 and leaf[0]['name'] == 'leaf'
    leaf_rows = client.get(f'/api/v1/messages/{leaf[0]["session_id"]}/load').json()['data']
    assert leaf_rows[-1]['content'] == 'Leaf answer'
    assert leaf_rows[-1]['agent_steps'][0]['tool_calls'][0]['id'] == 'leaf-source-call'


def test_native_child_exception_is_failed_in_live_and_history(harness, monkeypatch):
    from deepagents import create_deep_agent
    from tests.test_platform_harness import Model
    from webapi import harness as api
    client, sid, *_ = harness
    class FailingModel(Model):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            if messages[-1].content == 'Fail inside child':
                raise RuntimeError('native child model failure')
            return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
    model = FailingModel(responses=[AIMessage(content='', tool_calls=[call('task', {
        'description': 'Fail inside child', 'subagent_type': 'general-purpose'}, 'failing-child')])])
    async def graph(saver, user, selected, resolved, **kwargs):
        return create_deep_agent(model=model, checkpointer=saver)
    monkeypatch.setattr(api, '_graph', graph)
    wire = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Delegate failure'}))
    assert any('native child model failure' in item['content'] for item in wire if item['response_type'] == 'error'), wire
    live = [item['data']['tasks'][0] for item in wire if item['response_type'] == 'collaboration_status']
    assert live[-1]['status'] == 'failed', live
    response = client.get(f'/api/v1/messages/{sid}/load')
    assert response.status_code == 200, response.text
    assert response.json()['data'][-1]['collaboration_status']['tasks'][0]['status'] == 'failed'


def test_rewind_hides_discarded_native_child_views_without_deleting_checkpoint_audit(harness):
    client, sid, model, *_ = harness
    delegate(model, 'first-parent')
    events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'First child'}))
    first = client.get(f'/api/v1/messages/{sid}/load').json()['data'][-1]
    first_view = first['collaboration_status']['tasks'][0]['session_id']
    delegate(model, 'second-parent')
    events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Second child'}))
    second = client.get(f'/api/v1/messages/{sid}/load').json()['data'][-1]
    second_view = second['collaboration_status']['tasks'][0]['session_id']
    response = client.post(f'/api/v1/sessions/{sid}/rewind', json={'message_id': first['id']})
    assert response.status_code == 200, response.text
    assert client.get(f'/api/v1/messages/{first_view}/load').status_code == 200
    assert client.get(f'/api/v1/messages/{second_view}/load').status_code == 404
    current = client.get(f'/api/v1/messages/{sid}/load')
    assert current.status_code == 200, current.text
    assert current.json()['data'][-1]['collaboration_status']['tasks'][0]['session_id'] == first_view
