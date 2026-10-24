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
    WRIST, THUMB_TIP, INDEX_MCP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP
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

        # Zoom Loupe holographic visual feedback queue
        self.zoom_feedbacks: List[Dict[str, any]] = []
        self.virtual_zoom_scale: float = 1.0

        # Spatial Air-Canvas Stream Annotator: list of strokes
        self.air_draw_strokes: List[Dict[str, any]] = []
        self.current_air_stroke: Optional[Dict[str, any]] = None

        # Kinetic velocity tracker & precision reticle
        self.prev_pointer_tip: Optional[Tuple[int, int]] = None
        self.prev_pointer_time: float = 0.0
        self.smoothed_velocity: float = 0.0
        self.velocity_vector: Tuple[float, float] = (0.0, 0.0)

        # Cached CPU percentage (polled every 0.5s to reduce overhead)
        self.last_cpu_check = 0.0
        self.cached_cpu = 0.0

        # Camera Shutter Flash visual effect
        self.shutter_flash_time: float = 0.0

        # Floating Media Capsule feedback
        self.last_media_action_time: float = 0.0
        self.media_action_icon: str = "PLAY"
        self.media_action_label: str = ""

        # Privacy Shield visual feedback
        self.privacy_shield_time: float = 0.0

    def trigger_privacy_shield(self):
        """Triggers the biometric privacy shield lockdown visual effect in HUD."""
        self.privacy_shield_time = time.time()

    def draw_privacy_shield(self, frame: np.ndarray):
        """Renders glowing biometric security lockdown shield when workstation is locked."""
        now = time.time()
        dt = now - self.privacy_shield_time
        if dt > 0.85:
            return

        h, w, _ = frame.shape
        alpha = min(0.85, (0.85 - dt) / 0.25)
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (10, 8, 15), -1)
        cv2.addWeighted(overlay, alpha * 0.70, frame, 1.0 - (alpha * 0.70), 0, frame)

        cx, cy = w // 2, h // 2
        r = int(55 + 10 * (1.0 - dt / 0.85))
        pts_hex = []
        for i in range(6):
            ang = math.radians(60 * i - 30)
            pts_hex.append((int(cx + r * math.cos(ang)), int(cy + r * math.sin(ang))))
        pts_hex = np.array(pts_hex, np.int32)
        cv2.polylines(frame, [pts_hex], True, (0, 242, 254), 2, cv2.LINE_AA)

        # Padlock graphic
        pw, ph = 24, 20
        cv2.rectangle(frame, (cx - pw // 2, cy - 2), (cx + pw // 2, cy + ph), (0, 242, 254), -1, cv2.LINE_AA)
        cv2.ellipse(frame, (cx, cy - 2), (8, 10), 0, 180, 360, (0, 242, 254), 2, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy + 7), 2, (18, 16, 24), -1, cv2.LINE_AA)

        # Banner text
        cv2.putText(frame, "WORKSTATION SECURED", (cx - 105, cy + ph + 28),
                    self.font_mono, 1.0, (255, 255, 255), 2, cv2.LINE_AA)

    def trigger_media_feedback(self, action: str, label: str):
        """Triggers the floating HUD media playback capsule."""
        self.last_media_action_time = time.time()
        self.media_action_icon = action.upper()
        self.media_action_label = label

    def draw_media_capsule(self, frame: np.ndarray):
        """Renders an Apple visionOS styled floating media playback capsule with animated audio spectrum."""
        now = time.time()
        dt = now - self.last_media_action_time
        if dt > 1.8:
            return

        h, w, _ = frame.shape
        alpha = min(1.0, (1.8 - dt) / 0.3)
        cw, ch = 240, 36
        cx = w // 2
        cy = 38

        x1, y1 = cx - cw // 2, cy - ch // 2
        x2, y2 = cx + cw // 2, cy + ch // 2

        # Semi-transparent pill background
        overlay = frame.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (20, 18, 25), -1)
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 242, 254), 1, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.75 * alpha, frame, 1.0 - (0.75 * alpha), 0, frame)

        # Equalizer spectrum animation (5 vertical bars)
        bar_x = x1 + 18
        for i in range(5):
            bar_phase = now * 12.0 + i * 1.3
            bar_height = int(6 + 8 * (0.5 + 0.5 * math.sin(bar_phase)))
            bx = bar_x + i * 5
            by1 = cy + ch // 4 - bar_height
            by2 = cy + ch // 4
            cv2.line(frame, (bx, by1), (bx, by2), (0, 242, 254), 2, cv2.LINE_AA)

        # Media Text
        text = f"{self.media_action_icon} : {self.media_action_label}"
        cv2.putText(frame, text, (x1 + 52, cy + 5), self.font_mono, 0.85, (255, 255, 255), 1, cv2.LINE_AA)

    def trigger_shutter_flash(self):
        """Triggers a camera shutter white-flash bloom animation across the HUD frame."""
        self.shutter_flash_time = time.time()

    def draw_shutter_flash(self, frame: np.ndarray):
        """Draws glowing camera shutter flash and viewfinder brackets."""
        now = time.time()
        dt = now - self.shutter_flash_time
        if dt > 0.40:
            return
        progress = dt / 0.40
        alpha = max(0.0, 1.0 - progress) * 0.70
        h, w, _ = frame.shape
        flash_overlay = np.full_like(frame, 255)
        cv2.addWeighted(flash_overlay, alpha, frame, 1.0 - alpha, 0, frame)

        # Camera viewfinder corner brackets
        vf_color = (0, 242, 254)
        c_len = 28
        pad = 20
        # Top-left
        cv2.line(frame, (pad, pad), (pad + c_len, pad), vf_color, 2, cv2.LINE_AA)
        cv2.line(frame, (pad, pad), (pad, pad + c_len), vf_color, 2, cv2.LINE_AA)
        # Top-right
        cv2.line(frame, (w - pad, pad), (w - pad - c_len, pad), vf_color, 2, cv2.LINE_AA)
        cv2.line(frame, (w - pad, pad), (w - pad, pad + c_len), vf_color, 2, cv2.LINE_AA)
        # Bottom-left
        cv2.line(frame, (pad, h - pad), (pad + c_len, h - pad), vf_color, 2, cv2.LINE_AA)
        cv2.line(frame, (pad, h - pad), (pad, h - pad - c_len), vf_color, 2, cv2.LINE_AA)
        # Bottom-right
        cv2.line(frame, (w - pad, h - pad), (w - pad - c_len, h - pad), vf_color, 2, cv2.LINE_AA)
        cv2.line(frame, (w - pad, h - pad), (w - pad, h - pad - c_len), vf_color, 2, cv2.LINE_AA)

        # Status text
        cv2.putText(frame, "AIR-SNAP CAPTURED", (w // 2 - 80, pad + 24),
                    self.font_mono, 1.0, (0, 242, 254), 2, cv2.LINE_AA)

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

    def trigger_zoom_feedback(self, px: Tuple[int, int], zoom_delta: int):
        """Spawns an optical magnifying zoom loupe HUD with live scale percentage."""
        self.virtual_zoom_scale = max(0.25, min(4.0, self.virtual_zoom_scale + (0.10 if zoom_delta > 0 else -0.10)))
        self.zoom_feedbacks.append({
            "x": px[0],
            "y": px[1],
            "delta": zoom_delta,
            "scale": self.virtual_zoom_scale,
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

    def draw_zoom_loupes(self, frame: np.ndarray):
        """Renders animated futuristic optical zoom loupe HUD around active hand coordinates."""
        if not self.zoom_feedbacks:
            return
        now = time.time()
        active = []
        h, w, _ = frame.shape

        for zf in self.zoom_feedbacks:
            elapsed = now - zf["created"]
            duration = 0.55
            if elapsed < duration:
                progress = elapsed / duration
                alpha = max(0.0, 1.0 - progress)
                zx, zy = int(zf["x"]), int(zf["y"])
                delta = zf["delta"]
                scale_pct = int(round(zf["scale"] * 100))

                # Color: Electric Cyan for Zoom In, Vibrant Orange/Coral for Zoom Out
                col = (0, 242, 254) if delta > 0 else (60, 120, 255)

                # Outer animated pulsating ring
                r = int(36 + 14 * progress) if delta > 0 else int(50 - 14 * progress)
                r = max(18, min(140, r))

                overlay = frame.copy()

                # Loupe glass ring
                cv2.circle(overlay, (zx, zy), r, col, 2, cv2.LINE_AA)
                cv2.circle(overlay, (zx, zy), max(4, r - 5), (255, 255, 255), 1, cv2.LINE_AA)

                # Precision crosshair tick marks (compass 4 directions)
                for angle_deg in (0, 90, 180, 270):
                    rad = math.radians(angle_deg)
                    p1 = (int(zx + (r - 7) * math.cos(rad)), int(zy + (r - 7) * math.sin(rad)))
                    p2 = (int(zx + (r + 7) * math.cos(rad)), int(zy + (r + 7) * math.sin(rad)))
                    cv2.line(overlay, p1, p2, col, 2, cv2.LINE_AA)

                # Direction symbol
                sym = "+" if delta > 0 else "-"
                cv2.putText(overlay, sym, (zx - 5, zy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

                # VisionOS Glass Pill for Zoom readout
                label = f"ZOOM {scale_pct}%"
                font = cv2.FONT_HERSHEY_SIMPLEX
                scale = 0.48
                thickness = 1
                (lw, lh), _ = cv2.getTextSize(label, font, scale, thickness)
                bx = max(10, min(w - lw - 24, zx - lw // 2 - 8))
                by = max(lh + 16, min(h - 16, zy + r + 24))

                cv2.rectangle(overlay, (bx, by - lh - 6), (bx + lw + 16, by + 6), (18, 14, 22), -1)
                cv2.rectangle(overlay, (bx, by - lh - 6), (bx + lw + 16, by + 6), col, 1, cv2.LINE_AA)
                cv2.putText(overlay, label, (bx + 8, by), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)

                cv2.addWeighted(overlay, alpha * 0.90, frame, 1.0 - (alpha * 0.90), 0, frame)
                active.append(zf)

        self.zoom_feedbacks = active

    def add_air_draw_point(self, pt: Tuple[int, int], color: Tuple[int, int, int]):
        """Appends a new point to the active air-drawing stroke."""
        if self.current_air_stroke is None:
            self.current_air_stroke = {"color": color, "points": [pt]}
            self.air_draw_strokes.append(self.current_air_stroke)
        else:
            last_pt = self.current_air_stroke["points"][-1]
            if math.hypot(pt[0] - last_pt[0], pt[1] - last_pt[1]) >= 3.0:
                self.current_air_stroke["points"].append(pt)

    def finish_air_draw_stroke(self):
        """Ends the active drawing stroke."""
        self.current_air_stroke = None

    def clear_air_canvas(self):
        """Clears all mid-air drawn strokes."""
        self.air_draw_strokes.clear()
        self.current_air_stroke = None

    def draw_air_canvas(self, frame: np.ndarray):
        """Renders glowing multi-colored spatial whiteboard strokes directly into video frame."""
        if not self.air_draw_strokes:
            return
        overlay = frame.copy()
        for stroke in self.air_draw_strokes:
            pts = stroke.get("points", [])
            col = stroke.get("color", (0, 242, 254))
            if len(pts) < 2:
                if len(pts) == 1:
                    cv2.circle(frame, pts[0], 3, col, -1, cv2.LINE_AA)
                continue
            # Outer neon glow
            for i in range(len(pts) - 1):
                cv2.line(overlay, pts[i], pts[i + 1], col, 5, cv2.LINE_AA)
            # Crisp white core
            for i in range(len(pts) - 1):
                cv2.line(frame, pts[i], pts[i + 1], (255, 255, 255), 2, cv2.LINE_AA)

        cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

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

    def draw_proximity_edge_glow(
        self,
        frame: np.ndarray,
        edge_flags: Tuple[bool, bool, bool, bool]
    ):
        """
        Renders tactile glowing edge bars and magnetic corner sparks when cursor hits screen borders.
        edge_flags: (left, top, right, bottom)
        """
        if not edge_flags or not any(edge_flags):
            return
        left, top, right, bottom = edge_flags
        h, w, _ = frame.shape
        col = (0, 242, 254)

        overlay = frame.copy()
        if left:
            cv2.rectangle(overlay, (0, 0), (8, h), col, -1)
        if right:
            cv2.rectangle(overlay, (w - 8, 0), (w, h), col, -1)
        if top:
            cv2.rectangle(overlay, (0, 0), (w, 8), col, -1)
        if bottom:
            cv2.rectangle(overlay, (0, h - 8), (w, h), col, -1)

        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

        # Draw magnetic snap spark if corner reached
        corners = [
            (left and top, (14, 14)),
            (right and top, (w - 14, 14)),
            (left and bottom, (14, h - 14)),
            (right and bottom, (w - 14, h - 14))
        ]
        for is_corner, (cx, cy) in corners:
            if is_corner:
                cv2.circle(frame, (cx, cy), 6, (255, 255, 255), -1, cv2.LINE_AA)
                cv2.circle(frame, (cx, cy), 12, col, 2, cv2.LINE_AA)
                cv2.line(frame, (cx - 16, cy), (cx + 16, cy), (255, 255, 255), 1, cv2.LINE_AA)
                cv2.line(frame, (cx, cy - 16), (cx, cy + 16), (255, 255, 255), 1, cv2.LINE_AA)

    def draw_window_snap_preview(
        self,
        frame: np.ndarray,
        snap_zone: Optional[str]
    ):
        """
        Renders futuristic translucent visionOS holographic window snap preview drop zone
        when dragging an active window towards screen borders.
        snap_zone: 'left', 'right', 'top', 'bottom', or None
        """
        if not snap_zone:
            return
        h, w, _ = frame.shape
        overlay = frame.copy()

        # Zone geometry and labels
        if snap_zone == 'left':
            x1, y1, x2, y2 = 8, 8, int(w * 0.48), h - 8
            title = "SNAP LEFT (50%)"
            color = (255, 180, 0) # Electric cyan/blue
        elif snap_zone == 'right':
            x1, y1, x2, y2 = int(w * 0.52), 8, w - 8, h - 8
            title = "SNAP RIGHT (50%)"
            color = (255, 180, 0) # Electric cyan/blue
        elif snap_zone == 'top':
            x1, y1, x2, y2 = 8, 8, w - 8, h - 8
            title = "SNAP MAXIMIZE (100%)"
            color = (0, 242, 254) # Radiant teal
        elif snap_zone == 'bottom':
            x1, y1, x2, y2 = int(w * 0.25), int(h * 0.65), int(w * 0.75), h - 8
            title = "SNAP MINIMIZE"
            color = (200, 100, 255) # Lavender
        else:
            return

        # Semi-transparent frosted fill
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
        cv2.addWeighted(overlay, 0.22, frame, 0.78, 0, frame)

        # Crisp glowing perimeter border with inner highlight
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
        cv2.rectangle(frame, (x1 + 3, y1 + 3), (x2 - 3, y2 - 3), (255, 255, 255), 1, cv2.LINE_AA)

        # Holographic Glass Badge in center of preview
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        bw, bh = 170, 32
        bx1, by1 = max(0, cx - bw // 2), max(0, cy - bh // 2)
        bx2, by2 = min(w, cx + bw // 2), min(h, cy + bh // 2)

        badge_overlay = frame.copy()
        cv2.rectangle(badge_overlay, (bx1, by1), (bx2, by2), (20, 22, 28), -1)
        cv2.addWeighted(badge_overlay, 0.80, frame, 0.20, 0, frame)
        cv2.rectangle(frame, (bx1, by1), (bx2, by2), color, 1, cv2.LINE_AA)

        # Badge text
        cv2.putText(frame, title, (bx1 + 12, by1 + 21), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

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

        # Dynamic 3D Perspective Depth Scaling based on physical distance
        dist_val = getattr(hand, 'estimated_distance_cm', 50.0)
        depth_scale = max(0.65, min(1.65, 50.0 / max(22.0, dist_val)))
        bone_thick = max(1, int(round(2 * depth_scale)))
        tip_r = max(4, int(round(6 * depth_scale)))
        joint_r = max(2, int(round(3 * depth_scale)))
        shadow_dx = max(1, int(round(2 * depth_scale)))
        shadow_dy = max(2, int(round(3 * depth_scale)))

        # 1. Perspective Depth Drop Shadow (creates floating spatial 3D effect)
        for p1_idx, p2_idx in HAND_CONNECTIONS:
            pt1 = (pts[p1_idx][0] + shadow_dx, pts[p1_idx][1] + shadow_dy)
            pt2 = (pts[p2_idx][0] + shadow_dx, pts[p2_idx][1] + shadow_dy)
            cv2.line(frame, pt1, pt2, (10, 8, 14), bone_thick + 1, cv2.LINE_AA)

        # 2. Glowing Optical Bones
        for p1_idx, p2_idx in HAND_CONNECTIONS:
            pt1 = (pts[p1_idx][0], pts[p1_idx][1])
            pt2 = (pts[p2_idx][0], pts[p2_idx][1])
            cv2.line(frame, pt1, pt2, bone_col, bone_thick, cv2.LINE_AA)

        # 3. Floating 3D Joints & Specular Photon Reflections
        for idx, pt in enumerate(pts):
            coord = (pt[0], pt[1])
            is_tip = idx in (THUMB_TIP, INDEX_TIP, MIDDLE_TIP)

            if is_tip:
                # Shadow
                cv2.circle(frame, (coord[0] + shadow_dx, coord[1] + shadow_dy), tip_r, (10, 8, 14), -1, cv2.LINE_AA)
                # Colored core orb
                cv2.circle(frame, coord, tip_r, tip_col, -1, cv2.LINE_AA)
                # Outer photon halo
                cv2.circle(frame, coord, tip_r + 3, self.config.COLOR_WHITE, 1, cv2.LINE_AA)
                # Specular optical glint
                cv2.circle(frame, (coord[0] - 1, coord[1] - 1), max(1, tip_r // 3), (255, 255, 255), -1, cv2.LINE_AA)
            else:
                cv2.circle(frame, coord, joint_r, bone_col, -1, cv2.LINE_AA)
                cv2.circle(frame, coord, max(1, joint_r - 1), (255, 255, 255), -1, cv2.LINE_AA)

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

        # visionOS Holographic Smart Watch Widget anchored to wrist
        self.draw_wrist_holographic_clock(frame, hand)

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

        # Spatial Air-Ruler Vernier Caliper
        if getattr(self.config, 'enable_spatial_air_ruler', False):
            palm_px = getattr(hand, 'palm_size_px', 65.0)
            self.draw_spatial_air_ruler(frame, thumb_pt, index_pt, palm_size_px=palm_px)

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

        if getattr(self.config, 'enable_air_piano', False):
            self.draw_air_piano_keys(frame, hand)

    def draw_air_piano_keys(self, frame: np.ndarray, hand: HandData, active_notes: Optional[List[str]] = None):
        """
        Renders 5 floating neon holographic pentatonic synthesizer keys over the 5 fingertips.
        """
        pts = hand.landmarks_px
        h, w, _ = frame.shape
        tips = [
            (THUMB_TIP, "C4", "C"),
            (INDEX_TIP, "D4", "D"),
            (MIDDLE_TIP, "E4", "E"),
            (RING_TIP, "G4", "G"),
            (PINKY_TIP, "A4", "A")
        ]
        active_set = set(active_notes or [])

        overlay = frame.copy()
        for tip_idx, note_id, note_lbl in tips:
            pt = pts[tip_idx]
            fx, fy = int(pt[0]), int(pt[1])
            ky = max(18, fy - 24)
            is_active = note_id in active_set

            rw, rh = 12, 10
            x1, y1 = max(0, fx - rw), max(0, ky - rh)
            x2, y2 = min(w, fx + rw), min(h, ky + rh)

            col = (255, 0, 128) if is_active else (0, 242, 254)
            bg_col = (255, 100, 200) if is_active else (25, 20, 35)

            cv2.rectangle(overlay, (x1, y1), (x2, y2), bg_col, -1)
            cv2.rectangle(overlay, (x1, y1), (x2, y2), col, 1, cv2.LINE_AA)
            cv2.line(frame, (fx, fy), (fx, ky + rh), col, 1, cv2.LINE_AA)

        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

        for tip_idx, note_id, note_lbl in tips:
            pt = pts[tip_idx]
            fx, fy = int(pt[0]), int(pt[1])
            ky = max(18, fy - 24)
            is_active = note_id in active_set
            txt_col = (255, 255, 255) if is_active else (0, 242, 254)
            cv2.putText(frame, note_lbl, (fx - 4, ky + 4), self.font_mono, 0.85, txt_col, 1, cv2.LINE_AA)

    def draw_spatial_air_ruler(
        self,
        frame: np.ndarray,
        pt1: Tuple[int, int],
        pt2: Tuple[int, int],
        palm_size_px: float = 65.0
    ):
        """
        Renders a futuristic holographic vernier caliper ruler between two mid-air points
        with millimeter tick marks, reticles, and real-world distance estimation.
        """
        dx = float(pt2[0] - pt1[0])
        dy = float(pt2[1] - pt1[1])
        dist_px = math.hypot(dx, dy)
        if dist_px < 6.0:
            return

        ux = dx / dist_px
        uy = dy / dist_px
        px = -uy
        py = ux

        h, w, _ = frame.shape
        col = (0, 242, 254)

        # Main caliper beam
        cv2.line(frame, pt1, pt2, col, 1, cv2.LINE_AA)

        # End crosshairs
        for p in (pt1, pt2):
            cv2.circle(frame, p, 3, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, p, 6, col, 1, cv2.LINE_AA)

        # Vernier Caliper Tick Marks
        step_px = 12.0
        num_ticks = int(dist_px // step_px)
        for i in range(1, num_ticks):
            tx = pt1[0] + ux * (i * step_px)
            ty = pt1[1] + uy * (i * step_px)
            tick_len = 7.0 if (i % 3 == 0) else 4.0
            x_end = int(tx + px * tick_len)
            y_end = int(ty + py * tick_len)
            cv2.line(frame, (int(tx), int(ty)), (x_end, y_end), col, 1, cv2.LINE_AA)

        # Metric estimation: adult palm width ~8.5cm
        cm_est = (dist_px / max(10.0, palm_size_px)) * 8.5
        label = f"{int(dist_px)}px | {cm_est:.1f}cm"

        mx = int((pt1[0] + pt2[0]) / 2 + px * 16)
        my = int((pt1[1] + pt2[1]) / 2 + py * 16)
        mx = max(40, min(w - 70, mx))
        my = max(18, min(h - 18, my))

        tw, th = 84, 18
        x1, y1 = mx - tw // 2, my - th // 2
        x2, y2 = mx + tw // 2, my + th // 2
        overlay = frame.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (18, 16, 24), -1)
        cv2.rectangle(overlay, (x1, y1), (x2, y2), col, 1, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)
        cv2.putText(frame, label, (x1 + 6, my + 4), self.font_mono, 0.75, (255, 255, 255), 1, cv2.LINE_AA)

    def draw_wrist_holographic_clock(self, frame: np.ndarray, hand: HandData):
        """
        Renders an Apple visionOS styled floating holographic smart watch widget
        anchored directly beside the wrist joint in mid-air.
        """
        if not getattr(self.config, 'show_wrist_hud_clock', True):
            return

        pts = hand.landmarks_px
        h, w, _ = frame.shape
        wrist = pts[WRIST]
        wx, wy = int(wrist[0]), int(wrist[1])

        # Position watch to the side of the wrist
        handedness = getattr(hand, 'handedness', 'Right')
        offset_x = -56 if handedness == 'Right' else 56
        offset_y = -10
        cx = wx + offset_x
        cy = wy + offset_y

        # Clamp within frame margins
        r = 26
        cx = max(r + 6, min(w - r - 6, cx))
        cy = max(r + 6, min(h - r - 6, cy))

        # 1. Subtle glowing tether line connecting wrist joint to floating timepiece
        cv2.line(frame, (wx, wy), (cx, cy), (0, 242, 254), 1, cv2.LINE_AA)
        cv2.circle(frame, (wx, wy), 2, (0, 242, 254), -1, cv2.LINE_AA)

        # 2. Translucent VisionOS Glass Watch Bezel
        overlay = frame.copy()
        cv2.circle(overlay, (cx, cy), r, (18, 16, 24), -1)
        cv2.circle(overlay, (cx, cy), r, (0, 242, 254), 1, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)

        # 3. Seconds Progress Arc along perimeter
        now_ts = time.time()
        sec_frac = (now_ts % 60.0) / 60.0
        end_angle = int(sec_frac * 360)
        cv2.ellipse(frame, (cx, cy), (r - 2, r - 2), -90, 0, end_angle, (0, 242, 254), 2, cv2.LINE_AA)

        # 4. Digital Time Display (HH:MM)
        timestr = time.strftime("%H:%M")
        cv2.putText(frame, timestr, (cx - 16, cy + 3), cv2.FONT_HERSHEY_PLAIN, 0.75, (255, 255, 255), 1, cv2.LINE_AA)

        # 5. Seconds sub-tag
        sec_str = time.strftime("%S")
        cv2.putText(frame, sec_str, (cx - 7, cy + 13), cv2.FONT_HERSHEY_PLAIN, 0.55, (0, 242, 254), 1, cv2.LINE_AA)

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
        """Draws bottom-right real-time Jitter Attenuation graph with zero full-frame copying."""
        if len(self.raw_history) < 2:
            return

        h, w, _ = frame.shape
        chart_w = 190
        chart_h = 60
        chart_x = w - chart_w - 14
        chart_y = h - chart_h - 28

        if chart_x < 0 or chart_y < 0 or (chart_x + chart_w) > w or (chart_y + chart_h) > h:
            return

        # Local ROI clipping to avoid copying full 640x480 buffer
        roi = frame[chart_y:chart_y + chart_h, chart_x:chart_x + chart_w]
        overlay_roi = roi.copy()
        cv2.rectangle(overlay_roi, (0, 0), (chart_w, chart_h), (12, 10, 16), -1)
        cv2.addWeighted(overlay_roi, 0.72, roi, 0.28, 0, roi)
        cv2.rectangle(frame, (chart_x, chart_y), (chart_x + chart_w, chart_y + chart_h), (60, 50, 75), 1, cv2.LINE_AA)

        # Label & legend
        cv2.putText(frame, "1-EURO ATTENUATION", (chart_x + 6, chart_y - 6),
                    self.font_mono, 0.70, (0, 242, 254), 1, cv2.LINE_AA)

        # Scale data
        raw_arr = np.array(self.raw_history, dtype=np.float32)
        ema_arr = np.array(self.ema_history, dtype=np.float32)
        min_v = min(raw_arr.min(), ema_arr.min())
        max_v = max(raw_arr.max(), ema_arr.max())
        val_range = max(1.0, max_v - min_v)

        def val_to_y(val):
            norm = (val - min_v) / val_range
            return int(chart_y + chart_h - 5 - norm * (chart_h - 10))

        step_x = chart_w / float(self.max_chart_points - 1)

        # Draw raw noisy signal (Magenta/Red, 1px)
        for i in range(len(raw_arr) - 1):
            x1 = int(chart_x + i * step_x)
            y1 = val_to_y(raw_arr[i])
            x2 = int(chart_x + (i + 1) * step_x)
            y2 = val_to_y(raw_arr[i + 1])
            cv2.line(frame, (x1, y1), (x2, y2), (60, 60, 255), 1, cv2.LINE_AA)

        # Draw filtered signal (Cyan core, 2px)
        for i in range(len(ema_arr) - 1):
            x1 = int(chart_x + i * step_x)
            y1 = val_to_y(ema_arr[i])
            x2 = int(chart_x + (i + 1) * step_x)
            y2 = val_to_y(ema_arr[i + 1])
            cv2.line(frame, (x1, y1), (x2, y2), (0, 242, 254), 2, cv2.LINE_AA)

    def draw_ergonomic_alert(self, frame: np.ndarray, minutes_active: int):
        """Renders subtle frosted glass reminder to lower hands and rest forearm."""
        h, w, _ = frame.shape
        bw = 360
        bh = 30
        bx = w // 2 - bw // 2
        by = h - bh - 18

        if bx < 0 or by < 0 or (bx + bw) > w or (by + bh) > h:
            return

        roi = frame[by:by + bh, bx:bx + bw]
        overlay_roi = roi.copy()
        cv2.rectangle(overlay_roi, (0, 0), (bw, bh), (14, 18, 14), -1)
        cv2.addWeighted(overlay_roi, 0.75, roi, 0.25, 0, roi)
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (50, 200, 100), 1, cv2.LINE_AA)

        msg = f"REST FOREARM ({minutes_active}m continuous elevation)"
        cv2.putText(frame, msg, (bx + 16, by + 20), cv2.FONT_HERSHEY_PLAIN, 0.85, (160, 255, 180), 1, cv2.LINE_AA)

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

        l_col_name = getattr(self.config, 'laser_color', 'cyan').lower()
        if is_clicking:
            beam_color = (50, 50, 255) # Red on click
            glow_color = (80, 80, 255)
        elif l_col_name == "green":
            beam_color = (0, 240, 100) # Emerald green
            glow_color = (0, 230, 80)
        elif l_col_name == "red":
            beam_color = (50, 60, 255) # Crimson plasma
            glow_color = (80, 80, 255)
        elif l_col_name == "gold":
            beam_color = (0, 215, 255) # Solar gold
            glow_color = (40, 190, 255)
        else:
            beam_color = (0, 242, 254) # Electric cyan
            glow_color = (0, 180, 255)

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
        tip_pt = (int(tip[0]), int(tip[1]))
        cv2.line(overlay, tip_pt, (tx, ty), glow_color, 5, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

        # 2. Core crisp laser beam
        cv2.line(frame, tip_pt, (tx, ty), (255, 255, 255), 1, cv2.LINE_AA)
        cv2.circle(frame, tip_pt, 3, (255, 255, 255), -1, cv2.LINE_AA)

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

    def draw_presentation_spotlight(
        self,
        frame: np.ndarray,
        center_pt: Tuple[int, int],
        radius: int = 85,
        dim_opacity: float = 0.65
    ):
        """
        Renders Keynote-style presentation spotlight. Dims the background frame
        while cutting out a bright, high-contrast circular aperture with glowing boundary rim.
        """
        h, w, _ = frame.shape
        cx, cy = int(center_pt[0]), int(center_pt[1])
        radius = max(30, min(min(h, w) // 2, int(radius)))

        # 1. Dimmed version of frame
        dimmed = (frame * (1.0 - dim_opacity)).astype(np.uint8)

        # 2. Circular mask
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask, (cx, cy), radius, 255, -1)

        # 3. Soften the edge of the spotlight mask for natural vignette falloff
        mask_feathered = cv2.GaussianBlur(mask, (21, 21), 0)
        mask_norm = (mask_feathered.astype(np.float32) / 255.0)[:, :, np.newaxis]

        # 4. Blend: spotlight area gets original frame, outside gets dimmed frame
        np.copyto(frame, (frame * mask_norm + dimmed * (1.0 - mask_norm)).astype(np.uint8))

        # 5. Glowing cyan boundary ring around spotlight
        cv2.circle(frame, (cx, cy), radius, (0, 242, 254), 2, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), radius + 2, (255, 255, 255), 1, cv2.LINE_AA)

        # 6. Center precision crosshair
        cv2.circle(frame, (cx, cy), 4, (0, 242, 254), -1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), 2, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.line(frame, (cx - 10, cy), (cx + 10, cy), (0, 242, 254), 1, cv2.LINE_AA)
        cv2.line(frame, (cx, cy - 10), (cx, cy + 10), (0, 242, 254), 1, cv2.LINE_AA)

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

        if velocity >= 120.0:
            # Kinetic high-speed tracking: dynamic motion vector streak + speed badge
            norm = math.hypot(vec[0], vec[1])
            vel_col = (255, 0, 128) if velocity >= 450.0 else ((0, 215, 255) if velocity >= 250.0 else (0, 242, 254))
            if norm > 1.0:
                streak_len = min(36, int(norm * 0.035))
                tx = int(ix - (vec[0] / norm) * streak_len)
                ty = int(iy - (vec[1] / norm) * streak_len)
                cv2.line(frame, (ix, iy), (tx, ty), vel_col, 2, cv2.LINE_AA)
                cv2.circle(frame, (ix, iy), 3, (255, 255, 255), -1, cv2.LINE_AA)

            badge_text = f"{int(velocity)} px/s"
            bx = max(10, min(w - 95, ix + 14))
            by = max(18, min(h - 10, iy - 8))
            cv2.putText(frame, badge_text, (bx, by), cv2.FONT_HERSHEY_PLAIN, 0.85, vel_col, 1, cv2.LINE_AA)

        elif velocity <= 80.0:
            # Micro-Precision Stabilization reticle
            cv2.circle(frame, index_pt, 10, (0, 242, 254), 1, cv2.LINE_AA)
            cv2.line(frame, (ix - 14, iy), (ix - 6, iy), (0, 242, 254), 1, cv2.LINE_AA)
            cv2.line(frame, (ix + 6, iy), (ix + 14, iy), (0, 242, 254), 1, cv2.LINE_AA)
            cv2.line(frame, (ix, iy - 14), (ix, iy - 6), (0, 242, 254), 1, cv2.LINE_AA)
            cv2.line(frame, (ix, iy + 6), (ix, iy + 14), (0, 242, 254), 1, cv2.LINE_AA)
            cv2.circle(frame, index_pt, 2, (255, 255, 255), -1, cv2.LINE_AA)

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

    def draw_spatial_depth_gauge(self, frame: np.ndarray, distance_cm: float):
        """Renders a sleek visionOS-style vertical depth tape on the frame margin."""
        h, w, _ = frame.shape
        gw = 12
        gh = 130
        gx = w - gw - 14
        gy = h // 2 - gh // 2

        overlay = frame.copy()
        # Glass backdrop capsule
        cv2.rectangle(overlay, (gx - 4, gy - 16), (gx + gw + 4, gy + gh + 16), (14, 12, 18), -1)
        cv2.rectangle(overlay, (gx - 4, gy - 16), (gx + gw + 4, gy + gh + 16), (60, 50, 70), 1, cv2.LINE_AA)

        # Optimal range highlight bracket: 35cm to 75cm
        min_d, max_d = 20.0, 110.0
        opt_top = gy + int(gh * (35.0 - min_d) / (max_d - min_d))
        opt_bot = gy + int(gh * (75.0 - min_d) / (max_d - min_d))
        cv2.rectangle(overlay, (gx, opt_top), (gx + gw, opt_bot), (0, 180, 100), -1)

        # Distance indicator pip
        clamped_d = max(min_d, min(max_d, distance_cm))
        pip_y = gy + int(gh * (clamped_d - min_d) / (max_d - min_d))

        # Color based on zone
        if 35.0 <= distance_cm <= 75.0:
            pip_col = (0, 242, 254)   # Cyan (Sweet spot)
        elif distance_cm < 35.0:
            pip_col = (50, 80, 255)   # Coral warning (too close)
        else:
            pip_col = (255, 100, 200) # Lavender warning (too far)

        cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)

        # Pip line & circle
        cv2.circle(frame, (gx + gw // 2, pip_y), 4, pip_col, -1, cv2.LINE_AA)
        cv2.circle(frame, (gx + gw // 2, pip_y), 6, (255, 255, 255), 1, cv2.LINE_AA)

        # Labels
        cv2.putText(frame, "DEPTH", (gx - 10, gy - 4), cv2.FONT_HERSHEY_PLAIN, 0.65, (180, 180, 180), 1, cv2.LINE_AA)
        cv2.putText(frame, f"{int(distance_cm)}cm", (gx - 10, gy + gh + 13), cv2.FONT_HERSHEY_PLAIN, 0.70, pip_col, 1, cv2.LINE_AA)

    def draw_tracking_confidence_meter(
        self,
        frame: np.ndarray,
        confidence_pct: float
    ):
        """
        Renders a 5-bar LED VU meter indicating real-time neural network tracking confidence.
        Green/Cyan (>85%), Amber/Gold (60-85%), Coral (<60%).
        """
        h, w, _ = frame.shape
        mx = w - 165
        my = 18
        bw = 145
        bh = 22

        overlay = frame.copy()
        cv2.rectangle(overlay, (mx, my), (mx + bw, my + bh), (15, 18, 24), -1)
        cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)
        cv2.rectangle(frame, (mx, my), (mx + bw, my + bh), (60, 65, 75), 1, cv2.LINE_AA)

        # Label
        cv2.putText(frame, "SIG", (mx + 8, my + 15), cv2.FONT_HERSHEY_PLAIN, 0.8, (200, 200, 200), 1, cv2.LINE_AA)

        # 5 LED segments
        num_bars = 5
        active_bars = max(0, min(5, int(round((confidence_pct / 100.0) * num_bars))))
        bx_start = mx + 42
        bar_w = 14
        bar_gap = 4
        bar_h = 10
        bar_y = my + 6

        if confidence_pct >= 85.0:
            fill_col = (0, 242, 254)  # Cyan
        elif confidence_pct >= 60.0:
            fill_col = (0, 215, 255)  # Gold
        else:
            fill_col = (60, 60, 255)  # Coral

        for b in range(num_bars):
            bx = bx_start + b * (bar_w + bar_gap)
            if b < active_bars:
                cv2.rectangle(frame, (bx, bar_y), (bx + bar_w, bar_y + bar_h), fill_col, -1)
            else:
                cv2.rectangle(frame, (bx, bar_y), (bx + bar_w, bar_y + bar_h), (35, 38, 45), -1)

        # Readout text
        pct_text = f"{int(confidence_pct)}%"
        cv2.putText(frame, pct_text, (mx + bw - 28, my + 15), cv2.FONT_HERSHEY_PLAIN, 0.70, fill_col, 1, cv2.LINE_AA)

    def draw_virtual_touch_plane(
        self,
        frame: np.ndarray,
        hand: Optional[HandData] = None,
        is_touching: bool = False
    ):
        """
        Renders a futuristic holographic 3D perspective grid plane in the lower frame,
        with joint drop-shadow projection lines and surface ripple on touch contact.
        """
        h, w, _ = frame.shape
        horizon_y = int(h * 0.65)
        plane_bot_y = h - 6

        # Translucent perspective grid
        overlay = frame.copy()
        grid_col = (0, 242, 254) if is_touching else (140, 150, 165)

        # Draw horizontal depth lines
        for step in [0.0, 0.25, 0.55, 0.82, 1.0]:
            ly = int(horizon_y + step * (plane_bot_y - horizon_y))
            half_w = int((w * 0.35) + step * (w * 0.60))
            x1 = max(0, w // 2 - half_w)
            x2 = min(w, w // 2 + half_w)
            cv2.line(overlay, (x1, ly), (x2, ly), grid_col, 1, cv2.LINE_AA)

        # Draw converging perspective lines toward center vanishing point
        vanish_x, vanish_y = w // 2, int(horizon_y * 0.70)
        for fx in [-0.45, -0.22, 0.0, 0.22, 0.45]:
            bx = int(w // 2 + fx * w)
            cv2.line(overlay, (vanish_x, vanish_y), (bx, plane_bot_y), grid_col, 1, cv2.LINE_AA)

        alpha = 0.35 if not is_touching else 0.55
        cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0, frame)

        # Draw glowing horizon line
        cv2.line(frame, (int(w * 0.15), horizon_y), (int(w * 0.85), horizon_y), grid_col, 1, cv2.LINE_AA)

        # Drop line from index fingertip to virtual plane
        if hand and hasattr(hand, 'landmarks_px') and len(hand.landmarks_px) > INDEX_TIP:
            tx, ty = int(hand.landmarks_px[INDEX_TIP][0]), int(hand.landmarks_px[INDEX_TIP][1])
            proj_y = max(horizon_y, min(plane_bot_y, ty + 35))
            cv2.line(frame, (tx, ty), (tx, proj_y), (255, 255, 255), 1, cv2.LINE_AA)
            cv2.circle(frame, (tx, proj_y), 4, grid_col, -1, cv2.LINE_AA)
            if is_touching:
                cv2.circle(frame, (tx, proj_y), 16, (0, 242, 254), 2, cv2.LINE_AA)
                cv2.circle(frame, (tx, proj_y), 26, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(frame, "TOUCH SURFACE", (tx + 12, proj_y + 4), cv2.FONT_HERSHEY_PLAIN, 0.75, (0, 242, 254), 1, cv2.LINE_AA)

    def draw_screen_magnifier_pip(
        self,
        frame: np.ndarray,
        loupe_img: np.ndarray,
        tip_pt: Tuple[int, int]
    ):
        """
        Embeds the circular magnified screen patch next to the user's cursor tip in the HUD.
        Features a glowing visionOS glass border, 2.0x label, and specular ring.
        """
        fh, fw, _ = frame.shape
        lh, lw, _ = loupe_img.shape
        tx, ty = int(tip_pt[0]), int(tip_pt[1])

        # Position loupe offset to top-right of finger tip (or top-left if near right edge)
        lx = tx + 35 if (tx + 35 + lw) < fw else tx - lw - 35
        ly = ty - lh // 2
        lx = max(8, min(fw - lw - 8, lx))
        ly = max(8, min(fh - lh - 8, ly))

        # Create circular mask for loupe
        mask = np.zeros((lh, lw), dtype=np.uint8)
        cr = min(lh, lw) // 2 - 2
        cv2.circle(mask, (lw // 2, lh // 2), cr, 255, -1)

        # Blend circular loupe onto frame
        roi = frame[ly:ly + lh, lx:lx + lw]
        mask_3c = cv2.merge([mask, mask, mask]) / 255.0
        blended = (loupe_img * mask_3c + roi * (1.0 - mask_3c)).astype(np.uint8)
        frame[ly:ly + lh, lx:lx + lw] = blended

        # Glowing cyan border
        cv2.circle(frame, (lx + lw // 2, ly + lh // 2), cr, (0, 242, 254), 2, cv2.LINE_AA)
        cv2.circle(frame, (lx + lw // 2, ly + lh // 2), cr + 2, (255, 255, 255), 1, cv2.LINE_AA)

        # Connector tether line from finger tip to loupe rim
        tether_x = lx + 8 if lx > tx else lx + lw - 8
        cv2.line(frame, (tx, ty), (tether_x, ly + lh // 2), (0, 242, 254), 1, cv2.LINE_AA)
        cv2.circle(frame, (tx, ty), 3, (0, 242, 254), -1, cv2.LINE_AA)

        # 2.0X Badge
        cv2.putText(frame, "2.0X LOUPE", (lx + 10, ly + 14), cv2.FONT_HERSHEY_PLAIN, 0.70, (0, 242, 254), 1, cv2.LINE_AA)

    def draw_color_temperature_badge(self, frame: np.ndarray, kelvin: int):
        """Renders ambient color temperature indicator in Kelvin (Warm / Neutral / Cool)."""
        h, w, _ = frame.shape
        x, y = 14, 44
        if kelvin < 3500:
            status = "WARM"
            col = (0, 165, 255)
        elif kelvin > 6500:
            status = "COOL"
            col = (255, 200, 100)
        else:
            status = "NEUTRAL"
            col = (0, 242, 254)

        badge_txt = f"{kelvin}K {status}"
        cv2.putText(frame, badge_txt, (x, y), cv2.FONT_HERSHEY_PLAIN, 0.75, col, 1, cv2.LINE_AA)

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
        scroll_velocity: float = 0.0,
        edge_snap_flags: Optional[Tuple[bool, bool, bool, bool]] = None,
        ergonomic_minutes: Optional[int] = None,
        snap_zone: Optional[str] = None,
        spotlight_mode: bool = False,
        spotlight_radius: int = 85,
        confidence_pct: Optional[float] = None,
        virtual_surface_mode: bool = False,
        virtual_surface_touch: bool = False,
        loupe_img: Optional[np.ndarray] = None,
        color_temp_kelvin: Optional[int] = None
    ) -> np.ndarray:
        """Clean rendering for GUI stream: draws distinct glowing skeletons for both hands."""
        if color_temp_kelvin is not None:
            self.draw_color_temperature_badge(frame, color_temp_kelvin)
        if virtual_surface_mode:
            target_h = pointer_hand or (hands[0] if hands else hand)
            self.draw_virtual_touch_plane(frame, hand=target_h, is_touching=virtual_surface_touch)

        if loupe_img is not None:
            target_h = pointer_hand or (hands[0] if hands else hand)
            if target_h and hasattr(target_h, 'landmarks_px') and len(target_h.landmarks_px) > INDEX_TIP:
                tip = (int(target_h.landmarks_px[INDEX_TIP][0]), int(target_h.landmarks_px[INDEX_TIP][1]))
                self.draw_screen_magnifier_pip(frame, loupe_img, tip)

        if confidence_pct is not None and confidence_pct > 0.0:
            self.draw_tracking_confidence_meter(frame, confidence_pct)
        # Keynote Presentation Spotlight Vignette Dimming
        if spotlight_mode:
            target_h = pointer_hand or (hands[0] if hands else hand)
            if target_h and hasattr(target_h, 'landmarks_px') and len(target_h.landmarks_px) > INDEX_TIP:
                tip = (int(target_h.landmarks_px[INDEX_TIP][0]), int(target_h.landmarks_px[INDEX_TIP][1]))
                self.draw_presentation_spotlight(frame, tip, radius=spotlight_radius)

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

        if edge_snap_flags:
            self.draw_proximity_edge_glow(frame, edge_snap_flags)

        # Spatial 3D Distance Depth Gauge Tape
        active_target = pointer_hand or (hands[0] if hands else hand)
        if active_target is not None:
            dist_val = getattr(active_target, 'estimated_distance_cm', 50.0)
            if dist_val > 0.0:
                self.draw_spatial_depth_gauge(frame, dist_val)

        if getattr(self.config, 'show_jitter_graph', False):
            self.draw_jitter_chart(frame)

        self.draw_air_canvas(frame)
        self.draw_window_snap_preview(frame, snap_zone)
        self.draw_ripples(frame)
        self.draw_slide_chevrons(frame)
        self.draw_rotary_dials(frame)
        self.draw_zoom_loupes(frame)
        if ergonomic_minutes is not None and ergonomic_minutes >= 20:
            self.draw_ergonomic_alert(frame, ergonomic_minutes)
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
        self.draw_shutter_flash(frame)
        self.draw_media_capsule(frame)
        self.draw_privacy_shield(frame)
        return frame
