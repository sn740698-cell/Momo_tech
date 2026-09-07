from typing import Dict, Any, Optional
from .activity_tracker import ActivityTracker


class ContextEngine:
    """
    Coordinates context aggregation from activity tracker, vision, and session state.
    """

    def __init__(self):
        self.tracker = ActivityTracker()
        self.vision_present: bool = True
        self.attention_state: str = "attentive"
        self.camera_enabled: bool = False

    def update_vision_state(self, present: bool, attention: str = "attentive", camera_enabled: bool = False):
        self.vision_present = present
        self.attention_state = attention
        self.camera_enabled = camera_enabled

    def update_activity(self, active_app: Optional[str] = None, idle_seconds: Optional[int] = None):
        self.tracker.update_client_telemetry(active_app=active_app, idle_seconds=idle_seconds)

    def get_snapshot(self) -> Dict[str, Any]:
        """
        Produces a consolidated context snapshot for prompt construction and decision rules.
        """
        return {
            "active_app": self.tracker.detect_foreground_window(),
            "idle_seconds": self.tracker.get_idle_seconds(),
            "session_duration_minutes": self.tracker.get_session_duration_minutes(),
            "user_present": self.vision_present if self.camera_enabled else True,
            "attention_state": self.attention_state if self.camera_enabled else "normal",
            "camera_enabled": self.camera_enabled,
        }
