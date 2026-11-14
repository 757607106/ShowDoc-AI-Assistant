"""轻量级文档质量检查。

质量检查只做本地、确定性检查，不对每个链接发起网络请求，避免大批量任务
因为探测链接而显著变慢。原始文档仍然保留，报告只描述问题，不修改正文。
"""

import hashlib

def _issue(rule, severity, message):
    return {"rule": rule, "severity": severity, "message": message}


def _source_has_content(document):
    if getattr(document, "source_path", ""):
        return True
    return bool(getattr(document, "content", "").strip()) if hasattr(document, "content") else None


def assess_documents(documents):
    """返回文档级问题和汇总指标，保持 O(n) 复杂度。"""
    normalized_by_hash = {}
    results = []
    results_by_id = {}
    counts = {"error": 0, "warning": 0, "info": 0}
    source_empty_documents = 0
    empty_documents = 0

    for document in documents:
        content = document.markdown or ""
        issues = []
        if not str(document.id).strip():
            issues.append(_issue("document_id", "error", "缺少文档 ID"))
        if not str(document.title or "").strip():
            issues.append(_issue("title", "error", "缺少文档标题"))
        source_has_content = _source_has_content(document)
        if source_has_content is False:
            source_empty_documents += 1

        metadata = getattr(document, "metadata", {}) or {}
        if metadata.get("fetch_error"):
            issues.append(_issue("fetch_error", "error", str(metadata["fetch_error"])))
        if not content:
            empty_documents += 1
            if metadata.get("fetch_error"):
                pass
            elif source_has_content is False:
                issues.append(
                    _issue("source_empty", "error", "采集到的源正文为空，无法生成 Markdown")
                )
            else:
                issues.append(_issue("empty_content", "error", "规范正文为空"))
        elif len(content) < 40:
            issues.append(_issue("short_content", "warning", "正文少于 40 个字符"))

        # Empty source/fetch failures are the root cause.  The converter also
        # records a derived conversion_error for those records; reporting both
        # made one failed document look like two quality errors.
        if metadata.get("conversion_error") and not (
            not content and (source_has_content is False or metadata.get("fetch_error"))
        ):
            issues.append(
                _issue("conversion_error", "error", str(metadata["conversion_error"]))
            )
        if metadata.get("content_completeness") in {"summary", "unknown"}:
            issues.append(_issue("content_completeness", "warning", "尚未验证为详情全文"))
        if metadata.get("resource_errors"):
            issues.append(_issue("resource_download", "warning", "部分资源下载失败，请检查 metadata.resource_errors"))
        conversion = metadata.get("conversion", {})
        confidence = conversion.get("confidence", {})
        if str(confidence.get("low_grade", "")).lower() in {"poor", "fair"}:
            issues.append(_issue("parse_confidence", "warning", "部分页面的解析置信等级较低，请核对原文"))

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest() if content.strip() else ""
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
                "source_format": getattr(document, "source_format", ""),
                "source_content_length": (
                    len(str(getattr(document, "content")))
                    if hasattr(document, "content") and getattr(document, "content") is not None
                    else None
                ),
                "source_content_present": source_has_content,
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
    passed_docs = sum(result["status"] == "passed" for result in results)
    issue_document_counts = {}
    for result in results:
        for issue in result["issues"]:
            issue_document_counts.setdefault(issue["rule"], set()).add(
                result["document_id"]
            )
    valid_docs = total - error_docs
    score = round(max(0, 100 * (valid_docs - warning_docs * 0.08) / total), 1) if total else 0.0
    return {
        "version": 2,
        "summary": {
            "documents": total,
            "valid_documents": valid_docs,
            "exported_documents": valid_docs,
            "passed_documents": passed_docs,
            "error_documents": error_docs,
            "warning_documents": warning_docs,
            "empty_documents": empty_documents,
            "source_empty_documents": source_empty_documents,
            "duplicate_documents": len(duplicate_ids),
            "quality_score": score,
            "valid_content_percent": round(100 * valid_docs / total, 2) if total else 0.0,
            "issue_counts": counts,
            # issue_counts counts issue instances; this counts affected docs.
            # They intentionally differ when one document has multiple issues.
            "issue_document_counts": {
                rule: len(document_ids)
                for rule, document_ids in issue_document_counts.items()
            },
        },
        "documents": results,
    }
