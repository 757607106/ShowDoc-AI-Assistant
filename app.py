"""Local governance workbench; durable jobs run in governance.worker."""
import io
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, g, request, jsonify, send_file, send_from_directory, redirect
from werkzeug.exceptions import RequestEntityTooLarge

from crawlers.base import DocumentStub
from registry import ENTRIES, create_crawler, get_entry
from integrations.showdoc import ShowDocAuthenticator, ShowDocProjectManager
from integrations.contextdb import ContextDBError, ContextDBConflictError
from common.env_sanitize import sanitize_no_proxy
from governance.store import Store, StoreError, data_dir
from governance.database import connection
from governance.worker import publish
from webapi import register_blueprints
from webapi.auth import client_for_user, require_login, user_id, finish_audit

sanitize_no_proxy()
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY') or os.urandom(32)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
register_blueprints(app)
app.before_request(require_login)
app.after_request(finish_audit)
showdoc_auth = ShowDocAuthenticator(qwen_api_key=os.getenv('QWEN_API_KEY', ''))
showdoc_project_manager = ShowDocProjectManager()
LISTING_SAVE_DIR = str(data_dir() / '_listing')
CRAWLER_PARAM_KEYS = ('item_id', 'keyword', 'default_page_id', 'user_token', 'url',
                      'crawl_mode', 'max_pages', 'max_depth')


class ApiError(StoreError):
    def __init__(self, message, status=400):
        super().__init__(message, status)


@app.route('/assets/<path:filename>')
def frontend_assets(filename):
    return send_from_directory(FRONTEND_DIST / 'assets', filename)


@app.route('/favicon.svg')
def frontend_favicon():
    return send_from_directory(FRONTEND_DIST, 'favicon.svg')


@app.errorhandler(404)
def spa_fallback(error):
    """SPA fallback:前端路由路径回退到 index.html(非 /api、/entries 等已注册前缀)。"""
    public = (FRONTEND_DIST / request.path.lstrip('/')).resolve()
    if public.is_relative_to(FRONTEND_DIST.resolve()) and public.is_file():
        return send_from_directory(FRONTEND_DIST, request.path.lstrip('/'))
    if (FRONTEND_DIST / 'index.html').is_file() and not request.path.startswith(('/api', '/entries', '/tasks', '/download', '/showdoc', '/static')) and '.' not in request.path.rsplit('/',1)[-1]:
        return send_from_directory(FRONTEND_DIST, 'index.html')
    return jsonify(success=False, message='资源不存在'), 404


@app.errorhandler(StoreError)
def handle_api_error(error):
    return jsonify(success=False, message=str(error)), error.status


@app.errorhandler(ContextDBError)
def handle_contextdb_error(error):
    if isinstance(error, ContextDBConflictError):
        payload = {'success': False, 'message': str(error), 'request_id': error.request_id, 'error_code':error.error_code, 'source':'contextdb'}
        body = request.get_json(silent=True) or {}
        if body.get('knowledge_base_id') and body.get('page_id') and 'wiki/pages' in request.path:
            try:
                payload['current_version'] = client_for_user().get_wiki_page(body['knowledge_base_id'], body['page_id'])['version']
            except ContextDBError:
                pass
        return jsonify(**payload), 409
    status = error.status_code or 0
    if 400 <= status < 500:
        return jsonify(success=False, message=f'ContextDB 拒绝请求: {error}', request_id=error.request_id,error_code=error.error_code,source='contextdb'), status
    return jsonify(success=False, message=f'ContextDB 不可用: {error}',request_id=error.request_id,error_code=error.error_code,source='contextdb'), 503


@app.errorhandler(RequestEntityTooLarge)
def handle_large_upload(error):
    return jsonify(success=False, message='上传总大小不能超过 100 MB'), 413


def get_store():
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


def selected_space(store, value):
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise ApiError('请选择有效的业务知识库', 400)
    from governance.spaces import get_space
    return get_space(store, value.strip())['scope']


def public_document(document):
    return {key: value for key, value in document.items() if key != 'artifact_dir'}


def task_payload(task, include_logs=True):
    summary = task.get('summary') or {}
    store = get_store()
    documents = store.list_documents(task['task_id'])
    finished = datetime.fromisoformat(task.get('end_time') or datetime.now(timezone.utc).isoformat())
    started = datetime.fromisoformat(task['start_time'])
    executing = datetime.fromisoformat(task['attempt_started_at']) if task.get('attempt_started_at') else None
    payload = {key: task.get(key) for key in (
        'task_id', 'entry', 'status', 'phase', 'progress', 'total_pages', 'completed_pages',
        'failed_pages', 'skipped_pages', 'current_item', 'message', 'start_time', 'end_time', 'retry_of', 'scope', 'kind')}
    submitted = store._find('release', job_id=task['task_id'])
    queued = False
    if submitted:
        with connection() as conn:
            queued = conn.execute('''SELECT 1 FROM runtime_records WHERE owner_id=%s AND kind='job'
                AND payload->>'kind'='ctxdb_sync' AND payload->'params'->>'release_id'=%s LIMIT 1''',
                (store.owner_id or '', submitted['metadata']['release_id'])).fetchone() is not None
    payload.update(
        entry_name=ENTRIES.get(task['entry'], type('E', (), {'display_name': task['entry']})()).display_name,
        successful_pages=max(0, task['completed_pages'] - task['failed_pages']),
        elapsed_seconds=max(0, int((finished - started).total_seconds())),
        queued_seconds=max(0, int(((executing or finished) - started).total_seconds())),
        processing_seconds=max(0, int((finished - executing).total_seconds())) if executing else 0,
        selected_count=len(task['selected_ids'] or task['selected_titles']),
        download_available=bool(task.get('zip_file') and Path(task['zip_file']).exists()),
        publish_available=bool(task['status'] == 'completed' and documents),
        submit_available=bool(task['kind'] != 'ctxdb_sync' and task['status'] == 'completed' and documents and not queued),
        submission_id=submitted['metadata']['release_id'] if submitted else None,
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


FRONTEND_DIST = Path(__file__).resolve().parent / 'frontend' / 'dist'


@app.route('/')
def index():
    if (FRONTEND_DIST / 'index.html').is_file():
        return send_from_directory(FRONTEND_DIST, 'index.html')
    return '前端未构建:cd frontend && npm install && npm run build', 503


@app.route('/showdoc')
def showdoc():
    return redirect('/')


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
        from flask import g
        if g.user['role'] != 'admin':
            raise ApiError('服务器 ShowDoc 登录凭据仅限平台管理员使用；请提供自己的 user_token', 403)
        token = showdoc_auth.auto_login_if_needed()
        if not token:
            raise ApiError('未登录或登录失败', 401)
        params['user_token'] = token
    return params


@app.route('/api/entries')
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


@app.route('/entries/web/inspect')
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


@app.route('/entries/<key>/documents')
def entry_documents(key):
    """获取指定平台的文档列表（免登录平台直接返回；cyb 自动验证码登录）"""
    try:
        entry = get_entry_or_404(key)
        params = entry_crawler_params(key, request.args)
        if entry.key == 'showdoc' and not params.get('item_id'):
            raise ApiError('缺少item_id参数')

        crawler = create_crawler(entry.key, save_dir=LISTING_SAVE_DIR, **params)
        crawler.authenticate()
        pages = stubs_to_pages(crawler.list_documents())
        return jsonify({'success': True, 'pages': pages})
    except ApiError:
        raise
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取页面列表失败: {str(e)}'
        }), 500


@app.route('/entries/<key>/preview')
def entry_preview(key):
    entry = get_entry_or_404(key)
    doc_id = (request.args.get('doc_id') or '').strip()
    if not doc_id or doc_id == '0':
        raise ApiError('缺少有效 doc_id', 400)
    params = entry_crawler_params(key, request.args)
    if entry.key == 'showdoc' and not params.get('item_id'):
        raise ApiError('缺少 item_id 参数', 400)
    crawler = create_crawler(entry.key, save_dir=LISTING_SAVE_DIR, **params)
    crawler.authenticate()
    if entry.key == 'showdoc':
        stub = DocumentStub(doc_id, '页面预览', '根目录')
    else:
        stub = next((s for s in crawler.list_documents() if str(s.id) == doc_id), None)
        if stub is None:
            raise ApiError('文档不存在', 404)
    doc = crawler.fetch_document(stub)
    content = crawler._prepare_record(doc)['content']
    if not content.strip():
        raise ApiError('源正文为空，请采集后查看官方解析结果', 422)
    return jsonify(success=True, title=doc.title, content=content,
                   source_format=doc.source_format, page_id=doc_id,
                   source_kind=doc.metadata.get('source_kind'),
                   media_content_captured=doc.metadata.get('media_content_captured'))


@app.route('/entries/<key>/start', methods=['POST'])
def entry_start(key):
    entry = get_entry_or_404(key)
    if key == 'file':
        raise ApiError('文件请通过上传入口提交', 400)
    body = json_body()
    params = entry_crawler_params(key, body)
    if key == 'showdoc' and not params.get('item_id'):
        raise ApiError('缺少 item_id 参数', 400)
    for field in ('selected_ids', 'selected_titles'):
        values = body.get(field, [])
        if not isinstance(values, list) or not all(isinstance(v, (str, int)) for v in values):
            raise ApiError(f'{field} 必须是文档标识列表', 400)
    store = get_store()
    scope = selected_space(store, body.get('space_scope'))
    job = store.create_job(entry.key, params, body.get('selected_ids'), body.get('selected_titles'), scope=scope,
                                 applicability=applicability(body.get('scope')))
    return jsonify(success=True, task_id=job['task_id'], message='任务已入队')


@app.route('/task_status/<task_id>')
def task_status(task_id):
    return jsonify(task_payload(get_store().get_job(task_id)))


@app.route('/api/tasks')
def task_list():
    scope = request.args.get('space_scope')
    store = get_store()
    if scope is not None:
        scope = selected_space(store, scope)
    return jsonify(success=True, tasks=[task_payload(j, False) for j in store.list_jobs() if scope is None or j['scope'] == scope])


@app.route('/tasks/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    get_store().cancel(task_id)
    return jsonify(success=True, message='取消请求已保存')


@app.route('/tasks/<task_id>/retry', methods=['POST'])
def retry_task(task_id):
    store = get_store()
    job = store.get_job(task_id)
    if job['kind'] == 'ctxdb_sync':
        raise ApiError('请在知识库的治理进度中选择失败目标重试', 409)
    if job['status'] not in {'failed', 'cancelled', 'partial'}:
        raise ApiError('仅失败、取消或部分完成任务可以重试')
    retried = store.create_job(job['entry'], job['params'], job['selected_ids'], job['selected_titles'],
                              retry_of=task_id, kind=job['kind'], scope=job['scope'],
                              version_id=job.get('version_id'), document_id=job.get('document_id'),
                              revision_reason=job.get('revision_reason', ''), applicability=job.get('applicability'))
    return jsonify(success=True, task_id=retried['task_id'], message='重试任务已入队，将复用已保存产物')


@app.route('/download/<task_id>')
def download_result(task_id):
    job = get_store().get_job(task_id)
    path = job.get('zip_file')
    if not path or not Path(path).is_file():
        raise ApiError('审计包尚未生成', 404)
    return send_file(path, as_attachment=True, download_name=f'audit-{task_id}.zip')


@app.route('/api/uploads', methods=['POST'])
def upload_files():
    files = request.files.getlist('files')
    if not files or len(files) > 50:
        raise ApiError('请上传 1 至 50 个文件', 400)
    try:
        scope = applicability(json.loads(request.form.get('scope', '{}')))
    except (ValueError, TypeError):
        raise ApiError('scope 必须是有效 JSON 对象', 400)
    store = get_store()
    space_scope = selected_space(store, request.form.get('space_scope'))
    for file in files:
        if not file.filename:
            raise ApiError('上传文件必须有文件名', 400)
    directory = data_dir() / 'uploads' / str(uuid.uuid4())
    directory.mkdir(parents=True)
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
    job = store.create_job('file', {'file_paths': paths, 'file_names': names}, applicability=scope, scope=space_scope)
    return jsonify(success=True, task_id=job['task_id'], message='文件已保存，任务已入队')


@app.route('/api/documents')
def list_documents():
    return jsonify(success=True, documents=get_store().list_documents(request.args.get('task_id')))


@app.route('/api/documents/<version_id>')
def document_detail(version_id):
    document = get_store().get_document(version_id)
    return jsonify(success=True, document=public_document(document))


@app.route('/api/documents/<version_id>/source')
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


@app.route('/api/documents/<version_id>/revisions', methods=['POST'])
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
    directory = data_dir() / 'uploads' / str(uuid.uuid4())
    directory.mkdir(parents=True)
    path = directory / 'revision.md'
    path.write_text(content, encoding='utf-8')
    job = store.create_job('file', {'file_paths': [str(path)]}, scope=document['scope'],
                           version_id=version_id, document_id=document['id'], revision_reason=reason.strip(),
                           applicability=document.get('metadata', {}).get('scope'))
    return jsonify(success=True, task_id=job['task_id'], message='修订已保存为新版本输入，等待解析')


@app.route('/tasks/<task_id>/publish', methods=['POST'])
@app.route('/tasks/<task_id>/submit', methods=['POST'])
def publish_task(task_id):
    store = get_store()
    release_id = publish(store, task_id)
    store.update_job(task_id, phase='submitted',
        message='资料已加入 ContextDB 提交队列；评审、入库与 Wiki 编译状态请查看治理进度')
    return jsonify(success=True, release_id=release_id, message='资料已提交治理；官方评审、入库与构建状态请查看知识库治理进度')


@app.route('/api/releases')
def list_releases():
    return jsonify(success=True, releases=get_store().list_releases())


@app.route('/api/releases/<release_id>/activate', methods=['POST'])
def activate_release(release_id):
    store=get_store()
    release=store.get_release(release_id)
    store.activate_release(release_id)
    from governance.contextdb_sync import enqueue_sync
    job=enqueue_sync(store,release_id,release['scope'])
    return jsonify(success=True,task_id=job['task_id'],message='采集批次已激活并提交双库同步；知识生效以官方评审结果为准')


@app.route('/api/releases/<release_id>/download')
def download_release(release_id):
    release = get_store().get_release(release_id)
    if not Path(release['archive_path']).is_file():
        raise ApiError('提交快照文件缺失', 404)
    return send_file(release['archive_path'], as_attachment=True, download_name=f"dataset-{release_id}.zip")


@app.route('/api/health')
def health():
    try:
        store = Store()
        store.initialize()
        database, worker = True, store.worker_alive()
    except Exception:
        database, worker = False, False
    return jsonify(success=True, database=database, contextdb=bool(os.getenv('CONTEXTDB_API_KEY')), worker=worker)


# ==================== ShowDoc 登录辅助路由 ====================

@app.route('/showdoc/login', methods=['POST'])
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


@app.route('/showdoc/projects', methods=['GET'])
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

        # 先尝试从缓存获取
        projects = showdoc_project_manager.get_cached_projects()

        # 如果缓存为空或过期,重新获取
        if not projects:
            group_id = request.args.get('group_id', 0)
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


@app.route('/showdoc/project/<item_id>', methods=['GET'])
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


if __name__ == '__main__':
    import uvicorn
    from asgi import create_app
    uvicorn.run(create_app(app), host='127.0.0.1', port=8000)
