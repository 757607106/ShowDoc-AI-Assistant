"""Deployment and identity presentation for the reused WeKnora UI."""
import os

from flask import Blueprint, g, jsonify, request

from governance.database import connection
from webapi.auth import _identity
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


@platform_bp.route('/api/v1/tenants')
@platform_bp.route('/api/v1/tenants/all')
@platform_bp.route('/api/v1/tenants/search')
def tenants():
    return jsonify(success=True, data=[_identity(g.user)['tenant']])


@platform_bp.route('/api/v1/tenants/1')
def tenant():
    return jsonify(success=True, data=_identity(g.user)['tenant'])


@platform_bp.route('/api/v1/user/favorites', methods=['GET', 'POST'])
@platform_bp.route('/api/v1/user/favorites/<kind>/<resource_id>', methods=['DELETE'])
def favorites(kind=None, resource_id=None):
    body = request.get_json(silent=True) or {}
    kind = kind or request.args.get('type') or body.get('type')
    resource_id = resource_id or body.get('id')
    if kind not in ('kb', 'agent') or (request.method != 'GET' and (not isinstance(resource_id, str) or len(resource_id) > 200)):
        raise StoreError('收藏参数无效', 400)
    with connection() as conn:
        row = conn.execute('SELECT preferences FROM platform_users WHERE id=%s FOR UPDATE', (g.user['id'],)).fetchone()
        items = row['preferences'].get('favorites', [])
        if request.method != 'GET':
            items = [x for x in items if not (x['resource_type'] == kind and x['resource_id'] == resource_id)]
            if request.method == 'POST':
                items.append({'user_id': g.user['id'], 'tenant_id': 1, 'resource_type': kind,
                              'resource_id': resource_id, 'created_at': datetime.now(timezone.utc).isoformat()})
            conn.execute('UPDATE platform_users SET preferences=jsonb_set(preferences,\'{favorites}\',%s) WHERE id=%s', (Jsonb(items), g.user['id']))
    return jsonify(success=True, data=[x for x in items if x['resource_type'] == kind])
