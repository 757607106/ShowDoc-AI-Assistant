"""知识域 API:检索/图谱/知识评审/同步状态(全部代理 ContextDB 官方 REST)。

治理沿用原则:评审队列、评审动作都是 ContextDB 原生能力,本层只做
HTTP 代理与形状适配,不复制任何状态到本地。
"""
import os
import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, request

from integrations.contextdb import ContextDBClient, ContextDBError
from governance.store import Store, StoreError
from governance.knowledge_names import KnowledgeNames

knowledge_bp = Blueprint('knowledge', __name__)

from webapi.auth import user_id


def _client():
    from webapi.auth import client_for_user
    return client_for_user()


def _json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise StoreError('请求必须是 JSON 对象', 400)
    return body


def _space_store():
    from app import get_store
    return get_store()


@knowledge_bp.route('/api/kb/spaces', methods=['GET', 'POST'])
def knowledge_spaces():
    from governance.spaces import list_spaces, save_space
    store = _space_store()
    if request.method == 'POST':
        return jsonify(success=True, space=save_space(store, _json_body())), 201
    spaces, available = list_spaces(store)
    return jsonify(success=True, spaces=spaces, available_bases=available)


@knowledge_bp.route('/api/kb/spaces/<scope>', methods=['GET', 'PATCH'])
def knowledge_space(scope):
    from governance.spaces import get_space, save_space
    store = _space_store()
    if request.method == 'PATCH':
        space = save_space(store, _json_body(), scope)
    else:
        space = get_space(store, scope)
    return jsonify(success=True, space=space)


@knowledge_bp.route('/api/kb/spaces/<scope>/progress')
def knowledge_space_progress(scope):
    from governance.spaces import progress
    return jsonify(success=True, **progress(_space_store(), scope,
        page=max(1, request.args.get('page', 1, type=int)),
        page_size=min(100, max(1, request.args.get('page_size', 20, type=int)))))


@knowledge_bp.route('/api/kb/spaces/<scope>/retry', methods=['POST'])
def knowledge_space_retry(scope):
    from governance.spaces import retry
    return jsonify(success=True, result=retry(_space_store(), scope, _json_body()))


@knowledge_bp.route('/api/kb/spaces/<scope>/submit', methods=['POST'])
def knowledge_space_submit(scope):
    from governance.spaces import submit_current
    body = _json_body() if request.data else {}
    return jsonify(success=True, result=submit_current(_space_store(), scope, target_modes=body.get('target_modes')))


@knowledge_bp.route('/api/kb/bases')
def kb_bases():
    result = _client().list_knowledge_bases(page=1, page_size=100)
    names = KnowledgeNames(user_id())
    return jsonify(success=True, bases=[
        names.base({'id': item.get('id'), 'name': item.get('name'),
         'wiki_enabled': item.get('wiki_enabled'), 'graph_enabled': item.get('graph_enabled'),
         'review_enabled': item.get('review_enabled')})
        for item in result.get('knowledge_bases', [])
    ])


@knowledge_bp.route('/api/kb/search', methods=['POST'])
def kb_search():
    body = _json_body()
    question = str(body.get('question', '')).strip()
    if not question:
        raise StoreError('question 不能为空', 400)
    kb_ids = body.get('kb_ids') or []
    kb_names = body.get('kb_names') or []
    if not (kb_ids or kb_names):
        raise StoreError('请指定要检索的知识库(kb_ids 或 kb_names)', 400)
    if not isinstance(kb_ids, list) or not isinstance(kb_names, list):
        raise StoreError('kb_ids / kb_names 必须是列表', 400)
    result = _client().query(
        question,
        knowledge_base_ids=kb_ids or None,
        knowledge_base_names=kb_names or None,
        knowledge_view=body.get('view') or 'auto',
        top_k=int(body.get('top_k', 10)),
        similarity_threshold=body.get('threshold'),
        metadata_condition=body.get('metadata_condition'),
        document_ids=body.get('document_ids') or None,
        query_rewrite=body.get('query_rewrite', True),
        vector_weight=body.get('vector_weight'),
        context_token_budget=body.get('context_token_budget'),
        images=body.get('images') or None,
    )
    return jsonify(success=True, **KnowledgeNames(user_id()).present('knowledge/query', result))


@knowledge_bp.route('/api/kb/graph')
def kb_graph():
    kb_id = (request.args.get('kb_id') or '').strip()
    if not kb_id:
        raise StoreError('缺少 kb_id 参数', 400)
    entity_id = (request.args.get('entity_id') or '').strip() or None
    document_id = (request.args.get('document_id') or '').strip() or None
    result = _client().graph_visual(kb_id, document_id=document_id, entity_id=entity_id,
        max_hops=request.args.get('max_hops', 1, type=int),
        max_nodes=request.args.get('max_nodes', 500, type=int),
        max_edges=request.args.get('max_edges', 1000, type=int))
    return jsonify(success=True, **result)


REVIEW_ACTIONS = ('confirm', 'force_accept', 'accept_rewrite', 'reject', 'reject_reupload',
                  'retract', 'retry_review')
CONFLICT_RESOLUTIONS = ('use_new', 'keep_old', 'merge', 'annotate_divergence')


def _conflict_resolutions(value):
    if value is None:
        return None
    if not isinstance(value, list) or not all(
            isinstance(item, dict) and item.get('conflict_id') and item.get('resolution') in CONFLICT_RESOLUTIONS
            for item in value):
        raise StoreError('conflict_resolutions 必须是 [{conflict_id, resolution}] 列表,'
                         'resolution 取 use_new/keep_old/merge/annotate_divergence', 400)
    return [{'conflict_id': item['conflict_id'], 'resolution': item['resolution']} for item in value]


@knowledge_bp.route('/api/kb/reviews')
def kb_reviews():
    kb_id = (request.args.get('kb_id') or '').strip()
    lifecycle_state = request.args.get('lifecycle_state') or None
    review_status = request.args.get('review_status') or None
    if lifecycle_state and review_status:
        raise StoreError('lifecycle_state 与 review_status 只能二选一', 400)
    result = _client().list_reviews(
        kb_id or None,
        review_status=review_status,
        lifecycle_state=lifecycle_state,
        decision=request.args.get('decision'),
        page=int(request.args.get('page', 1)),
        page_size=int(request.args.get('page_size', 50)),
    )
    reviews = result.get('reviews', result.get('data', {}).get('reviews', [])) if isinstance(result, dict) else []
    names = KnowledgeNames(user_id())
    return jsonify(success=True, reviews=[names.document(item, reference=True, kb_id=kb_id) for item in reviews],
                   total=result.get('total', len(reviews)) if isinstance(result, dict) else len(reviews))


@knowledge_bp.route('/api/kb/reviews/<review_id>')
def kb_review_detail(review_id):
    content_page = request.args.get('content_page')
    result = _client().get_review(review_id, content_page=int(content_page) if content_page else None)
    return jsonify(success=True, review=KnowledgeNames(user_id()).document(result, reference=True))


@knowledge_bp.route('/api/kb/reviews/batch', methods=['POST'])
def kb_review_batch():
    body = _json_body()
    try:
        result = _client().batch_review_action(body.get('ids'), body.get('action'))
    except ValueError as exc:
        raise StoreError(str(exc), 400) from exc
    return jsonify(success=True, **result)


@knowledge_bp.route('/api/kb/reviews/<review_id>/action', methods=['POST'])
def kb_review_action(review_id):
    body = _json_body()
    action = body.get('action')
    if action not in REVIEW_ACTIONS:
        raise StoreError(f"action 必须是 {'/'.join(REVIEW_ACTIONS)}", 400)
    edited_content = body.get('edited_content')
    if edited_content is not None and not isinstance(edited_content, str):
        raise StoreError('edited_content 必须是字符串', 400)
    result = _client().review_action(
        review_id, action, edited_content=edited_content or None,
        conflict_resolutions=_conflict_resolutions(body.get('conflict_resolutions')),
    )
    return jsonify(success=True, review=result if isinstance(result, dict) else {'message': str(result)})


@knowledge_bp.route('/api/kb/reviews/<review_id>/conflicts', methods=['POST'])
def kb_review_conflicts(review_id):
    resolutions = _conflict_resolutions(_json_body().get('resolutions'))
    if not resolutions:
        raise StoreError('resolutions 不能为空', 400)
    result = _client().resolve_review_conflicts(review_id, resolutions)
    return jsonify(success=True, result=result)


@knowledge_bp.route('/api/kb/documents')
def kb_documents():
    kb_id = (request.args.get('kb_id') or '').strip()
    if not kb_id:
        raise StoreError('缺少 kb_id 参数', 400)
    result = _client().list_documents(kb_id, page=int(request.args.get('page', 1)),
                                      page_size=int(request.args.get('page_size', 50)),
                                      sort_by='created_at', sort_order='desc')
    documents = result.get('documents', []) if isinstance(result, dict) else []
    names = KnowledgeNames(user_id())
    return jsonify(success=True, documents=[names.document(item, kb_id=kb_id) for item in documents],
                   total=result.get('total', len(documents)) if isinstance(result, dict) else len(documents))


@knowledge_bp.route('/api/kb/documents/<document_id>/text')
def kb_document_text(document_id):
    kb_id = (request.args.get('kb_id') or '').strip()
    if not kb_id:
        raise StoreError('缺少 kb_id 参数', 400)
    client = _client()
    _editable_document(client, kb_id, document_id)
    return jsonify(success=True, text=client.download_document_text(kb_id, document_id))


def _editable_document(client, kb_id, document_id):
    detail = client.get_document(kb_id, document_id)
    source_type = detail.get('source_type')
    if source_type in ('text', 'memory_promotion'):
        return detail
    mime_type = (detail.get('mime_type') or '').split(';', 1)[0].strip().lower()
    if (source_type == 'file' and Path(detail.get('name') or '').suffix.lower() in ('.md', '.txt', '.html', '.json')
            and (not mime_type or mime_type.startswith('text/') or mime_type in
                 ('application/json', 'application/xhtml+xml', 'application/octet-stream'))):
        return detail
    raise StoreError('该来源不支持在线文本编辑，请下载原件或在 Wiki 中修订', 415)


@knowledge_bp.route('/api/kb/documents/<document_id>', methods=['PUT'])
def kb_document_update(document_id):
    body = _json_body()
    text = body.get('text')
    if not isinstance(text, str) or not text.strip():
        raise StoreError('text 必须是非空字符串', 400)
    if '\x00' in text:
        raise StoreError('正文不能包含二进制空字符', 400)
    kb_id = body.get('kb_id')
    if kb_id is not None and (not isinstance(kb_id, str) or not kb_id.strip()):
        raise StoreError('kb_id 必须是非空字符串', 400)
    client = _client()
    detail = _editable_document(client, kb_id, document_id)
    if detail['source_type'] == 'file':
        with tempfile.TemporaryDirectory(prefix='contextdb-edit-') as directory:
            path = Path(directory) / 'source'
            path.write_text(text, encoding='utf-8')
            result = client.update_file(document_id, detail['name'], path,
                                        mime_type=detail.get('mime_type') or 'application/octet-stream')
    else:
        result = client.update_text_document(text, document_id=document_id)
    return jsonify(success=True, document=result)


@knowledge_bp.route('/api/kb/sync-status')
def kb_sync_status():
    job_id = (request.args.get('job_id') or '').strip()
    if not job_id:
        raise StoreError('缺少 job_id 参数', 400)
    from app import get_store
    store = get_store()
    job = store.get_job(job_id)
    return jsonify(success=True, job={
        key: job.get(key) for key in (
            'task_id', 'kind', 'scope', 'status', 'phase', 'progress', 'message',
            'completed_pages', 'total_pages', 'end_time')
    })

@knowledge_bp.route('/api/kb/review-settings')
def kb_review_settings_get():
    kb_id = (request.args.get('kb_id') or '').strip()
    if not kb_id:
        raise StoreError('缺少 kb_id 参数', 400)
    result = _client().get_review_settings(kb_id)
    return jsonify(success=True, settings=result)


@knowledge_bp.route('/api/kb/review-settings', methods=['PUT'])
def kb_review_settings_update():
    body = _json_body()
    kb_id = str(body.get('kb_id', '')).strip()
    if not kb_id:
        raise StoreError('缺少 kb_id 参数', 400)
    result = _client().update_review_settings(
        kb_id,
        review_enabled=body.get('review_enabled'),
        high_threshold=body.get('high_threshold'),
        rewrite_enabled=body.get('rewrite_enabled'),
        conflict_detection_enabled=body.get('conflict_detection_enabled'),
        rewrite_auto_ingest_enabled=body.get('rewrite_auto_ingest_enabled'),
        max_rewrite_iterations=body.get('max_rewrite_iterations'),
    )
    return jsonify(success=True, settings=result)


@knowledge_bp.route('/api/kb/events')
def kb_events():
    result = _client().list_events(
        event_type=request.args.get('event_type'),
        page=int(request.args.get('page', 1)),
        page_size=int(request.args.get('page_size', 20)),
    )
    events = result if isinstance(result, list) else result.get('events', result.get('data', []))
    return jsonify(success=True, events=events)


@knowledge_bp.route('/api/kb/documents/<document_id>/retry', methods=['POST'])
def kb_document_retry(document_id):
    result = _client().retry_document(document_id)
    return jsonify(success=True, retry=result)


@knowledge_bp.route('/api/kb/sync-mappings')
def sync_mappings():
    from governance.database import connection
    with connection() as conn:
        page=max(1,request.args.get('page',1,type=int))
        size=min(100,max(1,request.args.get('page_size',20,type=int)))
        total=conn.execute('SELECT count(*) AS n FROM knowledge_sync WHERE owner_id=%s',(user_id(),)).fetchone()['n']
        rows = conn.execute('SELECT * FROM knowledge_sync WHERE owner_id=%s ORDER BY updated_at DESC,source_id,target_mode LIMIT %s OFFSET %s', (user_id(),size,(page-1)*size)).fetchall()
    for row in rows:
        if not row['document_id']:
            continue
        try:
            detail = _client().get_document(row['knowledge_base_id'], row['document_id'])
            row['official'] = {key:detail.get(key) for key in ('name','review_status','lifecycle_state','ingest_status','ingest_error_message','graph_status','graph_error_message','latest_ingest_event_id','latest_graph_event_id','wiki_status','wiki_error_message') if key in detail}
        except ContextDBError as exc:
            row['official_error'] = str(exc)
    return jsonify(success=True, mappings=rows,total=total,page=page,page_size=size)
