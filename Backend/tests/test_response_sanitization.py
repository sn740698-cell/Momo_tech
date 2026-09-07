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


if __name__ == "__main__":
    unittest.main()
