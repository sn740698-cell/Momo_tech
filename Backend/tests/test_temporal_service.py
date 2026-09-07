"""
Unit Tests for Deterministic TemporalService.
Verifies date calculations, timezone handling, temporal intent analysis, and calendar observances.
"""
import unittest
from datetime import datetime
from ai_workflow.services.temporal_service import TemporalService, CALENDAR_OBSERVANCES


class TestTemporalService(unittest.TestCase):

    def test_get_temporal_anchor_fields(self):
        anchor = TemporalService.get_temporal_anchor(tz_name="Asia/Kolkata")
        
        self.assertIn("today_date", anchor)
        self.assertIn("today_day", anchor)
        self.assertIn("today_readable", anchor)
        self.assertIn("yesterday_date", anchor)
        self.assertIn("yesterday_day", anchor)
        self.assertIn("yesterday_readable", anchor)
        self.assertIn("tomorrow_date", anchor)
        self.assertIn("current_time_readable", anchor)
        self.assertEqual(anchor["timezone"], "Asia/Kolkata")

        # Verify date format YYYY-MM-DD
        self.assertRegex(anchor["today_date"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertRegex(anchor["yesterday_date"], r"^\d{4}-\d{2}-\d{2}$")

    def test_analyze_date_query(self):
        query = "what is the date today?"
        intent = TemporalService.analyze_temporal_intent(query)

        self.assertTrue(intent["is_realtime"])
        self.assertTrue(intent["is_date_query"])
        self.assertFalse(intent["needs_web_search"])
        self.assertIn("Today is", intent["direct_answer"])

    def test_analyze_yesterday_query(self):
        query = "What happened with Indian government yesterday?"
        intent = TemporalService.analyze_temporal_intent(query)

        self.assertTrue(intent["is_realtime"])
        self.assertTrue(intent["needs_web_search"])
        self.assertEqual(intent["target_label"], "yesterday")
        self.assertEqual(intent["target_date"], intent["temporal_anchor"]["yesterday_date"])

    def test_analyze_special_day_query(self):
        query = "what special today is"
        intent = TemporalService.analyze_temporal_intent(query)

        self.assertTrue(intent["is_realtime"])
        self.assertTrue(intent["is_special_day_query"])
        self.assertTrue(intent["needs_web_search"])

    def test_calendar_observances_lookup(self):
        # Test known fixed national/international days
        # Republic Day: Jan 26
        dt_republic = datetime(2026, 1, 26)
        self.assertIn("Republic Day", TemporalService.get_special_day_for_date(dt_republic))

        # Teachers Day: Sep 5
        dt_teachers = datetime(2026, 9, 5)
        self.assertIn("Teachers' Day", TemporalService.get_special_day_for_date(dt_teachers))

        # Clean Air Day: Sep 7
        dt_clean_air = datetime(2026, 9, 7)
        self.assertIn("Clean Air", TemporalService.get_special_day_for_date(dt_clean_air))


if __name__ == "__main__":
    unittest.main()
