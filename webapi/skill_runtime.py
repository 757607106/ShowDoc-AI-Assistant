"""Static Skill content management and read-only former installation records."""
import base64
import hashlib
import io
import json
import mimetypes
from pathlib import Path
import uuid
import zipfile

from flask import Blueprint, Response, g, jsonify, request

from agent import registry
from agent.sandbox import CONFIG_ID
from agent.skill_bundle import MAX_DOWNLOAD, fetch_bundle, parse_bundle
from governance.database import connection
from governance.store import StoreError, data_dir
from webapi.legacy_runtime import unavailable

skill_runtime_bp = Blueprint('skill_runtime', __name__)
INSTRUCTION_BACKENDS = ('state-backend', CONFIG_ID)


def _body():
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise StoreError('请求必须为 JSON 对象', 400)
    return value


def _admin():
    if g.user['role'] != 'admin':
        raise StoreError('修改 Skill 内容需要管理员权限', 403)


def _read_upload():
    upload = request.files.get('file')
    if upload:
        return parse_bundle(upload.read(MAX_DOWNLOAD + 1))
    body = _body()
    if body.get('source'):
        return fetch_bundle(body['source'])
    if isinstance(body.get('files'), dict):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
            for path, text in body['files'].items():
                if not isinstance(text, str):
                    raise StoreError('files 内容必须为字符串；二进制文件请上传 ZIP', 400)
                bundle.writestr(path, text)
        return parse_bundle(archive.getvalue())
    raise StoreError('请上传包含 SKILL.md 的 ZIP 或提供 source', 400)


def _upload():
    try:
        return _read_upload()
    except (UnicodeError, zipfile.BadZipFile, RuntimeError) as exc:
        raise StoreError('Skill 归档编码无效、已加密或已损坏', 400) from exc


def _catalog_view(value):
    return {**{key: value[key] for key in ('id', 'name', 'description', 'version', 'bundle_sha256', 'created_at', 'updated_at') if key in value},
            'enabled': value.get('enabled', True), 'execution_mode': 'native_middleware', 'dependency_status': 'not_managed',
            'installations': []}


def _bundle_files(value):
    if 'files' in value:
        return {path: content.encode() for path, content in value['files'].items()}
    path = Path(value['_bundle_path']).resolve()
    directory = data_dir() / 'skill-bundles' / hashlib.sha256(g.user['id'].encode()).hexdigest()
    if not path.is_relative_to(directory.resolve()):
        raise StoreError('Skill 归档路径无效', 409)
    try:
        with zipfile.ZipFile(path) as archive:
            return {entry.filename: archive.read(entry) for entry in archive.infolist()}
    except (OSError, zipfile.BadZipFile) as exc:
        raise StoreError('Skill 归档已缺失或损坏，请重新上传', 409) from exc


def _install(config_id, install_id):
    row = registry.record('skill_install', install_id, g.user['id'])
    if row['sandbox_config_id'] != config_id:
        raise StoreError('Skill 安装记录不存在', 404)
    return row


def _install_view(row):
    return {**{key: row[key] for key in ('id', 'catalog_id', 'sandbox_config_id', 'name', 'description', 'status', 'error', 'version', 'created_at', 'updated_at', 'install_session_id', 'install_message_id') if key in row},
            'enabled': False, 'read_only': True, 'execution_available': False}


@skill_runtime_bp.route('/api/v1/skills')
def available_skills():
    config_id = request.args.get('sandbox_config_id') or 'state-backend'
    if config_id not in INSTRUCTION_BACKENDS:
        registry.record('sandbox', config_id, g.user['id'])
        return jsonify(success=True, data=[], skills_available=False, scripts_available=False)
    return jsonify(success=True, data=[_catalog_view(value) for value in registry.records('skill', g.user['id']) if value.get('enabled', True)],
                   skills_available=True, execution_mode='native_middleware', dependency_status='not_managed')


@skill_runtime_bp.route('/api/v1/skills/catalog', methods=['GET', 'POST'])
def catalog():
    owner = g.user['id']
    if request.method == 'POST':
        _admin()
        bundle = _upload()
        with connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(current_schema() || ':skills:' || %s, 0))", (owner,))
            old = next((value for value in registry.records('skill', owner) if value['name'] == bundle['name']), {})
            if old and any(row.get('catalog_id') == old['id'] for row in registry.records('skill_install', owner)):
                raise StoreError('旧安装记录引用此目录，请用新名称上传以保留历史版本', 409)
            directory = data_dir() / 'skill-bundles' / hashlib.sha256(owner.encode()).hexdigest()
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / (bundle['bundle_sha256'] + '.zip')
            if not path.exists():
                temporary = directory / (uuid.uuid4().hex + '.tmp')
                temporary.write_bytes(bundle['archive'])
                temporary.replace(path)
            value = {**old, 'id': old.get('id', str(uuid.uuid4())), 'name': bundle['name'],
                     'description': bundle['description'], 'version': bundle['version'],
                     'bundle_sha256': bundle['bundle_sha256'], '_bundle_path': str(path),
                     'enabled': old.get('enabled', True)}
            value.pop('files', None)
            value = registry.save_record('skill', value, owner)
        return jsonify(success=True, data=_catalog_view(value)), 201
    return jsonify(success=True, data=[_catalog_view(value) for value in registry.records('skill', owner)])


@skill_runtime_bp.route('/api/v1/skills/catalog/<catalog_id>', methods=['GET', 'DELETE'])
def catalog_item(catalog_id):
    owner = g.user['id']
    value = registry.record('skill', catalog_id, owner)
    if request.method == 'DELETE':
        _admin()
        if any(row.get('catalog_id') == catalog_id for row in registry.records('skill_install', owner)):
            raise StoreError('旧安装记录引用此目录，保留归档内容；自动卸载已停用', 409)
        registry.delete_record('skill', catalog_id, owner)
        return jsonify(success=True)
    return jsonify(success=True, data=_catalog_view(value))


@skill_runtime_bp.post('/api/v1/skills/catalog/<catalog_id>/install')
@skill_runtime_bp.post('/api/v1/sandbox-configs/<config_id>/skills/<install_id>/reinstall')
@skill_runtime_bp.post('/api/v1/sandbox-configs/<config_id>/skills/<install_id>/stop')
@skill_runtime_bp.route('/api/v1/me/env-vars/<scope>', methods=['PUT', 'DELETE'])
@skill_runtime_bp.get('/api/v1/me/env-vars')
def retired_installation(catalog_id=None, config_id=None, install_id=None, scope=None):
    unavailable()


@skill_runtime_bp.route('/api/v1/sandbox-configs/<config_id>/skills', methods=['GET', 'POST'])
def config_skills(config_id):
    if request.method == 'POST':
        unavailable()
    return jsonify(success=True, read_only=True, data=[_install_view(row) for row in registry.records('skill_install', g.user['id'])
        if row['sandbox_config_id'] == config_id])


@skill_runtime_bp.route('/api/v1/sandbox-configs/<config_id>/skills/<install_id>', methods=['GET', 'PATCH', 'DELETE'])
def config_skill(config_id, install_id):
    if request.method != 'GET':
        unavailable()
    return jsonify(success=True, data=_install_view(_install(config_id, install_id)))


@skill_runtime_bp.route('/api/v1/sandbox-configs/<config_id>/skills/<install_id>/guidance', methods=['GET', 'POST'])
def guidance(config_id, install_id):
    if request.method == 'POST':
        unavailable()
    return jsonify(success=True, data={'accepting': False, 'read_only': True,
        'messages': _install(config_id, install_id).get('guidance', [])})


@skill_runtime_bp.get('/api/v1/sandbox-configs/<config_id>/skills/<install_id>/install-events')
@skill_runtime_bp.get('/api/v1/sandbox-configs/<config_id>/skills/<install_id>/transcript')
def installation_history(config_id, install_id):
    row = _install(config_id, install_id)
    owner, run_id = g.user['id'], row.get('install_message_id', '')
    with connection() as conn:
        if request.path.endswith('/transcript'):
            values = conn.execute('SELECT event_json FROM agent_run_events WHERE owner_id=%s AND run_id=%s ORDER BY cursor', (owner, run_id)).fetchall()
            events = [value['event_json'] for value in values]
        else:
            values = conn.execute("SELECT payload FROM runtime_records WHERE owner_id=%s AND kind='skill_progress' AND payload->>'install_id'=%s AND payload->>'message_id'=%s ORDER BY created_at,id", (owner, row['id'], run_id)).fetchall()
            events = [value['payload']['event'] for value in values]
    events.append({'stage': 'archived', 'done': True, 'read_only': True})
    return Response(''.join('data: ' + json.dumps(event, ensure_ascii=False) + '\n\n' for event in events),
                    mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})


@skill_runtime_bp.get('/api/v1/skills/catalog/<catalog_id>/files')
@skill_runtime_bp.get('/api/v1/skills/catalog/<catalog_id>/files/content')
@skill_runtime_bp.get('/api/v1/sandbox-configs/<config_id>/skills/<install_id>/files')
@skill_runtime_bp.get('/api/v1/sandbox-configs/<config_id>/skills/<install_id>/files/content')
def files(catalog_id=None, config_id=None, install_id=None):
    owner = g.user['id']
    if config_id:
        row = _install(config_id, install_id)
        value = row.get('_served') or registry.record('skill', row['catalog_id'], owner)
    else:
        value = registry.record('skill', catalog_id, owner)
    values = _bundle_files(value)
    if request.path.endswith('/content'):
        path = request.args.get('path', '')
        if path not in values:
            raise StoreError('Skill 文件不存在', 404)
        raw = values[path]
        try:
            content, encoding = raw.decode('utf-8'), 'utf-8'
        except UnicodeDecodeError:
            content, encoding = base64.b64encode(raw).decode(), 'base64'
        return jsonify(success=True, data={'path': path, 'size': len(raw), 'content': content,
            'encoding': encoding, 'media_type': mimetypes.guess_type(path)[0] or 'application/octet-stream'})
    return jsonify(success=True, data=[{'path': path, 'name': path.rsplit('/', 1)[-1], 'size': len(raw), 'is_dir': False}
        for path, raw in values.items()])
