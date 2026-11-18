"""Original model draft APIs make real requests through official clients."""
import asyncio
import json
import os

from langchain_core.tools import tool
from agent.graph import build_model_record
import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from agent import registry
from tests.test_platform_mcp_runtime import runtime_client, serve


def test_weknora_cloud_retirement(authenticated_client, provider_server):
    client = authenticated_client
    provider = 'weknoracloud'
    assert client.get(f'/api/v1/models/{provider}/status').status_code == 404
    assert client.post(f'/api/v1/{provider}/credentials', json={}).status_code == 404
    providers = {item['value'] for item in client.get('/api/v1/models/providers').json['data']}
    assert provider not in providers and 'generic' in providers
    assert client.get(f'/api/v1/models/providers/{provider}').status_code == 404

    base, calls = provider_server
    model = {'name': 'chat', 'type': 'KnowledgeQA', 'source': 'remote', 'parameters': {'provider': provider, 'base_url': base}}
    assert client.post('/api/v1/models', json=model).status_code == 400
    registry.save_record('model', {**model, '_kind': 'model', 'id': 'old-cloud'}, os.environ['TEST_PLATFORM_USER'])
    assert client.post('/api/v1/initialization/remote/check', json={'modelId': 'old-cloud'}).status_code == 400
    assert client.delete('/api/v1/models/old-cloud').status_code == 200
    assert calls == []


@pytest.fixture
def provider_server():
    calls = []
    async def endpoint(request):
        raw = await request.body()
        payload = json.loads(raw) if 'application/json' in request.headers.get('content-type', '') else {}
        calls.append({'path': request.url.path, 'headers': dict(request.headers), 'payload': payload, 'raw': raw})
        if request.headers.get('x-reject'):
            return JSONResponse({'error': {'message': request.headers.get('authorization'), 'type': 'invalid_key'}}, status_code=401)
        if request.headers.get('x-empty-audio'):
            return JSONResponse({'error': 'silent audio'}, status_code=422)
        if payload.get('stream'):
            chunks = [
                {'choices': [{'index': 0, 'delta': {'role': 'assistant', 'reasoning_content': 'Provider reasoning'}, 'finish_reason': None}]},
                {'choices': [{'index': 0, 'delta': {'tool_calls': [{'index': 0, 'id': 'lookup1', 'type': 'function', 'function': {'name': 'lookup', 'arguments': '{"query":'}}]}, 'finish_reason': None}]},
                {'choices': [{'index': 0, 'delta': {'tool_calls': [{'index': 0, 'function': {'arguments': '"fixture"}'}}]}, 'finish_reason': None}]},
                {'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'tool_calls'}]},
            ]
            return StreamingResponse(iter(['data: ' + json.dumps({'id': 'fixture', 'object': 'chat.completion.chunk', 'model': 'qwen-plus', 'created': 1, **chunk}) + '\n\n' for chunk in chunks] + ['data: [DONE]\n\n']), media_type='text/event-stream')
        if request.url.path.endswith('/embeddings'):
            return JSONResponse({'object': 'list', 'model': 'fixture', 'data': [{'object': 'embedding', 'index': 0, 'embedding': [0.1, 0.2, 0.3]}], 'usage': {'prompt_tokens': 1, 'total_tokens': 1}})
        if request.url.path.endswith('/rerank'):
            return JSONResponse({'results': [{'index': 0, 'relevance_score': 0.9}]})
        if request.url.path.endswith('/audio/transcriptions'):
            return JSONResponse({'text': 'fixture transcription'})
        return JSONResponse({'id': 'chat-fixture', 'object': 'chat.completion', 'created': 1, 'model': 'fixture',
            'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'This service reads fixture records.'}, 'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': 2, 'completion_tokens': 3, 'total_tokens': 5}})
    app = Starlette(routes=[Route('/{path:path}', endpoint, methods=['POST'])])
    with serve(app) as base:
        yield base, calls


@pytest.mark.parametrize(('path', 'expected'), [('/remote/check', '/v1/chat/completions'), ('/embedding/test', '/v1/embeddings'),
    ('/asr/check', '/v1/audio/transcriptions'), ('/rerank/check', '/v1/rerank')])
def test_draft_checks_really_call_matching_provider_endpoint(runtime_client, provider_server, path, expected):
    base, calls = provider_server
    result = runtime_client.post('/api/v1/initialization' + path, json={'modelName': 'fixture', 'baseUrl': base + '/v1',
        'apiKey': 'draft-test-key', 'provider': 'generic', 'customHeaders': {'X-Fixture': 'present'}})
    assert result.status_code == 200 and result.json['data']['available'], result.json
    assert calls[-1]['path'] == expected and calls[-1]['headers']['authorization'] == 'Bearer draft-test-key'
    assert calls[-1]['headers']['x-fixture'] == 'present'
    if 'embedding' in path:
        assert result.json['data']['dimension'] == 3
    if 'asr' in path:
        assert b'connection-check.wav' in calls[-1]['raw'] and b'RIFF' in calls[-1]['raw']


@pytest.mark.parametrize(('headers', 'available'), [({'X-Empty-Audio': '1'}, True), ({'X-Reject': '1'}, False)])
def test_asr_check_distinguishes_reachable_silent_audio_from_auth_failure(runtime_client, provider_server, headers, available):
    base, _ = provider_server
    result = runtime_client.post('/api/v1/initialization/asr/check', json={
        'modelName': 'whisper', 'baseUrl': base + '/v1', 'provider': 'generic',
        'apiKey': 'private-asr-key', 'customHeaders': headers,
    })
    assert result.status_code == 200 and result.json['data']['available'] is available
    assert b'private-asr-key' not in result.data


def test_saved_secret_is_reused_for_draft_check_across_vendor_and_base_edits(runtime_client, provider_server):
    owner = os.environ['TEST_PLATFORM_USER']
    base, calls = provider_server
    saved = registry.save_model({'name': 'fixture', 'type': 'KnowledgeQA', 'source': 'remote',
        'parameters': {'base_url': base + '/v1', 'provider': 'generic', 'api_key': 'saved-only-key'}}, owner)
    body = {'modelId': saved['id'], 'modelName': 'fixture', 'baseUrl': base + '/v1', 'provider': 'generic'}
    assert runtime_client.post('/api/v1/initialization/remote/check', json=body).json['data']['available']
    assert calls[-1]['headers']['authorization'] == 'Bearer saved-only-key'
    # Provider/base edits keep the stored credential (official fillSecretsFromStoredModel);
    # a typed key replaces it.
    assert runtime_client.post('/api/v1/initialization/remote/check', json={**body, 'provider': 'aliyun'}).json['data']['available']
    assert calls[-1]['headers']['authorization'] == 'Bearer saved-only-key'
    assert runtime_client.post('/api/v1/initialization/remote/check', json={**body, 'baseUrl': base + '/changed/v1'}).json['data']['available']
    assert calls[-1]['headers']['authorization'] == 'Bearer saved-only-key'
    assert runtime_client.post('/api/v1/initialization/remote/check', json={**body, 'apiKey': 'typed-key'}).json['data']['available']
    assert calls[-1]['headers']['authorization'] == 'Bearer typed-key'
    assert 'saved-only-key' not in str(runtime_client.post('/api/v1/initialization/remote/check', json=body).json)


def test_old_local_row_can_be_tested_and_saved_as_a_remote_model(authenticated_client, provider_server):
    base, calls = provider_server
    owner = os.environ['TEST_PLATFORM_USER']
    legacy = registry.save_record('model', {'_kind': 'model', 'name': 'old', 'type': 'KnowledgeQA',
        'source': 'local', 'parameters': {'provider': 'ollama', 'interface_type': 'ollama', 'model_name': 'old'}}, owner)
    checked = authenticated_client.post('/api/v1/initialization/remote/check', json={
        'modelId': legacy['id'], 'modelName': 'remote', 'baseUrl': base, 'provider': 'generic', 'source': 'remote'})
    assert checked.json['data']['available'] and calls[-1]['payload']['model'] == 'remote'
    assert registry.record('model', legacy['id'], owner)['source'] == 'local'
    edited = authenticated_client.put('/api/v1/models/' + legacy['id'], json={'name': 'remote', 'source': 'remote',
        'parameters': {'provider': 'generic', 'base_url': base}})
    assert edited.status_code == 200 and edited.json['data']['parameters']['interface_type'] == ''
    assert registry.model_config(legacy['id'], owner)['name'] == 'remote'


@pytest.mark.parametrize('override,draft_override', [
    ({'source': 'local'}, {'source': 'local'}),
    ({'parameters': {'interface_type': 'ollama'}}, {'interfaceType': 'ollama'}),
    ({'parameters': {'extra_config': {'api': 'responses'}}}, {'extraConfig': {'api': 'responses'}}),
])
def test_unsupported_model_configuration_is_rejected_on_save_check_and_execution(authenticated_client, runtime_client, override, draft_override):
    from agent.graph import build_model
    from governance.store import StoreError
    owner = os.environ['TEST_PLATFORM_USER']
    body = {'name': 'fixture', 'type': 'KnowledgeQA', 'source': 'remote', 'parameters': {'base_url': 'https://model.invalid/v1',
        'interface_type': 'openai', 'extra_config': {}}}
    incompatible = {**body, **override, 'parameters': {**body['parameters'], **override.get('parameters', {})}}
    rejected = authenticated_client.post('/api/v1/models', json=incompatible)
    assert rejected.status_code == 400
    assert registry.records('model', owner) == []

    accepted = authenticated_client.post('/api/v1/models', json=body)
    assert accepted.status_code == 201 and accepted.json['data']['source'] == 'remote'
    identifier = accepted.json['data']['id']
    before = registry.record('model', identifier, owner)
    updated = authenticated_client.patch(f'/api/v1/models/{identifier}', json=override)
    assert updated.status_code == 400 and registry.record('model', identifier, owner) == before
    checked = runtime_client.post('/api/v1/initialization/remote/check', json={'modelId': identifier, **draft_override})
    assert checked.status_code == 400 and checked.json['message'] == rejected.json['error']['message']

    legacy = registry.save_record('model', {**before, **incompatible}, owner)
    assert authenticated_client.get(f'/api/v1/models/{identifier}').status_code == 200
    with pytest.raises(StoreError, match=rejected.json['error']['message']) as error:
        build_model({'model_id': legacy['id']}, owner)
    assert error.value.status == 400


def test_failed_provider_is_unavailable_without_leaking_its_error_body(runtime_client, provider_server):
    base, _ = provider_server
    response = runtime_client.post('/api/v1/initialization/remote/check', json={'modelName': 'fixture', 'baseUrl': base + '/v1',
        'apiKey': 'must-stay-secret', 'customHeaders': {'X-Reject': 'yes'}})
    assert response.status_code == 200 and response.json['data']['available'] is False
    assert 'must-stay-secret' not in str(response.json)


def test_native_qwen_stream_keeps_reasoning_and_fragmented_tool_arguments(provider_server):
    base, calls = provider_server
    @tool
    def lookup(query: str) -> str:
        """Read fixture data."""
        return query
    model = build_model_record({'name': 'qwen-plus', 'type': 'KnowledgeQA', 'parameters': {
        'provider': 'aliyun', 'api_key': 'fixture', 'base_url': base + '/v1'}}, {'thinking': True})
    chunks = list(model.bind_tools([lookup]).stream('Read fixture'))
    full = chunks[0]
    for chunk in chunks[1:]:
        full += chunk
    assert full.additional_kwargs['reasoning_content'] == 'Provider reasoning'
    assert full.tool_calls[0]['args'] == {'query': 'fixture'}
    assert calls[-1]['payload']['enable_thinking'] is True
    async def read():
        return [chunk async for chunk in model.bind_tools([lookup]).astream('Read fixture async')]
    streamed = asyncio.run(read())
    assert ''.join(chunk.additional_kwargs.get('reasoning_content', '') for chunk in streamed) == 'Provider reasoning'


def test_usage_generation_uses_only_cached_metadata_and_real_configured_model(runtime_client, provider_server):
    from agent.mcp_auth import fingerprint
    from tests.test_platform_mcp_runtime import service
    owner = os.environ['TEST_PLATFORM_USER']
    base, calls = provider_server
    value = service(owner, 'http://127.0.0.1:9')
    registry.save_record('mcp-metadata', {'id': value['id'], 'fingerprint': fingerprint(value), 'snapshot': {
        'service_id': value['id'], 'tools': [{'name': 'read', 'description': 'Read records', 'inputSchema': {'type': 'object'}, 'readOnlyHint': True}],
        'instructions': 'Reference only', 'server_name': 'Fixture', 'server_description': '', 'server_version': '1', 'synced_at': 'now', 'stale': False}}, owner)
    saved = registry.save_model({'name': 'fixture', 'type': 'KnowledgeQA', 'source': 'remote',
        'parameters': {'base_url': base + '/v1', 'api_key': 'model-private-key'}}, owner)
    registry.save_record('settings', {'id': 'default-settings', 'value': {'chat_model_id': saved['id']}}, owner)
    result = runtime_client.post('/api/v1/mcp-services/fixture-service/usage-instructions/generate', json={'language': 'en-US'})
    assert result.status_code == 200 and result.json['data']['usage_instructions'] == 'This service reads fixture records.'
    prompt = calls[-1]['payload']['messages']
    assert 'Read records' in prompt[-1]['content'] and value['url'] not in prompt[-1]['content']
    assert 'model-private-key' not in str(prompt) and 'untrusted reference data' in prompt[0]['content']


def test_model_mutations_require_platform_admin(authenticated_client):
    import app as app_module
    from webapi.auth import create_user

    owner = create_user('model-editor', '模型编辑者', 'editor-pass-123', 'editor')
    client = app_module.app.test_client()
    login = client.post('/api/v1/auth/login', json={'account': 'model-editor', 'password': 'editor-pass-123'})
    client.environ_base['HTTP_AUTHORIZATION'] = 'Bearer ' + login.json['token']
    body = {'name': 'editor-model', 'type': 'KnowledgeQA', 'source': 'remote',
            'parameters': {'provider': 'generic', 'base_url': 'https://model.invalid/v1'}}

    assert client.post('/api/v1/models', json=body).status_code == 403
    saved = registry.save_model(body, owner)
    before = registry.record('model', saved['id'], owner)
    attempts = [
        ('put', f"/api/v1/models/{saved['id']}", body),
        ('patch', f"/api/v1/models/{saved['id']}", {'description': 'changed'}),
        ('delete', f"/api/v1/models/{saved['id']}", None),
        ('post', f"/api/v1/models/{saved['id']}/copy", {'display_name': 'copy'}),
        ('put', f"/api/v1/models/{saved['id']}/credentials", {'api_key': 'replacement'}),
        ('delete', f"/api/v1/models/{saved['id']}/credentials/api_key", None),
    ]
    for method, path, payload in attempts:
        response = getattr(client, method)(path, json=payload) if payload is not None else getattr(client, method)(path)
        assert response.status_code == 403, (method, path, response.json)
    assert registry.record('model', saved['id'], owner) == before
    assert len(registry.records('model', owner)) == 1
