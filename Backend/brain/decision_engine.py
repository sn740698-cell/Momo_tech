from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Deterministic rules engine to evaluate proactive triggers and ensure safe,
    respectful, non-intrusive companion behavior.
    """

    MIN_PROACTIVE_INTERVAL_SECONDS = 900  # 15 minutes between proactive popups
    LONG_SESSION_THRESHOLD_MINUTES = 60
    LONG_SESSION_COOLDOWN_MINUTES = 25

    def __init__(self):
        self.last_proactive_trigger: Optional[datetime] = None

    def evaluate_triggers(
        self,
        session_duration_minutes: int,
        idle_seconds: int,
        minutes_since_last_interaction: float,
        active_app: str = "",
        is_muted: bool = False
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Evaluates whether a proactive companion event should fire.
        Returns: (should_trigger, event_type, payload_suggestion)
        """
        if is_muted:
            return False, None, None

        now = datetime.now()

        # Check proactive rate limit
        if self.last_proactive_trigger:
            elapsed = (now - self.last_proactive_trigger).total_seconds()
            if elapsed < self.MIN_PROACTIVE_INTERVAL_SECONDS:
                return False, None, None

        # Rule 1: Long coding/work session break reminder
        if (
            session_duration_minutes >= self.LONG_SESSION_THRESHOLD_MINUTES
            and minutes_since_last_interaction >= self.LONG_SESSION_COOLDOWN_MINUTES
            and idle_seconds >= 10
        ):
            self.last_proactive_trigger = now
            return True, "LONG_SESSION_BREAK_SUGGESTION", {
                "message": f"You've been in the zone for {session_duration_minutes} minutes! How about a quick stretch or water break?",
                "expression": "happy",
                "animation": "nod",
                "speak": True,
                "priority": "low",
            }

        # Rule 2: Late Night Inactivity Check (23:00 to 06:00)
        current_hour = now.hour
        if current_hour >= 23 or current_hour < 6:
            if minutes_since_last_interaction >= 45 and idle_seconds >= 30:
                self.last_proactive_trigger = now
                return True, "LATE_NIGHT_MODE", {
                    "message": "It's getting late! Remember to get some rest when you reach a good stopping point. -ᴗ-",
                    "expression": "sleepy",
                    "animation": "tilt_right",
                    "speak": False,
                    "priority": "low",
                }

        return False, None, None

    def evaluate_hardware_button_event(self, button_name: str, event_state: str) -> Dict[str, Any]:
        """
        Handles physical ESP32 button presses.
        """
        if button_name == "action" and event_state == "pressed":
            return {
                "message": "I felt that! What would you like to work on next? ^ᴗ^",
                "expression": "excited",
                "animation": "celebrate",
                "speak": True,
                "priority": "high",
            }
        elif button_name == "mute" and event_state == "pressed":
            return {
                "message": "Muted audio. I'll stay quiet for now. ◕ᴗ◕",
                "expression": "normal",
                "animation": "nod",
                "speak": False,
                "priority": "normal",
            }
        return {
            "message": "Button tapped.",
            "expression": "happy",
            "animation": "blink",
            "speak": False,
            "priority": "low",
        }
