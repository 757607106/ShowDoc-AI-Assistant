"""Configuration and authorization checks, with isolated PostgreSQL and no cloud calls."""
import asyncio
import os
import uuid

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
import pytest
from flask import Flask, g

from agent import config, registry
from governance.store import StoreError


@pytest.fixture
def configured_owner(platform_test_database, monkeypatch):
    schema = 'test_agent_config_' + uuid.uuid4().hex
    with psycopg.connect(platform_test_database, autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    monkeypatch.setenv('DATABASE_URL', make_conninfo(platform_test_database, options=f'-csearch_path={schema}'))
    from cryptography.fernet import Fernet
    monkeypatch.setenv('CREDENTIAL_ENCRYPTION_KEY', Fernet.generate_key().decode())
    from governance.database import initialize
    initialize()
    from webapi.auth import create_user
    owner_id = create_user('config@example.com', '配置测试', 'test-password-123', 'admin')
    yield owner_id
    with psycopg.connect(platform_test_database, autocommit=True) as conn:
        conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


@pytest.fixture
def settings_client(configured_owner):
    from webapi.agents import agents_bp
    from webapi.runtime_settings import runtime_settings_bp
    app = Flask(__name__)
    app.register_blueprint(agents_bp)
    app.register_blueprint(runtime_settings_bp)
    app.before_request(lambda: setattr(g, 'user', {'id': configured_owner, 'role': 'admin'}))
    @app.errorhandler(StoreError)
    def error(exc):
        return {'success': False, 'message': str(exc)}, exc.status
    return app.test_client()


class KnowledgeClient:
    def __init__(self):
        self.details = []

    def list_knowledge_bases(self, **kwargs):
        return {'knowledge_bases': [{'id': 'a', 'name': '知识A'}, {'id': 'b', 'name': '知识B'},
                                    {'id': 'internal', 'name': '_governance'}], 'total': 3}

    def get_knowledge_base(self, kb_id):
        self.details.append(kb_id)
        if kb_id not in ('a', 'b'):
            raise StoreError('denied', 403)
        return {'id': kb_id}

    def get_document(self, kb_id, document_id):
        if document_id != 'doc-a':
            raise StoreError('denied', 403)
        return {'id': document_id, 'knowledge_base_id': 'a'}


def test_agent_crud_copy_preserves_configuration_and_owner(settings_client, configured_owner):
    client = settings_client
    values = client.get('/api/v1/agents').json['data']
    assert {value['id'] for value in values} == set(config.BUILTINS)
    assert all(value['config']['kb_selection_mode'] == 'all' for value in values)
    assert all(value['config']['retrieval_provider'] == 'contextdb' for value in values)
    created = client.post('/api/v1/agents', json={'name': '我的助手', 'config': {'kb_selection_mode': 'selected',
        'knowledge_bases': ['a'], 'allowed_tools': [], 'skills_selection_mode': 'selected', 'selected_skills': ['guide']}})
    assert created.status_code == 201
    agent = created.json['data']
    assert config.load_agent(agent['id'], configured_owner)['config']['allowed_tools'] == []
    with pytest.raises(StoreError):
        config.load_agent(agent['id'], 'other-owner')
    updated = client.put('/api/v1/agents/' + agent['id'], json={'name': '更新', 'config': {**agent['config'], 'temperature': 0.2}})
    assert updated.json['data']['config']['temperature'] == 0.2
    copied = client.post('/api/v1/agents/' + agent['id'] + '/copy').json['data']
    assert copied['id'] != agent['id'] and copied['config'] == updated.json['data']['config']
    assert client.delete('/api/v1/agents/' + agent['id']).status_code == 200
    assert client.get('/api/v1/agents/' + agent['id']).status_code == 404
    assert client.delete('/api/v1/agents/builtin-smart-reasoning').status_code == 400


def test_smart_agent_accepts_upstream_dormant_defaults_and_projects_real_retrieval(settings_client):
    response = settings_client.post('/api/v1/agents', json={'name': '官方默认助手', 'config': {
        'agent_mode': 'smart-reasoning', 'memory_enabled': True, 'multi_turn_enabled': False,
        'enable_query_expansion': True, 'enable_rewrite': True, 'rerank_top_k': 5, 'rerank_threshold': 0.5,
        'history_turns': 5, 'context_template': 'Dormant quick-answer template', 'retrieval_provider': 'other'}})
    assert response.status_code == 201, response.json
    saved = response.json['data']['config']
    assert saved['memory_enabled'] is True and saved['multi_turn_enabled'] is True
    assert saved['retrieval_provider'] == 'contextdb' and saved['enable_rewrite'] is True
    presets = settings_client.get('/api/v1/agents/type-presets').json['data']
    assert all(value['config']['retain_retrieval_history'] is True for value in presets if value['config'])
    assert next(value for value in presets if value['id'] == 'custom')['config'] is None


@pytest.mark.parametrize('unsupported', [
    {'web_search_enabled': True}, {'reflection_enabled': True}, {'sandbox_config_id': 'docker'},
    {'retain_retrieval_history': False},
    {'agent_mode': 'quick-answer', 'history_turns': 5},
    {'agent_mode': 'quick-answer', 'multi_turn_enabled': False},
    {'agent_mode': 'quick-answer', 'context_template': 'Unsupported RAG template'},
    {'agent_mode': 'quick-answer', 'fallback_strategy': 'fixed'},
    {'agent_mode': 'quick-answer', 'enable_query_expansion': True},
    {'agent_mode': 'quick-answer', 'rerank_top_k': 5},
])
def test_unconnected_agent_options_reject_save_and_execution_but_keep_old_records_readable(settings_client, configured_owner, unsupported):
    response = settings_client.post('/api/v1/agents', json={'name': 'unsupported', 'config': unsupported})
    assert response.status_code == 501 and registry.records('agent', configured_owner) == []
    legacy = registry.save_record('agent', {'id': 'legacy-config', 'name': '旧配置', 'is_builtin': False,
        'config': unsupported}, configured_owner)
    read = settings_client.get('/api/v1/agents/legacy-config')
    assert read.status_code == 200 and read.json['data']['config']['retain_retrieval_history'] is True
    assert registry.record('agent', legacy['id'], configured_owner) == legacy
    with pytest.raises(StoreError) as error:
        config.resolve_request({'agent_id': legacy['id']}, client=KnowledgeClient(), owner_id=configured_owner)
    assert error.value.status == 501
    assert settings_client.post('/api/v1/agents/legacy-config/copy').status_code == 501
    repaired = settings_client.put('/api/v1/agents/legacy-config', json={'config': {}})
    assert repaired.status_code == 200 and repaired.json['data']['config']['sandbox_config_id'] == 'state-backend'


def test_builtin_quick_answer_uses_native_history_without_a_fabricated_turn_limit(settings_client):
    value = settings_client.get('/api/v1/agents/builtin-quick-answer').json['data']['config']
    assert value['history_turns'] == 0 and value['multi_turn_enabled'] is True
    assert config.validate_config(value)['history_turns'] == 0


def test_scope_default_all_selected_none_and_explicit_mentions(configured_owner):
    client = KnowledgeClient()
    def resolve(body):
        return config.resolve_request(body, client=client, owner_id=configured_owner, role='admin')
    assert resolve({})['knowledge_base_ids'] == ['a', 'b']
    assert resolve({'knowledge_base_ids': []})['knowledge_base_ids'] == ['a', 'b']
    agent = config.save_agent({'name': 'selected', 'config': {'kb_selection_mode': 'selected', 'knowledge_bases': ['b']}}, configured_owner)
    assert resolve({'agent_id': agent['id']})['knowledge_base_ids'] == ['b']
    assert resolve({'agent_id': agent['id'], 'mentioned_items': [{'type': 'kb', 'id': 'a'}]})['knowledge_base_ids'] == ['a']
    agent = config.save_agent({'name': 'mentions', 'config': {'retrieve_kb_only_when_mentioned': True}}, configured_owner)
    assert resolve({'agent_id': agent['id']})['knowledge_base_ids'] == []
    assert resolve({'agent_id': agent['id'], 'question_origin': {'knowledge_base_id': 'b'}})['knowledge_base_ids'] == ['b']
    source = resolve({'agent_id': agent['id'], 'question_origin': {'knowledge_base_id': 'a', 'knowledge_id': 'doc-a'}})
    assert source['knowledge_ids'] == ['doc-a'] and source['agent_config']['_whole_knowledge_bases'] == []
    with pytest.raises(StoreError, match='来源知识库'):
        resolve({'agent_id': agent['id'], 'question_origin': {'knowledge_base_id': 'b', 'knowledge_id': 'doc-a'}})
    agent = config.save_agent({'name': 'none', 'config': {'kb_selection_mode': 'none'}}, configured_owner)
    assert resolve({'agent_id': agent['id']})['knowledge_base_ids'] == []


def test_document_scope_and_permission_validation(configured_owner):
    client = KnowledgeClient()
    result = config.resolve_request({'knowledge_ids': ['doc-a']}, client=client, owner_id=configured_owner)
    assert result['knowledge_base_ids'] == ['a'] and result['knowledge_ids'] == ['doc-a']
    assert result['agent_config']['_whole_knowledge_bases'] == []
    assert result['agent_config']['_document_bases'] == {'doc-a': 'a'}
    assert result['agent_config']['access_level'] == 'read_only'
    for body in ({'knowledge_base_ids': ['outside']}, {'knowledge_ids': ['outside']}):
        with pytest.raises(StoreError, match='denied'):
            config.resolve_request(body, client=client, owner_id=configured_owner)
    with pytest.raises(StoreError, match='标签'):
        config.resolve_request({'tag_ids': ['tag']}, client=client, owner_id=configured_owner)


def test_models_encrypt_secrets_and_real_configuration_selects_model(settings_client, configured_owner, monkeypatch):
    body = {'name': 'my-model', 'type': 'KnowledgeQA', 'source': 'remote', 'parameters': {
        'base_url': 'https://model.invalid/v1', 'api_key': 'private-model-key', 'context_window': 32768}}
    value = settings_client.post('/api/v1/models', json=body).json['data']
    assert 'private-model-key' not in str(value)
    assert value['credentials']['api_key']['configured'] is True
    stored = registry.record('model', value['id'], configured_owner)
    assert 'private-model-key' not in str(stored)
    assert registry.model_config(value['id'], configured_owner)['parameters']['api_key'] == 'private-model-key'
    from agent import graph
    monkeypatch.setattr(graph, 'ChatOpenAI', lambda **kwargs: kwargs)
    model = graph.build_model({'model_id': value['id'], 'temperature': 0.2, 'max_completion_tokens': 123}, configured_owner)
    assert model['model'] == 'my-model' and model['api_key'] == 'private-model-key'
    assert model['temperature'] == 0.2 and model['max_tokens'] == 123
    with pytest.raises(StoreError):
        registry.model_config(value['id'], 'another-owner')
    assert settings_client.put(f"/api/v1/models/{value['id']}/credentials", json={'api_key': 'rotated'}).status_code == 200
    assert registry.model_config(value['id'], configured_owner)['parameters']['api_key'] == 'rotated'


def test_copy_environment_model_does_not_export_server_api_key(settings_client, configured_owner, monkeypatch):
    monkeypatch.setenv('BAILIAN_API_KEY', 'shared-server-key')
    value = settings_client.post('/api/v1/models/agent-main/copy', json={'display_name': 'personal'}).json['data']
    assert value['credentials']['api_key']['configured'] is False
    assert not registry.model_config(value['id'], configured_owner)['parameters'].get('api_key')


def test_image_turn_selects_configured_vlm_and_validates_asr_type(configured_owner):
    vision = registry.save_model({'name': 'vision', 'type': 'VLLM', 'parameters': {
        'base_url': 'https://model.invalid/v1', 'api_key': 'private'}}, configured_owner)
    speech = registry.save_model({'name': 'whisper-compatible', 'type': 'ASR', 'parameters': {
        'base_url': 'https://model.invalid/v1', 'api_key': 'private'}}, configured_owner)
    agent = config.save_agent({'name': 'multimodal', 'config': {'image_upload_enabled': True,
        'vlm_model_id': vision['id'], 'audio_upload_enabled': True, 'asr_model_id': speech['id']}}, configured_owner)
    result = config.resolve_request({'agent_id': agent['id']}, client=KnowledgeClient(), owner_id=configured_owner, has_image_attachments=True)
    assert result['agent_config']['model_id'] == vision['id']
    assert result['requested_knowledge_base_ids'] == [] and result['knowledge_base_ids'] == ['a', 'b']
    with pytest.raises(StoreError, match='类型'):
        config.save_agent({'name': 'invalid', 'config': {'asr_model_id': vision['id']}}, configured_owner)


def test_native_tool_catalog_uses_current_official_discovery(settings_client, monkeypatch):
    from types import SimpleNamespace
    from langchain_core.tools import StructuredTool
    candidate = StructuredTool.from_function(name='knowledge.search', description='Official description', func=lambda query: query,
        args_schema={'type': 'object', 'properties': {'query': {'type': 'string'}, 'knowledge_base_ids': {'type': 'array'}}},
        metadata={'readOnlyHint': True})
    class Client:
        def __init__(self, *args, **kwargs):
            pass
        async def get_tools(self):
            return [candidate]
    monkeypatch.setattr('webapi.auth.client_for_user', lambda: SimpleNamespace(api_key='fake'))
    monkeypatch.setattr('langchain_mcp_adapters.client.MultiServerMCPClient', Client)
    result = settings_client.get('/api/v1/agents/tools').json['data']
    found = next(item for item in result['tools'] if item['name'] == 'knowledge.search')
    assert found['description'] == 'Official description'
    assert 'knowledge.search' in result['default_tools']
    assert 'knowledge.fake_write' not in {item['name'] for item in result['tools']}


def test_native_tool_catalog_failure_does_not_invent_fallback_tools(settings_client, monkeypatch):
    from types import SimpleNamespace
    class Client:
        def __init__(self, *args, **kwargs):
            pass
        async def get_tools(self):
            raise RuntimeError('Discovery unavailable')
    monkeypatch.setattr('webapi.auth.client_for_user', lambda: SimpleNamespace(api_key='fake'))
    monkeypatch.setattr('langchain_mcp_adapters.client.MultiServerMCPClient', Client)
    response = settings_client.get('/api/v1/agents/tools')
    assert response.status_code == 502 and response.json['success'] is False
    assert 'data' not in response.json


def test_mcp_configuration_credentials_and_tool_flags(settings_client, configured_owner):
    value = settings_client.post('/api/v1/mcp-services', json={'name': 'server', 'transport_type': 'http-streamable',
        'url': 'https://mcp.invalid/mcp', 'headers': {'Secret': 'header-secret'},
        'auth_config': {'auth_type': 'bearer', 'token': 'private-token'}}).json['data']
    assert 'private-token' not in str(value) and 'header-secret' not in str(value)
    saved = registry.record('mcp', value['id'], configured_owner)
    assert 'private-token' not in str(saved)
    assert registry.mcp_connection(saved)['headers'] == {'Secret': 'header-secret', 'Authorization': 'Bearer private-token'}
    assert settings_client.put(f"/api/v1/mcp-services/{value['id']}", json=value).status_code == 200
    assert registry.secrets(registry.record('mcp', value['id'], configured_owner))['headers'] == {'Secret': 'header-secret'}
    response = settings_client.put(f"/api/v1/mcp-services/{value['id']}/tool-approvals/read", json={'enabled': False, 'require_approval': True})
    assert response.json['data'][0]['enabled'] is False
    assert settings_client.delete(f"/api/v1/mcp-services/{value['id']}/credentials/token").status_code == 200
    assert not registry.secrets(registry.record('mcp', value['id'], configured_owner)).get('token')


def test_runtime_mcp_uses_discovered_tools_and_preserves_schema(configured_owner, monkeypatch):
    from langchain_core.tools import StructuredTool
    value = registry.save_mcp({'name': 'server', 'transport_type': 'http-streamable', 'url': 'https://mcp.invalid/mcp'}, configured_owner)
    tool = StructuredTool.from_function(name=value['id'] + '_read', description='real schema',
        func=lambda query: query, args_schema={'type': 'object', 'properties': {'query': {'type': 'string'}}}, metadata={'readOnlyHint': True})
    seen = []
    class Client:
        def __init__(self, connections, **kwargs):
            seen.append(connections)
        async def get_tools(self):
            return [tool]
    monkeypatch.setattr('langchain_mcp_adapters.client.MultiServerMCPClient', Client)
    result = asyncio.run(registry.mcp_tools(configured_owner, {'mcp_selection_mode': 'selected', 'mcp_services': [value['id']]}))
    assert result == [tool] and result[0].args_schema['properties'] == {'query': {'type': 'string'}}
    assert seen[0][value['id']]['url'] == 'https://mcp.invalid/mcp'


def test_selected_skill_catalog_is_prepared_without_installation(configured_owner):
    from agent.harness_config import prepare_harness_files
    registry.save_skill('guide', {'SKILL.md': '---\nname: guide\ndescription: evidence\n---\nRead reference.md',
        'reference.md': 'trusted reference'}, configured_owner)
    config = {'skills_selection_mode': 'selected', 'selected_skills': ['guide']}
    before = registry.records('skill_install', configured_owner)
    files = prepare_harness_files(configured_owner, config)
    assert files['/skills/guide/reference.md']['content'] == 'trusted reference'
    assert registry.records('skill_install', configured_owner) == before
    with pytest.raises(StoreError):
        prepare_harness_files('another-owner', config)


def test_native_tool_selection_keeps_names_without_enabling_unselected_tools():
    assert config.allowed_knowledge_tools({'allowed_tools': ['search_knowledge', 'knowledge.wiki_search']}) == {'knowledge.search', 'knowledge.wiki_search'}
    assert config.allowed_knowledge_tools({'allowed_tools': []}) == set()
    with pytest.raises(StoreError):
        config.validate_config({'allowed_tools': 'search_knowledge'})


def test_native_document_scope_cannot_expand_to_other_documents(monkeypatch):
    from agent import tools as native_tools
    from langchain_core.tools import StructuredTool
    from langchain_mcp_adapters.interceptors import MCPToolCallRequest
    calls = []
    class Client:
        def __init__(self, connections, *, tool_interceptors):
            self.authorize = tool_interceptors[0]
        async def get_tools(self):
            async def invoke(**arguments):
                async def handler(request):
                    calls.append(request.args)
                    return request.args
                return await self.authorize(MCPToolCallRequest('knowledge.search', arguments, 'contextdb'), handler)
            return [StructuredTool.from_function(name='knowledge.search', description='Native search', coroutine=invoke,
                args_schema={'type': 'object', 'properties': {'query': {'type': 'string'}, 'knowledge_base_ids': {'type': 'array'},
                    'document_ids': {'type': 'array'}}}, metadata={'readOnlyHint': True})]
    class DocumentClient:
        def __init__(self, **kwargs):
            pass
        def get_document(self, kb_id, document_id):
            return {'knowledge_base_id': 'a'}
    monkeypatch.setattr('langchain_mcp_adapters.client.MultiServerMCPClient', Client)
    monkeypatch.setattr(native_tools, 'ContextDBClient', DocumentClient)
    async def exercise():
        loaded = await native_tools.load_knowledge_mcp_tools(api_key='fake', knowledge_base_ids=['a'],
            agent_config={'allowed_tools': ['search_knowledge'], '_whole_knowledge_bases': [], '_document_bases': {'doc-a': 'a'}})
        await loaded[0].ainvoke({'query': 'question'})
        with pytest.raises(StoreError, match='超出所选文档'):
            await loaded[0].ainvoke({'query': 'question', 'document_ids': ['other']})
    asyncio.run(exercise())
    assert calls == [{'query': 'question', 'knowledge_base_ids': ['a'], 'document_ids': ['doc-a']}]


def test_archived_search_configuration_is_masked_owned_and_read_only(settings_client, configured_owner, monkeypatch):
    from webapi.auth import create_user
    def no_network(*args, **kwargs):
        raise AssertionError('Retired search must not contact a provider')
    monkeypatch.setattr('requests.sessions.Session.request', no_network)
    value = registry.save_record('web-search', registry.with_secrets({
        'id': 'saved-search', '_kind': 'web-search', 'name': 'Saved search',
        'provider': 'tavily', 'enabled': True, 'parameters': {}}, {'api_key': 'tavily-secret'}), configured_owner)
    foreign = create_user('other-search@example.com', 'Other', 'test-password-123', 'admin')
    registry.save_record('web-search', {**value, 'id': 'foreign-search'}, foreign)
    for key, config_value in [('web-search-config', {'enabled': True, 'provider_id': value['id']}),
                              ('skill-installer-model', {'model_id': 'preserved-model'})]:
        registry.save_record('settings', {'id': key, 'value': config_value}, configured_owner)
    before = {kind: registry.records(kind, configured_owner) for kind in ('web-search', 'settings')}
    base = '/api/v1/web-search-providers'
    for path in (base, '/api/v1/web-search/providers', base + '/saved-search'):
        response = settings_client.get(path)
        assert response.status_code == 200
        assert 'tavily-secret' not in response.text and '_encrypted' not in response.text
        found = response.json['data'][0] if isinstance(response.json['data'], list) else response.json['data']
        assert found['credentials']['api_key']['configured'] is True
        assert found['enabled'] is False and found['read_only'] is True
    assert settings_client.get(base + '/types').json['data'] == []
    for method, suffix in [('PUT', ''), ('PATCH', ''), ('DELETE', ''), ('POST', '/test'),
                           ('PUT', '/credentials'), ('DELETE', '/credentials/api_key')]:
        assert settings_client.open(base + '/saved-search' + suffix, method=method, json={}).status_code == 410
        assert settings_client.open(base + '/foreign-search' + suffix, method=method, json={}).status_code == 404
    assert settings_client.get(base + '/foreign-search').status_code == 404
    assert settings_client.post(base, json={}).status_code == 410
    assert settings_client.post(base + '/test', json={}).status_code == 410
    for key in ('web-search-config', 'skill-installer-model'):
        response = settings_client.get('/api/v1/tenants/kv/' + key)
        assert response.status_code == 200 and response.json['data']['read_only'] is True
        assert settings_client.put('/api/v1/tenants/kv/' + key, json={}).status_code == 410
    assert settings_client.get('/api/v1/tenants/kv/web-search-config').json['data']['enabled'] is False
    assert settings_client.get('/api/v1/tenants/kv/skill-installer-model').json['data']['model_id'] == 'preserved-model'
    assert before == {kind: registry.records(kind, configured_owner) for kind in before}
