"""Read/control native async tasks through the deployed Agent Protocol service."""
import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import datetime, timezone

import anyio
import httpx
from langchain.agents.middleware import AgentMiddleware
from langgraph.types import Command
from deepagents.middleware.async_subagents import AsyncSubAgentState

from agent import async_runtime, registry, sessions
from agent.checkpointer import async_checkpointer
from agent.interactions import validate_responses as _validate_responses
from governance.store import StoreError

_STATES = {'success': 'succeeded', 'error': 'failed', 'timeout': 'failed',
           'interrupted': 'cancelled', 'cancelled': 'cancelled',
           'running': 'running', 'pending': 'pending', 'waiting': 'waiting'}
_CANCELLED_RUN = 'deepagents_cancelled_run_id'
_ASYNC_TOOLS = {'start_async_task', 'check_async_task', 'update_async_task',
                'cancel_async_task', 'list_async_tasks'}


@asynccontextmanager
async def control_scope(owner_id, sid):
    manager = sessions._background_mutation(sid, owner_id)
    row = await anyio.to_thread.run_sync(manager.__enter__)
    try:
        yield row
    finally:
        with anyio.CancelScope(shield=True):
            await anyio.to_thread.run_sync(lambda: manager.__exit__(None, None, None))


async def _active_runs(client, thread_id):
    result = []
    for status in ('pending', 'running'):
        offset = 0
        while batch := await client.runs.list(thread_id, limit=100, offset=offset, status=status):
            result.extend(batch)
            if len(batch) < 100:
                break
            offset += len(batch)
    return result


async def _live_task(client, task, *, active_refs=False):
    from deepagents.middleware.async_subagents import _task_status
    runs = await client.runs.list(task['thread_id'], limit=1)
    if not runs:
        raise StoreError('后台运行不存在', 404)
    run = runs[0]
    thread = await client.threads.get(task['thread_id'])
    status = _task_status(run, thread)
    if status not in ('running', 'pending') and (
            thread.get('metadata', {}).get(_CANCELLED_RUN) == run['run_id']
            or task.get('status') == 'cancelled' and task['run_id'] == run['run_id']):
        status = 'cancelled'
    refs = list(task.get('superseded_run_ids', []))
    if run['run_id'] != task['run_id']:
        refs.append(task['run_id'])
    if active_refs:
        refs.extend(item['run_id'] for item in await _active_runs(client, task['thread_id']))
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    updated = {**task, 'run_id': run['run_id'], 'status': status, 'last_checked_at': now,
               'last_updated_at': now if (run['run_id'], status) != (task['run_id'], task['status'])
                                  else task.get('last_updated_at', now)}
    if refs:
        updated['superseded_run_ids'] = list(dict.fromkeys(ref for ref in refs if ref != run['run_id']))
    return updated, run


async def _refreshed(owner_id, sid, tasks):
    result = {}
    for identifier, task in tasks.items():
        client, _ = await _context(owner_id, sid, task)
        result[identifier], _ = await _live_task(client, task, active_refs=True)
    return result


async def _write_tasks(graph, state, tasks):
    # External controls never change a parent's pending approval or scheduled nodes.
    if state.next or state.interrupts:
        return state
    current = state.values.get('async_tasks', {})
    changes = {key: task for key, task in tasks.items() if any(
        task.get(field) != current.get(key, {}).get(field)
        for field in ('run_id', 'status', 'superseded_run_ids'))}
    if not changes:
        return state
    from langgraph.graph import END
    updated = await graph.aupdate_state(state.config, {'async_tasks': changes}, as_node='model')
    await graph.aupdate_state(updated, None, as_node=END)
    return await graph.aget_state({'configurable': {'thread_id': state.config['configurable']['thread_id']}}, subgraphs=True)


async def reconcile_parent(graph, state, owner_id, sid):
    """Called under the parent's execution lock, after its iterator has stopped."""
    tasks = state.values.get('async_tasks', {})
    if not tasks or state.next or state.interrupts:
        return state
    async with control_scope(owner_id, sid):
        try:
            fresh = await _refreshed(owner_id, sid, tasks)
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                raise
            logging.getLogger(__name__).warning('Async reconciliation deferred: session=%s error=%s', sid, type(exc).__name__)
            return state
        return await _write_tasks(graph, state, fresh)


async def _sync_idle(owner_id, sid, tasks, grant):
    import psycopg
    from agent.checkpointer import database_url
    from agent.graph import build_agent
    # A running parent reconciles at native-tool and completed-run boundaries.
    async with await psycopg.AsyncConnection.connect(database_url(), autocommit=True) as lock:
        cursor = await lock.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0))', ('harness:' + sid,))
        if not (await cursor.fetchone())[0]:
            return
        selected = await anyio.to_thread.run_sync(lambda: sessions.get_session(sid, owner_id))
        config = selected['agent_config'].get('agent_config') or grant['agent_config']
        async with async_checkpointer() as saver:
            graph = await build_agent(saver, api_key='', owner_id=owner_id, load_tools=False,
                                      agent_config=config, session_id=sid)
            state = await graph.aget_state({'configurable': {'thread_id': sid}}, subgraphs=True)
            await _write_tasks(graph, state, tasks)


class NativeAsyncTasks(AgentMiddleware):
    """Reconcile external controls through native tool Commands, not concurrent graph writes."""
    state_schema = AsyncSubAgentState

    def __init__(self, owner_id, sid):
        self.owner_id, self.sid = owner_id, sid

    def wrap_tool_call(self, request, handler):
        if not self.sid or request.tool_call['name'] not in _ASYNC_TOOLS:
            return handler(request)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise RuntimeError('事件循环内请使用 ainvoke/astream 执行后台子代理控制')
        async def execute(updated):
            return handler(updated)
        return asyncio.run(self.awrap_tool_call(request, execute))

    async def awrap_tool_call(self, request, handler):
        name = request.tool_call['name']
        if not self.sid or name not in _ASYNC_TOOLS:
            return await handler(request)
        async with control_scope(self.owner_id, self.sid):
            tasks = request.state.get('async_tasks', {})
            identifier = request.tool_call.get('args', {}).get('task_id')
            selected = tasks if name == 'list_async_tasks' else {identifier: tasks[identifier]} if identifier in tasks else {}
            fresh = await _refreshed(self.owner_id, self.sid, selected)
            state = {**request.state, 'async_tasks': {**tasks, **fresh}}
            updated_request = replace(request, state=state, runtime=replace(request.runtime, state=state))
            result = await handler(updated_request)
            if (name == 'cancel_async_task' and identifier in fresh and isinstance(result, Command)
                    and result.update.get('async_tasks', {}).get(identifier, {}).get('status') == 'cancelled'):
                client, _ = await _context(self.owner_id, self.sid, fresh[identifier])
                await _cancel_runs(client, fresh[identifier]['thread_id'])
                await client.threads.update(fresh[identifier]['thread_id'],
                    metadata={_CANCELLED_RUN: fresh[identifier]['run_id']})
            if isinstance(result, Command):
                values = result.update or {}
                return replace(result, update={**values, 'async_tasks': {**fresh, **values.get('async_tasks', {})}})
            return Command(update={'messages': [result], 'async_tasks': fresh}) if fresh else result


async def _tasks(owner_id, sid):
    await anyio.to_thread.run_sync(lambda: sessions.get_session(sid, owner_id))
    async with async_checkpointer() as saver:
        saved = await saver.aget_tuple({'configurable': {'thread_id': sid}})
    return saved.checkpoint.get('channel_values', {}).get('async_tasks', {}) if saved else {}


async def _context(owner_id, sid, task):
    grants = await anyio.to_thread.run_sync(lambda: registry.records(async_runtime.GRANT_KIND, owner_id))
    grant = next((item for item in reversed(grants) if item['parent_session_id'] == sid
                  and item['subagent_name'] == task['agent_name']), None)
    if not grant:
        raise StoreError('后台任务的授权绑定已失效', 409)
    client = async_runtime.client(grant)
    thread = await client.threads.get(task['thread_id'])
    metadata = thread.get('metadata', {})
    if (metadata.get('parent_thread_id'), metadata.get('subagent_name')) != (sid, task['agent_name']):
        raise StoreError('后台任务不属于当前会话', 403)
    origin = metadata.get('delegation_id')
    if not isinstance(origin, str):
        raise StoreError('后台任务缺少原始授权', 403)
    grant = await anyio.to_thread.run_sync(lambda: registry.record(async_runtime.GRANT_KIND, origin, owner_id))
    if (grant['parent_session_id'], grant['subagent_name']) != (sid, task['agent_name']):
        raise StoreError('后台任务的原始授权范围不匹配', 403)
    return async_runtime.client(grant), grant


def _interrupts(state):
    found = {}
    def visit(value):
        for item in value.get('interrupts', []):
            if isinstance(item, dict) and isinstance(item.get('id'), str):
                found[item['id']] = item
        for task in value.get('tasks', []):
            for item in task.get('interrupts', []):
                if isinstance(item, dict) and isinstance(item.get('id'), str):
                    found[item['id']] = item
            if isinstance(task.get('state'), dict):
                visit(task['state'])
    visit(state)
    return list(found.values())


async def _observe(owner_id, sid, task, *, detail=False):
    client, grant = await _context(owner_id, sid, task)
    task, run = await _live_task(client, task)
    status = task['status']
    row = {'work_id': task['task_id'], 'kind': 'async_subagent', 'title': task['agent_name'],
        'state': _STATES.get(status, 'lost'), 'saved_status': status, 'read_only': False,
        'can_cancel': status in ('running', 'pending', 'waiting'),
        'started_at': task.get('created_at'), 'finished_at': run.get('updated_at') if status in ('success', 'error', 'timeout', 'cancelled', 'interrupted') else None}
    if detail:
        state = await client.threads.get_state(task['thread_id'], subgraphs=True)
        from webapi.weknora.adapter import text, message_dict
        messages = [message_dict(message) for message in state.get('values', {}).get('messages', [])]
        answers = [text(message.get('content')) for message in messages if message.get('type', message.get('role')) in ('ai', 'assistant') and not message.get('tool_calls')]
        result = {'display_type': 'async_subagent', 'output': answers[-1] if answers else '',
                  'interrupts': _interrupts(state), 'error': str(run.get('error') or '')}
        if 'structured_response' in state.get('values', {}) and status == 'success':
            result['structured_response'] = state['values']['structured_response']
        from webapi.weknora import async_views
        result.update(async_views.payload(owner_id, sid, task, state, grant, status))
        row['result'] = result
    return row, client, grant, run


async def list_work(owner_id, sid):
    tasks = await _tasks(owner_id, sid)
    rows = []
    for task in tasks.values():
        try:
            row, *_ = await _observe(owner_id, sid, task)
        except Exception as exc:
            if isinstance(exc, StoreError) and exc.status in (401, 403, 404):
                raise
            row = {'work_id': task['task_id'], 'kind': 'async_subagent', 'title': task['agent_name'],
                   'state': 'lost', 'saved_status': task.get('status'), 'read_only': False,
                   'started_at': task.get('created_at'), 'can_cancel': False}
        rows.append(row)
    return rows


async def task_detail(owner_id, sid, work_id):
    task = (await _tasks(owner_id, sid)).get(work_id)
    if task is None:
        raise StoreError('原生后台任务不存在', 404)
    try:
        row, *_ = await _observe(owner_id, sid, task, detail=True)
        return row
    except StoreError:
        raise
    except Exception as exc:
        raise StoreError('异步运行服务不可用，请稍后重试', 503) from exc


async def cleanup(owner_id, sid):
    """Stop and remove delegated threads before deleting their parent's identity."""
    grants = await anyio.to_thread.run_sync(lambda: registry.records(async_runtime.GRANT_KIND, owner_id))
    grants = [item for item in grants if item['parent_session_id'] == sid]
    from agent.sandbox import destroy_for_session
    try:
        for name in dict.fromkeys(item['subagent_name'] for item in grants):
            grant = next(item for item in reversed(grants) if item['subagent_name'] == name)
            client = async_runtime.client(grant)
            while threads := await client.threads.search(
                    metadata={'parent_thread_id': sid, 'subagent_name': name}, limit=100):
                for thread in threads:
                    thread_id = thread['thread_id']
                    # Search includes a thread created just before a failed parent launch.
                    await _cancel_runs(client, thread_id)
                    await anyio.to_thread.run_sync(lambda: destroy_for_session(owner_id, thread_id))
                    await client.threads.delete(thread_id)
    except StoreError:
        raise
    except Exception as exc:
        raise StoreError('后台任务清理失败，会话和授权已保留，请稍后重试', 503) from exc
    for grant in grants:
        await anyio.to_thread.run_sync(lambda: registry.delete_record(async_runtime.GRANT_KIND, grant['id'], owner_id))


async def _cancel_runs(client, thread_id):
    for status in ('pending', 'running'):
        while runs := await client.runs.list(thread_id, limit=100, status=status):
            for run in runs:
                await client.runs.cancel(thread_id, run['run_id'], wait=True)
            if any(item['run_id'] in {run['run_id'] for run in runs}
                   for item in await client.runs.list(thread_id, limit=100, status=status)):
                raise StoreError('后台运行尚未确认停止，请稍后重试', 503)
    for status in ('pending', 'running'):
        if await client.runs.list(thread_id, limit=1, status=status):
            raise StoreError('后台运行尚未确认停止，请稍后重试', 503)



async def cleanup_main(owner_id, sid):
    """Cancel the main session's official runs and remove its run/thread bindings."""
    try:
        client, _ = await anyio.to_thread.run_sync(lambda: async_runtime.main_client(owner_id, sid))
    except StoreError as exc:
        if exc.status != 404:
            raise
        client = None
    if client is not None:
        try:
            await _cancel_runs(client, sid)
            await client.threads.delete(sid)
        except Exception as exc:
            status = getattr(getattr(exc, 'response', None), 'status_code', None)
            if status != 404:
                raise StoreError('主会话运行记录清理失败，请稍后重试', 503) from exc
    grants = await anyio.to_thread.run_sync(lambda: registry.records(async_runtime.MAIN_KIND, owner_id))
    for grant in grants:
        if grant['session_id'] == sid:
            await anyio.to_thread.run_sync(lambda: registry.delete_record(async_runtime.MAIN_KIND, grant['id'], owner_id))


async def require_rewind_safe(owner_id, sid):
    try:
        client, _ = await anyio.to_thread.run_sync(lambda: async_runtime.main_client(owner_id, sid))
    except StoreError as exc:
        if exc.status != 404:
            raise
        client = None
    if client is not None and await _active_runs(client, sid):
        raise StoreError('请先完成或停止当前生成，再回退会话', 409)
    for task in (await _tasks(owner_id, sid)).values():
        try:
            row, *_ = await _observe(owner_id, sid, task)
        except StoreError:
            raise
        except Exception as exc:
            raise StoreError('无法核实后台任务状态，请稍后回退', 503) from exc
        if row['state'] in ('pending', 'running', 'waiting', 'lost'):
            raise StoreError('请先完成或取消后台任务，再回退会话', 409)


async def control(owner_id, sid, work_id, action, body):
    async with control_scope(owner_id, sid):
        return await _control(owner_id, sid, work_id, action, body)


async def _control(owner_id, sid, work_id, action, body):
    task = (await _tasks(owner_id, sid)).get(work_id)
    if task is None:
        raise StoreError('原生后台任务不存在', 404)
    try:
        client, grant = await _context(owner_id, sid, task)
        task, run = await _live_task(client, task, active_refs=True)
        state = _STATES.get(task['status'], 'lost')
        if action != 'cancel' and task.get('status') == 'cancelled':
            raise StoreError('后台任务已取消，请新建任务', 409)
        if action == 'cancel':
            await _cancel_runs(client, task['thread_id'])
            if state in ('succeeded', 'failed'):
                return {'work_id': work_id, 'state': state}
            # A paused run is already terminal remotely; persist its cancellation intent.
            await client.threads.update(task['thread_id'], metadata={_CANCELLED_RUN: run['run_id']})
            now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            task = {**task, 'status': 'cancelled', 'last_checked_at': now, 'last_updated_at': now}
            await _sync_idle(owner_id, sid, {work_id: task}, grant)
            return {'work_id': work_id, 'state': 'cancelled'}
        if action == 'update':
            message = body.get('message')
            if not isinstance(message, str) or not message.strip() or len(message) > 100_000:
                raise StoreError('更新内容须为 1 至 100000 字文本', 400)
            child = next(child for child in grant['agent_config']['subagents'] if child['name'] == task['agent_name'])
            run = await client.runs.create(task['thread_id'], async_runtime.GRAPH_ID,
                input={'messages': [{'role': 'user', 'content': message}]},
                multitask_strategy=child.get('update_strategy', 'interrupt'), durability='sync')
        elif action == 'resume':
            state = await client.threads.get_state(task['thread_id'], subgraphs=True)
            pending = _interrupts(state)
            if not pending:
                raise StoreError('后台中断已失效，请刷新', 409)
            _validate_responses(pending, body.get('responses'))
            run = await client.runs.create(task['thread_id'], async_runtime.GRAPH_ID,
                command={'resume': body['responses']}, multitask_strategy='reject', durability='sync')
        else:
            raise StoreError('后台任务操作无效', 400)
        from deepagents.middleware.async_subagents import _build_update_command
        strategy = child.get('update_strategy', 'interrupt') if action == 'update' else 'interrupt'
        updated = _build_update_command(task, run, strategy, 'web-control').update['async_tasks']
        await _sync_idle(owner_id, sid, updated, grant)
        return {'work_id': work_id, 'run_id': run['run_id'], 'state': _STATES.get(run['status'], 'pending')}
    except StoreError:
        raise
    except Exception as exc:
        status = getattr(getattr(exc, 'response', None), 'status_code', None)
        raise StoreError('后台任务状态已变化，请刷新重试' if status in (400, 404, 409) else '后台任务操作失败，请重试',
                         409 if status in (400, 404, 409) else 503) from exc
