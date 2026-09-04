from flask import Flask, render_template, request, jsonify, send_file, session, redirect
import os
import threading
import time
import uuid
from datetime import datetime
from crawler import YunHuiHuangCrawler
from showdoc_auth import ShowDocAuthenticator
from showdoc_project import ShowDocProjectManager
from showdoc_crawler import ShowDocCrawler
import zipfile
import shutil

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
# 从环境变量获取千问API密钥
qwen_api_key = os.getenv('QWEN_API_KEY', '')
if not qwen_api_key:
    print("⚠️  警告: 未设置QWEN_API_KEY环境变量,验证码识别可能失败")
    print("   请设置: export QWEN_API_KEY='your-api-key'")

showdoc_auth = ShowDocAuthenticator(qwen_api_key=qwen_api_key)
showdoc_project_manager = ShowDocProjectManager()

class CrawlerTask:
    def __init__(self, task_id, item_id, keyword='', default_page_id='', selected_titles=None, 
                 crawler_type='yunhuihuang', user_token=None):
        self.task_id = task_id
        self.item_id = item_id
        self.keyword = keyword
        self.default_page_id = default_page_id
        self.selected_titles = selected_titles or []  # 新增：选择的页面标题
        self.crawler_type = crawler_type  # 新增：爬虫类型 yunhuihuang/showdoc
        self.user_token = user_token  # 新增：ShowDoc认证令牌
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

@app.route('/get_pages')
def get_pages():
    """获取指定项目的所有页面列表"""
    try:
        item_id = request.args.get('item_id')
        keyword = request.args.get('keyword', '')
        default_page_id = request.args.get('default_page_id', '')

        if not item_id:
            return jsonify({
                'success': False,
                'message': '缺少item_id参数'
            }), 400

        crawler = YunHuiHuangCrawler(
            item_id=item_id,
            keyword=keyword,
            default_page_id=default_page_id
        )
        pages = crawler.get_available_pages()
        return jsonify({
            'success': True,
            'pages': pages
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取页面列表失败: {str(e)}'
        }), 500

@app.route('/preview_page')
def preview_page():
    """预览指定页面的内容"""
    try:
        item_id = request.args.get('item_id')
        page_id = request.args.get('page_id')
        platform = request.args.get('platform', 'yunhuihuang')  # yunhuihuang 或 showdoc

        if not item_id or not page_id:
            return jsonify({
                'success': False,
                'message': '缺少item_id或page_id参数'
            }), 400
        title = "页面预览"
        content = ""

        # 防御：page_id 为 0 或 非法时直接返回友好错误，避免调用爬虫引发不明确错误
        try:
            if str(int(page_id)) == '0':
                print(f"⚠️ 获取页面内容失败 (page_id={page_id}): 无效 page_id")
                return jsonify({
                    'success': False,
                    'message': '无效的 page_id 或项目没有默认页'
                }), 400
        except Exception:
            # 如果 page_id 不能转换为 int，也视为非法
            print(f"⚠️ 获取页面内容失败 (page_id={page_id}): 非法 page_id")
            return jsonify({
                'success': False,
                'message': '无效的 page_id 参数'
            }), 400

        if platform == 'yunhuihuang':
            crawler = YunHuiHuangCrawler(item_id=item_id)
            content = crawler.get_page_content(page_id)
            # 尝试从页面列表中获取标题
            try:
                pages = crawler.get_available_pages()
                page_info = next((p for p in pages if str(p['page_id']) == str(page_id)), None)
                if page_info:
                    title = page_info['page_title']
            except:
                pass
        elif platform == 'showdoc':
            token = showdoc_auth.auto_login_if_needed()
            if not token:
                return jsonify({
                    'success': False,
                    'message': '未登录或登录失败'
                }), 401

            crawler = ShowDocCrawler(item_id=item_id, user_token=token)
            content = crawler.get_page_content(page_id)
            # 尝试从页面列表中获取标题
            try:
                pages = crawler.get_available_pages()
                page_info = next((p for p in pages if str(p['page_id']) == str(page_id)), None)
                if page_info:
                    title = page_info['page_title']
            except:
                pass
        else:
            return jsonify({
                'success': False,
                'message': '不支持的平台类型'
            }), 400

        if content:
            return jsonify({
                'success': True,
                'title': title,
                'content': content,
                'page_id': page_id
            })
        else:
            return jsonify({
                'success': False,
                'message': '获取页面内容失败'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'预览失败: {str(e)}'
        }), 500

@app.route('/start_crawl', methods=['POST'])
def start_crawl():
    try:
        data = request.get_json()
        item_id = data.get('item_id', '412')
        keyword = data.get('keyword', '')
        default_page_id = data.get('default_page_id', '8653')
        selected_titles = data.get('selected_titles', [])  # 新增：选择的页面标题
        
        # 生成唯一任务ID
        task_id = str(uuid.uuid4())
        
        # 创建任务
        task = CrawlerTask(task_id, item_id, keyword, default_page_id, selected_titles)
        tasks[task_id] = task
        
        # 在后台线程中运行爬虫
        thread = threading.Thread(target=run_crawler, args=(task,))
        thread.daemon = True
        thread.start()
        
        download_type = "选择性下载" if selected_titles else "全量下载"
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': f'爬取任务已开始 ({download_type})'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'启动失败: {str(e)}'
        }), 500

@app.route('/task_status/<task_id>')
def task_status(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    
    return jsonify({
        'task_id': task.task_id,
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
        download_type = "selected" if task.selected_titles else "all"
        platform = "ShowDoc" if task.crawler_type == 'showdoc' else "云辉煌"
        return send_file(
            task.zip_file,
            as_attachment=True,
            download_name=f'{platform}知识库_{task.item_id}_{download_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        )
    except Exception as e:
        return jsonify({'error': f'下载失败: {str(e)}'}), 500

# ==================== ShowDoc相关路由 ====================

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

@app.route('/showdoc/pages', methods=['GET'])
def showdoc_get_pages():
    """获取ShowDoc项目的所有页面列表"""
    try:
        token = showdoc_auth.auto_login_if_needed()
        
        if not token:
            return jsonify({
                'success': False,
                'message': '未登录或登录失败'
            }), 401
        
        item_id = request.args.get('item_id')
        keyword = request.args.get('keyword', '')
        default_page_id = request.args.get('default_page_id', '')
        
        if not item_id:
            return jsonify({
                'success': False,
                'message': '缺少item_id参数'
            }), 400
        
        crawler = ShowDocCrawler(
            item_id=item_id,
            user_token=token,
            keyword=keyword,
            default_page_id=default_page_id
        )
        
        pages = crawler.get_available_pages()
        
        return jsonify({
            'success': True,
            'pages': pages
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取页面列表失败: {str(e)}'
        }), 500

@app.route('/showdoc/start_crawl', methods=['POST'])
def showdoc_start_crawl():
    """启动ShowDoc文档爬取任务"""
    try:
        token = showdoc_auth.auto_login_if_needed()
        
        if not token:
            return jsonify({
                'success': False,
                'message': '未登录或登录失败'
            }), 401
        
        data = request.get_json()
        item_id = data.get('item_id')
        keyword = data.get('keyword', '')
        default_page_id = data.get('default_page_id', '')
        selected_titles = data.get('selected_titles', [])
        
        if not item_id:
            return jsonify({
                'success': False,
                'message': '缺少item_id参数'
            }), 400
        
        # 生成唯一任务ID
        task_id = str(uuid.uuid4())
        
        # 创建任务
        task = CrawlerTask(
            task_id=task_id,
            item_id=item_id,
            keyword=keyword,
            default_page_id=default_page_id,
            selected_titles=selected_titles,
            crawler_type='showdoc',
            user_token=token
        )
        tasks[task_id] = task
        
        # 在后台线程中运行爬虫
        thread = threading.Thread(target=run_showdoc_crawler, args=(task,))
        thread.daemon = True
        thread.start()
        
        download_type = "选择性下载" if selected_titles else "全量下载"
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': f'ShowDoc爬取任务已开始 ({download_type})'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'启动失败: {str(e)}'
        }), 500

def run_crawler(task):
    """在后台运行爬虫"""
    print(f"\n{'='*60}")
    print(f"🚀 [云辉煌任务启动] task_id={task.task_id}")
    print(f"{'='*60}")
    
    try:
        task.status = 'running'
        task.message = '正在初始化爬虫...'
        
        # 创建输出目录
        task.output_dir = os.path.join('downloads', task.task_id)
        os.makedirs(task.output_dir, exist_ok=True)
        
        # 创建爬虫实例
        crawler = YunHuiHuangCrawler(
            item_id=task.item_id,
            keyword=task.keyword,
            default_page_id=task.default_page_id,
            save_directory=task.output_dir,
            selected_titles=task.selected_titles,
            progress_callback=lambda current, total, msg: update_task_progress(task, current, total, msg)
        )
        
        # 开始爬取
        success_count, total_count = crawler.crawl()
        
        print(f"\n📊 爬取结果: success={success_count}, total={total_count}")
        
        if total_count > 0:
            # 创建ZIP文件
            print(f"📦 正在创建ZIP文件...")
            zip_filename = os.path.join('downloads', f'{task.task_id}.zip')
            create_zip_file(task.output_dir, zip_filename)
            task.zip_file = zip_filename
            
            download_type = f"选择了{len(task.selected_titles)}个页面" if task.selected_titles else "全量下载"
            task.status = 'completed'
            task.message = f'处理成功！成功保存 {success_count}/{total_count} 个页面 ({download_type})'
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

def run_showdoc_crawler(task):
    """在后台运行ShowDoc爬虫"""
    print(f"\n{'='*60}")
    print(f"🚀 [任务启动] task_id={task.task_id}")
    print(f"{'='*60}")
    
    try:
        task.status = 'running'
        task.message = '正在初始化ShowDoc爬虫...'
        
        # 创建输出目录
        task.output_dir = os.path.join('downloads', task.task_id)
        os.makedirs(task.output_dir, exist_ok=True)
        
        # 创建ShowDoc爬虫实例
        crawler = ShowDocCrawler(
            item_id=task.item_id,
            user_token=task.user_token,
            keyword=task.keyword,
            default_page_id=task.default_page_id,
            save_directory=task.output_dir,
            selected_titles=task.selected_titles,
            progress_callback=lambda current, total, msg: update_task_progress(task, current, total, msg)
        )
        
        # 开始爬取
        success_count, total_count = crawler.crawl()
        
        print(f"\n📊 爬取结果: success={success_count}, total={total_count}")
        
        if total_count > 0:
            # 创建ZIP文件
            print(f"📦 正在创建ZIP文件...")
            zip_filename = os.path.join('downloads', f'{task.task_id}.zip')
            create_zip_file(task.output_dir, zip_filename)
            task.zip_file = zip_filename
            
            download_type = f"选择了{len(task.selected_titles)}个页面" if task.selected_titles else "全量下载"
            task.status = 'completed'
            task.message = f'处理完成！成功保存 {success_count}/{total_count} 个页面 ({download_type})'
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
        task.message = f'ShowDoc爬取失败: {str(e)}'
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
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
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
    
    app.run(host='0.0.0.0', port=8000, debug=True)  # 使用9999端口