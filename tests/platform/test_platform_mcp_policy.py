"""MCP policy APIs and runtime agree on the SDK-discovered read-only tools."""
import asyncio
from contextlib import contextmanager
import os

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
import pytest

from agent import registry
from tests.platform.test_platform_mcp_runtime import serve


@pytest.fixture
def policy_service():
    invoked = []
    server = FastMCP('Policy fixture', json_response=True, stateless_http=True)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def read_fixture() -> str:
        """Read a fixture."""
        invoked.append('read')
        return 'read'

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False))
    def write_fixture() -> str:
        """Write a fixture."""
        invoked.append('write')
        return 'write'

    @server.tool()
    def unknown_fixture() -> str:
        """A tool without a read-only declaration."""
        invoked.append('unknown')
        return 'unknown'

    owner = os.environ['TEST_PLATFORM_USER']
    with serve(server.streamable_http_app()) as base:
        value = registry.save_mcp({'name': 'Policy fixture', 'transport_type': 'http-streamable',
            'url': base + '/mcp'}, owner)
        # Stored legacy flags must not grant execution beyond the discovered policy.
        value['tool_approvals'] = {'write_fixture': {'enabled': True, 'require_approval': False}}
        registry.save_record('mcp', value, owner)
        yield value, invoked


def policies(response):
    assert response.status_code == 200, response.json
    return {item['tool_name']: item for item in response.json['data']}


def test_effective_policy_matches_tools_metadata_and_runtime(authenticated_client, policy_service):
    value, invoked = policy_service
    prefix = '/api/v1/mcp-services/' + value['id']
    rows = policies(authenticated_client.get(prefix + '/tool-approvals'))
    assert set(rows) == {'read_fixture', 'write_fixture', 'unknown_fixture'}
    assert rows['read_fixture']['enabled'] is True
    assert rows['read_fixture']['require_approval'] is False
    assert rows['write_fixture']['enabled'] is False and rows['unknown_fixture']['enabled'] is False
    tools = authenticated_client.get(prefix + '/tools').json['data']
    snapshot = authenticated_client.post(prefix + '/metadata/refresh', json={}).json['data']
    for catalog in (tools, snapshot['tools']):
        assert {item['name'] for item in catalog if item['enabled']} == {'read_fixture'}
    native = asyncio.run(registry.mcp_tools(os.environ['TEST_PLATFORM_USER'], {
        'mcp_selection_mode': 'selected', 'mcp_services': [value['id']]}))
    assert [tool.name for tool in native] == [value['id'] + '_read_fixture']
    assert invoked == []


@pytest.mark.parametrize('name,status', [('write_fixture', 403), ('unknown_fixture', 403), ('invented', 404)])
@pytest.mark.parametrize('updates', [{'enabled': True}, {'require_approval': False}])
def test_disallowed_tool_policies_cannot_be_saved(authenticated_client, policy_service, name, status, updates):
    value, invoked = policy_service
    owner = os.environ['TEST_PLATFORM_USER']
    before = registry.record('mcp', value['id'], owner)
    response = authenticated_client.put('/api/v1/mcp-services/' + value['id'] + '/tool-approvals/' + name,
                                        json=updates)
    assert response.status_code == status, response.json
    assert registry.record('mcp', value['id'], owner) == before
    assert invoked == []


def test_readonly_policy_changes_take_effect_and_preserve_other_fields(authenticated_client, policy_service):
    value, invoked = policy_service
    owner = os.environ['TEST_PLATFORM_USER']
    prefix = '/api/v1/mcp-services/' + value['id']
    rows = policies(authenticated_client.put(prefix + '/tool-approvals/read_fixture',
        json={'enabled': False, 'require_approval': True}))
    assert rows['read_fixture']['enabled'] is False and rows['read_fixture']['require_approval'] is True
    assert asyncio.run(registry.mcp_tools(owner, {
        'mcp_selection_mode': 'selected', 'mcp_services': [value['id']]})) == []
    rows = policies(authenticated_client.put(prefix + '/tool-approvals/read_fixture', json={'enabled': True}))
    assert rows['read_fixture']['enabled'] is True and rows['read_fixture']['require_approval'] is True
    native = asyncio.run(registry.mcp_tools(owner, {'mcp_selection_mode': 'selected', 'mcp_services': [value['id']]}))
    assert len(native) == 1 and native[0].metadata['require_approval'] is True
    saved = registry.record('mcp', value['id'], owner)
    assert saved['url'] == value['url'] and saved['auth_config'] == value['auth_config']
    assert invoked == []


def test_policy_rejects_invalid_input_and_foreign_service(authenticated_client, policy_service):
    value, invoked = policy_service
    prefix = '/api/v1/mcp-services/' + value['id']
    assert authenticated_client.put(prefix + '/tool-approvals/read_fixture', json={'enabled': 'true'}).status_code == 400
    assert authenticated_client.put(prefix + '/tool-approvals/read_fixture', json={'unexpected': True}).status_code == 400
    foreign = registry.save_record('mcp', {**value, 'id': 'foreign-service'}, 'other-owner')
    for method, suffix in [('get', ''), ('put', '/read_fixture')]:
        response = getattr(authenticated_client, method)(
            '/api/v1/mcp-services/' + foreign['id'] + '/tool-approvals' + suffix,
            **({'json': {'enabled': True}} if method == 'put' else {}))
        assert response.status_code == 404
    assert invoked == []


def test_changed_cached_directory_requires_refresh(authenticated_client, policy_service):
    value, invoked = policy_service
    owner = os.environ['TEST_PLATFORM_USER']
    prefix = '/api/v1/mcp-services/' + value['id']
    assert authenticated_client.post(prefix + '/metadata/refresh', json={}).status_code == 200
    cached = registry.record('mcp-metadata', value['id'], owner)
    cached['snapshot']['tools'].append({'name': 'removed_tool', 'readOnlyHint': True})
    registry.save_record('mcp-metadata', cached, owner)
    before = registry.record('mcp', value['id'], owner)
    assert authenticated_client.get(prefix + '/tool-approvals').status_code == 409
    assert authenticated_client.put(prefix + '/tool-approvals/read_fixture', json={'enabled': False}).status_code == 409
    assert registry.record('mcp', value['id'], owner) == before
    assert authenticated_client.post(prefix + '/metadata/refresh', json={}).status_code == 200
    assert 'removed_tool' not in policies(authenticated_client.get(prefix + '/tool-approvals'))
    assert invoked == []


@pytest.mark.parametrize('concurrent_change', ['credentials', 'delete'])
def test_policy_save_cannot_overwrite_concurrent_service_change(
        authenticated_client, policy_service, monkeypatch, concurrent_change):
    from webapi import runtime_settings
    value, invoked = policy_service
    owner = os.environ['TEST_PLATFORM_USER']
    original_connection = runtime_settings.connection
    changed = None

    @contextmanager
    def after_read_connection():
        nonlocal changed
        if concurrent_change == 'delete':
            registry.delete_record('mcp', value['id'], owner)
        else:
            current = registry.record('mcp', value['id'], owner)
            changed = registry.save_record('mcp', registry.with_secrets(current, {'api_key': 'new-credential'}), owner)
        with original_connection() as conn:
            yield conn

    monkeypatch.setattr(runtime_settings, 'connection', after_read_connection)
    response = authenticated_client.put('/api/v1/mcp-services/' + value['id'] + '/tool-approvals/read_fixture',
                                        json={'enabled': False})
    assert response.status_code == 409, response.json
    if concurrent_change == 'delete':
        assert not any(item['id'] == value['id'] for item in registry.records('mcp', owner))
    else:
        assert registry.record('mcp', value['id'], owner) == changed
        assert registry.secrets(changed) == {'api_key': 'new-credential'}
    assert invoked == []


def _fail_first_get_tools(monkeypatch, failures=1):
    from langchain_mcp_adapters.client import MultiServerMCPClient
    original = MultiServerMCPClient.get_tools
    state = {'n': 0}

    async def flaky(self, **kwargs):
        state['n'] += 1
        if state['n'] <= failures:
            raise RuntimeError('simulated outage')
        return await original(self, **kwargs)

    monkeypatch.setattr(MultiServerMCPClient, 'get_tools', flaky)
    return state


def test_unreachable_service_falls_back_to_synced_directory(authenticated_client, policy_service, monkeypatch):
    value, invoked = policy_service
    owner = os.environ['TEST_PLATFORM_USER']
    assert authenticated_client.post('/api/v1/mcp-services/' + value['id'] + '/metadata/refresh', json={}).status_code == 200
    _fail_first_get_tools(monkeypatch)
    config = {'mcp_selection_mode': 'selected', 'mcp_services': [value['id']]}
    tools = asyncio.run(registry.mcp_tools(owner, config))
    assert [tool.name for tool in tools] == [value['id'] + '_read_fixture']
    assert '_mcp_unavailable' not in config
    assert invoked == []
    result = asyncio.run(tools[0].ainvoke({'name': tools[0].name, 'args': {},
                                           'id': 'fallback-call', 'type': 'tool_call'}))
    assert invoked == ['read']
    assert result.content[0]['text'] == 'read'


def test_unreachable_service_without_directory_degrades_to_unavailable_note(policy_service, monkeypatch):
    value, invoked = policy_service
    owner = os.environ['TEST_PLATFORM_USER']
    from langchain_mcp_adapters.client import MultiServerMCPClient

    async def outage(self, **kwargs):
        raise RuntimeError('simulated outage')

    monkeypatch.setattr(MultiServerMCPClient, 'get_tools', outage)
    config = {'mcp_selection_mode': 'selected', 'mcp_services': [value['id']]}
    assert asyncio.run(registry.mcp_tools(owner, config)) == []
    assert config['_mcp_unavailable'] == [value['name']]
    assert invoked == []

    from agent.config import validate_config
    from agent.graph import _system_prompt
    rendered = validate_config({'agent_mode': 'smart-reasoning'})
    rendered['_mcp_unavailable'] = config['_mcp_unavailable']
    prompt = _system_prompt(rendered, [], False)
    assert value['name'] in prompt and '不可用' in prompt
