"""Native child checkpoint views keep media, prompts, files and owner boundaries."""
import base64
import os
from copy import deepcopy
from unittest.mock import AsyncMock
from types import SimpleNamespace

import pytest
from deepagents.backends.utils import create_file_data
from langchain_core.messages import AIMessage, HumanMessage

from agent import async_work
from webapi import async_views, weknora_adapter, weknora_traces
from tests.test_platform_harness import harness, original_prepare


@pytest.fixture
def child_view(harness, monkeypatch):
    client, sid, *_ = harness
    owner = os.environ['TEST_PLATFORM_USER']
    task = {'task_id': 'work', 'thread_id': 'remote', 'run_id': 'r1', 'agent_name': 'worker'}
    state = {'values': {'messages': [HumanMessage(id='question', content='Draw a dot').model_dump(mode='json'),
        AIMessage(id='answer', content=[{'type': 'image', 'url': 'https://example.invalid/dot.png'}]).model_dump(mode='json')],
        'files': {'/result.txt': create_file_data('native child file')}},
        'interrupts': [], 'tasks': [], 'checkpoint': {'checkpoint_id': 'cp1'}, 'parent_checkpoint': None,
        'created_at': '2026-11-17T00:00:00+00:00'}
    remote = SimpleNamespace(threads=SimpleNamespace(get_state=AsyncMock(side_effect=lambda *a, **kw: deepcopy(state))))
    async def tasks(current_owner, parent):
        assert current_owner == owner and parent == sid
        return {'work': task}
    async def observe(current_owner, parent, current_task, **kwargs):
        assert current_owner == owner and parent == sid and current_task == task
        return {'state': 'succeeded'}, remote, {'knowledge_base_ids': []}, state
    monkeypatch.setattr(async_work, '_tasks', tasks)
    monkeypatch.setattr(async_work, '_observe', observe)
    return client, sid, owner, task, state, remote, weknora_traces.locator(sid, async_views.NAMESPACE, 'work')


def test_signed_child_history_uses_original_message_and_artifact_contracts(child_view):
    client, _, _, _, _, remote, view = child_view
    response = client.get(f'/api/v1/messages/{view}/load')
    assert response.status_code == 200, response.text
    answer = response.json()['data'][-1]
    assert answer['content'] == '\n\n![image](https://example.invalid/dot.png)\n\n'
    assert answer['content_blocks'] == [{'type': 'image', 'url': 'https://example.invalid/dot.png'}]
    assert answer['is_completed'] is True
    assert answer['artifacts'][0]['file_name'] == 'result.txt'
    base = f'/api/v1/sessions/{view}/messages/{answer["id"]}/artifacts'
    listed = client.get(base)
    assert listed.status_code == 200 and listed.json()['read_only'] is True
    downloaded = client.get(base + '/0/download')
    assert downloaded.status_code == 200 and downloaded.content == b'native child file'
    assert remote.threads.get_state.await_count > 0
    assert client.get(f'/api/v1/messages/{view}tampered/load').status_code == 404


def test_signed_child_does_not_outlive_its_parent_membership(child_view, monkeypatch):
    client, _, _, _, _, remote, view = child_view
    monkeypatch.setattr(async_work, '_tasks', AsyncMock(return_value={}))
    assert client.get(f'/api/v1/messages/{view}/load').status_code == 404
    remote.threads.get_state.assert_not_awaited()


@pytest.mark.parametrize('kind,mime', [('audio', 'audio/wav'), ('video', 'video/mp4'), ('file', 'application/pdf')])
@pytest.mark.parametrize('data_url', [False, True])
def test_binary_child_answers_reuse_owned_artifact_downloads(child_view, kind, mime, data_url):
    client, _, _, _, state, _, view = child_view
    raw = b'\x00\xff\x01native-media'
    encoded = base64.b64encode(raw).decode()
    block = {'type': kind, **({'url': f'data:{mime};base64,{encoded}'} if data_url
                             else {'base64': encoded, 'mime_type': mime})}
    state['values']['messages'][-1]['content'] = [block]
    state['values']['files'] = {}
    answer = client.get(f'/api/v1/messages/{view}/load').json()['data'][-1]
    artifact = answer['artifacts'][0]
    assert len(answer['artifacts']) == 1
    assert answer['content'] == f'\n\n[{kind}](sandbox:{artifact["source_path"]})\n\n'
    assert 'data:' not in answer['content']
    downloaded = client.get(f'/api/v1/sessions/{view}/messages/{answer["id"]}/artifacts/0/download')
    assert downloaded.status_code == 200 and downloaded.content == raw
    assert downloaded.headers['content-disposition'].startswith('attachment;')
    again = client.get(f'/api/v1/messages/{view}/load').json()['data'][-1]
    assert again['artifacts'] == answer['artifacts']
    assert state['values']['files'] == {} and state['values']['messages'][-1]['content'] == [block]


def test_parent_media_artifacts_keep_their_original_turn_without_writing_native_files(harness):
    from tests.test_platform_harness import frames
    client, sid, model, *_ = harness
    model.responses = [AIMessage(content=[{'type': 'audio', 'base64': 'YXVkaW8=', 'mime_type': 'audio/wav'}]),
                       AIMessage(content='Second turn')]
    events = [event for _, event in frames(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Return audio'}))]
    first_artifacts = events[-1]['data']['artifacts']
    assert len(first_artifacts) == 1 and first_artifacts[0]['file_type'] == 'wav'
    response = client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Next question'})
    assert frames(response)[-1][1]['data']['artifacts'] == []
    rows = client.get(f'/api/v1/messages/{sid}/load').json()['data']
    assert rows[1]['artifacts'] == first_artifacts and rows[3]['artifacts'] == []
    assert client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values'].get('files', {}) == {}
    assert client.get(f'/api/v1/sessions/{sid}/messages/{rows[1]["id"]}/artifacts/0/download').content == b'audio'


def test_async_cards_keep_all_native_ids_and_batch_action_indices(child_view):
    _, sid, owner, task, state, _, _ = child_view
    state['interrupts'] = [
        {'id': 'choice', 'value': False, 'response_schema': {'type': 'boolean'}},
        {'id': 'approval', 'value': {'action_requests': [
            {'name': 'execute', 'args': {'command': 'one'}}, {'name': 'execute', 'args': {'command': 'two'}}],
            'review_configs': [{'allowed_decisions': ['approve', 'reject']}, {'allowed_decisions': ['approve']}]}}]
    prompts = async_views.payload(owner, sid, task, state, {}, 'waiting')['prompts']
    assert [(p['interrupt_id'], p['action_index'], p['action_count']) for p in prompts] == [
        ('choice', 0, 1), ('approval', 0, 2), ('approval', 1, 2)]
    assert prompts[0]['request']['value'] is False
    assert prompts[0]['request']['response_schema'] == {'type': 'boolean'}
    assert async_views.payload(owner, sid, task, state, {}, 'cancelled')['prompts'] == []


def test_background_notifications_wake_on_native_task_and_on_a_new_run(monkeypatch):
    monkeypatch.setattr(weknora_adapter, '_knowledge_names', lambda *a: None)
    projection = weknora_adapter.StreamProjection('parent', 'assistant:question')
    def update(run, status):
        return projection.feed({'ns': (), 'type': 'updates', 'data': {'tools': {'async_tasks': {
            'work': {'task_id': 'work', 'run_id': run, 'status': status, 'agent_name': 'worker'}}}}})
    assert [(e['response_type'], e['data']['state']) for e in update('r1', 'running')] == [('work_started', 'running')]
    assert update('r1', 'running') == []
    assert update('r2', 'running')[0]['data']['payload']['run_id'] == 'r2'
    assert update('r2', 'success')[0]['response_type'] == 'work_finished'


def test_media_rendering_excludes_reasoning_and_unsafe_urls():
    rendered, blocks = weknora_adapter.answer_content(AIMessage(content=[
        {'type': 'reasoning', 'reasoning': 'private'},
        {'type': 'image', 'url': 'data:image/png;base64,YQ=='},
        {'type': 'image', 'url': 'javascript:alert(1)'},
        {'type': 'text', 'text': 'Visible answer'}]).model_dump(mode='json'))
    assert 'private' not in rendered and 'javascript:' not in rendered
    assert '![image](data:image/png;base64,YQ==)' in rendered and 'Visible answer' in rendered
    assert all(item['type'] != 'reasoning' for item in blocks)
