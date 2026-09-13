from typing import Dict, Any, Optional
import numpy as np
from .expression_detector import ExpressionDetector


class AttentionEstimator:
    """
    Estimates user gaze and attention toward camera and OLED display.
    Since the display is mounted on/near the camera, looking at the display
    directly aligns with looking at the camera lens.
    """

    def __init__(self, detector: Optional[ExpressionDetector] = None):
        self.detector = detector or ExpressionDetector()

    def estimate(self, frame: Optional[np.ndarray] = None) -> Dict[str, Any]:
        if frame is not None:
            analysis = self.detector.analyze_frame(frame)
        else:
            analysis = self.detector.get_last_analysis()

        looking = analysis.get("looking_at_camera", False)
        pose = analysis.get("head_pose", "center")
        openness = analysis.get("eye_openness", 0.8)

        state = "screen" if looking else "away"
        if openness < 0.3:
            state = "drowsy"

        return {
            "attention_state": state,
            "looking_at_screen": looking,
            "looking_at_camera": looking,
            "head_pose": pose,
            "eye_openness": openness,
            "confidence": analysis.get("emotion_confidence", 0.8),
        }
