"""Owner/session lifecycle for the official OpenSandbox SDK and catalog adapter."""
import base64
import asyncio
import hashlib
import json
import logging
import os
import shlex
import threading
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import replace
from datetime import timedelta
from importlib.metadata import version
from pathlib import PurePosixPath

import anyio
from deepagents.backends.utils import create_file_data, file_data_to_string
from deepagents.backends.protocol import ExecuteResponse
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from langchain_opensandbox import OpenSandboxBackend
import langchain_opensandbox.sandbox as opensandbox_adapter
from opensandbox import SandboxManagerSync, SandboxSync
from opensandbox.config import ConnectionConfigSync
from opensandbox.exceptions import SandboxApiException
from opensandbox.models import NetworkPolicy, SearchEntry, WriteEntry
from opensandbox.models.execd import RunCommandOpts
from opensandbox.models.execd_sync import ExecutionHandlersSync

from agent import registry
from governance.database import connection
from governance.store import StoreError

CONFIG_ID = 'opensandbox-local'
SESSION_KIND = 'opensandbox-session'
MAX_ARTIFACT_BYTES = 25 * 1024 * 1024


class SandboxArtifacts(AgentMiddleware):
    """Commit workspace outputs with the native tool result, including before an interrupt."""
    archive_error = '工具已执行，但文件归档失败（文件可能仍在修改、超过 25 MiB 或沙箱不可用）；请勿重复执行原工具。'
    _file_changing_tools = {'write_file', 'edit_file', 'delete', 'execute', 'task'}

    def __init__(self, backend):
        self.backend = backend

    def _entries(self):
        try:
            entries = self.backend._sandbox.files.search(SearchEntry(path='/workspace', pattern='*'))
        except SandboxApiException as exc:
            if exc.status_code == 404:
                self.backend._sandbox.get_info()
                return {}
            raise
        files = {entry.path: entry for entry in entries if entry.entry_type == 'file'
                and entry.path.startswith('/workspace/') and str(PurePosixPath(entry.path)) == entry.path
                and '..' not in PurePosixPath(entry.path).parts
                and not entry.path.startswith(('/workspace/skills/', '/workspace/large_tool_results/',
                                               '/workspace/conversation_history/'))}
        return files

    @staticmethod
    def _checksum_command(files):
        script = ('import hashlib,json,sys\nhashes={}\n'
                  'for path in json.loads(sys.argv[1]):\n'
                  ' with open(path,"rb") as stream:\n'
                  '  hashes[path]=hashlib.file_digest(stream,"sha256").hexdigest()\n'
                  'print(json.dumps(hashes))')
        return f'python3 -c {shlex.quote(script)} {shlex.quote(json.dumps(list(files)))}'

    @staticmethod
    def _checked_snapshot(files, response):
        if response.exit_code != 0 or response.truncated:
            raise StoreError('沙箱产物校验失败', 503)
        digests = json.loads(response.output)
        if set(digests) != files.keys():
            raise StoreError('沙箱产物校验不完整', 503)
        return {path: (entry, digests[path]) for path, entry in files.items()}

    def _snapshot(self):
        files = self._entries()
        return self._checked_snapshot(files, self.backend.execute(self._checksum_command(files))) if files else {}

    async def _asnapshot(self):
        files = await anyio.to_thread.run_sync(self._entries, abandon_on_cancel=True)
        return self._checked_snapshot(files, await self.backend.aexecute(self._checksum_command(files))) if files else {}

    def _changes(self, before, after, archived):
        changed = [path for path, (_, digest) in after.items() if path not in before or digest != before[path][1]]
        if sum(after[path][0].size for path in changed) > MAX_ARTIFACT_BYTES:
            raise StoreError('单次工具生成的产物总量超过 25 MiB，未归档', 413)
        files = {path: None for path in before.keys() - after.keys() if path in archived}
        downloaded = [(path, self.backend._sandbox.files.read_bytes(path)) for path in changed]
        current = self.backend._sandbox.files.get_file_info(changed) if changed else {}
        for path, raw in downloaded:
            entry, digest = after[path]
            latest = current.get(path)
            if (raw is None or len(raw) != entry.size or latest is None
                    or hashlib.sha256(raw).hexdigest() != digest
                    or (latest.size, latest.modified_at) != (entry.size, entry.modified_at)):
                raise StoreError('沙箱产物读取失败或文件仍在修改', 503)
            files[path] = {**create_file_data(base64.b64encode(raw).decode(),
                created_at=entry.created_at.isoformat(), encoding='base64'),
                'modified_at': entry.modified_at.isoformat()}
        return files

    @staticmethod
    def _merge(request, result, files=None, error=None):
        update = (result.update or {}) if isinstance(result, Command) else {'messages': [result]}
        if error:
            update = {**update, 'messages': [message.model_copy(update={'status': 'error',
                'content': f'{message.content}\n{error}'})
                if isinstance(message, ToolMessage) and message.tool_call_id == request.tool_call['id']
                else message for message in update.get('messages', [])]}
        if files:
            update = {**update, 'files': {**update.get('files', {}), **files}}
        return replace(result, update=update) if isinstance(result, Command) else (
            Command(update=update) if files else update['messages'][0])

    @staticmethod
    def _failed(result):
        messages = (result.update or {}).get('messages', []) if isinstance(result, Command) else [result]
        return any(isinstance(message, ToolMessage) and message.status == 'error' for message in messages)

    def _finish(self, request, before, after, result):
        files = self._changes(before, after, request.state.get('files', {}))
        return self._merge(request, result, files=files)

    def wrap_tool_call(self, request, handler):
        if request.tool_call['name'] not in self._file_changing_tools:
            return handler(request)
        try:
            before = self._snapshot()
        except Exception:
            return ToolMessage(content='沙箱产物检查失败，未执行此工具，请检查运行环境。',
                tool_call_id=request.tool_call['id'], name=request.tool_call['name'], status='error')
        result = handler(request)
        if self._failed(result):
            return result
        try:
            return self._finish(request, before, self._snapshot(), result)
        except Exception:
            return self._merge(request, result, error=self.archive_error)

    async def awrap_tool_call(self, request, handler):
        if request.tool_call['name'] not in self._file_changing_tools:
            return await handler(request)
        try:
            before = await self._asnapshot()
        except Exception:
            return ToolMessage(content='沙箱产物检查失败，未执行此工具，请检查运行环境。',
                tool_call_id=request.tool_call['id'], name=request.tool_call['name'], status='error')
        result = await handler(request)
        if self._failed(result):
            return result
        try:
            after = await self._asnapshot()
            return await anyio.to_thread.run_sync(lambda: self._finish(request, before, after, result),
                                                abandon_on_cancel=True)
        except Exception:
            return self._merge(request, result, error=self.archive_error)


class ManagedOpenSandboxBackend(OpenSandboxBackend):
    """Use official execution IDs to stop commands when the owning request ends."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._commands_lock = threading.Lock()
        self._cancel_lock = threading.Lock()
        self._commands = set()
        self._inflight = 0
        self._cancelled = threading.Event()

    def execute(self, command, *, timeout=None):
        if self._cancelled.is_set():
            raise StoreError('当前请求已取消', 409)
        identifier = None
        def started(event):
            nonlocal identifier
            identifier = event.id
            with self._commands_lock:
                self._commands.add(identifier)
            # Cancellation may precede the server's execution-init event.
            if self._cancelled.is_set():
                self._sandbox.commands.interrupt(identifier)
        effective = self._default_timeout if timeout is None else timeout
        with self._commands_lock:
            self._inflight += 1
        try:
            execution = self._sandbox.commands.run(command,
                opts=RunCommandOpts(timeout=timedelta(seconds=effective) if effective else None),
                handlers=ExecutionHandlersSync(on_init=started))
            output = '\n'.join(message.text for message in execution.logs.stdout)
            stderr = '\n'.join(message.text for message in execution.logs.stderr)
            if stderr.strip():
                output += f'\n<stderr>{stderr.strip()}</stderr>'
            return ExecuteResponse(output=output, exit_code=execution.exit_code, truncated=False)
        finally:
            with self._commands_lock:
                self._inflight -= 1
                if identifier:
                    self._commands.discard(identifier)

    def cancel(self):
        self._cancelled.set()
        with self._cancel_lock:
            with self._commands_lock:
                identifiers = tuple(self._commands)
                pending = self._inflight > len(identifiers)
            failed = False
            for identifier in identifiers:
                try:
                    self._sandbox.commands.interrupt(identifier)
                except SandboxApiException as exc:
                    if exc.status_code == 404:
                        continue
                except Exception:
                    pass
                # A concurrent cancellation can already have stopped this ID.
                try:
                    for _ in range(20):
                        status = self._sandbox.commands.get_command_status(identifier)
                        if status.running is False:
                            break
                        time.sleep(0.05)
                    else:
                        failed = True
                except SandboxApiException as exc:
                    if exc.status_code != 404:
                        failed = True
                except Exception:
                    failed = True
            if failed:
                raise StoreError('部分沙箱命令尚未确认停止', 503)
            return {'command_state': 'interrupt_requested' if pending else 'stopped' if identifiers else 'idle'}

    async def aexecute(self, command, *, timeout=None):
        task = asyncio.create_task(asyncio.to_thread(self.execute, command, timeout=timeout))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            with anyio.CancelScope(shield=True):
                await anyio.to_thread.run_sync(self.cancel)
                try:
                    await asyncio.wait_for(asyncio.shield(task), 5)
                except Exception:
                    logging.getLogger(__name__).warning('Cancelled sandbox command stream did not finish cleanly')
            raise

# User-approved 0.1.2 compatibility fix: SDK mode uses digits 644, not bitmask 0o644 (420).
if version('langchain-sandbox-opensandbox') == '0.1.2' and opensandbox_adapter.DEFAULT_FILE_MODE == 0o644:
    opensandbox_adapter.DEFAULT_FILE_MODE = 644


def enabled():
    return bool(os.getenv('OPEN_SANDBOX_API_KEY'))


def connection_config():
    if not enabled():
        raise StoreError('OpenSandbox 控制服务未配置', 503)
    return ConnectionConfigSync(domain=os.getenv('OPEN_SANDBOX_DOMAIN', '127.0.0.1:8090'),
        api_key=os.environ['OPEN_SANDBOX_API_KEY'], protocol=os.getenv('OPEN_SANDBOX_PROTOCOL', 'http'),
        use_server_proxy=True, request_timeout=timedelta(seconds=60))


def configuration():
    return {'id': CONFIG_ID, 'name': 'OpenSandbox（受限开发环境）', 'sandbox_type': 'docker',
        'type': 'docker', 'enabled': enabled(), 'read_only': True, 'skills_available': True,
        'config': {'sandbox_type': 'docker'},
        'capabilities': {'shell': True, 'filesystem': True, 'terminal': True}}


def session_handle(owner_id, session_id):
    try:
        return registry.record(SESSION_KIND, session_id, owner_id)
    except StoreError as exc:
        if exc.status != 404:
            raise
        return None


@contextmanager
def connected_session(owner_id, session_id, *, create=False):
    """Close the HTTP client on exit; the sandbox lives until TTL or explicit delete."""
    sandbox = None
    try:
        try:
            # Both the chat request and a terminal can be the first provisioner.
            with connection() as conn:
                conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))',
                             ('opensandbox:' + owner_id + ':' + session_id,))
                handle = session_handle(owner_id, session_id)
                if handle:
                    sandbox = SandboxSync.connect(handle['sandbox_id'], connection_config=connection_config())
                elif create:
                    sandbox = SandboxSync.create(os.getenv('OPEN_SANDBOX_IMAGE', 'python:3.12-slim'),
                        connection_config=connection_config(), timeout=timedelta(minutes=30),
                        ready_timeout=timedelta(seconds=90), resource={'cpu': '1', 'memory': '512Mi'},
                        metadata={'application': 'showdoc-agent', 'owner_id': owner_id, 'session_id': session_id},
                        env={}, network_policy=NetworkPolicy(defaultAction='deny', egress=[]), volumes=[])
                    try:
                        registry.save_record(SESSION_KIND, {'id': session_id, 'session_id': session_id,
                            'sandbox_id': sandbox.id, 'sandbox_config_id': CONFIG_ID, 'ptys': {}}, owner_id)
                    except Exception:
                        sandbox.destroy()
                        sandbox = None
                        raise
                else:
                    raise StoreError('会话尚未绑定沙箱，请先运行 Agent 或主动创建终端', 409)
        except SandboxApiException as exc:
            if exc.status_code == 404:
                raise StoreError('沙箱环境已回收，请清理会话环境后重建', 410) from exc
            raise StoreError('OpenSandbox 控制服务调用失败', 503) from exc
        except StoreError:
            raise
        except Exception as exc:
            # Never silently recreate a lost environment or expose control-plane responses/secrets.
            raise StoreError('OpenSandbox 不可用或环境已回收；请检查控制服务与会话环境', 503) from exc
        yield sandbox
    finally:
        if sandbox is not None:
            sandbox.close()


@asynccontextmanager
async def backend_for_session(session_id, owner_id, agent_config, role):
    if (agent_config.get('sandbox_config_id', 'state-backend') == 'state-backend' or role == 'viewer'
            or agent_config.get('access_level') == 'read_only'):
        yield None
        return
    if agent_config.get('sandbox_config_id') != CONFIG_ID:
        raise StoreError('未接入此沙箱配置', 501)
    manager = connected_session(owner_id, session_id, create=True)
    sandbox = await anyio.to_thread.run_sync(manager.__enter__)
    try:
        await anyio.to_thread.run_sync(lambda: sandbox.files.create_directories([WriteEntry(path='/workspace', mode=755)]))
        backend = ManagedOpenSandboxBackend(sandbox=sandbox, timeout=180)
        try:
            yield backend
        finally:
            with anyio.CancelScope(shield=True):
                await anyio.to_thread.run_sync(backend.cancel)
    finally:
        with anyio.CancelScope(shield=True):
            await anyio.to_thread.run_sync(lambda: manager.__exit__(None, None, None))


def _attachment_entries(files):
    entries = []
    for path, item in files.items():
        relative = PurePosixPath(path)
        if (not path.startswith(('/uploads/', '/attachments/')) or '..' in relative.parts
                or '\\' in path or '\x00' in path or str(relative) != path or item is None):
            raise StoreError('沙箱附件路径无效', 400)
        try:
            if item.get('encoding', 'utf-8') not in ('utf-8', 'base64'):
                raise ValueError('Unsupported encoding')
            value = file_data_to_string(item)
            raw = value.encode('utf-8') if item.get('encoding', 'utf-8') == 'utf-8' else base64.b64decode(value, validate=True)
        except (KeyError, TypeError, ValueError) as exc:
            raise StoreError('沙箱附件编码无效', 400) from exc
        entries.append(WriteEntry(path=path, data=raw, mode=644))
    return entries


async def upload_harness_files(backend, files):
    """Write authenticated attachments via SDK; virtual Skills/memory stay outside the shell."""
    entries = _attachment_entries(files)
    if entries:
        try:
            await anyio.to_thread.run_sync(lambda: backend._sandbox.files.write_files(entries))
        except Exception as exc:
            raise StoreError('沙箱附件上传失败', 503) from exc


async def upload_skill_files(backend, files):
    """Copy authorized skill versions into the disposable execution environment."""
    entries, removed = [], []
    for path, item in files.items():
        if not path.startswith('/skills/'):
            continue
        relative = PurePosixPath(path)
        if ('..' in relative.parts or '\\' in path or '\x00' in path or str(relative) != path
                or len(relative.parts) < 4):
            raise StoreError('技能执行文件路径无效', 400)
        destination = '/workspace' + path
        if item is None:
            removed.append(destination)
            continue
        try:
            content = file_data_to_string(item)
            if item.get('encoding', 'utf-8') == 'base64':
                raw = base64.b64decode(content, validate=True)
            elif item.get('encoding', 'utf-8') == 'utf-8':
                raw = content.encode('utf-8')
            else:
                raise ValueError('Unsupported encoding')
        except (KeyError, TypeError, ValueError) as exc:
            raise StoreError('技能执行文件编码无效', 400) from exc
        mode = 755 if 'scripts' in relative.parts or relative.suffix == '.sh' else 644
        entries.append(WriteEntry(path=destination, data=raw, mode=mode))
    def transfer():
        for path in removed:
            try:
                backend._sandbox.files.delete_files([path])
            except SandboxApiException as exc:
                if exc.status_code != 404:
                    raise
        if entries:
            directories = sorted({str(PurePosixPath(item.path).parent) for item in entries})
            backend._sandbox.files.create_directories([WriteEntry(path=path, mode=755) for path in directories])
            backend._sandbox.files.write_files(entries)
    try:
        await anyio.to_thread.run_sync(transfer)
    except Exception as exc:
        raise StoreError('技能文件传入沙箱失败', 503) from exc


async def seed_checkpoint_attachments(backend, owner_id, session_id, headfiles):
    """Restore only checkpoint attachments once, including a terminal-created environment."""
    entries = _attachment_entries({path: item for path, item in headfiles.items()
                                  if path.startswith(('/attachments/', '/uploads/')) and item is not None})
    def seed():
        with connection() as conn:
            conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))',
                         ('opensandbox:' + owner_id + ':' + session_id,))
            handle = registry.record(SESSION_KIND, session_id, owner_id)
            if not handle.get('checkpoint_attachments_seeded'):
                if entries:
                    backend._sandbox.files.write_files(entries)
                handle['checkpoint_attachments_seeded'] = True
                registry.save_record(SESSION_KIND, handle, owner_id)
    try:
        await anyio.to_thread.run_sync(seed)
    except StoreError:
        raise
    except Exception as exc:
        raise StoreError('恢复沙箱附件失败', 503) from exc


def destroy_for_session(owner_id, session_id):
    """Delete the actual environment before its owner-scoped handle."""
    if not session_handle(owner_id, session_id):
        return
    with connection() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))',
                     ('opensandbox:' + owner_id + ':' + session_id,))
        handle = session_handle(owner_id, session_id)
        if handle is None:
            return
        manager = SandboxManagerSync.create(connection_config=connection_config())
        try:
            manager.kill_sandbox(handle['sandbox_id'])
        except SandboxApiException as exc:
            if exc.status_code != 404:
                raise StoreError('销毁 OpenSandbox 环境失败', 503) from exc
        except Exception as exc:
            raise StoreError('销毁 OpenSandbox 环境失败', 503) from exc
        finally:
            manager.close()
        registry.delete_record(SESSION_KIND, session_id, owner_id)
