"""Vendor-specific model configuration exercised on the wire without paid credentials."""
import httpx
import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from agent.model_catalog import provider_option
from agent.model_http import ModelTransport
from agent.model_transport import embed_model, rerank_model, transcribe_model
from governance.store import StoreError
from tests.test_platform_mcp_runtime import serve


@pytest.fixture
def provider():
    calls, reply = [], {}
    async def endpoint(request):
        calls.append((request.url.path, await request.json(), dict(request.headers)))
        return JSONResponse(reply['json'])
    with serve(Starlette(routes=[Route('/{path:path}', endpoint, methods=['POST'])])) as address:
        yield address, calls, reply


@pytest.mark.parametrize('vendor,name,expected_path,reply_body', [
    ('gemini', 'gemini-embedding-001', '/v1beta/models/gemini-embedding-001:batchEmbedContents', {'embeddings': [{'values': [1.0]}]}),
    ('aliyun', 'tongyi-embedding-vision-plus', '/api/v1/services/embeddings/multimodal-embedding/multimodal-embedding',
     {'output': {'embeddings': [{'index': 0, 'embedding': [1.0]}]}}),
    ('volcengine', 'doubao-embedding-vision-251215', '/api/v3/embeddings/multimodal', {'data': {'embedding': [1.0]}}),
    ('jina', 'jina-embeddings-v4', '/v1beta/embeddings', {'data': [{'index': 0, 'embedding': [1.0]}]}),
])
def test_vendor_embedding_formats(provider, vendor, name, expected_path, reply_body):
    base, calls, reply = provider
    reply['json'] = reply_body
    url = base if vendor in ('aliyun', 'volcengine') else base + '/v1beta'
    saved = {'name': name, 'type': 'Embedding', 'parameters': {'provider': vendor, 'base_url': url,
        'api_key': 'fixture', 'embedding_parameters': {'dimension': 256, 'supports_dimension_override': True}}}
    if vendor == 'gemini':
        saved['parameters']['spec'] = {'compat': {'input_type_field': 'taskType', 'input_type_values': {'query': 'RETRIEVAL_QUERY'}}}
    image = ('image/png', b'fixture')
    use_image = vendor != 'gemini'
    assert embed_model(saved, [image] if use_image else ['hello'], images=use_image, purpose='query') == [[1.0]]
    path, body, headers = calls.pop()
    assert path == expected_path
    if vendor == 'gemini':
        assert body['requests'][0]['embedContentConfig'] == {'taskType': 'RETRIEVAL_QUERY', 'outputDimensionality': 256}
        assert headers['x-goog-api-key'] == 'fixture'
    elif vendor == 'aliyun':
        assert body['input']['contents'][0]['image'].startswith('data:image/png;base64,')
        assert 'parameters' not in body  # This Tongyi catalog row has a fixed output width.
    elif vendor == 'volcengine':
        assert body['input'][0]['image_url']['url'].startswith('data:image/png;base64,')
    else:
        assert body['input'][0]['image'].startswith('data:image/png;base64,')


@pytest.mark.parametrize('vendor,body_key,path,reply_body', [
    ('cohere', 'documents', '/rerank', [{'index': 0, 'score': 0.8}]),
    ('aliyun', 'input', '/', {'output': {'results': [{'index': 0, 'relevance_score': 0.8}]}}),
    ('huggingface_tei', 'texts', '/rerank', [{'index': 0, 'score': 0.8}]),
    ('nvidia', 'passages', '/', {'rankings': [{'index': 0, 'logit': 0}]}),
    ('pinecone', 'rank_fields', '/rerank', {'data': [{'index': 0, 'score': 0.8}]}),
    ('lkeap', 'Docs', '/', {'Response': {'ScoreList': [0.8]}}),
    ('volcengine', 'datas', '/api/knowledge/service/rerank', {'code': 0, 'data': {'scores': [0.8]}}),
])
def test_vendor_rerank_formats_and_signatures(provider, vendor, body_key, path, reply_body):
    base, calls, reply = provider
    reply['json'] = reply_body
    saved = {'name': 'fixture', 'type': 'Rerank', 'parameters': {'provider': vendor, 'base_url': base,
        'api_key': 'fixture-id', 'app_secret': 'fixture-secret', 'custom_headers': {'X-Tenant': 'fixture'}}}
    result = rerank_model(saved, 'query', ['doc'])
    assert result == [{'index': 0, 'relevance_score': 0.5 if vendor == 'nvidia' else 0.8, 'document': {'text': 'doc'}}]
    actual_path, body, headers = calls.pop()
    assert actual_path == path and body_key in body and headers['x-tenant'] == 'fixture'
    if vendor in ('lkeap', 'volcengine'):
        assert 'Credential=fixture-id/' in headers['authorization'] and 'Signature=' in headers['authorization']
        assert 'fixture-secret' not in str(headers) + str(body)


def test_audio_chat_and_model_catalog(provider):
    base, calls, reply = provider
    reply['json'] = {'choices': [{'message': {'content': '转写'}}], 'usage': {'seconds': 1.5}}
    saved = {'name': 'qwen3-asr-flash', 'type': 'ASR', 'parameters': {'provider': 'aliyun', 'base_url': base}}
    assert transcribe_model(saved, ('a.wav', b'wav', 'audio/wav'), language='zh') == {'text': '转写', 'duration': 1.5}
    path, body, _ = calls.pop()
    assert path == '/chat/completions' and body['asr_options'] == {'language': 'zh'}
    assert body['messages'][0]['content'][0]['input_audio']['data'].startswith('data:audio/wav;base64,')
    listed = provider_option('aliyun', 'chat', True)
    assert next(row['name'] for row in listed['models'] if row['id'] == 'qwen3.8-max') == 'Qwen3.8 Max'
    assert all('image' in row['input'] for row in provider_option('aliyun', 'vllm', True)['models'])


def test_private_destinations_and_cross_origin_requests_require_explicit_configuration(monkeypatch):
    monkeypatch.delenv('SSRF_WHITELIST', raising=False)
    monkeypatch.delenv('SSRF_WHITELIST_EXTRA', raising=False)
    transport = ModelTransport('http://127.0.0.1')
    request = httpx.Request('GET', 'http://127.0.0.1/test')
    with pytest.raises(StoreError, match='SSRF_WHITELIST_EXTRA'):
        transport.pinned(request)
    monkeypatch.setenv('SSRF_WHITELIST_EXTRA', '127.0.0.0/8')
    assert transport.pinned(request).url == request.url
    with pytest.raises(StoreError, match='端点'):
        transport.pinned(httpx.Request('GET', 'http://localhost/test'))
