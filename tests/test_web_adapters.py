import unittest

from crawlers.web_adapters import ClubCmgraspAdapter, describe_web_strategy


class ClubAdapterTests(unittest.TestCase):
    def make_adapter(self, max_documents=0):
        adapter = ClubCmgraspAdapter(
            "http://club.cmgrasp.com/", max_documents=max_documents
        )

        def fake_post(endpoint, payload):
            if endpoint == "question/list":
                if payload["pn"] == 1:
                    return {
                        "data": [
                            {
                                "id": 10,
                                "title": "库存为什么不一致",
                                "content": "<p>问题正文</p>",
                                "answerCount": 1,
                                "createTime": 1700000000000,
                            }
                        ],
                        "total": 1,
                    }
                return {"data": [], "total": 1}
            if endpoint.startswith("answer/list"):
                return {
                    "data": [
                        {
                            "id": 20,
                            "authorName": "客服",
                            "content": "<p>回答正文</p>",
                        }
                    ],
                    "total": 1,
                }
            return {"data": [], "total": 0}

        adapter._post = fake_post
        return adapter

    def test_strategy_recognizes_verified_site(self):
        info = describe_web_strategy("http://club.cmgrasp.com/")
        self.assertEqual(info["strategy"], "adapter")
        self.assertEqual(info["adapter"], "club_cmgrasp")

    def test_adapter_lists_public_records_and_includes_answers(self):
        adapter = self.make_adapter()
        stubs = adapter.list_documents()
        self.assertEqual(len(stubs), 1)
        self.assertEqual(stubs[0].id, "question:10")

        document = adapter.fetch_document(stubs[0])
        self.assertIn("问题正文", document.content)
        self.assertIn("回答正文", document.content)
        self.assertEqual(document.metadata["adapter"], "club_cmgrasp")
        self.assertIn("?id=10", document.metadata["url"])

    def test_document_limit_stops_directory_collection(self):
        adapter = self.make_adapter(max_documents=1)
        self.assertEqual(len(adapter.list_documents()), 1)
        self.assertEqual(adapter.stats["question"]["reported_total"], 1)
        self.assertEqual(
            set(adapter.stats), {"question", "knowledge", "course", "activity", "news"}
        )


if __name__ == "__main__":
    unittest.main()
