"""
USB-C Serial Bridge for Physical MOMO Companion.
Auto-detects USB-C COM ports, connects at 115200 baud, and bridges
bi-directional frames between the ESP32 and Django Channels.
"""
import sys
import json
import time
import logging
import threading
from typing import Optional, List, Dict, Any

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

from .protocol import ESP32Protocol
from .device_registry import DeviceRegistry
from security.permissions import PermissionManager

logger = logging.getLogger(__name__)

KNOWN_USB_IDENTIFIERS = [
    "cp210", "ch340", "ch341", "usb serial", "espressif", "ftdi", "uart", "usb-serial"
]


class SerialBridge:
    """
    Manages direct USB-C Serial communication with the ESP32 companion.
    """

    def __init__(self, port: Optional[str] = None, baud_rate: int = 115200):
        self.port = port
        self.baud_rate = baud_rate
        self.serial_conn: Optional[Any] = None
        self.running = False
        self.read_thread: Optional[threading.Thread] = None

    @classmethod
    def list_available_ports(cls) -> List[Dict[str, str]]:
        if not SERIAL_AVAILABLE:
            return []
        ports = serial.tools.list_ports.comports()
        result = []
        for p in ports:
            result.append({
                "port": p.device,
                "description": p.description,
                "hwid": p.hwid,
            })
        return result

    @classmethod
    def auto_detect_esp32_port(cls) -> Optional[str]:
        if not SERIAL_AVAILABLE:
            return None
        ports = serial.tools.list_ports.comports()
        for p in ports:
            desc = (p.description or "").lower()
            hwid = (p.hwid or "").lower()
            for ident in KNOWN_USB_IDENTIFIERS:
                if ident in desc or ident in hwid:
                    logger.info(f"Auto-detected ESP32 on {p.device}: {p.description}")
                    return p.device
        if ports:
            # Fallback to first COM port if available
            logger.info(f"No specific ESP32 identifier matched, defaulting to {ports[0].device}")
            return ports[0].device
        return None

    def connect(self) -> bool:
        if not SERIAL_AVAILABLE:
            logger.error("pyserial is not installed. Run `pip install pyserial`.")
            return False

        if not self.port:
            self.port = self.auto_detect_esp32_port()

        if not self.port:
            logger.warning("No USB-C Serial port detected for ESP32.")
            return False

        try:
            self.serial_conn = serial.Serial(self.port, self.baud_rate, timeout=1.0)
            self.running = True
            DeviceRegistry.register_or_update(
                device_id="momo-01",
                connection_type="usb_serial",
                port=self.port
            )
            logger.info(f"Connected to ESP32 on USB-C Serial port: {self.port} ({self.baud_rate} baud)")
            
            # Start background read loop
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.read_thread.start()
            return True
        except Exception as e:
            logger.error(f"Failed to open serial port {self.port}: {e}")
            self.running = False
            return False

    def send_command(self, command_dict: Dict[str, Any]) -> bool:
        """
        Validates command against allowlist and sends JSON frame over USB-C Serial.
        """
        if not self.serial_conn or not self.running:
            return False

        valid, sanitized, msg = PermissionManager.validate_hardware_command(command_dict)
        if not valid:
            logger.warning(f"Hardware command validation failed: {msg}")
            return False

        try:
            line = json.dumps(sanitized) + "\n"
            self.serial_conn.write(line.encode("utf-8"))
            self.serial_conn.flush()
            return True
        except Exception as e:
            logger.error(f"Error sending serial command: {e}")
            return False

    def _read_loop(self):
        """
        Background loop reading incoming serial frames from the ESP32.
        """
        while self.running and self.serial_conn:
            try:
                if self.serial_conn.in_waiting:
                    line = self.serial_conn.readline().decode("utf-8", errors="ignore").strip()
                    if line.startswith("{") and line.endswith("}"):
                        try:
                            payload = json.loads(line)
                            self._handle_inbound_frame(payload)
                        except json.JSONDecodeError:
                            pass
                else:
                    time.sleep(0.05)
            except Exception as e:
                logger.error(f"Serial read loop error: {e}")
                time.sleep(1)

    def _handle_inbound_frame(self, frame: Dict[str, Any]):
        msg_type = frame.get("type", "")
        if msg_type == "heartbeat":
            DeviceRegistry.register_or_update(
                device_id=frame.get("device_id", "momo-01"),
                connection_type="usb_serial",
                battery_pct=frame.get("battery_pct"),
                rssi=frame.get("rssi"),
                port=self.port
            )
        elif msg_type == "button_event":
            logger.info(f"ESP32 hardware button event received over USB-C: {frame}")
            try:
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        "momo_companion_group",
                        {
                            "type": "companion_message",
                            "payload": frame
                        }
                    )
            except Exception as e:
                logger.debug(f"Could not forward button event to channel layer: {e}")

    def disconnect(self):
        self.running = False
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except Exception:
                pass
            self.serial_conn = None
        DeviceRegistry.mark_disconnected("momo-01")
        logger.info("USB-C Serial Bridge disconnected.")


_global_bridge: Optional[SerialBridge] = None

def get_serial_bridge() -> SerialBridge:
    global _global_bridge
    if _global_bridge is None:
        _global_bridge = SerialBridge()
    return _global_bridge


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    print("Scanning for connected USB-C ESP32 companion...")
    bridge = get_serial_bridge()
    ports = bridge.list_available_ports()
    print(f"Found {len(ports)} available serial ports: {ports}")
    if bridge.connect():
        print(f"MOMO USB-C Companion connected on {bridge.port}! Press Ctrl+C to stop.")
        try:
            # Send test welcome command
            bridge.send_command({
                "expression": "happy",
                "animation": "wave",
                "led": "blink"
            })
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            bridge.disconnect()
            print("Stopped.")
    else:
        print("No ESP32 detected on USB-C. Ensure cable is plugged into laptop and drivers are installed.")
