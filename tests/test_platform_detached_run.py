"""An accepted official run finishes its bookkeeping even when nobody is watching."""
import asyncio
import json
import os

import psycopg
from deepagents import create_deep_agent
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from governance.database import connection
from tests.test_platform_harness import call, harness, original_prepare
from tests.test_platform_session_titles import new_session, title_model


def _scope(path, headers):
    return {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1', 'method': 'POST',
            'scheme': 'http', 'path': path, 'query_string': b'', 'root_path': '',
            'server': ('testserver', 80), 'client': ('127.0.0.1', 1234),
            'headers': [(b'authorization', headers['Authorization'].encode()),
                        (b'content-type', b'application/json')]}


def test_detached_run_keeps_title_and_rejected_submit_has_no_side_effects(harness, title_model, monkeypatch):
    from agent.checkpointer import async_checkpointer
    from webapi import harness as api
    client, _, model, tools, _, app, headers = harness
    sid = new_session(client)

    async def scenario():
        started, allow = asyncio.Event(), asyncio.Event()

        @tool
        async def wait_tool() -> str:
            """Block until released."""
            started.set()
            await allow.wait()
            return 'done'

        tools.append(wait_tool)
        model.responses = [AIMessage(content='', tool_calls=[call('wait_tool', {})]), AIMessage(content='后台完成')]
        first = True

        async def receive():
            nonlocal first
            if first:
                first = False
                return {'type': 'http.request', 'body': json.dumps({'query': '断连后仍需标题'}).encode(),
                        'more_body': False}
            await started.wait()
            return {'type': 'http.disconnect'}

        async def ignore(message):
            pass

        await asyncio.wait_for(app(_scope(f'/api/v1/agent-chat/{sid}', headers), receive, ignore), timeout=10)
        async with async_checkpointer() as saver:
            graph = create_deep_agent(model=model, tools=tools, checkpointer=saver)
            # Checkpoint writers already refuse a thread with scheduled nodes.
            assert (await graph.aget_state({'configurable': {'thread_id': sid}})).next
        with connection() as conn:
            before = conn.execute('SELECT agent_config FROM agent_sessions WHERE id=%s', (sid,)).fetchone()['agent_config']
        monkeypatch.setattr(api, '_prepare', lambda *args: {
            'agent_config': {'access_level': 'auto'}, 'knowledge_base_ids': []})
        sent, body_sent = [], False

        async def receive_second():
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {'type': 'http.request', 'body': json.dumps({'query': '并发'}).encode(), 'more_body': False}
            await asyncio.Event().wait()

        async def collect(message):
            sent.append(message.get('body', b''))

        await asyncio.wait_for(app(_scope(f'/api/v1/agent-chat/{sid}', headers), receive_second, collect), timeout=10)
        assert b'"response_type": "error"' in b''.join(sent)
        with connection() as conn:
            after = conn.execute('SELECT agent_config FROM agent_sessions WHERE id=%s', (sid,)).fetchone()['agent_config']
        assert after == before
        allow.set()
        title = ''
        for _ in range(250):
            with connection() as conn:
                title = conn.execute('SELECT title FROM agent_sessions WHERE id=%s', (sid,)).fetchone()['title']
            if title:
                break
            await asyncio.sleep(0.02)
        assert title == '数据库查询指南'

    asyncio.run(scenario())
    assert len(title_model['calls']) == 1
    with psycopg.connect(os.environ['AGENT_DATABASE_URL'], autocommit=True) as conn:
        assert conn.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0))', ('harness:' + sid,)).fetchone()[0]
