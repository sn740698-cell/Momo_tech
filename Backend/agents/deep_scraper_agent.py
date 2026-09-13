"""
Deep Scraper Agent for MOMO.
Specializes in parallel high-density web page extraction using:
- Trafilatura (boilerplate, ad, and navigation stripping)
- Readability-lxml (document body scoring)
- Crawl4AI (dynamic JavaScript rendering)
- BeautifulSoup4 (semantic HTML paragraph filtering)
- Resilient async HTTP with SSL bypass
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional

from graph.state import MomoState, RetrievedChunk
from ai_workflow.services.web_crawler_service import LiveWebCrawlerService

logger = logging.getLogger(__name__)


class DeepScraperAgent:
    """
    Second stage of the Web Crawling Multi-Agent Squad.
    Consumes scouted URLs, extracts complete article bodies using a 4-tier
    extraction hierarchy, and populates high-fidelity text content.
    """

    def __init__(self, crawler_service: Optional[LiveWebCrawlerService] = None):
        self.crawler = crawler_service or LiveWebCrawlerService(timeout_seconds=12.0)

    async def run(self, state: MomoState) -> Dict[str, Any]:
        candidates = state.retrieved_context or []
        if not candidates:
            logger.info("DeepScraperAgent: No candidate URLs to scrape.")
            return {"current_agent": "deep_scraper_agent"}

        logger.info(f"DeepScraperAgent executing parallel deep crawl across {len(candidates)} URLs...")

        tasks = []
        for ch in candidates:
            url = ch.metadata.get("url", "")
            if url and url.startswith("http") and "wikipedia.org/api" not in url:
                tasks.append(self.crawler.crawl_article_text(url))
            else:
                tasks.append(asyncio.sleep(0, result=""))

        extracted_bodies = await asyncio.gather(*tasks, return_exceptions=True)

        scraped_chunks: List[RetrievedChunk] = []
        for idx, (ch, body) in enumerate(zip(candidates, extracted_bodies), 1):
            valid_body = body if isinstance(body, str) and len(body.strip()) > 60 else ""
            title = ch.metadata.get("title", "")
            src = ch.metadata.get("source", "Web Resource")
            url = ch.metadata.get("url", "")

            # If deep extraction returned body, use it; else fallback to candidate snippet
            final_content = valid_body if valid_body else ch.content

            scraped_chunks.append(RetrievedChunk(
                chunk_id=f"scraped-{idx}",
                document_id=f"doc-{idx}",
                content=final_content,
                score=0.9 if valid_body else 0.7,
                metadata={
                    "url": url,
                    "title": title,
                    "source": src,
                    "stage": "deep_scraped",
                    "content_length": len(final_content),
                    "extractor": "trafilatura_readability" if valid_body else "snippet"
                }
            ))

        logger.info(f"DeepScraperAgent successfully scraped {len(scraped_chunks)} pages.")

        return {
            "retrieved_context": scraped_chunks,
            "current_agent": "deep_scraper_agent"
        }
