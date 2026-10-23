"""
Camera & Processing Pipeline Manager
====================================
Handles multi-camera discovery, dynamic hot-switching between cameras,
threaded video capture, ML inference, AeroPrecisionEngine mouse dispatch,
and MJPEG / snapshot frame encoding.
Optimized for Windows DirectShow (CAP_DSHOW).
"""

import sys
import os

# Prevent OpenCV FFMPEG crash (exception 0x40000015) on Windows
os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"
os.environ["OPENCV_VIDEOIO_PRIORITY_FFMPEG"] = "0"

import time
import threading
import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple

from config import GestureConfig
from mouse_controller import MouseController
from hand_tracker import HandTracker, HandData, WRIST, THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP
from gestures import GestureRecognizer, GestureType
from filters import AeroPrecisionEngine, InertialScrollEngine
from hud import CyberHUD
from spatial_receiver import SpatialReceiver
from hotkeys import GlobalHotkeyService


def get_system_camera_names() -> List[str]:
    """Queries exact DirectShow device names on Windows via COM FilterGraph."""
    try:
        from pygrabber.dshow_graph import FilterGraph
        graph = FilterGraph()
        devices = graph.get_input_devices()
        if devices:
            return devices
    except Exception:
        pass
    return []


AIR_DRAW_COLOR_MAP = {
    "cyan": (254, 242, 0),      # #00F2FE Electric Cyan (BGR)
    "magenta": (255, 0, 255),   # #FF00FF Magenta (BGR)
    "green": (50, 255, 50),     # #32FF32 Emerald Green (BGR)
    "gold": (0, 215, 255),      # #FFD700 Neon Gold (BGR)
    "white": (255, 255, 255),   # #FFFFFF Crisp White (BGR)
    "coral": (80, 80, 255),     # #FF5050 Hot Coral (BGR)
}


class CameraManager:
    """Thread-safe multi-camera and gesture processing orchestrator."""
    def __init__(self, config: Optional[GestureConfig] = None):
        self.start_time = time.time()
        self.config = config or GestureConfig.load_from_file()
        self.mouse = MouseController(enable_sound=self.config.enable_sound_feedback)
        self.screen_size = (self.mouse.screen_width, self.mouse.screen_height)
        self.screen_origin = (self.mouse.x_origin, self.mouse.y_origin)

        # High-precision AeroPoint cursor engine
        self.precision_engine = AeroPrecisionEngine(
            min_cutoff=0.85,
            beta=0.007,
            deadzone_radius=self.config.deadzone_radius,
            enable_acceleration=True,
            enable_click_anchor=True
        )
        if hasattr(self.config, 'precision_profile'):
            self.precision_engine.apply_profile(self.config.precision_profile)
        self.scroll_engine = InertialScrollEngine()

        # Hand tracking & recognition
        self.tracker = HandTracker(self.config)
        self.recognizer = GestureRecognizer(self.config, self.screen_size, self.screen_origin)
        self.hud = CyberHUD(self.config)
        self.hotkeys = GlobalHotkeyService(self)

        # State flags
        self.control_enabled = True       # When False: preview only
        self.manual_pause = False
        self.active_camera_id = self.config.camera_id
        self.running = False
        self.lock = threading.Lock()
        self.active_tab = "webcam"        # "webcam" or "iphone"

        # iPhone Spatial Receiver (LiDAR / TrueDepth)
        self.spatial_receiver = SpatialReceiver(host="0.0.0.0", port=8765)
        self.spatial_receiver.start()

        # Telemetry metrics
        self.latest_jpeg: Optional[bytes] = self._generate_placeholder("Запуск камеры...")
        self.frame_id: int = 0
        self.last_jpeg_time: float = 0.0
        self.last_client_request_time: float = time.time()
        self.current_gesture = GestureType.NONE
        self.action_gesture = GestureType.NONE
        self.hand_detected = False
        self.current_hands: List[HandData] = []
        self.pointer_hand: Optional[HandData] = None
        self.action_hand: Optional[HandData] = None
        self.is_dual_hand_active = False
        self.pinch_ratio = 0.0
        self.pinch_pct = 0.0
        self.latest_air_tap_pct = 0.0
        self.fps = 0.0
        self.latency_ms = 0.0
        self.cpu_percent = 0.0
        self.is_power_saver = False
        self.last_hand_seen_time = time.time()
        self.radial_menu_open: bool = False
        self.active_radial_sector: Optional[int] = None
        self.last_radial_action_time: float = 0.0

        # Spatial Rotary Volume Knob state
        self.rotary_anchor_roll: Optional[float] = None
        self.last_rotary_step_time: float = 0.0
        self.is_rotary_tuning: bool = False

        # Video capture handle & double-buffering
        self.cap: Optional[cv2.VideoCapture] = None
        self.worker_thread: Optional[threading.Thread] = None
        self.grabber_thread: Optional[threading.Thread] = None
        self.frame_lock = threading.Lock()
        self.latest_raw_frame: Optional[np.ndarray] = None
        self.frame_available_event = threading.Event()

        # Visual calibration overlay state
        self.calibration_active_until: float = 0.0
        self.calibration_start_time: float = 0.0

        # Camera discovery
        self.discovered_cameras: List[Dict[str, any]] = self.discover_cameras()

    def _generate_placeholder(self, text: str) -> bytes:
        """Generates a stylish dark placeholder frame."""
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (18, 16, 22)
        cv2.putText(img, "AeroPoint Studio", (200, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(img, text, (220, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 242, 254), 1, cv2.LINE_AA)
        ret, jpeg = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return jpeg.tobytes() if ret else b''

    def _open_capture(self, cam_id: int) -> Optional[cv2.VideoCapture]:
        """Opens camera strictly using DirectShow on Windows to prevent FFMPEG crashes."""
        cap = None
        try:
            if sys.platform.startswith("win"):
                cap = cv2.VideoCapture(cam_id, cv2.CAP_DSHOW)
            else:
                cap = cv2.VideoCapture(cam_id)
        except Exception as e:
            print(f"[!] Warning opening camera {cam_id}: {e}")
            cap = None

        if cap and cap.isOpened():
            try:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.cam_width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.cam_height)
                cap.set(cv2.CAP_PROP_FPS, self.config.target_fps)
                return cap
            except Exception:
                pass
        return None

    def discover_cameras(self, max_test: int = 2) -> List[Dict[str, any]]:
        """Scans and discovers real hardware cameras using DirectShow device registry without slow polling."""
        results = []
        try:
            system_names = get_system_camera_names()
        except Exception:
            system_names = []

        if system_names:
            for idx, dev_name in enumerate(system_names[:max_test]):
                results.append({
                    "id": idx,
                    "label": dev_name,
                    "resolution": f"{self.config.cam_width}x{self.config.cam_height}"
                })
        else:
            # Fast single-device fallback if registry enumeration unavailable
            try:
                backend = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY
                cap = cv2.VideoCapture(0, backend)
                if cap and cap.isOpened():
                    results.append({
                        "id": 0,
                        "label": "Camera #0",
                        "resolution": f"{self.config.cam_width}x{self.config.cam_height}"
                    })
                    cap.release()
            except Exception:
                pass

        if not results:
            results.append({"id": 0, "label": "Default Camera", "resolution": f"{self.config.cam_width}x{self.config.cam_height}"})

        self.discovered_cameras = results
        return results

    def switch_monitor(self, monitor_id: int) -> int:
        """Switches active target display (-1 for full desktop, 0..N for individual monitor)."""
        with self.lock:
            self.mouse.set_active_monitor(monitor_id)
            self.screen_size = (self.mouse.screen_width, self.mouse.screen_height)
            self.screen_origin = (self.mouse.x_origin, self.mouse.y_origin)
            self.recognizer.screen_size = self.screen_size
            self.recognizer.screen_origin = self.screen_origin
            print(f"[+] Active Monitor switched to #{monitor_id}: origin={self.screen_origin}, size={self.screen_size}")
            return self.mouse.active_monitor_index

    def cycle_monitor(self) -> int:
        """Cycles through physical monitors and virtual desktop."""
        with self.lock:
            idx = self.mouse.cycle_monitor()
            self.screen_size = (self.mouse.screen_width, self.mouse.screen_height)
            self.screen_origin = (self.mouse.x_origin, self.mouse.y_origin)
            self.recognizer.screen_size = self.screen_size
            self.recognizer.screen_origin = self.screen_origin
            print(f"[+] Cycled to Monitor #{idx}: origin={self.screen_origin}, size={self.screen_size}")
            return idx

    def switch_camera(self, camera_id: int) -> bool:
        """Dynamically switches active video device safely."""
        with self.lock:
            if camera_id == self.active_camera_id and self.cap and self.cap.isOpened():
                return True

            print(f"[*] Switching to Camera #{camera_id}...")
            old_cap = self.cap
            old_id = self.active_camera_id

            try:
                # 1. Release old capture first to free DirectShow device lock
                if old_cap:
                    old_cap.release()
                    self.cap = None
                with self.frame_lock:
                    self.latest_raw_frame = None

                # Short delay to allow Windows DirectShow filter graph to unbind
                time.sleep(0.12)

                # 2. Open new device
                new_cap = self._open_capture(camera_id)
                if new_cap and new_cap.isOpened():
                    # Retry reading a few initial frames (DirectShow pipeline spin-up)
                    success = False
                    for _ in range(8):
                        ret, frame = new_cap.read()
                        if ret and frame is not None:
                            success = True
                            break
                        time.sleep(0.04)

                    if success:
                        self.cap = new_cap
                        self.active_camera_id = camera_id
                        self.config.camera_id = camera_id
                        print(f"[✓] Switched successfully to Camera #{camera_id}")
                        return True
                    else:
                        print(f"[!] Camera #{camera_id} opened but produced no frames.")
                        new_cap.release()
            except Exception as e:
                print(f"[!] Error switching camera: {e}")

            # Fallback restore old camera if new failed
            print(f"[*] Restoring previous Camera #{old_id}...")
            self.cap = self._open_capture(old_id)
            self.active_camera_id = old_id
            return False

    def trigger_calibration(self, duration: float = 3.0):
        """Starts animated visual calibration countdown and resets precision filters upon completion."""
        now = time.time()
        self.calibration_start_time = now
        self.calibration_active_until = now + duration
        self.precision_engine.reset()
        print(f"[*] Calibration triggered: active for {duration}s")

    def toggle_radial_menu(self):
        """Toggles in-air holographic 8-sector Quick-Dial radial menu overlay."""
        self.radial_menu_open = not self.radial_menu_open
        if not self.radial_menu_open:
            self.active_radial_sector = None
        state = "OPEN" if self.radial_menu_open else "CLOSED"
        print(f"[*] Radial Quick-Dial: {state}")

    def _execute_radial_sector(self, sector: int):
        """Executes the macro corresponding to selected radial sector."""
        actions = [
            ("WIN+TAB", self.mouse.task_view),
            ("SNIP", self.mouse.snipping_tool),
            ("VOL+", self.mouse.volume_up),
            ("VOL-", self.mouse.volume_down),
            ("PLAY", self.mouse.play_pause),
            ("DESK", self.mouse.show_desktop),
            ("ALT+TAB", self.mouse.alt_tab),
            ("LOCK", self.mouse.lock_workstation),
        ]
        if 0 <= sector < len(actions):
            label, fn = actions[sector]
            print(f"[⚡] Radial Executed: {label} (Sector #{sector})")
            fn()

    def clear_air_canvas(self):
        """Clears all spatial whiteboard strokes from the HUD."""
        self.hud.clear_air_canvas()

    def toggle_air_canvas(self, enabled: Optional[bool] = None) -> bool:
        """Toggles or sets the air-draw stream state."""
        if enabled is None:
            self.config.enable_air_draw_stream = not self.config.enable_air_draw_stream
        else:
            self.config.enable_air_draw_stream = bool(enabled)
        return self.config.enable_air_draw_stream

    def start(self):
        """Starts background capture and processing threads."""
        if self.running:
            return
        self.running = True
        with self.lock:
            self.cap = self._open_capture(self.active_camera_id)
        self.hotkeys.start()
        self.grabber_thread = threading.Thread(target=self._frame_grabber_loop, daemon=True, name="AeroPoint-Grabber")
        self.grabber_thread.start()
        self.worker_thread = threading.Thread(target=self._capture_loop, daemon=True, name="AeroPoint-Inference")
        self.worker_thread.start()

    def stop(self):
        """Stops background loops and releases devices."""
        self.running = False
        self.frame_available_event.set()
        self.hotkeys.stop()
        if self.grabber_thread:
            self.grabber_thread.join(timeout=1.0)
        if self.worker_thread:
            self.worker_thread.join(timeout=1.5)
        with self.lock:
            if self.cap:
                self.cap.release()
                self.cap = None
        if self.mouse.is_dragging:
            self.mouse.mouse_up("left")
        self.spatial_receiver.stop()

    def _frame_grabber_loop(self):
        """Dedicated high-speed thread to drain DirectShow buffer and prevent queue lag."""
        consecutive_fails = 0
        while self.running:
            if self.active_tab == "iphone":
                time.sleep(0.02)
                continue

            cap = None
            with self.lock:
                cap = self.cap

            if not cap or not cap.isOpened():
                time.sleep(0.04)
                continue

            try:
                ret, frame = cap.read()
                if ret and frame is not None:
                    consecutive_fails = 0
                    with self.frame_lock:
                        self.latest_raw_frame = frame
                    self.frame_available_event.set()
                else:
                    consecutive_fails += 1
                    if consecutive_fails % 30 == 0:
                        print(f"[!] DirectShow grabber lost frames ({consecutive_fails}). Reconnecting...")
                        with self.lock:
                            if self.cap:
                                try:
                                    self.cap.release()
                                except Exception:
                                    pass
                                self.cap = None
                            time.sleep(0.12)
                            self.cap = self._open_capture(self.active_camera_id)
                    time.sleep(0.01)
            except Exception:
                time.sleep(0.01)

    def _capture_loop(self):
        """Continuous camera capture and gesture execution loop."""
        hand_was_present = False

        while self.running:
            if self.active_tab == "iphone":
                iphone_hands = self.spatial_receiver.get_hands()
                frame = self.spatial_receiver.render_depth_view()
                all_hands = iphone_hands
                primary_hand = all_hands[0] if all_hands else None
                self.hand_detected = (len(all_hands) > 0)
                self.current_hands = all_hands
                self.fps = self.spatial_receiver.remote_fps if self.spatial_receiver.is_connected else 60.0
                self.latency_ms = self.spatial_receiver.latency_ms
            else:
                # Wait for fresh frame from grabber thread (zero-latency double buffering)
                got_frame = self.frame_available_event.wait(timeout=0.04)
                if not got_frame:
                    time.sleep(0.005)
                    continue

                self.frame_available_event.clear()
                raw_frame = None
                with self.frame_lock:
                    if self.latest_raw_frame is not None:
                        raw_frame = self.latest_raw_frame.copy()

                if raw_frame is None:
                    continue

                # Process frame through MediaPipe (supports 1 or 2 hands)
                frame, primary_hand, all_hands = self.tracker.process(raw_frame)

                self.hand_detected = (len(all_hands) > 0)
                self.current_hands = all_hands
                self.fps = self.tracker.fps
                self.latency_ms = self.tracker.latency_ms

            # Dynamic Power Saver State Check
            now_ts = time.time()
            if self.hand_detected:
                self.last_hand_seen_time = now_ts
                self.is_power_saver = False
            else:
                if getattr(self.config, 'enable_power_saver', True) and (now_ts - self.last_hand_seen_time) > 4.0:
                    self.is_power_saver = True
                else:
                    self.is_power_saver = False

            # Gesture classification (Single-hand vs Dual-hand)
            pointer_hand = None
            action_hand = None
            effective_gesture = GestureType.NONE
            events = {}

            try:
                if self.manual_pause or not self.hand_detected:
                    effective_gesture = GestureType.PAUSE if self.manual_pause else GestureType.NONE
                    self.action_gesture = GestureType.NONE
                    events = {
                        "trigger_left_click": False,
                        "trigger_right_click": False,
                        "drag_active": False,
                        "scroll_delta": 0,
                        "pinch_proximity_pct": 0.0,
                        "thumb_idx_ratio": 1.0,
                        "is_dual_hand": False
                    }
                elif len(all_hands) >= 2 and self.config.enable_two_hands:
                    self.is_dual_hand_active = True
                    h0, h1 = all_hands[0], all_hands[1]
                    if self.config.dominant_hand == "Left":
                        pointer_hand = h0 if h0.handedness == "Left" else h1
                        action_hand = h1 if pointer_hand is h0 else h0
                    else:
                        pointer_hand = h0 if h0.handedness == "Right" else h1
                        action_hand = h1 if pointer_hand is h0 else h0

                    # Spatial fallback if handedness labels match
                    if pointer_hand.handedness == action_hand.handedness:
                        x0 = h0.landmarks_px[WRIST][0]
                        x1 = h1.landmarks_px[WRIST][0]
                        if self.config.dominant_hand == "Left":
                            pointer_hand = h0 if x0 < x1 else h1
                            action_hand = h1 if pointer_hand is h0 else h0
                        else:
                            pointer_hand = h0 if x0 > x1 else h1
                            action_hand = h1 if pointer_hand is h0 else h0

                    effective_gesture, events = self.recognizer.update_bimanual(pointer_hand, action_hand, frame.shape[:2])
                    act_str = events.get("action_gesture", "NONE")
                    self.action_gesture = getattr(GestureType, act_str, GestureType.NONE) if hasattr(GestureType, act_str) else GestureType.NONE
                else:
                    self.is_dual_hand_active = False
                    pointer_hand = primary_hand
                    action_hand = None
                    self.action_gesture = GestureType.NONE
                    effective_gesture, events = self.recognizer.update(primary_hand, frame.shape[:2])
            except Exception as e:
                effective_gesture = GestureType.NONE
                events = {}
                pointer_hand = None
                action_hand = None

            self.pointer_hand = pointer_hand
            self.action_hand = action_hand
            self.current_gesture = effective_gesture
            self.pinch_ratio = events.get("thumb_idx_ratio", 0.0) if events else 0.0
            self.pinch_pct = events.get("pinch_proximity_pct", 0.0) if events else 0.0

            # Radial In-Air Sector Selection & Execution
            if self.radial_menu_open and pointer_hand:
                ix, iy = pointer_hand.landmarks_px[INDEX_TIP]
                fh, fw = frame.shape[:2]
                cx, cy = fw // 2, fh // 2
                dx, dy = ix - cx, iy - cy
                dist = math.hypot(dx, dy)
                if dist > 28.0:
                    angle = (math.degrees(math.atan2(dy, dx)) + 90.0 + 360.0) % 360.0
                    self.active_radial_sector = int((angle + 22.5) % 360.0 // 45.0)
                else:
                    self.active_radial_sector = None

                is_click = (effective_gesture in (GestureType.THUMB_CLICK, GestureType.PINCH_CLICK, GestureType.AIR_TAP)) or events.get("trigger_left_click", False)
                if is_click and self.active_radial_sector is not None:
                    now_click = time.time()
                    if now_click - self.last_radial_action_time > 0.4:
                        self.last_radial_action_time = now_click
                        self._execute_radial_sector(self.active_radial_sector)
                        self.hud.trigger_click_ripple((ix, iy), is_right=False)
                        self.radial_menu_open = False
                        self.active_radial_sector = None
                        self.precision_engine.reset()

            # Execute mouse actions only if control is enabled and radial menu is not active
            if self.control_enabled and not self.radial_menu_open and pointer_hand and effective_gesture not in (GestureType.PAUSE, GestureType.NONE):
                hand_was_present = True
                raw_target_x, raw_target_y = events["cursor_target"]

                # Process through AeroPrecisionEngine with Click Anchor & Double-Click stabilization
                is_click_gesture = (effective_gesture in (GestureType.THUMB_CLICK, GestureType.PINCH_CLICK, GestureType.AIR_TAP))
                smooth_x, smooth_y = self.precision_engine.process(
                    target_x=raw_target_x,
                    target_y=raw_target_y,
                    pinch_ratio=self.pinch_ratio,
                    pinch_activate_ratio=self.config.pinch_activate_ratio,
                    pinch_release_ratio=self.config.pinch_release_ratio,
                    is_clicking=is_click_gesture,
                    click_mode=self.config.click_mode
                )

                self.hud.update_jitter_chart(raw_target_x, smooth_x)

                if effective_gesture != GestureType.SCROLL:
                    self.mouse.move_to(smooth_x, smooth_y)

                self.latest_air_tap_pct = events.get("air_tap_pct", 0.0)

                if self.is_rotary_tuning and self.mouse.is_dragging:
                    self.mouse.mouse_up("left")

                # 1. Drag & Drop handling (✊ Fist)
                if events.get("drag_active") and not self.is_rotary_tuning:
                    if not self.mouse.is_dragging:
                        self.mouse.mouse_down("left")
                else:
                    if self.mouse.is_dragging:
                        self.mouse.mouse_up("left")

                # 2. Discrete clicks are ONLY evaluated if NOT dragging and NOT holding a fist
                if not events.get("drag_active") and not self.mouse.is_dragging:
                    # Ripple origin: if action hand clicked, show ripple at action hand; else pointer hand
                    ripple_hand = action_hand if (action_hand and events.get("action_gesture") in (GestureType.THUMB_CLICK.value, GestureType.PINCH_CLICK.value)) else pointer_hand

                    if events.get("trigger_double_click"):
                        self.scroll_engine.brake()
                        self.precision_engine.lock_cursor(duration=0.25)
                        self.mouse.double_click("left")
                        click_pt = ripple_hand.landmarks_px[THUMB_TIP] if effective_gesture == GestureType.THUMB_CLICK else ripple_hand.landmarks_px[INDEX_TIP]
                        self.hud.trigger_click_ripple(click_pt, is_right=False)
                    elif events.get("trigger_left_click"):
                        self.scroll_engine.brake()
                        self.precision_engine.lock_cursor(duration=0.25)
                        self.mouse.click("left")
                        click_pt = ripple_hand.landmarks_px[THUMB_TIP] if effective_gesture == GestureType.THUMB_CLICK else ripple_hand.landmarks_px[INDEX_TIP]
                        self.hud.trigger_click_ripple(click_pt, is_right=False)

                    if events.get("trigger_right_click"):
                        self.scroll_engine.brake()
                        self.mouse.click("right")
                        self.hud.trigger_click_ripple(ripple_hand.landmarks_px[MIDDLE_TIP], is_right=True)

                    if events.get("trigger_middle_click"):
                        self.scroll_engine.brake()
                        self.mouse.click("middle")
                        self.hud.trigger_click_ripple(ripple_hand.landmarks_px[RING_TIP], is_right=False)

                    if events.get("trigger_task_switch"):
                        self.scroll_engine.brake()
                        self.mouse.task_view()
                        self.hud.trigger_click_ripple(ripple_hand.landmarks_px[PINKY_TIP], is_right=True)

                    if events.get("trigger_alt_tab"):
                        self.scroll_engine.brake()
                        self.mouse.alt_tab()
                        self.hud.trigger_click_ripple(ripple_hand.landmarks_px[INDEX_TIP], is_right=True)

                    if events.get("trigger_show_desktop"):
                        self.scroll_engine.brake()
                        self.mouse.show_desktop()
                        self.hud.trigger_click_ripple(ripple_hand.landmarks_px[PINKY_TIP], is_right=False)

                    if events.get("trigger_next_slide"):
                        self.scroll_engine.brake()
                        self.mouse.next_slide()
                        self.hud.trigger_slide_chevron(is_next=True)
                        self.hud.trigger_click_ripple(ripple_hand.landmarks_px[INDEX_TIP], is_right=False)

                    if events.get("trigger_prev_slide"):
                        self.scroll_engine.brake()
                        self.mouse.prev_slide()
                        self.hud.trigger_slide_chevron(is_next=False)
                        self.hud.trigger_click_ripple(ripple_hand.landmarks_px[INDEX_TIP], is_right=False)

                # 3. Spatial Rotary Volume Dial (twist wrist while holding pinch or fist)
                rotary_hand = action_hand if (action_hand and events.get("is_dual_hand")) else pointer_hand
                is_holding_action = (events.get("drag_active") or self.mouse.is_dragging or self.pinch_pct > 65.0 or effective_gesture in (GestureType.PINCH_CLICK, GestureType.THUMB_CLICK))

                if rotary_hand and is_holding_action:
                    curr_roll = getattr(rotary_hand, 'roll_deg', 0.0)
                    if self.rotary_anchor_roll is None:
                        self.rotary_anchor_roll = curr_roll
                    else:
                        d_roll = (curr_roll - self.rotary_anchor_roll + 180.0) % 360.0 - 180.0
                        if abs(d_roll) >= 12.0:
                            now_rot = time.time()
                            if now_rot - self.last_rotary_step_time >= 0.08:
                                self.last_rotary_step_time = now_rot
                                self.is_rotary_tuning = True
                                wrist_pos = (int(rotary_hand.landmarks_px[WRIST][0]), int(rotary_hand.landmarks_px[WRIST][1]))
                                if d_roll > 0:
                                    self.mouse.volume_up()
                                    self.hud.trigger_rotary_feedback(wrist_pos, is_up=True, delta_deg=d_roll)
                                    self.rotary_anchor_roll = curr_roll
                                else:
                                    self.mouse.volume_down()
                                    self.hud.trigger_rotary_feedback(wrist_pos, is_up=False, delta_deg=d_roll)
                                    self.rotary_anchor_roll = curr_roll
                else:
                    self.rotary_anchor_roll = None
                    self.is_rotary_tuning = False

                scroll_delta = events.get("scroll_delta", 0)
                if scroll_delta != 0:
                    self.mouse.scroll(scroll_delta)
                    self.scroll_engine.push(scroll_delta)
                else:
                    inertial_delta = self.scroll_engine.tick()
                    if inertial_delta != 0:
                        self.mouse.scroll(inertial_delta)

                zoom_delta = events.get("zoom_delta", 0)
                if zoom_delta != 0:
                    self.mouse.zoom(zoom_delta)
            else:
                self.latest_air_tap_pct = 0.0
                self.scroll_engine.brake()
                if self.mouse.is_dragging:
                    self.mouse.mouse_up("left")
                if hand_was_present:
                    self.precision_engine.reset()
                    hand_was_present = False

            # Spatial Air-Canvas Stream Annotator: record stroke when drawing
            if getattr(self.config, 'enable_air_draw_stream', False) and pointer_hand:
                is_drawing = (
                    events.get("drag_active", False)
                    or (self.pinch_ratio < self.config.pinch_activate_ratio)
                    or (effective_gesture in (GestureType.PINCH_CLICK, GestureType.AIR_TAP))
                )
                if is_drawing:
                    ix, iy = pointer_hand.landmarks_px[INDEX_TIP]
                    col_bgr = AIR_DRAW_COLOR_MAP.get(str(self.config.air_draw_color).lower(), (254, 242, 0))
                    self.hud.add_air_draw_point((int(ix), int(iy)), col_bgr)
                else:
                    self.hud.finish_air_draw_stroke()
            elif getattr(self.config, 'enable_air_draw_stream', False):
                self.hud.finish_air_draw_stroke()

            # Render clean video stream for GUI only when client is actively viewing
            loop_now = time.time()
            client_active = (loop_now - self.last_client_request_time) < 4.0
            if client_active and (loop_now - self.last_jpeg_time) >= 0.033:
                if self.active_tab == "iphone":
                    rendered = frame
                else:
                    calibration_prog = None
                    if loop_now < self.calibration_active_until:
                        elapsed = loop_now - self.calibration_start_time
                        total = max(0.1, self.calibration_active_until - self.calibration_start_time)
                        calibration_prog = min(1.0, elapsed / total)

                    edge_flags = None
                    if 'smooth_x' in locals() and 'smooth_y' in locals():
                        sw, sh = self.screen_size
                        e_l = (smooth_x <= 16)
                        e_r = (smooth_x >= sw - 16)
                        e_t = (smooth_y <= 16)
                        e_b = (smooth_y >= sh - 16)
                        if e_l or e_r or e_t or e_b:
                            edge_flags = (e_l, e_t, e_r, e_b)

                    rendered = self.hud.render_clean(
                        frame=frame,
                        hands=all_hands,
                        pointer_hand=pointer_hand,
                        action_hand=action_hand,
                        gesture=effective_gesture,
                        action_gesture=self.action_gesture,
                        show_skeleton=self.config.show_skeleton,
                        laser_pointer_mode=getattr(self.config, 'laser_pointer_mode', False),
                        calibration_progress=calibration_prog,
                        air_tap_pct=events.get("air_tap_pct", 0.0),
                        radial_menu_active=self.radial_menu_open,
                        active_radial_sector=self.active_radial_sector,
                        scroll_velocity=getattr(self.scroll_engine, 'velocity', 0.0),
                        edge_snap_flags=edge_flags
                    )

                # High performance JPEG encoding (quality 68 saves ~60% CPU)
                ret, jpeg = cv2.imencode('.jpg', rendered, [cv2.IMWRITE_JPEG_QUALITY, 68])
                if ret:
                    self.latest_jpeg = jpeg.tobytes()
                    self.frame_id += 1
                    self.last_jpeg_time = loop_now

            # Relinquish CPU slice to scheduler: dynamic power-saving pacing
            if self.is_power_saver:
                time.sleep(0.055)  # Throttled standby to ~15 FPS to conserve CPU and thermals
            else:
                time.sleep(0.001)  # Full unthrottled 60 FPS turbo

    def get_jpeg(self) -> Optional[bytes]:
        """Returns latest processed frame as JPEG bytes."""
        self.last_client_request_time = time.time()
        return self.latest_jpeg

    def get_latest_frame_data(self) -> Tuple[int, Optional[bytes]]:
        """Returns (frame_id, jpeg_bytes) to prevent redundant stream transmissions."""
        self.last_client_request_time = time.time()
        return self.frame_id, self.latest_jpeg

    def get_telemetry(self) -> Dict[str, any]:
        """Returns live metrics dictionary for GUI."""
        self.last_client_request_time = time.time()
        landmarks_3d = None
        if self.pointer_hand and hasattr(self.pointer_hand, 'landmarks_norm'):
            landmarks_3d = [[round(p[0], 3), round(p[1], 3), round(p[2], 3)] for p in self.pointer_hand.landmarks_norm]
        elif self.current_hands and len(self.current_hands) > 0 and hasattr(self.current_hands[0], 'landmarks_norm'):
            landmarks_3d = [[round(p[0], 3), round(p[1], 3), round(p[2], 3)] for p in self.current_hands[0].landmarks_norm]

        return {
            "fps": round(self.fps, 1),
            "latency_ms": round(self.latency_ms, 1),
            "cpu": round(self.hud.cached_cpu, 1),
            "hand_detected": self.hand_detected,
            "hands_count": len(self.current_hands),
            "is_dual_hand": self.is_dual_hand_active,
            "landmarks_3d": landmarks_3d,
            "enable_two_hands": self.config.enable_two_hands,
            "dominant_hand": self.config.dominant_hand,
            "gesture": self.current_gesture.value,
            "action_gesture": self.action_gesture.value if hasattr(self, "action_gesture") and self.action_gesture else "NONE",
            "control_enabled": self.control_enabled,
            "manual_pause": self.manual_pause,
            "active_camera_id": self.active_camera_id,
            "pinch_ratio": round(self.pinch_ratio, 2),
            "pinch_pct": round(self.pinch_pct, 1),
            "is_power_saver": self.is_power_saver,
            "enable_power_saver": getattr(self.config, 'enable_power_saver', True),
            "air_tap_pct": round(getattr(self, "latest_air_tap_pct", 0.0), 1),
            "velocity_px_s": round(getattr(self.hud, "smoothed_velocity", 0.0), 1),
            "click_mode": self.config.click_mode,
            "is_anchored": self.precision_engine.is_anchor_active,
            "precision_profile": getattr(self.precision_engine, 'profile', 'desktop'),
            "gain": round(self.precision_engine.current_gain, 2),
            "luminance": round(getattr(self.tracker, 'current_luminance', 120.0), 1),
            "is_night_mode": getattr(self.tracker, 'is_night_mode', False),
            "use_clahe": self.config.use_clahe,
            "show_skeleton": self.config.show_skeleton,
            "hud_theme": getattr(self.config, 'hud_theme', 'cyberpunk'),
            "enable_sound": self.config.enable_sound_feedback,
            "sound_enabled": getattr(self.config, 'sound_enabled', True),
            "sound_theme": getattr(self.config, 'sound_theme', 'quantum'),
            "sound_volume": getattr(self.config, 'sound_volume', 0.65),
            "enable_legacy_shortcuts": getattr(self.config, 'enable_legacy_shortcuts', False),
            "laser_pointer_mode": getattr(self.config, 'laser_pointer_mode', False),
            "enable_air_draw_stream": getattr(self.config, 'enable_air_draw_stream', False),
            "air_draw_color": getattr(self.config, 'air_draw_color', 'cyan'),
            "air_draw_strokes_count": len(getattr(self.hud, 'air_draw_strokes', [])),
            "enable_corner_snap": getattr(self.config, 'enable_corner_snap', True),
            "enable_distance_adaptation": getattr(self.config, 'enable_distance_adaptation', True),
            "enable_anchor": self.precision_engine.enable_click_anchor,
            "enable_acceleration": self.precision_engine.enable_acceleration,
            "deadzone": self.precision_engine.deadzone_radius,
            "sensitivity": round(getattr(self.config, 'sensitivity', 1.8), 2),
            "margin_x": round(self.config.margin_x, 2),
            "margin_y": round(self.config.margin_y, 2),
            "min_cutoff": round(self.precision_engine.one_euro.min_cutoff, 2),
            "active_monitor": self.mouse.active_monitor_index,
            "monitors": self.mouse.monitors,
            "distance_cm": round(getattr(self.pointer_hand or (self.current_hands[0] if self.current_hands else None), 'estimated_distance_cm', 50.0), 1) if (self.pointer_hand or self.current_hands) else 0.0,
            "roll_deg": round(getattr(self.pointer_hand or (self.current_hands[0] if self.current_hands else None), 'roll_deg', 0.0), 1) if (self.pointer_hand or self.current_hands) else 0.0,
            "radial_menu_open": self.radial_menu_open,
            "active_radial_sector": self.active_radial_sector,
            "active_tab": self.active_tab,
            "iphone_status": self.spatial_receiver.get_status()
        }
