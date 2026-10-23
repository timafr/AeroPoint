"""
Cyberpunk HUD (Head-Up Display) & Visual Overlay
================================================
Implements:
1. Glassmorphic telemetry panel (FPS, Latency, CPU Load, Active Gesture, 21 Joints) - Slide 11 & 17
2. Cyber-styled hand skeleton with glowing joints & pinch distance indicator - Slide 11
3. Active Workspace Box with corner brackets - Slide 7
4. Real-time Jitter comparison mini-chart (Raw vs EMA Filter) - Slide 15
5. Click pulse / ripple effect
"""

import time
import math
import collections
import cv2
import numpy as np
import psutil
from typing import List, Tuple, Optional, Dict

from config import GestureConfig
from hand_tracker import (
    HandData, HAND_CONNECTIONS,
    WRIST, THUMB_TIP, INDEX_MCP, INDEX_TIP, MIDDLE_TIP
)
from gestures import GestureType


class CyberHUD:
    """Renders high-tech futuristic HUD elements over OpenCV frames."""
    def __init__(self, config: GestureConfig):
        self.config = config
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_mono = cv2.FONT_HERSHEY_PLAIN

        # Real-time jitter chart buffer (Slide 15)
        self.max_chart_points = 64
        self.raw_history = collections.deque(maxlen=self.max_chart_points)
        self.ema_history = collections.deque(maxlen=self.max_chart_points)

        # Click ripple animation queue: list of (x, y, radius, max_radius, color, start_time)
        self.ripples: List[Dict[str, any]] = []

        # Cached CPU percentage (polled every 0.5s to reduce overhead)
        self.last_cpu_check = 0.0
        self.cached_cpu = 0.0

    def trigger_click_ripple(self, px: Tuple[int, int], is_right: bool = False):
        """Spawns an expanding animated ripple at the click coordinate."""
        color = self.config.COLOR_MAGENTA if not is_right else self.config.COLOR_VIOLET
        self.ripples.append({
            "x": px[0],
            "y": px[1],
            "radius": 4.0,
            "max_radius": 36.0,
            "color": color,
            "created": time.time()
        })

    def update_jitter_chart(self, raw_coord: float, ema_coord: float):
        """Appends latest coordinates for real-time jitter graph rendering."""
        self.raw_history.append(raw_coord)
        self.ema_history.append(ema_coord)

    def draw_active_box(self, frame: np.ndarray):
        """Draws glowing boundary of the workspace area with corner brackets."""
        h, w, _ = frame.shape
        x1 = int(w * self.config.margin_x)
        x2 = int(w * (1.0 - self.config.margin_x))
        y1 = int(h * self.config.margin_y)
        y2 = int(h * (1.0 - self.config.margin_y))

        # Thin cyan boundary with alpha
        overlay = frame.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), self.config.COLOR_CYAN, 1)
        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)

        # Corner brackets (Cyberpunk aesthetic)
        bracket_len = 18
        bracket_thick = 2
        col = self.config.COLOR_CYAN

        # Top-left
        cv2.line(frame, (x1, y1), (x1 + bracket_len, y1), col, bracket_thick)
        cv2.line(frame, (x1, y1), (x1, y1 + bracket_len), col, bracket_thick)
        # Top-right
        cv2.line(frame, (x2, y1), (x2 - bracket_len, y1), col, bracket_thick)
        cv2.line(frame, (x2, y1), (x2, y1 + bracket_len), col, bracket_thick)
        # Bottom-left
        cv2.line(frame, (x1, y2), (x1 + bracket_len, y2), col, bracket_thick)
        cv2.line(frame, (x1, y2), (x1, y2 - bracket_len), col, bracket_thick)
        # Bottom-right
        cv2.line(frame, (x2, y2), (x2 - bracket_len, y2), col, bracket_thick)
        cv2.line(frame, (x2, y2), (x2, y2 - bracket_len), col, bracket_thick)

        # Label
        cv2.putText(frame, "ACTIVE CONTROL REGION", (x1 + 6, y1 - 8),
                    self.font_mono, 0.8, col, 1, cv2.LINE_AA)

    def draw_skeleton(
        self,
        frame: np.ndarray,
        hand: HandData,
        gesture: GestureType,
        is_action_hand: bool = False
    ):
        """Draws 21 joints and glowing bones with distinct color palette for dual-hand roles."""
        pts = hand.landmarks_px

        # Base color theme
        if is_action_hand:
            # Action hand palette: Neon violet / purple & amber accents
            if gesture == GestureType.PAUSE:
                bone_col = (180, 180, 180)
            elif gesture == GestureType.DRAG:
                bone_col = (50, 50, 255)
            elif gesture == GestureType.SCROLL:
                bone_col = (50, 255, 120)
            elif gesture in (GestureType.THUMB_CLICK, GestureType.PINCH_CLICK):
                bone_col = (255, 100, 220)
            else:
                bone_col = (240, 120, 180)
            tip_col = (0, 215, 255)
        else:
            # Pointer hand palette: Electric cyan & magenta accents
            if gesture == GestureType.PINCH_CLICK:
                bone_col = self.config.COLOR_MAGENTA
            elif gesture == GestureType.RIGHT_CLICK:
                bone_col = self.config.COLOR_VIOLET
            elif gesture == GestureType.SCROLL:
                bone_col = self.config.COLOR_GREEN
            elif gesture == GestureType.DRAG:
                bone_col = self.config.COLOR_RED
            elif gesture == GestureType.PAUSE:
                bone_col = (180, 180, 180)
            else:
                bone_col = self.config.COLOR_CYAN
            tip_col = self.config.COLOR_MAGENTA

        # Draw bones
        for p1_idx, p2_idx in HAND_CONNECTIONS:
            pt1 = (pts[p1_idx][0], pts[p1_idx][1])
            pt2 = (pts[p2_idx][0], pts[p2_idx][1])
            cv2.line(frame, pt1, pt2, bone_col, 2, cv2.LINE_AA)

        # Draw joints
        for idx, pt in enumerate(pts):
            coord = (pt[0], pt[1])
            is_tip = idx in (THUMB_TIP, INDEX_TIP, MIDDLE_TIP)

            if is_tip:
                cv2.circle(frame, coord, 6, tip_col, -1, cv2.LINE_AA)
                cv2.circle(frame, coord, 9, self.config.COLOR_WHITE, 1, cv2.LINE_AA)
            else:
                cv2.circle(frame, coord, 3, bone_col, -1, cv2.LINE_AA)

        # Role badge above wrist
        w_pt = (pts[WRIST][0], max(20, pts[WRIST][1] - 12))
        role_label = "КОМАНДЫ (Action)" if is_action_hand else "КУРСОР (Pointer)"
        cv2.putText(frame, role_label, (max(10, w_pt[0] - 50), w_pt[1]),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, bone_col, 1, cv2.LINE_AA)

        # Pinch distance guide line
        thumb_pt = (pts[THUMB_TIP][0], pts[THUMB_TIP][1])
        index_pt = (pts[INDEX_TIP][0], pts[INDEX_TIP][1])
        cv2.line(frame, thumb_pt, index_pt, (255, 255, 255), 1, cv2.LINE_AA)

    def draw_ripples(self, frame: np.ndarray):
        """Renders click shockwave rings with optimized local ROI blending (zero full-frame copying)."""
        if not self.ripples:
            return
        now = time.time()
        active_ripples = []
        h, w, _ = frame.shape
        for r in self.ripples:
            elapsed = now - r["created"]
            if elapsed < 0.4:
                curr_rad = int(r["radius"] + (r["max_radius"] - r["radius"]) * (elapsed / 0.4))
                rx, ry = int(r["x"]), int(r["y"])
                # Local ROI clipping to avoid copying the entire 640x480 frame
                x1 = max(0, rx - curr_rad - 3)
                x2 = min(w, rx + curr_rad + 3)
                y1 = max(0, ry - curr_rad - 3)
                y2 = min(h, ry + curr_rad + 3)
                if x2 > x1 and y2 > y1:
                    roi = frame[y1:y2, x1:x2]
                    overlay_roi = roi.copy()
                    alpha = max(0.0, 1.0 - (elapsed / 0.4))
                    cv2.circle(overlay_roi, (rx - x1, ry - y1), curr_rad, r["color"], 2, cv2.LINE_AA)
                    cv2.addWeighted(overlay_roi, alpha, roi, 1.0 - alpha, 0, roi)
                active_ripples.append(r)
        self.ripples = active_ripples

    def draw_telemetry_panel(
        self,
        frame: np.ndarray,
        fps: float,
        latency_ms: float,
        gesture: GestureType,
        hand_detected: bool,
        filter_alpha: float = 0.65
    ):
        """Draws top glassmorphism HUD card with live stats (Slide 17)."""
        now = time.time()
        if now - self.last_cpu_check > 1.0:
            self.cached_cpu = psutil.cpu_percent()
            self.last_cpu_check = now

        panel_w = 260
        panel_h = 160
        panel_x = 14
        panel_y = 14

        # Dark glass background
        overlay = frame.copy()
        cv2.rectangle(overlay, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h),
                      (12, 14, 18), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
        cv2.rectangle(frame, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h),
                      self.config.COLOR_CYAN, 1)

        # Header Badge
        cv2.putText(frame, "HUD TELEMETRY // AI HCI", (panel_x + 12, panel_y + 20),
                    self.font_mono, 0.8, self.config.COLOR_CYAN, 1, cv2.LINE_AA)

        # Status row
        status_text = "STATUS: TRACKING" if hand_detected else "STATUS: SCANNING..."
        status_col = self.config.COLOR_GREEN if hand_detected else (140, 140, 140)
        cv2.putText(frame, status_text, (panel_x + 12, panel_y + 42),
                    self.font_mono, 0.9, status_col, 1, cv2.LINE_AA)

        # Gesture indicator
        gesture_col = self.config.COLOR_CYAN
        if gesture == GestureType.PINCH_CLICK:
            gesture_col = self.config.COLOR_MAGENTA
        elif gesture == GestureType.RIGHT_CLICK:
            gesture_col = self.config.COLOR_VIOLET
        elif gesture == GestureType.SCROLL:
            gesture_col = self.config.COLOR_GREEN
        elif gesture == GestureType.DRAG:
            gesture_col = self.config.COLOR_RED
        elif gesture == GestureType.PAUSE:
            gesture_col = (160, 160, 160)

        cv2.putText(frame, f"MODE: {gesture.value}", (panel_x + 12, panel_y + 64),
                    self.font, 0.44, gesture_col, 1, cv2.LINE_AA)

        # FPS & Latency
        fps_col = self.config.COLOR_GREEN if fps >= 30.0 else (0, 165, 255)
        cv2.putText(frame, f"FPS: {fps:4.1f}", (panel_x + 12, panel_y + 88),
                    self.font_mono, 0.9, fps_col, 1, cv2.LINE_AA)

        cv2.putText(frame, f"LATENCY: {latency_ms:4.1f} ms", (panel_x + 120, panel_y + 88),
                    self.font_mono, 0.9, self.config.COLOR_WHITE, 1, cv2.LINE_AA)

        # CPU Load & Joints
        cv2.putText(frame, f"CPU: {self.cached_cpu:4.1f}%", (panel_x + 12, panel_y + 110),
                    self.font_mono, 0.9, self.config.COLOR_WHITE, 1, cv2.LINE_AA)

        joints_text = "JOINTS: 21/21" if hand_detected else "JOINTS: 0/21"
        cv2.putText(frame, joints_text, (panel_x + 120, panel_y + 110),
                    self.font_mono, 0.9, self.config.COLOR_CYAN, 1, cv2.LINE_AA)

        # Filter info
        clahe_str = "ON" if self.config.use_clahe else "OFF"
        cv2.putText(frame, f"FILTER: EMA(a={filter_alpha:.2f})  CLAHE: {clahe_str}",
                    (panel_x + 12, panel_y + 132),
                    self.font_mono, 0.75, (180, 180, 180), 1, cv2.LINE_AA)

    def draw_jitter_chart(self, frame: np.ndarray):
        """Draws bottom-right real-time Jitter Attenuation graph (Slide 15)."""
        if len(self.raw_history) < 2:
            return

        h, w, _ = frame.shape
        chart_w = 200
        chart_h = 70
        chart_x = w - chart_w - 14
        chart_y = h - chart_h - 35

        # Background
        overlay = frame.copy()
        cv2.rectangle(overlay, (chart_x, chart_y), (chart_x + chart_w, chart_y + chart_h),
                      (10, 10, 14), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        cv2.rectangle(frame, (chart_x, chart_y), (chart_x + chart_w, chart_y + chart_h),
                      (60, 60, 80), 1)

        # Label & legend
        cv2.putText(frame, "JITTER FILTER (EMA)", (chart_x + 6, chart_y - 6),
                    self.font_mono, 0.75, self.config.COLOR_CYAN, 1, cv2.LINE_AA)

        # Scale data
        raw_arr = np.array(self.raw_history, dtype=np.float32)
        ema_arr = np.array(self.ema_history, dtype=np.float32)
        min_v = min(raw_arr.min(), ema_arr.min())
        max_v = max(raw_arr.max(), ema_arr.max())
        val_range = max(1.0, max_v - min_v)

        def val_to_y(val):
            norm = (val - min_v) / val_range
            return int(chart_y + chart_h - 6 - norm * (chart_h - 14))

        step_x = chart_w / float(self.max_chart_points - 1)

        # Draw raw signal (Red)
        for i in range(len(raw_arr) - 1):
            x1 = int(chart_x + i * step_x)
            y1 = val_to_y(raw_arr[i])
            x2 = int(chart_x + (i + 1) * step_x)
            y2 = val_to_y(raw_arr[i + 1])
            cv2.line(frame, (x1, y1), (x2, y2), self.config.COLOR_RED, 1, cv2.LINE_AA)

        # Draw EMA signal (Cyan)
        for i in range(len(ema_arr) - 1):
            x1 = int(chart_x + i * step_x)
            y1 = val_to_y(ema_arr[i])
            x2 = int(chart_x + (i + 1) * step_x)
            y2 = val_to_y(ema_arr[i + 1])
            cv2.line(frame, (x1, y1), (x2, y2), self.config.COLOR_CYAN, 2, cv2.LINE_AA)

    def draw_footer_bar(self, frame: np.ndarray):
        """Renders bottom control help keys."""
        h, w, _ = frame.shape
        bar_y = h - 12
        help_text = "[Q] Quit  |  [C] CLAHE  |  [H] Toggle HUD  |  [S] Skeleton  |  [P] Pause"
        cv2.putText(frame, help_text, (16, bar_y),
                    self.font_mono, 0.8, (200, 200, 200), 1, cv2.LINE_AA)

    def draw_laser_pointer(
        self,
        frame: np.ndarray,
        hand: HandData,
        is_clicking: bool = False
    ):
        """Renders holographic laser targeting beam and futuristic reticle."""
        pts = hand.landmarks_px
        h, w, _ = frame.shape
        mcp = pts[INDEX_MCP]
        tip = pts[INDEX_TIP]

        # Ray vector from knuckle through index tip
        dx = float(tip[0] - mcp[0])
        dy = float(tip[1] - mcp[1])
        mag = math.hypot(dx, dy)
        if mag < 1e-4:
            return

        ndx = dx / mag
        ndy = dy / mag

        # Project 220 pixels in front of the finger tip
        target_dist = 220.0
        tx = int(tip[0] + ndx * target_dist)
        ty = int(tip[1] + ndy * target_dist)
        tx = max(8, min(w - 8, tx))
        ty = max(8, min(h - 8, ty))

        beam_color = (0, 242, 254) if not is_clicking else (50, 50, 255)
        glow_color = (0, 180, 255) if not is_clicking else (80, 80, 255)

        # 1. Outer glowing beam (alpha blended)
        overlay = frame.copy()
        cv2.line(overlay, (tip[0], tip[1]), (tx, ty), glow_color, 5, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

        # 2. Core crisp laser beam
        cv2.line(frame, (tip[0], tip[1]), (tx, ty), (255, 255, 255), 1, cv2.LINE_AA)
        cv2.circle(frame, (tip[0], tip[1]), 3, (255, 255, 255), -1, cv2.LINE_AA)

        # 3. Holographic Reticle at target
        reticle_rad = 12 if not is_clicking else 7
        cv2.circle(frame, (tx, ty), reticle_rad, beam_color, 1, cv2.LINE_AA)
        cv2.circle(frame, (tx, ty), 3, (255, 255, 255), -1, cv2.LINE_AA)

        # Crosshairs
        ch_len = 8
        cv2.line(frame, (tx - ch_len - 4, ty), (tx - 4, ty), beam_color, 1, cv2.LINE_AA)
        cv2.line(frame, (tx + 4, ty), (tx + ch_len + 4, ty), beam_color, 1, cv2.LINE_AA)
        cv2.line(frame, (tx, ty - ch_len - 4), (tx, ty - 4), beam_color, 1, cv2.LINE_AA)
        cv2.line(frame, (tx, ty + 4), (tx, ty + ch_len + 4), beam_color, 1, cv2.LINE_AA)

        # Target Coordinates Tag
        tag = f"L-AIM [{tx},{ty}]"
        cv2.putText(frame, tag, (tx + 12, ty - 6), cv2.FONT_HERSHEY_PLAIN, 0.75, beam_color, 1, cv2.LINE_AA)

    def render_clean(
        self,
        frame: np.ndarray,
        hand: Optional[HandData] = None,
        hands: Optional[List[HandData]] = None,
        gesture: GestureType = GestureType.NONE,
        action_gesture: GestureType = GestureType.NONE,
        pointer_hand: Optional[HandData] = None,
        action_hand: Optional[HandData] = None,
        show_skeleton: bool = True,
        laser_pointer_mode: bool = False
    ) -> np.ndarray:
        """Clean rendering for GUI stream: draws distinct glowing skeletons for both hands."""
        if show_skeleton:
            if pointer_hand and action_hand:
                self.draw_skeleton(frame, pointer_hand, gesture, is_action_hand=False)
                self.draw_skeleton(frame, action_hand, action_gesture, is_action_hand=True)
            elif hands and len(hands) > 0:
                for idx, h in enumerate(hands):
                    self.draw_skeleton(frame, h, gesture, is_action_hand=(idx > 0))
            elif hand:
                self.draw_skeleton(frame, hand, gesture, is_action_hand=False)

        # Holographic Laser Aiming Vector
        if laser_pointer_mode:
            target_h = pointer_hand or (hands[0] if hands else hand)
            if target_h:
                is_click = gesture in (GestureType.THUMB_CLICK, GestureType.PINCH_CLICK, GestureType.AIR_TAP)
                self.draw_laser_pointer(frame, target_h, is_clicking=is_click)

        self.draw_ripples(frame)
        return frame

    def render(
        self,
        frame: np.ndarray,
        hand: Optional[HandData],
        gesture: GestureType,
        fps: float,
        latency_ms: float,
        filter_alpha: float = 0.65
    ) -> np.ndarray:
        """Assembles all HUD elements onto the frame."""
        if self.config.show_active_box:
            self.draw_active_box(frame)

        if hand and self.config.show_skeleton:
            self.draw_skeleton(frame, hand, gesture)

        self.draw_ripples(frame)

        if self.config.show_hud:
            self.draw_telemetry_panel(
                frame,
                fps=fps,
                latency_ms=latency_ms,
                gesture=gesture,
                hand_detected=(hand is not None),
                filter_alpha=filter_alpha
            )

        if self.config.show_jitter_graph:
            self.draw_jitter_chart(frame)

        self.draw_footer_bar(frame)
        return frame
