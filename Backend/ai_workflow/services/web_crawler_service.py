"""
Real-Time Multi-Source Web Search & Deep Article Crawler Service for MOMO.
Fetches authentic real-time news and web content via direct national feeds
(The Hindu, Indian Express, NDTV), Wikipedia Observances API, DuckDuckGo search,
and deep article paragraph extractors.
"""
import os
import re
import html
import logging
import asyncio
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)


class LiveWebCrawlerService:
    """
    Retrieves authentic real-time news headlines, article body text, and calendar observances.
    """

    DIRECT_NEWS_FEEDS = [
        ("The Hindu", "https://www.thehindu.com/news/national/feeder/default.rss"),
        ("Indian Express", "https://indianexpress.com/section/india/feed/"),
        ("NDTV", "https://feeds.feedburner.com/ndtvnews-top-stories"),
        ("Times of India", "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"),
    ]

    def __init__(self, timeout_seconds: float = 7.0):
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
        text = re.sub(r"(?is)<(script|style|nav|footer|header|aside|noscript|figure|form).*?>.*?</\1>", " ", raw_html)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        text = " ".join(text.split())
        return text

    async def fetch_direct_national_news(
        self,
        keywords: Optional[List[str]] = None,
        max_results: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Retrieves breaking national news directly from top Indian news outlets
        (The Hindu, Indian Express, NDTV, Times of India) with direct article URLs.
        """
        results: List[Dict[str, Any]] = []
        kw_lower = [k.lower() for k in keywords] if keywords else []

        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            tasks = [client.get(feed_url, follow_redirects=True) for _, feed_url in self.DIRECT_NEWS_FEEDS]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            for (src_name, _), resp in zip(self.DIRECT_NEWS_FEEDS, responses):
                if not isinstance(resp, httpx.Response) or resp.status_code != 200:
                    continue

                try:
                    root = ET.fromstring(resp.text)
                    items = root.findall(".//item")
                    for it in items:
                        title_el = it.find("title")
                        link_el = it.find("link")
                        pub_el = it.find("pubDate")
                        desc_el = it.find("description")

                        title = title_el.text.strip() if title_el is not None and title_el.text else ""
                        link = link_el.text.strip() if link_el is not None and link_el.text else ""
                        pub_date = pub_el.text.strip() if pub_el is not None and pub_el.text else ""
                        desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

                        clean_desc = self.clean_html(desc)
                        searchable = f"{title} {clean_desc}".lower()

                        # Filter by keywords if provided, or take breaking news
                        if kw_lower and not any(k in searchable for k in kw_lower):
                            continue

                        results.append({
                            "title": title,
                            "url": link,
                            "source": src_name,
                            "pub_date": pub_date,
                            "snippet": clean_desc or title,
                            "content": clean_desc or title,
                        })

                        if len(results) >= max_results:
                            return results
                except Exception as e:
                    logger.debug(f"Error parsing feed {src_name}: {e}")

        return results

    async def fetch_special_days_wikipedia(
        self,
        month: int,
        day: int,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Queries official Wikipedia On This Day API for real-time observances and holidays.
        """
        url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/holidays/{month:02d}/{day:02d}"
        results = []

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
                r = await client.get(url)
                if r.status_code == 200:
                    data = r.json()
                    holidays = data.get("holidays", [])
                    for h in holidays[:max_results]:
                        text = h.get("text", "")
                        page_url = ""
                        pages = h.get("pages", [])
                        if pages and isinstance(pages, list):
                            page_url = pages[0].get("content_urls", {}).get("desktop", {}).get("page", "")

                        results.append({
                            "title": text,
                            "source": "Wikipedia Observances",
                            "url": page_url,
                            "pub_date": f"Calendar {month:02d}-{day:02d}",
                            "snippet": text,
                            "content": text,
                        })
        except Exception as e:
            logger.warning(f"Wikipedia holidays lookup error: {e}")

        return results

    async def search_duckduckgo(
        self,
        query: str,
        max_results: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Queries DuckDuckGo HTML search and decodes actual destination URLs from uddg parameter.
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
                matches = re.findall(
                    r'<a class="result__url"[^>]*href="([^"]+)"[^>]*>(.*?)</a>[\s\S]*?<a class="result__snippet[^>]*>(.*?)</a>',
                    body
                )

                for raw_url, disp_url, snip in matches[:max_results]:
                    real_url = raw_url
                    if "uddg=" in raw_url:
                        try:
                            real_url = urllib.parse.unquote(raw_url.split("uddg=")[1].split("&")[0])
                        except Exception:
                            real_url = raw_url

                    clean_snip = self.clean_html(snip)
                    title = self.clean_html(disp_url)

                    results.append({
                        "title": title or "Web Result",
                        "source": "Web",
                        "url": real_url,
                        "pub_date": "Recent",
                        "snippet": clean_snip,
                        "content": clean_snip,
                    })
        except Exception as e:
            logger.warning(f"DuckDuckGo search error: {e}")

        return results

    PAYWALL_PATTERNS = [
        "subscribe now", "active subscription", "cookie policy", "sign in",
        "subscribed with another email", "logout and login", "unlock these with subscription",
        "premium stories", "view from india", "newsletter", "terms of use", "account subscription benefits"
    ]

    async def crawl_article_text(
        self,
        url: str,
        client: Optional[httpx.AsyncClient] = None
    ) -> str:
        """
        Deep crawls direct article URL and extracts the authentic paragraph content (<p> tags).
        Guarantees that paywall notices and subscription boilerplate are excluded.
        """
        if not url or not url.startswith("http") or any(skip in url for skip in ["google.com/rss", "duckduckgo.com"]):
            return ""

        close_client = False
        if client is None:
            client = httpx.AsyncClient(headers=self.headers, timeout=self.timeout)
            close_client = True

        try:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code == 200:
                raw_html = resp.text
                # Extract paragraph blocks (<p>...</p>)
                paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', raw_html, re.DOTALL)
                substantive_paras = []
                for p in paragraphs:
                    clean_p = self.clean_html(p)
                    # Exclude paywall, boilerplate, login, or cookie prompts
                    if len(clean_p) > 40 and not any(pw in clean_p.lower() for pw in self.PAYWALL_PATTERNS):
                        substantive_paras.append(clean_p)

                if substantive_paras:
                    joined = "\n\n".join(substantive_paras[:5])
                    return joined[:1800]

                # Fallback to general text clean if no substantive <p> tags found
                fallback = self.clean_html(raw_html)
                if not any(pw in fallback.lower() for pw in self.PAYWALL_PATTERNS):
                    return fallback[:1500]
        except Exception as e:
            logger.debug(f"Could not crawl {url}: {e}")
        finally:
            if close_client:
                await client.aclose()

        return ""

    @classmethod
    def is_valid_article_body(cls, title: str, body: str) -> bool:
        """Checks whether extracted HTML body is genuine article content vs newsletter/boilerplate."""
        if not body or len(body) < 80:
            return False
        bad_phrases = [
            "first day first show", "today's cache", "data point decoding",
            "subscribe now", "active subscription", "sign in to read",
            "logout and login", "unlock these with subscription", "premium stories"
        ]
        if any(bp in body.lower() for bp in bad_phrases):
            return False
        # Verify title relevance: at least one substantive title word must appear in the body
        title_words = [w.lower() for w in re.sub(r"[^\w\s]", "", title).split() if len(w) > 3]
        if title_words and not any(tw in body.lower() for tw in title_words):
            return False
        return True

    async def gather_realtime_context(
        self,
        query: str,
        target_date: Optional[str] = None,
        target_label: Optional[str] = None,
        max_results: int = 4
    ) -> List[Dict[str, Any]]:
        """
        End-to-end multi-source real-time intelligence gathering:
        1. Observances / Special Day Queries -> Wikipedia Holidays API + Observances Search
        2. Breaking / Government / Yesterday Queries -> Direct National Feeds (The Hindu, Indian Express, NDTV) + Deep Crawl
        3. General Queries -> DuckDuckGo with uddg decode + Deep Crawl
        """
        q_lower = query.lower()
        items: List[Dict[str, Any]] = []

        # 1. Special Day / Observance Queries
        if any(w in q_lower for w in ["special today", "special day", "observance", "holiday"]):
            dt = datetime.now()
            if target_date:
                try:
                    dt = datetime.strptime(target_date, "%Y-%m-%d")
                except Exception:
                    pass
            wiki_items = await self.fetch_special_days_wikipedia(dt.month, dt.day, max_results=max_results)
            if wiki_items:
                items.extend(wiki_items)

        # 2. National News / Government / Yesterday / Current Events
        if not items or any(w in q_lower for w in ["government", "yesterday", "today", "cabinet", "news", "happening", "india", "pib"]):
            raw_keywords = [
                w for w in re.sub(r"[^\w\s]", "", query).split()
                if len(w) > 3 and w.lower() not in ["what", "happened", "with", "yesterday", "today", "show", "tell"]
            ]
            if not raw_keywords:
                raw_keywords = ["government", "cabinet", "india", "minister"]

            direct_news = await self.fetch_direct_national_news(keywords=raw_keywords, max_results=max_results)
            if direct_news:
                items.extend(direct_news)

        # 3. Fallback to DuckDuckGo if still insufficient
        if len(items) < 2:
            ddg_items = await self.search_duckduckgo(query=query, max_results=max_results)
            items.extend(ddg_items)

        if not items:
            return []

        # Limit to requested count
        items = items[:max_results]

        # 4. Deep crawl the top real URLs to extract authentic article paragraphs
        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            crawl_tasks = []
            for it in items:
                url = it.get("url", "")
                if url and url.startswith("http"):
                    crawl_tasks.append(self.crawl_article_text(url, client=client))
                else:
                    crawl_tasks.append(asyncio.sleep(0, result=""))

            deep_texts = await asyncio.gather(*crawl_tasks)

            for i, deep_text in enumerate(deep_texts):
                title = items[i].get("title", "")
                snip = items[i].get("snippet", "")
                if self.is_valid_article_body(title, deep_text):
                    items[i]["content"] = deep_text
                elif snip and snip != title:
                    items[i]["content"] = f"{title}. {snip}"
                else:
                    items[i]["content"] = title

        return items
