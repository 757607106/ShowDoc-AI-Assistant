"""Platform storage/browser handoff for the official MCP OAuthClientProvider.

Discovery, DCR, PKCE, issuer/state validation and refresh remain in mcp==1.30.0.
Only owner-scoped encrypted persistence and the existing UI handoff live here.
"""
import asyncio
import copy
import hashlib
import json
import secrets
import threading
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

import httpx
from langchain_core.tools import StructuredTool
from langgraph.func import task
from langgraph.runtime import get_runtime
from langgraph.types import Interrupt, interrupt
from mcp.client.auth import OAuthClientProvider
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthMetadata, OAuthToken, ProtectedResourceMetadata
from mcp.shared._httpx_utils import create_mcp_http_client
from psycopg.types.json import Jsonb

from agent import registry
from governance.database import connection as database
from governance.store import StoreError

CALLBACK_PATH = '/api/v1/mcp-oauth/callback'
TTL = 300
_workers = threading.BoundedSemaphore(8)


class OAuthRequired(StoreError):
    def __init__(self, service_id):
        super().__init__('MCP 服务需要当前用户授权', 401)
        self.service_id = service_id


def fingerprint(value):
    fields = {key: value.get(key) for key in ('transport_type', 'url', 'auth_config', 'stdio_config')}
    fields['credentials'] = registry.secrets(value)
    return hashlib.sha256(json.dumps(fields, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate_oauth_config(auth, transport):
    if auth.get('auth_type') != 'oauth':
        return
    if transport == 'stdio':
        raise StoreError('OAuth 仅适用于 HTTP/SSE MCP 服务', 400)
    scopes = auth.get('scopes', [])
    if not isinstance(scopes, list) or len(scopes) > 100 or any(not isinstance(scope, str) or not scope or len(scope) > 300 for scope in scopes):
        raise StoreError('OAuth scopes 须为字符串列表', 400)
    if not isinstance(auth.get('client_id', ''), str):
        raise StoreError('OAuth client_id 须为字符串', 400)
    override = auth.get('auth_server_metadata_url')
    if override and not registry._http_url(override):
        raise StoreError('OAuth 元数据地址无效', 400)


def _record(kind, key, owner):
    try:
        return registry.record(kind, key, owner)
    except StoreError as exc:
        if exc.status != 404:
            raise
        return None


def _state(owner, value):
    stored = _record('mcp-oauth', value['id'], owner)
    if stored and stored.get('fingerprint') == fingerprint(value):
        return stored
    return {'id': value['id'], 'generation': str(uuid.uuid4()), 'fingerprint': fingerprint(value)}


def status(owner, value, attempt_id=None):
    if attempt_id:
        attempt = _record('mcp-oauth-attempt', attempt_id, owner)
        if not attempt or attempt.get('service_id') != value['id'] or attempt.get('fingerprint') != fingerprint(value):
            raise StoreError('授权尝试不存在', 404)
        ready = attempt.get('status') == 'authorized' and attempt['expires'] > time.time()
        return {'authorized': ready, 'state': 'authorized' if ready else 'reauth_required' if attempt.get('status') == 'failed' or attempt['expires'] <= time.time() else 'pending', 'refresh_available': False}
    state = _state(owner, value)
    private = registry.secrets(state)
    token = private.get('tokens') or {}
    expires = state.get('expires_at')
    ready = bool(token.get('access_token') and (expires is None or expires > time.time()))
    refresh = bool(token.get('refresh_token'))
    return {'authorized': ready, 'state': 'authorized' if ready else 'refreshable' if refresh else 'reauth_required',
        'refresh_available': refresh, **({'expires_at': datetime.fromtimestamp(expires, timezone.utc).isoformat()} if expires is not None else {})}


class TokenStorage:
    def __init__(self, owner, value, redirect_uri, *, fresh=False):
        self.owner, self.value, self.redirect_uri, self.fresh = owner, copy.deepcopy(value), redirect_uri, fresh
        with database() as conn:
            conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (f'mcp-oauth:{owner}:{value["id"]}',))
            row = conn.execute("SELECT payload FROM runtime_records WHERE owner_id=%s AND kind='mcp-oauth' AND record_key=%s FOR UPDATE", (owner, value['id'])).fetchone()
            state = row['payload'] if row and row['payload'].get('fingerprint') == fingerprint(value) else _state(owner, value)
            if not row or row['payload'].get('fingerprint') != fingerprint(value):
                conn.execute("""INSERT INTO runtime_records(id,owner_id,kind,record_key,name,payload,metadata)
                    VALUES (%s,%s,'mcp-oauth',%s,%s,%s,'{}') ON CONFLICT (owner_id,kind,record_key) DO UPDATE SET payload=excluded.payload""",
                    (str(uuid.uuid4()), owner, value['id'], value['name'], Jsonb(state)))
        self.generation = state['generation']
        self.provider = None
        self.seen_access_token = (registry.secrets(state).get('tokens') or {}).get('access_token')

    def valid(self):
        current = registry.record('mcp', self.value['id'], self.owner)
        state = _record('mcp-oauth', self.value['id'], self.owner)
        with database() as conn:
            member = conn.execute('SELECT active FROM workspace_users WHERE id=%s', (self.owner,)).fetchone()
        if not member or not member['active'] or fingerprint(current) != fingerprint(self.value) or not state or state.get('generation') != self.generation:
            raise OAuthRequired(self.value['id'])
        return state

    def save(self, state, private):
        previous_encrypted = state.get('_encrypted')
        payload = registry.with_secrets(state, private)
        with database() as conn:
            row = conn.execute("""UPDATE runtime_records SET payload=%s,updated_at=now()
                WHERE owner_id=%s AND kind='mcp-oauth' AND record_key=%s AND payload->>'generation'=%s
                AND payload->>'_encrypted' IS NOT DISTINCT FROM %s RETURNING id""",
                (Jsonb(payload), self.owner, self.value['id'], self.generation, previous_encrypted)).fetchone()
        if not row:
            raise OAuthRequired(self.value['id'])

    def clear_tokens(self):
        state = self.valid()
        private = registry.secrets(state)
        if (private.get('tokens') or {}).get('access_token') != self.seen_access_token:
            return
        private.pop('tokens', None)
        state.pop('expires_at', None)
        self.save(state, private)

    async def get_tokens(self):
        state = await asyncio.to_thread(self.valid)
        token = registry.secrets(state).get('tokens')
        self.seen_access_token = (token or {}).get('access_token')
        return OAuthToken.model_validate(token) if token and not self.fresh else None

    async def set_tokens(self, tokens):
        state = await asyncio.to_thread(self.valid)
        private = registry.secrets(state)
        if not tokens.refresh_token and private.get('tokens', {}).get('refresh_token'):
            tokens = tokens.model_copy(update={'refresh_token': private['tokens']['refresh_token']})
        private['tokens'] = tokens.model_dump(mode='json')
        state['expires_at'] = time.time() + tokens.expires_in if tokens.expires_in is not None else None
        if self.provider:
            for key in ('oauth_metadata', 'protected_resource_metadata'):
                model = getattr(self.provider.context, key)
                if model:
                    private[key] = model.model_dump(mode='json')
        await asyncio.to_thread(self.save, state, private)
        self.seen_access_token = tokens.access_token
        self.fresh = False

    async def get_client_info(self):
        state = await asyncio.to_thread(self.valid)
        private = registry.secrets(state)
        saved = private.get('client_info')
        if saved:
            client = OAuthClientInformationFull.model_validate(saved)
            if client.client_secret_expires_at and client.client_secret_expires_at <= time.time():
                return None
            return client
        auth = self.value.get('auth_config') or {}
        if auth.get('client_id'):
            secret = registry.secrets(self.value).get('client_secret')
            return OAuthClientInformationFull(client_id=auth['client_id'], client_secret=secret,
                redirect_uris=[self.redirect_uri], token_endpoint_auth_method='client_secret_post' if secret else 'none')
        return None

    async def set_client_info(self, client_info):
        state = await asyncio.to_thread(self.valid)
        private = registry.secrets(state)
        private['client_info'] = client_info.model_dump(mode='json')
        await asyncio.to_thread(self.save, state, private)


class GuardedAuth(httpx.Auth):
    requires_response_body = True

    def __init__(self, provider, storage):
        self.provider, self.storage = provider, storage

    async def async_auth_flow(self, request):
        await asyncio.to_thread(self.storage.valid)
        flow = self.provider.async_auth_flow(request)
        try:
            outgoing = await anext(flow)
            while True:
                response = yield outgoing
                outgoing = await flow.asend(response)
        except StopAsyncIteration:
            return
        finally:
            await flow.aclose()


class ConfiguredOAuthProvider(OAuthClientProvider):
    async def _perform_authorization_code_grant(self):
        # SDK 1.30 selects discovered scopes before authorization. Honor an explicit
        # user selection; all PKCE/state/redirect/token protocol remains upstream.
        if self.requested_scope:
            self.context.client_metadata.scope = self.requested_scope
        return await super()._perform_authorization_code_grant()


def provider(owner, value, *, redirect_uri=None, redirect_handler=None, callback_handler=None, fresh=False):
    validate_oauth_config(value.get('auth_config', {}), value['transport_type'])
    state = _state(owner, value)
    private = registry.secrets(state)
    redirect_uri = redirect_uri or state.get('redirect_uri') or 'http://127.0.0.1' + CALLBACK_PATH
    storage = TokenStorage(owner, value, redirect_uri, fresh=fresh)
    async def required(_url):
        await asyncio.to_thread(storage.clear_tokens)
        raise OAuthRequired(value['id'])
    result = ConfiguredOAuthProvider(server_url=value['url'],
        client_metadata=OAuthClientMetadata(redirect_uris=[redirect_uri], client_name='WeKnora',
            grant_types=['authorization_code', 'refresh_token'], response_types=['code'],
            scope=' '.join(value.get('auth_config', {}).get('scopes', [])) or None),
        storage=storage, redirect_handler=redirect_handler or required, callback_handler=callback_handler, timeout=TTL)
    result.requested_scope = ' '.join(value.get('auth_config', {}).get('scopes', []))
    storage.provider = result
    if not fresh:
        result.context.token_expiry_time = state.get('expires_at')
        for key, model in (('oauth_metadata', OAuthMetadata), ('protected_resource_metadata', ProtectedResourceMetadata)):
            if private.get(key):
                setattr(result.context, key, model.model_validate(private[key]))
    return GuardedAuth(result, storage)


def mcp_connection(value, owner, auth=None):
    config = registry.mcp_connection(value)
    if value.get('auth_config', {}).get('auth_type') == 'oauth':
        config['auth'] = auth or provider(owner, value)
        override = value.get('auth_config', {}).get('auth_server_metadata_url')
        if override:
            async def metadata_request(request):
                if request.method == 'GET' and any(path in request.url.path for path in
                    ('/.well-known/oauth-authorization-server', '/.well-known/openid-configuration')):
                    request.url = httpx.URL(override)
                    request.headers['Host'] = request.url.netloc.decode()
            def factory(**kwargs):
                client = create_mcp_http_client(**kwargs)
                client.event_hooks['request'].append(metadata_request)
                return client
            config['httpx_client_factory'] = factory
    return config


def revoke(owner, value):
    state = {'id': value['id'], 'fingerprint': fingerprint(value), 'generation': str(uuid.uuid4())}
    registry.save_record('mcp-oauth', state, owner)


def delete_service_state(owner, service_id):
    """Called on connection changes/deletion; unrelated display edits preserve consent."""
    with database() as conn:
        conn.execute("""DELETE FROM runtime_records WHERE owner_id=%s AND
            ((kind IN ('mcp-oauth','mcp-metadata') AND record_key=%s)
             OR (kind='mcp-oauth-attempt' AND payload->>'service_id'=%s))""", (owner, service_id, service_id))


def _attempt(owner, identifier, **patch):
    value = _record('mcp-oauth-attempt', identifier, owner)
    if value is None:
        return None
    value.update(patch)
    registry.save_record('mcp-oauth-attempt', value, owner)
    return value


def start_authorization(owner, value, redirect_uri, frontend_redirect='/'):
    if not _workers.acquire(blocking=False):
        raise StoreError('授权请求较多，请稍后重试', 503)
    try:
        identifier = str(uuid.uuid4())
        with database() as conn:
            conn.execute("DELETE FROM runtime_records WHERE kind='mcp-oauth-attempt' AND (payload->>'expires')::double precision<%s", (time.time() - 86400,))
        attempt = {'id': identifier, 'service_id': value['id'], 'fingerprint': fingerprint(value), 'status': 'pending',
            'expires': time.time() + TTL, 'frontend_redirect': frontend_redirect}
        registry.save_record('mcp-oauth-attempt', attempt, owner)
        storage = TokenStorage(owner, value, redirect_uri)
        with database() as conn:
            conn.execute("""UPDATE runtime_records SET payload=payload || %s WHERE owner_id=%s
                AND kind='mcp-oauth' AND record_key=%s AND payload->>'generation'=%s""",
                (Jsonb({'redirect_uri': redirect_uri}), owner, value['id'], storage.generation))
    except BaseException:
        _workers.release()
        raise
    ready = threading.Event()
    async def redirect(url):
        nonce = parse_qs(urlsplit(url).query).get('state', [''])[0]
        _attempt(owner, identifier, authorization_url=url, state_hash=hashlib.sha256(nonce.encode()).hexdigest())
        ready.set()
    async def callback():
        while time.time() < attempt['expires']:
            current = await asyncio.to_thread(registry.record, 'mcp-oauth-attempt', identifier, owner)
            if current.get('status') in ('failed', 'cancelled'):
                raise StoreError('授权已取消或失败', 400)
            private = registry.secrets(current)
            if private.get('code'):
                return private['code'], private['state']
            await asyncio.sleep(0.2)
        raise TimeoutError('OAuth authorization expired')
    async def run():
        from langchain_mcp_adapters.sessions import create_session
        auth = provider(owner, value, redirect_uri=redirect_uri, redirect_handler=redirect, callback_handler=callback, fresh=True)
        async with asyncio.timeout(TTL):
            async with create_session(mcp_connection(value, owner, auth)) as session:
                await session.initialize()
        _attempt(owner, identifier, status='authorized', _encrypted=None)
    def worker():
        try:
            asyncio.run(run())
        except Exception:
            _attempt(owner, identifier, status='failed', _encrypted=None)
        finally:
            ready.set()
            _workers.release()
    threading.Thread(target=worker, name='mcp-oauth', daemon=True).start()
    if not ready.wait(15):
        raise StoreError('授权发现超时，请稍后重试', 504)
    result = registry.record('mcp-oauth-attempt', identifier, owner)
    if not result.get('authorization_url'):
        raise StoreError('无法发现 MCP OAuth 授权服务，请检查连接配置', 502)
    return {'authorization_url': result['authorization_url'], 'authorization_attempt': identifier}


def complete_callback(state, code, error=None):
    if not isinstance(state, str) or not state or len(state) > 512 or not isinstance(code, str) or len(code) > 8192:
        raise StoreError('授权回调无效', 400)
    digest = hashlib.sha256(state.encode()).hexdigest()
    with database() as conn:
        row = conn.execute("SELECT owner_id,payload FROM runtime_records WHERE kind='mcp-oauth-attempt' AND payload->>'state_hash'=%s FOR UPDATE", (digest,)).fetchone()
        if not row or row['payload']['expires'] <= time.time() or row['payload'].get('status') != 'pending' or row['payload'].get('callback_received'):
            raise StoreError('授权回调已失效', 400)
        attempt = row['payload']
        attempt.update(callback_received=True, status='failed' if error or not code else 'pending')
        registry.with_secrets(attempt, {'code': code, 'state': state})
        conn.execute("UPDATE runtime_records SET payload=%s WHERE owner_id=%s AND kind='mcp-oauth-attempt' AND record_key=%s",
                     (Jsonb(attempt), row['owner_id'], attempt['id']))
    return attempt.get('frontend_redirect') or '/', row['owner_id'], attempt['id']


def oauth_required(exc):
    if isinstance(exc, OAuthRequired):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        challenge = exc.response.headers.get('www-authenticate', '')
        if exc.response.status_code in (401, 403) and ('resource_metadata=' in challenge or 'insufficient_scope' in challenge):
            return True
    return any(oauth_required(child) for child in getattr(exc, 'exceptions', []))


def oauth_interrupt(owner, value, tool_name=None):
    response = interrupt({'kind': 'mcp_oauth', 'request': {'service_id': value['id'],
        'service_name': value['name'], 'mcp_tool_name': tool_name or '', 'timeout_seconds': TTL}})
    if not response or response.get('decision') == 'cancel' or response.get('authorized') is False:
        return False
    if status(owner, registry.record('mcp', value['id'], owner))['state'] not in ('authorized', 'refreshable'):
        raise OAuthRequired(value['id'])
    return True


async def make_oauth_tools(owner, value, tool_interceptors=()):
    """Expose native schemas; invoke through fresh official adapters after consent."""
    from langchain_mcp_adapters.client import MultiServerMCPClient
    snapshot = _record('mcp-metadata', value['id'], owner)
    specs = (snapshot or {}).get('snapshot', {}).get('tools', []) if snapshot and snapshot.get('fingerprint') == fingerprint(value) else []
    if not specs and status(owner, value)['state'] in ('authorized', 'refreshable'):
        client = MultiServerMCPClient({value['id']: mcp_connection(value, owner)})
        try:
            discovered = await client.get_tools()
            specs = [{'name': tool.name, 'description': tool.description, 'inputSchema': tool.args_schema,
                      **(tool.metadata or {})} for tool in discovered]
        except Exception as exc:
            if not oauth_required(exc):
                raise
    authorization_name = '__platform_authorize'
    specs = [*specs, {'name': authorization_name, 'description': 'Authorize this selected MCP service. '
        'This platform helper opens user consent; it does not execute an upstream action.',
        'inputSchema': {'type': 'object', 'properties': {}, 'additionalProperties': False}, 'readOnlyHint': True}]
    @task
    async def call_authorized(spec_name, arguments, *, wait_for_decision=False):
        # Keep the pause decision stable when a token appears before the tool resumes.
        if wait_for_decision or status(owner, value)['state'] not in ('authorized', 'refreshable'):
            return None
        try:
            client = MultiServerMCPClient({value['id']: mcp_connection(value, owner)},
                tool_name_prefix=True, tool_interceptors=list(tool_interceptors))
            actual = await client.get_tools()
            if spec_name == authorization_name:
                return 'Authorized. Available tools: ' + ', '.join(tool.name for tool in actual), None
            candidate = next((tool for tool in actual if tool.name == value['id'] + '_' + spec_name), None)
            if candidate is None:
                raise StoreError('MCP 工具目录已变化，请刷新元数据', 409)
            if (candidate.metadata or {}).get('readOnlyHint') is not True:
                raise StoreError('当前 MCP 工具未声明只读，请刷新工具目录', 403)
            result = await candidate.ainvoke({'name': candidate.name, 'args': arguments,
                                             'id': uuid.uuid4().hex, 'type': 'tool_call'})
            return result.content, result.artifact
        except Exception as exc:
            if not oauth_required(exc):
                raise
            return None

    def make_call(spec_name):
        async def call(**arguments):
            runtime = get_runtime()
            pending = (runtime.context or {}).get('pending_oauth', ())
            # Older interrupted calls lack the persisted result of the first task.
            wait_for_decision = bool(pending) and Interrupt.from_ns(None, runtime.execution_info.checkpoint_ns).id in pending
            result = await call_authorized(spec_name, arguments, wait_for_decision=wait_for_decision)
            if result is not None:
                return result
            if not oauth_interrupt(owner, value, spec_name):
                return 'The user skipped this MCP authorization. No upstream tool was executed.', None
            result = await call_authorized(spec_name, arguments)
            if result is None:
                raise OAuthRequired(value['id'])
            return result
        return call
    return [StructuredTool(name=value['id'] + '_' + spec['name'], description=spec.get('description') or spec['name'],
        args_schema=spec['inputSchema'], coroutine=make_call(spec['name']), response_format='content_and_artifact',
        metadata={'readOnlyHint': spec.get('readOnlyHint', False), 'mcp_service_id': value['id']}) for spec in specs]
