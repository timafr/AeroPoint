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
        self._prev_frame_time = time.time()
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def apply_clahe(self, bgr_image: np.ndarray) -> np.ndarray:
        """Adaptive histogram equalization for low-light enhancement (Slide 6)."""
        lab = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        cl = self._clahe.apply(l)
        merged = cv2.merge((cl, a, b))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    def process(
        self,
        frame: np.ndarray,
        timestamp_ms: Optional[int] = None
    ) -> Tuple[np.ndarray, Optional[HandData]]:
        """
        Processes a raw camera frame:
        1. Flips horizontally (mirror effect)
        2. Applies CLAHE if enabled
        3. Runs HandLandmarker inference
        4. Returns processed BGR frame and HandData (if detected)
        """
        t_start = time.time()

        # Step 1: Flip frame for intuitive mirror control
        if self.config.flip_horizontal:
            frame = cv2.flip(frame, 1)

        # Step 2: Optional CLAHE illumination normalization
        if self.config.use_clahe:
            frame = self.apply_clahe(frame)

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

                handedness = "Right"
                if result.handedness and len(result.handedness) > hand_idx and len(result.handedness[hand_idx]) > 0:
                    handedness = result.handedness[hand_idx][0].category_name

                h_data = HandData(
                    landmarks_norm=landmarks_norm,
                    landmarks_px=landmarks_px,
                    landmarks_world=lms_3d,
                    palm_size=palm_size_3d,
                    palm_size_px=palm_size_px,
                    handedness=handedness
                )
                all_hands.append(h_data)

        self.latest_hands = all_hands
        primary_hand = all_hands[0] if all_hands else None
        return frame, primary_hand, all_hands
