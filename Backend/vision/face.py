from typing import Dict, Any, Optional
import numpy as np
from .expression_detector import ExpressionDetector


class FaceDetector:
    """
    OpenCV face & expression detector interface for MOMO.
    """

    def __init__(self, detector: Optional[ExpressionDetector] = None):
        self.detector = detector or ExpressionDetector()

    def detect(self, frame: Optional[np.ndarray] = None) -> Dict[str, Any]:
        if frame is not None:
            return self.detector.analyze_frame(frame)
        return self.detector.get_last_analysis()
