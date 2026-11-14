"""Runtime settings used by the original model, MCP and Skills panels."""
import asyncio

from flask import Blueprint, g, jsonify, request

from agent import registry
from webapi.legacy_runtime import unavailable
from governance.store import StoreError

runtime_settings_bp = Blueprint('runtime_settings', __name__)


def _body():
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise StoreError('请求必须为 JSON 对象', 400)
    return value


@runtime_settings_bp.route('/api/v1/models', methods=['GET', 'POST'])
def models():
    value = registry.public(registry.save_model(_body(), g.user['id'])) if request.method == 'POST' else registry.models(g.user['id'])
    return jsonify(success=True, data=value)


@runtime_settings_bp.route('/api/v1/models/providers')
def model_providers():
    return jsonify(success=True, data=[{'value': 'generic', 'label': 'OpenAI-compatible',
        'description': '用户提供的 OpenAI 兼容 API', 'api': 'chat_completions', 'requiresAuth': True,
        'defaultUrls': {}, 'modelTypes': ['KnowledgeQA', 'VLLM', 'ASR', 'Embedding', 'Rerank'], 'models': []},
        {'value': 'aliyun', 'label': '阿里云百炼', 'description': '百炼 OpenAI 兼容接口', 'api': 'chat_completions',
         'requiresAuth': True, 'defaultUrls': {'KnowledgeQA': 'https://dashscope.aliyuncs.com/compatible-mode/v1'},
         'modelTypes': ['KnowledgeQA', 'VLLM'], 'models': []}])


@runtime_settings_bp.route('/api/v1/models/catalog/resolve', methods=['POST'])
def resolve_model_catalog():
    body = _body()
    spec = body.get('spec') or {}
    capabilities = {'provider': body.get('provider', 'generic'), 'api': 'chat_completions', 'cataloged': False,
        'reasoning': bool(spec.get('reasoning', body.get('provider') == 'aliyun')),
        'thinking_format': 'enable_thinking' if body.get('provider') == 'aliyun' else 'reasoning_effort',
        'thinking_levels': ['off', 'auto'] if body.get('provider') == 'aliyun' else [],
        **{key: spec[key] for key in ('context_window', 'max_output_tokens', 'input') if key in spec}}
    return jsonify(success=True, data={'provider': capabilities['provider'], 'api': capabilities['api'],
        'base_url': body.get('base_url', ''), 'remote_model': body.get('remote_model_name') or body.get('model', ''),
        'cataloged': False, 'model': {}, 'capabilities': capabilities})


@runtime_settings_bp.route('/api/v1/models/<model_id>', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
def model(model_id):
    if model_id == 'agent-main':
        if request.method != 'GET':
            raise StoreError('环境模型请通过服务器环境配置；可以复制为个人模型', 400)
        return jsonify(success=True, data=registry.environment_model())
    if request.method == 'DELETE':
        from agent.config import list_agents
        if any(item['config'].get('model_id') == model_id for item in list_agents(g.user['id'])):
            raise StoreError('模型正被 Agent 使用，请先更换模型', 409)
        if any(model_id in item.get('value', {}).values() for item in registry.records('settings', g.user['id']) if item['id'] == 'default-settings'):
            raise StoreError('模型正用于默认设置，请先更换默认模型', 409)
        registry.delete_record('model', model_id, g.user['id'])
        return jsonify(success=True)
    value = registry.save_model(_body(), g.user['id'], model_id) if request.method != 'GET' else registry.record('model', model_id, g.user['id'])
    return jsonify(success=True, data=registry.public(value))


@runtime_settings_bp.route('/api/v1/models/<model_id>/copy', methods=['POST'])
def copy_model(model_id):
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
    from agent.config import list_agents
    registry.model_config(model_id, g.user['id'])
    agents = [item for item in list_agents(g.user['id']) if item['config'].get('model_id') == model_id]
    return jsonify(success=True, data={'model_id': model_id, 'agents': agents, 'knowledge_bases': [], 'in_use': bool(agents)})


@runtime_settings_bp.route('/api/v1/models/<model_id>/debug', methods=['POST'])
def debug_model(model_id):
    from agent.graph import build_model
    body = _body()
    config = {'model_id': model_id, 'temperature': body.get('temperature', 0), 'max_completion_tokens': body.get('max_tokens', 128)}
    output = build_model(config, g.user['id']).invoke(body.get('input') or body.get('query') or '请回复 OK')
    return jsonify(success=True, data={'content': output.content, 'model_id': model_id})


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
        'enabled': True, 'require_approval': (tool.metadata or {}).get('readOnlyHint') is not True,
        **value.get('tool_approvals', {}).get(tool.name, {}),
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
    value = registry.record('mcp', service_id, g.user['id'])
    flags = value.setdefault('tool_approvals', {})
    if tool_name:
        body = _body()
        updates = {key: body[key] for key in ('enabled', 'require_approval') if key in body}
        if not updates or any(not isinstance(item, bool) for item in updates.values()):
            raise StoreError('工具开关必须为布尔值', 400)
        flags[tool_name] = {**flags.get(tool_name, {}), **updates}
        registry.save_record('mcp', value, g.user['id'])
    return jsonify(success=True, data=[{'id': name, 'service_id': service_id, 'tool_name': name, **settings} for name, settings in flags.items()])


@runtime_settings_bp.route('/api/v1/<resource>/<resource_id>/credentials', methods=['PUT'])
@runtime_settings_bp.route('/api/v1/<resource>/<resource_id>/credentials/<field>', methods=['DELETE'])
def credentials(resource, resource_id, field=None):
    kind = {'models': 'model', 'mcp-services': 'mcp', 'web-search-providers': 'web-search'}.get(resource)
    if not kind:
        raise StoreError('配置类型无效', 404)
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
    return jsonify(success=True, data=[{'id': 'state-backend', 'name': '会话文件（无 Shell）', 'type': 'state', 'enabled': True,
        'sandbox_type': 'state', 'config': {'type': 'state'},
        'skills_available': True, 'capabilities': {'shell': False, 'filesystem': True}},
        *[{**registry.public(value), 'enabled': False, 'read_only': True} for value in registry.records('sandbox', g.user['id'])]], workspace_scripts_disabled=True)


@runtime_settings_bp.route('/api/v1/sandbox-configs/<config_id>', methods=['GET', 'PUT', 'DELETE'])
def sandbox_config(config_id):
    if request.method != 'GET':
        unavailable()
    if config_id == 'state-backend':
        return jsonify(success=True, data={'id': config_id, 'name': '会话文件（无 Shell）', 'sandbox_type': 'state', 'config': {'sandbox_type': 'state'}})
    value = registry.record('sandbox', config_id, g.user['id'])
    return jsonify(success=True, data={**registry.public(value), 'enabled': False, 'read_only': True})


@runtime_settings_bp.route('/api/v1/sandbox-configs/<config_id>/sandboxes')
def sandbox_inventory(config_id):
    if config_id == 'state-backend':
        return jsonify(success=True, data={'sandbox_count': 0, 'unverifiable': False})
    registry.record('sandbox', config_id, g.user['id'])
    return jsonify(success=True, data={'sandbox_count': None, 'unverifiable': True, 'disabled': True})


@runtime_settings_bp.route('/api/v1/system/sandbox-check', methods=['POST'])
def sandbox_check():
    unavailable()








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
        if request.method != 'GET':
            raise StoreError('跨会话长期记忆尚未接入；当前仅提供官方 Harness 会话状态持久化', 501)
        return jsonify(success=True, data={**defaults[key], 'read_only': True, 'supported': False})
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
        if key == 'default-settings':
            for name, model_id in value.items():
                if name.endswith('_model_id') and model_id:
                    registry.model_config(model_id, g.user['id'])
        registry.save_record('settings', {'id': key, 'name': key, 'value': value}, g.user['id'])
    return jsonify(success=True, data=value)


@runtime_settings_bp.route('/api/v1/memory/settings', methods=['GET', 'PUT'])
def memory_settings():
    if request.method != 'GET':
        raise StoreError('跨会话长期记忆尚未接入；当前仅提供官方 Harness 会话状态持久化', 501)
    return jsonify(success=True, data={'workspace_enabled': False, 'user_enabled': False,
        'effective': False, 'write_mode': 'explicit_only', 'max_items': 0, 'supported': False,
        'item_count': len(registry.records('memory', g.user['id']))})
