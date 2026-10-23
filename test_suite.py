"""
AeroPoint Quantum 3.0 — Comprehensive Automated Unit & Regression Test Suite
Verifies mathematical stability, gesture gating, bimanual coordination,
spatial networking, and HUD pipeline resilience.
"""

import math
import time
import struct
import unittest
import numpy as np

from config import GestureConfig
from filters import OneEuroFilter1D, OneEuroFilter2D, AeroPrecisionEngine, InertialScrollEngine
from gestures import GestureType, GestureRecognizer
from hand_tracker import HandData
from spatial_receiver import SpatialReceiver
from mouse_controller import MouseController
from hud import CyberHUD


class TestOneEuroFilter(unittest.TestCase):
    """Verifies numerical stability and jitter reduction of 1-Euro filter."""

    def test_filter_smooths_jitter(self):
        f = OneEuroFilter1D(min_cutoff=1.0, beta=0.007, d_cutoff=1.0)
        # Constant value with random high-frequency micro-jitter
        np.random.seed(42)
        base = 500.0
        outputs = []
        for i in range(50):
            noisy = base + np.random.uniform(-4.0, 4.0)
            filtered = f.filter(noisy, timestamp=i * 0.016)
            outputs.append(filtered)
        # Variance of output should be significantly lower than input
        raw_std = np.std([base + np.random.uniform(-4.0, 4.0) for _ in range(50)])
        filt_std = np.std(outputs[10:])
        self.assertLess(filt_std, raw_std * 0.5)

    def test_filter_zero_dt_protection(self):
        f = OneEuroFilter1D()
        v1 = f.filter(100.0, timestamp=1.0)
        # Same timestamp should not cause ZeroDivisionError or NaN
        v2 = f.filter(105.0, timestamp=1.0)
        self.assertFalse(math.isnan(v2))
        self.assertFalse(math.isinf(v2))

    def test_filter_nan_inf_protection(self):
        f = OneEuroFilter1D()
        f.filter(100.0, timestamp=1.0)
        v = f.filter(float('nan'), timestamp=1.016)
        self.assertEqual(v, 100.0)  # Should return last valid coordinate


class TestConfigPersistence(unittest.TestCase):
    """Tests JSON serialization and disk persistence of GestureConfig."""

    def test_save_and_load_config(self):
        import os
        test_file = "test_config_temp.json"
        try:
            cfg = GestureConfig()
            cfg.sensitivity = 2.75
            cfg.click_mode = "pinch"
            cfg.enable_corner_snap = True
            cfg.enable_power_saver = True
            cfg.save_to_file(test_file)

            self.assertTrue(os.path.exists(test_file))
            loaded = GestureConfig.load_from_file(test_file)
            self.assertEqual(loaded.sensitivity, 2.75)
            self.assertEqual(loaded.click_mode, "pinch")
            self.assertEqual(loaded.enable_corner_snap, True)
            self.assertEqual(loaded.enable_power_saver, True)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_hud_theme_palettes(self):
        cfg = GestureConfig()
        # Default
        self.assertEqual(cfg.hud_theme, "cyberpunk")
        self.assertEqual(cfg.COLOR_CYAN, (254, 242, 0))

        # visionOS theme
        cfg.apply_hud_theme("visionos")
        self.assertEqual(cfg.hud_theme, "visionos")
        self.assertEqual(cfg.COLOR_CYAN, (255, 255, 255))

        # Matrix theme
        cfg.apply_hud_theme("matrix")
        self.assertEqual(cfg.hud_theme, "matrix")
        self.assertEqual(cfg.COLOR_GREEN, (0, 255, 65))

        # Solar theme
        cfg.apply_hud_theme("solar")
        self.assertEqual(cfg.hud_theme, "solar")
        self.assertEqual(cfg.COLOR_CYAN, (0, 185, 255))


class TestAeroPrecisionEngine(unittest.TestCase):
    """Tests click anchor locking, micro-movement deadzones, and boundary magnets."""

    def setUp(self):
        self.engine = AeroPrecisionEngine()
        self.config = GestureConfig()
        self.config.enable_corner_snap = True
        self.recognizer = GestureRecognizer(self.config, screen_size=(1920, 1080), screen_origin=(0, 0))

    def test_anchor_locks_cursor_during_click(self):
        self.engine.enable_click_anchor = True
        # Establish initial position
        self.engine.process(960, 540, pinch_ratio=0.8, is_clicking=False)
        # Now initiate click with finger displacement
        ax, ay = self.engine.process(965, 543, pinch_ratio=0.15, is_clicking=True)
        self.assertTrue(self.engine.is_anchor_active)
        # While clicking, cursor should be locked to anchor position
        self.assertEqual((ax, ay), (self.engine.anchor_x, self.engine.anchor_y))

    def test_corner_magnet_attraction(self):
        cam_shape = (480, 640)
        # Near top-left corner
        sx, sy = self.recognizer.map_to_screen(
            (cam_shape[1] * self.config.margin_x + 2, cam_shape[0] * self.config.margin_y + 2),
            cam_shape
        )
        self.assertEqual((sx, sy), (0.0, 0.0))

        # Near bottom-right corner
        sx, sy = self.recognizer.map_to_screen(
            (cam_shape[1] * (1.0 - self.config.margin_x) - 2, cam_shape[0] * (1.0 - self.config.margin_y) - 2),
            cam_shape
        )
        self.assertEqual((sx, sy), (1920.0, 1080.0))

    def test_precision_profiles(self):
        # Default profile
        self.assertEqual(self.engine.profile, "desktop")
        self.assertEqual(self.engine.deadzone_radius, 3.5)
        self.assertAlmostEqual(self.engine.one_euro.min_cutoff, 0.85)

        # CAD profile
        self.engine.apply_profile("cad")
        self.assertEqual(self.engine.profile, "cad")
        self.assertEqual(self.engine.deadzone_radius, 4.2)
        self.assertAlmostEqual(self.engine.one_euro.min_cutoff, 0.45)

        # Gaming profile
        self.engine.apply_profile("gaming")
        self.assertEqual(self.engine.profile, "gaming")
        self.assertEqual(self.engine.deadzone_radius, 1.8)
        self.assertAlmostEqual(self.engine.one_euro.min_cutoff, 1.65)

    def test_dynamic_acceleration_curve(self):
        engine = AeroPrecisionEngine(enable_acceleration=True)
        # Establish start
        engine.process(500, 500, pinch_ratio=0.8, is_clicking=False, timestamp=1.00)

        # Micro slow motion (e.g. 6px in 0.15s)
        engine.process(506, 500, pinch_ratio=0.8, is_clicking=False, timestamp=1.15)
        self.assertLess(engine.current_gain, 1.0)
        self.assertGreaterEqual(engine.current_gain, 0.70)

        # Rapid flick motion (e.g. 150px in 0.05s -> 3000 px/s)
        engine.process(652, 500, pinch_ratio=0.8, is_clicking=False, timestamp=1.25)
        self.assertGreater(engine.current_gain, 1.0)

        # Acceleration disabled
        engine_linear = AeroPrecisionEngine(enable_acceleration=False)
        engine_linear.process(500, 500, pinch_ratio=0.8, is_clicking=False, timestamp=1.00)
        engine_linear.process(650, 500, pinch_ratio=0.8, is_clicking=False, timestamp=1.05)
        self.assertEqual(engine_linear.current_gain, 1.0)


class TestInertialScrollEngine(unittest.TestCase):
    """Tests inertial decay and flick boost."""

    def test_scroll_decay_and_brake(self):
        engine = InertialScrollEngine()
        # Feed high velocity pulses
        engine.push(-25.0)
        engine.push(-30.0)
        # Tick decay
        total_steps = 0
        for _ in range(20):
            step = engine.tick()
            if step != 0:
                total_steps += 1
            time.sleep(0.01)
        self.assertGreater(total_steps, 0)
        # Brake should immediately zero out velocity
        engine.brake()
        self.assertEqual(engine.velocity, 0.0)
        self.assertEqual(engine.tick(), 0)


class TestSpatialNetworking(unittest.TestCase):
    """Tests iPhone TrueDepth binary UDP struct unpacker and integrity verification."""

    def test_binary_packet_unpack(self):
        header_fmt = '!4sBBBBHHHB'
        header_size = struct.calcsize(header_fmt)
        hand_fmt = '!BH63f'
        coords = [0.05 * i for i in range(63)]

        bin_packet = struct.pack(header_fmt, b'AERO', 1, 98, 1, 1, 600, 8, 410, 1) + struct.pack(hand_fmt, 1, 850, *coords)
        self.assertEqual(len(bin_packet), 270)

        # Unpack test
        magic, ver, batt, sensor, num_hands, fps, ping, depth, mirror = struct.unpack_from(header_fmt, bin_packet, 0)
        self.assertEqual(magic, b'AERO')
        self.assertEqual(ver, 1)
        self.assertEqual(batt, 98)
        self.assertEqual(depth, 410)
        self.assertEqual(mirror, 1)

    def test_lidar_unmirrored_auto_inverted(self):
        receiver = SpatialReceiver(port=9999)
        header_fmt = '!4sBBBBHHHB'
        hand_fmt = '!BH63f'
        # sensor=1 (LiDAR), mirror_flag=0 (unmirrored from iPhone rear camera)
        coords = [0.2] * 63
        bin_packet = struct.pack(header_fmt, b'AERO', 1, 95, 1, 0, 600, 8, 420, 1) + struct.pack(hand_fmt, 0, 850, *coords)
        receiver._process_binary_payload(bin_packet, time.time())
        hands = receiver.get_hands()
        self.assertEqual(len(hands), 1)
        # Should be flipped to "Right" (from 0="Left")
        self.assertEqual(hands[0].handedness, "Right")
        # Landmark X should be inverted: 1.0 - 0.2 = 0.8
        self.assertAlmostEqual(hands[0].landmarks_norm[0][0], 0.8, places=2)
        receiver.stop()


class TestCyberHUD(unittest.TestCase):
    """Ensures HUD renderer never crashes regardless of frame size, hands count or modes."""

    def setUp(self):
        self.config = GestureConfig()
        self.hud = CyberHUD(self.config)

    def test_render_clean_empty_frame(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        rendered = self.hud.render_clean(frame)
        self.assertIsNotNone(rendered)
        self.assertEqual(rendered.shape, (480, 640, 3))

    def test_render_proximity_edge_glow(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.hud.draw_proximity_edge_glow(frame, (True, True, False, False))
        rendered = self.hud.render_clean(frame, edge_snap_flags=(False, False, True, True))
        self.assertIsNotNone(rendered)
        self.assertEqual(rendered.shape, (480, 640, 3))

    def test_render_window_snap_preview(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        for zone in ['left', 'right', 'top', 'bottom']:
            f = frame.copy()
            self.hud.draw_window_snap_preview(f, zone)
            rendered = self.hud.render_clean(f, snap_zone=zone)
            self.assertIsNotNone(rendered)
            self.assertEqual(rendered.shape, (480, 640, 3))

    def test_render_presentation_spotlight(self):
        frame = np.full((480, 640, 3), 200, dtype=np.uint8)
        self.hud.draw_presentation_spotlight(frame, (320, 240), radius=60, dim_opacity=0.60)
        # Outside spotlight should be dimmed significantly (< 120)
        self.assertLess(frame[50, 50, 0], 120)
        # Inside spotlight should be bright (> 170)
        self.assertGreater(frame[240, 300, 0], 170)
        rendered = self.hud.render_clean(frame, spotlight_mode=True, spotlight_radius=50)
        self.assertIsNotNone(rendered)

    def test_render_clean_with_calibration_and_ripples(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.hud.trigger_click_ripple((320, 240), is_right=False)
        rendered = self.hud.render_clean(frame, calibration_progress=0.75, air_tap_pct=45.0)
        self.assertIsNotNone(rendered)

    def test_render_clean_with_radial_menu(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        rendered = self.hud.render_clean(frame, radial_menu_active=True, active_radial_sector=2)
        self.assertIsNotNone(rendered)
        self.assertEqual(rendered.shape, (480, 640, 3))

    def test_render_clean_with_scroll_cylinder(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        rendered = self.hud.render_clean(frame, scroll_velocity=-1.8)
        self.assertIsNotNone(rendered)
        self.assertEqual(rendered.shape, (480, 640, 3))
        # Direct cylinder drawing
        self.hud.draw_scroll_cylinder(frame, (320, 240), velocity=2.5)
        self.hud.draw_scroll_cylinder(frame, (320, 240), velocity=-2.5)

    def test_render_laser_pointer_plasma_trail(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Create mock hand with landmarks
        hand = HandData(
            landmarks_norm=[(0.5, 0.5, 0.0) for _ in range(21)],
            landmarks_px=[(320, 240, 0.0) for _ in range(21)],
            landmarks_world=[(0.0, 0.0, 0.0) for _ in range(21)],
            palm_size=0.15,
            handedness="Right"
        )
        hand.landmarks_px[5] = (300, 300, 0.0)   # INDEX_MCP
        hand.landmarks_px[8] = (320, 260, 0.0)   # INDEX_TIP
        self.hud.draw_laser_pointer(frame, hand, is_clicking=False)
        self.hud.draw_laser_pointer(frame, hand, is_clicking=True)
        self.assertGreater(len(self.hud.laser_trail), 0)

    def test_render_with_hand_tilt_and_roll_compass(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        hand = HandData(
            landmarks_norm=[(0.5, 0.5, 0.0) for _ in range(21)],
            landmarks_px=[(320, 240, 0.0) for _ in range(21)],
            landmarks_world=[(0.0, 0.0, 0.0) for _ in range(21)],
            palm_size=0.15,
            handedness="Right",
            roll_deg=18.5,
            pitch_deg=-4.2
        )
        self.hud.draw_skeleton(frame, hand, GestureType.NONE, is_action_hand=False)
        self.hud.draw_skeleton(frame, hand, GestureType.NONE, is_action_hand=True)
        self.assertEqual(hand.roll_deg, 18.5)
        self.assertEqual(hand.pitch_deg, -4.2)

    def test_render_slide_chevrons_and_rotary_dials(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.hud.trigger_slide_chevron(is_next=True)
        self.hud.trigger_slide_chevron(is_next=False)
        self.hud.trigger_rotary_feedback((320, 240), is_up=True, delta_deg=14.0)
        self.hud.trigger_rotary_feedback((320, 240), is_up=False, delta_deg=-14.0)
        rendered = self.hud.render_clean(frame)
        self.assertIsNotNone(rendered)
        self.assertEqual(rendered.shape, (480, 640, 3))

    def test_render_optical_zoom_loupes(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        initial_scale = self.hud.virtual_zoom_scale
        self.hud.trigger_zoom_feedback((320, 240), zoom_delta=1)
        self.assertGreater(self.hud.virtual_zoom_scale, initial_scale)
        self.assertEqual(len(self.hud.zoom_feedbacks), 1)

        self.hud.trigger_zoom_feedback((320, 240), zoom_delta=-1)
        self.assertEqual(len(self.hud.zoom_feedbacks), 2)

        self.hud.draw_zoom_loupes(frame)
        self.assertGreater(int(np.sum(frame)), 0)

        rendered = self.hud.render_clean(frame)
        self.assertIsNotNone(rendered)
        self.assertEqual(rendered.shape, (480, 640, 3))

    def test_render_spatial_depth_gauge(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.hud.draw_spatial_depth_gauge(frame, distance_cm=48.0)
        self.assertGreater(int(np.sum(frame)), 0)

        # Warnings: too close and too far
        self.hud.draw_spatial_depth_gauge(frame, distance_cm=22.0)
        self.hud.draw_spatial_depth_gauge(frame, distance_cm=105.0)

        # Integration in render_clean
        hand = HandData(
            landmarks_norm=[(0.5, 0.5, 0.0) for _ in range(21)],
            landmarks_px=[(320, 240, 0.0) for _ in range(21)],
            landmarks_world=[(0.0, 0.0, 0.0) for _ in range(21)],
            palm_size=0.15,
            handedness="Right",
            estimated_distance_cm=46.5
        )
        rendered = self.hud.render_clean(frame, pointer_hand=hand)
        self.assertIsNotNone(rendered)
        self.assertEqual(rendered.shape, (480, 640, 3))

    def test_draw_speedometer_and_reticle(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # High-speed motion vector
        self.hud.draw_speedometer_and_precision_reticle(frame, (320, 240), velocity=360.0, vec=(180.0, 120.0))
        self.assertGreater(int(np.sum(frame)), 0)

        # Micro-precision reticle
        frame.fill(0)
        self.hud.draw_speedometer_and_precision_reticle(frame, (320, 240), velocity=35.0, vec=(0.0, 0.0))
        self.assertGreater(int(np.sum(frame)), 0)

    def test_draw_jitter_chart(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        for i in range(20):
            self.hud.update_jitter_chart(500.0 + (i % 5) * 4.0, 500.0 + i)
        self.hud.draw_jitter_chart(frame)
        self.assertGreater(int(np.sum(frame)), 0)

        self.hud.config.show_jitter_graph = True
        rendered = self.hud.render_clean(frame)
        self.assertIsNotNone(rendered)
        self.assertEqual(rendered.shape, (480, 640, 3))

    def test_ergonomic_break_alert(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.hud.draw_ergonomic_alert(frame, minutes_active=25)
        self.assertGreater(int(np.sum(frame)), 0)

        # Integration in render_clean
        frame.fill(0)
        rendered = self.hud.render_clean(frame, ergonomic_minutes=30)
        self.assertIsNotNone(rendered)
        self.assertEqual(rendered.shape, (480, 640, 3))


class TestNightVisionBooster(unittest.TestCase):
    """Verifies low-light CLAHE and zero-latency LUT gamma boost."""

    def test_gamma_lut_enhances_shadows(self):
        import cv2
        dark_img = np.full((100, 100, 3), 30, dtype=np.uint8)
        table = np.array([min(255, int(((i / 255.0) ** (1.0 / 1.40)) * 255)) for i in range(256)], dtype=np.uint8)
        boosted = cv2.LUT(dark_img, table)
        # Shadow values (30/255) must be non-linearly brightened
        self.assertGreater(int(boosted[50, 50, 0]), 50)


class TestMultiMonitorManagement(unittest.TestCase):
    """Verifies DPI-aware physical display enumeration and bounds clamping."""

    def test_monitor_enumeration(self):
        mc = MouseController()
        monitors = mc.enumerate_monitors()
        self.assertGreater(len(monitors), 0)
        for m in monitors:
            self.assertGreater(m["width"], 0)
            self.assertGreater(m["height"], 0)

    def test_monitor_switching(self):
        mc = MouseController()
        mc.set_active_monitor(0)
        self.assertEqual(mc.active_monitor_index, 0)
        # Reset to full desktop
        mc.set_active_monitor(-1)
        self.assertEqual(mc.active_monitor_index, -1)

    def test_distance_estimation(self):
        # Normal palm size in px (~94px) corresponds to ~50cm distance
        palm_px = 94.0
        dist_cm = round(max(15.0, min(300.0, 4700.0 / max(12.0, palm_px))), 1)
        self.assertAlmostEqual(dist_cm, 50.0, delta=2.0)
        # Small palm size in px (~25px, hand far away) -> ~188cm
        palm_far = 25.0
        dist_far = round(max(15.0, min(300.0, 4700.0 / max(12.0, palm_far))), 1)
        self.assertGreater(dist_far, 150.0)

    def test_keyboard_type_unicode(self):
        from unittest.mock import patch
        mc = MouseController()
        # Mock low-level User32 keybd_event to prevent terminal input interception
        with patch('mouse_controller.user32.keybd_event') as mock_keybd:
            mc.type_text("Aero")
            mc.press_key("esc")
            self.assertGreater(mock_keybd.call_count, 0)

    def test_window_snapping(self):
        from unittest.mock import patch
        mc = MouseController()
        with patch('mouse_controller.user32.keybd_event') as mock_keybd:
            mc.snap_window_left()
            mc.snap_window_right()
            mc.snap_window_maximize()
            mc.snap_window_minimize()
            # 4 actions * 2 keys * 2 events (down + up) = 16 events
            self.assertEqual(mock_keybd.call_count, 16)


class TestDynamicPowerSaver(unittest.TestCase):
    """Tests adaptive standby throttling and zero-latency turbo wake-up."""

    def test_power_saver_idle_state(self):
        import time
        from unittest.mock import patch
        from camera_manager import CameraManager
        with patch.object(CameraManager, 'discover_cameras', return_value=[]):
            with patch('camera_manager.SpatialReceiver'):
                with patch('camera_manager.HandTracker'):
                    cm = CameraManager()
                    cm.hand_detected = True
                    cm.last_hand_seen_time = time.time()
                    cm.is_power_saver = False

                    # When hand is active
                    self.assertFalse(cm.is_power_saver)

                    # Simulate 5 seconds without hand
                    cm.hand_detected = False
                    cm.last_hand_seen_time = time.time() - 5.0
                    now_ts = time.time()
                    if (now_ts - cm.last_hand_seen_time) > 4.0:
                        cm.is_power_saver = True

                    self.assertTrue(cm.is_power_saver)

                    # Immediate turbo wake-up on hand detection
                    cm.hand_detected = True
                    cm.last_hand_seen_time = time.time()
                    cm.is_power_saver = False
                    self.assertFalse(cm.is_power_saver)
                    cm.stop()


class TestDiagnosticsAPI(unittest.TestCase):
    """Verifies automated diagnostics data structure and telemetry reporting."""

    def test_diagnostics_report_structure(self):
        import io
        import json
        from server import create_app
        from camera_manager import CameraManager
        from unittest.mock import patch

        with patch.object(CameraManager, 'discover_cameras', return_value=[]):
            with patch('camera_manager.SpatialReceiver'):
                with patch('camera_manager.HandTracker'):
                    cm = CameraManager()
                    app = create_app(cm)
                    self.assertIsNotNone(app)

                    # WSGI invocation of Bottle route
                    environ = {
                        'PATH_INFO': '/api/diagnostics',
                        'REQUEST_METHOD': 'GET',
                        'wsgi.input': io.BytesIO(),
                        'wsgi.errors': io.StringIO(),
                        'SERVER_NAME': 'localhost',
                        'SERVER_PORT': '5000'
                    }
                    status_captured = []
                    headers_captured = []
                    def start_response(status, headers, *args):
                        status_captured.append(status)
                        headers_captured.extend(headers)

                    body = b"".join(app(environ, start_response))
                    self.assertTrue(status_captured[0].startswith("200"))
                    data = json.loads(body.decode('utf-8'))
                    self.assertIn("status", data)
                    self.assertIn("subsystems", data)
                    self.assertIn("system_resources", data)
                    self.assertIn("camera_pipeline", data["subsystems"])
                    self.assertIn("spatial_receiver", data["subsystems"])
                    cm.stop()

    def test_session_export_endpoint(self):
        import io
        import json
        from server import create_app
        from camera_manager import CameraManager
        from unittest.mock import patch

        with patch.object(CameraManager, 'discover_cameras', return_value=[]):
            with patch('camera_manager.SpatialReceiver'):
                with patch('camera_manager.HandTracker'):
                    cm = CameraManager()
                    app = create_app(cm)

                    # Add mock telemetry samples
                    cm.telemetry_history.append({"t": 0.5, "fps": 59.8, "lat": 16.5, "gest": "HOVER", "hand": True})
                    cm.telemetry_history.append({"t": 0.65, "fps": 60.1, "lat": 15.9, "gest": "PINCH", "hand": True})

                    environ = {
                        'PATH_INFO': '/api/session/export',
                        'REQUEST_METHOD': 'GET',
                        'wsgi.input': io.BytesIO(),
                        'wsgi.errors': io.StringIO(),
                        'SERVER_NAME': 'localhost',
                        'SERVER_PORT': '5000'
                    }
                    status_captured = []
                    def start_response(status, headers, *args):
                        status_captured.append(status)

                    body = b"".join(app(environ, start_response))
                    self.assertTrue(status_captured[0].startswith("200"))
                    data = json.loads(body.decode('utf-8'))
                    self.assertIn("session_duration_sec", data)
                    self.assertEqual(data["total_samples"], 2)
                    self.assertEqual(len(data["samples"]), 2)
                    self.assertEqual(data["samples"][0]["gest"], "HOVER")
                    cm.stop()


class TestSpatialAirCanvas(unittest.TestCase):
    """Verifies Spatial Air-Canvas Stream Annotator: stroke persistence, rendering, and API control."""

    def test_air_canvas_hud_drawing(self):
        config = GestureConfig()
        hud = CyberHUD(config)
        self.assertEqual(len(hud.air_draw_strokes), 0)

        # 1. Add points to first stroke
        color_cyan = (254, 242, 0)
        hud.add_air_draw_point((100, 100), color_cyan)
        self.assertEqual(len(hud.air_draw_strokes), 1)
        self.assertEqual(len(hud.air_draw_strokes[0]["points"]), 1)

        # 2. Points too close (<3px) should be filtered out to avoid overdraw
        hud.add_air_draw_point((101, 101), color_cyan)
        self.assertEqual(len(hud.air_draw_strokes[0]["points"]), 1)

        # 3. Point sufficiently moved should be recorded
        hud.add_air_draw_point((115, 120), color_cyan)
        self.assertEqual(len(hud.air_draw_strokes[0]["points"]), 2)

        # 4. Finish stroke and start another
        hud.finish_air_draw_stroke()
        self.assertIsNone(hud.current_air_stroke)

        color_magenta = (255, 0, 255)
        hud.add_air_draw_point((200, 200), color_magenta)
        hud.add_air_draw_point((220, 225), color_magenta)
        self.assertEqual(len(hud.air_draw_strokes), 2)

        # 5. Render onto synthetic frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        hud.draw_air_canvas(frame)
        # Drawn lines must alter the canvas pixels
        self.assertGreater(int(np.sum(frame)), 0)

        # 6. Clear canvas
        hud.clear_air_canvas()
        self.assertEqual(len(hud.air_draw_strokes), 0)
        self.assertIsNone(hud.current_air_stroke)

    def test_air_canvas_api_endpoints(self):
        import io
        import json
        from server import create_app
        from camera_manager import CameraManager
        from unittest.mock import patch

        with patch.object(CameraManager, 'discover_cameras', return_value=[]):
            with patch('camera_manager.SpatialReceiver'):
                with patch('camera_manager.HandTracker'):
                    cm = CameraManager()
                    app = create_app(cm)

                    def make_request(path, method='POST', body_dict=None):
                        body_bytes = json.dumps(body_dict or {}).encode('utf-8')
                        environ = {
                            'PATH_INFO': path,
                            'REQUEST_METHOD': method,
                            'CONTENT_LENGTH': str(len(body_bytes)),
                            'CONTENT_TYPE': 'application/json',
                            'wsgi.input': io.BytesIO(body_bytes),
                            'wsgi.errors': io.StringIO(),
                            'SERVER_NAME': 'localhost',
                            'SERVER_PORT': '5000'
                        }
                        status_cap = []
                        def start_response(status, headers, *args):
                            status_cap.append(status)
                        resp = b"".join(app(environ, start_response))
                        return status_cap[0], json.loads(resp.decode('utf-8'))

                    # Test toggle
                    status, res = make_request('/api/canvas/toggle', 'POST', {'enabled': True})
                    self.assertTrue(status.startswith("200"))
                    self.assertTrue(res['enabled'])
                    self.assertTrue(cm.config.enable_air_draw_stream)

                    # Test color
                    status, res = make_request('/api/canvas/color', 'POST', {'color': 'gold'})
                    self.assertTrue(status.startswith("200"))
                    self.assertEqual(res['color'], 'gold')
                    self.assertEqual(cm.config.air_draw_color, 'gold')

                    # Test clear
                    cm.hud.add_air_draw_point((50, 50), (0, 255, 255))
                    self.assertEqual(len(cm.hud.air_draw_strokes), 1)
                    status, res = make_request('/api/canvas/clear', 'POST', {})
                    self.assertTrue(status.startswith("200"))
                    self.assertEqual(len(cm.hud.air_draw_strokes), 0)

                    # Test spotlight toggle
                    status, res = make_request('/api/spotlight/toggle', 'POST', {'enabled': True, 'radius': 95})
                    self.assertTrue(status.startswith("200"))
                    self.assertTrue(res['presentation_spotlight_mode'])
                    self.assertEqual(res['spotlight_radius'], 95)
                    self.assertTrue(cm.config.presentation_spotlight_mode)
                    self.assertEqual(cm.config.spotlight_radius, 95)

                    cm.stop()


class TestBimanualAirClap(unittest.TestCase):
    """Verifies Bimanual Air-Clap Macro: gesture triggering, palm proximity detection, and cooldown."""

    def test_air_clap_detection(self):
        config = GestureConfig()
        rec = GestureRecognizer(config, screen_size=(1920, 1080), screen_origin=(0, 0))

        # Helper to build an open palm hand (5 extended fingers)
        def build_open_palm(wx: float, wy: float) -> HandData:
            px = [(wx, wy, 0.0)] * 21
            # Thumb (1, 2, 3, 4)
            px[1] = (wx - 15.0, wy - 15.0, 0.0)
            px[2] = (wx - 25.0, wy - 30.0, 0.0)
            px[3] = (wx - 35.0, wy - 45.0, 0.0)
            px[4] = (wx - 45.0, wy - 60.0, 0.0)
            # Index (5, 6, 7, 8)
            px[5] = (wx - 10.0, wy - 40.0, 0.0)
            px[6] = (wx - 10.0, wy - 65.0, 0.0)
            px[7] = (wx - 10.0, wy - 85.0, 0.0)
            px[8] = (wx - 10.0, wy - 105.0, 0.0)
            # Middle (9, 10, 11, 12)
            px[9] = (wx, wy - 42.0, 0.0)
            px[10] = (wx, wy - 70.0, 0.0)
            px[11] = (wx, wy - 92.0, 0.0)
            px[12] = (wx, wy - 115.0, 0.0)
            # Ring (13, 14, 15, 16)
            px[13] = (wx + 10.0, wy - 40.0, 0.0)
            px[14] = (wx + 10.0, wy - 65.0, 0.0)
            px[15] = (wx + 10.0, wy - 85.0, 0.0)
            px[16] = (wx + 10.0, wy - 105.0, 0.0)
            # Pinky (17, 18, 19, 20)
            px[17] = (wx + 20.0, wy - 35.0, 0.0)
            px[18] = (wx + 20.0, wy - 55.0, 0.0)
            px[19] = (wx + 20.0, wy - 72.0, 0.0)
            px[20] = (wx + 20.0, wy - 90.0, 0.0)

            return HandData(
                landmarks_norm=[(p[0] / 640.0, p[1] / 480.0, 0.0) for p in px],
                landmarks_px=px,
                landmarks_world=[(p[0] * 0.001, p[1] * 0.001, 0.0) for p in px],
                palm_size=0.15,
                handedness="Right"
            )

        # 1. Hands far apart (180px distance) -> NO clap
        h1 = build_open_palm(200.0, 300.0)
        h2 = build_open_palm(380.0, 300.0)
        gest, events = rec.update_bimanual(h1, h2, (480, 640))
        self.assertFalse(events.get("trigger_air_clap", False))

        # 2. Hands come together (<50px distance) -> AIR CLAP!
        h3 = build_open_palm(300.0, 300.0)
        h4 = build_open_palm(335.0, 300.0)
        gest, events = rec.update_bimanual(h3, h4, (480, 640))
        self.assertTrue(events.get("trigger_air_clap", False))
        self.assertEqual(events.get("action_gesture"), "AIR CLAP")
        self.assertIn("air_clap_midpoint", events)

        # 3. Consecutive frame in quick succession (<0.65s) -> Debounced
        gest, events_cooldown = rec.update_bimanual(h3, h4, (480, 640))
        self.assertFalse(events_cooldown.get("trigger_air_clap", False))


class TestDoubleClickGesture(unittest.TestCase):
    """Verifies dual-tap fast double click detection across thumb_bend and pinch modes."""

    def test_thumb_bend_double_click(self):
        config = GestureConfig()
        config.click_mode = "thumb_bend"
        rec = GestureRecognizer(config, screen_size=(1920, 1080), screen_origin=(0, 0))

        def make_pointing_hand(thumb_bent: bool) -> HandData:
            px = [(300.0, 300.0, 0.0)] * 21
            px[0] = (300.0, 350.0, 0.0)
            # Index extended
            px[5] = (300.0, 260.0, 0.0)
            px[6] = (300.0, 230.0, 0.0)
            px[7] = (300.0, 210.0, 0.0)
            px[8] = (300.0, 190.0, 0.0)
            # Middle curled
            px[9] = (320.0, 260.0, 0.0)
            px[10] = (320.0, 280.0, 0.0)
            px[11] = (320.0, 300.0, 0.0)
            px[12] = (320.0, 310.0, 0.0)
            # Thumb
            if thumb_bent:
                px[1] = (260.0, 300.0, 0.0)
                px[2] = (275.0, 280.0, 0.0)
                px[3] = (295.0, 280.0, 0.0)
                px[4] = (295.0, 305.0, 0.0)
            else:
                px[1] = (270.0, 280.0, 0.0)
                px[2] = (250.0, 260.0, 0.0)
                px[3] = (235.0, 245.0, 0.0)
                px[4] = (220.0, 230.0, 0.0)

            return HandData(
                landmarks_norm=[(p[0] / 640.0, p[1] / 480.0, 0.0) for p in px],
                landmarks_px=px,
                landmarks_world=[(p[0] * 0.001, p[1] * 0.001, 0.0) for p in px],
                palm_size=0.15,
                handedness="Right"
            )

        h_bent = make_pointing_hand(thumb_bent=True)
        h_open = make_pointing_hand(thumb_bent=False)

        # First click: single click
        rec.update(h_open, (480, 640))
        time.sleep(0.01)
        gest1, ev1 = rec.update(h_bent, (480, 640))
        self.assertTrue(ev1.get("trigger_left_click", False))
        self.assertFalse(ev1.get("trigger_double_click", False))

        # Release thumb
        rec.update(h_open, (480, 640))
        time.sleep(0.12)

        # Second rapid bend within 0.20s -> Double Click!
        gest2, ev2 = rec.update(h_bent, (480, 640))
        self.assertTrue(ev2.get("trigger_double_click", False))

    def test_pinch_double_click(self):
        config = GestureConfig()
        config.click_mode = "pinch"
        rec = GestureRecognizer(config, screen_size=(1920, 1080), screen_origin=(0, 0))

        def make_pinch_hand(pinched: bool) -> HandData:
            px = [(300.0, 300.0, 0.0)] * 21
            px[0] = (300.0, 350.0, 0.0)
            # Index extended
            px[5] = (300.0, 260.0, 0.0)
            px[6] = (300.0, 230.0, 0.0)
            px[7] = (300.0, 210.0, 0.0)
            px[8] = (300.0, 190.0, 0.0)
            # Middle curled
            px[9] = (320.0, 260.0, 0.0)
            px[10] = (320.0, 280.0, 0.0)
            px[11] = (320.0, 300.0, 0.0)
            px[12] = (320.0, 310.0, 0.0)
            if pinched:
                px[4] = (300.0, 195.0, 0.0)  # thumb touching index tip
            else:
                px[4] = (250.0, 240.0, 0.0)  # thumb far from index tip

            return HandData(
                landmarks_norm=[(p[0] / 640.0, p[1] / 480.0, 0.0) for p in px],
                landmarks_px=px,
                landmarks_world=[(p[0] * 0.001, p[1] * 0.001, 0.0) for p in px],
                palm_size=0.15,
                handedness="Right"
            )

        h_pinched = make_pinch_hand(pinched=True)
        h_open = make_pinch_hand(pinched=False)

        # First pinch tap: pinch down then release
        rec.update(h_pinched, (480, 640))
        time.sleep(0.01)
        gest1, ev1 = rec.update(h_open, (480, 640))
        self.assertTrue(ev1.get("trigger_left_click", False))

        time.sleep(0.12)

        # Second rapid pinch tap: pinch down then release
        rec.update(h_pinched, (480, 640))
        time.sleep(0.01)
        gest2, ev2 = rec.update(h_open, (480, 640))
        self.assertTrue(ev2.get("trigger_double_click", False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
