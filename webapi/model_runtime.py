"""Draft connection checks using the same chat assembly and official API client."""
import copy
import asyncio
import io
import json
import math
import time
from urllib.parse import urlsplit
import wave

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from agent import registry
from agent.models import embed_model, rerank_model, transcribe_model, remote_model_name, model_capabilities
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
               'extraConfig': 'extra_config', 'spec': 'spec'}
    for incoming, field in aliases.items():
        if incoming in body:
            parameters[field] = body[incoming]
    for incoming, field in (('dimension', 'dimension'), ('supportsDimensionOverride', 'supports_dimension_override')):
        if incoming in body:
            parameters.setdefault('embedding_parameters', {})[field] = body[incoming]
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
        elif kind == 'Embedding':
            vectors = _vectors(embed_model(value, ['connection check']), 1)
            result['dimension'] = len(vectors[0])
        elif kind == 'ASR':
            sample = io.BytesIO()
            with wave.open(sample, 'wb') as audio:
                audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
                audio.writeframes(b'\0\0' * 16000)
            output = transcribe_model(value, ('connection-check.wav', sample.getvalue(), 'audio/wav'), timeout=30)
            if not isinstance(output.text, str):
                raise ValueError('Invalid transcription response')
        else:
            matches = rerank_model(value, 'connection check', ['connection check', 'unrelated example'], top_n=1).results
            if not matches or not isinstance(matches[0].get('index'), int):
                raise ValueError('Invalid rerank response')
        return jsonify(success=True, data={'available': True, 'message': '模型接口已实际响应', **result})
    except StoreError:
        raise
    except Exception as exc:
        return jsonify(success=True, data={'available': False, 'message': f'模型接口测试失败（{type(exc).__name__}）'})


def _vectors(response, count):
    data = sorted(response.data, key=lambda item: item['index'])
    vectors = [item['embedding'] for item in data]
    if len(vectors) != count or [item['index'] for item in data] != list(range(count)) or any(
            not vector or any(type(value) not in (int, float) or not math.isfinite(value) for value in vector) for vector in vectors):
        raise ValueError('Invalid embedding response')
    return vectors


def debug_nonchat_model(saved, body, options, upload):
    query = body.get('input', '')
    if not isinstance(query, str) or len(query) > 100000:
        raise StoreError('调试输入无效', 400)
    documents = body.get('documents', [])
    if isinstance(documents, str):
        try:
            documents = json.loads(documents)
        except ValueError as exc:
            raise StoreError('documents 必须为 JSON 字符串数组', 400) from exc
    if not isinstance(documents, list) or len(documents) > 100 or any(not isinstance(item, str) for item in documents):
        raise StoreError('documents 必须为最多 100 项的字符串数组', 400)
    if not isinstance(options.get('similarity', False), bool):
        raise StoreError('similarity 必须为布尔值', 400)
    kind = saved['type']
    if upload and kind in ('Embedding', 'Rerank'):
        raise StoreError('当前 LiteLLM 适配尚未接入图片向量或图片重排，请使用文本输入', 501)
    if kind == 'ASR' and not upload:
        raise StoreError('请提供音频文件', 400)
    if kind == 'Embedding' and (not query.strip() or options.get('similarity') and not documents):
        raise StoreError('请提供向量查询文本及相似度候选', 400)
    if kind == 'Rerank' and (not query.strip() or not documents):
        raise StoreError('重排需要查询文本和候选文档', 400)
    data = upload.read(25 * 1024 * 1024 + 1) if upload else None
    if data is not None and (not data or len(data) > 25 * 1024 * 1024):
        raise StoreError('音频大小须为 1 B 至 25 MB', 413)
    request_info = {'model': remote_model_name(saved), 'input': query, 'documents': documents,
        'options': dict(options), 'file_attached': bool(upload)}
    observations = {'api': model_capabilities(saved)['api']}
    started = time.monotonic()
    try:
        if kind == 'Embedding':
            vector = _vectors(embed_model(saved, [query]), 1)[0]
            observations['dimension'] = len(vector)
            if options.get('similarity'):
                candidates = _vectors(embed_model(saved, documents), len(documents))
                results = []
                for index, candidate in enumerate(candidates):
                    if len(candidate) != len(vector):
                        raise ValueError('Embedding dimensions differ')
                    norm = math.sqrt(sum(value * value for value in vector)) * math.sqrt(sum(value * value for value in candidate))
                    results.append({'index': index, 'kind': 'text', 'content': documents[index],
                        'similarity': sum(left * right for left, right in zip(vector, candidate)) / norm if norm else 0})
                results.sort(key=lambda item: item['similarity'], reverse=True)
                native = {'results': results}
                observations['result_count'] = len(results)
            else:
                native = vector
        elif kind == 'Rerank':
            native = rerank_model(saved, query, documents).results
            if not isinstance(native, list):
                raise ValueError('Invalid rerank response')
            observations['result_count'] = len(native)
        else:
            output = transcribe_model(saved, (secure_filename(upload.filename or 'voice.wav'), data, upload.mimetype))
            native = output.model_dump(exclude_none=True)
            if not isinstance(native.get('text'), str):
                raise ValueError('Invalid transcription response')
            observations.update(text_characters=len(native['text']), segment_count=len(native.get('segments') or []))
        result = {'ok': True, 'raw_response': native}
    except StoreError:
        raise
    except Exception as exc:
        result = {'ok': False, 'raw_response': None, 'error': f'模型调试失败（{type(exc).__name__}）'}
    return jsonify(success=True, data={**result, 'request': request_info, 'observations': observations,
        'elapsed_ms': round((time.monotonic() - started) * 1000)})


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
