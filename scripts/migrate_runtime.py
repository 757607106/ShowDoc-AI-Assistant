"""Back up legacy ContextDB platform records, then import into PostgreSQL.

Cloud data is read only. Obsolete local knowledge judgments stay in the backup.
Re-running a verified snapshot does not overwrite migrated runtime records.
"""
import argparse
import base64
import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from governance.database import connection, initialize
from governance.store import Store, data_dir
from agent.checkpointer import make_checkpointer, initialize_checkpoints
from integrations.contextdb import ContextDBClient

RUNTIME_TYPES = {'job', 'version', 'doc', 'jobdoc', 'scope', 'release'}


def snapshot(client, path):
    kb = client.find_knowledge_base(os.getenv('CONTEXTDB_GOVERNANCE_KB', '_governance'))
    records = []
    if kb:
        page = 1
        while True:
            docs = client.list_documents(kb['id'], page=page, page_size=100,
                                         sort_by='created_at', sort_order='asc')['documents']
            for doc in docs:
                body = json.loads(client.download_document_text(kb['id'], doc['id']))
                records.append({'document': doc, 'payload': body})
            if len(docs) < 100:
                break
            page += 1
    payload = {'created_at': datetime.now(timezone.utc).isoformat(), 'knowledge_base_id': kb['id'] if kb else None,
               'records': records}
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open('x', encoding='utf-8') as stream:
        os.chmod(path, 0o600)
        json.dump(payload, stream, ensure_ascii=False)
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    path.with_suffix('.sha256').write_text(checksum + '\n')
    return payload


def import_snapshot(data, owner_id):
    store = Store(owner_id=owner_id)
    imported, existing, archived = Counter(), Counter(), Counter()
    sessions = {}
    for record in data['records']:
        meta = dict(record['document'].get('metadata', {}))
        body = dict(record['payload'])
        kind = meta.get('type')
        if kind == 'agent_session':
            sid = body['session_id']
            with connection() as conn:
                prior = conn.execute('SELECT owner_id FROM agent_sessions WHERE id=%s', (sid,)).fetchone()
                if prior and prior['owner_id'] != owner_id:
                    raise RuntimeError('旧会话 ID 与其他用户冲突，停止迁移')
                conn.execute('INSERT INTO agent_sessions(id,owner_id,title,created_at,updated_at) VALUES (%s,%s,%s,coalesce(%s::timestamptz,now()),coalesce(%s::timestamptz,now())) ON CONFLICT DO NOTHING',
                    (sid, owner_id, body.get('title', '迁移会话'), meta.get('created_at'), meta.get('updated_at')))
            sessions[sid] = True
            imported[kind] += 1
        elif kind in RUNTIME_TYPES:
            key = record['document']['name'].removeprefix(kind + '-').removesuffix('.json')
            condition = {name: meta[name] for name in ('job_id', 'version_id', 'doc_id', 'scope', 'release_id') if name in meta}
            # Type-specific logical identity avoids title/path truncation in old filenames.
            identity = {'job':'job_id', 'version':'version_id', 'doc':'doc_id', 'scope':'scope', 'release':'release_id'}.get(kind)
            condition = {identity:meta[identity]} if identity else condition
            if store._find(kind, **condition):
                existing[kind] += 1
                continue
            if kind == 'job':
                body['owner_id'] = owner_id
                if meta.get('status') in ('pending', 'running', 'cancelling'):
                    meta.update(status='failed', phase='interrupted', message='迁移时中断的旧任务；请核对采集参数后重试')
                    body.update(status=meta['status'], phase=meta['phase'], message=meta['message'])
            meta['legacy_cloud_id'] = record['document']['id']
            store._create(kind, key, body, meta)
            imported[kind] += 1
        elif kind not in ('checkpoint', 'write'):
            archived[kind or 'unknown'] += 1
    checkpoints = sorted((r for r in data['records'] if r['document'].get('metadata', {}).get('type') == 'checkpoint'),
                         key=lambda r:r['document']['metadata']['checkpoint_id'])
    writes = defaultdict(list)
    for record in data['records']:
        meta = record['document'].get('metadata', {})
        if meta.get('type') == 'write':
            writes[(meta['thread_id'], meta.get('checkpoint_ns', ''), meta['checkpoint_id'], meta['task_id'])].append(record)
    with make_checkpointer() as saver:
        for record in checkpoints:
            meta, body = record['document']['metadata'], record['payload']
            sid = meta['thread_id']
            if sid not in sessions:
                # Preserve orphaned checkpoints under an explicitly owned imported session.
                with connection() as conn:
                    prior = conn.execute('SELECT owner_id FROM agent_sessions WHERE id=%s', (sid,)).fetchone()
                    if prior and prior['owner_id'] != owner_id:
                        raise RuntimeError('旧 checkpoint 与其他用户会话冲突')
                    conn.execute('INSERT INTO agent_sessions(id,owner_id,title) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING', (sid,owner_id,'迁移会话'))
                sessions[sid] = True
            config = {'configurable': {'thread_id':sid, 'checkpoint_ns':meta.get('checkpoint_ns', '')}}
            checkpoint = saver.serde.loads_typed((body['checkpoint_type'],base64.b64decode(body['checkpoint_blob'])))
            if body.get('parent_id'):
                config['configurable']['checkpoint_id'] = body['parent_id']
            saved_config = saver.put(config, checkpoint, body.get('metadata', {}), checkpoint['channel_versions'])
            assert saver.get_tuple(saved_config).checkpoint['id'] == checkpoint['id']
            imported['checkpoint'] += 1
        for (sid, ns, checkpoint_id, task_id), items in writes.items():
            values = [(r['payload']['channel'], saver.serde.loads_typed((r['payload']['write_blob_type'],base64.b64decode(r['payload']['write_blob']))))
                      for r in sorted(items,key=lambda r:r['document']['metadata']['idx'])]
            saver.put_writes({'configurable':{'thread_id':sid,'checkpoint_ns':ns,'checkpoint_id':checkpoint_id}},values,task_id)
            imported['write'] += len(values)
    return {'imported':dict(imported), 'existing':dict(existing), 'backup_only':dict(archived)}


def main():
    load_dotenv()
    from common.env_sanitize import sanitize_no_proxy
    sanitize_no_proxy()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, help='已保存的只读快照（校验 SHA256）')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--owner-email', default=os.getenv('PLATFORM_ADMIN_EMAIL'))
    args = parser.parse_args()
    initialize(); initialize_checkpoints()
    if args.snapshot:
        path = args.snapshot
        if hashlib.sha256(path.read_bytes()).hexdigest() != path.with_suffix('.sha256').read_text().strip():
            raise ValueError('快照校验失败')
        data = json.loads(path.read_text())
    else:
        path = data_dir() / 'migrations' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.json')
        data = snapshot(ContextDBClient(), path)
    report = {'snapshot':str(path), 'records':len(data['records']), 'cloud_writes':0}
    if args.apply:
        with connection() as conn:
            owner = conn.execute('SELECT id,contextdb_member_id FROM platform_users WHERE email=%s AND active', (args.owner_email,)).fetchone()
        if not owner or not owner['contextdb_member_id']:
            raise RuntimeError('迁移目标必须是已绑定 ContextDB 成员的有效平台账号')
        report.update(import_snapshot(data, owner['id']))
    output = path.with_suffix('.report.json')
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
