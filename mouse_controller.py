"""
Mouse Controller Module
=======================
High-performance, ultra-low latency mouse emulation layer.
Uses Windows User32 C API via ctypes with zero artificial delays.
Includes Per-Monitor High-DPI awareness to support full native screen resolutions
(e.g., 1920x1080, 2K, 4K, and multi-monitor setups).
"""

import sys
import time
from typing import Tuple, Optional, List, Dict
import cv2
import numpy as np

# Check if running on Windows for direct User32 API
IS_WINDOWS = sys.platform.startswith("win")

if IS_WINDOWS:
    import ctypes
    import ctypes.wintypes
    # No winsound import to prevent annoying Windows error dings

    # Enable Per-Monitor High-DPI awareness so GetSystemMetrics and SetCursorPos
    # work with the true physical screen pixel resolution (1920x1080) rather than virtualized 1536x864.
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    user32 = ctypes.windll.user32
    
    # User32 mouse event flags
    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_MIDDLEDOWN = 0x0020
    MOUSEEVENTF_MIDDLEUP = 0x0040
    MOUSEEVENTF_WHEEL = 0x0800
    MOUSEEVENTF_ABSOLUTE = 0x8000

    # User32 keyboard event flags and virtual keys
    KEYEVENTF_KEYUP = 0x0002
    VK_LWIN = 0x5B
    VK_TAB = 0x09
    VK_LMENU = 0x12  # Alt key
    VK_D = 0x44      # 'D' key
    VK_SHIFT = 0x10  # Shift key
    VK_S = 0x53      # 'S' key
    VK_CONTROL = 0x11
    VK_C = 0x43
    VK_V = 0x56
    VK_Z = 0x5A
    VK_F5 = 0x74
    VK_VOLUME_MUTE = 0xAD
    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_UP = 0xAF
    VK_MEDIA_PLAY_PAUSE = 0xB3
    VK_MEDIA_NEXT_TRACK = 0xB0
    VK_MEDIA_PREV_TRACK = 0xB1
    VK_LEFT = 0x25
    VK_UP = 0x26
    VK_RIGHT = 0x27
    VK_DOWN = 0x28
    VK_RETURN = 0x0D
    VK_BACK = 0x08
    VK_SPACE = 0x20
    VK_ESCAPE = 0x1B
else:
    import pyautogui
    pyautogui.PAUSE = 0.0
    pyautogui.FAILSAFE = False


class MouseController:
    """Ultra-low latency mouse manipulator with true DPI-aware coordinates & multi-monitor support."""
    def __init__(self, enable_sound: bool = True):
        self.enable_sound = enable_sound
        self.is_dragging = False
        self.monitors: List[Dict[str, any]] = self.enumerate_monitors()
        self.active_monitor_index: int = -1  # -1 = Full Virtual Desktop spanning all displays
        self.x_origin, self.y_origin, self.screen_width, self.screen_height = self.get_virtual_desktop_bounds()
        self.last_pos = (self.x_origin + self.screen_width // 2, self.y_origin + self.screen_height // 2)

    def enumerate_monitors(self) -> List[Dict[str, any]]:
        """Enumerates physical and virtual displays with DPI-aware physical bounds."""
        if not IS_WINDOWS:
            w, h = pyautogui.size()
            return [{"id": 0, "name": "Основной дисплей", "left": 0, "top": 0, "width": w, "height": h, "is_primary": True}]

        monitors = []
        try:
            def enum_cb(hMonitor, hdcMonitor, lprcMonitor, dwData):
                r = lprcMonitor.contents
                w = max(1, r.right - r.left)
                h = max(1, r.bottom - r.top)
                monitors.append({
                    "id": len(monitors),
                    "name": f"Монитор {len(monitors) + 1} ({w}x{h})",
                    "left": int(r.left),
                    "top": int(r.top),
                    "width": int(w),
                    "height": int(h),
                    "is_primary": (r.left == 0 and r.top == 0)
                })
                return True

            MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HMONITOR, ctypes.wintypes.HDC, ctypes.POINTER(ctypes.wintypes.RECT), ctypes.wintypes.LPARAM)
            user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(enum_cb), 0)
        except Exception:
            pass

        if not monitors:
            w = user32.GetSystemMetrics(0)
            h = user32.GetSystemMetrics(1)
            monitors.append({"id": 0, "name": f"Основной дисплей ({w}x{h})", "left": 0, "top": 0, "width": w, "height": h, "is_primary": True})
        return monitors

    def set_active_monitor(self, index: int):
        """Locks cursor movement bounds to a specific monitor, or -1 for the entire multi-monitor span."""
        self.monitors = self.enumerate_monitors()
        if index < 0 or index >= len(self.monitors):
            self.active_monitor_index = -1
            self.x_origin, self.y_origin, self.screen_width, self.screen_height = self.get_virtual_desktop_bounds()
        else:
            self.active_monitor_index = index
            m = self.monitors[index]
            self.x_origin = m["left"]
            self.y_origin = m["top"]
            self.screen_width = m["width"]
            self.screen_height = m["height"]

    def cycle_monitor(self) -> int:
        """Cycles target display: Monitor 0 -> Monitor 1 -> ... -> Full Desktop (-1)."""
        self.monitors = self.enumerate_monitors()
        if not self.monitors:
            return -1
        next_idx = self.active_monitor_index + 1
        if next_idx >= len(self.monitors):
            next_idx = -1
        self.set_active_monitor(next_idx)
        return self.active_monitor_index

    def get_virtual_desktop_bounds(self) -> Tuple[int, int, int, int]:
        """Returns (x_origin, y_origin, width, height) of full multi-monitor virtual desktop."""
        if IS_WINDOWS:
            x_min = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
            y_min = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
            w_virt = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
            h_virt = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
            if w_virt > 0 and h_virt > 0:
                return x_min, y_min, w_virt, h_virt
            w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
            h = user32.GetSystemMetrics(1)  # SM_CYSCREEN
            return 0, 0, max(1, w), max(1, h)
        else:
            w, h = pyautogui.size()
            return 0, 0, w, h

    def get_screen_size(self) -> Tuple[int, int]:
        """Returns (width, height) of display space."""
        return self.screen_width, self.screen_height

    def get_cursor_pos(self) -> Tuple[int, int]:
        """Returns current mouse coordinates."""
        if IS_WINDOWS:
            pt = ctypes.wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            return pt.x, pt.y
        else:
            pos = pyautogui.position()
            return pos.x, pos.y

    def move_to(self, x: float, y: float):
        """Moves cursor directly to (x, y) with clamping across entire multi-monitor bounds."""
        target_x = max(self.x_origin, min(self.x_origin + self.screen_width - 1, int(round(x))))
        target_y = max(self.y_origin, min(self.y_origin + self.screen_height - 1, int(round(y))))
        self.last_pos = (target_x, target_y)

        if IS_WINDOWS:
            user32.SetCursorPos(target_x, target_y)
        else:
            pyautogui.moveTo(target_x, target_y)

    def click(self, button: str = "left"):
        """Performs a single click (left, right, or middle wheel click)."""
        if IS_WINDOWS:
            if button == "left":
                user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            elif button == "right":
                user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            elif button == "middle":
                user32.mouse_event(MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0)
                user32.mouse_event(MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)
            if self.enable_sound:
                self._play_click_sound()
        else:
            pyautogui.click(button=button)

    def task_view(self):
        """Triggers Windows Task View (Win + Tab)."""
        if IS_WINDOWS:
            user32.keybd_event(VK_LWIN, 0, 0, 0)
            user32.keybd_event(VK_TAB, 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_TAB, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.hotkey('win', 'tab')

    def show_desktop(self):
        """Toggles Show Desktop (Win + D)."""
        if IS_WINDOWS:
            user32.keybd_event(VK_LWIN, 0, 0, 0)
            user32.keybd_event(VK_D, 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_D, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.hotkey('win', 'd')

    def alt_tab(self):
        """Switches active window (Alt + Tab)."""
        if IS_WINDOWS:
            user32.keybd_event(VK_LMENU, 0, 0, 0)
            user32.keybd_event(VK_TAB, 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_TAB, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_LMENU, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.hotkey('alt', 'tab')

    def snipping_tool(self):
        """Opens Windows Snipping Tool (Win + Shift + S)."""
        if IS_WINDOWS:
            user32.keybd_event(VK_LWIN, 0, 0, 0)
            user32.keybd_event(VK_SHIFT, 0, 0, 0)
            user32.keybd_event(VK_S, 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_S, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.hotkey('win', 'shift', 's')

    def volume_up(self):
        """Increases system master volume."""
        if IS_WINDOWS:
            user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(VK_VOLUME_UP, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.press('volumeup')

    def volume_down(self):
        """Decreases system master volume."""
        if IS_WINDOWS:
            user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(VK_VOLUME_DOWN, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.press('volumedown')

    def volume_mute(self):
        """Toggles audio mute."""
        if IS_WINDOWS:
            user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.press('volumemute')

    def play_pause(self):
        """Toggles media play/pause."""
        if IS_WINDOWS:
            user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.press('playpause')

    def next_track(self):
        """Skips to next media track."""
        if IS_WINDOWS:
            user32.keybd_event(VK_MEDIA_NEXT_TRACK, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(VK_MEDIA_NEXT_TRACK, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.press('nexttrack')

    def prev_track(self):
        """Returns to previous media track."""
        if IS_WINDOWS:
            user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.press('prevtrack')

    def lock_workstation(self):
        """Locks the Windows workstation instantly."""
        if IS_WINDOWS:
            try:
                user32.LockWorkStation()
            except Exception:
                pass
        else:
            pyautogui.hotkey('win', 'l')

    def zoom(self, amount: int):
        """Performs zoom via Ctrl + Wheel."""
        if IS_WINDOWS:
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            delta = int(amount * 120)
            user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
            time.sleep(0.02)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.keyDown('ctrl')
            pyautogui.scroll(amount * 100)
            pyautogui.keyUp('ctrl')

    def next_slide(self):
        """Advances presentation slide or next media track."""
        if IS_WINDOWS:
            user32.keybd_event(VK_RIGHT, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(VK_RIGHT, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.press('right')

    def prev_slide(self):
        """Returns to previous presentation slide or previous track."""
        if IS_WINDOWS:
            user32.keybd_event(VK_LEFT, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(VK_LEFT, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.press('left')

    def snap_window_left(self):
        """Snaps active window to left half (Win + Left)."""
        if IS_WINDOWS:
            user32.keybd_event(VK_LWIN, 0, 0, 0)
            user32.keybd_event(VK_LEFT, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(VK_LEFT, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.hotkey('win', 'left')

    def snap_window_right(self):
        """Snaps active window to right half (Win + Right)."""
        if IS_WINDOWS:
            user32.keybd_event(VK_LWIN, 0, 0, 0)
            user32.keybd_event(VK_RIGHT, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(VK_RIGHT, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.hotkey('win', 'right')

    def snap_window_maximize(self):
        """Maximizes active window (Win + Up)."""
        if IS_WINDOWS:
            user32.keybd_event(VK_LWIN, 0, 0, 0)
            user32.keybd_event(VK_UP, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(VK_UP, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.hotkey('win', 'up')

    def snap_window_minimize(self):
        """Minimizes active window (Win + Down)."""
        if IS_WINDOWS:
            user32.keybd_event(VK_LWIN, 0, 0, 0)
            user32.keybd_event(VK_DOWN, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(VK_DOWN, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.hotkey('win', 'down')

    def switch_desktop_next(self):
        """Switches to next virtual desktop (Win + Ctrl + Right)."""
        if IS_WINDOWS:
            user32.keybd_event(VK_LWIN, 0, 0, 0)
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_RIGHT, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(VK_RIGHT, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.hotkey('win', 'ctrl', 'right')

    def switch_desktop_prev(self):
        """Switches to previous virtual desktop (Win + Ctrl + Left)."""
        if IS_WINDOWS:
            user32.keybd_event(VK_LWIN, 0, 0, 0)
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_LEFT, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(VK_LEFT, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.hotkey('win', 'ctrl', 'left')

    def copy(self):
        """Dispatches Ctrl + C."""
        if IS_WINDOWS:
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_C, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.hotkey('ctrl', 'c')

    def paste(self):
        """Dispatches Ctrl + V."""
        if IS_WINDOWS:
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_V, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.hotkey('ctrl', 'v')

    def undo(self):
        """Dispatches Ctrl + Z."""
        if IS_WINDOWS:
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_Z, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(VK_Z, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.hotkey('ctrl', 'z')

    def search_spotlight(self):
        """Dispatches Win + S for system search."""
        if IS_WINDOWS:
            user32.keybd_event(VK_LWIN, 0, 0, 0)
            user32.keybd_event(VK_S, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(VK_S, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.hotkey('win', 's')

    def browser_refresh(self):
        """Dispatches F5 refresh."""
        if IS_WINDOWS:
            user32.keybd_event(VK_F5, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(VK_F5, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.press('f5')

    def press_key(self, key: str):
        """Presses an on-screen / virtual key by name."""
        key_lower = key.lower()
        if IS_WINDOWS:
            vk_map = {
                'enter': VK_RETURN,
                'backspace': VK_BACK,
                'space': VK_SPACE,
                'escape': VK_ESCAPE,
                'esc': VK_ESCAPE,
                'tab': VK_TAB,
                'left': VK_LEFT,
                'right': VK_RIGHT,
                'up': VK_UP,
                'down': VK_DOWN,
            }
            if key_lower in vk_map:
                vk = vk_map[key_lower]
                user32.keybd_event(vk, 0, 0, 0)
                time.sleep(0.02)
                user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
            elif len(key) == 1:
                char_code = ord(key.upper())
                user32.keybd_event(char_code, 0, 0, 0)
                time.sleep(0.02)
                user32.keybd_event(char_code, 0, KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.press(key)

    def double_click(self, button: str = "left"):
        """Performs a precise rapid double-click on current pixel coordinates."""
        if IS_WINDOWS:
            if button == "left":
                user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                time.sleep(0.04)
                user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        else:
            pyautogui.doubleClick(button=button)

    def type_text(self, text: str):
        """Types Unicode text directly into the focused Windows application."""
        if not text:
            return
        if IS_WINDOWS:
            KEYEVENTF_UNICODE = 0x0004
            KEYEVENTF_KEYUP = 0x0002
            for ch in text:
                code = ord(ch)
                user32.keybd_event(0, code, KEYEVENTF_UNICODE, 0)
                time.sleep(0.004)
                user32.keybd_event(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0)
                time.sleep(0.004)
        else:
            pyautogui.write(text)

    def mouse_down(self, button: str = "left"):
        """Presses and holds the mouse button down."""
        if button == "left":
            self.is_dragging = True
            if IS_WINDOWS:
                user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            else:
                pyautogui.mouseDown(button="left")

    def mouse_up(self, button: str = "left"):
        """Releases the mouse button."""
        if button == "left":
            self.is_dragging = False
            if IS_WINDOWS:
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            else:
                pyautogui.mouseUp(button="left")

    def scroll(self, amount: int):
        """Scrolls the vertical wheel. Positive = up, Negative = down."""
        if amount == 0:
            return
        if IS_WINDOWS:
            delta = int(amount * 120)
            user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
        else:
            pyautogui.scroll(amount * 50)

    def _play_click_sound(self):
        """OS click sound disabled to avoid Windows error dings."""
        pass

    def get_screen_loupe(self, screen_x: int, screen_y: int, radius: int = 40, zoom: float = 2.0) -> np.ndarray:
        """
        Captures a magnified region around the screen cursor.
        If desktop grab is unavailable (headless / lockscreen), generates a synthetic CAD reticle grid.
        """
        patch_size = radius * 2
        try:
            from PIL import ImageGrab
            x1, y1 = max(0, screen_x - radius), max(0, screen_y - radius)
            x2, y2 = x1 + patch_size, y1 + patch_size
            pil_img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            if img.shape[0] != patch_size or img.shape[1] != patch_size:
                img = cv2.resize(img, (patch_size, patch_size))
        except Exception:
            # Synthetic CAD precision grid fallback
            img = np.full((patch_size, patch_size, 3), 24, dtype=np.uint8)
            cv2.line(img, (0, radius), (patch_size, radius), (60, 60, 70), 1)
            cv2.line(img, (radius, 0), (radius, patch_size), (60, 60, 70), 1)

        # Magnify by zoom factor
        zoom_size = int(patch_size * zoom)
        zoomed = cv2.resize(img, (zoom_size, zoom_size), interpolation=cv2.INTER_NEAREST)

        # Reticle in zoomed center
        cx, cy = zoom_size // 2, zoom_size // 2
        cv2.line(zoomed, (cx - 10, cy), (cx + 10, cy), (0, 242, 254), 1, cv2.LINE_AA)
        cv2.line(zoomed, (cx, cy - 10), (cx, cy + 10), (0, 242, 254), 1, cv2.LINE_AA)
        cv2.circle(zoomed, (cx, cy), 2, (255, 255, 255), -1, cv2.LINE_AA)

        return zoomed

    def take_screenshot(self, output_dir: str = "screenshots") -> Tuple[str, str]:
        """
        Captures a high-resolution snapshot of the desktop.
        Saves to screenshots folder and returns (absolute_path, filename).
        If headless/locked, creates a synthetic test screen image.
        """
        import os
        import datetime
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:21]
        filename = f"aeropoint_snap_{timestamp}.png"
        filepath = os.path.join(output_dir, filename)

        try:
            from PIL import ImageGrab
            pil_img = ImageGrab.grab()
            pil_img.save(filepath, "PNG")
        except Exception:
            # Synthetic canvas fallback
            synth = np.zeros((1080, 1920, 3), dtype=np.uint8)
            cv2.putText(synth, f"AEROPOINT AIR-SNAP: {timestamp}", (100, 200),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 242, 254), 2, cv2.LINE_AA)
            cv2.imwrite(filepath, synth)

        return os.path.abspath(filepath), filename
