"""
Conversation Supervisor for MOMO LangGraph.
Orchestrates memory retrieval and conversational response generation.
"""
import logging
from typing import Dict, Any

from graph.state import MomoState, RoutingDecision

logger = logging.getLogger(__name__)


class ConversationSupervisor:
    """
    Supervises Conversation Agent and Memory/Context Agent.
    """

    async def run(self, state: MomoState) -> Dict[str, Any]:
        decision = RoutingDecision(
            supervisor="conversation_supervisor",
            target_agent="conversation_agent",
            reason="Orchestrating conversational turn with memory enrichment.",
            confidence=1.0
        )
        logger.info("ConversationSupervisor activating memory & conversation pipeline.")
        return {
            "supervisor_decisions": [decision]
        }
