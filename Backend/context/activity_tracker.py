import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ActivityTracker:
    """
    Monitors user activity, active foreground applications, and idle time.
    """

    def __init__(self):
        self.last_active_time = time.time()
        self.session_start_time = time.time()
        self.active_app_name = "Desktop"
        self.client_idle_seconds = 0

    def update_client_telemetry(self, active_app: Optional[str] = None, idle_seconds: Optional[int] = None):
        """
        Updates tracker from client-reported WebSocket telemetry.
        """
        if active_app:
            self.active_app_name = active_app
        if idle_seconds is not None:
            self.client_idle_seconds = idle_seconds
            if idle_seconds == 0:
                self.last_active_time = time.time()

    def record_user_action(self):
        self.last_active_time = time.time()
        self.client_idle_seconds = 0

    def get_idle_seconds(self) -> int:
        if self.client_idle_seconds > 0:
            return self.client_idle_seconds
        return int(time.time() - self.last_active_time)

    def get_session_duration_minutes(self) -> int:
        return int((time.time() - self.session_start_time) // 60)

    def detect_foreground_window(self) -> str:
        """
        Attempts to read active window title on Windows without crashing if ctypes is restricted.
        """
        if sys.platform == "win32":
            try:
                import ctypes
                user32 = ctypes.windll.user32
                hwnd = user32.GetForegroundWindow()
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value
                    if title:
                        self.active_app_name = title
                        return title
            except Exception:
                pass
        return self.active_app_name
