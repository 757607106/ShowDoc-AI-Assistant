"""已验证网站的薄适配器。

适配器仅负责公开目录发现和站点字段映射；Markdown、质量检查、RAG 分块和
落盘仍由 WebCrawler/BaseCrawler 的统一流程处理。
"""
from __future__ import annotations

import html
import os
import re
import time
import urllib.parse
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from crawlers.base import CrawledDocument, DocumentStub, CrawlCancelled


class WebSourceAdapter:
    key = ""
    display_name = ""
    hostnames = ()

    def __init__(self, url, max_documents=0, progress_callback=None):
        self.url = url
        self.max_documents = max(0, int(max_documents or 0))
        self.progress_callback = progress_callback
        self.records = []
        self.record_by_id = {}
        self.stats = {}

    @classmethod
    def matches(cls, url):
        hostname = (urllib.parse.urlsplit(url).hostname or "").lower()
        return hostname in cls.hostnames

    def list_documents(self):
        raise NotImplementedError

    def fetch_document(self, stub):
        raise NotImplementedError

    def crawl_documents(self, selected_ids=None, selected_titles=None):
        stubs = self.list_documents()
        if selected_ids:
            wanted = {str(item) for item in selected_ids}
            stubs = [stub for stub in stubs if stub.id in wanted]
        elif selected_titles:
            wanted = set(selected_titles)
            stubs = [stub for stub in stubs if stub.title in wanted]

        documents = []
        for index, stub in enumerate(stubs, 1):
            if self.progress_callback:
                self.progress_callback(index - 1, len(stubs), f"正在抓取: {stub.title}")
            try:
                documents.append(self.fetch_document(stub))
            except CrawlCancelled:
                raise
            except Exception as exc:
                documents.append(CrawledDocument(stub.id, stub.title, stub.category, "", "", {"fetch_error": str(exc)}, "html"))
            if self.progress_callback:
                self.progress_callback(index, len(stubs), f"已抓取: {stub.title}")
        return documents


class ClubCmgraspAdapter(WebSourceAdapter):
    key = "club_cmgrasp"
    display_name = "管家婆官方社区结构化采集"
    hostnames = ("club.cmgrasp.com",)
    api_base = "http://club.cmgrasp.com/api/api/"
    page_size = 24
    endpoints = (
        ("question/list", "社区问答", "question"),
        ("knowledge/list", "社区知识", "knowledge"),
        ("course/list", "社区课程", "course"),
        ("activity/list", "社区活动", "activity"),
        ("news/list", "社区公告", "news"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = self._make_session()

    @staticmethod
    def _make_session():
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.4,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("POST",),
        )
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/140.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "Origin": "http://club.cmgrasp.com",
                "Referer": "http://club.cmgrasp.com/",
            }
        )
        session.mount("http://", HTTPAdapter(max_retries=retry))
        return session

    def _post(self, endpoint, payload):
        response = self.session.post(self.api_base + endpoint, json=payload, timeout=25)
        response.raise_for_status()
        data = response.json()
        if data.get("status") not in (None, "OK"):
            raise RuntimeError(data.get("msg") or f"接口返回异常: {endpoint}")
        return data.get("result") or {}

    def _load_endpoint(
        self, endpoint, category, record_type, remaining=0, metadata_only=False
    ):
        records = []
        total = None
        page_number = 1
        max_api_pages = max(1, int(os.getenv("WEB_CRAWLER_MAX_API_PAGES", "200")))
        while page_number <= max_api_pages:
            result = self._post(endpoint, {"pn": page_number, "ps": self.page_size})
            items = result.get("data") or []
            try:
                total = int(result.get("total"))
            except (TypeError, ValueError):
                total = None
            if metadata_only:
                break
            if not items:
                break
            for item in items:
                if not isinstance(item, dict) or not item.get("id"):
                    continue
                records.append(
                    {
                        "stub_id": f"{record_type}:{item['id']}",
                        "record_type": record_type,
                        "category": category,
                        "endpoint": endpoint,
                        "data": item,
                    }
                )
                if remaining and len(records) >= remaining:
                    break
            if remaining and len(records) >= remaining:
                break
            if total is not None and len(records) >= total:
                break
            page_number += 1
            delay = float(os.getenv("WEB_CRAWLER_API_DELAY", "0.03"))
            if delay > 0:
                time.sleep(delay)
        self.stats[record_type] = {
            "endpoint": endpoint,
            "reported_total": total,
            "fetched": len(records),
            "pages": page_number,
            "complete": (total is not None and len(records) >= total) or (total is None and not items and not metadata_only),
        }
        return records

    def _ensure_records(self):
        if self.records:
            return
        records = []
        for endpoint, category, record_type in self.endpoints:
            remaining = self.max_documents - len(records) if self.max_documents else 0
            if self.max_documents and remaining <= 0:
                self._load_endpoint(
                    endpoint,
                    category,
                    record_type,
                    metadata_only=True,
                )
                continue
            records.extend(
                self._load_endpoint(endpoint, category, record_type, remaining=remaining)
            )
        self.records = records
        self.record_by_id = {record["stub_id"]: record for record in records}

    def list_documents(self):
        self._ensure_records()
        return [
            DocumentStub(
                record["stub_id"],
                str(record["data"].get("title") or record["data"].get("subTitle") or "未命名内容"),
                record["category"],
            )
            for record in self.records
        ]

    @staticmethod
    def _timestamp(value):
        try:
            return datetime.fromtimestamp(int(value) / 1000).isoformat(timespec="seconds")
        except (TypeError, ValueError, OSError):
            return datetime.now().isoformat(timespec="seconds")

    @staticmethod
    def _detail_url(record_type, record_id, data):
        link = data.get("link") or ""
        if link:
            return urllib.parse.urljoin("http://club.cmgrasp.com/", link)
        route = {
            "question": "question/list",
            "knowledge": "knowledge/list",
            "course": "course/list",
            "activity": "activities/detail",
            "news": "activities/detail",
        }.get(record_type, "")
        return f"http://club.cmgrasp.com/{route}?id={urllib.parse.quote(str(record_id))}"

    def _fetch_answers(self, question_id):
        answers = []
        page_number = 1
        while page_number <= 100:
            result = self._post(
                "answer/list?voteCount=D&createTime=D",
                {"pn": page_number, "ps": 20, "questionId": question_id},
            )
            items = result.get("data") or []
            if not items:
                break
            answers.extend(item for item in items if isinstance(item, dict))
            try:
                total = int(result.get("total"))
            except (TypeError, ValueError):
                total = len(answers)
            if len(answers) >= total:
                break
            page_number += 1
            delay = float(os.getenv("WEB_CRAWLER_API_DELAY", "0.03"))
            if delay > 0:
                time.sleep(delay)
        return answers

    @staticmethod
    def _course_html(data):
        parts = []
        if data.get("subTitle"):
            parts.append(f"<p>{html.escape(str(data['subTitle']))}</p>")
        if data.get("description") and data.get("description") != data.get("subTitle"):
            parts.append(f"<p>{html.escape(str(data['description']))}</p>")
        if data.get("speakerName"):
            parts.append(f"<p><strong>讲师：</strong>{html.escape(str(data['speakerName']))}</p>")
        video = str(data.get("videoUrl") or "")
        match = re.search(r"src=[\"']([^\"']+)", video, re.I)
        if match:
            video_url = match.group(1)
            if video_url.startswith("//"):
                video_url = "https:" + video_url
            parts.append(
                f'<p><a href="{html.escape(video_url, quote=True)}">观看课程视频</a></p>'
            )
        if data.get("thumbUrl"):
            parts.append(
                f'<p><img src="{html.escape(str(data["thumbUrl"]), quote=True)}" alt="课程封面"></p>'
            )
        return "".join(parts)

    def fetch_document(self, stub):
        self._ensure_records()
        record = self.record_by_id.get(stub.id)
        if not record:
            raise KeyError(f"未找到社区内容: {stub.id}")
        data = record["data"]
        record_type = record["record_type"]
        html_content = str(data.get("content") or "")
        metadata = dict(data)
        if record_type == "question":
            answers = self._fetch_answers(data["id"]) if int(data.get("answerCount") or 0) else []
            metadata["answers"] = answers
            answer_html = "".join(
                "<section><h3>回答</h3>"
                f"<p><strong>回答者：</strong>{html.escape(str(answer.get('authorName') or '匿名'))}</p>"
                f"{answer.get('content') or ''}</section>"
                for answer in answers
            )
            html_content = f"<section><h2>问题</h2>{html_content}</section>{answer_html}"
        elif record_type == "course":
            html_content = self._course_html(data)
        elif record_type in {"news", "activity"} and data.get("link"):
            target = html.escape(str(data["link"]), quote=True)
            html_content = f'<p><a href="{target}">查看原始内容</a></p>'
        elif not html_content:
            summary = data.get("summary") or data.get("description") or ""
            html_content = f"<p>{html.escape(str(summary))}</p>" if summary else ""

        return CrawledDocument(
            id=stub.id,
            title=stub.title,
            category=stub.category,
            content=html_content,
            updated_at=self._timestamp(data.get("updateTime") or data.get("createTime")),
            metadata={
                **metadata,
                "adapter": self.key,
                "record_type": record_type,
                "content_completeness": "unknown" if data.get("content") else "summary",
                "url": self._detail_url(record_type, data["id"], data),
            },
            source_format="html",
        )


ADAPTERS = (ClubCmgraspAdapter,)


def resolve_web_adapter(url, **kwargs):
    for adapter_class in ADAPTERS:
        if adapter_class.matches(url):
            return adapter_class(url, **kwargs)
    return None


def describe_web_strategy(url):
    for adapter_class in ADAPTERS:
        if adapter_class.matches(url):
            return {
                "strategy": "adapter",
                "adapter": adapter_class.key,
                "name": adapter_class.display_name,
                "message": f"已识别为{adapter_class.display_name}，同站采集将自动遍历公开分页内容。",
            }
    return {
        "strategy": "generic",
        "adapter": None,
        "name": "增强型通用网页采集",
        "message": "将使用站点地图、页面链接、JavaScript 渲染和安全 API 分页发现。",
    }
