"""Generated sandbox bytes travel through the production graph and existing artifact HTTP API."""
import base64
import hashlib
import json
import os
import shlex
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage

from agent import graph, registry, sandbox
from tests.test_platform_harness import call, frames, harness, original_prepare
from webapi.harness import _graph as production_graph


class Files:
    def __init__(self):
        self.values = {}
        self.revision = 0
        self.downloads = []
        self.fail_download = False

    def put(self, path, data):
        self.revision += 1
        stamp = datetime(2026, 11, 17, tzinfo=timezone.utc) + timedelta(seconds=self.revision)
        created = self.values[path][1].created_at if path in self.values else stamp
        self.values[path] = (data, SimpleNamespace(path=path, entry_type='file', size=len(data),
            created_at=created, modified_at=stamp))

    def write_files(self, entries):
        for entry in entries:
            self.put(entry.path, entry.data.encode() if isinstance(entry.data, str) else entry.data)

    def search(self, entry):
        assert entry.path == '/workspace' and entry.pattern == '*'
        return [meta for path, (_, meta) in self.values.items() if path.startswith('/workspace/')]

    def get_file_info(self, paths):
        return {path: self.values[path][1] for path in paths if path in self.values}

    def read_bytes(self, path, **kwargs):
        self.downloads.append(path)
        if self.fail_download:
            raise OSError('fixture download failed')
        return self.values[path][0]


class NativeSandbox:
    id = 'isolated-sandbox-fixture'

    def __init__(self):
        self.files = Files()
        self.executed = []
        self.commands = SimpleNamespace(run=self.run, interrupt=lambda identifier: None,
            get_command_status=lambda identifier: SimpleNamespace(running=False))

    def run(self, command, *, opts, handlers=None):
        if handlers:
            handlers.on_init(SimpleNamespace(id='execution-' + str(len(self.executed))))
        exit_code, output = 0, 'command done'
        arguments = shlex.split(command)
        if (arguments[:2] == ['python3', '-c'] and 'hashlib.file_digest' in arguments[2]):
            output = json.dumps({path: hashlib.sha256(self.files.values[path][0]).hexdigest()
                                 for path in json.loads(arguments[3])})
        elif arguments[:2] == ['python3', '-c'] and 'os.scandir(path)' in arguments[2]:
            assert base64.b64encode(b'/workspace/report.bin').decode() in arguments[2]
            output = json.dumps({'error': 'not_a_directory'})
        elif command.startswith('test -e '):
            exit_code = int(arguments[2] not in self.files.values)
        elif arguments[:2] == ['rm', '-rf']:
            del self.files.values[arguments[2]]
        elif command.startswith('python3 -c ') and 'os.makedirs(os.path.dirname(path)' in command:
            output = ''
        elif command.startswith('if [ -d '):
            output = 'OTHER'
        else:
            self.executed.append(command)
            if command == 'emit-binary':
                self.files.put('/workspace/report.bin', b'\x00\xfffirst')
                self.files.put('/workspace/skills/input.dat', b'input mutation')
                self.files.put('/workspace/large_tool_results/internal.txt', b'offload')
            elif command == 'modify-binary':
                self.files.put('/workspace/report.bin', b'\x00\xffsecond')
            elif command == 'preserve-mtime':
                _, metadata = self.files.values['/workspace/report.bin']
                self.files.values['/workspace/report.bin'] = (b'\x00\xffthird!', metadata)
            else:
                assert command == 'noop', command
        return SimpleNamespace(logs=SimpleNamespace(stdout=[SimpleNamespace(text=output)], stderr=[]), exit_code=exit_code)


def install(monkeypatch, harness, *, real=False, **overrides):
    from webapi import harness as api
    client, sid, model, *_ = harness
    config = {'access_level': 'auto_write', 'sandbox_config_id': sandbox.CONFIG_ID,
        'allowed_tools': [], 'mcp_selection_mode': 'none', 'kb_selection_mode': 'none',
        'memory_enabled': False, **overrides}
    monkeypatch.setattr(api, '_graph', production_graph)
    monkeypatch.setattr(api, '_prepare', lambda *args: {'agent_config': config, 'knowledge_base_ids': []})
    monkeypatch.setattr(graph, 'build_model', lambda *args: model)
    monkeypatch.setattr(graph, 'load_knowledge_mcp_tools', AsyncMock(return_value=[]))
    native = None
    if not real:
        native = NativeSandbox()
        registry.save_record(sandbox.SESSION_KIND, {'id': sid, 'session_id': sid,
            'sandbox_id': native.id, 'checkpoint_attachments_seeded': True}, os.environ['TEST_PLATFORM_USER'])
        @asynccontextmanager
        async def backend(*args):
            yield sandbox.ManagedOpenSandboxBackend(sandbox=native, timeout=10)
        monkeypatch.setattr(sandbox, 'backend_for_session', backend)
    return client, sid, model, native


def send(client, sid, query):
    response = client.post(f'/api/v1/agent-chat/{sid}', json={'query': query})
    events = [event for _, event in frames(response)]
    errors = [event['content'] for event in events if event['response_type'] == 'error']
    assert not errors, errors
    return events


def answers(client, sid):
    response = client.get(f'/api/v1/messages/{sid}/load')
    assert response.status_code == 200, response.text
    return [row for row in response.json()['data'] if row['role'] == 'assistant']


def download_path(sid, answer, index=0):
    return f'/api/v1/sessions/{sid}/messages/{answer["id"]}/artifacts/{index}/download'


def test_empty_workspace_file_is_listed_downloadable_and_owner_scoped(harness, monkeypatch):
    client, sid, model, native = install(monkeypatch, harness)
    model.responses = [AIMessage(content='', tool_calls=[call('write_file',
        {'file_path': '/workspace/new_file.txt', 'content': ''}, 'empty-write')]), AIMessage(content='Created')]
    events = send(client, sid, 'Create an empty file')
    assert events[-1]['data']['artifacts'][0]['file_size'] == 0
    answer = answers(client, sid)[-1]
    assert answer['artifacts'][0]['file_name'] == 'new_file.txt'
    downloaded = client.get(download_path(sid, answer))
    assert downloaded.status_code == 200 and downloaded.content == b''
    listed = client.get('/api/v1/artifacts').json()['data']
    assert [(item['file_name'], item['file_size']) for item in listed] == [('new_file.txt', 0)]
    assert native.files.values['/workspace/new_file.txt'][0] == b''
    from webapi.auth import create_user
    create_user('other@example.com', 'Other user', 'other-password-123', 'admin')
    other = client.post('/api/v1/auth/login', json={'email': 'other@example.com', 'password': 'other-password-123'}).json()
    headers = {'Authorization': 'Bearer ' + other['token']}
    assert client.get(download_path(sid, answer), headers=headers).status_code == 404
    assert client.get(f'/api/v1/messages/{sid}/load', headers=headers).status_code == 404
    assert client.get('/api/v1/artifacts', headers=headers).json()['data'] == []


def test_binary_versions_survive_later_turns_and_unchanged_files_do_not_repeat(harness, monkeypatch):
    client, sid, model, native = install(monkeypatch, harness)
    model.responses = [message for command in ('emit-binary', 'modify-binary', 'preserve-mtime', 'noop')
        for message in (AIMessage(content='', tool_calls=[call('execute', {'command': command}, command)]), AIMessage(content='Done'))]
    model.responses.extend([AIMessage(content='', tool_calls=[call('delete', {'file_path': '/workspace/report.bin'}, 'delete-report')]),
                            AIMessage(content='Deleted')])
    first = send(client, sid, 'Generate binary')[-1]['data']['artifacts']
    assert [item['source_path'] for item in first] == ['/workspace/report.bin']
    send(client, sid, 'Modify binary')
    metadata = native.files.values['/workspace/report.bin'][1]
    stamp, size = metadata.modified_at, metadata.size
    send(client, sid, 'Replace same-length bytes while preserving modification time')
    assert native.files.values['/workspace/report.bin'][1].modified_at == stamp
    assert native.files.values['/workspace/report.bin'][1].size == size
    no_change = send(client, sid, 'Do not change files')
    assert no_change[-1]['data']['artifacts'] == []
    rows = answers(client, sid)
    assert client.get(download_path(sid, rows[0])).content == b'\x00\xfffirst'
    assert client.get(download_path(sid, rows[1])).content == b'\x00\xffsecond'
    assert client.get(download_path(sid, rows[2])).content == b'\x00\xffthird!'
    assert rows[3]['artifacts'] == []
    library = client.get('/api/v1/artifacts').json()['data']
    assert len(library) == 1 and library[0]['version_count'] == 3
    assert native.files.downloads.count('/workspace/report.bin') == 3
    deleted = send(client, sid, 'Remove working copy')
    assert any(event['response_type'] == 'tool_result' and event['data']['tool_call_id'] == 'delete-report'
               and event['data']['success'] for event in deleted)
    state = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']
    assert '/workspace/report.bin' not in state.get('files', {})
    assert '/workspace/report.bin' not in native.files.values
    assert client.get(download_path(sid, rows[0])).content == b'\x00\xfffirst'


@pytest.mark.parametrize('decision', ['approve', 'edit'])
def test_archive_is_durable_before_another_tool_interrupt_and_resume_executes_once(harness, monkeypatch, decision):
    client, sid, model, native = install(monkeypatch, harness, interrupt_on={'write_file': True})
    model.responses = [AIMessage(content='', tool_calls=[call('execute', {'command': 'emit-binary'}, 'write-first')]),
        AIMessage(content='', tool_calls=[call('write_file',
            {'file_path': '/workspace/reviewed.txt', 'content': 'after'}, 'approval-second')]), AIMessage(content='Approved')]
    paused = send(client, sid, 'Write then ask before the next command')
    prompt = next(event['data'] for event in paused if event['response_type'] == 'tool_approval_required')
    pending = answers(client, sid)[-1]
    assert pending['run_state'] == 'awaiting_input' and len(pending['artifacts']) == 1
    assert client.get(download_path(sid, pending)).content == b'\x00\xfffirst'
    assert '/workspace/reviewed.txt' not in native.files.values
    response = {'decision': 'approve'}
    if decision == 'edit':
        response['modified_args'] = {'file_path': '/workspace/edited.txt', 'content': 'edited'}
    accepted = client.post('/api/v1/agent/tool-approvals/' + prompt['pending_id'], json=response)
    assert accepted.status_code == 200
    response = client.get(f'/api/v1/sessions/continue-stream/{sid}', params={
        'message_id': pending['id'], 'resume_pending_id': prompt['pending_id']})
    assert frames(response)[-1][1]['response_type'] == 'complete'
    assert native.executed == ['emit-binary']
    path = '/workspace/edited.txt' if decision == 'edit' else '/workspace/reviewed.txt'
    final = answers(client, sid)[-1]
    assert {item['source_path'] for item in final['artifacts']} == {'/workspace/report.bin', path}
    index = next(item['index'] for item in final['artifacts'] if item['source_path'] == path)
    assert client.get(download_path(sid, final, index)).content == (b'edited' if decision == 'edit' else b'after')
    assert native.files.downloads.count(path) == 1
    if decision == 'edit':
        assert '/workspace/reviewed.txt' not in native.files.values


@pytest.mark.parametrize('failure', ['download', 'limit'])
def test_archival_failure_is_visible_without_reexecuting_the_successful_command(harness, monkeypatch, failure):
    client, sid, model, native = install(monkeypatch, harness)
    if failure == 'download':
        native.files.fail_download = True
    else:
        monkeypatch.setattr(sandbox, 'MAX_ARTIFACT_BYTES', 1)
    model.responses = [AIMessage(content='', tool_calls=[call('execute', {'command': 'emit-binary'}, 'execute-once')]),
                       AIMessage(content='The archive failed')]
    send(client, sid, 'Generate once')
    state = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']
    result = next(message for message in state['messages'] if message.get('tool_call_id') == 'execute-once')
    assert result['status'] == 'error' and '归档' in result['content'] and 'command done' in result['content']
    assert native.executed == ['emit-binary']
    assert native.files.values['/workspace/report.bin'][0] == b'\x00\xfffirst'
    assert answers(client, sid)[-1]['artifacts'] == []
    if failure == 'limit':
        assert native.files.downloads == []


def test_parallel_writes_keep_both_native_delta_updates(harness, monkeypatch):
    client, sid, model, _ = install(monkeypatch, harness)
    model.responses = [AIMessage(content='', tool_calls=[call('write_file',
        {'file_path': '/workspace/' + name + '.txt', 'content': name}, name) for name in ('first', 'second')]),
        AIMessage(content='Both created')]
    events = send(client, sid, 'Create two files in parallel')
    assert {item['file_name'] for item in events[-1]['data']['artifacts']} == {'first.txt', 'second.txt'}
    answer = answers(client, sid)[-1]
    for item in answer['artifacts']:
        assert client.get(download_path(sid, answer, item['index'])).content == item['file_name'].removesuffix('.txt').encode()


def test_original_tool_error_is_preserved_without_downloading_existing_files(harness, monkeypatch):
    client, sid, model, native = install(monkeypatch, harness)
    native.files.put('/workspace/existing.txt', b'original')
    native.files.fail_download = True
    model.responses = [AIMessage(content='', tool_calls=[call('write_file',
        {'file_path': '/workspace/existing.txt', 'content': 'must not overwrite'}, 'already-exists')]), AIMessage(content='Not overwritten')]
    send(client, sid, 'Try existing path')
    state = client.get(f'/api/v1/harness/sessions/{sid}/state').json()['values']
    result = next(message for message in state['messages'] if message.get('tool_call_id') == 'already-exists')
    assert result['status'] == 'error' and 'already exists' in result['content'] and '归档' not in result['content']
    assert native.files.downloads == [] and native.files.values['/workspace/existing.txt'][0] == b'original'


@pytest.mark.skipif(os.getenv('OPEN_SANDBOX_TEST_REAL') != '1', reason='requires local OpenSandbox/Docker')
def test_real_sandbox_archives_empty_and_binary_outputs_before_environment_removal(harness, monkeypatch):
    from dotenv import dotenv_values
    settings = dotenv_values('.env')
    monkeypatch.setenv('OPEN_SANDBOX_API_KEY', settings['OPEN_SANDBOX_API_KEY'])
    monkeypatch.setenv('OPEN_SANDBOX_DOMAIN', '127.0.0.1:8090')
    client, sid, model, _ = install(monkeypatch, harness, real=True)
    raw = b'\x00\xffreal-binary\r\n'
    updated = b'\x00\xffREAL-binary\r\n'
    encoded = base64.b64encode(raw).decode()
    command = f"python3 -c 'from pathlib import Path; import base64; Path(\"/workspace/real.bin\").write_bytes(base64.b64decode(\"{encoded}\"))'"
    copy = ('from pathlib import Path\nimport os,shutil,base64\n'
        'target=Path("/workspace/real.bin"); old=target.stat(); source=Path("/tmp/new-source.bin")\n'
        f'source.write_bytes(base64.b64decode("{base64.b64encode(updated).decode()}"))\n'
        'os.utime(source,ns=(old.st_atime_ns,old.st_mtime_ns)); shutil.copy2(source,target)\n'
        'assert target.stat().st_size==old.st_size and target.stat().st_mtime_ns==old.st_mtime_ns')
    model.responses = [AIMessage(content='', tool_calls=[call('write_file',
        {'file_path': '/workspace/real-empty.txt', 'content': ''}, 'real-empty')]),
        AIMessage(content='', tool_calls=[call('execute', {'command': command}, 'real-binary')]), AIMessage(content='Created both'),
        AIMessage(content='', tool_calls=[call('execute', {'command': 'python3 -c ' + shlex.quote(copy)}, 'real-preserved-mtime')]),
        AIMessage(content='Replaced binary with preserved mtime')]
    owner = os.environ['TEST_PLATFORM_USER']
    try:
        events = send(client, sid, 'Generate empty and binary output files')
        assert {item['file_name'] for item in events[-1]['data']['artifacts']} == {'real-empty.txt', 'real.bin'}
        answer = answers(client, sid)[-1]
        replacement = send(client, sid, 'Copy different same-length content while preserving mtime')
        assert [item['file_name'] for item in replacement[-1]['data']['artifacts']] == ['real.bin']
        changed = answers(client, sid)[-1]
        sandbox.destroy_for_session(owner, sid)
        for item in answer['artifacts']:
            response = client.get(download_path(sid, answer, item['index']))
            assert response.status_code == 200
            assert response.content == (raw if item['file_name'] == 'real.bin' else b'')
        assert client.get(download_path(sid, changed)).content == updated
        library = client.get('/api/v1/artifacts').json()['data']
        assert {item['file_name'] for item in library} == {'real-empty.txt', 'real.bin'}
        assert next(item for item in library if item['file_name'] == 'real.bin')['version_count'] == 2
    finally:
        sandbox.destroy_for_session(owner, sid)
