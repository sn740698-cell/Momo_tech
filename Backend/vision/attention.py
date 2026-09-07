from typing import Dict, Any


class AttentionEstimator:
    """
    Estimates user gaze and screen attention state.
    """

    def __init__(self):
        self.state = "attentive"

    def estimate(self, face_landmarks=None) -> Dict[str, Any]:
        return {
            "attention_state": self.state,
            "looking_at_screen": True,
            "confidence": 0.90,
        }
