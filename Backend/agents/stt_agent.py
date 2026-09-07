"""
Speech-to-Text Agent for MOMO.
Processes inbound audio frames into text using local Whisper interfaces.
"""
import logging
from typing import Dict, Any

from graph.state import MomoState
from voice.stt import SpeechToText
from security.permissions import PermissionManager

logger = logging.getLogger(__name__)


class STTAgent:
    """
    Handles transcription of inbound voice audio into MomoState.
    """

    def __init__(self):
        self.stt = SpeechToText()

    async def run(self, state: MomoState) -> Dict[str, Any]:
        if not PermissionManager.is_microphone_enabled():
            logger.info("Microphone is disabled in privacy settings.")
            return {
                "errors": ["Microphone is disabled in privacy settings."],
                "current_agent": "stt_agent"
            }

        audio_payload = state.metadata.get("audio_bytes")
        if not audio_payload:
            return {"current_agent": "stt_agent"}

        transcribed = self.stt.transcribe(audio_payload)
        logger.info(f"STTAgent transcribed: '{transcribed}'")

        return {
            "voice_input": transcribed,
            "current_agent": "stt_agent"
        }
