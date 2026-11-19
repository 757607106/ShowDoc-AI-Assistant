"""Authenticated forwarding to declared official APIs. No knowledge algorithms or storage."""
import json
from contextlib import ExitStack
import re
import tempfile
import zipfile
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

from common.converter import clean_filename
from governance.store import StoreError
from governance.knowledge_names import KnowledgeNames, download_name
from webapi.auth import client_for_user, user_id
from webapi.contextdb.preview import asset_response, attachment_response, document_response

contextdb_bp = Blueprint('contextdb', __name__)
MAX_BATCH_DOWNLOAD_BYTES = 512 * 1024 * 1024
DECLARED_V1 = {
    'ping', 'events', 'workspaces/members', 'workspaces/members/detail',
    'workspaces/members/self/permissions', 'workspaces/members/permissions',
    'workspaces/groups', 'workspaces/groups/members', 'workspaces/groups/members/batch',
    'workspaces/groups/permissions', 'workspaces/knowledge_acls',
    'workspaces/knowledge_acls/batch', 'workspaces/knowledge_acl_matrix',
    'workspaces/knowledge_base_permission_subjects', 'workspaces/feature_whitelist',
    'knowledge/knowledge_bases', 'knowledge/knowledge_bases/detail',
    'knowledge/documents', 'knowledge/documents/detail', 'knowledge/documents/batch',
    'knowledge/documents/metadata', 'knowledge/documents/retry', 'knowledge/documents/chunks',
    'knowledge/files', 'knowledge/files/init-upload', 'knowledge/files/chunks',
    'knowledge/files/complete', 'knowledge/files/abort', 'knowledge/events', 'knowledge/query',
    'knowledge/assets', 'knowledge/nodes', 'knowledge/nodes/ensure', 'knowledge/nodes/batch',
    'knowledge/entities', 'knowledge/entities/detail', 'knowledge/entities/chunks',
    'knowledge/entity-relations', 'knowledge/entity-relations/detail',
    'knowledge/graph-visual', 'knowledge/graph/consolidate',
    'knowledge/reviews', 'knowledge/reviews/detail', 'knowledge/reviews/action',
    'knowledge/reviews/resolve-conflicts', 'knowledge/reviews/batch',
    'knowledge/review_settings', 'knowledge/review_templates', 'knowledge/review_templates/detail',
    'knowledge/review_templates/set_default', 'knowledge/review_templates/default',
}
WIKI_METHODS = {
    'knowledge/wiki/index': {'GET'},
    'knowledge/wiki/pages': {'GET', 'POST', 'PUT', 'DELETE'},
    'knowledge/wiki/pages/detail': {'GET'},
    'knowledge/wiki/search': {'GET'},
    'knowledge/wiki/summary': {'GET'},
    'knowledge/wiki/revisions': {'GET'},
    'knowledge/wiki/revisions/diff': {'GET'},
    'knowledge/wiki/directories': {'POST'},
    'knowledge/wiki/directories/actions': {'POST'},
    'knowledge/wiki/pages/actions': {'POST'},
    'knowledge/wiki/compile-runs': {'GET'},
    'knowledge/wiki/compile-runs/actions': {'POST'},
    'knowledge/wiki/issues': {'GET'},
    'knowledge/wiki/issues/detail': {'GET'},
    'knowledge/wiki/issues/actions': {'POST'},
    'knowledge/wiki/issues/tasks': {'POST'},
    'knowledge/wiki/issue-tasks/detail': {'GET'},
}


def forward_nodes(client, store, resource):
    from governance.knowledge_bases import base_write_lock, require_writable_base
    params = request.args.to_dict()
    kb_id = params.pop('knowledge_base_id', None)
    body = request.get_json(silent=True) if request.method == 'PATCH' or resource.endswith('/batch') else None
    if body is not None and not isinstance(body, dict):
        raise StoreError('请求必须是 JSON 对象', 400)
    if not kb_id:
        raise StoreError('节点操作必须指定 knowledge_base_id，以核对所属知识库', 400)
    if isinstance(body, dict) and body.get('knowledge_base_id') not in (None, kb_id):
        raise StoreError('knowledge_base_id 不能指定不同目标', 400)
    body = {key: value for key, value in body.items() if key != 'knowledge_base_id'} if isinstance(body, dict) else body
    fields = {**params, **(body or {})}
    for key in ('node_id', 'parent_node_id'):
        if key in params and body and key in body and params[key] != body[key]:
            raise StoreError(f'{key} 不能指定不同目标', 400)
    ids = fields.get('ids') if resource.endswith('/batch') else [fields.get('node_id')]
    if not isinstance(ids, list) or not 1 <= len(ids) <= 50 or any(not isinstance(item, str) or not item.strip() for item in ids):
        raise StoreError('节点操作必须指定 1～50 个有效节点 ID', 400)
    if 'parent_node_id' in fields and (not isinstance(fields['parent_node_id'], str) or not fields['parent_node_id'].strip()):
        raise StoreError('移动目标必须是有效节点 ID', 400)
    checked = ids + ([fields['parent_node_id']] if fields.get('parent_node_id') else [])
    with base_write_lock(kb_id):
        require_writable_base(store, kb_id)
        for node_id in dict.fromkeys(checked):
            result = client._request('GET', '/v1/knowledge/nodes',
                params={'knowledge_base_id': kb_id, 'parent_node_id': node_id, 'page_size': 1})
            node = result.get('parent_node') if isinstance(result, dict) else None
            if not isinstance(node, dict) or node.get('node_id') != node_id:
                raise StoreError('节点所属知识库未确认，请刷新目录后重试', 409)
        return client._request(request.method, '/v1/' + resource, json_body=body, params=params)


@contextdb_bp.route('/api/contextdb/<version>/<path:resource>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def forward(version, resource):
    dynamic = bool(re.fullmatch(r'event/[A-Za-z0-9_-]+', resource))
    allowed = version == 'v1' and (resource in DECLARED_V1 or dynamic
                                 or request.method in WIKI_METHODS.get(resource, ()))
    if not allowed:
        raise StoreError('当前平台未提供该操作', 501)
    if resource == 'knowledge/wiki/revisions' and not request.args.get('page_id', '').strip():
        raise StoreError('官方章节修订列表必须指定 page_id，不是全库候选审批列表', 400)
    client = client_for_user()
    path = f'/{version}/{resource}'
    if resource == 'knowledge/assets':
        if request.method != 'GET':
            raise StoreError('资产接口只支持读取', 405)
        return asset_response(client, request.args.get('asset_id'))
    if resource == 'knowledge/knowledge_bases' and request.method not in ('GET', 'HEAD'):
        from webapi.material import get_store
        from governance.knowledge_bases import create_base, update_base, delete_base
        store = get_store()
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            raise StoreError('请求必须是 JSON 对象', 400)
        kb_id = request.args.get('knowledge_base_id') or body.get('knowledge_base_id')
        if request.args.get('knowledge_base_id') and body.get('knowledge_base_id') and request.args['knowledge_base_id'] != body['knowledge_base_id']:
            raise StoreError('knowledge_base_id 不能指定不同目标', 400)
        if request.method == 'POST':
            result = create_base(store, body)
        elif request.method == 'PUT':
            result = update_base(store, kb_id, body)
        elif request.method == 'DELETE':
            result = delete_base(store, kb_id)
        else:
            raise StoreError('知识库更新请使用 PUT', 405)
        return jsonify(success=True, data=result)
    from webapi.contextdb.files import RESOURCES, forward_file
    if resource in RESOURCES:
        from webapi.material import get_store
        result = forward_file(client, get_store(), resource)
    elif ((resource == 'knowledge/nodes' and request.method in ('PATCH', 'DELETE')) or
          (resource == 'knowledge/nodes/batch' and request.method in ('POST', 'DELETE'))):
        from webapi.material import get_store
        result = forward_nodes(client, get_store(), resource)
    elif resource == 'knowledge/reviews/batch' and request.method in ('POST', 'DELETE'):
        from webapi.material import get_store
        from governance.knowledge_bases import batch_reviews
        from integrations.contextdb.client import BATCH_REVIEW_ACTIONS
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            raise StoreError('请求必须是 JSON 对象', 400)
        if request.method == 'POST' and (
                not isinstance(body.get('action'), str) or body['action'] not in BATCH_REVIEW_ACTIONS):
            raise StoreError('不支持的批量评审动作', 400)
        result = batch_reviews(get_store(), body.get('ids'), lambda ids: client._request(
            request.method, path, json_body={**body, 'ids': ids}, params=request.args.to_dict()))
    else:
        body = request.get_json(silent=True) if request.method not in ('GET', 'HEAD') else None
        if resource == 'knowledge/query' and isinstance(body, dict) and 'query' in body:
            if 'question' in body and body['question'] != body['query']:
                raise StoreError('query 与 question 不能指定不同的问题', 400)
            body = {**body, 'question': body['query']}
            body.pop('query')
        with ExitStack() as writes:
            if request.method not in ('GET', 'HEAD') and resource.startswith('knowledge/') and resource != 'knowledge/query':
                from webapi.material import get_store
                from governance.knowledge_bases import base_write_lock, require_writable_base, review_base_ids
                fields = {**request.args.to_dict(), **(body if isinstance(body, dict) else {})}
                for key in ('knowledge_base_id', 'kb_id', 'document_id', 'review_id'):
                    if request.args.get(key) and isinstance(body, dict) and body.get(key) and request.args[key] != body[key]:
                        raise StoreError(f'{key} 不能指定不同目标', 400)
                if fields.get('knowledge_base_id') and fields.get('kb_id') and fields['knowledge_base_id'] != fields['kb_id']:
                    raise StoreError('knowledge_base_id 与 kb_id 不能指定不同目标', 400)
                kb_id = fields.get('knowledge_base_id') or fields.get('kb_id')
                document_id = fields.get('document_id')
                store = get_store()
                ids = []
                if fields.get('review_id'):
                    ids = review_base_ids(store, [fields['review_id']])
                elif kb_id or document_id:
                    ids = [require_writable_base(store, kb_id, document_id)['knowledge_base_id']]
                for target in ids:
                    writes.enter_context(base_write_lock(target))
                    require_writable_base(store, target)
                result = client._request(request.method, path, json_body=body, params=request.args.to_dict())
            else:
                result = client._request(request.method, path, json_body=body, params=request.args.to_dict())
    if request.method == 'GET' or resource == 'knowledge/query':
        result = KnowledgeNames(user_id()).present(resource, result, kb_id=request.args.get('knowledge_base_id'))
    return jsonify(success=True, data=result)


@contextdb_bp.route('/api/platform/capabilities')
def capabilities():
    path = Path(__file__).resolve().parents[1] / 'docs/architecture/contextdb-capabilities.json'
    if not path.exists():
        raise StoreError('请先运行官方接口契约验证', 503)
    return jsonify(success=True, data=json.loads(path.read_text()))


@contextdb_bp.route('/api/contextdb/documents/<document_id>/download')
def download(document_id):
    return document_response(client_for_user(), document_id, request.args.get('knowledge_base_id'))


@contextdb_bp.get('/api/contextdb/assets/<asset_id>')
def asset(asset_id):
    return asset_response(client_for_user(), asset_id)


@contextdb_bp.get('/api/contextdb/documents/<document_id>/attachments/<int:chunk_index>/<int:attachment_index>')
def attachment(document_id, chunk_index, attachment_index):
    return attachment_response(client_for_user(), document_id, chunk_index, attachment_index,
                               request.args.get('knowledge_base_id'))


@contextdb_bp.get('/api/contextdb/documents/<document_id>/source-images')
def source_images(document_id):
    from webapi.contextdb.source_images import source_images
    images = source_images(client_for_user(), document_id, request.args.get('knowledge_base_id'))
    return jsonify(success=True, data={'document_id': document_id, 'images': [
        {'image_key': key, 'description': image['description']} for key, image in images.items()]})


@contextdb_bp.get('/api/contextdb/documents/<document_id>/source-images/<image_key>')
def source_image(document_id, image_key):
    from webapi.contextdb.source_images import source_image_response
    return source_image_response(client_for_user(), document_id, image_key, request.args.get('knowledge_base_id'))


@contextdb_bp.route('/api/v1/knowledge-bases/<kb_id>/knowledge/batch-download', methods=['POST'])
def batch_download(kb_id):
    body = request.get_json(silent=True)
    ids = body.get('ids') if isinstance(body, dict) else None
    if not isinstance(ids, list) or not 1 <= len(ids) <= 200 or any(not isinstance(value, str) or not value.strip() for value in ids):
        raise StoreError('请选择 1 至 200 篇文档', 400)
    if len(set(ids)) != len(ids):
        raise StoreError('请勿重复选择文档', 400)
    client = client_for_user()
    details = []
    for document_id in ids:
        detail = client._request('GET', '/v1/knowledge/documents/detail',
                                 params={'document_id': document_id, 'with_download_url': 'true'})
        if detail.get('knowledge_base_id') != kb_id:
            raise StoreError('所选文档不属于当前知识库', 404)
        if not detail.get('download_url'):
            raise StoreError('所选文档的源文件不可下载', 409)
        details.append(detail)
    archive = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024)
    names_view = KnowledgeNames(user_id())
    try:
        total_bytes = 0
        names = set()
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as output:
            for detail in details:
                name = download_name(names_view.document(detail, kb_id=kb_id)) or 'document'
                name = clean_filename(name)
                original, number = Path(name), 1
                while name.casefold() in names:
                    number += 1
                    name = f'{original.stem} ({number}){original.suffix}'
                names.add(name.casefold())
                upstream = client._session.get(detail['download_url'], timeout=client.timeout, stream=True)
                try:
                    upstream.raise_for_status()
                    with output.open(name, 'w') as target:
                        for chunk in upstream.iter_content(chunk_size=64 * 1024):
                            total_bytes += len(chunk)
                            if total_bytes > MAX_BATCH_DOWNLOAD_BYTES:
                                raise StoreError('单次下载的源文件总大小不能超过 512 MB', 413)
                            target.write(chunk)
                finally:
                    upstream.close()
        archive.seek(0)
        response = send_file(archive, mimetype='application/zip', as_attachment=True, download_name='knowledge-files.zip')
        response.call_on_close(archive.close)
        return response
    except Exception:
        archive.close()
        raise
