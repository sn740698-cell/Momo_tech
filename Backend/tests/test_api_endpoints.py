"""
Unit tests for MOMO REST API endpoints:
- /api/vision/status/
- /api/vision/capture/
- /api/vision/preview/
- /api/automation/games/
- /api/automation/motivate/
- /api/automation/launch_game/
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import unittest
from django.test import Client
from security.permissions import PermissionManager


from unittest.mock import patch
from vision.camera import CameraManager


class TestApiEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = Client()
        PermissionManager.set_permission("camera", True)
        self.mock_frame = CameraManager.generate_mock_face_frame("happy")
        self.cam_patcher = patch("api.views._api_camera_manager.read_frame", return_value=(True, self.mock_frame))
        self.cam_patcher.start()

    def tearDown(self):
        self.cam_patcher.stop()

    def test_vision_status_endpoint(self):
        response = self.client.get("/api/vision/status/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("face_detected", data)
        self.assertIn("emotion", data)
        self.assertIn("work_duration_minutes", data)

    def test_vision_capture_endpoint(self):
        response = self.client.post("/api/vision/capture/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("analysis", data)

    def test_vision_preview_endpoint(self):
        response = self.client.get("/api/vision/preview/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertGreater(len(response.content), 500)

    def test_automation_games_endpoint(self):
        response = self.client.get("/api/automation/games/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("games", data)
        self.assertIn("2048", data["games"])

    def test_automation_motivate_endpoint(self):
        response = self.client.get("/api/automation/motivate/?game=2048")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("motivation", data)
        self.assertEqual(data["expression"], "excited")

    @patch("webbrowser.open", return_value=True)
    def test_automation_launch_game_endpoint(self, mock_browser):
        import json
        response = self.client.post(
            "/api/automation/launch_game/",
            data=json.dumps({"game": "2048"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "launched")
        self.assertEqual(data["game"], "2048")

    def test_api_chat_endpoint(self):
        import json
        response = self.client.post(
            "/api/chat/",
            data=json.dumps({"message": "Hello Momo!"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertIn("expression", data)
        self.assertIn("animation", data)
        self.assertIn("model", data)
        self.assertGreater(len(data["message"]), 2)

    @patch("ai_workflow.services.web_crawler_service.LiveWebCrawlerService.crawl_url")
    def test_crawler_crawl_endpoint(self, mock_crawl):
        import json
        mock_crawl.return_value = {
            "url": "https://example.com",
            "title": "Example Domain",
            "content": "Example Domain contents...",
            "status": "success",
            "crawler": "crawl4ai"
        }
        response = self.client.post(
            "/api/crawler/crawl/",
            data=json.dumps({"url": "https://example.com"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["url"], "https://example.com")

    @patch("ai_workflow.services.web_crawler_service.LiveWebCrawlerService.gather_realtime_context")
    def test_crawler_search_endpoint(self, mock_search):
        import json
        mock_search.return_value = [
            {
                "title": "Python 3.12 Features",
                "url": "https://en.wikipedia.org/wiki/Python",
                "source": "Wikipedia Knowledge",
                "pub_date": "Verified",
                "snippet": "Python is a high-level programming language.",
                "content": "Python is a high-level programming language."
            }
        ]
        response = self.client.post(
            "/api/crawler/search/",
            data=json.dumps({"query": "Python"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["query"], "Python")
        self.assertEqual(data["count"], 1)


if __name__ == "__main__":
    unittest.main()
