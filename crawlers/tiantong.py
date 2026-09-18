"""天通资源管理中心爬虫。

入口 http://117.172.29.67:6067/knowledge 为 Vite SPA；
数据来自免登录分页接口 GET /api/knowledge?page=&pageSize=，列表直接内联全文 HTML。
附件通过 GET /api/upload/{fileId}/token 换取临时下载地址（15 分钟失效），
因此必须在抓取阶段立即下载落盘。
"""
import json
import os

import requests

from common.converter import clean_filename

from .base import BaseCrawler, CrawledDocument, DocumentStub


class TiantongCrawler(BaseCrawler):
    platform = "tiantong"
    display_name = "天通资源管理中心"
    requires_auth = False

    DEFAULT_SITE_BASE_URL = "http://117.172.29.67:6067"

    def __init__(
        self,
        save_dir,
        progress_callback=None,
        pipeline_mode=None,
        page_size=50,
        timeout=20,
        site_base_url=None,
    ):
        self.site_base_url = (
            site_base_url
            or os.getenv("TIANTONG_BASE_URL", self.DEFAULT_SITE_BASE_URL)
        ).rstrip("/")
        self.entry_url = f"{self.site_base_url}/knowledge"
        self.page_size = page_size
        self.timeout = timeout
        self._items = {}
        super().__init__(
            save_dir,
            progress_callback=progress_callback,
            pipeline_mode=pipeline_mode,
        )

    def list_documents(self):
        api_url = f"{self.site_base_url}/api/knowledge"
        stubs = []
        page = 1
        while True:
            response = requests.get(
                api_url,
                params={"page": page, "pageSize": self.page_size},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("code") != 200:
                raise RuntimeError(
                    f"获取天通知识列表失败: {payload.get('message')}"
                )

            data = payload.get("data") or {}
            items = data.get("list") or []
            if not items:
                break

            for item in items:
                item_id = str(item.get("id"))
                self._items[item_id] = item
                stubs.append(DocumentStub(
                    id=item_id,
                    title=(item.get("title") or f"未命名文档_{item_id}").strip(),
                    category=(item.get("categoryName") or "未分类").strip(),
                ))

            total = int(data.get("total") or 0)
            self._notify(
                min(page * self.page_size, total),
                total,
                f"正在获取文档列表: 第 {page} 页，已收录 {len(stubs)} 条",
            )
            if page * self.page_size >= total or len(items) < self.page_size:
                break
            page += 1

        print(
            f"📦 天通知识列表获取完成: {len(stubs)} 条 / "
            f"{len({stub.category for stub in stubs})} 个分类"
        )
        return stubs

    def fetch_document(self, stub):
        item = self._items.get(stub.id)
        if item is None:
            raise RuntimeError(f"文档 {stub.id} 不在已抓取的列表缓存中")
        return CrawledDocument(
            id=stub.id,
            title=stub.title,
            category=stub.category,
            html=item.get("content") or "",
            updated_at=(
                item.get("updatedAt") or item.get("createdAt") or "未知"
            ),
            metadata=dict(item),
        )

    def supplement_resources(self, doc, resources):
        links = list(resources.get("links", []))
        for attachment in self._parse_attachments(doc.metadata.get("attachments")):
            local_path = self._download_attachment(attachment)
            if local_path:
                links.append({
                    "text": attachment.get("name") or "附件",
                    "url": local_path,
                })
        return {
            "images": list(resources.get("images", [])),
            "links": links,
        }

    @staticmethod
    def _parse_attachments(raw):
        if not raw:
            return []
        if isinstance(raw, list):
            return raw
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            print(f"⚠️ 附件字段解析失败，保留原始值: {str(raw)[:100]!r}")
            return []
        return parsed if isinstance(parsed, list) else []

    def _download_attachment(self, attachment):
        file_id = attachment.get("fileId")
        name = clean_filename(
            attachment.get("name") or f"attachment_{file_id}"
        )
        if not file_id:
            print(f"⚠️ 附件缺少 fileId，跳过下载: {name}")
            return None

        try:
            token_response = requests.get(
                f"{self.site_base_url}/api/upload/{file_id}/token",
                timeout=self.timeout,
            )
            token_response.raise_for_status()
            token_payload = token_response.json()
            if token_payload.get("code") != 200:
                raise RuntimeError(
                    token_payload.get("message") or "token 接口返回错误"
                )
            download_url = (token_payload.get("data") or {}).get("downloadUrl", "")
            if not download_url:
                raise RuntimeError("token 接口未返回 downloadUrl")

            if not download_url.startswith(("http://", "https://")):
                download_url = f"{self.site_base_url}{download_url}"
            file_response = requests.get(download_url, timeout=60)
            file_response.raise_for_status()

            attachments_dir = os.path.join(self.asset_dir, "attachments")
            os.makedirs(attachments_dir, exist_ok=True)
            filename = f"{clean_filename(str(file_id))[:8]}_{name}"
            file_path = os.path.join(attachments_dir, filename)
            with open(file_path, "wb") as output_file:
                output_file.write(file_response.content)
            print(f"📎 附件已下载: {filename}")
            return f"assets/attachments/{filename}"
        except Exception as exc:
            print(f"⚠️ 附件下载失败 ({name}): {exc}")
            return None
