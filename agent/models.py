"""Owner-scoped model configuration used by the editor, model checks and agents."""
import json
import math
import re
from functools import cached_property
from pathlib import Path
from urllib.parse import urlsplit

import anthropic
import httpx
import httpx2
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from openai import Omit
from pydantic import Field

from agent.model_catalog import APIS, LEVELS, resolve
from agent.model_http import ModelTransport
from governance.store import StoreError

_COMPAT = json.loads((Path(__file__).parent / 'model_catalog' / 'compat.json').read_text())
_RESERVED = {'authorization', 'proxy-authorization', 'content-type', 'content-length', 'host', 'connection',
             'transfer-encoding', 'accept-encoding', 'x-api-key', 'x-goog-api-key', 'api-key'}
_PROTECTED = {'model', 'messages', 'input', 'query', 'documents', 'file', 'dimensions', 'encoding_format',
              'max_tokens', 'max_completion_tokens', 'max_output_tokens', 'temperature', 'top_p', 'stream',
              'stream_options', 'api_key', 'api_base', 'base_url', 'headers', 'extra_headers', 'timeout',
              'reasoning_effort', 'thinking', 'store', 'include', 'top_n', 'return_documents'}


def model_headers(saved):
    headers = saved.get('parameters', {}).get('custom_headers') or {}
    if not isinstance(headers, dict):
        raise StoreError('自定义请求头必须为字符串映射', 400)
    result = {}
    for key, value in headers.items():
        if not isinstance(key, str) or not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", key) or not isinstance(value, str) or re.search(r'[\x00-\x1f\x7f]', value):
            raise StoreError('自定义请求头名称或内容无效', 400)
        if key.lower() not in _RESERVED:
            result[key] = value
    return result


def _valid_compat_type(value, kind):
    if kind == 'int':
        return type(value) is int and value >= 0
    if kind == 'float64':
        return type(value) in (int, float) and math.isfinite(value)
    if kind == 'bool':
        return type(value) is bool
    if kind == '[]string':
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    if kind.startswith('map['):
        return isinstance(value, dict) and (kind.endswith('any') or all(
            _valid_compat_type(v, 'int' if kind.endswith('int') else 'string') for v in value.values()))
    return isinstance(value, str)


def validate_model_runtime(saved):
    params = saved.get('parameters', {})
    if not isinstance(params, dict) or not isinstance(saved.get('name'), str) or any(not isinstance(params.get(k, ''), str) for k in ('provider', 'model_name', 'base_url')):
        raise StoreError('模型名称、供应商和地址必须为字符串', 400)
    if saved.get('source', 'remote') != 'remote' or params.get('interface_type') == 'ollama':
        raise StoreError('请选择远程 API 模型', 400)
    if params.get('provider', '').strip().lower() in ('weknoracloud', 'ollama', 'litellm'):
        raise StoreError('该模型服务商已停用，请重新选择服务商', 400)
    base = params.get('base_url')
    if base:
        try:
            url = urlsplit(base)
            url.port
            if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ValueError()
        except ValueError as exc:
            raise StoreError('模型 API 地址无效', 400) from exc
    for key in ('context_window', 'max_output_tokens', 'max_concurrency'):
        if params.get(key) is not None and (type(params[key]) is not int or params[key] < 0):
            raise StoreError(f'{key} 必须为非负整数', 400)
    if not isinstance(params.get('supports_vision', False), bool):
        raise StoreError('supports_vision 必须为布尔值', 400)
    if any(not isinstance(params.get(k, ''), str) for k in ('interface_type', 'parameter_size', 'app_id')):
        raise StoreError('模型参数类型无效', 400)
    embedding = params.get('embedding_parameters', {})
    if not isinstance(embedding, dict) or any(type(embedding.get(k, 0)) is not int for k in ('dimension', 'truncate_prompt_tokens')):
        raise StoreError('embedding_parameters 无效', 400)
    model_headers(saved)
    extra = params.get('extra_config', {})
    if not isinstance(extra, dict) or any(not isinstance(v, str) for v in extra.values()):
        raise StoreError('extra_config 必须为字符串映射', 400)
    spec = params.get('spec', {})
    if not isinstance(spec, dict) or set(spec) - {'api', 'reasoning', 'input', 'context_window', 'max_output_tokens', 'thinking_levels', 'compat'}:
        raise StoreError('模型 spec 无效', 400)
    if any(v and v not in APIS for v in (spec.get('api'), extra.get('api'))):
        raise StoreError('模型协议无效', 400)
    if 'reasoning' in spec and not isinstance(spec['reasoning'], bool):
        raise StoreError('reasoning 必须为布尔值', 400)
    for key in ('context_window', 'max_output_tokens'):
        if key in spec and (type(spec[key]) is not int or spec[key] <= 0):
            raise StoreError(f'{key} 必须为正整数', 400)
    levels = spec.get('thinking_levels', {})
    if not isinstance(levels, dict) or any(k not in LEVELS or (v is not None and not isinstance(v, str)) for k, v in levels.items()):
        raise StoreError('thinking_levels 无效', 400)
    if 'input' in spec and (not isinstance(spec['input'], list) or any(v not in ('text', 'image', 'audio', 'video') for v in spec['input'])):
        raise StoreError('模型输入类型无效', 400)
    kind = saved.get('type', 'KnowledgeQA')
    if kind not in ('KnowledgeQA', 'VLLM', 'Embedding', 'Rerank', 'ASR'):
        raise StoreError('模型类型无效', 400)
    if kind == 'Embedding':
        emb = params.get('embedding_parameters', params)
        if not isinstance(emb, dict) or type(emb.get('supports_dimension_override', False)) is not bool:
            raise StoreError('embedding_parameters 无效', 400)
        if emb.get('supports_dimension_override') and (type(emb.get('dimension')) is not int or not 1 <= emb['dimension'] <= 65536):
            raise StoreError('Embedding dimension 必须为正整数', 400)
    compat = spec.get('compat', {})
    if not isinstance(compat, dict):
        raise StoreError('spec.compat 必须为 JSON 对象', 400)
    resolved = resolve(saved)
    fields = _COMPAT.get(kind) or _COMPAT[resolved['api']]
    for key, value in compat.items():
        if key not in fields or not _valid_compat_type(value, fields[key]):
            raise StoreError(f'spec.compat.{key} 无效', 400)
    if 'fixed_temperature' in compat and not 0 <= compat['fixed_temperature'] <= 2:
        raise StoreError('fixed_temperature 必须在 0 到 2 之间', 400)
    if set(compat.get('extra_body', {})) & _PROTECTED:
        raise StoreError('extra_body 不能覆盖平台生成的请求字段', 400)
    if kind == 'Embedding' and resolved['api'] not in ('openai-embeddings', 'ark-embeddings', 'google-embeddings', 'dashscope-embeddings'):
        raise StoreError('Embedding 协议无效', 400)
    if kind == 'ASR' and resolved['api'] not in ('openai-transcriptions', 'openai-chat-audio'):
        raise StoreError('ASR 协议无效', 400)
    if kind == 'Rerank' and resolved['api'] not in ('cohere-rerank', 'tei-rerank', 'dashscope-rerank', 'pinecone-rerank', 'nim-rerank', 'tencent-lkeap', 'volcengine-knowledge'):
        raise StoreError('ReRank 协议无效', 400)
    if reason := resolved['compat'].get('unsupported_reason'):
        raise StoreError(reason, 400)
    if extra.get('score_scale', 'probability') not in ('probability', 'logit'):
        raise StoreError('score_scale 无效', 400)
    if kind == 'Rerank' and 'truncate_prompt_tokens' in extra and (not resolved['compat'].get('accepts_truncate_prompt_tokens')
            or not extra['truncate_prompt_tokens'].isdigit() or int(extra['truncate_prompt_tokens']) <= 0):
        raise StoreError('truncate_prompt_tokens 无效', 400)
    return resolved


def remote_model_name(saved):
    return resolve(saved)['remote_model']


def model_capabilities(saved):
    return resolve(saved)['capabilities']


def supports_image_input(saved):
    kind = saved.get('type')
    if kind not in ('KnowledgeQA', 'VLLM'):
        return False
    inputs = (saved.get('capabilities') or model_capabilities(saved)).get('input')
    if inputs is not None:
        return 'image' in inputs
    return kind == 'VLLM' or saved.get('parameters', {}).get('supports_vision') is True


def describe_model(saved):
    caps = model_capabilities(saved)
    params = dict(saved.get('parameters', {}))
    params.setdefault('supports_vision', 'image' in caps.get('input', []))
    return {**saved, 'parameters': params, 'capabilities': caps}


def completion_budget(capabilities, config):
    budget = config.get('max_completion_tokens') or (2048 if config.get('agent_mode') == 'quick-answer' else 24576)
    if capabilities.get('max_output_tokens'):
        budget = min(budget, capabilities['max_output_tokens'])
    window = capabilities.get('context_window')
    if window and budget >= int(window * 0.95):
        raise StoreError('max_completion_tokens：输出预算过大，请为 Agent 输入预留上下文空间', 400)
    return budget


class AnthropicChat(ChatAnthropic):
    @cached_property
    def _client(self):
        return anthropic.Anthropic(**self._client_params, http_client=httpx2.Client(transport=ModelTransport(self.anthropic_api_url, httpx2)))

    @cached_property
    def _async_client(self):
        return anthropic.AsyncAnthropic(**self._client_params, http_client=httpx2.AsyncClient(transport=ModelTransport(self.anthropic_api_url, httpx2)))

    def _make_message_chunk_from_anthropic_event(self, event, *, block_start_event=None, **kwargs):
        # Some endpoints report input tokens only in message_start, others repeat them in message_delta.
        block, start_usage = block_start_event or (None, None)
        if event.type == 'message_start':
            start_usage = event.message.usage
        elif event.type == 'message_delta' and start_usage:
            missing = {key: value for key, value in start_usage.model_dump(exclude_none=True).items()
                       if key != 'output_tokens' and getattr(event.usage, key, None) is None}
            event = event.model_copy(update={'usage': event.usage.model_copy(update=missing)})
        chunk, block = super()._make_message_chunk_from_anthropic_event(event, block_start_event=block, **kwargs)
        return chunk, (block, start_usage)


class CompatibleChat(ChatOpenAI):
    """Apply the catalog wire settings which differ across OpenAI-compatible servers."""
    compat: dict = Field(default_factory=dict, exclude=True)
    thinking_fields: dict = Field(default_factory=dict, exclude=True)
    send_bearer: bool = Field(default=True, exclude=True)
    reasoning_model: bool = Field(default=False, exclude=True)

    def _resolve_model_profile(self):
        # A deployment alias must never pick up an unrelated SDK model profile.
        return None

    def _get_request_payload(self, input_, **kwargs):
        payload = super()._get_request_payload(input_, **kwargs)
        if not self.send_bearer:
            payload['extra_headers'] = {**(payload.get('extra_headers') or {}), 'Authorization': Omit()}
        if self.use_responses_api:
            if self.compat.get('supports_max_output_tokens') is False:
                payload.pop('max_output_tokens', None)
            if self.compat.get('supports_parallel_tool_calls') is False:
                payload.pop('parallel_tool_calls', None)
            return payload
        if self.compat.get('max_tokens_field') == 'max_tokens' and 'max_completion_tokens' in payload:
            payload['max_tokens'] = payload.pop('max_completion_tokens')
        thinking = self.thinking_fields
        if self.compat.get('thinking_disable_on_non_stream') and not payload.get('stream') and thinking.get('enable_thinking'):
            thinking = {'enable_thinking': False}
        payload['extra_body'] = {**(payload.get('extra_body') or {}), **thinking}
        for msg, row in zip(self._convert_input(input_).to_messages(), payload['messages']):
            if row['role'] == 'assistant':
                if row.get('content') is None:
                    row['content'] = ''
                if self.compat.get('replay_reasoning_content', True) and msg.additional_kwargs.get('reasoning_content'):
                    row['reasoning_content'] = msg.additional_kwargs['reasoning_content']
                if self.compat.get('thinking_format') == 'openrouter' and msg.additional_kwargs.get('reasoning_details'):
                    row['reasoning_details'] = msg.additional_kwargs['reasoning_details']
                for item in msg.additional_kwargs.get('tool_call_metadata', []):
                    calls = row.get('tool_calls', [])
                    if 0 <= item['index'] < len(calls):
                        calls[item['index']].update({k: item[k] for k in self.compat.get('tool_call_extra_fields', ()) if k in item})
            elif row['role'] in ('developer', 'system'):
                row['role'] = 'developer' if self.reasoning_model and self.compat.get('supports_developer_role') else 'system'
            if self.compat.get('supports_multi_content') is False and isinstance(row.get('content'), list):
                row['content'] = '\n'.join(part['text'] for part in row['content'] if part.get('type') == 'text')
        if modes := self.compat.get('tool_choice_modes'):
            choice = payload.get('tool_choice')
            if ('function' if isinstance(choice, dict) else choice) not in modes:
                payload.pop('tool_choice', None)
        for flag, field in [('supports_parallel_tool_calls', 'parallel_tool_calls'), ('supports_seed', 'seed'),
                            ('supports_response_format', 'response_format'), ('supports_temperature', 'top_p')]:
            if self.compat.get(flag) is False:
                payload.pop(field, None)
        return payload

    def _retain_provider_fields(self, message, native):
        for key in self.compat.get('reasoning_fields', ['reasoning_content', 'reasoning', 'reasoning_text']):
            if isinstance(native.get(key), str) and native[key]:
                message.additional_kwargs['reasoning_content'] = native[key]
                break
        if self.compat.get('thinking_format') == 'openrouter' and isinstance(native.get('reasoning_details'), list):
            message.additional_kwargs['reasoning_details'] = native['reasoning_details']
        extra = self.compat.get('tool_call_extra_fields', ())
        if extra:
            metadata = []
            for i, call in enumerate(native.get('tool_calls') or []):
                fields = {key: call[key] for key in extra if call.get(key) is not None}
                if fields:
                    metadata.append({'index': call.get('index', i), **fields})
            if metadata:
                message.additional_kwargs['tool_call_metadata'] = metadata

    def _convert_chunk_to_generation_chunk(self, chunk, default_chunk_class, base_generation_info):
        result = super()._convert_chunk_to_generation_chunk(chunk, default_chunk_class, base_generation_info)
        choices = chunk.get('choices')
        if result and choices:
            self._retain_provider_fields(result.message, choices[0].get('delta') or {})
        return result

    def _create_chat_result(self, response, generation_info=None):
        result = super()._create_chat_result(response, generation_info)
        native = response if isinstance(response, dict) else response.model_dump()
        for gen, choice in zip(result.generations, native.get('choices', [])):
            self._retain_provider_fields(gen.message, choice.get('message', {}))
        return result


def _thinking_fields(fmt, compat, level, levels):
    if not level:
        return {}
    enabled = level != 'off'
    effort = levels.get(level, level) if level not in ('off', 'auto') and compat.get('supports_reasoning_effort') else None
    fields = {}
    if fmt == 'enable-thinking':
        fields['enable_thinking'] = enabled
    elif fmt == 'thinking-type':
        fields['thinking'] = {'type': compat.get('thinking_enabled_value', 'enabled') if enabled else 'disabled'}
    elif fmt == 'chat-template-kwargs':
        fields['chat_template_kwargs'] = {'enable_thinking': enabled}
    elif fmt == 'openrouter':
        return {'reasoning': {'effort': effort} if effort else {'enabled': enabled}}
    elif fmt == 'openai':
        if not enabled:
            effort = levels.get('off')
    else:
        return {}
    if effort:
        fields[compat.get('reasoning_effort_field', 'reasoning_effort')] = effort
    return fields


def build_model_record(saved, config):
    r = validate_model_runtime(saved)
    if saved.get('type', 'KnowledgeQA') not in ('KnowledgeQA', 'VLLM'):
        raise StoreError('请选择对话模型', 400)
    from agent.model_transport import authentication
    params = saved.get('parameters', {})
    caps, c, api = r['capabilities'], r['compat'], r['api']
    level = config.get('reasoning_effort') or ('auto' if config.get('thinking') else 'off')
    if level not in LEVELS:
        raise StoreError('reasoning_effort 无效', 400)
    if level != 'off' and not caps['thinking_levels']:
        raise StoreError('所选模型未声明支持深度思考', 400)
    if level not in caps['thinking_levels']:
        if config.get('reasoning_effort') and level != 'off':
            raise StoreError('所选模型不支持此思考强度', 400)
        level = ''
    budget = completion_budget(caps, config)
    profile = {k: caps[v] for k,v in [('max_input_tokens', 'context_window'), ('max_output_tokens', 'max_output_tokens')] if caps.get(v)}
    if 'input' in caps:
        profile['image_inputs'] = 'image' in caps['input']
    fmt = caps['thinking_format']
    temperature = c.get('fixed_temperature', config.get('temperature', 0.7)) if c.get('supports_temperature', True) else None
    common = dict(model=r['remote_model'], api_key=params.get('api_key') or 'not-required', temperature=temperature,
                  max_tokens=budget, profile=profile or None, timeout=config.get('llm_call_timeout') or 120, max_retries=2)
    base = r['base_url']
    headers = authentication(saved, r)
    enabled = level not in ('', 'off')
    effort = r['levels'].get(level, level)
    graded = enabled and level != 'auto'
    if api == 'anthropic-messages':
        from anthropic import Omit as AnthropicOmit
        thinking = None
        if enabled:
            if fmt == 'thinking.adaptive':
                thinking = {'type': 'adaptive', 'display': 'summarized'}
            else:
                if budget <= 1024:
                    raise StoreError('Claude 深度思考的最大输出须大于 1024 tokens', 400)
                budgets = {'minimal': 1024, 'low': 2048, 'medium': 8192, 'high': 16384, 'xhigh': 32768, 'max': 63999,
                           **c.get('thinking_budgets', {})}
                thinking = {'type': 'enabled', 'budget_tokens': min(budgets.get(level, 8192), budget - 1)}
            if not c.get('temperature_with_thinking'):
                common['temperature'] = None
        elif level and fmt == 'thinking.adaptive':
            thinking = {'type': c.get('thinking_off_type', 'disabled')}
        request_options = {'extra_body': c['extra_body']} if c.get('extra_body') else {}
        if 'x-api-key' not in headers:
            request_options['extra_headers'] = {'x-api-key': AnthropicOmit()}
        if c.get('version'):
            headers['anthropic-version'] = c['version']
        return AnthropicChat(**common, base_url=base.removesuffix('/v1/messages').removesuffix('/v1'),
            default_headers=headers, thinking=thinking, betas=c.get('beta_headers'),
            effort=effort if graded and c.get('supports_effort') else None,
            model_kwargs=request_options)
    if api == 'google-generative-ai':
        from langchain_google_genai import ChatGoogleGenerativeAI
        version = c.get('api_version_prefix', '/v1beta').strip('/')
        versioned = re.search(r'/(v\d+(?:alpha|beta)?)(?:/openai)?$', base)
        if versioned:
            version, base = versioned[1], base[:versioned.start()]
        thinking = {}
        if level and fmt != 'thinkingConfig.none':
            thinking['include_thoughts'] = enabled and c.get('include_thoughts', True)
            if fmt == 'thinkingConfig.level':
                if graded or not enabled:
                    thinking['thinking_level'] = (effort if graded else r['levels'].get('off') or 'minimal').upper()
            else:
                budgets = {'auto': -1, 'minimal': 128, 'low': 2048, 'medium': 8192, 'high': 24576, 'xhigh': 32768, 'max': 32768,
                           **c.get('thinking_budgets', {})}
                thinking['thinking_budget'] = budgets.get(level, 0)
        return ChatGoogleGenerativeAI(**common, base_url=base, api_version=version, vertexai=False, additional_headers=headers,
            client_args={'transport': ModelTransport(base), 'follow_redirects': False},
            thinking_config=thinking or None, model_kwargs=c.get('extra_generation_config', {}))
    extras = {}
    if r['url']:
        url = urlsplit(r['url'])
        base = r['url'].split('?')[0].rsplit('/responses' if api == 'openai-responses' else '/chat/completions', 1)[0]
        if url.query:
            extras['default_query'] = {'api-version': params['extra_config']['api_version']}
    base = base.removesuffix('/chat/completions').removesuffix('/responses')
    extras['send_bearer'] = 'Authorization' in headers
    extras.update(http_client=httpx.Client(transport=ModelTransport(base)),
                  http_async_client=httpx.AsyncClient(transport=ModelTransport(base)))
    if api == 'openai-responses':
        reasoning = {}
        if graded or level == 'off' and effort not in (None, 'off'):
            reasoning['effort'] = effort
        if enabled and c.get('supports_reasoning_summary', True):
            reasoning['summary'] = 'auto'
        extras.update(use_responses_api=True, reasoning=reasoning or None,
                      include=['reasoning.encrypted_content'] if c.get('supports_encrypted_reasoning', True) else None,
                      store=False if c.get('supports_store', True) else None)
    else:
        extras.update(use_responses_api=False, thinking_fields=_thinking_fields(fmt, c, level, r['levels']))
    if not extras['use_responses_api'] and c.get('supports_store'):
        extras['store'] = False
    return CompatibleChat(**common, **extras, base_url=base, default_headers=headers, compat=c, reasoning_model=caps['reasoning'],
                          stream_usage=c.get('supports_usage_in_streaming', True), extra_body=c.get('extra_body'))
