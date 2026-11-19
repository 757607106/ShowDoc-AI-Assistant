"""Shared HTTP token validation must trust current database identity only."""
from contextlib import contextmanager

import pytest
from itsdangerous import URLSafeTimedSerializer, TimestampSigner

from governance.store import StoreError
from webapi import auth


@pytest.fixture
def database(monkeypatch):
    state = {'row': {'id': 'actual-owner', 'workspace_id': 10000, 'principal_id': 'actual-owner', 'account_id': 'actual-owner', 'role': 'viewer', 'active': True}, 'queries': []}

    class Connection:
        def execute(self, query, params):
            state['queries'].append((query, params))
            return self

        def fetchone(self):
            return state['row']

    @contextmanager
    def connection():
        yield Connection()

    monkeypatch.setattr(auth, 'connection', connection)
    monkeypatch.setenv('FLASK_SECRET_KEY', 'shared-test-secret')
    return state


def token(claims):
    return URLSafeTimedSerializer('shared-test-secret', salt='platform-access').dumps(claims)


def test_current_database_identity_overrides_token_role_and_owner(database):
    user, session_id = auth.validate_access_token(token({'session': 'session-id', 'id': 'forged', 'role': 'admin'}))
    assert user == database['row'] and session_id == 'session-id'
    assert user['role'] == 'viewer' and user['id'] == 'actual-owner'
    query, params = database['queries'][0]
    assert params == ('session-id',) and 'u.active' in query and 't.expires_at>now()' in query


@pytest.mark.parametrize('claims', [{}, {'session': []}, {'session': ''}, ['session-id']])
def test_invalid_signed_claims_are_rejected_before_database(database, claims):
    with pytest.raises(StoreError) as error:
        auth.validate_access_token(token(claims))
    assert error.value.status == 401 and not database['queries']


def test_revoked_or_disabled_session_is_rejected(database):
    database['row'] = None
    with pytest.raises(StoreError) as error:
        auth.validate_access_token(token({'session': 'revoked'}))
    assert error.value.status == 401


def test_bad_signature_and_expiry_are_rejected(database, monkeypatch):
    with pytest.raises(StoreError) as error:
        auth.validate_access_token('forged-token')
    assert error.value.status == 401
    with monkeypatch.context() as patch:
        patch.setattr(TimestampSigner, 'get_timestamp', lambda self: 1)
        expired = token({'session': 'expired'})
    with pytest.raises(StoreError) as error:
        auth.validate_access_token(expired)
    assert error.value.status == 401 and not database['queries']
