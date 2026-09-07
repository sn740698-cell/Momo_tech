"""
Voice Supervisor for MOMO LangGraph.
Coordinates STT transcription, brain processing, and TTS speech synthesis.
"""
import logging
from typing import Dict, Any

from graph.state import MomoState, RoutingDecision

logger = logging.getLogger(__name__)


class VoiceSupervisor:
    """
    Supervises STT Agent, Conversation Agent, and TTS Agent.
    """

    async def run(self, state: MomoState) -> Dict[str, Any]:
        decision = RoutingDecision(
            supervisor="voice_supervisor",
            target_agent="stt_agent",
            reason="Routing audio request through voice transcription pipeline.",
            confidence=1.0
        )
        logger.info("VoiceSupervisor activated -> stt_agent")
        return {
            "supervisor_decisions": [decision]
        }
