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
    laser_color: str = "cyan"               # "cyan", "green", "red", "gold"
    presentation_spotlight_mode: bool = False # Keynote-style circular stage spotlight with dimmed vignette
    spotlight_radius: int = 85              # Pixel radius of spotlight beam
    enable_air_draw_stream: bool = False    # Live glowing air-draw annotations directly in the camera stream
    air_draw_color: str = "cyan"            # "cyan", "magenta", "green", "gold", "white"
    enable_ergonomic_alerts: bool = True    # Ergonomic rest alerts after prolonged mid-air hand elevation
    ergonomic_alert_interval_sec: float = 1500.0 # 25 minutes threshold
    enable_virtual_touch_surface: bool = False # Virtual Touchscreen Desk surface plane in 3D air
    virtual_surface_z: float = -0.045       # Calibrated virtual surface depth plane (meters)
    enable_screen_magnifier: bool = False   # Floating 2.0x Screen Magnifier Loupe beside cursor
    magnifier_zoom: float = 2.0             # Zoom scale (1.5x - 4.0x)
    show_wrist_hud_clock: bool = True       # visionOS holographic smart timepiece over wrist landmark

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
    enable_window_snap_zones: bool = True  # Holographic Window Snap Previews (Drop target on edge drag)
    enable_distance_adaptation: bool = True  # Dynamic reach normalization based on user distance from camera
    precision_profile: str = "desktop"       # "cad", "desktop", "gaming"
    acceleration_curve: str = "exponential"  # "linear", "sigmoid", "exponential"

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
    hud_theme: str = "cyberpunk"  # "cyberpunk", "visionos", "matrix", "solar"

    # Colors in BGR format for OpenCV
    COLOR_CYAN: Tuple[int, int, int] = (254, 242, 0)      # #00f2fe
    COLOR_VIOLET: Tuple[int, int, int] = (255, 0, 127)   # #7f00ff
    COLOR_MAGENTA: Tuple[int, int, int] = (127, 0, 255)  # #ff007f
    COLOR_GREEN: Tuple[int, int, int] = (136, 255, 0)    # #00ff88
    COLOR_WHITE: Tuple[int, int, int] = (255, 255, 255)
    COLOR_DARK_BG: Tuple[int, int, int] = (10, 7, 6)     # #06070a
    COLOR_RED: Tuple[int, int, int] = (85, 0, 255)       # Raw jitter noise color

    def apply_hud_theme(self, theme: str) -> str:
        """Applies real-time color palettes for OpenCV HUD and Skeleton rendering."""
        t = (theme or "cyberpunk").strip().lower()
        if t in ("visionos", "apple", "white"):
            self.hud_theme = "visionos"
            self.COLOR_CYAN = (255, 255, 255)      # Crisp frosted white
            self.COLOR_VIOLET = (235, 205, 175)    # Lavender frost
            self.COLOR_MAGENTA = (255, 180, 50)    # Soft amber
            self.COLOR_GREEN = (180, 240, 100)     # Apple mint
        elif t in ("matrix", "terminal", "emerald"):
            self.hud_theme = "matrix"
            self.COLOR_CYAN = (50, 255, 100)       # Phosphor green
            self.COLOR_VIOLET = (30, 200, 70)      # Deep terminal green
            self.COLOR_MAGENTA = (80, 255, 180)    # Digital lime
            self.COLOR_GREEN = (0, 255, 65)        # Pure matrix green
        elif t in ("solar", "amber", "gold"):
            self.hud_theme = "solar"
            self.COLOR_CYAN = (0, 185, 255)        # Solar gold
            self.COLOR_VIOLET = (0, 100, 255)      # Molten orange
            self.COLOR_MAGENTA = (50, 50, 255)     # Crimson red
            self.COLOR_GREEN = (0, 230, 255)       # Amber glow
        else:
            self.hud_theme = "cyberpunk"
            self.COLOR_CYAN = (254, 242, 0)        # #00f2fe
            self.COLOR_VIOLET = (255, 0, 127)      # #7f00ff
            self.COLOR_MAGENTA = (127, 0, 255)     # #ff007f
            self.COLOR_GREEN = (136, 255, 0)       # #00ff88
        return self.hud_theme

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
            "enable_window_snap_zones": self.enable_window_snap_zones,
            "enable_distance_adaptation": self.enable_distance_adaptation,
            "precision_profile": self.precision_profile,
            "acceleration_curve": self.acceleration_curve,
            "enable_legacy_shortcuts": self.enable_legacy_shortcuts,
            "laser_pointer_mode": self.laser_pointer_mode,
            "laser_color": self.laser_color,
            "presentation_spotlight_mode": self.presentation_spotlight_mode,
            "spotlight_radius": self.spotlight_radius,
            "enable_virtual_touch_surface": self.enable_virtual_touch_surface,
            "virtual_surface_z": self.virtual_surface_z,
            "enable_screen_magnifier": self.enable_screen_magnifier,
            "magnifier_zoom": self.magnifier_zoom,
            "show_wrist_hud_clock": self.show_wrist_hud_clock,
            "enable_power_saver": self.enable_power_saver,
            "sound_enabled": self.sound_enabled,
            "sound_theme": self.sound_theme,
            "sound_volume": self.sound_volume,
            "hud_theme": self.hud_theme,
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
                    if hasattr(cfg, 'hud_theme'):
                        cfg.apply_hud_theme(cfg.hud_theme)
            except Exception:
                pass
        return cfg
