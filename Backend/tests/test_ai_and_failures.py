"""
Unit tests for AI response parser, GPU manager, and failure resilience.
"""
import unittest
from ai.response_parser import ResponseParser
from ai.gpu_manager import GPUManager
from ai.ollama_client import OllamaClient


class TestAIAndFailures(unittest.IsolatedAsyncioTestCase):

    def test_response_parser_clean_json(self):
        json_str = '{"message": "Hello friend!", "expression": "happy", "animation": "wave", "speak": true}'
        resp = ResponseParser.parse(json_str)
        self.assertEqual(resp.message, "Hello friend!")
        self.assertEqual(resp.expression, "happy")
        self.assertEqual(resp.animation, "wave")

    def test_response_parser_markdown_fence(self):
        fenced_str = """
        Here is my response:
        ```json
        {
          "message": "Nice work on the code!",
          "expression": "excited",
          "animation": "celebrate",
          "speak": true
        }
        ```
        """
        resp = ResponseParser.parse(fenced_str)
        self.assertEqual(resp.message, "Nice work on the code!")
        self.assertEqual(resp.expression, "excited")

    def test_response_parser_raw_text_fallback(self):
        raw_text = "Haha that was so funny and awesome!"
        resp = ResponseParser.parse(raw_text)
        self.assertEqual(resp.message, raw_text)
        self.assertEqual(resp.expression, "happy")

    def test_gpu_manager(self):
        # Should execute without throwing error on any machine
        GPUManager.clear_cache()
        telemetry = GPUManager.get_vram_telemetry()
        self.assertIn("cuda_available", telemetry)
        GPUManager.handle_cuda_oom("test_operation")

    async def test_ollama_offline_resilience(self):
        # Point to unreachable port
        dummy_client = OllamaClient(host="http://127.0.0.1:59999")
        health = dummy_client.check_health()
        self.assertFalse(health["online"])

        chat_res = await dummy_client.chat(messages=[{"role": "user", "content": "Hi"}])
        self.assertFalse(chat_res["success"])
        self.assertIn("error", chat_res)


if __name__ == "__main__":
    unittest.main()
