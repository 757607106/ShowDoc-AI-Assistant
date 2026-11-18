"""Personal workspaces and the bytes of the files they own."""
import json
from pathlib import Path

from governance.store import StoreError, data_dir


def disk_sizes(paths, folder):
    """Only server-managed files are charged. External crawler inputs stay external."""
    root = data_dir()
    sizes = {}
    for raw in filter(None, paths):
        path = Path(raw).resolve()
        if not path.is_relative_to(root / folder):
            continue
        if path.is_file():
            size = path.stat().st_size
        elif path.is_dir() and folder == 'jobs':
            size = sum(p.stat().st_size for p in path.rglob('*') if not p.is_symlink() and p.is_file())
        else:
            continue
        sizes['file:' + str(path.relative_to(root))] = size
    return sizes


def record_sizes(kind, key, payload, metadata):
    if kind == 'job':
        sizes = disk_sizes(payload.get('params', {}).get('file_paths', []), 'uploads')
        sizes.update(disk_sizes([payload.get('output_dir'), metadata.get('zip_file') or payload.get('zip_file')], 'jobs'))
        return sizes
    if kind == 'version':
        if '_capture_path' in payload:
            return disk_sizes([payload['_capture_path']], 'captures')
        return {'capture:' + key: len(json.dumps(payload, ensure_ascii=False).encode())}
    if kind == 'release':
        return disk_sizes([metadata.get('archive_path')], 'releases')
    if kind == 'chat_attachment':
        return {f"attachment:{payload['session_id']}:{key}": payload['file_size']}
    if kind == 'skill':
        sizes = disk_sizes([payload.get('_bundle_path')], 'skill-bundles')
        size = sum(sizes.values()) or sum(len(v.encode()) for v in payload.get('files', {}).values())
        return {'skill:' + key: size}
    return {}


def current_workspace(account_id, conn):
    row = conn.execute("""
        SELECT w.id,w.account_id AS owner_id,w.principal_id,w.storage_indexed,w.name,w.description,'active' AS status,
               w.storage_quota,w.created_at,w.updated_at,
               COALESCE((SELECT sum(size_bytes) FROM workspace_storage
                         WHERE principal_id=w.principal_id),0)::bigint AS storage_used
        FROM platform_workspaces w WHERE w.account_id=%s AND w.deleted_at IS NULL
    """, (account_id,)).fetchone()
    if row:
        principal_id = row.pop('principal_id')
        if not row.pop('storage_indexed'):
            _index_existing(conn, principal_id)
            row['storage_used'] = conn.execute(
                'SELECT coalesce(sum(size_bytes),0)::bigint AS used FROM workspace_storage WHERE principal_id=%s',
                (principal_id,)).fetchone()['used']
    return row


def create_workspace(conn, account_id, principal_id, name, description='Default workspace'):
    conn.execute("""INSERT INTO platform_workspaces(account_id,principal_id,name,description)
                    VALUES (%s,%s,%s,%s)""", (account_id, principal_id, name, description))


def _index_existing(conn, owner):
    """Index legacy files once on the first read or write in their own workspace."""
    from agent.file_storage import index_existing_agent_files
    if not conn.execute("""SELECT id FROM platform_workspaces WHERE principal_id=%s
            AND NOT storage_indexed AND deleted_at IS NULL FOR UPDATE""", (owner,)).fetchone():
        return
    sizes = {}
    with conn.cursor(name='personal_file_inventory') as cursor:
        cursor.execute("""SELECT kind,record_key,
            CASE WHEN kind='chat_attachment' THEN payload-'raw_content'-'text' ELSE payload END AS payload,
            metadata FROM runtime_records WHERE owner_id=%s
            AND kind IN ('job','release','version','chat_attachment','skill')""", (owner,))
        for record in cursor:
            sizes.update(record_sizes(record['kind'], record['record_key'], record['payload'], record['metadata']))
    set_file_sizes(conn, owner, sizes, migrating=True)
    index_existing_agent_files(conn, owner)
    conn.execute('UPDATE platform_workspaces SET storage_indexed=true WHERE principal_id=%s', (owner,))


def set_file_sizes(conn, principal_id, sizes, *, migrating=False):
    """Replace logical file sizes in the same transaction as the owning records."""
    if not principal_id or not sizes:
        return
    workspace = conn.execute("""SELECT storage_quota,storage_indexed FROM platform_workspaces
        WHERE principal_id=%s AND deleted_at IS NULL FOR UPDATE""", (principal_id,)).fetchone()
    if not workspace:
        raise StoreError('个人空间已删除', 410)
    if not migrating and not workspace['storage_indexed']:
        _index_existing(conn, principal_id)
    totals = conn.execute("""SELECT COALESCE(sum(size_bytes),0) AS used,
        COALESCE(sum(size_bytes) FILTER (WHERE resource_key=ANY(%s)),0) AS replaced
        FROM workspace_storage WHERE principal_id=%s""", (list(sizes), principal_id)).fetchone()
    delta = sum(sizes.values()) - totals['replaced']
    if not migrating and delta > 0 and totals['used'] + delta > workspace['storage_quota']:
        raise StoreError('个人空间存储配额不足', 413)
    with conn.cursor() as cursor:
        cursor.executemany("""INSERT INTO workspace_storage(principal_id,resource_key,size_bytes) VALUES (%s,%s,%s)
            ON CONFLICT (principal_id,resource_key) DO UPDATE SET size_bytes=excluded.size_bytes
            WHERE workspace_storage.size_bytes<>excluded.size_bytes""",
            [(principal_id, key, size) for key, size in sizes.items() if size])
    removed = [key for key, size in sizes.items() if not size]
    if removed:
        conn.execute('DELETE FROM workspace_storage WHERE principal_id=%s AND resource_key=ANY(%s)', (principal_id, removed))
