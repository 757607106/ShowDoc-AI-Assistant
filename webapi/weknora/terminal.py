"""One-use tickets for the upstream WeKnora terminal protocol adapter."""
import os
import secrets

from flask import Blueprint, g, jsonify
from itsdangerous import URLSafeTimedSerializer

from agent import registry, sessions
from governance.store import StoreError

terminal_bp = Blueprint('terminal', __name__)


@terminal_bp.post('/api/v1/sessions/<session_id>/sandbox/terminal-ticket')
def terminal_ticket(session_id):
    selected = sessions.get_session(session_id, g.user['id'])
    if selected['agent_config'].get('runtime') != 'deepagents':
        raise StoreError('旧会话只读，请新建官方 Deep Agents 会话', 410)
    if g.user['role'] == 'viewer':
        raise StoreError('只读账号不能打开执行终端', 403)
    nonce = secrets.token_urlsafe(24)
    from governance.database import connection
    with connection() as conn:
        conn.execute("DELETE FROM runtime_records WHERE owner_id=%s AND kind='sandbox-terminal-ticket' AND created_at<now()-interval '2 minutes'", (g.user['id'],))
    claims = {'id': nonce, 'owner_id': g.user['id'], 'session_id': session_id, 'auth_session': g.auth_session}
    registry.save_record('sandbox-terminal-ticket', claims, g.user['id'])
    ticket = URLSafeTimedSerializer(os.environ['FLASK_SECRET_KEY'], salt='sandbox-terminal').dumps(claims)
    return jsonify(success=True, data={'ticket': ticket})
