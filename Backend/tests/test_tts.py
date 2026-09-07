import os
import unittest
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from rest_framework.test import APIClient
from voice.tts import momo_tts

class TestTTS(unittest.TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_tts_engine_voices(self):
        voices = momo_tts.get_available_voices()
        self.assertIsInstance(voices, list)
        if voices:
            self.assertIn("id", voices[0])
            self.assertIn("name", voices[0])

    def test_tts_engine_synthesize_wav(self):
        wav_bytes = momo_tts.synthesize_wav("Hello from MOMO companion.")
        if wav_bytes is not None:
            self.assertIsInstance(wav_bytes, bytes)
            self.assertGreater(len(wav_bytes), 0)

    def test_tts_voices_api(self):
        response = self.client.get("/api/tts/voices/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("voices", data)
        self.assertIn("count", data)

    def test_tts_synthesize_api_empty_text(self):
        response = self.client.post("/api/tts/", {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_tts_synthesize_api_success(self):
        response = self.client.post("/api/tts/", {"text": "Testing MOMO voice synthesis"}, format="json")
        self.assertIn(response.status_code, [200, 503])
        if response.status_code == 200:
            self.assertEqual(response["Content-Type"], "audio/wav")

if __name__ == "__main__":
    unittest.main()
