from flask import Flask, render_template, request, jsonify, send_file, redirect
import os
import re
import threading
import time
import uuid
from datetime import datetime
from zipfile import ZIP_DEFLATED, ZipFile
import shutil

from common.converter import (
    convert_html_to_markdown,
    normalize_markdown,
    prepare_html_content,
)
from registry import ENTRIES, create_crawler, get_entry
from showdoc_auth import ShowDocAuthenticator
from showdoc_project import ShowDocProjectManager

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

# 正文包含 HTML 块级标签时先转 Markdown 再预览；
# ShowDoc 正文本身是 Markdown 源码，原样返回
HTML_TAG_PATTERN = re.compile(
    r'<(?:p|div|h[1-6]|img|table|ul|ol|li|br|strong|a)\b', re.IGNORECASE
)


class ApiError(Exception):
    """带 HTTP 状态码的业务异常，由全局 errorhandler 统一返回。"""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


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
    def __init__(self, task_id, entry, params=None, selected_titles=None):
        self.task_id = task_id
        self.entry = entry          # registry 平台键
        self.params = params or {}  # create_crawler 透传的平台参数
        self.selected_titles = selected_titles or []
        self.status = 'pending'  # pending, running, completed, failed
        self.progress = 0
        self.total_pages = 0
        self.completed_pages = 0
        self.message = ''
        self.start_time = datetime.now()
        self.end_time = None
        self.output_dir = None
        self.zip_file = None


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
            # 标题去重后走内容拼接钩子；视频教程的封面/视频链接在钩子里补齐，
            # 因此正文为空的文档仍可能拼出可预览内容
            assembled = crawler.assemble_html(
                doc,
                prepare_html_content(doc.html or '', doc.title, document_id=doc.id),
            )
            if assembled and HTML_TAG_PATTERN.search(assembled):
                # 相对图片地址绝对化到站点根，保证预览模态框内可加载
                content = normalize_markdown(
                    convert_html_to_markdown(assembled, doc.title),
                    heading_offset=0,
                    site_base_url=crawler.site_base_url,
                )
            else:
                content = assembled

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
        data = request.get_json(silent=True) or {}
        params = entry_crawler_params(entry.key, data)
        if entry.key == 'showdoc' and not params.get('item_id'):
            raise ApiError('缺少item_id参数')

        task_id = str(uuid.uuid4())
        task = CrawlerTask(
            task_id,
            entry.key,
            params=params,
            selected_titles=data.get('selected_titles') or [],
        )
        tasks[task_id] = task

        # 在后台线程中运行爬虫
        thread = threading.Thread(target=run_crawler_task, args=(task,))
        thread.daemon = True
        thread.start()

        download_type = "选择性下载" if task.selected_titles else "全量下载"
        return jsonify({
            'success': True,
            'task_id': task_id,
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

    return jsonify({
        'task_id': task.task_id,
        'entry': task.entry,
        'status': task.status,
        'progress': task.progress,
        'total_pages': task.total_pages,
        'completed_pages': task.completed_pages,
        'message': task.message,
        'start_time': task.start_time.isoformat(),
        'end_time': task.end_time.isoformat() if task.end_time else None,
        'selected_count': len(task.selected_titles) if task.selected_titles else 0
    })


@app.route('/download/<task_id>')
def download_result(task_id):
    task = tasks.get(task_id)
    if not task or task.status != 'completed' or not task.zip_file:
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
        task.message = '正在初始化爬虫...'

        task.output_dir = os.path.join('downloads', task.task_id)
        os.makedirs(task.output_dir, exist_ok=True)

        crawler = create_crawler(
            task.entry,
            save_dir=task.output_dir,
            progress_callback=lambda current, total, msg: update_task_progress(task, current, total, msg),
            **task.params,
        )

        summary = crawler.crawl(selected_titles=task.selected_titles)

        print(f"\n📊 爬取结果: total={summary.total_documents}, "
              f"empty={summary.empty_documents}, categories={summary.category_count}")

        if summary.total_documents > 0:
            print(f"📦 正在创建ZIP文件...")
            zip_filename = os.path.join('downloads', f'{task.task_id}.zip')
            create_zip_file(task.output_dir, zip_filename)
            task.zip_file = zip_filename

            download_type = f"选择了{len(task.selected_titles)}个页面" if task.selected_titles else "全量下载"
            task.status = 'completed'
            task.message = (
                f'处理完成！共 {summary.total_documents} 个页面'
                f'（{summary.empty_documents} 个无内容），'
                f'{summary.category_count} 个分类 ({download_type})'
            )
            print(f"\n{'='*60}")
            print(f"✅ [任务完成] status=completed")
            print(f"   ZIP文件: {zip_filename}")
            print(f"{'='*60}\n")
        else:
            task.status = 'failed'
            task.message = '未找到任何页面内容或所选页面不存在'
            print(f"\n❌ [任务失败] 未找到页面内容")

    except Exception as e:
        task.status = 'failed'
        task.message = f'爬取失败: {str(e)}'
        print(f"\n❌ [任务异常] {str(e)}")
    finally:
        task.end_time = datetime.now()
        task.progress = 100
        print(f"📋 任务最终状态: status={task.status}, progress={task.progress}%")


def update_task_progress(task, current, total, message):
    """更新任务进度"""
    task.completed_pages = current
    task.total_pages = total
    task.progress = int((current / total * 100)) if total > 0 else 0
    task.message = message


def create_zip_file(source_dir, zip_filename):
    """创建ZIP压缩文件"""
    with ZipFile(zip_filename, 'w', ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)


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
