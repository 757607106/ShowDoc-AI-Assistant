"""通用网页的动态 API 发现与只读分页。

本模块只处理浏览器已经真实发出的同源 GET/POST 请求。自动分页必须同时满足：
响应是 JSON 列表、请求包含常见分页字段、接口路径不包含写操作关键词。
它不会猜测或调用未在页面加载过程中出现过的接口。
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import urllib.parse
from collections import defaultdict, deque
from dataclasses import dataclass, field


PAGE_KEYS = ("page", "pn", "page_no", "pageno", "page_num", "pagenum", "current")
SIZE_KEYS = ("size", "ps", "page_size", "pagesize", "limit")
LIST_KEYS = ("data", "list", "items", "records", "results", "rows")
TOTAL_KEYS = ("total", "count", "total_count", "totalcount")
SAFE_PATH_PATTERN = re.compile(r"(?:^|[/_-])(list|search|query|page|get|view|detail)(?:$|[/_?-])", re.I)
UNSAFE_PATH_PATTERN = re.compile(
    r"(?:^|[/_-])(create|update|delete|remove|save|submit|pay|order|login|logout|upload)(?:$|[/_?-])",
    re.I,
)
SAFE_HEADER_NAMES = {
    "accept",
    "accept-language",
    "content-type",
    "origin",
    "referer",
    "user-agent",
    "x-requested-with",
}


@dataclass
class NetworkExchange:
    url: str
    method: str
    headers: dict
    post_data: str
    status: int
    response_headers: dict
    response_text: str


@dataclass
class PaginationPlan:
    url: str
    method: str
    headers: dict
    body: dict
    page_key: str
    size_key: str | None
    list_path: tuple[str, ...]
    total_path: tuple[str, ...] | None
    first_records: list[dict] = field(default_factory=list)
    total: int | None = None


@dataclass
class PaginationResult:
    plan: PaginationPlan
    records: list[dict]
    requests_made: int
    complete: bool
    stop_reason: str


def pair_network_exchanges(events):
    """按 URL 将 Crawl4AI 的 request/response 事件配成交换记录。"""
    pending = defaultdict(deque)
    ambiguous = set()
    exchanges = []
    for event in events or []:
        event_type = event.get("event_type")
        url = event.get("url") or ""
        if not url:
            continue
        if event_type == "request":
            if pending[url]:
                ambiguous.add(url)
            pending[url].append(event)
            continue
        if event_type != "response" or not pending[url]:
            continue
        request = pending[url].popleft()
        if url in ambiguous:
            if not pending[url]:
                ambiguous.discard(url)
            continue
        body = event.get("body") or {}
        exchanges.append(
            NetworkExchange(
                url=url,
                method=(request.get("method") or "GET").upper(),
                headers=request.get("headers") or {},
                post_data=request.get("post_data") or "",
                status=int(event.get("status") or 0),
                response_headers=event.get("headers") or {},
                response_text=body.get("text") or "",
            )
        )
    return exchanges


def _lower_key_map(mapping):
    return {str(key).lower(): key for key in mapping}


def _find_pagination_keys(mapping):
    if not isinstance(mapping, dict):
        return None, None
    keys = _lower_key_map(mapping)
    page_key = next((keys[key] for key in PAGE_KEYS if key in keys), None)
    size_key = next((keys[key] for key in SIZE_KEYS if key in keys), None)
    return page_key, size_key


def _find_list_payload(value, path=()):
    """寻找包含记录列表和可选总数的最近字典。"""
    if isinstance(value, dict):
        keys = _lower_key_map(value)
        for list_name in LIST_KEYS:
            original = keys.get(list_name)
            records = value.get(original) if original is not None else None
            if isinstance(records, list) and all(isinstance(item, dict) for item in records):
                total_key = next((keys[key] for key in TOTAL_KEYS if key in keys), None)
                total_path = path + (total_key,) if total_key is not None else None
                return path + (original,), total_path, records
        for key, child in value.items():
            found = _find_list_payload(child, path + (key,))
            if found:
                return found
    return None


def value_at_path(value, path):
    current = value
    for key in path or ():
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _safe_headers(headers):
    return {
        key: value
        for key, value in (headers or {}).items()
        if str(key).lower() in SAFE_HEADER_NAMES
    }


def infer_pagination_plans(events, page_url):
    """从已发生的网络请求推断可安全重放的分页计划。"""
    page_parts = urllib.parse.urlsplit(page_url)
    page_origin = (
        page_parts.scheme.lower(),
        (page_parts.hostname or "").lower(),
        page_parts.port or (443 if page_parts.scheme.lower() == "https" else 80),
    )
    plans = []
    seen = set()
    for exchange in pair_network_exchanges(events):
        parsed = urllib.parse.urlsplit(exchange.url)
        exchange_origin = (
            parsed.scheme.lower(),
            (parsed.hostname or "").lower(),
            parsed.port or (443 if parsed.scheme.lower() == "https" else 80),
        )
        response_header_names = _lower_key_map(exchange.response_headers)
        content_type_key = response_header_names.get("content-type")
        content_type = str(
            exchange.response_headers.get(content_type_key, "")
            if content_type_key is not None
            else ""
        ).lower()
        if (
            exchange_origin != page_origin
            or exchange.method not in {"GET", "POST"}
            or exchange.status < 200
            or exchange.status >= 300
            or "json" not in content_type
            or UNSAFE_PATH_PATTERN.search(parsed.path)
            or not SAFE_PATH_PATTERN.search(parsed.path)
        ):
            continue
        try:
            response_data = json.loads(exchange.response_text)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        found = _find_list_payload(response_data)
        if not found:
            continue
        list_path, total_path, records = found

        body = {}
        query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
        if exchange.method == "POST":
            try:
                body = json.loads(exchange.post_data or "{}")
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            page_key, size_key = _find_pagination_keys(body)
        else:
            page_key, size_key = _find_pagination_keys(query)
        if not page_key:
            continue

        total_value = value_at_path(response_data, total_path)
        try:
            total = int(total_value) if total_value is not None else None
        except (TypeError, ValueError):
            total = None
        identity_query = {key: value for key, value in query.items() if key != page_key}
        identity_body = {key: value for key, value in body.items() if key != page_key}
        identity = (exchange.method, parsed.scheme, parsed.netloc, parsed.path,
                    json.dumps(identity_query, sort_keys=True), json.dumps(identity_body, sort_keys=True),
                    tuple(list_path), str(page_key))
        if identity in seen:
            continue
        seen.add(identity)
        plans.append(
            PaginationPlan(
                url=exchange.url,
                method=exchange.method,
                headers=_safe_headers(exchange.headers),
                body=body,
                page_key=page_key,
                size_key=size_key,
                list_path=tuple(list_path),
                total_path=tuple(total_path) if total_path else None,
                first_records=records,
                total=total,
            )
        )
    return plans


def _record_key(record):
    for key in ("id", "uuid", "key", "url", "link", "href", "slug"):
        value = record.get(key)
        if value not in (None, ""):
            return f"{key}:{value}"
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True, default=str)
    return "sha1:" + hashlib.sha1(payload.encode("utf-8")).hexdigest()


def paginate_plan(session, plan, max_records=0, max_api_pages=200, timeout=25):
    """重放已验证的只读分页请求，并按记录身份去重。"""
    records = []
    seen = set()

    def append_records(items):
        added = 0
        for item in items or []:
            if not isinstance(item, dict):
                continue
            key = _record_key(item)
            if key in seen:
                continue
            seen.add(key)
            records.append(item)
            added += 1
            if max_records and len(records) >= max_records:
                break
        return added

    append_records(plan.first_records)
    if max_records and len(records) >= max_records:
        return PaginationResult(plan, records[:max_records], 0, False, "record_limit")
    if plan.total is not None and len(records) >= plan.total:
        return PaginationResult(plan, records, 0, True, "total_reached")

    request_count = 0
    start_page = 1
    source = plan.body if plan.method == "POST" else dict(
        urllib.parse.parse_qsl(urllib.parse.urlsplit(plan.url).query, keep_blank_values=True)
    )
    try:
        start_page = int(source.get(plan.page_key, 1))
    except (TypeError, ValueError):
        start_page = 1

    for page_number in range(start_page + 1, start_page + max_api_pages):
        if max_records and len(records) >= max_records:
            return PaginationResult(plan, records[:max_records], request_count, False, "record_limit")
        if plan.total is not None and len(records) >= plan.total:
            return PaginationResult(plan, records, request_count, True, "total_reached")

        request_count += 1
        if plan.method == "POST":
            payload = copy.deepcopy(plan.body)
            payload[plan.page_key] = page_number
            response = session.post(
                plan.url,
                json=payload,
                headers=plan.headers,
                timeout=timeout,
            )
        else:
            parsed = urllib.parse.urlsplit(plan.url)
            params = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
            params[plan.page_key] = page_number
            request_url = urllib.parse.urlunsplit(
                (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(params), "")
            )
            response = session.get(request_url, headers=plan.headers, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        items = value_at_path(payload, plan.list_path)
        if not isinstance(items, list):
            return PaginationResult(plan, records, request_count, False, "invalid_response")
        if not items:
            complete = plan.total is None or len(records) >= plan.total
            return PaginationResult(plan, records, request_count, complete,
                                    "empty_page" if complete else "total_mismatch")
        if append_records(items) == 0:
            return PaginationResult(plan, records, request_count, False, "duplicate_page")

    complete = plan.total is not None and len(records) >= plan.total
    return PaginationResult(
        plan,
        records[:max_records] if max_records else records,
        request_count,
        complete,
        "total_reached" if complete else "page_limit",
    )
