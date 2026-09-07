"""
Device Registry for Physical MOMO Companions.
Tracks active ESP32 units and their physical health telemetry.
"""
import time
from typing import Dict, Any, Optional


class DeviceRegistry:
    """
    In-memory registry of connected physical ESP32 devices.
    """
    _devices: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register_or_update(
        cls,
        device_id: str = "momo-01",
        connection_type: str = "websocket",
        battery_pct: Optional[int] = None,
        rssi: Optional[int] = None,
        port: Optional[str] = None
    ) -> Dict[str, Any]:
        now = time.time()
        device = cls._devices.get(device_id, {
            "device_id": device_id,
            "status": "online",
            "first_connected": now,
        })

        device.update({
            "status": "online",
            "connection_type": connection_type,
            "last_seen": now,
            "battery_pct": battery_pct if battery_pct is not None else device.get("battery_pct"),
            "rssi": rssi if rssi is not None else device.get("rssi"),
            "port": port if port is not None else device.get("port"),
        })

        cls._devices[device_id] = device
        return device

    @classmethod
    def mark_disconnected(cls, device_id: str = "momo-01") -> Optional[Dict[str, Any]]:
        if device_id in cls._devices:
            cls._devices[device_id]["status"] = "disconnected"
            return cls._devices[device_id]
        return None

    @classmethod
    def get_device(cls, device_id: str = "momo-01") -> Optional[Dict[str, Any]]:
        return cls._devices.get(device_id)

    @classmethod
    def get_all_devices(cls) -> Dict[str, Dict[str, Any]]:
        return dict(cls._devices)
