"""
Unit tests for security allowlists, permission enforcement, and IoT protocol.
"""
import unittest
from security.permissions import PermissionManager
from iot.protocol import ESP32Protocol
from iot.device_registry import DeviceRegistry
from iot.heartbeat import HeartbeatMonitor


class TestSecurityAndIoT(unittest.TestCase):

    def test_hardware_command_allowlist_sanitization(self):
        # Valid command
        valid, sanitized, msg = PermissionManager.validate_hardware_command({
            "expression": "happy",
            "animation": "celebrate",
            "led": "blink",
            "servo": {"pan": 90, "tilt": 90}
        })
        self.assertTrue(valid)
        self.assertEqual(sanitized["expression"], "happy")
        self.assertEqual(sanitized["animation"], "celebrate")
        self.assertEqual(sanitized["led"], "blink")

        # Invalid malicious command gets safely sanitized to allowlisted defaults
        valid, sanitized, msg = PermissionManager.validate_hardware_command({
            "expression": "malicious_script_inject",
            "animation": "unauthorized_spin_1000rpm",
            "led": "super_laser",
            "servo": {"pan": 9999, "tilt": -500}
        })
        self.assertTrue(valid)
        self.assertEqual(sanitized["expression"], "normal")
        self.assertEqual(sanitized["animation"], "none")
        self.assertEqual(sanitized["led"], "solid")
        # Pan and tilt constrained
        self.assertLessEqual(sanitized["servo"]["pan"], 150)
        self.assertGreaterEqual(sanitized["servo"]["tilt"], 45)

    def test_permission_toggles(self):
        PermissionManager.set_permission("camera", True)
        self.assertTrue(PermissionManager.is_camera_enabled())
        PermissionManager.set_permission("camera", False)
        self.assertFalse(PermissionManager.is_camera_enabled())

    def test_esp32_protocol(self):
        cmd = ESP32Protocol.create_device_command(expression="happy", animation="nod")
        self.assertEqual(cmd["type"], "device_command")
        self.assertEqual(cmd["expression"], "happy")
        self.assertEqual(cmd["oled_display"], "( ^ ᴗ ^ )")

    def test_device_registry_and_heartbeat(self):
        dev = HeartbeatMonitor.record_heartbeat("momo-01", battery_pct=95, rssi=-60)
        self.assertEqual(dev["status"], "online")
        self.assertEqual(dev["battery_pct"], 95)
        self.assertEqual(dev["rssi"], -60)


if __name__ == "__main__":
    unittest.main()
