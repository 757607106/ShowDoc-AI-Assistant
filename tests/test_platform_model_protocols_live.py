"""Opt-in real Qwen acceptance; all files and checkpoints stay in the test schema."""
import asyncio
import json
import os
from pathlib import Path

import pytest
from deepagents.backends.utils import file_data_to_string
from langgraph.types import Command

from agent import graph, registry
from agent.checkpointer import async_checkpointer


@pytest.mark.skipif(os.getenv('RUN_LLM_ACCEPTANCE') != '1', reason='Set RUN_LLM_ACCEPTANCE=1 to call the configured provider')
def test_live_qwen_sdk_thinking_tool_approval_and_postgres_recovery(authenticated_client):
    owner = os.environ['TEST_PLATFORM_USER']
    source = registry.model_config('agent-main', owner)
    if not source['parameters'].get('api_key'):
        pytest.skip('The environment model has no API key')
    source.update(name='qwen-plus', type='KnowledgeQA')
    source['parameters'].update(model_name='qwen-plus', provider='aliyun')
    saved = registry.save_model(source, owner)
    config = {'model_id': saved['id'], 'reasoning_effort': 'auto', 'allowed_tools': [], 'mcp_selection_mode': 'none',
        'memory_enabled': False, 'access_level': 'confirm', 'max_completion_tokens': 8192, 'max_iterations': 5, 'llm_call_timeout': 45,
        'system_prompt': '这是工具调用验收。严格按用户指定路径和内容调用一次 write_file，不规划、不委派、不追问。工具完成后只回复 LIVE_SDK_DONE。'}
    thread = {'configurable': {'thread_id': 'live-model-protocol'}}
    report = {'model': 'qwen-plus', 'client': 'CompatibleChat', 'mocked_provider': False}
    async def build(saver):
        return await graph.build_agent(saver, api_key='', owner_id=owner, role='admin', agent_config=config)
    async def run():
        async with async_checkpointer() as saver:
            agent = await build(saver)
            async for _ in agent.astream({'messages': [{'role': 'user', 'content':
                '请调用 write_file，file_path=/model-protocol-live.txt，content=LIVE_SDK_OK；完成后只回复 LIVE_SDK_DONE。'}]},
                    thread, stream_mode=['messages', 'updates', 'values'], version='v2', durability='sync'):
                pass
            waiting = await agent.aget_state(thread)
            assert len(waiting.interrupts) == 1
            assert '/model-protocol-live.txt' not in waiting.values.get('files', {})
            message = next(m for m in waiting.values['messages'] if getattr(m, 'tool_calls', []))
            assert message.tool_calls[0]['name'] == 'write_file'
            assert message.tool_calls[0]['args'] == {'file_path': '/model-protocol-live.txt', 'content': 'LIVE_SDK_OK'}
            reasoning = message.additional_kwargs.get('reasoning_content', '')
            assert reasoning, 'The real provider did not return visible reasoning'
            interrupt_id = waiting.interrupts[0].id
            call_id = message.tool_calls[0]['id']
            report.update(reasoning_characters=len(reasoning), approval_before_write=True)
        async with async_checkpointer() as saver:
            agent = await build(saver)
            restored = await agent.aget_state(thread)
            assert restored.interrupts[0].id == interrupt_id
            async for _ in agent.astream(Command(resume={interrupt_id: {'decisions': [{'type': 'approve'}]}}),
                    thread, stream_mode=['messages', 'updates', 'values'], version='v2', durability='sync'):
                pass
            final = await agent.aget_state(thread)
            assert not final.interrupts and not final.next
            assert file_data_to_string(final.values['files']['/model-protocol-live.txt']) == 'LIVE_SDK_OK'
            assert len([m for m in final.values['messages'] if m.type == 'tool' and m.tool_call_id == call_id]) == 1
            assert 'LIVE_SDK_DONE' in final.values['messages'][-1].content
            report.update(restored_and_approved=True, single_tool_result=True, usage=final.values['messages'][-1].usage_metadata)
    try:
        asyncio.run(run())
    except Exception as exc:
        pytest.fail(f'Real provider acceptance failed: {type(exc).__name__}', pytrace=False)
    target = Path('output/verification/model-protocol-20261115/live-qwen.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
