import requests
from crawler import YunHuiHuangCrawler


class ShowDocCrawler(YunHuiHuangCrawler):
    """ShowDoc平台文档爬虫
    
    继承YunHuiHuangCrawler,适配ShowDoc API并复用Markdown处理逻辑
    """
    
    def __init__(self, item_id, user_token, keyword='', default_page_id='', 
                 save_directory=None, progress_callback=None, selected_titles=None):
        """初始化ShowDoc爬虫
        
        Args:
            item_id: 项目ID
            user_token: 用户认证令牌
            keyword: 关键词过滤
            default_page_id: 默认页面ID
            save_directory: 保存目录
            progress_callback: 进度回调函数
            selected_titles: 选择的页面标题列表
        """
        # 调用父类初始化
        super().__init__(
            item_id=item_id,
            keyword=keyword,
            default_page_id=default_page_id,
            save_directory=save_directory,
            progress_callback=progress_callback,
            selected_titles=selected_titles
        )
        
        # ShowDoc特有属性
        self.user_token = user_token
        self.base_url = "https://yunhelp.gmgrasp.com.cn/server/index.php"
        
        # 更新API URLs以适配ShowDoc
        self.url_item_info = f"{self.base_url}?s=/api/item/info"
        self.url_page_info = f"{self.base_url}?s=/api/page/info"
    
    def fetch_item_info(self):
        """获取项目信息(带认证)
        
        Returns:
            dict: 项目信息数据,如果失败返回None
        """
        try:
            data = {
                's': '/api/item/info',
                'item_id': self.item_id,
                'user_token': self.user_token,
                'keyword': self.keyword,
                'default_page_id': self.default_page_id
            }
            
            response = requests.post(self.url_item_info, data=data, timeout=15)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('error_code') == 0:
                return result
            else:
                error_msg = result.get('error_message', '未知错误')
                print(f"❌ 获取项目信息失败: {error_msg}")
                return None
                
        except Exception as e:
            print(f"❌ 请求项目信息异常: {str(e)}")
            return None
    
    def get_page_content(self, page_id):
        """获取指定页面的详细内容(带认证)
        
        Args:
            page_id: 页面ID
            
        Returns:
            str: 页面HTML内容
        """
        try:
            data = {
                's': '/api/page/info',
                'page_id': page_id,
                'user_token': self.user_token
            }
            
            response = requests.post(self.url_page_info, data=data, timeout=15)
            response.raise_for_status()
            
            page_data = response.json()

            if page_data.get('error_code') == 0:
                return page_data.get('data', {}).get('page_content', '')
            else:
                error_msg = page_data.get('error_message', '未知错误')
                print(f"⚠️ 获取页面内容失败 (page_id={page_id}): {error_msg}")
                return ''
                
        except Exception as e:
            print(f"⚠️ 请求页面内容异常 (page_id={page_id}): {str(e)}")
            return ''
    
    def crawl(self):
        """主爬取函数(重写以适配ShowDoc)
        
        Returns:
            tuple: (成功数量, 总数量)
        """
        print("\n" + "="*60)
        print("开始ShowDoc爬取任务")
        print("="*60)
        
        if self.progress_callback:
            self.progress_callback(0, 100, "正在获取ShowDoc项目信息...")
        
        try:
            # 获取项目信息
            data_item = self.fetch_item_info()
            
            if not data_item:
                raise Exception("获取项目信息失败")
            
            if data_item.get('error_code') != 0:
                error_msg = data_item.get('error_message', '未知错误')
                raise Exception(f"获取项目信息失败: {error_msg}")
            
        except Exception as e:
            print(f"❌ {str(e)}")
            if self.progress_callback:
                self.progress_callback(0, 0, f"错误: {str(e)}")
            return 0, 0
        
        # 获取项目名称
        from jsonpath_ng import parse
        item_name_path = parse('$.data.item_name')
        item_name_matches = item_name_path.find(data_item)
        item_name = item_name_matches[0].value if item_name_matches else "未知项目"
        
        # 保存项目名称用于合并文档
        self.project_name = item_name
        # 清空之前收集的文档
        self.collected_docs = []
        
        print(f"📚 开始爬取项目: {item_name}")
        print(f"📁 保存目录: {self.save_directory}")
        if self.selected_titles:
            print(f"🎯 选择性下载: {len(self.selected_titles)} 个页面")
        else:
            print(f"🌐 全量下载模式")
        print("-" * 60)
        
        total_success = 0
        total_count = 0
        
        # 处理分类目录
        catalogs = data_item['data']['menu']['catalogs']
        if catalogs:
            print("\n📂 处理分类目录...")
            if self.progress_callback:
                self.progress_callback(0, 100, "正在处理分类目录... (优化为RAG格式)")
            cat_success, cat_count = self.extract_and_save_catalogs(
                catalogs, self.save_directory
            )
            total_success += cat_success
            total_count += cat_count
            print(f"   ✓ 分类目录: {cat_success}/{cat_count} 个页面")
        
        # 处理根目录页面
        pages = data_item['data']['menu']['pages']
        if pages:
            print("\n📄 处理根目录页面...")
            if self.progress_callback:
                self.progress_callback(
                    total_count, 
                    total_count + len(pages), 
                    "正在处理根目录页面... (优化为RAG格式)"
                )
            page_success, page_count = self.extract_and_save_pages(
                pages, self.save_directory, total_count, "根目录"
            )
            total_success += page_success
            total_count += page_count
            print(f"   ✓ 根目录: {page_success}/{page_count} 个页面")
        
        print("\n" + "="*60)
        print(f"✅ 处理完成!")
        print(f"   成功: {total_success}/{total_count} 个页面")
        print(f"   保存路径: {self.save_directory}")
        print("="*60 + "\n")
        
        # 爬取完成后，生成合并的完整MD文档
        if total_count > 0:
            self.generate_merged_document()
        
        # 确保返回正确的结果
        return total_success, total_count
    
    def get_available_pages(self):
        """获取所有可用的页面列表
        
        Returns:
            list: 页面列表,每个元素包含page_id, page_title, category
        """
        try:
            data_item = self.fetch_item_info()
            
            if not data_item or data_item.get('error_code') != 0:
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
            print(f"❌ 获取页面列表失败: {str(e)}")
            return []


# 测试代码
if __name__ == '__main__':
    from showdoc_auth import ShowDocAuthenticator
    
    print("=" * 60)
    print("ShowDoc爬虫模块测试")
    print("=" * 60)
    
    # 先登录
    auth = ShowDocAuthenticator()
    token = auth.login()
    
    if not token:
        print("❌ 登录失败,无法测试爬虫")
        exit(1)
    
    # 获取项目列表
    from showdoc_project import ShowDocProjectManager
    manager = ShowDocProjectManager()
    projects = manager.get_project_list(token)
    
    if not projects:
        print("❌ 未获取到任何项目")
        exit(1)
    
    # 选择第一个项目进行测试
    test_project = projects[0]
    print(f"\n📚 测试项目: {test_project['item_name']} (ID: {test_project['item_id']})")
    
    # 创建爬虫实例
    crawler = ShowDocCrawler(
        item_id=test_project['item_id'],
        user_token=token,
        save_directory=f"./downloads/test_showdoc_{test_project['item_id']}"
    )
    
    # 测试获取页面列表
    pages = crawler.get_available_pages()
    print(f"\n📄 项目包含 {len(pages)} 个页面")
    
    if pages:
        print("\n前5个页面:")
        for i, page in enumerate(pages[:5], 1):
            print(f"  {i}. [{page['category']}] {page['page_title']}")
        
        # 测试爬取功能(只爬取前2个页面)
        if len(pages) >= 2:
            crawler.selected_titles = [pages[0]['page_title'], pages[1]['page_title']]
            print(f"\n🚀 开始爬取测试 (只爬取前2个页面)...")
            success, total = crawler.crawl()
            print(f"\n✅ 测试完成: {success}/{total} 个页面成功")
