"""Upload immutable captures to paired official Wiki/graph libraries.

PostgreSQL stores identities and delivery status only. ContextDB owns review,
parsing, compilation, graph construction and their authoritative states.
"""
import hashlib
import json
import mimetypes
import os
import tempfile
from pathlib import Path
from zipfile import ZipFile

from governance.database import connection
from governance.store import StoreError, now, safe_name
from integrations.contextdb import ContextDBConflictError, ContextDBError

REVIEW_HIGH_THRESHOLD = 0.85


def knowledge_kb_name(scope, mode='wiki'):
    explicit = os.getenv('CONTEXTDB_KB_ID' if mode == 'wiki' else 'CONTEXTDB_GRAPH_KB_ID', '').strip()
    return explicit or f"knowledge-{safe_name(scope)}" + ('-graph' if mode == 'graph' else '')


def enqueue_sync(store, release_id, scope, *, target_modes=None, retry_of=None):
    from governance.spaces import get_space, persist_space, require_no_active_sync
    with connection() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (f'space:{store.owner_id}:{scope}',))
        space = get_space(store, scope)
        modes = ['wiki', 'graph'] if space['graph_enabled'] else ['wiki']
        if target_modes is not None:
            if not target_modes or any(mode not in modes for mode in target_modes):
                raise StoreError('目标未在当前业务空间启用', 409)
            modes = list(dict.fromkeys(target_modes))
        if any(space['targets'][mode]['status'] == 'missing' for mode in modes):
            require_no_active_sync(store, scope)
        persist_space(store, space)
        params = {'release_id': release_id, 'target_modes': modes,
                  'target_ids': {mode: space.get(mode + '_kb_id') for mode in modes}}
        return store.create_job('contextdb', params, kind='ctxdb_sync', scope=scope, retry_of=retry_of)


def _target(store, scope, mode, target_id=None):
    from governance.spaces import get_space, bind_target
    with connection() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',
                     (f'space-target:{store.owner_id}:{scope}:{mode}',))
        client = store.client
        space = get_space(store, scope)
        configured = space.get(mode + '_kb_id')
        if target_id and configured and target_id != configured:
            raise StoreError('任务的目标知识库映射已改变，请重新提交当前批次', 409)
        suffix = hashlib.sha256(f'{store.owner_id or ""}:{scope}'.encode()).hexdigest()[:12]
        name = (f"knowledge-{safe_name(scope)}" if space.get('legacy') else
                f"knowledge-{safe_name(scope)}-{suffix}") + ('-graph' if mode == 'graph' else '')
        explicit = target_id or configured
        kb = client.get_knowledge_base(explicit) if explicit else client.find_knowledge_base(name)
        if kb is None:
            kb = client.create_knowledge_base(name, description=f'采集范围 {scope} · {mode}',
                wiki_enabled=mode == 'wiki', graph_enabled=mode == 'graph', review_enabled=True)
            client.update_review_settings(kb['id'], high_threshold=REVIEW_HIGH_THRESHOLD,
                                          rewrite_auto_ingest_enabled=False)
        if bool(kb.get('wiki_enabled')) != (mode == 'wiki') or bool(kb.get('graph_enabled')) != (mode == 'graph'):
            raise StoreError(f'{mode} 目标库的官方模式不匹配，请检查配置', 409)
        bind_target(store, scope, mode, kb['id'])
        return kb


def _save(owner, scope, source, mode, kb, **fields):
    with connection() as conn:
        conn.execute('''INSERT INTO knowledge_sync(owner_id,scope,source_id,target_mode,knowledge_base_id,status)
            VALUES (%s,%s,%s,%s,%s,'pending') ON CONFLICT DO NOTHING''', (owner, scope, source, mode, kb))
        if fields:
            allowed = {'document_id', 'source_hash', 'source_version', 'status', 'event_id', 'error'}
            assert set(fields) <= allowed
            clause = ','.join(f'{key}=%s' for key in fields)
            updated = conn.execute(f'''UPDATE knowledge_sync SET {clause},updated_at=now()
                WHERE owner_id=%s AND scope=%s AND source_id=%s AND target_mode=%s
                AND knowledge_base_id=%s''',
                (*fields.values(), owner, scope, source, mode, kb))
            if updated.rowcount != 1:
                raise StoreError('目标知识库映射已改变，旧任务不能覆盖新投递回执', 409)


def _mapping(owner, scope, source, mode):
    with connection() as conn:
        return conn.execute('SELECT * FROM knowledge_sync WHERE owner_id=%s AND scope=%s AND source_id=%s AND target_mode=%s',
                            (owner, scope, source, mode)).fetchone()


def _find_document(client, kb, name, scope):
    page = 1
    while True:
        result = client.list_documents(kb, page=page, page_size=100)
        items = result.get('documents', [])
        for doc in items:
            if doc.get('name') == name and doc.get('file_path', '') == scope:
                return doc
        if len(items) < 100:
            return None
        page += 1


def _document_metadata(record, scope, source, digest, existing=None):
    metadata = dict(existing or {})
    captured = record.get('metadata') or {}
    applicability = captured.get('scope') or {}
    # These fields follow the capture; unrelated cloud annotations stay intact.
    for key in ('product', 'version', 'role', 'url', 'filename'):
        metadata.pop(key, None)
        value = applicability.get(key) if key in ('product', 'version', 'role') else captured.get(key)
        if value:
            metadata[key] = value
    metadata.update(source='crawler', governance_scope=scope[:200], platform_source_id=source[:200],
                    source_version=str(record.get('version_id', ''))[:200], source_content_hash=digest,
                    title=str(record.get('title', ''))[:200])
    return metadata


def _deliver(store, record, archive, mode, kb, scope):
    owner = store.owner_id or ''
    source = str(record['id'])
    name = f"doc-{safe_name(source)}"
    if record.get('archive_source'):
        name += Path(record['archive_source']).suffix
        content = archive.read(record['archive_source'])
    else:
        name += {'html': '.html', 'text': '.txt', 'markdown': '.md'}.get(record.get('source_format'), '.md')
        content = record.get('content', '').encode('utf-8')
    if not content.strip():
        raise StoreError(f'源文档为空: {source}', 422)
    digest = hashlib.sha256(content).hexdigest()
    row = _mapping(owner, scope, source, mode)
    if row and row['knowledge_base_id'] != kb['id']:
        from governance.spaces import missing_knowledge_base
        try:
            store.client.get_knowledge_base(row['knowledge_base_id'])
        except ContextDBError as exc:
            if not missing_knowledge_base(exc):
                raise
        else:
            raise StoreError('目标知识库映射已改变，需要独立迁移后重试', 409)
        history_key = hashlib.sha256(json.dumps([owner, scope, source, mode, row['knowledge_base_id']]).encode()).hexdigest()
        if not store._find('knowledge_sync_history', sync_key=history_key):
            history = {**row, 'updated_at': row['updated_at'].isoformat()}
            store._create('knowledge_sync_history', history_key, history,
                          {'scope': scope, 'target_mode': mode, 'sync_key': history_key})
        with connection() as conn:
            row = conn.execute('''UPDATE knowledge_sync SET knowledge_base_id=%s, document_id=NULL,
                source_hash=NULL, source_version=NULL, status='pending', event_id=NULL, error=NULL, updated_at=now()
                WHERE owner_id=%s AND scope=%s AND source_id=%s AND target_mode=%s AND knowledge_base_id=%s
                RETURNING *''', (kb['id'], owner, scope, source, mode, row['knowledge_base_id'])).fetchone()
            if row is None:
                raise StoreError('目标知识库映射已改变，请刷新后重试', 409)
    doc = None
    if row and row['document_id']:
        doc = store.client.get_document(kb['id'], row['document_id'])
    elif row:
        doc = _find_document(store.client, kb['id'], name, scope)
        if doc is None and row['status'] in ('uploading', 'uncertain'):
            raise StoreError('上次上传结果未知，官方列表尚未返回该文档；请核实后重试，防止重复提交', 409)
    unchanged = doc and (doc.get('metadata', {}).get('source_content_hash') == digest or
                         (row and row['source_hash'] == digest and row['source_version'] == str(record.get('version_id', ''))))
    if not unchanged and row and row['status'] in ('uploading', 'uncertain'):
        raise StoreError('上次写入结果未知，官方文档尚未确认目标内容版本；请核实后重试，防止覆盖或重复提交', 409)
    metadata = _document_metadata(record, scope, source, digest, doc.get('metadata') if doc else None)
    metadata_changed = doc is not None and metadata != doc.get('metadata', {})
    try:
        if unchanged:
            result = doc
            if metadata_changed:
                result = {**doc, **store.client.update_document_metadata(metadata, document_id=doc['id'])}
        else:
            _save(owner, scope, source, mode, kb['id'], status='uploading', error=None)
            with tempfile.TemporaryDirectory(prefix='ctxdb-sync-') as directory:
                path = Path(directory) / name
                path.write_bytes(content)
                mime = mimetypes.guess_type(name)[0] or 'application/octet-stream'
                if doc:
                    result = store.client.update_file(doc['id'], name, path, metadata=metadata, mime_type=mime)
                else:
                    try:
                        result = store.client.upload_file(kb['id'], name, path, file_path=scope, metadata=metadata, mime_type=mime)
                    except ContextDBConflictError as exc:
                        if exc.error_code != 1003:
                            raise
                        existing = _find_document(store.client, kb['id'], name, scope)
                        if existing is None:
                            raise
                        metadata = _document_metadata(record, scope, source, digest, existing.get('metadata'))
                        result = store.client.update_file(existing['id'], name, path, metadata=metadata, mime_type=mime)
        _save(owner, scope, source, mode, kb['id'], document_id=result['id'], source_hash=digest,
              source_version=str(record.get('version_id', '')), status=result.get('ingest_status', 'unknown'),
              event_id=result.get('latest_ingest_event_id'), error=result.get('ingest_error_message'))
        return not unchanged or metadata_changed
    except Exception as exc:
        definite = isinstance(exc, ContextDBError) and exc.status_code is not None and 400 <= exc.status_code < 500
        _save(owner, scope, source, mode, kb['id'], status='rejected' if definite else 'uncertain', error=str(exc)[:1000])
        raise


def run_sync(store, job):
    release = store.get_release(job['params']['release_id'])
    if not release['active']:
        raise StoreError('该提交已被更新批次取代，请同步当前资料，避免覆盖新版本', 409)
    if not Path(release['archive_path']).is_file():
        raise StoreError('治理提交包缺失', 404)
    scope = release['scope']
    modes = job['params'].get('target_modes', ['wiki', 'graph'])
    if not isinstance(modes, list) or not modes or any(mode not in ('wiki', 'graph') for mode in modes):
        raise StoreError('治理任务目标无效', 409)
    targets, failures, stages = {}, [], {}
    for mode in modes:
        stages[mode] = {'uploaded': 0, 'skipped': 0, 'errors': [], 'status': 'pending'}
        try:
            targets[mode] = _target(store, scope, mode, job['params'].get('target_ids', {}).get(mode))
            stages[mode]['knowledge_base_id'] = targets[mode]['id']
        except Exception as exc:
            failures.append(f'{mode}: {exc}')
            stages[mode]['errors'].append(str(exc))
            stages[mode]['status'] = 'failed'
    uploaded = skipped = 0
    with ZipFile(release['archive_path']) as archive:
        records = [json.loads(line) for line in archive.read('rag_documents.jsonl').decode('utf-8').splitlines() if line.strip()]
        total = len(records) * len(modes)
        for mode, kb in targets.items():
            for record in records:
                store.guard_attempt()
                if store.get_job(job['task_id'])['cancel_requested']:
                    from crawlers.base import CrawlCancelled
                    raise CrawlCancelled('同步已取消')
                try:
                    with connection() as conn:
                        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',
                                     (f'sync-delivery:{store.owner_id}:{scope}',))
                        if not store.get_release(release['id'])['active']:
                            raise StoreError('该提交已被更新批次取代，停止写入旧内容', 409)
                        delivered = _deliver(store, record, archive, mode, kb, scope)
                    if delivered:
                        uploaded += 1
                        stages[mode]['uploaded'] += 1
                    else:
                        skipped += 1
                        stages[mode]['skipped'] += 1
                except Exception as exc:
                    failures.append(f'{mode}/{record["id"]}: {exc}')
                    stages[mode]['errors'].append(f'{record["id"]}: {exc}')
                stages[mode]['status'] = 'partial' if stages[mode]['errors'] else 'submitting'
                store.update_job(job['task_id'], summary={'targets': stages})
                store.log(job['task_id'], f'上传 {uploaded}，未变化 {skipped}，错误 {len(failures)}',
                          phase='syncing', completed_pages=uploaded+skipped, total_pages=total)
    for mode in targets:
        stages[mode]['status'] = 'partial' if stages[mode]['errors'] else 'submitted'
    store.update_job(job['task_id'], status='partial' if failures else 'completed', summary={'targets': stages},
        phase='partial' if failures else 'submitted', progress=int(100*(uploaded+skipped)/total) if total else 100,
        end_time=now(), failed_pages=len(failures), skipped_pages=skipped,
        message=('；'.join(failures)[:1400] if failures else '资料已提交治理；评审、入库、Wiki 编译与图谱构建请查看各目标官方处理状态'))
    return {'targets': {mode: kb['id'] for mode, kb in targets.items()}, 'uploaded': uploaded,
            'skipped': skipped, 'total': total, 'errors': failures}
