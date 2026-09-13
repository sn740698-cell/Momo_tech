"""
Camera Manager for MOMO Physical Companion.
Manages OpenCV VideoCapture lifecycle with hardware privacy shutter enforcement.
When privacy is enabled, the camera device is released immediately.
"""
import os
import cv2
import time
import logging
import threading
import numpy as np
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class CameraManager:
    """
    Manages camera capture lifecycle via OpenCV.
    Enforces privacy shutter constraints and low-overhead thread-safe frame acquisition.
    """

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.privacy_shutter_closed: bool = False
        self.is_capturing: bool = False
        self._cap: Optional[cv2.VideoCapture] = None
        self._lock = threading.Lock()
        self._last_frame: Optional[np.ndarray] = None
        self._last_frame_time: float = 0.0
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_worker = threading.Event()

    def set_privacy_shutter(self, closed: bool):
        """
        Enforces privacy policy. When shutter is closed, release camera immediately.
        """
        with self._lock:
            self.privacy_shutter_closed = closed
            if closed:
                self._release_camera()
            logger.info(f"Privacy shutter set to: {'CLOSED (Privacy ON)' if closed else 'OPEN (Camera ON)'}")

    def start_capture(self) -> bool:
        """
        Initializes the video capture device if privacy is not active.
        Tries DirectShow, MSMF, and default backend sequentially.
        """
        with self._lock:
            if self.privacy_shutter_closed:
                logger.warning("Cannot start camera capture while privacy shutter is closed.")
                return False

            if self._cap is not None and self._cap.isOpened():
                self.is_capturing = True
                self._ensure_worker_running()
                return True

            backends = [
                ("DirectShow", cv2.CAP_DSHOW),
                ("MSMF", cv2.CAP_MSMF),
                ("Default", cv2.CAP_ANY),
            ]

            for name, backend in backends:
                try:
                    cap = cv2.VideoCapture(self.camera_index, backend)
                    if cap.isOpened():
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        cap.set(cv2.CAP_PROP_FPS, 30)
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None:
                            self._cap = cap
                            self.is_capturing = True
                            self._last_frame = test_frame
                            self._last_frame_time = time.time()
                            logger.info(f"Camera opened successfully on index {self.camera_index} using {name}.")
                            self._ensure_worker_running()
                            return True
                        else:
                            cap.release()
                except Exception as e:
                    logger.debug(f"Failed opening camera with {name}: {e}")

            logger.warning(f"Could not open physical camera on index {self.camera_index}.")
            self.is_capturing = False
            return False

    def _ensure_worker_running(self):
        """Spawns background capture thread if not already active."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_worker.clear()
            self._worker_thread = threading.Thread(
                target=self._capture_worker,
                daemon=True,
                name="CameraCaptureWorker"
            )
            self._worker_thread.start()

    def _capture_worker(self):
        """Continuously pulls frames from camera into _last_frame buffer."""
        consecutive_failures = 0
        while not self._stop_worker.is_set():
            if self.privacy_shutter_closed:
                time.sleep(0.1)
                continue

            with self._lock:
                cap = self._cap

            if cap is None or not cap.isOpened():
                time.sleep(0.1)
                continue

            try:
                ret, frame = cap.read()
                if ret and frame is not None:
                    consecutive_failures = 0
                    with self._lock:
                        self._last_frame = frame
                        self._last_frame_time = time.time()
                    time.sleep(0.005)  # Smooth ~30-60 FPS capture with yield
                else:
                    consecutive_failures += 1
                    if consecutive_failures > 30 and not self.privacy_shutter_closed:
                        # Camera may have disconnected or stalled; trigger reconnect
                        logger.warning("Camera capture stalled; triggering reconnect...")
                        self._reconnect_camera()
                        consecutive_failures = 0
                    time.sleep(0.03)
            except Exception as e:
                logger.debug(f"Capture worker read error: {e}")
                time.sleep(0.05)

    def _reconnect_camera(self):
        """Gracefully re-opens the capture device if it stalled."""
        with self._lock:
            if self._cap is not None:
                try:
                    self._cap.release()
                except Exception:
                    pass
                self._cap = None
        # Attempt restart outside the lock
        self.start_capture()

    def stop_capture(self):
        """
        Stops active capturing and releases camera resource.
        """
        with self._lock:
            self._release_camera()

    def _release_camera(self):
        self.is_capturing = False
        self._stop_worker.set()
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception as e:
                logger.warning(f"Error releasing camera: {e}")
            finally:
                self._cap = None
        self._last_frame = None

    def get_last_frame(self, fallback_mock: bool = True) -> Optional[np.ndarray]:
        """
        Returns the most recently captured real frame if available.
        If the physical camera is not initialized or still starting, returns synthetic fallback if requested.
        """
        with self._lock:
            if self.privacy_shutter_closed:
                return None
            if self._last_frame is not None:
                # Return real frame
                return self._last_frame.copy()

        # If no frame exists and not capturing, trigger start
        if not self.is_capturing and not self.privacy_shutter_closed:
            self.start_capture()

        with self._lock:
            if self._last_frame is not None:
                return self._last_frame.copy()

        if fallback_mock:
            return self.generate_mock_face_frame("happy")
        return None

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Reads the most recent frame from the camera buffer.
        Guarantees thread-safety: never calls cap.read() concurrently with the worker thread.
        Returns (success: bool, frame: Optional[np.ndarray]).
        """
        with self._lock:
            if self.privacy_shutter_closed:
                return False, None

            # If we already have a fresh frame (< 2.0s old), return it immediately
            if self._last_frame is not None and (time.time() - self._last_frame_time < 2.0):
                return True, self._last_frame.copy()

        # If not capturing, attempt start
        if not self.is_capturing and not self.privacy_shutter_closed:
            self.start_capture()

        # Wait briefly up to 150ms for the worker to pull the first frame
        for _ in range(15):
            with self._lock:
                if self._last_frame is not None:
                    return True, self._last_frame.copy()
            time.sleep(0.01)

        return True, self.generate_mock_face_frame("happy")

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            opened = self._cap.isOpened() if self._cap is not None else False
            has_recent_frame = (time.time() - self._last_frame_time < 2.5) if self._last_frame_time > 0 else False
            age = round(time.time() - self._last_frame_time, 2) if self._last_frame_time > 0 else None
            return {
                "privacy_shutter_closed": self.privacy_shutter_closed,
                "is_capturing": self.is_capturing,
                "camera_index": self.camera_index,
                "camera_opened": opened or has_recent_frame,
                "has_frames": self._last_frame is not None,
                "is_physical_feed": bool(opened and has_recent_frame),
                "last_frame_age_seconds": age,
            }

    @classmethod
    def generate_mock_face_frame(cls, emotion: str = "happy") -> np.ndarray:
        """
        Generates a synthetic 640x480 RGB frame with a detectable geometric face for testing and offline environments.
        Uses dark slate aesthetics matching MOMO UI with visible face landmarks.
        """
        frame = np.full((480, 640, 3), (25, 20, 15), dtype=np.uint8)
        center_x, center_y = 320, 230
        radius = 110

        # Subtle background grid lines
        for y in range(0, 480, 40):
            cv2.line(frame, (0, y), (640, y), (35, 30, 25), 1)
        for x in range(0, 640, 40):
            cv2.line(frame, (x, 0), (x, 480), (35, 30, 25), 1)

        # Draw head circle (face shape)
        cv2.circle(frame, (center_x, center_y), radius, (55, 45, 35), -1)
        cv2.circle(frame, (center_x, center_y), radius, (140, 110, 50), 2)

        # Draw eyes
        eye_y = center_y - 25
        left_eye_x = center_x - 40
        right_eye_x = center_x + 40

        if emotion == "tired":
            # Closed droopy eyes
            cv2.line(frame, (left_eye_x - 18, eye_y), (left_eye_x + 18, eye_y), (220, 220, 220), 3)
            cv2.line(frame, (right_eye_x - 18, eye_y), (right_eye_x + 18, eye_y), (220, 220, 220), 3)
        else:
            # Open eyes
            cv2.circle(frame, (left_eye_x, eye_y), 15, (240, 240, 240), -1)
            cv2.circle(frame, (right_eye_x, eye_y), 15, (240, 240, 240), -1)
            cv2.circle(frame, (left_eye_x, eye_y), 7, (40, 40, 40), -1)
            cv2.circle(frame, (right_eye_x, eye_y), 7, (40, 40, 40), -1)

        # Draw mouth based on emotion
        mouth_y = center_y + 40
        if emotion in ["happy", "excited"]:
            cv2.ellipse(frame, (center_x, mouth_y - 8), (40, 22), 0, 0, 180, (230, 230, 230), 3)
        elif emotion in ["sad", "stressed"]:
            cv2.ellipse(frame, (center_x, mouth_y + 12), (35, 18), 0, 180, 360, (230, 230, 230), 3)
        else:
            cv2.line(frame, (center_x - 25, mouth_y), (center_x + 25, mouth_y), (230, 230, 230), 3)

        # Status text overlay
        cv2.putText(
            frame,
            "MOMO VISION PIPELINE (STANDBY / SIMULATED)",
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (160, 220, 100),
            1,
            cv2.LINE_AA,
        )

        return frame


# Global singleton instance
_global_camera_manager: Optional[CameraManager] = None
_camera_lock = threading.Lock()


def get_camera_manager(camera_index: int = 0) -> CameraManager:
    """
    Returns the shared singleton instance of CameraManager.
    Guarantees single handle ownership on Windows.
    """
    global _global_camera_manager
    with _camera_lock:
        if _global_camera_manager is None:
            _global_camera_manager = CameraManager(camera_index=camera_index)
            try:
                _global_camera_manager.start_capture()
            except Exception as e:
                logger.warning(f"Error pre-starting camera singleton: {e}")
        return _global_camera_manager
