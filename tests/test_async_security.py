"""Grant boundaries use explicit fake identities; never load deployment credentials."""
import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from langgraph_sdk import Auth

from agent import async_runtime, async_service, async_work, registry, sessions
from governance.store import StoreError


def test_runtime_platform_database_override_does_not_replace_the_runtime_database(monkeypatch):
    from governance.database import database_url
    monkeypatch.setenv('DATABASE_URL', 'postgresql://runtime.invalid/async')
    monkeypatch.setenv('PLATFORM_DATABASE_URL', 'postgresql://platform.invalid/platform')
    assert database_url() == 'postgresql://platform.invalid/platform'
    monkeypatch.delenv('PLATFORM_DATABASE_URL')
    assert database_url() == 'postgresql://runtime.invalid/async'


@pytest.fixture
def scoped_auth(monkeypatch):
    metadata = {'parent_thread_id': 'parent-a', 'subagent_name': 'worker', 'delegation_id': 'original'}
    rows = {('alice', 'own-thread'): metadata,
            ('alice', 'other-parent'): {**metadata, 'parent_thread_id': 'parent-b'},
            ('alice', 'other-child'): {**metadata, 'subagent_name': 'other'},
            ('bob', 'other-owner'): metadata}

    async def lookup(thread_id, owner):
        return rows.get((owner, thread_id))

    monkeypatch.setattr(async_service, '_thread_scope', lookup, raising=False)
    user = SimpleNamespace(identity='alice', parent_session_id='parent-a', subagent_name='worker', grant_id='latest')
    return lambda action: SimpleNamespace(resource='threads', action=action, user=user)


def denied(ctx, value):
    try:
        result = asyncio.run(async_service.authorize(ctx, value))
    except Auth.exceptions.HTTPException as error:
        assert error.status_code in (403, 404)
    else:
        assert result is False, 'A metadata filter alone does not deny Aegra run/update routes'


@pytest.mark.parametrize('action', ['read', 'search', 'update', 'delete', 'create_run'])
@pytest.mark.parametrize('thread', ['other-parent', 'other-child', 'other-owner'])
def test_thread_bound_actions_reject_a_different_grant_scope(scoped_auth, action, thread):
    denied(scoped_auth(action), {'thread_id': thread})


def test_idempotent_create_cannot_adopt_another_parent_thread(scoped_auth):
    denied(scoped_auth('create'), {'thread_id': 'other-parent', 'if_exists': 'do_nothing', 'metadata': {}})


def test_bulk_cancel_without_thread_cannot_escape_the_grant(scoped_auth):
    denied(scoped_auth('update'), {'status': 'all'})


@pytest.mark.parametrize('patch', [
    {'delegation_id': 'latest'}, {'parent_thread_id': 'parent-b'}, {'subagent_name': 'other'},
])
def test_metadata_cannot_rebind_an_existing_thread(scoped_auth, patch):
    denied(scoped_auth('update'), {'thread_id': 'own-thread', 'metadata': patch})


def test_new_grant_can_read_the_same_scope_without_replacing_its_original_binding(scoped_auth):
    value = {'thread_id': 'own-thread'}
    result = asyncio.run(async_service.authorize(scoped_auth('read'), value))
    assert result is not False


def test_thread_creation_overwrites_untrusted_binding_metadata(scoped_auth):
    value = {'metadata': {'parent_thread_id': 'parent-b', 'subagent_name': 'other', 'delegation_id': 'forged'}}
    assert asyncio.run(async_service.authorize(scoped_auth('create'), value)) is not False
    assert value['metadata'] == {'parent_thread_id': 'parent-a', 'subagent_name': 'worker', 'delegation_id': 'latest'}


def test_parent_ownership_is_checked_before_reading_its_checkpoint(monkeypatch):
    def missing_parent(sid, owner):
        assert (sid, owner) == ('bobs-parent', 'alice')
        raise StoreError('not found', 404)
    monkeypatch.setattr(sessions, 'get_session', missing_parent)
    monkeypatch.setattr(async_work, 'async_checkpointer', lambda: pytest.fail('Unauthorized checkpoint read'))
    with pytest.raises(StoreError) as failure:
        asyncio.run(async_work._tasks('alice', 'bobs-parent'))
    assert failure.value.status == 404


@pytest.mark.parametrize('changed', [{'parent_session_id': 'parent-b'}, {'subagent_name': 'other'}])
def test_work_control_rejects_an_origin_grant_with_a_different_scope(monkeypatch, changed):
    grant = {'id': 'latest', 'parent_session_id': 'parent-a', 'subagent_name': 'worker'}
    origin = {**grant, 'id': 'original', **changed}
    monkeypatch.setattr(registry, 'records', lambda kind, owner: [grant] if owner == 'alice' else [])
    monkeypatch.setattr(registry, 'record', lambda kind, key, owner: origin if (key, owner) == ('original', 'alice') else None)
    async def get(thread_id):
        return {'metadata': {'parent_thread_id': 'parent-a', 'subagent_name': 'worker', 'delegation_id': 'original'}}
    monkeypatch.setattr(async_runtime, 'client', lambda grant: SimpleNamespace(threads=SimpleNamespace(get=get)))
    with pytest.raises(StoreError) as failure:
        asyncio.run(async_work._context('alice', 'parent-a', {'agent_name': 'worker', 'thread_id': 'own-thread'}))
    assert failure.value.status == 403


def test_graph_uses_the_threads_original_grant_snapshot(monkeypatch):
    child = {'name': 'worker', 'description': 'Work'}
    original = {'id': 'original', 'owner_id': 'alice', 'parent_session_id': 'parent-a', 'subagent_name': 'worker',
                'agent_id': 'agent', 'agent_config': {'access_level': 'read_only', 'subagents': [child]},
                'knowledge_base_ids': [], 'knowledge_ids': [], 'tag_scopes': []}
    latest = {**original, 'id': 'latest', 'agent_config': {**original['agent_config'], 'system_prompt': 'CHANGED'}}
    monkeypatch.setattr(registry, 'record', lambda kind, key, owner: {'original': original, 'latest': latest}[key])
    async def scope(thread_id, owner):
        return {'delegation_id': 'original'}
    monkeypatch.setattr(async_service, '_thread_scope', scope)
    monkeypatch.setattr(async_runtime, 'headers', lambda grant: {'Authorization': 'Bearer ' + grant['id']})
    monkeypatch.setattr(async_runtime, 'principal', lambda token: ({'id': 'alice', 'role': 'viewer'}, original))
    @asynccontextmanager
    async def store():
        yield object()
    monkeypatch.setattr('agent.checkpointer.async_store', store)
    async def build(*args, **kwargs):
        return kwargs
    monkeypatch.setattr('agent.graph.build_agent', build)
    runtime = SimpleNamespace(user={'identity': 'alice', 'grant_id': 'latest'}, execution_runtime=None)
    async def exercise():
        async with async_service.graph({'configurable': {'thread_id': 'own-thread'}}, runtime) as result:
            assert result['agent_config'] is original['agent_config']
            assert result['knowledge_base_ids'] == []
    asyncio.run(exercise())
