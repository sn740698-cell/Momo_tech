"""
Unit tests for ChromaDB vector memory, explicit memory storage/recall, and MemoryAgent.
"""
import os
import unittest
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from graph.state import MomoState, Message
from memory.chroma_memory import ChromaMemoryService
from memory.memory_manager import MemoryManager
from agents.memory_agent import MemoryAgent


class TestVectorMemoryAndDeepening(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.chroma_svc = ChromaMemoryService()
        self.manager = MemoryManager()
        self.agent = MemoryAgent()

    def test_chroma_chat_interaction_indexing_and_search(self):
        user_text = "Who is Virat Kohli?"
        assistant_text = "Virat Kohli is a world-class Indian cricketer and batsman."
        session_id = "test_session_123"

        # 1. Index interaction
        indexed = self.chroma_svc.index_chat_interaction(user_text, assistant_text, session_id)
        self.assertTrue(indexed)

        # 2. Search past chats
        results = self.chroma_svc.search_past_chats(query_text="Virat Kohli", top_k=2)
        self.assertTrue(len(results) > 0)
        self.assertIn("Virat Kohli", results[0]["document"])

    async def test_explicit_memory_save_and_recall(self):
        fact_text = "My favorite programming language is Python"
        
        # 1. Save explicit memory
        saved = await self.manager.save_explicit_memory(fact_text)
        self.assertIsNotNone(saved.get("id"))
        self.assertEqual(saved.get("content"), fact_text)

        # 2. Recall memory
        recalled = await self.manager.recall_saved_memories(query="favorite programming language")
        self.assertTrue(len(recalled) > 0)
        self.assertIn(fact_text, recalled)

    async def test_memory_agent_save_intent(self):
        state = MomoState(
            messages=[Message(role="user", content="save it to my memory: my dog is a golden retriever")],
            user_intent="save_memory",
            metadata={"memory_payload": "my dog is a golden retriever"}
        )
        res = await self.agent.run(state)
        self.assertEqual(res["current_agent"], "memory_agent")
        self.assertIn("EXPLICIT MEMORY COMMITTED TO DATABASE", res["conversation_context"])

    async def test_memory_agent_recall_intent(self):
        # First save a fact
        await self.manager.save_explicit_memory("Project Apollo launched in 1969")
        
        state = MomoState(
            messages=[Message(role="user", content="what is in my memory?")],
            user_intent="recall_memory",
            metadata={"memory_query": "Apollo"}
        )
        res = await self.agent.run(state)
        self.assertEqual(res["current_agent"], "memory_agent")
        self.assertIn("RETRIEVED FROM USER DATABASE MEMORY", res["conversation_context"])
        self.assertIn("Apollo", res["conversation_context"])

    async def test_memory_agent_conversational_enrichment(self):
        # Index prior chat
        await self.manager.record_and_index_interaction(
            user_text="I am studying quantum computing",
            assistant_text="Quantum computing utilizes superposition and entanglement.",
            session_id="test_session_qc"
        )

        state = MomoState(
            messages=[Message(role="user", content="tell me more about quantum algorithms")],
            conversation_context="User Intent: followup_deepening. Directive: Deepen topic."
        )
        res = await self.agent.run(state)
        self.assertEqual(res["current_agent"], "memory_agent")
        # Verify the supervisor directive was preserved
        self.assertIn("User Intent: followup_deepening", res["conversation_context"])


if __name__ == "__main__":
    unittest.main()
