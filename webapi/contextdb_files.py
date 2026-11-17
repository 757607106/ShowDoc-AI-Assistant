"""Forward official file uploads while retaining the owning knowledge-base identity."""
import hashlib
import json
import tempfile
from pathlib import Path

from flask import request
import requests

from common.converter import prepare_review_file
from governance.knowledge_bases import base_write_lock, require_writable_base
from governance.store import StoreError
from integrations.contextdb import ContextDBError


RESOURCES = {'knowledge/files': {'POST', 'PUT'},
             'knowledge/files/init-upload': {'POST', 'PUT'},
             'knowledge/files/chunks': {'POST'}, 'knowledge/files/complete': {'POST'},
             'knowledge/files/abort': {'POST'}}


def forward_file(client, store, resource):
    if request.method not in RESOURCES[resource]:
        raise StoreError('文件接口不支持该请求方法', 405)
    if resource in {'knowledge/files', 'knowledge/files/init-upload'}:
        fields = request.form if resource == 'knowledge/files' else request.get_json(silent=True) or request.args.to_dict()
        if not isinstance(fields, dict) and resource != 'knowledge/files':
            raise StoreError('请求必须是 JSON 对象', 400)
        kb_id = fields.get('knowledge_base_id')
        if fields.get('document_id'):
            kb_id = client.get_document(None, fields['document_id']).get('knowledge_base_id')
    else:
        ticket = request.headers.get('X-Upload-Ticket', '')
        receipt = store._find('knowledge_upload', upload_key=hashlib.sha256(ticket.encode()).hexdigest()) if ticket else None
        if not receipt:
            raise StoreError('当前账号没有对应的分片上传记录，请重新初始化上传', 409 if ticket else 400)
        kb_id = store._body(receipt['id']).get('knowledge_base_id')
    if not kb_id:
        raise StoreError('缺少 knowledge_base_id，无法确认目标知识库', 400)
    with base_write_lock(kb_id):
        try:
            return _forward_file(client, store, resource)
        except requests.RequestException as exc:
            raise ContextDBError('文件请求结果未确认，请查询文档实际状态；不会自动重试') from exc
        except StoreError:
            raise
        except ValueError as exc:
            raise StoreError(str(exc), 400) from exc


def _forward_file(client, store, resource):
    path = '/v1/' + resource
    if resource == 'knowledge/files':
        upload = request.files.get('file')
        if not upload or not upload.filename:
            raise StoreError('缺少上传文件', 400)
        fields = request.form
        document_id = fields.get('document_id')
        if request.method == 'PUT' and not document_id:
            raise StoreError('更新文件必须指定 document_id', 400)
        if request.method == 'POST' and document_id:
            raise StoreError('新文件请指定 knowledge_base_id，已有文档使用 PUT 更新', 400)
        space = require_writable_base(store, fields.get('knowledge_base_id'), document_id)
        kb_id = space['knowledge_base_id']
        try:
            metadata = json.loads(fields['metadata']) if 'metadata' in fields else None
        except ValueError as exc:
            raise StoreError('metadata 必须是 JSON 对象', 400) from exc
        if metadata is not None and not isinstance(metadata, dict):
            raise StoreError('metadata 必须是 JSON 对象', 400)
        if 'review_enabled' in fields:
            if fields['review_enabled'] not in ('true', 'false'):
                raise StoreError('review_enabled 必须是 true 或 false', 400)
        review_enabled = fields['review_enabled'] == 'true' if 'review_enabled' in fields else None
        with tempfile.TemporaryDirectory(prefix='contextdb-file-') as directory:
            name = fields.get('name') or Path(upload.filename.replace('\\', '/')).name
            local = Path(directory) / 'source'
            upload.save(local)
            if not local.stat().st_size:
                raise StoreError('不能上传空文件', 400)
            source_name = name
            name, local, _ = prepare_review_file(client, kb_id, name, local, review_enabled=review_enabled)
            if name != source_name and 'filename' not in (metadata or {}):
                if len(metadata or {}) >= 32:
                    raise StoreError('格式转换需保留原始文件名，请在 metadata 预留 filename 字段或减少一个字段', 422)
                metadata = {**(metadata or {}), 'filename': source_name}
            options = {'metadata': metadata, 'mime_type': 'text/markdown' if name.endswith('.md') else upload.mimetype,
                       'review_template_id': fields.get('review_template_id'), 'review_enabled': review_enabled}
            if request.method == 'PUT':
                return client.update_file(document_id, name, local, **options)
            return client.upload_file(kb_id, name, local, file_path=fields.get('file_path'),
                parent_node_id=fields.get('parent_node_id'), **options)

    if resource == 'knowledge/files/init-upload':
        fields = request.get_json(silent=True) or request.args.to_dict()
        if (not isinstance(fields, dict) or not isinstance(fields.get('file_name'), str)
                or not fields['file_name'].strip()):
            raise StoreError('分片上传必须指定 file_name', 400)
        if 'review_enabled' in fields:
            raise StoreError('分片上传不支持单次评审开关，评审方式跟随知识库设置；请使用普通上传或移除 review_enabled', 400)
        if request.method == 'PUT' and (not fields.get('document_id') or any(
                key in fields for key in ('knowledge_base_id', 'name', 'file_path', 'parent_node_id'))):
            raise StoreError('分片更新仅使用 document_id 定位文档', 400)
        if request.method == 'POST' and fields.get('document_id'):
            raise StoreError('已有文档请使用 PUT 初始化更新', 400)
        space = require_writable_base(store, fields.get('knowledge_base_id'), fields.get('document_id'))
        base = client.get_knowledge_base(space['knowledge_base_id'])
        if base.get('review_enabled') and Path(fields['file_name']).suffix.lower() not in {
                '.txt', '.md', '.markdown', '.pdf', '.doc', '.docx'}:
            raise StoreError('该格式不能直接分片送审，请使用资料上传入口或调整知识库评审策略', 422)
        fields = {key: json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value
                  for key, value in fields.items()}
        result = client._request(request.method, path, params=fields)
        if (not isinstance(result, dict) or not isinstance(result.get('upload_ticket'), str)
                or not result['upload_ticket'] or result.get('knowledge_base_id') != space['knowledge_base_id']):
            raise StoreError('官方分片初始化响应缺少可核对的知识库或票据', 502)
        key = hashlib.sha256(result['upload_ticket'].encode()).hexdigest()
        store._create('knowledge_upload', key,
            {'knowledge_base_id': space['knowledge_base_id'], 'document_id': result.get('document_id'),
             'state': 'uploading'}, {'upload_key': key, 'scope': space['scope']})
        return result

    ticket = request.headers.get('X-Upload-Ticket', '')
    if not ticket:
        raise StoreError('缺少 X-Upload-Ticket', 400)
    key = hashlib.sha256(ticket.encode()).hexdigest()
    receipt = store._find('knowledge_upload', upload_key=key)
    if not receipt:
        raise StoreError('当前账号没有对应的分片上传记录，请重新初始化上传', 409)
    state = store._body(receipt['id'])
    if state['state'] != 'uploading':
        raise StoreError('该分片会话已提交完成或取消，请查看文档实际状态，勿重复提交', 409)
    require_writable_base(store, state['knowledge_base_id'])
    headers = {**client._headers(), 'X-Upload-Ticket': ticket}
    if resource == 'knowledge/files/chunks':
        upload = request.files.get('data')
        part = request.form.get('part_number', type=int)
        if not upload or not part or part < 1:
            raise StoreError('缺少有效的 part_number 或 data 分片', 400)
        response = client._session.post(client.base_url + path, data={'part_number': part},
            files={'data': (upload.filename or 'part', upload.stream, upload.mimetype)},
            headers=headers, timeout=client.timeout)
    else:
        body = request.get_json(silent=True) if resource.endswith('/complete') else None
        if resource.endswith('/complete'):
            parts = body.get('parts') if isinstance(body, dict) else None
            if (not isinstance(parts, list) or not parts or any(
                    not isinstance(part, dict) or type(part.get('part_number')) is not int
                    or part['part_number'] != i or not isinstance(part.get('etag'), str) or not part['etag']
                    for i, part in enumerate(parts, 1))):
                raise StoreError('完成上传必须提供按顺序排列的 parts 回执', 400)
            store._write(receipt['id'], {**state, 'state': 'completing'})
        response = client._session.request('POST', client.base_url + path, json=body,
            headers=headers, timeout=client.timeout)
    try:
        result = client._payload(response)
    except ContextDBError as exc:
        if resource.endswith('/complete') and exc.status_code and 400 <= exc.status_code < 500 and exc.status_code != 409:
            store._write(receipt['id'], state)
        raise
    if resource.endswith('/complete') and (not isinstance(result, dict)
            or not isinstance(result.get('document_id'), str) or not result['document_id'].strip()
            or result.get('knowledge_base_id') != state['knowledge_base_id']):
        raise StoreError('完成上传结果未确认，请查看文档实际状态，勿重复完成或取消', 502)
    if not resource.endswith('/chunks'):
        store._write(receipt['id'], {**state, 'state': 'completed' if resource.endswith('/complete') else 'aborted',
                                   'document_id': (result or {}).get('document_id', state.get('document_id'))})
    return result
