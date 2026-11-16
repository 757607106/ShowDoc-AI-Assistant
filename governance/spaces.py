"""Business-space routing metadata. All knowledge content and processing remain in ContextDB."""
import os
import re
import uuid

from governance.database import connection
from governance.store import StoreError
from integrations.contextdb import ContextDBError


def missing_knowledge_base(error):
    if error.status_code == 404:
        return True
    message = re.sub(r'\s*\(errorcode=1001\)$', '', str(error).strip().lower())
    return error.status_code == 400 and error.error_code == 1001 and message in (
        'common_bad_request: knowledge base not found', 'knowledge base not found')


def _view(value, has_submission, store):
    result = {**value, 'has_submission': has_submission, 'targets': {}}
    for mode in ('wiki', 'graph'):
        key = mode + '_kb_id'
        kb_id = value.get(key)
        target = {'knowledge_base_id': kb_id, 'enabled': mode == 'wiki' or value['graph_enabled'],
                  'status': 'unbound' if not kb_id else 'available',
                  'previous_knowledge_base_ids': list(value.get('previous_knowledge_base_ids', {}).get(mode, []))}
        if kb_id:
            try:
                store.client.get_knowledge_base(kb_id)
            except ContextDBError as exc:
                target['error'] = str(exc)
                if missing_knowledge_base(exc):
                    target.update(status='missing', knowledge_base_id=None, missing_knowledge_base_id=kb_id)
                    result[key] = None
                else:
                    target['status'] = 'forbidden' if exc.status_code in (401, 403) else 'unknown'
        result['targets'][mode] = target
    with connection() as conn:
        history = conn.execute('''SELECT target_mode,knowledge_base_id FROM knowledge_sync
            WHERE owner_id=%s AND scope=%s
            UNION SELECT metadata->>'target_mode',payload->>'knowledge_base_id' FROM runtime_records
            WHERE owner_id=%s AND kind='knowledge_sync_history' AND metadata->>'scope'=%s''',
            (store.owner_id or '', value['scope'], store.owner_id or '', value['scope'])).fetchall()
    for row in history:
        result['targets'][row['target_mode']]['previous_knowledge_base_ids'].append(row['knowledge_base_id'])
    for mode, target in result['targets'].items():
        target['previous_knowledge_base_ids'] = sorted({kb_id for kb_id in target['previous_knowledge_base_ids']
                                                      if kb_id and kb_id != value.get(mode + '_kb_id')})
    return result


def _legacy_scopes(store):
    with connection() as conn:
        rows = conn.execute('''SELECT scope FROM knowledge_sync WHERE owner_id=%s
            UNION SELECT metadata->>'scope' AS scope FROM runtime_records
            WHERE owner_id=%s AND kind IN ('job','scope','release')''',
            (store.owner_id or '', store.owner_id or '')).fetchall()
    return {row['scope'] for row in rows if row['scope']}


def get_space(store, scope):
    record = store._find('knowledge_space', scope=scope)
    if record:
        return _view(store._body(record['id']), bool(store._find('release', scope=scope, active=True)), store)
    with connection() as conn:
        mappings = conn.execute('''SELECT DISTINCT target_mode,knowledge_base_id FROM knowledge_sync
            WHERE owner_id=%s AND scope=%s''', (store.owner_id or '', scope)).fetchall()
    ids = {}
    for row in mappings:
        if row['target_mode'] in ids and ids[row['target_mode']] != row['knowledge_base_id']:
            raise StoreError('同一业务范围存在多个目标库，请先核对映射', 409)
        ids[row['target_mode']] = row['knowledge_base_id']
    known = scope in _legacy_scopes(store)
    if not known and scope != 'default':
        raise StoreError('业务知识库不存在', 404)
    from governance.contextdb_sync import knowledge_kb_name
    for mode in ('wiki', 'graph'):
        if mode in ids:
            continue
        explicit = os.getenv('CONTEXTDB_KB_ID' if mode == 'wiki' else 'CONTEXTDB_GRAPH_KB_ID', '').strip()
        if explicit:
            ids[mode] = explicit
            continue
        kb = store.client.find_knowledge_base(knowledge_kb_name(scope, mode))
        if kb:
            ids[mode] = kb['id']
    if not known and not ids.get('wiki'):
        raise StoreError('业务知识库不存在', 404)
    return _view({'scope': scope, 'name': '默认知识库' if scope == 'default' else scope,
                  'graph_enabled': True, 'wiki_kb_id': ids.get('wiki'), 'graph_kb_id': ids.get('graph'), 'legacy': True},
                 bool(store._find('release', scope=scope, active=True)), store)


def list_spaces(store):
    records = store._list({'type': 'knowledge_space'}, sort_by='created_at', sort_order='asc')
    scopes = {record['metadata']['scope'] for record in records} | _legacy_scopes(store)
    bases, page = [], 1
    while True:
        response = store.client.list_knowledge_bases(page=page, page_size=100)
        items = response.get('knowledge_bases', [])
        bases.extend(items)
        if len(items) < 100:
            break
        page += 1
    if any(item.get('name') == 'knowledge-default' and item.get('wiki_enabled') for item in bases):
        scopes.add('default')
    spaces = [get_space(store, scope) for scope in sorted(scopes)]
    bound = {space.get(key) for space in spaces for key in ('wiki_kb_id', 'graph_kb_id')}
    available = [{key: item.get(key) for key in ('id', 'name', 'wiki_enabled', 'graph_enabled')}
                 for item in bases if item['id'] not in bound and item.get('name') != '_governance']
    return spaces, available


def persist_space(store, value):
    record = store._find('knowledge_space', scope=value['scope'])
    previous = store._body(record['id']) if record else {}
    aliases = {mode: set(previous.get('previous_knowledge_base_ids', {}).get(mode, [])) |
                    set(value.get('targets', {}).get(mode, {}).get('previous_knowledge_base_ids', []))
               for mode in ('wiki', 'graph')}
    missing = {mode: value.get('targets', {}).get(mode, {}).get('missing_knowledge_base_id')
               for mode in ('wiki', 'graph')}
    value = {key: value.get(key) for key in ('scope', 'name', 'graph_enabled', 'wiki_kb_id', 'graph_kb_id', 'legacy')}
    for mode, kb_id in missing.items():
        if not value.get(mode + '_kb_id') and kb_id:
            value[mode + '_kb_id'] = kb_id
        old_id = previous.get(mode + '_kb_id')
        if old_id and old_id != value.get(mode + '_kb_id'):
            aliases[mode].add(old_id)
    value['previous_knowledge_base_ids'] = {mode: sorted(ids) for mode, ids in aliases.items()}
    if record:
        store._write(record['id'], value)
    else:
        store._create('knowledge_space', value['scope'], value, {'scope': value['scope']})
    return _view(value, bool(store._find('release', scope=value['scope'], active=True)), store)


def require_no_active_sync(store, scope):
    with connection() as conn:
        active = conn.execute('''SELECT 1 FROM runtime_records WHERE owner_id=%s AND kind='job'
            AND metadata->>'scope'=%s AND metadata->>'kind'='ctxdb_sync'
            AND metadata->>'status' IN ('pending','running','cancelling') LIMIT 1''',
            (store.owner_id or '', scope)).fetchone()
    if active:
        raise StoreError('该知识库已有同步任务，请等待提交完成后恢复目标库', 409)


def save_space(store, body, scope=None):
    lock_scope = scope or body.get('scope') or 'space-' + uuid.uuid4().hex[:16]
    if scope is None:
        body = {**body, 'scope': lock_scope}
    with connection() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (f'space-config:{store.owner_id}',))
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (f'space:{store.owner_id}:{lock_scope}',))
        return _save_space(store, body, scope)


def _save_space(store, body, scope=None):
    unknown = set(body) - {'scope', 'name', 'graph_enabled', 'wiki_kb_id', 'graph_kb_id'}
    if unknown:
        raise StoreError('不支持的知识库配置字段', 400)
    if scope:
        previous = get_space(store, scope)
        if 'scope' in body and body['scope'] != scope:
            raise StoreError('业务范围标识不能修改', 400)
    else:
        scope = body.get('scope') or 'space-' + uuid.uuid4().hex[:16]
        if not isinstance(scope, str) or not re.fullmatch(r'[A-Za-z0-9_:.\-]{1,180}', scope):
            raise StoreError('业务范围标识仅支持字母、数字、下划线、点、冒号和短横线', 400)
        if store._find('knowledge_space', scope=scope) or scope in _legacy_scopes(store):
            raise StoreError('业务范围已存在，请修改现有知识库', 409)
        if scope == 'default':
            try:
                get_space(store, scope)
            except StoreError as exc:
                if exc.status != 404:
                    raise
            else:
                raise StoreError('业务范围已存在，请修改现有知识库', 409)
        previous = {'scope': scope, 'name': '', 'graph_enabled': False, 'wiki_kb_id': None, 'graph_kb_id': None, 'legacy': False}
    value = {**previous, **body, 'scope': scope}
    if not isinstance(value['name'], str) or not 1 <= len(value['name'].strip()) <= 100:
        raise StoreError('知识库名称需为 1 至 100 字文本', 400)
    value['name'] = value['name'].strip()
    if not isinstance(value['graph_enabled'], bool):
        raise StoreError('graph_enabled 必须是布尔值', 400)
    existing_spaces = list_spaces(store)[0] if value.get('wiki_kb_id') or value.get('graph_kb_id') else []
    for mode in ('wiki', 'graph'):
        key = mode + '_kb_id'
        kb_id = value.get(key)
        if previous.get(key) and previous[key] != kb_id:
            raise StoreError('已有目标库不能直接替换；请独立迁移映射', 409)
        if key in body and previous.get('targets', {}).get(mode, {}).get('status') == 'missing':
            require_no_active_sync(store, scope)
            value['targets'] = {**value.get('targets', {}), mode: {}}
        if kb_id:
            if not isinstance(kb_id, str):
                raise StoreError('知识库 ID 必须是文本', 400)
            kb = store.client.get_knowledge_base(kb_id)
            if bool(kb.get('wiki_enabled')) != (mode == 'wiki') or bool(kb.get('graph_enabled')) != (mode == 'graph'):
                raise StoreError(f'{mode} 目标库模式不匹配', 409)
            if any(other['scope'] != scope and kb_id in (other.get('wiki_kb_id'), other.get('graph_kb_id'))
                   for other in existing_spaces):
                raise StoreError('该知识库已关联另一个业务范围', 409)
    return persist_space(store, value)


def bind_target(store, scope, mode, kb_id):
    with connection() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (f'space:{store.owner_id}:{scope}',))
        value = get_space(store, scope)
        key = mode + '_kb_id'
        if value.get(key) and value[key] != kb_id:
            raise StoreError('目标知识库映射已改变，需要独立迁移后重试', 409)
        value[key] = kb_id
        return persist_space(store, value)


def retry_stages(detail, mode):
    stages = []
    if detail.get('ingest_status') == 'failed' and 'retry' in (detail.get('recovery_actions') or []):
        stages.append('ingest')
    if mode == 'graph' and detail.get('ingest_status') == 'succeeded':
        graph_status = detail.get('graph_status')
        initial = ('graph_status' in detail and graph_status in (None, '')
                   and 'latest_graph_event_id' in detail and not detail['latest_graph_event_id'])
        if graph_status in ('failed', 'skipped') or initial:
            stages.append('graph')
    return stages


def progress(store, scope, page=1, page_size=20):
    from governance.knowledge_names import KnowledgeNames
    names = KnowledgeNames(store.owner_id)
    space = get_space(store, scope)
    with connection() as conn:
        total = conn.execute('SELECT count(*) AS n FROM knowledge_sync WHERE owner_id=%s AND scope=%s',
                             (store.owner_id or '', scope)).fetchone()['n']
        rows = conn.execute('''SELECT * FROM knowledge_sync WHERE owner_id=%s AND scope=%s
            ORDER BY source_id,target_mode LIMIT %s OFFSET %s''',
            (store.owner_id or '', scope, page_size, (page - 1) * page_size)).fetchall()
    for row in rows:
        row['retry_stages'] = []
        target = space['targets'][row['target_mode']]
        if row['knowledge_base_id'] != (target['knowledge_base_id'] or target.get('missing_knowledge_base_id')):
            row['target_status'] = 'pending_submission'
            row['official_error'] = '此来源尚未投递到当前目标库，原投递回执已保留；请重新提交最近批次'
            continue
        if target['status'] != 'available':
            row['target_status'] = target['status']
            row['official_error'] = ('目标知识库已删除，原投递回执已保留；请重新提交最近批次恢复目标库'
                                     if target['status'] == 'missing' else target.get('error', '目标知识库状态未确认'))
            continue
        if not row['document_id']:
            continue
        try:
            detail = store.client.get_document(row['knowledge_base_id'], row['document_id'])
            fields = ('name', 'ingest_status', 'ingest_error_message', 'graph_status', 'graph_error_message',
                      'latest_ingest_event_id', 'latest_graph_event_id', 'wiki_status', 'wiki_error_message',
                      'review_status', 'decision', 'lifecycle_state', 'recovery_actions')
            row['official'] = {key: detail[key] for key in fields if key in detail}
            row['official']['display_name'] = names.document(detail, kb_id=row['knowledge_base_id'])['display_name']
            if row['target_mode'] != 'graph' or space['graph_enabled']:
                row['retry_stages'] = retry_stages(detail, row['target_mode'])
        except ContextDBError as exc:
            row['official_error'] = str(exc)
    jobs = [store._job_from_doc(record) for record in store._list(
        {'type': 'job', 'scope': scope, 'kind': 'ctxdb_sync'}, sort_by='created_at', sort_order='desc', limit=20)]
    jobs = [{key: job.get(key) for key in ('task_id', 'status', 'phase', 'message', 'params', 'summary', 'retry_of', 'start_time', 'end_time')}
            for job in jobs]
    return {'space': space, 'mappings': rows, 'jobs': jobs, 'total': total, 'page': page, 'page_size': page_size}


def retry(store, scope, body):
    from governance.contextdb_sync import enqueue_sync
    from governance.store import digest
    space = get_space(store, scope)
    mode, stage = body.get('target_mode'), body.get('stage')
    if mode not in ('wiki', 'graph') or stage not in ('upload', 'ingest', 'graph'):
        raise StoreError('请选择已支持的处理阶段与目标', 400)
    if mode == 'graph' and not space['graph_enabled']:
        raise StoreError('该业务范围的图谱同步已关闭', 409)
    lock = f'space-retry:{store.owner_id}:{scope}:{mode}:{body.get("task_id") or body.get("source_id")}'
    with connection() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (lock,))
        if stage == 'upload':
            task_id = body.get('task_id')
            if not isinstance(task_id, str) or not task_id:
                raise StoreError('上传重试必须指定 task_id', 400)
            job = store.get_job(task_id)
            if job['scope'] != scope or job['kind'] != 'ctxdb_sync':
                raise StoreError('同步任务不属于该业务范围', 404)
            if not store.get_release(job['params']['release_id'])['active']:
                raise StoreError('已有更新的提交批次，请重试当前批次，避免旧内容覆盖新版本', 409)
            if job['status'] not in ('failed', 'partial', 'cancelled'):
                raise StoreError('仅失败或中断的提交任务可以重试', 409)
            if mode not in job['params'].get('target_modes', ['wiki', 'graph']):
                raise StoreError('该任务未提交此目标', 409)
            target = (job.get('summary') or {}).get('targets', {}).get(mode, {})
            if target.get('status') == 'submitted' and not target.get('errors'):
                raise StoreError('该目标已提交成功，请查看后续官方治理状态', 409)
            active = conn.execute('''SELECT 1 FROM runtime_records WHERE owner_id=%s AND kind='job'
                AND metadata->>'retry_of'=%s AND metadata->>'status' IN ('pending','running','cancelling')
                AND payload->'params'->'target_modes' ? %s LIMIT 1''', (store.owner_id or '', task_id, mode)).fetchone()
            if active:
                raise StoreError('该目标已有重试任务，请等待处理结果', 409)
            queued = enqueue_sync(store, job['params']['release_id'], scope, target_modes=[mode], retry_of=task_id)
            return {'task_id': queued['task_id'], 'status': 'pending'}
        source = body.get('source_id')
        if not isinstance(source, str) or not source:
            raise StoreError('处理请求必须指定 source_id', 400)
        row = conn.execute('''SELECT * FROM knowledge_sync WHERE owner_id=%s AND scope=%s
            AND source_id=%s AND target_mode=%s''', (store.owner_id or '', scope, source, mode)).fetchone()
        if not row or not row['document_id']:
            raise StoreError('来源与目标文档映射不存在', 404)
        if row['knowledge_base_id'] != space.get(mode + '_kb_id'):
            raise StoreError('该来源仍关联旧目标，请重新提交最近批次后重试', 409)
        detail = store.client.get_document(row['knowledge_base_id'], row['document_id'])
        if stage not in retry_stages(detail, mode):
            raise StoreError('当前官方状态不允许此处理，请刷新或前往知识评审处理', 409)
        if stage == 'graph':
            kb = store.client.get_knowledge_base(row['knowledge_base_id'])
            if not kb.get('graph_enabled'):
                raise StoreError('官方知识库未启用图谱', 409)
        fingerprint = digest({'scope': scope, 'source': source, 'mode': mode, 'stage': stage,
                              'document_id': row['document_id'], 'event_id': detail.get(
                                  'latest_graph_event_id' if stage == 'graph' else 'latest_ingest_event_id')})
        previous = store._find('processing_retry', retry_key=fingerprint)
        if previous:
            raise StoreError('此文档版本已发起处理，请先刷新官方状态；结果未知时不要重复提交', 409)
        receipt = store._create('processing_retry', fingerprint, {'status': 'submitting'},
                                {'scope': scope, 'retry_key': fingerprint})
        try:
            if stage == 'ingest':
                result = store.client.retry_document(row['document_id'])
            else:
                result = store.client._request('POST', '/v1/knowledge/events',
                    json_body={'document_id': row['document_id'], 'event_type': 'graph_build'})
        except Exception as exc:
            if isinstance(exc, ContextDBError) and exc.status_code is not None and 400 <= exc.status_code < 500:
                store._delete(receipt['id'])
            else:
                store._write(receipt['id'], {'status': 'uncertain'})
            raise
        store._write(receipt['id'], {'status': 'submitted', 'result': result})
        return result


def submit_current(store, scope, *, target_modes=None):
    from governance.contextdb_sync import enqueue_sync
    if target_modes is not None and (not isinstance(target_modes, list) or not target_modes or
                                     any(mode not in ('wiki', 'graph') for mode in target_modes)):
        raise StoreError('target_modes 必须是包含 wiki 或 graph 的非空列表', 400)
    get_space(store, scope)
    with connection() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (f'space-submit:{store.owner_id}:{scope}',))
        release = store._find('release', scope=scope, active=True)
        if not release:
            raise StoreError('尚无已提交资料，请先采集或上传，并在任务中提交治理', 409)
        release_id = release['metadata']['release_id']
        active = conn.execute('''SELECT 1 FROM runtime_records WHERE owner_id=%s AND kind='job'
            AND metadata->>'scope'=%s AND metadata->>'kind'='ctxdb_sync'
            AND metadata->>'status' IN ('pending','running','cancelling') LIMIT 1''',
            (store.owner_id or '', scope)).fetchone()
        if active:
            raise StoreError('该知识库已有同步任务，请等待提交完成', 409)
        job = enqueue_sync(store, release_id, scope, target_modes=target_modes)
        return {'task_id': job['task_id'], 'status': 'pending'}
