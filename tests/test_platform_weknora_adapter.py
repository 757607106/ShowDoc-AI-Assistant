"""The unmodified WeKnora chat contract over real native checkpoint execution."""
import json
import asyncio
import os

import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from governance.database import connection
from tests.test_platform_harness import call, frames, harness, original_prepare


def events(response):
    return [event for _, event in frames(response)]


def test_native_todos_use_the_original_weknora_plan_contract(harness):
    client, sid, model, *_ = harness
    todos = [{'content': 'Read the source', 'status': 'in_progress'},
             {'content': 'Summarize the result', 'status': 'pending'}]
    model.responses = [AIMessage(content='', tool_calls=[call('write_todos', {'todos': todos}, 'native-plan')]),
                       AIMessage(content='Plan prepared')]
    streamed = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Prepare a plan'}))
    result = next(event['data'] for event in streamed if event['response_type'] == 'tool_result')
    expected = [{'id': '0', 'description': 'Read the source', 'status': 'in_progress'},
                {'id': '1', 'description': 'Summarize the result', 'status': 'pending'}]
    assert result['success'], result
    assert result['tool_call_id'] == 'native-plan' and result['tool_name'] == 'todo_write'
    assert result['display_type'] == 'plan' and result['total_steps'] == 2
    assert result['steps'] == expected
    history = client.get(f'/api/v1/messages/{sid}/load').json()['data']
    saved = history[-1]['agent_steps'][0]['tool_calls'][0]['result']['data']
    assert saved['display_type'] == 'plan' and saved['steps'] == expected


def test_native_todo_validation_error_stays_a_tool_error(harness):
    client, sid, model, *_ = harness
    model.responses = [AIMessage(content='', tool_calls=[call('write_todos',
        {'todos': [{'status': 'pending'}]}, 'invalid-plan')]), AIMessage(content='Invalid plan rejected')]
    streamed = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Try an invalid plan'}))
    result = next(event['data'] for event in streamed if event['response_type'] == 'tool_result')
    assert result['tool_call_id'] == 'invalid-plan' and result['success'] is False
    assert result['error'] and not result['steps']
    assert not any(event['response_type'] == 'error' for event in streamed)


@pytest.mark.parametrize('exit_code', [0, 7, None])
@pytest.mark.parametrize('delegated', [False, True])
def test_native_execute_uses_shell_cards_in_stream_history_and_child_replay(harness, exit_code, delegated):
    client, sid, model, tools, *_ = harness
    output = 'combined output\n<stderr>diagnostic</stderr>'
    metadata = {'truncated': True, **({'exit_code': exit_code} if exit_code is not None else {})}

    @tool(response_format='content_and_artifact')
    def execute(command: str) -> tuple[str, dict]:
        """Return an SDK-shaped execution result without running a command."""
        return output, metadata

    tools.append(execute)
    shell = AIMessage(content='', tool_calls=[call('execute', {'command': 'fixture-command'}, 'native-shell')])
    model.responses = ([AIMessage(content='', tool_calls=[call('task', {
        'description': 'Check a command result', 'subagent_type': 'general-purpose'}, 'shell-parent')])]
        if delegated else []) + [shell, AIMessage(content='command checked')] + (
        [AIMessage(content='parent answer')] if delegated else [])
    streamed = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Check the command'}))
    assert not [event for event in streamed if event['response_type'] == 'error'], streamed
    rows = client.get(f'/api/v1/messages/{sid}/load').json()['data']
    if delegated:
        view = rows[-1]['collaboration_status']['tasks'][0]['session_id']
        rows = client.get(f'/api/v1/messages/{view}/load').json()['data']
        streamed = events(client.get(f'/api/v1/sessions/continue-stream/{view}',
            params={'message_id': rows[-1]['id']}))
    else:
        native = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']['messages']
        assert next(message for message in native if message['type'] == 'tool')['name'] == 'execute'
        assert next(message for message in native if message.get('tool_calls'))['tool_calls'][0]['name'] == 'execute'
    projected = next(event['data'] for event in streamed if event['response_type'] == 'tool_call')
    assert projected == {'tool_call_id': 'native-shell', 'tool_name': 'shell_exec',
                         'arguments': {'command': 'fixture-command'}}
    result = next(event['data'] for event in streamed if event['response_type'] == 'tool_result')
    saved = rows[-1]['agent_steps'][0]['tool_calls'][0]
    assert saved['name'] == 'shell_exec' and saved['args'] == {'command': 'fixture-command'}
    for value in (result, saved['result']['data']):
        assert value['tool_call_id'] == 'native-shell' and value['tool_name'] == 'shell_exec'
        assert value['display_type'] == 'shell_exec' and value['command'] == 'fixture-command'
        assert value['output'] == output and value['truncated'] is True
        assert value['success'] is (exit_code in (None, 0))
        assert ('exit_code' in value) is (exit_code is not None)
        if exit_code is not None:
            assert value['exit_code'] == exit_code
        if exit_code == 7:
            assert value['error'] == output
        assert not {'stdout', 'stderr', 'duration_ms', 'work_dir', 'killed'} & value.keys()


@pytest.mark.parametrize('decision', ['approve', 'reject', 'edit'])
def test_shell_approval_replay_keeps_native_execution_and_edited_command(harness, decision):
    client, sid, model, tools, approvals, *_ = harness
    executed = []

    @tool(response_format='content_and_artifact')
    def execute(command: str) -> tuple[str, dict]:
        """Record an approved command without executing it."""
        executed.append(command)
        return 'approved output', {'exit_code': 0, 'truncated': False}

    tools.append(execute)
    approvals['execute'] = {'allowed_decisions': ['approve', 'reject', 'edit']}
    model.responses = [AIMessage(content='', tool_calls=[call('execute',
        {'command': 'original-command'}, 'approval-shell')]), AIMessage(content='command reviewed')]
    first = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Review the command'}))
    assert next(event['data'] for event in first if event['response_type'] == 'tool_call')['tool_name'] == 'shell_exec'
    card = next(event['data'] for event in first if event['response_type'] == 'tool_approval_required')
    assert card['mcp_tool_name'] == 'execute' and executed == []
    body = {'decision': 'reject' if decision == 'reject' else 'approve'}
    if decision == 'edit':
        body['modified_args'] = {'command': 'edited-command'}
    accepted = client.post('/api/v1/agent/tool-approvals/' + card['pending_id'], json=body)
    assert accepted.status_code == 200 and accepted.json()['resumed'] is True
    assert executed == []
    params = {'message_id': first[0]['assistant_message_id'], 'resume_pending_id': card['pending_id']}
    resumed = events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params=params))
    assert resumed[-1]['response_type'] == 'complete', resumed
    assert next(event['data'] for event in resumed if event['response_type'] == 'tool_call')['tool_name'] == 'shell_exec'
    result = next(event['data'] for event in resumed if event['response_type'] == 'tool_result')
    command = 'edited-command' if decision == 'edit' else 'original-command'
    assert result['tool_name'] == 'shell_exec' and result['display_type'] == 'shell_exec'
    assert result['command'] == 'original-command' and result['success'] is (decision != 'reject')
    assert executed == ([] if decision == 'reject' else [command])
    if decision == 'edit':
        assert 'edited-command' in result['output'] and 'approved output' in result['output']
    history = client.get(f'/api/v1/messages/{sid}/load').json()['data']
    saved = history[-1]['agent_steps'][0]['tool_calls'][0]['result']['data']
    assert saved['command'] == 'original-command' and saved['output'] == result['output']
    native = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']['messages']
    assert next(message for message in native if message.get('tool_calls'))['tool_calls'][0] == {
        'name': 'execute', 'args': {'command': 'original-command'}, 'id': 'approval-shell', 'type': 'tool_call'}
    replay = events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params=params))
    assert replay[-1]['response_type'] == 'stop'
    assert executed == ([] if decision == 'reject' else [command])


@pytest.mark.parametrize('endpoint', ['agent-chat', 'knowledge-chat'])
def test_official_weknora_chat_history_and_reconnect_do_not_create_shadow_runs(harness, endpoint):
    client, sid, model, *_ = harness
    streamed = events(client.post(f'/api/v1/{endpoint}/{sid}', json={'query': '官方页面的问题'}))
    assert streamed[0]['response_type'] == 'agent_query'
    identifier = streamed[0]['assistant_message_id']
    assert streamed[-1]['response_type'] == 'complete'
    answers = [event for event in streamed if event['response_type'] == 'answer']
    assert answers[-1]['content'] == '官方 Harness 回答'
    assert answers[-1]['data']['replace'] is True
    response = client.get(f'/api/v1/messages/{sid}/load')
    assert response.status_code == 200, response.text
    rows = response.json()['data']
    assert [row['role'] for row in rows] == ['user', 'assistant']
    assert rows[0]['content'] == '官方页面的问题'
    assert rows[1]['id'] == identifier and rows[1]['content'] == '官方 Harness 回答'
    assert rows[1]['is_completed'] is True
    saved_index = model.i
    replay = events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params={'message_id': identifier}))
    assert replay[-1]['response_type'] == 'stop'
    assert not any(event['response_type'] == 'complete' for event in replay)
    assert model.i == saved_index
    assert client.post(f'/api/v1/sessions/{sid}/stop', json={'message_id': identifier}).status_code == 200
    with connection() as conn:
        assert conn.execute('SELECT count(*) AS n FROM agent_runs WHERE session_id=%s', (sid,)).fetchone()['n'] == 0
        assert conn.execute('SELECT count(*) AS n FROM agent_run_events WHERE run_id IN '
                            '(SELECT id FROM agent_runs WHERE session_id=%s)', (sid,)).fetchone()['n'] == 0


def test_weknora_projection_keeps_tool_ids_results_and_checkpoint_history(harness):
    client, sid, model, tools, *_ = harness
    @tool
    def source_tool(query: str) -> str:
        """Read an original source."""
        return json.dumps({'verified': query})
    tools.append(source_tool)
    model.responses = [AIMessage(content='查原文', tool_calls=[call('source_tool', {'query': 'proof'}, 'native-call')]),
                       AIMessage(content='根据原文回答')]
    streamed = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': '读取来源'}))
    calls = [event['data'] for event in streamed if event['response_type'] == 'tool_call']
    results = [event['data'] for event in streamed if event['response_type'] == 'tool_result']
    assert calls == [{'tool_call_id': 'native-call', 'tool_name': 'source_tool', 'arguments': {'query': 'proof'}}]
    assert len(results) == 1 and results[0]['tool_call_id'] == 'native-call'
    assert results[0]['success'] is True and results[0]['data'] == {'verified': 'proof'}
    rows = client.get(f'/api/v1/messages/{sid}/load').json()['data']
    assert rows[-1]['content'] == '根据原文回答'
    saved_call = rows[-1]['agent_steps'][0]['tool_calls'][0]
    assert saved_call['id'] == 'native-call' and saved_call['result']['success'] is True


def test_weknora_input_and_reconnect_are_owner_scoped_and_do_not_resume_implicitly(harness):
    client, sid, model, *_ = harness
    assert client.post(f'/api/v1/agent-chat/{sid}', json={'query': ''}).status_code == 400
    assert client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'hi'},
                       headers={'Authorization': 'Bearer invalid'}).status_code == 401
    assert client.get(f'/api/v1/sessions/continue-stream/{sid}', params={'message_id': 'forged'}).status_code == 404
    assert client.post(f'/api/v1/sessions/{sid}/stop', json={'message_id': 'forged'}).status_code == 404
    assert client.get(f'/api/v1/sessions/continue-stream/{sid}',
        params={'message_id': 'forged', 'resume_pending_id': 'forged'}).status_code == 409


def test_individual_approvals_stage_without_execution_then_resume_once_on_get(harness):
    client, sid, model, _, approvals, *_ = harness
    model.responses = [AIMessage(content='', tool_calls=[
        call('write_file', {'file_path': '/accepted.txt', 'content': 'yes'}, 'accept-call'),
        call('write_file', {'file_path': '/rejected.txt', 'content': 'no'}, 'reject-call')]),
        AIMessage(content='审批已执行')]
    approvals['write_file'] = {'allowed_decisions': ['approve', 'reject', 'edit']}
    first = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': '分别处理两个文件'}))
    cards = [event['data'] for event in first if event['response_type'] == 'tool_approval_required']
    assert len(cards) == 2 and [card['tool_call_id'] for card in cards] == ['accept-call', 'reject-call']
    identifier = first[0]['assistant_message_id']
    path = '/api/v1/agent/tool-approvals/'
    assert client.post(path + cards[0]['pending_id'], json={'decision': 'approve'}).json() == {'resumed': False}
    after_one = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']
    assert after_one.get('files', {}) == {} and after_one['__interrupt__']
    restored = client.get(f'/api/v1/messages/{sid}/load').json()['data'][-1]
    assert restored['delegated_prompts'][0]['status'] == 'answered'
    assert restored['delegated_prompts'][1]['status'] == 'suspended'
    assert client.post(path + cards[1]['pending_id'], json={'decision': 'reject'}).json() == {'resumed': True}
    assert client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values'].get('files', {}) == {}
    params = {'message_id': identifier, 'resume_pending_id': cards[1]['pending_id']}
    resumed = events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params=params))
    assert not [event for event in resumed if event['response_type'] == 'error'], resumed
    assert [event['data']['tool_call_id'] for event in resumed if event['response_type'] == 'tool_call'] == ['accept-call', 'reject-call']
    assert next(event['data']['arguments'] for event in resumed if event['response_type'] == 'tool_call') == {
        'file_path': '/accepted.txt', 'content': 'yes'}
    assert resumed[-1]['response_type'] == 'complete'
    final = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']
    assert set(final['files']) == {'/accepted.txt'}
    assert len([message for message in final['messages'] if message['type'] == 'human']) == 1
    replay = events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params=params))
    assert replay[-1]['response_type'] == 'stop'
    assert client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values'] == final
    assert client.post(path + cards[0]['pending_id'], json={'decision': 'approve'}).status_code == 409


def test_native_ask_user_card_resumes_via_official_get_stream(harness):
    from agent.interactions import make_interaction_tools
    client, sid, model, tools, *_ = harness
    tools.extend(make_interaction_tools(sid, 'owner'))
    model.responses = [AIMessage(content='', tool_calls=[call('ask_user', {
        'question': '选择哪个来源？', 'options': ['A', 'B']}, 'question-call')]), AIMessage(content='使用A')]
    first = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': '先询问我'}))
    card = next(event['data'] for event in first if event['response_type'] == 'agent_prompt_required')
    assert card['request']['options'] == ['A', 'B'] and card['tool_call_id'] == 'question-call'
    answer = client.post('/api/v1/agent/prompts/' + card['pending_id'],
        json={'kind': 'ask_user', 'response': {'answer': 'A'}})
    assert answer.status_code == 200 and answer.json()['resumed'] is True
    resumed = events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params={
        'message_id': first[0]['assistant_message_id'], 'resume_pending_id': card['pending_id']}))
    assert resumed[-1]['response_type'] == 'complete', resumed
    assert [event['content'] for event in resumed if event['response_type'] == 'answer'][-1] == '使用A'


def test_child_approval_keeps_native_call_id_and_child_answers_out_of_parent(harness):
    client, sid, model, _, approvals, *_ = harness
    model.responses = [AIMessage(content='', tool_calls=[call('task', {
        'subagent_type': 'general-purpose', 'description': 'Write child file'}, 'parent-task')]),
        AIMessage(content='', tool_calls=[call('write_file', {
            'file_path': '/child.txt', 'content': 'child file'}, 'child-write')]),
        AIMessage(content='private child answer'), AIMessage(content='parent final answer')]
    approvals['write_file'] = {'allowed_decisions': ['approve', 'reject', 'edit']}
    first = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': '委派文件任务'}))
    card = next(event['data'] for event in first if event['response_type'] == 'tool_approval_required')
    assert card['tool_call_id'] == 'child-write'
    assert client.post('/api/v1/agent/tool-approvals/' + card['pending_id'], json={
        'decision': 'approve', 'modified_args': {'file_path': '/child.txt', 'content': 'edited child'}}).json()['resumed']
    resumed = events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params={
        'message_id': first[0]['assistant_message_id'], 'resume_pending_id': card['pending_id']}))
    assert resumed[-1]['response_type'] == 'complete', resumed
    assert all('private child answer' not in event['content'] for event in resumed if event['response_type'] == 'answer')
    values = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']
    assert values['files']['/child.txt']['content'] == 'edited child'
    assert client.get(f'/api/v1/messages/{sid}/load').json()['data'][-1]['content'] == 'parent final answer'


def test_protocol_receipts_are_owned_and_removed_when_session_is_cleared(harness):
    from webapi.auth import create_user
    from agent import registry, sessions
    client, sid, model, _, approvals, *_ = harness
    model.responses = [AIMessage(content='', tool_calls=[call('write_file', {
        'file_path': '/pending.txt', 'content': 'pending'}, 'pending-file')])]
    approvals['write_file'] = True
    first = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': '暂停'}))
    card = next(event['data'] for event in first if event['response_type'] == 'tool_approval_required')
    assert client.post('/api/v1/agent/tool-approvals/' + card['pending_id'], json={'decision': 'reject'}).status_code == 200
    assert registry.record('harness_resume', sid, os.environ['TEST_PLATFORM_USER'])['responses']
    other = create_user('other-adapter@example.com', 'Other', 'other-password-123')
    other_sid = sessions.create_session('Other', other)['id']
    forged = other_sid + ':' + card['pending_id'].split(':', 1)[1]
    assert client.post('/api/v1/agent/tool-approvals/' + forged, json={'decision': 'approve'}).status_code == 404
    assert client.delete(f'/api/v1/sessions/{sid}/messages').status_code == 200
    with connection() as conn:
        assert conn.execute("SELECT count(*) AS n FROM runtime_records WHERE kind='harness_resume' AND record_key=%s", (sid,)).fetchone()['n'] == 0


def test_official_stop_endpoint_cancels_only_the_current_http_tool(harness):
    client, sid, model, tools, _, app, headers = harness
    async def scenario():
        started, cancelled = asyncio.Event(), asyncio.Event()
        @tool
        async def waiting_tool() -> str:
            """Wait for the user to stop this request."""
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()
            return 'unreachable'
        tools.append(waiting_tool)
        model.responses = [AIMessage(content='', tool_calls=[call('waiting_tool', {}, 'wait-call')])]
        first, sent = True, []
        async def receive():
            nonlocal first
            if first:
                first = False
                return {'type': 'http.request', 'body': json.dumps({'query': '等待停止'}).encode(), 'more_body': False}
            await asyncio.Event().wait()
        async def send(message):
            sent.append(message)
        scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1', 'method': 'POST',
            'scheme': 'http', 'path': f'/api/v1/agent-chat/{sid}', 'query_string': b'', 'root_path': '',
            'server': ('testserver', 80), 'client': ('127.0.0.1', 1234),
            'headers': [(b'authorization', headers['Authorization'].encode()), (b'content-type', b'application/json')]}
        execution = asyncio.create_task(app(scope, receive, send))
        await asyncio.wait_for(started.wait(), timeout=5)
        data = b''.join(message.get('body', b'') for message in sent).decode()
        identifier = next(json.loads(line[6:])['assistant_message_id'] for line in data.splitlines()
                          if line.startswith('data: ') and 'agent_query' in line)
        response = await asyncio.to_thread(client.post, f'/api/v1/sessions/{sid}/stop', json={'message_id': identifier})
        assert response.status_code == 200, response.text
        await asyncio.wait_for(cancelled.wait(), timeout=2)
        await asyncio.wait_for(execution, timeout=5)
    asyncio.run(scenario())


@pytest.mark.parametrize('explicit', [True, False])
def test_disconnect_before_native_resume_does_not_consume_the_approved_command(harness, explicit):
    from urllib.parse import urlencode
    client, sid, model, _, approvals, app, headers = harness
    model.responses = [AIMessage(content='', tool_calls=[call('write_file', {
        'file_path': '/resume.txt', 'content': 'once'}, 'resume-file')]), AIMessage(content='resumed')]
    approvals['write_file'] = True
    first = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': '稍后恢复'}))
    card = next(event['data'] for event in first if event['response_type'] == 'tool_approval_required')
    assert client.post('/api/v1/agent/tool-approvals/' + card['pending_id'], json={'decision': 'approve'}).json()['resumed']
    params = {'message_id': first[0]['assistant_message_id'], 'resume_pending_id': card['pending_id']}
    async def scenario():
        first_frame = asyncio.Event()
        async def receive():
            await first_frame.wait()
            return {'type': 'http.disconnect'}
        async def send(message):
            if message['type'] == 'http.response.body' and b'agent_query' in message.get('body', b''):
                first_frame.set()
                await asyncio.sleep(0.02)
        scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1', 'method': 'GET',
            'scheme': 'http', 'path': f'/api/v1/sessions/continue-stream/{sid}',
            'query_string': urlencode(params).encode(), 'root_path': '',
            'server': ('testserver', 80), 'client': ('127.0.0.1', 1234),
            'headers': [(b'authorization', headers['Authorization'].encode())]}
        await asyncio.wait_for(app(scope, receive, send), timeout=5)
    asyncio.run(scenario())
    before = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']
    assert before.get('files', {}) == {} and before['__interrupt__']
    retry = params if explicit else {'message_id': params['message_id']}
    resumed = events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params=retry))
    assert resumed[-1]['response_type'] == 'complete', resumed
    final = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']
    assert final['files']['/resume.txt']['content'] == 'once'
    assert len([message for message in final['messages'] if message.get('tool_call_id') == 'resume-file']) == 1


def test_approval_stage_rejects_a_decision_outside_native_review_config(harness):
    client, sid, model, _, approvals, *_ = harness
    model.responses = [AIMessage(content='', tool_calls=[call('write_file', {
        'file_path': '/denied.txt', 'content': 'no'}, 'denied-file')])]
    approvals['write_file'] = {'allowed_decisions': ['reject']}
    first = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': '仅允许拒绝'}))
    card = next(event['data'] for event in first if event['response_type'] == 'tool_approval_required')
    path = '/api/v1/agent/tool-approvals/' + card['pending_id']
    assert client.post(path, json={'decision': 'approve'}).status_code == 400
    assert client.post(path, json={'decision': 'reject'}).json()['resumed'] is True


def test_artifact_downloads_keep_each_turn_version_and_native_binary_bytes(harness):
    from deepagents.backends import StateBackend
    client, sid, model, tools, *_ = harness
    raw = b'\x00\xffbinary\x80\x00'
    @tool
    def upload_binary() -> str:
        """Create a native binary file."""
        result = StateBackend().upload_files([('/image.bin', raw)])
        assert result[0].error is None
        return 'uploaded'
    tools.append(upload_binary)
    model.responses = [AIMessage(content='', tool_calls=[call('write_file', {
        'file_path': '/report.txt', 'content': 'first'}, 'write-first')]), AIMessage(content='first report')]
    first = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': '生成首版'}))
    first_id = first[0]['assistant_message_id']
    first_artifacts = first[-1]['data']['artifacts']
    assert first_artifacts[0]['index'] == 0 and first_artifacts[0]['file_size'] == 5
    model.responses = [AIMessage(content='', tool_calls=[call('edit_file', {
        'file_path': '/report.txt', 'old_string': 'first', 'new_string': 'second'}, 'write-second')]),
        AIMessage(content='', tool_calls=[call('upload_binary', {}, 'native-binary')]), AIMessage(content='second report')]
    second = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': '更新并生成二进制'}))
    assert second[-1]['response_type'] == 'complete', second
    second_id = second[0]['assistant_message_id']
    second_artifacts = second[-1]['data']['artifacts']
    assert [item['source_path'] for item in second_artifacts] == ['/report.txt', '/image.bin']
    base = f'/api/v1/sessions/{sid}/messages/'
    assert client.get(base + first_id + '/artifacts/0/download').content == b'first'
    assert client.get(base + second_id + '/artifacts/0/download').content == b'second'
    assert client.get(base + second_id + '/artifacts/1/download').content == raw
    history = client.get(f'/api/v1/messages/{sid}/load').json()['data']
    assert history[1]['artifacts'] == first_artifacts and history[3]['artifacts'] == second_artifacts
    library = client.get('/api/v1/artifacts').json()['data']
    report = next(item for item in library if item['source_path'] == '/report.txt')
    assert report['version_count'] == 2 and report['message_id'] == second_id
    assert client.get(base + 'assistant:forged' + '/artifacts/0/download').status_code == 404
    with connection() as conn:
        assert conn.execute('SELECT count(*) AS n FROM agent_runs').fetchone()['n'] == 0
        assert conn.execute("SELECT count(*) AS n FROM runtime_records WHERE kind LIKE '%artifact%' ").fetchone()['n'] == 0


def test_native_followups_and_in_chat_oauth_are_explicitly_unavailable(harness):
    client, sid, *_ = harness
    first = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': '完成回答'}))
    identifier = first[0]['assistant_message_id']
    response = client.get(f'/api/v1/sessions/{sid}/messages/{identifier}/suggestions')
    assert response.status_code == 501
    response = client.post('/api/v1/agent/mcp-oauth-resolutions/pending', json={'decision': 'authorize'})
    assert response.status_code == 501


def test_resume_replays_current_pending_tool_but_not_previous_completed_turn(harness):
    client, sid, model, _, approvals, *_ = harness
    model.responses = [AIMessage(content='', tool_calls=[call('write_file', {
        'file_path': '/earlier.txt', 'content': 'earlier'}, 'completed-earlier')]), AIMessage(content='earlier done')]
    events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': '先完成上一轮'}))
    model.responses = [AIMessage(content='', tool_calls=[call('write_file', {
        'file_path': '/current.txt', 'content': 'current'}, 'pending-current')]), AIMessage(content='current done')]
    approvals['write_file'] = True
    first = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': '审批当前轮'}))
    card = next(event['data'] for event in first if event['response_type'] == 'tool_approval_required')
    client.post('/api/v1/agent/tool-approvals/' + card['pending_id'], json={'decision': 'approve'})
    resumed = events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params={
        'message_id': first[0]['assistant_message_id'], 'resume_pending_id': card['pending_id']}))
    calls = [event['data'] for event in resumed if event['response_type'] == 'tool_call']
    assert calls == [{'tool_call_id': 'pending-current', 'tool_name': 'write_file',
                      'arguments': {'file_path': '/current.txt', 'content': 'current'}}]
