import requests
from jsonpath_ng import parse
import time


class ShowDocProjectManager:
    """ShowDoc项目管理模块
    
    负责获取项目列表、项目信息查询和数据缓存
    """
    
    def __init__(self, base_url='https://yunhelp.gmgrasp.com.cn/server/index.php'):
        self.base_url = base_url
        self.projects_cache = []
        self.cache_timestamp = None
        self.cache_duration = 300  # 缓存有效期5分钟
    
    def get_project_list(self, user_token, group_id=0):
        """获取项目列表
        
        Args:
            user_token: 用户认证令牌
            group_id: 项目分组ID,默认0表示所有项目
            
        Returns:
            list: 项目列表,每个项目包含item_id和item_name
                 格式: [{'item_id': 'xxx', 'item_name': 'xxx'}, ...]
                 如果失败返回空列表
        """
        try:
            url = f"{self.base_url}?s=/api/item/myList"
            data = {
                's': '/api/item/myList',
                'user_token': user_token,
                'item_group_id': group_id
            }
            
            print(f"📋 正在获取项目列表 (group_id={group_id})...")
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            # 检查响应是否成功
            if result.get('error_code') != 0:
                error_msg = result.get('error_message', '未知错误')
                print(f"❌ 获取项目列表失败: {error_msg}")
                return []
            
            # 使用JSONPath提取项目ID和名称
            id_expr = parse('$.data[*].item_id')
            name_expr = parse('$.data[*].item_name')
            
            item_ids = [match.value for match in id_expr.find(result)]
            item_names = [match.value for match in name_expr.find(result)]
            
            # 组合成项目列表
            projects = []
            for item_id, item_name in zip(item_ids, item_names):
                projects.append({
                    'item_id': str(item_id),
                    'item_name': item_name
                })
            
            print(f"✅ 成功获取 {len(projects)} 个项目")
            
            # 更新缓存
            self.cache_projects(projects)
            
            return projects
            
        except Exception as e:
            print(f"❌ 获取项目列表异常: {str(e)}")
            return []
    
    def get_project_info(self, item_id, user_token, keyword='', default_page_id=''):
        """获取项目详细信息
        
        Args:
            item_id: 项目ID
            user_token: 用户认证令牌
            keyword: 关键词过滤
            default_page_id: 默认页面ID
            
        Returns:
            dict: 项目详细信息,如果失败返回None
        """
        try:
            url = f"{self.base_url}?s=/api/item/info"
            data = {
                's': '/api/item/info',
                'item_id': item_id,
                'user_token': user_token,
                'keyword': keyword,
                'default_page_id': default_page_id
            }
            
            print(f"📖 正在获取项目详情 (item_id={item_id})...")
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            # 检查响应是否成功
            if result.get('error_code') != 0:
                error_msg = result.get('error_message', '未知错误')
                print(f"❌ 获取项目详情失败: {error_msg}")
                return None
            
            project_data = result.get('data', {})
            print(f"✅ 成功获取项目详情: {project_data.get('item_name', 'Unknown')}")
            
            return project_data
            
        except Exception as e:
            print(f"❌ 获取项目详情异常: {str(e)}")
            return None
    
    def cache_projects(self, projects):
        """缓存项目数据
        
        Args:
            projects: 项目列表
        """
        self.projects_cache = projects
        self.cache_timestamp = time.time()
        print(f"💾 项目列表已缓存 ({len(projects)} 个项目)")
    
    def get_cached_projects(self):
        """获取缓存的项目列表
        
        Returns:
            list: 缓存的项目列表,如果缓存过期或为空返回None
        """
        if not self.projects_cache:
            print("⚠️ 项目缓存为空")
            return None
        
        # 检查缓存是否过期
        if self.cache_timestamp:
            elapsed = time.time() - self.cache_timestamp
            if elapsed > self.cache_duration:
                print(f"⚠️ 项目缓存已过期 (已过 {int(elapsed)} 秒)")
                return None
        
        print(f"✅ 使用缓存的项目列表 ({len(self.projects_cache)} 个项目)")
        return self.projects_cache
    
    def search_projects(self, keyword):
        """在缓存中搜索项目
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            list: 匹配的项目列表
        """
        if not self.projects_cache:
            print("⚠️ 项目缓存为空,无法搜索")
            return []
        
        keyword_lower = keyword.lower()
        matched = []
        
        for project in self.projects_cache:
            item_name = project.get('item_name', '').lower()
            item_id = str(project.get('item_id', '')).lower()
            
            if keyword_lower in item_name or keyword_lower in item_id:
                matched.append(project)
        
        print(f"🔍 搜索 '{keyword}' 找到 {len(matched)} 个匹配项目")
        return matched
    
    def get_project_by_id(self, item_id):
        """根据ID在缓存中查找项目
        
        Args:
            item_id: 项目ID
            
        Returns:
            dict: 项目信息,如果未找到返回None
        """
        if not self.projects_cache:
            return None
        
        for project in self.projects_cache:
            if str(project.get('item_id')) == str(item_id):
                return project
        
        return None
    
    def clear_cache(self):
        """清除项目缓存"""
        self.projects_cache = []
        self.cache_timestamp = None
        print("🗑️ 项目缓存已清除")


# 测试代码
if __name__ == '__main__':
    from showdoc_auth import ShowDocAuthenticator
    
    print("=" * 60)
    print("ShowDoc项目管理模块测试")
    print("=" * 60)
    
    # 先登录获取token
    auth = ShowDocAuthenticator()
    token = auth.login()
    
    if not token:
        print("❌ 登录失败,无法测试项目管理模块")
        exit(1)
    
    # 测试项目管理功能
    manager = ShowDocProjectManager()
    
    # 获取项目列表
    projects = manager.get_project_list(token)
    
    if projects:
        print(f"\n📋 项目列表:")
        for i, project in enumerate(projects[:5], 1):  # 只显示前5个
            print(f"  {i}. ID: {project['item_id']}, 名称: {project['item_name']}")
        
        if len(projects) > 5:
            print(f"  ... 还有 {len(projects) - 5} 个项目")
        
        # 测试搜索功能
        if projects:
            first_project = projects[0]
            search_keyword = first_project['item_name'][:3]
            print(f"\n🔍 搜索测试 (关键词: '{search_keyword}'):")
            matched = manager.search_projects(search_keyword)
            print(f"  找到 {len(matched)} 个匹配项目")
        
        # 测试获取项目详情
        if projects:
            test_item_id = projects[0]['item_id']
            print(f"\n📖 获取项目详情测试 (item_id: {test_item_id}):")
            info = manager.get_project_info(test_item_id, token)
            if info:
                print(f"  项目名: {info.get('item_name', 'N/A')}")
                print(f"  项目类型: {info.get('item_type', 'N/A')}")
    else:
        print("\n❌ 未获取到任何项目")
