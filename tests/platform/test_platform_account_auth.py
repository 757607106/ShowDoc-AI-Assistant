"""Account/password authentication over the existing isolated platform user store."""
import sys

from werkzeug.security import check_password_hash

import app as app_module
from governance.database import connection
from webapi.auth import create_user, main


def sign_in(account, password='admin123', **extra):
    client = app_module.app.test_client()
    response = client.post('/api/v1/auth/login', json={'account': account, 'password': password, **extra})
    if response.status_code == 200:
        client.environ_base['HTTP_AUTHORIZATION'] = 'Bearer ' + response.json['token']
    return client, response


def test_plain_account_login_preserves_identity_role_and_legacy_field(authenticated_client):
    uid = create_user(' ADMIN ', '管理员', 'admin123', 'admin')
    client, response = sign_in(' AdMiN ')
    assert response.status_code == 200
    assert response.json['user']['id'] == uid
    assert response.json['user']['account'] == 'admin'
    assert response.json['user']['email'] == 'admin'
    assert response.json['user']['username'] == '管理员'
    assert response.json['memberships'][0]['role'] == 'owner'
    assert client.get('/api/v1/auth/me').json['data']['user']['account'] == 'admin'
    with connection() as conn:
        row = conn.execute('SELECT email,password_hash FROM platform_users WHERE id=%s', (uid,)).fetchone()
    assert row['email'] == 'admin' and row['password_hash'] != 'admin123'
    assert check_password_hash(row['password_hash'], 'admin123')


def test_account_creation_requires_no_email_and_is_case_insensitively_unique(authenticated_client):
    body = {'account': ' Employee ', 'username': '显示名称', 'password': 'user1234', 'role': 'editor'}
    created = authenticated_client.post('/api/platform/users', json=body)
    assert created.status_code == 201
    client, response = sign_in('employee', 'user1234')
    assert response.status_code == 200 and response.json['user']['id'] == created.json['id']
    assert response.json['user']['username'] == '显示名称'
    assert response.json['memberships'][0]['role'] == 'owner'
    assert response.json['user']['platform_role'] == 'editor'
    body['account'] = 'EMPLOYEE'
    assert authenticated_client.post('/api/platform/users', json=body).status_code == 409
    users = authenticated_client.get('/api/platform/users').json['users']
    assert next(row for row in users if row['id'] == created.json['id'])['account'] == 'employee'
    assert client.get('/api/platform/users').status_code == 403


def test_legacy_email_request_still_works_but_cannot_override_explicit_account(authenticated_client):
    client = app_module.app.test_client()
    credentials = {'email': 'test@example.com', 'password': 'test-password-123'}
    assert client.post('/api/v1/auth/login', json=credentials).status_code == 200
    for invalid in ('', None, [], {}, 'missing'):
        response = client.post('/api/v1/auth/login', json={**credentials, 'account': invalid})
        assert response.status_code == 401
        assert response.json['message'] == '账号或密码错误'
    created = authenticated_client.post('/api/platform/users', json={
        'email': 'legacy@example.com', 'username': '旧客户端', 'password': 'legacy12'})
    assert created.status_code == 201
    assert sign_in('legacy@example.com', 'legacy12')[1].status_code == 200
    assert authenticated_client.post('/api/platform/users', json={
        'account': None, 'email': 'ignored@example.com', 'username': '成员', 'password': 'user1234'}).status_code == 400


def test_malformed_accounts_passwords_and_payloads_do_not_reach_authentication(authenticated_client):
    create_user('admin', '管理员', 'admin123')
    client = app_module.app.test_client()
    for payload in ([], ['account'], 1, True, 'admin', None):
        assert client.post('/api/v1/auth/login', json=payload).status_code == 400
    for invalid in ('', ' ', 'a b', 'a\nb', 'a\x00b', 'a\u200bb', 'x' * 256, None, [], {}, True, 123):
        assert sign_in(invalid)[1].status_code == 401
        response = authenticated_client.post('/api/platform/users', json={
            'account': invalid, 'username': '显示名称', 'password': 'user1234'})
        assert response.status_code == 400
    for invalid in (None, [], {}, True, 123, '', 'wrong', 'x' * 1025):
        assert sign_in('admin', invalid)[1].status_code == 401
    assert authenticated_client.post('/api/platform/users', json=[]).status_code == 400


def test_password_length_policy_is_consistent_for_creation_reset_and_change(authenticated_client):
    uid = create_user('employee', '成员', 'user1234')
    for invalid in ('1234567', 'x' * 1025, None, [], {}, True):
        assert authenticated_client.post('/api/platform/users', json={
            'account': 'invalid', 'username': '成员', 'password': invalid}).status_code == 400
        if invalid is not None:
            assert authenticated_client.patch('/api/platform/users/' + uid,
                json={'role': 'editor', 'password': invalid}).status_code == 400
        assert authenticated_client.post('/api/v1/auth/change-password', json={
            'old_password': 'test-password-123', 'new_password': invalid}).status_code == 400
    assert authenticated_client.get('/api/v1/auth/config').json['complex_password_enabled'] is False
    create_user('max-length', '成员', 'x' * 1024)
    assert sign_in('max-length', 'x' * 1024)[1].status_code == 200


def test_change_to_eight_character_password_revokes_access_and_refresh_without_changing_owner(authenticated_client):
    current = authenticated_client.get('/api/v1/auth/me').json['data']['user']
    old_session = app_module.app.test_client().post('/api/v1/auth/login', json={
        'account': current['account'], 'password': 'test-password-123'}).json
    headers = {'Authorization': 'Bearer ' + old_session['access_token']}
    response = authenticated_client.post('/api/v1/auth/change-password', json={
        'old_password': 'test-password-123', 'new_password': 'admin123'})
    assert response.status_code == 200
    client = app_module.app.test_client()
    assert client.get('/api/v1/auth/me', headers=headers).status_code == 401
    assert client.post('/api/v1/auth/refresh', json={'refreshToken': old_session['refresh_token']}).status_code == 401
    assert sign_in(current['account'], 'test-password-123')[1].status_code == 401
    new_client, signed_in = sign_in(current['account'])
    assert signed_in.status_code == 200 and signed_in.json['user']['id'] == current['id']
    assert new_client.get('/api/v1/auth/me').json['data']['user']['username'] == current['username']


def test_reset_and_disable_revoke_only_the_selected_account_sessions(authenticated_client):
    uid = create_user('employee', '成员', 'user1234')
    employee, signed_in = sign_in('employee', 'user1234')
    assert signed_in.status_code == 200
    response = authenticated_client.patch('/api/platform/users/' + uid, json={'password': 'admin123'})
    assert response.status_code == 200
    assert employee.get('/api/v1/auth/me').status_code == 401
    assert sign_in('employee', 'user1234')[1].status_code == 401
    employee, signed_in = sign_in('employee')
    assert signed_in.status_code == 200 and signed_in.json['user']['id'] == uid
    assert authenticated_client.patch('/api/platform/users/' + uid, json={'active': False}).status_code == 200
    assert employee.get('/api/v1/auth/me').status_code == 401
    assert sign_in('employee')[1].status_code == 401
    assert authenticated_client.get('/api/v1/auth/me').status_code == 200


def test_account_login_refresh_and_logout_keep_the_existing_session_contract(authenticated_client):
    uid = create_user('admin', '管理员', 'admin123')
    client, login = sign_in('admin')
    refreshed = client.post('/api/v1/auth/refresh', json={'refreshToken': login.json['refresh_token']})
    assert refreshed.status_code == 200 and refreshed.json['user']['id'] == uid
    assert refreshed.json['user']['account'] == 'admin'
    assert client.post('/api/v1/auth/logout').status_code == 200
    assert client.get('/api/v1/auth/me').status_code == 401
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': refreshed.json['refresh_token']}).status_code == 401


def test_bootstrap_is_idempotent_and_does_not_reset_existing_credentials(authenticated_client, monkeypatch, capsys):
    with connection() as conn:
        before = conn.execute('SELECT id,email,password_hash,contextdb_key_encrypted FROM platform_users').fetchall()
    monkeypatch.setattr(sys, 'argv', ['webapi.auth', '--bootstrap'])
    monkeypatch.setenv('PLATFORM_ADMIN_ACCOUNT', 'admin')
    monkeypatch.setenv('PLATFORM_ADMIN_PASSWORD', 'admin123')
    main()
    assert '未修改现有账号' in capsys.readouterr().out
    with connection() as conn:
        assert conn.execute('SELECT id,email,password_hash,contextdb_key_encrypted FROM platform_users').fetchall() == before


def test_bootstrap_defaults_and_legacy_account_environment(authenticated_client, monkeypatch):
    import webapi.auth as auth
    with connection() as conn:
        conn.execute('DELETE FROM platform_tokens')
        conn.execute('DELETE FROM platform_users')
    monkeypatch.setattr(sys, 'argv', ['webapi.auth', '--bootstrap'])
    monkeypatch.setattr('dotenv.load_dotenv', lambda *args, **kwargs: None)
    monkeypatch.delenv('PLATFORM_ADMIN_ACCOUNT', raising=False)
    monkeypatch.delenv('PLATFORM_ADMIN_EMAIL', raising=False)
    monkeypatch.delenv('PLATFORM_ADMIN_PASSWORD', raising=False)
    monkeypatch.delenv('CONTEXTDB_API_KEY', raising=False)
    auth.main()
    assert sign_in('admin')[1].status_code == 200
    with connection() as conn:
        conn.execute('DELETE FROM platform_tokens')
        conn.execute('DELETE FROM platform_users')
    monkeypatch.setenv('PLATFORM_ADMIN_EMAIL', 'old-config@example.com')
    monkeypatch.setenv('PLATFORM_ADMIN_PASSWORD', 'legacy12')
    auth.main()
    assert sign_in('old-config@example.com', 'legacy12')[1].status_code == 200
    with connection() as conn:
        conn.execute('DELETE FROM platform_tokens')
        conn.execute('DELETE FROM platform_users')
    monkeypatch.setenv('PLATFORM_ADMIN_ACCOUNT', 'configured-admin')
    auth.main()
    assert sign_in('configured-admin', 'legacy12')[1].status_code == 200
    assert sign_in('old-config@example.com', 'legacy12')[1].status_code == 401
