"""Local governance workbench; durable jobs run in governance.worker."""
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory, redirect
from werkzeug.exceptions import RequestEntityTooLarge

from integrations.contextdb import ContextDBError, ContextDBConflictError
from governance.store import Store, StoreError
from common.env_sanitize import sanitize_no_proxy

sanitize_no_proxy()
load_dotenv()
# material.py 在导入期创建需要环境变量的单例，webapi 的导入必须晚于环境装配
from webapi import register_blueprints
from webapi.auth import client_for_user, require_login, finish_audit

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY') or os.urandom(32)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
register_blueprints(app)
app.before_request(require_login)
app.after_request(finish_audit)
FRONTEND_DIST = Path(__file__).resolve().parent / 'frontend' / 'dist'


@app.route('/')
def index():
    if (FRONTEND_DIST / 'index.html').is_file():
        return send_from_directory(FRONTEND_DIST, 'index.html')
    return '前端未构建:cd frontend && npm install && npm run build', 503


@app.route('/showdoc')
def showdoc():
    return redirect('/')


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
    if (request.path.startswith('/api/v1/models') or request.path == '/api/v1/tenants/kv/default-settings'
            or request.blueprint == 'model_runtime'):
        codes = {400: 1000, 401: 1001, 403: 1002, 404: 1003, 409: 1005, 422: 1010, 503: 1008}
        return jsonify(success=False, error={'code': codes.get(error.status, 1007), 'message': str(error), 'details': None}), error.status
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


@app.route('/api/health')
def health():
    try:
        store = Store()
        store.initialize()
        database, worker = True, store.worker_alive()
    except Exception:
        database, worker = False, False
    return jsonify(success=True, database=database, contextdb=bool(os.getenv('CONTEXTDB_API_KEY')), worker=worker)


if __name__ == '__main__':
    import uvicorn
    from asgi import create_app
    uvicorn.run(create_app(app), host='127.0.0.1', port=8000)
