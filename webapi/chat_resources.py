"""User supplied chat files and generated artifacts, isolated from permanent knowledge."""
import base64
import asyncio
import io
import json
import mimetypes
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Blueprint, g, jsonify, request, send_file
from psycopg.types.json import Jsonb
from werkzeug.utils import secure_filename

from agent import sessions
from governance.database import connection
from governance.store import StoreError, data_dir
from webapi.auth import client_for_user, user_id
from webapi.legacy_runtime import unavailable

chat_resources_bp = Blueprint('chat_resources', __name__)
TEXT_EXTENSIONS = {'.txt', '.md', '.csv', '.tsv', '.json', '.xml', '.html', '.htm', '.yaml', '.yml', '.log', '.py', '.js', '.ts', '.sql', '.css'}
IMAGE_MIMES = {'image/png', 'image/jpeg', 'image/webp', 'image/gif'}


@chat_resources_bp.route('/api/v1/tenants/kv/storage-engine-config')
def attachment_storage_config():
    return jsonify(success=True, data={'default_provider': 'local', 'local': {'path_prefix': 'chat-attachments'},
        **{provider: {} for provider in ('minio', 'cos', 'tos', 's3', 'oss', 'ks3', 'obs')}})


@chat_resources_bp.route('/api/v1/system/storage-engine-status')
def attachment_storage_status():
    directory = data_dir() / 'chat-attachments'
    directory.mkdir(parents=True, exist_ok=True)
    return jsonify(success=True, data={'engines': [{'name': 'local', 'allowed': True,
        'available': os.access(directory, os.W_OK), 'description': '成员与会话隔离的聊天附件存储'}],
        'allowed_providers': ['local'], 'minio_env_available': False})


@chat_resources_bp.route('/api/v1/system/parser-engines')
def attachment_parser_engines():
    return jsonify(success=True, connected=True, data=[{'Name': 'local', 'Available': True,
        'Description': '聊天附件本机解析；永久知识库解析由 ContextDB 管理',
        'FileTypes': [*sorted(extension.lstrip('.') for extension in TEXT_EXTENSIONS), 'pdf', 'docx', 'pptx', 'xlsx', 'xlsm']}])


def _text_file(path):
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return path.read_text(encoding='utf-8-sig')
    if path.suffix.lower() == '.docx':
        from docx import Document
        document = Document(path)
        return '\n'.join([p.text for p in document.paragraphs] + ['\t'.join(cell.text for cell in row.cells) for table in document.tables for row in table.rows])
    if path.suffix.lower() in {'.xlsx', '.xlsm'}:
        from openpyxl import load_workbook
        book = load_workbook(path, read_only=True, data_only=True)
        try:
            return '\n\n'.join('# ' + sheet.title + '\n' + '\n'.join('\t'.join('' if v is None else str(v) for v in row) for row in sheet.iter_rows(values_only=True)) for sheet in book)
        finally:
            book.close()
    if path.suffix.lower() == '.pptx':
        from pptx import Presentation
        return '\n\n'.join('\n'.join(shape.text for shape in slide.shapes if shape.has_text_frame) for slide in Presentation(path).slides)
    if path.suffix.lower() == '.pdf':
        import pypdfium2 as pdfium
        document = pdfium.PdfDocument(path)
        try:
            pages = []
            for i in range(len(document)):
                page = document[i]
                text = page.get_textpage()
                try:
                    pages.append(text.get_text_range())
                finally:
                    text.close()
                    page.close()
            result = '\n\n'.join(pages)
            if result.strip():
                return result
        finally:
            document.close()
    # Other document formats use the already installed converter; no permanent KB is created.
    from docling.document_converter import DocumentConverter
    return DocumentConverter().convert(path).document.export_to_markdown()


def _attachment(sid, attachment_id, owner):
    sessions.get_session(sid, owner)
    with connection() as conn:
        row = conn.execute("SELECT payload FROM runtime_records WHERE id=%s AND owner_id=%s AND kind='chat_attachment' AND payload->>'session_id'=%s", (attachment_id, owner, sid)).fetchone()
    if not row:
        raise StoreError('附件不存在', 404)
    item = row['payload']
    if datetime.fromisoformat(item['expires_at']) < datetime.now(timezone.utc):
        raise StoreError('附件已过期，请重新上传', 410)
    return item


def _public_attachment(item):
    return {key: value for key, value in item.items() if key not in ('path', 'text')}


def _store_attachment(sid, owner, name, content, mime=None):
    if not content or len(content) > 25 * 1024 * 1024:
        raise StoreError('单个聊天附件须为 1 B 至 25 MB', 413)
    attachment_id = str(uuid.uuid4())
    name = Path(name or 'attachment.txt').name[:255]
    directory = data_dir() / 'chat-attachments' / owner / sid
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (attachment_id + Path(name).suffix.lower())
    path.write_bytes(content)
    mime = mime or mimetypes.guess_type(name)[0] or 'application/octet-stream'
    item = {'id': attachment_id, 'session_id': sid, 'file_name': name,
            'file_type': Path(name).suffix.lstrip('.').lower(), 'file_size': len(content), 'mime_type': mime,
            'status': 'ready', 'token_count': 0, 'chunk_count': 0, 'path': str(path),
            'expires_at': (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()}
    try:
        if mime not in IMAGE_MIMES:
            item['text'] = _text_file(path)
            if not item['text'].strip() or len(item['text']) > 4_000_000:
                raise ValueError('empty or excessive extracted text')
    except Exception as exc:
        item.update(status='failed', error_message=f'附件解析失败（{type(exc).__name__}），请检查格式或转为文本后重试')
    with connection() as conn:
        conn.execute("INSERT INTO runtime_records(id,owner_id,kind,record_key,name,payload,metadata) VALUES (%s,%s,'chat_attachment',%s,%s,%s,'{}')",
                     (attachment_id, owner, attachment_id, name, Jsonb(item)))
    return item


@chat_resources_bp.route('/api/v1/sessions/<sid>/attachments', methods=['POST'])
def upload_attachment(sid):
    if sessions.get_session(sid)['agent_config'].get('runtime') != 'deepagents':
        unavailable()
    file = request.files.get('file')
    if not file:
        raise StoreError('请选择附件', 400)
    if request.form.get('parser_engine') not in (None, '', 'auto', 'local', 'docling'):
        raise StoreError('此聊天附件解析引擎尚未配置', 400)
    item = _store_attachment(sid, user_id(), file.filename, file.read(25 * 1024 * 1024 + 1), file.mimetype)
    return jsonify(success=True, data=_public_attachment(item))


@chat_resources_bp.route('/api/v1/sessions/<sid>/attachments/<attachment_id>', methods=['GET', 'DELETE'])
@chat_resources_bp.route('/api/v1/sessions/<sid>/attachments/<attachment_id>/preview')
def attachment(sid, attachment_id):
    if request.method == 'DELETE' and sessions.get_session(sid)['agent_config'].get('runtime') != 'deepagents':
        unavailable()
    item = _attachment(sid, attachment_id, user_id())
    if request.method == 'DELETE':
        with connection() as conn:
            conn.execute("DELETE FROM runtime_records WHERE id=%s AND owner_id=%s AND kind='chat_attachment'", (attachment_id, user_id()))
        path = Path(item['path']).resolve()
        if path.is_relative_to((data_dir() / 'chat-attachments').resolve()):
            path.unlink(missing_ok=True)
        return jsonify(success=True)
    if request.path.endswith('/preview'):
        if not Path(item['path']).is_file():
            raise StoreError('附件文件已不存在', 404)
        return send_file(item['path'], download_name=item['file_name'], mimetype=item['mime_type'])
    return jsonify(success=True, data=_public_attachment(item))


def prepare_attachments(sid, owner, body):
    from deepagents.backends.utils import create_file_data
    files, blocks, user_images, attachments = {}, [], [], []
    ids = body.get('attachment_ids') or []
    images = body.get('images') or []
    uploads = body.get('attachment_uploads') or []
    if any(not isinstance(value, list) for value in (ids, images, uploads)) or len(ids) + len(images) + len(uploads) > 20:
        raise StoreError('每轮最多携带 20 个附件或图片', 400)
    ids = list(ids)
    for upload in uploads:
        if not isinstance(upload, dict) or not isinstance(upload.get('data'), str):
            raise StoreError('附件数据无效', 400)
        try:
            content = base64.b64decode(upload['data'].split(',', 1)[-1], validate=True)
        except ValueError:
            raise StoreError('附件编码无效', 400)
        item = _store_attachment(sid, owner, upload.get('file_name'), content)
        ids.append(item['id'])
    for attachment_id in ids:
        if not isinstance(attachment_id, str):
            raise StoreError('附件 ID 无效', 400)
        item = _attachment(sid, attachment_id, owner)
        if item['status'] != 'ready':
            raise StoreError(item.get('error_message') or '附件尚未就绪', 400)
        if item['mime_type'] in IMAGE_MIMES:
            content = base64.b64encode(Path(item['path']).read_bytes()).decode()
            blocks.append({'type': 'image_url', 'image_url': {'url': f'data:{item["mime_type"]};base64,{content}'}})
            user_images.append({'id': item['id'], 'url': f'/api/v1/sessions/{sid}/attachments/{item["id"]}/preview', 'file_name': item['file_name']})
        else:
            attachments.append(_public_attachment(item))
            name = secure_filename(item['file_name']) or 'attachment.txt'
            path = f'/attachments/{attachment_id}/{name}'
            files[path] = create_file_data(item['text'])
            blocks.append({'type': 'text', 'text': f'用户附件：{item["file_name"]}，可通过 read_file 读取 {path}'})
    for image in images:
        if not isinstance(image, dict) or not isinstance(image.get('data'), str):
            raise StoreError('图片数据无效', 400)
        data = image['data']
        if not data.startswith(tuple(f'data:{mime};base64,' for mime in IMAGE_MIMES)) or len(data) > 20_000_000:
            raise StoreError('图片须为有效的 PNG/JPEG/WebP/GIF，且小于 15 MB', 400)
        try:
            raw = base64.b64decode(data.split(',', 1)[1], validate=True)
        except ValueError:
            raise StoreError('图片编码无效', 400)
        blocks.append({'type': 'image_url', 'image_url': {'url': data}})
        mime = data[5:data.index(';')]
        extension = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/gif': 'gif'}[mime]
        item = _store_attachment(sid, owner, f'image-{len(user_images) + 1}.{extension}', raw, mime)
        ids.append(item['id'])
        user_images.append({'id': item['id'], 'url': f'/api/v1/sessions/{sid}/attachments/{item["id"]}/preview', 'file_name': item['file_name']})
    return {'files': files, 'message_blocks': blocks, 'attachment_ids': ids,
            'user_images': user_images, 'attachments': attachments} if files or blocks else {}


@chat_resources_bp.route('/api/v1/knowledge/search')
def document_picker():
    client = client_for_user()
    query = request.args.get('keyword', '').casefold()
    offset = max(0, request.args.get('offset', 0, type=int))
    limit = min(100, max(1, request.args.get('limit', 20, type=int)))
    types = set(filter(None, request.args.get('file_types', '').lower().split(',')))
    matches = []
    page = 1
    while True:
        bases = client.list_knowledge_bases(page=page, page_size=100).get('knowledge_bases', [])
        for base in bases:
            if base.get('name', '').startswith('_governance'):
                continue
            doc_page = 1
            while True:
                docs = client.list_documents(base['id'], page=doc_page, page_size=100).get('documents', [])
                for item in docs:
                    name = item.get('name', '')
                    extension = Path(name).suffix.lstrip('.').lower()
                    if query in name.casefold() and (not types or extension in types):
                        matches.append({**item, 'id': item['id'], 'title': name, 'file_name': name,
                            'file_type': extension, 'knowledge_base_id': base['id'], 'knowledge_base_name': base['name'],
                            'parse_status': 'completed' if item.get('ingest_status') == 'succeeded' else item.get('ingest_status')})
                if len(docs) < 100:
                    break
                doc_page += 1
        if len(bases) < 100:
            break
        page += 1
    return jsonify(success=True, data=matches[offset:offset + limit], total=len(matches))


def _artifact_record(sid, message_id):
    selected = sessions.get_session(sid)
    if selected['agent_config'].get('runtime') == 'deepagents':
        from webapi.weknora_artifacts import read
        turns = asyncio.run(read(g.user, selected))
        if message_id not in turns:
            raise StoreError('消息不存在', 404)
        return {'artifacts_json': [metadata for metadata, _ in turns[message_id]],
                'artifacts_truncated': False, '_native_items': turns[message_id]}
    with connection() as conn:
        row = conn.execute('SELECT * FROM agent_runs WHERE id=%s AND session_id=%s AND owner_id=%s', (message_id, sid, user_id())).fetchone()
    if not row:
        raise StoreError('消息不存在', 404)
    return row




@chat_resources_bp.route('/api/v1/sessions/<sid>/artifacts')
@chat_resources_bp.route('/api/v1/sessions/<sid>/messages/<message_id>/artifacts')
def artifacts(sid, message_id=None):
    if message_id is None:
        sessions.get_session(sid)
        return jsonify(success=True, read_only=True, data=_recorded_artifacts(sid))
    row = _artifact_record(sid, message_id)
    return jsonify(success=True, read_only=True, data=row['artifacts_json'], truncated=row['artifacts_truncated'])


@chat_resources_bp.route('/api/v1/sessions/<sid>/messages/<message_id>/artifacts/<int:index>/download')
def download_artifact(sid, message_id, index):
    row = _artifact_record(sid, message_id)
    metadata = next((item for item in row['artifacts_json'] if item['index'] == index), None)
    if not metadata or metadata.get('deleted_at'):
        raise StoreError('文件不存在或已删除', 404)
    if '_native_items' in row:
        from agent.artifacts import download
        item = next(item for meta, item in row['_native_items'] if meta['index'] == index)
        return send_file(io.BytesIO(download(user_id(), sid, metadata['source_path'], item)), as_attachment=True,
                         download_name=metadata['file_name'],
                         mimetype=mimetypes.guess_type(metadata['file_name'])[0] or 'application/octet-stream')
    if index >= len(row['artifact_sources']):
        raise StoreError('历史文件未保存版本地址，无法重新扫描已停用的运行器', 410)
    source = row['artifact_sources'][index]
    if source['path'] != metadata['source_path']:
        raise StoreError('历史文件版本地址不一致', 409)
    if source.get('workspace') or source.get('config_id') not in (None, '', 'state-backend'):
        raise StoreError('旧沙箱文件保留，下载需要已停用的执行器；未启动或删除沙箱', 410)
    from agent.artifacts import download
    item = {'_source': source, '_version_key': source['version_key']}
    path = source['path']
    return send_file(io.BytesIO(download(user_id(), sid, path, item)), as_attachment=True,
                     download_name=Path(path).name, mimetype=mimetypes.guess_type(path)[0] or 'text/plain')


@chat_resources_bp.route('/api/v1/sessions/<sid>/messages/<message_id>/artifacts/<int:index>', methods=['DELETE'])
def delete_artifact(sid, message_id, index, all_versions=False):
    unavailable(sid)


def _recorded_artifacts(sid=None):
    with connection() as conn:
        runs = conn.execute('''SELECT r.*,s.title FROM agent_runs r JOIN agent_sessions s ON s.id=r.session_id
            WHERE r.owner_id=%s AND s.parent_session_id IS NULL AND (%s::text IS NULL OR r.session_id=%s)
            ORDER BY r.created_at,r.id''', (user_id(), sid, sid)).fetchall()
        native_sessions = conn.execute("SELECT id,title,agent_config FROM agent_sessions WHERE owner_id=%s "
            "AND agent_config->>'runtime'='deepagents' AND (%s::text IS NULL OR id=%s) ORDER BY created_at,id",
            (user_id(), sid, sid)).fetchall()
    linked = {(run['pending_json'] or {}).get('resumed_run_id') for run in runs}
    values = [{**item, 'session_id': run['session_id'], 'session_title': run['title'], 'message_id': run['id']}
              for run in runs if run['id'] not in linked for item in run['artifacts_json']]
    from webapi.weknora_artifacts import read
    for selected in native_sessions:
        for message_id, items in asyncio.run(read(g.user, selected)).items():
            values.extend({**metadata, 'session_id': selected['id'], 'session_title': selected['title'],
                           'message_id': message_id} for metadata, _ in items)
    return values


@chat_resources_bp.route('/api/v1/artifacts', methods=['GET', 'DELETE'])
def artifact_library():
    if request.method == 'DELETE':
        unavailable(request.args.get('session_id'))
    latest = {}
    for item in _recorded_artifacts():
        if item.get('deleted_at'):
            continue
        key = (item['session_id'], item['source_path'])
        latest[key] = {**item, 'version_count': latest.get(key, {}).get('version_count', 0) + 1}
    keyword = request.args.get('keyword', '').casefold()
    types = {value.lstrip('.').lower() for value in request.args.get('file_types', '').split(',') if value}
    items = [item for item in latest.values() if keyword in item['file_name'].casefold()
             and (not types or item['file_type'] in types)]
    items.sort(key=lambda item: (item.get('mod_time') or item.get('created_at') or '', item['session_id'], item['index']), reverse=True)
    page = max(1, request.args.get('page', 1, type=int))
    size = min(100, max(1, request.args.get('page_size', 20, type=int)))
    return jsonify(success=True, data=items[(page-1)*size:page*size], total=len(items), page=page, page_size=size)


@chat_resources_bp.route('/api/v1/sessions/transcriptions', methods=['POST'])
def transcribe():
    from agent.config import load_agent
    from agent.registry import model_config
    from openai import OpenAI
    agent = load_agent(request.form.get('agent_id'), user_id())
    config = agent['config']
    if not config.get('audio_upload_enabled') or not config.get('asr_model_id'):
        raise StoreError('请先为 Agent 配置语音识别模型', 400)
    model = model_config(config['asr_model_id'], user_id())
    if model['type'] != 'ASR':
        raise StoreError('所选模型不是语音识别模型', 400)
    upload = request.files.get('file')
    if not upload:
        raise StoreError('请选择音频文件', 400)
    content = upload.read(25 * 1024 * 1024 + 1)
    if not content or len(content) > 25 * 1024 * 1024:
        raise StoreError('音频大小须为 1 B 至 25 MB', 413)
    params = model['parameters']
    client = OpenAI(api_key=params.get('api_key') or 'not-required', base_url=params['base_url'], timeout=120)
    try:
        result = client.audio.transcriptions.create(model=params.get('model_name') or model['name'],
            file=(secure_filename(upload.filename or 'voice.wav'), content, upload.mimetype),
            language=(request.form.get('locale') or 'zh').split('-')[0])
    except Exception as exc:
        raise StoreError(f'语音识别失败（{type(exc).__name__}）', 502) from exc
    return jsonify(success=True, data={'text': result.text, 'duration': getattr(result, 'duration', None)})
