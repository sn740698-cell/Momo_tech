"""
Search Scout Agent for MOMO.
Specializes in multi-angle search query formulation, multi-source discovery
(Bing Live, DuckDuckGo, Wikipedia, Direct RSS), URL decoding, and deduplication.
"""
import logging
import re
from typing import Dict, Any, List, Optional

from graph.state import MomoState, RetrievedChunk
from ai_workflow.services.web_crawler_service import LiveWebCrawlerService

logger = logging.getLogger(__name__)


class SearchScoutAgent:
    """
    First stage of the Web Crawling Multi-Agent Squad.
    Scouts the web across multiple search backends, generates query variations,
    resolves direct destination URLs, and provides candidates to DeepScraperAgent.
    """

    def __init__(self, crawler_service: Optional[LiveWebCrawlerService] = None):
        self.crawler = crawler_service or LiveWebCrawlerService(timeout_seconds=12.0)

    async def run(self, state: MomoState) -> Dict[str, Any]:
        last_user_msg = ""
        for m in reversed(state.messages):
            if m.role == "user":
                last_user_msg = m.content
                break

        if not last_user_msg:
            last_user_msg = state.voice_input or ""

        logger.info(f"SearchScoutAgent scouting candidates for query: '{last_user_msg}'")

        # 1. Multi-angle query expansion
        clean_q = self.crawler.expand_query(last_user_msg)
        queries = [clean_q]

        # Add targeted variant if applicable
        if not any(w in clean_q.lower() for w in ["latest", "recent", "2026", "2025"]):
            queries.append(f"{clean_q} 2026")

        all_candidates: List[Dict[str, Any]] = []

        # Direct domain/URL detection (e.g. 'web crawl python.org', 'crawl wikipedia.org')
        domain_match = re.search(r'(https?://[^\s]+|\b[a-zA-Z0-9-]+\.(?:org|com|net|io|edu|gov|in)\b)', last_user_msg)
        if domain_match:
            raw_target = domain_match.group(1).strip()
            target_url = raw_target if raw_target.startswith("http") else f"https://{raw_target}"
            all_candidates.append({
                "title": f"{raw_target} Web Page",
                "url": target_url,
                "snippet": f"Direct web crawl candidate for {raw_target}",
                "source": "Direct Crawl Scout"
            })

        # 1.5. If query relates to news or current events, pull authentic live national feeds directly
        is_news_query = any(w in last_user_msg.lower() for w in [
            "news", "headline", "breaking", "happening", "today's events", "current events",
            "the hindu", "ndtv", "times of india", "indian express", "india"
        ])
        if is_news_query:
            try:
                raw_keywords = [
                    w for w in re.sub(r"[^\w\s]", "", clean_q).split()
                    if len(w) > 3 and w.lower() not in ["news", "latest", "breaking", "today", "date", "time", "tell"]
                ]
                direct_news = await self.crawler.fetch_direct_national_news(keywords=raw_keywords, max_results=4)
                if direct_news:
                    all_candidates.extend(direct_news)
                    logger.info(f"SearchScoutAgent pulled {len(direct_news)} live national news feed items.")
            except Exception as e:
                logger.debug(f"Direct national news fetch error in SearchScout: {e}")

        # 2. Query search backends in priority order
        for q in queries:
            # Primary: Bing Live Search
            bing_items = await self.crawler.fetch_bing_search(q, max_results=3)
            all_candidates.extend(bing_items)

            # Fallback to Wikipedia Knowledge if needed
            if len(all_candidates) < 3:
                wiki_items = await self.crawler.fetch_wikipedia_search(clean_q, max_results=2)
                all_candidates.extend(wiki_items)

        # 3. Deduplicate by URL
        seen_urls = set()
        deduped: List[Dict[str, Any]] = []
        for it in all_candidates:
            url = it.get("url", "").strip()
            if url and url not in seen_urls:
                seen_urls.add(url)
                deduped.append(it)

        # Convert to candidate RetrievedChunks
        candidate_chunks: List[RetrievedChunk] = []
        for idx, it in enumerate(deduped[:4], 1):
            title = it.get("title", f"Web Resource {idx}")
            url = it.get("url", "")
            src = it.get("source", "Web Scout")
            snip = it.get("snippet", title)

            candidate_chunks.append(RetrievedChunk(
                chunk_id=f"scout-{idx}",
                document_id=f"candidate-{idx}",
                content=snip,
                score=0.8,
                metadata={
                    "url": url,
                    "title": title,
                    "source": src,
                    "stage": "scouted"
                }
            ))

        logger.info(f"SearchScoutAgent identified {len(candidate_chunks)} candidate URLs.")

        metadata = dict(state.metadata or {})
        metadata["scout_candidates"] = [c.metadata.get("url") for c in candidate_chunks]

        return {
            "retrieved_context": candidate_chunks,
            "metadata": metadata,
            "current_agent": "search_scout_agent"
        }
