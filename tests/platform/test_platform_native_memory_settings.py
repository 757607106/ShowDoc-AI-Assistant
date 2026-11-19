"""Personal native-memory controls preserve old gates and never enable on reads."""
import os

from agent import registry
from agent.memory_files import policy
from webapi.auth import create_user


def test_memory_adoption_preserves_legacy_effective_state_and_records(authenticated_client):
    owner = os.environ['TEST_PLATFORM_USER']
    registry.save_record('memory', {'id': 'old-note', 'content': 'preserve'}, owner)
    assert authenticated_client.get('/api/v1/memory/settings').json['data']['enabled'] is False
    assert registry.records('settings', owner) == []
    registry.save_record('settings', {'id': 'memory-config', 'value': {'enabled': True, 'extract_instructions': 'legacy'}}, owner)
    registry.save_record('settings', {'id': 'memory-preference', 'value': {'enabled': False}}, owner)
    before = registry.records('settings', owner)
    assert authenticated_client.get('/api/v1/memory/settings').json['data']['enabled'] is False
    assert registry.records('settings', owner) == before
    enabled = authenticated_client.put('/api/v1/memory/settings', json={'enabled': True})
    assert enabled.status_code == 200
    assert enabled.json['data']['enabled'] is True
    assert enabled.json['data']['scope'] == 'personal_agent'
    assert registry.record('settings', 'memory-config', owner)['value']['extract_instructions'] == 'legacy'
    assert authenticated_client.put('/api/v1/memory/settings', json={'enabled': False}).json['data']['effective'] is False
    assert registry.record('memory', 'old-note', owner)['content'] == 'preserve'


def test_personal_memory_is_isolated_and_viewer_cannot_write_workspace_defaults(authenticated_client):
    from app import app
    owner = os.environ['TEST_PLATFORM_USER']
    other_owner = create_user('native-reader@example.com', 'Reader', 'reader-password-123', 'viewer')
    other = app.test_client()
    token = other.post('/api/v1/auth/login', json={'account': 'native-reader@example.com', 'password': 'reader-password-123'}).json['token']
    other.environ_base['HTTP_AUTHORIZATION'] = 'Bearer ' + token
    assert other.put('/api/v1/memory/settings', json={'enabled': True}).status_code == 200
    assert policy(other_owner)['enabled'] is True
    assert policy(owner)['enabled'] is False
    assert other.put('/api/v1/tenants/kv/default-settings', json={'chat_model_id': 'agent-main'}).status_code == 403
    assert registry.records('settings', owner) == []
    assert other.post('/api/v1/models', json={}).status_code == 403
    assert other.put('/api/v1/tenants/kv/memory-config', json={'enabled': True}).status_code == 403
    assert other.put('/api/v1/agents/builtin-smart-reasoning/memory-file', json={'content': 'denied'}).status_code == 403
