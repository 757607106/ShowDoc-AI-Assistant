"""Runtime settings used by the original model, MCP and Skills panels."""
import asyncio

from flask import Blueprint, g, jsonify, request
from psycopg.types.json import Jsonb

from agent import registry
from webapi.legacy_runtime import unavailable
from governance.database import connection
from governance.store import StoreError, now

runtime_settings_bp = Blueprint('runtime_settings', __name__)


def _body():
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise StoreError('请求必须为 JSON 对象', 400)
    return value


def _require_model_admin():
    if g.user['role'] != 'admin':
        raise StoreError('模型配置仅限平台管理员管理', 403)


@runtime_settings_bp.route('/api/v1/models', methods=['GET', 'POST'])
def models():
    if request.method == 'POST':
        _require_model_admin()
    value = registry.public(registry.save_model(_body(), g.user['id'])) if request.method == 'POST' else registry.models(g.user['id'])
    return jsonify(success=True, data=value)


@runtime_settings_bp.route('/api/v1/models/providers')
def model_providers():
    from agent.models import PROVIDERS
    values = [{'value': provider, 'label': label,
        'description': '用户提供的 OpenAI 兼容 API' if provider == 'generic' else f'{label} 模型服务',
        'api': {'anthropic': 'anthropic-messages', 'gemini': 'google-generative-ai'}.get(provider, 'openai-completions'), 'requiresAuth': True,
        'defaultUrls': {'KnowledgeQA': base, 'VLLM': base} if base else {},
        'modelTypes': ['KnowledgeQA', 'VLLM', 'ASR', 'Embedding', 'Rerank'] if provider == 'generic' else ['KnowledgeQA', 'VLLM'],
        'models': []} for provider, label, _, base in PROVIDERS]
    requested = request.args.get('model_type')
    requested = {'chat': 'KnowledgeQA', 'vllm': 'VLLM', 'embedding': 'Embedding', 'rerank': 'Rerank', 'asr': 'ASR'}.get(requested, requested)
    return jsonify(success=True, data=[value for value in values if not requested or requested in value['modelTypes']])


@runtime_settings_bp.route('/api/v1/models/catalog/resolve', methods=['POST'])
def resolve_model_catalog():
    from agent.models import model_capabilities, validate_model_runtime, remote_model_name
    body = _body()
    name = body.get('model') or ''
    extra = dict(body.get('extra_config') or {})
    for key in ('api', 'remote_model_name'):
        if body.get(key):
            extra[key] = body[key]
    kind = {'chat': 'KnowledgeQA', 'vllm': 'VLLM', 'embedding': 'Embedding', 'rerank': 'Rerank', 'asr': 'ASR'}.get(body.get('model_type'), 'KnowledgeQA')
    value = {'name': name, 'type': kind, 'parameters': {'provider': body.get('provider', 'generic'), 'base_url': body.get('base_url', ''),
        'context_window': body.get('context_window'), 'max_output_tokens': body.get('max_output_tokens'),
        'spec': body.get('spec') or {}, 'extra_config': extra}}
    validate_model_runtime(value)
    capabilities = model_capabilities(value)
    return jsonify(success=True, data={'provider': capabilities['provider'], 'api': capabilities['api'],
        'base_url': body.get('base_url', ''), 'remote_model': remote_model_name(value),
        'cataloged': capabilities['cataloged'], 'model': {}, 'capabilities': capabilities})


@runtime_settings_bp.route('/api/v1/models/<model_id>', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
def model(model_id):
    if request.method != 'GET':
        _require_model_admin()
    if model_id == 'agent-main':
        if request.method != 'GET':
            raise StoreError('环境模型请通过服务器环境配置；可以复制为个人模型', 400)
        return jsonify(success=True, data=registry.environment_model())
    if request.method == 'DELETE':
        with registry.model_bindings_transaction(g.user['id']) as conn:
            registry.record('model', model_id, g.user['id'], _connection=conn)
            defaults = registry.default_model_references(model_id, g.user['id'], _connection=conn)
            if defaults:
                raise StoreError('模型正用于默认设置，请先更换：' + '、'.join(defaults), 409)
            usage = registry.model_usage(model_id, g.user['id'], _connection=conn)
            if usage['agent_total']:
                return jsonify(success=False, error={'code': 2300,
                    'message': '模型正被 Agent 使用，请先更换模型', 'details': usage}), 400
            registry.delete_record('model', model_id, g.user['id'], _connection=conn)
        return jsonify(success=True)
    if request.method != 'GET':
        body = _body()
        if request.method == 'PUT' and isinstance(body.get('parameters'), dict):
            # The upstream editor omits spec after its last override is cleared.
            body['parameters'].setdefault('spec', {})
        value = registry.save_model(body, g.user['id'], model_id)
    else:
        value = registry.record('model', model_id, g.user['id'])
    return jsonify(success=True, data=registry.public(value))


@runtime_settings_bp.route('/api/v1/models/<model_id>/copy', methods=['POST'])
def copy_model(model_id):
    _require_model_admin()
    value = registry.model_config(model_id, g.user['id'])
    value.pop('id', None)
    if model_id == 'agent-main':
        # A personal copy must never export shared server credentials to a user-controlled endpoint.
        for key in ('api_key', 'app_secret', 'custom_headers'):
            value['parameters'].pop(key, None)
    value['display_name'] = _body().get('display_name') or value.get('display_name', value['name']) + ' (副本)'
    return jsonify(success=True, data=registry.public(registry.save_model(value, g.user['id'])))


@runtime_settings_bp.route('/api/v1/models/<model_id>/usage')
def model_usage(model_id):
    registry.model_config(model_id, g.user['id'])
    usage = registry.model_usage(model_id, g.user['id'])
    return jsonify(success=True, data={'model_id': model_id, **usage,
        'in_use': bool(usage['agent_total'] or registry.default_model_references(model_id, g.user['id']))})


@runtime_settings_bp.route('/api/v1/models/<model_id>/debug', methods=['POST'])
def debug_model(model_id):
    import asyncio
    import json
    import time
    from agent.config import validate_config
    from agent.graph import build_model
    from agent.models import model_capabilities, remote_model_name
    from webapi.weknora_adapter import message_dict, reasoning_text, text
    if request.is_json:
        body = _body()
        options = body.get('options', body)
    else:
        body = request.form
        try:
            options = json.loads(body.get('options', '{}'))
        except (TypeError, ValueError) as exc:
            raise StoreError('调试 options 必须为 JSON 对象', 400) from exc
    if not isinstance(options, dict):
        raise StoreError('调试 options 必须为对象', 400)
    saved = registry.model_config(model_id, g.user['id'])
    if saved['type'] not in ('KnowledgeQA', 'VLLM'):
        from webapi.model_runtime import debug_nonchat_model
        return debug_nonchat_model(saved, body, options, request.files.get('file'))
    config = validate_config({'model_id': model_id, 'temperature': options.get('temperature', 0),
        'max_completion_tokens': options.get('max_tokens', 2048), 'thinking': options.get('thinking', False),
        'reasoning_effort': options.get('reasoning_effort', '')})
    query = body.get('input') or body.get('query') or '请回复 OK'
    if not isinstance(query, str) or len(query) > 100000:
        raise StoreError('调试输入无效', 400)
    prompt = options.get('system_prompt', '')
    if not isinstance(prompt, str) or len(prompt) > 100000:
        raise StoreError('调试系统提示词无效', 400)
    messages = ([{'role': 'system', 'content': prompt}] if prompt else []) + [{'role': 'user', 'content': query}]
    file = request.files.get('file')
    caps = model_capabilities(saved)
    if saved['type'] == 'VLLM' and not file:
        raise StoreError('请提供视觉模型调试图片', 400)
    if file and saved['type'] == 'KnowledgeQA' and not (saved['parameters'].get('supports_vision') or 'image' in caps['input']):
        raise StoreError('当前对话模型不支持图片输入', 400)
    if file:
        import base64
        from opensandbox.exceptions import SandboxException
        from webapi.chat_resources import _image_mime
        data = file.read(10 * 1024 * 1024 + 1)
        if len(data) > 10 * 1024 * 1024:
            raise StoreError('调试图片不能超过 10 MB', 400)
        try:
            mime = _image_mime(file.filename or 'image', data)
        except StoreError as exc:
            if exc.status != 422:
                raise
            raise StoreError('请提供有效图片', 400) from exc
        except SandboxException as exc:
            raise StoreError('隔离图片校验服务不可用', 503) from exc
        except (KeyError, TypeError, ValueError) as exc:
            raise StoreError('请提供有效图片', 400) from exc
        messages[-1]['content'] = [{'type': 'text', 'text': query}, {'type': 'image_url', 'image_url': {
            'url': f'data:{mime};base64,' + base64.b64encode(data).decode()}}]
    model = build_model(config, g.user['id'])
    caps = model_capabilities(saved)
    if 'top_p' in options:
        if type(options['top_p']) not in (int, float) or not 0 <= options['top_p'] <= 1:
            raise StoreError('top_p 必须在 0 到 1 之间', 400)
        if model.temperature is not None:
            model = model.bind(top_p=options['top_p'])
    started = time.monotonic()
    async def query_model():
        result = None
        async for chunk in model.astream(messages):
            result = chunk if result is None else result + chunk
        if result is None:
            raise ValueError('Empty model response')
        return result
    observations = {'api': caps['api'], 'capabilities': caps, 'requested_reasoning_effort': config.get('reasoning_effort') or
                    ('auto' if config['thinking'] else 'off')}
    client = model.bound if hasattr(model, 'bound') else model
    request_info = {'model': remote_model_name(saved), 'input': query,
                    'system_prompt': prompt, 'options': dict(options), 'image_attached': bool(file),
                    'effective_options': {'temperature': client.temperature, 'max_tokens': client.max_tokens,
                        **client.model_kwargs, **(model.kwargs if hasattr(model, 'kwargs') else {})}}
    try:
        output = asyncio.run(query_model())
        native = message_dict(output)
        reasoning = reasoning_text(native)
        observations.update(answer_characters=len(text(output.content)), reasoning_characters=len(reasoning), reasoning_returned=bool(reasoning))
        result = {'ok': True, 'raw_response': native, 'content': output.content, 'model_id': model_id}
    except Exception as exc:
        result = {'ok': False, 'raw_response': None, 'error': f'模型调试失败（{type(exc).__name__}）'}
    return jsonify(success=True, data={**result, 'request': request_info, 'observations': observations,
        'elapsed_ms': round((time.monotonic() - started) * 1000)})


@runtime_settings_bp.route('/api/v1/mcp-services', methods=['GET', 'POST'])
def services():
    value = registry.public(_save_service(_body())) if request.method == 'POST' else [registry.public(item) for item in registry.records('mcp', g.user['id'])]
    return jsonify(success=True, data=value)


@runtime_settings_bp.route('/api/v1/mcp-services/<service_id>', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
def service(service_id):
    if request.method == 'DELETE':
        registry.delete_record('mcp', service_id, g.user['id'])
        from agent.mcp_auth import delete_service_state
        delete_service_state(g.user['id'], service_id)
        return jsonify(success=True)
    value = _save_service(_body(), service_id) if request.method != 'GET' else registry.record('mcp', service_id, g.user['id'])
    return jsonify(success=True, data=registry.public(value))


def _check_service(value):
    if value.get('transport_type') == 'stdio' and g.user['role'] != 'admin':
        raise StoreError('stdio MCP 会启动服务器进程，仅允许管理员配置和执行', 403)


def _save_service(body, service_id=None):
    current = registry.record('mcp', service_id, g.user['id']) if service_id else {}
    _check_service({**current, **body})
    return registry.save_mcp(body, g.user['id'], service_id)


async def _catalog(value):
    _check_service(value)
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from agent.mcp_auth import mcp_connection
    client = MultiServerMCPClient({value['id']: mcp_connection(value, g.user['id'])})
    values = await client.get_tools()
    return [{'name': tool.name, 'description': tool.description, 'inputSchema': tool.args_schema.model_json_schema()
        if isinstance(tool.args_schema, type) else tool.args_schema,
        **registry.mcp_tool_policy(value, tool.name, (tool.metadata or {}).get('readOnlyHint')),
        'readOnlyHint': (tool.metadata or {}).get('readOnlyHint') is True} for tool in values]


@runtime_settings_bp.route('/api/v1/mcp-services/<service_id>/tools')
@runtime_settings_bp.route('/api/v1/mcp-services/<service_id>/test', methods=['POST'])
def service_catalog(service_id):
    value = registry.record('mcp', service_id, g.user['id'])
    _check_service(value)
    try:
        tools = asyncio.run(_catalog(value))
    except Exception as exc:
        if request.path.endswith('/test'):
            return jsonify(success=True, data={'success': False, 'message': f'MCP 连接失败（{type(exc).__name__}）'})
        raise StoreError(f'MCP 工具发现失败（{type(exc).__name__}）', 502) from exc
    return jsonify(success=True, data={'success': True, 'tools': tools} if request.path.endswith('/test') else tools)


@runtime_settings_bp.route('/api/v1/mcp-services/<service_id>/resources')
def service_resources(service_id):
    from langchain_mcp_adapters.client import MultiServerMCPClient
    value = registry.record('mcp', service_id, g.user['id'])
    _check_service(value)
    async def read():
        from agent.mcp_auth import mcp_connection
        client = MultiServerMCPClient({service_id: mcp_connection(value, g.user['id'])})
        async with client.session(service_id) as session:
            result = await session.list_resources()
            return [item.model_dump(mode='json') for item in result.resources]
    return jsonify(success=True, data=asyncio.run(read()))


@runtime_settings_bp.route('/api/v1/mcp-services/<service_id>/tool-approvals')
@runtime_settings_bp.route('/api/v1/mcp-services/<service_id>/tool-approvals/<path:tool_name>', methods=['PUT'])
def tool_flags(service_id, tool_name=None):
    from agent import mcp_auth
    value = registry.record('mcp', service_id, g.user['id'])
    if tool_name:
        body = _body()
        updates = {key: body[key] for key in ('enabled', 'require_approval') if key in body}
        if not updates or any(not isinstance(item, bool) for item in updates.values()):
            raise StoreError('工具开关必须为布尔值', 400)
    catalog = asyncio.run(_catalog(value))
    cached = mcp_auth._record('mcp-metadata', service_id, g.user['id'])
    if cached and (cached['fingerprint'] != mcp_auth.fingerprint(value) or
                   {tool['name'] for tool in cached['snapshot']['tools']} != {tool['name'] for tool in catalog}):
        raise StoreError('MCP 工具目录已变化，请刷新工具目录后重试', 409)
    if tool_name:
        selected = next((tool for tool in catalog if tool['name'] == tool_name), None)
        if selected is None:
            raise StoreError('MCP 工具不存在，请刷新工具目录', 404)
        if selected['readOnlyHint'] is not True:
            raise StoreError('当前 Agent 仅支持明确声明只读的 MCP 工具', 403)
        current = registry.record('mcp', service_id, g.user['id'])
        if mcp_auth.fingerprint(current) != mcp_auth.fingerprint(value):
            raise StoreError('MCP 连接配置已变化，请刷新后重试', 409)
        flags = current.get('tool_approvals', {})
        value = {**current, 'tool_approvals': {**flags, tool_name: {**flags.get(tool_name, {}), **updates}},
                 'updated_at': now()}
        with connection() as conn:
            saved = conn.execute('''UPDATE runtime_records SET payload=%s,updated_at=now()
                WHERE owner_id=%s AND kind='mcp' AND record_key=%s AND payload=%s RETURNING id''',
                (Jsonb(value), g.user['id'], service_id, Jsonb(current))).fetchone()
            if saved is None:
                raise StoreError('MCP 服务配置已变化，请刷新后重试', 409)
    return jsonify(success=True, data=[{'id': tool['name'], 'service_id': service_id, 'tool_name': tool['name'],
        **registry.mcp_tool_policy(value, tool['name'], tool['readOnlyHint'])} for tool in catalog])


@runtime_settings_bp.route('/api/v1/<resource>/<resource_id>/credentials', methods=['PUT'])
@runtime_settings_bp.route('/api/v1/<resource>/<resource_id>/credentials/<field>', methods=['DELETE'])
def credentials(resource, resource_id, field=None):
    kind = {'models': 'model', 'mcp-services': 'mcp', 'web-search-providers': 'web-search'}.get(resource)
    if not kind:
        raise StoreError('配置类型无效', 404)
    if kind == 'model':
        _require_model_admin()
    value = registry.record(kind, resource_id, g.user['id'])
    if kind == 'web-search':
        unavailable()
    from agent import mcp_auth
    previous_fingerprint = mcp_auth.fingerprint(value) if kind == 'mcp' else None
    private = registry.secrets(value)
    allowed = ('api_key', 'app_secret') if kind == 'model' else ('api_key', 'token', 'client_secret')
    if field:
        if field not in allowed:
            raise StoreError('凭据字段无效', 400)
        private.pop(field, None)
    else:
        body = _body()
        if set(body) - set(allowed) or any(not isinstance(value, str) for value in body.values()):
            raise StoreError('凭据字段无效', 400)
        private.update(body)
    value = registry.with_secrets(value, private)
    if kind == 'mcp' and mcp_auth.fingerprint(value) != previous_fingerprint:
        mcp_auth.delete_service_state(g.user['id'], resource_id)
    registry.save_record(kind, value, g.user['id'])
    return jsonify(success=True, data={'fields': {key: {'configured': bool(private.get(key))} for key in allowed}})














@runtime_settings_bp.route('/api/v1/sandbox-configs', methods=['GET', 'POST'])
def sandbox_configs():
    if request.method == 'POST':
        unavailable()
    from agent.sandbox import configuration
    return jsonify(success=True, data=[configuration(),
        *[{**registry.public(value), 'enabled': False, 'read_only': True}
          for value in registry.records('sandbox', g.user['id']) if value['id'] != 'state-backend']], workspace_scripts_disabled=True)


@runtime_settings_bp.route('/api/v1/sandbox-configs/<config_id>', methods=['GET', 'PUT', 'DELETE'])
def sandbox_config(config_id):
    if request.method != 'GET':
        unavailable()
    if config_id == 'state-backend':
        return jsonify(success=True, data={'id': config_id, 'name': '会话文件（无 Shell）', 'sandbox_type': '', 'config': {'sandbox_type': ''}})
    from agent.sandbox import CONFIG_ID, configuration
    if config_id == CONFIG_ID:
        return jsonify(success=True, data=configuration())
    value = registry.record('sandbox', config_id, g.user['id'])
    return jsonify(success=True, data={**registry.public(value), 'enabled': False, 'read_only': True})


@runtime_settings_bp.route('/api/v1/sandbox-configs/<config_id>/sandboxes')
def sandbox_inventory(config_id):
    if config_id == 'state-backend':
        return jsonify(success=True, data={'sandbox_count': 0, 'unverifiable': False})
    from agent.sandbox import CONFIG_ID, connection_config
    if config_id == CONFIG_ID:
        from opensandbox import SandboxManagerSync
        from opensandbox.models import SandboxFilter
        manager = SandboxManagerSync.create(connection_config=connection_config())
        try:
            result = manager.list_sandbox_infos(SandboxFilter(metadata={'application': 'showdoc-agent', 'owner_id': g.user['id']}))
            return jsonify(success=True, data={'sandbox_count': result.pagination.total_items, 'unverifiable': False})
        except Exception:
            return jsonify(success=True, data={'sandbox_count': None, 'unverifiable': True})
        finally:
            manager.close()
    registry.record('sandbox', config_id, g.user['id'])
    return jsonify(success=True, data={'sandbox_count': None, 'unverifiable': True, 'disabled': True})


@runtime_settings_bp.route('/api/v1/system/sandbox-check', methods=['POST'])
def sandbox_check():
    body = _body()
    from agent.sandbox import CONFIG_ID, connected_session, destroy_for_session, connection_config
    if body.get('config_id') != CONFIG_ID:
        unavailable()
    if body.get('config') is not None:
        raise StoreError('OpenSandbox 使用服务器托管策略，不能从浏览器覆盖配置', 501)
    if not isinstance(body.get('deep', False), bool):
        raise StoreError('deep 必须为布尔值', 400)
    from opensandbox import SandboxManagerSync
    from opensandbox.models import SandboxFilter
    manager = SandboxManagerSync.create(connection_config=connection_config())
    checks = []
    try:
        manager.list_sandbox_infos(SandboxFilter(metadata={'owner_id': g.user['id']}, page_size=1))
        checks.append({'name': 'control', 'ok': True})
    except Exception:
        checks.append({'name': 'control', 'ok': False, 'message': '无法连接 OpenSandbox 控制服务'})
    finally:
        manager.close()
    if checks[0]['ok'] and body.get('deep'):
        import uuid
        from langchain_opensandbox import OpenSandboxBackend
        probe = 'probe-' + str(uuid.uuid4())
        try:
            with connected_session(g.user['id'], probe, create=True) as sandbox:
                result = OpenSandboxBackend(sandbox=sandbox, timeout=15).execute('printf opensandbox-ok')
                checks.append({'name': 'execute', 'ok': result.exit_code == 0 and result.output == 'opensandbox-ok'})
        except StoreError:
            checks.append({'name': 'execute', 'ok': False, 'message': '创建或执行沙箱失败'})
        finally:
            destroy_for_session(g.user['id'], probe)
    return jsonify(success=True, data={'ok': all(item['ok'] for item in checks),
        'provider': 'opensandbox', 'checks': checks})








@runtime_settings_bp.route('/api/v1/web-search-providers/types')
def search_types():
    return jsonify(success=True, data=[], supported=False)


@runtime_settings_bp.route('/api/v1/web-search-providers', methods=['GET', 'POST'])
@runtime_settings_bp.route('/api/v1/web-search/providers')
def search_providers():
    if request.method == 'POST':
        unavailable()
    value = [{**registry.public(item), 'enabled': False, 'read_only': True}
             for item in registry.records('web-search', g.user['id'])]
    return jsonify(success=True, data=value)


@runtime_settings_bp.route('/api/v1/web-search-providers/<provider_id>', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
def search_provider(provider_id):
    value = registry.record('web-search', provider_id, g.user['id'])
    if request.method != 'GET':
        unavailable()
    return jsonify(success=True, data={**registry.public(value), 'enabled': False, 'read_only': True})


@runtime_settings_bp.route('/api/v1/web-search-providers/<provider_id>/test', methods=['POST'])
@runtime_settings_bp.route('/api/v1/web-search-providers/test', methods=['POST'])
def test_search(provider_id=None):
    if provider_id:
        registry.record('web-search', provider_id, g.user['id'])
    unavailable()


@runtime_settings_bp.route('/api/v1/tenants/kv/<key>', methods=['GET', 'PUT'])
def settings(key):
    defaults = {'default-settings': {'summary_model_id': 'agent-main', 'chat_model_id': 'agent-main', 'utility_model_id': 'agent-main',
        'embedding_model_id': '', 'rerank_model_id': '', 'vlm_model_id': '', 'asr_model_id': '', 'agent_enabled': True},
        'retrieval-config': {}, 'web-search-config': {'enabled': False}, 'skill-installer-model': {'model_id': ''},
        'memory-config': {'enabled': False, 'write_mode': 'explicit_only', 'extract_model_id': '',
            'max_items': 0, 'extract_delay_seconds': 0, 'extract_min_interval_seconds': 0,
            'extract_instructions': '', 'interest_threshold': 0, 'retrieval_conditioning': False,
            'embedding_model_id': '', 'vector_recall': False},
        'prompt-templates': {'system_prompt': [], 'agent_system_prompt': [], 'context_template': [], 'rewrite': [], 'fallback': []}}
    if key not in defaults:
        raise StoreError('配置不存在', 404)
    if key == 'memory-config':
        from agent.memory_files import policy
        if request.method == 'PUT':
            updates = _body()
            if set(updates) != {'enabled'}:
                raise StoreError('当前仅支持 AGENTS.md 文件记忆开关；结构化提炼和召回配置尚未接入', 501)
            if not isinstance(updates['enabled'], bool):
                raise StoreError('文件记忆开关必须为 enabled 布尔值', 400)
            saved = next((item for item in registry.records('settings', g.user['id']) if item['id'] == key), None)
            registry.save_record('settings', {**(saved or {}), 'id': key,
                'value': {**(saved or {}).get('value', {}), **updates}}, g.user['id'])
        return jsonify(success=True, data={**defaults[key], 'enabled': policy(g.user['id'])['workspace_enabled'],
            'supported': True, 'write_mode': 'native_file', 'storage_mode': 'agents_md', 'structured_memory_supported': False})
    read_only = key in ('web-search-config', 'skill-installer-model')
    if read_only and request.method != 'GET':
        unavailable()
    saved = next((item for item in registry.records('settings', g.user['id']) if item['id'] == key), None)
    value = {**defaults[key], **(saved.get('value', {}) if saved else {})}
    if read_only:
        value['read_only'] = True
        if key == 'web-search-config':
            value['enabled'] = False
    if request.method == 'PUT':
        updates = _body()
        value.update(updates)
        if key == 'default-settings' and 'chat_model_id' in updates and 'summary_model_id' not in updates:
            value['summary_model_id'] = updates['chat_model_id']
        registry.save_record('settings', {'id': key, 'name': key, 'value': value}, g.user['id'])
    return jsonify(success=True, data=value)


@runtime_settings_bp.route('/api/v1/memory/settings', methods=['GET', 'PUT'])
def memory_settings():
    from agent.memory_files import policy
    if request.method == 'PUT':
        body = _body()
        if set(body) != {'enabled'} or not isinstance(body['enabled'], bool):
            raise StoreError('个人记忆开关必须为 enabled 布尔值', 400)
        # Adopt both owner-scoped legacy gates without changing their state on reads.
        with connection() as conn:
            saved = {item['id']: item for item in registry.records('settings', g.user['id'], _connection=conn)}
            for key in ('memory-config', 'memory-preference'):
                previous = saved.get(key, {})
                registry.save_record('settings', {**previous, 'id': key,
                    'value': {**previous.get('value', {}), **body}}, g.user['id'], _connection=conn)
    return jsonify(success=True, data=policy(g.user['id']))


@runtime_settings_bp.route('/api/v1/agents/<agent_id>/memory-file', methods=['GET', 'PUT'])
def memory_file(agent_id):
    from agent.config import load_agent
    from agent.checkpointer import async_store
    from agent.memory_files import namespace, policy
    from deepagents.backends.utils import create_file_data, file_data_to_string
    agent = load_agent(agent_id, g.user['id'])
    owner_id = g.user['id']
    selected_namespace = namespace(owner_id, agent['id'])
    content = _body().get('content') if request.method == 'PUT' else None
    if request.method == 'PUT' and (not isinstance(content, str) or len(content) > 100_000):
        raise StoreError('记忆文件必须是不超过 100000 字符的文本', 400)
    if content is not None:
        try:
            content.encode('utf-8')
        except UnicodeEncodeError as exc:
            raise StoreError('记忆文件必须为有效 UTF-8 文本', 400) from exc
    async def access():
        async with async_store() as store:
            previous = await store.aget(selected_namespace, '/AGENTS.md')
            if content is not None:
                value = create_file_data(content, created_at=previous.value.get('created_at') if previous else None)
                await store.aput(selected_namespace, '/AGENTS.md', value, index=False)
            elif previous:
                value = previous.value
            else:
                value = None
            if value and value.get('encoding', 'utf-8') != 'utf-8':
                raise StoreError('AGENTS.md 记忆文件不是 UTF-8 文本', 409)
            return {'content': file_data_to_string(value) if value else '',
                    'created_at': value.get('created_at') if value else None,
                    'modified_at': value.get('modified_at') if value else None}
    value = asyncio.run(access())
    return jsonify(success=True, data={**value, 'agent_id': agent['id'], 'file_path': f'/memories/{agent["id"]}/AGENTS.md',
        'storage_mode': 'agents_md', 'effective': policy(owner_id)['effective'] and agent['config']['memory_enabled']})


@runtime_settings_bp.route('/api/v1/memory/items', methods=['GET', 'POST', 'DELETE'])
@runtime_settings_bp.route('/api/v1/memory/items/<path:item_id>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@runtime_settings_bp.route('/api/v1/memory/consolidate', methods=['POST'])
@runtime_settings_bp.route('/api/v1/memory/topics', methods=['GET'])
@runtime_settings_bp.route('/api/v1/memory/topics/<path:item_id>', methods=['POST', 'DELETE'])
@runtime_settings_bp.route('/api/v1/memory/documents', methods=['GET'])
@runtime_settings_bp.route('/api/v1/memory/documents/<path:item_id>', methods=['DELETE'])
@runtime_settings_bp.route('/api/v1/memory/export', methods=['GET'])
def structured_memory_unavailable(item_id=None):
    raise StoreError('当前使用原生 AGENTS.md 文件记忆，结构化提炼、审核、话题与向量召回尚未接入', 501)
