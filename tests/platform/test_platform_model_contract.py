"""WeKnora model configuration contracts against isolated PostgreSQL workspaces."""
import base64
import json
import os

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from psycopg.types.json import Jsonb

from agent import config, model_secrets, registry
from agent.credentials import cipher
from governance.database import _initialize_schema, connection
from governance.store import StoreError
from tests.agent.test_agent_configuration import KnowledgeClient


def model_body(name='model', kind='KnowledgeQA', **params):
    return {'name': name, 'type': kind, 'source': 'remote', 'parameters': {
        'provider': 'generic', 'base_url': 'https://model.invalid/v1', **params}}


def test_put_preserves_credentials_copy_and_rotation_are_independent(authenticated_client):
    client = authenticated_client
    owner = os.environ['TEST_PLATFORM_USER']
    body = model_body(kind='Rerank', provider='lkeap', api_key='create-key', extra_config={'secret_key': 'create-secret'})
    created = client.post('/api/v1/models', json=body)
    path = '/api/v1/models/' + created.json['data']['id']
    assert created.status_code == 201
    for value in ('', '********', 'overwritten'):
        params = {'api_key': value, 'app_secret': value, 'extra_config': {'secret_key': value, 'region': 'ap-guangzhou'}}
        updated = client.put(path, json={**body, 'parameters': {**body['parameters'], **params}})
        assert updated.status_code == 200
        assert updated.json['data']['credentials']['secret_key'] == {'configured': True}
        assert updated.json['data']['parameters']['extra_config'] == {'region': 'ap-guangzhou'}
    copied = client.post(path + '/copy', json={'display_name': 'Copy', 'parameters': {'api_key': 'ignored'}})
    assert copied.status_code == 201 and client.post(path + '/copy', json={}).status_code == 400
    copy_id = copied.json['data']['id']
    assert registry.model_config(copy_id, owner)['parameters']['app_secret'] == 'create-secret'
    assert registry.model_config(copy_id, owner)['parameters']['api_key'] == 'create-key'
    rotated = client.put(path + '/credentials', json={'api_key': 'rotated-key'})
    assert rotated.json == {'success': True, 'data': {'fields': {
        'api_key': {'configured': True}, 'app_secret': {'configured': True}}}}
    assert client.delete(path + '/credentials/app_secret').status_code == 204
    assert client.delete(path + '/credentials/app_secret').status_code == 204
    assert registry.model_config(copy_id, owner)['parameters']['app_secret'] == 'create-secret'
    stored = registry.record('model', path.split('/')[-1], owner)
    encrypted = stored['_encrypted']['api_key']
    assert encrypted.startswith('enc:v1:') and 'rotated-key' not in json.dumps(stored)
    binary = base64.urlsafe_b64decode(encrypted[7:] + '=' * (-len(encrypted[7:]) % 4))
    assert AESGCM(os.environ['SYSTEM_AES_KEY'].encode()).decrypt(binary[:12], binary[12:], None) == b'rotated-key'
    for response in [created, updated, copied, rotated, client.get(path), client.get('/api/v1/models')]:
        assert all(secret not in response.text for secret in ('create-key', 'create-secret', 'rotated-key', 'enc:v1:'))


def test_no_aes_key_allows_public_reads_and_secretless_writes(authenticated_client, monkeypatch, caplog):
    client = authenticated_client
    model = client.post('/api/v1/models', json=model_body(api_key='existing')).json['data']
    path = '/api/v1/models/' + model['id']
    original_key = os.environ['SYSTEM_AES_KEY']
    monkeypatch.setenv('SYSTEM_AES_KEY', 'short')
    _initialize_schema()
    assert '32 字节' in caplog.text
    assert client.post('/api/v1/models', json=model_body()).status_code == 201
    assert client.get(path).json['data']['credentials']['api_key']['configured']
    assert client.patch(path, json={'description': 'editable'}).status_code == 200
    updated = client.put(path, json={'parameters': {'context_window': 64000, 'api_key': 'ignore', 'custom_headers': {}}})
    assert updated.status_code == 200 and updated.json['data']['parameters']['context_window'] == 64000
    assert client.put(path + '/credentials', json={'api_key': 'lost'}).status_code == 503
    assert client.post('/api/v1/models', json=model_body(api_key='plaintext')).status_code == 503
    monkeypatch.setenv('SYSTEM_AES_KEY', original_key)
    assert registry.model_config(model['id'], os.environ['TEST_PLATFORM_USER'])['parameters']['api_key'] == 'existing'


def test_legacy_cipher_and_default_settings_migrate_atomically(authenticated_client, monkeypatch):
    owner = os.environ['TEST_PLATFORM_USER']
    encrypted = cipher().encrypt(b'{"api_key":"legacy"}').decode()
    def put_legacy(identifier, token):
        return registry.save_record('model', {**model_body(identifier), '_kind': 'model', 'id': identifier,
            '_encrypted': token}, owner)
    put_legacy('old', encrypted)
    put_legacy('bad', 'invalid')
    with connection() as conn, pytest.raises(StoreError):
        with conn.transaction():
            model_secrets.migrate(conn)
    assert registry.record('model', 'old', owner)['_encrypted'] == encrypted
    put_legacy('bad', encrypted)
    with connection() as conn:
        conn.execute('ALTER TABLE platform_workspaces ALTER COLUMN default_settings DROP NOT NULL')
        conn.execute('UPDATE platform_workspaces SET default_settings=NULL WHERE principal_id=%s', (owner,))
        conn.execute("""INSERT INTO runtime_records(id,owner_id,kind,record_key,name,payload,metadata)
            VALUES ('old-default',%s,'settings','default-settings','default-settings',%s,'{}')""",
            (owner, Jsonb({'id': 'default-settings','value': {'summary_model_id': 'old','utility_model_id': 'stale'}})))
    _initialize_schema()
    stored = registry.record('model', 'old', owner)
    assert stored['_encrypted']['api_key'].startswith(model_secrets.PREFIX)
    assert registry.model_config('old', owner)['parameters']['api_key'] == 'legacy'
    assert registry.workspace_defaults(owner)['chat_model_id'] == 'old'
    registry.save_workspace_defaults(owner, {'chat_model_id': 'agent-main','utility_model_id':'stale'})
    _initialize_schema()
    assert registry.workspace_defaults(owner)['chat_model_id'] == 'agent-main'
    assert registry.record('model', 'old', owner) == stored


def test_system_admin_edits_builtin_and_tenant_admin_can_only_use_it(authenticated_client, monkeypatch):
    client = authenticated_client
    owner = os.environ['TEST_PLATFORM_USER']
    monkeypatch.setenv('BAILIAN_API_KEY', 'built-in-secret')
    path = '/api/v1/models/agent-main'
    detail = client.get(path).json['data']
    assert not detail['parameters']['base_url'] and 'credentials' not in detail
    assert client.put(path, json=model_body()).status_code == 403
    assert client.put(path + '/credentials', json={'api_key':'other'}).status_code == 403
    assert client.post('/api/v1/initialization/remote/check', json={'modelId':'agent-main'}).status_code == 403
    with connection() as conn:
        conn.execute('UPDATE platform_users SET is_system_admin=true WHERE id=%s', (owner,))
    assert client.get(path).json['data']['parameters']['base_url']
    assert client.patch(path, json={'display_name':'Shared'}).status_code == 200
    assert registry.model_config('agent-main', owner)['parameters']['api_key'] == 'built-in-secret'
    assert client.put(path, json=model_body(api_key='ignored')).status_code == 200
    assert client.put(path + '/credentials', json={'api_key':'shared-rotation'}).status_code == 200
    assert registry.model_config('agent-main', 'another-owner')['parameters']['api_key'] == 'shared-rotation'
    assert client.post(path + '/copy', json={'display_name':'forbidden'}).status_code == client.delete(path).status_code == 400
    assert 'shared-rotation' not in client.get(path).text


def test_six_slots_validate_only_changed_active_choices(authenticated_client):
    client = authenticated_client
    owner = os.environ['TEST_PLATFORM_USER']
    path = '/api/v1/tenants/kv/default-settings'
    assert client.get(path).json['data'] == dict.fromkeys(registry.MODEL_SLOTS, '')
    vision = registry.save_model(model_body(supports_vision=True), owner)
    asr = registry.save_model(model_body(kind='ASR'), owner)
    assert client.put(path, json={'utility_model_id':asr['id']}).status_code == 400
    assert client.put(path, json={'chat_model_id':'nonexistent'}).status_code == 400
    initial = client.put(path, json={'asr_model_id':asr['id'], 'vlm_model_id':' '+vision['id']+' '}).json['data']
    assert initial['vlm_model_id'] == vision['id']
    registry.save_record('model',{**asr,'status':'disabled'},owner)
    assert client.put(path, json={**initial, 'utility_model_id':vision['id']}).status_code == 200
    assert client.put(path, json={}).json['data'] == dict.fromkeys(registry.MODEL_SLOTS, '')
    assert client.put(path, json={'asr_model_id':asr['id']}).status_code == 400


def test_runtime_model_precedence_and_workspace_knowledge_reference(authenticated_client):
    owner = os.environ['TEST_PLATFORM_USER']
    default, kb_model, assigned, override = [registry.save_model(model_body(name), owner)['id']
                                            for name in ('workspace','kb','assigned','override')]
    inherited = config.save_agent({'name': 'Inherited'}, owner)['id']
    registry.save_workspace_defaults(owner, {'chat_model_id': default})
    knowledge = KnowledgeClient()
    def selection(agent, **body):
        return config.resolve_request({'agent_id':agent, **body}, client=knowledge, owner_id=owner)['agent_config']['model_id']
    assert selection(inherited) == default
    registry.save_record('knowledge_space', {'id':'space-a','knowledge_base_id':'a','name':'Knowledge A',
                                             'summary_model_id':kb_model}, owner)
    assert selection(inherited, knowledge_base_ids=['a']) == kb_model
    agent = config.save_agent({'name':'Assigned','config':{'model_id':assigned}}, owner)['id']
    assert selection(agent, knowledge_base_ids=['a']) == assigned
    assert selection(agent, summary_model_id=override, knowledge_base_ids=['a']) == override
    assert selection(agent, summary_model_id='stale') == assigned
    blocked = authenticated_client.delete('/api/v1/models/'+kb_model)
    assert blocked.json['error']['code'] == 2300
    assert blocked.json['error']['details']['knowledge_bases'] == [
        {'id':'a','name':'Knowledge A','bindings':['summary_model']}]


def test_create_checks_address_before_storage(authenticated_client, monkeypatch):
    monkeypatch.setenv('SSRF_WHITELIST_EXTRA', '')
    monkeypatch.setenv('SSRF_WHITELIST', '')
    client = authenticated_client
    assert client.post('/api/v1/models', json=model_body(base_url='http://127.0.0.1/v1')).status_code == 400
    assert client.post('/api/v1/models', json=model_body(base_url='http://models.example.org:5432')).status_code == 400
    assert registry.records('model', os.environ['TEST_PLATFORM_USER']) == []
