"""Retain saved browser preferences without an execution runtime."""
import pytest


@pytest.mark.parametrize('value', [True, 42, [], {}, '中' * 4001])
def test_browser_preferences_reject_invalid_type_and_length(authenticated_client, value):
    response = authenticated_client.put('/api/v1/auth/me/preferences', json={'browser_search_instructions': value})
    assert response.status_code == 400
    assert not authenticated_client.get('/api/v1/auth/me').json['data']['user']['preferences'].get('browser_search_instructions')



def test_browser_preferences_accept_limit_and_null_preserves_saved_value(authenticated_client):
    value = '中' * 4000
    assert authenticated_client.put('/api/v1/auth/me/preferences', json={'browser_search_instructions': value}).status_code == 200
    response = authenticated_client.put('/api/v1/auth/me/preferences', json={'browser_search_instructions': None})
    assert response.json['data']['browser_search_instructions'] == value

