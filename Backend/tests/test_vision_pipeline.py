"""
Unit Tests for OpenCV Facial Expression, Emotion Perception, & Proactive Care.
Verifies:
1. CameraManager lifecycle and privacy shutter safety enforcement.
2. ExpressionDetector facial landmark, camera gaze, smile, and fatigue classification.
3. ProactiveMonitor continuous work duration tracking (30-min alert) and proactive triggers.
"""
import unittest
import numpy as np
import time
from unittest.mock import patch, MagicMock

from vision.camera import CameraManager
from vision.expression_detector import ExpressionDetector
from vision.proactive_monitor import ProactiveMonitor
from vision.face import FaceDetector
from vision.attention import AttentionEstimator
from security.permissions import PermissionManager


class TestVisionPipeline(unittest.TestCase):

    def setUp(self):
        PermissionManager.set_permission("camera", True)
        self.camera = CameraManager()
        self.detector = ExpressionDetector()

    def tearDown(self):
        self.camera.stop_capture()

    def test_camera_privacy_shutter_enforcement(self):
        """When privacy shutter is closed, camera capture is completely inhibited."""
        self.camera.set_privacy_shutter(True)
        self.assertTrue(self.camera.privacy_shutter_closed)
        success, frame = self.camera.read_frame()
        self.assertFalse(success)
        self.assertIsNone(frame)

        # Reopen privacy shutter
        self.camera.set_privacy_shutter(False)
        self.assertFalse(self.camera.privacy_shutter_closed)

    def test_synthetic_face_generation(self):
        """Verifies synthetic test frames generate valid RGB images."""
        frame = CameraManager.generate_mock_face_frame("happy")
        self.assertIsInstance(frame, np.ndarray)
        self.assertEqual(frame.shape, (480, 640, 3))

    def test_expression_detector_default_on_empty(self):
        """Detector returns safe default when frame is None."""
        res = self.detector.analyze_frame(None)
        self.assertFalse(res["face_detected"])
        self.assertEqual(res["face_count"], 0)
        self.assertEqual(res["emotion"], "neutral")

    def test_expression_detector_landmarks_and_emotions(self):
        """Verifies landmark, emotion, and gaze detection."""
        frame_happy = CameraManager.generate_mock_face_frame("happy")
        res_happy = self.detector.analyze_frame(frame_happy)
        self.assertIn("emotion", res_happy)
        self.assertIn("looking_at_camera", res_happy)
        self.assertIn("smile_intensity", res_happy)
        self.assertIn("eye_openness", res_happy)

        frame_tired = CameraManager.generate_mock_face_frame("tired")
        res_tired = self.detector.analyze_frame(frame_tired)
        self.assertIn("emotion", res_tired)
        self.assertIn("tired_score", res_tired)

    def test_proactive_monitor_fatigue_alert(self):
        """Verifies that exceeding 30 minutes of continuous sad+tired state triggers fatigue alert."""
        monitor = ProactiveMonitor(fatigue_minutes=30.0, check_interval_seconds=1.0)
        # Simulate 31 minutes of continuous work and sad+tired countdown
        monitor.continuous_work_seconds = 31.0 * 60.0
        monitor.sad_tired_seconds = 31.0 * 60.0
        monitor.last_proactive_alert_time = 0.0  # Cold cooldown

        # Mock camera frame returning a sad+tired face
        with patch.object(monitor.camera_manager, "read_frame") as mock_read:
            mock_frame = CameraManager.generate_mock_face_frame("tired")
            mock_read.return_value = (True, mock_frame)
            with patch.object(monitor.detector, "analyze_frame") as mock_analyze:
                mock_analyze.return_value = {
                    "face_detected": True,
                    "emotion": "sad",
                    "emotion_confidence": 0.85,
                    "sensors": {
                        "sadness_score": 0.75,
                        "tired_score": 0.70,
                    }
                }
                telemetry = monitor.check_once()
                self.assertTrue(telemetry["fatigue_detected"])
                self.assertIsNotNone(telemetry["proactive_event"])
                self.assertEqual(telemetry["proactive_event"]["trigger"], "fatigue_break")
                self.assertIn("game", telemetry["proactive_event"]["message"].lower())

    def test_proactive_monitor_neutral_or_happy_no_game_alert(self):
        """Verifies that working 31 minutes while NOT sad and tired never suggests a game break."""
        monitor = ProactiveMonitor(fatigue_minutes=30.0, check_interval_seconds=1.0)
        monitor.continuous_work_seconds = 31.0 * 60.0
        monitor.sad_tired_seconds = 0.0

        with patch.object(monitor.camera_manager, "read_frame") as mock_read:
            mock_read.return_value = (True, CameraManager.generate_mock_face_frame("happy"))
            with patch.object(monitor.detector, "analyze_frame") as mock_analyze:
                mock_analyze.return_value = {
                    "face_detected": True,
                    "emotion": "happy",
                    "emotion_confidence": 0.90,
                    "sensors": {
                        "happiness_score": 0.85,
                        "sadness_score": 0.05,
                        "tired_score": 0.10,
                    }
                }
                telemetry = monitor.check_once()
                self.assertFalse(telemetry["fatigue_detected"])
                self.assertIsNone(telemetry.get("proactive_event"))

    def test_face_detector_and_attention_interfaces(self):
        """Verifies FaceDetector and AttentionEstimator wrappers."""
        face_dec = FaceDetector(detector=self.detector)
        att_est = AttentionEstimator(detector=self.detector)

        mock_frame = CameraManager.generate_mock_face_frame("excited")
        face_res = face_dec.detect(mock_frame)
        att_res = att_est.estimate(mock_frame)

        self.assertIn("face_detected", face_res)
        self.assertIn("attention_state", att_res)
        self.assertIn("looking_at_camera", att_res)


if __name__ == "__main__":
    unittest.main()
