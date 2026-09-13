"""
Real-Time Multi-Source Web Search & Deep Article Crawler Service for MOMO.
Combines universal web search (DuckDuckGo HTML & Lite APIs), deep high-fidelity
article extraction (Trafilatura, Readability-lxml, Crawl4AI, BeautifulSoup4),
direct national feeds (The Hindu, Indian Express, NDTV, Times of India), and
Wikipedia Knowledge & Observances APIs.
Delivers genuine, up-to-date, grounded web intelligence for multi-agent reasoning.
"""
import os
import re
import sys
import html
import logging
import asyncio
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any, Optional

import httpx
import bs4

# On Windows, ensure WindowsProactorEventLoopPolicy is used for subprocess support (Playwright/Crawl4AI)
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

logger = logging.getLogger(__name__)

# Lazy imports for Crawl4AI, ScrapeGraphAI, Trafilatura, and Readability
_crawl4ai_available = None
_scrapegraphai_available = None
_trafilatura_available = None
_readability_available = None


def is_crawl4ai_available() -> bool:
    global _crawl4ai_available
    if _crawl4ai_available is None:
        try:
            if sys.platform == "win32":
                try:
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                except Exception:
                    pass
            from crawl4ai import AsyncWebCrawler
            _crawl4ai_available = True
        except ImportError:
            _crawl4ai_available = False
    return _crawl4ai_available


def is_scrapegraphai_available() -> bool:
    global _scrapegraphai_available
    if _scrapegraphai_available is None:
        try:
            from scrapegraphai.graphs import SmartScraperGraph
            _scrapegraphai_available = True
        except ImportError:
            _scrapegraphai_available = False
    return _scrapegraphai_available


def is_trafilatura_available() -> bool:
    global _trafilatura_available
    if _trafilatura_available is None:
        try:
            import trafilatura
            _trafilatura_available = True
        except ImportError:
            _trafilatura_available = False
    return _trafilatura_available


def is_readability_available() -> bool:
    global _readability_available
    if _readability_available is None:
        try:
            from readability import Document
            _readability_available = True
        except ImportError:
            _readability_available = False
    return _readability_available


class LiveWebCrawlerService:
    """
    Real-Time Web Intelligence and Crawling Engine.
    Uses Bing Live Search for universal search and Trafilatura + Readability + Crawl4AI
    for clean, paywall-free, high-density article content extraction.
    """

    DIRECT_NEWS_FEEDS = [
        ("The Hindu", "https://www.thehindu.com/news/national/feeder/default.rss"),
        ("Indian Express", "https://indianexpress.com/section/india/feed/"),
        ("NDTV", "https://feeds.feedburner.com/ndtvnews-top-stories"),
        ("Times of India", "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"),
    ]

    PAYWALL_PATTERNS = [
        "subscribe now", "active subscription", "cookie policy", "sign in",
        "subscribed with another email", "logout and login", "unlock these with subscription",
        "premium stories", "view from india", "newsletter", "terms of use", "account subscription benefits"
    ]

    def __init__(self, timeout_seconds: float = 12.0):
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
    def extract_urls(text: str) -> List[str]:
        """Extracts all valid HTTP/HTTPS URLs from a given query or text string."""
        if not text:
            return []
        pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*'
        urls = re.findall(pattern, text)
        cleaned = [re.sub(r'[\.,;!\?\)]+$', '', u) for u in urls]
        return [u for u in cleaned if len(u) > 8]

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

    @classmethod
    def expand_query(cls, query: str) -> str:
        """
        Normalizes and semantically expands user search queries by stripping chat prefixes,
        fixing common misspellings, and removing trailing search noise words.
        """
        clean = query.strip()
        # Strip conversational conversational wrappers (e.g. 'tell me its', 'show me', 'what is', 'can you find')
        clean = re.sub(r'^(?:ok\s+|please\s+)?(?:go\s+)?(?:web\s+crawl\s+(?:about|on|for)?|crawl\s+(?:about|on|for)?|search\s+(?:web\s+)?(?:for|about)?|look\s+up|tell\s+(?:me\s+)?(?:its\s+|about\s+|the\s+)?|what\s+is\s+|show\s+(?:me\s+)?|give\s+(?:me\s+)?|find\s+(?:me\s+)?)\s*', '', clean, flags=re.IGNORECASE).strip()
        # Strip trailing date/time clauses that confuse web search engines
        clean = re.sub(r'\s*(?:with\s+(?:the\s+)?date\s+and\s+time|with\s+date\s+and\s+time|with\s+time\s+and\s+date|date\s+and\s+time)\s*$', '', clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r'\bsih\b', 'Smart India Hackathon', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\bhackothon\b', 'Hackathon', clean, flags=re.IGNORECASE)
        # Strip trailing intent noise words that disrupt web search relevance
        clean = re.sub(r'\b(?:details|overview|info|information|updates|give me)\b', '', clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean or query.strip()

    # =========================================================================
    # UNIVERSAL WEB SEARCH ENGINES (BING LIVE SEARCH + DUCKDUCKGO HTML & LITE)
    # =========================================================================

    @staticmethod
    def decode_bing_url(href: str) -> str:
        """Decodes the real destination URL from Bing redirection /ck/a? wrapper."""
        if not href:
            return ""
        if "bing.com/ck/a?" in href and "u=" in href:
            try:
                parsed = urllib.parse.urlparse(href)
                qs = urllib.parse.parse_qs(parsed.query)
                u_vals = qs.get("u", [])
                if u_vals:
                    raw_u = u_vals[0]
                    if raw_u.startswith("a1"):
                        raw_u = raw_u[2:]
                    raw_u += "=" * ((4 - len(raw_u) % 4) % 4)
                    import base64
                    decoded = base64.urlsafe_b64decode(raw_u).decode("utf-8", errors="ignore")
                    if decoded.startswith("http"):
                        return decoded
            except Exception:
                pass
        return href

    async def fetch_bing_search(self, query: str, max_results: int = 4) -> List[Dict[str, Any]]:
        """
        Universal live web search using Bing endpoint via httpx + BeautifulSoup.
        Extracts authentic live search results, real destination URLs, and direct snippets.
        """
        results: List[Dict[str, Any]] = []
        if not query or not query.strip():
            return results

        clean_q = self.expand_query(query)

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout, verify=False) as client:
                url = "https://www.bing.com/search?q=" + urllib.parse.quote(clean_q)
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code == 200 and resp.text:
                    soup = bs4.BeautifulSoup(resp.text, "html.parser")
                    algo_items = soup.select("li.b_algo")
                    for b in algo_items:
                        h2 = b.find("h2")
                        a = h2.find("a") if h2 else None
                        if not a:
                            continue
                        raw_url = a.get("href", "")
                        real_url = self.decode_bing_url(raw_url)
                        if not real_url.startswith("http") or "bing.com" in real_url or "microsoft.com/en-us/bing" in real_url:
                            continue

                        title = a.get_text(strip=True)
                        p_el = b.find("p") or b.select_one(".b_caption p")
                        snippet = self.clean_html(p_el.get_text(strip=True)) if p_el else title

                        results.append({
                            "title": title,
                            "url": real_url,
                            "source": "Web Search (Bing Live)",
                            "pub_date": "Live Web",
                            "snippet": snippet or title,
                            "content": snippet or title,
                        })
                        if len(results) >= max_results:
                            break
        except Exception as e:
            logger.debug(f"Bing search error for '{query}': {e}")

        return results

    # =========================================================================
    # ENCYCLOPEDIC & DIRECT NEWS SOURCES
    # =========================================================================

    async def fetch_wikipedia_search(
        self,
        query: str,
        max_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Uses official Wikipedia OpenSearch / Search API for instant global topic search.
        """
        results: List[Dict[str, Any]] = []
        if not query or not query.strip():
            return results

        clean_q = re.sub(r'[^\w\s]', ' ', query).strip()
        url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(clean_q)}&utf8=&format=json"

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
                r = await client.get(url)
                if r.status_code == 200:
                    data = r.json()
                    search_items = data.get("query", {}).get("search", [])
                    for it in search_items[:max_results]:
                        title = it.get("title", "")
                        raw_snippet = it.get("snippet", "")
                        clean_snippet = self.clean_html(raw_snippet)
                        page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"

                        results.append({
                            "title": title,
                            "url": page_url,
                            "source": "Wikipedia Knowledge",
                            "pub_date": "Verified Encyclopedia",
                            "snippet": clean_snippet or title,
                            "content": clean_snippet or title,
                        })
        except Exception as e:
            logger.debug(f"Wikipedia search error for '{query}': {e}")

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

    async def fetch_direct_national_news(
        self,
        keywords: Optional[List[str]] = None,
        max_results: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Retrieves breaking national news directly from top Indian news outlets
        (The Hindu, Indian Express, NDTV, Times of India).
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

    # =========================================================================
    # HIGH-FIDELITY ARTICLE EXTRACTION (TRAFILATURA, READABILITY, CRAWL4AI, BS4)
    # =========================================================================

    async def crawl_article_text(
        self,
        url: str,
        client: Optional[httpx.AsyncClient] = None
    ) -> str:
        """
        Deep crawls a direct article URL using a 4-tier extractor hierarchy:
        1. Trafilatura (pristine text extraction, stripping navbars, ads, boilerplate)
        2. Readability-lxml (document scoring and main body synthesis)
        3. Crawl4AI (AsyncWebCrawler for dynamic browser content)
        4. BeautifulSoup4 paragraph fallback
        """
        if not url or not url.startswith("http"):
            return ""

        # Tier 1 & 2 via async HTTP fetch + Trafilatura / Readability
        try:
            async def _fetch():
                if client:
                    return await client.get(url, follow_redirects=True)
                async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout, verify=False) as c:
                    return await c.get(url, follow_redirects=True)

            resp = await _fetch()
            if resp.status_code == 200 and resp.text:
                html_content = resp.text

                # 1. Trafilatura
                if is_trafilatura_available():
                    try:
                        import trafilatura
                        extracted = trafilatura.extract(
                            html_content,
                            include_links=False,
                            include_images=False,
                            output_format="txt",
                            favor_recall=True
                        )
                        if extracted and len(extracted.strip()) > 140:
                            clean_txt = self.clean_html(extracted.strip())
                            if self.is_valid_article_body("", clean_txt):
                                return clean_txt[:3500]
                    except Exception as e:
                        logger.debug(f"Trafilatura extraction failed for {url}: {e}")

                # 2. Readability-lxml
                if is_readability_available():
                    try:
                        from readability import Document
                        doc = Document(html_content)
                        summary_html = doc.summary()
                        clean_summary = self.clean_html(summary_html)
                        if len(clean_summary) > 140 and self.is_valid_article_body("", clean_summary):
                            return clean_summary[:3000]
                    except Exception as e:
                        logger.debug(f"Readability extraction failed for {url}: {e}")

                # 3. Fallback paragraph extraction via BeautifulSoup
                try:
                    soup = bs4.BeautifulSoup(html_content, "html.parser")
                    # Focus on article / main / body
                    target = soup.find("article") or soup.find("main") or soup.body
                    if target:
                        paragraphs = [p.get_text(strip=True) for p in target.find_all("p")]
                        substantive = [p for p in paragraphs if len(p) > 35 and not any(pw in p.lower() for pw in self.PAYWALL_PATTERNS)]
                        if substantive:
                            return "\n\n".join(substantive[:6])[:2500]
                except Exception as e:
                    logger.debug(f"BS4 paragraph extraction failed for {url}: {e}")

        except Exception as e:
            logger.debug(f"HTTP fetch error for {url}: {e}")

        # Tier 3: Crawl4AI fallback
        if is_crawl4ai_available():
            try:
                from crawl4ai import AsyncWebCrawler
                async with AsyncWebCrawler(verbose=False) as crawler:
                    res = await asyncio.wait_for(crawler.arun(url=url), timeout=self.timeout)
                    if res and res.markdown:
                        clean = self.clean_html(res.markdown)
                        if self.is_valid_article_body("", clean):
                            return clean[:3000]
            except Exception as e:
                logger.debug(f"Crawl4AI extraction for {url} failed: {e}")

        return ""

    async def crawl_url(self, url: str, max_chars: int = 4000) -> Dict[str, Any]:
        """
        Directly crawls and extracts content from a given web URL.
        """
        if not url or not url.startswith("http"):
            return {"url": url, "error": "Invalid URL", "status": "failed", "content": ""}

        content = await self.crawl_article_text(url)
        source_type = "trafilatura_high_fidelity" if content else "no_content"
        title = url.split("/")[-1].replace("-", " ").replace("_", " ").title() or url

        return {
            "url": url,
            "title": title,
            "content": content,
            "status": "success" if content else "no_content",
            "crawler": source_type,
            "length": len(content)
        }

    async def crawl_with_crawl4ai(self, url: str) -> str:
        """Crawl URL using Crawl4AI dynamic rendering engine."""
        return await self.crawl_article_text(url)

    async def search_and_scrape_with_graphai(self, query: str) -> List[Dict[str, Any]]:
        """Search and extract structured knowledge using the web intelligence pipeline."""
        return await self.gather_realtime_context(query)

    @classmethod
    def is_valid_article_body(cls, title: str, body: str) -> bool:
        """Checks whether extracted body is genuine content vs newsletter/boilerplate."""
        if not body or len(body) < 60:
            return False
        bad_phrases = [
            "first day first show", "today's cache", "data point decoding",
            "subscribe now", "active subscription", "sign in to read",
            "logout and login", "unlock these with subscription", "premium stories",
            "javascript is required", "enable cookies"
        ]
        if any(bp in body.lower() for bp in bad_phrases):
            return False
        return True

    # =========================================================================
    # REAL-TIME INTELLIGENCE GATHERING PIPELINE
    # =========================================================================

    async def gather_realtime_context(
        self,
        query: str,
        target_date: Optional[str] = None,
        target_label: Optional[str] = None,
        max_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        End-to-end multi-source real-time intelligence gathering:
        1. Explicit URL in prompt -> Crawl directly via Trafilatura / Crawl4AI
        2. Observances / Special Day Queries -> Wikipedia Holidays API + Calendar Math
        3. Real-Time Universal Search -> DuckDuckGo HTML / Lite Universal Search Engine
        4. Knowledge & Encyclopedia Fallback -> Wikipedia Search API
        5. Breaking National News -> Direct Indian RSS Feeds
        6. Deep Content Crawling -> High-density article extraction across top URLs
        """
        q_lower = query.lower()
        expanded_q = self.expand_query(query)
        items: List[Dict[str, Any]] = []

        # 0. Check for explicit URL in query
        urls = self.extract_urls(query)
        if urls:
            direct_crawl = await self.crawl_url(urls[0])
            if direct_crawl.get("content"):
                return [{
                    "title": direct_crawl.get("title", "Direct Web Resource"),
                    "url": urls[0],
                    "source": "Direct Crawl",
                    "pub_date": "Live Real-Time Crawl",
                    "snippet": direct_crawl.get("content", "")[:350],
                    "content": direct_crawl.get("content", ""),
                }]

        # 1. Observance / Holiday Queries
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

        # 1.5. Direct National News Feeds for live news & current events (The Hindu, NDTV, Times of India, Indian Express)
        is_news_intent = any(w in q_lower for w in ["news", "headline", "breaking", "happening", "yesterday", "today's events", "current events", "the hindu", "ndtv"])
        if is_news_intent:
            raw_keywords = [
                w for w in re.sub(r"[^\w\s]", "", expanded_q).split()
                if len(w) > 3 and w.lower() not in ["what", "happened", "with", "yesterday", "today", "show", "tell", "news", "give", "please"]
            ]
            direct_news = await self.fetch_direct_national_news(keywords=raw_keywords, max_results=max_results)
            if direct_news:
                items.extend(direct_news)

        # 2. Universal Web Search via Bing Live Search Engine (Fast, live, authoritative)
        if len(items) < max_results:
            bing_results = await self.fetch_bing_search(query=expanded_q, max_results=max_results + 1)
            if bing_results:
                items.extend(bing_results)

        # 3. Wikipedia Topic Search Fallback
        if not items or len(items) < 2:
            wiki_search = await self.fetch_wikipedia_search(query=expanded_q, max_results=max_results)
            if wiki_search:
                items.extend(wiki_search)

        if not items:
            return []

        # Deduplicate items by URL
        seen_urls = set()
        deduped: List[Dict[str, Any]] = []
        for it in items:
            u = it.get("url", "")
            if u not in seen_urls:
                seen_urls.add(u)
                deduped.append(it)

        items = deduped[:max_results]

        # 6. Deep crawl top URLs using Trafilatura / Readability
        crawl_tasks = []
        for it in items:
            url = it.get("url", "")
            if url and url.startswith("http") and "wikipedia.org/api" not in url:
                crawl_tasks.append(self.crawl_article_text(url))
            else:
                crawl_tasks.append(asyncio.sleep(0, result=""))

        deep_texts = await asyncio.gather(*crawl_tasks)

        for i, deep_text in enumerate(deep_texts):
            title = items[i].get("title", "")
            snip = items[i].get("snippet", "")
            if deep_text and len(deep_text) > len(snip):
                items[i]["content"] = deep_text
            elif snip and snip != title:
                items[i]["content"] = f"{title}. {snip}"
            else:
                items[i]["content"] = title

        return items
