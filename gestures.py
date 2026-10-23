"""
Gesture Recognition & Mathematical Engine
=========================================
Implements:
1. Euclidean distance and Palm Scale normalization - Slide 12
2. Joint angle calculation via Cosine theorem - Slide 12
3. Thumb Flexion / Bend Click Detection (сгиб большого пальца)
4. Blended DIP/TIP landmark tracking for rock-solid cursor stability
5. Gesture Vocabulary State Machine (Hover, Thumb Bend Click, Pinch, Right Click, Scroll, Drag, Pause)
6. Live proximity metrics for UI gauges
7. Debounce and Hysteresis protection
"""

import time
import math
import numpy as np
from enum import Enum
from typing import List, Tuple, Dict, Optional

from config import GestureConfig
from hand_tracker import (
    HandData,
    WRIST,
    THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP,
    INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP,
    MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP,
    RING_MCP, RING_PIP, RING_DIP, RING_TIP,
    PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP,
)


class GestureType(Enum):
    NONE = "NO HAND"
    HOVER = "HOVER (MOVE)"                  # ☝️ Index pointing
    THUMB_CLICK = "THUMB BEND (LEFT CLICK)" # 👍 Сгиб большого пальца
    PINCH_CLICK = "PINCH (LEFT CLICK)"       # 🤏 Thumb + Index
    PINCH = "PINCH (LEFT CLICK)"             # Alias for backward compatibility
    RIGHT_CLICK = "RIGHT CLICK"              # 👌 Thumb + Middle
    MIDDLE_CLICK = "MIDDLE CLICK (WHEEL)"    # 🔘 Thumb + Ring (Безымянный - колесико)
    TASK_SWITCH = "TASK SWITCH (WIN+TAB)"    # 🪟 Thumb + Pinky (Мизинец - окна)
    ROCK_ALT_TAB = "QUICK ALT+TAB"           # 🤘 Rock pose (Index + Pinky)
    SHAKA_DESKTOP = "SHOW DESKTOP (WIN+D)"   # 🤙 Shaka pose (Thumb + Pinky)
    SCROLL = "SCROLL"                        # ✌️ Index + Middle (V-sign)
    DRAG = "DRAG & DROP"                     # ✊ Closed fist
    PAUSE = "PAUSE (NEUTRAL)"                # 🖐️ Open palm safety mode


def calc_euclidean_distance(pt1: Tuple[float, ...], pt2: Tuple[float, ...]) -> float:
    """3D Euclidean distance invariant to hand rotation and perspective foreshortening."""
    dx = pt2[0] - pt1[0]
    dy = pt2[1] - pt1[1]
    dz = pt2[2] - pt1[2] if len(pt1) > 2 and len(pt2) > 2 else 0.0
    return float(math.sqrt(dx * dx + dy * dy + dz * dz))


def calc_joint_angle(
    a: Tuple[float, ...],
    b: Tuple[float, ...],
    c: Tuple[float, ...]
) -> float:
    """Computes true 3D joint angle at point B between vectors BA and BC using Cosine Theorem."""
    v1 = (a[0] - b[0], a[1] - b[1], a[2] - b[2] if len(a) > 2 and len(b) > 2 else 0.0)
    v2 = (c[0] - b[0], c[1] - b[1], c[2] - b[2] if len(c) > 2 and len(b) > 2 else 0.0)

    dot = v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]
    mag1 = math.sqrt(v1[0] * v1[0] + v1[1] * v1[1] + v1[2] * v1[2])
    mag2 = math.sqrt(v2[0] * v2[0] + v2[1] * v2[1] + v2[2] * v2[2])

    if mag1 * mag2 == 0:
        return 0.0

    cosine = max(-1.0, min(1.0, dot / (mag1 * mag2)))
    return math.degrees(math.acos(cosine))


class GestureRecognizer:
    """Classifies hand poses and tracks gesture state transitions with hysteresis."""
    def __init__(self, config: GestureConfig, screen_size: Tuple[int, int]):
        self.config = config
        self.screen_width, self.screen_height = screen_size

        # State tracking
        self.current_gesture = GestureType.NONE
        self.is_pinch_active = False
        self.is_thumb_bend_active = False
        self.is_right_click_active = False
        self.is_middle_click_active = False
        self.is_task_switch_active = False
        self.is_fist_active = False
        self.fist_start_time = 0.0

        # Debounce timestamps
        self.last_left_click_time = 0.0
        self.last_right_click_time = 0.0
        self.last_middle_click_time = 0.0
        self.last_task_switch_time = 0.0
        self.last_rock_time = 0.0
        self.last_shaka_time = 0.0
        self.last_scroll_time = 0.0

        # Scroll reference tracking
        self.prev_scroll_y: Optional[float] = None

        # Bimanual action hand state tracking
        self.is_action_thumb_bend_active = False
        self.is_action_pinch_active = False
        self.is_action_right_click_active = False
        self.is_action_middle_click_active = False
        self.is_action_task_switch_active = False
        self.is_action_fist_active = False
        self.action_fist_start_time = 0.0
        self.prev_action_scroll_y: Optional[float] = None
        self.last_action_gesture = GestureType.NONE

    def get_finger_states(self, hand: HandData) -> Dict[str, bool]:
        """Determines whether each finger is extended (True) or curled (False) using true 3D kinematics."""
        pts = hand.landmarks_world if (hasattr(hand, "landmarks_world") and hand.landmarks_world) else hand.landmarks_px
        w = pts[WRIST]

        # 1. Thumb
        thumb_tip_dist = calc_euclidean_distance(pts[THUMB_TIP], pts[PINKY_MCP])
        thumb_ip_dist = calc_euclidean_distance(pts[THUMB_IP], pts[PINKY_MCP])
        thumb_angle = calc_joint_angle(pts[THUMB_MCP], pts[THUMB_IP], pts[THUMB_TIP])
        thumb_extended = (thumb_tip_dist > thumb_ip_dist * 1.05) and (thumb_angle > 118.0)

        # 2. Index Finger
        idx_tip_wrist = calc_euclidean_distance(pts[INDEX_TIP], w)
        idx_pip_wrist = calc_euclidean_distance(pts[INDEX_PIP], w)
        idx_angle = calc_joint_angle(pts[INDEX_MCP], pts[INDEX_PIP], pts[INDEX_TIP])
        index_extended = (idx_tip_wrist > idx_pip_wrist * 1.06) and (idx_angle > 130.0)

        # 3. Middle Finger
        mid_tip_wrist = calc_euclidean_distance(pts[MIDDLE_TIP], w)
        mid_pip_wrist = calc_euclidean_distance(pts[MIDDLE_PIP], w)
        mid_angle = calc_joint_angle(pts[MIDDLE_MCP], pts[MIDDLE_PIP], pts[MIDDLE_TIP])
        middle_extended = (mid_tip_wrist > mid_pip_wrist * 1.06) and (mid_angle > 130.0)

        # 4. Ring Finger
        ring_tip_wrist = calc_euclidean_distance(pts[RING_TIP], w)
        ring_pip_wrist = calc_euclidean_distance(pts[RING_PIP], w)
        ring_angle = calc_joint_angle(pts[RING_MCP], pts[RING_PIP], pts[RING_TIP])
        ring_extended = (ring_tip_wrist > ring_pip_wrist * 1.06) and (ring_angle > 130.0)

        # 5. Pinky Finger
        pinky_tip_wrist = calc_euclidean_distance(pts[PINKY_TIP], w)
        pinky_pip_wrist = calc_euclidean_distance(pts[PINKY_PIP], w)
        pinky_angle = calc_joint_angle(pts[PINKY_MCP], pts[PINKY_PIP], pts[PINKY_TIP])
        pinky_extended = (pinky_tip_wrist > pinky_pip_wrist * 1.06) and (pinky_angle > 130.0)

        return {
            "thumb": thumb_extended,
            "index": index_extended,
            "middle": middle_extended,
            "ring": ring_extended,
            "pinky": pinky_extended
        }

    def map_to_screen(
        self,
        point_px: Tuple[float, float, ...],
        cam_shape: Tuple[int, int]
    ) -> Tuple[float, float]:
        """Maps coordinates within the Active Tracking Zone to Screen Resolution with sensitivity multiplier."""
        cam_h, cam_w = cam_shape
        x, y = point_px[0], point_px[1]

        # Calculate bounding box with configured margins
        x_min = cam_w * self.config.margin_x
        x_max = cam_w * (1.0 - self.config.margin_x)
        y_min = cam_h * self.config.margin_y
        y_max = cam_h * (1.0 - self.config.margin_y)

        # Normalize to [0.0, 1.0] inside active zone
        norm_x = (x - x_min) / max(1.0, (x_max - x_min))
        norm_y = (y - y_min) / max(1.0, (y_max - y_min))

        # Sensitivity speed scaling (expands range from center [0.5, 0.5])
        sens = getattr(self.config, 'sensitivity', 1.8)
        if sens != 1.0:
            norm_x = 0.5 + (norm_x - 0.5) * sens
            norm_y = 0.5 + (norm_y - 0.5) * sens

        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        screen_x = norm_x * self.screen_width
        screen_y = norm_y * self.screen_height

        return screen_x, screen_y

    def update(
        self,
        hand: Optional[HandData],
        cam_shape: Tuple[int, int]
    ) -> Tuple[GestureType, Dict[str, any]]:
        """Updates gesture recognition state from latest HandData."""
        if hand is None:
            self.current_gesture = GestureType.NONE
            self.is_pinch_active = False
            self.is_thumb_bend_active = False
            self.is_right_click_active = False
            self.is_fist_active = False
            self.prev_scroll_y = None
            return GestureType.NONE, {}

        now = time.time()
        pts_3d = hand.landmarks_world if (hasattr(hand, "landmarks_world") and hand.landmarks_world) else hand.landmarks_px
        pts_2d = hand.landmarks_px
        palm = hand.palm_size

        # Invariant 3D distance ratios normalized to 3D palm scale
        thumb_idx_dist = calc_euclidean_distance(pts_3d[THUMB_TIP], pts_3d[INDEX_TIP]) / palm
        thumb_mid_dist = calc_euclidean_distance(pts_3d[THUMB_TIP], pts_3d[MIDDLE_TIP]) / palm
        thumb_ring_dist = calc_euclidean_distance(pts_3d[THUMB_TIP], pts_3d[RING_TIP]) / palm
        thumb_pinky_dist = calc_euclidean_distance(pts_3d[THUMB_TIP], pts_3d[PINKY_TIP]) / palm
        thumb_knuckle_dist = calc_euclidean_distance(pts_3d[THUMB_TIP], pts_3d[INDEX_MCP]) / palm

        # Invariant 3D joint angle of thumb flexion at IP joint
        thumb_ip_angle = calc_joint_angle(pts_3d[THUMB_MCP], pts_3d[THUMB_IP], pts_3d[THUMB_TIP])

        # --- 1. Pinch Proximity Calculation ---
        act = self.config.pinch_activate_ratio
        rel = self.config.pinch_release_ratio
        if thumb_idx_dist >= rel:
            pinch_pct = 0.0
        elif thumb_idx_dist <= act:
            pinch_pct = 100.0
        else:
            pinch_pct = ((rel - thumb_idx_dist) / max(1e-4, rel - act)) * 100.0

        # --- 2. Thumb Bend Proximity Calculation (Dynamic UI Gauge) ---
        # 152 deg = straight thumb (0%), deliberate bend threshold = 100%
        b_act = self.config.thumb_bend_angle_activate
        gauge_max = 152.0
        if thumb_ip_angle >= gauge_max:
            thumb_bend_pct = 0.0
        elif thumb_ip_angle <= b_act:
            thumb_bend_pct = 100.0
        else:
            thumb_bend_pct = ((gauge_max - thumb_ip_angle) / max(1e-4, gauge_max - b_act)) * 100.0

        finger_states = self.get_finger_states(hand)
        num_extended = sum(finger_states.values())

        # Blended tracking anchor: 70% Index Tip + 30% Index DIP for high physical stability
        # Always uses 2D camera viewport pixels for screen mapping
        blended_tip = (
            pts_2d[INDEX_TIP][0] * 0.70 + pts_2d[INDEX_DIP][0] * 0.30,
            pts_2d[INDEX_TIP][1] * 0.70 + pts_2d[INDEX_DIP][1] * 0.30
        )

        # Primary gauge percentage depending on active click mode
        primary_gauge_pct = thumb_bend_pct if self.config.click_mode == "thumb_bend" else pinch_pct

        events = {
            "trigger_left_click": False,
            "trigger_right_click": False,
            "trigger_middle_click": False,
            "trigger_task_switch": False,
            "trigger_alt_tab": False,
            "trigger_show_desktop": False,
            "drag_active": False,
            "scroll_delta": 0,
            "cursor_target": self.map_to_screen(blended_tip, cam_shape),
            "thumb_idx_ratio": thumb_idx_dist,
            "thumb_mid_ratio": thumb_mid_dist,
            "thumb_ring_ratio": thumb_ring_dist,
            "thumb_pinky_ratio": thumb_pinky_dist,
            "thumb_knuckle_ratio": thumb_knuckle_dist,
            "thumb_ip_angle": round(thumb_ip_angle, 1),
            "pinch_proximity_pct": round(primary_gauge_pct, 1),
            "thumb_bend_pct": round(thumb_bend_pct, 1),
            "click_mode": self.config.click_mode,
            "finger_states": finger_states,
        }

        # --- A. PAUSE MODE (🖐️ Open palm: 5 fingers extended) ---
        if num_extended == 5:
            self.current_gesture = GestureType.PAUSE
            self.is_pinch_active = False
            self.is_thumb_bend_active = False
            self.is_right_click_active = False
            self.is_middle_click_active = False
            self.is_task_switch_active = False
            self.is_fist_active = False
            self.prev_scroll_y = None
            return self.current_gesture, events

        # --- B. DRAG & DROP (✊ Fist: 0 fingers extended held for > 0.20s) ---
        if num_extended == 0:
            if self.fist_start_time == 0.0:
                self.fist_start_time = now
            elif now - self.fist_start_time > 0.20:
                self.current_gesture = GestureType.DRAG
                self.is_fist_active = True
                events["drag_active"] = True
                events["cursor_target"] = self.map_to_screen(pts_2d[INDEX_MCP], cam_shape)
                self.prev_scroll_y = None
                return self.current_gesture, events
            # In fist posture, suppress all discrete clicks
            return GestureType.NONE, events
        else:
            self.fist_start_time = 0.0
            self.is_fist_active = False

        # --- SPECIAL POSE 1: SHAKA 🤙 (Thumb + Pinky extended) -> SHOW DESKTOP (Win+D) ---
        if finger_states["thumb"] and finger_states["pinky"] and not finger_states["index"] and not finger_states["middle"] and not finger_states["ring"]:
            if (now - self.last_shaka_time) > 0.45:
                self.last_shaka_time = now
                events["trigger_show_desktop"] = True
            self.current_gesture = GestureType.SHAKA_DESKTOP
            return self.current_gesture, events

        # --- SPECIAL POSE 2: ROCK 🤘 (Index + Pinky extended) -> QUICK ALT+TAB ---
        if finger_states["index"] and finger_states["pinky"] and not finger_states["middle"] and not finger_states["ring"]:
            if (now - self.last_rock_time) > 0.40:
                self.last_rock_time = now
                events["trigger_alt_tab"] = True
            self.current_gesture = GestureType.ROCK_ALT_TAB
            return self.current_gesture, events

        # --- C. SCROLLING (✌️ Index + Middle extended, Ring + Pinky curled) ---
        if finger_states["index"] and finger_states["middle"] and not finger_states["ring"] and not finger_states["pinky"]:
            self.current_gesture = GestureType.SCROLL
            self.is_pinch_active = False
            self.is_thumb_bend_active = False
            self.is_right_click_active = False
            self.is_middle_click_active = False
            self.is_task_switch_active = False

            mid_y = (pts_2d[INDEX_TIP][1] + pts_2d[MIDDLE_TIP][1]) / 2.0
            if self.prev_scroll_y is not None:
                dy = mid_y - self.prev_scroll_y
                if abs(dy) > 1.8 and (now - self.last_scroll_time > self.config.scroll_cooldown_sec):
                    palm_px = getattr(hand, 'palm_size_px', 60.0)
                    scroll_delta = -int(dy * (self.config.scroll_speed_multiplier / max(10.0, palm_px)))
                    if scroll_delta != 0:
                        events["scroll_delta"] = scroll_delta
                        self.last_scroll_time = now
            self.prev_scroll_y = mid_y
            return self.current_gesture, events
        else:
            self.prev_scroll_y = None

        # --- D. SECONDARY PINCH CLASSIFIER (Middle, Ring, or Pinky) ---
        # Disambiguates which finger the thumb is contacting based on minimum Euclidean distance
        min_pinch_dist = min(thumb_mid_dist, thumb_ring_dist, thumb_pinky_dist)
        pinch_act = self.config.right_click_activate_ratio
        pinch_rel = self.config.right_click_release_ratio

        # D1. Right Click (👌 Pinch Thumb + Middle)
        if self.is_right_click_active:
            if thumb_mid_dist > pinch_rel:
                self.is_right_click_active = False
        elif min_pinch_dist == thumb_mid_dist and thumb_mid_dist < pinch_act:
            if (now - self.last_right_click_time) > self.config.click_debounce_sec:
                self.is_right_click_active = True
                self.last_right_click_time = now
                events["trigger_right_click"] = True

        if self.is_right_click_active:
            self.current_gesture = GestureType.RIGHT_CLICK
            return self.current_gesture, events

        # D2. Middle Click / Wheel (🔘 Pinch Thumb + Ring)
        if self.is_middle_click_active:
            if thumb_ring_dist > pinch_rel:
                self.is_middle_click_active = False
        elif min_pinch_dist == thumb_ring_dist and thumb_ring_dist < pinch_act:
            if (now - self.last_middle_click_time) > self.config.click_debounce_sec:
                self.is_middle_click_active = True
                self.last_middle_click_time = now
                events["trigger_middle_click"] = True

        if self.is_middle_click_active:
            self.current_gesture = GestureType.MIDDLE_CLICK
            return self.current_gesture, events

        # D3. Task Switch / Win+Tab (🪟 Pinch Thumb + Pinky)
        if self.is_task_switch_active:
            if thumb_pinky_dist > pinch_rel:
                self.is_task_switch_active = False
        elif min_pinch_dist == thumb_pinky_dist and thumb_pinky_dist < pinch_act:
            if (now - self.last_task_switch_time) > 0.40:
                self.is_task_switch_active = True
                self.last_task_switch_time = now
                events["trigger_task_switch"] = True

        if self.is_task_switch_active:
            self.current_gesture = GestureType.TASK_SWITCH
            return self.current_gesture, events

        # --- E. LEFT CLICK: THUMB BEND OR PINCH ---
        if self.config.click_mode == "thumb_bend":
            # Release hysteresis: releases if thumb unbends OR extends OR user stops pointing
            if self.is_thumb_bend_active:
                if (thumb_ip_angle >= self.config.thumb_bend_angle_release and thumb_knuckle_dist >= self.config.thumb_bend_dist_release) or not finger_states["index"]:
                    self.is_thumb_bend_active = False

            # Activation: require active pointing (index extended, middle and ring curled)
            # AND deliberate thumb bend angle drop or tuck into palm
            pointing_posture = finger_states["index"] and not finger_states["middle"] and not finger_states["ring"]
            if not self.is_thumb_bend_active and pointing_posture:
                is_deliberate_bend = (thumb_ip_angle <= self.config.thumb_bend_angle_activate)
                is_tucked_in = (thumb_knuckle_dist <= self.config.thumb_bend_dist_activate and thumb_ip_angle < 132.0)
                if is_deliberate_bend or is_tucked_in:
                    time_since_last = now - self.last_left_click_time
                    if time_since_last > self.config.click_debounce_sec:
                        self.is_thumb_bend_active = True
                        if time_since_last < 0.42:
                            events["trigger_double_click"] = True
                        else:
                            events["trigger_left_click"] = True
                        self.last_left_click_time = now

            if self.is_thumb_bend_active:
                self.current_gesture = GestureType.THUMB_CLICK
                return self.current_gesture, events

        elif self.config.click_mode == "pinch":
            if self.is_pinch_active:
                if thumb_idx_dist > self.config.pinch_release_ratio or not finger_states["index"]:
                    self.is_pinch_active = False
            else:
                if thumb_idx_dist < self.config.pinch_activate_ratio and finger_states["index"] and not finger_states["ring"]:
                    time_since_last = now - self.last_left_click_time
                    if time_since_last > self.config.click_debounce_sec:
                        self.is_pinch_active = True
                        if time_since_last < 0.42:
                            events["trigger_double_click"] = True
                        else:
                            events["trigger_left_click"] = True
                        self.last_left_click_time = now

            if self.is_pinch_active:
                self.current_gesture = GestureType.PINCH_CLICK
                return self.current_gesture, events

        # --- F. HOVER / MOVE (☝️ Index pointing) ---
        if finger_states["index"]:
            self.current_gesture = GestureType.HOVER
        else:
            self.current_gesture = GestureType.NONE

        return self.current_gesture, events

    def update_bimanual(
        self,
        pointer_hand: HandData,
        action_hand: HandData,
        cam_shape: Tuple[int, int]
    ) -> Tuple[GestureType, Dict[str, any]]:
        """
        Processes bimanual HCI:
        - Pointer hand controls smooth cursor movement
        - Action hand executes left click (thumb bend or pinch), right click, scroll, drag, and safety pause
        """
        now = time.time()

        # 1. Evaluate Pointer Hand (cursor position & pointer gestures)
        pointer_gesture, pointer_events = self.update(pointer_hand, cam_shape)

        # 2. Evaluate Action Hand kinematics
        action_pts_3d = action_hand.landmarks_world if (hasattr(action_hand, "landmarks_world") and action_hand.landmarks_world) else action_hand.landmarks_px
        action_pts_2d = action_hand.landmarks_px
        action_palm = action_hand.palm_size

        act_thumb_idx_dist = calc_euclidean_distance(action_pts_3d[THUMB_TIP], action_pts_3d[INDEX_TIP]) / action_palm
        act_thumb_mid_dist = calc_euclidean_distance(action_pts_3d[THUMB_TIP], action_pts_3d[MIDDLE_TIP]) / action_palm
        act_thumb_ring_dist = calc_euclidean_distance(action_pts_3d[THUMB_TIP], action_pts_3d[RING_TIP]) / action_palm
        act_thumb_pinky_dist = calc_euclidean_distance(action_pts_3d[THUMB_TIP], action_pts_3d[PINKY_TIP]) / action_palm
        act_thumb_knuckle_dist = calc_euclidean_distance(action_pts_3d[THUMB_TIP], action_pts_3d[INDEX_MCP]) / action_palm
        act_thumb_ip_angle = calc_joint_angle(action_pts_3d[THUMB_MCP], action_pts_3d[THUMB_IP], action_pts_3d[THUMB_TIP])

        action_finger_states = self.get_finger_states(action_hand)
        action_num_extended = sum(action_finger_states.values())

        # Start with pointer events (cursor target from pointer hand)
        events = pointer_events.copy()
        events["is_dual_hand"] = True
        events["pointer_hand"] = pointer_hand.handedness
        events["action_hand"] = action_hand.handedness
        events["action_gesture"] = GestureType.NONE.value
        # In bimanual mode, commands are issued strictly by the Action Hand to avoid cursor deflection
        events["trigger_left_click"] = False
        events["trigger_double_click"] = False
        events["trigger_right_click"] = False
        events["trigger_middle_click"] = False
        events["trigger_task_switch"] = False
        events["trigger_alt_tab"] = False
        events["trigger_show_desktop"] = False
        events["drag_active"] = False
        effective_gesture = pointer_gesture

        # --- A. ACTION HAND SAFETY PAUSE (🖐️ Open palm on action hand: 5 fingers extended) ---
        if action_num_extended == 5:
            self.action_fist_start_time = 0.0
            self.is_action_fist_active = False
            self.prev_action_scroll_y = None
            events["drag_active"] = False
            events["action_gesture"] = GestureType.PAUSE.value
            self.last_action_gesture = GestureType.PAUSE
            return GestureType.PAUSE, events

        # --- B. ACTION HAND DRAG & DROP (✊ Fist on action hand held for > 0.18s) ---
        if action_num_extended == 0:
            if self.action_fist_start_time == 0.0:
                self.action_fist_start_time = now
            elif now - self.action_fist_start_time > 0.18:
                self.is_action_fist_active = True
                events["drag_active"] = True
                events["action_gesture"] = GestureType.DRAG.value
                self.last_action_gesture = GestureType.DRAG
                effective_gesture = GestureType.DRAG
            # CRITICAL: In fist posture, NEVER trigger any discrete click! Return immediately!
            events["trigger_left_click"] = False
            events["trigger_double_click"] = False
            events["trigger_right_click"] = False
            events["trigger_middle_click"] = False
            events["trigger_task_switch"] = False
            return effective_gesture, events
        else:
            self.action_fist_start_time = 0.0
            if self.is_action_fist_active:
                self.is_action_fist_active = False
                events["drag_active"] = False

        # --- SPECIAL POSE 1 ON ACTION HAND: SHAKA 🤙 -> SHOW DESKTOP (Win+D) ---
        if action_finger_states["thumb"] and action_finger_states["pinky"] and not action_finger_states["index"] and not action_finger_states["middle"] and not action_finger_states["ring"]:
            if (now - self.last_shaka_time) > 0.45:
                self.last_shaka_time = now
                events["trigger_show_desktop"] = True
            events["action_gesture"] = GestureType.SHAKA_DESKTOP.value
            self.last_action_gesture = GestureType.SHAKA_DESKTOP
            return GestureType.SHAKA_DESKTOP, events

        # --- SPECIAL POSE 2 ON ACTION HAND: ROCK 🤘 -> QUICK ALT+TAB ---
        if action_finger_states["index"] and action_finger_states["pinky"] and not action_finger_states["middle"] and not action_finger_states["ring"]:
            if (now - self.last_rock_time) > 0.40:
                self.last_rock_time = now
                events["trigger_alt_tab"] = True
            events["action_gesture"] = GestureType.ROCK_ALT_TAB.value
            self.last_action_gesture = GestureType.ROCK_ALT_TAB
            return GestureType.ROCK_ALT_TAB, events

        # --- C. ACTION HAND SCROLLING (✌️ Index + Middle extended on action hand) ---
        if action_finger_states["index"] and action_finger_states["middle"] and not action_finger_states["ring"] and not action_finger_states["pinky"]:
            events["action_gesture"] = GestureType.SCROLL.value
            self.last_action_gesture = GestureType.SCROLL
            mid_y = (action_pts_2d[INDEX_TIP][1] + action_pts_2d[MIDDLE_TIP][1]) / 2.0
            if self.prev_action_scroll_y is not None:
                dy = mid_y - self.prev_action_scroll_y
                if abs(dy) > 1.8 and (now - self.last_scroll_time > self.config.scroll_cooldown_sec):
                    palm_px = getattr(action_hand, 'palm_size_px', 60.0)
                    scroll_delta = -int(dy * (self.config.scroll_speed_multiplier / max(10.0, palm_px)))
                    if scroll_delta != 0:
                        events["scroll_delta"] = scroll_delta
                        self.last_scroll_time = now
                        effective_gesture = GestureType.SCROLL
            self.prev_action_scroll_y = mid_y
        else:
            self.prev_action_scroll_y = None

        # --- D. ACTION HAND SECONDARY PINCH CLASSIFIER (Middle, Ring, or Pinky) ---
        act_min_pinch = min(act_thumb_mid_dist, act_thumb_ring_dist, act_thumb_pinky_dist)
        pinch_act = self.config.right_click_activate_ratio
        pinch_rel = self.config.right_click_release_ratio

        # D1. Action Hand Right Click (👌 Pinch Thumb + Middle)
        if self.is_action_right_click_active:
            if act_thumb_mid_dist > pinch_rel:
                self.is_action_right_click_active = False
        elif act_min_pinch == act_thumb_mid_dist and act_thumb_mid_dist < pinch_act:
            if (now - self.last_right_click_time) > self.config.click_debounce_sec:
                self.is_action_right_click_active = True
                self.last_right_click_time = now
                events["trigger_right_click"] = True
                events["action_gesture"] = GestureType.RIGHT_CLICK.value
                self.last_action_gesture = GestureType.RIGHT_CLICK
                effective_gesture = GestureType.RIGHT_CLICK

        # D2. Action Hand Middle Click (🔘 Pinch Thumb + Ring)
        if self.is_action_middle_click_active:
            if act_thumb_ring_dist > pinch_rel:
                self.is_action_middle_click_active = False
        elif act_min_pinch == act_thumb_ring_dist and act_thumb_ring_dist < pinch_act:
            if (now - self.last_middle_click_time) > self.config.click_debounce_sec:
                self.is_action_middle_click_active = True
                self.last_middle_click_time = now
                events["trigger_middle_click"] = True
                events["action_gesture"] = GestureType.MIDDLE_CLICK.value
                self.last_action_gesture = GestureType.MIDDLE_CLICK
                effective_gesture = GestureType.MIDDLE_CLICK

        # D3. Action Hand Task Switch (🪟 Pinch Thumb + Pinky)
        if self.is_action_task_switch_active:
            if act_thumb_pinky_dist > pinch_rel:
                self.is_action_task_switch_active = False
        elif act_min_pinch == act_thumb_pinky_dist and act_thumb_pinky_dist < pinch_act:
            if (now - self.last_task_switch_time) > 0.40:
                self.is_action_task_switch_active = True
                self.last_task_switch_time = now
                events["trigger_task_switch"] = True
                events["action_gesture"] = GestureType.TASK_SWITCH.value
                self.last_action_gesture = GestureType.TASK_SWITCH
                effective_gesture = GestureType.TASK_SWITCH

        # --- E. ACTION HAND LEFT CLICK (Thumb Bend or Pinch on action hand) ---
        # Only evaluate clicks if action hand is open/pointing (not in a fist)
        if action_num_extended >= 1:
            if self.config.click_mode == "thumb_bend":
                if self.is_action_thumb_bend_active:
                    if act_thumb_ip_angle >= self.config.thumb_bend_angle_release and act_thumb_knuckle_dist >= self.config.thumb_bend_dist_release:
                        self.is_action_thumb_bend_active = False
                else:
                    is_act_flexed = (act_thumb_ip_angle <= self.config.thumb_bend_angle_activate) or \
                                    (act_thumb_knuckle_dist <= self.config.thumb_bend_dist_activate and act_thumb_ip_angle < 132.0)
                    if is_act_flexed:
                        time_since_last = now - self.last_left_click_time
                        if time_since_last > self.config.click_debounce_sec:
                            self.is_action_thumb_bend_active = True
                            if time_since_last < 0.42:
                                events["trigger_double_click"] = True
                            else:
                                events["trigger_left_click"] = True
                            self.last_left_click_time = now
                            events["action_gesture"] = GestureType.THUMB_CLICK.value
                            self.last_action_gesture = GestureType.THUMB_CLICK
                            effective_gesture = GestureType.THUMB_CLICK

            elif self.config.click_mode == "pinch":
                if self.is_action_pinch_active:
                    if act_thumb_idx_dist > self.config.pinch_release_ratio:
                        self.is_action_pinch_active = False
                else:
                    if act_thumb_idx_dist < self.config.pinch_activate_ratio:
                        time_since_last = now - self.last_left_click_time
                        if time_since_last > self.config.click_debounce_sec:
                            self.is_action_pinch_active = True
                            if time_since_last < 0.42:
                                events["trigger_double_click"] = True
                            else:
                                events["trigger_left_click"] = True
                            self.last_left_click_time = now
                            events["action_gesture"] = GestureType.PINCH_CLICK.value
                            self.last_action_gesture = GestureType.PINCH_CLICK
                            effective_gesture = GestureType.PINCH_CLICK

        return effective_gesture, events
