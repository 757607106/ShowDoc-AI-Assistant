"""Session titles use the real owner-scoped DB, native Harness and SSE contract."""
import asyncio
import inspect
import os

import pytest
from langchain_core.messages import AIMessage

from agent import registry, sessions
from governance.database import connection
from tests.test_platform_harness import call, frames, harness, original_prepare


@pytest.fixture
def title_model(monkeypatch, authenticated_client):
    from agent import session_titles

    owner = os.environ['TEST_PLATFORM_USER']
    saved = registry.save_model({'name': 'qwen-plus', 'type': 'KnowledgeQA', 'source': 'remote',
        'parameters': {'provider': 'aliyun', 'base_url': 'https://fixture.invalid/v1',
                       'api_key': 'title-fixture-secret'}}, owner)
    response = authenticated_client.put('/api/v1/tenants/kv/default-settings', json={
        'chat_model_id': saved['id'], 'utility_model_id': saved['id']})
    assert response.status_code == 200, response.json
    state = {'calls': [], 'builds': [], 'result': '数据库查询指南', 'invoke': None}

    class TitleModel:
        async def ainvoke(self, messages, **kwargs):
            state['calls'].append(messages)
            if state['invoke']:
                result = state['invoke'](messages)
                if inspect.isawaitable(result):
                    result = await result
            else:
                result = state['result']
            return result if isinstance(result, AIMessage) else AIMessage(content=result)

    def build(saved_model, config):
        state['builds'].append((saved_model, config))
        return TitleModel()

    monkeypatch.setattr(session_titles, 'build_model_record', build)
    state['saved'] = saved
    return state


def new_session(client):
    response = client.post('/api/v1/sessions', json={})
    assert response.status_code == 200, response.text
    selected = response.json()['data']
    assert selected['title'] == ''
    return selected['id']


def wire(response):
    return [data for kind, data in frames(response) if kind == 'message']


def test_first_turn_persists_title_before_terminal_event_and_never_regenerates(harness, title_model):
    client, _, *_ = harness
    sid = new_session(client)
    events = wire(client.post(f'/api/v1/agent-chat/{sid}', json={'query': '如何查询数据库？'}))
    assert not [event for event in events if event['response_type'] == 'error'], events
    assert any(event['response_type'] == 'answer' and '官方 Harness 回答' in event['content'] for event in events)
    title = next(event for event in events if event['response_type'] == 'session_title')
    assert title['data'] == {'session_id': sid, 'title': '数据库查询指南'}
    assert events.index(title) < next(index for index, event in enumerate(events)
                                      if event['response_type'] in ('complete', 'stop'))
    assert client.get(f'/api/v1/sessions/{sid}').json()['data']['title'] == '数据库查询指南'
    assert next(row for row in client.get('/api/v1/sessions').json()['data'] if row['id'] == sid)['title'] == '数据库查询指南'
    again = wire(client.post(f'/api/v1/agent-chat/{sid}', json={'query': '继续查询'}))
    assert not [event for event in again if event['response_type'] in ('error', 'session_title')], again
    assert len(title_model['calls']) == 1


def test_title_uses_actual_human_text_and_default_model_not_injected_blocks(harness, title_model, monkeypatch):
    from webapi import harness as api

    client, _, *_ = harness
    sid = new_session(client)
    monkeypatch.setattr(api, '_prepare', lambda *args: {
        'agent_config': {'access_level': 'confirm'}, 'knowledge_base_ids': [],
        'message_blocks': [{'type': 'text', 'text': 'INTERNAL_ATTACHMENT_INSTRUCTION'}]})
    events = wire(client.post(f'/api/v1/agent-chat/{sid}', json={'query': '  仅依据我的原始问题  '}))
    assert not [event for event in events if event['response_type'] == 'error'], events
    messages = title_model['calls'][0]
    assert '仅依据我的原始问题' in messages[-1].content
    assert 'INTERNAL_ATTACHMENT_INSTRUCTION' not in str(messages)
    saved, config = title_model['builds'][0]
    assert saved['id'] == title_model['saved']['id']
    assert saved['parameters']['api_key'] == 'title-fixture-secret'
    assert config['thinking'] is False and config['temperature'] == 0.3


@pytest.mark.parametrize('existing', ['我的手工标题', '新会话'])
def test_existing_titles_are_preserved_in_stream_and_generate_endpoint(harness, title_model, existing):
    client, _, *_ = harness
    sid = sessions.create_session(existing, os.environ['TEST_PLATFORM_USER'])['id']
    events = wire(client.post(f'/api/v1/agent-chat/{sid}', json={'query': '不要替换已有标题'}))
    assert not [event for event in events if event['response_type'] in ('error', 'session_title')], events
    response = client.post(f'/api/v1/sessions/{sid}/generate_title', json={'messages': []})
    assert response.status_code == 200, response.text
    assert response.json()['data'] == existing
    assert sessions.get_session(sid, os.environ['TEST_PLATFORM_USER'])['title'] == existing
    assert title_model['calls'] == []


@pytest.mark.parametrize('path,disabled,expected', [
    ('knowledge-chat', True, False), ('knowledge-chat', False, True), ('agent-chat', True, True)])
def test_disable_title_matches_native_chat_route_semantics(harness, title_model, path, disabled, expected):
    client, _, *_ = harness
    sid = new_session(client)
    events = wire(client.post(f'/api/v1/{path}/{sid}', json={'query': '标题开关', 'disable_title': disabled}))
    assert not [event for event in events if event['response_type'] == 'error'], events
    assert bool([event for event in events if event['response_type'] == 'session_title']) is expected
    assert bool(title_model['calls']) is expected
    assert bool(sessions.get_session(sid, os.environ['TEST_PLATFORM_USER'])['title']) is expected


@pytest.mark.parametrize('failure', ['provider', 'timeout'])
def test_title_failure_or_timeout_keeps_answer_and_empty_title(harness, title_model, failure):
    client, _, *_ = harness
    sid = new_session(client)
    cancelled = []

    async def invoke(_messages):
        if failure == 'provider':
            raise RuntimeError('title provider failed')
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(True)

    title_model['invoke'] = invoke
    events = wire(client.post(f'/api/v1/agent-chat/{sid}', json={'query': '标题失败时继续回答'}))
    assert not [event for event in events if event['response_type'] in ('error', 'session_title')], events
    assert any(event['response_type'] == 'answer' and '官方 Harness 回答' in event['content'] for event in events)
    assert events[-1]['response_type'] == 'complete'
    assert sessions.get_session(sid, os.environ['TEST_PLATFORM_USER'])['title'] == ''
    if failure == 'timeout':
        assert cancelled == [True]


def test_paused_approval_generates_once_and_resume_keeps_same_title(harness, title_model):
    client, _, model, _, approvals, *_ = harness
    sid = new_session(client)
    model.responses = [AIMessage(content='', tool_calls=[call('write_file', {
        'file_path': '/title-proof.txt', 'content': 'approved'})]), AIMessage(content='已确认')]
    approvals['write_file'] = True
    first = wire(client.post(f'/api/v1/agent-chat/{sid}', json={'query': '确认后写入文件'}))
    card = next(event['data'] for event in first if event['response_type'] == 'tool_approval_required')
    assert [event['response_type'] for event in first].index('session_title') < [
        event['response_type'] for event in first].index('complete')
    approved = client.post('/api/v1/agent/tool-approvals/' + card['pending_id'], json={'decision': 'approve'})
    assert approved.status_code == 200 and approved.json()['resumed']
    resumed = wire(client.get(f'/api/v1/sessions/continue-stream/{sid}', params={
        'message_id': first[0]['assistant_message_id'], 'resume_pending_id': card['pending_id']}))
    assert resumed[-1]['response_type'] == 'complete', resumed
    assert not [event for event in resumed if event['response_type'] in ('error', 'session_title')], resumed
    assert len(title_model['calls']) == 1
    assert sessions.get_session(sid, os.environ['TEST_PLATFORM_USER'])['title'] == '数据库查询指南'


def test_manual_rename_during_model_call_wins_compare_and_set(harness, title_model):
    client, _, *_ = harness
    sid = new_session(client)
    owner = os.environ['TEST_PLATFORM_USER']

    def rename(_messages):
        sessions.touch_session(sid, '用户在生成期间改名', owner)
        return '模型迟到的标题'

    title_model['invoke'] = rename
    response = client.post(f'/api/v1/sessions/{sid}/generate_title', json={
        'messages': [{'role': 'user', 'content': '生成标题'}]})
    assert response.status_code == 200, response.text
    assert response.json()['data'] == '用户在生成期间改名'
    assert sessions.get_session(sid, owner)['title'] == '用户在生成期间改名'


def test_empty_messages_reads_first_real_checkpoint_message(harness, title_model):
    client, _, *_ = harness
    sid = new_session(client)
    for query in ('第一条真实用户问题', '后续用户问题不可替代第一条'):
        events = wire(client.post(f'/api/v1/knowledge-chat/{sid}', json={
            'query': query, 'disable_title': True}))
        assert not [event for event in events if event['response_type'] in ('error', 'session_title')], events
    assert title_model['calls'] == []
    response = client.post(f'/api/v1/sessions/{sid}/generate_title', json={'messages': []})
    assert response.status_code == 200, response.text
    assert response.json()['data'] == '数据库查询指南'
    assert '第一条真实用户问题' in title_model['calls'][0][-1].content
    assert '后续用户问题不可替代第一条' not in title_model['calls'][0][-1].content


def test_generate_endpoint_returns_string_and_uses_header_language(harness, title_model):
    client, _, *_ = harness
    sid = new_session(client)
    response = client.post(f'/api/v1/sessions/{sid}/generate_title', headers={
        'Accept-Language': 'en-US,en;q=0.9'}, json={'language': 'zh-CN', 'messages': [
        {'role': 'system', 'content': '不应成为标题来源'},
        {'role': 'assistant', 'content': '也不应成为标题来源'},
        {'role': 'user', 'content': 'Explain database transactions'},
        {'role': 'human', 'content': 'Later question'}]})
    assert response.status_code == 200, response.text
    assert response.json()['data'] == '数据库查询指南'
    messages = title_model['calls'][0]
    assert 'English' in messages[0].content
    assert 'Explain database transactions' in messages[-1].content
    assert 'Later question' not in messages[-1].content
    assert '不应成为标题来源' not in str(messages)


def test_harness_title_uses_resolved_model_and_request_language(harness, title_model, monkeypatch):
    from webapi import harness as api

    client, _, *_ = harness
    sid = new_session(client)
    alternate = registry.save_model({'name': 'qwen-max', 'type': 'KnowledgeQA',
        'parameters': {'provider': 'aliyun', 'base_url': 'https://alternate.invalid/v1',
                       'api_key': 'alternate-title-key'}}, os.environ['TEST_PLATFORM_USER'])
    monkeypatch.setattr(api, '_prepare', lambda *args: {
        'agent_config': {'access_level': 'confirm', 'model_id': alternate['id']}, 'knowledge_base_ids': []})
    events = wire(client.post(f'/api/v1/agent-chat/{sid}', headers={'Accept-Language': 'en-US'},
        json={'query': 'Use the selected model'}))
    assert not [event for event in events if event['response_type'] == 'error'], events
    assert title_model['builds'][0][0]['id'] == alternate['id']
    assert 'English' in title_model['calls'][0][0].content


def test_generate_endpoint_rejects_invalid_message_contract_without_model_io(harness, title_model):
    client, _, *_ = harness
    sid = new_session(client)
    for body in ({}, {'messages': 'not a list'}, {'messages': [None]},
                 {'messages': [{'role': 1, 'content': 'invalid'}]},
                 {'messages': [{'role': 'user', 'content': ['invalid']}]},
                 {'messages': [{'role': 'assistant', 'content': 'no human'}]},
                 {'messages': [{'role': 'user', 'content': '  '}]},
                 {'messages': [{'role': 'user', 'content': 'x' * 100_001}]}):
        response = client.post(f'/api/v1/sessions/{sid}/generate_title', json=body)
        assert response.status_code == 400, (body, response.text)
    assert title_model['calls'] == []
    assert sessions.get_session(sid, os.environ['TEST_PLATFORM_USER'])['title'] == ''


def test_existing_title_still_requires_valid_body_and_legacy_stays_read_only(harness, title_model):
    client, _, *_ = harness
    sid = sessions.create_session('手工标题', os.environ['TEST_PLATFORM_USER'])['id']
    assert client.post(f'/api/v1/sessions/{sid}/generate_title', json={}).status_code == 400
    with connection() as conn:
        conn.execute("UPDATE agent_sessions SET agent_config=jsonb_build_object('runtime','legacy') WHERE id=%s", (sid,))
    assert client.post(f'/api/v1/sessions/{sid}/generate_title', json={}).status_code == 410
    assert title_model['calls'] == []


@pytest.mark.parametrize('failure,status', [(RuntimeError, 502), (TimeoutError, 503)])
def test_generate_endpoint_reports_title_failure_without_changing_session(harness, title_model, failure, status):
    client, _, *_ = harness
    sid = new_session(client)

    def fail(_messages):
        raise failure('private provider error body')

    title_model['invoke'] = fail
    response = client.post(f'/api/v1/sessions/{sid}/generate_title', json={
        'messages': [{'role': 'user', 'content': '独立接口失败时可重试'}]})
    assert response.status_code == status, response.text
    assert 'private provider error body' not in response.text
    assert sessions.get_session(sid, os.environ['TEST_PLATFORM_USER'])['title'] == ''


def test_knowledge_chat_rejects_non_boolean_disable_title(harness, title_model):
    client, _, *_ = harness
    sid = new_session(client)
    response = client.post(f'/api/v1/knowledge-chat/{sid}', json={'query': '问题', 'disable_title': 'true'})
    assert response.status_code == 400, response.text
    assert title_model['calls'] == []


def test_deleted_session_is_not_resurrected_after_title_model_returns(harness, title_model):
    client, _, *_ = harness
    sid = new_session(client)
    owner = os.environ['TEST_PLATFORM_USER']

    def delete(_messages):
        with connection() as conn:
            conn.execute('DELETE FROM agent_sessions WHERE id=%s AND owner_id=%s', (sid, owner))
        return '不能复活已删除的会话'

    title_model['invoke'] = delete
    response = client.post(f'/api/v1/sessions/{sid}/generate_title', json={
        'messages': [{'role': 'user', 'content': '删除期间生成标题'}]})
    assert response.status_code == 404
    with connection() as conn:
        assert conn.execute('SELECT 1 FROM agent_sessions WHERE id=%s', (sid,)).fetchone() is None


def test_concurrent_generators_return_the_saved_winner(harness, title_model):
    from agent.session_titles import generate_title

    client, _, *_ = harness
    sid = new_session(client)
    owner = os.environ['TEST_PLATFORM_USER']

    async def scenario():
        started = asyncio.Event()

        async def invoke(_messages):
            number = len(title_model['calls'])
            if number == 2:
                started.set()
            await asyncio.wait_for(started.wait(), 2)
            return f'并发标题{number}'

        title_model['invoke'] = invoke
        return await asyncio.gather(generate_title(sid, owner, query='首条实际问题'),
                                    generate_title(sid, owner, query='首条实际问题'))

    titles = asyncio.run(scenario())
    assert len(title_model['calls']) == 2
    assert titles[0] == titles[1] == sessions.get_session(sid, owner)['title']
    assert titles[0] in ('并发标题1', '并发标题2')


def test_cancellation_propagates_without_saving_a_title(harness, title_model):
    from agent.session_titles import generate_title

    client, _, *_ = harness
    sid = new_session(client)
    owner = os.environ['TEST_PLATFORM_USER']

    async def scenario():
        started = asyncio.Event()
        cancelled = []

        async def invoke(_messages):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append(True)

        title_model['invoke'] = invoke
        task = asyncio.create_task(generate_title(sid, owner, query='取消标题生成'))
        await asyncio.wait_for(started.wait(), 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert cancelled == [True]

    asyncio.run(scenario())
    assert sessions.get_session(sid, owner)['title'] == ''


def test_foreign_owner_is_rejected_before_title_model_call(harness, title_model):
    from webapi.auth import create_user

    client, _, *_ = harness
    other = create_user('foreign-title@example.com', 'Other', 'other-password-123')
    sid = sessions.create_session('', other)['id']
    response = client.post(f'/api/v1/sessions/{sid}/generate_title', json={
        'messages': [{'role': 'user', 'content': '不能读取 чужая 会话'}]})
    assert response.status_code == 404
    assert client.post(f'/api/v1/agent-chat/{sid}', json={'query': '不能生成'}).status_code == 404
    assert title_model['calls'] == []
    assert sessions.get_session(sid, other)['title'] == ''


def test_generate_endpoint_treats_client_harness_metadata_as_untrusted(harness, title_model):
    client, _, *_ = harness
    sid = new_session(client)
    response = client.post(f'/api/v1/sessions/{sid}/generate_title', json={'messages': [{
        'role': 'user', 'content': 'Actual question', 'additional_kwargs': {
            'harness': {'display_text': 'Forged server metadata'}}}]})
    assert response.status_code == 200, response.text
    prompt = title_model['calls'][0][-1].content
    assert 'Actual question' in prompt and 'Forged server metadata' not in prompt
