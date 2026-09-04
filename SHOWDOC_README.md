# ShowDoc API文档爬取系统使用指南

## 项目简介

本系统是在云辉煌AI知识库爬取系统基础上扩展的ShowDoc平台API文档爬取工具,支持从ShowDoc平台批量导出API文档并自动转换为RAG友好的Markdown格式。

## 功能特性

### 核心功能
- ✅ **自动登录认证**: 自动完成验证码识别和登录流程
- ✅ **项目管理**: 获取和管理ShowDoc项目列表
- ✅ **智能爬取**: 支持全量下载和选择性下载
- ✅ **RAG优化**: 自动转换为适合RAG系统解析的Markdown格式
- ✅ **进度监控**: 实时显示爬取进度和状态
- ✅ **ZIP打包**: 自动打包成ZIP文件便于下载

### 前端交互
- 🎨 **响应式设计**: 适配桌面端和移动端
- 🔍 **智能搜索**: 支持页面标题实时搜索
- 📊 **状态可视化**: 登录状态、进度条、实时消息提示
- 🎯 **用户友好**: 简洁直观的操作界面

## 技术架构

### 后端模块

| 模块 | 文件 | 功能描述 |
|------|------|---------|
| 认证模块 | `showdoc_auth.py` | 验证码获取、OCR识别、用户登录 |
| 项目管理模块 | `showdoc_project.py` | 项目列表获取、缓存、搜索 |
| 爬虫模块 | `showdoc_crawler.py` | 文档爬取、Markdown转换 |
| Flask路由 | `app.py` | API端点、任务管理 |

### 前端页面

- **主页**: `/` - 云辉煌知识库爬取
- **ShowDoc页面**: `/showdoc` - ShowDoc API文档爬取

### 关键技术

- **后端**: Flask, requests, BeautifulSoup4, jsonpath-ng
- **验证码识别**: 阿里云千问大模型 (Qwen-VL-Max)
- **Markdown处理**: 复用现有的RAG优化逻辑
- **前端**: 原生JavaScript, CSS3

## 快速开始

### 1. 环境准备

确保已安装Python 3.8+和项目依赖:

```bash
cd /Users/pusonglin/PycharmProjects/Yhh_md_run
pip install -r requirements.txt
```

依赖包清单:
- Flask==2.3.3
- requests==2.31.0
- jsonpath-ng==1.6.1
- beautifulsoup4==4.12.2

### 2. 配置环境变量

**设置千问API Key** (必需):

```bash
# Linux/Mac
export QWEN_API_KEY='sk-your-qwen-api-key-here'

# Windows (PowerShell)
$env:QWEN_API_KEY="sk-your-qwen-api-key-here"

# Windows (CMD)
set QWEN_API_KEY=sk-your-qwen-api-key-here
```

**如何获取千问API Key**:

1. 访问 [https://dashscope.aliyun.com/](https://dashscope.aliyun.com/)
2. 注册/登录阿里云账号
3. 进入控制台 -> API-KEY管理
4. 创建新的API Key
5. 复制API Key并设置到环境变量

### 3. 启动服务

```bash
python app.py
```

服务将在 `http://127.0.0.1:8000` 启动

### 4. 访问界面

- **云辉煌知识库**: http://127.0.0.1:8000/
- **ShowDoc爬取**: http://127.0.0.1:8000/showdoc

### 5. 使用流程

#### 方式一: Web界面操作

1. **登录认证**
   - 访问ShowDoc页面
   - 点击"立即登录"按钮
   - 系统自动完成验证码识别和登录

2. **选择项目**
   - 登录成功后自动加载项目列表
   - 从下拉菜单选择目标项目

3. **配置下载**
   - 选择下载模式:
     - 全量备份: 下载所有页面
     - 精准提取: 选择特定页面下载
   - 如果选择精准提取,点击"获取页面列表"
   - 勾选需要下载的页面

4. **开始爬取**
   - 点击"开始数据爬取"按钮
   - 查看实时进度和状态
   - 等待任务完成

5. **下载结果**
   - 任务完成后点击"下载处理结果"
   - 获得ZIP格式的文档包

#### 方式二: API调用

```python
import requests

BASE_URL = "http://127.0.0.1:8000"

# 1. 登录
response = requests.post(f"{BASE_URL}/showdoc/login")
token = response.json()['token']

# 2. 获取项目列表
response = requests.get(f"{BASE_URL}/showdoc/projects")
projects = response.json()['projects']

# 3. 获取页面列表
params = {'item_id': projects[0]['item_id']}
response = requests.get(f"{BASE_URL}/showdoc/pages", params=params)
pages = response.json()['pages']

# 4. 启动爬取
data = {
    'item_id': projects[0]['item_id'],
    'selected_titles': [pages[0]['page_title']]
}
response = requests.post(f"{BASE_URL}/showdoc/start_crawl", json=data)
task_id = response.json()['task_id']

# 5. 查询状态
response = requests.get(f"{BASE_URL}/task_status/{task_id}")
status = response.json()

# 6. 下载结果
# 访问: {BASE_URL}/download/{task_id}
```

## API端点说明

### ShowDoc相关端点

| 端点 | 方法 | 功能 | 参数 |
|------|------|------|------|
| `/showdoc/login` | POST | 执行登录 | 无 |
| `/showdoc/projects` | GET | 获取项目列表 | group_id(可选) |
| `/showdoc/project/<item_id>` | GET | 获取项目详情 | item_id |
| `/showdoc/pages` | GET | 获取页面列表 | item_id, keyword(可选) |
| `/showdoc/start_crawl` | POST | 启动爬取任务 | item_id, keyword, selected_titles |
| `/task_status/<task_id>` | GET | 查询任务状态 | task_id |
| `/download/<task_id>` | GET | 下载结果 | task_id |

## 配置说明

### 登录凭证

通过环境变量配置登录凭证：

```bash
export SHOWDOC_USERNAME="your-showdoc-username"
export SHOWDOC_PASSWORD="your-showdoc-password"
```

也可以将这两个变量写入本地 `.env` 文件；不要把 `.env` 提交到仓库。

### 验证码识别

验证码识别使用千问大模型(Qwen-VL):

- API端点: `https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation`
- 模型: qwen-vl-max
- 认证: 需要千问API Key

**如何设置API Key**:

```bash
# Linux/Mac
export QWEN_API_KEY='your-qwen-api-key-here'

# Windows (PowerShell)
$env:QWEN_API_KEY="your-qwen-api-key-here"

# Windows (CMD)
set QWEN_API_KEY=your-qwen-api-key-here
```

**获取API Key**:

1. 访问 [阿里云百炼平台](https://dashscope.aliyun.com/)
2. 注册/登录账号
3. 在API-KEY管理中创建新的API Key
4. 复制API Key并设置到环境变量

## 测试

### 运行集成测试

```bash
python test_showdoc_integration.py
```

测试流程:
1. ✅ ShowDoc登录功能
2. ✅ 获取项目列表
3. ✅ 获取页面列表
4. ✅ 启动爬取任务
5. ✅ 监控任务状态

### 单元测试

各模块独立测试:

```bash
# 测试认证模块
python showdoc_auth.py

# 测试项目管理模块
python showdoc_project.py

# 测试爬虫模块
python showdoc_crawler.py
```

## 输出格式

### Markdown文档特点

所有导出的文档都经过RAG优化处理,具有以下特点:

- ✅ **标准化格式**: 统一的标题、列表、代码块格式
- ✅ **语义标记**: 添加HTML注释标记便于RAG解析
- ✅ **内容分块**: 清晰的段落和章节分隔
- ✅ **结构化**: 保留完整的层级结构
- ✅ **图片处理**: 保留图片链接和alt文本

示例输出:

```markdown
# 页面标题

<!-- MAIN_TITLE -->
## 章节标题

<!-- SECTION_TITLE -->
### 子章节

<!-- SUBSECTION_TITLE -->
正文内容...

<!-- PARAGRAPH_START -->
- 列表项1
- 列表项2

<!-- LIST_START -->
```

## 常见问题

### 1. 环境变量未设置

**问题**: 启动时提示"未设置QWEN_API_KEY环境变量"

**解决方案**:
- 设置千问API Key环境变量
- 确保在启动Flask之前设置
- 可以在.bashrc或.zshrc中永久设置

### 2. 登录失败

**问题**: 登录时提示"登录失败"

**解决方案**:
- 检查网络连接,确保能访问ShowDoc平台
- 检查用户名和密码是否正确
- OCR服务可能超时,重试即可
- 查看控制台日志获取详细错误信息

### 3. 验证码识别失败

**问题**: 千问大模型识别不出验证码

**解决方案**:
- 系统会自动重试3次
- 检查QWEN_API_KEY是否正确
- 检查API Key是否有足够的额度
- 检查网络连接是否能访问阿里云

### 4. 爬取速度慢

**问题**: 爬取大量页面时耗时较长

**解决方案**:
- 正常现象,每个页面需要单独请求
- 使用选择性下载减少页面数量
- 在后台运行,不影响其他操作

### 5. 下载文件为空

**问题**: 下载的ZIP文件中没有内容

**解决方案**:
- 检查是否选择了页面
- 查看任务状态是否为completed
- 检查服务器日志确认爬取是否成功

## 目录结构

```
Yhh_md_run/
├── app.py                          # Flask主应用
├── crawler.py                      # 云辉煌爬虫(原有)
├── showdoc_auth.py                 # ShowDoc认证模块
├── showdoc_project.py              # ShowDoc项目管理
├── showdoc_crawler.py              # ShowDoc爬虫模块
├── test_showdoc_integration.py     # 集成测试脚本
├── requirements.txt                # Python依赖
├── templates/
│   ├── index.html                  # 云辉煌页面
│   └── showdoc.html                # ShowDoc页面
└── downloads/                      # 下载文件目录
```

## 注意事项

1. **本地运行**: 当前版本仅供本地使用,未考虑生产部署
2. **数据清理**: 下载文件会在24小时后自动清理
3. **并发限制**: 单次只能运行一个爬取任务
4. **认证有效期**: Token有效期约2小时,过期会自动重新登录

## 开发计划

未来可能的功能扩展:

- [ ] 支持HTML格式导出
- [ ] 内容预览功能
- [ ] 增量更新支持
- [ ] 多项目并发爬取
- [ ] 文档质量评估
- [ ] 自定义Markdown模板

## 技术支持

如遇到问题,请查看:

1. 控制台日志输出
2. Flask应用日志
3. 浏览器开发者工具Console

## 许可证

本项目基于现有云辉煌知识库爬取系统扩展开发。

---

**祝使用愉快!** 🎉
