"""Deployment and identity presentation for the reused WeKnora UI."""
import uuid

from flask import Blueprint, g, jsonify, request

from governance.database import connection
from governance.workspaces import create_workspace, current_workspace
from governance.store import StoreError
from psycopg.types.json import Jsonb
from datetime import datetime, timezone

platform_bp = Blueprint('platform', __name__)
DISABLED = ('organizations', 'integrations.im', 'integrations.embed', 'integrations.api',
            'integrations.mcpserver', 'settings.mcp', 'settings.assistant', 'settings.websearch', 'settings.vectorstore',
            'settings.storage', 'settings.sandbox', 'settings.sandbox.docker', 'settings.sandbox.host',
            'settings.sandbox.remote', 'settings.sandbox.user_allocation', 'agents.steering', 'agents.browser')


@platform_bp.route('/api/v1/system/capabilities')
def deployment_capabilities():
    values = {key: {'supported': False, 'reason': '当前平台未启用此功能'} for key in DISABLED}
    values['agents'] = {'supported': True}
    from agent.async_runtime import enabled
    values['agents.async'] = {'supported': enabled(), 'reason': '' if enabled() else '异步运行服务尚未部署启用'}
    for key in ('settings.mcp', 'settings.sandbox', 'settings.sandbox.state'):
        values[key] = {'supported': True}
    return jsonify(success=True, data={'edition': 'contextdb', 'capabilities': values})


@platform_bp.route('/api/v1/system/info')
def system_info():
    return jsonify(success=True, data={'version': '0.1.0', 'edition': 'contextdb',
                                       'vector_store_engine': 'ContextDB', 'keyword_index_engine': 'ContextDB',
                                       'graph_database_engine': 'ContextDB'})


@platform_bp.route('/api/v1/initialization/status')
def initialization_status():
    configured = bool(g.user.get('contextdb_key_encrypted'))
    return jsonify(success=True, data={'initialized': configured, 'is_initialized': configured,
                                       'need_initialization': not configured})


def _workspace_fields():
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not body or body.keys() - {'name', 'description'}:
        raise StoreError('仅支持修改空间名称和描述', 400)
    if 'name' in body and (not isinstance(body['name'], str) or not 1 <= len(body['name'].strip()) <= 64):
        raise StoreError('空间名称须为 1 至 64 个字符', 400)
    if 'description' in body and (not isinstance(body['description'], str) or len(body['description']) > 512):
        raise StoreError('空间描述最多 512 个字符', 400)
    return {key: value.strip() for key, value in body.items()}


@platform_bp.route('/api/v1/tenants', methods=['GET', 'POST'])
@platform_bp.route('/api/v1/tenants/all')
@platform_bp.route('/api/v1/tenants/search')
def tenants():
    account = g.user['account_id']
    with connection() as conn:
        if request.method == 'POST':
            body = _workspace_fields()
            if 'name' not in body:
                raise StoreError('请提供空间名称', 400)
            conn.execute('SELECT id FROM platform_users WHERE id=%s FOR UPDATE', (account,))
            if current_workspace(account, conn):
                raise StoreError('该账号已有个人空间', 409)
            create_workspace(conn, account, str(uuid.uuid4()), body['name'], body.get('description', ''))
            return jsonify(success=True, data=current_workspace(account, conn)), 201
        workspace = current_workspace(account, conn)
    items = [workspace] if workspace else []
    return jsonify(success=True, data={'items': items, 'total': len(items), 'page': 1, 'page_size': 1})


@platform_bp.route('/api/v1/tenants/<int:tenant_id>', methods=['GET', 'PUT', 'DELETE'])
def tenant(tenant_id):
    account = g.user['account_id']
    with connection() as conn:
        row = conn.execute("""SELECT principal_id FROM platform_workspaces
            WHERE id=%s AND account_id=%s AND deleted_at IS NULL FOR UPDATE""", (tenant_id, account)).fetchone()
        if row is None:
            raise StoreError('空间不存在', 404)
        if request.method == 'PUT':
            body = _workspace_fields()
            conn.execute("""UPDATE platform_workspaces SET name=COALESCE(%s,name),
                description=COALESCE(%s,description),updated_at=now() WHERE id=%s""",
                (body.get('name'), body.get('description'), tenant_id))
        elif request.method == 'DELETE':
            conn.execute('UPDATE platform_workspaces SET deleted_at=now() WHERE id=%s', (tenant_id,))
            conn.execute("""UPDATE runtime_records SET metadata=metadata || jsonb_build_object(
                'cancel_requested',true,'status',CASE WHEN metadata->>'status'='pending' THEN 'cancelled' ELSE 'cancelling' END)
                WHERE owner_id=%s AND kind='job' AND metadata->>'status' IN ('pending','running')""", (row['principal_id'],))
            # Knowledge favorites belong to the account. Personal agent favorites belong to this workspace.
            conn.execute("""UPDATE platform_users SET preferences=jsonb_set(preferences,'{favorites}',
                COALESCE((SELECT jsonb_agg(f) FROM jsonb_array_elements(preferences->'favorites') f
                          WHERE f->>'resource_type'='kb'),'[]')) WHERE id=%s AND preferences ? 'favorites'""", (account,))
            conn.execute('DELETE FROM platform_tokens WHERE owner_id=%s AND id<>%s', (account, g.auth_session))
            return jsonify(success=True)
        return jsonify(success=True, data=current_workspace(account, conn))


@platform_bp.get('/api/v1/tenants/<int:tenant_id>/members')
def workspace_members(tenant_id):
    if tenant_id != g.user['workspace_id']:
        raise StoreError('空间不存在', 404)
    with connection() as conn:
        workspace = current_workspace(g.user['account_id'], conn)
    if not workspace:
        raise StoreError('空间不存在', 404)
    member = {'user_id': workspace['owner_id'], 'email': g.user['email'], 'username': g.user['username'],
              'role': 'owner', 'status': 'active', 'joined_at': workspace['created_at']}
    return jsonify(success=True, data={'members': [member], 'total': 1})


@platform_bp.route('/api/v1/user/favorites', methods=['GET', 'POST'])
@platform_bp.route('/api/v1/user/favorites/<kind>/<resource_id>', methods=['DELETE'])
def favorites(kind=None, resource_id=None):
    body = request.get_json(silent=True) or {}
    kind = kind or request.args.get('type') or body.get('type')
    resource_id = resource_id or body.get('id')
    if kind not in ('kb', 'agent') or (request.method != 'GET' and (not isinstance(resource_id, str) or len(resource_id) > 200)):
        raise StoreError('收藏参数无效', 400)
    with connection() as conn:
        row = conn.execute('SELECT preferences FROM platform_users WHERE id=%s FOR UPDATE', (g.user['account_id'],)).fetchone()
        items = row['preferences'].get('favorites', [])
        if request.method != 'GET':
            items = [x for x in items if not (x['resource_type'] == kind and x['resource_id'] == resource_id)]
            if request.method == 'POST':
                items.append({'user_id': g.user['account_id'], 'tenant_id': g.user['workspace_id'], 'resource_type': kind,
                              'resource_id': resource_id, 'created_at': datetime.now(timezone.utc).isoformat()})
            conn.execute('UPDATE platform_users SET preferences=jsonb_set(preferences,\'{favorites}\',%s) WHERE id=%s', (Jsonb(items), g.user['account_id']))
    return jsonify(success=True, data=[x for x in items if x['resource_type'] == kind])
