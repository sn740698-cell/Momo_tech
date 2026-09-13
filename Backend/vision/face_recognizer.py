"""
Low-Resolution Invariant Facial Recognition & Biometric Profile Engine for MOMO.
Combines OpenCV SFace (deep neural embeddings) with illumination/scale-invariant
Spatial Multi-Region Local Binary Patterns (LBP) and geometric landmark ratios.
Reliably identifies and verifies the user even on noisy, compressed, or low-megapixel webcams.
"""
import os
import cv2
import json
import math
import time
import logging
import numpy as np
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
SFACE_MODEL_PATH = os.path.join(MODELS_DIR, "face_recognition_sface_2021dec.onnx")
PROFILE_PATH = os.path.join(os.path.dirname(__file__), "face_profiles.json")


class LowResFaceRecognizer:
    """
    Biometric face recognition and user verification optimized for low-megapixel webcams.
    """

    def __init__(
        self,
        sface_model_path: Optional[str] = None,
        profile_path: Optional[str] = None
    ):
        self.sface_model_path = sface_model_path or SFACE_MODEL_PATH
        self.profile_path = profile_path or PROFILE_PATH
        self.sface: Optional[cv2.FaceRecognizerSF] = None
        self._init_sface()

        # Biometric profiles store: user_id -> profile dict
        self.profiles: Dict[str, Any] = self._load_profiles()

        # Auto-enrollment accumulator
        self._enrollment_samples: List[Dict[str, Any]] = []
        self._auto_enrolled_id: str = "primary_user"
        self._last_match_result: Dict[str, Any] = {
            "recognized": False,
            "user_id": "unknown",
            "user_name": "Guest",
            "confidence": 0.0,
            "method": "none",
            "status": "Scanning for face...",
        }

    def _init_sface(self):
        if os.path.exists(self.sface_model_path) and os.path.getsize(self.sface_model_path) > 100000:
            try:
                self.sface = cv2.FaceRecognizerSF_create(self.sface_model_path, "")
                logger.info(f"OpenCV FaceRecognizerSF initialized from: {self.sface_model_path}")
            except Exception as e:
                logger.warning(f"Failed initializing FaceRecognizerSF: {e}")
                self.sface = None
        else:
            logger.info("SFace model not found; running in native LBP + geometric invariant mode.")

    def _load_profiles(self) -> Dict[str, Any]:
        if os.path.exists(self.profile_path):
            try:
                with open(self.profile_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load face profiles: {e}")
        return {}

    def _save_profiles(self):
        try:
            with open(self.profile_path, "w", encoding="utf-8") as f:
                json.dump(self.profiles, f, indent=2)
        except Exception as e:
            logger.error(f"Failed saving face profiles: {e}")

    # =========================================================================
    # LOW-RES BIOMETRIC FEATURE EXTRACTION
    # =========================================================================

    def extract_lbp_histogram(self, face_gray: np.ndarray, grid_x: int = 4, grid_y: int = 4) -> np.ndarray:
        """
        Extracts spatial multi-region Local Binary Pattern (LBP) histogram.
        Highly invariant to monotonic grayscale shifts, contrast drops, and low resolution.
        """
        if face_gray is None or face_gray.size == 0:
            return np.zeros(grid_x * grid_y * 16, dtype=np.float32)

        # Standardize face patch to 80x80 for low-res comparison
        resized = cv2.resize(face_gray, (80, 80), interpolation=cv2.INTER_AREA)

        # Simple 8-neighborhood LBP
        h, w = resized.shape
        lbp_img = np.zeros((h - 2, w - 2), dtype=np.uint8)

        center = resized[1:-1, 1:-1]
        lbp_img += (resized[0:-2, 0:-2] >= center).astype(np.uint8) * 1
        lbp_img += (resized[0:-2, 1:-1] >= center).astype(np.uint8) * 2
        lbp_img += (resized[0:-2, 2:] >= center).astype(np.uint8) * 4
        lbp_img += (resized[1:-1, 2:] >= center).astype(np.uint8) * 8
        lbp_img += (resized[2:, 2:] >= center).astype(np.uint8) * 16
        lbp_img += (resized[2:, 1:-1] >= center).astype(np.uint8) * 32
        lbp_img += (resized[2:, 0:-2] >= center).astype(np.uint8) * 64
        lbp_img += (resized[1:-1, 0:-2] >= center).astype(np.uint8) * 128

        # Spatial grid histograms (16 bins each for compactness & robustness)
        cell_h = lbp_img.shape[0] // grid_y
        cell_w = lbp_img.shape[1] // grid_x
        histograms = []

        for gy in range(grid_y):
            for gx in range(grid_x):
                cell = lbp_img[gy * cell_h:(gy + 1) * cell_h, gx * cell_w:(gx + 1) * cell_w]
                hist, _ = np.histogram(cell, bins=16, range=(0, 256))
                norm = np.linalg.norm(hist)
                if norm > 0:
                    hist = hist / norm
                histograms.append(hist)

        full_hist = np.concatenate(histograms).astype(np.float32)
        norm = np.linalg.norm(full_hist)
        return (full_hist / norm) if norm > 0 else full_hist

    def extract_geometric_ratios(self, landmarks: Dict[str, Tuple[float, float]], bbox: List[int]) -> np.ndarray:
        """
        Computes 5 normalized geometric scale-invariant facial ratios:
        1. Inter-ocular distance / face width
        2. Eye midpoint to nose / face height
        3. Nose to mouth midpoint / face height
        4. Mouth width / inter-ocular distance
        5. Facial aspect ratio (height / width)
        """
        try:
            r_eye = landmarks.get("right_eye", (0, 0))
            l_eye = landmarks.get("left_eye", (0, 0))
            nose = landmarks.get("nose", (0, 0))
            r_mouth = landmarks.get("right_mouth", (0, 0))
            l_mouth = landmarks.get("left_mouth", (0, 0))
            bw, bh = max(1.0, float(bbox[2])), max(1.0, float(bbox[3]))

            eye_dist = max(1.0, math.dist(r_eye, l_eye))
            eye_mid_y = (r_eye[1] + l_eye[1]) / 2.0
            mouth_mid_y = (r_mouth[1] + l_mouth[1]) / 2.0
            mouth_w = max(1.0, math.dist(r_mouth, l_mouth))

            ratios = np.array([
                eye_dist / bw,
                (nose[1] - eye_mid_y) / bh,
                (mouth_mid_y - nose[1]) / bh,
                mouth_w / eye_dist,
                bh / bw
            ], dtype=np.float32)
            return ratios
        except Exception:
            return np.zeros(5, dtype=np.float32)

    def extract_sface_embedding(self, frame: np.ndarray, face_data: np.ndarray) -> Optional[np.ndarray]:
        """
        Extracts 128-dim deep embedding via OpenCV FaceRecognizerSF.
        """
        if self.sface is None or frame is None or face_data is None:
            return None
        try:
            aligned_face = self.sface.alignCrop(frame, face_data)
            embedding = self.sface.feature(aligned_face)
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            return embedding.flatten().astype(np.float32)
        except Exception as e:
            logger.debug(f"SFace feature extraction error: {e}")
            return None

    # =========================================================================
    # RECOGNITION & ENROLLMENT
    # =========================================================================

    def recognize_or_enroll(
        self,
        frame: np.ndarray,
        primary_bbox: List[int],
        landmarks: Dict[str, Tuple[float, float]],
        raw_face_yunet: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Recognizes the face in frame against stored profiles.
        If no profile exists, automatically enrolls the user after 4 stable detections.
        """
        if frame is None or not primary_bbox:
            return self._last_match_result

        h, w = frame.shape[:2]
        bx, by, bw, bh = primary_bbox
        # Safe crop with 10% padding
        px = max(0, int(bx - bw * 0.05))
        py = max(0, int(by - bh * 0.05))
        pw = min(w - px, int(bw * 1.10))
        ph = min(h - py, int(bh * 1.10))

        if pw < 10 or ph < 10:
            return self._last_match_result

        crop = frame[py:py + ph, px:px + pw]
        gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop

        # 1. Extract multi-resolution invariant features
        lbp_feat = self.extract_lbp_histogram(gray_crop)
        geom_feat = self.extract_geometric_ratios(landmarks, primary_bbox)
        sface_feat = self.extract_sface_embedding(frame, raw_face_yunet) if raw_face_yunet is not None else None

        # 2. Check if we have enrolled profiles
        if not self.profiles:
            # Accumulate samples for auto-enrollment
            self._enrollment_samples.append({
                "lbp": lbp_feat.tolist(),
                "geom": geom_feat.tolist(),
                "sface": sface_feat.tolist() if sface_feat is not None else None,
            })
            sample_count = len(self._enrollment_samples)
            if sample_count >= 4:
                self._finalize_auto_enrollment()
                res = {
                    "recognized": True,
                    "user_id": self._auto_enrolled_id,
                    "user_name": "Primary User",
                    "confidence": 0.95,
                    "method": "auto_enrolled",
                    "status": "User Enrolled & Recognized",
                }
            else:
                res = {
                    "recognized": False,
                    "user_id": "enrolling",
                    "user_name": "New User",
                    "confidence": round(sample_count / 4.0, 2),
                    "method": "enrolling",
                    "status": f"Enrolling face profile ({sample_count}/4 frames)...",
                }
            self._last_match_result = res
            return res

        # 3. Match against stored profiles
        best_id = None
        best_conf = 0.0
        best_method = "lbp_geom"

        for user_id, prof in self.profiles.items():
            conf_sface = 0.0
            conf_lbp = 0.0
            conf_geom = 0.0

            # SFace match (cosine similarity)
            if sface_feat is not None and prof.get("sface_embedding"):
                ref_sface = np.array(prof["sface_embedding"], dtype=np.float32)
                sim = float(np.dot(sface_feat, ref_sface))
                # SFace cosine similarity > 0.363 is official threshold; map 0.30 - 0.70 to 0.50 - 1.0
                conf_sface = max(0.0, min(1.0, (sim - 0.25) / 0.45))

            # LBP match (histogram intersection / cosine similarity)
            if prof.get("lbp_features"):
                ref_lbp = np.array(prof["lbp_features"], dtype=np.float32)
                lbp_sim = float(np.dot(lbp_feat, ref_lbp))
                conf_lbp = max(0.0, min(1.0, (lbp_sim - 0.45) / 0.45))

            # Geometric match (L2 distance ratio)
            if prof.get("geometric_ratios"):
                ref_geom = np.array(prof["geometric_ratios"], dtype=np.float32)
                geom_diff = float(np.linalg.norm(geom_feat - ref_geom))
                conf_geom = max(0.0, min(1.0, 1.0 - (geom_diff * 1.8)))

            # Composite match confidence
            if sface_feat is not None and prof.get("sface_embedding"):
                combined_conf = 0.60 * conf_sface + 0.25 * conf_lbp + 0.15 * conf_geom
                method = "deep_sface"
            else:
                combined_conf = 0.65 * conf_lbp + 0.35 * conf_geom
                method = "low_res_lbp_geom"

            if combined_conf > best_conf:
                best_conf = combined_conf
                best_id = user_id
                best_method = method

        recognized = best_conf >= 0.50
        user_name = self.profiles.get(best_id, {}).get("name", "User") if recognized else "Unknown User"

        res = {
            "recognized": recognized,
            "user_id": best_id if recognized else "unknown",
            "user_name": user_name,
            "confidence": round(best_conf, 2),
            "method": best_method,
            "status": f"Recognized as {user_name} ({int(best_conf * 100)}%)" if recognized else "Face not verified",
        }
        self._last_match_result = res
        return res

    def _finalize_auto_enrollment(self):
        """Averages collected samples into persistent user profile."""
        if not self._enrollment_samples:
            return

        all_lbp = np.mean([s["lbp"] for s in self._enrollment_samples], axis=0)
        norm = np.linalg.norm(all_lbp)
        if norm > 0:
            all_lbp = all_lbp / norm

        all_geom = np.mean([s["geom"] for s in self._enrollment_samples], axis=0)

        sface_samples = [s["sface"] for s in self._enrollment_samples if s["sface"] is not None]
        all_sface = None
        if sface_samples:
            all_sface = np.mean(sface_samples, axis=0)
            norm_sf = np.linalg.norm(all_sface)
            if norm_sf > 0:
                all_sface = all_sface / norm_sf
            all_sface = all_sface.tolist()

        self.profiles[self._auto_enrolled_id] = {
            "name": "User",
            "created_at": time.time(),
            "lbp_features": all_lbp.tolist(),
            "geometric_ratios": all_geom.tolist(),
            "sface_embedding": all_sface,
        }
        self._save_profiles()
        self._enrollment_samples.clear()
        logger.info(f"Auto-enrolled face profile for '{self._auto_enrolled_id}' successfully.")

    def reset_profiles(self):
        """Clears all stored face profiles."""
        self.profiles.clear()
        self._enrollment_samples.clear()
        if os.path.exists(self.profile_path):
            try:
                os.remove(self.profile_path)
            except Exception as e:
                logger.debug(f"Could not remove profiles file: {e}")
        self._last_match_result = {
            "recognized": False,
            "user_id": "unknown",
            "user_name": "Guest",
            "confidence": 0.0,
            "method": "reset",
            "status": "Profiles reset. Awaiting new face...",
        }
