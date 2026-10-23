"""
AeroPoint Studio — Neural Gesture Application Launcher
======================================================
Launches the sleek AeroPoint Spatial Desktop App with Motion Design.
Supports dynamic camera switching, live viewfinder, telemetry, and kinetic gesture tuning.
"""

import sys
import os

# Prevent OpenCV FFMPEG crash (exception 0x40000015) on Windows
os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"
os.environ["OPENCV_VIDEOIO_PRIORITY_FFMPEG"] = "0"

import time
import threading
import argparse
import webbrowser
import bottle

from config import GestureConfig
from camera_manager import CameraManager
from server import create_app, ThreadingAdapter

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def parse_args():
    parser = argparse.ArgumentParser(description="AeroPoint Studio — Neural Gesture Control")
    parser.add_argument("--camera", type=int, default=0, help="Initial camera ID (default: 0)")
    parser.add_argument("--port", type=int, default=5055, help="Local server port (default: 5055)")
    parser.add_argument("--browser", action="store_true", help="Open in standard browser instead of native window")
    return parser.parse_args()


def main():
    args = parse_args()

    print("=================================================================")
    print("       ✦ AeroPoint Studio — Neural Gesture Interface             ")
    print("=================================================================")
    print(f"[*] Initializing vision pipeline on Camera #{args.camera}...")

    config = GestureConfig()
    config.camera_id = args.camera
    manager = CameraManager(config)

    # Start camera and ML inference
    manager.start()

    # Create bottle app
    app = create_app(manager)

    # Start web server in background thread
    server_url = f"http://127.0.0.1:{args.port}"
    server_thread = threading.Thread(
        target=lambda: bottle.run(app, server=ThreadingAdapter(host='127.0.0.1', port=args.port)),
        daemon=True
    )
    server_thread.start()
    print(f"[*] AeroPoint Studio Server running at: {server_url}")

    # Launch UI
    if args.browser:
        print("[*] Opening in system browser...")
        webbrowser.open(server_url)
        print("[*] Press Ctrl+C in terminal to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Shutting down...")
    else:
        try:
            import webview
            print("[*] Launching native AeroPoint Glassmorphic Window...")
            window = webview.create_window(
                title="AeroPoint Studio — Neural Gesture Control",
                url=server_url,
                width=1280,
                height=840,
                min_size=(980, 640),
                background_color='#090a0f',
                text_select=False
            )
            webview.start()
        except Exception as e:
            print(f"[!] PyWebView failed ({e}), opening in default browser instead...")
            webbrowser.open(server_url)
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass

    # Cleanup
    print("[*] Stopping camera manager and releasing devices...")
    manager.stop()
    print("[✓] AeroPoint Studio shut down cleanly.")


if __name__ == "__main__":
    main()
