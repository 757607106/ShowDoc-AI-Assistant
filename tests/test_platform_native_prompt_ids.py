"""Native question IDs through real Deep Agents, HTTP cards and checkpoint resume."""
import asyncio
import json
import os
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent import registry, sessions
from agent.interactions import make_interaction_tools
from tests.test_platform_harness import call, frames, harness, original_prepare
from webapi import weknora_prompts


def events(response):
    return [event for _, event in frames(response)]


@pytest.mark.parametrize('delegated', [False, True], ids=['main', 'general-purpose'])
@pytest.mark.parametrize('same_question', [False, True], ids=['different-text', 'identical-text'])
def test_parallel_native_questions_keep_real_ids_through_sse_history_and_individual_resume(harness, delegated, same_question):
    client, sid, model, tools, *_ = harness
    tools.extend(make_interaction_tools(sid, os.environ['TEST_PLATFORM_USER']))
    questions = {'call-a': 'Question A', 'call-b': 'Question A' if same_question else 'Question B'}
    asks = [call('ask_user', {'question': question, 'runtime': {'tool_call_id': 'forged-runtime'},
                             'tool_call_id': 'forged-argument'}, identifier)
            for identifier, question in questions.items()]
    model.responses = ([AIMessage(content='', tool_calls=[call('task', {
        'description': 'Ask both questions', 'subagent_type': 'general-purpose'}, 'parent-task')])]
        if delegated else []) + [AIMessage(content='', tool_calls=asks), AIMessage(content='Child finished' if delegated else 'Finished')] + (
        [AIMessage(content='Parent finished')] if delegated else [])
    first = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Ask both questions'}))
    assert not [event for event in first if event['response_type'] == 'error'], first
    cards = [event['data'] for event in first if event['response_type'] == 'agent_prompt_required']
    assert len(cards) == 2 and len({card['pending_id'] for card in cards}) == 2
    assert {card['tool_call_id']: card['request']['question'] for card in cards} == questions
    assert all(set(card['request']) == {'question', 'options', 'fields', 'multi_select', 'allow_free_text'} for card in cards)
    restored = client.get(f'/api/v1/messages/{sid}/load').json()['data'][-1]
    assert {card['tool_call_id']: card['request']['question'] for card in restored['delegated_prompts']} == questions
    by_call = {card['tool_call_id']: card for card in cards}
    answers = {identifier: {'answer': 'Answer for ' + identifier} for identifier in questions}
    for index, identifier in enumerate(questions):
        card = by_call[identifier]
        posted = client.post('/api/v1/agent/prompts/' + card['pending_id'],
            json={'kind': 'ask_user', 'response': answers[identifier]})
        assert posted.status_code == 200 and posted.json()['resumed'] is (index == 1)
        state = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']
        assert state['__interrupt__'] and not any(message['type'] == 'tool' for message in state['messages'])
        refreshed = client.get(f'/api/v1/messages/{sid}/load').json()['data'][-1]
        refreshed_cards = {item['tool_call_id']: item for item in refreshed['delegated_prompts']}
        assert refreshed_cards[identifier]['response'] == answers[identifier]
        assert refreshed_cards[identifier]['status'] == 'answered'
        if index == 0:
            assert refreshed_cards['call-b']['status'] == 'suspended'
            assert client.post('/api/v1/agent/prompts/' + card['pending_id'],
                json={'kind': 'ask_user', 'response': answers[identifier]}).status_code == 409
    params = {'message_id': first[0]['assistant_message_id'], 'resume_pending_id': by_call['call-b']['pending_id']}
    resumed = events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params=params))
    assert resumed[-1]['response_type'] == 'complete', json.dumps(resumed[-1], ensure_ascii=False)
    assert not [event for event in resumed if event['response_type'] == 'error'], resumed
    history = client.get(f'/api/v1/messages/{sid}/load').json()['data']
    assert history[-1]['content'] == ('Parent finished' if delegated else 'Finished')
    if delegated:
        child = history[-1]['collaboration_status']['tasks'][0]['session_id']
        history = client.get(f'/api/v1/messages/{child}/load').json()['data']
    saved_calls = [item for row in history if row['role'] == 'assistant'
                   for step in row.get('agent_steps', []) for item in step['tool_calls'] if item['name'] == 'ask_user']
    assert {item['id']: item['result']['data']['answer'] for item in saved_calls} == answers
    if not delegated:
        native = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']['messages']
        assert {item['tool_call_id']: json.loads(item['content']) for item in native if item['type'] == 'tool'} == answers
    replayed = events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params=params))
    assert replayed[-1]['response_type'] == 'stop'


def test_question_schema_hides_runtime_and_native_id():
    tool = make_interaction_tools('session', 'owner')[0]
    properties = tool.tool_call_schema.model_json_schema()['properties']
    assert set(properties) == {'question', 'options', 'multi_select', 'fields', 'allow_free_text'}


@pytest.mark.parametrize('same_question', [False, True], ids=['different-text', 'identical-text'])
def test_parent_and_child_questions_keep_native_ids_through_history_and_resume(harness, same_question):
    client, sid, model, tools, *_ = harness
    tools.extend(make_interaction_tools(sid, os.environ['TEST_PLATFORM_USER']))
    questions = {'root-question': 'Question A', 'child-question': 'Question A' if same_question else 'Question B'}
    model.responses = [AIMessage(content='', tool_calls=[
        call('ask_user', {'question': questions['root-question']}, 'root-question'),
        call('task', {'description': 'Ask a question', 'subagent_type': 'general-purpose'}, 'parent-task')]),
        AIMessage(content='', tool_calls=[call('ask_user', {'question': questions['child-question']}, 'child-question')]),
        AIMessage(content='Child finished'), AIMessage(content='Parent finished')]
    first = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Ask in parent and child'}))
    assert not [event for event in first if event['response_type'] == 'error'], first
    pending = [event['data'] for event in first if event['response_type'] == 'agent_prompt_required']
    assert len(pending) == 2 and len({card['pending_id'] for card in pending}) == 2
    assert {card['tool_call_id']: card['request']['question'] for card in pending} == questions
    loaded = client.get(f'/api/v1/messages/{sid}/load')
    assert loaded.status_code == 200, loaded.text
    restored = loaded.json()['data'][-1]
    assert {card['tool_call_id']: card['request']['question'] for card in restored['delegated_prompts']} == questions
    child = restored['collaboration_status']['tasks'][0]['session_id']
    by_call = {card['tool_call_id']: card for card in pending}
    answers = {identifier: {'answer': 'Answer for ' + identifier} for identifier in questions}
    for index, identifier in enumerate(questions):
        card = by_call[identifier]
        posted = client.post('/api/v1/agent/prompts/' + card['pending_id'],
            json={'kind': 'ask_user', 'response': answers[identifier]})
        assert posted.status_code == 200 and posted.json()['resumed'] is (index == 1)
        state = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']
        assert len(state['__interrupt__']) == 2 and not any(message['type'] == 'tool' for message in state['messages'])
        refreshed = client.get(f'/api/v1/messages/{sid}/load').json()['data'][-1]['delegated_prompts']
        answered = next(item for item in refreshed if item['tool_call_id'] == identifier)
        assert answered['status'] == 'answered' and answered['response'] == answers[identifier]
    resumed = events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params={
        'message_id': first[0]['assistant_message_id'], 'resume_pending_id': by_call['child-question']['pending_id']}))
    assert not [event for event in resumed if event['response_type'] == 'error'], resumed
    assert resumed[-1]['response_type'] == 'complete'
    state = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']
    assert '__interrupt__' not in state
    assert next(json.loads(message['content']) for message in state['messages']
                if message.get('tool_call_id') == 'root-question') == answers['root-question']
    assert not any(call['id'] == 'child-question' for message in state['messages'] for call in message.get('tool_calls', []))
    history = client.get(f'/api/v1/messages/{sid}/load').json()['data'][-1]
    assert history['content'] == 'Parent finished'
    assert history['collaboration_status']['tasks'][0]['session_id'] == child
    child_history = client.get(f'/api/v1/messages/{child}/load').json()['data'][-1]
    assert child_history['content'] == 'Child finished'
    saved = [item for step in child_history['agent_steps'] for item in step['tool_calls'] if item['name'] == 'ask_user']
    assert len(saved) == 1 and saved[0]['id'] == 'child-question'
    assert saved[0]['result']['data']['answer'] == answers['child-question']


def legacy_snapshot(requests, calls):
    return SimpleNamespace(
        interrupts=[SimpleNamespace(id=f'interrupt-{index}', value={'kind': 'ask_user', 'request': request})
                    for index, request in enumerate(requests)],
        tasks=[], values={'messages': [HumanMessage(content='Question', id='human-question'),
                                      AIMessage(content='', tool_calls=calls)]},
        created_at='2026-11-17T00:00:00+00:00', next=('tools',),
        config={'configurable': {'checkpoint_id': 'legacy-checkpoint'}},
    )


def test_legacy_questions_bind_only_unique_full_requests_not_tool_name_or_latest_call():
    requests = [{'question': 'Same title', 'options': ['A']}, {'question': 'Same title', 'options': ['B']}]
    calls = [call('ask_user', requests[1], 'call-b'), call('ask_user', requests[0], 'call-a')]
    pending = weknora_prompts.cards(legacy_snapshot(requests, calls), 'session')
    assert [item['tool_call_id'] for item in pending] == ['call-a', 'call-b']
    assert weknora_prompts.cards(legacy_snapshot([{'question': 'No exact match'}], calls), 'session')[0]['tool_call_id'] is None
    duplicate_calls = [call('ask_user', requests[0], 'call-a'), call('ask_user', requests[0], 'call-b')]
    pending = weknora_prompts.cards(legacy_snapshot([requests[0], requests[0]], duplicate_calls), 'session')
    assert [item['tool_call_id'] for item in pending] == [None, None]
    # Even one candidate is ambiguous when two outstanding cards have the same request.
    pending = weknora_prompts.cards(legacy_snapshot([requests[0], requests[0]], duplicate_calls[:1]), 'session')
    assert [item['tool_call_id'] for item in pending] == [None, None]


def test_ambiguous_legacy_questions_ignore_stale_receipt_ids_in_binding_and_refresh(harness, monkeypatch):
    from webapi import harness as api
    client, sid, *_ = harness
    owner = os.environ['TEST_PLATFORM_USER']
    request = {'question': 'Identical question'}
    calls = [call('ask_user', request, 'call-a'), call('ask_user', request, 'call-b')]
    state = legacy_snapshot([request, request], calls)
    pending = weknora_prompts.cards(state, sid)
    registry.save_record('harness_resume', {'id': sid, 'checkpoint': 'legacy-checkpoint', 'responses': {},
        'tool_ids': {item['id']: 'call-b' for item in pending}}, owner)
    weknora_prompts.bind_card_ids(owner, sid, state, pending, calls)
    assert [item['tool_call_id'] for item in pending] == [None, None]

    async def snapshot(*args):
        return state
    async def artifacts(*args):
        return {}
    monkeypatch.setattr(api, 'read_snapshot', snapshot)
    monkeypatch.setattr('webapi.weknora_artifacts.read', artifacts)
    rows = asyncio.run(api.read_weknora_history({'id': owner}, sessions.get_session(sid, owner)))
    assert [item['tool_call_id'] for item in rows[-1]['delegated_prompts']] == [None, None]
    assert all(item['status'] == 'suspended' for item in rows[-1]['delegated_prompts'])


def test_legacy_stream_binding_accepts_unique_arguments_but_never_name_only(monkeypatch):
    receipt = {'id': 'session', 'checkpoint': 'checkpoint', 'responses': {}, 'tool_ids': {}}
    monkeypatch.setattr(weknora_prompts, '_receipt', lambda *args: receipt)
    monkeypatch.setattr(registry, 'save_record', lambda *args: None)
    request = {'question': 'Choose', 'options': ['A', 'B']}
    pending = [{'id': 'unique', 'kind': 'ask_user', 'request': request, 'tool_call_id': None},
               {'id': 'unmatched', 'kind': 'ask_user', 'request': {'question': 'Other'}, 'tool_call_id': None}]
    weknora_prompts.bind_card_ids('owner', 'session', None, pending, [call('ask_user', request, 'actual')])
    assert [item['tool_call_id'] for item in pending] == ['actual', None]


def test_native_file_approvals_still_bind_stage_and_resume_per_call(harness):
    client, sid, model, _, approvals, *_ = harness
    approvals['write_file'] = {'allowed_decisions': ['approve', 'reject', 'edit']}
    model.responses = [AIMessage(content='', tool_calls=[
        call('write_file', {'file_path': '/approved.txt', 'content': 'yes'}, 'accept-file'),
        call('write_file', {'file_path': '/rejected.txt', 'content': 'no'}, 'reject-file')]), AIMessage(content='Reviewed')]
    first = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Review files'}))
    cards = [event['data'] for event in first if event['response_type'] == 'tool_approval_required']
    assert {card['tool_call_id'] for card in cards} == {'accept-file', 'reject-file'}
    for card in cards:
        response = client.post('/api/v1/agent/tool-approvals/' + card['pending_id'],
            json={'decision': 'approve' if card['tool_call_id'] == 'accept-file' else 'reject'})
        assert response.status_code == 200
    resumed = events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params={
        'message_id': first[0]['assistant_message_id'], 'resume_pending_id': cards[-1]['pending_id']}))
    assert resumed[-1]['response_type'] == 'complete', resumed
    values = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']
    assert set(values['files']) == {'/approved.txt'}
    assert values['files']['/approved.txt']['content'] == 'yes'
