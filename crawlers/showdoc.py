"""ShowDoc 文档站爬虫。

入口 https://yunhelp.gmgrasp.com.cn，项目 → 目录树 → 页面三级结构：
- 公开项目可匿名访问 item/info 与 page/info（旧 YunHuiHuangCrawler 的用法）；
- 登录（验证码 + 千问 VL 识别）后可通过 item/myList 列出账号下的全部项目，
  并访问受保护项目（旧 ShowDocCrawler 的用法）。
本类合并上述两套同平台实现，token 因此设计为可选。
"""
import os
import time
import urllib.parse

import requests

from showdoc_auth import ShowDocAuthenticator

from .base import BaseCrawler, CrawledDocument, DocumentStub

DEFAULT_BASE_URL = "https://yunhelp.gmgrasp.com.cn/server/index.php"


class ShowDocCrawler(BaseCrawler):
    platform = "showdoc"
    display_name = "ShowDoc"
    requires_auth = False  # 公开项目匿名可爬；auto_login=True 时先登录

    def __init__(
        self,
        save_dir,
        progress_callback=None,
        pipeline_mode=None,
        item_id=None,
        user_token=None,
        keyword="",
        default_page_id="",
        auto_login=False,
        timeout=15,
        base_url=None,
    ):
        if not item_id:
            raise ValueError("ShowDoc 爬取需要通过 --item 指定项目 ID")
        self.base_url = (
            base_url or os.getenv("SHOWDOC_BASE_URL", DEFAULT_BASE_URL)
        ).rstrip("/")
        parts = urllib.parse.urlsplit(self.base_url)
        self.site_base_url = urllib.parse.urlunsplit(
            (parts.scheme, parts.netloc, "", "", "")
        )
        self.entry_url = self.site_base_url
        self.item_id = str(item_id)
        self.user_token = user_token
        self.keyword = keyword or ""
        self.default_page_id = default_page_id or ""
        self.auto_login = auto_login
        self.timeout = timeout
        self.project_name = ""
        self._item_info = None
        super().__init__(
            save_dir,
            progress_callback=progress_callback,
            pipeline_mode=pipeline_mode,
        )

    # ---------- 认证 ----------

    def authenticate(self):
        if self.user_token or not self.auto_login:
            # 无 token 且未要求登录时匿名访问（公开项目可用）。
            return
        auth = ShowDocAuthenticator(base_url=self.base_url)
        token = auth.login()
        if not token:
            raise RuntimeError("ShowDoc 登录失败，请检查凭证或网络连接")
        self.user_token = token

    # ---------- 项目列表（CLI / Web 选择项目用） ----------

    @classmethod
    def list_projects(cls, user_token=None, base_url=None, group_id=0, timeout=15):
        """登录并列出账号下的项目；返回 [{item_id, item_name}]。"""
        base_url = (
            base_url or os.getenv("SHOWDOC_BASE_URL", DEFAULT_BASE_URL)
        ).rstrip("/")
        token = user_token
        if not token:
            auth = ShowDocAuthenticator(base_url=base_url)
            token = auth.login()
            if not token:
                raise RuntimeError("ShowDoc 登录失败，无法获取项目列表")

        response = requests.post(
            f"{base_url}?s=/api/item/myList",
            data={
                "s": "/api/item/myList",
                "user_token": token,
                "item_group_id": group_id,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        result = response.json()
        if result.get("error_code") != 0:
            raise RuntimeError(
                f"获取项目列表失败: {result.get('error_message', '未知错误')}"
            )
        return [
            {
                "item_id": str(item.get("item_id")),
                "item_name": item.get("item_name", ""),
            }
            for item in result.get("data") or []
        ]

    # ---------- BaseCrawler 接口 ----------

    def _post(self, api_path, extra=None):
        payload = {"s": api_path, **(extra or {})}
        if self.user_token:
            payload["user_token"] = self.user_token
        response = requests.post(
            f"{self.base_url}?s={api_path}", data=payload, timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def fetch_item_info(self):
        if self._item_info is not None:
            return self._item_info

        self._notify(0, 0, f"正在获取项目信息 (item_id={self.item_id})...")
        result = self._post(
            "/api/item/info",
            {
                "item_id": self.item_id,
                "keyword": self.keyword,
                "default_page_id": self.default_page_id,
            },
        )
        if result.get("error_code") != 0:
            raise RuntimeError(
                f"获取项目信息失败: {result.get('error_message', '未知错误')}"
            )
        self._item_info = result
        data = result.get("data") or {}
        self.project_name = (data.get("item_name") or f"项目{self.item_id}").strip()
        # 合并文档以项目名命名，与旧版 {项目名}_完整文档.md 行为一致。
        self.collection_name = self.project_name
        return self._item_info

    def list_documents(self):
        data = self.fetch_item_info().get("data") or {}
        menu = data.get("menu") or {}

        stubs = []
        for page in menu.get("pages") or []:
            stubs.append(self._page_stub(page, "根目录"))
        stubs.extend(self._walk_catalogs(menu.get("catalogs") or []))

        category_count = len({stub.category for stub in stubs})
        print(
            f"📦 项目「{self.project_name}」共 {len(stubs)} 个页面 / "
            f"{category_count} 个分类"
        )
        return stubs

    def _page_stub(self, page, category):
        page_id = str(page.get("page_id"))
        title = (page.get("page_title") or f"未命名页面_{page_id}").strip()
        return DocumentStub(id=page_id, title=title, category=category)

    def _walk_catalogs(self, catalogs, parent_category=""):
        stubs = []
        for catalog in catalogs:
            name = (catalog.get("cat_name") or "未命名目录").strip()
            category = (
                f"{parent_category}/{name}" if parent_category else name
            )
            for page in catalog.get("pages") or []:
                stubs.append(self._page_stub(page, category))
            stubs.extend(
                self._walk_catalogs(catalog.get("catalogs") or [], category)
            )
        return stubs

    def fetch_document(self, stub):
        result = self._post("/api/page/info", {"page_id": stub.id})
        if result.get("error_code") != 0:
            # 单页失败不中断整体爬取；错误原因记入 metadata 便于排查。
            message = result.get("error_message", "未知错误")
            print(f"⚠️ 获取页面失败 (page_id={stub.id}): {message}")
            return CrawledDocument(
                id=stub.id,
                title=stub.title,
                category=stub.category,
                html="",
                updated_at="未知",
                metadata={
                    "page_id": stub.id,
                    "page_title": stub.title,
                    "fetch_error": message,
                },
            )

        page = result.get("data") or {}
        return CrawledDocument(
            id=str(page.get("page_id") or stub.id),
            title=(page.get("page_title") or stub.title).strip(),
            category=stub.category,
            html=page.get("page_content") or "",
            updated_at=self._format_time(
                page.get("page_addtime") or page.get("addtime")
            ),
            metadata=dict(page),
        )

    def fetch_page_data(self, page_id):
        """获取单页原始数据（预览用）；失败返回 None。"""
        result = self._post("/api/page/info", {"page_id": str(page_id)})
        if result.get("error_code") != 0:
            print(
                f"⚠️ 获取页面失败 (page_id={page_id}): "
                f"{result.get('error_message', '未知错误')}"
            )
            return None
        return result.get("data") or {}

    @staticmethod
    def _format_time(value):
        value = str(value or "").strip()
        if value.isdigit() and len(value) >= 9:
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(value)))
        return value or "未知"
