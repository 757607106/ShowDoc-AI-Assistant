"""Official command IDs and real Skill file transfer, without a second executor."""
import asyncio
import base64
import threading
from types import SimpleNamespace

import pytest
from deepagents.backends.utils import create_file_data

from agent import sandbox
from agent.harness_config import prepare_harness_files
from governance.store import StoreError
from tests.test_platform_harness import harness, original_prepare


def test_subagent_skill_sources_only_copy_parent_selected_files(monkeypatch):
    skills = [{'name': name, 'enabled': True, 'files': {'SKILL.md': name, 'scripts/test.py': 'print(42)'}}
              for name in ('alpha', 'beta')]
    monkeypatch.setattr('agent.registry.records', lambda *args: skills)
    config = {'skills_selection_mode': 'selected', 'selected_skills': ['alpha'],
              'subagents': [{'name': 'researcher', 'selected_skills': ['alpha']}]}
    files = prepare_harness_files('owner', config, {'/subagent-skills/removed/alpha/SKILL.md': {}})
    assert files['/subagent-skills/researcher/alpha/scripts/test.py'] == files['/skills/alpha/scripts/test.py']
    assert files['/subagent-skills/removed/alpha/SKILL.md'] is None
    config['subagents'][0]['selected_skills'] = ['beta']
    with pytest.raises(StoreError) as denied:
        prepare_harness_files('owner', config)
    assert denied.value.status == 403


def test_skill_execution_files_use_real_paths_and_original_binary_bytes():
    written, directories, removed = [], [], []
    backend = SimpleNamespace(_sandbox=SimpleNamespace(files=SimpleNamespace(
        write_files=written.extend, create_directories=directories.extend, delete_files=removed.extend)))
    raw = b'\x00\xffPNG'
    files = {'/skills/demo/scripts/check.py': create_file_data('print(42)'),
             '/skills/demo/data.bin': create_file_data(base64.b64encode(raw).decode(), encoding='base64'),
             '/skills/old/scripts/gone.py': None,
             '/subagent-skills/researcher/demo/SKILL.md': create_file_data('virtual'),
             '/memories/a/AGENTS.md': create_file_data('must never enter shell')}
    asyncio.run(sandbox.upload_skill_files(backend, files))
    assert removed == ['/workspace/skills/old/scripts/gone.py']
    assert {entry.path for entry in directories} == {'/workspace/skills/demo', '/workspace/skills/demo/scripts'}
    assert [(entry.path, entry.data, entry.mode) for entry in written] == [
        ('/workspace/skills/demo/scripts/check.py', b'print(42)', 755),
        ('/workspace/skills/demo/data.bin', raw, 644)]
    for path in ('/skills/../secret', '/skills//demo/x', '/skills/demo/./x', '/skills/demo/../../x'):
        with pytest.raises(StoreError) as invalid:
            asyncio.run(sandbox.upload_skill_files(backend, {path: create_file_data('bad')}))
        assert invalid.value.status == 400


@pytest.mark.parametrize('late_init', [False, True])
def test_cancellation_interrupts_official_execution_even_before_init(late_init):
    started, release, ended = threading.Event(), threading.Event(), threading.Event()
    calls = []
    def run(command, *, opts, handlers):
        started.set()
        if late_init:
            assert release.wait(5)
        handlers.on_init(SimpleNamespace(id='native-execution'))
        assert ended.wait(5)
        return SimpleNamespace(logs=SimpleNamespace(stdout=[], stderr=[]), exit_code=143)
    def interrupt(identifier):
        calls.append(identifier)
        ended.set()
    native = SimpleNamespace(id='sandbox', commands=SimpleNamespace(run=run, interrupt=interrupt,
        get_command_status=lambda identifier: SimpleNamespace(running=False)))
    backend = sandbox.ManagedOpenSandboxBackend(sandbox=native, timeout=5)
    async def exercise():
        task = asyncio.create_task(backend.aexecute('sleep 100'))
        assert await asyncio.to_thread(started.wait, 5)
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(exercise())
    assert calls and set(calls) == {'native-execution'}
    assert ended.is_set()
    with pytest.raises(StoreError):
        backend.execute('must not start another command')


def test_cancel_does_not_report_stopped_when_provider_still_runs(monkeypatch):
    native = SimpleNamespace(id='sandbox', commands=SimpleNamespace(interrupt=lambda identifier: None,
        get_command_status=lambda identifier: SimpleNamespace(running=True)))
    backend = sandbox.ManagedOpenSandboxBackend(sandbox=native)
    backend._commands.add('execution')
    monkeypatch.setattr(sandbox.time, 'sleep', lambda seconds: None)
    with pytest.raises(StoreError) as failed:
        backend.cancel()
    assert failed.value.status == 503


@pytest.mark.skipif(__import__('os').getenv('OPEN_SANDBOX_TEST_REAL') != '1', reason='requires local OpenSandbox/Docker')
def test_real_skill_script_binary_copy_and_command_cancel(authenticated_client, monkeypatch):
    import os
    import time
    from dotenv import dotenv_values
    from langchain_opensandbox import OpenSandboxBackend
    from agent import sessions
    settings = dotenv_values('.env')
    monkeypatch.setenv('OPEN_SANDBOX_API_KEY', settings['OPEN_SANDBOX_API_KEY'])
    monkeypatch.setenv('OPEN_SANDBOX_DOMAIN', '127.0.0.1:8090')
    owner = os.environ['TEST_PLATFORM_USER']
    sid = sessions.create_session(owner_id=owner)['id']
    try:
        with sandbox.connected_session(owner, sid, create=True) as native:
            backend = sandbox.ManagedOpenSandboxBackend(sandbox=native, timeout=30)
            data = b'\x00\xff\x89PNG\r\n'
            files = {'/skills/check/SKILL.md': create_file_data('Run scripts/check.py'),
                '/skills/check/data.bin': create_file_data(base64.b64encode(data).decode(), encoding='base64'),
                '/skills/check/scripts/check.py': create_file_data(
                    'from pathlib import Path\nroot=Path(__file__).resolve().parents[1]\n'
                    'assert (root/"data.bin").read_bytes()==bytes([0,255,137,80,78,71,13,10])\n'
                    '(root/"SKILL.md").write_text("session-copy-only")\nprint("skill-real-ok")\n')}
            asyncio.run(sandbox.upload_skill_files(backend, files))
            result = backend.execute('python3 /workspace/skills/check/scripts/check.py')
            assert result.exit_code == 0 and 'skill-real-ok' in result.output
            assert files['/skills/check/SKILL.md']['content'] == 'Run scripts/check.py'
            observer = OpenSandboxBackend(sandbox=native, timeout=10)
            async def exercise():
                command = "python3 -u -c 'import time; from pathlib import Path; p=Path(\"/workspace/ticks\"); [(p.open(\"a\").write(\"x\"),time.sleep(.1)) for _ in range(600)]'"
                tasks = [asyncio.create_task(backend.aexecute(command)) for _ in range(2)]
                for _ in range(100):
                    with backend._commands_lock:
                        identifiers = tuple(backend._commands)
                    if len(identifiers) == 2:
                        break
                    await asyncio.sleep(.05)
                assert len(identifiers) == 2, 'parallel execution-init IDs were not received'
                await asyncio.sleep(.3)
                for task in tasks:
                    task.cancel()
                results = await asyncio.gather(*tasks, return_exceptions=True)
                assert all(isinstance(result, asyncio.CancelledError) for result in results)
                assert all(native.commands.get_command_status(identifier).running is False for identifier in identifiers)
            asyncio.run(exercise())
            before = observer.download_files(['/workspace/ticks'])[0].content
            assert before
            time.sleep(.4)
            assert observer.download_files(['/workspace/ticks'])[0].content == before
    finally:
        sandbox.destroy_for_session(owner, sid)


@pytest.mark.skipif(__import__('os').getenv('OPEN_SANDBOX_TEST_REAL') != '1', reason='requires local OpenSandbox/Docker')
def test_real_http_stop_terminates_official_command(harness, monkeypatch):
    import json
    import os
    from dotenv import dotenv_values
    from deepagents import create_deep_agent
    from langchain_core.messages import AIMessage
    from tests.test_platform_harness import call
    from webapi import harness as api
    client, sid, model, _, _, app, headers = harness
    settings = dotenv_values('.env')
    monkeypatch.setenv('OPEN_SANDBOX_API_KEY', settings['OPEN_SANDBOX_API_KEY'])
    monkeypatch.setenv('OPEN_SANDBOX_DOMAIN', '127.0.0.1:8090')
    owner = os.environ['TEST_PLATFORM_USER']
    monkeypatch.setattr(api, '_prepare', lambda *args: {'agent_config': {
        'access_level': 'auto_write', 'sandbox_config_id': sandbox.CONFIG_ID}, 'knowledge_base_ids': []})
    async def graph(saver, user, selected, resolved, *, backend=None, **kwargs):
        return create_deep_agent(model=model, backend=backend, checkpointer=saver)
    monkeypatch.setattr(api, '_graph', graph)
    command = "python3 -u -c 'import time; from pathlib import Path; p=Path(\"/workspace/http-ticks\"); [(p.open(\"a\").write(\"x\"),time.sleep(.1)) for _ in range(600)]'"
    model.responses = [AIMessage(content='', tool_calls=[call('execute', {'command': command}, 'http-command')])]
    async def scenario():
        first, sent = True, []
        async def receive():
            nonlocal first
            if first:
                first = False
                return {'type': 'http.request', 'body': b'{"query":"Run until stopped"}', 'more_body': False}
            await asyncio.Event().wait()
        async def send(message):
            sent.append(message)
        scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1', 'method': 'POST',
            'scheme': 'http', 'path': f'/api/v1/agent-chat/{sid}', 'query_string': b'', 'root_path': '',
            'server': ('testserver', 80), 'client': ('127.0.0.1', 1234),
            'headers': [(b'authorization', headers['Authorization'].encode()), (b'content-type', b'application/json')]}
        execution = asyncio.create_task(app(scope, receive, send))
        try:
            identifiers = ()
            for _ in range(200):
                backend = api._active_backends.get(sid)
                if backend:
                    with backend._commands_lock:
                        identifiers = tuple(backend._commands)
                if identifiers or execution.done():
                    break
                await asyncio.sleep(.05)
            assert identifiers, b''.join(item.get('body', b'') for item in sent).decode()
            data = b''.join(item.get('body', b'') for item in sent).decode()
            identifier = next(json.loads(line[6:])['assistant_message_id'] for line in data.splitlines()
                if line.startswith('data: ') and 'agent_query' in line)
            await asyncio.sleep(.3)
            stopped = await asyncio.to_thread(client.post, f'/api/v1/sessions/{sid}/stop', json={'message_id': identifier})
            assert stopped.status_code == 200, stopped.text
            assert stopped.json()['command_state'] in ('stopped', 'idle')
            await asyncio.wait_for(execution, 10)
            with sandbox.connected_session(owner, sid) as native:
                assert native.commands.get_command_status(identifiers[0]).running is False
            assert sid not in api._active_requests and sid not in api._active_backends
        finally:
            if not execution.done():
                execution.cancel()
                await asyncio.gather(execution, return_exceptions=True)
    try:
        asyncio.run(scenario())
    finally:
        sandbox.destroy_for_session(owner, sid)


def test_cancel_attempts_every_parallel_command_even_if_one_provider_call_fails(monkeypatch):
    attempted = []
    def interrupt(identifier):
        attempted.append(identifier)
        raise RuntimeError('provider unavailable')
    native = SimpleNamespace(id='sandbox', commands=SimpleNamespace(interrupt=interrupt))
    backend = sandbox.ManagedOpenSandboxBackend(sandbox=native)
    backend._commands.update(('execution-a', 'execution-b'))
    with pytest.raises(StoreError) as failed:
        backend.cancel()
    assert failed.value.status == 503 and set(attempted) == {'execution-a', 'execution-b'}
