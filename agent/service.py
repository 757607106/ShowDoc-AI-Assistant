"""deepagents execution with official checkpoints and WeKnora SSE presentation."""
import asyncio
import json
import queue
import threading
import time
import uuid
from contextlib import suppress

from psycopg.types.json import Jsonb

from agent import sessions
from agent.citations import AnswerCitations
from agent.checkpointer import async_checkpointer
from agent.graph import build_agent
from governance.database import connection
from governance.store import StoreError, now

END = object()


def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return ''.join(part.get('text', '') for part in content if isinstance(part, dict))
    return str(content or '')


def begin_run(session_id, owner_id, message, run_id, knowledge_base_ids=None):
    sessions.get_session(session_id, owner_id)
    from psycopg.errors import UniqueViolation
    try:
        with connection() as conn:
            row = conn.execute('SELECT running_id FROM agent_sessions WHERE id=%s AND owner_id=%s FOR UPDATE', (session_id, owner_id)).fetchone()
            if row['running_id']:
                raise StoreError('会话正在执行，请等待或停止后重试', 409)
            conn.execute("INSERT INTO agent_runs(id,session_id,owner_id,status,query) VALUES (%s,%s,%s,'running',%s)", (run_id, session_id, owner_id, message))
            conn.execute('UPDATE agent_sessions SET running_id=%s,cancel_requested=false,updated_at=now() WHERE id=%s', (run_id, session_id))
            if knowledge_base_ids is not None:
                conn.execute('UPDATE agent_sessions SET knowledge_base_ids=%s WHERE id=%s', (Jsonb(knowledge_base_ids), session_id))
    except UniqueViolation as exc:
        raise StoreError('该请求已受理，不能重复提交', 409) from exc


def _finish(run_id, session_id, owner_id, status, answer, references, pending=None, error=None, steps=None):
    with connection() as conn:
        conn.execute('UPDATE agent_runs SET status=%s,answer=%s,references_json=%s,pending_json=%s,error=%s,updated_at=now() WHERE id=%s AND owner_id=%s',
                     (status, answer, Jsonb(references), Jsonb(pending) if pending else None, error, run_id, owner_id))
        conn.execute('UPDATE agent_sessions SET running_id=NULL,updated_at=now() WHERE id=%s AND owner_id=%s AND running_id=%s', (session_id, owner_id, run_id))
        conn.execute('UPDATE agent_runs SET steps_json=%s WHERE id=%s AND owner_id=%s', (Jsonb(steps or []),run_id,owner_id))


def _structured(output):
    if isinstance(output, dict):
        return output
    artifact = getattr(output, 'artifact', None)
    if artifact is not None:
        data = getattr(artifact, 'structured_content', None)
        if data is None and isinstance(artifact, dict):
            data = artifact.get('structured_content')
        if isinstance(data, dict):
            return data
    content = _text(getattr(output, 'content', output))
    try:
        data = json.loads(content)
        return data if isinstance(data, dict) else {}
    except (ValueError, TypeError):
        return {}


def _tool_succeeded(output, native):
    return (getattr(output, 'status', None) != 'error' and
            native.get('isError') is not True and native.get('success') is not False and
            native.get('errorCode') in (None, 0))


async def _execute(session_id, message, owner_id, api_key, role, run_id, events, decisions=None):
    answer, references, steps = '', [], []
    citations = None
    truncated_result, limitation_sent = False, False
    def emit(kind, content='', data=None, done=False):
        events.put({'id': run_id, 'assistant_message_id': run_id, 'response_type': kind,
                    'content': content, 'data': data or {}, 'done': done})
    emit('agent_query', data={'session_id': session_id})
    def append_answer(content):
        nonlocal answer
        if content:
            answer += content
            emit('answer', content, {'event_id': run_id})

    def append_limit_notice():
        nonlocal limitation_sent
        if truncated_result and not limitation_sent:
            limitation_sent = True
            append_answer('\n\n> 范围说明：本轮官方结果已截断，回答仅依据已返回内容；未展示的资料或关系尚未核实。')

    def finish_tool(tool_id, name, *, success, output='', error=None):
        result = {'success': success, 'output': output}
        if error:
            result['error'] = error
        for step in reversed(steps):
            call = step['tool_calls'][0]
            if call['id'] == tool_id:
                if call.get('result') == result:
                    return
                call['result'] = result
                break
        emit('tool_result', data={'tool_call_id': tool_id, 'tool_name': name, **result})

    def close_open_tools(reason):
        for step in steps:
            call = step['tool_calls'][0]
            if 'result' not in call:
                finish_tool(call['id'], call['name'], success=False, error=reason)

    execution_task = asyncio.current_task()
    async def watch_run():
        last_save = time.monotonic()
        while True:
            await asyncio.sleep(0.5)
            if await asyncio.to_thread(lambda: sessions.get_session(session_id, owner_id)['cancel_requested']):
                execution_task.cancel()
                return
            if time.monotonic() - last_save < 5:
                continue
            def save():
                with connection() as conn:
                    conn.execute("UPDATE agent_runs SET answer=%s,references_json=%s,steps_json=%s,updated_at=now() WHERE id=%s AND owner_id=%s AND status='running'", (answer,Jsonb(references),Jsonb(steps),run_id,owner_id))
            await asyncio.to_thread(save)
            last_save = time.monotonic()
    progress_task = asyncio.create_task(watch_run())
    try:
        async with async_checkpointer() as saver:
            selected = await asyncio.to_thread(sessions.get_session, session_id, owner_id)
            citations = AnswerCitations(selected['knowledge_base_ids'])
            references = citations.references
            agent = await build_agent(saver, api_key=api_key, owner_id=owner_id, role=role, knowledge_base_ids=selected['knowledge_base_ids'])
            config = {'configurable': {'thread_id': session_id}, 'recursion_limit': 80}
            state = await agent.aget_state(config)
            if decisions is None:
                if state.interrupts:
                    raise StoreError('请先处理当前待确认的工具操作', 409)
                inputs = {'messages': [{'role': 'user', 'content': message}]}
            else:
                # Approval resumes the same user turn; earlier turns are not evidence.
                messages = (getattr(state, 'values', {}) or {}).get('messages', [])
                start = next((i for i in range(len(messages) - 1, -1, -1)
                              if getattr(messages[i], 'type', None) == 'human'), len(messages))
                for output in messages[start + 1:]:
                    if getattr(output, 'type', None) == 'tool':
                        native = _structured(output)
                        success = _tool_succeeded(output, native)
                        citations.register(output.name, native, success=success)
                        truncated_result |= success and (output.name or '').startswith('knowledge.') and native.get('truncated') is True
                if references:
                    emit('references', data={'references': list(references)})
                from langgraph.types import Command
                inputs = Command(resume={'decisions': decisions})
            async for event in agent.astream_events(inputs, config=config, version='v2'):
                kind, data = event.get('event'), event.get('data') or {}
                if kind == 'on_chat_model_stream':
                    delta = _text(getattr(data.get('chunk'), 'content', ''))
                    if delta:
                        append_answer(citations.feed(delta))
                elif kind == 'on_chat_model_end':
                    append_answer(citations.flush())
                elif kind == 'on_tool_start':
                    steps.append({'iteration':len(steps), 'timestamp':now(), 'tool_calls':[{
                        'id':event.get('run_id'),'name':event.get('name'),'arguments':data.get('input')}]})
                    emit('tool_call', data={'tool_call_id': event.get('run_id'), 'tool_name': event.get('name'), 'arguments': data.get('input')})
                elif kind == 'on_tool_end':
                    output = data.get('output')
                    native = _structured(output)
                    success = _tool_succeeded(output, native)
                    truncated_result |= success and (event.get('name') or '').startswith('knowledge.') and native.get('truncated') is True
                    display = native or _text(getattr(output, 'content', output))[:12000]
                    error = None if success else _text(native.get('errorMessage') or native.get('error') or display)
                    finish_tool(event.get('run_id'), event.get('name'), success=success, output=display, error=error)
                    count = len(references)
                    citations.register(event.get('name'), native, success=success)
                    if len(references) != count:
                        emit('references', data={'references': list(references)})
                elif kind == 'on_tool_error':
                    error = str(data.get('error') or '工具执行失败')
                    error = error.replace(api_key, '[REDACTED]') if api_key else error
                    finish_tool(event.get('run_id'), event.get('name'), success=False, error=error[:1000])
            append_answer(citations.flush())
            state = await agent.aget_state(config)
            pending = None
            if state.interrupts:
                pending = {'id': run_id, 'kind': 'tool_approval', 'status': 'suspended',
                           'request': state.interrupts[0].value, 'created_at':now()}
                actions = pending['request'].get('action_requests', [])
                pending['request'].update(service_name='ContextDB',
                    mcp_tool_name=actions[0]['name'] if len(actions) == 1 else 'ContextDB 批量操作',
                    args={'actions': actions}, description='确认后才执行下列官方知识库操作')
                emit('tool_approval_required', data={'pending_id': run_id,
                    'service_name': 'ContextDB', 'mcp_tool_name': pending['request']['mcp_tool_name'],
                    'args_json': json.dumps({'actions': actions}, ensure_ascii=False),
                    'suspendable': True, 'session_id': session_id})
                emit('run_suspended', data={'pending_id':run_id})
            status = 'waiting' if pending else 'completed'
            if not pending:
                close_open_tools('执行已结束，未收到工具结果；如涉及写入，请核实官方状态')
                append_limit_notice()
            await asyncio.to_thread(_finish, run_id, session_id, owner_id, status, answer, references, pending, steps=steps)
            emit('complete', data={'session_id': session_id, 'pending_prompt': pending}, done=True)
    except asyncio.CancelledError:
        if citations:
            append_answer(citations.flush())
        append_limit_notice()
        close_open_tools('执行已取消，未收到工具结果；如涉及写入，请核实官方状态')
        await asyncio.to_thread(_finish, run_id, session_id, owner_id, 'cancelled', answer, references, steps=steps)
        emit('stop', done=True)
    except Exception as exc:
        if citations:
            append_answer(citations.flush())
        append_limit_notice()
        error = str(exc).replace(api_key, '[REDACTED]')[:500] if api_key else str(exc)[:500]
        close_open_tools('执行失败，未收到工具结果；如涉及写入，请核实官方状态')
        await asyncio.to_thread(_finish, run_id, session_id, owner_id, 'failed', answer, references, error=error, steps=steps)
        emit('error', error, done=True)
    finally:
        progress_task.cancel()
        with suppress(asyncio.CancelledError):
            await progress_task
        events.put(END)


def stream_chat(session_id, message, *, owner_id, api_key, role, run_id=None, decisions=None, knowledge_base_ids=None):
    run_id = run_id or str(uuid.uuid4())
    begin_run(session_id, owner_id, message, run_id, knowledge_base_ids)
    events = queue.Queue()
    def worker():
        try:
            asyncio.run(asyncio.wait_for(_execute(session_id, message, owner_id, api_key, role, run_id, events, decisions), timeout=1800))
        finally:
            events.put(END)
    threading.Thread(target=worker, daemon=True).start()
    def generate():
        while True:
            try:
                event = events.get(timeout=15)
            except queue.Empty:
                event = {'response_type': 'heartbeat', 'id': run_id}
            if event is END:
                break
            yield 'data: ' + json.dumps(event, ensure_ascii=False, default=str) + '\n\n'
    return generate()


def stream_chat_flask(session_id, message, **kwargs):
    from flask import stream_with_context
    return stream_with_context(stream_chat(session_id, message, **kwargs))
