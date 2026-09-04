import requests
import os
from jsonpath_ng import parse
import re
from bs4 import BeautifulSoup

class YunHuiHuangCrawler:
    def __init__(self, item_id='412', keyword='', default_page_id='8653', 
                 save_directory=None, progress_callback=None, selected_titles=None):
        self.item_id = item_id
        self.keyword = keyword
        self.default_page_id = default_page_id
        self.save_directory = save_directory or f"./downloads/云辉煌AI知识库_{item_id}"
        self.progress_callback = progress_callback
        self.selected_titles = selected_titles or []  # 新增：指定要下载的页面标题列表
        
        # 用于收集文档结构的数据（用于生成合并MD）
        self.collected_docs = []  # 存储所有页面内容和层级信息
        self.project_name = ""  # 项目名称
        
        # 网站URL：https://yunhelp.gmgrasp.com.cn/web/#/item/index


        # API URLs
        self.url_item_info = "https://yunhelp.gmgrasp.com.cn/server/index.php?s=/api/item/info"
        self.url_page_info = "https://yunhelp.gmgrasp.com.cn/server/index.php?s=/api/page/info"
        
        # 请求参数
        self.params_item_info = {
            'item_id': self.item_id,
            'keyword': self.keyword,
            'default_page_id': self.default_page_id
        }


    def clean_filename(self, filename):
        """清理文件名，移除不合法字符"""
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.strip()
        return filename
    
    def clean_html_content(self, content):
        """清理HTML标签，保留纯文本内容并转换为适合RAG解析的标准Markdown格式"""
        if not content:
            return ""
        
        try:
            # 首先解码HTML实体
            import html
            content = html.unescape(content)
            
            # 处理转义字符
            content = content.replace('\\[', '[').replace('\\]', ']')
            
            # 预处理：移除 <center> 标签但保留内容
            content = re.sub(r'<center>\s*', '', content, flags=re.IGNORECASE)
            content = re.sub(r'\s*</center>', '', content, flags=re.IGNORECASE)
            
            # 处理特殊的图片格式
            content = re.sub(r'!\s*`([^`]+)`', r'![](\1)', content)
            
            # 使用BeautifulSoup解析HTML内容
            soup = BeautifulSoup(content, 'html.parser')
            
            # 处理图片标签 - 转换为标准Markdown格式，添加语义标记
            for tag in soup.find_all('img'):
                src = tag.get('src', '')
                alt = tag.get('alt', '图片')
                if src:
                    # 为图片添加明确的语义分隔
                    tag.string = f"\n\n---\n\n**图片**: {alt}\n\n![{alt}]({src})\n\n---\n\n"
                else:
                    tag.string = f"**图片说明**: {alt}\n\n"
                tag.name = 'span'
            
            # 处理标题标签 - 确保标题层级结构清晰
            for i in range(1, 7):
                for tag in soup.find_all(f'h{i}'):
                    text = tag.get_text().strip()
                    if text:
                        # 确保标题前后有适当的空行，便于RAG分块
                        tag.string = f"\n\n{'#' * i} {text}\n\n"
                    else:
                        tag.string = ""
                    tag.name = 'span'
            
            # 处理粗体标签
            for tag in soup.find_all(['b', 'strong']):
                text = tag.get_text().strip()
                if text:
                    tag.string = f"**{text}**"
                else:
                    tag.string = ""
                tag.name = 'span'
            
            # 处理斜体标签
            for tag in soup.find_all(['i', 'em']):
                text = tag.get_text().strip()
                if text:
                    tag.string = f"*{text}*"
                else:
                    tag.string = ""
                tag.name = 'span'
            
            # 处理代码标签 - 使用标准代码块格式
            for tag in soup.find_all('code'):
                text = tag.get_text().strip()
                if text:
                    # 检测是否为多行代码
                    if '\n' in text or len(text) > 50:
                        tag.string = f"\n\n```\n{text}\n```\n\n"
                    else:
                        tag.string = f"`{text}`"
                else:
                    tag.string = ""
                tag.name = 'span'
            
            # 处理预格式化文本
            for tag in soup.find_all('pre'):
                text = tag.get_text().strip()
                if text:
                    tag.string = f"\n\n```\n{text}\n```\n\n"
                else:
                    tag.string = ""
                tag.name = 'span'
            
            # 处理链接标签
            for tag in soup.find_all('a'):
                href = tag.get('href', '')
                text = tag.get_text().strip()
                if href and text:
                    tag.string = f"[{text}]({href})"
                elif text:
                    tag.string = text
                else:
                    tag.string = ""
                tag.name = 'span'
            
            # 处理列表标签 - 确保列表格式标准化
            for tag in soup.find_all(['ul', 'ol']):
                items = []
                for i, li in enumerate(tag.find_all('li')):
                    li_text = li.get_text().strip()
                    if li_text:
                        if tag.name == 'ul':
                            items.append(f"- {li_text}")
                        else:
                            items.append(f"{i+1}. {li_text}")
                if items:
                    tag.string = "\n\n" + "\n".join(items) + "\n\n"
                else:
                    tag.string = ""
                tag.name = 'span'
            
            # 处理表格标签
            for table in soup.find_all('table'):
                table_text = self._convert_table_to_markdown(table)
                if table_text:
                    table.string = f"\n\n{table_text}\n\n"
                else:
                    table.string = ""
                table.name = 'span'
            
            # 处理换行标签
            for tag in soup.find_all('br'):
                tag.string = "\n"
                tag.name = 'span'
            
            # 处理段落标签 - 确保段落间有清晰分隔
            for tag in soup.find_all('p'):
                text = tag.get_text().strip()
                if text:
                    tag.string = f"\n\n{text}\n\n"
                else:
                    tag.string = ""
                tag.name = 'span'
            
            # 处理div标签
            for tag in soup.find_all('div'):
                text = tag.get_text().strip()
                if text:
                    tag.string = f"\n{text}\n"
                else:
                    tag.string = ""
                tag.name = 'span'
            
            # 获取清理后的文本
            cleaned_text = soup.get_text()
            
            # 最终清理：移除所有剩余的HTML标签
            cleaned_text = re.sub(r'<[^>]+>', '', cleaned_text)
            
            # 优化Markdown格式排版，使其适合RAG解析
            cleaned_text = self._optimize_markdown_for_rag(cleaned_text)
            
            return cleaned_text
            
        except Exception as e:
            # 如果处理失败，返回原始内容并记录错误
            print(f"HTML清理过程中出现错误: {e}")
            return content if content else ""
    
    def _convert_table_to_markdown(self, table):
        """将HTML表格转换为Markdown表格格式"""
        try:
            rows = table.find_all('tr')
            if not rows:
                return ""
            
            markdown_rows = []
            
            for i, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                if not cells:
                    continue
                
                # 提取单元格文本
                cell_texts = []
                for cell in cells:
                    text = cell.get_text().strip().replace('\n', ' ').replace('|', '\|')
                    cell_texts.append(text if text else " ")
                
                # 构建表格行
                markdown_row = "| " + " | ".join(cell_texts) + " |"
                markdown_rows.append(markdown_row)
                
                # 如果是第一行（表头），添加分隔符
                if i == 0:
                    separator = "| " + " | ".join(["---"] * len(cell_texts)) + " |"
                    markdown_rows.append(separator)
            
            return "\n".join(markdown_rows) if markdown_rows else ""
            
        except Exception as e:
            print(f"表格转换错误: {e}")
            return ""
    
    def _optimize_markdown_for_rag(self, content):
        """专门为RAG解析优化Markdown格式"""
        if not content:
            return ""
        
        # 清理多余的空行，但保持适当的段落间距
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        # 清理行内多余的空格
        content = re.sub(r'[ \t]+', ' ', content)
        
        # 确保标题前后有适当的空行，便于RAG分块
        content = re.sub(r'\n*(#{1,6}\s[^\n]+)\n*', r'\n\n\1\n\n', content)
        
        # 确保图片前后有适当的空行和分隔符
        content = re.sub(r'\n*(!\[[^\]]*\]\([^)]+\))\n*', r'\n\n\1\n\n', content)
        
        # 确保代码块前后有适当的空行
        content = re.sub(r'\n*(```[\s\S]*?```)\n*', r'\n\n\1\n\n', content)
        
        # 确保列表前后有适当的空行
        content = re.sub(r'\n*(([-*+]|\d+\.)\s[^\n]+(?:\n([-*+]|\d+\.)\s[^\n]+)*)\n*', r'\n\n\1\n\n', content)
        
        # 处理特殊符号，确保它们在行首
        lines = content.split('\n')
        processed_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('✅'):
                # 确保✅符号格式正确，便于RAG识别
                processed_lines.append(f"**解决方案**: {stripped}")
            elif stripped.startswith('###') and '问题描述：' in stripped:
                # 标准化问题描述格式
                processed_lines.append(stripped)
            elif stripped.startswith('---') and len(stripped) == 3:
                # 标准化分隔符
                processed_lines.append('---')
            else:
                processed_lines.append(line.rstrip())
        
        content = '\n'.join(processed_lines)
        
        # 添加语义分块标记，帮助RAG更好地理解内容结构
        content = self._add_semantic_markers(content)
        
        # 最终清理：移除开头和结尾的多余空行
        content = content.strip()
        
        # 确保文档以单个换行结束
        if content and not content.endswith('\n'):
            content += '\n'
        
        return content
    
    def _add_semantic_markers(self, content):
        """为内容添加语义标记，便于RAG系统理解"""
        try:
            lines = content.split('\n')
            marked_lines = []
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                
                # 识别并标记不同类型的内容
                if stripped.startswith('# '):
                    # 主标题
                    marked_lines.append(f"<!-- MAIN_TITLE -->\n{line}")
                elif stripped.startswith('## '):
                    # 二级标题
                    marked_lines.append(f"<!-- SECTION_TITLE -->\n{line}")
                elif stripped.startswith('### '):
                    # 三级标题
                    marked_lines.append(f"<!-- SUBSECTION_TITLE -->\n{line}")
                elif '问题描述' in stripped or '解决方案' in stripped:
                    # 问题解决类内容
                    marked_lines.append(f"<!-- PROBLEM_SOLUTION -->\n{line}")
                elif stripped.startswith('!['):
                    # 图片内容
                    marked_lines.append(f"<!-- IMAGE_CONTENT -->\n{line}")
                elif stripped.startswith('```'):
                    # 代码块
                    marked_lines.append(f"<!-- CODE_BLOCK -->\n{line}")
                elif stripped.startswith('- ') or re.match(r'^\d+\.\s', stripped):
                    # 列表项
                    if i == 0 or not lines[i-1].strip().startswith(('- ', '1. ', '2. ', '3.')):
                        marked_lines.append(f"<!-- LIST_START -->\n{line}")
                    else:
                        marked_lines.append(line)
                else:
                    marked_lines.append(line)
            
            return '\n'.join(marked_lines)
            
        except Exception as e:
            print(f"语义标记添加错误: {e}")
            return content
    
    def _optimize_markdown_layout(self, content):
        """优化Markdown格式的排版（保留兼容性）"""
        # 调用新的RAG优化方法
        return self._optimize_markdown_for_rag(content)

    def validate_markdown_format(self, content):
        """验证并修正Markdown格式，确保内容完整性"""
        if not content:
            return ""
        
        try:
            lines = content.split('\n')
            validated_lines = []
            
            for i, line in enumerate(lines):
                # 保留原始缩进，但清理行尾空格
                original_line = line.rstrip()
                stripped_line = line.strip()
                
                if not stripped_line:
                    validated_lines.append('')
                    continue
                
                # 确保标题格式正确
                if stripped_line.startswith('#'):
                    # 确保#后面有空格
                    if not re.match(r'^#+\s', stripped_line):
                        stripped_line = re.sub(r'^(#+)', r'\1 ', stripped_line)
                    validated_lines.append(stripped_line)
                
                # 处理特殊的问题描述格式
                elif '问题描述：' in stripped_line and not stripped_line.startswith('#'):
                    # 确保问题描述有正确的标题级别
                    if stripped_line.startswith('###'):
                        validated_lines.append(stripped_line)
                    else:
                        validated_lines.append(f"### {stripped_line}")
                
                # 处理处理方案格式
                elif stripped_line.startswith('✅'):
                    validated_lines.append(stripped_line)
                
                # 处理列表项
                elif re.match(r'^[-*+]\s', stripped_line) or re.match(r'^\d+\.\s', stripped_line):
                    validated_lines.append(stripped_line)
                
                # 处理图片
                elif re.match(r'^!\[.*\]\(.*\)$', stripped_line):
                    validated_lines.append(stripped_line)
                
                # 处理链接
                elif re.match(r'^\[.*\]\(.*\)$', stripped_line):
                    validated_lines.append(stripped_line)
                
                else:
                    # 保持原始格式，但确保内容完整
                    validated_lines.append(original_line)
            
            # 重新组合内容
            validated_content = '\n'.join(validated_lines)
            
            # 最终清理：确保段落之间有适当的间距，但不超过两个换行
            validated_content = re.sub(r'\n{3,}', '\n\n', validated_content)
            
            # 确保内容完整性检查
            if len(validated_content.strip()) < len(content.strip()) * 0.8:
                print("警告：验证后的内容长度显著减少，可能存在内容丢失")
                return content  # 返回原始内容以避免数据丢失
            
            return validated_content
            
        except Exception as e:
            print(f"Markdown格式验证过程中出现错误: {e}")
            return content  # 返回原始内容以确保稳定性
    
    def create_markdown_content(self, page_title, page_content, page_id=None, category=None):
        """创建适合RAG解析的标准Markdown格式内容（不包含YAML元数据）"""
        # 直接创建主标题，不包含元数据头部
        markdown_content = f"# {page_title}\n\n"
        
        if page_content:
            # 清理HTML标签并转换为适合RAG的Markdown格式
            clean_content = self.clean_html_content(page_content)
            # 验证并修正Markdown格式
            validated_content = self.validate_markdown_format(clean_content)
            # 添加内容结构化标记
            structured_content = self._add_content_structure(validated_content)
            markdown_content += structured_content
        else:
            markdown_content += "<!-- EMPTY_CONTENT -->\n\n*暂无内容*\n\n"
        
        # 添加文档结尾标记
        markdown_content += "\n\n<!-- DOCUMENT_END -->\n"
        
        return markdown_content
    
    def _add_content_structure(self, content):
        """为内容添加结构化标记，增强RAG理解能力"""
        if not content:
            return content
        
        try:
            lines = content.split('\n')
            structured_lines = []
            in_list = False
            in_code_block = False
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                
                # 检测代码块
                if stripped.startswith('```'):
                    in_code_block = not in_code_block
                    if in_code_block:
                        structured_lines.append("<!-- CODE_BLOCK_START -->")
                    else:
                        structured_lines.append("<!-- CODE_BLOCK_END -->")
                    structured_lines.append(line)
                    continue
                
                # 在代码块内，不做处理
                if in_code_block:
                    structured_lines.append(line)
                    continue
                
                # 检测段落开始
                if stripped and not stripped.startswith(('#', '-', '*', '1.', '2.', '3.', '>', '![', '[', '**解决方案**', '---')):
                    # 判断是否是新段落
                    prev_line = lines[i-1].strip() if i > 0 else ""
                    if not prev_line or prev_line.startswith(('#', '---', '<!-- ')):
                        structured_lines.append("<!-- PARAGRAPH_START -->")  #  段落开始
                
                # 检测列表
                if stripped.startswith(('-', '*')) or re.match(r'^\d+\.\s', stripped):
                    if not in_list:
                        structured_lines.append("<!-- LIST_START -->") # 列表开始
                        in_list = True
                elif in_list and stripped and not stripped.startswith(('-', '*')) and not re.match(r'^\d+\.\s', stripped):
                    structured_lines.append("<!-- LIST_END -->") # 列表结束
                    in_list = False
                
                # 检测问题解决类内容
                if '问题描述' in stripped or '解决方案' in stripped or '处理方案' in stripped:
                    structured_lines.append("<!-- QA_CONTENT -->") # 问题解决类内容
                
                structured_lines.append(line)
            
            # 结束未闭合的列表
            if in_list:
                structured_lines.append("<!-- LIST_END -->") # 列表结束
            
            return '\n'.join(structured_lines)
            
        except Exception as e:
            print(f"内容结构化处理错误: {e}")
            return content
    
    def save_page_to_file(self, page_id, page_title, page_content, directory, category=None):
        """将页面内容保存为适合RAG解析的Markdown文件"""
        os.makedirs(directory, exist_ok=True)
        
        clean_title = self.clean_filename(page_title)
        filename = f"{clean_title}.md"
        filepath = os.path.join(directory, filename)
        
        # 清理HTML内容并转换为Markdown
        clean_content = self.clean_html_content(page_content) if page_content else ""
        
        # 创建适合RAG的Markdown内容
        markdown_content = self.create_markdown_content(
            page_title, 
            page_content, 
            page_id=page_id, 
            category=category
        )
        
        # 收集文档信息用于生成合并MD文档
        self.collected_docs.append({
            'page_id': page_id,
            'page_title': page_title,
            'category': category or '根目录',
            'content': clean_content,
            'depth': len(category.split('/')) if category else 0  # 目录层级深度
        })
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"✅ 成功保存 {filename}")
            return True
        except Exception as e:
            print(f"❌ 保存失败 {filename}: {str(e)}")
            return False
    
    def get_page_content(self, page_id):
        """获取指定页面的详细内容"""
        payload = {'page_id': page_id}
        try:
            response = requests.post(self.url_page_info, data=payload)
            response.raise_for_status()
            page_data = response.json()

            if page_data.get('error_code') == 0:
                return page_data.get('data', {}).get('page_content', '')
            else:
                return ''
        except Exception as e:
            return ''

    def should_download_page(self, page_title):
        """判断是否应该下载该页面"""
        # 如果没有指定选择的标题，则下载所有页面
        if not self.selected_titles:
            return True
        # 如果指定了选择的标题，则只下载匹配的页面
        return page_title in self.selected_titles

    def extract_and_save_pages(self, pages, directory, current_count=0, category=None):
        """提取并保存页面内容，优化为RAG格式"""
        success_count = 0
        processed_count = 0

        # 过滤需要下载的页面
        pages_to_download = [page for page in pages if self.should_download_page(page['page_title'])]
        
        # 如果没有需要下载的页面，直接返回
        if not pages_to_download:
            return 0, 0

        for i, page in enumerate(pages_to_download):
            page_id = page['page_id']
            page_title = page['page_title']

            if self.progress_callback:
                # 修正进度计算，确保不会超过总数
                self.progress_callback(
                    current_count + i + 1,
                    current_count + len(pages_to_download),
                    f"正在处理: {page_title} (RAG格式)"
                )

            page_content = self.get_page_content(page_id)

            # 传递分类信息以便于生成元数据
            if self.save_page_to_file(page_id, page_title, page_content, directory, category):
                success_count += 1
                print(f"  ✓ [{category or '根目录'}] {page_title}")

            processed_count += 1

        return success_count, len(pages_to_download)

    def extract_and_save_catalogs(self, catalogs, directory, current_count=0, parent_category=""):
        """递归处理目录结构，优化为RAG格式"""
        total_success = 0
        total_count = 0
        processed_count = current_count

        for cat in catalogs:
            cat_name = cat['cat_name']
            # 构建完整的分类路径
            current_category = f"{parent_category}/{cat_name}" if parent_category else cat_name
            cat_directory = os.path.join(directory, self.clean_filename(cat_name))

            if 'pages' in cat and cat['pages']:
                success, count = self.extract_and_save_pages(
                    cat['pages'], cat_directory, processed_count, current_category
                )
                total_success += success
                total_count += count
                processed_count += count

            if 'catalogs' in cat and cat['catalogs']:
                sub_success, sub_count = self.extract_and_save_catalogs(
                    cat['catalogs'], cat_directory, processed_count, current_category
                )
                total_success += sub_success
                total_count += sub_count
                processed_count += sub_count

        # 只在顶层调用时（parent_category为空）更新进度总结
        # 移除递归调用中的进度回调，避免重复触发
        return total_success, total_count

    def get_available_pages(self):
        """获取所有可用的页面列表"""
        try:
            response_item = requests.post(self.url_item_info, data=self.params_item_info)
            response_item.raise_for_status()
            data_item = response_item.json()

            if data_item.get('error_code') != 0:
                return []

            pages = []

            # 获取根目录页面
            root_pages = data_item['data']['menu']['pages']
            for page in root_pages:
                pages.append({
                    'page_id': page['page_id'],
                    'page_title': page['page_title'],
                    'category': '根目录'
                })

            # 获取分类目录中的页面
            catalogs = data_item['data']['menu']['catalogs']
            pages.extend(self._extract_pages_from_catalogs(catalogs))

            return pages

        except Exception as e:
            return []

    def _extract_pages_from_catalogs(self, catalogs, parent_category=''):
        """从分类目录中提取页面信息"""
        pages = []

        for cat in catalogs:
            cat_name = cat['cat_name']
            current_category = f"{parent_category}/{cat_name}" if parent_category else cat_name

            # 添加当前分类下的页面
            if 'pages' in cat and cat['pages']:
                for page in cat['pages']:
                    pages.append({
                        'page_id': page['page_id'],
                        'page_title': page['page_title'],
                        'category': current_category
                    })

            # 递归处理子分类
            if 'catalogs' in cat and cat['catalogs']:
                pages.extend(self._extract_pages_from_catalogs(cat['catalogs'], current_category))

        return pages

    def crawl(self):
        """主爬取函数"""
        print("\n" + "="*60)
        print("开始爬取任务")
        print("="*60)
        
        if self.progress_callback:
            self.progress_callback(0, 100, "正在获取项目信息...")
        
        try:
            response_item = requests.post(self.url_item_info, data=self.params_item_info)
            response_item.raise_for_status()
            data_item = response_item.json()
            
            if data_item.get('error_code') != 0:
                raise Exception(f"获取项目信息失败: {data_item.get('error_message', '未知错误')}")
            
        except Exception as e:
            print(f"❌ 错误: {str(e)}")
            if self.progress_callback:
                self.progress_callback(0, 0, f"错误: {str(e)}")
            raise Exception(f"请求项目信息失败: {str(e)}")
        
        # 获取项目名称
        item_name_path = parse('$.data.item_name')
        item_name_matches = item_name_path.find(data_item)
        item_name = item_name_matches[0].value if item_name_matches else "未知项目"
        
        # 保存项目名称用于合并文档
        self.project_name = item_name
        # 清空之前收集的文档
        self.collected_docs = []
        
        print(f"📚 项目: {item_name}")
        print(f"📁 保存: {self.save_directory}")
        if self.selected_titles:
            print(f"🎯 模式: 选择性下载 ({len(self.selected_titles)}个页面)")
        else:
            print(f"🌐 模式: 全量下载")
        print("-" * 60)
        
        total_success = 0
        total_count = 0
        
        # 处理分类目录
        catalogs = data_item['data']['menu']['catalogs']
        if catalogs:
            print("\n📂 处理分类目录...")
            if self.progress_callback:
                self.progress_callback(0, 100, "正在处理分类目录... (RAG格式)")
            cat_success, cat_count = self.extract_and_save_catalogs(catalogs, self.save_directory)
            total_success += cat_success
            total_count += cat_count
            print(f"   → 分类目录: {cat_success}/{cat_count}")
        
        # 处理根目录页面
        pages = data_item['data']['menu']['pages']
        if pages:
            print("\n📄 处理根目录页面...")
            if self.progress_callback:
                self.progress_callback(total_count, total_count + len(pages), "正在处理根目录页面... (RAG格式)")
            page_success, page_count = self.extract_and_save_pages(pages, self.save_directory, total_count, "根目录")
            total_success += page_success
            total_count += page_count
            print(f"   → 根目录: {page_success}/{page_count}")
        
        print("\n" + "="*60)
        print(f"✅ 爬取完成! 成功: {total_success}/{total_count}")
        print(f"📂 保存路径: {self.save_directory}")
        print("="*60 + "\n")
        
        # 爬取完成后，生成合并的完整MD文档
        if total_count > 0:
            self.generate_merged_document()
        
        return total_success, total_count
    
    def generate_merged_document(self):
        """生成合并的完整MD文档，按目录层级组织标题和内容"""
        if not self.collected_docs:
            print("⚠️ 没有收集到任何文档，跳过合并")
            return
        
        print("\n" + "-"*60)
        print("📝 正在生成合并的完整MD文档...")
        
        # 按目录层级组织文档
        docs_by_category = {}
        for doc in self.collected_docs:
            category = doc['category']
            if category not in docs_by_category:
                docs_by_category[category] = []
            docs_by_category[category].append(doc)
        
        # 构建目录树结构
        category_tree = self._build_category_tree(docs_by_category)
        
        # 生成合并的Markdown内容
        merged_content = self._generate_merged_content(category_tree, docs_by_category)
        
        # 保存合并文档
        merged_filename = f"{self.clean_filename(self.project_name)}_完整文档.md"
        merged_filepath = os.path.join(self.save_directory, merged_filename)
        
        try:
            with open(merged_filepath, 'w', encoding='utf-8') as f:
                f.write(merged_content)
            print(f"✅ 合并文档已保存: {merged_filename}")
            print(f"   包含 {len(self.collected_docs)} 个页面")
        except Exception as e:
            print(f"❌ 保存合并文档失败: {str(e)}")
    
    def _build_category_tree(self, docs_by_category):
        """构建目录树结构"""
        tree = {'children': {}, 'docs': []}
        
        for category in docs_by_category.keys():
            if category == '根目录':
                tree['docs'] = docs_by_category[category]
            else:
                parts = category.split('/')
                current = tree
                for part in parts:
                    if part not in current['children']:
                        current['children'][part] = {'children': {}, 'docs': []}
                    current = current['children'][part]
                current['docs'] = docs_by_category[category]
        
        return tree
    
    def _generate_merged_content(self, tree, docs_by_category, depth=0):
        """递归生成合并的Markdown内容"""
        content_parts = []
        
        # 添加项目标题（仅在根层级）
        if depth == 0:
            content_parts.append(f"# {self.project_name}\n\n")
            # content_parts.append("> 本文档由爬虫自动生成，按目录层级组织内容\n\n")
            content_parts.append("---\n\n")
            
            # 生成目录
            content_parts.append("## 目录\n\n")
            toc = self._generate_toc(tree, 0)
            content_parts.append(toc)
            content_parts.append("\n---\n\n")
        
        # 处理根目录的文档（仅在根层级）
        if depth == 0 and tree.get('docs'):
            for doc in tree['docs']:
                # 根目录页面使用二级标题
                content_parts.append(f"## {doc['page_title']}\n\n")
                if doc['content']:
                    # 调整内容中的标题层级
                    adjusted_content = self._adjust_heading_levels(doc['content'], 2)
                    content_parts.append(adjusted_content)
                else:
                    content_parts.append("*暂无内容*\n")
                content_parts.append("\n\n---\n\n")
        
        # 递归处理子目录
        for cat_name, subtree in sorted(tree.get('children', {}).items()):
            # 目录标题级别: 一级目录##，二级目录###，以此类推
            heading_level = min(depth + 2, 6)  # 最大到h6
            heading_prefix = '#' * heading_level
            
            content_parts.append(f"{heading_prefix} {cat_name}\n\n")
            
            # 处理该目录下的文档
            for doc in subtree.get('docs', []):
                # 页面标题比目录标题低一级
                page_heading_level = min(heading_level + 1, 6)
                page_heading_prefix = '#' * page_heading_level
                
                content_parts.append(f"{page_heading_prefix} {doc['page_title']}\n\n")
                if doc['content']:
                    # 调整内容中的标题层级
                    adjusted_content = self._adjust_heading_levels(doc['content'], page_heading_level)
                    content_parts.append(adjusted_content)
                else:
                    content_parts.append("*暂无内容*\n")
                content_parts.append("\n\n")
            
            # 递归处理子目录
            if subtree.get('children'):
                sub_content = self._generate_merged_content(
                    subtree, docs_by_category, depth + 1
                )
                content_parts.append(sub_content)
        
        return ''.join(content_parts)
    
    def _generate_toc(self, tree, depth=0):
        """生成目录"""
        toc_parts = []
        indent = "  " * depth
        
        # 添加根目录文档
        if depth == 0 and tree.get('docs'):
            for doc in tree['docs']:
                toc_parts.append(f"- [{doc['page_title']}](#{self._generate_anchor(doc['page_title'])})\n")
        
        # 添加子目录和其文档
        for cat_name, subtree in sorted(tree.get('children', {}).items()):
            toc_parts.append(f"{indent}- **{cat_name}**\n")
            
            # 添加该目录下的文档
            for doc in subtree.get('docs', []):
                toc_parts.append(f"{indent}  - [{doc['page_title']}](#{self._generate_anchor(doc['page_title'])})\n")
            
            # 递归处理子目录
            if subtree.get('children'):
                sub_toc = self._generate_toc(subtree, depth + 1)
                toc_parts.append(sub_toc)
        
        return ''.join(toc_parts)
    
    def _generate_anchor(self, title):
        """生成Markdown键接（anchor）"""
        # 简单处理：转小写，空格转-，移除特殊字符
        anchor = title.lower()
        anchor = re.sub(r'[^\w\u4e00-\u9fff\s-]', '', anchor)
        anchor = re.sub(r'\s+', '-', anchor)
        return anchor
    
    def _adjust_heading_levels(self, content, base_level):
        """调整内容中的标题层级，避免层级冲突"""
        if not content:
            return content
        
        lines = content.split('\n')
        adjusted_lines = []
        
        for line in lines:
            stripped = line.strip()
            # 检测标题行（以#开头）
            if stripped.startswith('#'):
                # 计算原始标题级别
                match = re.match(r'^(#+)\s*(.*)$', stripped)
                if match:
                    original_level = len(match.group(1))
                    heading_text = match.group(2)
                    # 新标题级别 = 基础级别 + 原始级别，最大不超过6
                    new_level = min(base_level + original_level, 6)
                    adjusted_lines.append(f"{'#' * new_level} {heading_text}")
                    continue
            
            # 跳过语义标记注释
            if stripped.startswith('<!-- ') and stripped.endswith(' -->'):
                continue
            
            adjusted_lines.append(line)
        
        return '\n'.join(adjusted_lines)