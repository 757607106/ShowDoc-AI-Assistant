"""Translate unchanged WeKnora terminal frames to official OpenSandbox execd PTYs."""
import asyncio
import json
import logging
import os
from urllib.parse import urlsplit

import anyio
import httpx
from itsdangerous import BadSignature, URLSafeTimedSerializer
from starlette.routing import WebSocketRoute
from starlette.websockets import WebSocketDisconnect
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from agent import registry, sessions
from agent.config import load_agent
from agent.sandbox import CONFIG_ID, SESSION_KIND, connected_session, destroy_for_session
from governance.database import connection
from governance.store import StoreError


def _authorize(claims, *, check_config=False, agent_id=None):
    with connection() as conn:
        user = conn.execute('''SELECT u.* FROM platform_users u JOIN platform_tokens t ON t.owner_id=u.id
            WHERE t.id=%s AND u.id=%s AND t.expires_at>now() AND u.active''',
            (claims['auth_session'], claims['owner_id'])).fetchone()
    if not user or user['role'] == 'viewer':
        raise StoreError('终端授权已撤销', 403)
    selected = sessions.get_session(claims['session_id'], user['id'])
    if selected['agent_config'].get('runtime') != 'deepagents':
        raise StoreError('旧会话不可执行', 410)
    if check_config:
        config = selected['agent_config'].get('agent_config') or load_agent(agent_id, user['id'])['config']
        if config.get('sandbox_config_id') != CONFIG_ID or config.get('access_level') == 'read_only':
            raise StoreError('终端权限已撤销', 403)
    return user, selected


def _consume(ticket, session_id):
    try:
        claims = URLSafeTimedSerializer(os.environ['FLASK_SECRET_KEY'], salt='sandbox-terminal').loads(ticket, max_age=120)
        if claims['session_id'] != session_id:
            raise StoreError('终端票据不属于此会话', 403)
        with connection() as conn:
            row = conn.execute("DELETE FROM runtime_records WHERE owner_id=%s AND kind='sandbox-terminal-ticket' AND record_key=%s RETURNING id",
                               (claims['owner_id'], claims['id'])).fetchone()
        if row is None:
            raise StoreError('终端票据已使用', 403)
        return claims, _authorize(claims)
    except (BadSignature, KeyError, TypeError) as exc:
        raise StoreError('终端票据无效或过期', 403) from exc


def _pty_id(owner_id, session_id, requested, native_id=None, *, remove=False):
    with connection() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))',
                     ('opensandbox:' + owner_id + ':' + session_id,))
        handle = registry.record(SESSION_KIND, session_id, owner_id)
        ptys = handle.setdefault('ptys', {})
        if remove:
            ptys.pop(str(requested), None)
            registry.save_record(SESSION_KIND, handle, owner_id)
            return None
        if native_id is None:
            return ptys.get(requested)
        if len(ptys) >= 5:
            raise StoreError('每个会话最多打开 5 个终端', 429)
        number = str(handle.get('next_pty_id', max([int(value) for value in ptys] or [0]) + 1))
        ptys[number] = native_id
        handle['next_pty_id'] = int(number) + 1
        registry.save_record(SESSION_KIND, handle, owner_id)
        return int(number)


async def terminal(websocket):
    manager = None
    entered = False
    accepted = False
    unready_pty = None
    ready_sent = False
    try:
        session_id = websocket.path_params['session_id']
        claims, (user, selected) = await anyio.to_thread.run_sync(lambda: _consume(websocket.query_params.get('ticket', ''), session_id))
        configured = selected['agent_config'].get('agent_config')
        if not configured and websocket.query_params.get('provision') == '1':
            configured = (await anyio.to_thread.run_sync(lambda: load_agent(websocket.query_params.get('agent_id'), user['id'])))['config']
        if not configured or configured.get('sandbox_config_id') != CONFIG_ID or configured.get('access_level') == 'read_only':
            raise StoreError('TERMINAL_UNSUPPORTED', 501)
        manager = connected_session(user['id'], session_id, create=websocket.query_params.get('provision') == '1')
        try:
            sandbox = await anyio.to_thread.run_sync(manager.__enter__)
        except StoreError as exc:
            if exc.status != 410 or websocket.query_params.get('provision') != '1':
                raise
            # The unchanged UI only sends provision=1 after an explicit user click.
            await anyio.to_thread.run_sync(lambda: destroy_for_session(user['id'], session_id))
            manager = connected_session(user['id'], session_id, create=True)
            sandbox = await anyio.to_thread.run_sync(manager.__enter__)
        entered = True
        endpoint = await anyio.to_thread.run_sync(lambda: sandbox.get_endpoint(44772))
        base = endpoint.endpoint
        if not urlsplit(base).scheme:
            base = sandbox.connection_config.protocol + '://' + base
        headers = endpoint.build_request_headers(sandbox.connection_config)
        requested = websocket.query_params.get('pty_id', '')
        native_id = await anyio.to_thread.run_sync(lambda: _pty_id(user['id'], session_id, requested)) if requested else None
        number = int(requested) if native_id else None
        async with httpx.AsyncClient(headers=headers, timeout=15) as client:
            if native_id:
                check = await client.get(base + '/pty/' + native_id)
                if check.status_code == 404:
                    await anyio.to_thread.run_sync(lambda: _pty_id(user['id'], session_id, requested, remove=True))
                    native_id = None
                else:
                    check.raise_for_status()
            if native_id is None:
                response = await client.post(base + '/pty', json={'cwd': '/tmp'})
                response.raise_for_status()
                native_id = response.json()['session_id']
                try:
                    number = await anyio.to_thread.run_sync(lambda: _pty_id(user['id'], session_id, '', native_id))
                except StoreError:
                    await client.delete(base + '/pty/' + native_id)
                    raise
                unready_pty = (base, headers, native_id, number)
            target = base.replace('http://', 'ws://', 1).replace('https://', 'wss://', 1) + '/pty/' + native_id + '/ws'
            async with connect(target, additional_headers=headers, max_size=1024 * 1024) as remote:
                await websocket.accept()
                accepted = True
                await websocket.send_json({'type': 'ready', 'pty_id': number, 'backend': 'opensandbox', 'reattachable': True})
                ready_sent = True

                async def browser_input():
                    while True:
                        message = await asyncio.wait_for(websocket.receive(), timeout=120)
                        if message['type'] == 'websocket.disconnect':
                            return
                        if message.get('bytes') is not None:
                            data = message['bytes']
                            if len(data) > 4096:
                                raise StoreError('终端输入超过单帧限制', 400)
                            await remote.send(b'\x00' + data)
                        elif message.get('text'):
                            if len(message['text']) > 4096:
                                raise StoreError('终端控制帧过长', 400)
                            frame = json.loads(message['text'])
                            if frame.get('type') == 'resize':
                                cols, rows = frame.get('cols'), frame.get('rows')
                                if not all(isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 500 for v in (cols, rows)):
                                    raise StoreError('终端尺寸无效', 400)
                                await remote.send(json.dumps({'type': 'resize', 'cols': cols, 'rows': rows}))
                            elif frame.get('type') == 'ping':
                                await websocket.send_json({'type': 'pong'})

                async def terminal_output():
                    async for message in remote:
                        if isinstance(message, bytes):
                            if message[:1] in (b'\x01', b'\x02'):
                                await websocket.send_bytes(message[1:])
                            elif message[:1] == b'\x03' and len(message) >= 9:
                                await websocket.send_bytes(message[9:])
                        else:
                            frame = json.loads(message)
                            if frame.get('type') == 'exit':
                                await anyio.to_thread.run_sync(lambda: _pty_id(user['id'], session_id, str(number), remove=True))
                                await client.delete(base + '/pty/' + native_id)
                                await websocket.send_json({'type': 'exited', 'exit_code': frame.get('exit_code')})
                                return

                async def recheck():
                    while True:
                        await asyncio.sleep(60)
                        await anyio.to_thread.run_sync(lambda: _authorize(claims,
                            check_config=True, agent_id=websocket.query_params.get('agent_id')))

                tasks = [asyncio.create_task(fn()) for fn in (browser_input, terminal_output, recheck)]
                try:
                    done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    for task in done:
                        task.result()
                finally:
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
    except (StoreError, WebSocketDisconnect, ConnectionClosed, httpx.HTTPError, ValueError, KeyError, TimeoutError) as exc:
        code = 'AUTH_REVOKED' if isinstance(exc, StoreError) and exc.status == 403 else 'INTERNAL'
        if isinstance(exc, StoreError):
            code = {409: 'SANDBOX_NOT_BOUND', 410: 'SANDBOX_STOPPED', 501: 'TERMINAL_UNSUPPORTED'}.get(exc.status, code)
        if accepted:
            try:
                await websocket.send_json({'type': 'error', 'code': code})
                await websocket.close(code=1008, reason=code)
            except (RuntimeError, WebSocketDisconnect):
                pass
        else:
            await websocket.close(code=1008, reason=code)
    finally:
        if unready_pty is not None and not ready_sent:
            base, headers, native_id, number = unready_pty
            with anyio.CancelScope(shield=True):
                try:
                    async with httpx.AsyncClient(headers=headers, timeout=5) as client:
                        response = await client.delete(base + '/pty/' + native_id)
                        if response.status_code != 404:
                            response.raise_for_status()
                    await anyio.to_thread.run_sync(lambda: _pty_id(user['id'], session_id, str(number), remove=True))
                except Exception:
                    # Keep the handle on failure so an operator can retry; sandbox TTL still applies.
                    logging.getLogger(__name__).warning('Failed to release a terminal before ready; retained its sandbox mapping')
        if entered:
            with anyio.CancelScope(shield=True):
                await anyio.to_thread.run_sync(lambda: manager.__exit__(None, None, None))


routes = [WebSocketRoute('/api/v1/sessions/{session_id}/sandbox/terminal', terminal)]
