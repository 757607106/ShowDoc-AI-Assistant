"""Original Agent sharing API, backed by native ContextDB groups and platform Agent grants."""
from flask import Blueprint, g, jsonify, request
from psycopg.types.json import Jsonb

from agent import registry, sharing
from agent.config import load_agent
from governance.database import connection
from governance.store import StoreError
from webapi.auth import client_for_user

sharing_bp = Blueprint('sharing', __name__)


def _body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise StoreError('请求必须为 JSON 对象', 400)
    return body


@sharing_bp.route('/api/v1/organizations', methods=['GET', 'POST'])
def organizations():
    actor = g.user['id']
    if request.method == 'POST':
        value = client_for_user()._request('POST', '/v1/workspaces/groups', json_body={'name': _body().get('name')})
        return jsonify(success=True, data=sharing.group(actor, str(value['group_id']))), 201
    return jsonify(success=True, data=sharing.groups(actor))


@sharing_bp.get('/api/v1/organizations/<group_id>')
def organization(group_id):
    return jsonify(success=True, data=sharing.group(g.user['id'], group_id))


@sharing_bp.route('/api/v1/agents/<agent_id>/shares', methods=['GET', 'POST'])
@sharing_bp.route('/api/v1/agents/<agent_id>/shares/<share_id>', methods=['PUT', 'DELETE'])
def shares(agent_id, share_id=None):
    actor = g.user['id']
    agent = load_agent(agent_id, actor)
    if agent['is_builtin']:
        raise StoreError('请复制内置 Agent 后共享', 400)
    values = [item for item in registry.records('agent_share', actor) if item['agent_id'] == agent_id]
    if request.method == 'GET':
        return jsonify(success=True, data={'shares': values, 'total': len(values)})
    if request.method == 'POST':
        body = _body()
        target = sharing.group(actor, str(body.get('organization_id', '')), edit=True)
        if any(item['organization_id'] == target['id'] for item in values):
            raise StoreError('此 Agent 已共享至该用户组', 409)
        value = {'agent_id': agent_id, 'agent_name': agent['name'], 'organization_id': target['id'],
            'organization_name': target['name'], 'shared_by_user_id': actor, 'source_tenant_id': 1}
    else:
        value = next((item for item in values if item['id'] == share_id), None)
        if value is None:
            raise StoreError('共享记录不存在', 404)
        if request.method == 'DELETE':
            registry.delete_record('agent_share', share_id, actor)
            return jsonify(success=True)
        body = _body()
    # A shared Agent delegates use; editing its source configuration remains an owner operation.
    permission = body.get('permission', 'viewer')
    if permission not in ('viewer', 'editor', 'admin'):
        raise StoreError('共享权限无效', 400)
    value['permission'] = permission
    return jsonify(success=True, data=registry.save_record('agent_share', value, actor))


@sharing_bp.get('/api/v1/shared-agents')
@sharing_bp.get('/api/v1/organizations/<group_id>/shared-agents')
@sharing_bp.get('/api/v1/organizations/<group_id>/agent-shares')
def shared_agents(group_id=None):
    if group_id:
        sharing.group(g.user['id'], group_id)
    values = sharing.shared_agents(g.user['id'], group_id)
    for value in values:
        value.pop('_resource_owner_id', None)
    if request.path.endswith('/agent-shares'):
        values = [share for _, share in sharing._shares() if share['organization_id'] == str(group_id)]
    return jsonify(success=True, data=values)


@sharing_bp.post('/api/v1/shared-agents/disabled')
def disable_agent():
    body, actor = _body(), g.user['id']
    agent_id = body.get('agent_id')
    if not isinstance(agent_id, str) or not isinstance(body.get('disabled'), bool):
        raise StoreError('agent_id 或 disabled 无效', 400)
    sharing.resource_owner(agent_id, actor)
    with connection() as conn:
        row = conn.execute('SELECT preferences FROM platform_users WHERE id=%s FOR UPDATE', (actor,)).fetchone()
        preferences = row['preferences'] or {}
        disabled = set(preferences.get('disabled_agent_ids', []))
        disabled.add(agent_id) if body['disabled'] else disabled.discard(agent_id)
        preferences['disabled_agent_ids'] = sorted(disabled)
        conn.execute('UPDATE platform_users SET preferences=%s WHERE id=%s', (Jsonb(preferences), actor))
    return jsonify(success=True)


@sharing_bp.get('/api/v1/agents/<agent_id>/knowledge-bases')
def agent_bases(agent_id):
    actor = g.user['id']
    owner = sharing.resource_owner(agent_id, actor)
    config, client = load_agent(agent_id, owner)['config'], client_for_user()
    bases = list(sharing._pages(client, '/v1/knowledge-bases', 'knowledge_bases'))
    mode = config['kb_selection_mode']
    return jsonify(success=True, data=[item for item in bases if mode == 'all' or
        mode == 'selected' and item.get('id', item.get('knowledge_base_id')) in config['knowledge_bases']])


@sharing_bp.get('/api/v1/shared-knowledge-bases')
def shared_bases():
    # ContextDB returns every readable KB through its normal list, including group grants.
    return jsonify(success=True, data=[])
