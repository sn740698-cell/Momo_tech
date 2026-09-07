import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SpeechToText:
    """
    Speech to Text transcription interface for local voice pipeline.
    """

    def __init__(self, backend: str = "mock"):
        self.backend = backend

    def transcribe(self, audio_bytes: bytes) -> Optional[str]:
        if not audio_bytes:
            return None
        logger.info("Transcribing audio payload...")
        return "Hello MOMO"
