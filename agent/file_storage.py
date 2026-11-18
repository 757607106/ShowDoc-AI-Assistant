"""Charge the downloadable bytes of native files at their persistence boundary."""
from contextlib import contextmanager, nullcontext

from langgraph.checkpoint.serde.types import _DeltaSnapshot
from langgraph.store.base import PutOp
from langgraph.store.postgres import PostgresStore

from agent.artifacts import artifact_key, file_bytes, is_artifact, media_files
from governance.database import connection
from governance.workspaces import set_file_sizes


def artifact_sizes(sid, writes):
    sizes = {}
    for channel, value in writes:
        if isinstance(value, _DeltaSnapshot):
            value = value.value
        if channel == 'files' and isinstance(value, dict):
            files = value
        elif channel == 'messages' and value:
            messages = value if isinstance(value, list) else [value]
            files = media_files([m for m in messages if isinstance(m, dict) or getattr(m, 'type', None) == 'ai'])
        else:
            continue
        for path, item in files.items():
            if item and is_artifact(path):
                sizes['artifact:' + artifact_key(sid, path, item)] = len(file_bytes(item))
    return sizes


def charge_versions(conn, owner, sizes, *, migrating=False):
    if sizes:
        deleted = conn.execute("""SELECT record_key FROM runtime_records WHERE owner_id=%s
            AND kind='artifact_deleted' AND record_key=ANY(%s)""",
            (owner, [key.removeprefix('artifact:') for key in sizes])).fetchall()
        for row in deleted:
            sizes.pop('artifact:' + row['record_key'], None)
        set_file_sizes(conn, owner, sizes, migrating=migrating)


@contextmanager
def checkpoint_charge(sid, writes, parent_sid, platform_connection):
    sizes = artifact_sizes(f'{parent_sid}:{sid}' if parent_sid else sid, writes)
    if not sizes:
        yield
        return
    with nullcontext(platform_connection) if platform_connection is not None else connection() as conn:
        from governance.store import StoreError
        row = conn.execute('SELECT owner_id FROM agent_sessions WHERE id=%s', (parent_sid or sid,)).fetchone()
        if not row:
            raise StoreError('会话不存在', 404)
        charge_versions(conn, row['owner_id'], sizes)
        yield


class WorkspaceFileStore(PostgresStore):
    def batch(self, ops):
        ops = list(ops)
        sizes = {}
        for op in ops:
            if isinstance(op, PutOp) and len(op.namespace) == 4 and op.namespace[1::2] == ('agents', 'memory'):
                owner, _, agent_id, _ = op.namespace
                sizes.setdefault(owner, {})[f'memory:{agent_id}:{op.key}'] = len(file_bytes(op.value)) if op.value else 0
        if not sizes:
            return super().batch(ops)
        with connection() as conn:
            for owner in sorted(sizes):
                set_file_sizes(conn, owner, sizes[owner])
            return super().batch(ops)


def index_existing_agent_files(conn, owner):
    from agent import registry
    from agent.checkpointer import make_checkpointer, sync_store
    from agent.async_runtime import GRANT_KIND
    sessions = conn.execute('SELECT id FROM agent_sessions WHERE owner_id=%s', (owner,)).fetchall()
    if sessions:
        with make_checkpointer() as saver:
            for row in sessions:
                sid = row['id']
                sizes = {}
                config = {'configurable': {'thread_id': sid}}
                before = None
                while batch := list(saver.list(config, before=before, limit=20)):
                    for entry in batch:
                        sizes.update(artifact_sizes(sid, entry.checkpoint['channel_values'].items()))
                        sizes.update(artifact_sizes(sid, [(k, v) for _, k, v in entry.pending_writes or ()]))
                    before = batch[-1].config
                charge_versions(conn, owner, sizes, migrating=True)
    with sync_store() as store:
        if store.conn.execute("SELECT to_regclass('store') AS relation").fetchone()['relation']:
            offset = 0
            while items := store.search((owner, 'agents'), limit=100, offset=offset):
                sizes = {f'memory:{i.namespace[2]}:{i.key}': len(file_bytes(i.value)) for i in items
                         if len(i.namespace) == 4 and i.namespace[-1] == 'memory'}
                set_file_sizes(conn, owner, sizes, migrating=True)
                offset += len(items)
    grants = registry.records(GRANT_KIND, owner, _connection=conn)
    if grants:
        charge_versions(conn, owner, _delegated_sizes(grants), migrating=True)


def _delegated_sizes(grants):
    from langgraph_sdk import get_sync_client
    from agent.async_runtime import configuration, headers
    sizes = {}
    for (parent, name), grant in {(g['parent_session_id'], g['subagent_name']): g for g in grants}.items():
        threads = get_sync_client(url=configuration()['url'], headers=headers(grant)).threads
        offset = 0
        while batch := threads.search(metadata={'parent_thread_id': parent, 'subagent_name': name}, limit=100, offset=offset):
            for thread in batch:
                sid = thread['thread_id']
                before = None
                while states := threads.get_history(sid, limit=20, before=before):
                    for state in states:
                        sizes.update(artifact_sizes(f'{parent}:{sid}', state['values'].items()))
                    before = states[-1]['checkpoint']['checkpoint_id']
            offset += len(batch)
    return sizes
