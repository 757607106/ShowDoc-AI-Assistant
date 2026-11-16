"""Read-only WeKnora views of native tool subgraphs, never child executions."""
import asyncio
import os
import time
from types import SimpleNamespace

import anyio
from itsdangerous import BadSignature, URLSafeSerializer

from agent.checkpointer import make_checkpointer
from governance.store import StoreError
from webapi.weknora_adapter import StreamProjection, assistant_id, history, message_dict

PREFIX = 'subgraph~'
# These handles last only as long as their owning HTTP request. No event log or runner.
active = {}


def _signer():
    key = os.environ.get('FLASK_SECRET_KEY')
    if not key:
        raise StoreError('FLASK_SECRET_KEY 未配置', 503)
    return URLSafeSerializer(key, salt='native-subgraph-view')


def locator(parent, namespace, call_id):
    return PREFIX + _signer().dumps([parent, namespace, call_id])


def decode(value):
    try:
        result = _signer().loads(value.removeprefix(PREFIX))
    except (BadSignature, TypeError, ValueError):
        raise StoreError('子图视图不存在', 404) from None
    if not isinstance(result, list) or len(result) != 3 or not all(isinstance(v, str) and v for v in result):
        raise StoreError('子图视图不存在', 404)
    return tuple(result)


def _messages(checkpoint):
    values = checkpoint.checkpoint['channel_values']
    messages = values.get('messages')
    if not isinstance(messages, list):
        # DeltaChannel saver tuples are sparse. Only LangGraph may hydrate them.
        raise StoreError('此动态子图未提供完整消息快照；不支持重建 DeltaChannel 历史', 501)
    return [message_dict(message) for message in messages]


def _origin(messages, call_id, name):
    for index in range(len(messages) - 1, -1, -1):
        for call in messages[index].get('tool_calls', []):
            if call.get('id') == call_id and call.get('name') == 'task' and call.get('args', {}).get('subagent_type') == name:
                human = next((m for m in reversed(messages[:index]) if m.get('type') == 'human'), None)
                if human and human.get('id') and messages[index].get('id'):
                    return messages[index]['id'], assistant_id(human)
    raise StoreError('子图缺少可验证的原生 task 调用', 501)


def _result(messages, origin_id, call_id):
    start = next((i for i, m in enumerate(messages) if m.get('id') == origin_id), None)
    if start is None:
        return None
    for message in messages[start + 1:]:
        if message.get('type') == 'human':
            break
        if message.get('type') == 'tool' and message.get('tool_call_id') == call_id:
            return 'failed' if message.get('status') == 'error' else 'succeeded'
    return None


def _interrupts(checkpoint):
    return [item for _, channel, value in checkpoint.pending_writes or []
            if channel == '__interrupt__' for item in value]


def _error_status(error):
    # JsonPlusSerializer stores native exceptions as repr(), including cancellation.
    if isinstance(error, asyncio.CancelledError) or isinstance(error, str) and error.startswith('CancelledError('):
        return 'interrupted'
    return 'failed' if error else None


def _request_busy(parent):
    with make_checkpointer() as saver:
        row = saver.conn.execute('SELECT pg_try_advisory_xact_lock(hashtextextended(%s,0)) AS available',
                           ('harness:' + parent,)).fetchone()
    return not row['available']


def _scope(messages):
    human = next((message_dict(m) for m in reversed(messages) if message_dict(m).get('type') == 'human'), {})
    value = human.get('additional_kwargs', {}).get('harness', {}).get('knowledge_base_ids', [])
    return tuple(value) if isinstance(value, list) and all(isinstance(item, str) for item in value) else ()


def _rows(messages, view, status, knowledge_base_ids=(), *, owner_id=None):
    rows = history(SimpleNamespace(values={'messages': messages}, next=(), interrupts=()), view, knowledge_base_ids,
                   owner_id=owner_id)
    if rows:
        rows[-1]['is_completed'] = status in ('succeeded', 'failed')
        if status == 'waiting':
            rows[-1]['run_state'] = 'awaiting_input'
        elif status not in ('succeeded', 'failed', 'running'):
            rows[-1]['run_state'] = 'interrupted'
    return rows


def task_view(view, name, status, rows):
    return {'id': view, 'name': name, 'display_name': name, 'agent_id': '',
            'session_id': view, 'run_id': '', 'status': status,
            'latest_message': rows[-1]['content'] if rows else ''}


def snapshot(group_id, tasks, revision=None):
    # A wire revision orders presentation snapshots; it is not execution state.
    return {'group_id': group_id, 'revision': revision or time.time_ns() // 1000, 'tasks': tasks}


async def read_child(saver, graph, root_state, parent, namespace, call_id, *, owner_id=None):
    live = active.get(parent)
    node = live.nodes.get(namespace) if live else None
    if node and node['call_id'] == call_id:
        rows = _rows(node['messages'], node['view'], node['status'], node['scope'], owner_id=owner_id)
        return node['view'], node['group_id'], task_view(node['view'], node['name'], node['status'], rows), rows
    saved = await saver.aget_tuple({'configurable': {'thread_id': parent, 'checkpoint_ns': namespace}})
    if saved is None:
        raise StoreError('子图视图不存在', 404)
    meta = saved.metadata
    name = meta.get('lc_agent_name')
    if not name or meta.get('lc_subagent_tool_call_id') != call_id:
        raise StoreError('子图缺少原生调用元数据', 501)
    parent_ns = namespace.rpartition('|')[0]
    origin_checkpoint = meta.get('parents', {}).get(parent_ns)
    if not origin_checkpoint:
        raise StoreError('子图缺少原生父 checkpoint', 501)
    config = {'configurable': {'thread_id': parent, 'checkpoint_ns': parent_ns,
                              'checkpoint_id': origin_checkpoint}}
    if parent_ns:
        origin = await saver.aget_tuple(config)
        current = await saver.aget_tuple({'configurable': {'thread_id': parent, 'checkpoint_ns': parent_ns}})
        if origin is None or current is None:
            raise StoreError('原生父子图不存在', 404)
        origin_messages, current_messages = _messages(origin), _messages(current)
        error = next((value for task_id, channel, value in current.pending_writes or []
                      if channel == '__error__' and namespace.rpartition('|')[2] == f'tools:{task_id}'), None)
        root_checkpoint = meta.get('parents', {}).get('')
        if not root_checkpoint:
            raise StoreError('子图缺少可验证的父问题范围', 501)
        root_origin = await graph.aget_state({'configurable': {'thread_id': parent, 'checkpoint_id': root_checkpoint}})
    else:
        origin = await graph.aget_state(config)
        root_origin = origin
        origin_messages = [message_dict(m) for m in origin.values.get('messages', [])]
        current_messages = [message_dict(m) for m in root_state.values.get('messages', [])]
        error = next((task.error for task in root_state.tasks if namespace == f'{task.name}:{task.id}'), None)
    origin_id, group_id = _origin(origin_messages, call_id, name)
    if not any(message.get('id') == origin_id for message in current_messages):
        raise StoreError('子图不属于当前 checkpoint 分支', 404)
    messages = _messages(saved)
    view = locator(parent, namespace, call_id)
    status = _result(current_messages, origin_id, call_id)
    if not status:
        status = _error_status(error) or ('waiting' if _interrupts(saved) else node['status'] if node else 'interrupted')
    if status not in ('succeeded', 'failed') and node is None and await anyio.to_thread.run_sync(lambda: _request_busy(parent)):
        raise StoreError('父请求在另一 API 进程执行，当前进程无法订阅其实时子图；请使用单 worker 或会话粘连', 409)
    rows = _rows(messages, view, status, _scope(root_origin.values.get('messages', [])), owner_id=owner_id)
    return view, group_id, task_view(view, name, status, rows), rows


async def children(saver, graph, root_state, parent, parent_namespace='', *, owner_id=None):
    """Read each native namespace once, retaining no second trace history."""
    latest = {}
    async for saved in saver.alist({'configurable': {'thread_id': parent}}):
        namespace = saved.config['configurable'].get('checkpoint_ns', '')
        if namespace and namespace.rpartition('|')[0] == parent_namespace and namespace not in latest:
            latest[namespace] = saved
    groups = {}
    for namespace, saved in latest.items():
        call_id = saved.metadata.get('lc_subagent_tool_call_id')
        if not call_id:
            continue
        try:
            _, group_id, task, _ = await read_child(saver, graph, root_state, parent, namespace, call_id, owner_id=owner_id)
        except StoreError as exc:
            if exc.status == 404:
                continue
            raise
        groups.setdefault(group_id, []).append(task)
    return groups


class LiveTraces:
    """Bounded SSE fan-out of the one parent request's native stream."""
    def __init__(self, parent, projection):
        self.parent, self.projection = parent, projection
        self.nodes = {}
        self.subscribers = {}
        self.closed = False
        self.scope = ()
        self.revision = time.time_ns() // 1000

    def subscribe(self, namespace):
        queue = asyncio.Queue(maxsize=128)
        self.subscribers.setdefault(namespace, set()).add(queue)
        if self.closed:
            queue.put_nowait(None)
        return queue

    def unsubscribe(self, namespace, queue):
        self.subscribers.get(namespace, set()).discard(queue)

    def publish(self, namespace, event):
        for queue in tuple(self.subscribers.get(namespace, ())):
            if queue.full():
                self.unsubscribe(namespace, queue)
                while not queue.empty():
                    queue.get_nowait()
                queue.put_nowait(self.nodes[namespace]['projection'].event('error',
                    '子图流订阅过慢，请重新加载原生历史', {'status': 409}, done=True))
                queue.put_nowait(None)
            else:
                queue.put_nowait(event)

    def collaboration(self, namespace=''):
        self.revision = max(self.revision + 1, time.time_ns() // 1000)
        items = [task_view(node['view'], node['name'], node['status'], [])
                 for ns, node in self.nodes.items() if ns.rpartition('|')[0] == namespace]
        source = self.nodes[namespace]['projection'] if namespace else self.projection
        return snapshot(source.identifier, items, self.revision)

    def feed(self, part):
        ns = '|'.join(part['ns'])
        data = part['data']
        changed = False
        if not ns and part['type'] == 'values':
            self.scope = _scope(data.get('messages', []))
        if ns and part['type'] == 'tasks' and 'input' in data:
            meta = data.get('metadata', {})
            call_id, name = meta.get('lc_subagent_tool_call_id'), meta.get('lc_agent_name')
            if call_id and name and ns not in self.nodes:
                parent_ns = ns.rpartition('|')[0]
                source = self.nodes.get(parent_ns, {}).get('projection') if parent_ns else self.projection
                call = source.calls.get(call_id) if source else None
                if call and call['name'] == 'task' and call.get('args', {}).get('subagent_type') == name:
                    messages = [message_dict(m) for m in data['input'].get('messages', [])]
                    human = next((m for m in messages if m.get('type') == 'human' and m.get('id')), None)
                    if human:
                        view = locator(self.parent, ns, call_id)
                        projection = StreamProjection(view, assistant_id(human), self.scope, owner_id=self.projection.owner_id)
                        projection.calls = {call['id']: call for message in messages
                                            for call in message.get('tool_calls', [])}
                        self.nodes[ns] = {'view': view, 'name': name, 'call_id': call_id,
                            'group_id': source.identifier, 'status': 'running', 'scope': self.scope,
                            'messages': messages, 'projection': projection}
                        changed = True
        if ns in self.nodes:
            node = self.nodes[ns]
            if part['type'] == 'values':
                node['messages'] = [message_dict(m) for m in data.get('messages', [])]
            if part.get('interrupts') or (part['type'] == 'updates' and data.get('__interrupt__')):
                node['status'] = 'waiting'
                changed = True
            for event in node['projection'].feed({**part, 'ns': []}):
                self.publish(ns, event)
        if part['type'] == 'tasks' and 'result' in data:
            child_ns = '|'.join([*part['ns'], f"{data['name']}:{data['id']}"])
            node = self.nodes.get(child_ns)
            if node:
                status = 'waiting' if data.get('interrupts') else _error_status(data.get('error')) or 'succeeded'
                if not data.get('error') and any(message_dict(m).get('status') == 'error'
                        for m in data.get('result', {}).get('messages', [])):
                    status = 'failed'
                node['status'] = status
                if data.get('error'):
                    self.publish(child_ns, node['projection'].event('error', str(data['error']), done=True))
                self.publish(child_ns, node['projection'].event('stop', data={'reason': status}, done=True))
                self.publish(child_ns, None)
                changed = True
        if changed:
            for parent_ns, parent_node in self.nodes.items():
                if any(ns.rpartition('|')[0] == parent_ns for ns in self.nodes):
                    self.publish(parent_ns, parent_node['projection'].event('collaboration_status',
                        data=self.collaboration(parent_ns)))
            return [self.projection.event('collaboration_status', data=self.collaboration())]
        return []

    def close(self):
        self.closed = True
        for ns, node in self.nodes.items():
            if node['status'] == 'running':
                node['status'] = 'interrupted'
            self.publish(ns, node['projection'].event('stop',
                data={'reason': node['status']}, done=True))
            self.publish(ns, None)
