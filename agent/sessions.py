"""Owner-scoped platform sessions; messages come from official checkpoints."""
import uuid

from governance.database import connection
from governance.store import StoreError


def _owner(owner_id=None):
    if owner_id is None:
        from webapi.auth import user_id
        owner_id = user_id()
    if not owner_id:
        raise StoreError('请先登录', 401)
    return owner_id


def _public(row):
    return {'id': row['id'], 'session_id': row['id'], 'title': row['title'],
            'created_at': row['created_at'].isoformat(), 'updated_at': row['updated_at'].isoformat(),
            'is_running': bool(row['running_id']), 'kind': '', 'source': 'web',
            'is_pinned': bool(row.get('pinned_at')), 'pinned_at': row['pinned_at'].isoformat() if row.get('pinned_at') else None,
            'agent_config': {'agent_enabled':True, 'knowledge_base_ids':row.get('knowledge_base_ids', [])}}


def get_session(session_id, owner_id=None):
    with connection() as conn:
        row = conn.execute('SELECT * FROM agent_sessions WHERE id=%s AND owner_id=%s', (session_id, _owner(owner_id))).fetchone()
    if row and row['running_id']:
        with connection() as conn:
            abandoned = conn.execute("UPDATE agent_runs SET status='interrupted',error='运行进程已中断；保留 checkpoint，请查看记录后发起新会话',updated_at=now() WHERE id=%s AND status='running' AND updated_at<now()-interval '90 seconds' RETURNING id", (row['running_id'],)).fetchone()
            if abandoned:
                conn.execute('UPDATE agent_sessions SET running_id=NULL WHERE id=%s AND running_id=%s',(session_id,row['running_id']))
                row['running_id'] = None
    if row is None:
        raise StoreError('会话不存在', 404)
    return row


def list_sessions(owner_id=None):
    with connection() as conn:
        return [_public(row) for row in conn.execute('SELECT * FROM agent_sessions WHERE owner_id=%s ORDER BY pinned_at DESC NULLS LAST,updated_at DESC,id', (_owner(owner_id),))]


def create_session(title='', owner_id=None):
    sid = str(uuid.uuid4())
    with connection() as conn:
        row = conn.execute('INSERT INTO agent_sessions(id,owner_id,title) VALUES (%s,%s,%s) RETURNING *',
                           (sid, _owner(owner_id), str(title or '新会话')[:200])).fetchone()
    return _public(row)


def touch_session(session_id, title=None, owner_id=None):
    owner_id = _owner(owner_id)
    with connection() as conn:
        row = conn.execute('UPDATE agent_sessions SET title=coalesce(%s,title),updated_at=now() WHERE id=%s AND owner_id=%s RETURNING *',
                           (str(title)[:200] if title is not None else None, session_id, owner_id)).fetchone()
    if row is None:
        raise StoreError('会话不存在', 404)
    return _public(row)


def delete_session(session_id, owner_id=None):
    row = get_session(session_id, owner_id)
    if row['running_id']:
        raise StoreError('请先停止正在执行的会话', 409)
    from agent.checkpointer import make_checkpointer
    with make_checkpointer() as saver:
        saver.delete_thread(session_id)
    with connection() as conn:
        conn.execute('DELETE FROM agent_sessions WHERE id=%s AND owner_id=%s', (session_id, row['owner_id']))
    return True


def _serialize_message(message):
    data = message.model_dump() if hasattr(message, 'model_dump') else message
    if not isinstance(data, dict):
        return None
    content = data.get('content', '')
    if isinstance(content, list):
        content = ''.join(part.get('text', '') for part in content if isinstance(part, dict))
    return {'id': data.get('id'), 'role': data.get('type', data.get('role', 'unknown')),
            'content': str(content), 'name': data.get('name') or '',
            'tool_calls': data.get('tool_calls', []), 'tool_call_id': data.get('tool_call_id')}


def read_messages(session_id, limit=100, owner_id=None):
    get_session(session_id, owner_id)
    from agent.checkpointer import make_checkpointer
    with make_checkpointer() as saver:
        # Deepagents uses sparse DeltaChannel checkpoints; LangGraph hydrates them.
        from deepagents.graph import DeepAgentState
        from langgraph.graph import StateGraph, START, END
        reader = StateGraph(DeepAgentState)
        reader.add_node('read', lambda state: state)
        reader.add_edge(START, 'read')
        reader.add_edge('read', END)
        state = reader.compile(checkpointer=saver).get_state({'configurable': {'thread_id': session_id}})
    messages = state.values.get('messages', [])
    return [item for item in (_serialize_message(m) for m in messages[-limit:]) if item]
