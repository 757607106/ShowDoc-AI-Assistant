"""Native model debug DTOs verified against the SDK's real HTTP requests."""
import base64
import io
import json
import os
import wave
from unittest.mock import Mock

import pytest
from PIL import Image
from opensandbox.models.execd import Execution, ExecutionError, ExecutionLogs, OutputMessage

from agent import registry
from tests.test_platform_model_runtime import provider_server


def saved_model(kind, base, **parameters):
    return registry.save_model({'name': 'fixture', 'type': kind, 'parameters': {
        'provider': 'generic', 'base_url': base + '/v1', 'api_key': 'private-fixture-key',
        'extra_config': {'remote_model_name': 'deployment-alias'},
        'custom_headers': {'X-Fixture': 'present', 'X-API-Key': 'must-not-forward'},
        **parameters}}, os.environ['TEST_PLATFORM_USER'])


def audio_file():
    content = io.BytesIO()
    with wave.open(content, 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b'\0\0' * 1600)
    content.seek(0)
    return content


@pytest.mark.parametrize('kind,path', [
    ('Embedding', '/v1/embeddings'), ('Rerank', '/v1/rerank'),
    ('ASR', '/v1/audio/transcriptions'),
])
def test_non_chat_debug_uses_native_dto_and_same_sdk_destination(authenticated_client, provider_server, kind, path):
    base, calls = provider_server
    model = saved_model(kind, base, **({'embedding_parameters': {
        'dimension': 3, 'supports_dimension_override': True}} if kind == 'Embedding' else {}))
    data = {'input': 'debug input', 'documents': json.dumps(['candidate', 'other']), 'options': '{}'}
    if kind == 'ASR':
        data['file'] = (audio_file(), 'probe.wav')
    response = authenticated_client.post(f"/api/v1/models/{model['id']}/debug", data=data)
    assert response.status_code == 200, response.json
    result = response.json['data']
    assert result['ok'] is True, result
    assert isinstance(result['request'], dict) and result['elapsed_ms'] >= 0
    wire = calls[-1]
    assert wire['path'] == path
    assert wire['headers']['authorization'] == 'Bearer private-fixture-key'
    assert wire['headers']['x-fixture'] == 'present'
    assert 'x-api-key' not in wire['headers']
    assert 'private-fixture-key' not in str(response.json)
    if kind == 'Embedding':
        assert wire['payload']['model'] == 'deployment-alias'
        assert wire['payload']['dimensions'] == 3
        assert result['raw_response'] == [0.1, 0.2, 0.3]
        assert result['observations']['dimension'] == 3
    elif kind == 'Rerank':
        assert wire['payload']['model'] == 'deployment-alias'
        assert wire['payload']['documents'] == ['candidate', 'other']
        assert result['raw_response'][0]['index'] == 0
        assert result['raw_response'][0]['relevance_score'] == 0.9
        assert result['observations']['result_count'] == 1
    else:
        assert b'deployment-alias' in wire['raw'] and b'RIFF' in wire['raw']
        assert result['raw_response']['text'] == 'fixture transcription'
        assert result['observations']['text_characters'] == len('fixture transcription')


def test_chat_deployment_alias_keeps_catalog_reasoning_capability(authenticated_client, provider_server):
    base, calls = provider_server
    model = registry.save_model({'name': 'qwen-plus', 'type': 'KnowledgeQA', 'parameters': {
        'provider': 'aliyun', 'base_url': base + '/v1', 'api_key': 'private-fixture-key',
        'extra_config': {'remote_model_name': 'deployment-alias'}}}, os.environ['TEST_PLATFORM_USER'])
    public = authenticated_client.get(f"/api/v1/models/{model['id']}").json['data']
    assert public['capabilities']['reasoning'] is True
    response = authenticated_client.post(f"/api/v1/models/{model['id']}/debug", data={
        'input': 'debug reasoning', 'options': json.dumps({'thinking': True, 'max_tokens': 2048})})
    assert response.status_code == 200 and response.json['data']['ok'], response.json
    assert calls[-1]['payload']['model'] == 'deployment-alias'
    assert calls[-1]['payload']['enable_thinking'] is True
    assert response.json['data']['observations']['reasoning_returned'] is True


def test_vlm_debug_retains_validated_image_parts(authenticated_client, provider_server, monkeypatch):
    base, calls = provider_server
    model = saved_model('VLLM', base, supports_vision=True)
    picture = io.BytesIO()
    Image.new('RGB', (1, 1)).save(picture, format='PNG')
    png = picture.getvalue()
    native = Mock()
    native.commands.run.return_value = Execution(exit_code=0, logs=ExecutionLogs(
        stdout=[OutputMessage(text='{"mime":"image/png"}', timestamp=0)]))
    monkeypatch.setattr('opensandbox.SandboxSync.create', Mock(return_value=native))
    monkeypatch.setattr('agent.sandbox.connection_config', lambda: None)
    response = authenticated_client.post(f"/api/v1/models/{model['id']}/debug", data={
        'input': 'describe image', 'options': '{}', 'file': (io.BytesIO(png), 'probe.png')})
    assert response.status_code == 200 and response.json['data']['ok'], response.json
    wire = calls[-1]['payload']
    assert wire['model'] == 'deployment-alias'
    parts = wire['messages'][-1]['content']
    assert parts[0] == {'type': 'text', 'text': 'describe image'}
    assert parts[1]['type'] == 'image_url'
    assert parts[1]['image_url']['url'] == 'data:image/png;base64,' + base64.b64encode(png).decode()
    assert native.files.write_files.call_args.args[0][0].data == png
    assert native.commands.run.call_args.args[0][-1] == '--image'
    native.destroy.assert_called_once()


def test_invalid_debug_image_is_rejected_in_sandbox_before_model_call(authenticated_client, provider_server, monkeypatch):
    base, calls = provider_server
    model = saved_model('VLLM', base)
    native = Mock()
    native.commands.run.return_value = Execution(exit_code=1,
        error=ExecutionError(name='UnidentifiedImageError', value='invalid image', timestamp=0, exit_code=1))
    monkeypatch.setattr('opensandbox.SandboxSync.create', Mock(return_value=native))
    monkeypatch.setattr('agent.sandbox.connection_config', lambda: None)
    monkeypatch.setattr('PIL.Image.open', Mock(side_effect=AssertionError('host image parsing is forbidden')))
    response = authenticated_client.post(f"/api/v1/models/{model['id']}/debug", data={
        'input': 'describe image', 'options': '{}', 'file': (io.BytesIO(b'invalid image'), 'invalid.png')})
    assert response.status_code == 400 and calls == []
    native.destroy.assert_called_once()


def test_debug_image_without_sandbox_configuration_fails_closed(authenticated_client, provider_server, monkeypatch):
    base, calls = provider_server
    model = saved_model('VLLM', base)
    monkeypatch.setattr('agent.sandbox.enabled', lambda: False)
    monkeypatch.setattr('PIL.Image.open', Mock(side_effect=AssertionError('host image parsing is forbidden')))
    response = authenticated_client.post(f"/api/v1/models/{model['id']}/debug", data={
        'input': 'describe image', 'options': '{}', 'file': (io.BytesIO(b'input'), 'fixture.png')})
    assert response.status_code == 503 and calls == []


@pytest.mark.parametrize('kind', ['ASR', 'VLLM'])
def test_required_debug_media_is_rejected_before_provider_call(authenticated_client, provider_server, kind):
    base, calls = provider_server
    model = saved_model(kind, base)
    response = authenticated_client.post(f"/api/v1/models/{model['id']}/debug", data={
        'input': 'missing media', 'options': '{}'})
    assert response.status_code == 400, response.json
    assert calls == []
