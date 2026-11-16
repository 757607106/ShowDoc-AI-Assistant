"""Owner/session lifecycle for the official OpenSandbox SDK and catalog adapter."""
import base64
import os
from contextlib import asynccontextmanager, contextmanager
from datetime import timedelta
from importlib.metadata import version
from pathlib import PurePosixPath

import anyio
from deepagents.backends.utils import file_data_to_string
from langchain_opensandbox import OpenSandboxBackend
import langchain_opensandbox.sandbox as opensandbox_adapter
from opensandbox import SandboxManagerSync, SandboxSync
from opensandbox.config import ConnectionConfigSync
from opensandbox.exceptions import SandboxApiException
from opensandbox.models import NetworkPolicy, WriteEntry

from agent import registry
from governance.database import connection
from governance.store import StoreError

CONFIG_ID = 'opensandbox-local'
SESSION_KIND = 'opensandbox-session'

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
        yield OpenSandboxBackend(sandbox=sandbox, timeout=180)
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
