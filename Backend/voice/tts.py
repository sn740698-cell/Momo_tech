"""
Local Text-to-Speech (TTS) Engine for MOMO.
Synthesizes text into offline .wav audio using Windows SAPI5 / pyttsx3.
"""
import os
import io
import re
import tempfile
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class TextToSpeech:
    """
    Synthesizes speech audio from text using local offline engines.
    """

    def __init__(self, rate: int = 175, volume: float = 1.0):
        self.rate = rate
        self.volume = volume

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Strips markdown, emojis, and code fences so speech sounds natural.
        """
        cleaned = re.sub(r"```[\s\S]*?```", "Code snippet omitted.", text)
        cleaned = re.sub(r"[*_#`~>\[\]]", "", cleaned)
        cleaned = re.sub(r"https?://\S+", "link", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def get_available_voices(self) -> List[Dict[str, str]]:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            result = []
            for v in voices:
                result.append({
                    "id": v.id,
                    "name": v.name,
                    "languages": getattr(v, 'languages', []),
                    "gender": getattr(v, 'gender', 'unknown')
                })
            engine.stop()
            return result
        except Exception as e:
            logger.warning(f"Error fetching TTS voices: {e}")
            return [{"id": "default", "name": "Default System Voice"}]

    def synthesize(self, text: str, voice_id: Optional[str] = None) -> Optional[bytes]:
        """
        Synthesizes text into WAV audio bytes.
        """
        if not text or not text.strip():
            return None

        clean = self.clean_text(text)
        if not clean:
            return None

        logger.info(f"Synthesizing speech for: '{clean[:40]}...'")

        try:
            import pyttsx3
            # Initialize engine per synthesis to ensure thread safety
            engine = pyttsx3.init()
            engine.setProperty('rate', self.rate)
            engine.setProperty('volume', self.volume)

            if voice_id:
                engine.setProperty('voice', voice_id)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                temp_path = tf.name

            try:
                engine.save_to_file(clean, temp_path)
                engine.runAndWait()
                engine.stop()

                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    with open(temp_path, "rb") as f:
                        audio_data = f.read()
                    return audio_data
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Local pyttsx3 synthesis error: {e}")

        # Fallback empty wave container for testing/resilience
        return self._generate_fallback_wav()

    def _generate_fallback_wav(self) -> bytes:
        """
        Generates a 44-byte silent PCM WAV header as safe fallback.
        """
        buf = io.BytesIO()
        buf.write(b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00')
        return buf.getvalue()

    synthesize_wav = synthesize


momo_tts = TextToSpeech()
