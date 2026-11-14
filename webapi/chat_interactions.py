"""Read-only legacy interaction records; execution belongs to the native Harness."""
from flask import Blueprint, jsonify, request

from agent import registry, sessions
from governance.database import connection
from governance.store import StoreError
from webapi.auth import user_id
from webapi.legacy_runtime import unavailable

chat_interactions_bp = Blueprint('chat_interactions', __name__)


@chat_interactions_bp.route('/api/v1/agent/grants')
def grants():
    sid = request.args.get('session_id')
    sessions.get_session(sid)
    return jsonify(success=True, read_only=True, data=[{key: item.get(key) for key in ('id', 'scope', 'scope_id', 'grant_key', 'label', 'created_at')}
        for item in registry.records('agent_grant', user_id()) if item.get('scope_id') == sid])


@chat_interactions_bp.route('/api/v1/agent/grants/<grant_id>', methods=['DELETE'])
def revoke_grant(grant_id):
    unavailable()


@chat_interactions_bp.route('/api/v1/sessions/<sid>/steer', methods=['GET', 'POST'])
def steers(sid):
    if request.method == 'POST':
        unavailable(sid)
    sessions.get_session(sid)
    with connection() as conn:
        rows = conn.execute("SELECT id AS steer_id,content,delivery,mentioned_items,run_id AS expected_assistant_message_id,created_at FROM agent_steers WHERE session_id=%s AND owner_id=%s AND status='queued' ORDER BY created_at,id", (sid, user_id())).fetchall()
    return jsonify(success=True, read_only=True, data=rows)


@chat_interactions_bp.route('/api/v1/sessions/<sid>/steer/<steer_id>', methods=['DELETE'])
@chat_interactions_bp.route('/api/v1/sessions/<sid>/steer/<steer_id>/inject', methods=['POST'])
@chat_interactions_bp.route('/api/v1/sessions/<sid>/fork', methods=['POST'])
@chat_interactions_bp.route('/api/v1/sessions/<sid>/rewind', methods=['POST'])
@chat_interactions_bp.route('/api/v1/sessions/<sid>/background-work/<work_id>/cancel', methods=['POST'])
def retired_interaction(sid, steer_id=None, work_id=None):
    unavailable(sid)


def _background(sid, work_id=None):
    sessions.get_session(sid)
    with connection() as conn:
        rows = conn.execute('''SELECT r.*,s.title FROM agent_runs r JOIN agent_sessions s ON s.id=r.session_id
            WHERE s.parent_session_id=%s AND r.owner_id=%s AND (%s::text IS NULL OR r.id=%s)
            ORDER BY r.created_at,r.id''', (sid, user_id(), work_id, work_id)).fetchall()
    states = {'completed': 'succeeded', 'succeeded': 'succeeded', 'failed': 'failed',
              'timed_out': 'failed', 'cancelled': 'cancelled'}
    items = [{**row, 'work_id': row['id'], 'kind': 'subagent', 'state': states.get(row['status'], 'lost'),
              'saved_status': row['status'], 'started_at': row['created_at'].isoformat(),
              'finished_at': row['updated_at'].isoformat() if row['status'] in states else None} for row in rows]
    for job in registry.records('sandbox_job', user_id()):
        if job.get('session_id') != sid or (work_id and job['id'] != work_id):
            continue
        items.append({**job, 'work_id': job['id'], 'kind': 'shell', 'title': job.get('command', ''),
            'saved_status': job.get('status'), 'state': states.get(job.get('status'), 'lost'),
            'started_at': job['created_at'], 'finished_at': job.get('finished_at')})
    return sorted(items, key=lambda item: item['started_at'])


@chat_interactions_bp.route('/api/v1/sessions/<sid>/background-work')
def background(sid):
    return jsonify(success=True, read_only=True, data=[{key: item.get(key) for key in
        ('work_id', 'kind', 'title', 'state', 'saved_status', 'started_at', 'finished_at')} for item in _background(sid)])


@chat_interactions_bp.route('/api/v1/sessions/<sid>/background-work/<work_id>')
def background_detail(sid, work_id):
    rows = _background(sid, work_id)
    if not rows:
        raise StoreError('后台任务不存在', 404)
    item = rows[0]
    result = {'display_type': item['kind'], 'work_id': work_id, 'state': item['state'],
              'session_id': item['session_id'], 'read_only': True}
    if item['kind'] == 'shell':
        result.update(command=item.get('command', ''), output_available=False,
                      note='旧命令执行器已停用，仅展示已存任务记录；未读取或启动沙箱。')
    else:
        result.update(output=item['answer'], error=item['error'])
    return jsonify(success=True, read_only=True, data={'work_id': work_id, 'title': item['title'],
        'state': item['state'], 'saved_status': item['saved_status'], 'result': result})
