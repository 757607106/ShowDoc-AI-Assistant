from flask import Flask, render_template, request, jsonify, send_file, redirect
import os
import threading
import time
import uuid
from datetime import datetime
from zipfile import ZIP_DEFLATED, ZipFile
import shutil

from crawlers.base import CrawlCancelled
from registry import ENTRIES, create_crawler, get_entry
from integrations.showdoc import ShowDocAuthenticator, ShowDocProjectManager

# 尝试加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except (ImportError, FileNotFoundError, PermissionError) as e:
    # 如果 python-dotenv 未安装、.env 文件不存在或权限不足，跳过加载
    print(f"ℹ️  .env 加载被忽略: {e}")

app = Flask(__name__)
# 从环境变量获取密钥，如果未设置则使用默认值（仅用于开发）
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# 全局变量存储任务状态
tasks = {}

# ShowDoc相关全局对象
qwen_api_key = os.getenv('QWEN_API_KEY', '')
if not qwen_api_key:
    print("⚠️  警告: 未设置QWEN_API_KEY环境变量,验证码识别可能失败")
    print("   请设置: export QWEN_API_KEY='your-api-key'")

showdoc_auth = ShowDocAuthenticator(qwen_api_key=qwen_api_key)
showdoc_project_manager = ShowDocProjectManager()

# 爬虫仅用于列出页面/预览，不落盘的临时目录占位
LISTING_SAVE_DIR = os.path.join('downloads', '_listing')

# 请求中允许透传给 create_crawler 的爬取参数白名单
CRAWLER_PARAM_KEYS = (
    'item_id', 'keyword', 'default_page_id', 'user_token', 'url',
    'crawl_mode', 'max_pages', 'max_depth',
)

class ApiError(Exception):
    """带 HTTP 状态码的业务异常，由全局 errorhandler 统一返回。"""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class TaskCancelled(CrawlCancelled):
    """任务在安全检查点收到取消请求。"""


@app.errorhandler(ApiError)
def handle_api_error(error):
    return jsonify({'success': False, 'message': error.message}), error.status_code


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
        token = showdoc_auth.auto_login_if_needed()
        if not token:
            raise ApiError('未登录或登录失败', 401)
        params['user_token'] = token
    return params


class CrawlerTask:
    def __init__(
        self,
        task_id,
        entry,
        params=None,
        selected_ids=None,
        selected_titles=None,
        retry_of=None,
    ):
        self.task_id = task_id
        self.entry = entry          # registry 平台键
        self.params = params or {}  # create_crawler 透传的平台参数
        self.selected_ids = [str(item) for item in (selected_ids or [])]
        self.selected_titles = selected_titles or []
        self.retry_of = retry_of
        self.status = 'pending'  # pending, running, cancelling, completed, failed, cancelled
        self.phase = 'queued'
        self.progress = 0
        self.total_pages = 0
        self.completed_pages = 0
        self.failed_pages = 0
        self.skipped_pages = 0
        self.current_item = ''
        self.message = ''
        self.start_time = datetime.now()
        self.end_time = None
        self.output_dir = None
        self.zip_file = None
        self.summary = None
        self.logs = []
        self.cancel_event = threading.Event()

    def add_log(self, message):
        text = str(message or '').strip()
        if not text:
            return
        if self.logs and self.logs[-1]['message'] == text:
            return
        self.logs.append({
            'time': datetime.now().isoformat(timespec='seconds'),
            'message': text,
        })
        self.logs = self.logs[-120:]


def task_payload(task, include_logs=True):
    """生成前端任务契约，避免暴露账号 token 等爬虫参数。"""
    finished_at = task.end_time or datetime.now()
    elapsed_seconds = max(0, int((finished_at - task.start_time).total_seconds()))
    metrics = {
        'documents': task.summary.total_documents if task.summary else 0,
        'empty_documents': task.summary.empty_documents if task.summary else 0,
        'categories': task.summary.category_count if task.summary else 0,
        'chunks': task.summary.chunk_count if task.summary else 0,
        'quality_score': task.summary.quality_score if task.summary else None,
        'duplicate_documents': task.summary.duplicate_count if task.summary else 0,
        'errors': task.summary.error_count if task.summary else 0,
        'warnings': task.summary.warning_count if task.summary else 0,
        'discovery_strategy': getattr(task.summary, 'discovery_strategy', '') if task.summary else '',
        'coverage_score': getattr(task.summary, 'coverage_score', None) if task.summary else None,
    }
    payload = {
        'task_id': task.task_id,
        'entry': task.entry,
        'entry_name': get_entry(task.entry).display_name,
        'status': task.status,
        'phase': task.phase,
        'progress': task.progress,
        'total_pages': task.total_pages,
        'completed_pages': task.completed_pages,
        'successful_pages': max(0, task.completed_pages - task.failed_pages),
        'failed_pages': task.failed_pages,
        'skipped_pages': task.skipped_pages,
        'current_item': task.current_item,
        'message': task.message,
        'start_time': task.start_time.isoformat(),
        'end_time': task.end_time.isoformat() if task.end_time else None,
        'elapsed_seconds': elapsed_seconds,
        'selected_count': len(task.selected_ids or task.selected_titles),
        'retry_of': task.retry_of,
        'download_available': bool(task.status in {'completed', 'partial'} and task.zip_file),
        'metrics': metrics,
    }
    if include_logs:
        payload['logs'] = list(task.logs)
    return payload


def start_task(entry, params, selected_ids=None, selected_titles=None, retry_of=None):
    task = CrawlerTask(
        str(uuid.uuid4()),
        entry,
        params=params,
        selected_ids=selected_ids,
        selected_titles=selected_titles,
        retry_of=retry_of,
    )
    task.add_log('任务已创建，等待执行')
    tasks[task.task_id] = task
    thread = threading.Thread(target=run_crawler_task, args=(task,), daemon=True)
    thread.start()
    return task


def get_active_task():
    """工作台按单任务串行执行，避免重复提交占用采集会话与网络资源。"""
    return next(
        (task for task in tasks.values() if task.status in {'pending', 'running', 'cancelling'}),
        None,
    )


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/showdoc')
def showdoc():
    """ShowDoc页面（已合并到首页，保持兼容重定向）"""
    return redirect('/')


# ==================== 通用平台接口（registry 分发） ====================

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
    """预览指定文档内容"""
    try:
        entry = get_entry_or_404(key)
        doc_id = (request.args.get('doc_id') or '').strip()
        if not doc_id:
            raise ApiError('缺少doc_id参数')
        if doc_id == '0':
            raise ApiError('无效的 page_id 或项目没有默认页')

        params = entry_crawler_params(key, request.args)
        crawler = create_crawler(entry.key, save_dir=LISTING_SAVE_DIR, **params)

        if entry.key == 'showdoc':
            if not params.get('item_id'):
                raise ApiError('缺少item_id参数')
            # ShowDoc 有单页直取接口，无需先拉取整份目录
            page_data = crawler.fetch_page_data(doc_id)
            if not page_data:
                raise ApiError('获取页面内容失败', 404)
            title = (page_data.get('page_title') or '').strip() or '页面预览'
            content = page_data.get('page_content') or ''
        elif entry.key == 'web':
            crawler.authenticate()
            stubs = crawler.list_documents()
            stub = next((s for s in stubs if s.id == doc_id), None)
            if stub is None:
                raise ApiError('未找到网页文档', 404)
            doc = crawler.fetch_document(stub)
            title = doc.title
            content = doc.markdown
        else:
            crawler.authenticate()
            stubs = crawler.list_documents()
            stub = next((s for s in stubs if s.id == doc_id), None)
            if stub is None:
                raise ApiError(f'未找到文档: {doc_id}', 404)
            doc = crawler.fetch_document(stub)
            title = doc.title
            content = crawler.convert_document(doc, include_attachments=False).markdown

        if not content.strip():
            raise ApiError('获取页面内容失败', 404)
        return jsonify({
            'success': True,
            'title': title,
            'content': content,
            'page_id': doc_id,
        })
    except ApiError:
        raise
    except Exception as e:
        return jsonify({'success': False, 'message': f'预览失败: {str(e)}'}), 500


@app.route('/entries/<key>/start', methods=['POST'])
def entry_start(key):
    """启动指定平台的爬取任务"""
    try:
        entry = get_entry_or_404(key)
        active = get_active_task()
        if active:
            raise ApiError(
                f'已有 {get_entry(active.entry).display_name} 任务正在处理，请等待完成或先取消',
                409,
            )
        data = request.get_json(silent=True) or {}
        params = entry_crawler_params(entry.key, data)
        if entry.key == 'showdoc' and not params.get('item_id'):
            raise ApiError('缺少item_id参数')

        task = start_task(
            entry.key,
            params=params,
            selected_ids=data.get('selected_ids') or [],
            selected_titles=data.get('selected_titles') or [],
        )

        download_type = "选择性下载" if (task.selected_ids or task.selected_titles) else "全量下载"
        return jsonify({
            'success': True,
            'task_id': task.task_id,
            'message': f'{entry.display_name}爬取任务已开始 ({download_type})'
        })
    except ApiError:
        raise
    except Exception as e:
        return jsonify({'success': False, 'message': f'启动失败: {str(e)}'}), 500


@app.route('/task_status/<task_id>')
def task_status(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404

    return jsonify(task_payload(task))


@app.route('/api/tasks')
def task_list():
    """返回最近任务，用于刷新恢复、侧栏状态与数据集历史。"""
    recent = sorted(tasks.values(), key=lambda item: item.start_time, reverse=True)[:30]
    return jsonify({
        'success': True,
        'tasks': [task_payload(task, include_logs=False) for task in recent],
    })


@app.route('/tasks/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    task = tasks.get(task_id)
    if not task:
        raise ApiError('任务不存在', 404)
    if task.status not in {'pending', 'running', 'cancelling'}:
        raise ApiError('当前任务已经结束，无法取消', 409)
    task.cancel_event.set()
    task.status = 'cancelling'
    task.message = '正在安全停止任务...'
    task.add_log(task.message)
    return jsonify({'success': True, 'message': task.message})


@app.route('/tasks/<task_id>/retry', methods=['POST'])
def retry_task(task_id):
    task = tasks.get(task_id)
    if not task:
        raise ApiError('任务不存在', 404)
    if task.status not in {'failed', 'cancelled', 'partial'}:
        raise ApiError('只有失败或已取消的任务可以重试', 409)
    active = get_active_task()
    if active:
        raise ApiError('已有任务正在处理，请等待完成或先取消', 409)
    retried = start_task(
        task.entry,
        params=dict(task.params),
        selected_ids=list(task.selected_ids),
        selected_titles=list(task.selected_titles),
        retry_of=task.task_id,
    )
    return jsonify({
        'success': True,
        'task_id': retried.task_id,
        'message': '已创建重试任务',
    })


@app.route('/download/<task_id>')
def download_result(task_id):
    task = tasks.get(task_id)
    if not task or task.status not in {'completed', 'partial'} or not task.zip_file:
        return jsonify({'error': '文件不可用'}), 404

    try:
        platform = get_entry(task.entry).display_name
        item_id = task.params.get('item_id', '')
        download_type = "selected" if task.selected_titles else "all"
        name_parts = [f'{platform}知识库']
        if item_id:
            name_parts.append(str(item_id))
        name_parts.extend([download_type, datetime.now().strftime("%Y%m%d_%H%M%S")])
        return send_file(
            task.zip_file,
            as_attachment=True,
            download_name='_'.join(name_parts) + '.zip'
        )
    except Exception as e:
        return jsonify({'error': f'下载失败: {str(e)}'}), 500


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


# ==================== 任务执行 ====================

def run_crawler_task(task):
    """在后台按注册表入口运行爬取任务"""
    entry = get_entry(task.entry)
    print(f"\n{'='*60}")
    print(f"🚀 [{entry.display_name}任务启动] task_id={task.task_id}")
    print(f"{'='*60}")

    try:
        task.status = 'running'
        set_task_message(task, '正在初始化采集器...', phase='connecting')
        ensure_task_active(task)

        task.output_dir = os.path.join('downloads', task.task_id)
        os.makedirs(task.output_dir, exist_ok=True)

        crawler = create_crawler(
            task.entry,
            save_dir=task.output_dir,
            progress_callback=lambda current, total, msg: update_task_progress(task, current, total, msg),
            **task.params,
        )
        ensure_task_active(task)

        summary = crawler.crawl(
            selected_ids=task.selected_ids,
            selected_titles=task.selected_titles,
        )
        ensure_task_active(task)
        task.summary = summary

        print(f"\n📊 爬取结果: total={summary.total_documents}, "
              f"empty={summary.empty_documents}, categories={summary.category_count}")

        if summary.total_documents > 0 or summary.failed_documents > 0:
            set_task_message(task, '正在打包数据集...', phase='packaging')
            ensure_task_active(task)
            print("📦 正在创建ZIP文件...")
            zip_filename = os.path.join('downloads', f'{task.task_id}.zip')
            create_zip_file(
                task.output_dir,
                zip_filename,
                cancel_check=lambda: ensure_task_active(task),
            )
            task.zip_file = zip_filename
            ensure_task_active(task)

            selected_count = len(task.selected_ids or task.selected_titles)
            if selected_count:
                task.skipped_pages = max(0, selected_count - summary.total_documents)
            download_type = f"选择了{selected_count}个页面" if selected_count else "全量下载"
            task.failed_pages = getattr(summary, 'failed_documents', 0)
            task.completed_pages = summary.total_documents + task.failed_pages
            task.total_pages = task.completed_pages
            task.status = 'partial' if task.failed_pages or summary.error_count else 'completed'
            task.phase = 'completed'
            task.progress = 100
            task.message = (
                f'处理完成！共 {summary.total_documents} 个页面'
                f'（{summary.empty_documents} 个无内容），'
                f'{summary.category_count} 个分类 ({download_type})'
            )
            if task.status == 'partial':
                task.message = (
                    f'部分完成：{summary.total_documents} 篇有效文档，'
                    f'{task.failed_pages} 篇采集或转换失败，'
                    f'{summary.error_count} 项质量错误；详情见失败清单和质量报告。'
                )
            task.add_log(task.message)
            print(f"\n{'='*60}")
            print(f"✅ [任务完成] status={task.status}")
            print(f"   ZIP文件: {zip_filename}")
            print(f"{'='*60}\n")
        else:
            task.status = 'failed'
            task.phase = 'failed'
            task.message = '未找到任何页面内容或所选页面不存在'
            task.failed_pages = max(1, task.failed_pages)
            task.add_log(task.message)
            print("\n❌ [任务失败] 未找到页面内容")

    except TaskCancelled:
        task.status = 'cancelled'
        task.phase = 'cancelled'
        task.message = '任务已取消，已完成的数据不会进入最终数据集'
        task.skipped_pages = max(0, task.total_pages - task.completed_pages)
        task.add_log(task.message)
        print(f"\n⏹️ [任务取消] task_id={task.task_id}")
    except Exception as e:
        task.status = 'failed'
        task.phase = 'failed'
        task.message = f'爬取失败: {str(e)}'
        task.failed_pages = max(1, task.failed_pages)
        task.add_log(task.message)
        print(f"\n❌ [任务异常] {str(e)}")
    finally:
        task.end_time = datetime.now()
        print(f"📋 任务最终状态: status={task.status}, progress={task.progress}%")


def ensure_task_active(task):
    """在网络请求、清洗与打包之间提供安全取消点。"""
    if task.cancel_event.is_set():
        raise TaskCancelled('任务已取消')


def set_task_message(task, message, phase=None):
    task.message = message
    if phase:
        task.phase = phase
    task.add_log(message)


def update_task_progress(task, current, total, message):
    """更新任务进度"""
    ensure_task_active(task)
    task.completed_pages = current
    task.total_pages = total
    task.progress = int((current / total * 100)) if total > 0 else 0
    task.message = message
    if message.startswith('正在抓取:'):
        task.current_item = message.split(':', 1)[1].strip()
    elif message.startswith('已抓取:'):
        task.current_item = message.split(':', 1)[1].strip()

    if '质量' in message:
        task.phase = 'quality_check'
    elif '数据集' in message or '保存' in message or '打包' in message:
        task.phase = 'packaging'
    elif '清洗' in message:
        task.phase = 'cleaning'
    elif '抓取' in message:
        task.phase = 'crawling'
    elif '登录' in message or '初始化' in message or '目录' in message:
        task.phase = 'connecting'
    task.add_log(message)


def create_zip_file(source_dir, zip_filename, cancel_check=None):
    """原子创建 ZIP；取消或失败时不会留下可误认成数据集的半成品。"""
    partial_filename = f'{zip_filename}.part'
    try:
        with ZipFile(partial_filename, 'w', ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    if cancel_check:
                        cancel_check()
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
        os.replace(partial_filename, zip_filename)
    except Exception:
        if os.path.exists(partial_filename):
            os.remove(partial_filename)
        raise


# 清理旧任务的定时任务
def cleanup_old_tasks():
    """清理超过24小时的旧任务"""
    current_time = datetime.now()
    to_remove = []

    for task_id, task in tasks.items():
        if (current_time - task.start_time).total_seconds() > 86400:  # 24小时
            # 删除相关文件
            if task.output_dir and os.path.exists(task.output_dir):
                shutil.rmtree(task.output_dir, ignore_errors=True)
            if task.zip_file and os.path.exists(task.zip_file):
                os.remove(task.zip_file)
            to_remove.append(task_id)

    for task_id in to_remove:
        del tasks[task_id]


if __name__ == '__main__':
    # 确保下载目录存在
    os.makedirs('downloads', exist_ok=True)

    # 启动定时清理任务
    cleanup_thread = threading.Thread(target=lambda: [time.sleep(3600), cleanup_old_tasks()])
    cleanup_thread.daemon = True
    cleanup_thread.start()

    app.run(host='0.0.0.0', port=8000, debug=True)
