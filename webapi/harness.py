"""HTTP/auth bindings for the official Deep Agents Harness on Agent Protocol runs."""
import asyncio
import json
import logging
import uuid
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone

import anyio
import httpx
import psycopg
from langchain_core.messages import BaseMessage
from langgraph.types import Command, Interrupt
from psycopg.types.json import Jsonb
from sse_starlette.sse import EventSourceResponse, ServerSentEvent
from starlette.responses import JSONResponse
from starlette.routing import Route
from pydantic import BaseModel

from agent import async_runtime, sessions
from agent.checkpointer import async_checkpointer, database_url
from agent.config import apply_image_model, resolve_request
from agent.graph import build_agent
from agent.harness_config import prepare_harness_files
from agent.time_travel import ancestry
from governance.database import connection
from governance.store import StoreError
from integrations.contextdb import ContextDBError
from webapi.auth import client_for_user, validate_access_token
from webapi.weknora import traces as weknora_traces

_followers = set()



def _json_default(value):
    if isinstance(value, Interrupt):
        from webapi.weknora.prompts import response_schema
        return {'id': value.id, 'value': value.value, 'response_schema': response_schema(value)}
    if isinstance(value, BaseMessage):
        return value.model_dump(mode='json')
    if isinstance(value, BaseModel):
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


async def _graph(saver, user, selected, resolved, *, load_tools=True, store=None, backend=None):
    client = await anyio.to_thread.run_sync(lambda: client_for_user(user['id'])) if load_tools else None
    return await build_agent(saver, api_key=client.api_key if client else '', owner_id=user['id'],
        role=user['role'], knowledge_base_ids=resolved.get('knowledge_base_ids', []),
        knowledge_ids=resolved.get('knowledge_ids', []), tag_scopes=resolved.get('tag_scopes', []),
        agent_config=resolved['agent_config'], session_id=selected['id'], load_tools=load_tools,
        store=store, agent_id=resolved.get('agent_id'), backend=backend)


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
    from webapi.chat.chat_resources import prepare_attachments
    client = client_for_user(user['id'])
    resolved = resolve_request({**context, 'query': message}, client=client, owner_id=user['id'],
                               role=user['role'], session=selected)
    if resolved['agent_config']['_local_browser_enabled'] or resolved['agent_config']['web_search_enabled']:
        raise StoreError('当前 Harness 尚未接入浏览器或网络搜索，请关闭该能力后发送', 501)
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
    return {**({'structured_output': True} if resolved['agent_config'].get('response_format') is not None else {}),
        'display_text': message, 'created_at': datetime.now(timezone.utc).isoformat(),
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
        if weknora and request.url.path.startswith('/api/v1/knowledge-chat/') and not isinstance(
                context.get('disable_title', False), bool):
            raise StoreError('disable_title 必须为布尔值', 400)
        # A database connection lock protects this HTTP request, not a task queue.
        lock = await psycopg.AsyncConnection.connect(database_url(), autocommit=True)
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
    heartbeats_finished = False

    def terminal_frame(frame):
        nonlocal heartbeats_finished
        heartbeats_finished = True
        return frame

    async def cancel_on_response_exit():
        try:
            await anyio.sleep_forever()
        finally:
            if request_task is not None and not request_task.done():
                request_task.cancel()

    async def events():
        nonlocal request_task, resume
        request_task = asyncio.current_task()
        traces = None
        try:
            async with async_checkpointer() as saver:
                graph = await _graph(saver, user, selected, resolved, load_tools=False)
                config = {'configurable': {'thread_id': selected['id']}}
                state = await graph.aget_state(config, subgraphs=True)
                resume_context = None
                if resume_protocol:
                    from webapi.weknora.adapter import history
                    rows = history(state, selected['id'], owner_id=user['id'])
                    if not rows or rows[-1]['id'] != request.query_params.get('message_id'):
                        raise StoreError('消息与当前待恢复交互不匹配', 409)
                    from webapi.weknora.prompts import consume
                    resume = await anyio.to_thread.run_sync(lambda: consume(user['id'], selected['id'], state,
                        pending_id))
                    if resume is None:
                        from webapi.weknora.adapter import StreamProjection
                        target = rows[-1]
                        projection = StreamProjection(selected['id'], target['id'], owner_id=user['id'])
                        yield _event('message', projection.event('agent_query'))
                        yield _event('message', projection.event('answer', target['content'],
                            {'event_id': target['id'], 'replace': True}, done=True))
                        yield terminal_frame(_event('message', projection.event('stop', data={'reason': 'resume_already_consumed'}, done=True)))
                        return
                if resume is not None:
                    if not state.interrupts or set(resume) != {item.id for item in state.interrupts}:
                        raise StoreError('审批已失效，请重新加载当前会话', 409)
                    from webapi.weknora.prompts import validate_native_resume
                    validate_native_resume(state, resume)
                    pending_oauth = {item.id for item in state.interrupts
                                     if isinstance(item.value, dict) and item.value.get('kind') == 'mcp_oauth'}
                    if pending_oauth:
                        resume_context = {'pending_oauth': pending_oauth}
                    inputs = Command(resume=resume)
                    if resume_protocol:
                        from webapi.weknora.prompts import cards, _receipt
                        receipt = await anyio.to_thread.run_sync(lambda: _receipt(user['id'], selected['id'], state))
                        human = next(message for message in reversed(state.values.get('messages', []))
                                     if getattr(message, 'type', None) == 'human')
                        metadata = human.additional_kwargs.get('harness', {})
                        interactions = {card['id']: card for card in metadata.get('interactions', [])}
                        for card in cards(state, selected['id']):
                            card['tool_call_id'] = card['tool_call_id'] or receipt.get('tool_ids', {}).get(card['id'])
                            response = resume[card['_interrupt']]
                            if card['kind'] == 'tool_approval':
                                response = response['decisions'][card['_index']]
                                response = {**response, 'approved': response['type'] != 'reject',
                                    **({'modified_args': response['edited_action']['args']} if response['type'] == 'edit' else {})}
                            interactions[card['id']] = {**{key: value for key, value in card.items() if not key.startswith('_')},
                                                        'status': 'answered', 'response': response}
                        updated = human.model_copy(update={'additional_kwargs': {**human.additional_kwargs,
                            'harness': {**metadata, 'interactions': list(interactions.values())}}})
                        inputs = Command(resume=resume, update={'messages': [updated]})
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
                    if resolved['agent_config'].get('response_format') is not None:
                        inputs['structured_response'] = None
                projection = None
                if weknora:
                    from webapi.weknora.adapter import StreamProjection, history, pending_calls, tool_display_name
                    identifier = history(state, selected['id'], owner_id=user['id'])[-1]['id'] if resume_protocol else 'assistant:' + inputs['messages'][0]['id']
                    projection = StreamProjection(selected['id'], identifier,
                                                  resolved.get('knowledge_base_ids', []), owner_id=user['id'])
                    traces = weknora_traces.LiveTraces(selected['id'], projection)
                    weknora_traces.active[selected['id']] = traces
                    replay_calls = pending_calls(state) if resume_protocol else []
                    for call in replay_calls:
                        projection.calls[call['id']] = call
                    yield _event('message', projection.event('agent_query', data={'query': message,
                        'resume_pending_id': pending_id}))
                    if resume_protocol:
                        yield _event('message', projection.event('run_resumed'))
                        for call in replay_calls:
                            yield _event('message', projection.event('tool_call', data={
                                'tool_call_id': call['id'], 'tool_name': tool_display_name(call['name']), 'arguments': call['args']}))
                modes = ['messages', 'updates', 'values'] + (['tasks'] if projection else [])
                if not async_runtime.enabled():
                    raise StoreError('官方 Agent 运行服务尚未部署', 503)
                grant = await anyio.to_thread.run_sync(lambda: async_runtime.create_main_grant(user['id'], selected, resolved))
                client = async_runtime.client(grant)
                await client.threads.create(thread_id=selected['id'], metadata={'main_session_id': selected['id']},
                                            if_exists='do_nothing')
                command = None
                if resume is not None:
                    command = {'resume': resume}
                    update = getattr(inputs, 'update', None)
                    if update:
                        command['update'] = {'messages': [item.model_dump(mode='json') for item in update['messages']]}
                try:
                    run = await client.runs.create(selected['id'], async_runtime.MAIN_GRAPH_ID,
                        input=None if resume is not None else inputs, command=command, context=resume_context,
                        stream_mode=modes, stream_subgraphs=True, multitask_strategy='reject', durability='sync',
                        metadata={'main_session_id': selected['id'],
                                  'assistant_id': projection.identifier if projection else ''})
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 409:
                        raise StoreError('会话正在执行，请等待当前生成完成或先停止', 409) from exc
                    raise
                if resume is None:
                    await anyio.to_thread.run_sync(lambda: _save_selection(user, selected, resolved))

                live_traces = traces

                async def follow():
                    structured_written = False
                    async for part in client.runs.join_stream(selected['id'], run['run_id'], cancel_on_disconnect=False):
                        if part.event == 'end':
                            break
                        if part.event == 'error':
                            raise StoreError(str(part.data), 500)
                        kind, _, namespace = part.event.partition('|')
                        mapped = {'type': kind, 'data': part.data, 'ns': namespace.split('|') if namespace else []}
                        if kind == 'updates' and not mapped['ns']:
                            structured_written |= any(isinstance(update, dict) and 'structured_response' in update
                                                      for update in part.data.values())
                        if projection:
                            for event in projection.feed(mapped):
                                yield _event('message', event)
                            for event in live_traces.feed(mapped):
                                yield _event('message', event)
                        else:
                            yield _event(part.event, part.data)
                    final_run = await client.runs.get(selected['id'], run['run_id'])
                    if final_run.get('status') == 'cancelled':
                        return
                    if final_run.get('status') in ('error', 'timeout'):
                        raise StoreError(str(final_run.get('error') or '后台执行失败'),
                                         final_run.get('status_code') or 500)
                    # Own checkpointer: the request's resources may already be closed after a disconnect.
                    async with async_checkpointer() as follow_saver:
                        follow_graph = await _graph(follow_saver, user, selected, resolved, load_tools=False)
                        state = await follow_graph.aget_state(config, subgraphs=True)
                        if projection:
                            async for frame in _completion(follow_graph, state, user=user, selected=selected,
                                                           resolved=resolved, projection=projection, traces=live_traces,
                                                           structured_written=structured_written, request=request,
                                                           context=context, terminal_frame=terminal_frame):
                                yield frame
                        else:
                            values = _state_values(state)
                            pending = values.pop('__interrupt__', None)
                            yield _event('values', values)
                            if pending:
                                yield _event('values', {'__interrupt__': pending})

                queue, done = asyncio.Queue(), object()
                attached = True

                async def pump():
                    try:
                        async for frame in follow():
                            queue.put_nowait(frame)
                    except Exception as exc:
                        if not attached:
                            logging.getLogger(__name__).warning('Detached run completion failed: session=%s type=%s',
                                                                selected['id'], type(exc).__name__)
                        queue.put_nowait(exc)
                    finally:
                        if live_traces:
                            live_traces.close()
                            if weknora_traces.active.get(selected['id']) is live_traces:
                                weknora_traces.active.pop(selected['id'], None)
                        queue.put_nowait(done)

                # The accepted run outlives the HTTP response; its post-run bookkeeping must too.
                follower = asyncio.create_task(pump())
                _followers.add(follower)
                follower.add_done_callback(_followers.discard)
                traces = None
                try:
                    while (item := await queue.get()) is not done:
                        if isinstance(item, Exception):
                            raise item
                        yield item
                finally:
                    attached = False
        except Exception as exc:
            if weknora:
                from webapi.weknora.adapter import StreamProjection
                failed = projection if 'projection' in locals() and projection else StreamProjection(selected['id'], '', owner_id=user['id'])
                yield terminal_frame(_event('message', failed.event('error', str(exc), {'status': getattr(exc, 'status', 500)}, done=True)))
            else:
                yield _event('error', {'message': str(exc), 'status': getattr(exc, 'status', 500)})
        finally:
            if traces:
                traces.close()
                if weknora_traces.active.get(selected['id']) is traces:
                    weknora_traces.active.pop(selected['id'], None)

    heartbeat = ServerSentEvent(event='message', data=json.dumps({'response_type': 'heartbeat'})) if weknora else None
    heartbeat_bytes = heartbeat.encode() if heartbeat else None
    response = EventSourceResponse(events(), data_sender_callable=cancel_on_response_exit,
                                   ping_message_factory=(lambda: heartbeat) if weknora else None,
                                   headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})

    async def send_stream(scope, receive, send):
        send_lock = anyio.Lock()

        async def send_ordered(message):
            async with send_lock:
                # Official pings remain active while the iterator closes its resources.
                if heartbeats_finished and message.get('body') == heartbeat_bytes:
                    return
                await send(message)

        try:
            await response(scope, receive, send_ordered if weknora else send)
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
    from webapi.weknora.adapter import history, structured_outputs
    from webapi.weknora.artifacts import collect
    from webapi.weknora.prompts import cards, _receipt
    owner, sid = user['id'], selected['id']
    resolved = selected['agent_config']
    if not resolved.get('agent_config'):
        return []
    async with async_checkpointer() as saver:
        graph = await _graph(saver, user, selected, resolved, load_tools=False)
        state = await graph.aget_state({'configurable': {'thread_id': sid}}, subgraphs=True)
        rows = history(state, sid, resolved.get('knowledge_base_ids', []), owner_id=owner)
        snapshots = [snapshot async for snapshot in ancestry(graph, state)]
        messages = state.values.get('messages', [])
        outputs = await structured_outputs(snapshots, saver) if any(
            getattr(message, 'additional_kwargs', {}).get('harness', {}).get('structured_output')
            for message in messages) else {}
        groups = await weknora_traces.children(saver, graph, state, sid, messages, owner_id=owner)
        artifacts = collect(snapshots, owner, sid)
        for row in rows:
            identifier = row['id']
            if identifier in outputs:
                row['structured_response'] = outputs[identifier]
            if identifier in groups:
                row['collaboration_status'] = weknora_traces.snapshot(identifier, groups[identifier])
            if row['role'] == 'assistant':
                row['artifacts'] = [metadata for metadata, _ in artifacts.get(identifier, [])]
    if rows and state.interrupts:
        pending = cards(state, selected['id'])
        receipt = await anyio.to_thread.run_sync(lambda: _receipt(user['id'], selected['id'], state))
        for card in pending:
            if card['kind'] != 'ask_user':
                card['tool_call_id'] = card['tool_call_id'] or receipt.get('tool_ids', {}).get(card['id'])
            response = receipt['responses'].get(card['id'])
            if card['id'] in receipt['responses']:
                card.update(status='answered', response=({**response, 'approved': response['type'] != 'reject',
                            **({'modified_args': response['edited_action']['args']} if response['type'] == 'edit' else {})}
                            if card['kind'] == 'tool_approval' else response))
        interactions = {card['id']: card for card in rows[-1].get('delegated_prompts', [])}
        interactions.update({card['id']: {key: value for key, value in card.items() if not key.startswith('_')}
                             for card in pending})
        rows[-1]['delegated_prompts'] = list(interactions.values())
    return rows


async def _completion(graph, state, *, user, selected, resolved, projection, traces, structured_written,
                      request, context, terminal_frame=lambda frame: frame):
    """Shared post-run projection after the official run reaches a terminal state."""
    from agent.async_work import reconcile_parent
    state = await reconcile_parent(graph, state, user['id'], selected['id'])
    if traces.nodes:
        yield _event('message', projection.event('collaboration_status', data=traces.collaboration()))
    from webapi.weknora.artifacts import collect
    artifacts = collect([snapshot async for snapshot in ancestry(graph, state)], user['id'], selected['id'])
    artifact_meta = [metadata for metadata, _ in artifacts.get(projection.identifier, [])]
    if not selected['title'] and not (request.url.path.startswith('/api/v1/knowledge-chat/')
                                      and context.get('disable_title') is True):
        from agent.session_titles import first_query, generate_title
        try:
            title = await generate_title(selected['id'], user['id'],
                query=first_query(state.values.get('messages', [])),
                model_id=resolved['agent_config'].get('model_id'),
                language=request.headers.get('Accept-Language', 'zh-CN'))
        except Exception as exc:
            logging.getLogger(__name__).warning('Session title generation failed: session=%s type=%s',
                                                selected['id'], type(exc).__name__)
        else:
            if title:
                yield _event('message', projection.event('session_title', title,
                    {'session_id': selected['id'], 'title': title}, done=True))
    if state.interrupts:
        from webapi.weknora.prompts import cards, card_event, bind_card_ids
        pending = cards(state, selected['id'])
        await anyio.to_thread.run_sync(lambda: bind_card_ids(user['id'], selected['id'], state,
                                                          pending, projection.child_calls))
        for card in pending:
            kind, data = card_event(card)
            yield _event('message', projection.event(kind, data=data))
            yield _event('message', projection.event('run_suspended', data={'pending_id': card['id']}))
        yield terminal_frame(_event('message', projection.event('complete', data={'artifacts': artifact_meta}, done=True)))
        return
    complete = {'artifacts': artifact_meta}
    if not state.next and structured_written and 'structured_response' in state.values:
        complete['structured_response'] = state.values['structured_response']
    yield terminal_frame(_event('message', projection.event('stop' if state.next else 'complete',
        data=complete, done=True)))


async def continue_weknora(request):
    """Read saved state only; reconnecting must never replay an accepted tool."""
    if request.path_params['session_id'].startswith(weknora_traces.PREFIX):
        return await continue_child(request)
    if request.query_params.get('resume_pending_id'):
        return await stream(request, weknora=True, resume_protocol=True)
    try:
        user, selected = await anyio.to_thread.run_sync(lambda: _identity(request))
        state = await read_snapshot(user, selected)
        if state is not None and state.interrupts:
            from webapi.weknora.prompts import cards, _receipt
            pending = cards(state, selected['id'])
            receipt = await anyio.to_thread.run_sync(lambda: _receipt(user['id'], selected['id'], state))
            if pending and all(item['id'] in receipt['responses'] for item in pending):
                return await stream(request, weknora=True, resume_protocol=True, pending_id=pending[-1]['id'])
        from webapi.weknora.adapter import StreamProjection, history
        rows = history(state, selected['id'], selected['agent_config'].get('knowledge_base_ids', []),
                       owner_id=user['id']) if state is not None else []
        target = next((row for row in rows if row['id'] == request.query_params.get('message_id')
                       and row['role'] == 'assistant'), None)
        if target is None:
            raise StoreError('消息不存在', 404)
        run = None
        try:
            client, _ = await anyio.to_thread.run_sync(lambda: async_runtime.main_client(user['id'], selected['id']))
            for run_status in ('pending', 'running'):
                if batch := await client.runs.list(selected['id'], status=run_status, limit=1):
                    run = batch[0]
                    break
        except StoreError as exc:
            if exc.status != 404:
                raise
        identifier = (run.get('metadata') or {}).get('assistant_id') or target['id'] if run else target['id']
        projection = StreamProjection(selected['id'], identifier, owner_id=user['id'])
        traces = None
        async def events():
            nonlocal traces
            yield _event('message', projection.event('agent_query'))
            yield _event('message', projection.event('answer', target['content'],
                {'event_id': target['id'], 'replace': True}, done=True))
            if run is None:
                yield _event('message', projection.event('stop', data={'reason': 'stream_interrupted'}, done=True))
                return
            try:
                traces = weknora_traces.LiveTraces(selected['id'], projection)
                weknora_traces.active[selected['id']] = traces
                structured_written = False
                async for part in client.runs.join_stream(selected['id'], run['run_id'], cancel_on_disconnect=False):
                    if part.event == 'end':
                        break
                    if part.event == 'error':
                        raise StoreError(str(part.data), 500)
                    kind, _, namespace = part.event.partition('|')
                    mapped = {'type': kind, 'data': part.data, 'ns': namespace.split('|') if namespace else []}
                    if kind == 'updates' and not mapped['ns']:
                        structured_written |= any(isinstance(update, dict) and 'structured_response' in update
                                                  for update in part.data.values())
                    for event in projection.feed(mapped):
                        yield _event('message', event)
                    for event in traces.feed(mapped):
                        yield _event('message', event)
                final_run = await client.runs.get(selected['id'], run['run_id'])
                if final_run.get('status') == 'cancelled':
                    yield _event('message', projection.event('stop', data={'reason': 'cancelled'}, done=True))
                    return
                if final_run.get('status') in ('error', 'timeout'):
                    raise StoreError(str(final_run.get('error') or '后台执行失败'),
                                     final_run.get('status_code') or 500)
                resolved = selected['agent_config']
                async with async_checkpointer() as saver:
                    graph = await _graph(saver, user, selected, resolved, load_tools=False)
                    state = await graph.aget_state({'configurable': {'thread_id': selected['id']}}, subgraphs=True)
                    async for frame in _completion(graph, state, user=user, selected=selected, resolved=resolved,
                                                   projection=projection, traces=traces,
                                                   structured_written=structured_written, request=request, context={}):
                        yield frame
            except Exception as exc:
                yield _event('message', projection.event('error', str(exc), {'status': getattr(exc, 'status', 500)}, done=True))
            finally:
                if traces:
                    traces.close()
                    if weknora_traces.active.get(selected['id']) is traces:
                        weknora_traces.active.pop(selected['id'], None)
        return EventSourceResponse(events(), headers={'Cache-Control': 'no-store'})
    except StoreError as exc:
        return JSONResponse({'message': str(exc)}, status_code=exc.status)


async def _child(request, *, subscribe=False):
    token = request.headers.get('authorization', '').removeprefix('Bearer ').strip()
    user, _ = await anyio.to_thread.run_sync(lambda: validate_access_token(token))
    view = request.path_params.get('session_id') or weknora_traces.PREFIX + request.path_params['view']
    parent, namespace, call_id = weknora_traces.decode(view)
    selected = await anyio.to_thread.run_sync(lambda: sessions.get_session(parent, user['id']))
    from webapi.weknora import async_views
    if namespace == async_views.NAMESPACE:
        task, rows = await async_views.read(user['id'], parent, call_id)
        return parent, namespace, task, rows, None, None, user['id']
    live = weknora_traces.active.get(parent)
    node = live.nodes.get(namespace) if live else None
    queue = live.subscribe(namespace) if subscribe and node and node['status'] == 'running' else None
    try:
        resolved = selected['agent_config']
        if not resolved.get('agent_config'):
            raise StoreError('子图视图不存在', 404)
        async with async_checkpointer() as saver:
            graph = await _graph(saver, user, selected, resolved, load_tools=False)
            state = await graph.aget_state({'configurable': {'thread_id': parent}}, subgraphs=True)
            _, _, task, rows, messages = await weknora_traces.read_child(
                saver, graph, state, parent, namespace, call_id, owner_id=user['id'])
            children = await weknora_traces.children(saver, graph, state, parent, messages, namespace, owner_id=user['id'])
        for row in rows:
            if row['id'] in children:
                row['collaboration_status'] = weknora_traces.snapshot(row['id'], children[row['id']])
        return parent, namespace, task, rows, live, queue, user['id']
    except BaseException:
        if queue is not None:
            live.unsubscribe(namespace, queue)
        raise


async def read_child_history(request):
    try:
        _, _, _, rows, _, _, _ = await _child(request)
        return JSONResponse({'success': True, 'data': rows})
    except StoreError as exc:
        return JSONResponse({'message': str(exc)}, status_code=exc.status)


async def continue_child(request):
    """Observe the parent request only; this GET cannot invoke or resume a graph."""
    queue = None
    try:
        parent, namespace, task, rows, live, queue, owner = await _child(request, subscribe=True)
        if request.query_params.get('resume_pending_id'):
            raise StoreError('子图为只读视图；请在父会话处理原生审批', 409)
        target = next((row for row in rows if row['role'] == 'assistant'
                       and row['id'] == request.query_params.get('message_id')), None)
        if target is None:
            raise StoreError('消息不存在', 404)
        from webapi.weknora.adapter import StreamProjection
        projection = StreamProjection(task['session_id'], target['id'], owner_id=owner)
        async def events():
            try:
                yield _event('message', projection.event('agent_query'))
                for step in target['agent_steps']:
                    for call in step['tool_calls']:
                        yield _event('message', projection.event('tool_call', data={
                            'tool_call_id': call['id'], 'tool_name': call['name'], 'arguments': call['args']}))
                        if call.get('result'):
                            yield _event('message', projection.event('tool_result', data=call['result']))
                yield _event('message', projection.event('answer', target['content'],
                    {'event_id': target['id'], 'replace': True}, done=True))
                if queue is not None:
                    while (event := await queue.get()) is not None:
                        yield _event('message', event)
                else:
                    yield _event('message', projection.event('stop', data={'reason': task['status']}, done=True))
            finally:
                if queue is not None:
                    live.unsubscribe(namespace, queue)
        response = EventSourceResponse(events(), headers={'Cache-Control': 'no-store'})
        async def send_observation(scope, receive, send):
            try:
                await response(scope, receive, send)
            finally:
                if queue is not None:
                    live.unsubscribe(namespace, queue)
        return send_observation
    except StoreError as exc:
        if queue is not None:
            live.unsubscribe(namespace, queue)
        return JSONResponse({'message': str(exc)}, status_code=exc.status)


routes = [
    Route('/api/v1/messages/subgraph~{view}/load', read_child_history, methods=['GET']),
    Route('/api/v1/agent-chat/{session_id}', weknora_stream, methods=['POST']),
    Route('/api/v1/knowledge-chat/{session_id}', weknora_stream, methods=['POST']),
    Route('/api/v1/sessions/continue-stream/{session_id}', continue_weknora, methods=['GET']),
    Route('/api/v1/harness/sessions/{session_id}/state', read_state, methods=['GET']),
    Route('/api/v1/harness/sessions/{session_id}/stream', stream, methods=['POST']),
]
