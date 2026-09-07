"""
Unit tests for LangGraph Supervisors and routing decisions.
"""
import unittest
from graph.state import MomoState, Message
from supervisors.root import RootSupervisor
from supervisors.finance import FinanceSupervisor
from supervisors.communication import CommunicationSupervisor
from supervisors.conversation import ConversationSupervisor


class TestSupervisors(unittest.IsolatedAsyncioTestCase):

    async def test_root_supervisor_conversation_routing(self):
        root = RootSupervisor()
        state = MomoState(messages=[Message(role="user", content="Hello MOMO, how's your day?")])
        result = await root.run(state)
        self.assertEqual(result["current_route"], "conversation")
        self.assertTrue(len(result["supervisor_decisions"]) > 0)

    async def test_root_supervisor_finance_routing(self):
        root = RootSupervisor()
        state = MomoState(messages=[Message(role="user", content="What is the balance due on invoice INV-1042?")])
        result = await root.run(state)
        self.assertEqual(result["current_route"], "finance")

    async def test_root_supervisor_communication_routing(self):
        root = RootSupervisor()
        state = MomoState(messages=[Message(role="user", content="Draft a reminder message for Rahul regarding his overdue invoice balance.")])
        result = await root.run(state)
        self.assertEqual(result["current_route"], "communication")

    async def test_root_supervisor_system_routing(self):
        root = RootSupervisor()
        state = MomoState(messages=[Message(role="user", content="Test ESP32 hardware servo connect and telemetry.")])
        result = await root.run(state)
        self.assertEqual(result["current_route"], "system")

    async def test_finance_supervisor(self):
        fin = FinanceSupervisor()
        state = MomoState(messages=[Message(role="user", content="Check invoice")])
        result = await fin.run(state)
        self.assertEqual(result["supervisor_decisions"][0].supervisor, "finance_supervisor")

    def test_intent_save_memory(self):
        intent_info = RootSupervisor.analyze_query_intent("save it to my memory: my dog's name is Bruno")
        self.assertEqual(intent_info["intent"], "save_memory")
        self.assertEqual(intent_info["memory_payload"], "my dog's name is Bruno")

    def test_intent_recall_memory(self):
        intent_info = RootSupervisor.analyze_query_intent("what is in my memory?")
        self.assertEqual(intent_info["intent"], "recall_memory")

    def test_intent_followup_deepening(self):
        messages = [
            Message(role="user", content="Who is Virat Kohli?"),
            Message(role="assistant", content="Virat Kohli is an Indian cricketer.")
        ]
        intent_info = RootSupervisor.analyze_query_intent("tell me more about him", messages)
        self.assertEqual(intent_info["intent"], "followup_deepening")
        self.assertEqual(intent_info["topic"], "Virat Kohli")

    def test_safe_eval_math(self):
        self.assertEqual(RootSupervisor.safe_eval_math("What is 42 * 17?"), "714")
        self.assertEqual(RootSupervisor.safe_eval_math("calculate 100 plus 250"), "350")
        self.assertIsNone(RootSupervisor.safe_eval_math("hello world"))


if __name__ == "__main__":
    unittest.main()
