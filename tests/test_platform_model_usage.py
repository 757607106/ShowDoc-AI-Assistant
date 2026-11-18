"""Model deletion follows native usage DTOs and cannot race new bindings."""
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from agent import config, registry
from governance.store import StoreError


def model(owner, kind='KnowledgeQA'):
    return registry.save_model({'name': 'usage-fixture', 'type': kind,
        'parameters': {'base_url': 'https://model.invalid/v1', 'api_key': 'never-return-this-key'}}, owner)


def reference(field, model_id):
    return {field: model_id}


@pytest.mark.parametrize('field,binding,kind', [
    ('model_id', 'chat_model', 'KnowledgeQA'),
    ('rerank_model_id', 'rerank_model', 'Rerank'),
    ('vlm_model_id', 'vlm_model', 'VLLM'),
    ('asr_model_id', 'asr_model', 'ASR'),
    ('query_understand_model_id', 'query_understand_model', 'KnowledgeQA'),
])
def test_native_usage_and_delete_cover_every_agent_binding(authenticated_client, field, binding, kind):
    owner = os.environ['TEST_PLATFORM_USER']
    saved = model(owner, kind)
    agent = config.save_agent({'name': 'Bound agent', 'config': {
        **reference(field, saved['id']), 'system_prompt': 'never-return-this-prompt'}}, owner)
    response = authenticated_client.get(f"/api/v1/models/{saved['id']}/usage")
    assert response.status_code == 200
    usage = response.json['data']
    assert usage['in_use'] is True
    assert usage['agents'] == [{'id': agent['id'], 'name': 'Bound agent', 'bindings': [binding]}]
    assert usage['agent_total'] == 1 and usage['knowledge_base_total'] == 0
    assert usage['knowledge_bases'] == [] and usage['long_term_memory'] == {'bindings': []}
    deleted = authenticated_client.delete(f"/api/v1/models/{saved['id']}")
    assert deleted.status_code == 400 and deleted.json['error']['code'] == 2300
    assert deleted.json['error']['details']['agents'] == usage['agents']
    assert 'never-return' not in str(response.json) + str(deleted.json)
    config.save_agent({'config': {}}, owner, agent['id'])
    assert authenticated_client.delete(f"/api/v1/models/{saved['id']}").status_code == 200


def test_usage_merges_bindings_and_copy_keeps_references(authenticated_client):
    owner = os.environ['TEST_PLATFORM_USER']
    saved = model(owner)
    agent = config.save_agent({'name': 'Merged', 'config': {'model_id': saved['id'],
        'query_understand_model_id': saved['id']}}, owner)
    copied = config.copy_agent(agent['id'], owner)
    usage = authenticated_client.get(f"/api/v1/models/{saved['id']}/usage").json['data']
    assert usage['agent_total'] == 2 and len(usage['agents']) == 2
    assert {item['id'] for item in usage['agents']} == {agent['id'], copied['id']}
    assert all(item['bindings'] == ['chat_model', 'query_understand_model'] for item in usage['agents'])
    config.delete_agent(agent['id'], owner)
    assert authenticated_client.delete(f"/api/v1/models/{saved['id']}").status_code == 400


def test_usage_lists_are_capped_without_under_counting(authenticated_client):
    owner = os.environ['TEST_PLATFORM_USER']
    saved = model(owner)
    for index in range(51):
        config.save_agent({'name': f'Agent {index:02}', 'config': {'model_id': saved['id']}}, owner)
    deleted = authenticated_client.delete(f"/api/v1/models/{saved['id']}")
    details = deleted.json['error']['details']
    assert deleted.status_code == 400 and details['agent_total'] == 51
    assert len(details['agents']) == 50
    assert [item['name'] for item in details['agents']] == [f'Agent {index:02}' for index in range(50)]


def test_default_pins_keep_plain_conflict_and_file_memory_has_no_model_dependency(authenticated_client):
    owner = os.environ['TEST_PLATFORM_USER']
    saved = model(owner)
    response = authenticated_client.put('/api/v1/tenants/kv/default-settings', json={'chat_model_id': saved['id']})
    assert response.status_code == 200
    usage = authenticated_client.get(f"/api/v1/models/{saved['id']}/usage").json['data']
    assert usage['in_use'] is True and usage['agents'] == []
    deleted = authenticated_client.delete(f"/api/v1/models/{saved['id']}")
    assert deleted.status_code == 409 and 'chat_model_id' in deleted.json['message']
    assert 'error' not in deleted.json
    assert authenticated_client.put('/api/v1/tenants/kv/default-settings', json={
        'chat_model_id': 'agent-main', 'summary_model_id': 'agent-main'}).status_code == 200
    registry.save_record('settings', {'id': 'memory-config', 'value': {
        'enabled': True, 'extract_model_id': saved['id'], 'embedding_model_id': saved['id']}}, owner)
    assert authenticated_client.delete(f"/api/v1/models/{saved['id']}").status_code == 200


def test_usage_and_binding_writes_are_owner_scoped(authenticated_client):
    owner = os.environ['TEST_PLATFORM_USER']
    foreign = model('another-owner')
    assert authenticated_client.get(f"/api/v1/models/{foreign['id']}/usage").status_code == 404
    assert authenticated_client.delete(f"/api/v1/models/{foreign['id']}").status_code == 404
    for field in ('model_id', 'asr_model_id'):
        with pytest.raises(StoreError) as error:
            config.save_agent({'name': 'Invalid owner', 'config': reference(field, foreign['id'])}, owner)
        assert error.value.status == 404
    assert registry.records('agent', owner) == []
    assert registry.record('model', foreign['id'], 'another-owner')['id'] == foreign['id']


@pytest.mark.parametrize('delete_first', [False, True])
def test_binding_save_and_model_delete_serialize(authenticated_client, monkeypatch, delete_first):
    owner = os.environ['TEST_PLATFORM_USER']
    saved = model(owner)
    holder_acquired, contender_started, release = threading.Event(), threading.Event(), threading.Event()
    lock = registry._lock_model_bindings

    def controlled_lock(conn, selected_owner):
        holder = threading.current_thread().name.startswith('model-holder')
        if not holder:
            contender_started.set()
        lock(conn, selected_owner)
        if holder:
            holder_acquired.set()
            assert release.wait(10), 'test did not release the first transaction'

    monkeypatch.setattr(registry, '_lock_model_bindings', controlled_lock)

    def save():
        return config.save_agent({'name': 'Concurrent agent', 'config': {'model_id': saved['id']}}, owner)

    def delete():
        return authenticated_client.delete(f"/api/v1/models/{saved['id']}")

    first, second = (delete, save) if delete_first else (save, delete)
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix='model-holder') as holder, \
            ThreadPoolExecutor(max_workers=1, thread_name_prefix='model-contender') as contender:
        first_result = holder.submit(first)
        try:
            assert holder_acquired.wait(10)
            second_result = contender.submit(second)
            assert contender_started.wait(10)
            assert not second_result.done()
        finally:
            release.set()
        first_value = first_result.result(timeout=10)
        if delete_first:
            assert first_value.status_code == 200
            with pytest.raises(StoreError) as error:
                second_result.result(timeout=10)
            assert error.value.status == 404 and registry.records('agent', owner) == []
        else:
            assert first_value['config']['model_id'] == saved['id']
            assert second_result.result(timeout=10).status_code == 400
