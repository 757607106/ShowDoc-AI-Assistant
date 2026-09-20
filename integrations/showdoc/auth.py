import requests
import base64
import time
import re
from jsonpath_ng import parse
import tempfile
import os
import dashscope
from dashscope import MultiModalConversation


class ShowDocAuthenticator:
    """ShowDoc平台认证模块
    
    负责处理验证码获取、大模型识别和用户登录流程
    """
    
    def __init__(self, base_url='https://yunhelp.gmgrasp.com.cn/server/index.php',
                 qwen_api_key=None):
        self.base_url = base_url
        self.user_token = None
        self.token_timestamp = None
        
        # 千问大模型配置 - 优先使用DASHSCOPE_API_KEY环境变量
        self.qwen_api_key = qwen_api_key or os.getenv('DASHSCOPE_API_KEY', '') or os.getenv('QWEN_API_KEY', '')
        self.qwen_api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        
        # 登录凭证只能通过环境变量配置，避免将账号密码提交到仓库
        self.username = os.getenv('SHOWDOC_USERNAME', '')
        self.password = os.getenv('SHOWDOC_PASSWORD', '')
    
    def create_captcha(self):
        """步骤1: 创建验证码并获取captcha_id
        
        Returns:
            str: captcha_id,如果失败返回None
        """
        try:
            url = f"{self.base_url}?s=/api/common/createCaptcha"
            data = {'s': '/api/common/createCaptcha'}
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            # 使用JSONPath提取captcha_id
            jsonpath_expr = parse('$.data.captcha_id')
            matches = jsonpath_expr.find(result)
            
            if matches:
                captcha_id = matches[0].value
                print(f"✅ 成功获取验证码ID: {captcha_id}")
                return captcha_id
            else:
                print(f"❌ 未能从响应中提取captcha_id: {result}")
                return None
                
        except Exception as e:
            print(f"❌ 创建验证码失败: {str(e)}")
            return None
    
    def get_captcha_image(self, captcha_id):
        """步骤2: 获取验证码图片
        
        Args:
            captcha_id: 验证码ID
            
        Returns:
            bytes: 图片二进制数据,如果失败返回None
        """
        try:
            timestamp = int(time.time() * 1000)
            url = f"{self.base_url}?s=/api/common/showCaptcha&captcha_id={captcha_id}&{timestamp}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            if response.content:
                print(f"✅ 成功获取验证码图片 (大小: {len(response.content)} bytes)")
                return response.content
            else:
                print("❌ 验证码图片为空")
                return None
                
        except Exception as e:
            print(f"❌ 获取验证码图片失败: {str(e)}")
            return None
    
    def recognize_captcha(self, image_data):
        """步骤3: 使用千问大模型识别验证码
        
        Args:
            image_data: 图片二进制数据
            
        Returns:
            str: 识别出的验证码数字,如果失败返回None
        """
        try:
            # 将图片数据转换为base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # 使用DashScope SDK调用千问视觉模型
            # 从环境变量获取API密钥
            api_key = os.getenv('DASHSCOPE_API_KEY') or self.qwen_api_key
            
            if not api_key or api_key == 'sk-your-qwen-api-key-here':
                print("❌ 未配置有效的DASHSCOPE_API_KEY或QWEN_API_KEY")
                return None
            
            print("🔍 正在调用千问大模型识别验证码...")
            
            # 使用MultiModalConversation进行图片识别
            response = MultiModalConversation.call(
                model='qwen-vl-max',
                api_key=api_key,
                messages=[
                    {
                        'role': 'user',
                        'content': [
                            {
                                'image': f'data:image/png;base64,{image_base64}'
                            },
                            {
                                'text': '这是一个验证码图片,验证码由字母和数字混合组成(可能含大小写字母)。请识别图片中的所有字符,按从左到右的顺序直接返回完整的验证码字符串,不要有任何解释、空格或标点符号。'
                            }
                        ]
                    }
                ]
            )
            
            # 从响应中提取结果
            status_code = getattr(response, 'status_code', None)
            if status_code != 200:
                error_code = getattr(response, 'code', '') or '未知错误码'
                error_message = getattr(response, 'message', '') or '未知错误'
                print(f"❌ 千问API调用失败 [{status_code} {error_code}]: {error_message}")
                return None

            if hasattr(response, 'output') and response.output and 'choices' in response.output:
                choices = response.output['choices']
                if choices and len(choices) > 0:
                    content = choices[0]['message']['content']
                    
                    # 提取纯数字
                    if isinstance(content, list):
                        text_content = ""
                        for item in content:
                            if isinstance(item, dict) and "text" in item:
                                text_content += item["text"]
                        content = text_content
                    
                    # 验证码为字母+数字混合,提取字母与数字组成的完整序列
                    # 去除空白、标点等干扰字符,保留字母和数字
                    tokens = re.findall(r'[A-Za-z0-9]+', str(content))
                    
                    if tokens:
                        # 取最长的连续字母数字序列作为验证码
                        captcha = max(tokens, key=len)
                        print(f"✅ 千问识别成功,验证码: {captcha}")
                        print(f"   原始响应: {content}")
                        return captcha
                    else:
                        print(f"⚠️ 千问响应中未找到有效字符,原始内容: {content}")
                        return None
            
            print(f"❌ 千问API响应格式异常: {response}")
            return None
            
        except Exception as e:
            print(f"❌ 千问识别失败: {str(e)}")
            return None
    
    def login(self, username=None, password=None, max_retries=3):
        """步骤4: 执行完整登录流程
        
        Args:
            username: 用户名,默认使用类属性
            password: 密码,默认使用类属性
            max_retries: 最大重试次数
            
        Returns:
            str: user_token,如果失败返回None
        """
        username = username or self.username
        password = password or self.password

        if not username or not password:
            print("❌ 未配置SHOWDOC_USERNAME或SHOWDOC_PASSWORD环境变量")
            return None
        
        for attempt in range(max_retries):
            try:
                print(f"\n🔐 开始登录流程 (尝试 {attempt + 1}/{max_retries})...")
                
                # 步骤1: 创建验证码
                captcha_id = self.create_captcha()
                if not captcha_id:
                    print("⚠️ 验证码ID获取失败,重试...")
                    continue
                
                # 步骤2: 获取验证码图片
                image_data = self.get_captcha_image(captcha_id)
                if not image_data:
                    print("⚠️ 验证码图片获取失败,重试...")
                    continue
                
                # 步骤3: 千问大模型识别验证码
                captcha = self.recognize_captcha(image_data)
                if not captcha:
                    print("⚠️ 验证码识别失败,重试...")
                    continue
                
                # 步骤4: 执行登录
                url = f"{self.base_url}?s=/api/user/loginByVerify"
                data = {
                    's': '/api/user/loginByVerify',
                    'username': username,
                    'password': password,
                    'captcha': captcha,
                    'captcha_id': captcha_id,
                    'redirect_login': 'false'
                }
                
                print(f"🔑 正在提交登录请求...")
                response = requests.post(url, data=data, timeout=10)
                response.raise_for_status()
                
                result = response.json()
                
                # 检查登录是否成功
                if result.get('error_code') == 0:
                    # 使用JSONPath提取user_token
                    jsonpath_expr = parse('$.data.user_token')
                    matches = jsonpath_expr.find(result)
                    
                    if matches:
                        self.user_token = matches[0].value
                        self.token_timestamp = time.time()
                        print(f"✅ 登录成功! Token: {self.user_token[:20]}...")
                        return self.user_token
                    else:
                        print(f"❌ 响应中未找到user_token: {result}")
                else:
                    error_msg = result.get('error_message', '未知错误')
                    print(f"❌ 登录失败: {error_msg}")
                    
                    # 如果是验证码错误,重试;其他错误直接返回
                    if '验证码' not in error_msg:
                        return None
                
            except Exception as e:
                print(f"❌ 登录过程异常: {str(e)}")
        
        print(f"❌ 登录失败,已重试{max_retries}次")
        return None
    
    def get_token(self):
        """获取当前有效的token
        
        Returns:
            str: user_token,如果未登录或token失效返回None
        """
        if not self.user_token:
            print("⚠️ 尚未登录,请先调用login()方法")
            return None
        
        # 检查token是否过期(假设有效期为2小时)
        if self.token_timestamp:
            elapsed = time.time() - self.token_timestamp
            if elapsed > 7200:  # 2小时
                print("⚠️ Token已过期,请重新登录")
                self.user_token = None
                self.token_timestamp = None
                return None
        
        return self.user_token
    
    def is_token_valid(self):
        """检查token是否有效
        
        Returns:
            bool: Token是否有效
        """
        return self.get_token() is not None
    
    def auto_login_if_needed(self):
        """如果token无效,自动重新登录
        
        Returns:
            str: 有效的user_token,如果登录失败返回None
        """
        token = self.get_token()
        if token:
            return token
        
        print("🔄 Token无效或已过期,尝试自动登录...")
        return self.login()


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("ShowDoc认证模块测试")
    print("=" * 60)
    
    auth = ShowDocAuthenticator()
    token = auth.login()
    
    if token:
        print(f"\n✅ 测试成功! 获取到Token: {token}")
        print(f"Token有效性: {auth.is_token_valid()}")
    else:
        print("\n❌ 测试失败,未能获取Token")
