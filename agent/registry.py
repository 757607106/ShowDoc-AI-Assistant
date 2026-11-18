"""Owner-scoped model, MCP and Skill configuration in existing runtime records."""
import asyncio
import copy
import json
import os
import re
import uuid
from contextlib import contextmanager, nullcontext
from urllib.parse import urlsplit

from psycopg.types.json import Jsonb

from agent import model_secrets
from governance.database import connection
from governance.store import StoreError

MASKED = '********'
EMBEDDING_DEFAULTS = {'dimension': 0, 'truncate_prompt_tokens': 0, 'supports_dimension_override': False}
AGENT_MODEL_FIELDS = {
    'model_id': ('chat_model', ('KnowledgeQA', 'VLLM')),
    'rerank_model_id': ('rerank_model', ('Rerank',)),
    'vlm_model_id': ('vlm_model', ('VLLM', 'KnowledgeQA')),
    'asr_model_id': ('asr_model', ('ASR',)),
    'query_understand_model_id': ('query_understand_model', ('KnowledgeQA', 'VLLM')),
}


def _masked_map(values, current):
    return {key: current[key] if value == MASKED and key in current else value for key, value in values.items()}


def _http_url(value):
    try:
        parsed = urlsplit(value)
        return parsed.scheme in ('http', 'https') and bool(parsed.hostname) and not parsed.username
    except (TypeError, ValueError):
        return False


def records(kind, owner_id, *, _connection=None):
    with nullcontext(_connection) if _connection is not None else connection() as conn:
        rows = conn.execute('SELECT payload FROM runtime_records WHERE owner_id=%s AND kind=%s ORDER BY created_at,id',
                            (owner_id, kind)).fetchall()
    return [row['payload'] for row in rows]


def record(kind, record_id, owner_id, *, _connection=None):
    with nullcontext(_connection) if _connection is not None else connection() as conn:
        row = conn.execute('SELECT payload FROM runtime_records WHERE owner_id=%s AND kind=%s AND record_key=%s',
                           (owner_id, kind, record_id)).fetchone()
    if row is None:
        raise StoreError('配置不存在或无权访问', 404)
    return row['payload']


def agent_model_references(config):
    values = [(config.get(field), binding, types) for field, (binding, types) in AGENT_MODEL_FIELDS.items()]
    subagents = config.get('subagents', [])
    if not isinstance(subagents, list) or any(not isinstance(item, dict) for item in subagents):
        raise StoreError('子代理配置必须为对象列表', 400)
    values.extend((item.get('model_id'), f'subagent:{item.get("name", index)}:model', ('KnowledgeQA', 'VLLM'))
                  for index, item in enumerate(subagents))
    return [(model_id, binding, types) for model_id, binding, types in values if model_id]


def _lock_model_bindings(conn, owner_id):
    conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('model-bindings:' + owner_id,))


@contextmanager
def model_bindings_transaction(owner_id):
    with connection() as conn:
        _lock_model_bindings(conn, owner_id)
        yield conn


def knowledge_model_bindings(owner_id, *, _connection=None):
    bases = {}
    for row in records('knowledge_space', owner_id, _connection=_connection):
        kb_id = row.get('knowledge_base_id')
        if kb_id and row.get('lifecycle') not in ('deleted', 'deleting', 'missing'):
            bindings = {field: row[field] for field in ('summary_model_id', 'embedding_model_id') if row.get(field)}
            if bindings:
                bases[kb_id] = {'id': kb_id, 'name': row.get('name') or kb_id, **bindings}
    return bases


def model_in_use(usage):
    return bool(usage['agent_total'] or usage['knowledge_base_total'] or usage['long_term_memory']['bindings'])


def model_usage(model_id, owner_id, *, _connection=None):
    agents = []
    for value in records('agent', owner_id, _connection=_connection):
        bindings = [binding for referenced, binding, _ in agent_model_references(value.get('config', {}))
                    if referenced == model_id]
        if bindings:
            agents.append({'id': value['id'], 'name': value.get('name', value['id']), 'bindings': bindings})
    agents.sort(key=lambda value: (value['name'], value['id']))
    bases = []
    for kb in knowledge_model_bindings(owner_id, _connection=_connection).values():
        bindings = [k.removesuffix('_id') for k in ('summary_model_id','embedding_model_id') if kb.get(k) == model_id]
        if bindings:
            bases.append({'id': kb['id'], 'name': kb['name'], 'bindings': bindings})
    bases.sort(key=lambda kb: (kb['name'], kb['id']))
    # Native AGENTS.md memory files do not bind an extraction or an embedding model.
    return {'knowledge_bases': bases[:50], 'agents': agents[:50], 'knowledge_base_total': len(bases),
            'agent_total': len(agents), 'long_term_memory': {'bindings': []}}


def save_record(kind, value, owner_id, *, _connection=None):
    from governance.store import now
    value = copy.deepcopy(value)
    value.setdefault('id', str(uuid.uuid4()))
    value.setdefault('created_at', now())
    value['updated_at'] = now()
    metadata = {'type': kind, 'owner_id': owner_id}
    with nullcontext(_connection) if _connection is not None else connection() as conn:
        if kind == 'settings' and value['id'] == 'default-settings':
            _lock_model_bindings(conn, owner_id)
            return {**value, 'value': save_workspace_defaults(owner_id, value['value'], _connection=conn)}
        if kind == 'agent':
            _lock_model_bindings(conn, owner_id)
            references = agent_model_references(value.get('config', {}))
            for model_id, binding, types in references:
                if not isinstance(model_id, str):
                    raise StoreError('模型 ID 必须为字符串', 400)
                model = model_config(model_id, owner_id, _connection=conn)
                if types and model['type'] not in types:
                    raise StoreError(f'{binding} 的模型类型必须为 {"、".join(types)}', 400)
                if binding == 'vlm_model' and model['type'] == 'KnowledgeQA' and not model.get('parameters', {}).get('supports_vision'):
                    raise StoreError('图片模型必须支持图片输入', 400)
                config = value.get('config', {})
                if kind == 'agent' and (binding == 'chat_model' or binding.startswith('subagent:')
                        or binding == 'vlm_model' and config.get('image_upload_enabled')):
                    from agent.models import completion_budget, model_capabilities
                    completion_budget(model_capabilities(model), config)
        conn.execute('''INSERT INTO runtime_records(id,owner_id,kind,record_key,name,payload,metadata)
            VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (owner_id,kind,record_key)
            DO UPDATE SET payload=excluded.payload,name=excluded.name,updated_at=now()''',
            (str(uuid.uuid4()), owner_id, kind, value['id'], value.get('name', value['id']), Jsonb(value), Jsonb(metadata)))
    return value


def delete_record(kind, record_id, owner_id, *, _connection=None):
    with nullcontext(_connection) if _connection is not None else connection() as conn:
        record(kind, record_id, owner_id, _connection=conn)
        conn.execute('DELETE FROM runtime_records WHERE owner_id=%s AND kind=%s AND record_key=%s',
                     (owner_id, kind, record_id))


def secrets(value):
    if value.get('_kind') == 'model':
        return model_secrets.read(value)
    from agent.credentials import cipher
    encrypted = value.get('_encrypted')
    return json.loads(cipher().decrypt(encrypted.encode())) if encrypted else {}


def with_secrets(value, private):
    if value.get('_kind') == 'model':
        return model_secrets.store(value, private)
    from agent.credentials import cipher
    value['_encrypted'] = cipher().encrypt(json.dumps(private).encode()).decode()
    return value


def public(value):
    if value.get('_kind') == 'model':
        return model_response(value)
    value = copy.deepcopy(value)
    private = secrets(value)
    value.pop('_encrypted', None)
    if value.get('_kind') in ('mcp', 'web-search'):
        fields = ('api_key', 'token', 'client_secret') if value['_kind'] == 'mcp' else ('api_key',)
        value['credentials'] = {key: {'configured': bool(private.get(key))} for key in fields}
    if value.get('_kind') == 'mcp':
        for key in ('headers', 'env_vars'):
            if private.get(key):
                value[key] = {name: MASKED for name in private[key]}
        if private.get('custom_headers'):
            value.setdefault('auth_config', {})['custom_headers'] = {name: MASKED for name in private['custom_headers']}
    if value.get('_kind') == 'sandbox' and private.get('env_vars'):
        value.setdefault('config', {})['env_vars'] = {key: MASKED for key in private['env_vars']}
    value.pop('_kind', None)
    return value


MODEL_SLOTS = {'chat_model_id': 'KnowledgeQA', 'embedding_model_id': 'Embedding', 'rerank_model_id': 'Rerank',
               'vlm_model_id': 'VLLM', 'asr_model_id': 'ASR', 'utility_model_id': 'Utility'}


def environment_model():
    name = os.getenv('AGENT_MAIN_MODEL', 'qwen-max')
    return {'id': 'agent-main', '_kind': 'model', 'name': name, 'display_name': name, 'type': 'KnowledgeQA',
            'source': 'remote', 'is_default': True, 'is_builtin': True, 'status': 'active',
            'parameters': {'model_name': name, 'provider': 'aliyun',
                'base_url': os.getenv('AGENT_BAILIAN_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
                if os.getenv('BAILIAN_API_KEY', '').strip() else (os.getenv('DASHSCOPE_API_URL') or
                    'https://llm-rtc5v8cnt0umugh9.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions'
                ).rstrip('/').removesuffix('/chat/completions')}, '_from_environment': True}


def _model_rows(owner_id, model_id=None, *, conn, lock=False):
    query = """SELECT r.owner_id,r.payload,r.created_at,r.updated_at,coalesce(w.id,0) AS tenant_id
        FROM runtime_records r LEFT JOIN platform_workspaces w ON w.principal_id=r.owner_id
        WHERE r.kind='model' AND (r.owner_id=%s OR r.payload @> '{"is_builtin":true}')"""
    args = [owner_id]
    if model_id is not None:
        query += ' AND r.record_key=%s'
        args.append(model_id)
    rows = conn.execute(query + ' ORDER BY r.created_at,r.id' + (' FOR UPDATE OF r' if lock else ''), args).fetchall()
    values = []
    for row in rows:
        value = row['payload']
        if value.get('_from_environment'):
            value = {**environment_model(), **value}
        value.setdefault('created_at', row['created_at'].isoformat())
        value.setdefault('updated_at', row['updated_at'].isoformat())
        value.update(_kind='model', tenant_id=row['tenant_id'], _storage_owner=row['owner_id'])
        values.append(value)
    return values


def model_record(model_id, owner_id, *, _connection=None, lock=False):
    with nullcontext(_connection) if _connection is not None else connection() as conn:
        rows = _model_rows(owner_id, model_id, conn=conn, lock=lock)
    if not rows:
        raise StoreError('Model not found', 404)
    return rows[0]


def model_response(value, *, admin=False, system_admin=False):
    from agent.model_catalog import PROVIDERS
    from agent.models import model_capabilities
    params = value.get('parameters', {})
    builtin = bool(value.get('is_builtin'))
    manage_builtin = builtin and system_admin
    visible = manage_builtin or (admin and not builtin)
    result = {key: value[key] for key in ('id', 'name', 'type', 'source', 'created_at', 'updated_at') if key in value}
    result.update(tenant_id=value.get('tenant_id', 0), display_name=value.get('display_name', ''),
                  description=value.get('description', ''), is_default=bool(value.get('is_default')), is_builtin=builtin,
                  status=value.get('status', 'active'))
    if value.get('default_for'):
        result['default_for'] = value['default_for']
    stored_embedding = params.get('embedding_parameters') or {}
    public_params = {'base_url': params.get('base_url', '') if visible else '',
                     'provider': params.get('provider', ''), 'supports_vision': bool(params.get('supports_vision')),
                     'interface_type': params.get('interface_type', ''), 'parameter_size': params.get('parameter_size', ''),
                     'embedding_parameters': {k: stored_embedding.get(k, default) for k, default in EMBEDDING_DEFAULTS.items()}}
    for key in ('context_window', 'max_output_tokens', 'max_concurrency'):
        if params.get(key):
            public_params[key] = params[key]
    if not builtin or manage_builtin:
        if params.get('app_id'):
            public_params['app_id'] = params['app_id']
        private = model_secrets.read(value, metadata=True)
        result['credentials'] = {key: {'configured': bool(private.get(key))} for key in model_secrets.FIELDS}
        fields = PROVIDERS.get(params.get('provider'), {}).get('extraFields', [])
        if any(field.get('key') == 'secret_key' for field in fields) or (params.get('extra_config') or {}).get('secret_key'):
            result['credentials']['secret_key'] = {'configured': bool(private.get('app_secret'))}
        if visible:
            extra = {k: v for k, v in (params.get('extra_config') or {}).items() if k != 'secret_key'}
            if extra:
                public_params['extra_config'] = extra
            if private.get('custom_headers'):
                public_params['custom_headers'] = dict.fromkeys(private['custom_headers'], MASKED)
            if params.get('spec'):
                public_params['spec'] = params['spec']
    result['parameters'] = public_params
    if value.get('source', 'remote') == 'remote' and value.get('type') != 'ASR':
        result['capabilities'] = model_capabilities(value)
    return result


def _supports(model, kind):
    kind = 'KnowledgeQA' if kind == 'Utility' else kind
    return model.get('type') == kind or (kind == 'VLLM' and model.get('type') == 'KnowledgeQA'
                                         and model.get('parameters', {}).get('supports_vision'))


def workspace_defaults(owner_id, *, _connection=None):
    with nullcontext(_connection) if _connection is not None else connection() as conn:
        row = conn.execute('SELECT default_settings FROM platform_workspaces WHERE principal_id=%s AND deleted_at IS NULL',
                           (owner_id,)).fetchone()
    values = row['default_settings'] if row else {}
    return {field: (values.get(field) or '').strip() for field in MODEL_SLOTS}


def save_workspace_defaults(owner_id, updates, *, _connection=None):
    if any(updates.get(field) is not None and not isinstance(updates[field], str) for field in MODEL_SLOTS):
        raise StoreError('模型 ID 必须为字符串', 400)
    values = {field: (updates.get(field) or '').strip() for field in MODEL_SLOTS}
    with nullcontext(_connection) if _connection is not None else model_bindings_transaction(owner_id) as conn:
        previous = workspace_defaults(owner_id, _connection=conn)
        rows = {row['id']: row for row in _model_rows(owner_id, conn=conn)}
        for field, kind in MODEL_SLOTS.items():
            model_id = values[field]
            if not model_id or model_id == previous[field]:
                continue
            row = rows.get(model_id)
            if not row:
                raise StoreError(f'{field}: model not found', 400)
            if not _supports(row, kind):
                raise StoreError(f'{field} must be a {"KnowledgeQA" if kind == "Utility" else kind} model', 400)
            if row.get('status', 'active') != 'active':
                raise StoreError(f'{field}: model is not active', 400)
        if not conn.execute('UPDATE platform_workspaces SET default_settings=%s,updated_at=now() WHERE principal_id=%s AND deleted_at IS NULL',
                            (Jsonb(values), owner_id)).rowcount:
            raise StoreError('Workspace not found', 404)
    return values


def models(owner_id, *, admin=False, system_admin=False):
    with connection() as conn:
        defaults = workspace_defaults(owner_id, _connection=conn)
        rows = _model_rows(owner_id, conn=conn)
    for field, kind in MODEL_SLOTS.items():
        selected = next((row for row in rows if row['id'] == defaults[field] and _supports(row, kind)
                         and row.get('status', 'active') == 'active'), None)
        if selected:
            selected.setdefault('default_for', []).append(kind)
            for row in rows:
                if row['type'] == kind:
                    row['is_default'] = row is selected
    return [model_response(row, admin=admin, system_admin=system_admin) for row in rows]


def default_model_id(owner_id, field='chat_model_id'):
    kind = MODEL_SLOTS[field]
    rows = models(owner_id)
    active = [row for row in rows if _supports(row, kind) and row['status'] == 'active']
    chosen = next((row for row in active if kind in row.get('default_for', [])), None)
    if not chosen and kind == 'Utility':
        chosen = next((row for row in active if 'KnowledgeQA' in row.get('default_for', [])), None)
        kind = 'KnowledgeQA'
    if not chosen:
        chosen = next((row for row in active if row['type'] == kind and row['is_default']), None)
    return (chosen or (active[0] if active else {})).get('id', '')


def model_config(model_id, owner_id, *, _connection=None):
    from governance.database import database_url
    from agent.models import validate_model_runtime
    if not database_url() and (not model_id or model_id == 'agent-main'):
        value = environment_model()
    else:
        value = model_record(model_id or 'agent-main', owner_id, _connection=_connection)
    validate_model_runtime(value)
    value['parameters'].update(model_secrets.read(value))
    (value['parameters'].get('extra_config') or {}).pop('secret_key', None)
    return value


def persist_model(value, owner_id, conn):
    storage_owner = value.pop('_storage_owner', owner_id)
    value.pop('_from_environment', None)
    return save_record('model', value, storage_owner, _connection=conn)


def save_model(body, owner_id, *, stored=None, _connection=None):
    from agent.models import model_headers, validate_model_runtime
    from agent.model_http import validate_model_address
    value = copy.deepcopy(stored) if stored else {'_kind': 'model'}
    original = value.setdefault('parameters', {})
    if body.get('source') == 'remote' and value.get('source') == 'local':
        original.pop('interface_type', None)
    if body.get('name') and original.get('model_name') == value.get('name'):
        original.pop('model_name', None)
    for key in ('name', 'display_name', 'type', 'source', 'description'):
        if key in body:
            if not isinstance(body[key], str):
                raise StoreError(f'{key} 必须为字符串', 400)
            value[key] = body[key]
    if not value.get('name', '').strip():
        raise StoreError('请提供模型名称', 400)
    params = copy.deepcopy(body.get('parameters', {}))
    if not isinstance(params, dict):
        raise StoreError('模型参数必须为对象', 400)
    if isinstance(params.get('embedding_parameters'), dict):
        params['embedding_parameters'] = {k: v for k, v in params['embedding_parameters'].items() if k in EMBEDDING_DEFAULTS}
    if stored and 'custom_headers' in params:
        existing_headers = model_secrets.read(value, metadata=True).get('custom_headers') or {}
        if params['custom_headers'] == dict.fromkeys(existing_headers, MASKED):
            params.pop('custom_headers')
    # Ordinary edits keep the stored ciphertext, including while a key is unavailable.
    needs_encryption = (not stored or value.get('_from_environment') or 'custom_headers' in params
                        or any(original.get(k) for k in (*model_secrets.FIELDS, 'custom_headers'))
                        or (original.get('extra_config') or {}).get('secret_key'))
    private = model_secrets.read(value) if needs_encryption else None
    extra = params.get('extra_config')
    if isinstance(extra, dict) and 'secret_key' in extra:
        params.setdefault('app_secret', extra.pop('secret_key'))
    for key in model_secrets.FIELDS:
        if key in params:
            submitted = params.pop(key)
            if not stored:
                if not isinstance(submitted, str):
                    raise StoreError('模型凭据必须为字符串', 400)
                private[key] = submitted
    if 'custom_headers' in params:
        headers = params.pop('custom_headers')
        if not isinstance(headers, dict) or any(not isinstance(v, str) for v in headers.values()):
            raise StoreError('自定义请求头必须为字符串映射', 400)
        private['custom_headers'] = _masked_map(headers, private.get('custom_headers', {}))
        model_headers({'parameters': {'custom_headers': private['custom_headers']}})
    value['parameters'] = {**original, **params}
    value.setdefault('type', 'KnowledgeQA')
    value.setdefault('source', 'remote')
    if not stored or stored.get('source') == 'local' and value['source'] == 'remote':
        value['status'] = 'active'
    resolved = validate_model_runtime(value)
    if not resolved['base_url']:
        raise StoreError('请提供有效的模型 API 地址', 400)
    validate_model_address(resolved['base_url'])
    if private is not None:
        model_secrets.store(value, private)
    with nullcontext(_connection) if _connection is not None else connection() as conn:
        return persist_model(value, owner_id, conn)


def save_mcp(body, owner_id, service_id=None):
    value = copy.deepcopy(record('mcp', service_id, owner_id)) if service_id else {'_kind': 'mcp', 'enabled': True}
    from agent import mcp_auth
    previous_fingerprint = mcp_auth.fingerprint(value) if service_id else None
    private = secrets(value)
    value.update({key: body[key] for key in ('name', 'description', 'usage_instructions', 'enabled', 'transport_type',
                                           'url', 'advanced_config', 'stdio_config') if key in body})
    if not isinstance(value.get('name'), str) or not value['name'].strip():
        raise StoreError('请提供 MCP 服务名称', 400)
    transport = value.get('transport_type', 'http-streamable')
    if transport not in ('http-streamable', 'sse', 'stdio'):
        raise StoreError('MCP 传输类型无效', 400)
    value['transport_type'] = transport
    if not isinstance(value.get('enabled'), bool):
        raise StoreError('MCP enabled 必须为布尔值', 400)
    submitted_advanced = body.get('advanced_config')
    if submitted_advanced is not None and (not isinstance(submitted_advanced, dict) or set(submitted_advanced) - {'timeout'}):
        raise StoreError('MCP 高级配置仅支持 timeout', 400)
    advanced = submitted_advanced if submitted_advanced is not None else value.get('advanced_config', {})
    if not isinstance(advanced, dict):
        raise StoreError('MCP 高级配置必须为对象', 400)
    timeout = advanced.get('timeout', 30)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 1 <= timeout <= 300:
        raise StoreError('MCP timeout 必须为 1 至 300 秒', 400)
    value['advanced_config'] = {'timeout': timeout}
    if transport != 'stdio' and not _http_url(value.get('url', '')):
        raise StoreError('请提供 MCP 服务地址', 400)
    if transport == 'stdio':
        stdio = value.get('stdio_config', {})
        if stdio.get('command') not in ('npx', 'uvx') or not isinstance(stdio.get('args'), list) or any(not isinstance(x, str) for x in stdio['args']):
            raise StoreError('stdio 服务仅支持 npx/uvx 及字符串参数列表', 400)
    auth = copy.deepcopy(body.get('auth_config', {}))
    if not isinstance(auth, dict):
        raise StoreError('MCP 鉴权配置无效', 400)
    for key in ('api_key', 'token', 'client_secret', 'custom_headers'):
        if key in auth:
            if key == 'custom_headers':
                if not isinstance(auth[key], dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in auth[key].items()):
                    raise StoreError('MCP 请求头必须为字符串映射', 400)
            elif not isinstance(auth[key], str):
                raise StoreError('MCP 凭据必须为字符串', 400)
            submitted = auth.pop(key)
            private[key] = _masked_map(submitted, private.get(key, {})) if key == 'custom_headers' else submitted
    for key in ('headers', 'env_vars'):
        if key in body:
            if not isinstance(body[key], dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in body[key].items()):
                raise StoreError('请求头及环境变量必须为字符串映射', 400)
            private[key] = _masked_map(body[key], private.get(key, {}))
    value['auth_config'] = {**value.get('auth_config', {}), **auth}
    mcp_auth.validate_oauth_config(value['auth_config'], transport)
    value = with_secrets(value, private)
    if service_id and mcp_auth.fingerprint(value) != previous_fingerprint:
        mcp_auth.delete_service_state(owner_id, service_id)
    return save_record('mcp', value, owner_id)


def mcp_connection(value):
    transport = value['transport_type']
    if transport == 'stdio':
        raise StoreError('当前 Agent 仅支持远程 MCP；禁止在宿主机启动 stdio 服务', 501)
    private = secrets(value)
    headers = {**private.get('headers', {}), **private.get('custom_headers', {})}
    auth = value.get('auth_config', {})
    if auth.get('auth_type') == 'api_key' and private.get('api_key'):
        headers[auth.get('api_key_header') or 'X-API-Key'] = private['api_key']
    if auth.get('auth_type') == 'bearer' and private.get('token'):
        headers['Authorization'] = 'Bearer ' + private['token']
    return {'transport': 'streamable_http' if transport == 'http-streamable' else 'sse', 'url': value['url'], 'headers': headers,
            'timeout': (value.get('advanced_config') or {}).get('timeout', 30)}


def mcp_tool_policy(value, name, read_only):
    settings = value.get('tool_approvals', {}).get(name, {})
    return {'enabled': read_only is True and settings.get('enabled', True),
            'require_approval': read_only is True and settings.get('require_approval', False)}


async def mcp_tools(owner_id, config):
    from langchain_mcp_adapters.client import MultiServerMCPClient
    mode = config.get('mcp_selection_mode', 'none')
    if mode == 'none':
        return []
    selected = set(config.get('mcp_services') or [])
    values = [item for item in await asyncio.to_thread(records, 'mcp', owner_id) if item.get('enabled') and
              (mode == 'all' or item['id'] in selected)]
    if mode == 'selected' and selected - {item['id'] for item in values}:
        raise StoreError('所选 MCP 服务不存在、已停用或无权访问', 403)
    if any(value['transport_type'] == 'stdio' for value in values):
        raise StoreError('当前 Agent 仅支持远程 MCP；禁止在宿主机启动 stdio 服务', 501)
    result = []
    for value in values:
        readonly = set()
        async def authorize(request, handler, snapshot=value, readonly_names=readonly):
            current = await asyncio.to_thread(record, 'mcp', snapshot['id'], owner_id)
            if not current.get('enabled') or current.get('_encrypted') != snapshot.get('_encrypted') or current.get('tool_approvals') != snapshot.get('tool_approvals'):
                raise StoreError('MCP 服务凭据或工具配置已变化，请重新执行', 403)
            with connection() as conn:
                member = conn.execute('SELECT role,active FROM workspace_users WHERE id=%s', (owner_id,)).fetchone()
            if not member or not member['active']:
                raise StoreError('账号已停用', 403)
            if member['role'] == 'viewer' and request.name not in readonly_names:
                raise StoreError('当前账号没有该工具的写入权限', 403)
            return await handler(request)
        # Service IDs isolate same-named tools without changing each server's input schema.
        from agent import mcp_auth
        if value.get('auth_config', {}).get('auth_type') == 'oauth':
            tools = await mcp_auth.make_oauth_tools(owner_id, value, tool_interceptors=[authorize])
        else:
            client = MultiServerMCPClient({value['id']: mcp_auth.mcp_connection(value, owner_id)}, tool_name_prefix=True, tool_interceptors=[authorize])
            tools = await client.get_tools()
        for candidate in tools:
            original = candidate.name.removeprefix(value['id'] + '_')
            policy = mcp_tool_policy(value, original, (candidate.metadata or {}).get('readOnlyHint'))
            if policy['enabled']:
                if (candidate.metadata or {}).get('readOnlyHint') is True:
                    readonly.update((original, candidate.name))
                candidate.metadata = {**(candidate.metadata or {}), 'service_id': value['id'],
                    'require_approval': policy['require_approval']}
                if value.get('usage_instructions', '').strip():
                    candidate.description = f"{value['name']} usage: {value['usage_instructions'][:500]}\n\n{candidate.description}"
                result.append(candidate)
    return result


def skill_targets(value):
    return value.get('targets', ['state-backend'])


def skill_enabled(value, target):
    return target in skill_targets(value) and value.get('target_enabled', {}).get(target, value.get('enabled', True))


def save_skill(name, files, owner_id, skill_id=None):
    if not isinstance(name, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,100}', name):
        raise StoreError('Skill 名称只能含字母、数字、点、下划线和连字符', 400)
    if not isinstance(files, dict) or 'SKILL.md' not in files or len(files) > 100:
        raise StoreError('Skill 必须包含 SKILL.md，且最多100个文件', 400)
    for path, content in files.items():
        if not isinstance(path, str) or path.startswith('/') or '..' in path.split('/') or not isinstance(content, str):
            raise StoreError('Skill 文件路径或内容无效', 400)
    if sum(len(value.encode()) for value in files.values()) > 2 * 1024 * 1024:
        raise StoreError('Skill 文本总量不得超过2MB', 400)
    description = ''
    match = re.search(r'^description:\s*(.+)$', files['SKILL.md'], re.M)
    if match:
        description = match[1].strip().strip('"\'')
    if skill_id:
        record('skill', skill_id, owner_id)
    elif any(item['name'] == name for item in records('skill', owner_id)):
        raise StoreError('Skill 名称已存在', 409)
    return save_record('skill', {'id': skill_id or str(uuid.uuid4()), 'name': name, 'description': description, 'files': files,
        'enabled': True, 'targets': ['state-backend']}, owner_id)
