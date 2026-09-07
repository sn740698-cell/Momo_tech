"""
Communication Supervisor for MOMO LangGraph.
Coordinates with financial insights and directs the Texting Agent
to produce professional balance-due drafts and notifications.
"""
import logging
from typing import Dict, Any

from graph.state import MomoState, RoutingDecision

logger = logging.getLogger(__name__)


class CommunicationSupervisor:
    """
    Supervises the Texting Agent for message drafting.
    """

    async def run(self, state: MomoState) -> Dict[str, Any]:
        decision = RoutingDecision(
            supervisor="communication_supervisor",
            target_agent="texting_agent",
            reason="Routing to Texting Agent for balance-due draft generation.",
            confidence=1.0
        )
        logger.info("CommunicationSupervisor activated -> texting_agent")
        return {
            "supervisor_decisions": [decision]
        }
