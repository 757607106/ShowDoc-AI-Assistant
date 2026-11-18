"""Supported WeKnora overrides use SDK parameters; unsupported policies fail early."""
import io
import json
import os

import pytest

from agent import config, registry
from agent.model_catalog import resolve
from agent.model_transport import embed_model, rerank_model, transcribe_model
from tests.test_platform_model_protocols import sdk_provider
from tests.test_platform_model_runtime import provider_server


def save(kind, base, compat, **parameters):
    return registry.save_model({'name': 'fixture', 'type': kind, 'parameters': {
        'provider': 'generic', 'base_url': base + '/v1', 'api_key': 'private-key',
        'spec': {'compat': compat}, **parameters}}, os.environ['TEST_PLATFORM_USER'])


def test_chat_compat_controls_real_sampling_stream_options_and_extra_body(authenticated_client, sdk_provider):
    base, calls, _ = sdk_provider
    model = save('KnowledgeQA', base, {'supports_temperature': False,
        'supports_usage_in_streaming': False, 'extra_body': {'enable_search': True}})
    response = authenticated_client.post(f"/api/v1/models/{model['id']}/debug", json={
        'input': 'debug', 'options': {'temperature': 0.5, 'top_p': 0.8}})
    assert response.status_code == 200 and response.json['data']['ok'], response.json
    payload = calls[-1]['payload']
    assert 'temperature' not in payload and 'top_p' not in payload
    assert not payload.get('stream_options', {}).get('include_usage')
    assert payload['enable_search'] is True


def test_fixed_temperature_overrides_form_sampling(authenticated_client, sdk_provider):
    base, calls, _ = sdk_provider
    model = save('KnowledgeQA', base, {'fixed_temperature': 1})
    response = authenticated_client.post(f"/api/v1/models/{model['id']}/debug", json={
        'input': 'debug', 'options': {'temperature': 0.1}})
    assert response.status_code == 200 and response.json['data']['ok'], response.json
    assert calls[-1]['payload']['temperature'] == 1


def test_upstream_put_can_clear_last_compat_while_patch_preserves_omitted_spec(authenticated_client, sdk_provider):
    base, calls, _ = sdk_provider
    model = save('KnowledgeQA', base, {'fixed_temperature': 1})
    path = f"/api/v1/models/{model['id']}"
    assert authenticated_client.patch(path, json={'parameters': {'context_window': 32768}}).status_code == 400
    patched = authenticated_client.patch(path, json={'display_name': 'Renamed', 'parameters': {'context_window': 32768}})
    assert not patched.json['data']['parameters'].get('context_window')
    assert patched.status_code == 200
    assert patched.json['data']['parameters']['spec']['compat'] == {'fixed_temperature': 1}
    assert authenticated_client.post(path + '/debug', json={
        'input': 'debug', 'options': {'temperature': 0.2}}).json['data']['ok']
    assert calls[-1]['payload']['temperature'] == 1
    put = authenticated_client.put(path, json={'name': 'fixture', 'type': 'KnowledgeQA', 'source': 'remote',
        'parameters': {'provider': 'generic', 'base_url': base + '/v1'}})
    assert put.status_code == 200 and 'spec' not in put.json['data']['parameters']
    assert 'spec' not in authenticated_client.get(path).json['data']['parameters']
    assert authenticated_client.post(path + '/debug', json={
        'input': 'debug', 'options': {'temperature': 0.2}}).json['data']['ok']
    assert calls[-1]['payload']['temperature'] == 0.2


@pytest.mark.parametrize('kind,compat,status', [
    ('KnowledgeQA', {'misspelled': True}, 400),
    ('KnowledgeQA', {'max_tokens_field': []}, 400),
    ('KnowledgeQA', {'supports_temperature': 'false'}, 400),
    ('KnowledgeQA', {'fixed_temperature': True}, 400),
    ('KnowledgeQA', {'extra_body': {'model': 'different-deployment'}}, 400),
    ('KnowledgeQA', {'extra_body': {'api_base': 'https://other.invalid'}}, 400),
    ('Embedding', {'request_timeout_seconds': True}, 400),
    ('Embedding', {'dimensions_field': []}, 400),
    ('Rerank', {'extra_body': []}, 400),
    ('ASR', {'response_format': 42}, 400),
    ('ASR', {'language_param': {}}, 400),
])
def test_unsupported_or_malformed_compat_is_rejected_before_storage_or_request(authenticated_client, kind, compat, status):
    body = {'name': 'fixture', 'type': kind, 'source': 'remote', 'parameters': {'provider': 'generic',
        'base_url': 'https://model.invalid/v1', 'spec': {'compat': compat}}}
    response = authenticated_client.post('/api/v1/models', json=body)
    assert response.status_code == status
    assert registry.records('model', os.environ['TEST_PLATFORM_USER']) == []
    path = {'KnowledgeQA': 'remote/check', 'Embedding': 'embedding/test', 'Rerank': 'rerank/check', 'ASR': 'asr/check'}[kind]
    checked = authenticated_client.post('/api/v1/initialization/' + path, json={
        'modelName': 'fixture', 'baseUrl': 'https://model.invalid/v1', 'spec': {'compat': compat}})
    assert checked.status_code == status and checked.json['error']['message'] == response.json['error']['message']


def test_embedding_draft_uses_saved_native_dimension_and_wire_alias(authenticated_client, provider_server):
    base, calls = provider_server
    model = save('Embedding', base, {'send_encoding_format': True, 'extra_body': {'task': 'search_document'}},
        embedding_parameters={'dimension': 3, 'supports_dimension_override': True},
        extra_config={'remote_model_name': 'deployment-alias'})
    checked = authenticated_client.post('/api/v1/initialization/embedding/test', json={'modelId': model['id']})
    assert checked.status_code == 200 and checked.json['data']['available'], checked.json
    assert checked.json['data']['dimension'] == 3
    assert calls[-1]['payload']['model'] == 'deployment-alias'
    assert calls[-1]['payload']['dimensions'] == 3 and calls[-1]['payload']['task'] == 'search_document'
    assert calls[-1]['payload']['encoding_format'] == 'float'


@pytest.mark.parametrize('embedding', ['invalid', [], {'supports_dimension_override': 'true'}])
def test_invalid_native_embedding_parameters_are_rejected_before_save(authenticated_client, monkeypatch, embedding):
    monkeypatch.setattr('agent.model_transport._post', lambda *a, **k: pytest.fail('invalid configuration reached transport'))
    response = authenticated_client.post('/api/v1/models', json={'name': 'fixture', 'type': 'Embedding', 'source': 'remote',
        'parameters': {'provider': 'generic', 'base_url': 'https://model.invalid/v1', 'embedding_parameters': embedding}})
    assert response.status_code == 400, response.json
    assert registry.records('model', os.environ['TEST_PLATFORM_USER']) == []


def test_embedding_compat_can_omit_encoding_field(authenticated_client, provider_server):
    base, calls = provider_server
    model = save('Embedding', base, {'send_encoding_format': False})
    checked = authenticated_client.post('/api/v1/initialization/embedding/test', json={'modelId': model['id']})
    assert checked.status_code == 200 and checked.json['data']['available'], checked.json
    assert 'encoding_format' not in calls[-1]['payload']


def test_rerank_compat_omits_top_n_and_can_request_documents(authenticated_client, provider_server):
    base, calls = provider_server
    model = save('Rerank', base, {'send_top_n': False, 'send_return_documents': True})
    checked = authenticated_client.post('/api/v1/initialization/rerank/check', json={'modelId': model['id']})
    assert checked.status_code == 200 and checked.json['data']['available'], checked.json
    assert 'top_n' not in calls[-1]['payload'] and calls[-1]['payload']['return_documents'] is True


def test_actual_transcription_keeps_sdk_credentials_headers_wire_alias_and_locale(authenticated_client, provider_server):
    base, calls = provider_server
    model = save('ASR', base, {'response_format': 'verbose_json'},
        extra_config={'remote_model_name': 'speech-deployment'},
        custom_headers={'X-Fixture': 'actual-transcription', 'X-Api-Key': 'must-not-forward'})
    agent = config.save_agent({'name': 'Voice', 'config': {'audio_upload_enabled': True,
        'asr_model_id': model['id']}}, os.environ['TEST_PLATFORM_USER'])
    response = authenticated_client.post('/api/v1/sessions/transcriptions', data={
        'agent_id': agent['id'], 'locale': 'en-US', 'file': (io.BytesIO(b'fixture-audio'), 'voice.wav')})
    assert response.status_code == 200 and response.json['data']['text'] == 'fixture transcription', response.json
    wire = calls[-1]
    assert wire['path'] == '/v1/audio/transcriptions'
    assert wire['headers']['authorization'] == 'Bearer private-key'
    assert wire['headers']['x-fixture'] == 'actual-transcription' and 'x-api-key' not in wire['headers']
    assert b'speech-deployment' in wire['raw'] and b'verbose_json' in wire['raw'] and b'\r\nen\r\n' in wire['raw']
    assert 'private-key' not in str(response.json)


def test_empty_asr_response_format_uses_sdk_default(authenticated_client, provider_server):
    base, calls = provider_server
    model = save('ASR', base, {'response_format': ''})
    checked = authenticated_client.post('/api/v1/initialization/asr/check', json={'modelId': model['id']})
    assert checked.status_code == 200 and checked.json['data']['available'], checked.json
    assert b'name="response_format"' not in calls[-1]['raw']


@pytest.mark.parametrize('kind,expected', [
    ('Embedding', 'openai-embeddings'), ('ASR', 'openai-transcriptions'), ('Rerank', 'cohere-rerank'),
])
def test_explicit_generic_protocol_wins_at_vendor_hostname(kind, expected):
    saved = {'name': 'fixture', 'type': kind, 'parameters': {'provider': 'generic',
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1'}}
    assert resolve(saved)['api'] == expected
    assert resolve(saved)['base_url'] == saved['parameters']['base_url']


@pytest.mark.parametrize('kind', ['Embedding', 'Rerank'])
def test_text_only_model_rejects_images_before_request(authenticated_client, kind):
    model = save(kind, 'http://127.0.0.1:9', {})
    with pytest.raises(ValueError, match='图片'):
        if kind == 'Embedding':
            embed_model(model, [('image/png', b'test')], images=True)
        else:
            rerank_model(model, 'query', [('image/png', b'test')], images=True)
