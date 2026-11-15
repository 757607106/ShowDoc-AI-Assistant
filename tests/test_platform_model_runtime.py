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


@pytest.fixture
def provider_server():
    calls = []
    async def endpoint(request):
        raw = await request.body()
        payload = json.loads(raw) if 'application/json' in request.headers.get('content-type', '') else {}
        calls.append({'path': request.url.path, 'headers': dict(request.headers), 'payload': payload, 'raw': raw})
        if request.headers.get('x-reject'):
            return JSONResponse({'error': {'message': request.headers.get('authorization'), 'type': 'invalid_key'}}, status_code=401)
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


def test_saved_secret_is_reused_only_at_same_provider_endpoint(runtime_client, provider_server):
    owner = os.environ['TEST_PLATFORM_USER']
    base, calls = provider_server
    saved = registry.save_model({'name': 'fixture', 'type': 'KnowledgeQA', 'source': 'remote',
        'parameters': {'base_url': base + '/v1', 'provider': 'generic', 'api_key': 'saved-only-key'}}, owner)
    body = {'modelId': saved['id'], 'modelName': 'fixture', 'baseUrl': base + '/v1', 'provider': 'generic'}
    assert runtime_client.post('/api/v1/initialization/remote/check', json=body).json['data']['available']
    assert calls[-1]['headers']['authorization'] == 'Bearer saved-only-key'
    assert runtime_client.post('/api/v1/initialization/remote/check', json={**body, 'baseUrl': base + '/changed/v1'}).json['data']['available']
    assert calls[-1]['headers']['authorization'] == 'Bearer not-required'
    assert 'saved-only-key' not in str(runtime_client.post('/api/v1/initialization/remote/check', json=body).json)


@pytest.mark.parametrize('override,draft_override', [
    ({'source': 'local'}, {'source': 'local'}),
    ({'parameters': {'interface_type': 'ollama'}}, {'interfaceType': 'ollama'}),
    ({'parameters': {'extra_config': {'api': 'responses'}}}, {'extraConfig': {'api': 'responses'}}),
])
def test_unsupported_model_configuration_is_rejected_on_save_check_and_execution(authenticated_client, runtime_client, override, draft_override):
    from agent.graph import build_model
    from governance.store import StoreError
    owner = os.environ['TEST_PLATFORM_USER']
    body = {'name': 'fixture', 'parameters': {'base_url': 'https://model.invalid/v1',
        'interface_type': 'openai', 'extra_config': {}}}
    incompatible = {**body, **override, 'parameters': {**body['parameters'], **override.get('parameters', {})}}
    rejected = authenticated_client.post('/api/v1/models', json=incompatible)
    assert rejected.status_code == 501
    assert registry.records('model', owner) == []

    accepted = authenticated_client.post('/api/v1/models', json=body)
    assert accepted.status_code == 200 and accepted.json['data']['source'] == 'remote'
    identifier = accepted.json['data']['id']
    before = registry.record('model', identifier, owner)
    updated = authenticated_client.patch(f'/api/v1/models/{identifier}', json=override)
    assert updated.status_code == 501 and registry.record('model', identifier, owner) == before
    checked = runtime_client.post('/api/v1/initialization/remote/check', json={'modelId': identifier, **draft_override})
    assert checked.status_code == 501 and checked.json['message'] == rejected.json['message']

    legacy = registry.save_record('model', {**before, **incompatible}, owner)
    assert authenticated_client.get(f'/api/v1/models/{identifier}').status_code == 200
    with pytest.raises(StoreError, match=rejected.json['message']) as error:
        build_model({'model_id': legacy['id']}, owner)
    assert error.value.status == 501


def test_failed_provider_is_unavailable_without_leaking_its_error_body(runtime_client, provider_server):
    base, _ = provider_server
    response = runtime_client.post('/api/v1/initialization/remote/check', json={'modelName': 'fixture', 'baseUrl': base + '/v1',
        'apiKey': 'must-stay-secret', 'customHeaders': {'X-Reject': 'yes'}})
    assert response.status_code == 200 and response.json['data']['available'] is False
    assert 'must-stay-secret' not in str(response.json)


def test_litellm_qwen_stream_keeps_reasoning_and_fragmented_tool_arguments(provider_server):
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
        'service_id': value['id'], 'tools': [{'name': 'read', 'description': 'Read records', 'inputSchema': {'type': 'object'}}],
        'instructions': 'Reference only', 'server_name': 'Fixture', 'server_description': '', 'server_version': '1', 'synced_at': 'now', 'stale': False}}, owner)
    saved = registry.save_model({'name': 'fixture', 'type': 'KnowledgeQA', 'source': 'remote',
        'parameters': {'base_url': base + '/v1', 'api_key': 'model-private-key'}}, owner)
    registry.save_record('settings', {'id': 'default-settings', 'value': {'chat_model_id': saved['id']}}, owner)
    result = runtime_client.post('/api/v1/mcp-services/fixture-service/usage-instructions/generate', json={'language': 'en-US'})
    assert result.status_code == 200 and result.json['data']['usage_instructions'] == 'This service reads fixture records.'
    prompt = calls[-1]['payload']['messages']
    assert 'Read records' in prompt[-1]['content'] and value['url'] not in prompt[-1]['content']
    assert 'model-private-key' not in str(prompt) and 'untrusted reference data' in prompt[0]['content']
