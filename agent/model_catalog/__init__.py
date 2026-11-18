"""WeKnora 7d064bc3 model catalog and provider resolution (frontend/UPSTREAM-LICENSE)."""
import json
from fnmatch import fnmatchcase
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit

from governance.store import StoreError

_ROOT = Path(__file__).parent
PROVIDERS = json.loads((_ROOT / 'providers.json').read_text())
_MODELS = json.loads((_ROOT / 'models.json').read_text())
TYPES = {'chat': 'KnowledgeQA', 'embedding': 'Embedding', 'rerank': 'Rerank', 'vllm': 'VLLM', 'asr': 'ASR'}
LEVELS = ('off', 'auto', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max')
APIS = ('openai-completions', 'openai-responses', 'anthropic-messages', 'google-generative-ai')
_NONCHAT = {'Embedding': ('embeddings', 'embedding_api', 'openai-embeddings'),
            'Rerank': ('rerank', 'rerank_api', 'cohere-rerank'),
            'ASR': ('transcriptions', 'transcription_api', 'openai-transcriptions')}
_PUBLIC = ('label', 'labels', 'description', 'descriptions', 'website', 'api', 'auth', 'order', 'extraFields',
           'credentialLabels', 'modelTypes', 'requiresAuth', 'icon')


def provider_id(params):
    key = (params.get('provider') or '').strip().lower()
    key = {'dashscope': 'aliyun', 'qwen': 'aliyun', 'google_genai': 'gemini'}.get(key, key)
    if key:
        return key if key in PROVIDERS else 'generic'
    base = (params.get('base_url') or '').lower()
    matches = [(len(pattern), -vendor['order'], ident) for ident, vendor in PROVIDERS.items()
               for pattern in vendor.get('patterns', []) if pattern.lower() in base]
    return max(matches)[2] if matches else 'generic'


@lru_cache(maxsize=2048)
def _find(provider, kind, name):
    entries = [entry for entry in _MODELS[provider] if entry.get('type', 'KnowledgeQA') == kind]
    needle = name.strip().lower()
    if needle:
        for entry in entries:
            if entry.get('id', '').lower() == needle:
                return entry
        for entry in entries:
            if any(alias.lower() == needle for alias in entry.get('aliases', ())):
                return entry
        matches = [entry for entry in entries if 'match' in entry and fnmatchcase(needle, entry['match'].lower())]
        if matches:
            return max(matches, key=lambda e: len(e['match'].split('*')[0]))
    return None


def custom_endpoint(provider, kind, api, base, name, extra):
    if provider == 'azure_openai':
        path = {'Embedding': '/embeddings', 'ASR': '/audio/transcriptions'}.get(kind,
            '/responses' if api == 'openai-responses' else '/chat/completions')
        if version := extra.get('api_version'):
            return base + '/openai/deployments/' + quote(name, safe='') + path + '?' + urlencode({'api-version': version})
        return base.removesuffix('/openai/v1') + '/openai/v1' + path
    if provider == 'aliyun' and kind == 'Embedding':
        root = base.split('/compatible-mode')[0].split('/api/v1')[0]
        return root + ('/api/v1/services/embeddings/multimodal-embedding/multimodal-embedding'
                       if api == 'dashscope-embeddings' else '/compatible-mode/v1/embeddings')
    if provider == 'volcengine' and kind == 'Embedding':
        return base.split('/api/')[0] + ('/api/v3/embeddings' if api == 'openai-embeddings' else '/api/v3/embeddings/multimodal')
    return ''


def resolve(saved):
    params = saved.get('parameters', {})
    provider = provider_id(params)
    vendor = PROVIDERS[provider]
    name = params.get('model_name') or saved['name']
    kind = saved.get('type', 'KnowledgeQA')
    catalog_kind = 'KnowledgeQA' if kind == 'VLLM' else kind
    matched = _find(provider, catalog_kind, name)
    spec = dict(matched or {'id': name, 'type': catalog_kind, 'reasoning': False})
    spec.setdefault('type', catalog_kind)
    spec.setdefault('api', vendor['api'])
    original_api = spec['api']
    override = params.get('spec') or {}
    extra = params.get('extra_config') or {}
    for key in ('api', 'reasoning', 'input', 'context_window', 'max_output_tokens'):
        if key in override and (override[key] or key == 'reasoning'):
            spec[key] = override[key]
    short = next((s for s, mt in TYPES.items() if mt == kind), 'chat')
    base = (params.get('base_url') or vendor['defaultUrls'].get(short) or vendor['defaultUrls'].get('chat') or '').strip().rstrip('/')
    remote = extra.get('remote_model_name', '').strip() or name
    nonchat = kind in _NONCHAT
    if nonchat:
        group, field, default = _NONCHAT[kind]
        api = vendor.get(field, default)
    else:
        api = extra.get('api') or spec['api']
        if not extra.get('api') and not override.get('api'):
            if provider == 'openai' and urlsplit(base).hostname == 'api.openai.com':
                api = 'openai-responses'
            elif base.endswith(('/anthropic', '/anthropic/v1')):
                api = 'anthropic-messages'
            elif api == 'google-generative-ai' and base.endswith('/openai'):
                api = 'openai-completions'
        group = api.replace('-', '_')
    compat = {**vendor.get('compat', {}).get(group, {}),
              **(spec.get('compat', {}) if nonchat or original_api == api else {}), **(override.get('compat') or {})}
    if nonchat:
        api = compat.get('api', api)
    levels = {**vendor.get('levels', {}), **spec.get('thinking_levels', {}), **override.get('thinking_levels', {})}
    supported = [level for level in LEVELS if levels.get(level, None if level in ('xhigh', 'max') else level) is not None]
    fmt, token_field = '', ''
    if api == 'openai-completions':
        fmt = compat.get('thinking_format', 'none')
        legacy = extra.get('thinking_control')
        if legacy and not (legacy == 'none' and fmt == 'openrouter'):
            fmt = {'none': 'none', 'enable_thinking': 'enable-thinking', 'thinking_type': 'thinking-type'}.get(legacy, 'chat-template-kwargs')
        elif matched is not None and not spec.get('reasoning'):
            fmt = 'none'
        if fmt == 'chat-template-kwargs' and not compat.get('supports_reasoning_effort'):
            supported = [level for level in supported if level in ('off', 'auto')]
        token_field = compat.get('max_tokens_field', 'max_completion_tokens')
    elif api == 'openai-responses':
        fmt, token_field = 'reasoning.effort', 'max_output_tokens'
    elif api == 'anthropic-messages':
        fmt, token_field = 'thinking.' + compat.get('thinking_mode', 'budget'), 'max_tokens'
    elif api == 'google-generative-ai':
        fmt, token_field = 'thinkingConfig.' + compat.get('thinking_mode', 'budget'), 'maxOutputTokens'
    if nonchat or fmt in ('none', 'thinkingConfig.none'):
        supported = []
    elif matched and not spec.get('reasoning') and not extra.get('thinking_control'):
        supported = ['off']
    caps = {'provider': provider, 'api': '' if nonchat else api, 'cataloged': matched is not None,
            'reasoning': bool(spec.get('reasoning')), 'thinking_levels': supported, 'thinking_format': fmt}
    if token_field:
        caps['max_tokens_field'] = token_field
    if 'input' in spec:
        caps['input'] = spec['input']
    for key in ('context_window', 'max_output_tokens'):
        if limit := override.get(key) or params.get(key) or spec.get(key):
            caps[key] = limit
    return {'provider': provider, 'api': api, 'base_url': base, 'remote_model': remote, 'cataloged': matched is not None,
            'model': spec, 'capabilities': caps, 'compat': compat, 'levels': levels,
            'url': custom_endpoint(provider, kind, api, base, remote, extra)}


@lru_cache(maxsize=200)
def provider_option(ident, short, include_urls):
    vendor = PROVIDERS[ident]
    result = {key: vendor[key] for key in _PUBLIC if key in vendor}
    if ident in ('cohere','huggingface_tei'):
        result['icon'] = PROVIDERS['generic']['icon']
    if result.get('extraFields'):
        result['extraFields'] = [{'required': False, **f} for f in result['extraFields']]
    def caps(name):
        return resolve({'name': name, 'parameters': {'provider': ident}})['capabilities']
    defaults = caps('__vendor_default__')
    result.update(value=ident, defaultUrls=vendor['defaultUrls'] if include_urls else None,
                  thinking={'format': defaults['thinking_format'], 'levels': defaults['thinking_levels']}, models=[])
    seen = set()
    for category in ([short] if short else vendor['modelTypes']):
        for entry in _MODELS[ident]:
            name = entry.get('id')
            if not name or name in seen or entry.get('deprecated'):
                continue
            kind = entry.get('type', 'KnowledgeQA')
            if category == 'vllm':
                if kind != 'KnowledgeQA' or 'image' not in entry.get('input', []):
                    continue
            elif kind != TYPES[category]:
                continue
            seen.add(name)
            picked = {key: entry[key] for key in ('id', 'api', 'input', 'context_window', 'max_output_tokens', 'dimension', 'cost', 'source') if key in entry}
            if kind == 'KnowledgeQA':
                picked.setdefault('api', vendor['api'])
            picked.update(name=entry.get('name') or name, type=next(k for k,v in TYPES.items() if v == kind),
                          reasoning=bool(entry.get('reasoning')), thinking_levels=caps(name)['thinking_levels'] if kind == 'KnowledgeQA' else [])
            result['models'].append(picked)
    if not result['models']:
        result.pop('models')
    return result
