"""Business-space routing metadata. All knowledge content and processing remain in ContextDB."""
import os
import re

from governance.database import connection
from governance.store import StoreError
from integrations.contextdb import ContextDBError


def missing_knowledge_base(error):
    if error.status_code == 404:
        return True
    message = re.sub(r'\s*\(errorcode=1001\)$', '', str(error).strip().lower())
    return error.status_code == 400 and error.error_code == 1001 and message in (
        'common_bad_request: knowledge base not found', 'knowledge base not found')


def base_mode(base):
    if base.get('wiki_enabled') and base.get('graph_enabled'):
        raise StoreError('ContextDB 知识库模式不一致', 409)
    return 'wiki' if base.get('wiki_enabled') else 'graph' if base.get('graph_enabled') else 'source'


def _single(value):
    value = dict(value)
    legacy_targets = dict(value.get('legacy_targets') or {})
    for mode in ('wiki', 'graph'):
        if value.get(mode + '_kb_id'):
            legacy_targets[mode] = value[mode + '_kb_id']
    kb_id = value.get('knowledge_base_id') or value.get('wiki_kb_id') or value.get('graph_kb_id')
    mode = value.get('mode') or ('wiki' if value.get('wiki_kb_id') else
                                 'graph' if value.get('graph_kb_id') else 'wiki')
    return {**value, 'knowledge_base_id': kb_id, 'mode': mode,
            'lifecycle': value.get('lifecycle') or ('active' if kb_id else 'unbound'),
            'legacy_targets': legacy_targets,
            'wiki_kb_id': kb_id if mode == 'wiki' else None,
            'graph_kb_id': kb_id if mode == 'graph' else None,
            'graph_enabled': mode == 'graph'}


def _view(value, has_submission, store, base=None):
    result = _single(value)
    kb_id, mode = result['knowledge_base_id'], result['mode']
    status = 'unbound' if not kb_id else 'available'
    error = None
    if result['lifecycle'] in ('deleted', 'deleting'):
        status = result['lifecycle']
    elif kb_id:
        try:
            base = base or store.client.get_knowledge_base(kb_id)
            official_mode = base_mode(base)
            result.update(name=base['name'], description=base.get('description', ''), official_mode=official_mode)
            if (official_mode == 'wiki') != (mode == 'wiki'):
                status, error = 'unknown', '官方知识库模式与创建时不一致，禁止继续写入'
            else:
                mode = official_mode
                result.update(mode=mode, graph_enabled=bool(base.get('graph_enabled')),
                              wiki_kb_id=kb_id if mode == 'wiki' else None,
                              graph_kb_id=kb_id if mode == 'graph' else None)
        except ContextDBError as exc:
            error = str(exc)
            if missing_knowledge_base(exc):
                status, result['lifecycle'] = 'missing', 'missing'
            else:
                status = 'forbidden' if exc.status_code in (401, 403) else 'unknown'
    result.update(has_submission=has_submission, targets={})
    for target_mode in ('source', 'wiki', 'graph'):
        enabled = target_mode == mode
        target = {'knowledge_base_id': kb_id if enabled else None, 'enabled': enabled,
                  'status': status if enabled else 'unbound',
                  'previous_knowledge_base_ids': list((value.get('previous_knowledge_base_ids') or {}).get(target_mode, []))}
        if enabled and error:
            target['error'] = error
        if enabled and status == 'missing':
            target['missing_knowledge_base_id'] = kb_id
        result['targets'][target_mode] = target
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
        value = store._body(record['id'])
    else:
        with connection() as conn:
            rows = conn.execute('''SELECT DISTINCT target_mode,knowledge_base_id FROM knowledge_sync
                WHERE owner_id=%s AND scope=%s''', (store.owner_id or '', scope)).fetchall()
        ids = {}
        for row in rows:
            if row['target_mode'] in ids and ids[row['target_mode']] != row['knowledge_base_id']:
                raise StoreError('同一业务范围存在多个目标库，请先核对映射', 409)
            ids[row['target_mode']] = row['knowledge_base_id']
        known = scope in _legacy_scopes(store)
        if not known and scope != 'default':
            raise StoreError('业务知识库不存在', 404)
        for mode in ('wiki', 'graph'):
            if mode not in ids:
                explicit = os.getenv('CONTEXTDB_KB_ID' if mode == 'wiki' else 'CONTEXTDB_GRAPH_KB_ID', '').strip()
                base = None if explicit else store.client.find_knowledge_base(
                    f"knowledge-{scope.replace(':', '_').replace('/', '_')[:180]}" + ('-graph' if mode == 'graph' else ''))
                if explicit or base:
                    ids[mode] = explicit or base['id']
        if not known and not ids:
            raise StoreError('业务知识库不存在', 404)
        value = {'scope': scope, 'name': '默认知识库' if scope == 'default' else scope,
                 'wiki_kb_id': ids.get('wiki'), 'graph_kb_id': ids.get('graph'), 'legacy': True}
        if not ids.get('wiki') and not ids.get('graph') and ids.get('source'):
            value.update(knowledge_base_id=ids['source'], mode='source')
    return _view(value, bool(store._find('release', scope=scope, active=True)), store)


def persist_space(store, value):
    value = _single(value)
    saved = {key: value.get(key) for key in ('scope', 'name', 'description', 'knowledge_base_id', 'mode',
             'lifecycle', 'legacy', 'legacy_targets', 'legacy_origin_scope', 'previous_knowledge_base_ids')}
    saved['previous_knowledge_base_ids'] = value.get('previous_knowledge_base_ids') or {}
    record = store._find('knowledge_space', scope=value['scope'])
    if record:
        store._write(record['id'], saved, metadata={**record['metadata'],
            'knowledge_base_id': value['knowledge_base_id']})
    else:
        store._create('knowledge_space', value['scope'], saved,
                      {'scope': value['scope'], 'knowledge_base_id': value['knowledge_base_id']})
    return _view(saved, bool(store._find('release', scope=value['scope'], active=True)), store)


def ensure_base_space(store, kb_id):
    if not isinstance(kb_id, str) or not kb_id.strip():
        raise StoreError('knowledge_base_id 必须是非空文本', 400)
    with connection() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (f'space-config:{store.owner_id}',))
        records = store._list({'type': 'knowledge_space'})
        origin = None
        for record in records:
            value = _single(store._body(record['id']))
            if value['knowledge_base_id'] == kb_id:
                if value['lifecycle'] == 'creating':
                    base = store.client.get_knowledge_base(kb_id)
                    return persist_space(store, {**value, 'mode': base_mode(base), 'lifecycle': 'active'})
                return _view(value, bool(store._find('release', scope=value['scope'], active=True)), store)
            if kb_id in value['legacy_targets'].values():
                origin = value['scope']
        base = store.client.get_knowledge_base(kb_id)
        for scope in sorted(_legacy_scopes(store) | {'default'}):
            try:
                old = get_space(store, scope)
            except StoreError as exc:
                if exc.status == 404:
                    continue
                raise
            if old['knowledge_base_id'] == kb_id:
                return persist_space(store, {**old, 'name': base['name'], 'mode': base_mode(base)})
            if kb_id in old.get('legacy_targets', {}).values():
                origin = scope
        return persist_space(store, {'scope': 'kb-' + kb_id, 'knowledge_base_id': kb_id,
            'mode': base_mode(base), 'name': base['name'], 'description': base.get('description', ''),
            'lifecycle': 'active', 'legacy_origin_scope': origin})


def list_spaces(store):
    bases = store.client.list_knowledge_bases().get('knowledge_bases', [])
    values = [_single(store._body(record['id'])) for record in store._list({'type': 'knowledge_space'})]
    for scope in sorted(_legacy_scopes(store) | {'default'}):
        if any(value['scope'] == scope for value in values):
            continue
        try:
            values.append(get_space(store, scope))
        except StoreError as exc:
            if exc.status != 404:
                raise
    by_id = {value['knowledge_base_id']: value for value in values if value['knowledge_base_id']}
    for base in bases:
        if base['id'] not in by_id:
            value = {'scope': 'kb-' + base['id'], 'knowledge_base_id': base['id'], 'name': base['name'],
                     'mode': base_mode(base), 'lifecycle': 'active'}
            values.append(value)
            by_id[base['id']] = value
    spaces = [_view(value, bool(store._find('release', scope=value['scope'], active=True)), store)
              for value in values if value.get('lifecycle') != 'deleted']
    return spaces, []


def require_writable_space(store, scope):
    space = get_space(store, scope)
    if space['lifecycle'] != 'active' or not space['knowledge_base_id']:
        raise StoreError('知识库未绑定、已删除或正在删除，不能继续写入；请新建或选择现有知识库', 409)
    with connection() as conn:
        stopped = conn.execute('''SELECT 1 FROM runtime_records WHERE kind='knowledge_space'
            AND payload->>'knowledge_base_id'=%s AND payload->>'lifecycle' IN ('deleting','deleted') LIMIT 1''',
            (space['knowledge_base_id'],)).fetchone()
    if stopped:
        raise StoreError('知识库已删除或正在删除，不能继续写入', 409)
    target = space['targets'][space['mode']]
    if target['status'] != 'available':
        raise StoreError(target.get('error') or '无法确认官方知识库状态，不能继续写入', 409)
    return space


def save_space(store, body, scope=None):
    from governance.knowledge_bases import create_base, update_base
    if not isinstance(body, dict):
        raise StoreError('请求必须是 JSON 对象', 400)
    unknown = set(body) - {'scope', 'name', 'description', 'mode', 'knowledge_base_id',
                           'wiki_kb_id', 'graph_kb_id', 'graph_enabled'}
    if unknown:
        raise StoreError('不支持的知识库配置字段', 400)
    if 'graph_enabled' in body and not isinstance(body['graph_enabled'], bool):
        raise StoreError('graph_enabled 必须是布尔值', 400)
    if scope:
        space = require_writable_space(store, scope)
        if any(key in body and body[key] != space.get(key) for key in
               ('scope', 'knowledge_base_id', 'wiki_kb_id', 'graph_kb_id')):
            raise StoreError('知识库创建后不能替换目标 ID', 409)
        update_base(store, space['knowledge_base_id'],
                    {key: body[key] for key in ('name', 'description', 'mode', 'graph_enabled') if key in body})
        return get_space(store, scope)
    kb_ids = [body[key] for key in ('knowledge_base_id', 'wiki_kb_id', 'graph_kb_id') if body.get(key)]
    if len(set(kb_ids)) > 1:
        raise StoreError('一次只能绑定一个 ContextDB 知识库', 409)
    if kb_ids:
        base = store.client.get_knowledge_base(kb_ids[0])
        expected = body.get('mode') or ('wiki' if body.get('wiki_kb_id') else 'graph' if body.get('graph_kb_id') else None)
        if expected and base_mode(base) != expected:
            raise StoreError('目标库模式不匹配', 409)
        bound = ensure_base_space(store, kb_ids[0])
        if body.get('scope') and body['scope'] != bound['scope']:
            raise StoreError('已有知识库不能覆盖另一个业务范围', 409)
        return bound
    base = create_base(store, {'name': body.get('name'), 'description': body.get('description'),
                              'mode': body.get('mode') or ('graph' if body.get('graph_enabled') else 'wiki')}, scope=body.get('scope'))
    return ensure_base_space(store, base['id'])


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
        total = conn.execute('SELECT count(*) AS n FROM knowledge_sync WHERE owner_id=%s AND knowledge_base_id=%s',
                             (store.owner_id or '', space['knowledge_base_id'])).fetchone()['n']
        rows = conn.execute('''SELECT * FROM knowledge_sync WHERE owner_id=%s AND knowledge_base_id=%s
            ORDER BY source_id,target_mode LIMIT %s OFFSET %s''',
            (store.owner_id or '', space['knowledge_base_id'], page_size, (page - 1) * page_size)).fetchall()
    for row in rows:
        row['retry_stages'] = []
        target = space['targets'][space['mode']]
        if row['knowledge_base_id'] != (target['knowledge_base_id'] or target.get('missing_knowledge_base_id')):
            row['target_status'] = 'pending_submission'
            row['official_error'] = '此来源尚未投递到当前目标库，原投递回执已保留；请重新提交最近批次'
            continue
        if target['status'] != 'available':
            row['target_status'] = target['status']
            row['official_error'] = ('目标知识库已不存在，历史回执保留；请创建或选择现有知识库'
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
            row['retry_stages'] = retry_stages(detail, space['mode'])
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
    space = require_writable_space(store, scope)
    mode, stage = body.get('target_mode', space['mode']), body.get('stage')
    if mode not in ('source', 'wiki', 'graph') or stage not in ('upload', 'ingest', 'graph'):
        raise StoreError('请选择已支持的处理阶段与目标', 400)
    if (mode == 'wiki') != (space['mode'] == 'wiki'):
        raise StoreError('重试目标与当前知识库模式不一致', 409)
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
            job_modes = job['params'].get('target_modes', [job['params'].get('target_mode', space['mode'])])
            if not any((target == 'wiki') == (mode == 'wiki') for target in job_modes):
                raise StoreError('该任务未提交此目标', 409)
            target = (job.get('summary') or {}).get('targets', {}).get(mode, {})
            if target.get('status') == 'submitted' and not target.get('errors'):
                raise StoreError('该目标已提交成功，请查看后续官方治理状态', 409)
            active = conn.execute('''SELECT 1 FROM runtime_records WHERE owner_id=%s AND kind='job'
                AND metadata->>'retry_of'=%s AND metadata->>'status' IN ('pending','running','cancelling')
                LIMIT 1''', (store.owner_id or '', task_id)).fetchone()
            if active:
                raise StoreError('该目标已有重试任务，请等待处理结果', 409)
            queued = enqueue_sync(store, job['params']['release_id'], scope, retry_of=task_id)
            return {'task_id': queued['task_id'], 'status': 'pending'}
        from governance.knowledge_bases import base_write_lock
        with base_write_lock(space['knowledge_base_id']):
            require_writable_space(store, scope)
            source = body.get('source_id')
            if not isinstance(source, str) or not source:
                raise StoreError('处理请求必须指定 source_id', 400)
            row = conn.execute('''SELECT * FROM knowledge_sync WHERE owner_id=%s AND knowledge_base_id=%s
                AND source_id=%s''', (store.owner_id or '', space['knowledge_base_id'], source)).fetchone()
            if not row or not row['document_id']:
                raise StoreError('来源与目标文档映射不存在', 404)
            if row['knowledge_base_id'] != space['knowledge_base_id']:
                raise StoreError('该来源仍关联旧目标，请重新提交最近批次后重试', 409)
            detail = store.client.get_document(row['knowledge_base_id'], row['document_id'])
            if stage == 'graph':
                kb = store.client.get_knowledge_base(row['knowledge_base_id'])
                if not kb.get('graph_enabled'):
                    raise StoreError('官方知识库未启用图谱', 409)
            if stage not in retry_stages(detail, space['mode']):
                raise StoreError('当前官方状态不允许此处理，请刷新或前往知识评审处理', 409)
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
                                     any(mode not in ('source', 'wiki', 'graph') for mode in target_modes)):
        raise StoreError('target_modes 必须是包含 source、wiki 或 graph 的非空列表', 400)
    space = require_writable_space(store, scope)
    if target_modes is not None and list(dict.fromkeys(target_modes)) != [space['mode']]:
        raise StoreError('一次只能提交当前知识库的固定模式', 409)
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
