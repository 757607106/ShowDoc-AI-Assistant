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


def _heading_issues(markdown):
    issues = []
    previous_level = 0
    for line in (markdown or "").splitlines():
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


def assess_documents(documents):
    """返回文档级问题和汇总指标，保持 O(n) 复杂度。"""
    normalized_by_hash = {}
    results = []
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

        issues.extend(_heading_issues(content))

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

    duplicate_ids = set()
    for ids in normalized_by_hash.values():
        if len(ids) < 2:
            continue
        duplicate_ids.update(ids)
        for result in results:
            if result["document_id"] in ids:
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
    score = round(max(0, 100 - (error_docs / total * 35 if total else 0) - (warning_docs / total * 8 if total else 0)), 1)
    return {
        "version": 1,
        "summary": {
            "documents": total,
            "valid_documents": valid_docs,
            "error_documents": error_docs,
            "warning_documents": warning_docs,
            "duplicate_documents": len(duplicate_ids),
            "quality_score": score,
            "issue_counts": counts,
        },
        "documents": results,
    }
