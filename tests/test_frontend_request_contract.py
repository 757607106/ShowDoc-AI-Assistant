import re
import unittest
from pathlib import Path


APP_JS = Path(__file__).resolve().parents[1] / "static" / "js" / "app.js"


class FrontendRequestContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = APP_JS.read_text(encoding="utf-8")

    def function_body(self, name):
        match = re.search(
            rf"    function {re.escape(name)}\([^)]*\) \{{(.*?)\n    \}}",
            self.source,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match, f"未找到前端函数: {name}")
        return match.group(1)

    def test_web_document_request_includes_current_url(self):
        body = self.function_body("buildDocumentsUrl")
        self.assertIn('state.source === "web"', body)
        self.assertIn('params.set("url", $("#webUrl").value.trim())', body)
        self.assertIn('params.set("crawl_mode", $("#webCrawlMode").value)', body)
        self.assertIn('params.set("max_pages", $("#webMaxPages").value || "0")', body)

    def test_web_preview_request_includes_current_url(self):
        body = self.function_body("previewUrl")
        self.assertIn('key === "web"', body)
        self.assertIn('params.set("url", $("#webUrl").value.trim())', body)
        self.assertIn('params.set("crawl_mode", $("#webCrawlMode").value)', body)

    def test_web_strategy_is_inspected_before_start(self):
        self.assertIn("/entries/web/inspect?url=", self.source)
        self.assertIn("scheduleWebStrategyInspection", self.source)


if __name__ == "__main__":
    unittest.main()
