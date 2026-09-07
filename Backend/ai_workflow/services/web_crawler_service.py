"""
Real-Time Web Search & Deep Article Crawler Service for MOMO.
Fetches fresh news and web content via Google News RSS and DuckDuckGo,
extracting clean text without heavy browser dependencies.
"""
import os
import re
import html
import logging
import asyncio
import urllib.parse
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)


class LiveWebCrawlerService:
    """
    Retrieves real-time news headlines, article snippets, and crawls full-text content.
    """

    def __init__(self, timeout_seconds: float = 8.0):
        self.timeout = timeout_seconds
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    @staticmethod
    def clean_html(raw_html: str) -> str:
        """Strips HTML tags, scripts, styles, headers, and navigation bars."""
        if not raw_html:
            return ""
        # Remove scripts, styles, headers, footers, navs
        text = re.sub(r"(?is)<(script|style|nav|footer|header|aside|noscript).*?>.*?</\1>", " ", raw_html)
        # Remove remaining tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Unescape entities
        text = html.unescape(text)
        # Collapse whitespace
        text = " ".join(text.split())
        return text

    async def search_google_news(
        self,
        query: str,
        timelimit: str = "2d",
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Queries Google News RSS feed for real-time news items.
        Returns title, publisher, link, published date, and description snippet.
        """
        encoded_query = urllib.parse.quote(f"{query} when:{timelimit}")
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"

        results: List[Dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.warning(f"Google News RSS returned status {resp.status_code}")
                    return results

                root = ET.fromstring(resp.text)
                items = root.findall("./channel/item")

                for it in items[:max_results]:
                    title_elem = it.find("title")
                    link_elem = it.find("link")
                    pub_elem = it.find("pubDate")
                    desc_elem = it.find("description")
                    source_elem = it.find("source")

                    full_title = title_elem.text if title_elem is not None and title_elem.text else ""
                    raw_link = link_elem.text if link_elem is not None and link_elem.text else ""
                    pub_date = pub_elem.text if pub_elem is not None and pub_elem.text else ""
                    raw_desc = desc_elem.text if desc_elem is not None and desc_elem.text else ""
                    source_name = source_elem.text if source_elem is not None and source_elem.text else ""

                    # Clean publisher suffix from title (Google News standard "Headline - Publisher")
                    clean_title = full_title
                    if " - " in full_title:
                        parts = full_title.rsplit(" - ", 1)
                        clean_title = parts[0].strip()
                        if not source_name:
                            source_name = parts[1].strip()

                    clean_snippet = self.clean_html(raw_desc)

                    results.append({
                        "title": clean_title,
                        "source": source_name or "Google News",
                        "url": raw_link,
                        "pub_date": pub_date,
                        "snippet": clean_snippet,
                        "content": clean_snippet,
                    })
        except Exception as e:
            logger.warning(f"Error fetching Google News RSS: {e}")

        return results

    async def search_duckduckgo(
        self,
        query: str,
        max_results: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Queries DuckDuckGo HTML search for general real-time queries.
        """
        encoded = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        results: List[Dict[str, Any]] = []

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return results

                body = resp.text
                # Match result snippets and links using regex
                snippets = re.findall(
                    r'<a class="result__snippet[^>]*>(.*?)</a>',
                    body,
                    re.DOTALL
                )
                titles = re.findall(
                    r'<a class="result__url"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                    body,
                    re.DOTALL
                )

                for i, snip in enumerate(snippets[:max_results]):
                    raw_url = ""
                    title = "Web Result"
                    if i < len(titles):
                        raw_url = titles[i][0]
                        title = self.clean_html(titles[i][1])

                    results.append({
                        "title": title or "Search Result",
                        "source": "DuckDuckGo",
                        "url": raw_url,
                        "pub_date": "Recent",
                        "snippet": self.clean_html(snip),
                        "content": self.clean_html(snip),
                    })
        except Exception as e:
            logger.warning(f"DuckDuckGo search error: {e}")

        return results

    async def crawl_article_text(
        self,
        url: str,
        client: Optional[httpx.AsyncClient] = None
    ) -> str:
        """
        Fetches an article URL and extracts the primary readable text body.
        Truncates to 2000 characters to fit within prompt context windows.
        """
        if not url or not url.startswith("http"):
            return ""

        close_client = False
        if client is None:
            client = httpx.AsyncClient(headers=self.headers, timeout=self.timeout)
            close_client = True

        try:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code == 200:
                cleaned = self.clean_html(resp.text)
                return cleaned[:2000]
        except Exception as e:
            logger.debug(f"Could not crawl {url}: {e}")
        finally:
            if close_client:
                await client.aclose()

        return ""

    async def gather_realtime_context(
        self,
        query: str,
        target_date: Optional[str] = None,
        target_label: Optional[str] = None,
        max_results: int = 4
    ) -> List[Dict[str, Any]]:
        """
        End-to-end coordinator: searches Google News, falls back to DuckDuckGo if needed,
        and enriches top articles by crawling their text content.
        """
        # Determine time limit filter
        timelimit = "1d" if target_label == "today" else "3d"

        # Enhance query with temporal intent
        effective_query = query
        if target_label == "yesterday" and target_date:
            effective_query = f"{query} {target_date}"
        elif target_label == "today" and target_date:
            effective_query = f"{query} {target_date}"

        # 1. Search Google News
        items = await self.search_google_news(
            query=effective_query,
            timelimit=timelimit,
            max_results=max_results
        )

        # 2. Fallback to DuckDuckGo if Google News returned no results
        if not items:
            items = await self.search_duckduckgo(query=effective_query, max_results=max_results)

        if not items:
            return []

        # 3. Concurrently crawl top article bodies for deeper context
        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            crawl_tasks = []
            for item in items:
                url = item.get("url", "")
                # Only crawl valid direct http links (avoid heavy internal redirects if snippet is already rich)
                if url and url.startswith("http") and len(item.get("snippet", "")) < 300:
                    crawl_tasks.append(self.crawl_article_text(url, client=client))
                else:
                    crawl_tasks.append(asyncio.sleep(0, result=""))

            deep_texts = await asyncio.gather(*crawl_tasks)

            for i, deep_text in enumerate(deep_texts):
                if deep_text and len(deep_text) > len(items[i].get("snippet", "")):
                    items[i]["content"] = deep_text

        return items
