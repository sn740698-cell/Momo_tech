"""
Finance Supervisor for MOMO LangGraph.
Orchestrates document ingestion, semantic context retrieval,
and deterministic data analysis.
"""
import logging
from typing import Dict, Any

from graph.state import MomoState, RoutingDecision

logger = logging.getLogger(__name__)


class FinanceSupervisor:
    """
    Supervises Document Agent, Retrieval Agent, and Data Analyzer Agent.
    """

    async def run(self, state: MomoState) -> Dict[str, Any]:
        has_uploads = bool(state.metadata.get("upload_queue"))
        target_agent = "document_agent" if has_uploads else "retrieval_agent"

        decision = RoutingDecision(
            supervisor="finance_supervisor",
            target_agent=target_agent,
            reason=f"Processing financial request via {target_agent}.",
            confidence=1.0
        )
        logger.info(f"FinanceSupervisor directed pipeline to -> {target_agent}")
        return {
            "supervisor_decisions": [decision]
        }
