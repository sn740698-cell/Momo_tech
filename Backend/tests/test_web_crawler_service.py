"""
Unit Tests for LiveWebCrawlerService.
Verifies HTML cleaning, Google News RSS feed parsing, and real-time context gathering.
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

    def test_parse_sample_rss(self):
        sample_xml = """<rss version="2.0">
            <channel>
                <item>
                    <title>Cabinet Approves Railway Project - Press Information Bureau</title>
                    <link>https://news.google.com/articles/CAIiE...</link>
                    <pubDate>Sun, 06 Sep 2026 14:30:00 GMT</pubDate>
                    <description>&lt;a href="..."&gt;Full details of the infrastructure project...&lt;/a&gt;</description>
                    <source url="https://pib.gov.in">Press Information Bureau</source>
                </item>
            </channel>
        </rss>"""

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_resp.text = sample_xml
            mock_get.return_value = mock_resp

            results = asyncio.run(self.crawler.search_google_news("Indian government", max_results=1))
            self.assertEqual(len(results), 1)
            item = results[0]
            self.assertEqual(item["title"], "Cabinet Approves Railway Project")
            self.assertEqual(item["source"], "Press Information Bureau")
            self.assertIn("Full details of the infrastructure project", item["snippet"])
            self.assertEqual(item["pub_date"], "Sun, 06 Sep 2026 14:30:00 GMT")

    def test_gather_realtime_context(self):
        sample_items = [
            {
                "title": "Major Policy Decision",
                "source": "PIB",
                "url": "https://example.com/news/1",
                "pub_date": "Sun, 06 Sep 2026",
                "snippet": "Short summary of the policy decision.",
                "content": "Short summary of the policy decision."
            }
        ]

        with patch.object(self.crawler, "search_google_news", return_value=sample_items):
            res = asyncio.run(self.crawler.gather_realtime_context(
                query="Indian government",
                target_date="2026-09-06",
                target_label="yesterday"
            ))
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]["title"], "Major Policy Decision")
            self.assertEqual(res[0]["source"], "PIB")


if __name__ == "__main__":
    unittest.main()
