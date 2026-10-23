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

        # Slide swipe visual chevron animation queue
        self.swipe_chevrons: List[Dict[str, any]] = []

        # Rotary dial visual feedback queue
        self.rotary_feedbacks: List[Dict[str, any]] = []

        # Kinetic velocity tracker & precision reticle
        self.prev_pointer_tip: Optional[Tuple[int, int]] = None
        self.prev_pointer_time: float = 0.0
        self.smoothed_velocity: float = 0.0
        self.velocity_vector: Tuple[float, float] = (0.0, 0.0)

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

    def trigger_slide_chevron(self, is_next: bool = True):
        """Spawns a glowing directional slide transition chevron across the HUD."""
        self.swipe_chevrons.append({
            "is_next": is_next,
            "created": time.time()
        })

    def trigger_rotary_feedback(self, px: Tuple[int, int], is_up: bool = True, delta_deg: float = 0.0):
        """Spawns an in-air holographic volume dial arc around the wrist/hand."""
        self.rotary_feedbacks.append({
            "x": px[0],
            "y": px[1],
            "is_up": is_up,
            "delta_deg": delta_deg,
            "created": time.time()
        })

    def draw_slide_chevrons(self, frame: np.ndarray):
        """Renders animated presentation slide transition chevrons across the screen."""
        if not self.swipe_chevrons:
            return
        now = time.time()
        active = []
        h, w, _ = frame.shape
        cy = h // 2

        for sc in self.swipe_chevrons:
            elapsed = now - sc["created"]
            duration = 0.45
            if elapsed < duration:
                progress = elapsed / duration
                alpha = max(0.0, 1.0 - progress)
                col = (0, 242, 254) if sc["is_next"] else (255, 0, 128)
                label = "СЛЕДУЮЩИЙ СЛАЙД  >>>" if sc["is_next"] else "<<<  ПРЕДЫДУЩИЙ СЛАЙД"

                if sc["is_next"]:
                    cx = int(w * 0.40 + (w * 0.45 * progress))
                else:
                    cx = int(w * 0.60 - (w * 0.45 * progress))

                bw, bh = 240, 44
                x1 = max(0, cx - bw // 2)
                x2 = min(w, cx + bw // 2)
                y1 = max(0, cy - bh // 2)
                y2 = min(h, cy + bh // 2)

                if x2 > x1 and y2 > y1:
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (x1, y1), (x2, y2), (14, 12, 18), -1)
                    cv2.rectangle(overlay, (x1, y1), (x2, y2), col, 2, cv2.LINE_AA)
                    cv2.putText(overlay, label, (x1 + 14, cy + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)
                    cv2.addWeighted(overlay, alpha * 0.85, frame, 1.0 - (alpha * 0.85), 0, frame)

                active.append(sc)
        self.swipe_chevrons = active

    def draw_rotary_dials(self, frame: np.ndarray):
        """Renders in-air rotary volume knob dial arc at wrist/hand coordinates."""
        if not self.rotary_feedbacks:
            return
        now = time.time()
        active = []
        h, w, _ = frame.shape

        for rf in self.rotary_feedbacks:
            elapsed = now - rf["created"]
            duration = 0.40
            if elapsed < duration:
                progress = elapsed / duration
                alpha = max(0.0, 1.0 - progress)
                rx, ry = int(rf["x"]), int(rf["y"])
                col = (0, 230, 118) if rf["is_up"] else (255, 60, 160)
                tag = "VOL +" if rf["is_up"] else "VOL -"

                r = 32
                x1 = max(0, rx - r - 25)
                x2 = min(w, rx + r + 25)
                y1 = max(0, ry - r - 25)
                y2 = min(h, ry + r + 25)

                if x2 > x1 and y2 > y1:
                    overlay = frame.copy()
                    start_a = -90 if rf["is_up"] else 90
                    end_a = start_a + (120 if rf["is_up"] else -120)
                    cv2.ellipse(overlay, (rx, ry), (r, r), 0, start_a, end_a, col, 3, cv2.LINE_AA)
                    cv2.circle(overlay, (rx, ry), 4, (255, 255, 255), -1, cv2.LINE_AA)
                    cv2.putText(overlay, tag, (rx - 22, ry + 5), cv2.FONT_HERSHEY_PLAIN, 0.9, (255, 255, 255), 1, cv2.LINE_AA)
                    cv2.addWeighted(overlay, alpha * 0.80, frame, 1.0 - (alpha * 0.80), 0, frame)

                active.append(rf)
        self.rotary_feedbacks = active

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

        # Distance Caliper tag below wrist
        dist_val = getattr(hand, 'estimated_distance_cm', 50.0)
        dist_col = (0, 242, 254) if 35 <= dist_val <= 85 else ((0, 180, 255) if dist_val < 35 else (200, 120, 255))
        dist_tag = f"DIST: {int(dist_val)}cm"
        cv2.putText(frame, dist_tag, (max(10, w_pt[0] - 32), min(frame.shape[0] - 8, pts[WRIST][1] + 18)),
                    cv2.FONT_HERSHEY_PLAIN, 0.85, dist_col, 1, cv2.LINE_AA)

        # Hand Roll & Tilt angle indicator below distance caliper
        roll_angle = getattr(hand, 'roll_deg', 0.0)
        roll_sign = "+" if roll_angle >= 0 else ""
        tilt_tag = f"TILT: {roll_sign}{int(roll_angle)}deg"
        cv2.putText(frame, tilt_tag, (max(10, w_pt[0] - 32), min(frame.shape[0] - 6, pts[WRIST][1] + 32)),
                    cv2.FONT_HERSHEY_PLAIN, 0.75, (220, 220, 220), 1, cv2.LINE_AA)

        # Miniature Artificial Horizon Leveler Bar
        roll_rad = math.radians(roll_angle)
        bar_len = 14
        bx1 = int(w_pt[0] - bar_len * math.cos(roll_rad))
        by1 = int(min(frame.shape[0] - 6, pts[WRIST][1] + 42) - bar_len * math.sin(roll_rad))
        bx2 = int(w_pt[0] + bar_len * math.cos(roll_rad))
        by2 = int(min(frame.shape[0] - 6, pts[WRIST][1] + 42) + bar_len * math.sin(roll_rad))
        cv2.line(frame, (bx1, by1), (bx2, by2), dist_col, 1, cv2.LINE_AA)
        cv2.circle(frame, (w_pt[0], min(frame.shape[0] - 6, pts[WRIST][1] + 42)), 2, (255, 255, 255), -1, cv2.LINE_AA)

        # Interactive Pinch Proximity Halo & Magnetic Snap Spark
        thumb_pt = (int(pts[THUMB_TIP][0]), int(pts[THUMB_TIP][1]))
        index_pt = (int(pts[INDEX_TIP][0]), int(pts[INDEX_TIP][1]))
        dist_px = math.hypot(thumb_pt[0] - index_pt[0], thumb_pt[1] - index_pt[1])
        prox = max(0.0, min(1.0, 1.0 - (dist_px / 75.0)))

        # Dynamic color transitions from cyan to neon gold to magenta
        if prox > 0.82 or gesture in (GestureType.PINCH_CLICK, GestureType.THUMB_CLICK):
            guide_color = (255, 0, 128)  # Hot magenta
            line_thick = 2
        elif prox > 0.45:
            guide_color = (0, 215, 255)  # Gold/amber
            line_thick = 1
        else:
            guide_color = (180, 240, 255)
            line_thick = 1

        cv2.line(frame, thumb_pt, index_pt, guide_color, line_thick, cv2.LINE_AA)

        # Proximity magnetic halos
        halo_r = int(7 + 10 * prox)
        cv2.circle(frame, thumb_pt, halo_r, guide_color, 1, cv2.LINE_AA)
        cv2.circle(frame, index_pt, halo_r, guide_color, 1, cv2.LINE_AA)

        # Midpoint spark when approaching click threshold
        if prox > 0.65:
            mid_x = (thumb_pt[0] + index_pt[0]) // 2
            mid_y = (thumb_pt[1] + index_pt[1]) // 2
            cv2.circle(frame, (mid_x, mid_y), int(3 + 4 * prox), (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, (mid_x, mid_y), int(5 + 6 * prox), guide_color, 1, cv2.LINE_AA)

        # Kinetic velocity tracking and precision reticle for Pointer Hand
        if not is_action_hand:
            now = time.time()
            if self.prev_pointer_tip and (now - self.prev_pointer_time > 0.005):
                dt = now - self.prev_pointer_time
                vx = (index_pt[0] - self.prev_pointer_tip[0]) / dt
                vy = (index_pt[1] - self.prev_pointer_tip[1]) / dt
                inst_vel = math.hypot(vx, vy)
                self.smoothed_velocity = 0.70 * self.smoothed_velocity + 0.30 * inst_vel
                self.velocity_vector = (vx, vy)
            self.prev_pointer_tip = index_pt
            self.prev_pointer_time = now

            self.draw_speedometer_and_precision_reticle(frame, index_pt, self.smoothed_velocity, self.velocity_vector)

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

        # 0. Ephemeral Glowing Plasma Ribbon Trail
        now = time.time()
        if not hasattr(self, 'laser_trail'):
            self.laser_trail = []
        self.laser_trail.append((tx, ty, now))
        self.laser_trail = [(x, y, ts) for (x, y, ts) in self.laser_trail if (now - ts) <= 0.35]

        if len(self.laser_trail) > 1:
            trail_overlay = frame.copy()
            for idx in range(len(self.laser_trail) - 1):
                p1 = (self.laser_trail[idx][0], self.laser_trail[idx][1])
                p2 = (self.laser_trail[idx + 1][0], self.laser_trail[idx + 1][1])
                age = now - self.laser_trail[idx][2]
                alpha = max(0.05, 1.0 - (age / 0.35))
                thickness = max(1, int(3 * alpha))
                seg_col = (
                    int(glow_color[0] * alpha),
                    int(glow_color[1] * alpha),
                    int(glow_color[2] * alpha)
                )
                cv2.line(trail_overlay, p1, p2, seg_col, thickness, cv2.LINE_AA)
            cv2.addWeighted(trail_overlay, 0.50, frame, 0.50, 0, frame)

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

    def draw_calibration_target(
        self,
        frame: np.ndarray,
        progress_pct: float = 1.0,
        stage_label: str = "АВТО-КАЛИБРОВКА..."
    ):
        """Draws glowing holographic calibration target with animated rotating arcs and countdown ring."""
        h, w, _ = frame.shape
        cx, cy = w // 2, h // 2
        now = time.time()

        # Rotating outer reticle
        r_outer = 64
        angle = (now * 180.0) % 360.0
        overlay = frame.copy()

        # Neon circular arcs
        for offset in [0, 90, 180, 270]:
            start_a = int(angle + offset)
            end_a = int(angle + offset + 55)
            cv2.ellipse(overlay, (cx, cy), (r_outer, r_outer), 0, start_a, end_a, (0, 242, 254), 2, cv2.LINE_AA)

        # Inner progress gauge ring
        r_inner = 50
        prog_end = int(-90 + (progress_pct * 360.0))
        cv2.ellipse(overlay, (cx, cy), (r_inner, r_inner), 0, -90, prog_end, (0, 230, 118), 3, cv2.LINE_AA)

        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        # Center target dot
        cv2.circle(frame, (cx, cy), 5, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), 12, (0, 242, 254), 1, cv2.LINE_AA)

        # Crosshairs
        cv2.line(frame, (cx - 24, cy), (cx - 14, cy), (0, 242, 254), 1, cv2.LINE_AA)
        cv2.line(frame, (cx + 14, cy), (cx + 24, cy), (0, 242, 254), 1, cv2.LINE_AA)
        cv2.line(frame, (cx, cy - 24), (cx, cy - 14), (0, 242, 254), 1, cv2.LINE_AA)
        cv2.line(frame, (cx, cy + 14), (cx, cy + 24), (0, 242, 254), 1, cv2.LINE_AA)

        # Floating Calibration Labels
        cv2.putText(frame, stage_label, (cx - 75, cy - r_outer - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 242, 254), 1, cv2.LINE_AA)
        pct_text = f"{int(progress_pct * 100)}%"
        cv2.putText(frame, pct_text, (cx - 16, cy + r_outer + 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 230, 118), 1, cv2.LINE_AA)

    def draw_speedometer_and_precision_reticle(
        self,
        frame: np.ndarray,
        index_pt: Tuple[int, int],
        velocity: float,
        vec: Tuple[float, float]
    ):
        """Draws kinetic velocity readout and motion vector or micro-precision targeting reticle."""
        h, w, _ = frame.shape
        ix, iy = index_pt

        if velocity >= 260.0:
            # Kinetic high-speed tracking: motion streak + velocity tag
            norm = math.hypot(vec[0], vec[1])
            if norm > 1.0:
                streak_len = min(28, int(norm * 0.025))
                tx = int(ix - (vec[0] / norm) * streak_len)
                ty = int(iy - (vec[1] / norm) * streak_len)
                cv2.line(frame, (ix, iy), (tx, ty), (0, 242, 254), 2, cv2.LINE_AA)

            badge_text = f"{int(velocity)} px/s"
            bx = max(10, min(w - 95, ix + 14))
            by = max(18, min(h - 10, iy - 8))
            cv2.putText(frame, badge_text, (bx, by), cv2.FONT_HERSHEY_PLAIN, 0.85, (0, 242, 254), 1, cv2.LINE_AA)

        elif velocity <= 80.0:
            # Micro-Precision Stabilization reticle
            cv2.circle(frame, index_pt, 10, (0, 242, 254), 1, cv2.LINE_AA)
            cv2.line(frame, (ix - 14, iy), (ix - 6, iy), (0, 242, 254), 1, cv2.LINE_AA)
            cv2.line(frame, (ix + 6, iy), (ix + 14, iy), (0, 242, 254), 1, cv2.LINE_AA)
            cv2.line(frame, (ix, iy - 14), (ix, iy - 6), (0, 242, 254), 1, cv2.LINE_AA)
            cv2.line(frame, (ix, iy + 6), (ix, iy + 14), (0, 242, 254), 1, cv2.LINE_AA)

    def draw_depth_push_indicator(
        self,
        frame: np.ndarray,
        index_pt: Tuple[int, int],
        air_tap_pct: float
    ):
        """Draws Apple Vision Pro style 3D depth push rings shrinking toward fingertip as user presses forward."""
        if air_tap_pct <= 5.0:
            return
        ix, iy = index_pt
        ratio = min(1.0, max(0.0, air_tap_pct / 100.0))

        # Dynamic ring shrinks from radius 32 down to 10 as user pushes
        ring_r = int(32 - 20 * ratio)
        if ratio > 0.85:
            ring_col = (255, 0, 128)  # Hot magenta trigger zone
            thick = 2
        elif ratio > 0.50:
            ring_col = (0, 230, 118)  # Emerald green press in progress
            thick = 2
        else:
            ring_col = (0, 242, 254)  # Cyan approach
            thick = 1

        cv2.circle(frame, (ix, iy), ring_r, ring_col, thick, cv2.LINE_AA)

        # Inner feedback core
        core_r = max(2, int(6 * ratio))
        cv2.circle(frame, (ix, iy), core_r, ring_col, -1, cv2.LINE_AA)

        # Depth progress tag
        tag = f"DEPTH {int(air_tap_pct)}%"
        cv2.putText(frame, tag, (ix + 16, iy + 14), cv2.FONT_HERSHEY_PLAIN, 0.8, ring_col, 1, cv2.LINE_AA)

    def draw_scroll_cylinder(
        self,
        frame: np.ndarray,
        center_pt: Tuple[int, int],
        velocity: float
    ):
        """
        Renders an in-air holographic 3D rotating scroll wheel with sinusoidal projection.
        Ticks compress towards top/bottom edges simulating a physical cylindrical roller.
        """
        h, w, _ = frame.shape
        cx, cy = center_pt
        # Clamp within frame margins
        cx = max(30, min(w - 30, cx + 45))
        cy = max(60, min(h - 60, cy))

        wheel_w = 24
        wheel_h = 76
        half_w = wheel_w // 2
        half_h = wheel_h // 2

        # Draw semi-transparent dark backing capsule
        overlay = frame.copy()
        cv2.rectangle(
            overlay,
            (cx - half_w, cy - half_h),
            (cx + half_w, cy + half_h),
            (14, 12, 18),
            -1
        )
        cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)

        # Outer glowing border
        glow_col = self.config.COLOR_GREEN if abs(velocity) > 0.1 else self.config.COLOR_CYAN
        cv2.rectangle(
            frame,
            (cx - half_w, cy - half_h),
            (cx + half_w, cy + half_h),
            glow_col,
            1,
            cv2.LINE_AA
        )

        # Update accumulated rotational phase for cylindrical animation
        if not hasattr(self, '_scroll_phase'):
            self._scroll_phase = 0.0
        self._scroll_phase += velocity * 0.12

        # Draw 7 cylindrical rungs using sinusoidal projection
        num_ticks = 7
        for i in range(num_ticks):
            angle = (self._scroll_phase + i * (math.pi / 3.5)) % math.pi - (math.pi / 2.0)
            tick_y = int(cy + half_h * math.sin(angle))
            factor = max(0.2, math.cos(angle))
            tick_w = int(half_w * factor)
            tick_col = (
                int(glow_col[0] * factor),
                int(glow_col[1] * factor),
                int(glow_col[2] * factor)
            )
            cv2.line(
                frame,
                (cx - tick_w + 2, tick_y),
                (cx + tick_w - 2, tick_y),
                tick_col,
                1,
                cv2.LINE_AA
            )

        # Directional Arrow Indicator
        if velocity < -0.2:
            cv2.putText(frame, "^", (cx - 4, cy - half_h - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.config.COLOR_GREEN, 1, cv2.LINE_AA)
        elif velocity > 0.2:
            cv2.putText(frame, "v", (cx - 4, cy + half_h + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.config.COLOR_GREEN, 1, cv2.LINE_AA)

        # Label tag
        cv2.putText(frame, "SCROLL", (cx - 20, cy + half_h + (22 if velocity > 0.2 else 12)), cv2.FONT_HERSHEY_PLAIN, 0.65, (220, 220, 220), 1, cv2.LINE_AA)

    def draw_radial_hud(
        self,
        frame: np.ndarray,
        active_sector: Optional[int] = None
    ):
        """
        Renders a futuristic holographic 8-sector Quick-Dial radial overlay in the center of the frame.
        """
        h, w, _ = frame.shape
        cx, cy = w // 2, h // 2
        r_inner = 34
        r_outer = 135

        overlay = frame.copy()
        # Darkened semi-transparent circular backdrop
        cv2.circle(overlay, (cx, cy), r_outer + 8, (14, 12, 10), -1)

        # 8 Sectors definitions (clockwise from top)
        sectors = [
            ("WIN+TAB", (0, -1)),
            ("SNIP", (1, -1)),
            ("VOL+", (1, 0)),
            ("VOL-", (1, 1)),
            ("PLAY", (0, 1)),
            ("DESK", (-1, 1)),
            ("ALT+TAB", (-1, 0)),
            ("LOCK", (-1, -1)),
        ]

        # Draw sector background wedges
        for idx in range(8):
            start_angle = -90 + idx * 45 - 22.5
            end_angle = start_angle + 45
            is_active = (active_sector == idx)

            if is_active:
                wedge_col = (0, 242, 254) if idx % 2 == 0 else (255, 0, 128)
                cv2.ellipse(overlay, (cx, cy), (r_outer, r_outer), 0, start_angle, end_angle, wedge_col, -1)

        cv2.addWeighted(overlay, 0.68, frame, 0.32, 0, frame)

        # Draw divider lines and text
        for idx, (label, vec) in enumerate(sectors):
            div_angle = math.radians(-90 + idx * 45 - 22.5)
            x1 = int(cx + r_inner * math.cos(div_angle))
            y1 = int(cy + r_inner * math.sin(div_angle))
            x2 = int(cx + r_outer * math.cos(div_angle))
            y2 = int(cy + r_outer * math.sin(div_angle))
            cv2.line(frame, (x1, y1), (x2, y2), (255, 255, 255), 1, cv2.LINE_AA)

            mid_angle = math.radians(-90 + idx * 45)
            tx = int(cx + 85 * math.cos(mid_angle))
            ty = int(cy + 85 * math.sin(mid_angle))
            is_active = (active_sector == idx)
            text_col = (10, 10, 10) if is_active else (255, 255, 255)
            font_scale = 0.85 if is_active else 0.75
            thick = 2 if is_active else 1

            off_x = len(label) * 4
            cv2.putText(frame, label, (tx - off_x, ty + 4), cv2.FONT_HERSHEY_PLAIN, font_scale, text_col, thick, cv2.LINE_AA)

        # Outer & Inner rings
        cv2.circle(frame, (cx, cy), r_outer, self.config.COLOR_CYAN, 2, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), r_inner, (255, 255, 255), 2, cv2.LINE_AA)

        # Center core orb
        cv2.circle(frame, (cx, cy), r_inner - 2, (20, 16, 24), -1)
        cv2.putText(frame, "AERO", (cx - 18, cy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, self.config.COLOR_CYAN, 1, cv2.LINE_AA)

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
        laser_pointer_mode: bool = False,
        calibration_progress: Optional[float] = None,
        air_tap_pct: float = 0.0,
        radial_menu_active: bool = False,
        active_radial_sector: Optional[int] = None,
        scroll_velocity: float = 0.0
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

        # Vision Pro Depth Push visual feedback
        if air_tap_pct > 5.0:
            target_h = pointer_hand or (hands[0] if hands else hand)
            if target_h:
                tip = (int(target_h.landmarks_px[INDEX_TIP][0]), int(target_h.landmarks_px[INDEX_TIP][1]))
                self.draw_depth_push_indicator(frame, tip, air_tap_pct)

        # Holographic 3D Virtual Scroll Cylinder
        if abs(scroll_velocity) > 0.02 or gesture == GestureType.SCROLL or action_gesture == GestureType.SCROLL:
            target_h = action_hand if action_gesture == GestureType.SCROLL else (pointer_hand or (hands[0] if hands else hand))
            if target_h and hasattr(target_h, 'landmarks_px') and len(target_h.landmarks_px) > MIDDLE_MCP:
                pt = (int(target_h.landmarks_px[MIDDLE_MCP][0]), int(target_h.landmarks_px[MIDDLE_MCP][1]))
                self.draw_scroll_cylinder(frame, pt, scroll_velocity)

        # Holographic Auto-Calibration Countdown
        if calibration_progress is not None:
            self.draw_calibration_target(frame, progress_pct=calibration_progress)

        # Holographic 8-Sector Radial Menu Dial
        if radial_menu_active:
            self.draw_radial_hud(frame, active_sector=active_radial_sector)

        self.draw_ripples(frame)
        self.draw_slide_chevrons(frame)
        self.draw_rotary_dials(frame)
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
