"""
Web Crawl Orchestrator Agent for MOMO.
Coordinates the specialized web crawling multi-agent squad:
SearchScoutAgent -> DeepScraperAgent -> FactVerifierAgent.
Ensures seamless integration across Trafilatura, Readability-lxml, Crawl4AI, and BeautifulSoup.
"""
import logging
from typing import Dict, Any, List, Optional

from graph.state import MomoState, RetrievedChunk
from ai_workflow.services.web_crawler_service import LiveWebCrawlerService
from agents.search_scout_agent import SearchScoutAgent
from agents.deep_scraper_agent import DeepScraperAgent
from agents.fact_verifier_agent import FactVerifierAgent

logger = logging.getLogger(__name__)


class WebCrawlAgent:
    """
    Coordinates live web crawling squad execution within the LangGraph multi-agent workflow.
    Executes SearchScout -> DeepScraper -> FactVerifier in cohesive sequence.
    """

    def __init__(self, crawler_service: Optional[LiveWebCrawlerService] = None):
        self.crawler = crawler_service or LiveWebCrawlerService()
        self.scout_agent = SearchScoutAgent(self.crawler)
        self.scraper_agent = DeepScraperAgent(self.crawler)
        self.verifier_agent = FactVerifierAgent()

    async def run(self, state: MomoState) -> Dict[str, Any]:
        """
        Orchestrates full web research squad pipeline:
        1. SearchScout: discovers and deduplicates authentic destination URLs.
        2. DeepScraper: extracts complete article bodies using Trafilatura/Readability/Crawl4AI.
        3. FactVerifier: eliminates noise, validates facts, and computes consensus scores.
        """
        last_user_msg = ""
        for m in reversed(state.messages):
            if m.role == "user":
                last_user_msg = m.content
                break

        if not last_user_msg:
            last_user_msg = state.voice_input or ""

        logger.info(f"WebCrawlAgent orchestrating research squad for query: '{last_user_msg}'")

        # Step 1: Scout
        scout_res = await self.scout_agent.run(state)
        state.retrieved_context = scout_res.get("retrieved_context", [])

        # Step 2: Deep Scrape
        scraper_res = await self.scraper_agent.run(state)
        state.retrieved_context = scraper_res.get("retrieved_context", [])

        # Step 3: Fact Verify
        verifier_res = await self.verifier_agent.run(state)
        verified_chunks = verifier_res.get("retrieved_context", [])

        context_summaries = []
        for ch in verified_chunks:
            t = ch.metadata.get("title", "Web Source")
            s = ch.metadata.get("source", "Web Search")
            context_summaries.append(f"• {t} ({s})")

        directive = (
            f"[LIVE MULTI-AGENT WEB RESEARCH RETRIEVED ({len(verified_chunks)} verified sources)]:\n"
            + "\n".join(context_summaries) +
            "\n\nINSTRUCTION FOR LLM: Thoroughly synthesize the retrieved facts into an articulate, "
            "comprehensive, and well-structured response in MOMO's refined voice. "
            "Directly address the user's inquiry with genuine facts, figures, and explanations. "
            "Never reply with generic cheerleading, canned praise, or game suggestions."
        )

        return {
            "retrieved_context": verified_chunks,
            "conversation_context": directive,
            "current_agent": "web_crawl_agent"
        }
