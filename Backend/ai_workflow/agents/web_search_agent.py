"""
Temporal Web Search & Live Crawler Agent for MOMO.
Retrieves real-time news, government updates, calendar events, and live web evidence.
Transforms live web crawl results into structured EvidenceItems with strict source attribution.
"""
import logging
from typing import Dict, Any, List

from ai_workflow.agents.base import BaseWorkflowAgent
from ai_workflow.state import WorkflowState, EvidenceItem
from ai_workflow.services.temporal_service import TemporalService
from ai_workflow.services.web_crawler_service import LiveWebCrawlerService

logger = logging.getLogger(__name__)


class TemporalWebSearchAgent(BaseWorkflowAgent):
    """
    Agent responsible for temporal grounding, live news search, and web crawling.
    Ensures that current events and temporal questions have verified external citations.
    """

    def __init__(self):
        super().__init__(name="temporal_web_search_agent")
        self.crawler_service = LiveWebCrawlerService()

    async def execute(self, state: WorkflowState) -> Dict[str, Any]:
        raw_query = state.normalized_input or state.user_input
        temporal_anchor = state.temporal_anchor or TemporalService.get_temporal_anchor()
        
        # Analyze temporal intent
        intent = TemporalService.analyze_temporal_intent(raw_query)
        is_realtime = state.is_realtime_query or intent.get("is_realtime", False)

        # Check if subtasks explicitly request web search
        web_subtasks = [t.description for t in state.subtasks if "web" in t.description.lower() or "news" in t.description.lower()]
        if web_subtasks:
            is_realtime = True

        if not is_realtime:
            # Query is purely local/static, skip live web crawl
            return {
                "live_web_context": [],
                "is_realtime_query": False,
            }

        evidence_items: List[EvidenceItem] = []

        # 1. Deterministic direct answers for date queries
        if intent.get("is_date_query") and intent.get("direct_answer"):
            evidence_items.append(
                EvidenceItem(
                    content=intent["direct_answer"],
                    source="Deterministic System Clock",
                    document_id="clock_anchor",
                    score=1.0,
                    tenant_id=state.tenant_id,
                    project_id=state.project_id,
                    metadata={"temporal_anchor": temporal_anchor}
                )
            )

        # 2. Deterministic special day observances
        if intent.get("is_special_day_query") and intent.get("direct_answer"):
            evidence_items.append(
                EvidenceItem(
                    content=intent["direct_answer"],
                    source="National and UN Observances Calendar",
                    document_id="observances_anchor",
                    score=1.0,
                    tenant_id=state.tenant_id,
                    project_id=state.project_id,
                    metadata={"special_today": temporal_anchor.get("special_today")}
                )
            )

        # 3. Live search and crawling if needed
        if intent.get("needs_web_search", True) and not intent.get("is_date_query", False):
            target_date = intent.get("target_date", temporal_anchor.get("today_date"))
            target_label = intent.get("target_label", "today")

            # Formulate targeted search query
            search_query = raw_query
            # Remove filler words for search clarity
            search_query = search_query.replace("what happened with", "").replace("what happened", "").strip()

            logger.info(f"TemporalWebSearchAgent executing live search for '{search_query}' (target: {target_label} {target_date})")

            crawled_results = await self.crawler_service.gather_realtime_context(
                query=search_query,
                target_date=target_date,
                target_label=target_label,
                max_results=4
            )

            for idx, item in enumerate(crawled_results):
                clean_content = (
                    f"Headline: {item.get('title')}\n"
                    f"Published: {item.get('pub_date')}\n"
                    f"Publisher: {item.get('source')}\n"
                    f"Content Summary: {item.get('content')}"
                )
                evidence_items.append(
                    EvidenceItem(
                        content=clean_content,
                        source=f"{item.get('source', 'Web')} ({item.get('pub_date', 'Recent')})",
                        document_id=item.get("url") or f"web_article_{idx+1}",
                        chunk_index=idx,
                        score=0.92,
                        tenant_id=state.tenant_id,
                        project_id=state.project_id,
                        metadata={
                            "url": item.get("url"),
                            "pub_date": item.get("pub_date"),
                            "source_name": item.get("source"),
                            "target_date": target_date,
                            "target_label": target_label,
                        }
                    )
                )

        logger.info(f"TemporalWebSearchAgent gathered {len(evidence_items)} live evidence items.")

        return {
            "live_web_context": evidence_items,
            "retrieved_context": evidence_items,
            "is_realtime_query": True,
            "temporal_anchor": temporal_anchor,
        }
