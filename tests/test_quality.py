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
        self.assertEqual(report["summary"]["quality_score"], 83.0)


if __name__ == "__main__":
    unittest.main()
