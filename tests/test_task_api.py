import unittest
from unittest.mock import patch

import app as app_module


class TaskApiTests(unittest.TestCase):
    def setUp(self):
        app_module.tasks.clear()
        app_module.app.config.update(TESTING=True)
        self.client = app_module.app.test_client()

    def tearDown(self):
        app_module.tasks.clear()

    def make_task(self, status="running"):
        task = app_module.CrawlerTask(
            "task-1",
            "showdoc",
            params={"item_id": "412", "user_token": "secret"},
            selected_ids=["1", "2"],
        )
        task.status = status
        task.phase = "crawling" if status == "running" else status
        task.message = "正在抓取: 示例文档"
        task.total_pages = 2
        task.completed_pages = 1
        task.add_log(task.message)
        app_module.tasks[task.task_id] = task
        return task

    def test_task_list_does_not_expose_crawler_credentials(self):
        self.make_task()

        response = self.client.get("/api/tasks")
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["tasks"][0]["task_id"], "task-1")
        self.assertNotIn("params", payload["tasks"][0])
        self.assertNotIn("secret", response.get_data(as_text=True))

    def test_cancel_marks_task_and_sets_cancel_event(self):
        task = self.make_task()

        response = self.client.post("/tasks/task-1/cancel")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(task.status, "cancelling")
        self.assertTrue(task.cancel_event.is_set())

    def test_progress_callback_stops_at_cancel_checkpoint(self):
        task = self.make_task()
        task.cancel_event.set()

        with self.assertRaises(app_module.TaskCancelled):
            app_module.update_task_progress(task, 2, 2, "已抓取: 第二篇")

    def test_retry_clones_failed_task_without_exposing_parameters(self):
        task = self.make_task(status="failed")
        with patch.object(app_module.threading.Thread, "start"):
            response = self.client.post(f"/tasks/{task.task_id}/retry")

        payload = response.get_json()
        retried = app_module.tasks[payload["task_id"]]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(retried.retry_of, task.task_id)
        self.assertEqual(retried.params, task.params)
        self.assertNotEqual(retried.task_id, task.task_id)

    def test_new_start_is_rejected_while_another_task_is_active(self):
        self.make_task()

        response = self.client.post(
            "/entries/showdoc/start",
            json={"item_id": "412"},
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("已有", response.get_json()["message"])


if __name__ == "__main__":
    unittest.main()
