"""Authenticated forwarding to declared official APIs. No knowledge algorithms or storage."""
import json
import re
import tempfile
import zipfile
from pathlib import Path

from flask import Blueprint, Response, g, jsonify, request, send_file

from common.converter import clean_filename
from governance.store import StoreError
from governance.knowledge_names import KnowledgeNames
from webapi.auth import client_for_user, user_id

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
    if resource == 'knowledge/files' and request.method == 'POST':
        uploaded = request.files.get('file')
        if not uploaded or not uploaded.filename:
            raise StoreError('缺少上传文件', 400)
        with tempfile.TemporaryDirectory(prefix='contextdb-upload-') as directory:
            local = Path(directory) / 'upload'
            uploaded.save(local)
            result = client.upload_file(request.form.get('knowledge_base_id', ''), uploaded.filename, str(local),
                                        file_path=request.form.get('file_path'), mime_type=uploaded.mimetype,
                                        parent_node_id=request.form.get('parent_node_id'))
    else:
        body = request.get_json(silent=True) if request.method not in ('GET', 'HEAD') else None
        if resource == 'knowledge/query' and isinstance(body, dict) and 'query' in body:
            if 'question' in body and body['question'] != body['query']:
                raise StoreError('query 与 question 不能指定不同的问题', 400)
            body = {**body, 'question': body['query']}
            body.pop('query')
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
    client = client_for_user()
    detail = client._request('GET', '/v1/knowledge/documents/detail',
                             params={'document_id': document_id, 'with_download_url': 'true'})
    if not detail.get('download_url'):
        raise StoreError('官方未返回源文件下载地址', 409)
    # Only a URL obtained from the authenticated official detail may be fetched.
    upstream = client._session.get(detail['download_url'], timeout=client.timeout)
    upstream.raise_for_status()
    return Response(upstream.content, content_type=upstream.headers.get('Content-Type', 'application/octet-stream'))


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
                name = names_view.document(detail, kb_id=kb_id)['display_name'] or 'document'
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
