"""Owner-scoped LiteLLM SDK clients shared by chat, model checks and the catalog."""
import os
from urllib.parse import urlsplit

# Keep startup and capability reads offline and tied to the pinned SDK version.
os.environ.setdefault('LITELLM_LOCAL_MODEL_COST_MAP', 'True')

import litellm
from langchain_litellm import ChatLiteLLM

from governance.store import StoreError


LEVELS = ('off', 'auto', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max')
PROVIDERS = (
    ('generic', 'OpenAI-compatible', 'openai', ''),
    ('openai', 'OpenAI', 'openai', 'https://api.openai.com/v1'),
    ('aliyun', '阿里云百炼', 'dashscope', 'https://dashscope.aliyuncs.com/compatible-mode/v1'),
    ('deepseek', 'DeepSeek', 'deepseek', 'https://api.deepseek.com/v1'),
    ('anthropic', 'Anthropic', 'anthropic', 'https://api.anthropic.com'),
    ('gemini', 'Google Gemini', 'gemini', 'https://generativelanguage.googleapis.com'),
)
ALIASES = {'dashscope': 'aliyun', 'qwen': 'aliyun', 'google_genai': 'gemini'}
APIS = ('openai-completions', 'openai-responses', 'anthropic-messages', 'google-generative-ai')


def destination(saved):
    params = saved.get('parameters', {})
    provider = params.get('provider') or 'generic'
    provider = ALIASES.get(provider, provider)
    if provider == 'generic' and (urlsplit(params.get('base_url') or '').hostname or '').endswith('.aliyuncs.com'):
        provider = 'aliyun'
    sdk_provider = next((item[2] for item in PROVIDERS if item[0] == provider), 'openai')
    api = (params.get('extra_config') or {}).get('api') or (params.get('spec') or {}).get('api')
    if api in ('openai-responses', 'anthropic-messages', 'google-generative-ai'):
        sdk_provider = {'openai-responses': 'openai', 'anthropic-messages': 'anthropic', 'google-generative-ai': 'gemini'}[api]
    elif api == 'openai-completions' and sdk_provider in ('anthropic', 'gemini'):
        sdk_provider = 'openai'
    name = params.get('model_name') or saved['name']
    return provider, sdk_provider, name


def validate_model_runtime(saved):
    params = saved.get('parameters', {})
    if not isinstance(params.get('provider', ''), str) or not isinstance(params.get('model_name', saved['name']), str):
        raise StoreError('模型名称和供应商必须为字符串', 400)
    for key in ('context_window', 'max_output_tokens'):
        if params.get(key) is not None and (type(params[key]) is not int or params[key] < 0):
            raise StoreError(f'{key} 必须为非负整数', 400)
    if saved.get('source', 'remote') != 'remote':
        raise StoreError('当前模型运行时仅支持远程 API', 501)
    if params.get('interface_type') not in (None, '', 'openai', 'chat_completions', 'openai_compatible'):
        raise StoreError('此接口类型尚未接入，请通过供应商选择模型协议', 501)
    extra = params.get('extra_config') or {}
    if not isinstance(extra, dict) or set(extra) - {'api'} or (extra.get('api') and extra['api'] not in APIS):
        raise StoreError('extra_config 仅支持 api 协议选择', 501)
    spec = params.get('spec') or {}
    if not isinstance(spec, dict) or set(spec) - {'api', 'reasoning', 'input', 'context_window', 'max_output_tokens', 'thinking_levels'}:
        raise StoreError('模型 spec 包含尚未支持的配置', 400)
    if spec.get('api') and spec['api'] not in APIS:
        raise StoreError('模型协议无效', 400)
    if 'reasoning' in spec and not isinstance(spec['reasoning'], bool):
        raise StoreError('reasoning 必须为布尔值', 400)
    for key in ('context_window', 'max_output_tokens'):
        if key in spec and (type(spec[key]) is not int or spec[key] <= 0):
            raise StoreError(f'{key} 必须为正整数', 400)
    levels = spec.get('thinking_levels', {})
    if not isinstance(levels, dict) or any(key not in LEVELS or (value is not None and not isinstance(value, str)) for key, value in levels.items()):
        raise StoreError('thinking_levels 无效', 400)
    if 'input' in spec and (not isinstance(spec['input'], list) or any(value not in ('text', 'image', 'audio', 'video') for value in spec['input'])):
        raise StoreError('模型输入类型无效', 400)


def model_capabilities(saved):
    params = saved.get('parameters', {})
    provider, sdk_provider, name = destination(saved)
    info = litellm.model_cost.get(f'{sdk_provider}/{name}') or {}
    if not info and sdk_provider in ('openai', 'anthropic'):
        info = litellm.model_cost.get(name) or {}
    spec = params.get('spec') or {}
    reasoning = bool(info.get('supports_reasoning'))
    # The SDK catalog incorrectly marks qwen-max as reasoning-capable; Alibaba's model table excludes it.
    if sdk_provider == 'dashscope' and name.startswith('qwen-max'):
        reasoning = False
    reasoning = spec.get('reasoning', reasoning)
    levels = []
    if reasoning:
        levels = ['auto', 'low', 'medium', 'high']
        if sdk_provider == 'dashscope':
            levels = ['off', 'auto']
        elif (sdk_provider == 'openai' and info.get('supports_none_reasoning_effort')) or sdk_provider == 'deepseek' or (
                sdk_provider == 'anthropic' and info.get('supports_legacy_thinking')) or (
                sdk_provider == 'gemini' and 'flash' in name):
            levels.insert(0, 'off')
        for level in ('minimal', 'xhigh', 'max'):
            if info.get(f'supports_{level}_reasoning_effort'):
                levels.append(level)
        if 'thinking_levels' in spec:
            levels = [level for level in LEVELS if level in spec['thinking_levels'] and spec['thinking_levels'][level] is not None]
    api = (params.get('extra_config') or {}).get('api') or spec.get('api') or {
        'anthropic': 'anthropic-messages', 'gemini': 'google-generative-ai',
    }.get(sdk_provider, 'openai-completions')
    thinking_format = {
        'openai-responses': 'reasoning.effort',
        'anthropic-messages': 'thinking.adaptive' if info.get('supports_adaptive_thinking') else 'thinking.budget',
        'google-generative-ai': 'thinkingConfig.level' if name.startswith('gemini-3') else 'thinkingConfig.budget',
    }.get(api, {'dashscope': 'enable-thinking', 'deepseek': 'thinking-type'}.get(sdk_provider, 'openai'))
    return {'provider': provider, 'api': api, 'cataloged': bool(info), 'reasoning': reasoning,
        'thinking_levels': [level for level in LEVELS if level in levels],
        'thinking_format': thinking_format if reasoning else 'none',
        'input': spec.get('input', ['text', 'image'] if info.get('supports_vision') else ['text']),
        'context_window': spec.get('context_window') or params.get('context_window') or info.get('max_input_tokens'),
        'max_output_tokens': spec.get('max_output_tokens') or params.get('max_output_tokens') or info.get('max_output_tokens')}


def describe_model(saved):
    """Supply the fields consumed by the unchanged WeKnora model cards and editor."""
    caps = model_capabilities(saved)
    params = dict(saved.get('parameters', {}))
    for field in ('context_window', 'max_output_tokens'):
        if not params.get(field) and caps.get(field):
            params[field] = caps[field]
    params.setdefault('supports_vision', 'image' in caps['input'])
    return {**saved, 'parameters': params, 'capabilities': caps}


def build_model_record(saved, config):
    validate_model_runtime(saved)
    if saved['type'] not in ('KnowledgeQA', 'VLLM'):
        raise StoreError('请选择对话模型', 400)
    params = saved.get('parameters', {})
    _, provider, name = destination(saved)
    caps = model_capabilities(saved)
    api_provider = {'anthropic-messages': 'anthropic', 'google-generative-ai': 'gemini',
                    'openai-completions': provider, 'openai-responses': 'openai'}[caps['api']]
    effort = config.get('reasoning_effort') or ('auto' if config.get('thinking') else 'off')
    if effort not in LEVELS:
        raise StoreError('reasoning_effort 无效', 400)
    enabled = effort != 'off'
    if enabled and not caps['reasoning']:
        raise StoreError('所选模型未声明支持深度思考，请更换模型或核实模型能力配置', 400)
    if caps['reasoning'] and effort not in caps['thinking_levels']:
        if config.get('reasoning_effort') or enabled:
            raise StoreError('所选模型不支持此思考强度', 400)
        effort = ''  # Inherited false cannot disable an always-on model.
    budget = config.get('max_completion_tokens') or (2048 if config.get('agent_mode') == 'quick-answer' else 24576)
    if caps.get('max_output_tokens'):
        budget = min(budget, caps['max_output_tokens'])
    kwargs = {}
    if caps['reasoning'] and effort:
        if provider == 'dashscope':
            kwargs['extra_body'] = {'enable_thinking': enabled}
        elif effort == 'auto' and provider == 'deepseek':
            kwargs['thinking'] = {'type': 'enabled'}
        elif effort == 'auto' and provider == 'gemini':
            kwargs['thinking'] = {'type': 'enabled', 'budget_tokens': -1}
        elif effort == 'auto' and provider == 'anthropic' and (litellm.model_cost.get(name) or {}).get('supports_adaptive_thinking'):
            kwargs['thinking'] = {'type': 'adaptive', 'display': 'summarized'}
        else:
            value = (params.get('spec') or {}).get('thinking_levels', {}).get(effort)
            kwargs['reasoning_effort'] = value or ('none' if effort == 'off' else 'medium' if effort == 'auto' else effort)
    if enabled and api_provider == 'anthropic' and budget <= 1024:
        raise StoreError('Claude 深度思考的最大输出须大于 1024 tokens', 400)
    if caps['api'] == 'openai-responses':
        kwargs['extra_body'] = {'store': False, 'include': ['reasoning.encrypted_content']}
        if enabled:
            kwargs['reasoning_effort'] = {'effort': kwargs['reasoning_effort'], 'summary': 'auto'}
    headers = {key: value for key, value in (params.get('custom_headers') or {}).items()
               if key.lower() not in ('authorization', 'content-type', 'host', 'x-api-key', 'x-goog-api-key', 'api-key')}
    return ChatLiteLLM(model=name, custom_llm_provider=api_provider,
        api_key=params.get('api_key') or 'not-required', api_base=params.get('base_url'),
        extra_headers=headers or None, temperature=None if caps['reasoning'] and effort != 'off' and provider not in ('dashscope', 'gemini') else config.get('temperature', 0.7),
        max_tokens=budget, request_timeout=config.get('llm_call_timeout') or 180, max_retries=2,
        use_responses_api=caps['api'] == 'openai-responses', model_kwargs=kwargs)
