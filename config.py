"""
Configuration module for Gesture AI PC Control
===============================================
Parameters and thresholds aligned with the specifications in ai_studio_code.html:
- Zero-cost hardware pipeline (standard 720p/1080p webcam)
- Exponential Moving Average (EMA) and 1-Euro adaptive smoothing
- Deadzone and hysteresis thresholds to prevent false triggers
- Cyberpunk HUD styling
"""

import os
from dataclasses import dataclass, field
from typing import Tuple

@dataclass
class GestureConfig:
    # --- Hardware & Video Capture ---
    camera_id: int = 0
    cam_width: int = 640
    cam_height: int = 480
    target_fps: int = 60
    flip_horizontal: bool = True
    use_clahe: bool = False  # Contrast Limited Adaptive Histogram Equalization
    enable_power_saver: bool = True  # Drops frame rate to 15 FPS when idle (> 4s without hands) to save CPU/thermal load


    # --- MediaPipe Hand Tracking (Optimized for all-angle & perpendicular tracking) ---
    model_path: str = field(
        default_factory=lambda: os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
    )
    max_num_hands: int = 2
    min_detection_confidence: float = 0.50
    min_presence_confidence: float = 0.45
    min_tracking_confidence: float = 0.45

    # --- Two-Handed (Bimanual) Control Mode ---
    enable_two_hands: bool = True           # Allow simultaneous two-hand tracking
    dominant_hand: str = "Right"            # Pointer hand: "Right" or "Left"

    # --- Essential & Advanced Gesture Control ---
    enable_legacy_shortcuts: bool = False   # When False: suppresses accidental Shaka/Rock/Pinky clicks
    enable_pinch_hold_drag: bool = True    # Hold pinch for > 0.22s to start dragging
    pinch_hold_drag_delay_sec: float = 0.22 # Delay before drag locks in
    radial_menu_enabled: bool = True        # Radial Quick-Dial Pie Menu
    laser_pointer_mode: bool = False        # Laser vector aiming mode with snap assistance

    # --- Audio & Sonic Synthesizer ---
    sound_enabled: bool = True
    sound_theme: str = "quantum"            # "quantum", "vision", "bionic"
    sound_volume: float = 0.65

    # --- Active Workspace / Screen Mapping ---
    # Margins define the boundary inside camera frame that maps to 100% of the screen
    margin_x: float = 0.08  # Expanded 8% margins (allows cursor to easily reach the full right and left edge)
    margin_y: float = 0.10  # Expanded 10% vertical margins
    sensitivity: float = 1.8  # Cursor speed & reach multiplier (1.0 = standard, 2.0 = fast, 3.0+ = ultra-fast)
    deadzone_radius: float = 3.5  # Pixel threshold to lock cursor (Slide 16)
    enable_corner_snap: bool = True  # AeroMagnet: magnetic attraction to screen corners & window buttons
    enable_distance_adaptation: bool = True  # Dynamic reach normalization based on user distance from camera
    precision_profile: str = "desktop"       # "cad", "desktop", "gaming"

    # --- Jitter Reduction & Smoothing ---
    # Filter types: 'ema', 'adaptive_ema', 'one_euro'
    filter_type: str = "adaptive_ema"
    ema_alpha: float = 0.65       # Base EMA smoothing factor (Slide 15)
    ema_min_alpha: float = 0.20   # High smoothing when stationary (anti-jitter)
    ema_max_alpha: float = 0.85   # Low smoothing when moving fast (zero-latency)
    velocity_scale: float = 25.0  # Transition sensitivity for adaptive EMA

    # --- Gesture Detection Thresholds (Normalized to palm scale) ---
    click_mode: str = "thumb_bend"       # "thumb_bend" (сгиб большого пальца) or "pinch" (щипок)

    # Thumb Bend detection (Thumb IP angle & distance to index base)
    thumb_bend_angle_activate: float = 124.0   # Deliberate flexion angle threshold to click (< 124 deg)
    thumb_bend_angle_release: float = 138.0    # Release threshold (> 138 deg)
    thumb_bend_dist_activate: float = 0.26     # Distance ratio to Index MCP to click (< 0.26)
    thumb_bend_dist_release: float = 0.35      # Distance ratio to release (> 0.35)

    # Pinch detection (Thumb #4 to Index #8)
    pinch_activate_ratio: float = 0.28   # Normalized distance threshold to start click
    pinch_release_ratio: float = 0.38    # Hysteresis threshold to release click

    # Right Click detection (Thumb #4 to Middle #12)
    right_click_activate_ratio: float = 0.28
    right_click_release_ratio: float = 0.40

    # Debounce timers (Slide 16)
    click_debounce_sec: float = 0.25     # Crisp click response with anti-stutter protection (250 ms)
    scroll_cooldown_sec: float = 0.04    # Smooth scrolling interval

    # Scroll sensitivity
    scroll_speed_multiplier: float = 24.0

    # Audio feedback (disabled in OS to avoid Windows error beeps; handled cleanly via UI)
    enable_sound_feedback: bool = False

    # --- HUD & Visual Styling (Slide 11 & HTML Cyberpunk Palette) ---
    show_hud: bool = True
    show_skeleton: bool = True
    show_active_box: bool = True
    show_jitter_graph: bool = True
    show_cpu_load: bool = True
    hud_compact_mode: bool = False

    # Colors in BGR format for OpenCV
    COLOR_CYAN: Tuple[int, int, int] = (254, 242, 0)      # #00f2fe
    COLOR_VIOLET: Tuple[int, int, int] = (255, 0, 127)   # #7f00ff
    COLOR_MAGENTA: Tuple[int, int, int] = (127, 0, 255)  # #ff007f
    COLOR_GREEN: Tuple[int, int, int] = (136, 255, 0)    # #00ff88
    COLOR_WHITE: Tuple[int, int, int] = (255, 255, 255)
    COLOR_DARK_BG: Tuple[int, int, int] = (10, 7, 6)     # #06070a
    COLOR_RED: Tuple[int, int, int] = (85, 0, 255)       # Raw jitter noise color

    def to_dict(self) -> dict:
        """Serializes current configuration properties to JSON-compatible dictionary."""
        return {
            "camera_id": self.camera_id,
            "use_clahe": self.use_clahe,
            "enable_two_hands": self.enable_two_hands,
            "dominant_hand": self.dominant_hand,
            "click_mode": self.click_mode,
            "margin_x": self.margin_x,
            "margin_y": self.margin_y,
            "sensitivity": self.sensitivity,
            "deadzone_radius": self.deadzone_radius,
            "enable_corner_snap": self.enable_corner_snap,
            "enable_distance_adaptation": self.enable_distance_adaptation,
            "precision_profile": self.precision_profile,
            "enable_legacy_shortcuts": self.enable_legacy_shortcuts,
            "laser_pointer_mode": self.laser_pointer_mode,
            "enable_power_saver": self.enable_power_saver,
            "sound_enabled": self.sound_enabled,
            "sound_theme": self.sound_theme,
            "sound_volume": self.sound_volume,
            "show_skeleton": self.show_skeleton,
            "show_hud": self.show_hud,
        }

    def save_to_file(self, filepath: str = "config.json"):
        """Persists current user configuration to JSON file on disk."""
        import json
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2)
        except Exception:
            pass

    @classmethod
    def load_from_file(cls, filepath: str = "config.json") -> "GestureConfig":
        """Loads configuration from JSON file with graceful fallback to defaults."""
        import json
        cfg = cls()
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if hasattr(cfg, k):
                            setattr(cfg, k, v)
            except Exception:
                pass
        return cfg
