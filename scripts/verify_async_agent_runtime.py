"""Opt-in Docker acceptance using disposable records and a local, free fake model.

Run with the project's virtualenv, after starting the configured Agent Protocol
service: python scripts/verify_async_agent_runtime.py --run
"""
import argparse
import asyncio
import json
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@contextmanager
def fake_model(token, docker_host):
    """Serve only deterministic OpenAI chat responses, without external calls."""
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            if self.path != '/v1/chat/completions' or self.headers.get('Authorization') != 'Bearer ' + token:
                self.send_error(404)
                return
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            messages = payload.get('messages', [])
            latest_user = next((message for message in reversed(messages) if message.get('role') == 'user'), {})
            prompt = str(latest_user.get('content', ''))
            since_user = messages[next((index for index in range(len(messages) - 1, -1, -1)
                if messages[index].get('role') == 'user'), -1) + 1:]
            use_tool = bool(payload.get('tools')) and not any(message.get('role') == 'tool' for message in since_user)
            use_tool = use_tool and 'NO_TOOL_UPDATE' not in prompt
            message = {'role': 'assistant', 'content': None if use_tool else 'acceptance-complete ' + prompt}
            if use_tool:
                message['tool_calls'] = [{'id': 'write-' + uuid.uuid4().hex, 'type': 'function', 'function': {
                    'name': 'write_file', 'arguments': json.dumps({'file_path': '/approval.txt', 'content': 'original'})}}]
            requests.append({'used_tool': use_tool, 'update': 'NO_TOOL_UPDATE' in prompt})
            result = {'id': 'acceptance-' + uuid.uuid4().hex, 'model': payload['model'], 'created': int(time.time()),
                'choices': [{'index': 0, 'message': message, 'finish_reason': 'tool_calls' if use_tool else 'stop'}],
                'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}}
            self.send_response(200)
            if payload.get('stream'):
                self.send_header('Content-Type', 'text/event-stream')
                self.end_headers()
                delta = {'role': 'assistant'}
                if use_tool:
                    delta['tool_calls'] = [{'index': 0, **message['tool_calls'][0]}]
                else:
                    delta['content'] = message['content']
                for part, finish in ((delta, None), ({}, result['choices'][0]['finish_reason'])):
                    chunk = {**result, 'object': 'chat.completion.chunk', 'choices': [
                        {'index': 0, 'delta': part, 'finish_reason': finish}]}
                    self.wfile.write(('data: ' + json.dumps(chunk) + '\n\n').encode())
                self.wfile.write(b'data: [DONE]\n\n')
            else:
                body = json.dumps({**result, 'object': 'chat.completion'}).encode()
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

    server = ThreadingHTTPServer(('0.0.0.0', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://{docker_host}:{server.server_port}/v1', requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


async def exercise(owner, model_id, timeout, created, checks):
    from deepagents.backends.utils import file_data_to_string
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage
    from agent import async_runtime, async_work, graph, registry, sessions
    from agent.checkpointer import async_runtime as persistence
    from governance.store import StoreError

    class Launcher(FakeMessagesListChatModel):
        def bind_tools(self, _tools, **_kwargs):
            return self

    async def launch(label, update_strategy='interrupt'):
        config = {'model_id': model_id, 'allowed_tools': [], 'mcp_selection_mode': 'none', 'memory_enabled': False,
            'kb_selection_mode': 'none', 'access_level': 'confirm', 'subagents': [{'name': 'worker',
                'description': 'Disposable approval acceptance worker', 'execution_mode': 'async',
                'update_strategy': update_strategy, 'allowed_tools': []}]}
        sid = sessions.create_session('Disposable async acceptance ' + label + ' ' + uuid.uuid4().hex[:8], owner,
            agent_config={'agent_config': config, 'knowledge_base_ids': []})['id']
        created.append(sid)
        launcher = Launcher(responses=[AIMessage(content='', tool_calls=[{'name': 'start_async_task',
            'args': {'description': 'Write /approval.txt with original, then finish.', 'subagent_type': 'worker'},
            'id': 'launch-' + uuid.uuid4().hex, 'type': 'tool_call'}]), AIMessage(content='Delegated')])
        with patch.object(graph, 'build_model', return_value=launcher), patch.object(async_runtime, 'enabled', return_value=True):
            async with persistence() as (saver, store):
                agent = await graph.build_agent(saver, api_key='', owner_id=owner, role='admin', agent_config=config,
                    session_id=sid, store=store)
                result = await agent.ainvoke({'messages': [{'role': 'user', 'content': 'Start the worker.'}]},
                    {'configurable': {'thread_id': sid}}, durability='sync')
        tasks = result.get('async_tasks', {})
        assert len(tasks) == 1, 'The official SDK did not create exactly one async task'
        identifier, task = next(iter(tasks.items()))
        grant = next(item for item in registry.records(async_runtime.GRANT_KIND, owner) if item['parent_session_id'] == sid)
        return sid, identifier, task['thread_id'], async_runtime.client(grant)

    async def wait(sid, identifier, expected, predicate=None):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            detail = await async_work.task_detail(owner, sid, identifier)
            if detail['state'] in expected and (predicate is None or predicate(detail)):
                if detail['state'] == 'waiting':
                    from deepagents.middleware.async_subagents import _aobserve, _pending_interrupts, _task_status
                    raw_task = (await async_work._tasks(owner, sid))[identifier]
                    client, _grant = await async_work._context(owner, sid, raw_task)
                    run, thread = await _aobserve(client, raw_task)
                    assert _task_status(run, thread) == 'waiting', (run['status'], thread)
                    assert _pending_interrupts(thread), 'The official SDK must see the pending approval IDs'
                return detail
            assert detail['state'] not in ('failed', 'lost', 'cancelled'), detail
            await asyncio.sleep(.25)
        raise AssertionError(f'Task did not reach {sorted(expected)} before the timeout')

    async def file(client, thread_id):
        return (await client.threads.get_state(thread_id, subgraphs=True)).get('values', {}).get('files', {}).get('/approval.txt')

    async def reject(sid, identifier, responses, status):
        try:
            await async_work.control(owner, sid, identifier, 'resume', {'responses': responses})
        except StoreError as error:
            assert error.status == status, (error.status, status)
        else:
            raise AssertionError('Invalid interrupt response was accepted')
        assert (await async_work.task_detail(owner, sid, identifier))['state'] == 'waiting'

    for decision in ('edit', 'approve'):
        sid, identifier, thread_id, client = await launch(decision)
        waiting = await wait(sid, identifier, {'waiting'})
        pending = waiting['result']['interrupts']
        assert len(pending) == 1, pending
        interrupt = pending[0]
        action = interrupt['value']['action_requests'][0]
        assert action['name'] == 'write_file' and await file(client, thread_id) is None
        if decision == 'edit':
            await reject(sid, identifier, {}, 409)
            await reject(sid, identifier, {interrupt['id']: {'decisions': [{'type': 'invalid'}]}}, 400)
            await reject(sid, identifier, {interrupt['id']: {'decisions': [{'type': 'edit',
                'edited_action': {'name': 'execute', 'args': {}}}]}}, 400)
            assert await file(client, thread_id) is None, 'Rejected responses must not execute a tool'
        response = {'type': decision}
        if decision == 'edit':
            response['edited_action'] = {'name': action['name'], 'args': {**action['args'], 'content': 'edited'}}
        await async_work.control(owner, sid, identifier, 'resume', {'responses': {interrupt['id']: {'decisions': [response]}}})
        complete = await wait(sid, identifier, {'succeeded'})
        assert not complete['result']['interrupts'], complete
        assert file_data_to_string(await file(client, thread_id)) == ('edited' if decision == 'edit' else 'original')
        checks.append({'check': decision + ' approval resumes the real remote checkpoint', 'session_id': sid,
            'work_id': identifier, 'state': complete['state'], 'sdk_waiting_and_interrupts_verified': True,
            'bad_responses_rejected': decision == 'edit'})
        if decision == 'edit':
            marker = 'NO_TOOL_UPDATE ' + uuid.uuid4().hex
            await async_work.control(owner, sid, identifier, 'update', {'message': marker})
            updated = await wait(sid, identifier, {'succeeded'}, lambda value: marker in value['result']['output'])
            checks.append({'check': 'update reopens a completed task', 'session_id': sid, 'work_id': identifier,
                'state': updated['state'], 'new_output_observed': True})

    sid, identifier, thread_id, client = await launch('waiting-update', 'enqueue')
    await wait(sid, identifier, {'waiting'})
    marker = 'NO_TOOL_UPDATE ' + uuid.uuid4().hex
    await async_work.control(owner, sid, identifier, 'update', {'message': marker})
    updated = await wait(sid, identifier, {'succeeded'}, lambda value: marker in value['result']['output'])
    assert await file(client, thread_id) is None, 'Updating a waiting task must not execute its unapproved write'
    checks.append({'check': 'enqueue update replaces a waiting request without executing it', 'session_id': sid,
        'work_id': identifier, 'state': updated['state'], 'unapproved_file_absent': True})

    sid, identifier, thread_id, client = await launch('waiting-cancel')
    await wait(sid, identifier, {'waiting'})
    await async_work.control(owner, sid, identifier, 'cancel', {})
    cancelled = await async_work.task_detail(owner, sid, identifier)
    assert cancelled['state'] == 'cancelled' and not cancelled['can_cancel'], cancelled
    assert await file(client, thread_id) is None
    checks.append({'check': 'waiting cancellation keeps the unapproved file absent', 'session_id': sid,
        'work_id': identifier, 'state': cancelled['state'], 'unapproved_file_absent': True})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Opt in to creating and cleaning disposable records')
    parser.add_argument('--owner-id', help='Active admin owner; defaults to the first active admin')
    parser.add_argument('--docker-host', default='host.docker.internal', help='Docker-reachable hostname of this machine')
    parser.add_argument('--timeout', type=float, default=60, help='Maximum seconds for each task state transition')
    parser.add_argument('--output', type=Path, default=ROOT / 'output' / 'verification' / 'async-approval-acceptance.json')
    args = parser.parse_args()
    if not args.run:
        parser.error('This acceptance writes disposable records; pass --run to opt in')
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    from agent import registry, sessions
    from governance.database import connection
    with connection() as conn:
        row = conn.execute("SELECT id FROM platform_users WHERE active AND role='admin' AND (%s::text IS NULL OR id=%s) ORDER BY created_at LIMIT 1",
                           (args.owner_id, args.owner_id)).fetchone()
    if row is None:
        raise SystemExit('No matching active admin owner')
    owner = row['id']
    report = {'real_agent_protocol_service': True, 'external_model_calls': False, 'checks': [], 'cleanup': []}
    created = []
    model_id = None
    failure = None
    calls = []
    try:
        token = uuid.uuid4().hex
        with fake_model(token, args.docker_host) as (base, calls):
            model = registry.save_model({'name': 'gpt-4o-mini', 'display_name': 'Disposable async acceptance ' + uuid.uuid4().hex,
                'type': 'KnowledgeQA', 'source': 'remote', 'parameters': {'provider': 'openai', 'base_url': base,
                    'api_key': token}}, owner)
            # The fake endpoint's token is the only credential used by these disposable records.
            model_id = model['id']
            asyncio.run(exercise(owner, model_id, args.timeout, created, report['checks']))
    except Exception as error:
        failure = error
        report['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        report['fake_model_requests'] = len(calls)
        for sid in created:
            try:
                sessions.delete_session(sid, owner)
                report['cleanup'].append({'session_id': sid, 'deleted': True})
            except Exception as error:
                failure = failure or error
                report['cleanup'].append({'session_id': sid, 'deleted': False, 'error': str(error)})
        if model_id and all(item['deleted'] for item in report['cleanup']):
            registry.delete_record('model', model_id, owner)
            report['model_deleted'] = True
        report['passed'] = failure is None
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'checks': len(report['checks']), 'artifact': str(args.output)}))
    if failure:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
