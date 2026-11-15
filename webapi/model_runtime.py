"""Draft connection checks using the same chat assembly and official API client."""
import copy
import asyncio
import io
from urllib.parse import urlsplit
from typing import Any
import wave

from flask import Blueprint, jsonify, request
from openai import OpenAI

from agent import registry
from governance.store import StoreError
from webapi.auth import user_id

model_runtime_bp = Blueprint('model_runtime', __name__)


def _base(value):
    return value.rstrip('/').removesuffix('/chat/completions')


def draft_model(body, owner, model_type):
    if not isinstance(body, dict):
        raise StoreError('模型测试请求必须是 JSON 对象', 400)
    saved = registry.model_config(body['modelId'], owner) if body.get('modelId') else {}
    previous = saved.get('parameters', {})
    parameters = copy.deepcopy(previous)
    aliases = {'modelName': 'model_name', 'baseUrl': 'base_url', 'apiKey': 'api_key', 'appSecret': 'app_secret',
               'provider': 'provider', 'interfaceType': 'interface_type', 'customHeaders': 'custom_headers',
               'extraConfig': 'extra_config', 'spec': 'spec', 'dimension': 'dimension',
               'supportsDimensionOverride': 'supports_dimension_override'}
    for incoming, field in aliases.items():
        if incoming in body:
            parameters[field] = body[incoming]
    name = parameters.get('model_name') or saved.get('name')
    base = parameters.get('base_url')
    if not isinstance(name, str) or not name.strip() or not isinstance(base, str):
        raise StoreError('模型名称和 Base URL 不能为空', 400)
    try:
        parsed = urlsplit(base)
        parsed.port
    except ValueError as exc:
        raise StoreError('模型 API 地址无效', 400) from exc
    if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise StoreError('模型 API 地址无效', 400)
    parameters['base_url'] = _base(base)
    vendor = lambda provider: 'aliyun' if provider in ('aliyun', 'dashscope') else provider or 'generic'
    same_vendor = _base(previous.get('base_url', '')) == parameters['base_url'] and vendor(previous.get('provider')) == vendor(parameters.get('provider'))
    for field, incoming in (('api_key', 'apiKey'), ('app_secret', 'appSecret'), ('custom_headers', 'customHeaders')):
        submitted = body.get(incoming)
        if incoming not in body or submitted in ('', registry.MASKED):
            inherited = previous.get(field) if same_vendor else None
            parameters[field] = (inherited or {}) if field == 'custom_headers' else inherited
        elif field == 'custom_headers':
            if not isinstance(submitted, dict) or any(not isinstance(key, str) or not isinstance(value, str) for key, value in submitted.items()):
                raise StoreError('自定义请求头须为字符串映射', 400)
            parameters[field] = {key: (previous.get(field) or {}).get(key, '') if value == registry.MASKED and same_vendor else value
                                 for key, value in submitted.items()}
        elif not isinstance(submitted, str):
            raise StoreError('模型凭据须为字符串', 400)
    from agent.models import validate_model_runtime
    value = {'name': name.strip(), 'type': model_type, 'source': body.get('source', saved.get('source', 'remote')), 'parameters': parameters}
    validate_model_runtime(value)
    return value


def _client(value):
    params = value['parameters']
    headers = {key: item for key, item in (params.get('custom_headers') or {}).items()
               if key.lower() not in ('host', 'authorization', 'content-type')}
    return OpenAI(base_url=params['base_url'], api_key=params.get('api_key') or 'not-required',
                  default_headers=headers, timeout=30, max_retries=0)


def _check(kind):
    value = draft_model(request.get_json(silent=True), user_id(), kind)
    try:
        result = {}
        if kind == 'KnowledgeQA':
            from agent.graph import build_model_record
            model = build_model_record(value, {'temperature': 0, 'max_completion_tokens': 32, 'llm_call_timeout': 30,
                                               'thinking': False})
            async def query():
                async with asyncio.timeout(30):
                    return await model.ainvoke('Reply with OK.')
            output = asyncio.run(query())
            if not output.content and not output.additional_kwargs.get('reasoning_content'):
                raise ValueError('Empty model response')
        else:
            with _client(value) as client:
                if kind == 'Embedding':
                    dimension = value['parameters'].get('dimension')
                    extra = {}
                    if value['parameters'].get('supports_dimension_override'):
                        if isinstance(dimension, bool) or not isinstance(dimension, int) or not 1 <= dimension <= 65536:
                            raise StoreError('Embedding dimension 必须为正整数', 400)
                        extra['dimensions'] = dimension
                    vector = client.embeddings.create(model=value['name'], input=['connection check'], encoding_format='float', **extra)
                    if not vector.data or not vector.data[0].embedding:
                        raise ValueError('Empty embedding response')
                    result['dimension'] = len(vector.data[0].embedding)
                elif kind == 'ASR':
                    sample = io.BytesIO()
                    with wave.open(sample, 'wb') as audio:
                        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
                        audio.writeframes(b'\0\0' * 16000)
                    output = client.audio.transcriptions.create(model=value['name'], file=('connection-check.wav', sample.getvalue(), 'audio/wav'))
                    if not isinstance(output.text, str):
                        raise ValueError('Invalid transcription response')
                else:
                    ranked = client.post('/rerank', cast_to=dict[str, Any], body={'model': value['name'], 'query': 'connection check',
                        'documents': ['connection check', 'unrelated example'], 'top_n': 1})
                    matches = ranked.get('results')
                    if not isinstance(matches, list) or not matches or not isinstance(matches[0].get('index'), int):
                        raise ValueError('Invalid rerank response')
        return jsonify(success=True, data={'available': True, 'message': '模型接口已实际响应', **result})
    except StoreError:
        raise
    except Exception as exc:
        return jsonify(success=True, data={'available': False, 'message': f'模型接口测试失败（{type(exc).__name__}）'})


@model_runtime_bp.post('/api/v1/initialization/remote/check')
def remote():
    return _check('KnowledgeQA')


@model_runtime_bp.post('/api/v1/initialization/asr/check')
def asr():
    return _check('ASR')


@model_runtime_bp.post('/api/v1/initialization/embedding/test')
def embedding():
    return _check('Embedding')


@model_runtime_bp.post('/api/v1/initialization/rerank/check')
def rerank():
    return _check('Rerank')
