"""
Web Server for AeroPoint Studio GUI
===================================
Serves the modern glassmorphic web interface and API endpoints:
- High-performance multi-threaded MJPEG video feed
- Single-frame snapshot endpoint (/api/frame.jpg) for fallback
- Camera enumeration and hot-switching
- Real-time gesture and telemetry state
"""

import os
import time
import json
import socket
import bottle
from wsgiref.simple_server import make_server, WSGIServer, WSGIRequestHandler
from socketserver import ThreadingMixIn
from typing import Optional

from camera_manager import CameraManager

# Locate web directory
WEB_DIR = os.path.join(os.path.dirname(__file__), "web")


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    """Multi-threaded WSGI server so streaming does not block API requests."""
    daemon_threads = True
    multithread = True


class ThreadingAdapter(bottle.ServerAdapter):
    """Custom Bottle server adapter using ThreadingWSGIServer."""
    def run(self, handler):
        class QuietHandler(WSGIRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress request spam

        server = make_server(
            self.host,
            self.port,
            handler,
            server_class=ThreadingWSGIServer,
            handler_class=QuietHandler
        )
        server.serve_forever()


def get_primary_lan_ip() -> str:
    """Discovers best local IPv4 address for mobile device connection."""
    try:
        hostname = socket.gethostname()
        ips = [ip for ip in socket.gethostbyname_ex(hostname)[2] if not ip.startswith('127.')]
        ips.sort(key=lambda x: (not x.startswith('192.168.'), not x.startswith('10.'), not x.startswith('172.'), x))
        return ips[0] if ips else '127.0.0.1'
    except Exception:
        return '127.0.0.1'


def create_app(manager: CameraManager) -> bottle.Bottle:
    app = bottle.Bottle()

    @app.route('/')
    def index():
        return bottle.static_file('index.html', root=WEB_DIR)

    @app.route('/mobile')
    def mobile_view():
        return bottle.static_file('mobile.html', root=WEB_DIR)

    @app.route('/download/ipa')
    def download_ipa():
        return bottle.static_file('AeroPointSpatial.ipa', root=os.path.dirname(__file__), download='AeroPointSpatial.ipa')

    @app.route('/api/open_ipa_folder', method='POST')
    def open_ipa_folder():
        try:
            ipa_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "AeroPointSpatial.ipa"))
            if os.path.exists(ipa_path):
                import subprocess
                subprocess.Popen(f'explorer /select,"{ipa_path}"')
                return {"status": "ok"}
            else:
                return {"status": "not_found"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @app.route('/<filename:path>')
    def static_files(filename):
        return bottle.static_file(filename, root=WEB_DIR)

    @app.route('/video_feed')
    def video_feed():
        """MJPEG video stream with standard boundaries and Content-Length."""
        bottle.response.content_type = 'multipart/x-mixed-replace; boundary=frame'
        bottle.response.set_header('Cache-Control', 'no-cache, private, no-store, must-revalidate')
        bottle.response.set_header('Pragma', 'no-cache')
        bottle.response.set_header('Expires', '0')

        def generate():
            last_id = -1
            while manager.running:
                fid, jpeg = manager.get_latest_frame_data()
                if fid != last_id and jpeg:
                    last_id = fid
                    yield (
                        b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n'
                        b'Content-Length: ' + str(len(jpeg)).encode() + b'\r\n\r\n'
                        + jpeg + b'\r\n'
                    )
                time.sleep(0.02)
        return generate()

    @app.route('/api/frame.jpg')
    def current_frame():
        """Snapshot endpoint for Canvas polling fallback."""
        jpeg = manager.get_jpeg()
        if not jpeg:
            bottle.response.status = 503
            return b''
        bottle.response.content_type = 'image/jpeg'
        bottle.response.set_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        bottle.response.set_header('Pragma', 'no-cache')
        return jpeg

    @app.route('/api/cameras', method='GET')
    def get_cameras():
        cams = manager.discover_cameras()
        return {
            "cameras": cams,
            "active_id": manager.active_camera_id
        }

    @app.route('/api/select_camera', method='POST')
    def select_camera():
        try:
            data = bottle.request.json or {}
            cam_id = int(data.get('camera_id', 0))
            success = manager.switch_camera(cam_id)
            return {"status": "ok" if success else "error", "active_id": manager.active_camera_id}
        except Exception as e:
            bottle.response.status = 400
            return {"status": "error", "message": str(e)}

    @app.route('/api/settings', method='POST')
    def update_settings():
        try:
            data = bottle.request.json or {}
            if "control_enabled" in data:
                manager.control_enabled = bool(data["control_enabled"])
            if "manual_pause" in data:
                manager.manual_pause = bool(data["manual_pause"])
            if "use_clahe" in data:
                manager.config.use_clahe = bool(data["use_clahe"])
            if "show_skeleton" in data:
                manager.config.show_skeleton = bool(data["show_skeleton"])
            if "enable_sound" in data:
                manager.config.enable_sound_feedback = bool(data["enable_sound"])
                manager.mouse.enable_sound = manager.config.enable_sound_feedback
            if "smoothing_alpha" in data:
                val = float(data["smoothing_alpha"])
                # Map slider [0.1 .. 1.5] to 1-Euro min_cutoff
                manager.precision_engine.one_euro.min_cutoff = val
                manager.precision_engine.one_euro.fx.min_cutoff = val
                manager.precision_engine.one_euro.fy.min_cutoff = val
            if "deadzone_radius" in data:
                manager.precision_engine.deadzone_radius = float(data["deadzone_radius"])
            if "enable_anchor" in data:
                manager.precision_engine.enable_click_anchor = bool(data["enable_anchor"])
            if "enable_acceleration" in data:
                manager.precision_engine.enable_acceleration = bool(data["enable_acceleration"])
            if "enable_two_hands" in data:
                manager.config.enable_two_hands = bool(data["enable_two_hands"])
            if "dominant_hand" in data:
                dom = str(data["dominant_hand"])
                if dom in ("Right", "Left"):
                    manager.config.dominant_hand = dom
            if "click_mode" in data:
                mode = str(data["click_mode"])
                if mode in ("thumb_bend", "pinch", "air_tap"):
                    manager.config.click_mode = mode
            if "presentation_mode_enabled" in data:
                manager.config.presentation_mode_enabled = bool(data["presentation_mode_enabled"])
            if "margin_x" in data:
                manager.config.margin_x = float(data["margin_x"])
            if "margin_y" in data:
                manager.config.margin_y = float(data["margin_y"])
            if "sensitivity" in data:
                manager.config.sensitivity = float(data["sensitivity"])
            if "pinch_activate_ratio" in data:
                manager.config.pinch_activate_ratio = float(data["pinch_activate_ratio"])
                manager.config.pinch_release_ratio = manager.config.pinch_activate_ratio + 0.12
            if "enable_corner_snap" in data:
                manager.config.enable_corner_snap = bool(data["enable_corner_snap"])
            if "enable_distance_adaptation" in data:
                manager.config.enable_distance_adaptation = bool(data["enable_distance_adaptation"])
            if "enable_legacy_shortcuts" in data:
                manager.config.enable_legacy_shortcuts = bool(data["enable_legacy_shortcuts"])
            if "laser_pointer_mode" in data:
                manager.config.laser_pointer_mode = bool(data["laser_pointer_mode"])
            if "enable_power_saver" in data:
                manager.config.enable_power_saver = bool(data["enable_power_saver"])
            if "precision_profile" in data:
                prof = str(data["precision_profile"])
                manager.config.precision_profile = prof
                manager.precision_engine.apply_profile(prof)
            if "sound_enabled" in data:
                manager.config.sound_enabled = bool(data["sound_enabled"])
            if "sound_theme" in data:
                manager.config.sound_theme = str(data["sound_theme"])
            if "sound_volume" in data:
                manager.config.sound_volume = float(data["sound_volume"])
            if "hud_theme" in data:
                theme = str(data["hud_theme"])
                manager.config.apply_hud_theme(theme)

            # Auto-persist user settings to disk
            manager.config.save_to_file()

            return {"status": "ok"}
        except Exception as e:
            bottle.response.status = 400
            return {"status": "error", "message": str(e)}

    @app.route('/api/radial/toggle', method='POST')
    def toggle_radial_menu():
        manager.toggle_radial_menu()
        return {"status": "ok", "radial_open": manager.radial_menu_open}

    @app.route('/api/radial/action', method='POST')
    def radial_action():
        try:
            data = bottle.request.json or {}
            action = str(data.get('action', '')).lower()
            mouse = manager.mouse
            if action in ('win_tab', 'task_view'):
                mouse.task_view()
            elif action in ('win_d', 'show_desktop', 'desktop'):
                mouse.show_desktop()
            elif action in ('alt_tab', 'switch_window'):
                mouse.alt_tab()
            elif action in ('snipping_tool', 'screenshot'):
                mouse.snipping_tool()
            elif action in ('volume_up', 'vol_up'):
                mouse.volume_up()
            elif action in ('volume_down', 'vol_down'):
                mouse.volume_down()
            elif action in ('volume_mute', 'mute'):
                mouse.volume_mute()
            elif action in ('play_pause', 'media'):
                mouse.play_pause()
            elif action in ('lock_pc', 'lock'):
                mouse.lock_workstation()
            elif action == 'zoom_in':
                mouse.zoom(1)
            elif action == 'zoom_out':
                mouse.zoom(-1)
            elif action == 'double_click':
                mouse.double_click('left')
            elif action in ('next_slide', 'next'):
                mouse.next_slide()
            elif action in ('prev_slide', 'prev'):
                mouse.prev_slide()
            elif action in ('snap_left', 'window_left'):
                mouse.snap_window_left()
            elif action in ('snap_right', 'window_right'):
                mouse.snap_window_right()
            elif action in ('snap_maximize', 'maximize'):
                mouse.snap_window_maximize()
            elif action in ('desktop_next', 'workspace_next'):
                mouse.switch_desktop_next()
            elif action in ('desktop_prev', 'workspace_prev'):
                mouse.switch_desktop_prev()
            elif action in ('copy', 'ctrl_c'):
                mouse.copy()
            elif action in ('paste', 'ctrl_v'):
                mouse.paste()
            elif action in ('undo', 'ctrl_z'):
                mouse.undo()
            elif action in ('search', 'win_s'):
                mouse.search_spotlight()
            elif action in ('refresh', 'f5', 'browser_refresh'):
                mouse.browser_refresh()
            else:
                return {"status": "error", "message": f"Unknown action: {action}"}
            return {"status": "ok", "action": action}
        except Exception as e:
            bottle.response.status = 400
            return {"status": "error", "message": str(e)}

    @app.route('/api/keyboard/press', method='POST')
    def keyboard_press():
        try:
            data = bottle.request.json or {}
            key = str(data.get('key', '')).strip()
            if not key:
                return {"status": "error", "message": "Key parameter required"}
            manager.mouse.press_key(key)
            return {"status": "ok", "key": key}
        except Exception as e:
            bottle.response.status = 400
            return {"status": "error", "message": str(e)}

    @app.route('/api/keyboard/type', method='POST')
    def keyboard_type():
        try:
            data = bottle.request.json or {}
            text = str(data.get('text', ''))
            if not text:
                return {"status": "error", "message": "Text parameter required"}
            manager.mouse.type_text(text)
            return {"status": "ok", "length": len(text)}
        except Exception as e:
            bottle.response.status = 400
            return {"status": "error", "message": str(e)}

    @app.route('/api/spatial/mirror', method='POST')
    def toggle_spatial_mirror():
        try:
            data = bottle.request.json or {}
            if "mirror" in data or "force_mirror" in data:
                val = data.get("mirror") if "mirror" in data else data.get("force_mirror")
                manager.spatial_receiver.force_mirror_x = bool(val)
            else:
                cur = manager.spatial_receiver.force_mirror_x
                manager.spatial_receiver.force_mirror_x = not cur if cur is not None else True
            return {"status": "ok", "mirror_x": manager.spatial_receiver.force_mirror_x}
        except Exception as e:
            bottle.response.status = 400
            return {"status": "error", "message": str(e)}

    @app.route('/api/calibration/start', method='POST')
    def start_calibration():
        try:
            manager.trigger_calibration(duration=3.0)
            return {"status": "ok", "duration": 3.0}
        except Exception as e:
            bottle.response.status = 400
            return {"status": "error", "message": str(e)}

    @app.route('/api/switch_tab', method='POST')
    def switch_tab():
        try:
            data = bottle.request.json or {}
            tab = str(data.get('tab', 'webcam')).lower()
            if tab in ('webcam', 'iphone'):
                manager.active_tab = tab
                return {"status": "ok", "active_tab": manager.active_tab}
            return {"status": "error", "message": "Invalid tab"}
        except Exception as e:
            bottle.response.status = 400
            return {"status": "error", "message": str(e)}

    @app.route('/api/spatial/status', method='GET')
    def spatial_status():
        return manager.spatial_receiver.get_status()

    @app.route('/api/monitors', method='GET')
    def get_monitors():
        return {
            "monitors": manager.mouse.enumerate_monitors(),
            "active_monitor": manager.mouse.active_monitor_index
        }

    @app.route('/api/monitors/switch', method='POST')
    def switch_monitor():
        try:
            data = bottle.request.json or {}
            idx = int(data.get('monitor_id', -1))
            res = manager.switch_monitor(idx)
            return {"status": "ok", "active_monitor": res}
        except Exception as e:
            bottle.response.status = 400
            return {"status": "error", "message": str(e)}

    @app.route('/api/lan_info', method='GET')
    def lan_info():
        ip = get_primary_lan_ip()
        host_header = bottle.request.get_header('Host', '')
        port = 5055
        if ':' in host_header:
            try:
                port = int(host_header.split(':')[-1])
            except Exception:
                port = 5055
        return {
            "ip": ip,
            "port": port,
            "mobile_url": f"http://{ip}:{port}/mobile"
        }

    @app.route('/api/spatial_feed', method=['POST', 'OPTIONS'])
    def spatial_feed():
        bottle.response.set_header('Access-Control-Allow-Origin', '*')
        bottle.response.set_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        bottle.response.set_header('Access-Control-Allow-Headers', 'Content-Type')
        if bottle.request.method == 'OPTIONS':
            return {}
        try:
            payload = bottle.request.json or {}
            client_ip = bottle.request.environ.get('REMOTE_ADDR', 'Web-Safari')
            manager.spatial_receiver.feed_web_payload(payload, client_ip)
            return {"status": "ok"}
        except Exception as e:
            bottle.response.status = 400
            return {"status": "error", "message": str(e)}

    @app.route('/api/status', method='GET')
    def get_status():
        return manager.get_telemetry()

    @app.route('/api/stream_events')
    def stream_events():
        bottle.response.content_type = 'text/event-stream'
        bottle.response.headers['Cache-Control'] = 'no-cache'
        bottle.response.headers['Access-Control-Allow-Origin'] = '*'

        def event_generator():
            while True:
                try:
                    status_dict = manager.get_telemetry()
                    yield f"data: {json.dumps(status_dict)}\n\n"
                    time.sleep(0.04)
                except Exception:
                    break

        return event_generator()

    return app
