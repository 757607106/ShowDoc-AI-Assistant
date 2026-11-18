"""Draft connection checks using the same chat assembly and official API client."""
import copy
import asyncio
import io
import json
import math
import time
import wave

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from agent import registry
from agent.models import validate_model_runtime
from agent.model_transport import embed_model, rerank_model, transcribe_model
from governance.store import StoreError
from webapi.auth import user_id

model_runtime_bp = Blueprint('model_runtime', __name__)


def draft_model(body, owner, model_type):
    if not isinstance(body, dict):
        raise StoreError('模型测试请求必须是 JSON 对象', 400)
    saved = {}
    if model_id := body.get('modelId'):
        if not isinstance(model_id, str):
            raise StoreError('模型 ID 无效', 400)
        saved = registry.model_record(model_id, owner)
        if saved.get('is_builtin'):
            from webapi.runtime_settings import _require_model_edit
            _require_model_edit(saved)
        saved['parameters'] = {**saved.get('parameters', {}), **registry.secrets(saved)}
        (saved['parameters'].get('extra_config') or {}).pop('secret_key', None)
    previous = saved.get('parameters', {})
    parameters = copy.deepcopy(previous)
    if body.get('source') == 'remote' and saved.get('source') == 'local':
        parameters.pop('interface_type', None)
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
    if not isinstance(name, str) or not name.strip():
        raise StoreError("Key: 'ModelTestRequest.ModelName' Error:Field validation for 'ModelName' failed on the 'required' tag", 400)
    parameters['model_name'] = name.strip()
    value = {'name': name.strip(), 'type': model_type, 'source': body.get('source', saved.get('source', 'remote')), 'parameters': parameters}
    resolved = validate_model_runtime(value)
    if not resolved['base_url']:
        raise StoreError('请提供模型 API 地址', 400)
    # Stored credentials follow the record through provider/base edits, matching
    # the official fillSecretsFromStoredModel: only extra_config secrets are
    # vendor-scoped, api_key/app_secret refill unconditionally when omitted.
    for field, incoming in (('api_key', 'apiKey'), ('app_secret', 'appSecret'), ('custom_headers', 'customHeaders')):
        submitted = body.get(incoming)
        if incoming not in body or submitted in ('', registry.MASKED):
            parameters[field] = previous.get(field) or ({} if field == 'custom_headers' else None)
        elif field == 'custom_headers':
            if not isinstance(submitted, dict) or any(not isinstance(key, str) or not isinstance(value, str) for key, value in submitted.items()):
                raise StoreError('自定义请求头须为字符串映射', 400)
            parameters[field] = {key: (previous.get(field) or {}).get(key, '') if value == registry.MASKED else value
                                 for key, value in submitted.items()}
        elif not isinstance(submitted, str):
            raise StoreError('模型凭据须为字符串', 400)
    from agent.model_http import validate_model_address
    validate_model_address(resolved['base_url'])
    return value


def _check(kind):
    from webapi.runtime_settings import _require_model_admin
    _require_model_admin()
    value = draft_model(request.get_json(silent=True), user_id(), kind)
    try:
        result = {}
        message = '连接正常，模型可用'
        if kind == 'KnowledgeQA':
            from agent.graph import build_model_record
            model = build_model_record(value, {'temperature': 0, 'max_completion_tokens': 1, 'llm_call_timeout': 30,
                                               'thinking': False})
            async def query():
                async with asyncio.timeout(30):
                    return await model.ainvoke('test')
            asyncio.run(query())
        elif kind == 'Embedding':
            if value['parameters'].get('provider') == 'aliyun' and any(word in value['name'].lower() for word in ('vision', 'multimodal')):
                return jsonify(success=True, data={'available': False, 'dimension': 0,
                    'message': '阿里云多模态 Embedding 模型暂不支持，请使用纯文本 Embedding 模型（如 text-embedding-v4）'})
            vectors = embed_model(value, ['hello'])
            result['dimension'] = len(vectors[0])
            message = f'测试成功，向量维度={len(vectors[0])}'
        elif kind == 'ASR':
            sample = io.BytesIO()
            with wave.open(sample, 'wb') as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(16000)
                audio.writeframes(b'\0\0' * 16000)
            transcription = transcribe_model(value, ('connection-check.wav', sample.getvalue(), 'audio/wav'), timeout=30)
            message = 'ASR连接成功' + (f'，转写结果: {transcription["text"]}' if transcription.get('text') else '')
        else:
            matches = rerank_model(value, 'ping', ['pong'], top_n=1)
            if not matches or not isinstance(matches[0].get('index'), int):
                return jsonify(success=True, data={'available': False, 'message': '重排接口连接成功，但未返回重排结果'})
            message = f'重排功能正常，返回{len(matches)}个结果'
        return jsonify(success=True, data={'available': True, 'message': message, **result})
    except StoreError:
        raise
    except Exception as exc:
        response = getattr(exc, 'response', None)
        status = getattr(response, 'status_code', None) or getattr(exc, 'status_code', None) or getattr(exc, 'code', None)
        error = str(exc).lower()
        if status and getattr(response, 'text', None):
            error += ' ' + response.text[:1024].lower()
        bad_key = status == 401 or any(marker in error for marker in (
            'api_key_invalid', 'api key not valid', 'invalid api key', 'invalid_api_key', 'unauthorized', 'authentication'))
        if kind == 'KnowledgeQA' and status == 400 and not bad_key:
            return jsonify(success=True, data={'available': True, 'message': '连接正常，模型可用'})
        elif bad_key:
            message = '认证失败，请检查 API Key'
        elif status in (403, 404):
            message = '权限不足，请检查密钥权限' if status == 403 else '接口不存在，请检查 Base URL 和模型名称'
        elif 'timeout' in type(exc).__name__.lower() or 'timeout' in error:
            message = '请求超时，请检查网络连接'
        elif kind == 'ASR' and 'model' in error and 'not found' in error:
            message = '模型不存在，请检查模型名称'
        elif kind == 'ASR' and isinstance(status, int):
            return jsonify(success=True, data={'available': True, 'message': f'ASR端点可达（HTTP {status}）'})
        else:
            message = f'模型接口测试失败（{type(exc).__name__}）'
        if isinstance(status, int):
            message += f'（HTTP {status}）'
        return jsonify(success=True, data={'available': False, 'message': message, **({'dimension': 0} if kind == 'Embedding' else {})})


def debug_preview(saved, query, options, *, documents=None, upload=None, size=0):
    params = saved['parameters']
    preview = {'model_id': saved['id'], 'model_name': saved['name'], 'model_type': saved['type'],
               'source': saved['source'], 'provider': params.get('provider', ''), 'input': query, 'options': options}
    if documents:
        preview['documents'] = documents
    if upload:
        preview['file'] = {'name': upload.filename, 'size': size}
    if params.get('extra_config'):
        sensitive = ('secret', 'token', 'password', 'api_key', 'apikey', 'authorization')
        preview['model_extra_config'] = {k: '[REDACTED]' if any(part in k.lower() for part in sensitive) else v
                                         for k, v in params['extra_config'].items()}
    if params.get('custom_headers'):
        preview['custom_header_names'] = list(params['custom_headers'])
    return preview


async def debug_chat_stream(model, messages):
    from webapi.weknora_adapter import message_dict, reasoning_text, text
    events = []
    result = None
    async for chunk in model.astream(messages):
        item = message_dict(chunk)
        for kind, delta in (('thinking', reasoning_text(item)), ('answer', text(chunk.content))):
            if delta:
                events.append({'id': chunk.id or '', 'response_type': kind, 'content': delta, 'done': False})
        result = chunk if result is None else result + chunk
    if result is None:
        raise ValueError('Empty model response')
    item = message_dict(result)
    final = {'id': result.id or '', 'response_type': 'answer', 'content': '', 'done': True}
    raw = {'content': text(result.content), 'stream_events': events}
    if reasoning := reasoning_text(item):
        raw['reasoning_content'] = reasoning
    if calls := result.tool_calls:
        raw['tool_calls'] = final['tool_calls'] = [
            {'id': call['id'], 'type': 'function', 'function': {'name': call['name'], 'arguments': json.dumps(call['args'], ensure_ascii=False)}}
            for call in calls]
    if reason := result.response_metadata.get('finish_reason') or result.response_metadata.get('stop_reason'):
        raw['finish_reason'] = final['finish_reason'] = reason
    if usage := result.usage_metadata:
        details = usage.get('input_token_details') or {}
        reported = any(key in details for key in ('cache_read', 'cache_creation'))
        read = details.get('cache_read', 0)
        tokens = {'prompt_tokens': usage['input_tokens'], 'completion_tokens': usage['output_tokens'],
                  'total_tokens': usage['total_tokens'], 'cache_reported': reported,
                  'cache_status': ('hit' if read else 'miss') if reported else 'unreported'}
        if read:
            tokens.update(cache_read_tokens=read, cached_tokens=read)
        if details.get('cache_creation'):
            tokens['cache_write_tokens'] = details['cache_creation']
        raw['usage'] = final['usage'] = tokens
    events.append(final)
    return raw


def debug_nonchat_model(saved, body, options, upload):
    query = body.get('input', '')
    if not isinstance(query, str) or len(query.encode()) > 64 * 1024:
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
    if kind == 'ASR' and not upload:
        raise StoreError('请提供音频文件', 400)
    similarity = options.get('similarity', False)
    if kind == 'Embedding':
        if similarity and (not query.strip() or not (documents or upload)):
            raise StoreError('请提供查询文本和相似度候选', 400)
        if not similarity and bool(query.strip()) == bool(upload):
            raise StoreError('请选择文本或图片进行向量调试', 400)
    if kind == 'Rerank' and (not query.strip() or bool(documents) == bool(upload)):
        raise StoreError('请提供查询文本和一组文本或一张图片', 400)
    data = upload.read(25 * 1024 * 1024 + 1) if upload else None
    if data is not None and (not data or len(data) > 25 * 1024 * 1024):
        raise StoreError('文件大小须为 1 B 至 25 MB', 413)
    r = validate_model_runtime(saved)
    image = None
    if data and kind != 'ASR':
        if 'image' not in r['capabilities'].get('input', []):
            raise StoreError('模型未声明支持图片输入', 400)
        from webapi.chat_resources import debug_image
        image = debug_image(upload.filename or 'image', data, r['compat'])
    request_info = debug_preview(saved, query, options, documents=documents, upload=upload, size=len(data or b''))
    observations = {}
    started = time.monotonic()
    try:
        if kind == 'Embedding':
            if image and not similarity:
                native = embed_model(saved, [image], images=True)
                vector = native[0]
                observations['result_count'] = len(native)
            else:
                vector = embed_model(saved, [query], purpose='query' if similarity else 'document')[0]
                native = vector
            observations['dimension'] = len(vector)
            if options.get('similarity'):
                candidates = embed_model(saved, documents) if documents else []
                if image:
                    candidates.extend(embed_model(saved, [image], images=True))
                results = []
                for index, candidate in enumerate(candidates):
                    if len(candidate) != len(vector):
                        raise ValueError('Embedding dimensions differ')
                    norm = math.sqrt(sum(value * value for value in vector)) * math.sqrt(sum(value * value for value in candidate))
                    score = sum(left * right for left, right in zip(vector, candidate)) / norm if norm else 0
                    item = {'index': index, 'kind': 'text' if index < len(documents) else 'image', 'similarity': score}
                    if index < len(documents) and documents[index]:
                        item['content'] = documents[index]
                    results.append(item)
                results.sort(key=lambda item: item['similarity'], reverse=True)
                native = {'results': results}
                observations['result_count'] = len(results)
        elif kind == 'Rerank':
            native = rerank_model(saved, query, [image] if image else documents, images=bool(image))
            if not isinstance(native, list):
                raise ValueError('Invalid rerank response')
            observations['result_count'] = len(native)
        else:
            native = transcribe_model(saved, (secure_filename(upload.filename or 'voice.wav'), data, upload.mimetype))
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
