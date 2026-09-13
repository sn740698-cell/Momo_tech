"""
Tests for DesktopAutomationController, AutomationSupervisor/Agent,
ResearchSupervisor/WebCrawlAgent, and LLM-driven query orchestration.
"""
import unittest
import asyncio
from unittest.mock import patch, MagicMock

from graph.state import MomoState, Message
from graph.graph import momo_graph
from automation.desktop_controller import DesktopAutomationController, get_desktop_controller
from supervisors.root import RootSupervisor
from supervisors.automation import AutomationSupervisor
from supervisors.research import ResearchSupervisor
from agents.automation_agent import AutomationAgent
from agents.web_crawl_agent import WebCrawlAgent
from agents.conversation_agent import ConversationAgent


class TestAutomationAndSupervisors(unittest.TestCase):

    def setUp(self):
        self.controller = get_desktop_controller()

    def test_extract_automation_intent(self):
        # Instagram
        i1 = self.controller.extract_automation_intent("open instagram")
        self.assertIsNotNone(i1)
        self.assertEqual(i1["target"], "instagram")
        self.assertEqual(i1["url"], "https://www.instagram.com")

        # YouTube
        i2 = self.controller.extract_automation_intent("open youtube")
        self.assertIsNotNone(i2)
        self.assertEqual(i2["target"], "youtube")

        # Generic URL
        i3 = self.controller.extract_automation_intent("open https://github.com/trending")
        self.assertIsNotNone(i3)
        self.assertEqual(i3["url"], "https://github.com/trending")

        # Game
        i4 = self.controller.extract_automation_intent("play 2048")
        self.assertIsNotNone(i4)
        self.assertEqual(i4["type"], "launch_game")

    def test_root_supervisor_intent_classification(self):
        # Automation intent
        s1 = MomoState(messages=[Message(role="user", content="open instagram")])
        self.assertEqual(RootSupervisor.evaluate_route("open instagram", s1), "automation")

        # Web crawl / research intent
        s2 = MomoState(messages=[Message(role="user", content="OK GO WEB CRAWL ABOUT SIH INDIA HACKOTHON")])
        self.assertEqual(RootSupervisor.evaluate_route("OK GO WEB CRAWL ABOUT SIH INDIA HACKOTHON", s2), "research")

        # Greeting intent
        s3 = MomoState(messages=[Message(role="user", content="hi")])
        self.assertEqual(RootSupervisor.evaluate_route("hi", s3), "conversation")

        # "OK" at the start of a command is NOT treated as standalone affirmation
        intent = RootSupervisor.analyze_query_intent("OK GO WEB CRAWL ABOUT SIH INDIA HACKOTHON")
        self.assertEqual(intent["intent"], "web_crawl")

    def test_automation_supervisor_and_agent(self):
        auto_sup = AutomationSupervisor()
        state = MomoState(messages=[Message(role="user", content="open instagram")])
        res_sup = asyncio.run(auto_sup.run(state))
        self.assertEqual(res_sup["supervisor_decisions"][0].target_agent, "automation_agent")

        auto_agent = AutomationAgent()
        with patch.object(self.controller, "execute_automation") as mock_exec:
            mock_exec.return_value = {
                "success": True,
                "action": "open_website",
                "target": "Instagram",
                "url": "https://www.instagram.com",
                "summary": "Opened Instagram in web browser."
            }
            res_agent = asyncio.run(auto_agent.run(state))
            self.assertIn("automation_result", res_agent["metadata"])
            self.assertTrue(res_agent["metadata"]["automation_result"]["success"])
            self.assertIn("DESKTOP AUTOMATION EXECUTED", res_agent["conversation_context"])

    def test_research_supervisor_and_agent(self):
        res_sup = ResearchSupervisor()
        state = MomoState(messages=[Message(role="user", content="crawl SIH India Hackathon")])
        sup_res = asyncio.run(res_sup.run(state))
        self.assertIn(sup_res["supervisor_decisions"][0].target_agent, ["search_scout_agent", "web_crawl_agent"])

        crawl_agent = WebCrawlAgent()
        with patch.object(crawl_agent.crawler, "gather_realtime_context") as mock_crawl:
            mock_crawl.return_value = [
                {
                    "title": "Smart India Hackathon",
                    "source": "Official Portal",
                    "url": "https://sih.gov.in/",
                    "content": "Smart India Hackathon is a nationwide initiative to solve problems."
                }
            ]
            res_crawl = asyncio.run(crawl_agent.run(state))
            self.assertTrue(len(res_crawl["retrieved_context"]) >= 1)
            self.assertTrue(len(res_crawl["retrieved_context"][0].content) > 20)


if __name__ == "__main__":
    unittest.main()
