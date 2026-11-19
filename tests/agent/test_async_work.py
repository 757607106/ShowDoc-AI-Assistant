"""Authorization, native responses and cleanup boundaries for delegated work."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agent import async_runtime, async_work, registry
from governance.store import StoreError


def test_thread_origin_must_match_the_parent_and_child(monkeypatch):
    grant = {'id': 'current', 'parent_session_id': 'parent', 'subagent_name': 'worker'}
    monkeypatch.setattr(registry, 'records', lambda *args: [grant])
    monkeypatch.setattr(registry, 'record', lambda *args: {
        'parent_session_id': 'another-parent', 'subagent_name': 'worker'})
    client = SimpleNamespace(threads=SimpleNamespace(get=AsyncMock(return_value={
        'metadata': {'parent_thread_id': 'parent', 'subagent_name': 'worker', 'delegation_id': 'other'}})))
    monkeypatch.setattr(async_runtime, 'client', lambda grant: client)
    with pytest.raises(StoreError) as error:
        asyncio.run(async_work._context('owner', 'parent', {'thread_id': 'child', 'agent_name': 'worker'}))
    assert error.value.status == 403


@pytest.mark.parametrize('response', [False, None])
def test_native_false_and_null_are_present_responses(response):
    async_work._validate_responses([{'id': 'native', 'value': 'Answer'}], {'native': response})


def test_native_responses_require_exact_ids_and_schema():
    pending = [{'id': 'native', 'value': 'Answer', 'response_schema': {'type': 'boolean'}}]
    async_work._validate_responses(pending, {'native': False})
    for response in ({}, {'stale': False}, {'native': None}, {'native': False, 'extra': True}):
        with pytest.raises(StoreError):
            async_work._validate_responses(pending, response)


def test_cleanup_keeps_authorization_when_remote_stop_fails(monkeypatch):
    grant = {'id': 'grant', 'parent_session_id': 'parent', 'subagent_name': 'worker'}
    monkeypatch.setattr(registry, 'records', lambda *args: [grant])
    deleted = []
    monkeypatch.setattr(registry, 'delete_record', lambda *args: deleted.append(args))
    client = SimpleNamespace(threads=SimpleNamespace(search=AsyncMock(side_effect=OSError('offline'))))
    monkeypatch.setattr(async_runtime, 'client', lambda grant: client)
    with pytest.raises(StoreError) as error:
        asyncio.run(async_work.cleanup('owner', 'parent'))
    assert error.value.status == 503
    assert deleted == []


def test_cleanup_stops_orphan_thread_before_removing_grant(monkeypatch):
    from agent import sandbox
    grant = {'id': 'grant', 'parent_session_id': 'parent', 'subagent_name': 'worker'}
    monkeypatch.setattr(registry, 'records', lambda *args: [grant])
    events = []
    monkeypatch.setattr(sandbox, 'destroy_for_session', lambda *args: events.append('sandbox'))
    monkeypatch.setattr(registry, 'delete_record', lambda *args: events.append('grant'))
    async def stop(*args):
        events.append('stop')
    async def delete(*args):
        events.append('thread')
    client = SimpleNamespace(threads=SimpleNamespace(
        search=AsyncMock(side_effect=[[{'thread_id': 'orphan'}], []]), delete=delete))
    monkeypatch.setattr(async_runtime, 'client', lambda grant: client)
    monkeypatch.setattr(async_work, '_cancel_runs', stop)
    asyncio.run(async_work.cleanup('owner', 'parent'))
    assert events == ['stop', 'sandbox', 'thread', 'grant']


def test_fork_does_not_copy_remote_task_ownership():
    from agent.time_travel import seed
    graph = SimpleNamespace(aupdate_state=AsyncMock(return_value={'configurable': {'thread_id': 'new'}}))
    source = SimpleNamespace(values={'messages': ['history'], 'async_tasks': {'old': {'thread_id': 'foreign'}},
                                    'files': {}, 'memory_contents': 'old memory'})
    asyncio.run(seed(graph, source, 'new'))
    values = graph.aupdate_state.call_args_list[0].args[1]
    assert values == {'messages': ['history'], 'files': {}}
