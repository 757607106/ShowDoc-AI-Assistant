"""管家婆云辉煌创业版（CYB）爬虫。

入口 https://new.yuncyb.com；数据来自登录后的两个平铺接口：
- GET /tutorials：使用教程（含 category、coverImage、videoUrl）；
- GET /faqs：常见问题（faqTypeId → 中文分类映射）。
登录走 /auth/captcha → 千问 VL 识别 → /auth/phone/login（token 每次运行重新获取）。

分类设计：教程为 "使用教程/<分类>"，FAQ 为 "常见问题/<类型>"，
两类内容不会混入同一分类，与目录、合并文档、JSONL 一一对应。
"""
import base64
import json
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request

import requests

from html import escape

from common.converter import CYB_API_BASE_URL

from .base import BaseCrawler, CrawledDocument, DocumentStub

DASHSCOPE_API_URL = os.getenv(
    "DASHSCOPE_API_URL",
    "https://dashscope.aliyuncs.com/api/v1/services/aigc/"
    "multimodal-generation/generation",
)

# FAQ 类型映射表（将 ID 转换为清晰的 ERP 模块分类）
FAQ_TYPE_MAPPING = {
    "1": "基础与系统",
    "2": "采购业务",
    "3": "销售业务",
    "4": "库存业务",
    "5": "财务与账务",
    "6": "打印设置",
    "7": "系统设置",
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


class CYBCrawler(BaseCrawler):
    platform = "cyb"
    display_name = "管家婆云辉煌创业版"
    requires_auth = True

    def __init__(
        self,
        save_dir,
        progress_callback=None,
        pipeline_mode=None,
        phone=None,
        password=None,
        base_url=None,
        timeout=30,
    ):
        self.api_base_url = (
            base_url or CYB_API_BASE_URL
        ).rstrip("/")
        parts = urllib.parse.urlsplit(self.api_base_url)
        self.site_base_url = f"{parts.scheme}://{parts.netloc}"
        self.entry_url = self.site_base_url
        self.timeout = timeout
        self.authenticator = CYBAuthenticator(phone=phone, password=password)
        self._headers = {}
        self._items = {}
        super().__init__(
            save_dir,
            progress_callback=progress_callback,
            pipeline_mode=pipeline_mode,
        )

    def authenticate(self):
        token = self.authenticator.login()
        self._headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def list_documents(self):
        tutorials = self._fetch_list("/tutorials")
        print(f"📦 成功获取到 {len(tutorials)} 条使用教程。")

        faqs = self._fetch_list("/faqs")
        print(f"📦 成功获取到 {len(faqs)} 条常见问题。")

        stubs = []
        for index, item in enumerate(tutorials, 1):
            document_id = f"tutorial-{item.get('id') or index}"
            self._items[document_id] = item
            category = (item.get("category") or "未分类").strip() or "未分类"
            stubs.append(DocumentStub(
                id=document_id,
                title=(item.get("title") or f"未命名教程_{index}").strip(),
                category=f"使用教程/{category}",
            ))

        for index, item in enumerate(faqs, 1):
            document_id = f"faq-{item.get('id') or index}"
            self._items[document_id] = item
            faq_type = FAQ_TYPE_MAPPING.get(
                str(item.get("faqTypeId", "")), "其他常见问题"
            )
            stubs.append(DocumentStub(
                id=document_id,
                title=(item.get("title") or f"常见问题_{index}").strip(),
                category=f"常见问题/{faq_type}",
            ))

        print(
            f"📦 CYB 列表获取完成: {len(stubs)} 条 / "
            f"{len({stub.category for stub in stubs})} 个分类"
        )
        return stubs

    def fetch_document(self, stub):
        item = self._items.get(stub.id)
        if item is None:
            raise RuntimeError(f"文档 {stub.id} 不在已抓取的列表缓存中")

        if stub.id.startswith("tutorial-"):
            html = item.get("content") or ""
        else:
            html = item.get("answer") or ""

        return CrawledDocument(
            id=stub.id,
            title=stub.title,
            category=stub.category,
            html=html,
            updated_at=str(item.get("updateTime") or "未知"),
            metadata=dict(item),
        )

    def assemble_html(self, doc, prepared_html):
        if not doc.id.startswith("tutorial-"):
            return prepared_html

        # 视频教程无正文时，封面与视频链接构成其全部内容；正文教程则补挂封面。
        item = doc.metadata
        cover_image = item.get("coverImage") or ""
        if cover_image and cover_image not in prepared_html:
            cover_html = (
                f'<p><img src="{escape(cover_image, quote=True)}" '
                f'alt="{escape(doc.title, quote=True)}封面"></p>'
            )
            prepared_html = cover_html + prepared_html

        video_url = item.get("videoUrl") or ""
        if video_url and video_url not in prepared_html:
            prepared_html += (
                f'\n<p><a href="{escape(video_url, quote=True)}">'
                f'{escape("打开视频教程", quote=True)}</a></p>'
            )
        return prepared_html

    def build_finetuning_records(self, documents):
        records = []
        for doc in documents:
            question = doc.metadata.get("question")
            if not doc.markdown or not question:
                continue
            records.append({
                "messages": [
                    {
                        "role": "system",
                        "content": "你是管家婆云辉煌创业版产品知识助手。",
                    },
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": doc.markdown},
                ]
            })
        return records

    def _fetch_list(self, path):
        response = requests.get(
            f"{self.api_base_url}{path}",
            headers=self._headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != "A00000":
            raise RuntimeError(
                f"获取 {path} 失败[{payload.get('code')}]: {payload.get('message')}"
            )
        return payload.get("data") or []
