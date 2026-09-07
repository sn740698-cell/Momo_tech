import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class CameraManager:
    """
    Manages camera lifecycle with hardware privacy shutter enforcement.
    When privacy is enabled, camera capture is completely inhibited.
    """

    def __init__(self):
        self.privacy_shutter_closed: bool = True
        self.is_capturing: bool = False

    def set_privacy_shutter(self, closed: bool):
        self.privacy_shutter_closed = closed
        if closed:
            self.stop_capture()
        logger.info(f"Privacy shutter set to: {'CLOSED (Privacy ON)' if closed else 'OPEN (Camera ON)'}")

    def start_capture(self) -> bool:
        if self.privacy_shutter_closed:
            logger.warning("Cannot start camera capture while privacy shutter is closed.")
            return False
        self.is_capturing = True
        return True

    def stop_capture(self):
        self.is_capturing = False

    def get_status(self) -> Dict[str, Any]:
        return {
            "privacy_shutter_closed": self.privacy_shutter_closed,
            "is_capturing": self.is_capturing,
        }
