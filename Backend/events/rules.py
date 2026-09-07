"""
Deterministic event rules, cooldowns, and decision logic for proactive MOMO reactions.
Never delegates basic timers or cooldown arithmetic to the LLM.
"""
import time
from typing import Optional, Dict, Any, Tuple


class EventRules:
    """
    Evaluates triggers and maintains cooldown states.
    """

    # Cooldown durations in seconds
    COOLDOWNS = {
        "LONG_SESSION": 1800,  # 30 minutes
        "LONG_IDLE": 900,      # 15 minutes
        "USER_RETURNED": 600,  # 10 minutes
        "BUILD_SUCCESS": 60,   # 1 minute
        "BUILD_FAILED": 60,    # 1 minute
    }

    _last_triggered: Dict[str, float] = {}

    @classmethod
    def can_trigger(cls, event_type: str) -> bool:
        now = time.time()
        last = cls._last_triggered.get(event_type, 0.0)
        cooldown = cls.COOLDOWNS.get(event_type, 300)
        return (now - last) >= cooldown

    @classmethod
    def record_trigger(cls, event_type: str):
        cls._last_triggered[event_type] = time.time()

    @classmethod
    def evaluate(
        cls,
        session_minutes: int,
        idle_seconds: int,
        minutes_since_interaction: float,
        active_app: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        now = time.time()

        # 1. Long Session (e.g. >= 60 minutes)
        if session_minutes >= 60 and cls.can_trigger("LONG_SESSION") and minutes_since_interaction >= 5.0:
            cls.record_trigger("LONG_SESSION")
            return True, "LONG_SESSION", {
                "message": "Bro, you've been coding for an hour. Your keyboard deserves a lunch break.",
                "expression": "playful",
                "animation": "tilt_left",
                "speak": True,
                "priority": "normal"
            }

        # 2. Long Idle (e.g. >= 15 minutes idle)
        if idle_seconds >= 900 and cls.can_trigger("LONG_IDLE"):
            cls.record_trigger("LONG_IDLE")
            return True, "LONG_IDLE", {
                "message": "Looks like you stepped away. I'll stay on standby. -ᴗ-",
                "expression": "sleepy",
                "animation": "sleep",
                "speak": False,
                "priority": "low"
            }

        return False, None, None
