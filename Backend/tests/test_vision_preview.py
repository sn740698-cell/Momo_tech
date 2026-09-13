"""
Unit tests for ExpressionDetector.annotate_frame and live preview generation.
"""
import unittest
import numpy as np
from vision.expression_detector import ExpressionDetector
from vision.camera import CameraManager


class TestVisionPreview(unittest.TestCase):

    def setUp(self):
        self.detector = ExpressionDetector()

    def test_annotate_frame_shape_and_type(self):
        # Generate synthetic face frame
        frame = CameraManager.generate_mock_face_frame("happy")
        self.assertIsNotNone(frame)
        self.assertEqual(len(frame.shape), 3)

        annotated = self.detector.annotate_frame(frame, work_mins=15.0)
        self.assertIsInstance(annotated, np.ndarray)
        self.assertEqual(annotated.shape, frame.shape)
        self.assertEqual(annotated.dtype, np.uint8)

    def test_annotate_frame_with_fatigue(self):
        frame = CameraManager.generate_mock_face_frame("tired")
        annotated = self.detector.annotate_frame(frame, work_mins=35.0)
        self.assertIsNotNone(annotated)
        self.assertEqual(annotated.shape[0], 480)
        self.assertEqual(annotated.shape[1], 640)

    def test_annotate_empty_frame_handling(self):
        empty = None
        result = self.detector.annotate_frame(empty)
        self.assertIsNotNone(result)
        self.assertEqual(result.shape, (480, 640, 3))


if __name__ == "__main__":
    unittest.main()
