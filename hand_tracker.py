"""
Hand Tracker Module
===================
MediaPipe Hand Landmark Pipeline (MediaPipe 1.x Tasks API):
- Video capture preprocessing: Flip horizontal & optional CLAHE (Slide 6 & 9)
- Inference on 21 3D landmarks (BlazePalm + Hand Landmark model) - Slide 10 & 11
- Real-time FPS & Latency (ms) calculation - Slide 17
"""

import math
import time
import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from config import GestureConfig


# 21 Hand Landmark Indices (Slide 11 Topology)
WRIST = 0
THUMB_CMC = 1
THUMB_MCP = 2
THUMB_IP = 3
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_PIP = 6
INDEX_DIP = 7
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_DIP = 11
MIDDLE_TIP = 12
RING_MCP = 13
RING_PIP = 14
RING_DIP = 15
RING_TIP = 16
PINKY_MCP = 17
PINKY_PIP = 18
PINKY_DIP = 19
PINKY_TIP = 20

# Skeleton connection pairs for drawing
HAND_CONNECTIONS = [
    # Thumb
    (WRIST, THUMB_CMC), (THUMB_CMC, THUMB_MCP), (THUMB_MCP, THUMB_IP), (THUMB_IP, THUMB_TIP),
    # Index finger
    (WRIST, INDEX_MCP), (INDEX_MCP, INDEX_PIP), (INDEX_PIP, INDEX_DIP), (INDEX_DIP, INDEX_TIP),
    # Middle finger
    (INDEX_MCP, MIDDLE_MCP), (MIDDLE_MCP, MIDDLE_PIP), (MIDDLE_PIP, MIDDLE_DIP), (MIDDLE_DIP, MIDDLE_TIP),
    # Ring finger
    (MIDDLE_MCP, RING_MCP), (RING_MCP, RING_PIP), (RING_PIP, RING_DIP), (RING_DIP, RING_TIP),
    # Pinky finger
    (RING_MCP, PINKY_MCP), (PINKY_MCP, PINKY_PIP), (PINKY_PIP, PINKY_DIP), (PINKY_DIP, PINKY_TIP),
    # Palm base closure
    (WRIST, PINKY_MCP)
]


@dataclass
class HandData:
    """Contains extracted hand landmarks and spatial metrics."""
    landmarks_norm: List[Tuple[float, float, float]]  # (x, y, z) in [0.0, 1.0]
    landmarks_px: List[Tuple[int, int, float]]         # (x_px, y_px, z_px)
    landmarks_world: List[Tuple[float, float, float]] # (x, y, z) invariant 3D metric coordinates
    palm_size: float                                   # Invariant 3D palm scale
    palm_size_px: float = 60.0                         # Projected 2D scale in pixels for scroll
    handedness: str = "Right"                          # "Left" or "Right"
    estimated_distance_cm: float = 50.0                # Physical estimated distance from camera in cm
    roll_deg: float = 0.0                              # In-plane tilt angle of knuckle line in degrees
    pitch_deg: float = 0.0                             # Palm pointing angle in degrees
    confidence: float = 0.95                           # Neural network landmark detection confidence


class HandTracker:
    """Manages video frame preprocessing and MediaPipe Hand Landmarker."""
    def __init__(self, config: GestureConfig):
        self.config = config

        # Initialize MediaPipe Task
        base_options = python.BaseOptions(model_asset_path=self.config.model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=self.config.max_num_hands,
            min_hand_detection_confidence=self.config.min_detection_confidence,
            min_hand_presence_confidence=self.config.min_presence_confidence,
            min_tracking_confidence=self.config.min_tracking_confidence,
            running_mode=vision.RunningMode.VIDEO
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

        # Performance telemetry
        self.last_timestamp_ms = 0
        self.fps = 0.0
        self.latency_ms = 0.0
        self.current_luminance = 120.0
        self.color_temp_kelvin = 5500
        self.is_night_mode = False
        self._prev_frame_time = time.time()
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        # Precomputed zero-latency gamma LUTs for low-light night enhancement
        self._gamma_tables = {
            1.25: np.array([min(255, int(((i / 255.0) ** (1.0 / 1.25)) * 255)) for i in range(256)], dtype=np.uint8),
            1.40: np.array([min(255, int(((i / 255.0) ** (1.0 / 1.40)) * 255)) for i in range(256)], dtype=np.uint8),
        }

    def apply_clahe(self, bgr_image: np.ndarray, clip_limit: float = 2.0) -> np.ndarray:
        """Adaptive histogram equalization for low-light enhancement with dynamic clip limit."""
        clahe = self._clahe if clip_limit == 2.0 else cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
        lab = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        cl = clahe.apply(l)
        merged = cv2.merge((cl, a, b))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    def process(
        self,
        frame: np.ndarray,
        timestamp_ms: Optional[int] = None
    ) -> Tuple[np.ndarray, Optional[HandData], List[HandData]]:
        """
        Processes a raw camera frame:
        1. Flips horizontally (mirror effect)
        2. Applies dynamic CLAHE low-light enhancement automatically or manually
        3. Runs HandLandmarker inference
        4. Returns processed BGR frame, primary HandData, and all detected hands
        """
        t_start = time.time()

        # Step 1: Flip frame for intuitive mirror control
        if self.config.flip_horizontal:
            frame = cv2.flip(frame, 1)

        # Step 2: Dynamic Auto-Illumination (Smart Low-Light Booster) & Kelvin Estimation
        # Fast subsampled photometric check (takes < 0.04 ms)
        sub = frame[::16, ::16]
        mean_b = float(np.mean(sub[:, :, 0]))
        mean_g = float(np.mean(sub[:, :, 1]))
        mean_r = float(np.mean(sub[:, :, 2]))
        mean_lum = float(0.299 * mean_r + 0.587 * mean_g + 0.114 * mean_b)
        self.current_luminance = mean_lum

        # Color Temperature Estimation in Kelvin
        ratio_br = mean_b / max(1.0, mean_r)
        raw_kelvin = int(5500.0 * math.sqrt(ratio_br))
        self.color_temp_kelvin = max(2400, min(8500, raw_kelvin))

        self.is_night_mode = bool(self.config.use_clahe or mean_lum < 75.0)
        if self.is_night_mode:
            clip = 3.2 if mean_lum < 45.0 else 2.0
            frame = self.apply_clahe(frame, clip_limit=clip)
            if mean_lum < 45.0 and hasattr(self, '_gamma_tables'):
                frame = cv2.LUT(frame, self._gamma_tables[1.40])

        h, w, _ = frame.shape

        # Step 3: Color conversion BGR -> RGB for neural net
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Monotonically increasing timestamp in milliseconds
        if timestamp_ms is None:
            now_ms = int(time.time() * 1000)
            if now_ms <= self.last_timestamp_ms:
                now_ms = self.last_timestamp_ms + 1
            timestamp_ms = now_ms
        self.last_timestamp_ms = timestamp_ms

        # Step 4: MediaPipe inference
        result = self.detector.detect_for_video(mp_image, timestamp_ms)

        # Step 5: Measure performance
        t_end = time.time()
        self.latency_ms = (t_end - t_start) * 1000.0

        current_time = time.time()
        dt = current_time - self._prev_frame_time
        if dt > 0:
            instant_fps = 1.0 / dt
            self.fps = 0.85 * self.fps + 0.15 * instant_fps
        self._prev_frame_time = current_time

        # Step 6: Parse all hand landmarks (supports single-hand and dual-hand tracking)
        all_hands: List[HandData] = []
        if result.hand_landmarks and len(result.hand_landmarks) > 0:
            for hand_idx, raw_landmarks in enumerate(result.hand_landmarks):
                landmarks_norm: List[Tuple[float, float, float]] = []
                landmarks_px: List[Tuple[int, int, float]] = []

                for lm in raw_landmarks:
                    norm_pt = (float(lm.x), float(lm.y), float(lm.z))
                    px_pt = (int(lm.x * w), int(lm.y * h), float(lm.z * w))
                    landmarks_norm.append(norm_pt)
                    landmarks_px.append(px_pt)

                landmarks_world: List[Tuple[float, float, float]] = []
                if result.hand_world_landmarks and len(result.hand_world_landmarks) > hand_idx:
                    raw_world = result.hand_world_landmarks[hand_idx]
                    for wlm in raw_world:
                        landmarks_world.append((float(wlm.x), float(wlm.y), float(wlm.z)))

                lms_3d = landmarks_world if (landmarks_world and len(landmarks_world) == 21) else landmarks_px

                w0 = lms_3d[WRIST]
                m9 = lms_3d[MIDDLE_MCP]
                palm_size_3d = float(math.sqrt(
                    (m9[0] - w0[0])**2 + (m9[1] - w0[1])**2 + (m9[2] - w0[2])**2
                ))
                if palm_size_3d < 1e-4:
                    palm_size_3d = 0.08 if lms_3d is landmarks_world else 50.0

                w_x, w_y, _ = landmarks_px[WRIST]
                m_x, m_y, _ = landmarks_px[MIDDLE_MCP]
                palm_size_px = float(math.hypot(m_x - w_x, m_y - w_y))
                if palm_size_px < 10.0:
                    palm_size_px = 50.0

                # Metric distance estimation: focal length ~550px for standard 640px webcam, adult palm ~8.5cm
                dist_cm = round(max(15.0, min(300.0, 4700.0 / max(12.0, palm_size_px))), 1)

                # 3D spatial roll and pitch tilt estimation
                im_x, im_y, _ = landmarks_px[INDEX_MCP]
                pm_x, pm_y, _ = landmarks_px[PINKY_MCP]
                roll_deg = round(math.degrees(math.atan2(float(im_y - pm_y), float(im_x - pm_x))), 1)
                pitch_deg = round(math.degrees(math.atan2(-float(m_y - w_y), float(m_x - w_x))), 1)

                handedness = "Right"
                conf_score = 0.95
                if result.handedness and len(result.handedness) > hand_idx and len(result.handedness[hand_idx]) > 0:
                    handedness = result.handedness[hand_idx][0].category_name
                    conf_score = float(getattr(result.handedness[hand_idx][0], 'score', 0.95))

                h_data = HandData(
                    landmarks_norm=landmarks_norm,
                    landmarks_px=landmarks_px,
                    landmarks_world=lms_3d,
                    palm_size=palm_size_3d,
                    palm_size_px=palm_size_px,
                    handedness=handedness,
                    estimated_distance_cm=dist_cm,
                    roll_deg=roll_deg,
                    pitch_deg=pitch_deg,
                    confidence=conf_score
                )
                all_hands.append(h_data)

        self.latest_hands = all_hands
        primary_hand = all_hands[0] if all_hands else None
        return frame, primary_hand, all_hands
