"""Native OpenSandbox boundaries; real Docker verification is explicitly opt-in."""
import asyncio
import base64
import json
import os
import subprocess
from types import SimpleNamespace
from contextlib import contextmanager

import anyio
import httpx
from dotenv import dotenv_values
from deepagents.backends.utils import create_file_data
import pytest
from starlette.testclient import TestClient

from agent import registry, sandbox, sessions
from governance.store import StoreError


def test_readonly_never_provisions_execution_backend(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('read-only must not create or connect a shell')
    monkeypatch.setattr(sandbox, 'connected_session', forbidden)
    async def check():
        for role, access in [('viewer', 'auto_write'), ('editor', 'read_only')]:
            async with sandbox.backend_for_session('session', 'owner', {
                    'sandbox_config_id': sandbox.CONFIG_ID, 'access_level': access}, role) as backend:
                assert backend is None
    asyncio.run(check())


def test_cancelled_request_closes_sdk_client_without_destroying_environment(monkeypatch):
    calls = []
    directories = []
    @contextmanager
    def connected(*args, **kwargs):
        calls.append('connect')
        try:
            yield SimpleNamespace(id='native-sandbox', files=SimpleNamespace(create_directories=directories.extend))
        finally:
            calls.append('close')
    monkeypatch.setattr(sandbox, 'connected_session', connected)
    async def check():
        with anyio.CancelScope() as scope:
            async with sandbox.backend_for_session('session', 'owner', {
                    'sandbox_config_id': sandbox.CONFIG_ID, 'access_level': 'confirm'}, 'editor'):
                scope.cancel()
                await anyio.sleep(0)
    anyio.run(check)
    assert calls == ['connect', 'close']
    assert [(entry.path, entry.mode) for entry in directories] == [('/workspace', 755)]


def test_sdk_client_closes_if_handle_transaction_commit_fails(monkeypatch):
    calls = []
    @contextmanager
    def failing_commit():
        yield SimpleNamespace(execute=lambda *args: None)
        raise RuntimeError('commit failed')
    native = SimpleNamespace(close=lambda: calls.append('close'))
    monkeypatch.setattr(sandbox, 'connection', failing_commit)
    monkeypatch.setattr(sandbox, 'session_handle', lambda *args: {'sandbox_id': 'native-id'})
    monkeypatch.setattr(sandbox, 'connection_config', lambda: None)
    monkeypatch.setattr(sandbox.SandboxSync, 'connect', lambda *args, **kwargs: native)
    with pytest.raises(StoreError) as failed:
        with sandbox.connected_session('owner', 'session'):
            pytest.fail('transaction failure must not yield a backend')
    assert failed.value.status == 503 and calls == ['close']


def test_attachment_bytes_and_virtual_route_boundaries():
    written = []
    backend = SimpleNamespace(_sandbox=SimpleNamespace(files=SimpleNamespace(write_files=written.extend)))
    raw = b'\x00\xff\x89PNG'
    asyncio.run(sandbox.upload_harness_files(backend, {
        '/attachments/id/data.bin': create_file_data(base64.b64encode(raw).decode(), encoding='base64'),
        '/attachments/id/text.txt': create_file_data('中文\ntext')}))
    assert [item.data for item in written] == [raw, '中文\ntext'.encode()]
    assert all(item.mode == 644 for item in written)
    for path in ['/skills/example/SKILL.md', '/memories/user.md', '/state/skills/x',
                 '/attachments/../secret', '/attachments//bad', '/attachments/./bad']:
        with pytest.raises(StoreError) as denied:
            asyncio.run(sandbox.upload_harness_files(backend, {path: create_file_data('bad')}))
        assert denied.value.status == 400


def test_community_upload_uses_official_sdk_permission_digits(monkeypatch):
    from deepagents.backends.protocol import ExecuteResponse
    from langchain_opensandbox import OpenSandboxBackend
    written = []
    native = SimpleNamespace(files=SimpleNamespace(write_files=written.extend))
    backend = OpenSandboxBackend(sandbox=native)
    monkeypatch.setattr(backend, 'execute', lambda *args: ExecuteResponse(output='', exit_code=1))
    result = backend.upload_files([('/workspace/permission.txt', b'editable')])
    assert result[0].error is None
    assert written[0].mode == 644 and written[0].data == b'editable'


def test_checkpoint_attachment_seed_is_once_per_environment(monkeypatch):
    owner = os.environ['TEST_PLATFORM_USER']
    sid = sessions.create_session(owner_id=owner)['id']
    registry.save_record(sandbox.SESSION_KIND, {'id': sid, 'sandbox_id': 'native-id'}, owner)
    written = []
    backend = SimpleNamespace(_sandbox=SimpleNamespace(files=SimpleNamespace(write_files=written.extend)))
    files = {'/attachments/a/data.txt': create_file_data('seed'), '/skills/guide/SKILL.md': create_file_data('virtual')}
    asyncio.run(sandbox.seed_checkpoint_attachments(backend, owner, sid, files))
    asyncio.run(sandbox.seed_checkpoint_attachments(backend, owner, sid, files))
    assert len(written) == 1 and written[0].path == '/attachments/a/data.txt'
    assert registry.record(sandbox.SESSION_KIND, sid, owner)['checkpoint_attachments_seeded'] is True
    assert sandbox.session_handle('other-owner', sid) is None
    with pytest.raises(StoreError) as denied:
        with sandbox.connected_session('other-owner', sid):
            pass
    assert denied.value.status == 409


def test_terminal_ticket_single_use_owner_and_readonly(authenticated_client):
    from webapi.weknora.sandbox_terminal import _consume, _authorize
    owner = os.environ['TEST_PLATFORM_USER']
    sid = sessions.create_session(owner_id=owner)['id']
    response = authenticated_client.post(f'/api/v1/sessions/{sid}/sandbox/terminal-ticket', json={})
    assert response.status_code == 200
    ticket = response.json['data']['ticket']
    claims, (user, selected) = _consume(ticket, sid)
    assert user['id'] == owner and selected['id'] == sid
    with pytest.raises(StoreError) as reused:
        _consume(ticket, sid)
    assert reused.value.status == 403
    from governance.database import connection
    from psycopg.types.json import Jsonb

    for config in [{'sandbox_config_id': 'state-backend', 'access_level': 'confirm'},
                   {'sandbox_config_id': sandbox.CONFIG_ID, 'access_level': 'read_only'}]:
        with connection() as conn:
            conn.execute('UPDATE agent_sessions SET agent_config=%s WHERE id=%s',
                         (Jsonb({'runtime': 'deepagents', 'agent_config': config}), sid))
        with pytest.raises(StoreError) as revoked:
            _authorize(claims, check_config=True)
        assert revoked.value.status == 403
    with connection() as conn:
        conn.execute("UPDATE platform_users SET role='viewer' WHERE id=%s", (owner,))
    assert authenticated_client.post(f'/api/v1/sessions/{sid}/sandbox/terminal-ticket', json={}).status_code == 403
    assert authenticated_client.post('/api/v1/sessions/missing/sandbox/terminal-ticket', json={}).status_code == 404


def test_exited_pty_mapping_does_not_exhaust_session_slots():
    from webapi.weknora.sandbox_terminal import _pty_id
    owner = os.environ['TEST_PLATFORM_USER']
    sid = sessions.create_session(owner_id=owner)['id']
    registry.save_record(sandbox.SESSION_KIND, {'id': sid, 'sandbox_id': 'native-id', 'ptys': {}}, owner)
    for index in range(7):
        number = _pty_id(owner, sid, '', 'native-pty-' + str(index))
        assert number == index + 1
        assert _pty_id(owner, sid, str(number)) == 'native-pty-' + str(index)
        _pty_id(owner, sid, str(number), remove=True)
    assert registry.record(sandbox.SESSION_KIND, sid, owner)['ptys'] == {}


def test_pty_handshake_failure_releases_only_unready_new_pty(monkeypatch):
    from webapi.weknora import sandbox_terminal as terminal
    calls = []
    user = {'id': 'owner', 'role': 'editor'}
    selected = {'agent_config': {'agent_config': {'sandbox_config_id': sandbox.CONFIG_ID, 'access_level': 'confirm'}}}
    monkeypatch.setattr(terminal, '_consume', lambda *args: ({}, (user, selected)))
    @contextmanager
    def connected(*args, **kwargs):
        yield SimpleNamespace(get_endpoint=lambda port: SimpleNamespace(endpoint='http://native', build_request_headers=lambda config: {}), connection_config=None)
        calls.append('sdk-close')
    monkeypatch.setattr(terminal, 'connected_session', connected)
    def mapped(*args, **kwargs):
        calls.append('map-remove' if kwargs.get('remove') else 'map-create')
        return 17
    monkeypatch.setattr(terminal, '_pty_id', mapped)
    def request(req):
        calls.append(req.method + ' ' + req.url.path)
        return httpx.Response(200, json={'session_id': 'native-pty'})
    client = httpx.AsyncClient
    monkeypatch.setattr(terminal.httpx, 'AsyncClient', lambda **kwargs: client(transport=httpx.MockTransport(request), **kwargs))
    def failed_handshake(*args, **kwargs):
        raise ValueError('native websocket handshake failed')
    monkeypatch.setattr(terminal, 'connect', failed_handshake)
    class Browser:
        path_params = {'session_id': 'session'}
        query_params = {'ticket': 'ticket'}
        async def close(self, **kwargs):
            calls.append('browser-close')
    asyncio.run(terminal.terminal(Browser()))
    assert calls == ['POST /pty', 'map-create', 'browser-close',
                     'DELETE /pty/native-pty', 'map-remove', 'sdk-close']


@pytest.mark.skipif(os.getenv('OPEN_SANDBOX_TEST_REAL') != '1', reason='requires explicitly authorized local OpenSandbox/Docker')
def test_real_sdk_execute_binary_isolation_and_pty(authenticated_client, monkeypatch):
    from asgi import create_app
    from langchain_opensandbox import OpenSandboxBackend
    settings = dotenv_values('.env')
    monkeypatch.setenv('OPEN_SANDBOX_API_KEY', settings['OPEN_SANDBOX_API_KEY'])
    monkeypatch.setenv('OPEN_SANDBOX_DOMAIN', '127.0.0.1:8090')
    owner = os.environ['TEST_PLATFORM_USER']
    config = {'runtime': 'deepagents', 'agent_config': {'sandbox_config_id': sandbox.CONFIG_ID, 'access_level': 'confirm'}}
    first = sessions.create_session(owner_id=owner, agent_config=config)['id']
    second = sessions.create_session(owner_id=owner, agent_config=config)['id']
    try:
        with sandbox.connected_session(owner, first, create=True) as native:
            backend = OpenSandboxBackend(sandbox=native, timeout=15)
            assert backend.execute('mkdir -p /workspace; printf native-ok').output == 'native-ok'
            raw = b'\x00\xff\x89PNG\r\n'
            assert backend.upload_files([('/workspace/first.bin', raw)])[0].error is None
            assert backend.download_files(['/workspace/first.bin'])[0].content == raw
            candidates = subprocess.check_output(['docker', 'ps', '-q', '--filter', 'ancestor=python:3.12-slim'], text=True).split()
            containers = json.loads(subprocess.check_output(['docker', 'inspect', *candidates], text=True))
            execution = next(item for item in containers if native.id in item['Name'] or native.id in json.dumps(item['Config']['Labels']))
            policy = execution['HostConfig']
            assert not policy['Privileged'] and 'ALL' in policy['CapDrop']
            assert 'NET_ADMIN' not in (policy['CapAdd'] or [])
            assert policy['Memory'] == 512 * 1024 * 1024 and policy['PidsLimit'] == 128
            assert policy['NanoCpus'] == 10**9 or policy['CpuQuota'] / policy['CpuPeriod'] == 1
            assert any(value.startswith('no-new-privileges') for value in policy['SecurityOpt'])
            assert all(mount['Type'] != 'bind' for mount in execution['Mounts'])
            print('OPENSANDBOX_INSPECT ' + json.dumps({
                'runtime': policy['Runtime'], 'privileged': policy['Privileged'],
                'cap_drop': policy['CapDrop'], 'cap_add': policy['CapAdd'],
                'memory': policy['Memory'], 'nano_cpus': policy['NanoCpus'],
                'cpu_quota': policy['CpuQuota'], 'cpu_period': policy['CpuPeriod'],
                'pids_limit': policy['PidsLimit'], 'security_opt': policy['SecurityOpt'],
                'mounts': [{'type': item['Type'], 'destination': item['Destination'],
                            'read_write': item['RW']} for item in execution['Mounts']]}))
            boundary = backend.execute("python3 -c \"import os,socket; assert not os.path.exists('/var/run/docker.sock'); assert not any(k in os.environ for k in ['OPEN_SANDBOX_API_KEY','OPENAI_API_KEY','DATABASE_URL','CONTEXTDB_API_KEY']); s=socket.socket(); s.settimeout(2); assert s.connect_ex(('1.1.1.1',443)) != 0; print('boundaries-ok')\"")
            assert boundary.exit_code == 0 and 'boundaries-ok' in boundary.output
        with sandbox.connected_session(owner, second, create=True) as native:
            backend = OpenSandboxBackend(sandbox=native, timeout=15)
            assert backend.execute('test ! -e /workspace/first.bin').exit_code == 0
        ticket = authenticated_client.post(f'/api/v1/sessions/{first}/sandbox/terminal-ticket', json={}).json['data']['ticket']
        with TestClient(create_app()) as client:
            with client.websocket_connect(f'/api/v1/sessions/{first}/sandbox/terminal?ticket={ticket}') as ws:
                ready = ws.receive_json()
                assert ready['type'] == 'ready' and ready['backend'] == 'opensandbox'
                ws.send_json({'type': 'resize', 'cols': 100, 'rows': 30})
                ws.send_bytes(b"printf 'PTY_%s_OK\\n' NATIVE\n")
                output = b''
                for _ in range(20):
                    message = ws.receive()
                    output += message.get('bytes', b'')
                    if b'PTY_NATIVE_OK' in output:
                        break
                assert b'PTY_NATIVE_OK' in output
    finally:
        sandbox.destroy_for_session(owner, first)
        sandbox.destroy_for_session(owner, second)
