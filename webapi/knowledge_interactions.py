"""Original knowledge UI over real ContextDB nodes, document metadata and REST.

Directory locators consist of native node IDs. Tags are explicit metadata
selectors, not invented ContextDB tag entities. Retrieval still uses MCP.
"""
import base64
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from urllib.parse import quote
import uuid

from flask import Blueprint, jsonify, request
from psycopg.types.json import Jsonb

from agent import registry
from governance.database import connection
from governance.store import StoreError, now
from webapi.auth import client_for_user, user_id

knowledge_interactions_bp = Blueprint('knowledge_interactions', __name__)
MAX_DOCUMENTS, MAX_NODES = 60000, 10000
TAG_KEY = 'tags'


def tag_selector(value):
    raw = json.dumps([TAG_KEY, value], ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
    return 'metadata:' + base64.urlsafe_b64encode(raw).decode().rstrip('=')


def tag_value(selector):
    if not isinstance(selector, str) or not selector.startswith('metadata:') or not re.fullmatch(r'[A-Za-z0-9_-]+', selector[9:]):
        raise StoreError('标签须为当前 ContextDB 文档元数据选择器', 400)
    try:
        key, value = json.loads(base64.b64decode(selector[9:] + '=' * (-len(selector[9:]) % 4), altchars=b'-_', validate=True))
        if key != TAG_KEY or not isinstance(value, (str, int, float, bool)) or isinstance(value, float) and not math.isfinite(value) or tag_selector(value) != selector:
            raise ValueError()
        return value
    except (ValueError, TypeError, UnicodeError):
        raise StoreError('ContextDB 元数据选择器无效', 400)


def all_documents(client, kb_id, *, metadata_condition=None):
    result, seen = [], set()
    for page in range(1, MAX_DOCUMENTS // 100 + 2):
        response = client.list_documents(kb_id, page=page, page_size=100,
            metadata_condition=metadata_condition, sort_by='created_at', sort_order='asc')
        batch = response.get('documents', [])
        if not isinstance(batch, list):
            raise StoreError('ContextDB 文档目录响应无效', 502)
        for item in batch:
            if item.get('knowledge_base_id') != kb_id or not item.get('id') or item['id'] in seen:
                raise StoreError('文档目录发生变化或归属不符，请刷新', 409)
            result.append(item)
            seen.add(item['id'])
        if len(result) > MAX_DOCUMENTS or response.get('total', 0) > MAX_DOCUMENTS:
            raise StoreError('元数据目录超出 60000 篇文档，请在 ContextDB 中收窄知识库范围', 413)
        if len(batch) < 100 or response.get('total') is not None and len(result) >= response['total']:
            return result
    raise StoreError('ContextDB 文档分页未结束', 502)


def _tags(document):
    value = (document.get('metadata') or {}).get(TAG_KEY, [])
    values = value if isinstance(value, list) else [value]
    return [item for item in values if isinstance(item, (str, int, float, bool)) and not (isinstance(item, float) and not math.isfinite(item))]


def tag_document_ids(client, kb_id, selectors):
    """Resolve OR semantics to real native IDs, with no whole-library fallback."""
    if not isinstance(selectors, list) or not selectors or len(selectors) > 100:
        raise StoreError('请选择 1 至 100 个元数据标签', 400)
    client.get_knowledge_base(kb_id)
    documents, seen = [], set()
    for selector in selectors:
        matches = all_documents(client, kb_id, metadata_condition={TAG_KEY: tag_value(selector)})
        if not matches:
            raise StoreError('标签不存在或已没有可读取的文档，请刷新后选择', 404)
        for document in matches:
            if document['id'] not in seen:
                documents.append(document['id'])
                seen.add(document['id'])
    if len(documents) > MAX_NODES:
        raise StoreError('所选标签超过 10000 篇文档，请收窄范围', 413)
    return documents


def node_tree(client, kb_id, documents):
    folders, paths, doc_paths, visited = [], {}, {}, set()
    revision = None
    def layer(parent_id=None):
        nonlocal revision
        items = []
        for page in range(1, MAX_NODES // 100 + 2):
            params = {'knowledge_base_id': kb_id, 'page': page, 'page_size': 100, 'sort_by': 'created_at', 'sort_order': 'asc'}
            if parent_id:
                params['parent_node_id'] = parent_id
            response = client._request('GET', '/v1/knowledge/nodes', params=params)
            if revision is None:
                revision = response.get('tree_revision')
            elif response.get('tree_revision') != revision:
                raise StoreError('知识库目录已变化，请刷新', 409)
            if not parent_id:
                root = response.get('parent_node') or {}
                if not root.get('node_id') or root.get('node_type') != 'root':
                    raise StoreError('ContextDB 根目录尚未就绪，请稍后重试', 409)
                paths[''] = {'node_id': root['node_id'], 'display_path': '', 'node': root}
            batch = response.get('items', [])
            items.extend(batch)
            if len(items) + len(visited) > MAX_NODES:
                raise StoreError('目录超过 10000 个节点，请使用 ContextDB 原生目录按层访问', 413)
            if len(batch) < 100 or response.get('total') is not None and len(items) >= response['total']:
                return items
        raise StoreError('ContextDB 目录分页未结束', 502)
    def walk(items, parent_path, parent_names, output, depth):
        if depth > 32:
            raise StoreError('ContextDB 目录深度超出原生上限', 502)
        for item in items:
            identifier = item.get('node_id')
            if not identifier or identifier in visited:
                raise StoreError('目录节点重复或发生循环，请刷新', 409)
            visited.add(identifier)
            if item.get('document_id'):
                doc_paths[item['document_id']] = parent_path
            if item.get('node_type') == 'folder' or item.get('has_children'):
                path = '/'.join(filter(None, [parent_path, quote(identifier, safe='')]))
                names = [*parent_names, item.get('display_name') or identifier]
                paths[path] = {'node_id': identifier, 'display_path': '/'.join(names), 'node': item}
                node = {'path': path, 'node_id': identifier, 'name': item['display_name'], 'children': [],
                        'document_count': 0, 'total_count': 0}
                output.append(node)
                walk(layer(identifier), path, names, node['children'], depth + 1)
    walk(layer(), '', [], folders, 1)
    visible = {document['id'] for document in documents}
    direct = {}
    for document in documents:
        path = doc_paths.get(document['id'], '')
        doc_paths[document['id']] = path
        direct[path] = direct.get(path, 0) + 1
    def count(nodes):
        for node in nodes:
            count(node['children'])
            node['document_count'] = direct.get(node['path'], 0)
            node['total_count'] = node['document_count'] + sum(child['total_count'] for child in node['children'])
    count(folders)
    return {'folders': folders, 'root_document_count': direct.get('', 0), 'total_document_count': len(visible),
            'tree_revision': revision}, paths, doc_paths


def document_view(document, *, folder_path='', folder_display_path=''):
    metadata = document.get('metadata') or {}
    title = metadata.get('title') if isinstance(metadata.get('title'), str) else document.get('name', '')
    manual = metadata.get('document_type') == 'manual'
    statuses = {'succeeded': 'completed', 'processing': 'processing', 'pending': 'pending', 'uploading': 'processing',
        'ai_reviewing': 'processing', 'pending_review': 'pending_review', 'failed': 'failed', 'deleting': 'deleting', 'deleted': 'deleted'}
    return {**document, 'title': title, 'file_name': document.get('name', ''), 'file_type': 'md' if manual else Path(document.get('name', '')).suffix.lstrip('.').lower(),
        'file_size': document.get('size_bytes'), 'type': 'manual' if manual else 'file', 'source': 'manual' if manual else document.get('source_type'),
        'folder_path': folder_path, 'folder_display_path': folder_display_path, 'parse_status': statuses.get(document.get('ingest_status'), document.get('ingest_status')),
        'tag_ids': [tag_selector(value) for value in _tags(document)], 'custom_metadata': metadata}


def _page():
    page, size = request.args.get('page', 1, type=int), request.args.get('page_size', 20, type=int)
    if not 1 <= page <= 100000 or not 1 <= size <= 100:
        raise StoreError('分页参数超出范围', 400)
    return page, size


def _time(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed
    except (ValueError, AttributeError):
        raise StoreError('时间须为带时区的 ISO8601 字符串', 400)


@knowledge_interactions_bp.get('/api/v1/knowledge-bases/<kb_id>/knowledge/folders')
def folders(kb_id):
    client = client_for_user()
    client.get_knowledge_base(kb_id)
    documents = all_documents(client, kb_id)
    tree, _, _ = node_tree(client, kb_id, documents)
    return jsonify(success=True, data=tree)


@knowledge_interactions_bp.get('/api/v1/knowledge-bases/<kb_id>/tags')
def tags(kb_id):
    client = client_for_user()
    client.get_knowledge_base(kb_id)
    values = {}
    for document in all_documents(client, kb_id):
        for value in _tags(document):
            identifier = tag_selector(value)
            entry = values.setdefault(identifier, {'id': identifier, 'name': str(value), 'knowledge_base_id': kb_id,
                'metadata_key': TAG_KEY, 'metadata_value': value, 'source': 'contextdb_metadata', 'knowledge_count': 0})
            entry['knowledge_count'] += 1
    keyword = request.args.get('keyword', '').casefold()
    items = sorted((value for value in values.values() if keyword in value['name'].casefold()), key=lambda value: (value['name'].casefold(), value['id']))
    page, size = _page()
    return jsonify(success=True, data={'data': items[(page-1)*size:page*size], 'total': len(items), 'page': page, 'page_size': size})


@knowledge_interactions_bp.get('/api/v1/knowledge-bases/<kb_id>/knowledge')
def knowledge_list(kb_id):
    client = client_for_user()
    client.get_knowledge_base(kb_id)
    documents = all_documents(client, kb_id)
    requested_path = request.args.get('folder_path')
    tree, paths, doc_paths = node_tree(client, kb_id, documents) if requested_path is not None else (None, {'': {'display_path': ''}}, {})
    if requested_path is not None and requested_path not in paths:
        raise StoreError('知识库目录已不存在，请刷新', 404)
    recursive = request.args.get('folder_recursive', 'false')
    if recursive not in ('true', 'false'):
        raise StoreError('folder_recursive 须为布尔值', 400)
    selected_tags = request.args.get('tag_ids', '')
    selectors = selected_tags.split(',') if selected_tags else []
    allowed_tags = {tag_selector(tag_value(selector)) for selector in selectors}
    keyword = request.args.get('keyword', '').casefold()
    file_type = request.args.get('file_type', '').lower().lstrip('.')
    parse_status, source = request.args.get('parse_status'), request.args.get('source')
    start = _time(request.args['start_time']) if request.args.get('start_time') else None
    end = _time(request.args['end_time']) if request.args.get('end_time') else None
    items = []
    for document in documents:
        path = doc_paths.get(document['id'], '')
        if requested_path is not None and not (path == requested_path or recursive == 'true' and (not requested_path or path.startswith(requested_path + '/'))):
            continue
        item = document_view(document, folder_path=path, folder_display_path=paths.get(path, {}).get('display_path', ''))
        if allowed_tags and not allowed_tags.intersection(item['tag_ids']):
            continue
        if keyword not in (item['title'] + '\n' + item['file_name']).casefold() or file_type and item['file_type'] != file_type:
            continue
        if parse_status and item['parse_status'] != parse_status or source and item['source'] != source:
            continue
        created = _time(item['created_at']) if start or end else None
        if start and created < start or end and created > end:
            continue
        items.append(item)
    field, order = request.args.get('sort_by', 'created_at'), request.args.get('sort_order', 'desc')
    if field not in ('file_name', 'created_at', 'updated_at') or order not in ('asc', 'desc'):
        raise StoreError('排序参数无效', 400)
    items.sort(key=lambda item: ((item.get(field) or '').casefold(), item['id']), reverse=order == 'desc')
    page, size = _page()
    return jsonify(success=True, data=items[(page-1)*size:page*size], total=len(items), page=page, page_size=size)
