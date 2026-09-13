"""
Unit tests for QueryChunker: query decomposition, semantic chunking, and comprehension verification.
"""
import unittest
from ai.query_chunker import QueryChunker


class TestQueryChunker(unittest.TestCase):

    def test_decompose_compound_query(self):
        query = (
            "I've been working on this Python asyncio bug for 4 hours and I feel really stressed, "
            "can you explain what an event loop is and also give me some quick motivation?"
        )
        result = QueryChunker.decompose(query)

        self.assertIn("original_query", result)
        self.assertIn("chunks", result)
        self.assertGreaterEqual(len(result["chunks"]), 2)

        # Check emotion detection
        emotions = result["detected_emotions"]
        self.assertTrue("stressed" in emotions or "tired" in emotions)

        # Check entity extraction
        entities = result["entities"]
        self.assertTrue("python" in entities or "event loop" in entities)

        # Check directive formatting
        directive = result["comprehension_directive"]
        self.assertIn("[BACKEND AGENT QUERY DECOMPOSITION & COMPREHENSION DIRECTIVE]", directive)
        self.assertIn("STRICT RESPONSE VERIFICATION CRITERIA", directive)

    def test_decompose_math_query(self):
        query = "Calculate 42 plus 58"
        result = QueryChunker.decompose(query)
        self.assertGreaterEqual(len(result["chunks"]), 1)
        self.assertEqual(result["chunks"][0]["intent_type"], "calculation")

    def test_decompose_game_break_query(self):
        query = "I'm bored, let's play a game"
        result = QueryChunker.decompose(query)
        self.assertGreaterEqual(len(result["chunks"]), 1)
        self.assertEqual(result["chunks"][0]["intent_type"], "action_request")

    def test_response_coverage_complete(self):
        query = "I feel stressed, can you explain Python closures?"
        decomp = QueryChunker.decompose(query)
        resp = "I understand you are stressed with work, take care! A Python closure is a nested function that captures enclosing scope variables."
        coverage = QueryChunker.verify_response_coverage(decomp, resp)
        self.assertTrue(coverage["complete"])
        self.assertEqual(len(coverage["missing_chunks"]), 0)


if __name__ == "__main__":
    unittest.main()
