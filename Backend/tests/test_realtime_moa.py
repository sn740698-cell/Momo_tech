"""
Integration Tests for Real-Time Temporal Grounding & MoA Workflow Orchestration.
Verifies:
- TemporalWebSearchAgent evidence generation
- MoA graph execution on real-time and temporal queries
- Grounding in deterministic clocks, calendar observances, and live news
"""
import os
import unittest
import asyncio
from unittest.mock import patch

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from ai_workflow.state import WorkflowState, EvidenceItem
from ai_workflow.services.temporal_service import TemporalService
from ai_workflow.agents.web_search_agent import TemporalWebSearchAgent
from ai_workflow.graph import ai_workflow_graph
from ai_workflow.services.llm_factory import LLMFactory
from ai.prompt_builder import PromptBuilder


class TestRealTimeMoAWorkflow(unittest.TestCase):

    def setUp(self):
        self.agent = TemporalWebSearchAgent()
        self.anchor = TemporalService.get_temporal_anchor()

    def test_web_search_agent_date_query(self):
        state = WorkflowState(
            user_input="What's the date today?",
            temporal_anchor=self.anchor,
            is_realtime_query=True
        )

        res = asyncio.run(self.agent.execute(state))
        self.assertIn("live_web_context", res)
        evidence = res["live_web_context"]
        self.assertGreater(len(evidence), 0)
        self.assertEqual(evidence[0].source, "Deterministic System Clock")
        self.assertIn("Today is", evidence[0].content)
        self.assertIn(self.anchor["today_readable"], evidence[0].content)

    def test_web_search_agent_special_day_query(self):
        state = WorkflowState(
            user_input="What special today is?",
            temporal_anchor=self.anchor,
            is_realtime_query=True
        )

        # Mock out external network call to isolate agent logic
        mock_crawled = [
            {
                "title": "Observance Event",
                "source": "UN",
                "url": "https://un.org/event",
                "pub_date": self.anchor["today_date"],
                "snippet": "Celebrations around the globe.",
                "content": "Celebrations around the globe."
            }
        ]

        with patch.object(self.agent.crawler_service, "gather_realtime_context", return_value=mock_crawled):
            res = asyncio.run(self.agent.execute(state))
            evidence = res["live_web_context"]
            self.assertGreater(len(evidence), 0)
            sources = [e.source for e in evidence]
            self.assertTrue(any("Observances Calendar" in s or "UN" in s for s in sources))

    def test_web_search_agent_yesterday_query(self):
        state = WorkflowState(
            user_input="What happened with Indian government yesterday?",
            temporal_anchor=self.anchor,
            is_realtime_query=True
        )

        mock_news = [
            {
                "title": "Cabinet Approves High-Speed Rail Corridor",
                "source": "Press Information Bureau",
                "url": "https://pib.gov.in/PressRelease1",
                "pub_date": self.anchor["yesterday_readable"],
                "snippet": "The Union Cabinet approved the 500km high speed railway project.",
                "content": "The Union Cabinet approved the 500km high speed railway project."
            }
        ]

        with patch.object(self.agent.crawler_service, "gather_realtime_context", return_value=mock_news):
            res = asyncio.run(self.agent.execute(state))
            evidence = res["live_web_context"]
            self.assertEqual(len(evidence), 1)
            item = evidence[0]
            self.assertIn("Cabinet Approves High-Speed Rail Corridor", item.content)
            self.assertIn("Press Information Bureau", item.source)
            self.assertEqual(item.metadata["target_date"], self.anchor["yesterday_date"])

    def test_prompt_builder_temporal_grounding(self):
        prompt = PromptBuilder.build_system_prompt(user_name="Researcher")
        self.assertIn(self.anchor["today_date"], prompt)
        self.assertIn(self.anchor["today_day"], prompt)
        self.assertIn(self.anchor["yesterday_date"], prompt)

    def test_moa_full_graph_execution_mock_mode(self):
        # Force mock provider to verify deterministic graph traversal
        os.environ["AI_MOCK_MODE"] = "true"
        try:
            state = WorkflowState(
                user_input="What happened with Indian government yesterday?",
                tenant_id="tenant_alpha",
                project_id="project_live"
            )

            mock_news = [
                {
                    "title": "Parliamentary Standing Committee Report",
                    "source": "PIB",
                    "url": "https://pib.gov.in/report",
                    "pub_date": self.anchor["yesterday_readable"],
                    "snippet": "New national policy presented.",
                    "content": "New national policy presented."
                }
            ]

            with patch("ai_workflow.services.web_crawler_service.LiveWebCrawlerService.gather_realtime_context", return_value=mock_news):
                final_state = asyncio.run(ai_workflow_graph.ainvoke(state))

                self.assertIn(final_state.get("status"), ["completed", "unresolved_exhausted"])
                self.assertIsNotNone(final_state.get("final_output"))
                self.assertTrue(len(final_state.get("final_output")) > 0)
        finally:
            os.environ["AI_MOCK_MODE"] = "false"


if __name__ == "__main__":
    unittest.main()
