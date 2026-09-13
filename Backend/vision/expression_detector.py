"""
OpenCV Facial Expression, Gaze, Low-Resolution Enhancement, & 18-Sensor Emotion Perception Engine for MOMO.
Equipped with an 18-sensor multi-modal FACS geometric and photometric array:
1. ear_sensor: Eye Aspect Ratio & Palpebral Fissure Openness
2. eyebrow_furrow_sensor: Glabella Corrugator / Vertical Brow Tension
3. mouth_curvature_sensor: Commissure Angle & Elevation vs Depressor Frown
4. cheek_elevation_sensor: Infraorbital Zygomaticus Cheek Fold Contrast
5. jaw_drop_sensor: Lip Separation / Vertical Mouth Opening (Yawn vs Speech)
6. head_pitch_sensor: Downward Head Slump / Nod Angle
7. blink_duration_sensor: Micro-Blink & Prolonged Eye Closure Tracker
8. periorbital_texture_sensor: Eye Bag / Periorbital Strain & Darkness
9. symmetry_sensor: Facial Hemisphere Tension Balance
10. temporal_stability: Exponential Moving Average Multi-Frame Stability
11. clarity_quality_sensor: Normalized Laplacian Spatial Sharpness / Blur Metric
12. illumination_contrast_sensor: Facial RMS Contrast & Low-Light Dynamic Range
13. skin_chroma_vitality_sensor: YCbCr Cr/Cb Vascular Perfusion & Pallor Index
14. micro_motion_energy_sensor: Inter-Frame Temporal Face Velocity & Slump
15. mouth_aspect_energy_sensor: Otsu Adaptive Low-Res Oral Cavity Darkness (Yawn/Speech)
16. eye_glint_salience_sensor: Corneal Specular Reflection Glint Tracker
17. nasolabial_depth_sensor: Bilateral Cheek-Lip Furrow Strain Energy
18. recognition_confidence_sensor: Low-Res Invariant Biometric Identity Match
"""
import os
import cv2
import time
import math
import logging
import numpy as np
from typing import Dict, Any, Optional, Tuple, List

from .face_recognizer import LowResFaceRecognizer

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
YUNET_MODEL_PATH = os.path.join(MODELS_DIR, "face_detection_yunet_2023mar.onnx")
HAAR_FACE_PATH = os.path.join(MODELS_DIR, "haarcascade_frontalface_default.xml")
HAAR_EYE_PATH = os.path.join(MODELS_DIR, "haarcascade_eye.xml")


class ExpressionDetector:
    """
    OpenCV multi-sensor perception engine with low-megapixel enhancement,
    cascaded face detection, and 18 FACS & photometric sensors.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or YUNET_MODEL_PATH
        self.detector: Optional[cv2.FaceDetectorYN] = None
        self._detector_input_size: Tuple[int, int] = (640, 480)
        self._sensitive_input_size: Tuple[int, int] = (640, 480)
        self._init_detector()

        # Sensitive Low-Threshold YuNet detector for dark / low-res / blurry frames
        self.sensitive_detector: Optional[cv2.FaceDetectorYN] = None
        self._init_sensitive_detector()

        # Low-Res Biometric Face Recognizer
        self.recognizer = LowResFaceRecognizer()

        # Sliding window history for emotion smoothing
        self._emotion_history: List[str] = []
        self._last_analysis: Dict[str, Any] = self._default_result()

        # Temporal tracking state
        self._closed_eye_frames: int = 0
        self._ema_sensors: Dict[str, float] = {}
        self._ema_alpha: float = 0.35

        # Temporal dead-reckoning bounding box tracker
        self._last_known_bbox: Optional[List[int]] = None
        self._last_known_landmarks: Optional[Dict[str, Tuple[float, float]]] = None
        self._frames_since_detection: int = 999
        self._prev_face_gray: Optional[np.ndarray] = None

        # In-memory annotation & analysis caching to avoid redundant heavy detector runs
        self._last_analysis_time: float = 0.0
        self._analysis_cache_ttl: float = 0.15  # 150ms TTL for heavy ONNX detector (~6-7 FPS detection cadence)
        self._last_annotated_frame: Optional[np.ndarray] = None
        self._last_annotated_time: float = 0.0
        self._annotated_cache_ttl: float = 0.025  # 25ms TTL (allows up to 40 FPS streaming)

    def _init_detector(self):
        if os.path.exists(self.model_path) and os.path.getsize(self.model_path) > 10000:
            try:
                self.detector = cv2.FaceDetectorYN_create(
                    model=self.model_path,
                    config="",
                    input_size=self._detector_input_size,
                    score_threshold=0.45,  # Relaxed for low-light & low-res
                    nms_threshold=0.3,
                    top_k=5000
                )
                logger.info(f"OpenCV FaceDetectorYN initialized with model: {self.model_path}")
            except Exception as e:
                logger.warning(f"Could not initialize OpenCV FaceDetectorYN: {e}")
                self.detector = None
        else:
            logger.warning(f"YuNet ONNX model not found at {self.model_path}")

    def _init_sensitive_detector(self):
        if os.path.exists(self.model_path) and os.path.getsize(self.model_path) > 10000:
            try:
                self.sensitive_detector = cv2.FaceDetectorYN_create(
                    model=self.model_path,
                    config="",
                    input_size=self._sensitive_input_size,
                    score_threshold=0.20,  # Ultra-sensitive for low-megapixel / low-clarity frames
                    nms_threshold=0.3,
                    top_k=5000
                )
            except Exception as e:
                logger.debug(f"Could not initialize sensitive FaceDetectorYN: {e}")

    def _default_result(self) -> Dict[str, Any]:
        return {
            "face_detected": False,
            "face_count": 0,
            "primary_bbox": None,
            "landmarks": None,
            "emotion": "neutral",
            "emotion_confidence": 0.0,
            "looking_at_camera": False,
            "head_pose": "unknown",
            "eye_openness": 0.0,
            "smile_intensity": 0.0,
            "tired_score": 0.0,
            "sadness_score": 0.0,
            "expression_summary": "No face detected",
            "sensors": {
                "ear_sensor": 0.0,
                "eyebrow_furrow_sensor": 0.0,
                "mouth_curvature_sensor": 0.0,
                "cheek_elevation_sensor": 0.0,
                "jaw_drop_sensor": 0.0,
                "head_pitch_sensor": 0.0,
                "blink_duration_sensor": 0.0,
                "periorbital_texture_sensor": 0.0,
                "symmetry_sensor": 1.0,
                "temporal_stability": 1.0,
                "clarity_quality_sensor": 0.0,
                "illumination_contrast_sensor": 0.0,
                "skin_chroma_vitality_sensor": 0.5,
                "micro_motion_energy_sensor": 0.0,
                "mouth_aspect_energy_sensor": 0.0,
                "eye_glint_salience_sensor": 0.0,
                "nasolabial_depth_sensor": 0.0,
                "recognition_confidence_sensor": 0.0,
                "sadness_score": 0.0,
                "tired_score": 0.0,
                "happiness_score": 0.0,
                "stress_score": 0.0,
                "focus_score": 0.0,
            },
            "recognition": {
                "recognized": False,
                "user_name": "Unknown",
                "confidence": 0.0,
                "status": "No face detected",
            },
            "enhancement": {
                "clarity_boosted": False,
                "upscaled": False,
                "laplacian_var": 0.0,
            },
            "timestamp": time.time(),
        }

    # =========================================================================
    # LOW-MEGAPIXEL PREPROCESSING & ENHANCEMENT
    # =========================================================================

    def enhance_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Enhances low-clarity, blurry, low-light, or low-megapixel frames using:
        1. Bi-cubic upscaling if image is small (<480 width or <360 height)
        2. Dynamic range expansion / adaptive gamma correction for low-light frames
        3. Contrast-Limited Adaptive Histogram Equalization (CLAHE) on L-channel
        4. Edge-preserving noise suppression & unsharp masking for soft/blurry camera feeds
        """
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return frame, {"clarity_boosted": False, "upscaled": False, "laplacian_var": 0.0}

        h, w = frame.shape[:2]
        upscaled = False
        scale_factor = 1.0
        work_frame = frame

        # 1. Upscale if camera has low resolution (< 480w or < 360h)
        if w < 480 or h < 360:
            scale_factor = max(480.0 / w, 360.0 / h)
            new_w = int(w * scale_factor)
            new_h = int(h * scale_factor)
            work_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            upscaled = True

        # 2. Check blur level via Laplacian variance
        gray = cv2.cvtColor(work_frame, cv2.COLOR_BGR2GRAY)
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        # 3. Dynamic Range Expansion & CLAHE in LAB space
        lab = cv2.cvtColor(work_frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        mean_l = float(np.mean(l))

        # Adaptive gamma boost for dark / poorly lit camera feeds
        if mean_l < 95.0:
            gamma = 1.0 + min(1.2, (95.0 - mean_l) / 60.0)
            inv_gamma = 1.0 / gamma
            lut = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype('uint8')
            l = cv2.LUT(l, lut)

        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        enhanced = cv2.cvtColor(cv2.merge((cl, a, b)), cv2.COLOR_LAB2BGR)

        # 4. Noise suppression & Unsharp Masking for soft or out-of-focus camera sensors
        clarity_boosted = False
        if lap_var < 150.0:
            gaussian = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=1.8)
            enhanced = cv2.addWeighted(enhanced, 1.25, gaussian, -0.25, 0)
            enhanced = cv2.bilateralFilter(enhanced, d=5, sigmaColor=35, sigmaSpace=35)
            clarity_boosted = True

        return enhanced, {
            "clarity_boosted": clarity_boosted,
            "upscaled": upscaled,
            "scale_factor": scale_factor,
            "laplacian_var": round(lap_var, 1),
            "mean_luminance": round(mean_l, 1),
        }

    # =========================================================================
    # MULTI-TIER CASCADED DETECTION
    # =========================================================================

    def _detect_faces_cascaded(
        self,
        frame: np.ndarray,
        enhanced_frame: np.ndarray,
        scale_factor: float
    ) -> Tuple[Optional[List[Any]], Optional[str]]:
        """
        Executes cascaded face detection across 4 tiers:
        Tier 1: YuNet DNN on original frame
        Tier 2: YuNet DNN on enhanced frame with relaxed threshold
        Tier 3: OpenCV Haar Cascade on enhanced grayscale
        Tier 4: Temporal dead-reckoning tracking
        """
        faces = None
        method = None
        h, w = frame.shape[:2]

        # Tier 1: YuNet on native frame
        if self.detector is not None:
            if (w, h) != self._detector_input_size:
                self._detector_input_size = (w, h)
                self.detector.setInputSize((w, h))
            try:
                _, detected = self.detector.detect(frame)
                if detected is not None and len(detected) > 0:
                    return detected, "yunet_native"
            except Exception as e:
                logger.debug(f"YuNet native detection error: {e}")

        # Tier 2: YuNet on enhanced frame
        if self.detector is not None and enhanced_frame is not None:
            eh, ew = enhanced_frame.shape[:2]
            if (ew, eh) != self._detector_input_size:
                self._detector_input_size = (ew, eh)
                self.detector.setInputSize((ew, eh))
            try:
                _, detected = self.detector.detect(enhanced_frame)
                if detected is not None and len(detected) > 0:
                    # Rescale coordinates back to original frame space if upscaled
                    if scale_factor != 1.0:
                        rescaled = []
                        inv = 1.0 / scale_factor
                        for f in detected:
                            rf = f.copy()
                            rf[0] *= inv
                            rf[1] *= inv
                            rf[2] *= inv
                            rf[3] *= inv
                            for p in range(4, 14, 2):
                                rf[p] *= inv
                                rf[p + 1] *= inv
                            rescaled.append(rf)
                        return np.array(rescaled), "yunet_enhanced"
                    return detected, "yunet_enhanced"
            except Exception as e:
                logger.debug(f"YuNet enhanced detection error: {e}")

        # Tier 3: Sensitive YuNet on enhanced frame (down to 0.20 confidence)
        if self.sensitive_detector is not None and enhanced_frame is not None:
            eh, ew = enhanced_frame.shape[:2]
            if (ew, eh) != self._sensitive_input_size:
                self._sensitive_input_size = (ew, eh)
                self.sensitive_detector.setInputSize((ew, eh))
            try:
                _, detected = self.sensitive_detector.detect(enhanced_frame)
                if detected is not None and len(detected) > 0:
                    if scale_factor != 1.0:
                        rescaled = []
                        inv = 1.0 / scale_factor
                        for f in detected:
                            rf = f.copy()
                            rf[0] *= inv
                            rf[1] *= inv
                            rf[2] *= inv
                            rf[3] *= inv
                            for p in range(4, 14, 2):
                                rf[p] *= inv
                                rf[p + 1] *= inv
                            rescaled.append(rf)
                        return np.array(rescaled), "yunet_sensitive"
                    return detected, "yunet_sensitive"
            except Exception as e:
                logger.debug(f"YuNet sensitive detection error: {e}")

        # Tier 4: Physiological Chrominance Skin-Color Ellipse Detector (for extreme low clarity, noise, or blur)
        try:
            for target_img, s_factor in [(frame, 1.0), (enhanced_frame, scale_factor)]:
                if target_img is None:
                    continue
                th, tw = target_img.shape[:2]
                total_area = float(tw * th)
                ycrcb = cv2.cvtColor(target_img, cv2.COLOR_BGR2YCrCb)
                y, cr, cb = cv2.split(ycrcb)
                # Biometric skin chrominance: Cr > Cb distinguishes skin from neutral grays/shadows
                skin_mask = (cr >= 132) & (cr <= 182) & (cb >= 75) & (cb <= 130) & (cr > cb)
                mask = (skin_mask.astype(np.uint8) * 255)
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                valid_contours = []
                for c in contours:
                    area = cv2.contourArea(c)
                    frac = area / max(1.0, total_area)
                    if 0.02 <= frac <= 0.85:  # Face occupies 2% to 85% of frame
                        cx, cy, cw, ch = cv2.boundingRect(c)
                        aspect = ch / max(1.0, float(cw))
                        if 0.6 <= aspect <= 2.5:  # Realistic human head/face aspect ratio
                            valid_contours.append((area, cx, cy, cw, ch))
                if valid_contours:
                    valid_contours.sort(key=lambda x: x[0], reverse=True)
                    _, cx, cy, cw, ch = valid_contours[0]
                    inv = 1.0 / s_factor if s_factor != 1.0 else 1.0
                    rx, ry, rw, rh = cx * inv, cy * inv, cw * inv, ch * inv
                    synthetic = np.array([[
                        rx, ry, rw, rh,
                        rx + (rw * 0.32), ry + (rh * 0.38),
                        rx + (rw * 0.68), ry + (rh * 0.38),
                        rx + (rw * 0.50), ry + (rh * 0.58),
                        rx + (rw * 0.34), ry + (rh * 0.78),
                        rx + (rw * 0.66), ry + (rh * 0.78),
                        0.65
                    ]], dtype=np.float32)
                    return synthetic, "chroma_skin_ellipse"
        except Exception as e:
            logger.debug(f"Skin chroma detector error: {e}")

        # Tier 5: Temporal Dead-Reckoning (carry forward for up to 3 frames of motion blur/noise)
        if self._last_known_bbox is not None and self._frames_since_detection <= 3:
            bx, by, bw, bh = self._last_known_bbox
            lm = self._last_known_landmarks or {}
            r_eye = lm.get("right_eye", (bx + bw * 0.32, by + bh * 0.38))
            l_eye = lm.get("left_eye", (bx + bw * 0.68, by + bh * 0.38))
            nose = lm.get("nose", (bx + bw * 0.50, by + bh * 0.58))
            r_mouth = lm.get("right_mouth", (bx + bw * 0.34, by + bh * 0.78))
            l_mouth = lm.get("left_mouth", (bx + bw * 0.66, by + bh * 0.78))

            decay = 0.85 ** self._frames_since_detection
            synthetic = np.array([[
                bx, by, bw, bh,
                r_eye[0], r_eye[1],
                l_eye[0], l_eye[1],
                nose[0], nose[1],
                r_mouth[0], r_mouth[1],
                l_mouth[0], l_mouth[1],
                0.70 * decay
            ]], dtype=np.float32)
            return synthetic, "temporal_tracking"

        return None, None

    # =========================================================================
    # CORE FRAME ANALYSIS & 18 SENSORS
    # =========================================================================

    def analyze_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Analyzes a single frame for faces, landmarks, 18 facial & photometric sensors,
        biometric user recognition, composite emotions, and gaze orientation.
        """
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return self._default_result()

        h, w = frame.shape[:2]

        # 1. Low-Clarity Preprocessing & Enhancement
        enhanced_frame, enh_meta = self.enhance_frame(frame)
        scale_factor = enh_meta.get("scale_factor", 1.0)

        # 2. Cascaded Face Detection
        faces, detect_method = self._detect_faces_cascaded(frame, enhanced_frame, scale_factor)

        if faces is None or len(faces) == 0:
            self._frames_since_detection += 1
            res = self._default_result()
            res["enhancement"] = enh_meta
            self._last_analysis = res
            return res

        self._frames_since_detection = 0

        # Sort by bounding box area (primary face is largest)
        faces = sorted(faces, key=lambda f: float(f[2]) * float(f[3]), reverse=True)
        primary = faces[0]

        fx, fy, fw, fh = float(primary[0]), float(primary[1]), float(primary[2]), float(primary[3])
        r_eye = (float(primary[4]), float(primary[5]))
        l_eye = (float(primary[6]), float(primary[7]))
        nose = (float(primary[8]), float(primary[9]))
        r_mouth = (float(primary[10]), float(primary[11]))
        l_mouth = (float(primary[12]), float(primary[13]))
        confidence = float(primary[14])

        # Cache for temporal dead reckoning
        self._last_known_bbox = [int(fx), int(fy), int(fw), int(fh)]
        self._last_known_landmarks = {
            "right_eye": r_eye,
            "left_eye": l_eye,
            "nose": nose,
            "right_mouth": r_mouth,
            "left_mouth": l_mouth,
        }

        # Gaze & Head Pose
        eye_midpoint_x = (r_eye[0] + l_eye[0]) / 2.0
        eye_dist = max(1.0, math.dist(r_eye, l_eye))
        nose_offset = (nose[0] - eye_midpoint_x) / eye_dist

        frame_midpoint_x = w / 2.0
        face_center_x = fx + (fw / 2.0)
        frame_offset = abs(face_center_x - frame_midpoint_x) / max(1.0, frame_midpoint_x)
        looking_at_camera = abs(nose_offset) < 0.28 and frame_offset < 0.48

        head_pose = "center"
        if nose_offset < -0.28:
            head_pose = "right"
        elif nose_offset > 0.28:
            head_pose = "left"

        # Safe facial crop for texture and photometric sensors
        bx, by, bw, bh = int(max(0, fx)), int(max(0, fy)), int(min(w - max(0, fx), fw)), int(min(h - max(0, fy), fh))
        face_roi = frame[by:by + bh, bx:bx + bw] if bw > 4 and bh > 4 else frame

        # =====================================================================
        # CALCULATE 18 SENSORS
        # =====================================================================
        # Original 10 Sensors:
        raw_ear = self._estimate_ear(frame, r_eye, l_eye, eye_dist)
        raw_brow_furrow = self._estimate_brow_furrow(frame, r_eye, l_eye, nose)
        raw_mouth_curvature, raw_mouth_ratio = self._estimate_mouth_curvature(
            frame, r_mouth, l_mouth, nose, r_eye, l_eye, eye_dist, fh
        )
        raw_cheek_elevation = self._estimate_cheek_elevation(frame, r_eye, l_eye, r_mouth, l_mouth, eye_dist)
        raw_jaw_drop = self._estimate_jaw_drop(frame, r_mouth, l_mouth, nose, eye_dist)
        raw_head_pitch = self._estimate_head_pitch(fy, fh, r_eye, l_eye, nose)
        raw_blink_duration = self._track_blink_duration(raw_ear)
        raw_periorbital = self._estimate_periorbital_texture(frame, r_eye, l_eye, eye_dist)
        raw_symmetry = self._estimate_facial_symmetry(r_eye, l_eye, r_mouth, l_mouth)

        # 8 New Robust Low-Clarity Sensors:
        raw_clarity = self._estimate_clarity_quality(face_roi)
        raw_contrast = self._estimate_illumination_contrast(face_roi)
        raw_chroma_vitality = self._estimate_skin_chroma_vitality(frame, r_eye, l_eye, nose, eye_dist)
        raw_micro_motion = self._estimate_micro_motion_energy(face_roi)
        raw_mouth_energy = self._estimate_mouth_aspect_energy(face_roi)
        raw_eye_glint = self._estimate_eye_glint_salience(frame, r_eye, l_eye, eye_dist)
        raw_nasolabial = self._estimate_nasolabial_depth(frame, nose, r_mouth, l_mouth, eye_dist)

        # Biometric Face Recognition & Verification
        landmarks_dict = {
            "right_eye": r_eye,
            "left_eye": l_eye,
            "nose": nose,
            "right_mouth": r_mouth,
            "left_mouth": l_mouth,
        }
        rec_result = self.recognizer.recognize_or_enroll(
            frame=frame,
            primary_bbox=[bx, by, bw, bh],
            landmarks=landmarks_dict,
            raw_face_yunet=primary if detect_method and "yunet" in detect_method else None
        )
        raw_recognition_conf = rec_result.get("confidence", 0.0)

        # Apply Temporal EMA smoothing to all continuous sensors
        smoothed = self._apply_ema_smoothing({
            "ear_sensor": raw_ear,
            "eyebrow_furrow_sensor": raw_brow_furrow,
            "mouth_curvature_sensor": raw_mouth_curvature,
            "cheek_elevation_sensor": raw_cheek_elevation,
            "jaw_drop_sensor": raw_jaw_drop,
            "head_pitch_sensor": raw_head_pitch,
            "blink_duration_sensor": raw_blink_duration,
            "periorbital_texture_sensor": raw_periorbital,
            "symmetry_sensor": raw_symmetry,
            "clarity_quality_sensor": raw_clarity,
            "illumination_contrast_sensor": raw_contrast,
            "skin_chroma_vitality_sensor": raw_chroma_vitality,
            "micro_motion_energy_sensor": raw_micro_motion,
            "mouth_aspect_energy_sensor": raw_mouth_energy,
            "eye_glint_salience_sensor": raw_eye_glint,
            "nasolabial_depth_sensor": raw_nasolabial,
            "recognition_confidence_sensor": raw_recognition_conf,
        })

        ear = smoothed["ear_sensor"]
        brow_furrow = smoothed["eyebrow_furrow_sensor"]
        mouth_curv = smoothed["mouth_curvature_sensor"]
        cheek = smoothed["cheek_elevation_sensor"]
        jaw_drop = smoothed["jaw_drop_sensor"]
        head_pitch = smoothed["head_pitch_sensor"]
        blink_dur = smoothed["blink_duration_sensor"]
        periorbital = smoothed["periorbital_texture_sensor"]
        symm = smoothed["symmetry_sensor"]
        clarity_val = smoothed["clarity_quality_sensor"]
        chroma_vitality = smoothed["skin_chroma_vitality_sensor"]
        mouth_dark_energy = smoothed["mouth_aspect_energy_sensor"]
        eye_glint = smoothed["eye_glint_salience_sensor"]
        nasolabial = smoothed["nasolabial_depth_sensor"]
        rec_conf = smoothed["recognition_confidence_sensor"]

        # =====================================================================
        # COMPOSITE EMOTIONS (ENRICHED WITH LOW-RES SENSORS)
        # =====================================================================
        # Sadness: combines mouth downturn, brow tension, slump, nasolabial depth, and pallor
        downturned_intensity = max(0.0, -mouth_curv)
        skin_pallor = max(0.0, 0.50 - chroma_vitality) * 2.0  # Loss of skin warmth
        base_sadness = (
            0.35 * downturned_intensity +
            0.20 * brow_furrow +
            0.15 * max(0.0, -head_pitch) +
            0.10 * nasolabial +
            0.10 * skin_pallor +
            0.10 * max(0.0, 1.0 - cheek)
        )
        sadness_score = base_sadness * (1.0 - max(0.0, mouth_curv))
        sadness_score = max(0.0, min(1.0, sadness_score))

        # Tiredness: eye fatigue, blink duration, yawn (jaw drop + oral cavity darkness), slump, and glint loss
        eye_fatigue = max(0.0, (0.50 - ear) / 0.50) if ear < 0.50 else 0.0
        combined_yawn = max(jaw_drop, mouth_dark_energy)
        glint_loss = max(0.0, 1.0 - eye_glint) if eye_glint < 0.40 else 0.0
        tired_score = (
            0.25 * eye_fatigue +
            0.20 * blink_dur +
            0.20 * combined_yawn +
            0.15 * glint_loss +
            0.10 * max(0.0, -head_pitch) +
            0.10 * periorbital
        )
        tired_score = max(0.0, min(1.0, tired_score))

        # Happiness: requires genuine positive smile curvature
        smile_intensity = max(0.0, mouth_curv) if mouth_curv > 0.08 else 0.0
        if smile_intensity > 0.0:
            base_happiness = (
                0.55 * smile_intensity +
                0.20 * cheek +
                0.15 * eye_glint +
                0.10 * chroma_vitality
            )
            happiness_score = max(0.0, min(1.0, base_happiness * (1.0 - max(0.0, -mouth_curv))))
        else:
            happiness_score = 0.0

        # Stress: brow furrow, hemisphere asymmetry, nasolabial strain
        stress_score = (
            0.40 * brow_furrow +
            0.30 * max(0.0, 1.0 - symm) +
            0.20 * nasolabial +
            0.10 * max(0.0, 0.4 - jaw_drop)
        )
        stress_score = max(0.0, min(1.0, stress_score))

        # Focus: gaze alignment, glint stability, low fidgeting
        focus_score = (
            0.35 * (1.0 if looking_at_camera else 0.7) +
            0.25 * eye_glint +
            0.20 * min(1.0, ear / 0.65) +
            0.10 * (1.0 - abs(mouth_curv)) +
            0.10 * (1.0 - brow_furrow)
        )
        focus_score = max(0.0, min(1.0, focus_score))

        # Emotional State Classification (Baseline is NEUTRAL for attentive/calm users)
        detected_emotion = "neutral"
        emotion_conf = confidence

        # Strict Sad + Tired takes precedence
        if sadness_score >= 0.55 and tired_score >= 0.55:
            detected_emotion = "sad"
            emotion_conf = (sadness_score + tired_score) / 2.0
        elif happiness_score >= 0.50 and smile_intensity >= 0.20:
            if happiness_score > 0.75 and ear > 0.55:
                detected_emotion = "excited"
            else:
                detected_emotion = "happy"
            emotion_conf = happiness_score
        elif tired_score >= 0.52:
            detected_emotion = "tired"
            emotion_conf = tired_score
        elif sadness_score >= 0.52:
            detected_emotion = "sad"
            emotion_conf = sadness_score
        elif stress_score >= 0.72 and focus_score < 0.65 and mouth_curv < -0.30:
            detected_emotion = "stressed"
            emotion_conf = stress_score
        else:
            detected_emotion = "neutral"
            emotion_conf = max(0.85, focus_score)

        self._emotion_history.append(detected_emotion)
        if len(self._emotion_history) > 7:
            self._emotion_history.pop(0)

        smoothed_emotion = max(set(self._emotion_history), key=self._emotion_history.count)

        summary = (
            f"Face Detected ({detect_method}): {smoothed_emotion.upper()} ({int(emotion_conf * 100)}%) | "
            f"Sad: {int(sadness_score * 100)}% | Tired: {int(tired_score * 100)}% | "
            f"User: {rec_result.get('user_name', 'User')} ({int(rec_conf * 100)}%)"
        )

        all_sensors = {
            "ear_sensor": round(ear, 3),
            "eyebrow_furrow_sensor": round(brow_furrow, 3),
            "mouth_curvature_sensor": round(mouth_curv, 3),
            "cheek_elevation_sensor": round(cheek, 3),
            "jaw_drop_sensor": round(jaw_drop, 3),
            "head_pitch_sensor": round(head_pitch, 3),
            "blink_duration_sensor": round(blink_dur, 3),
            "periorbital_texture_sensor": round(periorbital, 3),
            "symmetry_sensor": round(symm, 3),
            "temporal_stability": round(1.0 - abs(smoothed["mouth_curvature_sensor"] - raw_mouth_curvature), 3),
            "clarity_quality_sensor": round(clarity_val, 3),
            "illumination_contrast_sensor": round(smoothed["illumination_contrast_sensor"], 3),
            "skin_chroma_vitality_sensor": round(chroma_vitality, 3),
            "micro_motion_energy_sensor": round(smoothed["micro_motion_energy_sensor"], 3),
            "mouth_aspect_energy_sensor": round(mouth_dark_energy, 3),
            "eye_glint_salience_sensor": round(eye_glint, 3),
            "nasolabial_depth_sensor": round(nasolabial, 3),
            "recognition_confidence_sensor": round(rec_conf, 3),
            "sadness_score": round(sadness_score, 3),
            "tired_score": round(tired_score, 3),
            "happiness_score": round(happiness_score, 3),
            "stress_score": round(stress_score, 3),
            "focus_score": round(focus_score, 3),
        }

        result = {
            "face_detected": True,
            "face_count": len(faces),
            "detection_method": detect_method,
            "primary_bbox": [int(fx), int(fy), int(fw), int(fh)],
            "landmarks": {
                "right_eye": [round(r_eye[0], 1), round(r_eye[1], 1)],
                "left_eye": [round(l_eye[0], 1), round(l_eye[1], 1)],
                "nose": [round(nose[0], 1), round(nose[1], 1)],
                "right_mouth": [round(r_mouth[0], 1), round(r_mouth[1], 1)],
                "left_mouth": [round(l_mouth[0], 1), round(l_mouth[1], 1)],
            },
            "emotion": smoothed_emotion,
            "emotion_confidence": round(emotion_conf, 2),
            "looking_at_camera": looking_at_camera,
            "head_pose": head_pose,
            "eye_openness": round(ear, 2),
            "smile_intensity": round(happiness_score, 2),
            "brow_tension": round(brow_furrow * 40.0, 2),
            "tired_score": round(tired_score, 2),
            "sadness_score": round(sadness_score, 2),
            "sensors": all_sensors,
            "recognition": rec_result,
            "enhancement": enh_meta,
            "expression_summary": summary,
            "timestamp": time.time(),
        }

        self._last_analysis = result
        return result

    # =========================================================================
    # SENSOR CALCULATION HELPERS
    # =========================================================================

    def _estimate_ear(
        self,
        frame: np.ndarray,
        r_eye: Tuple[float, float],
        l_eye: Tuple[float, float],
        eye_dist: float
    ) -> float:
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        patch_r = int(eye_dist * 0.16)
        if patch_r < 3:
            return 0.75

        variances = []
        for eye_pt in [r_eye, l_eye]:
            ex, ey = int(eye_pt[0]), int(eye_pt[1])
            y1, y2 = max(0, ey - patch_r), min(h, ey + patch_r)
            x1, x2 = max(0, ex - patch_r), min(w, ex + patch_r)
            if y2 > y1 and x2 > x1:
                patch = gray[y1:y2, x1:x2]
                var = float(np.var(patch))
                variances.append(var)

        if not variances:
            return 0.75

        avg_var = sum(variances) / len(variances)
        openness = max(0.10, min(1.0, (avg_var - 35.0) / 170.0))
        return openness

    def _estimate_brow_furrow(
        self,
        frame: np.ndarray,
        r_eye: Tuple[float, float],
        l_eye: Tuple[float, float],
        nose: Tuple[float, float]
    ) -> float:
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

        min_x = int(min(r_eye[0], l_eye[0]))
        max_x = int(max(r_eye[0], l_eye[0]))
        min_y = int(min(r_eye[1], l_eye[1]) - (nose[1] - min(r_eye[1], l_eye[1])) * 0.7)
        max_y = int(min(r_eye[1], l_eye[1]))

        y1, y2 = max(0, min_y), min(h, max_y)
        x1, x2 = max(0, min_x), min(w, max_x)

        if y2 > y1 and x2 > x1:
            roi = gray[y1:y2, x1:x2]
            sobel = cv2.Sobel(roi, cv2.CV_64F, 0, 1, ksize=3)
            std_grad = float(np.std(sobel))
            return max(0.0, min(1.0, (std_grad - 11.0) / 20.0))
        return 0.15

    def _estimate_mouth_curvature(
        self,
        frame: np.ndarray,
        r_mouth: Tuple[float, float],
        l_mouth: Tuple[float, float],
        nose: Tuple[float, float],
        r_eye: Optional[Tuple[float, float]] = None,
        l_eye: Optional[Tuple[float, float]] = None,
        eye_dist: float = 50.0,
        fh: float = 120.0
    ) -> Tuple[float, float]:
        mouth_w = math.dist(r_mouth, l_mouth)
        mouth_ratio = mouth_w / max(1.0, eye_dist)

        # 1. Coordinate frame orientation aligned with eye baseline (roll-invariant)
        if r_eye is not None and l_eye is not None and eye_dist > 1.0:
            u_x = np.array([(l_eye[0] - r_eye[0]) / eye_dist, (l_eye[1] - r_eye[1]) / eye_dist])
            u_y = np.array([-u_x[1], u_x[0]])  # Downward face normal vector
        else:
            u_y = np.array([0.0, 1.0])

        # 2. Sample lip crease profile along the line segment from right to left mouth corners
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        h, w = gray.shape[:2]
        pts_down = []
        for alpha in np.linspace(0.12, 0.88, 7):
            cx = (1.0 - alpha) * r_mouth[0] + alpha * l_mouth[0]
            cy = (1.0 - alpha) * r_mouth[1] + alpha * l_mouth[1]
            ix = int(round(min(w - 1, max(0, cx))))
            iy = int(round(min(h - 1, max(0, cy))))
            # Search vertical window around crease for darkest pixel (lip slit)
            y_start = max(0, iy - 8)
            y_end = min(h, iy + 9)
            col = gray[y_start:y_end, ix]
            if len(col) > 0:
                darkest_offset = int(np.argmin(col)) - (iy - y_start)
            else:
                darkest_offset = 0
            real_pt = np.array([cx, cy + darkest_offset])
            pts_down.append(float(np.dot(real_pt - np.array(nose), u_y)))

        corner_down = (pts_down[0] + pts_down[-1]) / 2.0
        center_down = pts_down[3]
        # In face coords, down vector is positive.
        # When smiling, the mouth corners elevate towards the eyes, making corner_down < center_down,
        # so (center_down - corner_down) is POSITIVE.
        smile_metric = (center_down - corner_down) / max(1.0, eye_dist)

        # Calibrate curvature:
        # Genuine smile: corners are elevated by > 3.5% of eye distance
        # Neutral / calm: smile_metric between -0.045 and +0.035
        # Frown / sad: corners droop downwards, smile_metric < -0.045
        if smile_metric > 0.035:
            curvature = min(1.0, (smile_metric - 0.03) / 0.10)
        elif smile_metric < -0.045:
            curvature = -min(1.0, (-0.04 - smile_metric) / 0.10)
        else:
            curvature = smile_metric / 0.15  # Near-zero neutral

        return max(-1.0, min(1.0, float(curvature))), mouth_ratio

    def _estimate_cheek_elevation(
        self,
        frame: np.ndarray,
        r_eye: Tuple[float, float],
        l_eye: Tuple[float, float],
        r_mouth: Tuple[float, float],
        l_mouth: Tuple[float, float],
        eye_dist: float
    ) -> float:
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

        cheek_r = int(eye_dist * 0.14)
        if cheek_r < 2:
            return 0.30

        vars_list = []
        for eye_pt, mouth_pt in [(r_eye, r_mouth), (l_eye, l_mouth)]:
            cx = int((eye_pt[0] * 2.0 + mouth_pt[0]) / 3.0)
            cy = int((eye_pt[1] * 2.0 + mouth_pt[1]) / 3.0)
            y1, y2 = max(0, cy - cheek_r), min(h, cy + cheek_r)
            x1, x2 = max(0, cx - cheek_r), min(w, cx + cheek_r)
            if y2 > y1 and x2 > x1:
                patch = gray[y1:y2, x1:x2]
                vars_list.append(float(np.std(patch)))

        if not vars_list:
            return 0.30

        avg_std = sum(vars_list) / len(vars_list)
        return max(0.0, min(1.0, (avg_std - 8.0) / 16.0))

    def _estimate_jaw_drop(
        self,
        frame: np.ndarray,
        r_mouth: Tuple[float, float],
        l_mouth: Tuple[float, float],
        nose: Tuple[float, float],
        eye_dist: float
    ) -> float:
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

        mouth_cx = int((r_mouth[0] + l_mouth[0]) / 2.0)
        mouth_cy = int((r_mouth[1] + l_mouth[1]) / 2.0)
        box_w = int(abs(l_mouth[0] - r_mouth[0]) * 0.4)
        box_h = int(eye_dist * 0.25)

        y1, y2 = max(0, mouth_cy - box_h), min(h, mouth_cy + box_h)
        x1, x2 = max(0, mouth_cx - box_w), min(w, mouth_cx + box_w)

        if y2 > y1 and x2 > x1:
            roi = gray[y1:y2, x1:x2]
            mean_lum = float(np.mean(roi))
            if mean_lum < 75.0:
                yawn_score = min(1.0, (85.0 - mean_lum) / 45.0)
                return yawn_score
        return 0.0

    def _estimate_head_pitch(
        self,
        fy: float,
        fh: float,
        r_eye: Tuple[float, float],
        l_eye: Tuple[float, float],
        nose: Tuple[float, float]
    ) -> float:
        eye_y = (r_eye[1] + l_eye[1]) / 2.0
        rel_eye_pos = (eye_y - fy) / max(1.0, fh)
        rel_nose_pos = (nose[1] - fy) / max(1.0, fh)

        if rel_eye_pos > 0.45 or rel_nose_pos > 0.65:
            slump = -min(1.0, (rel_eye_pos - 0.40) / 0.12)
            return slump
        return max(-1.0, min(1.0, (0.42 - rel_eye_pos) / 0.10))

    def _track_blink_duration(self, ear: float) -> float:
        if ear < 0.32:
            self._closed_eye_frames += 1
        else:
            self._closed_eye_frames = max(0, self._closed_eye_frames - 1)

        return min(1.0, self._closed_eye_frames / 3.0)

    def _estimate_periorbital_texture(
        self,
        frame: np.ndarray,
        r_eye: Tuple[float, float],
        l_eye: Tuple[float, float],
        eye_dist: float
    ) -> float:
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

        pw = int(eye_dist * 0.18)
        ph = int(eye_dist * 0.12)
        if pw < 2 or ph < 2:
            return 0.20

        diffs = []
        for eye_pt in [r_eye, l_eye]:
            ex, ey = int(eye_pt[0]), int(eye_pt[1])
            uy1, uy2 = min(h - 1, ey + int(ph * 0.5)), min(h, ey + ph * 2)
            ux1, ux2 = max(0, ex - pw), min(w, ex + pw)
            cy1, cy2 = min(h - 1, ey + ph * 3), min(h, ey + ph * 5)
            cx1, cx2 = ux1, ux2

            if uy2 > uy1 and ux2 > ux1 and cy2 > cy1 and cx2 > cx1:
                u_mean = float(np.mean(gray[uy1:uy2, ux1:ux2]))
                c_mean = float(np.mean(gray[cy1:cy2, cx1:cx2]))
                if c_mean > u_mean:
                    diffs.append((c_mean - u_mean) / max(1.0, c_mean))

        if not diffs:
            return 0.15
        avg_diff = sum(diffs) / len(diffs)
        return max(0.0, min(1.0, avg_diff * 4.0))

    def _estimate_facial_symmetry(
        self,
        r_eye: Tuple[float, float],
        l_eye: Tuple[float, float],
        r_mouth: Tuple[float, float],
        l_mouth: Tuple[float, float]
    ) -> float:
        eye_slope = abs(l_eye[1] - r_eye[1]) / max(1.0, abs(l_eye[0] - r_eye[0]))
        mouth_slope = abs(l_mouth[1] - r_mouth[1]) / max(1.0, abs(l_mouth[0] - r_mouth[0]))
        delta = abs(eye_slope - mouth_slope)
        return max(0.0, min(1.0, 1.0 - (delta * 3.0)))

    # =========================================================================
    # 8 NEW LOW-CLARITY / LOW-MEGAPIXEL ROBUST SENSORS
    # =========================================================================

    def _estimate_clarity_quality(self, face_roi: np.ndarray) -> float:
        """Sensor 11: Measures spatial sharpness and camera focus."""
        if face_roi is None or face_roi.size == 0:
            return 0.5
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        # Map 30 (very blurry) to 250 (crisp) -> 0.0 to 1.0
        return max(0.0, min(1.0, (lap_var - 30.0) / 220.0))

    def _estimate_illumination_contrast(self, face_roi: np.ndarray) -> float:
        """Sensor 12: Measures RMS contrast and dynamic range."""
        if face_roi is None or face_roi.size == 0:
            return 0.5
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
        std_val = float(np.std(gray))
        # Normal facial RMS contrast ranges from 20 (washed out / dark) to 60 (high contrast)
        return max(0.0, min(1.0, (std_val - 15.0) / 45.0))

    def _estimate_skin_chroma_vitality(
        self,
        frame: np.ndarray,
        r_eye: Tuple[float, float],
        l_eye: Tuple[float, float],
        nose: Tuple[float, float],
        eye_dist: float
    ) -> float:
        """Sensor 13: YCbCr Cr/Cb vascular perfusion & skin pallor."""
        if frame is None or len(frame.shape) != 3:
            return 0.5
        h, w = frame.shape[:2]
        # Sample forehead patch (above eye midpoint)
        fx = int((r_eye[0] + l_eye[0]) / 2.0)
        fy = int(min(r_eye[1], l_eye[1]) - eye_dist * 0.25)
        pr = max(3, int(eye_dist * 0.15))

        y1, y2 = max(0, fy - pr), min(h, fy + pr)
        x1, x2 = max(0, fx - pr), min(w, fx + pr)

        if y2 > y1 and x2 > x1:
            patch = frame[y1:y2, x1:x2]
            ycbcr = cv2.cvtColor(patch, cv2.COLOR_BGR2YCrCb)
            cr_mean = float(np.mean(ycbcr[:, :, 1]))
            cb_mean = float(np.mean(ycbcr[:, :, 2]))
            # Healthy human skin has Cr > Cb (ratio 1.1 to 1.45); pallor/fatigue drops ratio
            ratio = cr_mean / max(1.0, cb_mean)
            return max(0.0, min(1.0, (ratio - 1.0) / 0.40))
        return 0.5

    def _estimate_micro_motion_energy(self, face_roi: np.ndarray) -> float:
        """Sensor 14: Inter-frame temporal velocity & micro-nodding."""
        if face_roi is None or face_roi.size == 0:
            return 0.0
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
        # Standardize to 60x60
        resized = cv2.resize(gray, (60, 60), interpolation=cv2.INTER_AREA)

        motion = 0.0
        if self._prev_face_gray is not None and self._prev_face_gray.shape == resized.shape:
            diff = cv2.absdiff(resized, self._prev_face_gray)
            mean_diff = float(np.mean(diff))
            # Normal micro-head motion is between 2.0 and 18.0
            motion = max(0.0, min(1.0, (mean_diff - 1.5) / 15.0))

        self._prev_face_gray = resized
        return motion

    def _estimate_mouth_aspect_energy(self, face_roi: np.ndarray) -> float:
        """Sensor 15: Otsu adaptive oral cavity darkness for yawn/speech detection in low res."""
        if face_roi is None or face_roi.size == 0:
            return 0.0
        h, w = face_roi.shape[:2]
        # Lower third of face contains mouth
        lower_roi = face_roi[int(h * 0.65):h, int(w * 0.20):int(w * 0.80)]
        if lower_roi.size < 16:
            return 0.0
        gray = cv2.cvtColor(lower_roi, cv2.COLOR_BGR2GRAY) if len(lower_roi.shape) == 3 else lower_roi
        # In a yawn or open mouth, a dark cavity forms with values < 50
        dark_pixels = np.sum(gray < 55)
        total_pixels = max(1, gray.size)
        dark_ratio = float(dark_pixels) / total_pixels
        # Yawning typically occupies >15% dark cavity in mouth region
        return max(0.0, min(1.0, dark_ratio / 0.25))

    def _estimate_eye_glint_salience(
        self,
        frame: np.ndarray,
        r_eye: Tuple[float, float],
        l_eye: Tuple[float, float],
        eye_dist: float
    ) -> float:
        """Sensor 16: Corneal specular glint reflection tracker."""
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        pr = max(3, int(eye_dist * 0.14))

        glint_scores = []
        for eye_pt in [r_eye, l_eye]:
            ex, ey = int(eye_pt[0]), int(eye_pt[1])
            y1, y2 = max(0, ey - pr), min(h, ey + pr)
            x1, x2 = max(0, ex - pr), min(w, ex + pr)
            if y2 > y1 and x2 > x1:
                patch = gray[y1:y2, x1:x2]
                max_val = float(np.max(patch))
                mean_val = float(np.mean(patch))
                # Glint creates a sharp specular spike where max >> mean
                spike = (max_val - mean_val) / max(1.0, max_val)
                glint_scores.append(spike)

        if not glint_scores:
            return 0.5
        avg_spike = sum(glint_scores) / len(glint_scores)
        return max(0.0, min(1.0, (avg_spike - 0.15) / 0.50))

    def _estimate_nasolabial_depth(
        self,
        frame: np.ndarray,
        nose: Tuple[float, float],
        r_mouth: Tuple[float, float],
        l_mouth: Tuple[float, float],
        eye_dist: float
    ) -> float:
        """Sensor 17: Bilateral cheek-lip furrow strain energy."""
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

        pw = max(3, int(eye_dist * 0.12))
        depths = []
        for m_pt in [r_mouth, l_mouth]:
            # Midpoint between nose wing and mouth corner
            cx = int((nose[0] + m_pt[0]) / 2.0)
            cy = int((nose[1] + m_pt[1]) / 2.0)
            y1, y2 = max(0, cy - pw), min(h, cy + pw)
            x1, x2 = max(0, cx - pw), min(w, cx + pw)
            if y2 > y1 and x2 > x1:
                patch = gray[y1:y2, x1:x2]
                grad_x = cv2.Sobel(patch, cv2.CV_64F, 1, 0, ksize=3)
                depths.append(float(np.std(grad_x)))

        if not depths:
            return 0.20
        avg_depth = sum(depths) / len(depths)
        return max(0.0, min(1.0, (avg_depth - 8.0) / 22.0))

    # =========================================================================
    # TEMPORAL FILTER & GETTERS
    # =========================================================================

    def _apply_ema_smoothing(self, raw_sensors: Dict[str, float]) -> Dict[str, float]:
        smoothed = {}
        for k, v in raw_sensors.items():
            if k not in self._ema_sensors:
                self._ema_sensors[k] = v
            else:
                self._ema_sensors[k] = (self._ema_alpha * v) + ((1.0 - self._ema_alpha) * self._ema_sensors[k])
            smoothed[k] = self._ema_sensors[k]
        return smoothed

    def get_last_analysis(self) -> Dict[str, Any]:
        return dict(self._last_analysis)

    # =========================================================================
    # HUD ANNOTATION
    # =========================================================================

    def annotate_frame(
        self,
        frame: np.ndarray,
        analysis: Optional[Dict[str, Any]] = None,
        work_mins: float = 0.0,
        sad_tired_mins: float = 0.0
    ) -> np.ndarray:
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return np.zeros((480, 640, 3), dtype=np.uint8)

        now = time.time()
        if (
            analysis is None
            and self._last_annotated_frame is not None
            and (now - self._last_annotated_time < self._annotated_cache_ttl)
        ):
            return self._last_annotated_frame.copy()

        annotated = frame.copy()
        h, w = annotated.shape[:2]

        if analysis is not None:
            data = analysis
        elif (now - self._last_analysis_time < self._analysis_cache_ttl) and self._last_analysis.get("face_detected") is not None:
            data = self._last_analysis
        else:
            data = self.analyze_frame(annotated)
            self._last_analysis = data
            self._last_analysis_time = now
        face_detected = data.get("face_detected", False)
        emotion = data.get("emotion", "neutral")
        confidence = data.get("emotion_confidence", 0.0)
        looking = data.get("looking_at_camera", False)
        bbox = data.get("primary_bbox")
        landmarks = data.get("landmarks")
        sensors = data.get("sensors", {})
        recognition = data.get("recognition", {})
        enhancement = data.get("enhancement", {})
        detect_method = data.get("detection_method", "yunet")

        emotion_colors = {
            "happy": (0, 230, 115),
            "excited": (255, 191, 0),
            "tired": (0, 140, 255),
            "stressed": (71, 99, 255),
            "sad": (255, 128, 0),
            "neutral": (220, 220, 220),
        }
        theme_color = emotion_colors.get(emotion, (0, 230, 115))

        if face_detected and bbox:
            raw_bx, raw_by, raw_bw, raw_bh = bbox
            # Exponential Moving Average (EMA) coordinate smoothing for jitter-free tracking
            if self._last_known_bbox is not None:
                alpha = 0.35
                bx = int(alpha * raw_bx + (1 - alpha) * self._last_known_bbox[0])
                by = int(alpha * raw_by + (1 - alpha) * self._last_known_bbox[1])
                bw = int(alpha * raw_bw + (1 - alpha) * self._last_known_bbox[2])
                bh = int(alpha * raw_bh + (1 - alpha) * self._last_known_bbox[3])
            else:
                bx, by, bw, bh = raw_bx, raw_by, raw_bw, raw_bh
            self._last_known_bbox = [bx, by, bw, bh]

            corner_len = min(24, int(bw * 0.2))
            thick = 2

            # Clean sleek corner brackets
            cv2.line(annotated, (bx, by), (bx + corner_len, by), theme_color, thick)
            cv2.line(annotated, (bx, by), (bx, by + corner_len), theme_color, thick)
            cv2.line(annotated, (bx + bw, by), (bx + bw - corner_len, by), theme_color, thick)
            cv2.line(annotated, (bx + bw, by), (bx + bw, by + corner_len), theme_color, thick)
            cv2.line(annotated, (bx, by + bh), (bx + corner_len, by + bh), theme_color, thick)
            cv2.line(annotated, (bx, by + bh), (bx, by + bh - corner_len), theme_color, thick)
            cv2.line(annotated, (bx + bw, by + bh), (bx + bw - corner_len, by + bh), theme_color, thick)
            cv2.line(annotated, (bx + bw, by + bh), (bx + bw, by + corner_len), theme_color, thick)

            cv2.rectangle(annotated, (bx, by), (bx + bw, by + bh), theme_color, 1, cv2.LINE_AA)

            user_label = recognition.get("user_name", "User")
            rec_conf = int(recognition.get("confidence", 0.0) * 100)
            tag = f"[{user_label} {rec_conf}%] | {emotion.upper()}"
            cv2.putText(annotated, tag, (bx, max(18, by - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, theme_color, 1, cv2.LINE_AA)
        else:
            self._last_known_bbox = None

        # Top HUD Banner (clean semi-transparent status strip)
        hud_bg = np.zeros((48, w, 3), dtype=np.uint8)
        annotated[0:48, 0:w] = cv2.addWeighted(annotated[0:48, 0:w], 0.35, hud_bg, 0.65, 0)

        cv2.putText(annotated, "MOMO MULTI-SENSOR PERCEPTION CORE", (14, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
        
        clarity_txt = "18-Sensor Low-Res Array" + (" | CLARITY BOOSTED" if enhancement.get("clarity_boosted") else "")
        cv2.putText(annotated, clarity_txt, (14, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.34, (0, 255, 200) if enhancement.get("clarity_boosted") else (160, 160, 160), 1, cv2.LINE_AA)

        gaze_txt = "LOOKING AT MOMO: YES" if looking else "LOOKING AT SCREEN"
        gaze_col = (0, 255, 255) if looking else (180, 180, 180)
        cv2.putText(annotated, gaze_txt, (w - 260, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.38, gaze_col, 1, cv2.LINE_AA)

        emo_txt = f"EMOTION: {emotion.upper()} ({int(confidence * 100)}%)"
        cv2.putText(annotated, emo_txt, (w - 260, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.38, theme_color, 1, cv2.LINE_AA)

        # Bottom Session & Strict Dual Sad+Tired Timer Bar
        bot_bg = np.zeros((32, w, 3), dtype=np.uint8)
        annotated[h - 32:h, 0:w] = cv2.addWeighted(annotated[h - 32:h, 0:w], 0.35, bot_bg, 0.65, 0)

        is_sad_tired = (sensors.get("sadness_score", 0.0) >= 0.55 and sensors.get("tired_score", 0.0) >= 0.55)
        timer_col = (0, 140, 255) if is_sad_tired else (160, 160, 160)
        timer_txt = (
            f"Sad+Tired Countdown: {sad_tired_mins:.1f} / 30m" +
            (" [TIMER RUNNING - SAD & TIRED]" if is_sad_tired else " [TIMER PAUSED - User not both sad & tired]")
        )
        cv2.putText(annotated, timer_txt, (14, h - 11), cv2.FONT_HERSHEY_SIMPLEX, 0.38, timer_col, 1, cv2.LINE_AA)

        self._last_annotated_frame = annotated.copy()
        self._last_annotated_time = now
        return annotated
