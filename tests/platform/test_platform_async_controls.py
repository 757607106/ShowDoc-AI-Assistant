"""Native SDK and Web controls share remote runs without concurrent parent writes."""
import asyncio
import os
from datetime import datetime, timezone

import psycopg
import pytest
import httpx
from deepagents import create_deep_agent
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.types import interrupt

from agent import async_work, sessions
from agent.checkpointer import async_checkpointer, make_checkpointer
from governance.store import StoreError
from tests.agent.test_harness_native import Model, call


class Remote:
    def __init__(self):
        self.values = [{'run_id': 'r1', 'status': 'running'}]
        self.metadata = {}
        self.waiting = False
        self.cancelled = []
        self.created = []
        self.runs = self
        self.threads = self

    async def list(self, thread_id, *, limit=10, offset=0, status=None):
        rows = [run for run in reversed(self.values) if status is None or run['status'] == status]
        return [dict(row) for row in rows[offset:offset + limit]]

    async def get(self, thread_id, run_id=None):
        if run_id is not None:
            return next(dict(run) for run in self.values if run['run_id'] == run_id)
        status = 'busy' if any(run['status'] in ('pending', 'running') for run in self.values) else 'interrupted' if self.waiting else 'idle'
        return {'status': status, 'metadata': self.metadata}

    async def create(self, thread_id, graph_id, **kwargs):
        self.created.append(kwargs)
        run = {'run_id': 'r' + str(len(self.values) + 1), 'status': 'pending'}
        self.values.append(run)
        self.waiting = False
        return dict(run)

    async def cancel(self, thread_id, run_id, **kwargs):
        self.cancelled.append(run_id)
        for run in self.values:
            if run['run_id'] == run_id and run['status'] in ('pending', 'running'):
                run['status'] = 'interrupted'

    async def update(self, thread_id, *, metadata):
        self.metadata.update(metadata)

    async def get_state(self, thread_id, **kwargs):
        return {'interrupts': [{'id': 'child-question', 'value': 'Answer'}] if self.waiting else [], 'values': {}}


@pytest.fixture
def setup_control(monkeypatch):
    owner = os.environ['TEST_PLATFORM_USER']
    child = {'name': 'worker', 'description': 'Worker', 'execution_mode': 'async', 'update_strategy': 'enqueue'}
    config = {'subagents': [child], 'allowed_tools': [], 'mcp_selection_mode': 'none', 'memory_enabled': False}
    sid = sessions.create_session('Isolated async controls', owner, agent_config={'agent_config': config})['id']
    remote = Remote()
    grant = {'agent_config': config}
    async def context(*args):
        return remote, grant
    monkeypatch.setattr(async_work, '_context', context)
    monkeypatch.setattr('deepagents.middleware.async_subagents._ClientCache.get_async', lambda self, name: remote)
    now = datetime.now(timezone.utc).isoformat()
    task = {'task_id': 'work', 'thread_id': 'work', 'run_id': 'r1', 'agent_name': 'worker',
            'status': 'running', 'created_at': now, 'last_updated_at': now, 'last_checked_at': now}
    def build(model, saver, tools=()):
        return create_deep_agent(model=model, checkpointer=saver, tools=list(tools),
            middleware=[async_work.NativeAsyncTasks(owner, sid)],
            subagents=[{'name': 'worker', 'description': 'Worker', 'graph_id': 'delegated_agent',
                        'url': 'http://127.0.0.1:9', 'notify_parent': False, 'update_strategy': 'enqueue'}])
    return owner, sid, remote, task, build


@pytest.mark.parametrize('parent_busy', [False, True])
def test_web_enqueue_then_native_cancel_stops_every_run(setup_control, parent_busy):
    owner, sid, remote, task, build = setup_control
    async def exercise():
        async with async_checkpointer() as saver:
            graph = build(Model(responses=[AIMessage(content='Seed'),
                call('cancel_async_task', {'task_id': 'work'}, 'native-cancel'), AIMessage(content='Done')]), saver)
            cfg = {'configurable': {'thread_id': sid}}
            await graph.ainvoke({'messages': [{'role': 'user', 'content': 'Seed'}], 'async_tasks': {'work': task}}, cfg)
            with psycopg.connect(os.environ['AGENT_DATABASE_URL'], autocommit=True) as lock:
                if parent_busy:
                    lock.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))', ('harness:' + sid,))
                updated = await async_work.control(owner, sid, 'work', 'update', {'message': 'Queued follow-up'})
                assert updated['run_id'] == 'r2'
                saved = await graph.aget_state(cfg)
                assert [message.content for message in saved.values['messages']] == ['Seed', 'Seed']
                assert saved.values['async_tasks']['work']['run_id'] == ('r1' if parent_busy else 'r2')
                if not parent_busy:
                    assert saved.values['async_tasks']['work']['superseded_run_ids'] == ['r1']
                complete = await graph.ainvoke({'messages': [{'role': 'user', 'content': 'Cancel it'}]}, cfg)
            latest = complete['async_tasks']['work']
            assert latest['run_id'] == 'r2' and latest['status'] == 'cancelled'
            assert {'r1', 'r2'} <= set(remote.cancelled)
            assert all(run['status'] == 'interrupted' for run in remote.values)
            assert remote.metadata['deepagents_cancelled_run_id'] == 'r2'
    asyncio.run(exercise())


@pytest.mark.parametrize('action', ['update', 'resume', 'cancel'])
def test_child_controls_work_while_parent_holds_execution_lock(setup_control, action):
    owner, sid, remote, task, build = setup_control
    async def exercise():
        async with async_checkpointer() as saver:
            graph = build(Model(responses=[AIMessage(content='Seed')]), saver)
            cfg = {'configurable': {'thread_id': sid}}
            await graph.ainvoke({'messages': [{'role': 'user', 'content': 'Seed'}], 'async_tasks': {'work': task}}, cfg)
            if action == 'resume':
                remote.values[0]['status'] = 'success'
                remote.waiting = True
            with psycopg.connect(os.environ['AGENT_DATABASE_URL'], autocommit=True) as lock:
                lock.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))', ('harness:' + sid,))
                result = await async_work.control(owner, sid, 'work', action,
                    {'message': 'Update', 'responses': {'child-question': False}})
            assert result['state'] in ('pending', 'cancelled')
            assert (await graph.aget_state(cfg)).values['async_tasks']['work']['run_id'] == 'r1'
            reconciled = await async_work.reconcile_parent(graph, await graph.aget_state(cfg), owner, sid)
            assert reconciled.values['async_tasks']['work']['status'] == ('cancelled' if action == 'cancel' else 'pending')
    asyncio.run(exercise())


@pytest.mark.parametrize('parent_busy', [False, True])
def test_waiting_child_can_be_cancelled_without_consuming_parent_interrupt(setup_control, parent_busy):
    owner, sid, remote, task, build = setup_control
    @tool
    def parent_question() -> str:
        """Wait for the parent's independent answer."""
        return str(interrupt('Parent question'))
    async def exercise():
        async with async_checkpointer() as saver:
            graph = build(Model(responses=[call('parent_question', {}, 'parent-question')]), saver, [parent_question])
            cfg = {'configurable': {'thread_id': sid}}
            await graph.ainvoke({'messages': [{'role': 'user', 'content': 'Seed'}], 'async_tasks': {'work': task}}, cfg)
            before = await graph.aget_state(cfg)
            assert before.interrupts
            remote.values[0]['status'] = 'success'
            remote.waiting = True
            with psycopg.connect(os.environ['AGENT_DATABASE_URL'], autocommit=True) as lock:
                if parent_busy:
                    lock.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))', ('harness:' + sid,))
                result = await async_work.control(owner, sid, 'work', 'cancel', {})
            assert result['state'] == 'cancelled'
            after = await graph.aget_state(cfg)
            assert after.config == before.config and after.interrupts == before.interrupts
            observed, _ = await async_work._live_task(remote, task)
            assert observed['status'] == 'cancelled'
            remote.values.append({'run_id': 'r2', 'status': 'running'})
            observed, _ = await async_work._live_task(remote, task)
            assert observed['status'] == 'running'
    asyncio.run(exercise())


@pytest.mark.parametrize('action', ['update', 'resume', 'cancel'])
def test_web_routes_control_child_while_parent_is_running(authenticated_client, setup_control, action):
    owner, sid, remote, task, build = setup_control
    async def seed():
        async with async_checkpointer() as saver:
            graph = build(Model(responses=[AIMessage(content='Seed')]), saver)
            await graph.ainvoke({'messages': [{'role': 'user', 'content': 'Seed'}], 'async_tasks': {'work': task}},
                               {'configurable': {'thread_id': sid}})
    asyncio.run(seed())
    if action == 'resume':
        remote.values[0]['status'] = 'success'
        remote.waiting = True
    with psycopg.connect(os.environ['AGENT_DATABASE_URL'], autocommit=True) as lock:
        lock.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))', ('harness:' + sid,))
        response = authenticated_client.post(f'/api/v1/sessions/{sid}/background-work/work/{action}',
            json={'message': 'Updated', 'responses': {'child-question': None}})
    assert response.status_code == 200, response.json
    assert response.json['data']['state'] in ('pending', 'cancelled')


def test_native_cancel_and_web_enqueue_share_the_child_operation_lock(setup_control):
    owner, sid, remote, task, build = setup_control
    async def exercise():
        started, release = asyncio.Event(), asyncio.Event()
        original = remote.cancel
        async def held_cancel(*args, **kwargs):
            if not started.is_set():
                started.set()
                await release.wait()
            return await original(*args, **kwargs)
        remote.cancel = held_cancel
        async with async_checkpointer() as saver:
            graph = build(Model(responses=[AIMessage(content='Seed'),
                call('cancel_async_task', {'task_id': 'work'}, 'native-cancel'), AIMessage(content='Done')]), saver)
            cfg = {'configurable': {'thread_id': sid}}
            await graph.ainvoke({'messages': [{'role': 'user', 'content': 'Seed'}], 'async_tasks': {'work': task}}, cfg)
            cancelled = asyncio.create_task(graph.ainvoke({'messages': [{'role': 'user', 'content': 'Cancel'}]}, cfg))
            await asyncio.wait_for(started.wait(), 5)
            update = asyncio.create_task(async_work.control(owner, sid, 'work', 'update', {'message': 'Too late'}))
            await asyncio.sleep(.05)
            assert remote.created == [] and not update.done()
            release.set()
            await cancelled
            with pytest.raises(StoreError) as error:
                await update
            assert error.value.status == 409 and remote.created == []
    asyncio.run(exercise())


def test_control_during_inflight_parent_model_does_not_lose_the_new_run(setup_control):
    owner, sid, remote, task, build = setup_control
    async def exercise():
        entered, proceed = asyncio.Event(), asyncio.Event()
        class HeldModel(Model):
            async def _agenerate(self, messages, *args, **kwargs):
                if not entered.is_set() and any(message.content == 'In-flight model' for message in messages):
                    entered.set()
                    await proceed.wait()
                return await super()._agenerate(messages, *args, **kwargs)
        async with async_checkpointer() as saver:
            graph = build(HeldModel(responses=[AIMessage(content='Seed'),
                call('cancel_async_task', {'task_id': 'work'}, 'native-cancel'), AIMessage(content='Done')]), saver)
            cfg = {'configurable': {'thread_id': sid}}
            await graph.ainvoke({'messages': [{'role': 'user', 'content': 'Seed'}], 'async_tasks': {'work': task}}, cfg)
            with psycopg.connect(os.environ['AGENT_DATABASE_URL'], autocommit=True) as lock:
                lock.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))', ('harness:' + sid,))
                parent = asyncio.create_task(graph.ainvoke({'messages': [{'role': 'user', 'content': 'In-flight model'}]}, cfg))
                await asyncio.wait_for(entered.wait(), 5)
                updated = await async_work.control(owner, sid, 'work', 'update', {'message': 'Queued while model runs'})
                assert updated['run_id'] == 'r2'
                assert (await graph.aget_state(cfg)).values['async_tasks']['work']['run_id'] == 'r1'
                proceed.set()
                complete = await parent
            assert complete['async_tasks']['work']['run_id'] == 'r2'
            assert complete['async_tasks']['work']['status'] == 'cancelled'
            assert {'r1', 'r2'} <= set(remote.cancelled)
            assert [message.content for message in complete['messages'] if message.type == 'human'] == ['Seed', 'In-flight model']
    asyncio.run(exercise())


def test_cleanup_waits_for_child_control_without_deadlocking_parent_sync(setup_control, monkeypatch):
    owner, sid, remote, task, build = setup_control
    async def exercise():
        entered, proceed = asyncio.Event(), asyncio.Event()
        sequence = []
        original_create = remote.create
        async def held_create(*args, **kwargs):
            entered.set()
            await proceed.wait()
            sequence.append('control')
            return await original_create(*args, **kwargs)
        async def cleanup(*args):
            sequence.append('cleanup')
        monkeypatch.setattr(remote, 'create', held_create)
        monkeypatch.setattr(async_work, 'cleanup', cleanup)
        async with async_checkpointer() as saver:
            graph = build(Model(responses=[AIMessage(content='Seed')]), saver)
            await graph.ainvoke({'messages': [{'role': 'user', 'content': 'Seed'}], 'async_tasks': {'work': task}},
                               {'configurable': {'thread_id': sid}})
        control = asyncio.create_task(async_work.control(owner, sid, 'work', 'update', {'message': 'Update'}))
        await asyncio.wait_for(entered.wait(), 5)
        deleted = asyncio.create_task(asyncio.to_thread(sessions.delete_session, sid, owner))
        # Delete owns the parent lock while waiting for the short child-control lock.
        for _ in range(100):
            with psycopg.connect(os.environ['AGENT_DATABASE_URL'], autocommit=True) as probe:
                acquired = probe.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0))', ('harness:' + sid,)).fetchone()[0]
            if not acquired:
                break
            await asyncio.sleep(.01)
        else:
            pytest.fail('delete did not acquire the parent lock')
        assert not deleted.done() and sequence == []
        proceed.set()
        assert (await control)['run_id'] == 'r2'
        assert await deleted is True
        assert sequence == ['control', 'cleanup']
        with pytest.raises(StoreError) as error:
            sessions.get_session(sid, owner)
        assert error.value.status == 404
    asyncio.run(exercise())


@pytest.mark.parametrize('failure,deferred', [('network', True), (503, True), (401, False), (403, False)])
def test_parent_reconciliation_only_defers_transient_remote_failures(setup_control, monkeypatch, failure, deferred):
    owner, sid, remote, task, build = setup_control
    async def failed_list(*args, **kwargs):
        request = httpx.Request('GET', 'http://127.0.0.1:9/threads/work/runs')
        if failure == 'network':
            raise httpx.ConnectError('Offline', request=request)
        raise httpx.HTTPStatusError('Remote failure', request=request,
                                   response=httpx.Response(failure, request=request))
    async def exercise():
        async with async_checkpointer() as saver:
            graph = build(Model(responses=[AIMessage(content='Seed')]), saver)
            cfg = {'configurable': {'thread_id': sid}}
            await graph.ainvoke({'messages': [{'role': 'user', 'content': 'Seed'}], 'async_tasks': {'work': task}}, cfg)
            before = await graph.aget_state(cfg)
            monkeypatch.setattr(remote, 'list', failed_list)
            if deferred:
                assert await async_work.reconcile_parent(graph, before, owner, sid) is before
            else:
                with pytest.raises(httpx.HTTPStatusError):
                    await async_work.reconcile_parent(graph, before, owner, sid)
            with pytest.raises(httpx.HTTPError):
                await async_work._refreshed(owner, sid, {'work': task})
    asyncio.run(exercise())


def test_old_async_tasks_survive_a_parent_configuration_without_async_children(setup_control, monkeypatch):
    from agent import graph as graph_module, registry
    owner, sid, remote, task, build = setup_control
    async def no_tools(*args, **kwargs):
        return []
    monkeypatch.setattr(graph_module, 'load_knowledge_mcp_tools', no_tools)
    monkeypatch.setattr(registry, 'mcp_tools', no_tools)
    monkeypatch.setattr(graph_module, 'make_governance_tools', lambda *args: [])
    monkeypatch.setattr(graph_module, 'build_model', lambda *args: Model(responses=[AIMessage(content='New config')]))
    async def exercise():
        async with async_checkpointer() as saver:
            graph = build(Model(responses=[AIMessage(content='Seed')]), saver)
            cfg = {'configurable': {'thread_id': sid}}
            await graph.ainvoke({'messages': [{'role': 'user', 'content': 'Seed'}], 'async_tasks': {'work': task}}, cfg)
            replacement = await graph_module.build_agent(saver, api_key='', owner_id=owner, role='admin', session_id=sid,
                agent_config={'subagents': [], 'mcp_selection_mode': 'none', 'allowed_tools': [], 'memory_enabled': False})
            result = await replacement.ainvoke({'messages': [{'role': 'user', 'content': 'New config'}]}, cfg)
            assert result['async_tasks']['work'] == task
    asyncio.run(exercise())


def test_sync_plain_tools_still_use_native_execution(setup_control):
    owner, sid, remote, task, build = setup_control
    with make_checkpointer() as saver:
        graph = build(Model(responses=[call('write_file', {'file_path': '/sync.txt', 'content': 'sync'}),
                                       AIMessage(content='Done')]), saver)
        result = graph.invoke({'messages': [{'role': 'user', 'content': 'Write a file'}]},
                              {'configurable': {'thread_id': sid}})
    assert result['files']['/sync.txt']['content'] == 'sync'


def test_sync_native_cancel_uses_the_same_reconciled_run_references(setup_control, monkeypatch):
    owner, sid, remote, task, build = setup_control
    class SyncRemote:
        @property
        def runs(self):
            return self
        def get(self, thread_id, run_id):
            return next(dict(run) for run in remote.values if run['run_id'] == run_id)
        def cancel(self, thread_id, run_id, **kwargs):
            remote.cancelled.append(run_id)
            for run in remote.values:
                if run['run_id'] == run_id and run['status'] in ('pending', 'running'):
                    run['status'] = 'interrupted'
    monkeypatch.setattr('deepagents.middleware.async_subagents._ClientCache.get_sync', lambda self, name: SyncRemote())
    with make_checkpointer() as saver:
        graph = build(Model(responses=[AIMessage(content='Seed'),
            call('cancel_async_task', {'task_id': 'work'}, 'native-cancel'), AIMessage(content='Done')]), saver)
        cfg = {'configurable': {'thread_id': sid}}
        graph.invoke({'messages': [{'role': 'user', 'content': 'Seed'}], 'async_tasks': {'work': task}}, cfg)
        asyncio.run(async_work.control(owner, sid, 'work', 'update', {'message': 'Queued'}))
        result = graph.invoke({'messages': [{'role': 'user', 'content': 'Cancel'}]}, cfg)
    assert result['async_tasks']['work']['status'] == 'cancelled'
    assert result['async_tasks']['work']['run_id'] == 'r2'
    assert {'r1', 'r2'} <= set(remote.cancelled)


@pytest.mark.parametrize('remote_status,waiting,blocked', [
    ('running', False, True), ('pending', False, True), ('success', True, True), ('success', False, False)])
def test_rewind_checks_actual_remote_activity(setup_control, remote_status, waiting, blocked):
    owner, sid, remote, task, build = setup_control
    async def exercise():
        async with async_checkpointer() as saver:
            graph = build(Model(responses=[AIMessage(content='Seed')]), saver)
            await graph.ainvoke({'messages': [{'role': 'user', 'content': 'Seed'}], 'async_tasks': {'work': task}},
                               {'configurable': {'thread_id': sid}})
        remote.values[0]['status'] = remote_status
        remote.waiting = waiting
        if blocked:
            with pytest.raises(StoreError) as error:
                await async_work.require_rewind_safe(owner, sid)
            assert error.value.status == 409
        else:
            await async_work.require_rewind_safe(owner, sid)
    asyncio.run(exercise())
