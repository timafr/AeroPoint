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


class CameraManager:
    """Thread-safe multi-camera and gesture processing orchestrator."""
    def __init__(self, config: Optional[GestureConfig] = None):
        self.config = config or GestureConfig()
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
        self.scroll_engine = InertialScrollEngine()

        # Hand tracking & recognition
        self.tracker = HandTracker(self.config)
        self.recognizer = GestureRecognizer(self.config, self.screen_size, self.screen_origin)
        self.hud = CyberHUD(self.config)

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
        self.fps = 0.0
        self.latency_ms = 0.0
        self.cpu_percent = 0.0

        # Video capture handle
        self.cap: Optional[cv2.VideoCapture] = None
        self.worker_thread: Optional[threading.Thread] = None

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

    def discover_cameras(self, max_test: int = 4) -> List[Dict[str, any]]:
        """Scans and discovers real hardware cameras using DirectShow device registry."""
        results = []
        system_names = get_system_camera_names()

        if system_names:
            for idx, dev_name in enumerate(system_names[:max_test]):
                results.append({
                    "id": idx,
                    "label": dev_name,
                    "resolution": f"{self.config.cam_width}x{self.config.cam_height}"
                })
        else:
            for idx in range(max_test):
                try:
                    backend = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY
                    cap = cv2.VideoCapture(idx, backend)
                    if cap and cap.isOpened():
                        results.append({
                            "id": idx,
                            "label": f"Camera #{idx}",
                            "resolution": f"{self.config.cam_width}x{self.config.cam_height}"
                        })
                        cap.release()
                except Exception:
                    pass

        if not results:
            results.append({"id": 0, "label": "Default Camera", "resolution": "640x480"})

        self.discovered_cameras = results
        return results

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

    def start(self):
        """Starts background capture and processing thread."""
        if self.running:
            return
        self.running = True
        self.worker_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.worker_thread.start()

    def stop(self):
        """Stops background loop and releases devices."""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        with self.lock:
            if self.cap:
                self.cap.release()
                self.cap = None
        if self.mouse.is_dragging:
            self.mouse.mouse_up("left")
        self.spatial_receiver.stop()

    def _capture_loop(self):
        """Continuous camera capture and gesture execution loop."""
        with self.lock:
            self.cap = self._open_capture(self.active_camera_id)

        hand_was_present = False
        consecutive_fails = 0

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
                raw_frame = None
                ret = False
                with self.lock:
                    if not self.cap or not self.cap.isOpened():
                        time.sleep(0.05)
                        continue
                    try:
                        ret, raw_frame = self.cap.read()
                    except Exception:
                        ret = False
                        raw_frame = None

                if not ret or raw_frame is None:
                    consecutive_fails += 1
                    if consecutive_fails > 10:
                        time.sleep(0.1)
                    else:
                        time.sleep(0.01)
                    continue

                consecutive_fails = 0

                # Process frame through MediaPipe (supports 1 or 2 hands)
                frame, primary_hand, all_hands = self.tracker.process(raw_frame)

                self.hand_detected = (len(all_hands) > 0)
                self.current_hands = all_hands
                self.fps = self.tracker.fps
                self.latency_ms = self.tracker.latency_ms

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

            # Execute mouse actions only if control is enabled
            if self.control_enabled and pointer_hand and effective_gesture not in (GestureType.PAUSE, GestureType.NONE):
                hand_was_present = True
                raw_target_x, raw_target_y = events["cursor_target"]

                # Process through AeroPrecisionEngine with Click Anchor & Double-Click stabilization
                is_click_gesture = (effective_gesture in (GestureType.THUMB_CLICK, GestureType.PINCH_CLICK))
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

                # 1. Drag & Drop handling (✊ Fist)
                if events.get("drag_active"):
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

                scroll_delta = events.get("scroll_delta", 0)
                if scroll_delta != 0:
                    self.mouse.scroll(scroll_delta)
                    self.scroll_engine.push(scroll_delta)
                else:
                    inertial_delta = self.scroll_engine.tick()
                    if inertial_delta != 0:
                        self.mouse.scroll(inertial_delta)
            else:
                self.scroll_engine.brake()
                if self.mouse.is_dragging:
                    self.mouse.mouse_up("left")
                if hand_was_present:
                    self.precision_engine.reset()
                    hand_was_present = False

            # Render clean video stream for GUI only when client is actively viewing
            loop_now = time.time()
            client_active = (loop_now - self.last_client_request_time) < 4.0
            if client_active and (loop_now - self.last_jpeg_time) >= 0.033:
                if self.active_tab == "iphone":
                    rendered = frame
                else:
                    rendered = self.hud.render_clean(
                        frame=frame,
                        hands=all_hands,
                        pointer_hand=pointer_hand,
                        action_hand=action_hand,
                        gesture=effective_gesture,
                        action_gesture=self.action_gesture,
                        show_skeleton=self.config.show_skeleton
                    )

                # High performance JPEG encoding (quality 68 saves ~60% CPU)
                ret, jpeg = cv2.imencode('.jpg', rendered, [cv2.IMWRITE_JPEG_QUALITY, 68])
                if ret:
                    self.latest_jpeg = jpeg.tobytes()
                    self.frame_id += 1
                    self.last_jpeg_time = loop_now

            # Relinquish CPU slice to Windows scheduler to prevent high CPU consumption
            time.sleep(0.001)

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
        return {
            "fps": round(self.fps, 1),
            "latency_ms": round(self.latency_ms, 1),
            "cpu": round(self.hud.cached_cpu, 1),
            "hand_detected": self.hand_detected,
            "hands_count": len(self.current_hands),
            "is_dual_hand": self.is_dual_hand_active,
            "enable_two_hands": self.config.enable_two_hands,
            "dominant_hand": self.config.dominant_hand,
            "gesture": self.current_gesture.value,
            "action_gesture": self.action_gesture.value if hasattr(self, "action_gesture") and self.action_gesture else "NONE",
            "control_enabled": self.control_enabled,
            "manual_pause": self.manual_pause,
            "active_camera_id": self.active_camera_id,
            "pinch_ratio": round(self.pinch_ratio, 2),
            "pinch_pct": round(self.pinch_pct, 1),
            "click_mode": self.config.click_mode,
            "is_anchored": self.precision_engine.is_anchor_active,
            "gain": round(self.precision_engine.current_gain, 2),
            "use_clahe": self.config.use_clahe,
            "show_skeleton": self.config.show_skeleton,
            "enable_sound": self.config.enable_sound_feedback,
            "sound_enabled": getattr(self.config, 'sound_enabled', True),
            "sound_theme": getattr(self.config, 'sound_theme', 'quantum'),
            "sound_volume": getattr(self.config, 'sound_volume', 0.65),
            "enable_legacy_shortcuts": getattr(self.config, 'enable_legacy_shortcuts', False),
            "laser_pointer_mode": getattr(self.config, 'laser_pointer_mode', False),
            "enable_anchor": self.precision_engine.enable_click_anchor,
            "enable_acceleration": self.precision_engine.enable_acceleration,
            "deadzone": self.precision_engine.deadzone_radius,
            "sensitivity": round(getattr(self.config, 'sensitivity', 1.8), 2),
            "margin_x": round(self.config.margin_x, 2),
            "margin_y": round(self.config.margin_y, 2),
            "min_cutoff": round(self.precision_engine.one_euro.min_cutoff, 2),
            "active_tab": self.active_tab,
            "iphone_status": self.spatial_receiver.get_status()
        }
