"""
Main Application Entry Point
============================
Бесконтактное управление компьютером на базе жестов и ИИ (AI Hand Tracking HCI).
According to specifications in ai_studio_code (1).html.
"""

import sys
import os

# Prevent OpenCV FFMPEG crash (exception 0x40000015) on Windows
os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"
os.environ["OPENCV_VIDEOIO_PRIORITY_FFMPEG"] = "0"

import time
import argparse
import cv2

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config import GestureConfig
from mouse_controller import MouseController
from hand_tracker import HandTracker, THUMB_TIP, INDEX_TIP, MIDDLE_TIP
from gestures import GestureRecognizer, GestureType
from filters import EMAFilter, AdaptiveEMAFilter, DeadzoneFilter
from hud import CyberHUD


def print_banner():
    banner = r"""
========================================================================
     _    ___    ____         _                    _   _  ____ ___ 
    / \  |_ _|  / ___|___  __| |_   _ _ __ ___    | | | |/ ___|_ _|
   / _ \  | |  | |  _/ _ \/ _` | | | | '__/ _ \   | |_| | |    | | 
  / ___ \ | |  | |_|  __/ (_| | |_| | | |  __/   |  _  | |___ | | 
 /_/   \_\___|  \____\___|\__,_|\__,_|_|  \___|___|_| |_|\____|___|
                                             |_____|               
  Next-Gen Zero-Cost AI Gesture Human-Computer Interface (HCI)
========================================================================
  [Q / ESC] : Quit application
  [C]       : Toggle CLAHE contrast enhancement (Low-light mode)
  [H]       : Toggle Cyberpunk HUD overlay
  [S]       : Toggle 21-joint Skeleton
  [P]       : Toggle Manual Pause / Safety Lock
  [R]       : Reset smoothing filters
========================================================================
"""
    print(banner)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Gesture PC Control")
    parser.add_argument("--gui", action="store_true", help="Launch modern AeroPoint GUI application")
    parser.add_argument("--camera", type=int, default=0, help="Camera device index (default: 0)")
    parser.add_argument("--width", type=int, default=640, help="Camera capture width (default: 640)")
    parser.add_argument("--height", type=int, default=480, help="Camera capture height (default: 480)")
    parser.add_argument("--filter", type=str, default="adaptive_ema", choices=["ema", "adaptive_ema", "none"],
                        help="Jitter reduction filter type (default: adaptive_ema)")
    parser.add_argument("--clahe", action="store_true", help="Enable CLAHE illumination normalization by default")
    parser.add_argument("--no-sound", action="store_true", help="Disable audio feedback on click")
    parser.add_argument("--no-hud", action="store_true", help="Start with HUD overlay disabled")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.gui:
        import app
        app.main()
        return

    print_banner()

    # 1. Initialize Configuration
    config = GestureConfig()
    config.camera_id = args.camera
    config.cam_width = args.width
    config.cam_height = args.height
    config.use_clahe = args.clahe
    config.enable_sound_feedback = not args.no_sound
    config.show_hud = not args.no_hud

    # 2. Initialize Subsystems
    mouse = MouseController(enable_sound=config.enable_sound_feedback)
    screen_size = (mouse.screen_width, mouse.screen_height)
    print(f"[*] Detected Primary Display: {screen_size[0]}x{screen_size[1]} px")

    # Anti-jitter filters
    if args.filter == "adaptive_ema":
        jitter_filter = AdaptiveEMAFilter(
            min_alpha=config.ema_min_alpha,
            max_alpha=config.ema_max_alpha,
            velocity_scale=config.velocity_scale
        )
    elif args.filter == "ema":
        jitter_filter = EMAFilter(alpha=config.ema_alpha)
    else:
        jitter_filter = None

    deadzone_filter = DeadzoneFilter(radius=config.deadzone_radius)

    # Hand tracker and gesture engine
    print("[*] Initializing MediaPipe HandLandmarker...")
    tracker = HandTracker(config)
    recognizer = GestureRecognizer(config, screen_size)
    hud = CyberHUD(config)

    # 3. Video Capture Initialization
    print(f"[*] Opening Video Camera #{config.camera_id}...")
    cap = cv2.VideoCapture(config.camera_id, cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY)
    if not cap.isOpened():
        print(f"[!] Warning: DirectShow failed, trying default backend...")
        cap = cv2.VideoCapture(config.camera_id)

    if not cap.isOpened():
        print(f"[ERROR] Could not open camera {config.camera_id}. Please check webcam connection.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.cam_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.cam_height)
    cap.set(cv2.CAP_PROP_FPS, config.target_fps)

    window_name = "AI Gesture PC Control - [ESC / Q to Exit]"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    print("[*] Gesture System is ACTIVE. Place hand in camera view.\n")

    manual_pause = False
    hand_was_present = False

    try:
        while True:
            ret, raw_frame = cap.read()
            if not ret or raw_frame is None:
                time.sleep(0.01)
                continue

            # Process frame through MediaPipe
            frame, hand_data = tracker.process(raw_frame)

            # Manual Pause override
            if manual_pause:
                effective_gesture = GestureType.PAUSE
                events = {"trigger_left_click": False, "trigger_right_click": False, "drag_active": False, "scroll_delta": 0}
            else:
                effective_gesture, events = recognizer.update(hand_data, frame.shape[:2])

            curr_alpha = getattr(jitter_filter, "last_alpha", config.ema_alpha) if jitter_filter else 1.0

            # Execute Mouse Actions
            if hand_data is not None and effective_gesture != GestureType.PAUSE and effective_gesture != GestureType.NONE:
                hand_was_present = True
                raw_target_x, raw_target_y = events["cursor_target"]

                # Step 1: Smooth with Jitter Filter (EMA / Adaptive EMA)
                if jitter_filter:
                    filt_x, filt_y = jitter_filter.filter(raw_target_x, raw_target_y)
                else:
                    filt_x, filt_y = raw_target_x, raw_target_y

                # Step 2: Apply Deadzone (Slide 16)
                smooth_x, smooth_y = deadzone_filter.filter(filt_x, filt_y)

                # Feed telemetry chart (X-coordinate raw vs smoothed)
                hud.update_jitter_chart(raw_target_x, smooth_x)

                # Move cursor unless in scroll mode (so scrolling stays fixed)
                if effective_gesture != GestureType.SCROLL:
                    mouse.move_to(smooth_x, smooth_y)

                # --- Handle Clicks & Gestures ---
                if events.get("trigger_left_click"):
                    mouse.click("left")
                    click_pt = hand_data.landmarks_px[THUMB_TIP] if effective_gesture == GestureType.THUMB_CLICK else hand_data.landmarks_px[INDEX_TIP]
                    hud.trigger_click_ripple(click_pt, is_right=False)

                if events.get("trigger_right_click"):
                    mouse.click("right")
                    hud.trigger_click_ripple(hand_data.landmarks_px[MIDDLE_TIP], is_right=True)

                # Drag & Drop handling (Slide 14)
                if events.get("drag_active"):
                    if not mouse.is_dragging:
                        mouse.mouse_down("left")
                else:
                    if mouse.is_dragging:
                        mouse.mouse_up("left")

                # Scrolling handling (Slide 14)
                scroll_delta = events.get("scroll_delta", 0)
                if scroll_delta != 0:
                    mouse.scroll(scroll_delta)

            else:
                # Hand lost or pause mode
                if mouse.is_dragging:
                    mouse.mouse_up("left")
                if hand_was_present:
                    if jitter_filter:
                        jitter_filter.reset()
                    deadzone_filter.reset()
                    hand_was_present = False

            # Render HUD elements
            frame = hud.render(
                frame=frame,
                hand=hand_data,
                gesture=effective_gesture,
                fps=tracker.fps,
                latency_ms=tracker.latency_ms,
                filter_alpha=curr_alpha
            )

            cv2.imshow(window_name, frame)

            # Keyboard Input Handling
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q'), ord('Q')):
                print("[*] Exiting application...")
                break
            elif key in (ord('c'), ord('C')):
                config.use_clahe = not config.use_clahe
                print(f"[!] CLAHE Illumination Mode: {'ON' if config.use_clahe else 'OFF'}")
            elif key in (ord('h'), ord('H')):
                config.show_hud = not config.show_hud
            elif key in (ord('s'), ord('S')):
                config.show_skeleton = not config.show_skeleton
            elif key in (ord('p'), ord('P')):
                manual_pause = not manual_pause
                print(f"[!] Manual Safety Pause: {'LOCKED' if manual_pause else 'UNLOCKED'}")
            elif key in (ord('r'), ord('R')):
                if jitter_filter:
                    jitter_filter.reset()
                deadzone_filter.reset()
                print("[!] Filters reset.")

    finally:
        if mouse.is_dragging:
            mouse.mouse_up("left")
        cap.release()
        cv2.destroyAllWindows()
        print("[*] Clean shutdown completed.")


if __name__ == "__main__":
    main()
