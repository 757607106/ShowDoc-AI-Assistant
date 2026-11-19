import json
import unittest

from crawlers.web_discovery import infer_pagination_plans, paginate_plan


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append((url, json, headers, timeout))
        return FakeResponse(self.pages.get(json["pn"], {"result": {"data": []}}))


class WebDiscoveryTests(unittest.TestCase):
    @staticmethod
    def exchange(path="question/list"):
        url = f"https://example.test/api/{path}"
        return [
            {
                "event_type": "request",
                "url": url,
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "must-not-be-replayed",
                },
                "post_data": json.dumps({"pn": 1, "ps": 2}),
            },
            {
                "event_type": "response",
                "url": url,
                "status": 200,
                "headers": {"content-type": "application/json;charset=UTF-8"},
                "body": {
                    "text": json.dumps(
                        {"result": {"data": [{"id": 1}, {"id": 2}], "total": 3}}
                    )
                },
            },
        ]

    def test_infers_and_replays_same_origin_read_only_pagination(self):
        plans = infer_pagination_plans(self.exchange(), "https://example.test/")
        self.assertEqual(len(plans), 1)
        plan = plans[0]
        self.assertEqual(plan.page_key, "pn")
        self.assertEqual(plan.total, 3)
        self.assertNotIn("Authorization", plan.headers)

        session = FakeSession(
            {2: {"result": {"data": [{"id": 3}], "total": 3}}}
        )
        result = paginate_plan(session, plan)
        self.assertEqual([item["id"] for item in result.records], [1, 2, 3])
        self.assertTrue(result.complete)
        self.assertEqual(session.calls[0][1]["pn"], 2)

    def test_rejects_write_endpoint_and_cross_origin_response(self):
        self.assertEqual(
            infer_pagination_plans(
                self.exchange("question/update"), "https://example.test/"
            ),
            [],
        )
        self.assertEqual(
            infer_pagination_plans(self.exchange(), "https://other.test/"),
            [],
        )
        self.assertEqual(
            infer_pagination_plans(self.exchange(), "https://example.test:8443/"),
            [],
        )


if __name__ == "__main__":
    unittest.main()
