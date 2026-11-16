"""Opt-in real provider/native Agent/PostgreSQL acceptance in an existing isolated schema.

The caller supplies the shared private configuration with --config.
No HTTP service, ContextDB request, production mutation or fake model is used.
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def exercise(owner, created):
    from agent import graph, sessions
    from agent.checkpointer import async_runtime
    from agent.config import validate_config
    from deepagents.backends.utils import file_data_to_string
    from governance.database import connection
    from langgraph.types import Command

    saved = validate_config({'model_id': 'agent-main', 'allowed_tools': [],
        'mcp_selection_mode': 'none', 'memory_enabled': False, 'access_level': 'confirm',
        'temperature': 0, 'max_completion_tokens': 256, 'max_iterations': 4,
        'llm_call_timeout': 45, 'reasoning_effort': 'off',
        'system_prompt': '这是原生文件工具验收。写文件时只调用一次 write_file，严格使用用户指定路径和内容。'
                         '不要规划、委派、追问或读取知识库。工具写入成功后只回复 REAL_NATIVE_FILE_OK。'})
    selected = sessions.create_session('Real provider native acceptance', owner_id=owner,
        agent_config={'runtime': 'deepagents', 'agent_id': 'builtin-smart-reasoning',
                      'agent_config': saved})
    sid = selected['id']
    created.append(sid)
    config = {'configurable': {'thread_id': sid}}
    report = {'session_id': sid, 'model': os.environ.get('AGENT_MAIN_MODEL', 'qwen-max')}

    async def build(saver, store, **kwargs):
        return await graph.build_agent(saver, store=store, api_key='', owner_id=owner,
            agent_id='builtin-smart-reasoning', session_id=sid, role='admin',
            agent_config=saved, **kwargs)

    async with async_runtime() as (saver, store):
        agent = await build(saver, store)
        first = await agent.ainvoke({'messages': [{'role': 'user',
            'content': '本条只回复 REAL_NATIVE_CHAT_OK，不执行工具。'}]}, config, durability='sync')
        answer = first['messages'][-1]
        assert answer.type == 'ai' and 'REAL_NATIVE_CHAT_OK' in answer.content
        assert answer.usage_metadata and answer.usage_metadata['total_tokens'] > 0
        report['chat'] = {'content': answer.content, 'usage': answer.usage_metadata}
        await agent.ainvoke({'messages': [{'role': 'user', 'content':
            '请立即调用 write_file：file_path=/real-acceptance.txt，content=REAL_NATIVE_FILE_PAYLOAD。'
            '必须通过工具写入，不要仅给出示例。写入成功后只回复 REAL_NATIVE_FILE_OK。'}]},
            config, durability='sync')
        waiting = await agent.aget_state(config)
        assert len(waiting.interrupts) == 1
        interrupt = waiting.interrupts[0]
        actions = interrupt.value['action_requests']
        assert len(actions) == 1 and actions[0]['name'] == 'write_file'
        assert actions[0]['args'] == {'file_path': '/real-acceptance.txt', 'content': 'REAL_NATIVE_FILE_PAYLOAD'}
        assert '/real-acceptance.txt' not in waiting.values.get('files', {})
        pending = [call for message in waiting.values['messages'] for call in getattr(message, 'tool_calls', [])
                   if call['name'] == 'write_file']
        assert len(pending) == 1
        native_call_id = pending[0]['id']
        report['approval'] = {'interrupt_id': interrupt.id, 'tool_call_id': native_call_id,
            'checkpoint_id': waiting.config['configurable']['checkpoint_id'],
            'file_absent_before_approval': True}

    # A new saver, Store and graph must recover the exact provider-generated call.
    async with async_runtime() as (saver, store):
        agent = await build(saver, store)
        reloaded = await agent.aget_state(config)
        assert [item.id for item in reloaded.interrupts] == [interrupt.id]
        assert reloaded.config['configurable']['checkpoint_id'] == report['approval']['checkpoint_id']
        assert '/real-acceptance.txt' not in reloaded.values.get('files', {})
        chunks = 0
        async for _ in agent.astream(Command(resume={interrupt.id: {'decisions': [{'type': 'approve'}]}}),
                config, stream_mode=['messages', 'updates', 'values'], subgraphs=True,
                version='v2', durability='sync'):
            chunks += 1
        complete = await agent.aget_state(config)
        assert not complete.interrupts and not complete.next
        assert file_data_to_string(complete.values['files']['/real-acceptance.txt']) == 'REAL_NATIVE_FILE_PAYLOAD'
        results = [message for message in complete.values['messages']
                   if message.type == 'tool' and message.tool_call_id == native_call_id]
        assert len(results) == 1 and results[0].status == 'success'
        assert 'REAL_NATIVE_FILE_OK' in complete.values['messages'][-1].content
        report['resume'] = {'stream_chunks': chunks, 'tool_results': len(results),
            'content': complete.values['messages'][-1].content,
            'usage': complete.values['messages'][-1].usage_metadata}

    async with async_runtime() as (saver, store):
        reader = await build(saver, store, load_tools=False)
        final = await reader.aget_state(config)
        assert file_data_to_string(final.values['files']['/real-acceptance.txt']) == 'REAL_NATIVE_FILE_PAYLOAD'
        assert not final.interrupts and not final.next
        snapshots = [snapshot async for snapshot in reader.aget_state_history(config)]
        assert len(snapshots) >= 3
        report['post_reconnect'] = {'checkpoint_count': len(snapshots), 'file_matches': True,
                                  'pending': False}
    with connection() as conn:
        assert conn.execute('SELECT count(*) AS n FROM agent_runs WHERE session_id=%s', (sid,)).fetchone()['n'] == 0
        assert conn.execute('SELECT count(*) AS n FROM agent_run_events WHERE run_id IN '
            '(SELECT id FROM agent_runs WHERE session_id=%s)', (sid,)).fetchone()['n'] == 0
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True, help='Private acceptance configuration file')
    parser.add_argument('--output', type=Path, required=True, help='Non-secret verification JSON')
    args = parser.parse_args()
    data = json.loads(args.config.read_text())
    load_dotenv(ROOT / '.env', override=False)
    os.environ['DATABASE_URL'] = data['database_url']
    os.environ['AGENT_DATABASE_URL'] = data['agent_database_url']
    os.environ['GOVERNANCE_DATA_DIR'] = data['data_dir']
    owner = data['owner_id']
    from governance.database import connection
    from agent.checkpointer import make_checkpointer
    with make_checkpointer() as saver:
        runtime_target = saver.conn.execute('SELECT current_database() AS db,current_schema() AS schema').fetchone()
        assert runtime_target['db'].endswith('_test') and runtime_target['schema'] == data['schema'] != 'public', 'Requires isolated Agent test database/schema'
    with connection() as conn:
        target = conn.execute('SELECT current_database() AS db,current_schema() AS schema').fetchone()
        assert target['db'].endswith('_test') and target['schema'] == data['schema'] != 'public', 'Requires isolated test database/schema'
        user = conn.execute('SELECT active,role FROM platform_users WHERE id=%s', (owner,)).fetchone()
        assert user and user['active'] and user['role'] == 'admin', 'Requires temporary test owner'
    created = []
    try:
        report = asyncio.run(exercise(owner, created))
    finally:
        from agent.sessions import delete_session
        from governance.database import close_pool
        try:
            for sid in created:
                delete_session(sid, owner)
        finally:
            close_pool()
    result = {'ok': True, 'database': target['db'], 'schema': target['schema'],
              'agent_database': runtime_target['db'],
              'test_session_deleted': True, **report}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
