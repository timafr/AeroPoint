"""
Global Windows Hotkey Service for AeroPoint Spatial
===================================================
Ultra-lightweight background hotkey daemon using Windows User32 GetAsyncKeyState.
Allows toggling tracking, pause, presentation mode, and calibration globally from any app
(e.g., PowerPoint, Chrome, Blender, games, Desktop).

Default Hotkeys:
- Ctrl + Alt + A: Toggle Gesture Control (ON / OFF)
- Ctrl + Alt + P: Safety Pause (Hold cursor in place)
- Ctrl + Alt + S: Toggle Presentation & Media Air-Swipe Mode
- Ctrl + Alt + C: Trigger Quick Hand Calibration
"""

import sys
import time
import threading
from typing import Callable, Optional, Dict

IS_WINDOWS = sys.platform.startswith("win")

if IS_WINDOWS:
    import ctypes
    user32 = ctypes.windll.user32

    # Virtual key constants
    VK_CONTROL = 0x11
    VK_MENU = 0x12     # Alt
    VK_SHIFT = 0x10
    VK_A = 0x41
    VK_P = 0x50
    VK_S = 0x53
    VK_C = 0x43
    VK_Q = 0x51
    VK_L = 0x4C
    VK_Z = 0x5A
    VK_M = 0x4D
    VK_R = 0x52
    VK_ESCAPE = 0x1B


class GlobalHotkeyService:
    """Thread-safe global hotkey daemon with zero external dependencies."""
    def __init__(self, manager=None):
        self.manager = manager
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.callbacks: Dict[str, Callable[[], None]] = {}
        self.key_states: Dict[str, bool] = {
            "ctrl_alt_a": False,
            "ctrl_alt_p": False,
            "ctrl_alt_s": False,
            "ctrl_alt_c": False,
            "ctrl_alt_q": False,
            "ctrl_alt_l": False,
            "ctrl_alt_z": False,
            "ctrl_alt_m": False,
            "ctrl_alt_r": False,
        }

    def register_callback(self, hotkey: str, callback: Callable[[], None]):
        """Registers a custom callback for a hotkey combination."""
        self.callbacks[hotkey.lower()] = callback

    def start(self):
        """Starts background listener loop."""
        if not IS_WINDOWS or self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True, name="AeroPoint-Hotkeys")
        self.thread.start()
        print("[+] Global Hotkey Service active: [Ctrl+Alt+A: Toggle], [Ctrl+Alt+P: Pause], [Ctrl+Alt+S: Slides]")

    def stop(self):
        """Stops background loop."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None

    def _loop(self):
        while self.running:
            try:
                # Check modifier keys: Ctrl + Alt
                ctrl_down = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
                alt_down = bool(user32.GetAsyncKeyState(VK_MENU) & 0x8000)

                if ctrl_down and alt_down:
                    # 1. Ctrl + Alt + A -> Toggle Control
                    a_down = bool(user32.GetAsyncKeyState(VK_A) & 0x8000)
                    if a_down and not self.key_states["ctrl_alt_a"]:
                        self.key_states["ctrl_alt_a"] = True
                        self._trigger("ctrl_alt_a", self._toggle_control)
                    elif not a_down:
                        self.key_states["ctrl_alt_a"] = False

                    # 2. Ctrl + Alt + P -> Safety Pause
                    p_down = bool(user32.GetAsyncKeyState(VK_P) & 0x8000)
                    if p_down and not self.key_states["ctrl_alt_p"]:
                        self.key_states["ctrl_alt_p"] = True
                        self._trigger("ctrl_alt_p", self._toggle_pause)
                    elif not p_down:
                        self.key_states["ctrl_alt_p"] = False

                    # 3. Ctrl + Alt + S -> Presentation Mode
                    s_down = bool(user32.GetAsyncKeyState(VK_S) & 0x8000)
                    if s_down and not self.key_states["ctrl_alt_s"]:
                        self.key_states["ctrl_alt_s"] = True
                        self._trigger("ctrl_alt_s", self._toggle_presentation)
                    elif not s_down:
                        self.key_states["ctrl_alt_s"] = False

                    # 4. Ctrl + Alt + C -> Quick Calibration
                    c_down = bool(user32.GetAsyncKeyState(VK_C) & 0x8000)
                    if c_down and not self.key_states["ctrl_alt_c"]:
                        self.key_states["ctrl_alt_c"] = True
                        self._trigger("ctrl_alt_c", self._calibrate)
                    elif not c_down:
                        self.key_states["ctrl_alt_c"] = False

                    # 5. Ctrl + Alt + Q -> Quick-Dial Win+Tab
                    q_down = bool(user32.GetAsyncKeyState(VK_Q) & 0x8000)
                    if q_down and not self.key_states["ctrl_alt_q"]:
                        self.key_states["ctrl_alt_q"] = True
                        self._trigger("ctrl_alt_q", self._quick_dial)
                    elif not q_down:
                        self.key_states["ctrl_alt_q"] = False

                    # 6. Ctrl + Alt + L -> Toggle Laser Pointer Mode
                    l_down = bool(user32.GetAsyncKeyState(VK_L) & 0x8000)
                    if l_down and not self.key_states["ctrl_alt_l"]:
                        self.key_states["ctrl_alt_l"] = True
                        self._trigger("ctrl_alt_l", self._toggle_laser)
                    elif not l_down:
                        self.key_states["ctrl_alt_l"] = False

                    # 7. Ctrl + Alt + Z -> Snap Window Maximize
                    z_down = bool(user32.GetAsyncKeyState(VK_Z) & 0x8000)
                    if z_down and not self.key_states["ctrl_alt_z"]:
                        self.key_states["ctrl_alt_z"] = True
                        self._trigger("ctrl_alt_z", self._snap_maximize)
                    elif not z_down:
                        self.key_states["ctrl_alt_z"] = False

                    # 8. Ctrl + Alt + M -> Cycle Target Monitor
                    m_down = bool(user32.GetAsyncKeyState(VK_M) & 0x8000)
                    if m_down and not self.key_states["ctrl_alt_m"]:
                        self.key_states["ctrl_alt_m"] = True
                        self._trigger("ctrl_alt_m", self._cycle_monitor)
                    elif not m_down:
                        self.key_states["ctrl_alt_m"] = False

                    # 9. Ctrl + Alt + R -> Toggle In-Air Radial Menu
                    r_down = bool(user32.GetAsyncKeyState(VK_R) & 0x8000)
                    if r_down and not self.key_states["ctrl_alt_r"]:
                        self.key_states["ctrl_alt_r"] = True
                        self._trigger("ctrl_alt_r", self._toggle_radial_menu)
                    elif not r_down:
                        self.key_states["ctrl_alt_r"] = False

                else:
                    for k in self.key_states:
                        self.key_states[k] = False

            except Exception:
                pass

            time.sleep(0.025)  # 40 Hz polling = 0% CPU, instantaneous response

    def _trigger(self, key_id: str, default_action: Callable[[], None]):
        if key_id in self.callbacks:
            try:
                self.callbacks[key_id]()
            except Exception as e:
                print(f"[!] Hotkey callback error: {e}")
        else:
            default_action()

    def _toggle_control(self):
        if self.manager:
            self.manager.control_enabled = not self.manager.control_enabled
            state = "ENABLED" if self.manager.control_enabled else "DISABLED"
            print(f"[*] Hotkey [Ctrl+Alt+A]: Gesture Control {state}")

    def _toggle_pause(self):
        if self.manager:
            self.manager.manual_pause = not self.manager.manual_pause
            state = "PAUSED" if self.manager.manual_pause else "RESUMED"
            print(f"[*] Hotkey [Ctrl+Alt+P]: Safety Pause {state}")

    def _toggle_presentation(self):
        if self.manager and hasattr(self.manager, 'config'):
            cur = getattr(self.manager.config, 'presentation_mode_enabled', False)
            self.manager.config.presentation_mode_enabled = not cur
            state = "ACTIVE" if self.manager.config.presentation_mode_enabled else "OFF"
            print(f"[*] Hotkey [Ctrl+Alt+S]: Air-Swipe Presentation Mode {state}")

    def _calibrate(self):
        if self.manager:
            if hasattr(self.manager, 'trigger_calibration'):
                self.manager.trigger_calibration(3.0)
            elif hasattr(self.manager, 'precision_engine'):
                self.manager.precision_engine.reset()
            print("[*] Hotkey [Ctrl+Alt+C]: Precision filters re-centered & calibrated")

    def _quick_dial(self):
        if self.manager and hasattr(self.manager, 'mouse'):
            self.manager.mouse.task_view()
            print("[*] Hotkey [Ctrl+Alt+Q]: Quick Task Switch summoned")

    def _toggle_laser(self):
        if self.manager and hasattr(self.manager, 'config'):
            cur = getattr(self.manager.config, 'laser_pointer_mode', False)
            self.manager.config.laser_pointer_mode = not cur
            state = "ACTIVE" if self.manager.config.laser_pointer_mode else "OFF"
            print(f"[*] Hotkey [Ctrl+Alt+L]: Laser Pointer {state}")

    def _snap_maximize(self):
        if self.manager and hasattr(self.manager, 'mouse'):
            self.manager.mouse.snap_window_maximize()
            print("[*] Hotkey [Ctrl+Alt+Z]: Window Maximized / Snapped")

    def _cycle_monitor(self):
        if self.manager and hasattr(self.manager, 'cycle_monitor'):
            new_idx = self.manager.cycle_monitor()
            print(f"[*] Hotkey [Ctrl+Alt+M]: Target Monitor Cycled -> #{new_idx}")

    def _toggle_radial_menu(self):
        if self.manager and hasattr(self.manager, 'toggle_radial_menu'):
            self.manager.toggle_radial_menu()
            print(f"[*] Hotkey [Ctrl+Alt+M]: Cycled to Monitor #{new_idx}")
