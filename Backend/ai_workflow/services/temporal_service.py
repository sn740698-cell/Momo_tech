"""
Deterministic Temporal Grounding Service for MOMO.
Computes real-time anchors, resolves relative date expressions (yesterday, today, tomorrow),
and identifies national/international calendar observances without LLM hallucinations.
"""
import os
import re
from datetime import datetime, timedelta
import zoneinfo
from typing import Dict, Any, Optional, List


# Notable international observances and national days (India focus)
CALENDAR_OBSERVANCES = {
    (1, 1): "New Year's Day / Global Family Day",
    (1, 12): "National Youth Day (Swami Vivekananda Jayanti)",
    (1, 15): "Indian Army Day",
    (1, 23): "Parakram Diwas (Netaji Subhas Chandra Bose Jayanti)",
    (1, 26): "Republic Day of India / International Customs Day",
    (1, 30): "Martyrs' Day (Shaheed Diwas)",
    (2, 4): "World Cancer Day",
    (2, 13): "National Women's Day (Sarojini Naidu Jayanti)",
    (2, 28): "National Science Day (Raman Effect Discovery)",
    (3, 8): "International Women's Day",
    (3, 15): "World Consumer Rights Day",
    (3, 21): "World Forestry Day / International Day of Forests",
    (3, 22): "World Water Day",
    (3, 23): "Shaheed Diwas (Bhagat Singh, Sukhdev, Rajguru)",
    (4, 7): "World Health Day",
    (4, 14): "Dr. B. R. Ambedkar Jayanti / National Water Day",
    (4, 22): "Earth Day",
    (5, 1): "International Labour Day / Maharashtra Day / Gujarat Day",
    (5, 11): "National Technology Day",
    (5, 31): "World No Tobacco Day",
    (6, 5): "World Environment Day",
    (6, 21): "International Day of Yoga / World Music Day",
    (7, 1): "National Doctor's Day / Chartered Accountants Day / GST Day",
    (7, 26): "Kargil Vijay Diwas",
    (8, 7): "National Handloom Day / National Javelin Day",
    (8, 12): "International Youth Day",
    (8, 15): "Independence Day of India",
    (8, 20): "Sadbhavana Diwas",
    (8, 29): "National Sports Day (Major Dhyan Chand Jayanti)",
    (9, 5): "National Teachers' Day (Dr. S. Radhakrishnan Jayanti)",
    (9, 7): "International Day of Clean Air for blue skies",
    (9, 8): "International Literacy Day",
    (9, 14): "Hindi Diwas",
    (9, 15): "Engineers' Day (M. Visvesvaraya Jayanti) / International Day of Democracy",
    (9, 16): "World Ozone Day",
    (9, 21): "International Day of Peace",
    (9, 27): "World Tourism Day",
    (10, 2): "Gandhi Jayanti / International Day of Non-Violence / Lal Bahadur Shastri Jayanti",
    (10, 8): "Indian Air Force Day",
    (10, 11): "International Day of the Girl Child",
    (10, 16): "World Food Day",
    (10, 24): "United Nations Day",
    (10, 31): "National Unity Day (Rashtriya Ekta Diwas - Sardar Patel Jayanti)",
    (11, 11): "National Education Day (Maulana Abul Kalam Azad Jayanti)",
    (11, 14): "Children's Day (Jawaharlal Nehru Jayanti) / World Diabetes Day",
    (11, 26): "Constitution Day of India (Samvidhan Diwas) / National Milk Day",
    (12, 1): "World AIDS Day",
    (12, 4): "Indian Navy Day",
    (12, 7): "Armed Forces Flag Day",
    (12, 10): "Human Rights Day",
    (12, 16): "Vijay Diwas",
    (12, 22): "National Mathematics Day (Srinivasa Ramanujan Jayanti)",
    (12, 23): "Kisan Diwas (National Farmers' Day - Chaudhary Charan Singh Jayanti)",
    (12, 25): "Good Governance Day (Atal Bihari Vajpayee Jayanti) / Christmas",
}


class TemporalService:
    """
    Provides deterministic date, time, and calendar computations.
    """

    @classmethod
    def get_timezone_name(cls) -> str:
        return os.getenv("DEFAULT_TIMEZONE", "Asia/Kolkata")

    @classmethod
    def get_temporal_anchor(cls, tz_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Computes deterministic temporal anchor with day of week, relative dates,
        and calendar observances.
        """
        tz_str = tz_name or cls.get_timezone_name()
        try:
            tz = zoneinfo.ZoneInfo(tz_str)
        except Exception:
            tz = zoneinfo.ZoneInfo("Asia/Kolkata")
            tz_str = "Asia/Kolkata"

        now = datetime.now(tz)
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        special_today = cls.get_special_day_for_date(now)
        special_yesterday = cls.get_special_day_for_date(yesterday)

        return {
            "iso_timestamp": now.isoformat(),
            "timezone": tz_str,
            "today_date": now.strftime("%Y-%m-%d"),
            "today_day": now.strftime("%A"),
            "today_readable": now.strftime("%B %d, %Y"),
            "current_time_readable": now.strftime("%I:%M %p"),
            "yesterday_date": yesterday.strftime("%Y-%m-%d"),
            "yesterday_day": yesterday.strftime("%A"),
            "yesterday_readable": yesterday.strftime("%B %d, %Y"),
            "tomorrow_date": tomorrow.strftime("%Y-%m-%d"),
            "tomorrow_day": tomorrow.strftime("%A"),
            "tomorrow_readable": tomorrow.strftime("%B %d, %Y"),
            "special_today": special_today,
            "special_yesterday": special_yesterday,
        }

    @classmethod
    def get_special_day_for_date(cls, dt: datetime) -> Optional[str]:
        """Looks up calendar observances for a given datetime."""
        key = (dt.month, dt.day)
        return CALENDAR_OBSERVANCES.get(key)

    @classmethod
    def analyze_temporal_intent(cls, query: str) -> Dict[str, Any]:
        """
        Analyzes query to detect if real-time web search or temporal grounding is required.
        Resolves the exact target date for relative terms (today, yesterday, etc.).
        """
        q_lower = query.lower()
        anchor = cls.get_temporal_anchor()

        is_realtime = False
        target_date = anchor["today_date"]
        target_label = "today"
        reason = "standard"

        # Explicit date question
        if re.search(r"\b(what('s| is) the date|what date is it|today('s| is) date|date today)\b", q_lower):
            return {
                "is_realtime": True,
                "needs_web_search": False,  # Answerable deterministically from anchor
                "is_date_query": True,
                "target_date": anchor["today_date"],
                "target_label": "today",
                "direct_answer": f"Today is {anchor['today_day']}, {anchor['today_readable']} ({anchor['timezone']}).",
                "temporal_anchor": anchor,
            }

        # Special day query
        if re.search(r"\b(what special today|what is special today|special day today|today special|is today any special day)\b", q_lower):
            special = anchor.get("special_today")
            direct_ans = None
            if special:
                direct_ans = f"Today ({anchor['today_readable']}) is observed as: {special}."
            return {
                "is_realtime": True,
                "needs_web_search": True,  # Search for additional observances/news
                "is_special_day_query": True,
                "target_date": anchor["today_date"],
                "target_label": "today",
                "direct_answer": direct_ans,
                "temporal_anchor": anchor,
            }

        # Yesterday questions
        if "yesterday" in q_lower or "last night" in q_lower:
            is_realtime = True
            target_date = anchor["yesterday_date"]
            target_label = "yesterday"
            reason = "query references yesterday"

        # Today / Breaking news / Now questions
        elif any(k in q_lower for k in [
            "today", "happening now", "latest news", "breaking news", "current news",
            "recent updates", "what happened", "indian government", "cabinet decision"
        ]):
            is_realtime = True
            target_date = anchor["today_date"]
            target_label = "today"
            reason = "query references real-time / current news"

        return {
            "is_realtime": is_realtime,
            "needs_web_search": is_realtime,
            "target_date": target_date,
            "target_label": target_label,
            "reason": reason,
            "temporal_anchor": anchor,
        }
