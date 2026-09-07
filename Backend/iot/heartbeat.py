"""
Heartbeat watchdog and connection monitor for ESP32.
Detects disconnections and fires events deterministically.
"""
import time
import logging
from typing import Dict, Any, List
from .device_registry import DeviceRegistry

logger = logging.getLogger(__name__)

HEARTBEAT_TIMEOUT_SECONDS = 15.0


class HeartbeatMonitor:
    """
    Periodic monitor to detect disconnected devices without blocking the event loop.
    """

    @staticmethod
    def record_heartbeat(device_id: str, battery_pct: int = None, rssi: int = None) -> Dict[str, Any]:
        logger.debug(f"Heartbeat received from {device_id}: battery={battery_pct}%, rssi={rssi}dBm")
        return DeviceRegistry.register_or_update(
            device_id=device_id,
            battery_pct=battery_pct,
            rssi=rssi
        )

    @staticmethod
    def check_timeouts() -> List[str]:
        """
        Checks for timed-out devices and marks them disconnected.
        Returns list of device IDs that disconnected.
        """
        now = time.time()
        disconnected = []
        for dev_id, dev in DeviceRegistry.get_all_devices().items():
            if dev.get("status") == "online":
                last = dev.get("last_seen", 0)
                if now - last > HEARTBEAT_TIMEOUT_SECONDS:
                    DeviceRegistry.mark_disconnected(dev_id)
                    disconnected.append(dev_id)
                    logger.warning(f"Device {dev_id} heartbeat timed out (last seen {round(now - last, 1)}s ago).")
        return disconnected
