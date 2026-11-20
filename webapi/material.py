"""资料采集与治理工作流路由：entries / tasks / documents / uploads / releases / showdoc 辅助。"""
import io
import json
import os
import re
import shutil
import uuid
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from zipfile import ZipFile

from dotenv import load_dotenv
from flask import Blueprint, g, jsonify, request, send_file
from requests import RequestException, Timeout

from registry import ENTRIES, create_crawler, get_entry
from crawlers.base import DocumentStub
from integrations.showdoc import ShowDocAuthenticator, ShowDocProjectManager
from integrations.contextdb import ContextDBError
from governance.store import Store, StoreError, data_dir
from governance.database import connection
from governance.worker import create_zip_file, publish
from webapi.auth import client_for_user, user_id

# 单例在导入期创建，需先完成 .env 装配（幂等，不覆盖已有环境变量）
load_dotenv()

material_bp = Blueprint('material', __name__)

showdoc_auth = ShowDocAuthenticator(qwen_api_key=os.getenv('QWEN_API_KEY', ''))
showdoc_project_manager = ShowDocProjectManager()
LISTING_SAVE_DIR = str(data_dir() / '_listing')
CRAWLER_PARAM_KEYS = ('item_id', 'keyword', 'default_page_id', 'user_token', 'url',
                      'crawl_mode', 'max_pages', 'max_depth')


class ApiError(StoreError):
    def __init__(self, message, status=400):
        super().__init__(message, status)


def get_store():
    # 惰性解析 app 全局：测试会在无请求上下文时直接调用（依赖 testing/extensions 分支）
    from app import app
    if app.testing and app.extensions.get('governance_store') is not None:
        return app.extensions['governance_store']
    if 'governance_store' not in g:
        store = Store(client=client_for_user(), owner_id=user_id())
        store.initialize()
        g.governance_store = store
    return g.governance_store


def json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ApiError('请求必须是 JSON 对象', 400)
    return body


def applicability(value):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ApiError('scope 必须是对象', 400)
    output = {}
    for key in ('product', 'version', 'role'):
        item = value.get(key, '')
        if not isinstance(item, str) or len(item) > 200:
            raise ApiError('适用范围字段必须是 200 字以内的文本', 400)
        if item.strip():
            output[key] = item.strip()
    return output


def selected_space(store, value, knowledge_base_id=None):
    from governance.spaces import ensure_base_space, require_writable_space
    if knowledge_base_id is not None:
        if not isinstance(knowledge_base_id, str) or not knowledge_base_id.strip():
            raise ApiError('请选择有效的知识库', 400)
        space = ensure_base_space(store, knowledge_base_id.strip())
        if value is not None and value != space['scope']:
            raise ApiError('知识库与资料任务范围不一致', 409)
        return require_writable_space(store, space['scope'])['scope']
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise ApiError('请选择有效的业务知识库', 400)
    return require_writable_space(store, value.strip())['scope']


def public_document(document):
    return {key: value for key, value in document.items() if key != 'artifact_dir'}


def task_payload(task, include_logs=True, *, submission_lookup=None):
    summary = task.get('summary') or {}
    store = get_store()
    documents = store.list_documents(task['task_id'])
    finished = datetime.fromisoformat(task.get('end_time') or datetime.now(timezone.utc).isoformat())
    started = datetime.fromisoformat(task['start_time'])
    executing = datetime.fromisoformat(task['attempt_started_at']) if task.get('attempt_started_at') else None
    payload = {key: task.get(key) for key in (
        'task_id', 'entry', 'status', 'phase', 'progress', 'total_pages', 'completed_pages',
        'failed_pages', 'skipped_pages', 'current_item', 'message', 'start_time', 'end_time', 'retry_of', 'scope', 'kind')}
    if submission_lookup is None:
        submitted = store._find('release', job_id=task['task_id'])
        release_metadata = submitted['metadata'] if submitted else None
        sync_task = None
        if release_metadata:
            with connection() as conn:
                sync_task = conn.execute('''SELECT payload,metadata FROM runtime_records WHERE owner_id=%s AND kind='job'
                    AND payload->>'kind'='ctxdb_sync' AND payload->'params'->>'release_id'=%s
                    ORDER BY created_at DESC, id LIMIT 1''',
                    (store.owner_id or '', release_metadata['release_id'])).fetchone()
    else:
        release_metadata, sync_task = submission_lookup
    submission_task = None
    if sync_task:
        submission_task = {key: sync_task['metadata'].get(key, sync_task['payload'].get(key))
            for key in ('task_id', 'entry', 'kind', 'scope', 'status', 'phase', 'progress',
                'message', 'total_pages', 'completed_pages', 'failed_pages', 'skipped_pages',
                'start_time', 'end_time')}
        submission_task.update(entry_name='资料提交', source_name='知识库资料提交',
            release_id=release_metadata['release_id'], source_task_id=task['task_id'])
    release_id = task['params'].get('release_id') if task['kind'] == 'ctxdb_sync' else None
    source_release = store._find('release', release_id=release_id) if release_id else None
    source_task_id = (source_release['metadata'].get('job_id') if source_release and
                      source_release['metadata'].get('scope') == task['scope'] else None)
    source_name = (task.get('import_directory') or {}).get('root_name')
    file_names = task['params'].get('file_names') or []
    if task['kind'] == 'ctxdb_sync':
        source_name = '知识库资料提交'
    elif not source_name and file_names:
        source_name = str(file_names[0]) + (f' 等 {len(file_names)} 份' if len(file_names) > 1 else '')
    from governance.import_directories import imported_locations
    if task['kind'] == 'ctxdb_sync':
        kb_ids = [task['params'].get('knowledge_base_id')]
    else:
        space_record = store._find('knowledge_space', scope=task['scope'])
        if space_record:
            kb_ids = [store._body(space_record['id']).get('knowledge_base_id')]
        else:
            with connection() as conn:
                kb_ids = [row['knowledge_base_id'] for row in conn.execute('''SELECT DISTINCT knowledge_base_id
                    FROM knowledge_sync WHERE owner_id=%s AND scope=%s''',
                    (store.owner_id or '', task['scope'])).fetchall()]
    terminal = ('completed', 'partial', 'failed', 'cancelled')
    payload['import_directories'] = [location for kb_id in kb_ids if kb_id
        for location in imported_locations(store, kb_id,
            task.get('source_key') if task['kind'] != 'ctxdb_sync' else None)]
    payload['directory_sync_complete'] = (task['status'] in terminal if task['kind'] == 'ctxdb_sync' else
        bool((sync_task and sync_task['metadata'].get('status') in terminal) or
             task['status'] in ('partial', 'failed', 'cancelled') or task['phase'] == 'submission_failed'))
    payload.update(
        entry_name=ENTRIES.get(task['entry'], type('E', (), {'display_name': task['entry']})()).display_name,
        successful_pages=max(0, task['completed_pages'] - task['failed_pages']),
        elapsed_seconds=max(0, int((finished - started).total_seconds())),
        queued_seconds=max(0, int(((executing or finished) - started).total_seconds())),
        processing_seconds=max(0, int((finished - executing).total_seconds())) if executing else 0,
        selected_count=len(task['selected_ids'] or task['selected_titles']),
        download_available=bool(task.get('zip_file') and Path(task['zip_file']).exists()),
        publish_available=bool(task['status'] == 'completed' and documents),
        submit_available=bool(task['kind'] != 'ctxdb_sync' and task['status'] == 'completed' and documents and not sync_task),
        submission_id=release_metadata['release_id'] if release_metadata else None,
        sync_task_id=submission_task['task_id'] if submission_task else None,
        submission_task=submission_task,
        release_id=release_id,
        source_task_id=source_task_id,
        source_name=source_name,
        metrics={
            'documents': summary.get('total_documents', len(documents)),
            'exported_documents': summary.get('total_documents', len(documents)),
            'captured_documents': task.get('total_pages', 0),
            'empty_documents': summary.get('empty_documents', 0),
            'categories': summary.get('category_count', 0),
            'chunks': summary.get('chunk_count', 0),
            'quality_score': summary.get('quality_score'),
            'duplicate_documents': summary.get('duplicate_count', 0),
            'errors': summary.get('error_count', 0),
            'warnings': summary.get('warning_count', 0),
            'video_references': summary.get('video_reference_documents', 0),
            'discovery_strategy': summary.get('discovery_strategy', ''),
            'coverage_score': summary.get('coverage_score'),
        })
    if include_logs:
        payload['logs'] = task.get('logs', [])
        payload['failure_details'] = []
        payload['failure_details_truncated'] = False
        report = (Path(task['output_dir']) / 'failed_documents.jsonl').resolve()
        if task.get('failed_pages'):
            if report.is_relative_to(data_dir()) and report.is_file():
                try:
                    with report.open(encoding='utf-8') as source:
                        for line in source:
                            if not line.strip():
                                continue
                            if len(payload['failure_details']) == 20:
                                payload['failure_details_truncated'] = True
                                break
                            record = json.loads(line)
                            payload['failure_details'].append({key: str(record.get(key, ''))[:600]
                                for key in ('id', 'title', 'error')})
                except (OSError, ValueError, TypeError):
                    payload['failure_details_error'] = '失败报告无法完整读取，请查看任务日志或审计包'
            else:
                payload['failure_details_error'] = '失败报告不可用，请查看任务日志或审计包'
    return payload


def stubs_to_pages(stubs):
    """把 BaseCrawler 的 DocumentStub 转换为前端契约的页面结构"""
    return [
        {'page_id': stub.id, 'page_title': stub.title, 'category': stub.category}
        for stub in stubs
    ]


def get_entry_or_404(key):
    try:
        return get_entry(key)
    except KeyError as error:
        raise ApiError(str(error), 404) from error


def entry_crawler_params(key, payload):
    """从请求中提取爬取参数；showdoc 登录模式下注入会话登录令牌。"""
    params = {
        name: payload.get(name)
        for name in CRAWLER_PARAM_KEYS
        if payload.get(name) not in (None, '')
    }
    if key == 'web' and not params.get('url'):
        raise ApiError('请输入要抓取的网页 URL')
    if key == 'web':
        try:
            get_entry(key).crawler_class.validate_url(params['url'])
        except ValueError as error:
            raise ApiError(str(error)) from error
        crawl_mode = str(params.get('crawl_mode', 'page')).lower()
        if crawl_mode not in {'page', 'site'}:
            raise ApiError('crawl_mode 必须是 page 或 site')
        for name, default, minimum in (
            ('max_pages', 0, 0),
            ('max_depth', 0, 0),
        ):
            try:
                value = int(params.get(name, default))
            except (TypeError, ValueError) as error:
                raise ApiError(f'{name} 必须是整数') from error
            if value < minimum:
                raise ApiError(f'{name} 必须大于等于 {minimum}')
            params[name] = value
        params['crawl_mode'] = crawl_mode
    wants_session_auth = str(payload.get('auth', '')).lower() in ('1', 'true', 'yes')
    if key == 'showdoc' and wants_session_auth and 'user_token' not in params:
        if g.user['role'] != 'admin':
            raise ApiError('服务器 ShowDoc 登录凭据仅限平台管理员使用；请提供自己的 user_token', 403)
        token = showdoc_auth.auto_login_if_needed()
        if not token:
            raise ApiError('未登录或登录失败', 401)
        params['user_token'] = token
    return params


@material_bp.route('/api/entries')
def api_entries():
    """列出注册表中的全部爬取平台，供前端渲染平台选择器"""
    return jsonify({
        'success': True,
        'entries': [
            {
                'key': entry.key,
                'display_name': entry.display_name,
                'entry_url': entry.entry_url,
                'requires_auth': entry.requires_auth,
                'description': entry.description,
            }
            for entry in ENTRIES.values()
        ],
    })


@material_bp.route('/entries/web/inspect')
def inspect_web_entry():
    """只校验网址并返回采集策略，不发起目标站网络请求。"""
    try:
        params = entry_crawler_params('web', request.args)
        crawler = create_crawler('web', save_dir=LISTING_SAVE_DIR, **params)
        return jsonify({'success': True, **crawler.strategy_info()})
    except ApiError:
        raise
    except Exception as error:
        return jsonify({
            'success': False,
            'message': f'识别采集策略失败: {str(error)}',
        }), 500


@material_bp.route('/entries/<key>/documents')
def entry_documents(key):
    """获取指定平台的文档列表（免登录平台直接返回；cyb 自动验证码登录）"""
    try:
        entry = get_entry_or_404(key)
        params = entry_crawler_params(key, request.args)
        if entry.key == 'showdoc' and not params.get('item_id'):
            raise ApiError('缺少item_id参数')
        kb_id = request.args.get('knowledge_base_id')
        store = None
        if kb_id is not None:
            if not kb_id.strip() or len(kb_id) > 200:
                raise ApiError('请选择有效的知识库')
            kb_id = kb_id.strip()
            store = get_store()
            store.client.get_knowledge_base(kb_id)

        crawler = create_crawler(entry.key, save_dir=LISTING_SAVE_DIR, **params)
        crawler.authenticate()
        stubs = crawler.list_documents()
        pages = [{**page, 'directory_path': crawler.directory_metadata(stub.category, path=stub.directory_path)['path']}
                 for page, stub in zip(stubs_to_pages(stubs), stubs)]
        from governance.store import source_scope
        directory = {'root_name': crawler.directory_root_name, 'source_key': source_scope(entry.key, params),
                     'preview_complete': not (entry.key == 'web' and params.get('crawl_mode') == 'site')}
        if store:
            mapped = store._find('import_directory', knowledge_base_id=kb_id, source_key=directory['source_key'])
            if mapped:
                node_id = store._body(mapped['id']).get('node_id')
                if not node_id:
                    raise ApiError('已有来源目录尚未确认，请核对目录后重试', 409)
                node = store.client.list_nodes(kb_id, parent_node_id=node_id, page_size=1).get('parent_node')
                if not node or node.get('node_type') != 'folder' or node.get('node_id') != node_id:
                    raise ApiError('已有来源目录已改变，请核对目录后重试', 409)
                directory['root_name'] = node['display_name']
        return jsonify({'success': True, 'pages': pages, 'directory': directory})
    except (StoreError, ContextDBError):
        raise
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取页面列表失败: {str(e)}'
        }), 500


@material_bp.route('/entries/<key>/preview', methods=['GET', 'POST'])
def entry_preview(key):
    entry = get_entry_or_404(key)
    payload = json_body() if request.method == 'POST' else request.args
    doc_id = payload.get('doc_id')
    if not isinstance(doc_id, str) or not doc_id.strip() or doc_id.strip() == '0':
        raise ApiError('缺少有效 doc_id', 400)
    doc_id = doc_id.strip()
    params = entry_crawler_params(key, payload)
    if entry.key == 'showdoc' and not params.get('item_id'):
        raise ApiError('缺少 item_id 参数', 400)
    try:
        crawler = create_crawler(entry.key, save_dir=LISTING_SAVE_DIR, **params)
        crawler.authenticate()
        if entry.key == 'tiantong':
            stub = DocumentStub(doc_id, f'文档 {doc_id}', '未分类')
        else:
            stub = next((item for item in crawler.list_documents() if str(item.id) == doc_id), None)
        if stub is None:
            raise ApiError('当前来源的目录中没有这篇文档，请重新读取目录', 404)
        doc = crawler.fetch_document(stub)
        if doc.metadata.get('fetch_error'):
            raise ApiError('来源未能返回正文，请核对访问权限后重试', 502)
        record = crawler._prepare_record(doc)
        content = record['content']
    except (StoreError, ContextDBError):
        raise
    except Timeout as error:
        raise ApiError('读取来源正文超时，请重试', 504) from error
    except (RequestException, RuntimeError, ValueError) as error:
        raise ApiError('暂时无法读取来源正文，请核对来源设置后重试', 502) from error
    if not content.strip():
        raise ApiError('这篇文档的源正文为空', 422)
    source_base_url = ''
    if isinstance(record['base_url'], str):
        try:
            base = urlsplit(record['base_url'])
            if base.scheme in ('http', 'https') and base.hostname and not (base.username or base.password):
                source_base_url = base._replace(query='', fragment='').geturl()
        except ValueError:
            pass
    response = jsonify(success=True, title=doc.title, content=content,
                       source_format=doc.source_format, page_id=doc_id,
                       source_base_url=source_base_url,
                       source_kind=doc.metadata.get('source_kind'),
                       media_content_captured=doc.metadata.get('media_content_captured'))
    response.headers['Cache-Control'] = 'no-store'
    return response


@material_bp.route('/entries/<key>/start', methods=['POST'])
def entry_start(key):
    entry = get_entry_or_404(key)
    if key == 'file':
        raise ApiError('文件请通过上传入口提交', 400)
    body = json_body()
    directory = None
    if 'import_root_name' in body:
        from common.source_directories import validate_import_root_name
        try:
            directory = {'root_name': validate_import_root_name(body['import_root_name'])}
        except ValueError as error:
            raise ApiError(str(error)) from error
    params = entry_crawler_params(key, body)
    if key == 'showdoc' and not params.get('item_id'):
        raise ApiError('缺少 item_id 参数', 400)
    for field in ('selected_ids', 'selected_titles'):
        values = body.get(field, [])
        if not isinstance(values, list) or not all(isinstance(v, (str, int)) for v in values):
            raise ApiError(f'{field} 必须是文档标识列表', 400)
    store = get_store()
    scope = selected_space(store, body.get('space_scope'), body.get('knowledge_base_id'))
    from governance.knowledge_bases import base_write_lock
    from governance.spaces import require_writable_space
    kb_id = require_writable_space(store, scope)['knowledge_base_id'] if scope else None
    with base_write_lock(kb_id) if kb_id else nullcontext():
        if scope:
            require_writable_space(store, scope)
        job = store.create_job(entry.key, params, body.get('selected_ids'), body.get('selected_titles'), scope=scope,
                               applicability=applicability(body.get('scope')), import_directory=directory)
    return jsonify(success=True, task_id=job['task_id'], message='任务已入队')


@material_bp.route('/task_status/<task_id>')
def task_status(task_id):
    return jsonify(task_payload(get_store().get_job(task_id)))


@material_bp.route('/api/tasks')
def task_list():
    scope = request.args.get('space_scope')
    status_group = request.args.get('status_group')
    if status_group is not None and status_group not in ('all', 'active', 'action', 'done'):
        raise ApiError('资料任务状态筛选无效', 400)
    store = get_store()
    if scope is not None:
        from governance.spaces import get_space
        scope = get_space(store, scope)['scope']
    try:
        page = int(request.args.get('page', 1))
        size = int(request.args.get('page_size', 50))
    except ValueError:
        raise ApiError('分页参数必须是整数', 400)
    if page < 1 or not 1 <= size <= 100:
        raise ApiError('页码须大于 0，每页条数须为 1 至 100', 400)
    if status_group is None:
        total = store.count_jobs(scope)
        jobs = store.list_jobs(scope, page=page, page_size=size) if (page - 1) * size < total else []
        tasks = [task_payload(job, False) for job in jobs]
    else:
        total, rows = store.list_material_jobs(scope, status_group, page=page, page_size=size)
        tasks = [task_payload(job, False, submission_lookup=(release, sync)) for job, release, sync in rows]
    return jsonify(success=True, tasks=tasks, total=total, page=page, page_size=size)


@material_bp.route('/tasks/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    get_store().cancel(task_id)
    return jsonify(success=True, message='取消请求已保存')


@material_bp.route('/tasks/<task_id>/retry', methods=['POST'])
def retry_task(task_id):
    store = get_store()
    job = store.get_job(task_id)
    if job['kind'] == 'ctxdb_sync':
        raise ApiError('请在知识库的治理进度中选择失败目标重试', 409)
    if job['status'] not in {'failed', 'cancelled', 'partial'}:
        raise ApiError('仅失败、取消或部分完成任务可以重试')
    from governance.spaces import get_space, require_writable_space
    from governance.knowledge_bases import base_write_lock
    space = get_space(store, job['scope'])
    kb_id = space['knowledge_base_id']
    with base_write_lock(kb_id) if kb_id else nullcontext():
        if kb_id:
            require_writable_space(store, job['scope'])
        retried = store.create_job(job['entry'], job['params'], job['selected_ids'], job['selected_titles'],
                                  retry_of=task_id, kind=job['kind'], scope=job['scope'],
                                  version_id=job.get('version_id'), document_id=job.get('document_id'),
                                  revision_reason=job.get('revision_reason', ''), applicability=job.get('applicability'))
    return jsonify(success=True, task_id=retried['task_id'], message='重试任务已入队，将复用已保存产物')


@material_bp.route('/download/<task_id>')
def download_result(task_id):
    job = get_store().get_job(task_id)
    path = job.get('zip_file')
    if not path or not Path(path).is_file():
        raise ApiError('审计包尚未生成', 404)
    output = Path(job['output_dir']) if job.get('output_dir') else None
    if output and output.is_dir():
        with ZipFile(path) as archive:
            markdown_included = any(name.startswith('markdown/') and name.endswith('.md')
                                    for name in archive.namelist())
        if not markdown_included:
            create_zip_file(output, path, include_markdown=True)
    return send_file(path, as_attachment=True, download_name=f'audit-{task_id}.zip')


@contextmanager
def upload_directory():
    directory = data_dir() / 'uploads' / str(uuid.uuid4())
    directory.mkdir(parents=True)
    try:
        yield directory
    except BaseException:
        shutil.rmtree(directory)
        raise


@material_bp.route('/api/uploads', methods=['POST'])
def upload_files():
    files = request.files.getlist('files')
    if not files or len(files) > 50:
        raise ApiError('请上传 1 至 50 个文件', 400)
    try:
        scope = applicability(json.loads(request.form.get('scope', '{}')))
    except (ValueError, TypeError):
        raise ApiError('scope 必须是有效 JSON 对象', 400)
    store = get_store()
    space_scope = selected_space(store, request.form.get('space_scope'), request.form.get('knowledge_base_id'))
    for file in files:
        if not file.filename:
            raise ApiError('上传文件必须有文件名', 400)
    with upload_directory() as directory:
        paths, names = [], []
        for index, file in enumerate(files):
            original = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', Path(file.filename.replace('\\', '/')).name).strip(' .')
            suffix = Path(original).suffix.lower().encode('utf-8')[:40].decode('utf-8', errors='ignore')
            stem = Path(original).stem
            stem = stem.encode('utf-8')[:180].decode('utf-8', errors='ignore') or 'document'
            name = stem + suffix
            path = directory / f'{index + 1:03d}-{name}'
            file.save(path)
            if not path.stat().st_size:
                raise ApiError('不能上传空文件', 400)
            paths.append(str(path))
            names.append(name)
        from governance.knowledge_bases import base_write_lock
        from governance.spaces import require_writable_space
        kb_id = require_writable_space(store, space_scope)['knowledge_base_id'] if space_scope else None
        with base_write_lock(kb_id) if kb_id else nullcontext():
            if space_scope:
                require_writable_space(store, space_scope)
            job = store.create_job('file', {'file_paths': paths, 'file_names': names}, applicability=scope, scope=space_scope)
    return jsonify(success=True, task_id=job['task_id'], message='文件已保存，任务已入队')


@material_bp.route('/api/documents')
def list_documents():
    return jsonify(success=True, documents=get_store().list_documents(request.args.get('task_id')))


@material_bp.route('/api/documents/<version_id>')
def document_detail(version_id):
    document = get_store().get_document(version_id)
    return jsonify(success=True, document=public_document(document))


@material_bp.route('/api/documents/<version_id>/source')
def document_source(version_id):
    document = get_store().get_document(version_id)
    source = document['source']
    root = Path(document['artifact_dir']).resolve()
    if source.get('source_path'):
        path = (root / source['source_path']).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ApiError('原始文件不可用', 404)
        return send_file(path, as_attachment=True, download_name=path.name)
    suffix = '.html' if source.get('source_format') == 'html' else '.md'
    return send_file(io.BytesIO(source.get('content', '').encode('utf-8')), as_attachment=True,
                     download_name=f"{version_id[:12]}{suffix}", mimetype='text/plain')


@material_bp.route('/api/documents/<version_id>/revisions', methods=['POST'])
def revise_document(version_id):
    store = get_store()
    document = store.get_document(version_id)
    if not document['is_current']:
        raise ApiError('只能修订当前文档版本')
    body = json_body()
    content, reason = body.get('content'), body.get('reason')
    if not isinstance(content, str) or not content.strip() or len(content.encode()) > 5 * 1024 * 1024:
        raise ApiError('修订正文不能为空且不能超过 5 MB', 400)
    if not isinstance(reason, str) or not reason.strip():
        raise ApiError('请填写修订理由', 400)
    with upload_directory() as directory:
        path = directory / 'revision.md'
        path.write_text(content, encoding='utf-8')
        from governance.spaces import get_space, require_writable_space
        from governance.knowledge_bases import base_write_lock
        kb_id = get_space(store, document['scope'])['knowledge_base_id']
        with base_write_lock(kb_id) if kb_id else nullcontext():
            if kb_id:
                require_writable_space(store, document['scope'])
            job = store.create_job('file', {'file_paths': [str(path)]}, scope=document['scope'],
                                   version_id=version_id, document_id=document['id'], revision_reason=reason.strip(),
                                   applicability=document.get('metadata', {}).get('scope'))
    return jsonify(success=True, task_id=job['task_id'], message='修订已保存为新版本输入，等待解析')


@material_bp.route('/tasks/<task_id>/publish', methods=['POST'])
@material_bp.route('/tasks/<task_id>/submit', methods=['POST'])
def publish_task(task_id):
    store = get_store()
    release_id = publish(store, task_id)
    store.update_job(task_id, phase='submitted',
        message='资料已加入 ContextDB 提交队列；评审、入库与 Wiki 编译状态请查看治理进度')
    return jsonify(success=True, release_id=release_id, message='资料已提交治理；官方评审、入库与构建状态请查看知识库治理进度')


@material_bp.route('/api/releases')
def list_releases():
    store = get_store()
    scope = request.args.get('space_scope')
    if scope is not None:
        from governance.spaces import get_space
        scope = get_space(store, scope)['scope']
    return jsonify(success=True, releases=store.list_releases(scope))


@material_bp.route('/api/releases/<release_id>/activate', methods=['POST'])
def activate_release(release_id):
    store=get_store()
    release=store.get_release(release_id)
    store.activate_release(release_id)
    from governance.contextdb_sync import enqueue_sync
    job=enqueue_sync(store,release_id,release['scope'])
    return jsonify(success=True,task_id=job['task_id'],message='采集批次已激活并提交双库同步；知识生效以官方评审结果为准')


@material_bp.route('/api/releases/<release_id>/download')
def download_release(release_id):
    release = get_store().get_release(release_id)
    if not Path(release['archive_path']).is_file():
        raise ApiError('提交快照文件缺失', 404)
    return send_file(release['archive_path'], as_attachment=True, download_name=f"dataset-{release_id}.zip")


# ==================== ShowDoc 登录辅助路由 ====================

@material_bp.route('/showdoc/login', methods=['POST'])
def showdoc_login():
    """执行ShowDoc登录"""
    try:
        token = showdoc_auth.login()

        if token:
            return jsonify({
                'success': True,
                'token': token,
                'message': '登录成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '登录失败,请检查凭证或网络连接'
            }), 401

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'登录异常: {str(e)}'
        }), 500


@material_bp.route('/showdoc/projects', methods=['GET'])
def showdoc_get_projects():
    """获取ShowDoc项目列表"""
    try:
        # 自动登录（如果token无效）
        token = showdoc_auth.auto_login_if_needed()

        if not token:
            return jsonify({
                'success': False,
                'message': '未登录或登录失败'
            }), 401

        group_id = request.args.get('group_id', 0)
        projects = showdoc_project_manager.get_cached_projects(token, group_id)
        if not projects:
            projects = showdoc_project_manager.get_project_list(token, group_id)

        return jsonify({
            'success': True,
            'projects': projects,
            'count': len(projects)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取项目列表失败: {str(e)}'
        }), 500


@material_bp.route('/showdoc/project/<item_id>', methods=['GET'])
def showdoc_get_project_detail(item_id):
    """获取ShowDoc项目详情"""
    try:
        token = showdoc_auth.auto_login_if_needed()

        if not token:
            return jsonify({
                'success': False,
                'message': '未登录或登录失败'
            }), 401

        keyword = request.args.get('keyword', '')
        default_page_id = request.args.get('default_page_id', '')

        project_info = showdoc_project_manager.get_project_info(
            item_id, token, keyword, default_page_id
        )

        if project_info:
            return jsonify({
                'success': True,
                'project': project_info
            })
        else:
            return jsonify({
                'success': False,
                'message': '获取项目详情失败'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取项目详情异常: {str(e)}'
        }), 500
