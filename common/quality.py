"""轻量级文档质量检查。

质量检查只做本地、确定性检查，不对每个链接发起网络请求，避免大批量任务
因为探测链接而显著变慢。原始文档仍然保留，报告只描述问题，不修改正文。
"""

import hashlib
import re

from common.converter import clean_markdown_for_rag


def _issue(rule, severity, message):
    return {"rule": rule, "severity": severity, "message": message}


def _normalized_text(markdown):
    return re.sub(r"\s+", " ", clean_markdown_for_rag(markdown)).strip().casefold()


def _markdown_body_lines(markdown):
    """迭代非围栏代码行，避免把代码示例误判成正文结构。"""
    in_code_block = False
    fence_character = ""
    fence_length = 0
    for line in (markdown or "").splitlines():
        fence = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if fence:
            marker = fence.group(1)
            if not in_code_block:
                in_code_block = True
                fence_character = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_character and len(marker) >= fence_length:
                in_code_block = False
                fence_character = ""
                fence_length = 0
            continue
        if not in_code_block:
            yield line


def _heading_issues(markdown):
    issues = []
    previous_level = 0
    for line in _markdown_body_lines(markdown):
        match = re.match(r"^(#{1,6})\s+\S", line.strip())
        if not match:
            continue
        level = len(match.group(1))
        if previous_level and level > previous_level + 1:
            issues.append(
                _issue(
                    "heading_level",
                    "warning",
                    f"标题层级从 H{previous_level} 跳到了 H{level}",
                )
            )
        previous_level = level
    return issues


def _structure_issues(markdown, resources=None):
    issues = []
    content = markdown or ""
    collapsed = False
    body_lines = list(_markdown_body_lines(content))
    for line in body_lines:
        if (
            len(line) > 500
            and re.match(r"^#{1,6}\s+\S", line)
            and re.search(r"\S[ \t]+#{1,6}\s+\S", line)
        ):
            collapsed = True
            break
    if collapsed:
        issues.append(
            _issue(
                "collapsed_markdown_structure",
                "error",
                "正文疑似被压缩成单行，章节标题未被 Markdown 解析器识别",
            )
        )
    if any(re.match(r"^#\s+\S", line) for line in body_lines):
        issues.append(
            _issue(
                "body_h1",
                "warning",
                "正文包含 H1；单篇文档的 H1 应仅用于文档标题",
            )
        )
    for kind, items in (resources or {}).items():
        for item in items:
            url = item.get("url") or ""
            if url and url not in content:
                issues.append(
                    _issue(
                        "missing_resource",
                        "error",
                        f"{kind} 资源未出现在 Markdown 正文中: {url}",
                    )
                )
    return issues


def assess_documents(documents):
    """返回文档级问题和汇总指标，保持 O(n) 复杂度。"""
    normalized_by_hash = {}
    results = []
    results_by_id = {}
    counts = {"error": 0, "warning": 0, "info": 0}

    for document in documents:
        content = clean_markdown_for_rag(document.markdown or "")
        issues = []
        if not str(document.id).strip():
            issues.append(_issue("document_id", "error", "缺少文档 ID"))
        if not str(document.title or "").strip():
            issues.append(_issue("title", "error", "缺少文档标题"))
        if not content:
            issues.append(_issue("empty_content", "error", "正文为空"))
        elif len(content) < 40:
            issues.append(_issue("short_content", "warning", "正文少于 40 个字符"))

        metadata = getattr(document, "metadata", {}) or {}
        for field in ("fetch_error", "conversion_error"):
            if metadata.get(field):
                issues.append(_issue(field, "error", str(metadata[field])))
        if metadata.get("content_completeness") in {"summary", "unknown"}:
            issues.append(_issue("content_completeness", "warning", "尚未验证为详情全文"))
        if metadata.get("resource_errors"):
            issues.append(_issue("resource_download", "warning", "部分资源下载失败，请检查 metadata.resource_errors"))
        issues.extend(_heading_issues(content))
        issues.extend(
            _structure_issues(content, getattr(document, "resources", None))
        )

        normalized = _normalized_text(content)
        content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest() if normalized else ""
        if content_hash:
            normalized_by_hash.setdefault(content_hash, []).append(str(document.id))

        for issue in issues:
            counts[issue["severity"]] += 1

        results.append(
            {
                "document_id": str(document.id),
                "title": document.title,
                "category": document.category,
                "status": "error" if any(i["severity"] == "error" for i in issues) else (
                    "warning" if issues else "passed"
                ),
                "content_length": len(content),
                "issues": issues,
            }
        )

    for result in results:
        results_by_id.setdefault(result["document_id"], []).append(result)
    duplicate_ids = set()
    for ids in normalized_by_hash.values():
        if len(ids) < 2:
            continue
        duplicate_ids.update(ids)
        for document_id in set(ids):
            for result in results_by_id[document_id]:
                result["issues"].append(
                    _issue("duplicate_content", "warning", "与其他文档正文完全重复")
                )
                if result["status"] == "passed":
                    result["status"] = "warning"
                counts["warning"] += 1

    total = len(documents)
    error_docs = sum(result["status"] == "error" for result in results)
    warning_docs = sum(result["status"] == "warning" for result in results)
    valid_docs = total - error_docs
    score = round(max(0, 100 * (valid_docs - warning_docs * 0.08) / total), 1) if total else 0.0
    return {
        "version": 1,
        "summary": {
            "documents": total,
            "valid_documents": valid_docs,
            "error_documents": error_docs,
            "warning_documents": warning_docs,
            "duplicate_documents": len(duplicate_ids),
            "quality_score": score,
            "valid_content_percent": round(100 * valid_docs / total, 2) if total else 0.0,
            "issue_counts": counts,
        },
        "documents": results,
    }
