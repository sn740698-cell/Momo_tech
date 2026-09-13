"""
Research Supervisor for MOMO LangGraph.
Oversees real-time web research, scraping, and crawling requests.
Ensures authentic multi-source context is retrieved and routed into the conversation pipeline
so the local LLM can synthesize facts and generate comprehensive, grounded answers.
"""
import logging
from typing import Dict, Any

from graph.state import MomoState, RoutingDecision

logger = logging.getLogger(__name__)


class ResearchSupervisor:
    """
    Supervises the WebCrawlAgent.
    Validates web research queries and coordinates real-time information gathering.
    """

    async def run(self, state: MomoState) -> Dict[str, Any]:
        decision = RoutingDecision(
            supervisor="research_supervisor",
            target_agent="search_scout_agent",
            reason="Delegating live web crawling and research to Web Crawling Squad (SearchScout -> DeepScraper -> FactVerifier).",
            confidence=1.0
        )
        logger.info("ResearchSupervisor activating SearchScoutAgent and research squad pipeline.")
        return {
            "supervisor_decisions": [decision]
        }
