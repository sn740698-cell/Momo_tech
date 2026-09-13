"""
Unit Tests for ResponseParser Sanitization and Anti-Cutoff Defense.
Verifies that raw JSON and cutoff disclaimers never leak into companion messages.
"""
import unittest
from ai.response_parser import ResponseParser
from brain.response_parser import ResponseParser as BrainResponseParser


class TestResponseSanitization(unittest.TestCase):

    def test_truncated_json_does_not_leak_raw_scaffolding(self):
        truncated = (
            '{\n'
            '  "expression": "thinking",\n'
            '  "animation": "tilt_left",\n'
            '  "message": "As of my cu'
        )
        resp = ResponseParser.parse(truncated)
        self.assertNotIn("{", resp.message)
        self.assertNotIn("expression", resp.message)
        self.assertNotIn("tilt_left", resp.message)
        self.assertNotIn("knowledge cutoff", resp.message.lower())
        self.assertEqual(resp.expression, "thinking")
        self.assertEqual(resp.animation, "tilt_left")

    def test_cutoff_disclaimer_sanitization(self):
        text_with_cutoff = (
            '{\n'
            '  "expression": "normal",\n'
            '  "animation": "none",\n'
            '  "message": "As of my current knowledge cutoff in March 2023, I do not have real-time information about yesterday."\n'
            '}'
        )
        resp = ResponseParser.parse(text_with_cutoff)
        self.assertNotIn("knowledge cutoff", resp.message.lower())
        self.assertNotIn("as of my current", resp.message.lower())

    def test_brain_parser_truncated_json(self):
        truncated = (
            '{\n'
            '  "expression": "happy",\n'
            '  "animation": "nod",\n'
            '  "message": "Today is Monday, September 7'
        )
        parsed = BrainResponseParser.parse(truncated)
        self.assertNotIn("{", parsed["message"])
        self.assertNotIn("expression", parsed["message"])
        self.assertIn("Today is Monday", parsed["message"])
        self.assertEqual(parsed["expression"], "happy")
        self.assertEqual(parsed["animation"], "nod")

    def test_prompt_echo_stripping(self):
        text_with_echo = (
            '{\n'
            '  "expression": "happy",\n'
            '  "animation": "nod",\n'
            '  "message": "You are MOMO, an intelligent, helpful, articulate, and deeply caring AI companion robot. I would be glad to help with that. Launched Calculator on your desktop."\n'
            '}'
        )
        resp = ResponseParser.parse(text_with_echo)
        self.assertNotIn("You are MOMO", resp.message)
        self.assertNotIn("I would be glad to help", resp.message)
        self.assertIn("Launched Calculator on your desktop", resp.message)

    def test_inability_disclaimer_stripping(self):
        disclaimer_text = (
            '{\n'
            '  "expression": "normal",\n'
            '  "animation": "none",\n'
            '  "message": "As an AI language model, I do not have access to your computer. Here is the answer."\n'
            '}'
        )
        resp = ResponseParser.parse(disclaimer_text)
        self.assertNotIn("as an ai", resp.message.lower())
        self.assertNotIn("do not have access to your computer", resp.message.lower())
        self.assertIn("Here is the answer", resp.message)

    def test_format_as_bullets(self):
        long_paragraph = (
            "Quantum computing represents a paradigm shift in data processing. "
            "It utilizes quantum bits known as qubits capable of existing in multiple states simultaneously. "
            "Superposition enables exponential parallelism compared to classical binary logic. "
            "Entanglement links qubits together to perform synchronized calculations across systems."
        )
        formatted = ResponseParser.format_as_bullets(long_paragraph, min_chars=100)
        self.assertIn("• ", formatted)
        self.assertTrue(formatted.startswith("Quantum computing represents a paradigm shift"))
        self.assertIn("• It utilizes quantum bits", formatted)


if __name__ == "__main__":
    unittest.main()
