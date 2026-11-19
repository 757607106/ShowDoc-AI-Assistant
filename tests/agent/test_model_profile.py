"""Pinned SDK and native summarization contracts, using only local HTTP."""
import asyncio
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from deepagents.backends import StateBackend
from deepagents.middleware.summarization import compute_summarization_defaults, create_summarization_middleware
from flask import Flask
from langchain.agents.middleware.types import ModelRequest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from agent import graph, registry
from agent.config import validate_config
from agent.models import build_model_record, describe_model, model_capabilities
from governance.store import StoreError
from webapi.runtime.runtime_settings import runtime_settings_bp


def record(base='http://127.0.0.1:9', **parameters):
    return {'name': 'local-profile-fixture', 'type': 'KnowledgeQA', 'source': 'remote',
        'parameters': {'provider': 'generic', 'base_url': base + '/v1', 'api_key': 'unused', **parameters}}


def test_profile_uses_effective_limits_without_overwriting_editor_values():
    saved = record(context_window=32768, max_output_tokens=4096,
        spec={'context_window': 65536, 'max_output_tokens': 8192})
    model = build_model_record(saved, {'max_completion_tokens': 16384})
    assert model.profile == {'max_input_tokens': 65536, 'max_output_tokens': 8192}
    assert model.max_tokens == 8192
    described = describe_model(saved)
    assert described['parameters']['context_window'] == saved['parameters']['context_window'] == 32768
    assert described['parameters']['max_output_tokens'] == 4096
    assert described['capabilities']['context_window'] == 65536
    saved = record()
    saved['name'] = 'gpt-4.1'
    saved['parameters']['provider'] = 'openai'
    caps = model_capabilities(saved)
    assert caps['cataloged'] and caps['context_window'] == 1047576
    model = build_model_record(saved, {})
    assert model.profile == {'max_input_tokens': 1047576, 'max_output_tokens': caps['max_output_tokens']}
    assert compute_summarization_defaults(model)['trigger'] == ('fraction', 0.85)
    assert 'context_window' not in describe_model(saved)['parameters']


def test_unknown_model_and_deployment_alias_do_not_invent_a_window():
    saved = record(extra_config={'remote_model_name': 'gpt-4.1'})
    model = build_model_record(saved, {})
    assert 'context_window' not in model_capabilities(saved)
    assert model.profile is None
    assert compute_summarization_defaults(model)['trigger'] == ('tokens', 170000)
    model = build_model_record(record(max_output_tokens=4096), {})
    assert model.profile == {'max_output_tokens': 4096}
    assert compute_summarization_defaults(model)['trigger'] == ('tokens', 170000)


@pytest.mark.parametrize('name,output', [('qwen-plus-2025-01-25', None), ('qwen-plus-2025-04-28', None)])
@pytest.mark.parametrize('limits,context', [({}, None), ({'context_window': 0}, None),
    ({'context_window': 131072}, 131072),
    ({'context_window': 65536, 'spec': {'context_window': 131072}}, 131072)])
def test_catalog_input_limit_is_not_a_total_context_window(name, output, limits, context):
    # These snapshots match a family rule with no declared context or output cap.
    saved = record(provider='aliyun', **limits)
    saved['name'] = name
    caps = model_capabilities(saved)
    assert caps['cataloged'] and caps.get('context_window') == context
    assert caps.get('max_output_tokens') == output
    assert describe_model(saved)['capabilities'].get('context_window') == context
    app = Flask(__name__)
    app.register_blueprint(runtime_settings_bp)
    response = app.test_client().post('/api/v1/models/catalog/resolve', json={
        'provider': 'aliyun', 'model': name, **limits})
    assert response.status_code == 200
    assert response.json['data']['capabilities'] == caps
    model = build_model_record(saved, {'max_completion_tokens': 4096})
    assert model.profile == ({'max_input_tokens': context} if context else None)
    assert model.max_tokens == 4096
    middleware = create_summarization_middleware(model, StateBackend())
    request = ModelRequest(model=model, messages=[])
    assert middleware._input_budget(request) == (120422 if context else None)
    assert compute_summarization_defaults(model)['trigger'] == (
        ('fraction', 0.85) if context else ('tokens', 170000))


@pytest.mark.parametrize('settings,expected', [({}, 120), ({'llm_call_timeout': 0}, 120),
    ({'llm_call_timeout': 180}, 180), ({'llm_call_timeout': 7}, 7)])
def test_builder_timeout_defaults_preserve_explicit_values(settings, expected):
    assert build_model_record(record(), settings).request_timeout == expected


def test_null_timeout_remains_invalid():
    with pytest.raises(StoreError, match='llm_call_timeout'):
        validate_config({'llm_call_timeout': None})


@pytest.fixture
def harness(monkeypatch):
    async def empty(*args, **kwargs):
        return []
    monkeypatch.setattr(graph, 'load_knowledge_mcp_tools', empty)
    monkeypatch.setattr(graph, 'make_governance_tools', lambda *args: [])
    monkeypatch.setattr(registry, 'mcp_tools', empty)
    async def build(saved, **config):
        monkeypatch.setattr(registry, 'model_config', lambda *args, **kwargs: saved)
        return await graph.build_agent(InMemorySaver(), api_key='unused', owner_id='fixture-owner', role='admin',
            agent_config={'max_iterations': 2, 'memory_enabled': False, 'allowed_tools': [],
                'mcp_selection_mode': 'none', 'llm_call_timeout': 3, 'max_completion_tokens': 1024, **config})
    return build


def test_main_and_default_subagent_use_native_profile_and_exact_output_reservation(harness, monkeypatch):
    import deepagents.graph as native_graph
    middlewares = []
    original = native_graph.create_summarization_middleware
    def capture(model, backend, **kwargs):
        middleware = original(model, backend, **kwargs)
        middlewares.append(middleware)
        return middleware
    monkeypatch.setattr(native_graph, 'create_summarization_middleware', capture)
    asyncio.run(harness(record(context_window=32768, max_output_tokens=8192), max_completion_tokens=4096))
    assert len(middlewares) == 2
    for middleware in middlewares:
        assert middleware.model.profile == {'max_input_tokens': 32768, 'max_output_tokens': 8192}
        assert middleware._get_profile_limits() == 32768
        assert compute_summarization_defaults(middleware.model)['trigger'] == ('fraction', 0.85)
        assert middleware._input_budget(ModelRequest(model=middleware.model, messages=[])) == 27033
        assert middleware._input_budget(ModelRequest(model=middleware.model, messages=[],
            model_settings={'max_tokens': 2048, 'max_completion_tokens': 4096})) == 27033
    default_model = build_model_record(record(context_window=32768), {})
    assert default_model.max_tokens == 24576
    assert middlewares[0]._input_budget(ModelRequest(model=default_model, messages=[])) == 6553


@pytest.fixture
def provider():
    state = {'mode': 'history', 'calls': []}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            messages = body['messages']
            text = '\n'.join(str(item['content']) for item in messages)
            summary = len(messages) == 1 and 'summariz' in text.lower()
            rejected = (state['mode'] == 'history' and len(messages) > 10) or (
                state['mode'] == 'tool' and any(item['role'] == 'tool' and len(item['content']) > 2000 for item in messages))
            state['calls'].append({'body': body, 'summary': summary, 'rejected': rejected})
            if state['mode'] in ('steady', 'idle'):
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Connection', 'close')
                self.end_headers()
                def emit(content=None, finish=None):
                    chunk = {'id': 'fixture', 'object': 'chat.completion.chunk', 'created': 0,
                        'model': 'fixture', 'choices': [{'index': 0,
                            'delta': {'content': content} if content else {}, 'finish_reason': finish}]}
                    self.wfile.write(('data: ' + json.dumps(chunk) + '\n\n').encode())
                    self.wfile.flush()
                try:
                    emit('a')
                    for _ in range(7 if state['mode'] == 'steady' else 1):
                        time.sleep(.2 if state['mode'] == 'steady' else 1.4)
                        emit('b')
                    emit(finish='stop')
                    self.wfile.write(b'data: [DONE]\n\n')
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return
            if rejected:
                payload = {'error': {'message': 'maximum context length: context_length_exceeded',
                    'type': 'invalid_request_error', 'param': 'messages', 'code': 'context_length_exceeded'}}
            else:
                payload = {'id': 'fixture', 'object': 'chat.completion', 'created': 0, 'model': 'fixture',
                    'choices': [{'index': 0, 'message': {'role': 'assistant',
                        'content': 'summary text' if summary else 'HTTP recovered'}, 'finish_reason': 'stop'}],
                    'usage': {'prompt_tokens': 10, 'completion_tokens': 3, 'total_tokens': 13}}
            data = json.dumps(payload).encode()
            self.send_response(400 if rejected else 200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}', state
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_native_http_overflow_summarizes_without_replacing_raw_history(harness, provider, monkeypatch):
    from agent.time_travel import ancestry
    from webapi.weknora.artifacts import collect
    monkeypatch.setattr('webapi.weknora.artifacts.deleted_for', lambda *args: {})
    base, state = provider
    messages = []
    for i in range(10):
        messages.extend([HumanMessage(content=f'Q{i} ' + 'x' * 4000), AIMessage(content=f'A{i} ' + 'y' * 4000)])
    messages.append(HumanMessage(content='latest'))
    async def run():
        agent = await harness(record(base, context_window=32768))
        config = {'configurable': {'thread_id': 'overflow-history'}}
        result = await agent.ainvoke({'messages': messages}, config)
        snapshot = await agent.aget_state(config)
        assert result['messages'][-1].content == 'HTTP recovered'
        assert snapshot.values['_summarization_event']
        assert [m.content for m in snapshot.values['messages'][:-1]] == [m.content for m in messages]
        assert any(path.startswith('/conversation_history/') for path in snapshot.values['files'])
        artifacts = collect([state async for state in ancestry(agent, snapshot)], 'fixture-owner', 'overflow-history')
        assert artifacts and not any(artifacts.values())
    asyncio.run(run())
    assert any(call['rejected'] for call in state['calls'])
    assert any(call['summary'] for call in state['calls'])
    assert all('profile' not in call['body'] for call in state['calls'])


def test_native_http_overflow_offloads_tool_content_and_preserves_artifact(harness, provider):
    base, state = provider
    state['mode'] = 'tool'
    artifact = {'structured_content': {'results': [{'chunk_id': 'actual-chunk', 'content': 'source ' * 1000}]}}
    original = ToolMessage(content=json.dumps(artifact['structured_content']), id='source-result',
        tool_call_id='source-call', name='knowledge.search', artifact=artifact)
    messages = [HumanMessage(content='Search'), AIMessage(content='', tool_calls=[{
        'name': 'knowledge.search', 'args': {'query': 'source'}, 'id': 'source-call', 'type': 'tool_call'}]), original]
    async def run():
        agent = await harness(record(base, context_window=32768))
        config = {'configurable': {'thread_id': 'overflow-tool'}}
        result = await agent.ainvoke({'messages': messages}, config)
        snapshot = await agent.aget_state(config)
        assert result['messages'][-1].content == 'HTTP recovered'
        after = next(m for m in snapshot.values['messages'] if m.id == original.id)
        assert after.artifact == artifact
        assert len(after.content) < len(original.content)
        assert snapshot.values['files']
    asyncio.run(run())
    assert state['calls'][0]['rejected'] and not state['calls'][-1]['rejected']


def test_sdk_stream_timeout_measures_idle_gap_not_total_turn(provider):
    base, state = provider
    async def run(mode):
        state['mode'] = mode
        model = build_model_record(record(base), {'llm_call_timeout': 1, 'max_completion_tokens': 16})
        model.max_retries = 0
        content = ''
        start = time.monotonic()
        async for chunk in model.astream('fixture'):
            content += chunk.text
        return content, time.monotonic() - start
    content, elapsed = asyncio.run(run('steady'))
    assert content == 'a' + 'b' * 7 and elapsed > 1
    import httpx
    with pytest.raises(httpx.ReadTimeout):
        asyncio.run(run('idle'))
