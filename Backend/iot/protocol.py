from typing import Dict, Any, Optional
import time

# Supported LED modes on ESP32
LED_MODES = ["solid", "pulsing", "blink", "off"]

# Default servo angle mapping for SG90 micro-servos (pan, tilt)
SERVO_MOTION_MAP = {
    "none": {"pan": 90, "tilt": 90, "action": "hold"},
    "nod": {"pan": 90, "tilt": 110, "action": "oscillate_tilt", "repeat": 2},
    "tilt_left": {"pan": 90, "tilt": 75, "action": "hold"},
    "tilt_right": {"pan": 90, "tilt": 105, "action": "hold"},
    "celebrate": {"pan": 110, "tilt": 80, "action": "wobble", "repeat": 3},
    "wave": {"pan": 105, "tilt": 90, "action": "wobble", "repeat": 2},
    "blink": {"pan": 90, "tilt": 90, "action": "hold"},
}

OLED_FACE_MAP = {
    "normal": "( ● ᴗ ● )",
    "happy": "( ^ ᴗ ^ )",
    "thinking": "( • ᴗ • )",
    "confused": "( • _ • ? )",
    "sleepy": "( - ᴗ - )",
    "excited": "( ★ ᴗ ★ )",
    "sad": "( v _ v )",
    "angry": "( > _ < )",
    "surprised": "( o _ O )",
    "proud": "( ^ w ^ )",
    "embarrassed": "( >///< )",
}


class ESP32Protocol:
    """
    Serializes and formats command frames between Django Channels and the ESP32 robot.
    """

    @classmethod
    def create_device_command(
        cls,
        expression: str = "normal",
        animation: str = "none",
        led: Optional[str] = None,
        device_id: str = "momo-01"
    ) -> Dict[str, Any]:
        """
        Creates a validated device command frame for the ESP32.
        """
        # Automatically assign LED status if not provided
        if not led:
            if expression in ["thinking"]:
                led = "pulsing"
            elif expression in ["excited", "happy"]:
                led = "blink"
            else:
                led = "solid"

        servo_config = SERVO_MOTION_MAP.get(animation, SERVO_MOTION_MAP["none"])
        oled_art = OLED_FACE_MAP.get(expression, OLED_FACE_MAP["normal"])

        return {
            "type": "device_command",
            "device_id": device_id,
            "expression": expression,
            "oled_display": oled_art,
            "animation": animation,
            "servo": servo_config,
            "led": led if led in LED_MODES else "solid",
            "timestamp": time.time(),
        }

    @classmethod
    def parse_inbound_event(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses button events or heartbeat telemetry coming from the ESP32.
        """
        event_type = payload.get("type", "unknown")
        device_id = payload.get("device_id", "momo-01")

        if event_type == "button_event":
            return {
                "event_type": "button",
                "device_id": device_id,
                "button": payload.get("button", "action"),
                "state": payload.get("event", "pressed"),
                "timestamp": payload.get("timestamp", time.time()),
            }
        elif event_type == "heartbeat":
            return {
                "event_type": "heartbeat",
                "device_id": device_id,
                "battery_pct": payload.get("battery_pct"),
                "rssi": payload.get("rssi"),
                "timestamp": time.time(),
            }
        return {"event_type": "unknown", "raw": payload}
