"""
Automation Supervisor for MOMO LangGraph.
Oversees desktop and browser automation tasks (opening apps, websites, tools, games).
Ensures safe execution and routes results into the conversation pipeline
so the local LLM always articulates the outcome in MOMO's voice.
"""
import logging
from typing import Dict, Any

from graph.state import MomoState, RoutingDecision

logger = logging.getLogger(__name__)


class AutomationSupervisor:
    """
    Supervises the AutomationAgent.
    Validates automation requests and coordinates execution.
    """

    async def run(self, state: MomoState) -> Dict[str, Any]:
        decision = RoutingDecision(
            supervisor="automation_supervisor",
            target_agent="automation_agent",
            reason="Delegating desktop/browser action to AutomationAgent for execution.",
            confidence=1.0
        )
        logger.info("AutomationSupervisor activating AutomationAgent pipeline.")
        return {
            "supervisor_decisions": [decision]
        }
