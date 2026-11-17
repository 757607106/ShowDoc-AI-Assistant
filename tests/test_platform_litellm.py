"""Real LiteLLM transports against local provider protocols and PostgreSQL checkpoints."""
import asyncio
import io
import json
import os

import pytest
from deepagents.backends.utils import file_data_to_string
from langchain_core.messages import AIMessageChunk, ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command
from starlette.applications import Starlette
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from agent import graph, registry
from agent.checkpointer import async_checkpointer
from agent.models import build_model_record, model_capabilities
from governance.store import StoreError
from tests.test_platform_mcp_runtime import serve
from webapi.weknora_adapter import StreamProjection, history


MODELS = [('openai', 'gpt-5.1'), ('aliyun', 'qwen-plus'), ('deepseek', 'deepseek-v4-pro'),
          ('anthropic', 'claude-sonnet-4-6'), ('gemini', 'gemini-2.5-flash')]
REASONING = 'fixture reasoning'
SIGNATURE = 'Zml4dHVyZS1zaWduYXR1cmU='


@pytest.fixture
def sdk_provider():
    calls = []
    state = {'tool': 'lookup', 'args': {'query': 'fixture'}}

    async def endpoint(request):
        payload = await request.json()
        calls.append({'path': request.url.path, 'payload': payload, 'headers': dict(request.headers)})
        raw = json.dumps(payload)
        finished = any(message.get('role') == 'tool' for message in payload.get('messages', [])) or any(
            key in raw for key in ('"tool_result"', '"functionResponse"', '"function_response"'))
        use_tool = bool(payload.get('tools')) and not finished
        name, args = state['tool'], state['args']
        if request.url.path.endswith('/responses'):
            output = [{'id': 'reasoning-item', 'type': 'reasoning', 'summary': [{'type': 'summary_text', 'text': REASONING}],
                       'encrypted_content': 'fixture-encrypted-reasoning'}, {'id': 'answer-item', 'type': 'message',
                       'status': 'completed', 'role': 'assistant', 'content': [{'type': 'output_text', 'text': 'fixture answer', 'annotations': []}]}]
            result = {'id': 'fixture-response', 'object': 'response', 'created_at': 1, 'status': 'completed',
                'model': payload['model'], 'output': output, 'usage': {'input_tokens': 5, 'output_tokens': 7,
                'total_tokens': 12, 'output_tokens_details': {'reasoning_tokens': 2}}}
            if not payload.get('stream'):
                return JSONResponse(result)
            events = [{'type': 'response.created', 'response': {**result, 'status': 'in_progress', 'output': [], 'usage': None}},
                {'type': 'response.output_item.added', 'output_index': 0, 'item': {**output[0], 'summary': []}},
                {'type': 'response.reasoning_summary_part.added', 'item_id': 'reasoning-item', 'output_index': 0, 'summary_index': 0, 'part': {'type': 'summary_text', 'text': ''}},
                {'type': 'response.reasoning_summary_text.delta', 'item_id': 'reasoning-item', 'output_index': 0, 'summary_index': 0, 'delta': REASONING},
                {'type': 'response.output_item.done', 'output_index': 0, 'item': output[0]},
                {'type': 'response.output_item.added', 'output_index': 1, 'item': {**output[1], 'content': []}},
                {'type': 'response.content_part.added', 'item_id': 'answer-item', 'output_index': 1, 'content_index': 0, 'part': {'type': 'output_text', 'text': '', 'annotations': []}},
                {'type': 'response.output_text.delta', 'item_id': 'answer-item', 'output_index': 1, 'content_index': 0, 'delta': 'fixture answer'},
                {'type': 'response.output_item.done', 'output_index': 1, 'item': output[1]}, {'type': 'response.completed', 'response': result}]
            return StreamingResponse(iter(['event: ' + event['type'] + '\ndata: ' + json.dumps(event) + '\n\n' for event in events]), media_type='text/event-stream')
        if request.url.path.endswith('/messages'):
            blocks = [{'type': 'thinking', 'thinking': REASONING, 'signature': SIGNATURE},
                      {'type': 'tool_use', 'id': 'fixture-call', 'name': name, 'input': args} if use_tool else {'type': 'text', 'text': 'fixture answer'}]
            if not payload.get('stream'):
                return JSONResponse({'id': 'fixture', 'type': 'message', 'role': 'assistant', 'model': payload['model'],
                    'content': blocks, 'stop_reason': 'tool_use' if use_tool else 'end_turn', 'usage': {'input_tokens': 5, 'output_tokens': 7}})
            chunks = [{'type': 'message_start', 'message': {'id': 'fixture', 'type': 'message', 'role': 'assistant',
                'model': payload['model'], 'content': [], 'usage': {'input_tokens': 5, 'output_tokens': 0}}}]
            chunks += [{'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'thinking', 'thinking': ''}},
                {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'thinking_delta', 'thinking': REASONING}},
                {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'signature_delta', 'signature': SIGNATURE}},
                {'type': 'content_block_stop', 'index': 0}]
            block = {'type': 'tool_use', 'id': 'fixture-call', 'name': name, 'input': {}} if use_tool else {'type': 'text', 'text': ''}
            chunks.append({'type': 'content_block_start', 'index': 1, 'content_block': block})
            if use_tool:
                arguments = json.dumps(args)
                chunks += [{'type': 'content_block_delta', 'index': 1, 'delta': {'type': 'input_json_delta', 'partial_json': part}}
                           for part in (arguments[:5], arguments[5:])]
            else:
                chunks.append({'type': 'content_block_delta', 'index': 1, 'delta': {'type': 'text_delta', 'text': 'fixture answer'}})
            chunks += [{'type': 'content_block_stop', 'index': 1}, {'type': 'message_delta',
                'delta': {'stop_reason': 'tool_use' if use_tool else 'end_turn', 'stop_sequence': None}, 'usage': {'output_tokens': 7}}, {'type': 'message_stop'}]
            return StreamingResponse(iter(['event: ' + chunk['type'] + '\ndata: ' + json.dumps(chunk) + '\n\n' for chunk in chunks]), media_type='text/event-stream')
        if ':generateContent' in request.url.path or ':streamGenerateContent' in request.url.path:
            parts = [{'text': REASONING, 'thought': True}, {'functionCall': {'name': name, 'args': args}, 'thoughtSignature': SIGNATURE}
                     if use_tool else {'text': 'fixture answer'}]
            result = {'candidates': [{'content': {'role': 'model', 'parts': parts}, 'finishReason': 'STOP', 'index': 0}],
                      'usageMetadata': {'promptTokenCount': 5, 'candidatesTokenCount': 7, 'totalTokenCount': 12, 'thoughtsTokenCount': 2}, 'responseId': 'fixture'}
            if ':streamGenerateContent' in request.url.path:
                return StreamingResponse(iter(['data: ' + json.dumps(result) + '\n\n']), media_type='text/event-stream')
            return JSONResponse(result)
        message = {'role': 'assistant', 'content': None if use_tool else 'fixture answer', 'reasoning_content': REASONING}
        if use_tool:
            message['tool_calls'] = [{'id': 'fixture-call', 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(args)}}]
        usage = {'prompt_tokens': 5, 'completion_tokens': 7, 'total_tokens': 12, 'completion_tokens_details': {'reasoning_tokens': 2}}
        root = {'id': 'fixture', 'model': payload['model'], 'created': 1}
        if not payload.get('stream'):
            return JSONResponse({**root, 'object': 'chat.completion', 'choices': [{'index': 0, 'message': message,
                'finish_reason': 'tool_calls' if use_tool else 'stop'}], 'usage': usage})
        deltas = [{'role': 'assistant', 'reasoning_content': REASONING}]
        if use_tool:
            arguments = json.dumps(args)
            deltas += [{'tool_calls': [{'index': 0, 'id': 'fixture-call', 'type': 'function', 'function': {'name': name, 'arguments': arguments[:5]}}]},
                       {'tool_calls': [{'index': 0, 'function': {'arguments': arguments[5:]}}]}]
        else:
            deltas.append({'content': 'fixture answer'})
        chunks = [{**root, 'object': 'chat.completion.chunk', 'choices': [{'index': 0, 'delta': delta, 'finish_reason': None}]} for delta in deltas]
        chunks += [{**root, 'object': 'chat.completion.chunk', 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'tool_calls' if use_tool else 'stop'}]},
                   {**root, 'object': 'chat.completion.chunk', 'choices': [], 'usage': usage}]
        return StreamingResponse(iter(['data: ' + json.dumps(chunk) + '\n\n' for chunk in chunks] + ['data: [DONE]\n\n']), media_type='text/event-stream')

    with serve(Starlette(routes=[Route('/{path:path}', endpoint, methods=['POST'])])) as base:
        yield base, calls, state


def model_record(provider, name, base):
    return {'name': name, 'type': 'KnowledgeQA', 'source': 'remote', 'parameters': {'provider': provider,
        'base_url': base if provider in ('anthropic', 'gemini') else base + '/v1', 'api_key': 'fixture-key'}}


@pytest.mark.parametrize('provider,name', MODELS)
def test_sdk_stream_thinking_tools_usage_and_native_replay(sdk_provider, provider, name):
    base, calls, _ = sdk_provider
    @tool
    def lookup(query: str) -> str:
        """Read a fixture source."""
        return query
    model = build_model_record(model_record(provider, name, base), {'reasoning_effort': 'auto', 'max_completion_tokens': 8192})
    async def run():
        chunks = [chunk async for chunk in model.bind_tools([lookup]).astream('Read a fixture')]
        full = chunks[0]
        for chunk in chunks[1:]:
            full += chunk
        assert full.additional_kwargs['reasoning_content'] == REASONING
        assert full.tool_calls[0]['args'] == {'query': 'fixture'}
        assert full.usage_metadata['total_tokens'] == 12
        answer = await model.bind_tools([lookup]).ainvoke([{'role': 'user', 'content': 'Read a fixture'}, full,
            ToolMessage(content='fixture result', tool_call_id=full.tool_calls[0]['id'])])
        assert answer.content == 'fixture answer'
    asyncio.run(run())
    first, replay = calls[0]['payload'], calls[-1]['payload']
    if provider == 'aliyun':
        assert first['enable_thinking'] is True
    elif provider == 'anthropic':
        assert first['thinking']['type'] in ('enabled', 'adaptive')
        assert SIGNATURE in json.dumps(replay)
    elif provider == 'gemini':
        assert first['generationConfig']['thinkingConfig']['includeThoughts'] is True
        assert SIGNATURE in json.dumps(replay)
    elif provider == 'deepseek':
        assert first['thinking'] == {'type': 'enabled'}
        assert 'reasoning_effort' not in first
    else:
        assert first['reasoning_effort'] == 'medium'
    if provider in ('aliyun', 'deepseek', 'openai'):
        assert any(message.get('reasoning_content') == REASONING for message in replay['messages'])


@pytest.mark.parametrize('provider,name', MODELS)
def test_sdk_postgres_approval_resume_rebuilds_graph_without_losing_model_metadata(sdk_provider, provider, name):
    base, calls, state = sdk_provider
    state.update(tool='write_file', args={'file_path': '/sdk.txt', 'content': 'SDK file'})
    owner = os.environ['TEST_PLATFORM_USER']
    saved = registry.save_model(model_record(provider, name, base), owner)
    config = {'model_id': saved['id'], 'reasoning_effort': 'auto', 'max_completion_tokens': 8192,
        'allowed_tools': [], 'mcp_selection_mode': 'none', 'memory_enabled': False, 'access_level': 'confirm'}
    thread = {'configurable': {'thread_id': 'sdk-resume'}}
    async def build(saver):
        return await graph.build_agent(saver, api_key='', owner_id=owner, role='admin', agent_config=config)
    async def run():
        async with async_checkpointer() as saver:
            agent = await build(saver)
            chunks = [part async for part in agent.astream({'messages': [{'role': 'user', 'content': 'Write the fixture file'}]},
                thread, stream_mode=['messages', 'updates', 'values'], version='v2', durability='sync')]
            waiting = await agent.aget_state(thread)
            assert len(waiting.interrupts) == 1
            assert '/sdk.txt' not in waiting.values.get('files', {})
            interrupt_id = waiting.interrupts[0].id
            message = next(message for message in waiting.values['messages'] if getattr(message, 'tool_calls', []))
            call_id = message.tool_calls[0]['id']
            assert message.additional_kwargs['reasoning_content'] == REASONING
            projection = StreamProjection('sdk-resume', 'assistant')
            events = [event for part in chunks for event in projection.feed(part)]
            assert any(event['response_type'] == 'thinking' and REASONING in event['content'] for event in events)
        assert len(calls) == 1
        async with async_checkpointer() as saver:
            agent = await build(saver)
            before = await agent.aget_state(thread)
            assert before.interrupts[0].id == interrupt_id
            async for _ in agent.astream(Command(resume={interrupt_id: {'decisions': [{'type': 'approve'}]}}),
                    thread, stream_mode=['messages', 'updates', 'values'], version='v2', durability='sync'):
                pass
            complete = await agent.aget_state(thread)
            assert not complete.interrupts and not complete.next
            assert file_data_to_string(complete.values['files']['/sdk.txt']) == 'SDK file'
            assert len([m for m in complete.values['messages'] if m.type == 'tool' and m.tool_call_id == call_id]) == 1
            assert complete.values['messages'][-1].content == 'fixture answer'
        async with async_checkpointer() as saver:
            reader = await graph.build_agent(saver, api_key='', owner_id=owner, role='admin', agent_config=config, load_tools=False)
            reloaded = await reader.aget_state(thread)
            rows = history(reloaded, 'sdk-resume')
            assert rows[-1]['agent_steps'][0]['reasoning_content'] == REASONING
            assert rows[-1]['content'] == 'fixture answer'
        assert len(calls) == 2
        if provider in ('anthropic', 'gemini'):
            assert SIGNATURE in json.dumps(calls[-1]['payload'])
    asyncio.run(run())


def test_capabilities_disable_qwen_max_and_reject_unsupported_effort():
    saved = model_record('aliyun', 'qwen-max', 'https://fixture.invalid')
    assert model_capabilities(saved)['thinking_levels'] == []
    with pytest.raises(StoreError, match='未声明支持'):
        build_model_record(saved, {'reasoning_effort': 'auto'})
    saved['name'] = 'qwen-plus'
    with pytest.raises(StoreError, match='不支持此思考强度'):
        build_model_record(saved, {'reasoning_effort': 'high'})


def test_standard_reasoning_blocks_project_to_stream_and_history_without_signatures():
    message = AIMessageChunk(id='reasoning', content=[{'type': 'reasoning', 'reasoning': REASONING, 'signature': SIGNATURE},
        {'type': 'text', 'text': 'answer'}])
    events = StreamProjection('session', 'assistant').feed({'type': 'messages', 'ns': (), 'data': (message, {'langgraph_node': 'model'})})
    assert [(e['response_type'], e['content']) for e in events] == [('thinking', REASONING), ('answer', 'answer')]
    assert SIGNATURE not in json.dumps(events)


@pytest.mark.parametrize('provider,name', MODELS)
def test_model_editor_catalog_connection_and_multipart_debug_match_frontend(authenticated_client, sdk_provider, provider, name):
    base, calls, _ = sdk_provider
    client = authenticated_client
    available = client.get('/api/v1/models/providers?model_type=chat').json['data']
    assert provider in {item['value'] for item in available}
    assert {item['value'] for item in client.get('/api/v1/models/providers?model_type=embedding').json['data']} == {'generic'}
    draft = model_record(provider, name, base)
    created = client.post('/api/v1/models', json=draft)
    assert created.status_code == 200, created.json
    saved = created.json['data']
    identifier = saved['id']
    assert saved['capabilities']['reasoning'] is True
    assert saved['capabilities']['thinking_format'] == {'openai': 'openai', 'aliyun': 'enable-thinking',
        'deepseek': 'thinking-type', 'anthropic': 'thinking.adaptive', 'gemini': 'thinkingConfig.budget'}[provider]
    assert 'fixture-key' not in json.dumps(saved)
    preview = client.post('/api/v1/models/catalog/resolve', json={'provider': provider, 'model': name,
        'base_url': draft['parameters']['base_url'], 'model_type': 'chat', 'api': '', 'spec': {}})
    assert preview.status_code == 200 and preview.json['data']['capabilities'] == saved['capabilities']
    checked = client.post('/api/v1/initialization/remote/check', json={'modelId': identifier})
    assert checked.status_code == 200 and checked.json['data']['available'], checked.json
    response = client.post(f'/api/v1/models/{identifier}/debug', data={'input': 'Debug this fixture',
        'options': json.dumps({'system_prompt': 'Fixture system prompt', 'reasoning_effort': 'auto', 'thinking': True,
            'max_tokens': 8192, 'temperature': 0.4, 'top_p': 0.9})},
        content_type='multipart/form-data')
    assert response.status_code == 200, response.json
    result = response.json['data']
    assert result['ok'], result
    assert result['observations']['reasoning_returned'] is True
    assert result['observations']['reasoning_characters'] == len(REASONING)
    assert result['raw_response']['usage_metadata']['total_tokens'] == 12
    assert result['content'] == 'fixture answer'
    assert 'Fixture system prompt' in json.dumps(calls[-1]['payload'])
    assert 'fixture-key' not in json.dumps(result)
    if provider == 'aliyun':
        assert calls[-1]['payload']['temperature'] == 0.4 and calls[-1]['payload']['top_p'] == 0.9


@pytest.mark.parametrize('provider,name', MODELS)
def test_explicit_off_reaches_provider(sdk_provider, provider, name):
    base, calls, _ = sdk_provider
    model = build_model_record(model_record(provider, name, base), {'reasoning_effort': 'off', 'max_completion_tokens': 8192})
    asyncio.run(model.ainvoke('Reply briefly'))
    payload = calls[-1]['payload']
    if provider == 'aliyun':
        assert payload['enable_thinking'] is False
    elif provider == 'deepseek':
        assert payload['thinking']['type'] == 'disabled'
    elif provider == 'anthropic':
        assert 'thinking' not in payload or payload['thinking']['type'] == 'disabled'
    elif provider == 'gemini':
        assert payload['generationConfig']['thinkingConfig']['thinkingBudget'] == 0
    else:
        assert payload['reasoning_effort'] == 'none'


def test_debug_omits_sampling_for_always_on_reasoning_model(authenticated_client, sdk_provider):
    base, calls, _ = sdk_provider
    saved = authenticated_client.post('/api/v1/models', json=model_record('openai', 'o3', base)).json['data']
    response = authenticated_client.post(f"/api/v1/models/{saved['id']}/debug", json={
        'input': 'Reply briefly', 'options': {'max_tokens': 128, 'temperature': 0.7, 'top_p': 0.9}})
    assert response.status_code == 200 and response.json['data']['ok'], response.json
    assert 'temperature' not in calls[-1]['payload'] and 'top_p' not in calls[-1]['payload']
    assert response.json['data']['request']['effective_options']['temperature'] is None


def test_debug_picture_and_headers_use_saved_owner_credentials(authenticated_client, sdk_provider, monkeypatch):
    from PIL import Image
    base, calls, _ = sdk_provider
    draft = model_record('openai', 'gpt-4.1', base)
    draft['type'] = 'VLLM'
    draft['parameters']['custom_headers'] = {'X-Fixture': 'custom', 'X-Api-Key': 'must-not-override'}
    identifier = authenticated_client.post('/api/v1/models', json=draft).json['data']['id']
    png = io.BytesIO()
    Image.new('RGB', (1, 1)).save(png, format='PNG')
    png_bytes = png.getvalue()
    parsed = []
    def parser(name, content, *, image=False):
        parsed.append((name, content, image))
        return {'mime': 'image/png'}
    monkeypatch.setattr('webapi.chat_resources._attachment_parser_result', parser)
    png.seek(0)
    result = authenticated_client.post(f'/api/v1/models/{identifier}/debug', data={'input': 'Describe',
        'options': json.dumps({'reasoning_effort': 'off', 'max_tokens': 128}), 'file': (png, 'fixture.png')})
    assert result.status_code == 200 and result.json['data']['ok'], result.json
    assert calls[-1]['headers']['authorization'] == 'Bearer fixture-key'
    assert calls[-1]['headers']['x-fixture'] == 'custom'
    assert 'x-api-key' not in calls[-1]['headers']
    assert calls[-1]['payload']['messages'][-1]['content'][1]['image_url']['url'].startswith('data:image/png;base64,')
    assert parsed == [('fixture.png', png_bytes, True)]


@pytest.mark.parametrize('failure,status', [('malformed', 400), ('unavailable', 503)])
def test_debug_picture_parser_failures_do_not_call_model(authenticated_client, sdk_provider, monkeypatch, failure, status):
    from opensandbox.exceptions import SandboxException
    base, calls, _ = sdk_provider
    draft = model_record('openai', 'gpt-4.1', base)
    draft['type'] = 'VLLM'
    identifier = authenticated_client.post('/api/v1/models', json=draft).json['data']['id']
    def parser(*args, **kwargs):
        if failure == 'malformed':
            raise StoreError('隔离附件解析失败，请检查文件格式', 422)
        raise SandboxException('fixture parser unavailable')
    monkeypatch.setattr('webapi.chat_resources._attachment_parser_result', parser)
    response = authenticated_client.post(f'/api/v1/models/{identifier}/debug', data={
        'input': 'Describe', 'file': (io.BytesIO(b'untrusted image'), 'fixture.png')})
    assert response.status_code == status, response.json
    assert calls == []


def test_catalog_preview_resolves_draft_limits_with_same_precedence_as_runtime(authenticated_client):
    client = authenticated_client
    draft = {'provider': 'generic', 'model': 'unknown-local-model', 'model_type': 'chat',
        'context_window': 32768, 'max_output_tokens': 4096, 'spec': {}}
    result = client.post('/api/v1/models/catalog/resolve', json=draft)
    assert result.status_code == 200
    assert result.json['data']['capabilities']['context_window'] == 32768
    assert result.json['data']['capabilities']['max_output_tokens'] == 4096
    draft['spec'] = {'context_window': 65536, 'max_output_tokens': 8192}
    result = client.post('/api/v1/models/catalog/resolve', json=draft)
    assert result.status_code == 200
    assert result.json['data']['capabilities']['context_window'] == 65536
    assert result.json['data']['capabilities']['max_output_tokens'] == 8192
    draft.update(context_window=-1)
    assert client.post('/api/v1/models/catalog/resolve', json=draft).status_code == 400
    draft.update(context_window=0, max_output_tokens=0, spec={})
    result = client.post('/api/v1/models/catalog/resolve', json=draft)
    assert result.status_code == 200 and result.json['data']['capabilities']['context_window'] is None


def test_frontend_responses_protocol_streams_summaries_and_replays_encrypted_items(sdk_provider):
    base, calls, _ = sdk_provider
    saved = model_record('openai', 'gpt-5.1', base)
    saved['parameters']['extra_config'] = {'api': 'openai-responses'}
    assert model_capabilities(saved)['thinking_format'] == 'reasoning.effort'
    model = build_model_record(saved, {'reasoning_effort': 'auto', 'max_completion_tokens': 8192})
    async def run():
        chunks = [chunk async for chunk in model.astream('Explain the fixture')]
        full = chunks[0]
        for chunk in chunks[1:]:
            full += chunk
        assert full.content == 'fixture answer'
        assert full.additional_kwargs['reasoning_content'] == REASONING
        assert full.additional_kwargs['reasoning_items'][0]['encrypted_content'] == 'fixture-encrypted-reasoning'
        await model.ainvoke([{'role': 'user', 'content': 'Explain the fixture'}, full, {'role': 'user', 'content': 'Continue'}])
    asyncio.run(run())
    assert calls[0]['path'] == '/v1/responses'
    assert calls[0]['payload']['reasoning'] == {'effort': 'medium', 'summary': 'auto'}
    assert calls[0]['payload']['store'] is False
    assert 'fixture-encrypted-reasoning' in json.dumps(calls[-1]['payload'])
