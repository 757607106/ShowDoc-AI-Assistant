"""Platform login and ContextDB member bindings; ContextDB enforces knowledge ACLs."""
import argparse
import os
import re
import secrets
import unicodedata
import uuid

from cryptography.fernet import Fernet
from flask import Blueprint, current_app, g, has_request_context, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from governance.database import connection, initialize
from governance.store import StoreError
from integrations.contextdb import ContextDBClient

auth_bp = Blueprint('auth', __name__)
DEFAULT_BROWSER_SEARCH_INSTRUCTIONS = 'Default search engine: Bing.\nSearch URL: https://www.bing.com/search?q={query}'
PUBLIC_PATHS = {
    '/api/health', '/api/v1/auth/login', '/api/v1/auth/refresh',
    '/api/v1/auth/auto-setup', '/api/v1/auth/oidc/config',
    '/api/v1/auth/registration-config',
    '/api/v1/auth/config',
    '/api/v1/mcp-oauth/callback',
}


def cipher():
    key = os.getenv('CREDENTIAL_ENCRYPTION_KEY', '')
    if not key:
        raise StoreError('CREDENTIAL_ENCRYPTION_KEY 未配置', 503)
    return Fernet(key.encode())


def user_id():
    return g.user['id'] if has_request_context() and getattr(g, 'user', None) else None


def client_for_user(owner_id=None):
    owner_id = owner_id or user_id()
    if not owner_id:
        raise StoreError('请先登录', 401)
    with connection() as conn:
        row = conn.execute('SELECT contextdb_key_encrypted FROM platform_users WHERE id = %s AND active', (owner_id,)).fetchone()
    if row is None or not row['contextdb_key_encrypted']:
        raise StoreError('请由管理员绑定该账号的 ContextDB 成员凭据', 503)
    return ContextDBClient(api_key=cipher().decrypt(row['contextdb_key_encrypted'].encode()).decode())


def normalize_account(value):
    if not isinstance(value, str):
        raise StoreError('账号须为 1 至 255 字文本，不能包含空白或控制字符', 400)
    account = value.strip().lower()
    if (not account or len(account) > 255 or
            any(char.isspace() or unicodedata.category(char).startswith('C') for char in account)):
        raise StoreError('账号须为 1 至 255 字文本，不能包含空白或控制字符', 400)
    return account


def create_user(account, username, password, role='viewer', api_key=None):
    if role not in ('admin', 'editor', 'viewer') or not isinstance(password, str) or not 8 <= len(password) <= 1024:
        raise StoreError('角色无效或密码长度不在 8 至 1024 位之间', 400)
    account = normalize_account(account)
    if not isinstance(username, str) or not username.strip():
        raise StoreError('请提供有效显示名称', 400)
    member_id = encrypted = None
    if api_key:
        profile = ContextDBClient(api_key=api_key).current_permissions()
        member_id = profile['member']['member_id']
        encrypted = cipher().encrypt(api_key.encode()).decode()
    uid = str(uuid.uuid4())
    from psycopg.errors import UniqueViolation
    try:
        with connection() as conn:
            # Retain the unique legacy column for existing users and WeKnora clients.
            conn.execute('INSERT INTO platform_users(id,email,username,password_hash,role,contextdb_member_id,contextdb_key_encrypted) VALUES (%s,%s,%s,%s,%s,%s,%s)',
                         (uid, account, username.strip(), generate_password_hash(password), role, member_id, encrypted))
    except UniqueViolation as exc:
        raise StoreError('账号或 ContextDB 成员已绑定其他平台账号', 409) from exc
    return uid


def validate_access_token(token, *, secret_key=None):
    """Validate the same platform session from Flask or an ASGI request."""
    secret_key = secret_key or os.getenv('FLASK_SECRET_KEY')
    if not secret_key:
        raise StoreError('FLASK_SECRET_KEY 未配置', 503)
    try:
        claims = URLSafeTimedSerializer(secret_key, salt='platform-access').loads(token, max_age=8 * 3600)
    except (BadSignature, SignatureExpired, TypeError):
        raise StoreError('登录已失效，请重新登录', 401) from None
    if not isinstance(claims, dict) or not isinstance(claims.get('session'), str) or not claims['session']:
        raise StoreError('登录已失效，请重新登录', 401)
    with connection() as conn:
        row = conn.execute('SELECT u.* FROM platform_users u JOIN platform_tokens t ON t.owner_id=u.id WHERE t.id=%s AND t.expires_at>now() AND u.active', (claims['session'],)).fetchone()
    if row is None:
        raise StoreError('登录已失效，请重新登录', 401)
    return row, claims['session']


def require_login():
    if not request.path.startswith(('/api', '/entries', '/tasks', '/task_status', '/download', '/showdoc')):
        return None
    if request.path in PUBLIC_PATHS:
        return None
    token = request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
    row, session_id = validate_access_token(token, secret_key=current_app.secret_key)
    g.user = row
    g.auth_session = session_id
    if request.path.startswith('/showdoc/') and row['role'] != 'admin':
        raise StoreError('服务器 ShowDoc 登录凭据仅限平台管理员使用；采集可传入自己的 user_token', 403)
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and row['role'] == 'viewer' and not request.path.startswith(('/api/v1/auth/', '/api/v1/user/favorites')):
        read_posts = ('/search', '/chat', '/query', '/load')
        batch_download = request.method == 'POST' and re.fullmatch(r'/api/v1/knowledge-bases/[^/]+/knowledge/batch-download', request.path)
        revoke_grant = request.method == 'DELETE' and request.path.startswith('/api/v1/agent/grants/')
        personal = request.path.startswith(('/api/v1/me/env-vars/', '/api/v1/memory/', '/api/v1/agent/mcp-oauth-resolutions/'))
        oauth = bool(re.fullmatch(r'/api/v1/mcp-services/[^/]+/oauth/(authorize-url|token)', request.path))
        metadata = re.fullmatch(r'/api/v1/mcp-services/([^/]+)/metadata/refresh', request.path)
        if metadata and request.method == 'POST':
            from agent.registry import record
            oauth = record('mcp', metadata[1], row['id']).get('auth_config', {}).get('auth_type') == 'oauth'
        if not batch_download and not revoke_grant and not personal and not oauth and not request.path.endswith(read_posts) and '/sessions' not in request.path and not request.path.startswith(('/api/v1/agent-chat/', '/api/v1/knowledge-chat/', '/api/v1/agent/prompts/', '/api/v1/agent/tool-approvals/')):
            raise StoreError('当前账号为只读账号', 403)
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        with connection() as conn:
            g.audit_id = conn.execute('INSERT INTO platform_audit(owner_id,action,resource_id,request_id,outcome) VALUES (%s,%s,%s,%s,%s) RETURNING id',
                (row['id'], request.method, request.path, request.headers.get('X-Request-ID', '')[:100], 'in_progress')).fetchone()['id']
    return None


def finish_audit(response):
    if getattr(g, 'audit_id', None):
        from psycopg import Error
        try:
            with connection() as conn:
                conn.execute('UPDATE platform_audit SET outcome=%s WHERE id=%s', (str(response.status_code), g.audit_id))
        except Error:
            current_app.logger.error('Unable to finalize platform audit %s', g.audit_id)
            response.headers['X-Audit-Status'] = 'pending'
    return response


def _identity(row):
    role = {'admin': 'owner', 'editor': 'contributor', 'viewer': 'viewer'}[row['role']]
    user = {k: row[k] for k in ('id', 'email', 'username', 'active', 'created_at', 'updated_at')}
    user.update(account=row['email'], tenant_id=1, is_active=row['active'], is_system_admin=False, preferences=row.get('preferences', {}))
    tenant = {'id': 1, 'name': os.getenv('PLATFORM_NAME', '企业知识库'), 'status': 'active',
              'owner_id': row['id'] if row['role'] == 'admin' else '', 'created_at': row['created_at'], 'updated_at': row['updated_at']}
    return {'user': user, 'tenant': tenant, 'memberships': [{'tenant_id': 1, 'tenant_name': tenant['name'], 'role': role}],
            'capabilities': {'can_create_tenant': False, 'auto_accept_invitation': False}, 'tenant_required': False}


def _issue(row, existing_session=None):
    sid = existing_session or secrets.token_urlsafe(32)
    with connection() as conn:
        conn.execute('INSERT INTO platform_tokens(id, owner_id) VALUES (%s,%s) ON CONFLICT (id) DO UPDATE SET expires_at=now()+interval \'30 days\'', (sid, row['id']))
    access = URLSafeTimedSerializer(current_app.secret_key, salt='platform-access').dumps({'session': sid})
    refresh = URLSafeTimedSerializer(current_app.secret_key, salt='platform-refresh').dumps({'session': sid})
    return jsonify(success=True, **_identity(row), token=access, access_token=access, refresh_token=refresh)


@auth_bp.route('/api/v1/auth/login', methods=['POST'])
def login():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise StoreError('请求必须是 JSON 对象', 400)
    try:
        account = normalize_account(body.get('account', body.get('email', '')))
    except StoreError:
        raise StoreError('账号或密码错误', 401) from None
    password = body.get('password')
    if not isinstance(password, str) or not password or len(password) > 1024:
        raise StoreError('账号或密码错误', 401)
    with connection() as conn:
        row = conn.execute('SELECT * FROM platform_users WHERE email=%s AND active', (account,)).fetchone()
    if row is None or not check_password_hash(row['password_hash'], password):
        raise StoreError('账号或密码错误', 401)
    return _issue(row)


@auth_bp.route('/api/v1/auth/me')
def me():
    return jsonify(success=True, data={**_identity(g.user),
        'preference_defaults': {'browser_search_instructions': DEFAULT_BROWSER_SEARCH_INSTRUCTIONS}})


@auth_bp.route('/api/v1/auth/logout', methods=['POST'])
def logout():
    with connection() as conn:
        conn.execute('DELETE FROM platform_tokens WHERE id=%s', (g.auth_session,))
    return jsonify(success=True)


@auth_bp.post('/api/v1/auth/change-password')
def change_password():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise StoreError('请求必须是 JSON 对象', 400)
    password = body.get('new_password')
    if not isinstance(password, str) or not 8 <= len(password) <= 1024:
        raise StoreError('新密码长度须为 8 至 1024 位', 400)
    old_password = body.get('old_password')
    if not isinstance(old_password, str) or len(old_password) > 1024:
        raise StoreError('当前密码错误', 400)
    with connection() as conn:
        row = conn.execute('SELECT password_hash FROM platform_users WHERE id=%s FOR UPDATE', (g.user['id'],)).fetchone()
        if not check_password_hash(row['password_hash'], old_password):
            raise StoreError('当前密码错误', 400)
        conn.execute('UPDATE platform_users SET password_hash=%s,updated_at=now() WHERE id=%s',
                     (generate_password_hash(password), g.user['id']))
        conn.execute('DELETE FROM platform_tokens WHERE owner_id=%s', (g.user['id'],))
    return jsonify(success=True)


@auth_bp.route('/api/v1/auth/refresh', methods=['POST'])
def refresh():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise StoreError('请求必须是 JSON 对象', 400)
    token = body.get('refreshToken', body.get('refresh_token', ''))
    if not isinstance(token, str) or not token.strip():
        raise StoreError('登录已失效，请重新登录', 401)
    try:
        claims = URLSafeTimedSerializer(current_app.secret_key, salt='platform-refresh').loads(
            token, max_age=30 * 86400)
    except (BadSignature, SignatureExpired):
        raise StoreError('登录已失效，请重新登录', 401)
    with connection() as conn:
        row = conn.execute('SELECT u.* FROM platform_users u JOIN platform_tokens t ON t.owner_id=u.id WHERE t.id=%s AND t.expires_at>now() AND u.active', (claims['session'],)).fetchone()
    if row is None:
        raise StoreError('登录已失效，请重新登录', 401)
    return _issue(row, claims['session'])


@auth_bp.route('/api/v1/auth/auto-setup', methods=['GET', 'POST'])
def auto_setup():
    return jsonify(success=False, message='请使用平台账号登录', lite_mode=False), 401


@auth_bp.route('/api/v1/auth/oidc/config')
def oidc_config():
    return jsonify(success=True, enabled=False)


@auth_bp.route('/api/v1/auth/registration-config')
@auth_bp.route('/api/v1/auth/config')
def registration_config():
    return jsonify(success=True, enabled=False, registration_mode='invite_only', disable_registration=True, complex_password_enabled=False)


@auth_bp.route('/api/platform/users', methods=['GET', 'POST'])
def users():
    if g.user['role'] != 'admin':
        raise StoreError('需要平台管理员权限', 403)
    if request.method == 'POST':
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            raise StoreError('请求必须是 JSON 对象', 400)
        uid = create_user(body.get('account', body.get('email', '')), body.get('username', ''), body.get('password', ''),
                          body.get('role', 'viewer'), body.get('contextdb_api_key'))
        return jsonify(success=True, id=uid), 201
    with connection() as conn:
        rows = conn.execute('SELECT id,email AS account,email,username,role,contextdb_member_id,active,created_at FROM platform_users ORDER BY created_at').fetchall()
    return jsonify(success=True, users=rows)


@auth_bp.route('/api/v1/auth/me/preferences', methods=['PUT'])
def preferences():
    from psycopg.types.json import Jsonb
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or len(str(body)) > 32000:
        raise StoreError('偏好设置格式或大小无效', 400)
    if 'browser_search_instructions' in body:
        value = body['browser_search_instructions']
        if value is None:
            body.pop('browser_search_instructions')
        else:
            if not isinstance(value, str) or len(value) > 4000:
                raise StoreError('浏览器搜索指令须为不超过 4000 字符的文本', 400)
            value = value.strip()
            body['browser_search_instructions'] = None if not value or value == DEFAULT_BROWSER_SEARCH_INSTRUCTIONS else value
    with connection() as conn:
        row = conn.execute('UPDATE platform_users SET preferences=preferences || %s,updated_at=now() WHERE id=%s RETURNING preferences', (Jsonb(body), user_id())).fetchone()
    return jsonify(success=True, data=row['preferences'])


@auth_bp.route('/api/platform/users/<uid>', methods=['PATCH'])
def update_user(uid):
    if g.user['role'] != 'admin':
        raise StoreError('需要平台管理员权限', 403)
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise StoreError('请求必须是 JSON 对象', 400)
    fields = {}
    if 'role' in body:
        if body['role'] not in ('admin', 'editor', 'viewer'):
            raise StoreError('角色无效', 400)
        fields['role'] = body['role']
    if 'active' in body:
        if not isinstance(body['active'], bool):
            raise StoreError('active 必须为布尔值', 400)
        fields['active'] = body['active']
    if uid == user_id() and (fields.get('role', 'admin') != 'admin' or fields.get('active') is False):
        raise StoreError('不能撤销当前管理员自己的权限', 409)
    if 'password' in body and body['password'] not in (None, ''):
        if not isinstance(body['password'], str) or not 8 <= len(body['password']) <= 1024:
            raise StoreError('密码长度须为 8 至 1024 位', 400)
        fields['password_hash'] = generate_password_hash(body['password'])
    if body.get('contextdb_api_key'):
        key = str(body['contextdb_api_key'])
        profile = ContextDBClient(api_key=key).current_permissions()
        fields['contextdb_member_id'] = profile['member']['member_id']
        fields['contextdb_key_encrypted'] = cipher().encrypt(key.encode()).decode()
    if not fields:
        raise StoreError('没有可更新的账号字段', 400)
    from psycopg.errors import UniqueViolation
    try:
        with connection() as conn:
            row = conn.execute('UPDATE platform_users SET '+','.join(f'{k}=%s' for k in fields)+' ,updated_at=now() WHERE id=%s RETURNING id', (*fields.values(), uid)).fetchone()
            if row is None:
                raise StoreError('账号不存在', 404)
            conn.execute('DELETE FROM platform_tokens WHERE owner_id=%s', (uid,))
    except UniqueViolation as exc:
        raise StoreError('该 ContextDB 成员已被其他账号绑定', 409) from exc
    return jsonify(success=True)


def main():
    from dotenv import load_dotenv
    load_dotenv()
    from common.env_sanitize import sanitize_no_proxy
    sanitize_no_proxy()
    parser = argparse.ArgumentParser(description='创建平台账号；凭据通过环境变量提供')
    parser.add_argument('--bootstrap', action='store_true')
    args = parser.parse_args()
    initialize()
    if args.bootstrap:
        with connection() as conn:
            if conn.execute('SELECT 1 FROM platform_users LIMIT 1').fetchone():
                print('平台账号已存在，未修改现有账号。')
                return
        account = os.getenv('PLATFORM_ADMIN_ACCOUNT') or os.getenv('PLATFORM_ADMIN_EMAIL') or 'admin'
        password = os.getenv('PLATFORM_ADMIN_PASSWORD', 'admin123')
        create_user(account, '管理员', password, 'admin', os.getenv('CONTEXTDB_API_KEY'))
        print('平台管理员已创建，账号和密码请以本机配置为准。')


if __name__ == '__main__':
    main()
