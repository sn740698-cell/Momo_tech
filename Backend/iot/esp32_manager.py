import time
import logging
from typing import Dict, Any, List
from asgiref.sync import sync_to_async
from momo.models import DeviceConnection
from .protocol import ESP32Protocol

logger = logging.getLogger(__name__)


class ESP32Manager:
    """
    Registry and coordination layer for registered ESP32 physical companion robots.
    """

    @staticmethod
    def register_or_update_heartbeat(device_id: str, battery_pct: int = None, rssi: int = None, ip_address: str = None) -> DeviceConnection:
        dev, _ = DeviceConnection.objects.update_or_create(
            device_id=device_id,
            defaults={
                "is_online": True,
                "battery_pct": battery_pct,
                "rssi": rssi,
                "ip_address": ip_address,
            }
        )
        return dev

    @staticmethod
    def mark_offline(device_id: str):
        DeviceConnection.objects.filter(device_id=device_id).update(is_online=False)

    @staticmethod
    def list_devices() -> List[Dict[str, Any]]:
        devices = DeviceConnection.objects.all()
        return [
            {
                "device_id": d.device_id,
                "device_type": d.device_type,
                "is_online": d.is_online,
                "battery_pct": d.battery_pct,
                "rssi": d.rssi,
                "ip_address": d.ip_address,
                "registered_at": d.registered_at.isoformat(),
            }
            for d in devices
        ]

    @classmethod
    def serialize_command(cls, expression: str, animation: str = "none", led: str = None, device_id: str = "momo-01") -> Dict[str, Any]:
        return ESP32Protocol.create_device_command(
            expression=expression,
            animation=animation,
            led=led,
            device_id=device_id
        )
