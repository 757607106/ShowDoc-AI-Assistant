"""Official no-sandbox DTOs without changing native StateBackend configuration."""
import asyncio
import os

import pytest
from deepagents.backends.utils import create_file_data

from agent import config, graph, registry, sessions
from agent.checkpointer import async_runtime
from agent.sandbox import CONFIG_ID


def test_sandbox_catalog_omits_state_and_preserves_legacy_detail_without_docker_label(authenticated_client):
    owner = os.environ['TEST_PLATFORM_USER']
    archived = registry.save_record('sandbox', {'id': 'state-backend', 'name': 'Legacy State',
        'sandbox_type': 'state'}, owner)
    registry.save_record('sandbox', {'id': 'legacy-docker', 'name': 'Saved Docker',
        'sandbox_type': 'docker'}, owner)
    catalog = authenticated_client.get('/api/v1/sandbox-configs').json['data']
    assert {item['id'] for item in catalog} == {CONFIG_ID, 'legacy-docker'}
    assert next(item for item in catalog if item['id'] == 'legacy-docker')['name'] == 'Saved Docker'
    detail = authenticated_client.get('/api/v1/sandbox-configs/state-backend').json['data']
    assert detail['name'] == '会话文件（无 Shell）'
    assert detail['sandbox_type'] == detail['config']['sandbox_type'] == ''
    assert registry.record('sandbox', 'state-backend', owner) == archived


@pytest.mark.parametrize('requested,internal,public', [
    ('', 'state-backend', ''), ('state-backend', 'state-backend', ''),
    (CONFIG_ID, CONFIG_ID, CONFIG_ID),
])
def test_agent_sandbox_dto_round_trip_keeps_official_empty_value_and_native_id(
        authenticated_client, requested, internal, public):
    client = authenticated_client
    owner = os.environ['TEST_PLATFORM_USER']
    assert config.DEFAULT_CONFIG['sandbox_config_id'] == 'state-backend'
    assert config.validate_config({'sandbox_config_id': requested})['sandbox_config_id'] == internal
    created = client.post('/api/v1/agents', json={'name': 'Native sandbox projection',
        'config': {'sandbox_config_id': requested}})
    assert created.status_code == 201
    agent = created.json['data']
    aid = agent['id']
    assert agent['config']['sandbox_config_id'] == public
    assert config.load_agent(aid, owner)['config']['sandbox_config_id'] == internal
    assert client.get('/api/v1/agents/' + aid).json['data']['config']['sandbox_config_id'] == public
    listed = client.get('/api/v1/agents').json['data']
    assert next(item for item in listed if item['id'] == aid)['config']['sandbox_config_id'] == public
    assert all(item['config']['sandbox_config_id'] == '' for item in listed if item['is_builtin'])
    updated = client.put('/api/v1/agents/' + aid, json={'config': agent['config']})
    assert updated.status_code == 200 and updated.json['data']['config']['sandbox_config_id'] == public
    copied = client.post('/api/v1/agents/' + aid + '/copy').json['data']
    assert copied['config']['sandbox_config_id'] == public
    assert registry.record('agent', aid, owner)['config']['sandbox_config_id'] == internal
    assert registry.record('agent', copied['id'], owner)['config']['sandbox_config_id'] == internal


def test_session_projection_keeps_native_config_and_checkpoint_unchanged(authenticated_client):
    owner = os.environ['TEST_PLATFORM_USER']
    native = config.validate_config({'sandbox_config_id': '', 'memory_enabled': False})
    selected = sessions.create_session(owner_id=owner, agent_config={'agent_id': 'builtin-smart-reasoning',
        'agent_config': native})
    sid = selected['id']
    before = sessions.get_session(sid, owner)

    async def exercise():
        async with async_runtime() as (saver, store):
            agent = await graph.build_agent(saver, store=store, api_key='', owner_id=owner,
                agent_id='builtin-smart-reasoning', role='admin', agent_config=native, load_tools=False)
            state_config = {'configurable': {'thread_id': sid}}
            await agent.aupdate_state(state_config, {'files': {'/preserved.txt': create_file_data('native-checkpoint')}})
            checkpoint = await agent.aget_state(state_config)
            for public in (selected, authenticated_client.get('/api/v1/sessions/' + sid).json['data'],
                           authenticated_client.get('/api/v1/sessions').json['data'][0]):
                assert public['agent_config']['agent_config']['sandbox_config_id'] == ''
                assert public['last_request_state']['agent_config']['sandbox_config_id'] == ''
            reread = await agent.aget_state(state_config)
            assert reread.config == checkpoint.config and reread.values == checkpoint.values
    asyncio.run(exercise())
    assert sessions.get_session(sid, owner) == before
    assert before['agent_config']['agent_config']['sandbox_config_id'] == 'state-backend'
    assert native['sandbox_config_id'] == config.DEFAULT_CONFIG['sandbox_config_id'] == 'state-backend'
