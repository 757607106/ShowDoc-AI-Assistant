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

    def test_detects_collapsed_markdown_structure(self):
        document = SimpleNamespace(
            id="showdoc-1",
            title="操作手册",
            category="根目录",
            markdown=(
                "## 第一章 " + "正文内容" * 150 + " ### 第二章 后续正文"
            ),
            resources={"images": [], "links": []},
        )

        report = assess_documents([document])

        self.assertEqual(report["summary"]["error_documents"], 1)
        self.assertIn(
            "collapsed_markdown_structure",
            [issue["rule"] for issue in report["documents"][0]["issues"]],
        )

    def test_does_not_treat_code_as_collapsed_structure(self):
        document = SimpleNamespace(
            id="code-1",
            title="代码示例",
            category="教程",
            markdown=(
                "## 示例\n\n```text\n"
                + "正文内容" * 150
                + " ### 这是代码而不是标题\n```"
            ),
            resources={"images": [], "links": []},
        )

        report = assess_documents([document])

        self.assertNotIn(
            "collapsed_markdown_structure",
            [issue["rule"] for issue in report["documents"][0]["issues"]],
        )


if __name__ == "__main__":
    unittest.main()
