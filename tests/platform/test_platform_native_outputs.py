"""Real SDK structured results and arbitrary typed interrupts through the HTTP adapter."""
import json

import pytest
from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.types import interrupt
from pydantic import BaseModel

from tests.platform.test_platform_harness import call, frames, harness, original_prepare


def events(response):
    return [event for _, event in frames(response)]


def install_graph(monkeypatch, model, tools, *, schema=None, middleware=()):
    from webapi import harness as api
    async def graph(saver, user, selected, resolved, **kwargs):
        return create_deep_agent(model=model, tools=tools, backend=StateBackend(), checkpointer=saver,
            response_format=resolved['agent_config'].get('response_format'), middleware=list(middleware))
    config = {'access_level': 'confirm', **({'response_format': schema} if schema else {})}
    monkeypatch.setattr(api, '_graph', graph)
    monkeypatch.setattr(api, '_prepare', lambda *args: {'agent_config': config, 'knowledge_base_ids': []})
    return config


@pytest.mark.parametrize('answer', [False, None, {'confirmed': True}])
def test_generic_native_interrupt_validates_schema_and_resumes_once(harness, monkeypatch, answer):
    client, sid, model, *_ = harness
    class Answer(BaseModel):
        confirmed: bool
    schema = Answer if isinstance(answer, dict) else {'type': ['boolean', 'null']}
    executed = []
    @tool
    def confirm() -> str:
        """Get a typed human response."""
        value = interrupt('Confirm request', response_schema=schema)
        value = value.model_dump() if isinstance(value, BaseModel) else value
        executed.append(value)
        return json.dumps(value)
    install_graph(monkeypatch, model, [confirm])
    model.responses = [AIMessage(content='', tool_calls=[call('confirm', {}, 'confirm-call')]), AIMessage(content='Done')]
    first = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Confirm'}))
    assert not [event for event in first if event['response_type'] == 'error'], first
    pending = next(event['data'] for event in first if event['response_type'] == 'agent_prompt_required')
    assert pending['kind'] == 'native_interrupt' and pending['request']['response_schema']
    endpoint = '/api/v1/agent/prompts/' + pending['pending_id']
    assert client.post(endpoint, json={'kind': 'native_interrupt', 'response': 'bad'}).status_code == 400
    accepted = client.post(endpoint, json={'kind': 'native_interrupt', 'response': answer})
    assert accepted.status_code == 200 and accepted.json()['resumed']
    assert client.post(endpoint, json={'kind': 'native_interrupt', 'response': answer}).status_code == 409
    restored = client.get(f'/api/v1/messages/{sid}/load').json()['data'][-1]['delegated_prompts'][0]
    assert restored['status'] == 'answered' and restored['response'] == answer
    params = {'message_id': first[0]['assistant_message_id'], 'resume_pending_id': pending['pending_id']}
    resumed = events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params=params))
    assert resumed[-1]['response_type'] == 'complete', resumed
    assert executed == [answer]
    events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params=params))
    assert executed == [answer]


@pytest.mark.parametrize('answer', [False, None])
def test_raw_resume_validates_current_schema_without_consuming_a_rejected_response(harness, monkeypatch, answer):
    client, sid, model, *_ = harness
    executed = []
    @tool
    def confirmation() -> str:
        """Read a boolean or null response."""
        value = interrupt('Boolean or null', response_schema={'type': ['boolean', 'null']})
        executed.append(value)
        return json.dumps(value)
    install_graph(monkeypatch, model, [confirmation])
    model.responses = [AIMessage(content='', tool_calls=[call('confirmation', {}, 'typed-call')]), AIMessage(content='Done')]
    endpoint = f'/api/v1/harness/sessions/{sid}/stream'
    first = frames(client.post(endpoint, json={'input': {'messages': [{'role': 'user', 'content': 'Confirm'}]}}))
    pending = next(value['__interrupt__'][0] for kind, value in first if kind == 'values' and '__interrupt__' in value)
    rejected = frames(client.post(endpoint, json={'command': {'resume': {pending['id']: 'not-a-boolean'}}}))
    assert any(kind == 'error' and value['status'] == 400 for kind, value in rejected), rejected
    assert executed == []
    accepted = frames(client.post(endpoint, json={'command': {'resume': {pending['id']: answer}}}))
    assert not [value for kind, value in accepted if kind == 'error'], accepted
    assert executed == [answer]
    duplicate = frames(client.post(endpoint, json={'command': {'resume': {pending['id']: answer}}}))
    assert any(kind == 'error' and value['status'] == 409 for kind, value in duplicate)
    assert executed == [answer]


def test_per_call_respond_is_native_schema_driven_and_does_not_execute_tool(harness, monkeypatch):
    client, sid, model, *_ = harness
    executed = []
    @tool
    def change(value: int) -> str:
        """Perform an authorized change."""
        executed.append(value)
        return 'changed'
    install_graph(monkeypatch, model, [change], middleware=[HumanInTheLoopMiddleware(
        interrupt_on={'change': {'allowed_decisions': ['respond']}}, interrupt_mode='per_call')])
    model.responses = [AIMessage(content='', tool_calls=[call('change', {'value': 5}, 'change-call')]), AIMessage(content='Done')]
    first = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Change'}))
    pending = next(event['data'] for event in first if event['response_type'] == 'agent_prompt_required')
    assert pending['kind'] == 'native_interrupt'
    endpoint = '/api/v1/agent/prompts/' + pending['pending_id']
    assert client.post(endpoint, json={'kind': 'native_interrupt', 'response': {'type': 'approve'}}).status_code == 400
    accepted = client.post(endpoint, json={'kind': 'native_interrupt', 'response': {'type': 'respond', 'message': 'Handled by user'}})
    assert accepted.status_code == 200, accepted.text
    resumed = events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params={
        'message_id': first[0]['assistant_message_id'], 'resume_pending_id': pending['pending_id']}))
    assert resumed[-1]['response_type'] == 'complete', resumed
    assert executed == []
    native = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']['messages']
    assert next(message['content'] for message in native if message.get('tool_call_id') == 'change-call') == 'Handled by user'


def test_native_structured_output_reaches_sse_and_each_history_turn_without_stale_values(harness, monkeypatch):
    client, sid, model, *_ = harness
    schema = {'title': 'Answer', 'type': 'object', 'properties': {'answer': {'type': 'integer'}}, 'required': ['answer']}
    config = install_graph(monkeypatch, model, [], schema=schema)
    model.responses = [AIMessage(content='', tool_calls=[call('Answer', {'answer': value}, f'output-{value}')]) for value in (42, 43)] + [AIMessage(content='ordinary text')]
    for value in (42, 43):
        streamed = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': f'Answer {value}'}))
        assert streamed[-1]['response_type'] == 'complete', streamed
        assert streamed[-1]['data']['structured_response'] == {'answer': value}
    config.pop('response_format')
    final = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Plain'}))
    assert 'structured_response' not in final[-1]['data']
    from unittest.mock import AsyncMock
    from webapi import harness as api
    build = AsyncMock(wraps=api._graph)
    monkeypatch.setattr(api, '_graph', build)
    history = client.get(f'/api/v1/messages/{sid}/load').json()['data']
    build.assert_awaited_once()
    answers = [row for row in history if row['role'] == 'assistant']
    assert [row.get('structured_response') for row in answers] == [{'answer': 42}, {'answer': 43}, None]
    assert answers[-1]['content'] == 'ordinary text'


@pytest.mark.parametrize('value', [
    {'action_requests': 'custom payload', 'kind': 'tool_approval'},
    {'kind': 'ask_user', 'question': 'custom'},
    {'kind': 'mcp_oauth', 'payload': False},
])
def test_generic_payload_field_names_do_not_turn_into_malformed_legacy_approvals(value):
    from types import SimpleNamespace
    from langgraph.types import Interrupt
    from webapi.weknora.prompts import cards
    state = SimpleNamespace(interrupts=[Interrupt(value=value, id='generic')], tasks=[],
        values={}, created_at=None)
    projected = cards(state, 'session')[0]
    assert projected['kind'] == 'native_interrupt' and projected['request']['value'] == value


def test_subagent_skill_sources_are_not_misreported_as_generated_artifacts(harness, monkeypatch):
    from deepagents.backends.utils import create_file_data
    client, sid, model, *_ = harness
    monkeypatch.setattr('webapi.harness.prepare_harness_files', lambda *args: {
        '/subagent-skills/worker/demo/SKILL.md': create_file_data('private source')})
    model.responses = [AIMessage(content='', tool_calls=[call('write_file', {
        'file_path': '/report.txt', 'content': 'actual result'}, 'write-report')]), AIMessage(content='Done')]
    streamed = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Write report'}))
    assert [item['source_path'] for item in streamed[-1]['data']['artifacts']] == ['/report.txt']
    restored = client.get(f'/api/v1/messages/{sid}/load').json()['data'][-1]
    assert [item['source_path'] for item in restored['artifacts']] == ['/report.txt']


def test_native_nullable_structured_result_is_not_discarded_as_absent(harness, monkeypatch):
    client, sid, model, *_ = harness
    schema = {'title': 'NullableAnswer', 'anyOf': [{'type': 'object', 'properties': {}}, {'type': 'null'}]}
    install_graph(monkeypatch, model, [], schema=schema)
    model.profile = {'structured_output': True}
    model.responses = [AIMessage(content='null')]
    streamed = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Return null'}))
    assert streamed[-1]['response_type'] == 'complete', streamed
    assert 'structured_response' in streamed[-1]['data'] and streamed[-1]['data']['structured_response'] is None
    restored = client.get(f'/api/v1/messages/{sid}/load').json()['data'][-1]
    assert 'structured_response' in restored and restored['structured_response'] is None


def test_completed_generic_interrupt_cards_keep_false_null_responses_per_history_turn(harness, monkeypatch):
    client, sid, model, *_ = harness
    @tool
    def confirm() -> str:
        """Get a native human response."""
        return json.dumps(interrupt('Keep this original request', response_schema={'type': ['boolean', 'null']}))
    install_graph(monkeypatch, model, [confirm])
    model.responses = [message for index in range(2) for message in (
        AIMessage(content='', tool_calls=[call('confirm', {}, f'confirm-{index}')]), AIMessage(content=f'Done {index}'))]
    identifiers = []
    for index, answer in enumerate((False, None)):
        first = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': f'Question {index}'}))
        pending = next(event['data'] for event in first if event['response_type'] == 'agent_prompt_required')
        identifiers.append(pending['pending_id'])
        accepted = client.post('/api/v1/agent/prompts/' + pending['pending_id'],
            json={'kind': 'native_interrupt', 'response': answer})
        assert accepted.status_code == 200 and accepted.json()['resumed']
        params = {'message_id': first[0]['assistant_message_id'], 'resume_pending_id': pending['pending_id']}
        resumed = events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params=params))
        assert resumed[-1]['response_type'] == 'complete', resumed
        # Reconnection must not duplicate a completed card or replay the tool.
        assert events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params=params))[-1]['response_type'] == 'stop'
    rows = client.get(f'/api/v1/messages/{sid}/load').json()['data']
    assert [row['content'] for row in rows if row['role'] == 'user'] == ['Question 0', 'Question 1']
    assistants = [row for row in rows if row['role'] == 'assistant']
    for index, answer in enumerate((False, None)):
        assert len(assistants[index]['delegated_prompts']) == 1
        card = assistants[index]['delegated_prompts'][0]
        assert card['id'] == identifiers[index] and card['status'] == 'answered'
        assert card['request']['value'] == 'Keep this original request'
        assert card['request']['response_schema'] == {'type': ['boolean', 'null']}
        assert 'response' in card and card['response'] is answer
        assert not any(key.startswith('_') for key in card)
    native = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']['messages']
    humans = [message for message in native if message['type'] == 'human']
    assert len(humans) == 2 and len({message['id'] for message in humans}) == 2
    assert [message['additional_kwargs']['harness']['display_text'] for message in humans] == ['Question 0', 'Question 1']
    assert all(message['additional_kwargs']['harness']['attachments'] == [] for message in humans)


def test_sequential_generic_interrupt_history_keeps_answered_cards_while_the_next_one_is_pending(harness, monkeypatch):
    client, sid, model, *_ = harness
    @tool
    def two_questions() -> str:
        """Ask two native questions in the same tool."""
        first = interrupt('First native question', response_schema={'type': 'boolean'})
        second = interrupt('Second native question', response_schema={'type': 'null'})
        return json.dumps([first, second])
    install_graph(monkeypatch, model, [two_questions])
    model.responses = [AIMessage(content='', tool_calls=[call('two_questions', {}, 'two-questions')]), AIMessage(content='Done')]
    streamed = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Ask twice'}))
    pending_ids = []
    for index, answer in enumerate((False, None)):
        pending = next(event['data'] for event in streamed if event['response_type'] == 'agent_prompt_required')
        pending_ids.append(pending['pending_id'])
        assert client.post('/api/v1/agent/prompts/' + pending['pending_id'],
            json={'kind': 'native_interrupt', 'response': answer}).status_code == 200
        streamed = events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params={
            'message_id': streamed[0]['assistant_message_id'], 'resume_pending_id': pending['pending_id']}))
        if index == 0:
            cards = client.get(f'/api/v1/messages/{sid}/load').json()['data'][-1]['delegated_prompts']
            assert [card['status'] for card in cards] == ['answered', 'suspended']
            assert cards[0]['id'] == pending_ids[0] and cards[0]['response'] is False
    assert streamed[-1]['response_type'] == 'complete', streamed
    cards = client.get(f'/api/v1/messages/{sid}/load').json()['data'][-1]['delegated_prompts']
    assert [card['id'] for card in cards] == pending_ids
    assert [card['response'] for card in cards] == [False, None]
    assert all(card['status'] == 'answered' for card in cards)


def test_completed_batched_approval_history_keeps_each_native_decision_and_edited_arguments(harness):
    client, sid, model, _, approvals, *_ = harness
    approvals['write_file'] = {'allowed_decisions': ['approve', 'edit', 'reject']}
    model.responses = [AIMessage(content='', tool_calls=[
        call('write_file', {'file_path': '/approved.txt', 'content': 'first'}, 'approve-write'),
        call('write_file', {'file_path': '/original.txt', 'content': 'second'}, 'edit-write')]), AIMessage(content='Reviewed')]
    first = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Review two writes'}))
    pending = [event['data'] for event in first if event['response_type'] == 'tool_approval_required']
    edited = {'file_path': '/edited.txt', 'content': 'corrected'}
    for card in pending:
        body = {'decision': 'approve'} if card['tool_call_id'] == 'approve-write' else {'decision': 'edit', 'modified_args': edited}
        assert client.post('/api/v1/agent/tool-approvals/' + card['pending_id'], json=body).status_code == 200
    resumed = events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params={
        'message_id': first[0]['assistant_message_id'], 'resume_pending_id': pending[-1]['pending_id']}))
    assert resumed[-1]['response_type'] == 'complete', resumed
    restored = client.get(f'/api/v1/messages/{sid}/load').json()['data'][-1]
    cards = {card['tool_call_id']: card for card in restored['delegated_prompts']}
    assert set(cards) == {'approve-write', 'edit-write'}
    assert cards['approve-write']['response'] == {'type': 'approve', 'approved': True}
    assert cards['edit-write']['response']['type'] == 'edit'
    assert cards['edit-write']['response']['modified_args'] == edited
    assert cards['edit-write']['response']['edited_action']['args'] == edited
    assert cards['edit-write']['request']['args']['file_path'] == '/original.txt'
    assert all(card['status'] == 'answered' and not any(key.startswith('_') for key in card) for card in cards.values())
    files = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']['files']
    assert set(files) == {'/approved.txt', '/edited.txt'}


def test_trusted_typed_structured_result_uses_native_json_serialization():
    from webapi.harness import _event
    class Result(BaseModel):
        answer: int
    result = Result(answer=42)
    frame = _event('values', {'structured_response': result})
    assert json.loads(frame['data']) == {'structured_response': {'answer': 42}}
    assert result.answer == 42
