"""Original MCP metadata, usage and OAuth UI contracts over the official SDK."""
import asyncio
import json
from pathlib import Path
import time
from urllib.parse import urlsplit

from flask import Blueprint, g, jsonify, redirect, request
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.sessions import create_session

from agent import mcp_auth, registry
from governance.store import StoreError, now
from webapi.auth import user_id

mcp_runtime_bp = Blueprint('mcp_runtime', __name__)


def _service(identifier):
    value = registry.record('mcp', identifier, user_id())
    if value['transport_type'] == 'stdio' and g.user['role'] != 'admin':
        raise StoreError('stdio MCP 仅限管理员配置和执行', 403)
    return value


def metadata_for(owner, value):
    cached = mcp_auth._record('mcp-metadata', value['id'], owner)
    if not cached:
        return None
    result = dict(cached['snapshot'])
    result['stale'] = cached['fingerprint'] != mcp_auth.fingerprint(value)
    result['tools'] = [{**tool, **registry.mcp_tool_policy(value, tool['name'], tool.get('readOnlyHint'))}
                       for tool in result['tools']]
    return result


async def discover_metadata(owner, value):
    async with asyncio.timeout(60):
        async with create_session(mcp_auth.mcp_connection(value, owner)) as session:
            initialized = await session.initialize()
            tools, cursor, seen = [], None, set()
            if initialized.capabilities.tools:
                while True:
                    result = await session.list_tools(cursor=cursor)
                    for tool in result.tools:
                        if not tool.name or tool.name in seen:
                            raise StoreError('MCP 工具目录存在空名称或重复名称', 502)
                        seen.add(tool.name)
                        readonly = bool(tool.annotations and tool.annotations.readOnlyHint is True)
                        tools.append({'name': tool.name, 'description': tool.description or '', 'inputSchema': tool.inputSchema,
                            'readOnlyHint': readonly, 'enabled': True, 'require_approval': not readonly})
                    if not result.nextCursor:
                        break
                    if result.nextCursor == cursor or len(tools) > 10000:
                        raise StoreError('MCP 工具目录分页无效或过大', 502)
                    cursor = result.nextCursor
            snapshot = {'service_id': value['id'], 'tools': tools, 'instructions': initialized.instructions or '',
                'server_name': initialized.serverInfo.name, 'server_version': initialized.serverInfo.version,
                'server_description': getattr(initialized.serverInfo, 'description', None) or '', 'synced_at': now(), 'stale': False}
            if len(json.dumps(snapshot, ensure_ascii=False).encode()) > 8 * 1024 * 1024:
                raise StoreError('MCP 工具目录超出 8 MiB 限制', 502)
    current = await asyncio.to_thread(registry.record, 'mcp', value['id'], owner)
    if mcp_auth.fingerprint(current) != mcp_auth.fingerprint(value):
        raise StoreError('连接配置已变化，请重新刷新工具目录', 409)
    await asyncio.to_thread(registry.save_record, 'mcp-metadata', {'id': value['id'], 'fingerprint': mcp_auth.fingerprint(value), 'snapshot': snapshot}, owner)
    return metadata_for(owner, current)


@mcp_runtime_bp.get('/api/v1/mcp-services/<service_id>/metadata')
def metadata(service_id):
    value = metadata_for(user_id(), _service(service_id))
    return jsonify(success=True, synced=value is not None, data=value)


@mcp_runtime_bp.post('/api/v1/mcp-services/<service_id>/metadata/refresh')
def refresh_metadata(service_id):
    value = _service(service_id)
    try:
        result = asyncio.run(discover_metadata(user_id(), value))
    except Exception as exc:
        if mcp_auth.oauth_required(exc):
            return jsonify(success=False, oauth_required=True, message='请先授权当前 MCP 服务'), 401
        if isinstance(exc, StoreError):
            raise
        raise StoreError(f'MCP 目录同步失败（{type(exc).__name__}）', 502) from exc
    return jsonify(success=True, synced=True, data=result)


@mcp_runtime_bp.post('/api/v1/mcp-services/<service_id>/usage-instructions/generate')
def generate_usage(service_id):
    value = _service(service_id)
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise StoreError('生成请求必须是 JSON 对象', 400)
    snapshot = metadata_for(user_id(), value)
    if not snapshot or snapshot['stale']:
        raise StoreError('请先同步 MCP 工具目录', 400)
    tools, omitted, budget = [], 0, 24000
    for tool in snapshot['tools']:
        if not tool.get('enabled', True):
            continue
        item = {'name': tool['name'][:256], 'description': tool.get('description', '')[:2000]}
        size = len(item['name']) + len(item['description'])
        if len(tools) >= 100 or size > budget:
            omitted += 1
            continue
        tools.append(item)
        budget -= size
    if not tools:
        raise StoreError('没有可用的 MCP 工具，无法生成用法', 400)
    prompt = Path(__file__).resolve().parents[1].joinpath('agent/mcp_usage_prompt.txt').read_text()
    language = {'zh-CN': 'Simplified Chinese', 'zh-TW': 'Traditional Chinese', 'en-US': 'English', 'ja-JP': 'Japanese',
                'ko-KR': 'Korean', 'ru-RU': 'Russian'}.get(body.get('language'), 'Simplified Chinese')
    context = {'name': value['name'][:256], 'server_name': snapshot['server_name'][:256],
        'server_description': snapshot['server_description'][:2000], 'server_instructions': snapshot['instructions'][:4000],
        'tools': tools, 'omitted_tools': omitted}
    from agent.graph import build_model
    model_id = registry.default_model_id(user_id(), 'utility_model_id')
    try:
        model = build_model({'model_id': model_id, 'temperature': 0.2, 'max_completion_tokens': 512,
                             'llm_call_timeout': 60, 'thinking': False}, user_id())
        async def generate():
            async with asyncio.timeout(60):
                return await model.ainvoke([SystemMessage(prompt + '\nOutput language: ' + language + '.'),
                                           HumanMessage(json.dumps(context, ensure_ascii=False))])
        output = asyncio.run(generate())
        text = output.content.strip() if isinstance(output.content, str) else ''
        if not text or len(text) > 500 or output.response_metadata.get('finish_reason') == 'length':
            raise ValueError('Empty or excessive output')
    except Exception as exc:
        raise StoreError(f'MCP 用法生成失败，请检查已配置的对话模型（{type(exc).__name__}）', 503) from exc
    return jsonify(success=True, data={'usage_instructions': text})


@mcp_runtime_bp.post('/api/v1/mcp-services/<service_id>/oauth/authorize-url')
def authorize(service_id):
    value = _service(service_id)
    if value.get('auth_config', {}).get('auth_type') != 'oauth':
        raise StoreError('服务没有配置 OAuth', 400)
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or body.get('redirect_uri') != request.host_url.rstrip('/') + mcp_auth.CALLBACK_PATH:
        raise StoreError('OAuth redirect_uri 必须是本站回调地址', 400)
    target = body.get('frontend_redirect') or '/'
    if not isinstance(target, str) or not target.startswith('/') or target.startswith('//') or '\\' in target or any(ord(char) < 32 for char in target) or urlsplit(target).netloc:
        raise StoreError('OAuth 完成页面必须是本站路径', 400)
    return jsonify(success=True, data=mcp_auth.start_authorization(user_id(), value, body['redirect_uri'], target))


@mcp_runtime_bp.get('/api/v1/mcp-services/<service_id>/oauth/status')
def authorization_status(service_id):
    return jsonify(success=True, data=mcp_auth.status(user_id(), _service(service_id), request.args.get('authorization_attempt')))


@mcp_runtime_bp.delete('/api/v1/mcp-services/<service_id>/oauth/token')
def revoke_token(service_id):
    mcp_auth.revoke(user_id(), _service(service_id))
    return jsonify(success=True)


@mcp_runtime_bp.get(mcp_auth.CALLBACK_PATH)
def callback():
    target, owner, identifier = mcp_auth.complete_callback(request.args.get('state', ''), request.args.get('code', ''), request.args.get('error'))
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        attempt = registry.record('mcp-oauth-attempt', identifier, owner)
        if attempt['status'] != 'pending':
            key = 'mcp_oauth_result=success' if attempt['status'] == 'authorized' else 'mcp_oauth_error=authorization_failed'
            response = redirect(target.split('#', 1)[0] + '#' + key)
            response.headers.update({'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'})
            return response
        time.sleep(0.05)
    return 'Authorization is processing. Return to the original window to check the result.', 202, {'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'}
