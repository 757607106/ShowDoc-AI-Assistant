"""Agent 域 API:会话管理、消息读回、SSE 流式对话。"""
import json
import time
import uuid

from flask import Blueprint, Response, g, jsonify, request, stream_with_context

from agent import sessions as agent_sessions
from agent.service import stream_chat_flask
from governance.store import StoreError
from governance.database import connection
from webapi.auth import client_for_user, user_id

agent_bp = Blueprint('agent', __name__)


def _json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise StoreError('请求必须是 JSON 对象', 400)
    return body


def _knowledge_base_ids(body):
    ids = body.get('knowledge_base_ids')
    if ids is not None and (not isinstance(ids, list) or len(ids) > 100 or any(not isinstance(kb, str) or not kb or len(kb) > 200 for kb in ids)):
        raise StoreError('knowledge_base_ids 必须是有效 ID 列表', 400)
    return ids


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
    body = _json_body()
    session_id = str(body.get('session_id', '')).strip()
    message = str(body.get('message', '')).strip()
    if not session_id:
        raise StoreError('缺少 session_id 参数', 400)
    if not message:
        raise StoreError('message 不能为空', 400)
    client = client_for_user()
    generator = stream_chat_flask(session_id, message, owner_id=user_id(), api_key=client.api_key,
                                  role=g.user['role'], knowledge_base_ids=_knowledge_base_ids(body))
    return Response(generator, mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@agent_bp.route('/api/v1/sessions', methods=['GET', 'POST'])
def weknora_sessions():
    if request.method == 'POST':
        item = agent_sessions.create_session(_json_body().get('title', ''))
        return jsonify(success=True, data=item)
    source = request.args.get('source')
    items = agent_sessions.list_sessions() if not source or source=='web' else []
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
    agent_sessions.get_session(session_id)
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
    for run in runs:
        if run['id'] in linked:
            continue
        chain, seen=[],set()
        current=run
        while current and current['id'] not in seen:
            chain.append(current);seen.add(current['id'])
            next_id=(current['pending_json'] or {}).get('resumed_run_id')
            current=by_id.get(next_id)
        latest=chain[-1]
        if run['query']:
            messages.append({'id':'user-'+run['id'],'session_id':session_id,'role':'user','content':run['query'],
                             'created_at':run['created_at'].isoformat(),'is_completed':True})
        references=[]
        for part in chain:
            for ref in part['references_json']:
                if ref.get('title') and not ref.get('knowledge_title'):
                    ref={**ref,'knowledge_title':ref['title'],'knowledge_filename':ref['title']}
                if ref not in references:references.append(ref)
        messages.append({'id':run['id'],'session_id':session_id,'role':'assistant',
            'content':'\n\n'.join(part['answer'] for part in chain if part['answer']) or latest['error'] or '',
            'created_at':run['created_at'].isoformat(),'is_completed':latest['status']!='running',
            'knowledge_references':references,'pending_prompt':latest['pending_json'],'error':latest['error'],
            'agent_steps':[step for part in chain for step in part['steps_json']],
            'prompt_history':[part['pending_json'] for part in chain[:-1] if part['pending_json']],
            'run_state':'awaiting_input' if latest['status']=='waiting' else 'cancelled' if latest['status']=='cancelled' else ''})
    return jsonify(success=True, data=messages)


@agent_bp.route('/api/v1/sessions/<session_id>/generate_title', methods=['POST'])
def session_title(session_id):
    agent_sessions.get_session(session_id)
    with connection() as conn:
        first = conn.execute("SELECT query FROM agent_runs WHERE session_id=%s AND owner_id=%s AND query<>'' ORDER BY created_at LIMIT 1", (session_id,user_id())).fetchone()
    item = agent_sessions.touch_session(session_id, first['query'][:40] if first else None)
    return jsonify(success=True, data=item)


@agent_bp.route('/api/v1/sessions/<session_id>/pin', methods=['POST','DELETE'])
def session_pin(session_id):
    agent_sessions.get_session(session_id)
    with connection() as conn:
        row = conn.execute('UPDATE agent_sessions SET pinned_at=CASE WHEN %s THEN now() ELSE NULL END WHERE id=%s AND owner_id=%s RETURNING *', (request.method=='POST',session_id,user_id())).fetchone()
    return jsonify(success=True, data=agent_sessions._public(row))


@agent_bp.route('/api/v1/sessions/<session_id>/messages', methods=['DELETE'])
def session_clear(session_id):
    row = agent_sessions.get_session(session_id)
    if row['running_id']:
        raise StoreError('请先停止会话', 409)
    from agent.checkpointer import make_checkpointer
    with make_checkpointer() as saver:
        saver.delete_thread(session_id)
    with connection() as conn:
        conn.execute('DELETE FROM agent_runs WHERE session_id=%s AND owner_id=%s', (session_id,user_id()))
    return jsonify(success=True)


@agent_bp.route('/api/v1/sessions/batch', methods=['DELETE'])
def sessions_delete_batch():
    body = _json_body()
    ids = [s['id'] for s in agent_sessions.list_sessions()] if body.get('delete_all') is True else body.get('ids')
    if not isinstance(ids,list) or len(ids)>500 or any(not isinstance(sid,str) for sid in ids):
        raise StoreError('请提供不超过 500 个会话 ID', 400)
    for sid in ids:
        if agent_sessions.get_session(sid)['running_id']:
            raise StoreError('请先停止正在执行的会话',409)
    for sid in ids:
        agent_sessions.delete_session(sid)
    return jsonify(success=True)


@agent_bp.route('/api/v1/agent-chat', methods=['POST'])
@agent_bp.route('/api/v1/agent-chat/<session_id>', methods=['POST'])
@agent_bp.route('/api/v1/knowledge-chat/<session_id>', methods=['POST'])
def weknora_chat(session_id=None):
    body = _json_body()
    session_id = session_id or body.get('session_id')
    message = body.get('query', '')
    if not isinstance(message, str) or not message.strip() or not session_id:
        raise StoreError('缺少会话或问题', 400)
    if body.get('knowledge_ids') or body.get('tag_ids') or body.get('images') or body.get('attachment_ids'):
        raise StoreError('本期对话请按知识库选择范围；文件、标签和临时附件对话尚未接入', 501)
    ids = _knowledge_base_ids(body)
    client = client_for_user()
    request_id = request.headers.get('X-Request-ID', '')
    request_id = request_id[:80] if request_id else str(uuid.uuid4())
    generator = stream_chat_flask(session_id, message, owner_id=user_id(), api_key=client.api_key,
                                  role=g.user['role'], run_id=f'{user_id()}:{request_id}', knowledge_base_ids=ids)
    return Response(generator, mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@agent_bp.route('/api/v1/sessions/<session_id>/stop', methods=['POST'])
def stop(session_id):
    agent_sessions.get_session(session_id)
    with connection() as conn:
        conn.execute('UPDATE agent_sessions SET cancel_requested=true WHERE id=%s AND owner_id=%s', (session_id, user_id()))
    return jsonify(success=True)


@agent_bp.route('/api/v1/agent/tool-approvals/<pending_id>', methods=['POST'])
def approve_tool(pending_id):
    if g.user['role'] == 'viewer':
        raise StoreError('只读账号不能批准知识写入操作', 403)
    body = _json_body()
    if body.get('decision') not in ('approve', 'reject') or body.get('modified_args'):
        raise StoreError('当前确认仅支持批准或拒绝原始工具参数', 400)
    with connection() as conn:
        row = conn.execute('SELECT * FROM agent_runs WHERE id=%s AND owner_id=%s FOR UPDATE', (pending_id, user_id())).fetchone()
        if row is None or row['status'] != 'waiting':
            raise StoreError('待确认操作不存在或已处理', 409)
        count = len(row['pending_json']['request']['action_requests'])
        conn.execute("UPDATE agent_runs SET status='resuming',updated_at=now() WHERE id=%s", (pending_id,))
    client = client_for_user()
    from agent.service import stream_chat
    next_id = str(uuid.uuid4())
    try:
        stream_chat(row['session_id'], '', owner_id=user_id(), api_key=client.api_key, role=g.user['role'],
                    run_id=next_id, decisions=[{'type': body['decision']} for _ in range(count)])
    except Exception:
        with connection() as conn:
            conn.execute("UPDATE agent_runs SET status='waiting' WHERE id=%s", (pending_id,))
        raise
    from psycopg.types.json import Jsonb
    with connection() as conn:
        pending = {**row['pending_json'], 'status': 'done', 'response': {'approved': body['decision'] == 'approve'}, 'resumed_run_id': next_id}
        conn.execute('UPDATE agent_runs SET pending_json=%s WHERE id=%s', (Jsonb(pending), pending_id))
    return jsonify(success=True, resumed=True)


@agent_bp.route('/api/v1/sessions/continue-stream')
@agent_bp.route('/api/v1/sessions/continue-stream/<session_id>')
def continue_stream(session_id=None):
    run_id = request.args.get('message_id') or request.args.get('query')
    with connection() as conn:
        row = conn.execute('SELECT * FROM agent_runs WHERE id=%s AND owner_id=%s', (run_id, user_id())).fetchone()
    if row is None or (session_id and row['session_id'] != session_id):
        raise StoreError('执行记录不存在', 404)
    message_id=row['id']
    resume_pending_id=request.args.get('resume_pending_id','')
    seen={run_id}
    while row['pending_json'] and row['pending_json'].get('resumed_run_id'):
        run_id=row['pending_json']['resumed_run_id']
        if run_id in seen:raise StoreError('执行恢复链异常',409)
        seen.add(run_id)
        with connection() as conn:
            row=conn.execute('SELECT * FROM agent_runs WHERE id=%s AND owner_id=%s',(run_id,user_id())).fetchone()
        if row is None:raise StoreError('后续执行记录缺失',409)
    owner = user_id()
    def generate():
        while True:
            with connection() as conn:
                run = conn.execute('SELECT * FROM agent_runs WHERE id=%s AND owner_id=%s', (run_id, owner)).fetchone()
            if run is None:
                break
            if run['status'] == 'running':
                agent_sessions.get_session(run['session_id'], owner)
            if run['status'] != 'running':
                replay = [
                    {'response_type':'agent_query','id':message_id,'assistant_message_id':message_id,'data':{'resume_pending_id':resume_pending_id}},
                    {'response_type': 'answer', 'id': message_id, 'content': run['answer'], 'data': {'event_id': run_id, 'replace': True}},
                    {'response_type': 'references', 'id': message_id, 'data': {'references': run['references_json']}},
                    {'response_type': 'complete', 'id': message_id, 'done': True},
                ]
                for step in run['steps_json']:
                    for call in step.get('tool_calls', []):
                        replay.insert(-1, {'response_type': 'tool_call', 'id': message_id,
                            'data': {'tool_call_id': call['id'], 'tool_name': call['name'],
                                     'arguments': call.get('arguments')}})
                        if 'result' in call:
                            replay.insert(-1, {'response_type': 'tool_result', 'id': message_id,
                                'data': {'tool_call_id': call['id'], 'tool_name': call['name'], **call['result']}})
                if run['pending_json'] and run['status']=='waiting':
                    pending=run['pending_json'];req=pending['request']
                    replay.insert(-1,{'response_type':'tool_approval_required','id':message_id,'data':{'pending_id':run_id,'service_name':'ContextDB','mcp_tool_name':req['mcp_tool_name'],'args_json':json.dumps(req['args'],ensure_ascii=False),'suspendable':True}})
                    replay.insert(-1,{'response_type':'run_suspended','id':message_id,'data':{'pending_id':run_id}})
                if run['status'] in ('failed','interrupted'):
                    replay[-1]={'response_type':'error','id':message_id,'content':run['error'],'done':True}
                elif run['status'] == 'cancelled':
                    replay[-1]={'response_type':'stop','id':message_id,'done':True}
                for event in replay:
                    yield 'data: ' + json.dumps(event, ensure_ascii=False) + '\n\n'
                break
            yield 'data: ' + json.dumps({'response_type': 'heartbeat', 'id': run_id}) + '\n\n'
            time.sleep(1)
    return Response(stream_with_context(generate()), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
