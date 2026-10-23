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
from typing import Tuple, Optional

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
    VK_VOLUME_MUTE = 0xAD
    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_UP = 0xAF
    VK_MEDIA_PLAY_PAUSE = 0xB3
else:
    import pyautogui
    pyautogui.PAUSE = 0.0
    pyautogui.FAILSAFE = False


class MouseController:
    """Ultra-low latency mouse manipulator with true DPI-aware coordinates."""
    def __init__(self, enable_sound: bool = True):
        self.enable_sound = enable_sound
        self.is_dragging = False
        self.screen_width, self.screen_height = self.get_screen_size()
        self.last_pos = (self.screen_width // 2, self.screen_height // 2)

    def get_screen_size(self) -> Tuple[int, int]:
        """Returns (width, height) of display space."""
        if IS_WINDOWS:
            # Check virtual screen size for multi-monitor setups
            w_virt = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
            h_virt = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
            if w_virt > 0 and h_virt > 0:
                return w_virt, h_virt
            w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
            h = user32.GetSystemMetrics(1)  # SM_CYSCREEN
            return max(1, w), max(1, h)
        else:
            w, h = pyautogui.size()
            return w, h

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
        """Moves cursor directly to (x, y) with clamping across entire monitor width."""
        target_x = max(0, min(self.screen_width - 1, int(round(x))))
        target_y = max(0, min(self.screen_height - 1, int(round(y))))
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
