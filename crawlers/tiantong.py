"""天通资源管理中心爬虫。

入口 http://117.172.29.67:6067/knowledge 为 Vite SPA；
数据来自免登录分页接口 GET /api/knowledge?page=&pageSize=，列表直接内联全文 HTML。
附件通过 GET /api/upload/{fileId}/token 换取临时下载地址（15 分钟失效），
因此必须在抓取阶段立即下载落盘。
"""
import json
import os
import urllib.parse

import requests

from common.converter import clean_filename

from .base import BaseCrawler, CrawledDocument, DocumentStub


class TiantongCrawler(BaseCrawler):
    platform = "tiantong"
    display_name = "天通资源管理中心"
    requires_auth = False
    root_categories = ('未分类',)

    DEFAULT_SITE_BASE_URL = "http://117.172.29.67:6067"

    def __init__(
        self,
        save_dir,
        progress_callback=None,
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
        self.session = requests.Session()
        super().__init__(
            save_dir,
            progress_callback=progress_callback,
        )

    def list_documents(self):
        api_url = f"{self.site_base_url}/api/knowledge"
        stubs = []
        page = 1
        seen = set()
        while True:
            response = self.session.get(
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
            reported = data.get("total")
            total = int(reported) if reported is not None else None
            if not items:
                if total is not None and len(stubs) < total:
                    raise RuntimeError(f"文档目录不完整：预期 {total} 条，仅获取 {len(stubs)} 条")
                break
            added = 0
            for item in items:
                if item.get("id") is None:
                    raise RuntimeError("文档目录记录缺少 ID")
                item_id = str(item["id"])
                if item_id in seen:
                    continue
                seen.add(item_id)
                added += 1
                self._items[item_id] = item
                stubs.append(DocumentStub(
                    id=item_id,
                    title=(item.get("title") or f"未命名文档_{item_id}").strip(),
                    category=(item.get("categoryName") or "未分类").strip(),
                    directory_path=[item['categoryName'].strip()] if (item.get('categoryName') or '').strip() else [],
                ))

            if not added:
                raise RuntimeError("文档目录分页重复，已停止以避免无限请求")
            self._notify(
                len(stubs),
                total or len(stubs),
                f"正在获取文档列表: 第 {page} 页，已收录 {len(stubs)} 条",
            )
            if total is not None and len(stubs) >= total:
                break
            page += 1

        print(
            f"📦 天通知识列表获取完成: {len(stubs)} 条 / "
            f"{len({stub.category for stub in stubs})} 个分类"
        )
        return stubs

    def fetch_document(self, stub):
        item = self._items.get(stub.id)
        detail_loaded = item is None
        item = dict(item or {})
        fetch_error = None
        content_source = "detail" if detail_loaded else "list"

        if detail_loaded or not self._content_value(item):
            try:
                detail_url = (
                    f"{self.site_base_url}/api/knowledge/"
                    f"{urllib.parse.quote(str(stub.id), safe='')}"
                )
                response = self.session.get(detail_url, timeout=self.timeout)
                response.raise_for_status()
                payload = response.json()
                if payload.get("code") != 200:
                    raise RuntimeError(payload.get("message") or "详情接口返回错误")
                detail = payload.get("data") or {}
                if isinstance(detail, dict):
                    item.update(detail)
                    self._items[stub.id] = dict(item)
                    content_source = "detail"
            except Exception as exc:
                fetch_error = f"详情获取失败: {exc}"

        content, source_format = self._content_value(item, with_format=True)
        metadata = dict(item)
        metadata["content_source"] = content_source
        metadata["content_fetch_status"] = "ok" if content else "empty"
        if fetch_error:
            metadata["fetch_error"] = fetch_error
        return CrawledDocument(
            id=stub.id,
            title=(item.get("title") or stub.title).strip(),
            category=(item.get("categoryName") or stub.category).strip(),
            content=content,
            updated_at=(
                item.get("updatedAt") or item.get("createdAt") or "未知"
            ),
            metadata=metadata,
            source_format=source_format,
        )

    @staticmethod
    def _content_value(item, with_format=False):
        for field, source_format in (
            ("content", "html"),
            ("html", "html"),
            ("body", "html"),
            ("markdown", "markdown"),
            ("page_content", "markdown"),
        ):
            value = item.get(field)
            if value not in (None, ""):
                result = (str(value), source_format)
                return result if with_format else result[0]
        return ("", "html") if with_format else ""

    def supplement_resources(self, doc, resources):
        links = list(resources.get("links", []))
        for attachment in self._parse_attachments(doc.metadata.get("attachments")):
            local_path = self._download_attachment(attachment)
            if not local_path:
                doc.metadata.setdefault("resource_errors", []).append({
                    "file_id": attachment.get("fileId"), "name": attachment.get("name"), "error": "附件下载失败"
                })
            if local_path:
                links.append({
                    "text": attachment.get("name") or "附件",
                    "filename": attachment.get("name") or os.path.basename(local_path),
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
        except (TypeError, ValueError) as exc:
            raise ValueError(f"附件字段不是有效 JSON: {str(raw)[:100]!r}") from exc
        if not isinstance(parsed, list):
            raise ValueError("附件字段必须是列表")
        return parsed

    def _download_attachment(self, attachment):
        file_id = attachment.get("fileId")
        name = clean_filename(
            attachment.get("name") or f"attachment_{file_id}"
        )
        if not file_id:
            print(f"⚠️ 附件缺少 fileId，跳过下载: {name}")
            return None

        partial_path = None
        try:
            token_response = self.session.get(
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
            max_bytes = int(os.getenv("TIANTONG_MAX_ATTACHMENT_BYTES", str(100 * 1024 * 1024)))
            attachments_dir = os.path.join(self.asset_dir, "attachments")
            os.makedirs(attachments_dir, exist_ok=True)
            filename = f"{clean_filename(str(file_id))}_{name}"
            file_path = os.path.join(attachments_dir, filename)
            partial_path = file_path + '.part'
            with self.session.get(download_url, timeout=60, stream=True) as file_response:
                file_response.raise_for_status()
                declared_size = int(file_response.headers.get("Content-Length") or 0)
                if declared_size > max_bytes:
                    raise ValueError(f"附件大小 {declared_size} 超过上限 {max_bytes}")
                downloaded = 0
                with open(partial_path, "wb") as output_file:
                    for chunk in file_response.iter_content(1024 * 1024):
                        if not chunk:
                            continue
                        downloaded += len(chunk)
                        if downloaded > max_bytes:
                            raise ValueError(f"附件超过大小上限 {max_bytes}")
                        output_file.write(chunk)
            os.replace(partial_path, file_path)
            print(f"📎 附件已下载: {filename}")
            return f"assets/attachments/{filename}"
        except Exception as exc:
            if partial_path:
                try:
                    os.unlink(partial_path)
                except FileNotFoundError:
                    pass
            print(f"⚠️ 附件下载失败 ({name}): {exc}")
            return None
