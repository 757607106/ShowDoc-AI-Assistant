"""Personal model defaults and explicit clearing through the real settings API."""
import os

import pytest

from agent import config, registry
from governance.database import connection
from governance.store import StoreError


def save_model(owner, name, kind='KnowledgeQA', **parameters):
    return registry.save_model({'name': name, 'type': kind, 'parameters': {
        'base_url': 'https://model.invalid/v1', 'provider': 'generic', **parameters}}, owner)


def test_model_dtos_mark_environment_new_and_legacy_rows_active(authenticated_client):
    owner = os.environ['TEST_PLATFORM_USER']
    new = save_model(owner, 'new')
    legacy = save_model(owner, 'legacy')
    legacy.pop('status')
    registry.save_record('model', legacy, owner)
    disabled = save_model(owner, 'disabled')
    registry.save_record('model', {**disabled, 'status': 'disabled'}, owner)

    rows = {item['id']: item for item in authenticated_client.get('/api/v1/models').json['data']}
    for identifier in ('agent-main', new['id'], legacy['id']):
        assert rows[identifier]['status'] == 'active'
        assert authenticated_client.get('/api/v1/models/' + identifier).json['data']['status'] == 'active'
    assert rows[disabled['id']]['status'] == 'disabled'
    assert 'status' not in registry.record('model', legacy['id'], owner)


def test_legacy_default_slots_are_projected_without_sharing_between_owners(authenticated_client):
    owner = os.environ['TEST_PLATFORM_USER']
    chat = save_model(owner, 'chat')
    utility = save_model(owner, 'utility')
    vision_a, vision_b = [save_model(owner, name, 'VLLM') for name in ('vision-a', 'vision-b')]
    asr_a, asr_b = [save_model(owner, name, 'ASR') for name in ('asr-a', 'asr-b')]
    defaults = {'chat_model_id': chat['id'], 'utility_model_id': utility['id'],
                'vlm_model_id': vision_b['id'], 'asr_model_id': asr_b['id']}
    assert authenticated_client.put('/api/v1/tenants/kv/default-settings', json=defaults).status_code == 200

    rows = {item['id']: item for item in authenticated_client.get('/api/v1/models').json['data']}
    for identifier, kind in [(chat['id'], 'KnowledgeQA'), (utility['id'], 'Utility'),
                             (vision_b['id'], 'VLLM'), (asr_b['id'], 'ASR')]:
        assert rows[identifier]['default_for'] == [kind]
    assert rows[chat['id']]['is_default'] and not rows['agent-main']['is_default']
    assert rows[vision_b['id']]['is_default'] and not rows[vision_a['id']]['is_default']
    assert rows[asr_b['id']]['is_default'] and not rows[asr_a['id']]['is_default']
    assert registry.default_model_id(owner, 'utility_model_id') == utility['id']
    assert registry.models('other-owner')[0]['default_for'] == ['KnowledgeQA']
    assert registry.default_model_id('other-owner') == 'agent-main'


def test_vision_chat_default_does_not_replace_its_chat_default_marker(authenticated_client):
    owner = os.environ['TEST_PLATFORM_USER']
    vision = save_model(owner, 'vision-chat', supports_vision=True)
    assert authenticated_client.put('/api/v1/tenants/kv/default-settings', json={
        'vlm_model_id': vision['id']}).status_code == 200
    rows = {item['id']: item for item in authenticated_client.get('/api/v1/models').json['data']}
    assert rows[vision['id']]['default_for'] == ['VLLM']
    assert not rows[vision['id']]['is_default'] and rows['agent-main']['is_default']


def test_agent_vision_binding_accepts_vision_chat_but_not_text_only_chat(authenticated_client):
    owner = os.environ['TEST_PLATFORM_USER']
    vision = save_model(owner, 'vision-chat', supports_vision=True)
    text = save_model(owner, 'text-only')
    saved = registry.save_record('agent', {'name': 'Vision agent', 'config': {
        'model_id': 'agent-main', 'vlm_model_id': vision['id']}}, owner)
    assert saved['config']['vlm_model_id'] == vision['id']
    with pytest.raises(StoreError) as error:
        registry.save_record('agent', {'name': 'Text agent', 'config': {'vlm_model_id': text['id']}}, owner)
    assert error.value.status == 400


def test_stale_or_inactive_defaults_fall_back_only_during_default_selection(authenticated_client):
    from agent import session_titles
    owner = os.environ['TEST_PLATFORM_USER']
    chat = save_model(owner, 'chat')
    utility = save_model(owner, 'utility')
    assert authenticated_client.put('/api/v1/tenants/kv/default-settings', json={
        'chat_model_id': chat['id'], 'utility_model_id': utility['id']}).status_code == 200
    registry.save_record('model', {**utility, 'status': 'disabled'}, owner)
    assert session_titles._default_model_id(owner) == chat['id']
    registry.delete_record('model', chat['id'], owner)
    assert registry.default_model_id(owner) == 'agent-main'
    assert session_titles._default_model_id(owner) == 'agent-main'
    rows = {item['id']: item for item in authenticated_client.get('/api/v1/models').json['data']}
    assert rows['agent-main']['is_default']
    with pytest.raises(StoreError) as error:
        registry.model_config(chat['id'], owner)
    assert error.value.status == 404


def test_explicit_empty_model_overrides_clear_but_patch_omission_preserves(authenticated_client):
    owner = os.environ['TEST_PLATFORM_USER']
    saved = save_model(owner, 'configured', context_window=64000, max_output_tokens=4096,
                       max_concurrency=3, custom_headers={'X-Private': 'old-value'})
    url = '/api/v1/models/' + saved['id']
    assert authenticated_client.patch(url, json={'display_name': 'Renamed'}).status_code == 200
    unchanged = registry.model_config(saved['id'], owner)['parameters']
    assert unchanged['context_window'] == 64000 and unchanged['custom_headers'] == {'X-Private': 'old-value'}

    response = authenticated_client.put(url, json={'parameters': {
        'context_window': 0, 'max_output_tokens': 0, 'max_concurrency': 0, 'custom_headers': {}}})
    assert response.status_code == 200, response.json
    cleared = registry.model_config(saved['id'], owner)['parameters']
    assert all(cleared[key] == 0 for key in ('context_window', 'max_output_tokens', 'max_concurrency'))
    assert cleared['custom_headers'] == {}
    assert response.json['data']['capabilities']['context_window'] is None
    assert 'old-value' not in str(authenticated_client.get('/api/v1/models').json)


def test_viewer_can_change_only_their_personal_default_not_shared_or_model_settings(authenticated_client):
    owner = os.environ['TEST_PLATFORM_USER']
    saved = save_model(owner, 'personal')
    with connection() as conn:
        conn.execute("UPDATE platform_users SET role='viewer' WHERE id=%s", (owner,))
    result = authenticated_client.put('/api/v1/tenants/kv/default-settings', json={'chat_model_id': saved['id']})
    assert result.status_code == 200, result.json
    assert registry.default_model_id(owner) == saved['id']
    assert registry.default_model_id('another-owner') == 'agent-main'
    assert authenticated_client.put('/api/v1/tenants/kv/prompt-templates', json={}).status_code == 403
    assert authenticated_client.patch(f"/api/v1/models/{saved['id']}", json={'display_name': 'forbidden'}).status_code == 403


def test_subagent_models_participate_in_usage_copy_owner_and_delete_protection(authenticated_client):
    owner = os.environ['TEST_PLATFORM_USER']
    child_model = save_model(owner, 'specialist-model')
    selected = {'subagents': [{'name': 'specialist', 'description': 'Review records', 'model_id': child_model['id']}]}
    agent = config.save_agent({'name': 'Parent', 'config': selected}, owner)
    copied = config.copy_agent(agent['id'], owner)
    usage = authenticated_client.get(f"/api/v1/models/{child_model['id']}/usage").json['data']
    assert usage['agent_total'] == 2
    assert {row['id'] for row in usage['agents']} == {agent['id'], copied['id']}
    assert all(row['bindings'] == ['subagent:specialist:model'] for row in usage['agents'])
    assert authenticated_client.delete(f"/api/v1/models/{child_model['id']}").status_code == 400
    config.delete_agent(agent['id'], owner)
    config.delete_agent(copied['id'], owner)
    assert authenticated_client.delete(f"/api/v1/models/{child_model['id']}").status_code == 200

    foreign = save_model('another-owner', 'foreign')
    selected['subagents'][0]['model_id'] = foreign['id']
    with pytest.raises(StoreError) as error:
        config.save_agent({'name': 'Foreign child', 'config': selected}, owner)
    assert error.value.status == 404
