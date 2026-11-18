"""Remote embedding, rerank and speech protocols used by WeKnora model settings."""
import base64
import hashlib
import hmac
import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import PurePath

import httpx

from agent.model_catalog import PROVIDERS
from agent.model_http import ModelTransport
from agent.models import model_headers, validate_model_runtime
from governance.store import StoreError


def authentication(saved, resolved):
    vendor = PROVIDERS[resolved['provider']]
    style = vendor.get('auth_by_api', {}).get(resolved['api'], vendor['auth'])
    headers = {**vendor.get('headers', {}), **model_headers(saved)}
    if key := saved['parameters'].get('api_key'):
        if style == 'bearer':
            headers['Authorization'] = 'Bearer ' + key
        elif style in ('x-api-key', 'api-key', 'x-goog-api-key'):
            headers[style] = key
    return headers


def _signed_rank_headers(req, params, protocol):
    # Both managed rerank services sign the bytes actually sent, including their host and path.
    key, secret = params.get('api_key'), params.get('app_secret')
    if not key or not secret:
        raise StoreError('重排服务需要完整的密钥对', 400)
    def digest(data):
        return hashlib.sha256(data).hexdigest()
    def sign(key_bytes, value):
        return hmac.digest(key_bytes, value.encode(), 'sha256')
    extra = params.get('extra_config', {})
    now = datetime.now(timezone.utc)
    sha = digest(req.content)
    if protocol == 'tencent-lkeap':
        date, timestamp = now.strftime('%Y-%m-%d'), str(int(now.timestamp()))
        req.headers.update({'X-TC-Action': 'RunRerank', 'X-TC-Version': '2024-05-22', 'X-TC-Timestamp': timestamp,
                            'X-TC-Region': extra.get('region') or 'ap-guangzhou'})
        fields = ['content-type', 'host']
        scope, scheme = date + '/lkeap/tc3_request', 'TC3-HMAC-SHA256'
        signing = sign(sign(sign(('TC3' + secret).encode(), date), 'lkeap'), 'tc3_request')
    else:
        date, timestamp = now.strftime('%Y%m%d'), now.strftime('%Y%m%dT%H%M%SZ')
        region = extra.get('region') or 'cn-beijing'
        req.headers.update({'X-Date': timestamp, 'X-Content-Sha256': sha})
        fields = ['content-type', 'host', 'x-content-sha256', 'x-date']
        scope, scheme = f'{date}/{region}/air/request', 'HMAC-SHA256'
        signing = sign(sign(sign(sign(secret.encode(), date), region), 'air'), 'request')
    names = ';'.join(fields)
    canonical = '\n'.join(['POST', req.url.path, '', ''.join(f'{k}:{req.headers[k]}\n' for k in fields), names, sha])
    sig = sign(signing, '\n'.join([scheme, timestamp, scope, digest(canonical.encode())])).hex()
    req.headers['Authorization'] = f'{scheme} Credential={key}/{scope}, SignedHeaders={names}, Signature={sig}'


def _post(saved, r, path, timeout, *, headers=None, **body):
    base = r['base_url'].rstrip('/')
    url = r['url'] or (base if not path or base.endswith(path) else base + '/' + path.lstrip('/'))
    req_headers = {**authentication(saved, r), **(headers or {})}
    with httpx.Client(transport=ModelTransport(base), timeout=r['compat'].get('request_timeout_seconds') or timeout) as client:
        req = client.build_request('POST', url, headers=req_headers, **body)
        if r['api'] in ('tencent-lkeap', 'volcengine-knowledge'):
            _signed_rank_headers(req, saved['parameters'], r['api'])
        retries = 3 if saved.get('type') == 'Embedding' else 0
        for attempt in range(retries + 1):
            try:
                response = client.send(req)
                break
            except (httpx.TransportError, OSError):
                if attempt == retries:
                    raise
                time.sleep(2 ** attempt)
        response.raise_for_status()
        return response.json()


def _batches(items, limit, max_chars=0, total_limit=0, fixed=0):
    lengths = [len(x) if isinstance(x, str) else 0 for x in items]
    if any((max_chars and n > max_chars) or (total_limit and fixed + n > total_limit) for n in lengths):
        raise StoreError('输入超过模型的单次请求限制', 400)
    start, used = 0, fixed
    for i, n in enumerate(lengths):
        if i > start and (limit and i - start >= limit or total_limit and used + n > total_limit):
            yield start, items[start:i]
            start, used = i, fixed
        used += n
    if items:
        yield start, items[start:]


def _data_uri(image):
    mime, data = image
    return 'data:' + mime + ';base64,' + base64.b64encode(data).decode()


def _check_images(r, images):
    compat = r['compat']
    if 'image' not in r['capabilities'].get('input', []):
        raise StoreError('模型未声明支持图片输入', 400)
    for mime, data in images:
        if compat.get('image_mime_types') and mime not in compat['image_mime_types']:
            raise StoreError('模型不支持此图片格式', 400)
        if compat.get('max_image_bytes') and len(data) > compat['max_image_bytes']:
            raise StoreError('图片超过模型大小限制', 400)


def _embedding_batch(saved, r, batch, images, purpose, timeout):
    api, c, name = r['api'], r['compat'], r['remote_model']
    emb = saved['parameters'].get('embedding_parameters') or saved['parameters']
    dim = emb.get('dimension') if emb.get('supports_dimension_override') else None
    dimensions = {c['dimensions_field']: dim} if dim and c.get('dimensions_field') else {}
    input_type = {c['input_type_field']: c.get('input_type_values', {}).get(purpose, purpose)} if c.get('input_type_field') else {}
    path = c.get('path') or '/embeddings'
    if api == 'google-embeddings':
        name = 'models/' + name.removeprefix('models/')
        parts = [{'inlineData': {'mimeType': mime, 'data': base64.b64encode(data).decode()}} for mime, data in batch] if images else [{'text': item} for item in batch]
        config = {**dimensions, **input_type}
        body = {'requests': [{'model': name, 'content': {'parts': [p]}, **({'embedContentConfig': config} if config else {})} for p in parts]}
        r = {**r, 'base_url': r['base_url'].removesuffix('/openai')}
        path = '/' + name + ':batchEmbedContents'
    elif api == 'dashscope-embeddings':
        parts = [{'image': _data_uri(item)} for item in batch] if images else [{'text': item} for item in batch]
        body = {'model': name, 'input': {'contents': parts}}
        if dimensions:
            body['parameters'] = dimensions
    else:
        body = {'model': name, **dimensions, **input_type}
        if c.get('send_encoding_format'):
            body['encoding_format'] = 'float'
        if c.get('truncate_field'):
            value = c.get('truncate_value', '')
            body[c['truncate_field']] = {'true': True, 'false': False}.get(value, value)
        if c.get('accepts_truncate_prompt_tokens'):
            body['truncate_prompt_tokens'] = emb.get('truncate_prompt_tokens') or 511
        if api == 'ark-embeddings':
            body['input'] = ([{'type': 'image_url', 'image_url': {'url': _data_uri(item)}} for item in batch]
                             if images else [{'type': 'text', 'text': item} for item in batch])
        elif (images and c.get('image_format') == 'messages') or (not images and c.get('text_as_messages')):
            conversations = []
            for item in batch:
                parts = [{'type': 'image_url', 'image_url': {'url': _data_uri(item)}}] if images else [{'type': 'text', 'text': item}]
                if images and c.get('image_prompt'):
                    parts.append({'type': 'text', 'text': c['image_prompt']})
                conversations.append([{'role': 'user', 'content': parts}])
            body['messages'] = conversations[0] if len(conversations) == 1 else conversations
        else:
            body['input'] = [{c['image_field']: _data_uri(item)} for item in batch] if images else batch
    raw = _post(saved, r, path, timeout, json={**c.get('extra_body', {}), **body})
    if api == 'google-embeddings':
        vectors = [x['values'] for x in raw['embeddings']]
    elif api == 'ark-embeddings':
        vectors = [raw['data']['embedding']]
    else:
        entries = raw['output']['embeddings'] if api == 'dashscope-embeddings' else raw['data']
        indexed = sorted((x.get('index', i), x['embedding']) for i, x in enumerate(entries))
        if [i for i,_ in indexed] != list(range(len(batch))):
            raise ValueError('Invalid embedding indices')
        vectors = [vector for _, vector in indexed]
    if len(vectors) != len(batch) or any(not isinstance(v, list) or not v or any(type(x) not in (float, int) or not math.isfinite(x) for x in v) for v in vectors):
        raise ValueError('Invalid embedding response')
    return vectors


def embed_model(saved, inputs, *, images=False, purpose='document', timeout=30):
    r = validate_model_runtime(saved)
    if saved['type'] != 'Embedding':
        raise StoreError('请选择 Embedding 模型', 400)
    c = r['compat']
    if images:
        _check_images(r, inputs)
        if r['api'] == 'openai-embeddings' and not (c.get('image_field') or c.get('image_format') == 'messages'):
            raise StoreError('此模型协议不支持图片向量', 400)
    limit = (c.get('max_image_batch_size') if images else None) or c.get('max_batch_size', 0)
    messages = c.get('image_format') == 'messages' if images else c.get('text_as_messages')
    if r['api'] == 'ark-embeddings' or (r['api'] == 'openai-embeddings' and messages and not c.get('batch_messages')):
        limit = 1
    return [v for _, batch in _batches(inputs, limit, c.get('max_input_chars', 0))
            for v in _embedding_batch(saved, r, batch, images, purpose, timeout)]


def _rank_batch(saved, r, query, docs, images, top_n, timeout):
    c, api, name = r['compat'], r['api'], r['remote_model']
    path = c.get('path') or '/rerank'
    count = min(top_n or len(docs), len(docs))
    if api == 'dashscope-rerank':
        path = c.get('path', '')
        body = {'model': name, 'input': {'query': query, 'documents': docs},
                'parameters': {'return_documents': c.get('send_return_documents', False), 'top_n': len(docs)}}
    elif api == 'tei-rerank':
        body = {'query': query, 'texts': docs, 'raw_scores': False, 'truncate': c.get('extra_body', {}).get('truncate', True)}
    elif api == 'nim-rerank':
        path = c.get('path', '')
        body = {'model': name, 'query': {'text': query}, 'passages': [{'image': _data_uri(x)} if images else {'text': x} for x in docs]}
        if c.get('truncate'):
            body['truncate'] = c['truncate']
    elif api == 'pinecone-rerank':
        body = {'model': name, 'query': query, 'documents': [{'text': x} for x in docs], 'top_n': len(docs),
                'rank_fields': ['text'], 'return_documents': False}
        if c.get('truncate'):
            body['parameters'] = {'truncate': c['truncate']}
    elif api == 'tencent-lkeap':
        path, body = '/', {'Query': query, 'Docs': docs, 'Model': name}
    elif api == 'volcengine-knowledge':
        path = '/api/knowledge/service/rerank'
        extra = saved['parameters'].get('extra_config') or {}
        body = {'datas': [{'query': query, 'content': x} for x in docs], 'rerank_model': name,
                'rerank_instruction': extra.get('instruction') or 'Whether the document answers the query or matches the content retrieval intent'}
    else:
        body = {'model': name, 'query': query, 'documents': [{c['image_field']: _data_uri(x)} for x in docs] if images else docs}
        if c.get('send_top_n'):
            body['top_n'] = count
        if c.get('send_return_documents'):
            body['return_documents'] = not images
        if trunc := (saved['parameters'].get('extra_config') or {}).get('truncate_prompt_tokens'):
            body['truncate_prompt_tokens'] = int(trunc)
    raw = _post(saved, r, path, timeout, json={**c.get('extra_body', {}), **body})
    score_key = 'relevance_score'
    if api in ('tencent-lkeap', 'volcengine-knowledge'):
        scores = raw['Response']['ScoreList'] if api == 'tencent-lkeap' else raw['data']['scores']
        if len(scores) != len(docs) or raw.get('code', 0) != 0:
            raise ValueError('Invalid rerank scores')
        rows = [{'index': i, score_key: score} for i,score in enumerate(scores)]
    elif api == 'nim-rerank':
        rows, score_key = raw['rankings'], 'logit'
    elif api == 'tei-rerank':
        rows, score_key = raw, 'score'
    elif api == 'pinecone-rerank':
        rows, score_key = raw['data'], 'score'
    else:
        rows = raw['output']['results'] if api == 'dashscope-rerank' else (raw if isinstance(raw, list) else raw['results'])
    if api in ('pinecone-rerank', 'tei-rerank', 'nim-rerank') and len(rows) != len(docs):
        raise ValueError('Incomplete rerank results')
    scale = (saved['parameters'].get('extra_config') or {}).get('score_scale') or c.get('score_scale')
    result, seen = [], set()
    for row in rows:
        idx = row['index']
        score = row.get(score_key, row.get('score')) if api == 'cohere-rerank' else row[score_key]
        if type(idx) is not int or not 0 <= idx < len(docs) or idx in seen or type(score) not in (float, int) or not math.isfinite(score):
            raise ValueError('Invalid rerank result')
        seen.add(idx)
        if scale == 'logit':
            score = 1 / (1 + math.exp(-max(-700, score)))
        echoed = row.get('document') or {}
        text = echoed.get('text') if isinstance(echoed, dict) else echoed
        result.append({'index': idx, 'relevance_score': score, 'document': {'text': '' if images else text or docs[idx]}})
    if docs and not result:
        raise ValueError('Empty rerank results')
    return result


def rerank_model(saved, query, documents, *, images=False, top_n=None, timeout=30):
    r = validate_model_runtime(saved)
    if saved['type'] != 'Rerank':
        raise StoreError('请选择 ReRank 模型', 400)
    c = r['compat']
    if images:
        _check_images(r, documents)
        if r['api'] != 'nim-rerank' and not (r['api'] == 'cohere-rerank' and c.get('image_field')):
            raise StoreError('此模型协议不支持图片重排', 400)
    if c.get('max_query_chars') and len(query) > c['max_query_chars']:
        raise StoreError('查询超过模型限制', 400)
    limit = (c.get('max_image_batch_size') if images else None) or c.get('max_documents', 0)
    batches = list(_batches(documents, limit, c.get('max_document_chars', 0), c.get('max_request_chars', 0), len(query)))
    def score(group):
        start, batch = group
        return [{**row, 'index': row['index'] + start} for row in _rank_batch(saved, r, query, batch, images, top_n, timeout)]
    if len(batches) > 1:
        with ThreadPoolExecutor(max_workers=min(c.get('max_concurrency') or 4, len(batches))) as pool:
            results = [row for ranked in pool.map(score, batches) for row in ranked]
    else:
        results = score(batches[0]) if batches else []
    return sorted(results, key=lambda row: (-row['relevance_score'], row['index']))[:top_n]


def transcribe_model(saved, file, *, language=None, timeout=120):
    r = validate_model_runtime(saved)
    if saved['type'] != 'ASR':
        raise StoreError('请选择 ASR 模型', 400)
    c, model = r['compat'], r['remote_model']
    filename, data, mime = file
    ext = PurePath(filename).suffix.lower().lstrip('.')
    if c.get('formats') and ext not in c['formats']:
        raise StoreError('模型不支持此音频格式', 400)
    if c.get('max_file_bytes') and len(data) > c['max_file_bytes']:
        raise StoreError('音频超过模型大小限制', 400)
    if r['api'] == 'openai-chat-audio':
        if ext not in ('wav', 'mp3', 'm4a', 'mp4', 'aac', 'flac', 'ogg', 'opus', 'webm', 'amr'):
            raise StoreError('模型不支持此音频格式', 400)
        media = {'mp3': 'mpeg', 'm4a': 'mp4'}.get(ext, ext)
        uri = _data_uri(('audio/' + media, data))
        if c.get('max_encoded_bytes') and len(uri) > c['max_encoded_bytes']:
            raise StoreError('编码后的音频超过模型大小限制', 400)
        body = {'model': model, 'messages': [{'role': 'user', 'content': [{'type': 'input_audio', 'input_audio': {'data': uri}}]}]}
        if language and c.get('language_param') == 'asr_options':
            body['asr_options'] = {'language': language}
        raw = _post(saved, r, '/chat/completions', timeout, json=body)
        result = {'text': raw['choices'][0]['message']['content'], 'duration': (raw.get('usage') or {}).get('seconds')}
    else:
        form, headers = {'model': model}, {}
        if fmt := c.get('response_format'):
            form['response_format'] = fmt
        if language and c.get('language_param') in ('header', 'form'):
            (headers if c['language_param'] == 'header' else form)['language'] = language
        result = _post(saved, r, c.get('path') or '/audio/transcriptions', timeout, headers=headers, files={'file': (filename, data, mime)}, data=form)
    if not isinstance(result.get('text'), str):
        raise ValueError('Invalid transcription response')
    return result
