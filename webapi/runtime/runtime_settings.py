"""Runtime settings used by the original model, MCP and Skills panels."""
import asyncio

from flask import Blueprint, g, jsonify, request
from psycopg.types.json import Jsonb

from agent import registry
from webapi.retired_runtime import unavailable
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


def _model_access():
    return {'admin': g.user['role'] == 'admin', 'system_admin': bool(g.user.get('is_system_admin'))}


def _require_model_edit(value):
    if value.get('is_builtin'):
        if not g.user.get('is_system_admin'):
            raise StoreError('only system administrators can update builtin models', 403)
    else:
        _require_model_admin()


@runtime_settings_bp.route('/api/v1/models', methods=['GET', 'POST'])
def models():
    owner = g.user['id']
    if request.method == 'GET':
        return jsonify(success=True, data=registry.models(owner, **_model_access()))
    _require_model_admin()
    body = _body()
    missing = [key.title() for key in ('name', 'type', 'source') if not body.get(key)]
    if body.get('parameters') is None:
        missing.append('Parameters')
    if missing:
        raise StoreError('\n'.join(f"Key: 'CreateModelRequest.{field}' Error:Field validation for '{field}' failed on the 'required' tag"
                                   for field in missing), 400)
    if not isinstance(body['parameters'], dict):
        raise StoreError('parameters 必须为 JSON 对象', 400)
    with connection() as conn:
        value = registry.save_model(body, owner, _connection=conn)
        saved = registry.model_record(value['id'], owner, _connection=conn)
    return jsonify(success=True, data=registry.model_response(saved, **_model_access())), 201


@runtime_settings_bp.route('/api/v1/models/providers')
@runtime_settings_bp.route('/api/v1/models/providers/<provider>')
def model_providers(provider=None):
    from agent.model_catalog import PROVIDERS, TYPES, provider_option
    short = request.args.get('model_type', '').lower()
    short = 'chat' if short == 'knowledgeqa' else short
    if short and short not in TYPES:
        raise StoreError('模型类型无效', 400)
    admin = getattr(g, 'user', {}).get('role') == 'admin'
    if provider:
        if provider not in PROVIDERS:
            raise StoreError('provider not found', 404)
        if short and short not in PROVIDERS[provider]['modelTypes']:
            raise StoreError('provider does not offer this model_type', 400)
        data = dict(provider_option(provider, short, admin))
        keyword = request.args.get('keyword', '').strip().casefold()
        if keyword and 'models' in data:
            matches = [m for m in data.pop('models') if keyword in m['id'].casefold() or keyword in m['name'].casefold()]
            if matches:
                data['models'] = matches
    else:
        data = [provider_option(key, short, admin) for key, meta in PROVIDERS.items() if not short or short in meta['modelTypes']]
    return jsonify(success=True, data=data)


@runtime_settings_bp.route('/api/v1/models/catalog/resolve', methods=['GET', 'POST'])
def resolve_model_catalog():
    from agent.model_catalog import PROVIDERS, TYPES, provider_id
    from agent.models import validate_model_runtime
    body = _body() if request.method == 'POST' else request.args
    params = {key: body[key] for key in ('provider', 'base_url', 'context_window', 'max_output_tokens', 'spec') if key in body}
    if not all(isinstance(params.get(k, ''), str) for k in ('provider', 'base_url')):
        raise StoreError('服务商和地址必须为字符串', 400)
    fields = PROVIDERS[provider_id(params)].get('extraFields', [])
    keys = ['api', 'thinking_control', 'remote_model_name', *[f['key'] for f in fields if not f.get('secret') and f.get('type') != 'password']]
    params['extra_config'] = {k: body[k] for k in keys if body.get(k)}
    category = body.get('model_type') or 'chat'
    if not isinstance(category, str):
        raise StoreError('模型类型无效', 400)
    kind = TYPES.get(category.lower(), 'KnowledgeQA')
    r = validate_model_runtime({'name': body.get('model', ''), 'type': kind, 'parameters': params})
    data = {k: r[k] for k in ('provider', 'remote_model', 'cataloged', 'model', 'capabilities')}
    data['api'] = r['capabilities']['api']
    if getattr(g, 'user', {}).get('role') == 'admin':
        data['base_url'] = r['base_url']
        if r['url']:
            data['url'] = r['url']
    return jsonify(success=True, data=data)


@runtime_settings_bp.route('/api/v1/models/<model_id>', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
def model(model_id):
    owner = g.user['id']
    if request.method == 'GET':
        value = registry.model_record(model_id, owner)
    else:
        with registry.model_bindings_transaction(owner) as conn:
            value = registry.model_record(model_id, owner, _connection=conn, lock=True)
            if request.method == 'DELETE':
                _require_model_admin()
                if value.get('is_builtin'):
                    raise StoreError('builtin models cannot be deleted', 400)
                usage = registry.model_usage(model_id, owner, _connection=conn)
                if registry.model_in_use(usage):
                    counts = [(usage['knowledge_base_total'], 'knowledge base(s)'), (usage['agent_total'], 'agent(s)')]
                    bindings = [f'{count} {label}' for count, label in counts if count]
                    if usage['long_term_memory']['bindings']:
                        bindings.append('long-term memory')
                    message = 'model is used by ' + ' and '.join(bindings) + '; reconfigure or remove those references before deleting'
                    return jsonify(success=False, error={'code': 2300,
                        'message': message, 'details': usage}), 400
                registry.delete_record('model', model_id, owner, _connection=conn)
                return jsonify(success=True, message='Model deleted')
            _require_model_edit(value)
            body = _body()
            if request.method == 'PATCH':
                updates = {key: body[key] for key in ('display_name', 'description') if body.get(key) is not None}
                if not updates or any(not isinstance(v, str) for v in updates.values()):
                    raise StoreError('display_name or description is required', 400)
                if 'display_name' in updates:
                    updates['display_name'] = updates['display_name'].strip()
                if value.get('_from_environment'):
                    # A rename must keep following the environment endpoint and key.
                    value = {k: value[k] for k in ('id','_kind','is_builtin','_from_environment','created_at',
                                                   'display_name','description') if k in value}
                    registry.save_record('model', {**value, **updates}, '', _connection=conn)
                else:
                    registry.persist_model({**value, **updates}, owner, conn)
            else:
                if isinstance(body.get('parameters'), dict):
                    body['parameters'].setdefault('spec', {})
                registry.save_model(body, owner, stored=value, _connection=conn)
            value = registry.model_record(model_id, owner, _connection=conn)
    return jsonify(success=True, data=registry.model_response(value, **_model_access()))


@runtime_settings_bp.route('/api/v1/models/<model_id>/copy', methods=['POST'])
def copy_model(model_id):
    _require_model_admin()
    display_name = _body().get('display_name')
    if not isinstance(display_name, str) or not display_name.strip():
        raise StoreError('display_name is required', 400)
    owner = g.user['id']
    with registry.model_bindings_transaction(owner) as conn:
        value = registry.model_record(model_id, owner, _connection=conn, lock=True)
        if value.get('is_builtin'):
            raise StoreError('builtin models cannot be copied', 400)
        value['display_name'] = display_name.strip()
        value['parameters'].update(registry.secrets(value))
        saved = registry.save_model(value, owner, _connection=conn)
        copied = registry.model_record(saved['id'], owner, _connection=conn)
    return jsonify(success=True, data=registry.model_response(copied, **_model_access())), 201


@runtime_settings_bp.route('/api/v1/models/<model_id>/usage')
def model_usage(model_id):
    registry.model_record(model_id, g.user['id'])
    usage = registry.model_usage(model_id, g.user['id'])
    return jsonify(success=True, data={'model_id': model_id, **usage, 'in_use': registry.model_in_use(usage)})


@runtime_settings_bp.route('/api/v1/models/<model_id>/debug', methods=['POST'])
def debug_model(model_id):
    _require_model_admin()
    import asyncio
    import json
    import time
    from agent.config import validate_config
    from agent.models import build_model_record, supports_image_input
    from agent.model_catalog import LEVELS, resolve
    from webapi.runtime.model_runtime import debug_chat_stream, debug_nonchat_model, debug_preview
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
    options = {key: options[key] for key in ('system_prompt', 'temperature', 'top_p', 'max_tokens', 'thinking',
                                             'reasoning_effort', 'similarity') if options.get(key) is not None}
    if 'max_tokens' in options and (type(options['max_tokens']) is not int or not 1 <= options['max_tokens'] <= 8192):
        raise StoreError('max_tokens must be between 1 and 8192', 400)
    if 'top_p' in options and (type(options['top_p']) not in (float, int) or not 0 < options['top_p'] <= 1):
        raise StoreError('top_p must be greater than 0 and at most 1', 400)
    if 'temperature' in options and (type(options['temperature']) not in (float, int) or not 0 <= options['temperature'] <= 2):
        raise StoreError('temperature must be between 0 and 2', 400)
    if options.get('reasoning_effort', '') not in ('', *LEVELS):
        raise StoreError(f"reasoning_effort must be one of [{' '.join(LEVELS)}]", 400)
    if any(type(options[key]) is not bool for key in ('thinking', 'similarity') if key in options):
        raise StoreError('thinking and similarity must be booleans', 400)
    saved = registry.model_config(model_id, g.user['id'])
    if saved['type'] not in ('KnowledgeQA', 'VLLM'):
        return debug_nonchat_model(saved, body, options, request.files.get('file'))
    config = validate_config({'model_id': model_id, 'temperature': options.get('temperature', 0),
        'max_completion_tokens': options.get('max_tokens', 2048), 'thinking': options.get('thinking', False),
        'reasoning_effort': options.get('reasoning_effort', '')})
    query = body.get('input', body.get('query', ''))
    if not isinstance(query, str) or len(query.encode()) > 64 * 1024:
        raise StoreError('input is too long', 400)
    prompt = options.get('system_prompt', '')
    if not isinstance(prompt, str) or len(prompt) > 100000:
        raise StoreError('调试系统提示词无效', 400)
    messages = ([{'role': 'system', 'content': prompt}] if prompt else []) + [{'role': 'user', 'content': query}]
    file = request.files.get('file')
    resolved = resolve(saved)
    caps = resolved['capabilities']
    if not file and not query.strip() and saved['type'] == 'KnowledgeQA':
        raise StoreError('query cannot be empty', 400)
    size = 0
    if saved['type'] == 'VLLM' and not file:
        raise StoreError('请提供视觉模型调试图片', 400)
    if file and not supports_image_input(saved):
        raise StoreError('当前对话模型不支持图片输入', 400)
    if file:
        import base64
        from webapi.chat.chat_resources import debug_image
        data = file.read(10 * 1024 * 1024 + 1)
        size = len(data)
        if size > 10 * 1024 * 1024:
            raise StoreError('调试图片不能超过 10 MB', 400)
        mime, data = debug_image(file.filename or 'image', data)
        messages[-1]['content'] = [{'type': 'text', 'text': query}, {'type': 'image_url', 'image_url': {
            'url': f'data:{mime};base64,' + base64.b64encode(data).decode()}}]
    model = build_model_record(saved, config)
    if 'top_p' in options and model.temperature is not None and resolved['compat'].get('supports_top_p', True):
        model = model.bind(top_p=options['top_p'])
    started = time.monotonic()
    request_info = debug_preview(saved, query, options, upload=file, size=size)
    effort = config.get('reasoning_effort') or (('auto' if config['thinking'] else 'off') if 'thinking' in options else '')
    control = caps['thinking_format'] if caps.get('thinking_levels') else 'none'
    observations = {'api': caps['api'], 'capabilities': caps, 'requested_reasoning_effort': effort,
                    'stream': True, 'requested_thinking': effort not in ('', 'off'), 'thinking_control': control,
                    'thinking_parameter_sent': bool(effort) and control != 'none'} if saved['type'] == 'KnowledgeQA' else {}
    try:
        raw = asyncio.run(debug_chat_stream(model, messages))
        observations['answer_characters'] = len(raw['content'])
        if saved['type'] == 'KnowledgeQA':
            reasoning = raw.get('reasoning_content', '')
            observations.update(reasoning_characters=len(reasoning), reasoning_returned=bool(reasoning.strip()))
        result = {'ok': True, 'raw_response': raw if saved['type'] == 'KnowledgeQA' else raw['content']}
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
        from agent import model_secrets
        owner = g.user['id']
        with registry.model_bindings_transaction(owner) as conn:
            value = registry.model_record(resource_id, owner, _connection=conn, lock=True)
            _require_model_edit(value)
            updates = {field: ''} if field else _body()
            if set(updates) - set(model_secrets.FIELDS) or any(not isinstance(v, str) for v in updates.values()):
                raise StoreError('unknown credential field', 400)
            private = model_secrets.read(value)
            if any(private.get(k, '') != v for k,v in updates.items()):
                private.update(updates)
                registry.persist_model(model_secrets.store(value, private), owner, conn)
        if field:
            return '', 204
        return jsonify(success=True, data={'fields': {k: {'configured': bool(private.get(k))} for k in model_secrets.FIELDS}})
    value = registry.record(kind, resource_id, g.user['id'])
    if kind == 'web-search':
        unavailable()
    from agent import mcp_auth
    previous_fingerprint = mcp_auth.fingerprint(value) if kind == 'mcp' else None
    private = registry.secrets(value)
    allowed = ('api_key', 'token', 'client_secret')
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
    if key == 'default-settings':
        if request.method == 'GET':
            return jsonify(success=True, data=registry.workspace_defaults(g.user['id']))
        _require_model_admin()
        value = registry.save_workspace_defaults(g.user['id'], _body())
        return jsonify(success=True, data=value, message='Default settings updated successfully')
    from agent.config import default_prompt_templates
    defaults = {'retrieval-config': {'top_k': 10, 'similarity_threshold': 0.6, 'vector_weight': 0.7, 'query_rewrite': True},
        'web-search-config': {'enabled': False}, 'skill-installer-model': {'model_id': ''},
        'memory-config': {'enabled': False, 'write_mode': 'explicit_only', 'extract_model_id': '',
            'max_items': 0, 'extract_delay_seconds': 0, 'extract_min_interval_seconds': 0,
            'extract_instructions': '', 'interest_threshold': 0, 'retrieval_conditioning': False,
            'embedding_model_id': '', 'vector_recall': False},
        'prompt-templates': default_prompt_templates()}
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
        if key == 'retrieval-config':
            # 只接受 ContextDB 官方 query 契约支持的透传参数；top_k 上限取 REST 的 1–10。
            allowed_keys = {'top_k', 'similarity_threshold', 'vector_weight', 'query_rewrite'}
            if set(updates) - allowed_keys:
                raise StoreError(f'retrieval-config 仅支持 {sorted(allowed_keys)}', 400)
            for name, item in updates.items():
                if name == 'top_k':
                    if not isinstance(item, int) or isinstance(item, bool) or not 1 <= item <= 10:
                        raise StoreError('top_k 必须是 1–10 的整数', 400)
                elif name == 'query_rewrite':
                    if not isinstance(item, bool):
                        raise StoreError('query_rewrite 必须是布尔值', 400)
                elif not isinstance(item, (int, float)) or isinstance(item, bool) or not 0 <= float(item) <= 1:
                    raise StoreError(f'{name} 必须是 0–1 的数值', 400)
        value.update(updates)
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
