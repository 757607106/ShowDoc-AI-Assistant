"""Real MCP SDK + local FastMCP/OAuth endpoints; no cloud or browser automation."""
import asyncio
import base64
from contextlib import contextmanager
import hashlib
import json
import os
import socket
import threading
import time
from urllib.parse import parse_qs, urlsplit

from flask import Flask
import httpx
from langchain_core.messages import AIMessage
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
import pytest
from psycopg.types.json import Jsonb
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
import uvicorn

from agent import mcp_auth, registry
from governance.database import connection
from governance.store import StoreError
from tests.test_platform_harness import call, harness, original_prepare
from tests.test_platform_weknora_adapter import events
from webapi.auth import auth_bp, require_login
from webapi.mcp_runtime import mcp_runtime_bp
from webapi.model_runtime import model_runtime_bp


@contextmanager
def serve(app):
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    server = uvicorn.Server(uvicorn.Config(app, log_level='error', lifespan='on'))
    thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(.01)
    assert server.started
    try:
        yield 'http://127.0.0.1:' + str(listener.getsockname()[1])
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        listener.close()


@pytest.fixture
def runtime_client():
    app = Flask(__name__)
    app.secret_key = 'isolated-test-key'
    app.register_blueprint(auth_bp)
    app.register_blueprint(mcp_runtime_bp)
    app.register_blueprint(model_runtime_bp)
    app.before_request(lambda: None if __import__('flask').request.path == mcp_auth.CALLBACK_PATH else require_login())
    @app.errorhandler(StoreError)
    def error(exc):
        return {'success': False, 'message': str(exc)}, exc.status
    client = app.test_client()
    response = client.post('/api/v1/auth/login', json={'email': 'test@example.com', 'password': 'test-password-123'})
    client.environ_base['HTTP_AUTHORIZATION'] = 'Bearer ' + response.json['token']
    return client


@pytest.fixture
def native_mcp():
    state = {'base': '', 'protected': False, 'tokens': set(), 'calls': 0, 'registers': 0, 'exchanges': [], 'challenge': '', 'metadata_paths': []}
    mcp = FastMCP('Native fixture', instructions='Read fixture data.', json_response=True, stateless_http=True)
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def read_fixture(query: str) -> str:
        state['calls'] += 1
        return 'fixture:' + query
    state['read_tool'] = mcp._tool_manager.get_tool('read_fixture')
    native = mcp.streamable_http_app()
    class Auth(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if request.url.path == '/mcp' and state['protected'] and request.headers.get('authorization', '').removeprefix('Bearer ') not in state['tokens']:
                return JSONResponse({'error': 'unauthorized'}, status_code=401,
                    headers={'WWW-Authenticate': 'Bearer resource_metadata="' + state['base'] + '/prm"'})
            return await call_next(request)
    async def resource(request):
        return JSONResponse({'resource': state['base'] + '/mcp', 'authorization_servers': [state['base']], 'scopes_supported': ['read', 'write']})
    async def metadata(request):
        state['metadata_paths'].append(request.url.path)
        return JSONResponse({'issuer': state.get('issuer', state['base']), 'authorization_endpoint': state['base'] + '/authorize',
            'token_endpoint': state['base'] + '/token', 'registration_endpoint': state['base'] + '/register',
            'response_types_supported': ['code'], 'grant_types_supported': ['authorization_code', 'refresh_token'],
            'token_endpoint_auth_methods_supported': ['none'], 'code_challenge_methods_supported': ['S256'], 'scopes_supported': ['read', 'write']})
    async def register(request):
        body = await request.json()
        state['registers'] += 1
        return JSONResponse({**body, 'client_id': 'native-fixture-client', 'token_endpoint_auth_method': 'none'}, status_code=201)
    async def token(request):
        body = {key: values[0] for key, values in parse_qs((await request.body()).decode()).items()}
        state['exchanges'].append(body)
        if body['grant_type'] == 'authorization_code':
            actual = base64.urlsafe_b64encode(hashlib.sha256(body['code_verifier'].encode()).digest()).decode().rstrip('=')
            if body.get('code') != 'fixture-code' or actual != state['challenge']:
                return JSONResponse({'error': 'invalid_grant'}, status_code=400)
        elif body.get('refresh_token') != 'fixture-refresh':
            return JSONResponse({'error': 'invalid_grant'}, status_code=400)
        access = 'fixture-access-' + str(len(state['exchanges']))
        state['tokens'].add(access)
        return JSONResponse({'access_token': access, 'refresh_token': 'fixture-refresh', 'token_type': 'Bearer', 'expires_in': 60, 'scope': 'read'})
    app = Starlette(routes=[Route('/prm', resource), Route('/.well-known/oauth-authorization-server', metadata), Route('/explicit-issuer-metadata', metadata),
        Route('/register', register, methods=['POST']), Route('/token', token, methods=['POST']), Mount('/', native)],
        lifespan=native.router.lifespan_context)
    app.add_middleware(Auth)
    with serve(app) as base:
        state['base'] = base
        yield state


def service(owner, base, oauth=False):
    return registry.save_record('mcp', registry.with_secrets({'id': 'fixture-service', 'name': 'Fixture service',
        '_kind': 'mcp', 'transport_type': 'http-streamable', 'enabled': True, 'url': base + '/mcp',
        'auth_config': {'auth_type': 'oauth' if oauth else '', 'scopes': ['read']}}, {}), owner)


@pytest.mark.parametrize(('method', 'suffix', 'status'), [
    ('get', '/tools', 502), ('post', '/test', 200),
    ('get', '/resources', 501), ('post', '/metadata/refresh', 501), ('get', '/tool-approvals', 501),
])
def test_saved_stdio_cannot_start_host_process(authenticated_client, monkeypatch, method, suffix, status):
    owner = os.environ['TEST_PLATFORM_USER']
    saved = registry.save_mcp({'name': 'Archived stdio', 'transport_type': 'stdio',
        'stdio_config': {'command': 'npx', 'args': ['archived-mcp']}}, owner)
    monkeypatch.setattr('langchain_mcp_adapters.sessions.stdio_client',
                        lambda *args, **kwargs: pytest.fail('Host process must never start'))
    endpoint = '/api/v1/mcp-services/' + saved['id']
    assert authenticated_client.get(endpoint).status_code == 200
    response = getattr(authenticated_client, method)(endpoint + suffix)
    assert response.status_code == status, response.json
    if suffix == '/test':
        assert response.json['data']['success'] is False
    assert registry.record('mcp', saved['id'], owner)['stdio_config'] == saved['stdio_config']


def test_selected_stdio_connection_is_rejected_before_sdk_discovery(authenticated_client, monkeypatch):
    owner = os.environ['TEST_PLATFORM_USER']
    saved = registry.save_mcp({'name': 'Archived stdio', 'transport_type': 'stdio',
        'stdio_config': {'command': 'uvx', 'args': ['archived-mcp']}}, owner)
    monkeypatch.setattr('langchain_mcp_adapters.sessions.stdio_client',
                        lambda *args, **kwargs: pytest.fail('Host process must never start'))
    with pytest.raises(StoreError, match='禁止在宿主机') as error:
        asyncio.run(registry.mcp_tools(owner, {'mcp_selection_mode': 'selected', 'mcp_services': [saved['id']]}))
    assert error.value.status == 501


def test_metadata_refresh_is_native_cached_and_stale_on_connection_edit(runtime_client, native_mcp, authenticated_client):
    owner = os.environ['TEST_PLATFORM_USER']
    value = service(owner, native_mcp['base'])
    endpoint = '/api/v1/mcp-services/' + value['id'] + '/metadata'
    assert runtime_client.get(endpoint).json == {'success': True, 'synced': False, 'data': None}
    refreshed = runtime_client.post(endpoint + '/refresh', json={})
    assert refreshed.status_code == 200, refreshed.json
    snapshot = refreshed.json['data']
    assert snapshot['server_name'] == 'Native fixture' and snapshot['instructions'] == 'Read fixture data.'
    assert snapshot['tools'][0]['name'] == 'read_fixture' and snapshot['tools'][0]['readOnlyHint'] is True
    tools = authenticated_client.get('/api/v1/mcp-services/' + value['id'] + '/tools').json['data']
    assert tools[0]['readOnlyHint'] is True
    native_mcp['protected'] = True
    assert runtime_client.get(endpoint).json['data']['tools'] == snapshot['tools']
    assert native_mcp['calls'] == 0
    changed = {**value, 'url': native_mcp['base'] + '/another-mcp'}
    registry.save_record('mcp', changed, owner)
    assert runtime_client.get(endpoint).json['data']['stale']
    assert runtime_client.post('/api/v1/mcp-services/' + value['id'] + '/usage-instructions/generate', json={}).status_code == 400


@pytest.mark.parametrize('role', ['admin', 'viewer'])
def test_agent_catalog_matches_fixed_harness_and_selectable_readonly_tools(authenticated_client, monkeypatch, role):
    from agent.graph import build_agent
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage
    owner = os.environ['TEST_PLATFORM_USER']
    with connection() as conn:
        conn.execute('UPDATE platform_users SET role=%s WHERE id=%s', (role, owner))
    server = FastMCP('Knowledge catalog fixture', json_response=True, stateless_http=True)
    calls, declarations = [], []

    @server.tool(name='knowledge.search', annotations=ToolAnnotations(readOnlyHint=True))
    def search(query: str, knowledge_base_ids: list[str]) -> str:
        """Search the selected knowledge bases."""
        calls.append('search')
        return 'source'

    @server.tool(name='knowledge.delete_document', annotations=ToolAnnotations(readOnlyHint=False))
    def delete_document(document_id: str) -> str:
        """Delete a document; unavailable to the current harness."""
        calls.append('delete')
        return 'deleted'

    @server.tool(name='knowledge.unannotated')
    def unannotated(knowledge_base_id: str) -> str:
        """An operation without a confirmed read-only annotation."""
        return 'unknown'

    @server.tool(name='knowledge.unscoped', annotations=ToolAnnotations(readOnlyHint=True))
    def unscoped(query: str) -> str:
        """Read without a verifiable knowledge scope."""
        return 'unscoped'

    class Model(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            declarations.append({item.name if not isinstance(item, dict) else item['name'] for item in tools})
            return self

    monkeypatch.setattr('agent.graph.build_model', lambda *args: Model(responses=[AIMessage(content='done')]))
    with serve(server.streamable_http_app()) as base:
        monkeypatch.setenv('CONTEXTDB_MCP_URL', base + '/mcp')
        response = authenticated_client.get('/api/v1/agents/tools')
        assert response.status_code == 200, response.json
        catalog = response.json['data']
        fixed = set(catalog['switch_managed_tools'])
        optional = {item['name'] for item in catalog['tools']}
        assert fixed == {'task', 'write_todos', 'ls', 'read_file', 'write_file', 'edit_file', 'delete', 'glob', 'grep'}
        assert optional == {'knowledge.search', 'ask_user', 'list_governance_releases', 'get_capture_provenance'}
        assert set(catalog['default_tools']) == {'knowledge.search', 'ask_user'}
        assert not fixed.intersection(optional) and all('always_available' not in item for item in catalog['tools'])

        async def invoke(allowed):
            agent = await build_agent(None, api_key='ctxdb-fake', owner_id=owner, role=role,
                knowledge_base_ids=['kb'], agent_config={'allowed_tools': allowed})
            await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Show capabilities'}]})
        asyncio.run(invoke([]))
        assert declarations[-1] == fixed
        asyncio.run(invoke(sorted(optional)))
        assert declarations[-1] == fixed | optional
        assert calls == []


def authorize(client, state, identifier):
    started = client.post(f'/api/v1/mcp-services/{identifier}/oauth/authorize-url', json={
        'redirect_uri': 'http://localhost' + mcp_auth.CALLBACK_PATH, 'frontend_redirect': '/'})
    assert started.status_code == 200, started.json
    data = started.json['data']
    query = parse_qs(urlsplit(data['authorization_url']).query)
    assert query['code_challenge_method'] == ['S256']
    assert query['scope'] == ['read']
    state['challenge'] = query['code_challenge'][0]
    status = client.get(f'/api/v1/mcp-services/{identifier}/oauth/status', query_string={'authorization_attempt': data['authorization_attempt']})
    assert not status.json['data']['authorized']
    result = client.get(mcp_auth.CALLBACK_PATH, query_string={'state': query['state'][0], 'code': 'fixture-code'})
    assert result.status_code == 302 and result.headers['Location'] == '/#mcp_oauth_result=success'
    assert 'state=' not in result.headers['Location']
    return data, query


def test_official_oauth_pkce_tokens_refresh_and_revocation(runtime_client, native_mcp):
    owner = os.environ['TEST_PLATFORM_USER']
    native_mcp['protected'] = True
    value = service(owner, native_mcp['base'], True)
    prefix = '/api/v1/mcp-services/' + value['id']
    assert runtime_client.get(prefix + '/oauth/status').json['data']['state'] == 'reauth_required'
    data, query = authorize(runtime_client, native_mcp, value['id'])
    assert runtime_client.get(prefix + '/oauth/status').json['data']['authorized']
    assert runtime_client.get(mcp_auth.CALLBACK_PATH, query_string={'state': query['state'][0], 'code': 'fixture-code'}).status_code == 400
    assert native_mcp['registers'] == 1
    # A new consent attempt must remain pending even while an older token is valid.
    authorize(runtime_client, native_mcp, value['id'])
    assert native_mcp['registers'] == 1
    stored = registry.record('mcp-oauth', value['id'], owner)
    assert 'access_token' not in json.dumps({key: value for key, value in stored.items() if key != '_encrypted'})
    assert registry.secrets(stored)['tokens']['refresh_token'] == 'fixture-refresh'
    assert runtime_client.post(prefix + '/metadata/refresh', json={}).status_code == 200
    with connection() as conn:
        conn.execute("UPDATE runtime_records SET payload=payload || %s WHERE owner_id=%s AND kind='mcp-oauth' AND record_key=%s",
                     (Jsonb({'expires_at': time.time() - 1}), owner, value['id']))
    assert runtime_client.get(prefix + '/oauth/status').json['data']['state'] == 'refreshable'
    assert runtime_client.post(prefix + '/metadata/refresh', json={}).status_code == 200
    assert native_mcp['exchanges'][-1]['grant_type'] == 'refresh_token'
    assert runtime_client.get(prefix + '/oauth/status').json['data']['authorized']
    stale_auth = mcp_auth.provider(owner, value)
    assert runtime_client.delete(prefix + '/oauth/token').status_code == 200
    assert not runtime_client.get(prefix + '/oauth/status').json['data']['authorized']
    async def stale_call():
        async with httpx.AsyncClient(auth=stale_auth) as client:
            await client.post(value['url'], json={})
    with pytest.raises(mcp_auth.OAuthRequired):
        asyncio.run(stale_call())
    assert runtime_client.post(prefix + '/oauth/authorize-url', json={'redirect_uri': 'https://evil.example/callback'}).status_code == 400
    assert runtime_client.post(prefix + '/oauth/authorize-url', json={'redirect_uri': 'http://localhost' + mcp_auth.CALLBACK_PATH,
        'frontend_redirect': '//evil.example'}).status_code == 400


@pytest.mark.parametrize('outcome', ['authorize', 'cancel', 'legacy_cancel', 'changed_catalog'])
def test_real_harness_resumes_same_native_tool_after_oauth(harness, runtime_client, native_mcp, outcome):
    client, sid, model, tools, *_ = harness
    owner = os.environ['TEST_PLATFORM_USER']
    value = service(owner, native_mcp['base'], True)
    assert runtime_client.post('/api/v1/mcp-services/fixture-service/metadata/refresh', json={}).status_code == 200
    native_mcp['protected'] = True
    tools.extend(asyncio.run(registry.mcp_tools(owner, {'mcp_selection_mode': 'all'})))
    model.responses = [AIMessage('', tool_calls=[call('fixture-service_read_fixture',
        {'query': 'after-consent'}, 'pending-tool')]), AIMessage('Completed')]
    if outcome == 'legacy_cancel':
        candidate = next(tool for tool in tools if tool.name == 'fixture-service_read_fixture')
        coroutine = candidate.coroutine
        async def legacy_pause(**_arguments):
            return mcp_auth.oauth_interrupt(owner, value, 'read_fixture')
        candidate.coroutine = legacy_pause
    sent = events(client.post(f'/api/v1/agent-chat/{sid}', json={'query': 'Use the MCP tool'}))
    if outcome == 'legacy_cancel':
        candidate.coroutine = coroutine
    pending = next(event['data'] for event in sent if event['response_type'] == 'mcp_oauth_required')
    assert pending['mcp_tool_name'] == 'read_fixture'
    assert client.get(f'/api/v1/messages/{sid}/load').json()['data'][-1]['delegated_prompts'][0]['id'] == pending['pending_id']
    assert native_mcp['calls'] == 0
    endpoint = '/api/v1/agent/mcp-oauth-resolutions/' + pending['pending_id']
    body = {'service_id': value['id'], 'decision': 'authorize'}
    assert client.post(endpoint, json={**body, 'service_id': 'different-service'}).status_code == 400
    assert client.post(endpoint, json=body).status_code == 409
    authorize(runtime_client, native_mcp, value['id'])
    if outcome == 'changed_catalog':
        native_mcp['read_tool'].annotations = ToolAnnotations(readOnlyHint=False)
    cancelled = outcome in ('cancel', 'legacy_cancel')
    response = client.post(endpoint + '/cancel', json={}) if cancelled else client.post(endpoint, json=body)
    assert response.status_code == 200 and response.json() == {'resumed': True}, response.text
    params = {'message_id': sent[0]['assistant_message_id'], 'resume_pending_id': pending['pending_id']}
    resumed = events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params=params))
    if outcome == 'changed_catalog':
        assert resumed[-1]['response_type'] == 'error' and resumed[-1]['data']['status'] == 403
    else:
        assert resumed[-1]['response_type'] == 'complete', resumed
        result = next(event['data']['output'] for event in resumed if event['response_type'] == 'tool_result')
        assert ('skipped' if cancelled else 'fixture:after-consent') in result
        assert client.get(f'/api/v1/messages/{sid}/load').json()['data'][-1]['delegated_prompts'][0]['response']['authorized'] is (outcome == 'authorize')
        assert events(client.get(f'/api/v1/sessions/continue-stream/{sid}', params=params))[-1]['response_type'] == 'stop'
        assert client.post(endpoint, json=body).status_code == 409
    assert native_mcp['calls'] == int(outcome == 'authorize')


def test_oauth_revocation_during_callback_cannot_resurrect_token(runtime_client, native_mcp):
    owner = os.environ['TEST_PLATFORM_USER']
    native_mcp['protected'] = True
    value = service(owner, native_mcp['base'], True)
    prefix = '/api/v1/mcp-services/fixture-service'
    started = runtime_client.post(prefix + '/oauth/authorize-url', json={'redirect_uri': 'http://localhost' + mcp_auth.CALLBACK_PATH}).json['data']
    query = parse_qs(urlsplit(started['authorization_url']).query)
    native_mcp['challenge'] = query['code_challenge'][0]
    runtime_client.delete(prefix + '/oauth/token')
    result = runtime_client.get(mcp_auth.CALLBACK_PATH, query_string={'state': query['state'][0], 'code': 'fixture-code'})
    assert result.status_code == 302 and 'authorization_failed' in result.headers['Location']
    assert not mcp_auth.status(owner, value)['authorized']


def test_explicit_oauth_metadata_location_uses_native_issuer_validation(runtime_client, native_mcp):
    owner = os.environ['TEST_PLATFORM_USER']
    native_mcp['protected'] = True
    value = service(owner, native_mcp['base'], True)
    value['auth_config']['auth_server_metadata_url'] = native_mcp['base'] + '/explicit-issuer-metadata'
    registry.save_record('mcp', value, owner)
    authorize(runtime_client, native_mcp, value['id'])
    assert native_mcp['metadata_paths'] == ['/explicit-issuer-metadata']


def test_metadata_override_does_not_bypass_official_issuer_validation(runtime_client, native_mcp):
    owner = os.environ['TEST_PLATFORM_USER']
    native_mcp.update(protected=True, issuer='https://wrong-issuer.example')
    value = service(owner, native_mcp['base'], True)
    value['auth_config']['auth_server_metadata_url'] = native_mcp['base'] + '/explicit-issuer-metadata'
    registry.save_record('mcp', value, owner)
    result = runtime_client.post('/api/v1/mcp-services/fixture-service/oauth/authorize-url', json={'redirect_uri': 'http://localhost' + mcp_auth.CALLBACK_PATH})
    assert result.status_code == 502 and not mcp_auth.status(owner, value)['authorized']
    assert not native_mcp['exchanges'] and not native_mcp['registers']


def test_metadata_and_token_status_are_owner_scoped(runtime_client, native_mcp):
    from webapi.auth import create_user
    owner = os.environ['TEST_PLATFORM_USER']
    service(owner, native_mcp['base'], True)
    create_user('other-mcp@example.com', 'Other member', 'test-password-123', 'admin')
    other = runtime_client.application.test_client()
    signed_in = other.post('/api/v1/auth/login', json={'email': 'other-mcp@example.com', 'password': 'test-password-123'})
    other.environ_base['HTTP_AUTHORIZATION'] = 'Bearer ' + signed_in.json['token']
    for suffix in ('metadata', 'oauth/status'):
        assert other.get('/api/v1/mcp-services/fixture-service/' + suffix).status_code == 404


