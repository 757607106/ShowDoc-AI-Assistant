"""Owner-scoped platform sessions; messages come from official checkpoints."""
import os
import uuid
from contextlib import contextmanager

import psycopg
from psycopg.types.json import Jsonb

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
    kind = (row.get('agent_config') or {}).get('_kind', '')
    state = {key: value for key, value in (row.get('agent_config') or {}).items()
             if key not in ('files', 'message_blocks', 'attachment_ids', 'user_images', 'attachments') and not key.startswith('_')}
    config = {key: value for key, value in (state.get('agent_config') or {}).items() if not key.startswith('_')}
    if 'agent_config' in state:
        state['agent_config'] = config
    last = {**state, 'model_id': config.get('model_id', state.get('model_id')),
            'reasoning_effort': config.get('reasoning_effort', ''),
            'web_search_enabled': config.get('web_search_enabled', False),
            'assistant_access': config.get('access_level', 'confirm'),
            'knowledge_base_ids': state.get('requested_knowledge_base_ids', row.get('knowledge_base_ids', []))}
    return {'id': row['id'], 'session_id': row['id'], 'title': row['title'],
            'created_at': row['created_at'].isoformat(), 'updated_at': row['updated_at'].isoformat(),
            'runtime': state.get('runtime', 'legacy'), 'read_only': state.get('runtime') != 'deepagents',
            'is_running': False, 'kind': kind, 'source': 'assistant' if kind == 'assistant' else 'web',
            'is_pinned': bool(row.get('pinned_at')), 'pinned_at': row['pinned_at'].isoformat() if row.get('pinned_at') else None,
            'agent_config': {**state, 'agent_enabled': state.get('agent_enabled', True),
                             'knowledge_base_ids': row.get('knowledge_base_ids', [])},
            'last_request_state': last}


def get_session(session_id, owner_id=None):
    with connection() as conn:
        row = conn.execute('SELECT * FROM agent_sessions WHERE id=%s AND owner_id=%s', (session_id, _owner(owner_id))).fetchone()
    if row is None:
        raise StoreError('会话不存在', 404)
    return row


def list_sessions(owner_id=None, source=None):
    with connection() as conn:
        rows = conn.execute("""SELECT * FROM agent_sessions WHERE owner_id=%s AND parent_session_id IS NULL
            AND coalesce(agent_config->>'_skill_install','false')<>'true'
            ORDER BY pinned_at DESC NULLS LAST,updated_at DESC,id""", (_owner(owner_id),)).fetchall()
    values = [_public(row) for row in rows]
    return [row for row in values if source is None or row['source'] == source]


def create_session(title='', owner_id=None, agent_config=None, kind=''):
    from psycopg.types.json import Jsonb
    if agent_config is not None and not isinstance(agent_config, dict):
        raise StoreError('agent_config 必须是对象', 400)
    if kind not in ('', 'assistant'):
        raise StoreError('会话类型无效', 400)
    config = {key: value for key, value in (agent_config or {}).items() if not key.startswith('_')}
    config['runtime'] = 'deepagents'
    if kind:
        config['_kind'] = kind
    sid = str(uuid.uuid4())
    with connection() as conn:
        row = conn.execute('INSERT INTO agent_sessions(id,owner_id,title,agent_config) VALUES (%s,%s,%s,%s) RETURNING *',
                           (sid, _owner(owner_id), str(title or '新会话')[:200], Jsonb(config))).fetchone()
    return _public(row)


def touch_session(session_id, title=None, owner_id=None):
    owner_id = _owner(owner_id)
    if get_session(session_id, owner_id)['agent_config'].get('runtime') != 'deepagents':
        raise StoreError('旧会话已归档为只读，历史数据与资源保留', 410)
    with connection() as conn:
        row = conn.execute('UPDATE agent_sessions SET title=coalesce(%s,title),updated_at=now() WHERE id=%s AND owner_id=%s RETURNING *',
                           (str(title)[:200] if title is not None else None, session_id, owner_id)).fetchone()
    if row is None:
        raise StoreError('会话不存在', 404)
    return _public(row)


@contextmanager
def _mutation(session_id, owner_id):
    get_session(session_id, owner_id)
    with psycopg.connect(os.environ['DATABASE_URL'], autocommit=True) as lock:
        acquired = lock.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0))', ('harness:' + session_id,)).fetchone()[0]
        if not acquired:
            raise StoreError('会话正在执行，请等待本次请求结束', 409)
        row = get_session(session_id, owner_id)
        if row['agent_config'].get('runtime') != 'deepagents':
            raise StoreError('旧会话已归档为只读，历史数据与资源保留', 410)
        yield row


def _clear_checkpoint(session_id, owner_id):
    from agent.checkpointer import make_checkpointer
    with make_checkpointer() as saver:
        saver.delete_thread(session_id)
    with connection() as conn:
        conn.execute("DELETE FROM runtime_records WHERE owner_id=%s AND kind='harness_resume' AND record_key=%s",
                     (owner_id, session_id))


def delete_session(session_id, owner_id=None):
    with _mutation(session_id, owner_id) as row:
        _clear_checkpoint(session_id, row['owner_id'])
        with connection() as conn:
            conn.execute('DELETE FROM agent_sessions WHERE id=%s AND owner_id=%s', (session_id, row['owner_id']))
    return True


def clear_session(session_id, owner_id=None):
    with _mutation(session_id, owner_id) as row:
        _clear_checkpoint(session_id, row['owner_id'])
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


def state_reader(saver):
    import asyncio
    from agent.graph import build_agent
    return asyncio.run(build_agent(saver, api_key='', owner_id='', load_tools=False))


def read_messages(session_id, limit=100, owner_id=None):
    get_session(session_id, owner_id)
    from agent.checkpointer import make_checkpointer
    with make_checkpointer() as saver:
        # Both messages and files use sparse DeltaChannels; hydrate via LangGraph.
        state = state_reader(saver).get_state({'configurable': {'thread_id': session_id}})
    messages = state.values.get('messages', [])
    return [item for item in (_serialize_message(m) for m in messages[-limit:]) if item]
