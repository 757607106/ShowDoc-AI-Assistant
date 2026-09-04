import urllib.request
import urllib.parse
import urllib.error
import json
import ssl
import os
import re
import base64
from html.parser import HTMLParser
from collections import OrderedDict

from dotenv import load_dotenv


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

CYB_API_BASE_URL = os.getenv(
    "CYB_API_BASE_URL", "https://new.yuncyb.com/aicyberp-api"
).rstrip("/")
DASHSCOPE_API_URL = os.getenv(
    "DASHSCOPE_API_URL",
    "https://dashscope.aliyuncs.com/api/v1/services/aigc/"
    "multimodal-generation/generation",
)


class HTMLToMarkdown(HTMLParser):
    """
    一个轻量级且不依赖第三方库的 HTML 转 Markdown 解析器。
    能够正确提取段落、标题、加粗以及图片，并处理它们之间的排版间距。
    """

    def __init__(self):
        super().__init__()
        self.result = []
        self.list_stack = []
        self.list_index = 1

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            # 合并为一个文件时，把内容中的 h1~h6 降两级，作为四级及以下标题
            level = int(tag[1]) + 2
            if level > 6:
                level = 6
            self.result.append(f'\n\n{"#" * level} ')
        elif tag == 'p':
            self.result.append('\n\n')
        elif tag == 'br':
            self.result.append('\n')
        elif tag == 'img':
            src = attrs_dict.get('src', '')
            alt = attrs_dict.get('alt', '图片')
            if src.startswith('data:'):
                self.result.append(f'\n\n<!-- [Base64 图片已过滤] -->\n\n')
            else:
                self.result.append(f'\n\n![{alt}]({src})\n\n')
        elif tag in ['strong', 'b']:
            self.result.append(' **')
        elif tag in ['em', 'i']:
            self.result.append(' *')
        elif tag == 'ul':
            self.list_stack.append('ul')
            self.result.append('\n')
        elif tag == 'ol':
            self.list_stack.append('ol')
            self.list_index = 1
            self.result.append('\n')
        elif tag == 'li':
            if self.list_stack and self.list_stack[-1] == 'ol':
                self.result.append(f'\n{self.list_index}. ')
                self.list_index += 1
            else:
                self.result.append('\n- ')

    def handle_endtag(self, tag):
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.result.append('\n\n')
        elif tag == 'p':
            self.result.append('\n\n')
        elif tag in ['strong', 'b']:
            self.result.append('** ')
        elif tag in ['em', 'i']:
            self.result.append('* ')
        elif tag in ['ul', 'ol']:
            if self.list_stack:
                self.list_stack.pop()
            self.result.append('\n')

    def handle_data(self, data):
        self.result.append(data)

    def get_markdown(self):
        content = ''.join(self.result)
        content = re.sub(r'\n{3,}', '\n\n', content)

        lines = [line.rstrip() for line in content.split('\n')]
        formatted_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('![') or stripped.startswith('<!--'):
                if formatted_lines and formatted_lines[-1] != '':
                    formatted_lines.append('')
                formatted_lines.append(line)
                formatted_lines.append('')
            else:
                formatted_lines.append(line)

        final_content = '\n'.join(formatted_lines)
        final_content = re.sub(r'\n{3,}', '\n\n', final_content)
        return final_content.strip()


def clean_filename(filename):
    """
    过滤文件名及锚点链接中的非法字符
    """
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.strip()
    return filename


def slugify(text):
    """
    生成标准 Markdown 目录跳转锚点
    """
    anchor = text.lower().strip()
    anchor = re.sub(r'\s+', '-', anchor)
    anchor = re.sub(r'[^\w\s\u4e00-\u9fff\-]', '', anchor)
    return anchor


def convert_html_to_markdown(html_content, title):
    """
    将 HTML 内容转换为 Markdown，并去除开头可能重复的标题
    """
    if not html_content:
        return ""

    # 去除首部重复的大标题
    pattern = rf'^\s*<h1[^>]*>\s*{re.escape(title)}\s*</h1>'
    cleaned_html = re.sub(pattern, '', html_content, flags=re.IGNORECASE)

    if cleaned_html == html_content:
        cleaned_html = re.sub(r'^\s*<h1[^>]*>.*?</h1>', '', html_content, flags=re.IGNORECASE)

    parser = HTMLToMarkdown()
    parser.feed(cleaned_html)
    return parser.get_markdown()


# FAQ 类型映射表（将 ID 转换为清晰的 ERP 模块分类）
FAQ_TYPE_MAPPING = {
    "1": "基础与系统",
    "2": "采购业务",
    "3": "销售业务",
    "4": "库存业务",
    "5": "财务与账务",
    "6": "打印设置",
    "7": "系统设置"
}


class LoginRejectedError(RuntimeError):
    """账号、密码或登录响应导致的不可重试错误。"""


class CYBAuthenticator:
    """通过验证码和手机号登录云创业版并获取访问 token。"""

    def __init__(self, phone=None, password=None, ctx=None):
        self.phone = phone or os.getenv("CYB_PHONE", "")
        self.password = password or os.getenv("CYB_PASSWORD", "")
        self.qwen_api_key = (
            os.getenv("DASHSCOPE_API_KEY", "")
            or os.getenv("QWEN_API_KEY", "")
        )
        self.vl_model = os.getenv("CYB_VL_MODEL", "qwen-vl-max")
        self.ctx = ctx or ssl.create_default_context()

    def _request_json(self, url, method="GET", payload=None, headers=None, timeout=30):
        request_headers = {"Accept": "application/json", **(headers or {})}
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")

        req = urllib.request.Request(
            url,
            data=body,
            headers=request_headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, context=self.ctx, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {error_body[:300]}") from exc

    def get_captcha(self):
        """获取同一次登录必须配套使用的 captchaKey 和 captchaImage。"""
        result = self._request_json(f"{CYB_API_BASE_URL}/auth/captcha")
        if result.get("code") != "A00000":
            raise RuntimeError(
                f"获取验证码失败[{result.get('code')}]: {result.get('message')}"
            )

        data = result.get("data") or {}
        captcha_key = data.get("captchaKey")
        captcha_image = data.get("captchaImage")
        if not captcha_key or not captcha_image:
            raise RuntimeError("验证码接口缺少 captchaKey 或 captchaImage")
        return captcha_key, captcha_image

    @staticmethod
    def _extract_vl_text(result):
        try:
            content = result["output"]["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            message = result.get("message") or "响应结构不符合预期"
            raise RuntimeError(f"VL 模型调用失败: {message}") from exc

        if isinstance(content, list):
            return "".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict)
            ).strip()
        return str(content).strip()

    def recognize_captcha(self, captcha_image):
        """把 captchaImage 交给千问 VL，并返回验证码字符。"""
        if not self.qwen_api_key:
            raise RuntimeError(
                "未配置 DASHSCOPE_API_KEY（也可使用 QWEN_API_KEY）"
            )

        if not captcha_image.startswith("data:image/"):
            try:
                base64.b64decode(captcha_image, validate=True)
            except (ValueError, TypeError) as exc:
                raise RuntimeError("captchaImage 不是有效的图片 Data URL/Base64") from exc
            captcha_image = f"data:image/png;base64,{captcha_image}"

        payload = {
            "model": self.vl_model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": captcha_image},
                            {
                                "text": (
                                    "识别图片中的验证码主字符，忽略彩色干扰线。"
                                    "验证码由4到6个英文字母或数字组成。"
                                    "只返回验证码本身，不要解释、空格、标点或代码块。"
                                )
                            },
                        ],
                    }
                ]
            },
            "parameters": {"result_format": "message"},
        }
        result = self._request_json(
            DASHSCOPE_API_URL,
            method="POST",
            payload=payload,
            headers={"Authorization": f"Bearer {self.qwen_api_key}"},
            timeout=45,
        )
        raw_text = self._extract_vl_text(result)

        exact = re.fullmatch(r"[A-Za-z0-9]{4,6}", raw_text)
        if exact:
            return exact.group(0)

        candidates = re.findall(
            r"(?<![A-Za-z0-9])[A-Za-z0-9]{4,6}(?![A-Za-z0-9])",
            raw_text,
        )
        if candidates:
            # 解释性回复里可能出现 “code”等单词；优先选择包含数字、且靠后的片段。
            return max(
                enumerate(candidates),
                key=lambda item: (any(char.isdigit() for char in item[1]), item[0]),
            )[1]
        raise RuntimeError(f"VL 返回内容中没有有效验证码: {raw_text[:100]!r}")

    def login(self, max_retries=3):
        """自动刷新验证码并重试登录，成功时返回不带 Bearer 前缀的 token。"""
        if not self.phone or not self.password:
            raise RuntimeError("请在 .env 中配置 CYB_PHONE 和 CYB_PASSWORD")
        if not self.qwen_api_key:
            raise RuntimeError(
                "请在 .env 中配置 DASHSCOPE_API_KEY（或 QWEN_API_KEY）"
            )
        if max_retries < 1:
            raise ValueError("max_retries 必须大于等于 1")

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                print(f"🔐 正在自动登录 (尝试 {attempt}/{max_retries})...")
                captcha_key, captcha_image = self.get_captcha()
                captcha_code = self.recognize_captcha(captcha_image)
                result = self._request_json(
                    f"{CYB_API_BASE_URL}/auth/phone/login",
                    method="POST",
                    payload={
                        "phone": self.phone,
                        "password": self.password,
                        "captchaKey": captcha_key,
                        "captchaCode": captcha_code,
                    },
                )

                if result.get("code") == "A00000":
                    data = result.get("data") or {}
                    login_result = data.get("loginResult") or {}
                    token = login_result.get("token")
                    if token:
                        print("✅ 自动登录成功，已获取最新 token")
                        return token
                    response_type = data.get("responseType", "未知")
                    raise LoginRejectedError(
                        f"登录响应未包含 token，responseType={response_type}"
                    )

                message = result.get("message") or "未知错误"
                last_error = RuntimeError(
                    f"登录失败[{result.get('code')}]: {message}"
                )
                if "验证码" not in message:
                    raise LoginRejectedError(str(last_error))
                if attempt < max_retries:
                    print(f"⚠️ {message}，正在刷新验证码后重试")
            except LoginRejectedError:
                raise
            except (OSError, ValueError, RuntimeError) as exc:
                last_error = exc
                if attempt < max_retries:
                    print(f"⚠️ {exc}，正在刷新验证码后重试")

        raise RuntimeError(f"自动登录失败: {last_error}")


def request_api(url, headers, ctx):
    """发送 HTTP GET 请求获取 API 数据"""
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ctx) as response:
        status = response.getcode()
        if status != 200:
            print(f"❌ 接口请求失败，状态码: {status}")
            return None
        res_data = response.read().decode('utf-8')
        json_data = json.loads(res_data)
        if json_data.get("code") != "A00000":
            print(f"❌ 接口返回错误: {json_data.get('message')}")
            return None
        return json_data.get("data", [])


def crawl_and_process():
    # 基础保存目录
    base_save_dir = os.path.join(SCRIPT_DIR, "downloads")
    os.makedirs(base_save_dir, exist_ok=True)

    # SSL 忽略
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # 每次运行都通过验证码和手机号登录，避免依赖会过期的硬编码 token。
    token = CYBAuthenticator(ctx=ctx).login()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    url_tutorials = f"{CYB_API_BASE_URL}/tutorials"
    url_faqs = f"{CYB_API_BASE_URL}/faqs"

    # 1. 爬取使用教程 (Tutorials)
    print("🚀 开始爬取使用教程...")
    tutorial_raw = request_api(url_tutorials, headers, ctx)
    tutorial_groups = OrderedDict()

    if tutorial_raw:
        print(f"📦 成功获取到 {len(tutorial_raw)} 条使用教程。")
        for index, item in enumerate(tutorial_raw, 1):
            title = item.get("title", f"未命名教程_{index}").strip()
            category = item.get("category", "使用教程").strip()
            cover_image = item.get("coverImage", "")
            html_content = item.get("content", "")
            update_time = item.get('updateTime', '未知')

            if category not in tutorial_groups:
                tutorial_groups[category] = []

            markdown_body = convert_html_to_markdown(html_content, title)

            tutorial_data = {
                "title": title,
                "update_time": update_time,
                "content": markdown_body
            }
            tutorial_groups[category].append(tutorial_data)

            # 单篇保存到 data/教程/分类/标题.md
            save_dir = os.path.join(base_save_dir, "教程", clean_filename(category))
            os.makedirs(save_dir, exist_ok=True)
            file_path = os.path.join(save_dir, clean_filename(title) + ".md")

            single_md = [
                f"# {title}\n",
                f"- **分类**: {category}",
                f"- **更新时间**: {update_time}\n",
                "---\n",
                markdown_body
            ]

            with open(file_path, "w", encoding="utf-8") as sf:
                sf.write("\n".join(single_md))

    # 2. 爬取常见问题 (FAQs)
    print("\n🚀 开始爬取常见问题 (FAQ)...")
    faq_raw = request_api(url_faqs, headers, ctx)
    faq_groups = OrderedDict()

    if faq_raw:
        print(f"📦 成功获取到 {len(faq_raw)} 条常见问题。")
        for index, item in enumerate(faq_raw, 1):
            title = item.get("title", f"常见问题_{index}").strip()
            faq_type_id = str(item.get("faqTypeId", ""))
            category = FAQ_TYPE_MAPPING.get(faq_type_id, "其他常见问题")
            html_content = item.get("answer", "")
            update_time = item.get('updateTime', '未知')

            if category not in faq_groups:
                faq_groups[category] = []

            markdown_body = convert_html_to_markdown(html_content, title)

            faq_data = {
                "title": title,
                "update_time": update_time,
                "content": markdown_body
            }
            faq_groups[category].append(faq_data)

            # 单篇保存到 data/常见问题/分类/标题.md
            save_dir = os.path.join(base_save_dir, "常见问题", clean_filename(category))
            os.makedirs(save_dir, exist_ok=True)
            file_path = os.path.join(save_dir, clean_filename(title) + ".md")

            single_md = [
                f"# {title}\n",
                f"- **分类**: {category}",
                f"- **更新时间**: {update_time}\n",
                "---\n",
                markdown_body
            ]

            with open(file_path, "w", encoding="utf-8") as sf:
                sf.write("\n".join(single_md))

    # =================== 3. 生成合并知识库文档 ===================
    print("\n📝 开始构建合并的知识库汇总文档...")

    merged_lines = []
    merged_lines.append("# 管家婆云辉煌创业版知识库\n")

    # --- 3.1 生成目录 ---
    merged_lines.append("## 目录")

    if tutorial_groups:
        merged_lines.append(f"- [📖 使用教程](#📖-使用教程)")
        for cat, items in tutorial_groups.items():
            cat_anchor = slugify(cat)
            merged_lines.append(f"  - [{cat}](#{cat_anchor})")
            for item in items:
                item_title = item["title"]
                item_anchor = slugify(item_title)
                merged_lines.append(f"    - [{item_title}](#{item_anchor})")

    if faq_groups:
        merged_lines.append(f"- [❓ 常见问题 (FAQ)](#❓-常见问题-faq)")
        for cat, items in faq_groups.items():
            cat_anchor = slugify(cat)
            merged_lines.append(f"  - [{cat}](#{cat_anchor})")
            for item in items:
                item_title = item["title"]
                item_anchor = slugify(item_title)
                merged_lines.append(f"    - [{item_title}](#{item_anchor})")

    merged_lines.append("\n---\n")

    # --- 3.2 生成使用教程正文 ---
    if tutorial_groups:
        merged_lines.append("## 📖 使用教程\n")
        for cat, items in tutorial_groups.items():
            merged_lines.append(f"### {cat}\n")
            for item in items:
                item_title = item["title"]
                item_update = item["update_time"]
                item_body = item["content"]

                merged_lines.append(f"#### {item_title}\n")
                merged_lines.append(f"- **分类**: {cat}")
                merged_lines.append(f"- **更新时间**: {item_update}\n")
                merged_lines.append(item_body)
                merged_lines.append("\n---\n")

    # --- 3.3 生成常见问题正文 ---
    if faq_groups:
        merged_lines.append("## ❓ 常见问题 (FAQ)\n")
        for cat, items in faq_groups.items():
            merged_lines.append(f"### {cat}\n")
            for item in items:
                item_title = item["title"]
                item_update = item["update_time"]
                item_body = item["content"]

                merged_lines.append(f"#### {item_title}\n")
                merged_lines.append(f"- **分类**: {cat}")
                merged_lines.append(f"- **更新时间**: {item_update}\n")

                merged_lines.append(item_body)
                merged_lines.append("\n---\n")

    # 保存合并文档
    merged_file_path = os.path.join(base_save_dir, "管家婆云辉煌创业版知识库.md")
    with open(merged_file_path, "w", encoding="utf-8") as mf:
        mf.write("\n".join(merged_lines))

    print(f"✅ 合并汇总文档已成功保存至: {merged_file_path}")
    print("\n✨ 全部爬取与 Markdown 转换工作已完成！")


if __name__ == "__main__":
    crawl_and_process()
