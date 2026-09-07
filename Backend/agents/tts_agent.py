"""
Text-to-Speech Agent for MOMO.
Synthesizes speech audio from MOMO response using local neural Piper interfaces.
"""
import logging
from typing import Dict, Any
from asgiref.sync import sync_to_async

from graph.state import MomoState
from voice.tts import TextToSpeech

logger = logging.getLogger(__name__)


class TTSAgent:
    """
    Handles speech synthesis for MOMO responses.
    """

    def __init__(self):
        self.tts = TextToSpeech()

    async def run(self, state: MomoState) -> Dict[str, Any]:
        resp = state.response
        if not resp or not resp.speak or not resp.message:
            return {"current_agent": "tts_agent"}

        # Only perform heavy server-side WAV synthesis if specifically requested in metadata
        # (e.g. for offline headless export or physical ESP32 I2S stream).
        # Web clients speak instantly with zero delay via browser Web Speech API.
        if state.metadata and state.metadata.get("generate_server_audio"):
            try:
                audio_bytes = await sync_to_async(self.tts.synthesize)(resp.message)
                return {
                    "metadata": {"tts_audio": audio_bytes},
                    "current_agent": "tts_agent"
                }
            except Exception as e:
                logger.warning(f"TTS synthesis error: {e}")

        return {"current_agent": "tts_agent"}
