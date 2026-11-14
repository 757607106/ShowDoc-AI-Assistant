"""Platform task state and capture provenance; knowledge processing uses official ContextDB APIs."""
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from integrations.contextdb import ContextDBClient


GOVERNANCE_KB_ENV = 'CONTEXTDB_GOVERNANCE_KB'
DEFAULT_GOVERNANCE_KB = '_governance'
TEXT_BODY_LIMIT = 150_000
METADATA_TEXT_LIMIT = 4000

# 任务易变字段:全部镜像进文档 metadata(读路径由 metadata 覆盖 body)
JOB_VOLATILE_KEYS = (
    'status', 'phase', 'progress', 'message', 'current_item', 'total_pages', 'completed_pages',
    'failed_pages', 'skipped_pages', 'cancel_requested', 'attempt_token', 'attempt_started_at',
    'end_time', 'capture_complete', 'zip_file', 'updated_at', 'start_time',
)
# 任务定位字段:常驻 metadata
JOB_LOCATOR_KEYS = ('job_id', 'scope', 'kind', 'entry', 'retry_of', 'collection_id', 'version_id', 'document_id')


def now():
    return datetime.now(timezone.utc).isoformat()


def data_dir():
    return Path(os.getenv('GOVERNANCE_DATA_DIR', 'downloads')).resolve()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def source_scope(entry, params):
    if entry == 'showdoc':
        return f"showdoc:{params.get('item_id', '')}"
    if entry == 'web':
        return f"web:{urlsplit(params.get('url', '')).netloc.lower()}"
    return entry


def safe_name(value):
    return str(value).replace(':', '_').replace('/', '_')[:180]


class StoreError(ValueError):
    def __init__(self, message, status=409):
        super().__init__(message)
        self.status = status


class Store:
    """Platform tasks and capture provenance in PostgreSQL; published assets in ContextDB."""

    def __init__(self, client=None, kb_name=None, owner_id=None):
        self.client = client or ContextDBClient()
        self.kb_name = kb_name or os.getenv(GOVERNANCE_KB_ENV, DEFAULT_GOVERNANCE_KB)
        self.owner_id = owner_id
        self.active_attempt = None

    def initialize(self):
        from governance.database import initialize
        initialize()

    def _list(self, condition, *, sort_by=None, sort_order=None, limit=None):
        from governance.database import connection
        from psycopg.types.json import Jsonb
        condition = dict(condition)
        if self.owner_id is not None:
            condition['owner_id'] = self.owner_id
        order = {'name': 'name', 'updated_at': 'updated_at', 'created_at': 'created_at'}.get(sort_by, 'created_at')
        direction = 'ASC' if sort_order == 'asc' else 'DESC'
        query = f'SELECT * FROM runtime_records WHERE metadata @> %s ORDER BY {order} {direction}, id'
        params = [Jsonb(condition)]
        if limit is not None:
            query += ' LIMIT %s'
            params.append(int(limit))
        with connection() as conn:
            return [self._record(row) for row in conn.execute(query, params)]

    @staticmethod
    def _record(row):
        return {'id': row['id'], 'name': row['name'], 'metadata': row['metadata'],
                'created_at': row['created_at'].isoformat(), 'updated_at': row['updated_at'].isoformat()}

    def _find(self, kind, **condition):
        records = self._list({'type': kind, **condition}, limit=1)
        return records[0] if records else None

    def _body(self, document_id, *, cache_key=None, updated_at=None):
        from governance.database import connection
        with connection() as conn:
            row = conn.execute('SELECT payload, owner_id FROM runtime_records WHERE id = %s', (document_id,)).fetchone()
        if row is None or (self.owner_id is not None and row['owner_id'] != self.owner_id):
            raise StoreError('平台记录不存在', 404)
        payload = row['payload']
        if '_capture_path' in payload:
            path = Path(payload['_capture_path'])
            if not path.is_relative_to(data_dir()):
                raise StoreError('采集快照路径无效', 409)
            return json.loads(path.read_text(encoding='utf-8'))
        return payload

    def _write(self, document_id, payload, metadata=None, *, cache_key=None):
        from governance.database import connection
        from psycopg.types.json import Jsonb
        with connection() as conn:
            row = conn.execute('SELECT owner_id, metadata FROM runtime_records WHERE id = %s FOR UPDATE', (document_id,)).fetchone()
            if row is None or (self.owner_id is not None and row['owner_id'] != self.owner_id):
                raise StoreError('平台记录不存在', 404)
            if row['metadata'].get('type') == 'job':
                self._guard_doc({'metadata': row['metadata']}, row['metadata'].get('job_id'))
            conn.execute('UPDATE runtime_records SET payload = %s, updated_at = now() WHERE id = %s',
                         (Jsonb(payload), document_id))
            if metadata is not None:
                self._update_metadata_in(conn, document_id, metadata, row)

    def _create(self, kind, key, payload, metadata):
        from governance.database import connection
        from psycopg.types.json import Jsonb
        from psycopg.errors import UniqueViolation
        owner_id = metadata.get('owner_id') or self.owner_id or ''
        metadata = {**metadata, 'type': kind, 'owner_id': owner_id}
        record_id = str(uuid.uuid4())
        if kind == 'version':
            # Capture snapshots are source artifacts, never a local knowledge index or Wiki revision.
            path = data_dir() / 'captures' / (owner_id or 'legacy') / f'{key}.json'
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix('.json.part')
            temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
            temporary.replace(path)
            payload = {'_capture_path': str(path)}
        try:
            with connection() as conn:
                row = conn.execute(
                    'INSERT INTO runtime_records(id, owner_id, kind, record_key, name, payload, metadata) '
                    'VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *',
                    (record_id, owner_id, kind, str(key), f'{kind}-{key}.json', Jsonb(payload), Jsonb(metadata)),
                ).fetchone()
        except UniqueViolation as exc:
            raise StoreError('平台记录已存在', 409) from exc
        return self._record(row)

    def _update_metadata_in(self, conn, document_id, metadata, row):
        from psycopg.types.json import Jsonb
        current = row['metadata']
        if current.get('type') == 'job':
            self._guard_doc({'metadata': current}, current.get('job_id'))
        metadata = {**metadata, 'owner_id': row['owner_id']}
        if current.get('cancel_requested'):
            metadata['cancel_requested'] = True
            if current.get('status') == 'cancelling' and metadata.get('status') == 'running':
                metadata['status'] = 'cancelling'
        conn.execute('UPDATE runtime_records SET metadata = %s, updated_at = now() WHERE id = %s',
                     (Jsonb(metadata), document_id))

    def _update_metadata(self, metadata, *, document_id):
        from governance.database import connection
        with connection() as conn:
            row = conn.execute('SELECT owner_id, metadata FROM runtime_records WHERE id = %s FOR UPDATE', (document_id,)).fetchone()
            if row is None or (self.owner_id is not None and row['owner_id'] != self.owner_id):
                raise StoreError('平台记录不存在', 404)
            self._update_metadata_in(conn, document_id, metadata, row)

    def _delete(self, document_id):
        from governance.database import connection
        with connection() as conn:
            if self.owner_id is None:
                conn.execute('DELETE FROM runtime_records WHERE id = %s', (document_id,))
            else:
                conn.execute('DELETE FROM runtime_records WHERE id = %s AND owner_id = %s', (document_id, self.owner_id))

    def _drop_cache(self, cache_key):
        pass

    @staticmethod
    def _meta_text(value, limit=METADATA_TEXT_LIMIT):
        if value is None:
            return ''
        if isinstance(value, (int, float, bool)):
            return value
        return str(value)[:limit]

    # ---------- 任务 ----------

    def _job_metadata(self, payload):
        metadata = {'type': 'job'}
        for key in JOB_LOCATOR_KEYS:
            value = payload.get(key)
            if key == 'job_id' and value is None:
                value = payload.get('task_id')
            if value is not None:
                metadata[key] = self._meta_text(value)
        for key in JOB_VOLATILE_KEYS:
            value = payload.get(key)
            if value is not None:
                metadata[key] = self._meta_text(value)
        return metadata

    def create_job(self, entry, params=None, selected_ids=None, selected_titles=None,
                   retry_of=None, kind='crawl', scope=None, version_id=None,
                   document_id=None, revision_reason='', applicability=None):
        params = params or {}
        job_id = str(uuid.uuid4())
        payload = {
            'task_id': job_id, 'entry': entry, 'params': params,
            'selected_ids': selected_ids or [], 'selected_titles': selected_titles or [],
            'retry_of': retry_of, 'kind': kind, 'version_id': version_id,
            'collection_id': job_id,
            'document_id': document_id, 'revision_reason': revision_reason,
            'applicability': applicability or {}, 'source_key': source_scope(entry, params),
            'phase': 'queued', 'progress': 0, 'total_pages': 0, 'completed_pages': 0,
            'failed_pages': 0, 'skipped_pages': 0, 'current_item': '',
            'message': '任务已入队,等待 worker', 'start_time': now(), 'end_time': None,
            'output_dir': str(data_dir() / 'jobs' / job_id), 'zip_file': None,
            'summary': {}, 'logs': [], 'cancel_requested': False,
            'status': 'pending', 'scope': scope or 'default', 'owner_id': self.owner_id or '',
        }
        if retry_of:
            previous = self.get_job(retry_of)
            payload['collection_id'] = previous.get('collection_id', retry_of)
        if version_id and document_id:
            original = self.get_document(version_id)
            payload['source_key'] = original.get('source_key', payload['source_key'])
        self._create('job', job_id, payload, self._job_metadata(payload))
        # 新建文档的列表索引存在秒级滞后,直接返回本地载荷避免回读落空
        return dict(payload)

    def _job_from_doc(self, doc):
        metadata = doc.get('metadata', {})
        job_id = metadata.get('job_id')
        payload = dict(self._body(doc['id'], cache_key=f"job:{job_id}", updated_at=doc.get('updated_at')))
        for key in JOB_VOLATILE_KEYS:
            if key in metadata:
                payload[key] = metadata[key]
        for key in JOB_LOCATOR_KEYS:
            if key in metadata:
                payload[key] = metadata[key]
        return payload

    def _find_job_doc(self, job_id):
        """任务文档读取带短重试:新建任务的列表索引有秒级滞后。"""
        deadline = time.monotonic() + 3.0
        while True:
            doc = self._find('job', job_id=job_id)
            if doc:
                return doc
            if time.monotonic() >= deadline:
                raise StoreError('任务不存在', 404)
            time.sleep(0.5)

    def get_job(self, job_id):
        doc = self._find_job_doc(job_id)
        return self._job_from_doc(doc)

    def list_jobs(self):
        documents = self._list({'type': 'job'}, sort_by='created_at', sort_order='desc', limit=50)
        return [self._job_from_doc(doc) for doc in documents]

    def _guard_doc(self, doc, job_id):
        if not self.active_attempt:
            return
        held_id, token = self.active_attempt
        if held_id != job_id or doc['metadata'].get('attempt_token') != token:
            raise StoreError('任务执行权已失效,停止写入')

    def update_job(self, job_id, *, status=None, **changes):
        doc = self._find_job_doc(job_id)
        self._guard_doc(doc, job_id)
        volatile_only = set(changes) <= set(JOB_VOLATILE_KEYS)
        if volatile_only and status is not None:
            # 纯易变字段翻转走 metadata 快通道:无需正文重写,也避开写后短暂不稳窗口
            metadata = dict(doc['metadata'])
            merged = {**metadata, **changes, 'status': status, 'updated_at': now()}
            for key, value in self._job_metadata(merged).items():
                metadata[key] = value
            self._update_metadata(metadata, document_id=doc['id'])
            self._drop_cache(f"job:{job_id}")
            return
        payload = dict(self._body(doc['id'], cache_key=f"job:{job_id}", updated_at=doc.get('updated_at')))
        payload.update(changes)
        if status is not None:
            payload['status'] = status
        # metadata 一律以「当前值+本次变更」构造:body 中的易变字段是创建时的陈旧副本,禁止回流
        metadata = dict(doc['metadata'])
        for key, value in changes.items():
            if key in JOB_VOLATILE_KEYS or key in JOB_LOCATOR_KEYS:
                metadata[key] = self._meta_text(value)
        if status is not None:
            metadata['status'] = status
        metadata['updated_at'] = now()
        self._write(doc['id'], payload, metadata, cache_key=f"job:{job_id}")

    def log(self, job_id, message, **changes):
        doc = self._find_job_doc(job_id)
        self._guard_doc(doc, job_id)
        payload = dict(self._body(doc['id'], cache_key=f"job:{job_id}", updated_at=doc.get('updated_at')))
        logs = payload.get('logs', [])
        if not logs or logs[-1].get('message') != message:
            logs = (logs + [{'time': now(), 'message': str(message)[:METADATA_TEXT_LIMIT]}])[-120:]
        payload.update(changes)
        payload['logs'] = logs
        payload['message'] = str(message)[:METADATA_TEXT_LIMIT]
        metadata = dict(doc['metadata'])
        for key, value in {**changes, 'message': str(message)[:METADATA_TEXT_LIMIT]}.items():
            if key in JOB_VOLATILE_KEYS or key in JOB_LOCATOR_KEYS:
                metadata[key] = self._meta_text(value)
        metadata['updated_at'] = now()
        self._write(doc['id'], payload, metadata, cache_key=f"job:{job_id}")

    def cancel(self, job_id):
        doc = self._find_job_doc(job_id)
        status = doc['metadata'].get('status')
        if status not in {'pending', 'running', 'cancelling'}:
            raise StoreError('任务已经结束')
        pending = status == 'pending'
        metadata = dict(doc['metadata'])
        metadata['cancel_requested'] = True
        metadata['message'] = '任务已取消' if pending else '正在安全停止任务'
        if pending:
            metadata['status'] = 'cancelled'
            metadata['phase'] = 'cancelled'
            metadata['end_time'] = now()
        else:
            metadata['status'] = 'cancelling'
        # 易变状态翻转走 metadata 快通道,无需重写正文
        self._update_metadata(metadata, document_id=doc['id'])
        self._drop_cache(f"job:{job_id}")

    def guard_attempt(self):
        if not self.active_attempt:
            return
        job_id, token = self.active_attempt
        doc = self._find_job_doc(job_id)
        if doc['metadata'].get('attempt_token') != token:
            raise StoreError('任务执行权已失效,停止写入')

    def claim(self):
        from governance.database import connection
        from psycopg.types.json import Jsonb
        with connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtext('showdoc-worker-claim'))")
            running = conn.execute("SELECT 1 FROM runtime_records WHERE kind = 'job' AND metadata->>'status' IN ('running', 'cancelling') LIMIT 1").fetchone()
            if running:
                return None
            row = conn.execute("SELECT * FROM runtime_records WHERE kind = 'job' AND metadata->>'status' = 'pending' ORDER BY created_at, id FOR UPDATE SKIP LOCKED LIMIT 1").fetchone()
            if row is None:
                return None
            metadata = {**row['metadata'], 'status': 'running', 'attempt_token': str(uuid.uuid4()),
                        'attempt_started_at': now(), 'updated_at': now()}
            conn.execute('UPDATE runtime_records SET metadata = %s, updated_at = now() WHERE id = %s', (Jsonb(metadata), row['id']))
            payload = {**row['payload'], **metadata}
            payload['task_id'] = metadata['job_id']
            return payload

    def release_claim(self, job_id):
        doc = self._find('claim', job_id=job_id)
        if doc:
            try:
                self._delete(doc['id'])
            except StoreError:
                pass

    def recover_jobs(self, *, reset_all=False):
        """恢复孤儿任务;监督者启动后 reset_all=True(前任监督者必已死亡,运行态任务皆孤儿)。"""
        timeout = int(os.getenv('GOVERNANCE_JOB_TIMEOUT', '1800'))
        for status in ('running', 'cancelling'):
            for doc in self._list({'type': 'job', 'status': status}):
                metadata = doc['metadata']
                job_id = metadata.get('job_id')
                started = metadata.get('attempt_started_at')
                expired = False
                if started:
                    try:
                        expired = (datetime.now(timezone.utc) - datetime.fromisoformat(started)).total_seconds() > timeout
                    except ValueError:
                        expired = True
                if not reset_all and not expired:
                    continue
                new_status = 'cancelled' if status == 'cancelling' else 'failed'
                merged = {
                    **metadata,
                    'status': new_status,
                    'message': '处理超时,请重试已保存的阶段产物' if expired else 'worker 重启,恢复已保存的阶段产物',
                    'phase': new_status, 'end_time': now(), 'updated_at': now(),
                }
                # ContextDB metadata 值不允许 null:清空即删键
                merged.pop('attempt_token', None)
                merged.pop('attempt_started_at', None)
                self._update_metadata(merged, document_id=doc['id'])
                self._drop_cache(f"job:{job_id}")
                self.release_claim(job_id)

    def heartbeat(self):
        doc = self._find('heartbeat')
        if doc is None:
            self._create('heartbeat', 'worker', {'type': 'heartbeat'},
                         {'type': 'heartbeat', 'heartbeat_at': now(), 'updated_at': now()})
            return
        metadata = dict(doc['metadata'])
        metadata.update(heartbeat_at=now(), updated_at=now())
        self._update_metadata(metadata, document_id=doc['id'])

    def worker_alive(self):
        doc = self._find('heartbeat')
        if not doc:
            return False
        heartbeat_at = doc['metadata'].get('heartbeat_at') or doc.get('updated_at')
        if not heartbeat_at:
            return False
        try:
            return (datetime.now(timezone.utc) - datetime.fromisoformat(heartbeat_at)).total_seconds() <= 90
        except ValueError:
            return False

    # ---------- 语料与版本 ----------

    def _scope_doc(self, scope):
        return self._find('scope', scope=scope)

    def _scope_generation(self, scope_doc):
        if not scope_doc:
            return 0
        try:
            return int(scope_doc['metadata'].get('generation', 0))
        except (TypeError, ValueError):
            return 0

    def ingest(self, job, documents, sources, chunks):
        scope = job['scope']
        changed = False
        document_chunks = {}
        for chunk in chunks:
            document_chunks.setdefault(str(chunk.get('document_id')), []).append(chunk)
        self.guard_attempt()
        scope_doc = self._scope_doc(scope)
        if scope_doc is None:
            scope_doc = self._create('scope', scope, {'scope': scope},
                                     {'type': 'scope', 'scope': scope, 'generation': 0})
        created_version_ids = []
        for record in documents:
            record = dict(record)
            record['metadata'] = {**record.get('metadata', {}), 'scope': job.get('applicability', {})}
            if job.get('document_id') and job.get('version_id'):
                original = self.get_document(job['version_id'])
                if original['scope'] != scope:
                    raise StoreError('修订文档不属于当前业务空间', 409)
                record['title'] = original['title']
                record['category'] = original.get('category', '')
            source = sources.get(str(record['id']), {})
            record['source_format'] = source.get('source_format') or record.get('source_format', '')
            legacy_id = digest([self.owner_id, job['source_key'], str(record['id'])])
            legacy_doc = self._find('doc', doc_id=legacy_id, scope=scope)
            # Reuse existing IDs; new captures must not share versions across business spaces.
            doc_id = job.get('document_id') or (legacy_id if legacy_doc else
                digest([self.owner_id, scope, job['source_key'], str(record['id'])]))
            identity_metadata = {k: record['metadata'].get(k) for k in ('scope', 'content_source_field', 'content_completeness')}
            identity_metadata['conversion'] = record['metadata'].get('conversion', {}).get('fingerprint')
            version_id = digest([doc_id, source.get('source_sha256') or digest(source),
                                 identity_metadata, record.get('title'), record.get('category'), record.get('content', '')])
            payload = {
                **record, 'id': doc_id, 'source_record_id': str(record['id']),
                'version_id': version_id, 'source': source,
                'artifact_dir': job['output_dir'], 'job_id': job['task_id'],
                'source_key': job['source_key'],
                'chunks': document_chunks.get(str(record['id']), []),
                'revision_of': job.get('version_id'), 'revision_reason': job.get('revision_reason', ''),
            }
            existing_version = self._find('version', version_id=version_id)
            old_doc_record = self._find('doc', doc_id=doc_id)
            if job.get('document_id') and old_doc_record and old_doc_record['metadata'].get('current_version') not in {job['version_id'], version_id}:
                raise StoreError('修订基于旧版本,请在当前文档上重新修订')
            changed = changed or old_doc_record is None or old_doc_record['metadata'].get('current_version') != version_id
            previous_current = old_doc_record['metadata'].get('current_version') if old_doc_record else None
            if existing_version is None:
                version_metadata = {
                    'type': 'version', 'version_id': version_id, 'doc_id': doc_id, 'scope': scope,
                    'job_id': job['task_id'], 'is_current': True,
                    'title': self._meta_text(record.get('title', ''), 200),
                    'category': self._meta_text(record.get('category', ''), 100),
                    'source_format': self._meta_text(record.get('source_format', ''), 40),
                }
                self._create('version', version_id, payload, version_metadata)
                created_version_ids.append(version_id)
            else:
                version_metadata = dict(existing_version['metadata'])
                version_metadata['is_current'] = True
                self._update_metadata(version_metadata, document_id=existing_version['id'])
            if previous_current and previous_current != version_id:
                previous_doc = self._find('version', version_id=previous_current)
                if previous_doc is not None:
                    previous_metadata = dict(previous_doc['metadata'])
                    previous_metadata['is_current'] = False
                    self._update_metadata(previous_metadata, document_id=previous_doc['id'])
            doc_metadata = {
                'type': 'doc', 'doc_id': doc_id, 'scope': scope,
                'current_version': version_id,
                'title': self._meta_text(record.get('title', ''), 200),
            }
            if old_doc_record is None:
                self._create('doc', doc_id, {'doc_id': doc_id}, doc_metadata)
            else:
                self._update_metadata(doc_metadata, document_id=old_doc_record['id'])
            if self._find('jobdoc', jobdoc_id=f"{job['task_id']}-{version_id}") is None:
                self._create('jobdoc', f"{job['task_id']}-{version_id}",
                             {'job_id': job['task_id'], 'version_id': version_id},
                             {'type': 'jobdoc', 'jobdoc_id': f"{job['task_id']}-{version_id}",
                              'job_id': job['task_id'], 'version_id': version_id})
        if changed:
            generation = self._scope_generation(scope_doc) + 1
            scope_metadata = dict(scope_doc['metadata'])
            scope_metadata['generation'] = generation
            self._update_metadata(scope_metadata, document_id=scope_doc['id'])
        return changed

    def list_documents(self, job_id=None):
        if job_id:
            links = self._list({'type': 'jobdoc', 'job_id': job_id})
            wanted = {link['metadata'].get('version_id') for link in links}
            versions = [v for v in self._list({'type': 'version'}, sort_by='created_at', sort_order='desc')
                        if v['metadata'].get('version_id') in wanted]
        else:
            versions = self._list({'type': 'version', 'is_current': True},
                                  sort_by='created_at', sort_order='desc', limit=200)
        output = []
        for version in versions:
            metadata = version['metadata']
            output.append({
                'id': metadata.get('doc_id'), 'version_id': metadata.get('version_id'),
                'title': metadata.get('title', ''), 'category': metadata.get('category', ''),
                'updated_at': version.get('updated_at'), 'job_id': metadata.get('job_id'),
                'source_format': metadata.get('source_format', ''),
                'is_current': bool(metadata.get('is_current')),
            })
        return output

    def get_document(self, version_id):
        version_doc = self._find('version', version_id=version_id)
        if not version_doc:
            raise StoreError('文档版本不存在', 404)
        metadata = version_doc['metadata']
        payload = self._body(version_doc['id'], cache_key=f"version:{version_id}",
                              updated_at=version_doc.get('updated_at'))
        doc_record = self._find('doc', doc_id=metadata.get('doc_id'))
        versions = [{'version_id': sibling['metadata'].get('version_id'), 'created_at': sibling.get('created_at')}
                    for sibling in self._list({'type': 'version', 'doc_id': metadata.get('doc_id')},
                                              sort_by='created_at', sort_order='desc')]
        current = doc_record['metadata'].get('current_version') if doc_record else None
        return {**payload, 'scope': metadata.get('scope'), 'versions': versions,
                'is_current': current == version_id}

    # ---------- 发布 ----------

    def release_inputs(self, job_id):
        job_doc = self._find('job', job_id=job_id)
        if not job_doc:
            raise StoreError('任务不存在', 404)
        if job_doc['metadata'].get('status') != 'completed':
            raise StoreError('任务未完整完成,不能提交治理')
        scope = job_doc['metadata'].get('scope')
        scope_doc = self._scope_doc(scope)
        generation = self._scope_generation(scope_doc)
        latest_imports = {}
        for imported in self._list({'type': 'job', 'scope': scope, 'kind': 'crawl'}, sort_by='created_at', sort_order='asc'):
            request = self._body(imported['id'])
            collection = digest([request['entry'], request.get('params', {}),
                sorted(str(value) for value in request.get('selected_ids', [])),
                sorted(request.get('selected_titles', []))])
            latest_imports[collection] = imported
        links = self._list({'type': 'jobdoc'})
        for imported in latest_imports.values():
            if imported['metadata'].get('capture_complete'):
                continue
            collection_id = imported['metadata'].get('collection_id') or imported['metadata'].get('job_id')
            if imported['metadata'].get('status') == 'cancelled':
                job_ids = {collection_id, imported['metadata'].get('job_id')}
                if not any(link for link in links if link['metadata'].get('job_id') in job_ids):
                    # 被取消的空队列项从未进入知识库
                    continue
            raise StoreError('存在未完整采集的数据源任务，请先完成或重试')
        version_docs = self._list({'type': 'version', 'scope': scope, 'is_current': True},
                                  sort_by='name', sort_order='asc')
        if not version_docs:
            raise StoreError('语料为空,不能提交治理')
        documents = []
        for version_doc in version_docs:
            version_id = version_doc['metadata'].get('version_id')
            payload = self._body(version_doc['id'], cache_key=f"version:{version_id}",
                                 updated_at=version_doc.get('updated_at'))
            source_file = payload.get('source', {}).get('source_path')
            if (not str(payload.get('content', '')).strip() and not source_file) or payload.get('metadata', {}).get('conversion_error') or payload.get('metadata', {}).get('fetch_error'):
                raise StoreError('存在格式处理失败或空正文的当前文档,不能提交治理')
            documents.append(payload)
        return scope, generation, documents

    def create_release(self, job_id, scope, generation, version_ids, archive_path, release_id=None):
        """登记发布记录并置为当前激活版本(同 scope 旧发布自动去激活)。"""
        from governance.database import connection
        with connection() as conn:
            conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',
                         (f'sync-delivery:{self.owner_id}:{scope}',))
            release_id = release_id or str(uuid.uuid4())
            for other in self._list({'type': 'release', 'scope': scope}):
                if other['metadata'].get('active'):
                    metadata = dict(other['metadata'])
                    metadata['active'] = False
                    self._update_metadata(metadata, document_id=other['id'])
            self._create('release', release_id,
                         {'version_ids': list(version_ids), 'job_id': job_id, 'scope': scope},
                         {'type': 'release', 'release_id': release_id, 'job_id': job_id, 'scope': scope,
                          'generation': generation, 'archive_path': str(archive_path)[:METADATA_TEXT_LIMIT],
                          'active': True, 'created_at': now(), 'updated_at': now()})
            return release_id

    def list_releases(self):
        releases = self._list({'type': 'release'}, sort_by='created_at', sort_order='desc', limit=50)
        output = []
        for release in releases:
            metadata = release['metadata']
            body = self._body(release['id'])
            output.append({'id': metadata.get('release_id'), 'job_id': metadata.get('job_id'),
                           'scope': metadata.get('scope'), 'generation': metadata.get('generation'),
                           'version_ids': body.get('version_ids', []),
                           'active': bool(metadata.get('active')),
                           'created_at': release.get('created_at')})
        return output

    def get_release(self, release_id):
        release = self._find('release', release_id=release_id)
        if not release:
            raise StoreError('提交记录不存在', 404)
        metadata = release['metadata']
        body = self._body(release['id'])
        return {'id': metadata.get('release_id'), 'job_id': metadata.get('job_id'),
                'scope': metadata.get('scope'), 'generation': metadata.get('generation'),
                'version_ids': body.get('version_ids', []),
                'archive_path': metadata.get('archive_path', ''),
                'active': bool(metadata.get('active')),
                'created_at': release.get('created_at')}

    def activate_release(self, release_id):
        release = self._find('release', release_id=release_id)
        if not release:
            raise StoreError('提交记录不存在', 404)
        scope = release['metadata'].get('scope')
        from governance.database import connection
        with connection() as conn:
            conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',
                         (f'sync-delivery:{self.owner_id}:{scope}',))
            for other in self._list({'type': 'release', 'scope': scope}):
                target = other['metadata'].get('release_id') == release_id
                if target or other['metadata'].get('active'):
                    metadata = dict(other['metadata'])
                    metadata['active'] = target
                    self._update_metadata(metadata, document_id=other['id'])
