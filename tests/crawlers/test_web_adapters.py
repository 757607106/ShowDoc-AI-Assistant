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

    def test_selected_scope_cannot_silently_drop_missing_ids(self):
        adapter = self.make_adapter()
        with self.assertRaisesRegex(ValueError, '采集范围不完整'):
            adapter.crawl_documents(selected_ids=['question:10', 'question:missing'])

    def test_repeated_list_page_is_incomplete_instead_of_reaching_total(self):
        adapter = self.make_adapter()
        adapter.page_size = 1
        adapter._post = lambda *args: {"data": [{"id": 10}], "total": 2}

        records = adapter._load_endpoint("question/list", "社区问答", "question")

        self.assertEqual(len(records), 1)
        self.assertFalse(adapter.stats["question"]["complete"])
        self.assertEqual(adapter.stats["question"]["stop_reason"], "duplicate_page")

    def test_answers_without_total_continue_beyond_first_page(self):
        adapter = self.make_adapter()
        pages = {
            1: {"data": [{"id": 20}, {"id": 21}]},
            2: {"data": [{"id": 22}]},
            3: {"data": []},
        }
        adapter._post = lambda endpoint, payload: pages[payload["pn"]]

        answers, complete, stop_reason = adapter._fetch_answers(10, expected_count=3)

        self.assertEqual([item["id"] for item in answers], [20, 21, 22])
        self.assertTrue(complete)
        self.assertEqual(stop_reason, "total_reached")

    def test_missing_answers_mark_the_question_as_incomplete(self):
        adapter = self.make_adapter()
        stub = adapter.list_documents()[0]
        adapter._post = lambda *args: {"data": []}

        document = adapter.fetch_document(stub)

        self.assertFalse(document.metadata["answers_complete"])
        self.assertIn("预期 1 条，实际 0 条", document.metadata["resource_errors"][0]["error"])
        self.assertEqual(document.metadata["resource_errors"][0]["kind"], "answers")


if __name__ == "__main__":
    unittest.main()
