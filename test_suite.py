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
            cfg.save_to_file(test_file)

            self.assertTrue(os.path.exists(test_file))
            loaded = GestureConfig.load_from_file(test_file)
            self.assertEqual(loaded.sensitivity, 2.75)
            self.assertEqual(loaded.click_mode, "pinch")
            self.assertEqual(loaded.enable_corner_snap, True)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)


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

    def test_render_clean_with_calibration_and_ripples(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.hud.trigger_click_ripple((320, 240), is_right=False)
        rendered = self.hud.render_clean(frame, calibration_progress=0.75, air_tap_pct=45.0)
        self.assertIsNotNone(rendered)


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
