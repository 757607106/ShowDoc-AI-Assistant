"""ContextDB DATA API 官方 REST 客户端。

契约依据官方文档 API 章节(https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/
contextdb-documentation.html#/api-overview)与 docs/architecture/contextdb-integration-notes.md
的实测记录。认证用 `X-API-Key`;响应分裸业务 JSON 与统一信封(errorCode=0+data)两种,
错误可能为 errorCode 结构或 FastAPI 风格 `detail`(文本或校验数组)。
"""

from __future__ import annotations

import json
import os
import time

import requests

DEFAULT_BASE_URL = "https://context-database.aliyuncs.com"

REVIEW_ACTIONS = frozenset({
    "confirm", "force_accept", "accept_rewrite", "reject", "reject_reupload", "retract", "retry_review",
})
BATCH_REVIEW_ACTIONS = REVIEW_ACTIONS - {"reject_reupload"}
KNOWLEDGE_VIEWS = frozenset({"source", "auto", "wiki"})
WIKI_SEARCH_MODES = frozenset({"keyword", "regex"})

_INGEST_TERMINAL_STATUSES = frozenset({"succeeded", "failed", "pending_review", "deleted"})
_EVENT_TERMINAL_STATUSES = frozenset({"SUCCEEDED", "FAILED", "CANCELLED"})


class ContextDBError(RuntimeError):
    def __init__(self, message, *, status_code=None, error_code=None, request_id=None, detail=None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.request_id = request_id
        self.detail = detail


class ContextDBConflictError(ContextDBError):
    """409/1003:同名文档、并发修改或版本过期——insert-if-absent 与 CAS 的竞态信号。"""


class ContextDBAuthError(ContextDBError):
    """401/403:凭证、成员或权限问题;4006/4007/4008 为成员/权限/空间锁定。"""


_CONFLICT_ERROR_CODES = {1003, 4033}
_AUTH_ERROR_CODES = {4006, 4007, 4008}
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class ContextDBClient:
    """X-API-Key 直连的 DATA API 客户端;凭据来自 CONTEXTDB_BASE_URL / CONTEXTDB_API_KEY。"""

    def __init__(self, *, base_url=None, api_key=None, timeout=60.0, max_retries=2, session=None):
        self.base_url = (
            base_url
            or os.getenv("CONTEXTDB_BASE_URL")
            or os.getenv("CONTEXTDB_API_BASE")
            or DEFAULT_BASE_URL
        ).rstrip("/")
        self.api_key = api_key or os.getenv("CONTEXTDB_API_KEY") or ""
        self.timeout = timeout
        self.max_retries = max(0, int(max_retries))
        self._session = session or requests.Session()
        self._mcp_call_id = 0

    def configured(self):
        return bool(self.api_key)

    def current_permissions(self):
        return self._request('GET', '/v1/workspaces/members/self/permissions')

    # ---------- 底层请求 ----------

    def _headers(self, *, with_body=False):
        headers = {"X-API-Key": self.api_key, "Accept": "application/json"}
        if with_body:
            headers["Content-Type"] = "application/json"
        return headers

    def _request(self, method, path, *, json_body=None, params=None):
        attempts = self.max_retries + 1 if method.upper() in ('GET', 'HEAD') else 1
        for attempt in range(1, attempts + 1):
            try:
                response = self._session.request(
                    method,
                    f"{self.base_url}{path}",
                    json=json_body,
                    params=params,
                    headers=self._headers(with_body=json_body is not None),
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                if attempt == attempts:
                    raise ContextDBError(f"ContextDB 网络请求失败: {exc}") from exc
                time.sleep(min(1.0 * attempt, 3.0))
                continue
            if response.status_code in _RETRYABLE_STATUS and attempt < attempts:
                time.sleep(min(1.0 * attempt, 3.0))
                continue
            return self._payload(response)
        raise ContextDBError("ContextDB 请求重试耗尽")

    def _payload(self, response):
        payload = None
        try:
            payload = response.json()
        except ValueError:
            pass
        if isinstance(payload, dict) and "detail" in payload and "errorCode" not in payload:
            raise self._detail_error(response, payload["detail"])
        if isinstance(payload, dict) and payload.get("errorCode") not in (None, 0):
            code = payload.get("errorCode")
            message = payload.get("errorMessage") or "ContextDB 业务错误"
            request_id = payload.get("requestId")
            if code in _CONFLICT_ERROR_CODES or response.status_code == 409:
                error_cls = ContextDBConflictError
            elif code in _AUTH_ERROR_CODES or response.status_code in (401, 403):
                error_cls = ContextDBAuthError
            else:
                error_cls = ContextDBError
            raise error_cls(
                f"{message} (errorCode={code})",
                status_code=response.status_code,
                error_code=code,
                request_id=request_id,
            )
        if response.status_code >= 400:
            raise ContextDBError(
                f"ContextDB HTTP {response.status_code}: {response.text[:200]}",
                status_code=response.status_code,
            )
        if isinstance(payload, dict) and payload.get("errorCode") == 0 and "data" in payload:
            return payload["data"]
        return payload

    def _detail_error(self, response, detail):
        if isinstance(detail, list):
            message = "; ".join(str(item) for item in detail[:5])
        else:
            message = str(detail)
        if response.status_code in (401, 403):
            error_cls = ContextDBAuthError
        elif response.status_code == 409:
            error_cls = ContextDBConflictError
        else:
            error_cls = ContextDBError
        return error_cls(message, status_code=response.status_code, detail=detail)

    # ---------- 知识库 ----------

    def create_knowledge_base(self, name, description=None, *, wiki_enabled=False, graph_enabled=False,
                              review_enabled=False, chunk_size=None, chunk_overlap=None, profile_config=None):
        if wiki_enabled and graph_enabled:
            raise ValueError("wiki_enabled 与 graph_enabled 互斥(ContextDB 契约)")
        body = {"name": name, "wiki_enabled": wiki_enabled, "graph_enabled": graph_enabled,
                "review_enabled": review_enabled}
        if description is not None:
            body["description"] = description
        if chunk_size is not None:
            body["chunk_size"] = int(chunk_size)
        if chunk_overlap is not None:
            body["chunk_overlap"] = int(chunk_overlap)
        if profile_config is not None:
            body["profile_config"] = profile_config
        return self._request("POST", "/v1/knowledge/knowledge_bases", json_body=body)

    def list_knowledge_bases(self, *, page=1, page_size=20):
        return self._request("GET", "/v1/knowledge/knowledge_bases", params={"page": page, "page_size": page_size})

    def find_knowledge_base(self, name):
        """按精确名称在可读知识库中查找;未命中返回 None。"""
        page = 1
        while True:
            result = self.list_knowledge_bases(page=page, page_size=100)
            bases = result.get("knowledge_bases", []) if isinstance(result, dict) else []
            for item in bases:
                if item.get("name") == name:
                    return item
            if len(bases) < 100:
                return None
            page += 1

    def ensure_knowledge_base(self, name, **create_kwargs):
        """按名称幂等获取或创建知识库;返回 KB 对象。"""
        existing = self.find_knowledge_base(name)
        if existing is not None:
            return existing
        return self.create_knowledge_base(name, **create_kwargs)

    def get_knowledge_base(self, kb_id):
        return self._request("GET", "/v1/knowledge/knowledge_bases/detail", params={"knowledge_base_id": kb_id})

    def update_knowledge_base(self, kb_id, *, name=None, description=None, graph_enabled=None, review_enabled=None):
        body = {"knowledge_base_id": kb_id}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if graph_enabled is not None:
            body["graph_enabled"] = graph_enabled
        if review_enabled is not None:
            body["review_enabled"] = review_enabled
        return self._request("PUT", "/v1/knowledge/knowledge_bases", json_body=body)

    def delete_knowledge_base(self, kb_id):
        return self._request("DELETE", "/v1/knowledge/knowledge_bases", params={"knowledge_base_id": kb_id})

    # ---------- 知识文档 ----------

    def create_text_document(self, knowledge_base_id, name, text, *, file_path=None, metadata=None,
                             mime_type=None, source_type=None, review_enabled=None, parent_node_id=None,
                             wait=False, wait_timeout=300.0):
        """创建文本文档;同 file_path+name 为同一逻辑文档,重复创建→1003(需走 PUT 更新)。"""
        body = {"knowledge_base_id": knowledge_base_id, "name": name, "text": text}
        if file_path is not None:
            body["file_path"] = file_path
        if metadata is not None:
            body["metadata"] = metadata
        if mime_type is not None:
            body["mime_type"] = mime_type
        if source_type is not None:
            body["source_type"] = source_type
        if review_enabled is not None:
            body["review_enabled"] = review_enabled
        if parent_node_id is not None:
            body["parent_node_id"] = parent_node_id
        result = self._request("POST", "/v1/knowledge/documents", json_body=body)
        if wait:
            result = self.wait_for_ingest(knowledge_base_id, result["id"], wait_timeout)
        return result

    def update_text_document(self, text, *, document_id=None, knowledge_base_id=None, name=None,
                             file_path=None, metadata=None, wait=False, wait_timeout=300.0):
        """全量替换文档正文;document_id 与逻辑键(kb+name)互斥;不传 metadata 继承旧值。"""
        if document_id is not None:
            if knowledge_base_id is not None or name is not None:
                raise ValueError("document_id 与逻辑键定位互斥(ContextDB 契约)")
            body = {"document_id": document_id, "text": text}
        else:
            if knowledge_base_id is None or name is None:
                raise ValueError("缺少 document_id 或完整逻辑键(knowledge_base_id+name)")
            body = {"knowledge_base_id": knowledge_base_id, "name": name, "text": text}
            if file_path is not None:
                body["file_path"] = file_path
        if metadata is not None:
            body["metadata"] = metadata
        result = self._request("PUT", "/v1/knowledge/documents", json_body=body)
        doc_id = result.get("id") if isinstance(result, dict) else None
        if wait and doc_id and knowledge_base_id is not None:
            result = self.wait_for_ingest(knowledge_base_id, doc_id, wait_timeout)
        return result

    def update_document_metadata(self, metadata, *, document_id=None, knowledge_base_id=None, name=None, file_path=None):
        """单独更新文档元数据(全量覆盖,空对象清空);不触发正文重传——治理状态翻转通道。"""
        if document_id is not None:
            if knowledge_base_id is not None or name is not None:
                raise ValueError("document_id 与逻辑键定位互斥(ContextDB 契约)")
            body = {"document_id": document_id}
        else:
            if knowledge_base_id is None or name is None:
                raise ValueError("缺少 document_id 或完整逻辑键(knowledge_base_id+name)")
            body = {"knowledge_base_id": knowledge_base_id, "name": name}
            if file_path is not None:
                body["file_path"] = file_path
        body["metadata"] = metadata
        return self._request("PUT", "/v1/knowledge/documents/metadata", json_body=body)

    def upload_file(self, knowledge_base_id, name, local_path, *, file_path=None, metadata=None,
                    mime_type=None, review_enabled=None, parent_node_id=None):
        """官方文件上传(multipart POST /v1/knowledge/files);文本/代码类单文件上限 20 MB。

        适用于超过文本通道 200 KB 上限的治理载荷(如大体量版本记录)。
        """
        data = {"knowledge_base_id": knowledge_base_id, "name": name}
        if parent_node_id:
            data['parent_node_id'] = parent_node_id
        if file_path is not None:
            data["file_path"] = file_path
        if metadata is not None:
            data["metadata"] = json.dumps(metadata, ensure_ascii=False)
        if review_enabled is not None:
            data["review_enabled"] = "true" if review_enabled else "false"
        with open(local_path, "rb") as handle:
            files = {"file": (name, handle, mime_type or "application/json")}
            response = self._session.post(
                f"{self.base_url}/v1/knowledge/files",
                data=data,
                files=files,
                headers={"X-API-Key": self.api_key, "Accept": "application/json"},
                timeout=self.timeout,
            )
        return self._payload(response)

    def list_documents(self, knowledge_base_id, *, metadata_condition=None, page=1, page_size=50,
                       sort_by=None, sort_order=None, with_download_url=False):
        params = {"knowledge_base_id": knowledge_base_id, "page": page, "page_size": page_size}
        if metadata_condition is not None:
            params["metadata_condition"] = json.dumps(metadata_condition, ensure_ascii=False)
        if sort_by is not None:
            params["sort_by"] = sort_by
        if sort_order is not None:
            params["sort_order"] = sort_order
        if with_download_url:
            params["with_download_url"] = "true"
        return self._request("GET", "/v1/knowledge/documents", params=params)

    def update_file(self, document_id, name, local_path, *, metadata=None, mime_type=None):
        data = {'document_id': document_id}
        if metadata is not None:
            data['metadata'] = json.dumps(metadata, ensure_ascii=False)
        with open(local_path, 'rb') as handle:
            response = self._session.put(f'{self.base_url}/v1/knowledge/files', data=data,
                files={'file': (name, handle, mime_type or 'application/octet-stream')},
                headers={'X-API-Key': self.api_key, 'Accept': 'application/json'}, timeout=self.timeout)
        return self._payload(response)

    def get_document(self, knowledge_base_id, document_id, *, with_download_url=False):
        params = {"document_id": document_id}
        if knowledge_base_id is not None:
            params["knowledge_base_id"] = knowledge_base_id
        if with_download_url:
            params["with_download_url"] = "true"
        return self._request("GET", "/v1/knowledge/documents/detail", params=params)

    def delete_documents(self, knowledge_base_id, document_ids):
        """批量删除(≤50);ingest 未终态(processing/pending_review)的文档会被拒绝。"""
        ids = list(document_ids)
        if not ids:
            raise ValueError("document_ids 不能为空")
        if len(ids) > 50:
            raise ValueError("单次最多删除 50 个文档(ContextDB 契约)")
        return self._request("DELETE", "/v1/knowledge/documents/batch",
                             json_body={"knowledge_base_id": knowledge_base_id, "ids": ids})

    def download_document_text(self, knowledge_base_id, document_id, *, timeout=None):
        """读取文档正文:detail 取预签名 URL 后下载原文。"""
        detail = self.get_document(knowledge_base_id, document_id, with_download_url=True)
        url = detail.get("download_url") if isinstance(detail, dict) else None
        if not url:
            raise ContextDBError("文档详情未返回 download_url,无法读取正文")
        response = self._session.get(url, timeout=timeout or self.timeout)
        response.raise_for_status()
        try:
            content = response.content.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise ContextDBError('源文档不是有效 UTF-8 文本，请下载原件或在 Wiki 中修订', status_code=415) from exc
        if '\x00' in content:
            raise ContextDBError('源文档包含二进制空字符，不能作为文本读取', status_code=415)
        return content

    def retry_document(self, document_id):
        """官方 POST /v1/knowledge/documents/retry:入库失败文档自动重试(不创建新文档)。"""
        return self._request("POST", "/v1/knowledge/documents/retry",
                             json_body={"document_id": document_id})

    def wait_for_ingest(self, knowledge_base_id, document_id, timeout=300.0, poll_interval=2.0):
        """轮询文档 ingest 至终态(succeeded/failed/pending_review);pending_review 表示等待人工评审。"""
        deadline = time.monotonic() + timeout
        while True:
            document = self.get_document(knowledge_base_id, document_id)
            status = document.get("ingest_status")
            if status in _INGEST_TERMINAL_STATUSES:
                return document
            if time.monotonic() >= deadline:
                raise ContextDBError(f"等待文档 ingest 超时(当前状态: {status})", status_code=408)
            time.sleep(poll_interval)

    # ---------- 检索 ----------

    def query(self, question, *, knowledge_base_ids=None, knowledge_base_names=None, document_ids=None,
              knowledge_view=None, metadata_condition=None, top_k=None, similarity_threshold=None,
              vector_weight=None, rerank=None, query_rewrite=None, context_token_budget=None,
              images=None):
        body = {"question": question}
        if images:
            body["images"] = images
        if knowledge_base_ids:
            body["knowledge_base_ids"] = list(knowledge_base_ids)
        if knowledge_base_names:
            body["knowledge_base_names"] = list(knowledge_base_names)
        if document_ids:
            body["document_ids"] = list(document_ids)
        if knowledge_view is not None:
            if knowledge_view not in KNOWLEDGE_VIEWS:
                raise ValueError(f"knowledge_view 非法: {knowledge_view}")
            body["knowledge_view"] = knowledge_view
        if metadata_condition is not None:
            body["metadata_condition"] = metadata_condition
        if top_k is not None:
            body["top_k"] = int(top_k)
        if similarity_threshold is not None:
            body["similarity_threshold"] = float(similarity_threshold)
        if vector_weight is not None:
            body["vector_weight"] = float(vector_weight)
        if rerank is not None:
            body["rerank"] = bool(rerank)
        if query_rewrite is not None:
            body["query_rewrite"] = bool(query_rewrite)
        if context_token_budget is not None:
            body["context_token_budget"] = int(context_token_budget)
        if not (knowledge_base_ids or knowledge_base_names or document_ids):
            raise ValueError("检索必须限定 knowledge_base_ids / knowledge_base_names / document_ids 之一")
        return self._request("POST", "/v1/knowledge/query", json_body=body)

    # ---------- Wiki ----------

    def list_wiki_pages(self, knowledge_base_id, *, parent_page_id=None, page_type=None, cursor=None, limit=50):
        """分页读取根层或指定目录的直接子项；page_type=category 只列目录。"""
        params = {"knowledge_base_id": knowledge_base_id, "limit": limit}
        if parent_page_id is not None:
            params["parent_page_id"] = parent_page_id
        if page_type is not None:
            params["page_type"] = page_type
        if cursor is not None:
            params["cursor"] = cursor
        return self._request("GET", "/v1/knowledge/wiki/pages", params=params)

    def get_wiki_page(self, knowledge_base_id, page_id):
        return self._request('GET', '/v1/knowledge/wiki/pages/detail',
                             params={'knowledge_base_id': knowledge_base_id, 'page_id': page_id})

    def create_wiki_page(self, knowledge_base_id, title, content):
        """创建人工 Wiki 页;同 title 已存在时 409(identity 冲突)。"""
        return self._request("POST", "/v1/knowledge/wiki/pages",
                             json_body={"knowledge_base_id": knowledge_base_id, "title": title, "content": content})

    def update_wiki_page(self, knowledge_base_id, page_id, content, expected_version):
        """CAS 更新 Wiki 页:expected_version 必须等于当前版本,成功返回新版本。"""
        return self._request("PUT", "/v1/knowledge/wiki/pages",
                             json_body={"knowledge_base_id": knowledge_base_id, "page_id": page_id,
                                        "content": content, "expected_version": int(expected_version)})

    def wiki_search(self, knowledge_base_ids, query, *, mode="keyword", limit=10):
        """页级关键词导航(MCP 工具通道)，有界搜索结果不能作为完整目录。"""
        if mode not in WIKI_SEARCH_MODES:
            raise ValueError(f"mode 非法: {mode}")
        arguments = {"knowledge_base_ids": list(knowledge_base_ids), "query": query, "mode": mode, "limit": int(limit)}
        result = self.mcp_tool_call("knowledge.wiki_search", arguments)
        pages = result.get("pages", []) if isinstance(result, dict) else []
        total = result.get("total", len(pages)) if isinstance(result, dict) else len(pages)
        return {"pages": pages, "total": total}

    # ---------- 知识评审 ----------

    def list_reviews(self, knowledge_base_id=None, *, decision=None, review_status=None, lifecycle_state=None,
                     page=1, page_size=50, sort_by=None, sort_order=None):
        if review_status is not None and lifecycle_state is not None:
            raise ValueError("review_status 与 lifecycle_state 不能同传(ContextDB 契约)")
        params = {"page": page, "page_size": page_size}
        if knowledge_base_id is not None:
            params["knowledge_base_id"] = knowledge_base_id
        if decision is not None:
            params["decision"] = decision
        if review_status is not None:
            params["review_status"] = review_status
        if lifecycle_state is not None:
            params["lifecycle_state"] = lifecycle_state
        if sort_by is not None:
            params["sort_by"] = sort_by
        if sort_order is not None:
            params["sort_order"] = sort_order
        return self._request("GET", "/v1/knowledge/reviews", params=params)

    def get_review(self, review_id, *, content_page=None):
        """评审详情;原文按 3000 字分页,content_page 从 1 开始。"""
        params = {"review_id": review_id}
        if content_page is not None:
            params["content_page"] = content_page
        return self._request("GET", "/v1/knowledge/reviews/detail", params=params)

    def resolve_review_conflicts(self, review_id, resolutions):
        """保存冲突处置草稿;最终放行仍需走评审动作。"""
        return self._request("POST", "/v1/knowledge/reviews/resolve-conflicts",
                             json_body={"review_id": review_id, "resolutions": resolutions})

    def review_action(self, review_id, action, *, edited_content=None, conflict_resolutions=None):
        if action not in REVIEW_ACTIONS:
            raise ValueError(f"action 非法: {action}")
        body = {"review_id": review_id, "action": action}
        if edited_content is not None:
            body["edited_content"] = edited_content
        if conflict_resolutions is not None:
            body["conflict_resolutions"] = conflict_resolutions
        return self._request("POST", "/v1/knowledge/reviews/action", json_body=body)

    def batch_review_action(self, review_ids, action):
        """官方批量评审逐项返回结果，不接收编辑稿或冲突决策。"""
        if not isinstance(action, str) or action not in BATCH_REVIEW_ACTIONS:
            raise ValueError("批量 action 必须是 confirm/force_accept/accept_rewrite/reject/retract/retry_review")
        if not isinstance(review_ids, list) or not 1 <= len(review_ids) <= 50 or not all(
                isinstance(review_id, str) and review_id.strip() for review_id in review_ids):
            raise ValueError("ids 必须是 1～50 个非空评审 ID 的列表")
        return self._request("POST", "/v1/knowledge/reviews/batch",
                             json_body={"action": action, "ids": review_ids})

    # ---------- 评审设置 ----------

    def get_review_settings(self, knowledge_base_id):
        """读取指定知识库的评审开关、自动入库和重写配置。"""
        return self._request("GET", "/v1/knowledge/review_settings",
                             params={"knowledge_base_id": knowledge_base_id})

    def update_review_settings(self, knowledge_base_id, *, review_enabled=None, high_threshold=None,
                               rewrite_enabled=None, conflict_detection_enabled=None,
                               rewrite_auto_ingest_enabled=None, max_rewrite_iterations=None):
        """PATCH /v1/knowledge/review_settings:精调评审阈值与自动重写行为。"""
        body = {"knowledge_base_id": knowledge_base_id}
        for key, value in (("review_enabled", review_enabled),
                           ("high_threshold", high_threshold),
                           ("rewrite_enabled", rewrite_enabled),
                           ("conflict_detection_enabled", conflict_detection_enabled),
                           ("rewrite_auto_ingest_enabled", rewrite_auto_ingest_enabled),
                           ("max_rewrite_iterations", max_rewrite_iterations)):
            if value is not None:
                body[key] = value
        return self._request("PATCH", "/v1/knowledge/review_settings", json_body=body)

    # ---------- 图谱可视化 ----------

    def graph_visual(self, knowledge_base_id, *, document_id=None, entity_id=None,
                     max_hops=None, max_nodes=None, max_edges=None):
        """GET /v1/knowledge/graph-visual:官方节点、关系及查询范围;坐标由前端布局。"""
        params = {"knowledge_base_id": knowledge_base_id}
        if document_id is not None:
            params["document_id"] = document_id
        if entity_id is not None:
            params["entity_id"] = entity_id
        if max_hops is not None:
            params["max_hops"] = int(max_hops)
        if max_nodes is not None:
            params["max_nodes"] = int(max_nodes)
        if max_edges is not None:
            params["max_edges"] = int(max_edges)
        return self._request("GET", "/v1/knowledge/graph-visual", params=params)

    # ---------- 事件列表 ----------

    def list_events(self, *, event_type=None, page=1, page_size=20):
        """GET /v1/events:异步事件列表(可按事件类型过滤)。"""
        params = {"page": page, "page_size": page_size}
        if event_type is not None:
            params["event_type"] = event_type
        return self._request("GET", "/v1/events", params=params)

    # ---------- 异步事件 ----------

    def get_event(self, event_id):
        """查询异步事件状态(PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED)。"""
        return self._request("GET", f"/v1/event/{event_id}")

    def wait_event(self, event_id, timeout=300.0, poll_interval=2.0):
        """轮询事件至终态;超时抛 ContextDBError 并保留最后状态。"""
        deadline = time.monotonic() + timeout
        while True:
            event = self.get_event(event_id)
            status = event.get("status")
            if status in _EVENT_TERMINAL_STATUSES:
                return event
            if time.monotonic() >= deadline:
                raise ContextDBError(f"等待事件超时(当前状态: {status})", status_code=408)
            time.sleep(poll_interval)

    # ---------- MCP ----------

    def mcp_tool_call(self, name, arguments):
        """调用 /v1/mcp 原生工具(如 knowledge.wiki_search);返回 content text 解析结果。"""
        self._mcp_call_id += 1
        payload = {"jsonrpc": "2.0", "id": self._mcp_call_id,
                   "method": "tools/call", "params": {"name": name, "arguments": arguments}}
        response = self._session.post(
            f"{self.base_url}/v1/mcp",
            json=payload,
            headers={"X-API-Key": self.api_key, "Accept": "application/json, text/event-stream"},
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            raise ContextDBError(f"MCP HTTP {response.status_code}: {response.text[:200]}",
                                 status_code=response.status_code)
        result = _parse_mcp_response(response)
        if result.get("error") is not None:
            raise ContextDBError(f"MCP 调用失败: {result['error']}")
        tool_result = result.get("result", {})
        if tool_result.get("isError"):
            raise ContextDBError(f"MCP 工具 {name} 执行失败")
        for item in tool_result.get("content", []):
            if item.get("type") == "text":
                text = item.get("text", "")
                try:
                    return json.loads(text)
                except ValueError:
                    return text
        return tool_result

    # ---------- 健康 ----------

    def ping(self):
        """官方连通性检查(GET /v1/ping)。"""
        return self._request("GET", "/v1/ping")


def _parse_mcp_response(response):
    content_type = response.headers.get("Content-Type", "")
    if content_type.startswith("text/event-stream"):
        for line in response.text.splitlines():
            if line.startswith("data:"):
                try:
                    return json.loads(line[len("data:"):].strip())
                except ValueError:
                    continue
        raise ContextDBError("MCP SSE 响应解析失败")
    try:
        return response.json()
    except ValueError as exc:
        raise ContextDBError(f"MCP 响应解析失败: {exc}") from exc
