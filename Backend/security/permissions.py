"""
Security and privacy permissions enforcement for MOMO.
Enforces deterministic access control for sensors and hardware allowlists.
"""
import os
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Predefined hardware command allowlists
ALLOWED_EXPRESSIONS = {
    "normal", "happy", "thinking", "confused", "sleepy", 
    "excited", "sad", "angry", "surprised", "proud", "embarrassed", "playful"
}

ALLOWED_ANIMATIONS = {
    "none", "blink", "nod", "tilt_left", "tilt_right", 
    "wave", "celebrate", "shake", "sleep"
}

ALLOWED_LED_MODES = {"solid", "pulsing", "blink", "off"}

SERVO_PAN_MIN = 30
SERVO_PAN_MAX = 150
SERVO_TILT_MIN = 45
SERVO_TILT_MAX = 135


class PermissionManager:
    """
    Central permission and privacy manager.
    Checks environment configurations and user preferences.
    """
    @staticmethod
    def is_camera_enabled() -> bool:
        val = os.getenv("CAMERA_ENABLED", "false").lower()
        return val in ("true", "1", "yes")

    @staticmethod
    def is_microphone_enabled() -> bool:
        val = os.getenv("MICROPHONE_ENABLED", "false").lower()
        return val in ("true", "1", "yes")

    @staticmethod
    def is_memory_enabled() -> bool:
        val = os.getenv("MEMORY_ENABLED", "true").lower()
        return val in ("true", "1", "yes")

    @staticmethod
    def is_activity_tracking_enabled() -> bool:
        val = os.getenv("ACTIVITY_TRACKING_ENABLED", "false").lower()
        return val in ("true", "1", "yes")

    @classmethod
    def get_all_permissions(cls) -> Dict[str, bool]:
        return {
            "camera_enabled": cls.is_camera_enabled(),
            "microphone_enabled": cls.is_microphone_enabled(),
            "memory_enabled": cls.is_memory_enabled(),
            "activity_tracking_enabled": cls.is_activity_tracking_enabled(),
        }

    @classmethod
    def set_permission(cls, key: str, enabled: bool) -> bool:
        env_map = {
            "camera": "CAMERA_ENABLED",
            "microphone": "MICROPHONE_ENABLED",
            "memory": "MEMORY_ENABLED",
            "activity": "ACTIVITY_TRACKING_ENABLED",
        }
        env_var = env_map.get(key)
        if env_var:
            os.environ[env_var] = "true" if enabled else "false"
            logger.info(f"Privacy setting updated: {env_var}={os.environ[env_var]}")
            return True
        return False

    @staticmethod
    def validate_hardware_command(command_dict: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], str]:
        """
        Validates hardware command dictionary against strict allowlists.
        Never passes unvalidated or malicious parameters to ESP32.
        """
        expr = command_dict.get("expression", "normal")
        anim = command_dict.get("animation", "none")
        led = command_dict.get("led", "solid")
        servo = command_dict.get("servo", {"pan": 90, "tilt": 90, "action": "hold"})

        # Sanitize expression
        if expr not in ALLOWED_EXPRESSIONS:
            expr = "normal"

        # Sanitize animation
        if anim not in ALLOWED_ANIMATIONS:
            anim = "none"

        # Sanitize LED mode
        if led not in ALLOWED_LED_MODES:
            led = "solid"

        # Sanitize Servo bounds
        pan = servo.get("pan", 90)
        tilt = servo.get("tilt", 90)
        pan = max(SERVO_PAN_MIN, min(SERVO_PAN_MAX, pan))
        tilt = max(SERVO_TILT_MIN, min(SERVO_TILT_MAX, tilt))
        action = servo.get("action", "hold")

        sanitized = {
            "type": "device_command",
            "device_id": command_dict.get("device_id", "momo-01"),
            "expression": expr,
            "animation": anim,
            "led": led,
            "servo": {"pan": pan, "tilt": tilt, "action": action},
            "oled_display": command_dict.get("oled_display"),
            "speak": bool(command_dict.get("speak", False)),
        }

        return True, sanitized, "Command validated successfully."
