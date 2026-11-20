"""Upload immutable captures to one fixed ContextDB knowledge base.

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
from governance.import_directories import ImportDirectories
from governance.knowledge_names import captured_filename
from governance.store import StoreError, now, safe_name
from integrations.contextdb import ContextDBConflictError, ContextDBError


def knowledge_kb_name(scope, mode='wiki'):
    explicit = os.getenv('CONTEXTDB_KB_ID' if mode == 'wiki' else 'CONTEXTDB_GRAPH_KB_ID', '').strip()
    return explicit or f"knowledge-{safe_name(scope)}" + ('-graph' if mode == 'graph' else '')


def enqueue_sync(store, release_id, scope, *, target_modes=None, retry_of=None):
    from governance.spaces import require_writable_space
    from governance.knowledge_bases import base_write_lock
    target_id = require_writable_space(store, scope)['knowledge_base_id']
    with base_write_lock(target_id), connection() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (f'space:{store.owner_id}:{scope}',))
        space = require_writable_space(store, scope)
        if space['knowledge_base_id'] != target_id:
            raise StoreError('目标知识库映射已改变，请刷新后重试', 409)
        if target_modes is not None and target_modes != [space['mode']]:
            raise StoreError('一次提交只能使用该知识库的固定编译模式', 409)
        if store.get_release(release_id)['scope'] != scope:
            raise StoreError('提交批次不属于该知识库', 409)
        params = {'release_id': release_id, 'knowledge_base_id': space['knowledge_base_id'],
                  'target_mode': space['mode']}
        return store.create_job('contextdb', params, kind='ctxdb_sync', scope=scope, retry_of=retry_of)


def _target(store, scope, mode, target_id=None):
    from governance.spaces import require_writable_space
    space = require_writable_space(store, scope)
    if not target_id or target_id != space['knowledge_base_id'] or (mode == 'wiki') != (space['mode'] == 'wiki'):
        raise StoreError('任务的固定目标知识库或模式已改变，请重新提交当前批次', 409)
    kb = store.client.get_knowledge_base(target_id)
    if bool(kb.get('wiki_enabled')) != (mode == 'wiki'):
        raise StoreError('目标库的官方模式与提交记录不匹配', 409)
    return kb


def _save(owner, scope, source, mode, kb, **fields):
    with connection() as conn:
        conn.execute('''INSERT INTO knowledge_sync(owner_id,scope,source_id,target_mode,knowledge_base_id,status)
            VALUES (%s,%s,%s,%s,%s,'pending') ON CONFLICT DO NOTHING''', (owner, scope, source, mode, kb))
        if fields:
            allowed = {'document_id', 'source_hash', 'source_version', 'conversion_fingerprint', 'status', 'event_id', 'error'}
            assert set(fields) <= allowed
            clause = ','.join(f'{key}=%s' for key in fields)
            updated = conn.execute(f'''UPDATE knowledge_sync SET {clause},updated_at=now()
                WHERE owner_id=%s AND scope=%s AND source_id=%s AND target_mode=%s
                AND knowledge_base_id=%s''',
                (*fields.values(), owner, scope, source, mode, kb))
            if updated.rowcount != 1:
                raise StoreError('目标知识库映射已改变，旧任务不能覆盖新投递回执', 409)


def _mapping(owner, scope, source, kb_id):
    with connection() as conn:
        return conn.execute('SELECT * FROM knowledge_sync WHERE owner_id=%s AND scope=%s AND source_id=%s AND knowledge_base_id=%s',
                            (owner, scope, source, kb_id)).fetchone()


def _find_document(client, kb, name, scope, source=None):
    page = 1
    while True:
        result = client.list_documents(kb, page=page, page_size=100)
        items = result.get('documents', [])
        for doc in items:
            metadata = doc.get('metadata') or {}
            if (source is not None and metadata.get('platform_source_id') == source and
                    (metadata.get('governance_scope') == scope or doc.get('file_path', '') == scope)):
                return doc
            if doc.get('file_path', '') != scope:
                continue
            if source is None and doc.get('name', '').casefold() == name.casefold():
                return doc
        if len(items) < 100:
            return None
        page += 1


def _document_metadata(record, scope, source, digest, conversion_fingerprint, submitted_hash, existing=None):
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
                    source_conversion_fingerprint=conversion_fingerprint,
                    title=str(record.get('title', ''))[:200])
    filename = captured_filename(record)
    if filename:
        metadata['filename'] = filename
    if submitted_hash is not None:
        metadata['submitted_content_hash'] = submitted_hash
    return metadata


def _source_payload(store, kb, record, name, content, pipeline):
    from common.converter import prepare_review_file
    with tempfile.TemporaryDirectory(prefix='ctxdb-review-') as directory:
        path = Path(directory) / name
        path.write_bytes(content)
        captured = record.get('metadata') or {}
        name, path, fingerprint = prepare_review_file(store.client, kb['id'], name, path,
            base_url=captured.get('resource_base_url') or captured.get('url') or '', pipeline=pipeline)
        if not record.get('archive_source') and record.get('content_format') == 'markdown':
            fingerprint = (captured.get('conversion') or {}).get('fingerprint') or ''
        return name, path.read_bytes(), fingerprint


def _deliver(store, record, archive, mode, kb, scope, pipeline, directories):
    owner = store.owner_id or ''
    source = str(record['id'])
    suffix = Path(record['archive_source']).suffix.lower() if record.get('archive_source') else {
        'html': '.html', 'text': '.txt', 'markdown': '.md', 'md': '.md'}.get(record.get('content_format') or record.get('source_format') or 'markdown', '')
    legacy_name = f"doc-{safe_name(source)}{suffix}"
    from common.converter import clean_filename
    filename = captured_filename(record)
    name = clean_filename(Path(filename).stem)[:160 - len(suffix)] + suffix if filename else legacy_name
    content = archive.read(record['archive_source']) if record.get('archive_source') else record.get('content', '').encode('utf-8')
    if not content.strip():
        raise StoreError(f'源文档为空: {source}', 422)
    original = record['source_content'].encode('utf-8') if 'source_content' in record else content
    digest = hashlib.sha256(original).hexdigest()
    row = _mapping(owner, scope, source, kb['id'])
    if row:
        mode = row['target_mode']
    if row and row['knowledge_base_id'] != kb['id']:
        raise StoreError('目标知识库映射已改变，需要独立迁移后重试', 409)
    doc = None
    if row and row['document_id']:
        try:
            doc = store.client.get_document(kb['id'], row['document_id'])
        except ContextDBError as exc:
            # errorCode 1001：回执指向的官方文档已被删除。批次仍携带原件，按全新目标重新投递，
            # 而不是让整批提交停在旧回执上（软删除态 deleted/deleting 仍走下方 409 防护）。
            if exc.error_code != 1001:
                raise
    same_capture = bool(doc and row['source_hash'] == digest and row['source_version'] == str(record.get('version_id', '')))
    if same_capture:
        # Policy changes do not replace a previously accepted capture or its human rewrite.
        fingerprint = row.get('conversion_fingerprint') or ''
        submitted_hash = doc.get('metadata', {}).get('submitted_content_hash')
    else:
        name, content, fingerprint = _source_payload(store, kb, record, name, content, pipeline)
        submitted_hash = hashlib.sha256(content).hexdigest()
    if row and doc is None:
        legacy_name = str(Path(legacy_name).with_suffix(Path(name).suffix))
        doc = _find_document(store.client, kb['id'], legacy_name, scope, source)
        if doc is None and row['status'] in ('uploading', 'uncertain'):
            raise StoreError('上次上传结果未知，官方列表尚未返回该文档；请核实后重试，防止重复提交', 409)
    if doc and doc.get('ingest_status') in ('deleted', 'deleting'):
        raise StoreError('源文档已删除或正在删除，不能自动恢复', 409)
    unchanged = same_capture or doc and ((doc.get('metadata', {}).get('source_content_hash') == digest and
                          doc.get('metadata', {}).get('source_conversion_fingerprint', '') == fingerprint) or
                         (row and row['source_hash'] == digest and row['source_version'] == str(record.get('version_id', ''))
                          and (row.get('conversion_fingerprint') or '') == fingerprint))
    if not unchanged and row and row['status'] in ('uploading', 'uncertain'):
        raise StoreError('上次写入结果未知，官方文档尚未确认目标内容版本；请核实后重试，防止覆盖或重复提交', 409)
    metadata = _document_metadata(record, scope, source, digest, fingerprint, submitted_hash, doc.get('metadata') if doc else None)
    metadata_changed = doc is not None and metadata != doc.get('metadata', {})
    parent_node_id, import_root = directories.target(record)
    try:
        if unchanged:
            result = doc
            if metadata_changed:
                result = {**doc, **store.client.update_document_metadata(metadata, document_id=doc['id'])}
        else:
            _save(owner, scope, source, mode, kb['id'], status='uploading', error=None)
            if doc and Path(doc.get('name', '')).suffix.lower() == Path(name).suffix.lower():
                name = clean_filename(doc['name'])
            with tempfile.TemporaryDirectory(prefix='ctxdb-sync-') as directory:
                path = Path(directory) / name
                path.write_bytes(content)
                mime = mimetypes.guess_type(name)[0] or 'application/octet-stream'
                if doc:
                    result = store.client.update_file(doc['id'], name, path, metadata=metadata, mime_type=mime)
                else:
                    try:
                        result = store.client.upload_file(kb['id'], name, path, file_path=scope, metadata=metadata, mime_type=mime,
                                                          parent_node_id=parent_node_id)
                    except ContextDBConflictError as exc:
                        if exc.error_code != 1003:
                            raise
                        existing = _find_document(store.client, kb['id'], name, scope)
                        if existing is None:
                            raise
                        if existing.get('metadata', {}).get('platform_source_id') != source:
                            # Equal business titles do not make two sources the same document.
                            name = f'{Path(name).stem[:140]}-{hashlib.sha256(source.encode()).hexdigest()[:12]}{Path(name).suffix}'
                            path = path.with_name(name)
                            path.write_bytes(content)
                            result = store.client.upload_file(kb['id'], name, path, file_path=scope, metadata=metadata, mime_type=mime,
                                                              parent_node_id=parent_node_id)
                        else:
                            metadata = _document_metadata(record, scope, source, digest, fingerprint, submitted_hash, existing.get('metadata'))
                            unchanged = (existing.get('metadata', {}).get('source_content_hash') == digest and
                                         existing.get('metadata', {}).get('source_conversion_fingerprint', '') == fingerprint)
                            metadata_changed = metadata != existing.get('metadata', {})
                            if unchanged:
                                result = existing
                                if metadata_changed:
                                    result = {**existing, **store.client.update_document_metadata(metadata, document_id=existing['id'])}
                            else:
                                result = store.client.update_file(existing['id'], name, path, metadata=metadata, mime_type=mime)
        _save(owner, scope, source, mode, kb['id'], document_id=result['id'], source_hash=digest,
              source_version=str(record.get('version_id', '')), conversion_fingerprint=fingerprint,
              status=result.get('ingest_status', 'unknown'),
              event_id=result.get('latest_ingest_event_id'), error=result.get('ingest_error_message'))
        detail = store.client.get_document(kb['id'], result['id'])
        _save(owner, scope, source, mode, kb['id'], status=detail.get('ingest_status', 'unknown'),
              event_id=detail.get('latest_ingest_event_id'), error=detail.get('ingest_error_message'))
        directories.attach(result['id'], parent_node_id)
        directories.populated(import_root)
        return not unchanged or metadata_changed
    except Exception as exc:
        definite = isinstance(exc, ContextDBError) and exc.status_code is not None and 400 <= exc.status_code < 500
        _save(owner, scope, source, mode, kb['id'], status='rejected' if definite else 'uncertain', error=str(exc)[:1000])
        raise


def run_sync(store, job):
    params = job['params']
    mode, target_id = params.get('target_mode'), params.get('knowledge_base_id')
    if 'target_modes' in params:
        modes = params['target_modes']
        if not isinstance(modes, list) or len(modes) != 1:
            raise StoreError('旧双目标任务已停止，请选择一个知识库后重新提交', 409)
        mode = modes[0]
        target_id = (params.get('target_ids') or {}).get(mode)
    if mode not in ('source', 'graph', 'wiki') or not target_id:
        raise StoreError('提交任务缺少固定目标知识库，请重新提交当前批次', 409)
    release = store.get_release(job['params']['release_id'])
    if not release['active']:
        raise StoreError('该提交已被更新批次取代，请同步当前资料，避免覆盖新版本', 409)
    if not Path(release['archive_path']).is_file():
        raise StoreError('治理提交包缺失', 404)
    scope = release['scope']
    kb = _target(store, scope, mode, target_id)
    capture_job_record = store._find('job', job_id=release['job_id'])
    capture_job = store.get_job(release['job_id']) if capture_job_record else {}
    root_name = (capture_job.get('import_directory') or {}).get('root_name')
    root_names = {capture_job['source_key']: root_name} if root_name else {}
    directories = ImportDirectories(store, kb['id'], root_names=root_names)
    from common.converter import RAGContentPipeline
    pipeline = RAGContentPipeline(Path(release['archive_path']).with_suffix('') / 'assets')
    failures = []
    stage = {'knowledge_base_id': kb['id'], 'uploaded': 0, 'skipped': 0, 'errors': [], 'status': 'pending'}
    stages = {mode: stage}
    uploaded = skipped = 0
    with ZipFile(release['archive_path']) as archive:
        records = [json.loads(line) for line in archive.read('rag_documents.jsonl').decode('utf-8').splitlines() if line.strip()]
        total = len(records)
        for record in records:
            store.guard_attempt()
            if store.get_job(job['task_id'])['cancel_requested']:
                from crawlers.base import CrawlCancelled
                raise CrawlCancelled('同步已取消')
            try:
                from governance.knowledge_bases import base_write_lock
                with base_write_lock(target_id), connection() as conn:
                    conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',
                                 (f'sync-delivery:{store.owner_id}:{scope}',))
                    if not store.get_release(release['id'])['active']:
                        raise StoreError('该提交已被更新批次取代，停止写入旧内容', 409)
                    kb = _target(store, scope, mode, target_id)
                    delivered = _deliver(store, record, archive, mode, kb, scope, pipeline, directories)
                if delivered:
                    uploaded += 1
                    stage['uploaded'] += 1
                else:
                    skipped += 1
                    stage['skipped'] += 1
            except Exception as exc:
                failures.append(f'{mode}/{record["id"]}: {exc}')
                stage['errors'].append(f'{record["id"]}: {exc}')
            stage['status'] = 'partial' if stage['errors'] else 'submitting'
            store.update_job(job['task_id'], summary={'targets': stages})
            store.log(job['task_id'], f'上传 {uploaded}，未变化 {skipped}，错误 {len(failures)}',
                      phase='syncing', completed_pages=uploaded+skipped, total_pages=total)
    stage['status'] = 'partial' if stage['errors'] else 'submitted'
    store.update_job(job['task_id'], status='partial' if failures else 'completed', summary={'targets': stages},
        phase='partial' if failures else 'submitted', progress=int(100*(uploaded+skipped)/total) if total else 100,
        end_time=now(), failed_pages=len(failures), skipped_pages=skipped,
        message=('；'.join(failures)[:1400] if failures else '资料已提交；评审、入库与编译请查看该知识库的官方处理状态'))
    return {'knowledge_base_id': kb['id'], 'target_mode': mode, 'targets': {mode: kb['id']}, 'uploaded': uploaded,
            'skipped': skipped, 'total': total, 'errors': failures}
