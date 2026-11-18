"""Owner-scoped, read-only WeKnora views of existing Agent Protocol threads."""
from types import SimpleNamespace

from governance.store import StoreError
from webapi import weknora_traces
from webapi.weknora_adapter import history, media_files
from webapi.weknora_prompts import cards, card_event

NAMESPACE = '__async__'


def snapshot(data):
    def interrupts(items):
        return [SimpleNamespace(**item) for item in items if isinstance(item, dict) and isinstance(item.get('id'), str)]
    tasks = []
    for task in data.get('tasks', []):
        child = task.get('state')
        if not isinstance(child, dict) or 'values' not in child:
            child = {'values': data.get('values', {}), 'interrupts': task.get('interrupts', [])}
        tasks.append(SimpleNamespace(state=snapshot(child)))
    return SimpleNamespace(values=data.get('values', {}), next=data.get('next', ()), tasks=tasks,
        interrupts=interrupts(data.get('interrupts', [])), created_at=data.get('created_at'))


def payload(owner_id, sid, task, state, grant, status):
    view = weknora_traces.locator(sid, NAMESPACE, task['task_id'])
    pending = cards(snapshot(state), view) if status == 'waiting' else []
    prompts = []
    for card in pending:
        _, data = card_event(card)
        prompts.append({**data, 'interrupt_id': card['_interrupt'], 'action_index': card['_index'],
            'action_count': sum(item['_interrupt'] == card['_interrupt'] for item in pending)})
    return {'view_session_id': view, 'prompts': prompts}


async def context(owner_id, parent, work_id):
    from agent import async_work
    task = (await async_work._tasks(owner_id, parent)).get(work_id)
    if task is None:
        raise StoreError('原生后台任务不存在', 404)
    try:
        row, client, grant, _ = await async_work._observe(owner_id, parent, task)
        state = await client.threads.get_state(task['thread_id'], subgraphs=True)
    except StoreError:
        raise
    except Exception as exc:
        raise StoreError('异步运行服务不可用，请稍后重试', 503) from exc
    return row, client, grant, task, state


async def read(owner_id, parent, work_id):
    row, client, grant, task, state = await context(owner_id, parent, work_id)
    view = weknora_traces.locator(parent, NAMESPACE, work_id)
    native = snapshot(state)
    rows = history(native, view, grant['knowledge_base_ids'], owner_id=owner_id)
    if rows:
        current = rows[-1]
        current['is_completed'] = row['state'] not in ('running', 'pending', 'waiting')
        current['run_state'] = 'awaiting_input' if row['state'] == 'waiting' else row['state']
        if row['state'] == 'waiting':
            current['delegated_prompts'] = [{key: value for key, value in item.items() if not key.startswith('_')}
                                             for item in cards(native, view)]
        if row['state'] == 'succeeded' and 'structured_response' in native.values:
            current['structured_response'] = native.values['structured_response']
        if row['state'] not in ('pending', 'running') and (
                native.values.get('files') or media_files(native.values.get('messages', []))):
            versions = await _artifact_versions(owner_id, view, client, task['thread_id'], state)
            for message in rows:
                if message['role'] == 'assistant':
                    message['artifacts'] = [meta for meta, _ in versions.get(message['id'], [])]
    task_status = {'pending': 'running', 'cancelled': 'interrupted', 'lost': 'interrupted'}.get(row['state'], row['state'])
    return weknora_traces.task_view(view, task['agent_name'], task_status, rows), rows


async def artifacts(owner_id, view):
    """Reuse native artifact versioning over the service's official checkpoint reads."""
    parent, namespace, work_id = weknora_traces.decode(view)
    if namespace != NAMESPACE:
        raise StoreError('产物视图不存在', 404)
    _, client, _, task, state = await context(owner_id, parent, work_id)
    return await _artifact_versions(owner_id, view, client, task['thread_id'], state)


async def _artifact_versions(owner_id, view, client, thread_id, head):
    from langchain_core.messages import convert_to_messages
    from agent.time_travel import ancestry
    from webapi.weknora_artifacts import collect

    def view_state(state):
        value = snapshot(state)
        value.values = {**value.values, 'messages': convert_to_messages(value.values.get('messages', []))}
        identifier = (state.get('checkpoint') or {}).get('checkpoint_id')
        previous = (state.get('parent_checkpoint') or {}).get('checkpoint_id')
        value.config = {'configurable': {'thread_id': view, **({'checkpoint_id': identifier} if identifier else {})}}
        value.parent_config = {'configurable': {'thread_id': view, 'checkpoint_id': previous}} if previous else None
        return value
    async def read_state(config):
        return view_state(await client.threads.get_state(thread_id, checkpoint_id=config['configurable']['checkpoint_id']))

    snapshots = [state async for state in ancestry(SimpleNamespace(aget_state=read_state), view_state(head))]
    return collect(snapshots, owner_id, view)
