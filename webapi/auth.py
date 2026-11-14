"""Platform login and ContextDB member bindings; ContextDB enforces knowledge ACLs."""
import argparse
import os
import re
import secrets
import uuid

from cryptography.fernet import Fernet
from flask import Blueprint, current_app, g, has_request_context, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from governance.database import connection, initialize
from governance.store import StoreError
from integrations.contextdb import ContextDBClient

auth_bp = Blueprint('auth', __name__)
PUBLIC_PATHS = {
    '/api/health', '/api/v1/auth/login', '/api/v1/auth/refresh',
    '/api/v1/auth/auto-setup', '/api/v1/auth/oidc/config',
    '/api/v1/auth/registration-config',
    '/api/v1/auth/config',
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


def create_user(email, username, password, role='viewer', api_key=None):
    if role not in ('admin', 'editor', 'viewer') or not isinstance(password, str) or len(password) < 12:
        raise StoreError('角色无效或密码不足 12 位', 400)
    email = str(email).strip().lower()
    if '@' not in email or len(email) > 255 or not str(username).strip():
        raise StoreError('请提供有效邮箱和用户名', 400)
    member_id = encrypted = None
    if api_key:
        profile = ContextDBClient(api_key=api_key).current_permissions()
        member_id = profile['member']['member_id']
        encrypted = cipher().encrypt(api_key.encode()).decode()
    uid = str(uuid.uuid4())
    from psycopg.errors import UniqueViolation
    try:
        with connection() as conn:
            conn.execute('INSERT INTO platform_users(id,email,username,password_hash,role,contextdb_member_id,contextdb_key_encrypted) VALUES (%s,%s,%s,%s,%s,%s,%s)',
                         (uid, email, username.strip(), generate_password_hash(password), role, member_id, encrypted))
    except UniqueViolation as exc:
        raise StoreError('邮箱或 ContextDB 成员已绑定其他平台账号', 409) from exc
    return uid


def require_login():
    if not request.path.startswith(('/api', '/entries', '/tasks', '/task_status', '/download', '/showdoc')):
        return None
    if request.path in PUBLIC_PATHS:
        return None
    token = request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
    try:
        claims = URLSafeTimedSerializer(current_app.secret_key, salt='platform-access').loads(token, max_age=8 * 3600)
    except (BadSignature, SignatureExpired):
        raise StoreError('登录已失效，请重新登录', 401)
    with connection() as conn:
        row = conn.execute('SELECT u.* FROM platform_users u JOIN platform_tokens t ON t.owner_id=u.id WHERE t.id=%s AND t.expires_at>now() AND u.active', (claims['session'],)).fetchone()
    if row is None:
        raise StoreError('登录已失效，请重新登录', 401)
    g.user = row
    g.auth_session = claims['session']
    if request.path.startswith('/showdoc/') and row['role'] != 'admin':
        raise StoreError('服务器 ShowDoc 登录凭据仅限平台管理员使用；采集可传入自己的 user_token', 403)
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and row['role'] == 'viewer' and not request.path.startswith(('/api/v1/auth/', '/api/v1/user/favorites')):
        read_posts = ('/search', '/chat', '/query', '/load')
        batch_download = request.method == 'POST' and re.fullmatch(r'/api/v1/knowledge-bases/[^/]+/knowledge/batch-download', request.path)
        if not batch_download and not request.path.endswith(read_posts) and '/sessions' not in request.path and not request.path.startswith(('/api/v1/agent-chat/', '/api/v1/knowledge-chat/')):
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
    user.update(tenant_id=1, is_active=row['active'], is_system_admin=False, preferences=row.get('preferences', {}))
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
    return jsonify(success=True, **_identity(row), token=access, refresh_token=refresh)


@auth_bp.route('/api/v1/auth/login', methods=['POST'])
def login():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise StoreError('请求必须是 JSON 对象', 400)
    with connection() as conn:
        row = conn.execute('SELECT * FROM platform_users WHERE email=%s AND active', (str(body.get('email', '')).strip().lower(),)).fetchone()
    if row is None or not check_password_hash(row['password_hash'], str(body.get('password', ''))):
        raise StoreError('邮箱或密码错误', 401)
    return _issue(row)


@auth_bp.route('/api/v1/auth/me')
def me():
    return jsonify(success=True, data=_identity(g.user))


@auth_bp.route('/api/v1/auth/logout', methods=['POST'])
def logout():
    with connection() as conn:
        conn.execute('DELETE FROM platform_tokens WHERE id=%s', (g.auth_session,))
    return jsonify(success=True)


@auth_bp.route('/api/v1/auth/refresh', methods=['POST'])
def refresh():
    body = request.get_json(silent=True) or {}
    try:
        claims = URLSafeTimedSerializer(current_app.secret_key, salt='platform-refresh').loads(body.get('refresh_token', ''), max_age=30 * 86400)
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
    return jsonify(success=True, enabled=False, registration_mode='invite_only', disable_registration=True, complex_password_enabled=True)


@auth_bp.route('/api/platform/users', methods=['GET', 'POST'])
def users():
    if g.user['role'] != 'admin':
        raise StoreError('需要平台管理员权限', 403)
    if request.method == 'POST':
        body = request.get_json(silent=True) or {}
        uid = create_user(body.get('email', ''), body.get('username', ''), body.get('password', ''),
                          body.get('role', 'viewer'), body.get('contextdb_api_key'))
        return jsonify(success=True, id=uid), 201
    with connection() as conn:
        rows = conn.execute('SELECT id,email,username,role,contextdb_member_id,active,created_at FROM platform_users ORDER BY created_at').fetchall()
    return jsonify(success=True, users=rows)


@auth_bp.route('/api/v1/auth/me/preferences', methods=['PUT'])
def preferences():
    from psycopg.types.json import Jsonb
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or len(str(body)) > 32000:
        raise StoreError('偏好设置格式或大小无效', 400)
    with connection() as conn:
        row = conn.execute('UPDATE platform_users SET preferences=preferences || %s,updated_at=now() WHERE id=%s RETURNING preferences', (Jsonb(body), user_id())).fetchone()
    return jsonify(success=True, data=row)


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
    if body.get('password'):
        if not isinstance(body['password'], str) or len(body['password']) < 12:
            raise StoreError('密码至少 12 位', 400)
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
        email = os.getenv('PLATFORM_ADMIN_EMAIL', '')
        password = os.getenv('PLATFORM_ADMIN_PASSWORD', '')
        uid = create_user(email, '管理员', password, 'admin', os.getenv('CONTEXTDB_API_KEY'))
        print('平台管理员已创建，密码保存在本机 .env；ContextDB 成员绑定已验证。')


if __name__ == '__main__':
    main()
