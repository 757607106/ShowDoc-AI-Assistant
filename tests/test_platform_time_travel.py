"""WeKnora fork/rewind semantics against native PostgreSQL checkpoints."""
import os

import psycopg
import pytest
from langchain_core.messages import AIMessage
from psycopg.types.json import Jsonb

from agent import sessions
from agent.checkpointer import make_checkpointer
from governance.database import connection
from tests.test_platform_harness import call, frames, harness, original_prepare, send


def state(client, sid):
    return client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']


def questions(value):
    return [m for m in value.get('messages', []) if m['type'] == 'human']


def two_file_turns(harness):
    client, sid, model, *_ = harness
    model.responses = [
        AIMessage(id='write-old', content='', tool_calls=[call('write_file',
            {'file_path': '/draft.txt', 'content': 'old'}, 'old-call')]),
        AIMessage(id='answer-old', content='first answer'),
        AIMessage(id='write-new', content='', tool_calls=[call('edit_file',
            {'file_path': '/draft.txt', 'old_string': 'old', 'new_string': 'new'}, 'new-call')]),
        AIMessage(id='answer-new', content='second answer')]
    assert not [v for k, v in frames(send(client, sid, 'first')) if k == 'error']
    first = state(client, sid)
    assert not [v for k, v in frames(send(client, sid, 'second')) if k == 'error']
    return client, sid, model, first, state(client, sid)


def test_fork_seeds_selected_native_state_without_replaying_or_cloning_audit(harness):
    client, sid, model, first, original = two_file_turns(harness)
    first_id = questions(first)[0]['id']
    before_model = model.i
    with make_checkpointer() as saver, connection() as conn:
        old_count = saver.conn.execute('SELECT count(*) AS n FROM checkpoints WHERE thread_id=%s', (sid,)).fetchone()['n']
    response = client.post(f'/api/v1/sessions/{sid}/fork',
                           json={'message_id': 'assistant:' + first_id, 'title': 'branch'})
    assert response.status_code == 200, response.text
    child = response.json()['data']['session_id']
    assert child != sid
    branched = state(client, child)
    assert branched['messages'] == first['messages']
    assert branched['files'] == first['files']
    assert model.i == before_model
    assert state(client, sid) == original
    owner = os.environ['TEST_PLATFORM_USER']
    assert child in {row['id'] for row in sessions.list_sessions(owner)}
    assert sessions.get_session(child, owner)['parent_session_id'] is None
    with make_checkpointer() as saver, connection() as conn:
        assert saver.conn.execute('SELECT count(*) AS n FROM checkpoints WHERE thread_id=%s', (sid,)).fetchone()['n'] == old_count
        assert saver.conn.execute('SELECT count(*) AS n FROM checkpoints WHERE thread_id=%s', (child,)).fetchone()['n'] <= 2
        assert conn.execute("SELECT count(*) AS n FROM runtime_records WHERE kind='opensandbox-session' AND record_key=%s", (child,)).fetchone()['n'] == 0
    model.responses = [AIMessage(id='branch-answer', content='branch only')]
    frames(send(client, child, 'branch question'))
    assert [m['content'] for m in questions(state(client, child))] == ['first', 'branch question']
    assert state(client, sid) == original


def test_user_fork_excludes_question_and_first_question_can_be_rewound_to_empty(harness):
    client, sid, model, *_ = harness
    frames(send(client, sid, 'first'))
    original = state(client, sid)
    identifier = questions(original)[0]['id']
    fork = client.post(f'/api/v1/sessions/{sid}/fork', json={'message_id': identifier})
    assert fork.status_code == 200, fork.text
    child = fork.json()['data']['session_id']
    assert state(client, child).get('messages', []) == []
    response = client.post(f'/api/v1/sessions/{sid}/rewind', json={'message_id': identifier})
    assert response.status_code == 200, response.text
    assert response.json()['data'] == {'session_id': sid, 'deleted_messages': 2,
        'workspace_reset': False, 'reason': 'CHECKPOINT_ONLY'}
    assert state(client, sid).get('messages', []) == []
    model.responses = [AIMessage(id='fresh-answer', content='fresh')]
    frames(send(client, sid, 'replacement'))
    assert [m['content'] for m in questions(state(client, sid))] == ['replacement']
    assert len(state(client, sid)['messages']) == 2


def test_rewind_restores_prefix_files_and_excludes_future_artifacts(harness):
    client, sid, model, first, original = two_file_turns(harness)
    first_id = questions(first)[0]['id']
    second_id = questions(original)[1]['id']
    response = client.post(f'/api/v1/sessions/{sid}/rewind', json={'message_id': second_id})
    assert response.status_code == 200, response.text
    assert state(client, sid)['messages'] == first['messages']
    assert state(client, sid)['files'] == first['files']
    artifacts = client.get(f'/api/v1/sessions/{sid}/messages/assistant:{first_id}/artifacts')
    assert artifacts.status_code == 200, artifacts.text
    downloaded = client.get(f'/api/v1/sessions/{sid}/messages/assistant:{first_id}/artifacts/0/download')
    assert downloaded.content == b'old'
    assert client.get(f'/api/v1/sessions/{sid}/messages/assistant:{second_id}/artifacts').status_code == 404
    assert client.post(f'/api/v1/sessions/{sid}/fork', json={'message_id': second_id}).status_code == 404
    model.responses = [AIMessage(id='replacement-answer', content='replacement answer')]
    frames(send(client, sid, 'new second'))
    assert [m['content'] for m in questions(state(client, sid))] == ['first', 'new second']


def test_time_travel_checks_owner_active_lock_and_pending_native_interrupt(harness):
    client, sid, model, _, approvals, *_ = harness
    frames(send(client, sid))
    message_id = questions(state(client, sid))[0]['id']
    assert client.post(f'/api/v1/sessions/{sid}/fork', json={}).status_code == 400
    assert client.post(f'/api/v1/sessions/{sid}/fork', json={'message_id': 'missing'}).status_code == 404
    assert client.post(f'/api/v1/sessions/{sid}/rewind', json={'message_id': 'assistant:' + message_id}).status_code == 409
    from webapi.auth import create_user
    other_owner = create_user('other@example.com', 'Other', 'test-password-123', 'viewer')
    foreign = sessions.create_session('foreign', other_owner)['id']
    assert client.post(f'/api/v1/sessions/{foreign}/fork', json={'message_id': message_id}).status_code == 404
    with psycopg.connect(os.environ['AGENT_DATABASE_URL'], autocommit=True) as conn:
        conn.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))', ('harness:' + sid,))
        assert client.post(f'/api/v1/sessions/{sid}/rewind', json={'message_id': message_id}).status_code == 409
    model.responses = [AIMessage(id='pending-write', content='', tool_calls=[call('write_file',
        {'file_path': '/wait.txt', 'content': 'pending'})]), AIMessage(content='done')]
    approvals['write_file'] = {'allowed_decisions': ['approve', 'reject', 'edit']}
    frames(send(client, sid, 'needs approval'))
    assert client.post(f'/api/v1/sessions/{sid}/fork', json={'message_id': message_id}).status_code == 409
    assert client.post(f'/api/v1/sessions/{sid}/rewind', json={'message_id': message_id}).status_code == 409


def test_failed_fork_is_never_visible_and_leaves_no_orphan_checkpoint(harness, monkeypatch):
    from agent import time_travel
    from governance.store import StoreError
    client, sid, *_ = harness
    frames(send(client, sid))
    before = state(client, sid)
    identifier = 'assistant:' + questions(before)[0]['id']
    owner = os.environ['TEST_PLATFORM_USER']
    old_sessions = sessions.list_sessions(owner)
    seed = time_travel.seed
    child_ids = []

    async def failed_seed(graph, source, child_id):
        child_ids.append(child_id)
        with pytest.raises(StoreError) as error:
            sessions.get_session(child_id, owner)
        assert error.value.status == 404
        await seed(graph, source, child_id)
        raise StoreError('seed failed', 503)

    monkeypatch.setattr(time_travel, 'seed', failed_seed)
    response = client.post(f'/api/v1/sessions/{sid}/fork', json={'message_id': identifier})
    assert response.status_code == 503, response.text
    assert sessions.list_sessions(owner) == old_sessions
    assert state(client, sid) == before
    assert len(child_ids) == 1
    with make_checkpointer() as saver, connection() as conn:
        assert saver.conn.execute('SELECT count(*) AS n FROM checkpoints WHERE thread_id=%s', (child_ids[0],)).fetchone()['n'] == 0


def test_sandbox_history_rejects_missing_versions_and_preserves_checkpoint_artifacts(harness):
    client, sid, model, *_ = harness
    frames(send(client, sid, 'no artifact'))
    empty_id = 'assistant:' + questions(state(client, sid))[0]['id']
    model.responses = [AIMessage(id='artifact-write', content='', tool_calls=[call('write_file',
        {'file_path': '/saved.txt', 'content': 'checkpoint version'})]), AIMessage(id='artifact-answer', content='saved')]
    frames(send(client, sid, 'checkpoint artifact'))
    artifact_id = 'assistant:' + questions(state(client, sid))[-1]['id']
    owner = os.environ['TEST_PLATFORM_USER']
    saved = sessions.get_session(sid, owner)['agent_config']
    saved['agent_config']['sandbox_config_id'] = 'opensandbox-local'
    with connection() as conn:
        conn.execute('UPDATE agent_sessions SET agent_config=%s WHERE id=%s', (Jsonb(saved), sid))
    response = client.get(f'/api/v1/sessions/{sid}/messages/{empty_id}/artifacts')
    assert response.status_code == 501 and '历史文件版本' in response.json()['message']
    assert client.get(f'/api/v1/sessions/{sid}/messages/{artifact_id}/artifacts').status_code == 200
    assert client.get(f'/api/v1/sessions/{sid}/messages/{artifact_id}/artifacts/0/download').content == b'checkpoint version'
    # History must still load, and does not provision a sandbox or manufacture file snapshots.
    assert client.get(f'/api/v1/messages/{sid}/load').status_code == 200
