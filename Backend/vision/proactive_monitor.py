"""
Proactive Caring & Anti-Burnout Companion Monitor for MOMO.
Tracks continuous user presence, fatigue, work duration, and multi-sensor emotional states.
Strict rule: Game break timer ONLY runs when the user is continuously BOTH sad AND fully tired.
Only after the countdown gets over while sad AND tired does MOMO suggest a game break.
"""
import time
import logging
import threading
from typing import Dict, Any, Optional, Callable, List

from .camera import CameraManager, get_camera_manager
from .expression_detector import ExpressionDetector
from security.permissions import PermissionManager

logger = logging.getLogger(__name__)


class ProactiveMonitor:
    """
    Monitors user work sessions and emotional well-being via OpenCV vision.
    Enforces strict dual-condition: game suggestion timer only starts when
    user is continuously BOTH sad AND fully tired.
    """

    DEFAULT_FATIGUE_THRESHOLD_MINUTES = 30.0

    def __init__(
        self,
        camera_manager: Optional[CameraManager] = None,
        expression_detector: Optional[ExpressionDetector] = None,
        fatigue_minutes: float = DEFAULT_FATIGUE_THRESHOLD_MINUTES,
        check_interval_seconds: float = 3.0
    ):
        self.camera_manager = camera_manager or get_camera_manager()
        self.detector = expression_detector or ExpressionDetector()
        self.fatigue_threshold_minutes = fatigue_minutes
        self.check_interval_seconds = check_interval_seconds

        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Session tracking metrics
        self.session_start_time: float = time.time()
        self.last_presence_time: float = time.time()
        self.continuous_work_seconds: float = 0.0

        # Strict dual Sad+Tired timer
        self.sad_tired_seconds: float = 0.0

        self.last_proactive_alert_time: float = 0.0
        self.proactive_cooldown_seconds: float = 300.0  # 5 minute cooldown

        # Event callbacks
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []
        self._latest_telemetry: Dict[str, Any] = self._build_telemetry()

    def add_listener(self, callback: Callable[[Dict[str, Any]], None]):
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[Dict[str, Any]], None]):
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def start(self):
        """Starts background proactive monitoring thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self.session_start_time = time.time()
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="MomoProactiveMonitor")
            self._thread.start()
            logger.info("Momo Proactive Caring Monitor started.")

    def stop(self):
        """Stops background monitoring thread."""
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Momo Proactive Caring Monitor stopped.")

    def _monitor_loop(self):
        while self._running:
            try:
                self.check_once()
            except Exception as e:
                logger.error(f"Error in proactive monitor loop: {e}")
            time.sleep(self.check_interval_seconds)

    def check_once(self) -> Dict[str, Any]:
        """
        Executes a single perception and fatigue evaluation step.
        """
        if not PermissionManager.is_camera_enabled():
            self.camera_manager.set_privacy_shutter(True)
            return self._build_telemetry(privacy_blocked=True)

        self.camera_manager.set_privacy_shutter(False)
        success, frame = self.camera_manager.read_frame()

        if success and frame is not None:
            analysis = self.detector.analyze_frame(frame)
        else:
            analysis = self.detector.get_last_analysis()

        now = time.time()
        face_detected = analysis.get("face_detected", False)
        emotion = analysis.get("emotion", "neutral")
        sensors = analysis.get("sensors", {})
        sadness_score = sensors.get("sadness_score", 0.0)
        tired_score = sensors.get("tired_score", 0.0)

        with self._lock:
            delta = now - self.last_presence_time
            if face_detected:
                if delta < 15.0:
                    self.continuous_work_seconds += delta
                else:
                    self.continuous_work_seconds = 0.0
                self.last_presence_time = now
            else:
                if now - self.last_presence_time > 300.0:
                    self.continuous_work_seconds = 0.0

            # Strict dual condition: user must be BOTH sad AND fully tired
            is_sad = (emotion == "sad" or sadness_score >= 0.50)
            is_tired = (emotion == "tired" or tired_score >= 0.50)
            is_both_sad_and_tired = face_detected and is_sad and is_tired

            if is_both_sad_and_tired:
                # Timer strictly starts and accumulates ONLY when user is BOTH sad AND fully tired!
                step_delta = delta if (0 < delta < 15.0) else 1.0
                self.sad_tired_seconds += step_delta
            else:
                # If not both sad and tired, reset timer
                self.sad_tired_seconds = 0.0

            work_mins = self.continuous_work_seconds / 60.0
            sad_tired_mins = self.sad_tired_seconds / 60.0

            # Fatigue break trigger ONLY when sad+tired countdown completes
            fatigue_detected = (
                is_both_sad_and_tired and
                sad_tired_mins >= self.fatigue_threshold_minutes
            )

            # Evaluate proactive intervention triggers
            proactive_event = None
            can_alert = (now - self.last_proactive_alert_time) > self.proactive_cooldown_seconds

            if can_alert:
                if fatigue_detected:
                    proactive_event = {
                        "trigger": "fatigue_break",
                        "message": (
                            "I notice you are feeling down and genuinely tired after continuous effort. "
                            "Would you like to take a 3-minute mindful game break to recharge? "
                            "Reply 'yes' if you'd like me to open a game for you, or 'no' to keep working."
                        ),
                        "suggested_expression": "tired",
                        "suggested_animation": "nod",
                        "work_minutes": round(work_mins, 1),
                        "sad_tired_minutes": round(sad_tired_mins, 1)
                    }
                    self.last_proactive_alert_time = now
                elif emotion == "sad" and not is_tired:
                    # Empathetic check-in without suggesting games
                    proactive_event = {
                        "trigger": "empathy_checkin",
                        "message": (
                            "I noticed you're looking a little down or overwhelmed. "
                            "You are not alone — tell me about your day. I am right here with you."
                        ),
                        "suggested_expression": "sad",
                        "suggested_animation": "tilt_left",
                        "work_minutes": round(work_mins, 1),
                        "sad_tired_minutes": round(sad_tired_mins, 1)
                    }
                    self.last_proactive_alert_time = now
                elif emotion == "stressed":
                    proactive_event = {
                        "trigger": "stress_relief",
                        "message": (
                            "Take a gentle breath! Building great things takes time, and you are doing fantastic work. "
                            "Take a short sip of water or a quick stretch — you're doing great."
                        ),
                        "suggested_expression": "normal",
                        "suggested_animation": "tilt_right",
                        "work_minutes": round(work_mins, 1),
                        "sad_tired_minutes": round(sad_tired_mins, 1)
                    }
                    self.last_proactive_alert_time = now
                elif emotion == "excited":
                    proactive_event = {
                        "trigger": "celebrate_energy",
                        "message": (
                            "I love seeing that spark in your eyes! What amazing thing are you building right now? ★ᴗ★"
                        ),
                        "suggested_expression": "excited",
                        "suggested_animation": "celebrate",
                        "work_minutes": round(work_mins, 1),
                        "sad_tired_minutes": round(sad_tired_mins, 1)
                    }
                    self.last_proactive_alert_time = now

            telemetry = self._build_telemetry(
                analysis=analysis,
                work_mins=work_mins,
                sad_tired_mins=sad_tired_mins,
                is_sad_and_tired=is_both_sad_and_tired,
                fatigue_detected=fatigue_detected,
                proactive_event=proactive_event
            )
            self._latest_telemetry = telemetry

            if proactive_event:
                for cb in self._listeners:
                    try:
                        cb(telemetry)
                    except Exception as e:
                        logger.error(f"Error calling proactive listener: {e}")

        return telemetry

    def _build_telemetry(
        self,
        analysis: Optional[Dict[str, Any]] = None,
        work_mins: float = 0.0,
        sad_tired_mins: float = 0.0,
        is_sad_and_tired: bool = False,
        fatigue_detected: bool = False,
        proactive_event: Optional[Dict[str, Any]] = None,
        privacy_blocked: bool = False
    ) -> Dict[str, Any]:
        analysis = analysis or self.detector.get_last_analysis()
        cam_status = self.camera_manager.get_status()

        return {
            "camera_available": cam_status.get("camera_opened", False),
            "privacy_blocked": privacy_blocked,
            "face_detected": analysis.get("face_detected", False),
            "face_count": analysis.get("face_count", 0),
            "emotion": analysis.get("emotion", "neutral"),
            "emotion_confidence": analysis.get("emotion_confidence", 0.0),
            "looking_at_camera": analysis.get("looking_at_camera", False),
            "head_pose": analysis.get("head_pose", "unknown"),
            "work_duration_minutes": round(work_mins, 1),
            "sad_tired_minutes": round(sad_tired_mins, 1),
            "is_sad_and_tired": is_sad_and_tired,
            "fatigue_detected": fatigue_detected,
            "proactive_event": proactive_event,
            "sensors": analysis.get("sensors", {}),
            "recognition": analysis.get("recognition", {}),
            "recognized_user": analysis.get("recognition", {}).get("user_name", "User"),
            "recognition_confidence": analysis.get("recognition", {}).get("confidence", 0.0),
            "enhancement": analysis.get("enhancement", {}),
            "clarity_score": analysis.get("sensors", {}).get("clarity_quality_sensor", 0.0),
            "enhancement_active": analysis.get("enhancement", {}).get("clarity_boosted", False),
            "expression_summary": analysis.get("expression_summary", "Idle"),
            "timestamp": time.time(),
        }

    def get_latest_telemetry(self, refresh_if_stale: bool = True) -> Dict[str, Any]:
        with self._lock:
            stale = (time.time() - self._latest_telemetry.get("timestamp", 0)) > 4.0
        if refresh_if_stale and stale:
            try:
                return self.check_once()
            except Exception as e:
                logger.debug(f"Error refreshing telemetry on demand: {e}")
        with self._lock:
            return dict(self._latest_telemetry)


# Singleton monitor instance for application lifetime
_global_monitor: Optional[ProactiveMonitor] = None


def get_proactive_monitor() -> ProactiveMonitor:
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = ProactiveMonitor()
        try:
            _global_monitor.check_once()
        except Exception as e:
            logger.debug(f"Initial proactive check: {e}")
    return _global_monitor
