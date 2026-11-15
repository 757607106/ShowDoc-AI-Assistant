"""Owner-scoped model, MCP and Skill configuration in existing runtime records."""
import asyncio
import copy
import json
import os
import re
import uuid
from urllib.parse import urlsplit

from psycopg.types.json import Jsonb

from governance.database import connection
from governance.store import StoreError

MASKED = '********'


def _masked_map(values, current):
    return {key: current[key] if value == MASKED and key in current else value for key, value in values.items()}


def _http_url(value):
    try:
        parsed = urlsplit(value)
        return parsed.scheme in ('http', 'https') and bool(parsed.hostname) and not parsed.username
    except (TypeError, ValueError):
        return False


def records(kind, owner_id):
    with connection() as conn:
        rows = conn.execute('SELECT payload FROM runtime_records WHERE owner_id=%s AND kind=%s ORDER BY created_at,id',
                            (owner_id, kind)).fetchall()
    return [row['payload'] for row in rows]


def record(kind, record_id, owner_id):
    with connection() as conn:
        row = conn.execute('SELECT payload FROM runtime_records WHERE owner_id=%s AND kind=%s AND record_key=%s',
                           (owner_id, kind, record_id)).fetchone()
    if row is None:
        raise StoreError('配置不存在或无权访问', 404)
    return row['payload']


def save_record(kind, value, owner_id):
    from governance.store import now
    value = copy.deepcopy(value)
    value.setdefault('id', str(uuid.uuid4()))
    value.setdefault('created_at', now())
    value['updated_at'] = now()
    metadata = {'type': kind, 'owner_id': owner_id}
    with connection() as conn:
        conn.execute('''INSERT INTO runtime_records(id,owner_id,kind,record_key,name,payload,metadata)
            VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (owner_id,kind,record_key)
            DO UPDATE SET payload=excluded.payload,name=excluded.name,updated_at=now()''',
            (str(uuid.uuid4()), owner_id, kind, value['id'], value.get('name', value['id']), Jsonb(value), Jsonb(metadata)))
    return value


def delete_record(kind, record_id, owner_id):
    record(kind, record_id, owner_id)
    with connection() as conn:
        conn.execute('DELETE FROM runtime_records WHERE owner_id=%s AND kind=%s AND record_key=%s',
                     (owner_id, kind, record_id))


def secrets(value):
    from webapi.auth import cipher
    encrypted = value.get('_encrypted')
    return json.loads(cipher().decrypt(encrypted.encode())) if encrypted else {}


def with_secrets(value, private):
    from webapi.auth import cipher
    value['_encrypted'] = cipher().encrypt(json.dumps(private).encode()).decode()
    return value


def public(value):
    value = copy.deepcopy(value)
    private = secrets(value)
    value.pop('_encrypted', None)
    if value.get('_kind') in ('model', 'mcp', 'web-search'):
        fields = ('api_key', 'app_secret') if value['_kind'] == 'model' else ('api_key', 'token', 'client_secret') if value['_kind'] == 'mcp' else ('api_key',)
        value['credentials'] = {key: {'configured': bool(private.get(key))} for key in fields}
    if value.get('_kind') == 'model' and private.get('custom_headers'):
        value.setdefault('parameters', {})['custom_headers'] = {key: MASKED for key in private['custom_headers']}
    if value.get('_kind') == 'model' and value.get('type') in ('KnowledgeQA', 'VLLM'):
        from agent.models import describe_model
        value = describe_model(value)
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


def environment_model():
    from agent.models import describe_model
    name = os.getenv('AGENT_MAIN_MODEL', 'qwen-max')
    value = {'id': 'agent-main', 'name': name, 'display_name': name, 'type': 'KnowledgeQA', 'source': 'remote',
             'is_default': True, 'is_builtin': True, 'parameters': {'model_name': name, 'provider': 'aliyun'}}
    return describe_model(value)


def models(owner_id):
    default_id = default_model_id(owner_id)
    values = [environment_model(), *[public(item) for item in records('model', owner_id)]]
    for value in values:
        value['is_default'] = value['id'] == default_id
    return values


def default_model_id(owner_id, field='chat_model_id'):
    value = next((item for item in records('settings', owner_id) if item['id'] == 'default-settings'), {})
    return value.get('value', {}).get(field) or 'agent-main'


def model_config(model_id, owner_id):
    if not model_id or model_id == 'agent-main':
        value = environment_model()
        bailian = os.getenv('BAILIAN_API_KEY', '').strip()
        value['parameters'].update(api_key=bailian or os.getenv('DASHSCOPE_API_KEY') or os.getenv('QWEN_API_KEY', ''),
            base_url=os.getenv('AGENT_BAILIAN_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1') if bailian else
            (os.getenv('DASHSCOPE_API_URL') or 'https://llm-rtc5v8cnt0umugh9.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions').rstrip('/').removesuffix('/chat/completions'))
        return value
    value = copy.deepcopy(record('model', model_id, owner_id))
    from agent.models import validate_model_runtime
    validate_model_runtime(value)
    value['parameters'].update(secrets(value))
    return value


def save_model(body, owner_id, model_id=None):
    value = copy.deepcopy(record('model', model_id, owner_id)) if model_id else {'_kind': 'model'}
    private = secrets(value)
    value.update({key: body[key] for key in ('name', 'display_name', 'type', 'source', 'description') if key in body})
    if not isinstance(value.get('name'), str) or not value['name'].strip():
        raise StoreError('请提供模型名称', 400)
    if value.get('type', 'KnowledgeQA') not in ('KnowledgeQA', 'VLLM', 'Embedding', 'Rerank', 'ASR'):
        raise StoreError('模型类型无效', 400)
    params = body.get('parameters', {})
    if not isinstance(params, dict):
        raise StoreError('模型参数必须为对象', 400)
    params = copy.deepcopy(params)
    for key in ('api_key', 'app_secret', 'custom_headers'):
        if key in params:
            if key == 'custom_headers':
                if not isinstance(params[key], dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in params[key].items()):
                    raise StoreError('自定义请求头必须为字符串映射', 400)
            elif not isinstance(params[key], str):
                raise StoreError('模型凭据必须为字符串', 400)
            submitted = params.pop(key)
            private[key] = _masked_map(submitted, private.get(key, {})) if key == 'custom_headers' else submitted
    value['parameters'] = {**value.get('parameters', {}), **params}
    value.setdefault('type', 'KnowledgeQA')
    value.setdefault('source', 'remote')
    from agent.models import validate_model_runtime
    validate_model_runtime(value)
    base_url = value['parameters'].get('base_url', '')
    if not isinstance(base_url, str) or not _http_url(base_url):
        raise StoreError('请提供有效的模型 API 地址', 400)
    return save_record('model', with_secrets(value, private), owner_id)


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
    private = secrets(value)
    transport = value['transport_type']
    if transport == 'stdio':
        return {'transport': 'stdio', **value['stdio_config'], 'env': private.get('env_vars', {})}
    headers = {**private.get('headers', {}), **private.get('custom_headers', {})}
    auth = value.get('auth_config', {})
    if auth.get('auth_type') == 'api_key' and private.get('api_key'):
        headers[auth.get('api_key_header') or 'X-API-Key'] = private['api_key']
    if auth.get('auth_type') == 'bearer' and private.get('token'):
        headers['Authorization'] = 'Bearer ' + private['token']
    return {'transport': 'streamable_http' if transport == 'http-streamable' else 'sse', 'url': value['url'], 'headers': headers}


async def mcp_tools(owner_id, config):
    from langchain_mcp_adapters.client import MultiServerMCPClient
    mode = config.get('mcp_selection_mode', 'none')
    if mode == 'none':
        return []
    selected = set(config.get('mcp_services') or [])
    values = [item for item in records('mcp', owner_id) if item.get('enabled') and
              mode != 'none' and (mode == 'all' or item['id'] in selected)]
    if mode == 'selected' and selected - {item['id'] for item in values}:
        raise StoreError('所选 MCP 服务不存在、已停用或无权访问', 403)
    result = []
    for value in values:
        if value['transport_type'] == 'stdio':
            with connection() as conn:
                member = conn.execute('SELECT role,active FROM platform_users WHERE id=%s', (owner_id,)).fetchone()
            if not member or not member['active'] or member['role'] != 'admin':
                raise StoreError('stdio MCP 会启动服务器进程，仅允许管理员配置和执行', 403)
        readonly = set()
        async def authorize(request, handler, snapshot=value, readonly_names=readonly):
            current = await asyncio.to_thread(record, 'mcp', snapshot['id'], owner_id)
            if not current.get('enabled') or current.get('_encrypted') != snapshot.get('_encrypted') or current.get('tool_approvals') != snapshot.get('tool_approvals'):
                raise StoreError('MCP 服务凭据或工具配置已变化，请重新执行', 403)
            with connection() as conn:
                member = conn.execute('SELECT role,active FROM platform_users WHERE id=%s', (owner_id,)).fetchone()
            if not member or not member['active']:
                raise StoreError('账号已停用', 403)
            if member['role'] == 'viewer' and request.name not in readonly_names:
                raise StoreError('当前账号没有该工具的写入权限', 403)
            if snapshot['transport_type'] == 'stdio' and member['role'] != 'admin':
                raise StoreError('当前账号没有 stdio MCP 执行权限', 403)
            return await handler(request)
        # Service IDs isolate same-named tools without changing each server's input schema.
        from agent import mcp_auth
        if value.get('auth_config', {}).get('auth_type') == 'oauth':
            tools = await mcp_auth.make_oauth_tools(owner_id, value, tool_interceptors=[authorize])
        else:
            client = MultiServerMCPClient({value['id']: mcp_auth.mcp_connection(value, owner_id)}, tool_name_prefix=True, tool_interceptors=[authorize])
            tools = await client.get_tools()
        flags = value.get('tool_approvals', {})
        for candidate in tools:
            original = candidate.name.removeprefix(value['id'] + '_')
            settings = flags.get(original, {})
            if settings.get('enabled', True):
                if (candidate.metadata or {}).get('readOnlyHint') is True:
                    readonly.update((original, candidate.name))
                candidate.metadata = {**(candidate.metadata or {}), 'service_id': value['id'],
                    'require_approval': settings.get('require_approval', (candidate.metadata or {}).get('readOnlyHint') is not True)}
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
