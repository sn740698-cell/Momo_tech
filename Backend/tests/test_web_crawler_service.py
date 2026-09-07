"""
Unit Tests for LiveWebCrawlerService.
Verifies HTML cleaning, national news feeds, Wikipedia observances,
paywall filtering, and real-time context gathering.
"""
import unittest
import asyncio
from unittest.mock import patch, AsyncMock
from ai_workflow.services.web_crawler_service import LiveWebCrawlerService


class TestLiveWebCrawlerService(unittest.TestCase):

    def setUp(self):
        self.crawler = LiveWebCrawlerService(timeout_seconds=5.0)

    def test_clean_html(self):
        raw_html = (
            "<html><head><script>alert('xss');</script><style>p {color: red;}</style></head>"
            "<body><header><nav>Home Links</nav></header>"
            "<main><p>The Cabinet approved the <b>new policy</b> yesterday &amp; today.</p></main>"
            "<footer>Copyright 2026</footer></body></html>"
        )
        cleaned = self.crawler.clean_html(raw_html)
        self.assertNotIn("<script>", cleaned)
        self.assertNotIn("alert", cleaned)
        self.assertNotIn("<nav>", cleaned)
        self.assertNotIn("Copyright", cleaned)
        self.assertEqual(cleaned, "The Cabinet approved the new policy yesterday & today.")

    def test_is_valid_article_body(self):
        title = "Cabinet Approves High-Speed Rail Project"
        good_body = "The Union Cabinet on Monday approved the high-speed rail corridor connecting major industrial zones."
        paywall_body = "Subscribed with another email? Logout and login. Unlock these with subscription."
        unrelated_body = "Today's cache: download top 5 tech stories. Data point decoding the headlines."

        self.assertTrue(self.crawler.is_valid_article_body(title, good_body))
        self.assertFalse(self.crawler.is_valid_article_body(title, paywall_body))
        self.assertFalse(self.crawler.is_valid_article_body(title, unrelated_body))

    def test_gather_realtime_context(self):
        sample_items = [
            {
                "title": "Major Policy Decision",
                "source": "PIB",
                "url": "https://example.com/news/1",
                "pub_date": "Sun, 06 Sep 2026",
                "snippet": "Short summary of the policy decision.",
                "content": "Major Policy Decision. Short summary of the policy decision."
            }
        ]

        with patch.object(self.crawler, "fetch_direct_national_news", new_callable=AsyncMock) as mock_news:
            mock_news.return_value = sample_items
            res = asyncio.run(self.crawler.gather_realtime_context(
                query="Indian government",
                target_date="2026-09-06",
                target_label="yesterday"
            ))
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]["title"], "Major Policy Decision")
            self.assertEqual(res[0]["source"], "PIB")

    def test_special_day_wikipedia_lookup(self):
        sample_wiki = [
            {
                "title": "International Day of Clean Air",
                "source": "Wikipedia Observances",
                "url": "https://en.wikipedia.org/wiki/Clean_Air",
                "pub_date": "Calendar 09-07",
                "snippet": "Observed globally.",
                "content": "Observed globally."
            }
        ]

        with patch.object(self.crawler, "fetch_special_days_wikipedia", new_callable=AsyncMock) as mock_wiki:
            mock_wiki.return_value = sample_wiki
            res = asyncio.run(self.crawler.gather_realtime_context(
                query="what special today is",
                target_date="2026-09-07",
                target_label="today"
            ))
            self.assertGreaterEqual(len(res), 1)
            self.assertEqual(res[0]["title"], "International Day of Clean Air")


if __name__ == "__main__":
    unittest.main()
