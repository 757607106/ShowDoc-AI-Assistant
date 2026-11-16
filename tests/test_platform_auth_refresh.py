"""Official WeKnora refresh fields over real isolated PostgreSQL sessions."""
from datetime import timedelta

import pytest
from itsdangerous import TimestampSigner, URLSafeTimedSerializer

from governance.database import connection


def login(client):
    response = client.post('/api/v1/auth/login', json={
        'email': 'test@example.com', 'password': 'test-password-123'})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload['access_token'] == payload['token']
    return payload


def serializer(salt):
    from app import app
    return URLSafeTimedSerializer(app.secret_key, salt=salt)


@pytest.mark.parametrize('body_key', ['refreshToken', 'refresh_token'])
def test_refresh_contract_keeps_session_extends_expiry_and_honors_logout(authenticated_client, body_key):
    initial = login(authenticated_client)
    claims = serializer('platform-refresh').loads(initial['refresh_token'])
    with connection() as conn:
        conn.execute("UPDATE platform_tokens SET expires_at=now()+interval '1 day' WHERE id=%s",
                     (claims['session'],))
    refreshed = authenticated_client.post('/api/v1/auth/refresh',
        json={body_key: initial['refresh_token']})
    assert refreshed.status_code == 200
    payload = refreshed.get_json()
    assert payload['success'] and payload['access_token'] == payload['token']
    assert serializer('platform-access').loads(payload['access_token']) == claims
    assert serializer('platform-refresh').loads(payload['refresh_token']) == claims
    headers = {'Authorization': 'Bearer ' + payload['access_token']}
    assert authenticated_client.get('/api/v1/auth/me', headers=headers).status_code == 200
    with connection() as conn:
        row = conn.execute('SELECT owner_id,expires_at-now() AS remaining FROM platform_tokens WHERE id=%s',
                           (claims['session'],)).fetchone()
    assert row['owner_id'] == initial['user']['id']
    assert row['remaining'] > timedelta(days=29)
    assert authenticated_client.post('/api/v1/auth/logout', headers=headers).status_code == 200
    assert authenticated_client.get('/api/v1/auth/me', headers=headers).status_code == 401
    assert authenticated_client.post('/api/v1/auth/refresh',
        json={body_key: payload['refresh_token']}).status_code == 401
    with connection() as conn:
        assert conn.execute('SELECT count(*) AS n FROM platform_tokens WHERE id=%s',
                            (claims['session'],)).fetchone()['n'] == 0


def test_test_signed_expired_access_recovers_with_real_served_refresh(authenticated_client):
    """Backdate only this test signature; never change the process/system clock.

    The expired access is a test-created signature, while the refresh token and
    its live PostgreSQL session come from the real login endpoint.
    """
    initial = login(authenticated_client)
    claims = serializer('platform-access').loads(initial['token'])

    class NineHoursAgo(TimestampSigner):
        def get_timestamp(self):
            return super().get_timestamp() - 9 * 3600

    from app import app
    expired = URLSafeTimedSerializer(app.secret_key, salt='platform-access', signer=NineHoursAgo).dumps(claims)
    assert authenticated_client.get('/api/v1/auth/me',
        headers={'Authorization': 'Bearer ' + expired}).status_code == 401
    refreshed = authenticated_client.post('/api/v1/auth/refresh',
        json={'refreshToken': initial['refresh_token']},
        headers={'Authorization': 'Bearer ' + expired})
    assert refreshed.status_code == 200
    access = refreshed.get_json()['access_token']
    assert serializer('platform-access').loads(access) == claims
    assert authenticated_client.get('/api/v1/auth/me',
        headers={'Authorization': 'Bearer ' + access}).status_code == 200


@pytest.mark.parametrize('body,status', [
    ([], 400), (['value'], 400), (1, 400), (True, 400), ('value', 400), (None, 400),
    ({}, 401), ({'refreshToken': None}, 401), ({'refreshToken': 1}, 401),
    ({'refreshToken': []}, 401), ({'refreshToken': {}}, 401), ({'refreshToken': ''}, 401),
    ({'refreshToken': '  '}, 401), ({'refresh_token': None}, 401),
    ({'refresh_token': 1}, 401), ({'refresh_token': []}, 401),
])
def test_refresh_rejects_malformed_body_or_token_without_server_error(authenticated_client, body, status):
    assert authenticated_client.post('/api/v1/auth/refresh', json=body).status_code == status
