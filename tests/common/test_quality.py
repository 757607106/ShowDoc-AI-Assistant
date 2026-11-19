import unittest
from types import SimpleNamespace

from common.quality import assess_documents


class QualityTests(unittest.TestCase):
    def test_detects_empty_and_duplicate_documents(self):
        documents = [
            SimpleNamespace(
                id="1",
                title="库存查询",
                category="教程",
                markdown="# 库存查询\n\n这是用于质量检查的有效正文内容。",
            ),
            SimpleNamespace(
                id="2",
                title="库存查询副本",
                category="教程",
                markdown="# 库存查询\n\n这是用于质量检查的有效正文内容。",
            ),
            SimpleNamespace(
                id="3",
                title="空页面",
                category="教程",
                markdown="",
            ),
        ]

        report = assess_documents(documents)

        self.assertEqual(report["summary"]["documents"], 3)
        self.assertEqual(report["summary"]["error_documents"], 1)
        self.assertEqual(report["summary"]["duplicate_documents"], 2)
        self.assertEqual(report["summary"]["quality_score"], 61.3)

    def test_empty_source_is_reported_once_as_collection_issue(self):
        document = SimpleNamespace(
            id="empty-source",
            title="空源文档",
            category="教程",
            content="",
            source_format="markdown",
            markdown="",
            metadata={
                "conversion_error": "MarkdownValidationError: 正文为空",
            },
        )

        report = assess_documents([document])

        summary = report["summary"]
        self.assertEqual(summary["error_documents"], 1)
        self.assertEqual(summary["empty_documents"], 1)
        self.assertEqual(summary["source_empty_documents"], 1)
        self.assertEqual(summary["issue_counts"]["error"], 1)
        self.assertEqual(summary["issue_document_counts"]["source_empty"], 1)
        self.assertEqual(report["documents"][0]["issues"][0]["rule"], "source_empty")

    def test_issue_counts_and_affected_document_counts_are_separate(self):
        document = SimpleNamespace(
            id="one",
            title="短文档",
            category="教程",
            markdown="短正文",
            resources={"images": [], "links": []},
        )

        report = assess_documents([document])

        self.assertEqual(report["summary"]["issue_counts"]["warning"], 1)
        self.assertEqual(report["summary"]["issue_document_counts"]["short_content"], 1)

    def test_low_parse_confidence_is_visible_and_not_semantic_accuracy(self):
        document = SimpleNamespace(id="1", title="扫描件", category="教程", markdown="完整正文" * 20,
            metadata={"conversion": {"confidence": {"low_grade": "poor"}}})
        report = assess_documents([document])
        self.assertEqual(report["summary"]["error_documents"], 0)
        self.assertIn("parse_confidence", [issue["rule"] for issue in report["documents"][0]["issues"]])


if __name__ == "__main__":
    unittest.main()
