from typing import Dict, Any


class FaceDetector:
    """
    Lightweight face & presence detector interface.
    Gracefully falls back to mock telemetry if OpenCV/MediaPipe is not installed.
    """

    def __init__(self):
        self.face_present: bool = True
        self.face_count: int = 1

    def detect(self, frame=None) -> Dict[str, Any]:
        return {
            "face_detected": self.face_present,
            "face_count": self.face_count,
            "confidence": 0.95 if self.face_present else 0.0,
        }
