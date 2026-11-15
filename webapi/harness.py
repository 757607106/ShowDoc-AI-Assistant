"""HTTP/auth bindings for the official Deep Agents Harness; no background runner."""
import asyncio
import json
import uuid
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone

import anyio
import psycopg
from langchain_core.messages import BaseMessage
from langgraph.types import Command
from psycopg.types.json import Jsonb
from sse_starlette.sse import EventSourceResponse, ServerSentEvent
from starlette.responses import JSONResponse
from starlette.routing import Route

from agent import sessions
from agent.checkpointer import async_checkpointer
from agent.config import apply_image_model, resolve_request
from agent.graph import build_agent
from agent.harness_config import prepare_harness_files
from governance.database import connection
from governance.store import StoreError
from integrations.contextdb import ContextDBError
from webapi.auth import client_for_user, validate_access_token

# Cancellation handles belong to open HTTP requests, never to background runs.
_active_requests = {}


def _json_default(value):
    if isinstance(value, BaseMessage):
        return value.model_dump(mode='json')
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f'Unsupported stream value: {type(value).__name__}')


def _event(kind, value):
    return {'event': kind, 'data': json.dumps(value, ensure_ascii=False, default=_json_default)}


def _identity(request):
    token = request.headers.get('authorization', '').removeprefix('Bearer ').strip()
    user, _ = validate_access_token(token)
    selected = sessions.get_session(request.path_params['session_id'], user['id'])
    if selected['agent_config'].get('runtime') != 'deepagents':
        raise StoreError('旧会话只读，请新建官方 Deep Agents 会话', 409)
    return user, selected


def _state_values(state):
    # Interrupt IDs and messages are supplied by LangGraph, never reconstructed.
    values = {key: value for key, value in state.values.items() if key != '__interrupt__'}
    if state.interrupts:
        values['__interrupt__'] = list(state.interrupts)
    return values


async def _graph(saver, user, selected, resolved, *, load_tools=True):
    client = await anyio.to_thread.run_sync(lambda: client_for_user(user['id'])) if load_tools else None
    return await build_agent(saver, api_key=client.api_key if client else '', owner_id=user['id'],
        role=user['role'], knowledge_base_ids=resolved.get('knowledge_base_ids', []),
        knowledge_ids=resolved.get('knowledge_ids', []), tag_scopes=resolved.get('tag_scopes', []),
        agent_config=resolved['agent_config'], session_id=selected['id'], load_tools=load_tools)


async def read_state(request):
    try:
        user, selected = await anyio.to_thread.run_sync(lambda: _identity(request))
        resolved = selected['agent_config']
        if not resolved.get('agent_config'):
            return JSONResponse({'values': {'messages': []}, 'next': []})
        async with async_checkpointer() as saver:
            graph = await _graph(saver, user, selected, resolved, load_tools=False)
            state = await graph.aget_state({'configurable': {'thread_id': selected['id']}})
        return JSONResponse(json.loads(json.dumps({'values': _state_values(state), 'next': state.next},
                                                  default=_json_default)))
    except StoreError as exc:
        return JSONResponse({'message': str(exc)}, status_code=exc.status)


def _input(body):
    command = body.get('command')
    if command is not None:
        if not isinstance(command, dict) or set(command) != {'resume'} or not isinstance(command['resume'], dict):
            raise StoreError('恢复请求必须按官方 interrupt ID 提交 resume', 400)
        if body.get('input'):
            raise StoreError('恢复审批不能同时提交新消息', 400)
        return None, command['resume']
    value = body.get('input')
    messages = value.get('messages') if isinstance(value, dict) else None
    if not isinstance(messages, list) or len(messages) != 1:
        raise StoreError('每次请求只能提交一条用户消息', 400)
    message = messages[0]
    if not isinstance(message, dict) or (message.get('role') or message.get('type')) not in ('user', 'human'):
        raise StoreError('只能提交用户消息', 400)
    content = message.get('content')
    if not isinstance(content, str) or not content.strip() or len(content) > 100_000:
        raise StoreError('消息必须是非空文本，且不超过 100000 字符', 400)
    return content, None


def _prepare(user, selected, context, message):
    from webapi.chat_resources import prepare_attachments
    if context.get('local_browser_enabled') is True or context.get('web_search_enabled') is True:
        raise StoreError('当前 Harness 尚未接入浏览器或网络搜索，请关闭该能力后发送', 501)
    client = client_for_user(user['id'])
    resolved = resolve_request({**context, 'query': message}, client=client, owner_id=user['id'],
                               role=user['role'], session=selected)
    resolved.update(prepare_attachments(selected['id'], user['id'], context))
    apply_image_model(resolved, user['id'])
    resolved['mentioned_items'] = _display_mentions(resolved, client, user['id'])
    return resolved


def _display_mentions(resolved, client, owner_id):
    """Project verified business selections, never arbitrary request properties."""
    from agent import registry
    mentions = []
    seen = set()
    for item in resolved.get('mentioned_items', []):
        kind, identifier = item.get('type'), item.get('id')
        if kind == 'skill':
            identifier = item.get('skill_name') or identifier
        if kind not in ('kb', 'file', 'mcp', 'skill') or not isinstance(identifier, str):
            continue
        if (kind, identifier) in seen:
            continue
        if kind == 'kb' and identifier in resolved['knowledge_base_ids']:
            source = client.get_knowledge_base(identifier)
        elif kind == 'file' and identifier in resolved['knowledge_ids']:
            source = client.get_document(None, identifier)
        elif kind == 'mcp' and identifier in resolved['mcp_service_ids']:
            source = registry.record('mcp', identifier, owner_id)
        elif kind == 'skill' and identifier in resolved['skill_names']:
            source = {'name': identifier}
        else:
            continue
        seen.add((kind, identifier))
        value = {'id': identifier, 'type': kind, 'name': source.get('name') or identifier}
        if kind == 'kb':
            value['kb_type'] = 'faq' if source.get('type') == 'faq' else 'document'
        mentions.append(value)
    return mentions


def _message_metadata(message, resolved):
    return {'display_text': message, 'created_at': datetime.now(timezone.utc).isoformat(),
        'knowledge_base_ids': resolved['knowledge_base_ids'],
        'mentioned_items': resolved.get('mentioned_items', []),
        'attachments': [{key: item[key] for key in ('id', 'file_name', 'file_size', 'file_type', 'mime_type', 'status')
                         if key in item} for item in resolved.get('attachments', [])],
        'user_images': [{key: item[key] for key in ('id', 'url', 'file_name') if key in item}
                        for item in resolved.get('user_images', [])]}


def _save_selection(user, selected, resolved):
    # Only business selections live here; all execution state is in checkpoints.
    saved = {key: value for key, value in resolved.items()
             if key not in ('files', 'message_blocks', 'attachment_ids', 'user_images', 'attachments')}
    saved.update(runtime='deepagents')
    if selected['agent_config'].get('_kind'):
        saved['_kind'] = selected['agent_config']['_kind']
    with connection() as conn:
        conn.execute('UPDATE agent_sessions SET agent_config=%s,knowledge_base_ids=%s,updated_at=now() '
                     'WHERE id=%s AND owner_id=%s',
                     (Jsonb(saved), Jsonb(resolved['knowledge_base_ids']), selected['id'], user['id']))


async def stream(request, *, weknora=False, resume_protocol=False, pending_id=None):
    lock = None
    pending_id = pending_id or request.query_params.get('resume_pending_id', '')
    try:
        user, selected = await anyio.to_thread.run_sync(lambda: _identity(request))
        raw = b'{}' if resume_protocol else await request.body()
        if len(raw) > 30 * 1024 * 1024:
            raise StoreError('请求超过 30 MB', 413)
        try:
            body = json.loads(raw)
        except (ValueError, UnicodeDecodeError) as exc:
            raise StoreError('请求必须是 JSON 对象', 400) from exc
        if not isinstance(body, dict):
            raise StoreError('请求必须是 JSON 对象', 400)
        if resume_protocol:
            body = {'command': {'resume': {}}}
        elif weknora:
            body = {'input': {'messages': [{'role': 'user', 'content': body.get('query')}]}, 'context': body}
        message, resume = _input(body)
        configuration = body.get('config') or {}
        if not isinstance(configuration, dict):
            raise StoreError('config 必须是对象', 400)
        context = body.get('context') or configuration.get('configurable') or {}
        if not isinstance(context, dict):
            raise StoreError('context 必须是对象', 400)
        # A database connection lock protects this HTTP request, not a task queue.
        import os
        lock = await psycopg.AsyncConnection.connect(os.environ['DATABASE_URL'], autocommit=True)
        cursor = await lock.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0))',
                                    ('harness:' + selected['id'],))
        if not (await cursor.fetchone())[0]:
            raise StoreError('会话正在执行，请等待本次请求结束', 409)
        # Session deletion uses the same lock; recheck after acquiring it.
        selected = await anyio.to_thread.run_sync(lambda: sessions.get_session(selected['id'], user['id']))
        if selected['agent_config'].get('runtime') != 'deepagents':
            raise StoreError('旧会话只读，请新建官方 Deep Agents 会话', 409)
        resolved = selected['agent_config'] if resume is not None else await anyio.to_thread.run_sync(
            lambda: _prepare(user, selected, context, message))
        if not resolved.get('agent_config'):
            raise StoreError('没有可恢复的会话', 409)
    except (StoreError, ContextDBError) as exc:
        if lock is not None:
            await lock.close()
        return JSONResponse({'message': str(exc)}, status_code=getattr(exc, 'status', 503))
    except BaseException:
        if lock is not None:
            await lock.close()
        raise

    request_task = None

    async def cancel_on_response_exit():
        try:
            await anyio.sleep_forever()
        finally:
            if request_task is not None and not request_task.done():
                request_task.cancel()

    async def events():
        nonlocal request_task, resume
        request_task = asyncio.current_task()
        try:
            async with async_checkpointer() as saver:
                graph = await _graph(saver, user, selected, resolved)
                config = {'configurable': {'thread_id': selected['id']}}
                state = await graph.aget_state(config, subgraphs=True)
                if resume_protocol:
                    from webapi.weknora_adapter import history
                    rows = history(state, selected['id'])
                    if not rows or rows[-1]['id'] != request.query_params.get('message_id'):
                        raise StoreError('消息与当前待恢复交互不匹配', 409)
                    from webapi.weknora_prompts import consume
                    resume = await anyio.to_thread.run_sync(lambda: consume(user['id'], selected['id'], state,
                        pending_id))
                    if resume is None:
                        from webapi.weknora_adapter import StreamProjection
                        target = rows[-1]
                        projection = StreamProjection(selected['id'], target['id'])
                        yield _event('message', projection.event('agent_query'))
                        yield _event('message', projection.event('answer', target['content'],
                            {'event_id': target['id'], 'replace': True}, done=True))
                        yield _event('message', projection.event('stop', data={'reason': 'resume_already_consumed'}, done=True))
                        return
                if resume is not None:
                    if not state.interrupts or set(resume) != {item.id for item in state.interrupts}:
                        raise StoreError('审批已失效，请重新加载当前会话', 409)
                    inputs = Command(resume=resume)
                else:
                    if state.interrupts:
                        raise StoreError('请先处理当前待确认操作', 409)
                    files = await anyio.to_thread.run_sync(lambda: prepare_harness_files(
                        user['id'], resolved['agent_config'], state.values.get('files', {})))
                    files.update(resolved.get('files', {}))
                    blocks = resolved.get('message_blocks', [])
                    inputs = {'messages': [{'role': 'user', 'content':
                        [{'type': 'text', 'text': message}, *blocks] if blocks else message,
                        'additional_kwargs': {'harness': _message_metadata(message, resolved)}}]}
                    if weknora:
                        inputs['messages'][0]['id'] = str(uuid.uuid4())
                    if files:
                        inputs['files'] = files
                    await anyio.to_thread.run_sync(lambda: _save_selection(user, selected, resolved))
                projection = None
                if weknora:
                    from webapi.weknora_adapter import StreamProjection, history, pending_calls
                    identifier = history(state, selected['id'])[-1]['id'] if resume_protocol else 'assistant:' + inputs['messages'][0]['id']
                    projection = StreamProjection(selected['id'], identifier,
                                                  resolved.get('knowledge_base_ids', []))
                    replay_calls = pending_calls(state) if resume_protocol else []
                    for call in replay_calls:
                        projection.calls[call['id']] = call
                    _active_requests[selected['id']] = (asyncio.get_running_loop(), request_task, projection.identifier)
                    yield _event('message', projection.event('agent_query', data={'query': message,
                        'resume_pending_id': pending_id}))
                    if resume_protocol:
                        yield _event('message', projection.event('run_resumed'))
                        for call in replay_calls:
                            yield _event('message', projection.event('tool_call', data={
                                'tool_call_id': call['id'], 'tool_name': call['name'], 'arguments': call['args']}))
                output = graph.astream(inputs, config, stream_mode=['messages', 'updates', 'values'],
                                       subgraphs=True, version='v2', durability='sync')
                try:
                    while True:
                        try:
                            # Shield only the await: yielding inside a cancel scope corrupts SSE cancellation.
                            with anyio.CancelScope(shield=True):
                                part = await anext(output)
                        except StopAsyncIteration:
                            break
                        if projection:
                            for event in projection.feed(part):
                                yield _event('message', event)
                        else:
                            kind = part['type']
                            namespace = part['ns']
                            yield _event(kind + ('|' + '|'.join(namespace) if namespace else ''), part['data'])
                finally:
                    # Closing the official iterator also cancels its in-flight tools.
                    with anyio.CancelScope(shield=True):
                        await output.aclose()
                state = await graph.aget_state(config, subgraphs=True)
                if projection:
                    from webapi.weknora_artifacts import collect
                    artifacts = await collect(graph, config, user['id'], selected['id'])
                    artifact_meta = [metadata for metadata, _ in artifacts.get(projection.identifier, [])]
                    if state.interrupts:
                        from webapi.weknora_prompts import cards, card_event, bind_card_ids
                        pending = cards(state, selected['id'])
                        await anyio.to_thread.run_sync(lambda: bind_card_ids(user['id'], selected['id'], state,
                                                                          pending, projection.child_calls))
                        for card in pending:
                            kind, data = card_event(card)
                            yield _event('message', projection.event(kind, data=data))
                            yield _event('message', projection.event('run_suspended', data={'pending_id': card['id']}))
                        yield _event('message', projection.event('complete', data={'artifacts': artifact_meta}, done=True))
                        return
                    yield _event('message', projection.event('stop' if state.next else 'complete',
                        data={'artifacts': artifact_meta}, done=True))
                else:
                    values = _state_values(state)
                    pending = values.pop('__interrupt__', None)
                    yield _event('values', values)
                    if pending:
                        yield _event('values', {'__interrupt__': pending})
        except Exception as exc:
            if weknora:
                from webapi.weknora_adapter import StreamProjection
                failed = projection if 'projection' in locals() and projection else StreamProjection(selected['id'], '')
                yield _event('message', failed.event('error', str(exc), {'status': getattr(exc, 'status', 500)}, done=True))
            else:
                yield _event('error', {'message': str(exc), 'status': getattr(exc, 'status', 500)})
        finally:
            active = _active_requests.get(selected['id'])
            if active and active[1] is request_task:
                _active_requests.pop(selected['id'], None)

    response = EventSourceResponse(events(), data_sender_callable=cancel_on_response_exit,
                                   ping_message_factory=(lambda: ServerSentEvent(event='message',
                                       data=json.dumps({'response_type': 'heartbeat'}))) if weknora else None,
                                   headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})

    async def send_stream(scope, receive, send):
        try:
            await response(scope, receive, send)
        finally:
            # Also covers a failed header send, before the iterator starts.
            with anyio.CancelScope(shield=True):
                await lock.close()

    return send_stream


async def weknora_stream(request):
    return await stream(request, weknora=True)


async def read_snapshot(user, selected):
    resolved = selected['agent_config']
    if not resolved.get('agent_config'):
        return None
    async with async_checkpointer() as saver:
        graph = await _graph(saver, user, selected, resolved, load_tools=False)
        return await graph.aget_state({'configurable': {'thread_id': selected['id']}}, subgraphs=True)


async def read_weknora_history(user, selected):
    from webapi.weknora_adapter import history
    from webapi.weknora_prompts import cards, _receipt
    state = await read_snapshot(user, selected)
    if state is None:
        return []
    rows = history(state, selected['id'], selected['agent_config'].get('knowledge_base_ids', []))
    from webapi.weknora_artifacts import read
    artifacts = await read(user, selected)
    for row in rows:
        if row['role'] == 'assistant':
            row['artifacts'] = [metadata for metadata, _ in artifacts.get(row['id'], [])]
    if rows and state.interrupts:
        pending = cards(state, selected['id'])
        receipt = await anyio.to_thread.run_sync(lambda: _receipt(user['id'], selected['id'], state))
        for card in pending:
            card['tool_call_id'] = card['tool_call_id'] or receipt.get('tool_ids', {}).get(card['id'])
            response = receipt['responses'].get(card['id'])
            if response is not None:
                card.update(status='answered', response=({**response, 'approved': response['type'] != 'reject',
                            **({'modified_args': response['edited_action']['args']} if response['type'] == 'edit' else {})}
                            if card['kind'] == 'tool_approval' else response))
        rows[-1]['delegated_prompts'] = [{key: value for key, value in card.items() if not key.startswith('_')}
                                       for card in pending]
    return rows


async def continue_weknora(request):
    """Read saved state only; reconnecting must never replay an accepted tool."""
    if request.query_params.get('resume_pending_id'):
        return await stream(request, weknora=True, resume_protocol=True)
    try:
        user, selected = await anyio.to_thread.run_sync(lambda: _identity(request))
        state = await read_snapshot(user, selected)
        if state is not None and state.interrupts:
            from webapi.weknora_prompts import cards, _receipt
            pending = cards(state, selected['id'])
            receipt = await anyio.to_thread.run_sync(lambda: _receipt(user['id'], selected['id'], state))
            if pending and all(item['id'] in receipt['responses'] for item in pending):
                return await stream(request, weknora=True, resume_protocol=True, pending_id=pending[-1]['id'])
        rows = await read_weknora_history(user, selected)
        target = next((row for row in rows if row['id'] == request.query_params.get('message_id')
                       and row['role'] == 'assistant'), None)
        if target is None:
            raise StoreError('消息不存在', 404)
        from webapi.weknora_adapter import StreamProjection
        projection = StreamProjection(selected['id'], target['id'])
        async def events():
            yield _event('message', projection.event('agent_query'))
            yield _event('message', projection.event('answer', target['content'],
                {'event_id': target['id'], 'replace': True}, done=True))
            yield _event('message', projection.event('stop', data={'reason': 'stream_interrupted'}, done=True))
        return EventSourceResponse(events(), headers={'Cache-Control': 'no-store'})
    except StoreError as exc:
        return JSONResponse({'message': str(exc)}, status_code=exc.status)


routes = [
    Route('/api/v1/agent-chat/{session_id}', weknora_stream, methods=['POST']),
    Route('/api/v1/knowledge-chat/{session_id}', weknora_stream, methods=['POST']),
    Route('/api/v1/sessions/continue-stream/{session_id}', continue_weknora, methods=['GET']),
    Route('/api/v1/harness/sessions/{session_id}/state', read_state, methods=['GET']),
    Route('/api/v1/harness/sessions/{session_id}/stream', stream, methods=['POST']),
]
