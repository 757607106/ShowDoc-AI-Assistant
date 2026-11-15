"""Session metadata and read-only legacy history; native streaming lives in harness.py."""
import asyncio
from datetime import datetime

from flask import Blueprint, g, jsonify, request

from agent import sessions as agent_sessions
from governance.store import StoreError
from governance.database import connection
from webapi.auth import user_id
from webapi.legacy_runtime import unavailable

agent_bp = Blueprint('agent', __name__)


def _json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise StoreError('请求必须是 JSON 对象', 400)
    return body


@agent_bp.route('/api/agent/sessions')
def agent_sessions_list():
    return jsonify(success=True, sessions=agent_sessions.list_sessions())


@agent_bp.route('/api/agent/sessions', methods=['POST'])
def agent_sessions_create():
    body = _json_body()
    title = str(body.get('title', '') or '')[:200]
    session = agent_sessions.create_session(title)
    return jsonify(success=True, session=session)


@agent_bp.route('/api/agent/sessions/<session_id>')
def agent_session_detail(session_id):
    messages = agent_sessions.read_messages(session_id)
    return jsonify(success=True, session_id=session_id, messages=messages)


@agent_bp.route('/api/agent/sessions/<session_id>', methods=['DELETE'])
def agent_session_delete(session_id):
    removed = agent_sessions.delete_session(session_id)
    if not removed:
        raise StoreError('会话不存在', 404)
    return jsonify(success=True, message='会话及其上下文已删除')


@agent_bp.route('/api/agent/chat', methods=['POST'])
def agent_chat():
    unavailable(_json_body().get('session_id'))


@agent_bp.route('/api/v1/sessions', methods=['GET', 'POST'])
def weknora_sessions():
    if request.method == 'POST':
        body = _json_body()
        item = agent_sessions.create_session(body.get('title', ''), agent_config=body.get('agent_config'), kind=body.get('kind', ''))
        return jsonify(success=True, data=item)
    source = request.args.get('source')
    items = agent_sessions.list_sessions(source=source or None)
    page = max(1, request.args.get('page', 1, type=int))
    size = min(100, max(1, request.args.get('page_size', 30, type=int)))
    return jsonify(success=True, data=items[(page-1)*size:page*size], total=len(items))


@agent_bp.route('/api/v1/sessions/<session_id>', methods=['GET', 'PUT', 'DELETE'])
def weknora_session(session_id):
    if request.method == 'DELETE':
        agent_sessions.delete_session(session_id)
        return jsonify(success=True)
    if request.method == 'PUT':
        item = agent_sessions.touch_session(session_id, _json_body().get('title'))
    else:
        item = agent_sessions._public(agent_sessions.get_session(session_id))
    return jsonify(success=True, data=item)


@agent_bp.route('/api/v1/messages/<session_id>/load')
def weknora_messages(session_id):
    selected_session = agent_sessions.get_session(session_id)
    if selected_session['agent_config'].get('runtime') == 'deepagents':
        from webapi.harness import read_weknora_history
        messages = asyncio.run(read_weknora_history(g.user, selected_session))
        before = request.args.get('before_time')
        if before:
            try:
                cutoff = datetime.fromisoformat(before.replace('Z', '+00:00'))
                if cutoff.tzinfo is None:
                    raise ValueError()
            except ValueError:
                raise StoreError('消息时间无效', 400)
            messages = [item for item in messages if item.get('created_at')
                        and datetime.fromisoformat(item['created_at']) < cutoff]
        limit = min(100, max(2, request.args.get('limit', 20, type=int)))
        return jsonify(success=True, data=messages[-(limit // 2 * 2):])
    with connection() as conn:
        runs = conn.execute('SELECT * FROM agent_runs WHERE session_id=%s AND owner_id=%s ORDER BY created_at,id', (session_id, user_id())).fetchall()
    messages = []
    if not runs:
        roles = {'human':'user', 'ai':'assistant'}
        for i, item in enumerate(agent_sessions.read_messages(session_id)):
            if item['role'] in roles and item['content']:
                messages.append({**item, 'id':item['id'] or f'{session_id}-{i}',
                                 'role':roles[item['role']], 'session_id':session_id, 'is_completed':True})
    by_id={run['id']:run for run in runs}
    linked={run['pending_json']['resumed_run_id'] for run in runs if run['pending_json'] and run['pending_json'].get('resumed_run_id')}
    roots = [run for run in runs if run['id'] not in linked]
    before = request.args.get('before_time')
    if before:
        try:
            cutoff = datetime.fromisoformat(before.replace('Z', '+00:00'))
            if cutoff.tzinfo is None:
                raise ValueError()
        except ValueError:
            raise StoreError('消息时间无效', 400)
        roots = [run for run in roots if run['created_at'] < cutoff]
    limit = min(100, max(1, request.args.get('limit', 20, type=int)))
    # Keep a user turn and its resumed/injected assistant rows on the same page.
    selected = {run['id'] for run in roots[-max(1, limit // 2):]}
    for run in runs:
        if run['id'] not in selected:
            continue
        chain, seen=[],set()
        current=run
        while current and current['id'] not in seen:
            chain.append(current);seen.add(current['id'])
            next_id=(current['pending_json'] or {}).get('resumed_run_id')
            current=by_id.get(next_id)
        latest=chain[-1]
        with connection() as conn:
            event_rows = conn.execute('SELECT cursor,event_json FROM agent_run_events WHERE owner_id=%s AND run_id=ANY(%s) ORDER BY cursor',
                                      (user_id(), [part['id'] for part in chain])).fetchall()
        tools, answers, answer_parts, timeline, collaboration = {}, {}, {}, [], None
        for stored in event_rows:
            event = stored['event_json']
            data = event.get('data') or {}
            if event['response_type'] == 'answer':
                key = event['id']
                parts = answer_parts.setdefault(key, {})
                model_id = data.get('event_id', key)
                if data.get('replace'):
                    parts.clear()
                parts[model_id] = parts.get(model_id, '') + event.get('content', '')
                answers[key] = ''.join(parts.values())
            elif event['response_type'] == 'progress':
                parts = answer_parts.setdefault(event['id'], {})
                parts.pop(data.get('event_id'), None)
                answers[event['id']] = ''.join(parts.values())
                timeline.append({'iteration': len(timeline), 'tool_calls': [], 'progress': event.get('content') or data.get('content', ''), 'progress_event_id': data.get('event_id')})
            elif event['response_type'] == 'tool_call':
                if data['tool_call_id'] not in tools:
                    tools[data['tool_call_id']] = {'id': data['tool_call_id'], 'name': data['tool_name'], 'arguments': data.get('arguments')}
                    timeline.append({'iteration': len(timeline), 'tool_calls': [tools[data['tool_call_id']]]})
                else:
                    tools[data['tool_call_id']]['arguments'] = data.get('arguments')
            elif event['response_type'] == 'tool_result' and data['tool_call_id'] in tools:
                tools[data['tool_call_id']]['result'] = {k: data[k] for k in ('success', 'output', 'error') if k in data}
                tools[data['tool_call_id']]['result']['data'] = data.get('data') or data
            elif event['response_type'] == 'collaboration_status':
                collaboration = data
        if run['query']:
            messages.append({'id':'user-'+run['id'],'session_id':session_id,'role':'user','content':run['query'],
                             'mentioned_items': (run['request_json'] or {}).get('mentioned_items', []),
                             'images': (run['request_json'] or {}).get('user_images', []),
                             'attachments': (run['request_json'] or {}).get('attachments', []),
                             'created_at':run['created_at'].isoformat(),'is_completed':True})
        references=[]
        for part in chain:
            for ref in part['references_json']:
                if ref.get('title') and not ref.get('knowledge_title'):
                    ref={**ref,'knowledge_title':ref['title'],'knowledge_filename':ref['title']}
                if ref not in references:references.append(ref)
        for stored in event_rows:
            if stored['event_json']['response_type'] == 'references':
                for ref in stored['event_json'].get('data', {}).get('references', []):
                    if not any(existing.get('id') == ref.get('id') and existing.get('kb_id') == ref.get('kb_id') for existing in references):
                        references.append(ref)
        messages.append({'id':run['id'],'session_id':session_id,'role':'assistant',
            'content':'\n\n'.join(answers.get(part['id'], part['answer']) for part in chain if answers.get(part['id'], part['answer'])) or latest['error'] or '',
            'created_at':run['created_at'].isoformat(),'is_completed':True, 'read_only':True, 'archived_status':latest['status'],
            'knowledge_references':references,'pending_prompt':latest['pending_json'],'error':latest['error'],
            'artifacts': run.get('artifacts_json', []), 'artifacts_truncated': run.get('artifacts_truncated', False),
            'agent_steps': timeline if timeline else [step for part in chain for step in part['steps_json']],
            'collaboration_status': collaboration,
            'stream_cursor': event_rows[-1]['cursor'] if event_rows else 0,
            'prompt_history':[part['pending_json'] for part in chain[:-1] if part['pending_json']],
            'run_state':'awaiting_input' if latest['status']=='waiting' else 'cancelled' if latest['status']=='cancelled' else ''})
        injections = [i for i, stored in enumerate(event_rows) if stored['event_json']['response_type'] == 'user_message_injected'
                      and stored['event_json'].get('data', {}).get('delivery') != 'after']
        if injections:
            whole = messages.pop()
            start = 0
            for segment, end in enumerate([*injections, len(event_rows)]):
                segment_events = event_rows[start:end]
                segment_tools, segment_answers, segment_steps = {}, {}, []
                for stored in segment_events:
                    event = stored['event_json']
                    data = event.get('data') or {}
                    if event['response_type'] == 'answer':
                        model_id = data.get('event_id', event['id'])
                        if data.get('replace'):
                            segment_answers.clear()
                        segment_answers[model_id] = segment_answers.get(model_id, '') + event.get('content', '')
                    elif event['response_type'] == 'progress':
                        segment_answers.pop(data.get('event_id'), None)
                        segment_steps.append({'iteration': len(segment_steps), 'tool_calls': [], 'progress': event.get('content') or data.get('content', ''), 'progress_event_id': data.get('event_id')})
                    elif event['response_type'] == 'tool_call':
                        if data['tool_call_id'] not in segment_tools:
                            segment_tools[data['tool_call_id']] = {'id': data['tool_call_id'], 'name': data['tool_name'], 'arguments': data.get('arguments')}
                            segment_steps.append({'iteration': len(segment_steps), 'tool_calls': [segment_tools[data['tool_call_id']]]})
                        else:
                            segment_tools[data['tool_call_id']]['arguments'] = data.get('arguments')
                    elif event['response_type'] == 'tool_result' and data['tool_call_id'] in segment_tools:
                        segment_tools[data['tool_call_id']]['result'] = {k: data[k] for k in ('success', 'output', 'error') if k in data}
                        segment_tools[data['tool_call_id']]['result']['data'] = data.get('data') or data
                last_segment = end == len(event_rows)
                item = {**whole, 'id': run['id'] if segment == 0 else f'{run["id"]}:steer:{segment}',
                    'assistant_message_id': run['id'], 'request_id': run['id'], 'content': ''.join(segment_answers.values()),
                    'agent_steps': segment_steps}
                if not last_segment:
                    item.update(steerForked=True, is_completed=True, pending_prompt=None, prompt_history=[],
                                collaboration_status=None, stream_cursor=0, run_state='', artifacts=[], artifacts_truncated=False)
                messages.append(item)
                if not last_segment:
                    data = event_rows[end]['event_json']['data']
                    messages.append({'id': data.get('user_message_id') or 'steer-user-' + data['steer_id'],
                        'request_id': run['id'], 'session_id': session_id, 'role': 'user', 'isSteer': True,
                        'steer_id': data['steer_id'], 'content': data.get('content', ''),
                        'mentioned_items': data.get('mentioned_items', []), 'is_completed': True,
                        'created_at': run['created_at'].isoformat()})
                start = end + 1
    return jsonify(success=True, data=messages)


@agent_bp.route('/api/v1/sessions/<session_id>/generate_title', methods=['POST'])
def session_title(session_id):
    selected = agent_sessions.get_session(session_id)
    if selected['agent_config'].get('runtime') != 'deepagents':
        raise StoreError('旧会话已归档为只读，历史标题保留', 410)
    messages = _json_body().get('messages')
    if not isinstance(messages, list) or any(not isinstance(item, dict)
            or not isinstance(item.get('role'), str) or not isinstance(item.get('content'), str)
            for item in messages):
        raise StoreError('messages 必须为包含 role 和文本 content 的消息数组', 400)
    from agent.session_titles import first_query, generate_title
    query = first_query([{'role': item['role'], 'content': item['content']} for item in messages]) if messages else None
    if messages and (not query.strip() or len(query) > 100_000):
        raise StoreError('首条用户消息必须为非空文本，且不超过 100000 字符', 400)
    try:
        title = asyncio.run(generate_title(session_id, user_id(), query=query,
                            language=request.headers.get('Accept-Language', 'zh-CN')))
    except StoreError:
        raise
    except TimeoutError as exc:
        raise StoreError('会话标题生成超时，请稍后重试', 503) from exc
    except Exception as exc:
        raise StoreError(f'会话标题生成失败（{type(exc).__name__}）', 502) from exc
    return jsonify(success=True, data=title)


@agent_bp.route('/api/v1/sessions/<session_id>/pin', methods=['POST','DELETE'])
def session_pin(session_id):
    if agent_sessions.get_session(session_id)['agent_config'].get('runtime') != 'deepagents':
        unavailable()
    with connection() as conn:
        row = conn.execute('UPDATE agent_sessions SET pinned_at=CASE WHEN %s THEN now() ELSE NULL END WHERE id=%s AND owner_id=%s RETURNING *', (request.method=='POST',session_id,user_id())).fetchone()
    return jsonify(success=True, data=agent_sessions._public(row))


@agent_bp.route('/api/v1/sessions/<session_id>/messages', methods=['DELETE'])
def session_clear(session_id):
    agent_sessions.clear_session(session_id)
    return jsonify(success=True)


@agent_bp.route('/api/v1/sessions/batch', methods=['DELETE'])
def sessions_delete_batch():
    body = _json_body()
    ids = [s['id'] for s in agent_sessions.list_sessions()] if body.get('delete_all') is True else body.get('ids')
    if not isinstance(ids,list) or len(ids)>500 or any(not isinstance(sid,str) for sid in ids):
        raise StoreError('请提供不超过 500 个会话 ID', 400)
    for sid in ids:
        if agent_sessions.get_session(sid)['agent_config'].get('runtime') != 'deepagents':
            unavailable()
    for sid in ids:
        agent_sessions.delete_session(sid)
    return jsonify(success=True)


@agent_bp.route('/api/v1/agent-chat', methods=['POST'])
@agent_bp.route('/api/v1/agent-chat/<session_id>', methods=['POST'])
@agent_bp.route('/api/v1/knowledge-chat/<session_id>', methods=['POST'])
def weknora_chat(session_id=None):
    unavailable(session_id or _json_body().get('session_id'))


@agent_bp.route('/api/v1/sessions/<session_id>/stop', methods=['POST'])
def stop(session_id):
    selected = agent_sessions.get_session(session_id)
    if selected['agent_config'].get('runtime') != 'deepagents':
        unavailable(session_id)
    body = _json_body()
    identifier = body.get('message_id')
    if not isinstance(identifier, str) or not identifier:
        raise StoreError('message_id 必须是非空字符串', 400)
    from webapi.harness import _active_requests, read_weknora_history
    active = _active_requests.get(session_id)
    if active:
        loop, task, active_id = active
        if active_id != identifier:
            raise StoreError('消息已变化，请重新加载会话', 409)
        loop.call_soon_threadsafe(task.cancel)
    else:
        # shortcut: stop uses a local request handle; add cross-worker cancellation before deploying multiple API workers.
        with agent_sessions._mutation(session_id, g.user['id']):
            rows = asyncio.run(read_weknora_history(g.user, selected))
            if not any(row['role'] == 'assistant' and row['id'] == identifier for row in rows):
                raise StoreError('消息不存在', 404)
    return jsonify(success=True)


@agent_bp.route('/api/v1/agent/tool-approvals/<pending_id>', methods=['POST'])
def approve_tool(pending_id):
    from webapi.weknora_prompts import stage
    return jsonify(resumed=stage(g.user, pending_id, _json_body(), 'tool_approval'))


@agent_bp.route('/api/v1/agent/prompts/<pending_id>', methods=['POST'])
def answer_prompt(pending_id):
    from webapi.weknora_prompts import stage
    return jsonify(resumed=stage(g.user, pending_id, _json_body(), 'ask_user'))


@agent_bp.route('/api/v1/agent/mcp-oauth-resolutions/<pending_id>', methods=['POST'])
@agent_bp.route('/api/v1/agent/mcp-oauth-resolutions/<pending_id>/cancel', methods=['POST'])
def resolve_oauth(pending_id):
    from webapi.weknora_prompts import stage
    body = {'decision': 'cancel'} if request.path.endswith('/cancel') else _json_body()
    return jsonify(resumed=stage(g.user, pending_id, body, 'mcp_oauth'))




@agent_bp.route('/api/v1/sessions/continue-stream')
@agent_bp.route('/api/v1/sessions/continue-stream/<session_id>')
def continue_stream(session_id=None):
    unavailable(session_id)
