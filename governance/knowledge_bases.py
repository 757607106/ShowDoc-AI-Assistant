"""One official knowledge base per capture scope; no local knowledge or review state."""
import re
import uuid
from contextlib import ExitStack, contextmanager

from governance.database import connection
from governance.store import StoreError
from integrations.contextdb import ContextDBError

MODES = ('source', 'graph', 'wiki')


@contextmanager
def base_write_lock(kb_id):
    """Serialize official writes and deletion across members of the same library."""
    with connection() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (f'knowledge-base:{kb_id}',))
        yield


def _name(value):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 255:
        raise StoreError('知识库名称需为 1 至 255 字文本', 400)
    return value.strip()


def _creation_mode(body):
    for key in ('wiki_enabled', 'graph_enabled', 'review_enabled'):
        if key in body and not isinstance(body[key], bool):
            raise StoreError(f'{key} 必须是布尔值', 400)
    if body.get('wiki_enabled') and body.get('graph_enabled'):
        raise StoreError('Wiki 与图谱模式互斥', 400)
    flags = 'wiki' if body.get('wiki_enabled') else 'graph' if body.get('graph_enabled', True) else 'source'
    mode = body.get('mode', flags)
    if mode not in MODES:
        raise StoreError('mode 必须为 source、graph 或 wiki', 400)
    if any(key in body for key in ('wiki_enabled', 'graph_enabled')) and mode != flags:
        raise StoreError('mode 与官方模式开关不一致', 400)
    return mode


def create_base(store, body, *, scope=None):
    from governance.spaces import persist_space, _legacy_scopes
    name, mode = _name(body.get('name')), _creation_mode(body)
    scope = scope or 'space-' + uuid.uuid4().hex[:16]
    if not isinstance(scope, str) or not re.fullmatch(r'[A-Za-z0-9_:.\-]{1,180}', scope):
        raise StoreError('业务范围标识无效', 400)
    with connection() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (f'space-config:{store.owner_id}',))
        if store._find('knowledge_space', scope=scope) or scope in _legacy_scopes(store):
            raise StoreError('业务范围已存在，请读取现有知识库', 409)
        base = store.client.create_knowledge_base(name, description=body.get('description'),
            wiki_enabled=mode == 'wiki', graph_enabled=mode == 'graph',
            review_enabled=body.get('review_enabled', False),
            **{key: body[key] for key in ('chunk_size', 'chunk_overlap', 'profile_config') if key in body})
        value = {'scope': scope, 'knowledge_base_id': base['id'], 'name': name,
                 'mode': mode, 'lifecycle': 'active'}
        try:
            persist_space(store, value)
        except Exception as exc:
            raise StoreError(f'官方知识库已创建（{base["id"]}），本地绑定未保存，请按该 ID 恢复绑定，勿重复创建：{exc}', 409) from exc
    try:
        current = store.client.get_knowledge_base(base['id'])
        from governance.spaces import base_mode
        if base_mode(current) != mode:
            raise StoreError('官方回读的编译模式与创建请求不一致', 409)
    except Exception as exc:
        raise StoreError(f'官方知识库已创建（{base["id"]}），详情尚未确认，请按该 ID 核对，勿重复创建：{exc}', 409) from exc
    try:
        persist_space(store, {**value, 'name': current['name'], 'description': current.get('description', ''),
                              'lifecycle': 'active'})
    except Exception as exc:
        raise StoreError(f'官方知识库已创建（{base["id"]}），本地绑定确认未保存，请按该 ID 恢复绑定，勿重复创建：{exc}', 409) from exc
    return current


def update_base(store, kb_id, body):
    from governance.spaces import base_mode, ensure_base_space, require_writable_space, persist_space
    with connection() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (f'knowledge-base:{kb_id}',))
        space = ensure_base_space(store, kb_id)
        require_writable_space(store, space['scope'])
        mode = space['mode']
        for key in ('wiki_enabled', 'graph_enabled', 'review_enabled'):
            if key in body and not isinstance(body[key], bool):
                raise StoreError(f'{key} 必须是布尔值', 400)
        requested_mode = body.get('mode', mode)
        if requested_mode not in MODES:
            raise StoreError('mode 必须为 source、graph 或 wiki', 400)
        if ((requested_mode == 'wiki') != (mode == 'wiki') or
                ('wiki_enabled' in body and body['wiki_enabled'] != (mode == 'wiki')) or
                (mode == 'wiki' and body.get('graph_enabled'))):
            raise StoreError('知识库创建后不能切换 Wiki 模式', 409)
        name = body.get('name', body.get('knowledge_base_name'))
        fields = {key: body[key] for key in ('description', 'review_enabled', 'graph_enabled') if key in body}
        if 'mode' in body and mode != 'wiki':
            if 'graph_enabled' in body and body['graph_enabled'] != (requested_mode == 'graph'):
                raise StoreError('mode 与知识图谱开关不一致', 400)
            fields['graph_enabled'] = requested_mode == 'graph'
        if name is not None:
            fields['name'] = _name(name)
        if fields:
            store.client.update_knowledge_base(kb_id, **fields)
        current = store.client.get_knowledge_base(kb_id)
        persist_space(store, {**space, 'mode': base_mode(current), 'name': current['name'],
                              'description': current.get('description', '')})
        return current


def delete_base(store, kb_id):
    with base_write_lock(kb_id):
        return _delete_base(store, kb_id)


def _delete_base(store, kb_id):
    from governance.spaces import ensure_base_space, persist_space, missing_knowledge_base
    with connection() as conn:
        space = ensure_base_space(store, kb_id)
        if space['lifecycle'] == 'deleted':
            return {'knowledge_base_id': kb_id, 'lifecycle': 'deleted'}
        # Check all owners: another member may have a capture pinned to this same official ID.
        active = conn.execute('''SELECT 1 FROM runtime_records j WHERE j.kind='job'
            AND j.metadata->>'status' IN ('pending','running','cancelling') AND (
                j.payload->'params'->>'knowledge_base_id'=%s OR j.payload->'params'->>'target_id'=%s OR
                j.payload->'params'->'target_ids' @> jsonb_build_object('wiki',%s::text) OR
                j.payload->'params'->'target_ids' @> jsonb_build_object('graph',%s::text) OR
                EXISTS (SELECT 1 FROM runtime_records s WHERE s.kind='knowledge_space'
                    AND s.owner_id=j.owner_id AND s.payload->>'scope'=j.metadata->>'scope'
                    AND s.payload->>'knowledge_base_id'=%s) OR
                (j.owner_id=%s AND j.metadata->>'scope'=%s)) LIMIT 1''',
            (kb_id, kb_id, kb_id, kb_id, kb_id, store.owner_id or '', space['scope'])).fetchone()
        if active:
            raise StoreError('该知识库已有采集或同步任务，请先取消并等待任务停止', 409)
        upload = conn.execute('''SELECT 1 FROM runtime_records WHERE kind='knowledge_upload'
            AND payload->>'knowledge_base_id'=%s AND payload->>'state' IN ('uploading','completing')
            AND created_at > now() - interval '1 hour' LIMIT 1''', (kb_id,)).fetchone()
        if upload:
            raise StoreError('该知识库仍有分片上传会话，请取消上传或票据到期后核对文档，再删除知识库', 409)
        try:
            documents = store.client.list_documents(kb_id, page=1, page_size=1)
        except ContextDBError as exc:
            if not missing_knowledge_base(exc):
                raise
            persist_space(store, {**space, 'lifecycle': 'deleted'})
            return {'knowledge_base_id': kb_id, 'lifecycle': 'deleted'}
        if documents.get('documents') or documents.get('total', 0):
            raise StoreError('知识库非空，请先处理待评审或处理中资料并清空文档，等待官方删除完成后再删库', 409)
        persist_space(store, {**space, 'lifecycle': 'deleting'})
    delete_error = None
    try:
        store.client.delete_knowledge_base(kb_id)
    except ContextDBError as exc:
        if exc.status_code is not None and 400 <= exc.status_code < 500 and not missing_knowledge_base(exc):
            persist_space(store, space)
            raise
        if not missing_knowledge_base(exc):
            delete_error = exc
    try:
        store.client.get_knowledge_base(kb_id)
    except ContextDBError as exc:
        if not missing_knowledge_base(exc):
            raise
        persist_space(store, {**space, 'lifecycle': 'deleted'})
        return {'knowledge_base_id': kb_id, 'lifecycle': 'deleted'}
    if delete_error:
        raise delete_error
    return {'knowledge_base_id': kb_id, 'lifecycle': 'deleting'}


def require_writable_base(store, kb_id=None, document_id=None):
    from governance.spaces import ensure_base_space, require_writable_space
    if document_id:
        actual = store.client.get_document(None, document_id).get('knowledge_base_id')
        if kb_id and kb_id != actual:
            raise StoreError('document_id 不属于所选知识库', 409)
        kb_id = actual
    if not kb_id:
        raise StoreError('缺少 knowledge_base_id，无法确认目标知识库', 400)
    space = ensure_base_space(store, kb_id)
    return require_writable_space(store, space['scope'])


def _validate_review_ids(review_ids):
    if not isinstance(review_ids, list) or not 1 <= len(review_ids) <= 50 or not all(
            isinstance(review_id, str) and review_id.strip() for review_id in review_ids):
        raise StoreError('ids 必须是 1～50 个非空评审 ID 的列表', 400)


def review_base_ids(store, review_ids):
    _validate_review_ids(review_ids)
    ids = set()
    for review_id in review_ids:
        review = store.client.get_review(review_id)
        kb_id = review.get('knowledge_base_id')
        if not isinstance(kb_id, str) or not kb_id:
            raise StoreError('官方评审详情未返回可核对的 knowledge_base_id', 502)
        ids.add(kb_id)
    return sorted(ids)


def batch_reviews(store, review_ids, operation):
    """Keep per-item failures while locking each writable library against deletion."""
    _validate_review_ids(review_ids)
    bases, errors = {}, {}
    for review_id in review_ids:
        try:
            bases[review_id] = review_base_ids(store, [review_id])[0]
        except (ContextDBError, StoreError) as exc:
            errors[review_id] = str(exc)
    with ExitStack() as locks:
        for kb_id in sorted(set(bases.values())):
            locks.enter_context(base_write_lock(kb_id))
            try:
                require_writable_base(store, kb_id)
            except (ContextDBError, StoreError) as exc:
                errors.update({review_id: str(exc) for review_id, base in bases.items() if base == kb_id})
        allowed = [review_id for review_id in review_ids if review_id not in errors]
        response = operation(allowed) if allowed else {}
    pending = list(response.get('results', []))
    results = []
    for review_id in review_ids:
        if review_id in errors:
            results.append({'id': review_id, 'success': False, 'error': errors[review_id]})
            continue
        index = next((i for i, item in enumerate(pending) if item.get('id') == review_id), None)
        results.append(pending.pop(index) if index is not None else
                       {'id': review_id, 'success': False, 'error': '官方未返回该项处理结果，请核对评审状态'})
    succeeded = sum(item.get('success') is True for item in results)
    return {**response, 'total': len(results), 'succeeded': succeeded,
            'failed': len(results) - succeeded, 'results': results}
