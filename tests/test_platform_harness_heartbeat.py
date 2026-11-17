"""WeKnora's JSON heartbeat keeps a slow native SDK stream connected."""
import asyncio
import json
import os
import threading
from contextlib import asynccontextmanager
from types import SimpleNamespace

import httpx
import litellm
from sse_starlette.sse import EventSourceResponse

from agent import registry, sessions
from tests.test_platform_litellm import model_record, sdk_provider
from tests.test_platform_mcp_runtime import serve


def test_json_heartbeat_survives_wait_for_first_model_chunk(authenticated_client, sdk_provider, monkeypatch):
    import app as app_module
    from asgi import create_app
    from webapi import harness

    base, calls, state = sdk_provider
    state.update(tool='ls', args={'path': '/'})
    owner = os.environ['TEST_PLATFORM_USER']
    saved = registry.save_model(model_record('aliyun', 'qwen-plus', base), owner)
    selected = sessions.create_session('Slow SDK heartbeat', owner)
    config = {'model_id': saved['id'], 'reasoning_effort': 'auto', 'allowed_tools': [],
        'mcp_selection_mode': 'none', 'memory_enabled': False, 'access_level': 'read_only'}
    monkeypatch.setenv('FLASK_SECRET_KEY', app_module.app.secret_key)
    monkeypatch.setattr(harness, '_prepare', lambda *args: {'agent_config': config, 'knowledge_base_ids': []})
    monkeypatch.setattr(harness, 'client_for_user', lambda *args: SimpleNamespace(api_key=''))
    monkeypatch.setattr(EventSourceResponse, 'DEFAULT_PING_INTERVAL', .02)
    native_runtime = harness.async_runtime
    cleanup_started = threading.Event()

    @asynccontextmanager
    async def slow_cleanup():
        async with native_runtime() as runtime:
            yield runtime
            cleanup_started.set()
            await asyncio.sleep(.1)

    monkeypatch.setattr(harness, 'async_runtime', slow_cleanup)
    native_completion = litellm.acompletion
    waiting = threading.Event()

    async def slow_completion(*args, **kwargs):
        waiting.set()
        try:
            await asyncio.sleep(.2)
            return await native_completion(*args, **kwargs)
        finally:
            waiting.clear()

    monkeypatch.setattr(litellm, 'acompletion', slow_completion)
    events, heartbeats_during_wait = [], 0
    headers = {'Authorization': authenticated_client.environ_base['HTTP_AUTHORIZATION']}
    with serve(create_app(app_module.app)) as platform, httpx.Client(timeout=10) as client:
        with client.stream('POST', platform + '/api/v1/agent-chat/' + selected['id'],
                           headers=headers, json={'query': 'Read the fixture directory'}) as response:
            assert response.status_code == 200
            event, data = '', []
            for line in response.iter_lines():
                if line.startswith('event: '):
                    event = line[7:]
                elif line.startswith('data: '):
                    data.append(line[6:])
                elif not line:
                    assert event == 'message', 'The frontend cannot JSON-parse comment-only pings'
                    payload = json.loads('\n'.join(data))
                    events.append(payload)
                    if payload['response_type'] == 'heartbeat' and waiting.is_set():
                        heartbeats_during_wait += 1
                    event, data = '', []
    kinds = [event['response_type'] for event in events]
    assert cleanup_started.is_set()
    assert heartbeats_during_wait > 0
    assert kinds.index('heartbeat') < kinds.index('thinking')
    assert any(event['response_type'] == 'answer' and event['content'] == 'fixture answer' for event in events)
    assert kinds[-1] == 'complete' and 'error' not in kinds
    assert len(calls) == 2
