"""
Windows System Tray Service for AeroPoint Quantum 3.0
=====================================================
Integrates AeroPoint into the Windows Taskbar Notification Area (System Tray):
- Displays live tray icon next to the Windows clock
- Tooltip displays active telemetry and control state
- Left-click / double-click opens AeroPoint Studio in browser
- Right-click pops up a native Windows context menu:
    - 🌐 Открыть AeroPoint Studio
    - ⏸️ Пауза / Возобновить управление
    - 🎯 Быстрая перекалибровка
    - ❌ Выход
- Uses pure ctypes User32/Shell32 Win32 API with zero external dependencies.
"""

import sys
import time
import threading
import webbrowser
from typing import Optional

IS_WINDOWS = sys.platform.startswith("win")

if IS_WINDOWS:
    import ctypes
    import ctypes.wintypes as w

    user32 = ctypes.windll.user32
    shell32 = ctypes.windll.shell32
    kernel32 = ctypes.windll.kernel32

    # Win32 Constants
    WM_USER = 0x0400
    WM_TRAYICON = WM_USER + 20
    WM_COMMAND = 0x0111
    WM_DESTROY = 0x0002
    WM_RBUTTONUP = 0x0205
    WM_LBUTTONUP = 0x0202
    WM_LBUTTONDBLCLK = 0x0203

    NIM_ADD = 0x00000000
    NIM_MODIFY = 0x00000001
    NIM_DELETE = 0x00000002

    NIF_MESSAGE = 0x00000001
    NIF_ICON = 0x00000002
    NIF_TIP = 0x00000004

    IDI_APPLICATION = 32512
    IMAGE_ICON = 1
    LR_DEFAULTSIZE = 0x0040
    LR_SHARED = 0x8000

    MF_STRING = 0x00000000
    MF_SEPARATOR = 0x00000800
    TPM_RIGHTBUTTON = 0x0002

    ID_TRAY_OPEN = 1001
    ID_TRAY_TOGGLE_PAUSE = 1002
    ID_TRAY_CALIBRATE = 1003
    ID_TRAY_EXIT = 1004

    WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
    HCURSOR = w.HANDLE

    class WNDCLASSEXW(ctypes.Structure):
        _fields_ = [
            ('cbSize', w.UINT),
            ('style', w.UINT),
            ('lpfnWndProc', WNDPROC),
            ('cbClsExtra', ctypes.c_int),
            ('cbWndExtra', ctypes.c_int),
            ('hInstance', w.HINSTANCE),
            ('hIcon', w.HICON),
            ('hCursor', HCURSOR),
            ('hbrBackground', w.HBRUSH),
            ('lpszMenuName', w.LPCWSTR),
            ('lpszClassName', w.LPCWSTR),
            ('hIconSm', w.HICON)
        ]

    class NOTIFYICONDATAW(ctypes.Structure):
        _fields_ = [
            ('cbSize', w.DWORD),
            ('hWnd', w.HWND),
            ('uID', w.UINT),
            ('uFlags', w.UINT),
            ('uCallbackMessage', w.UINT),
            ('hIcon', w.HICON),
            ('szTip', w.WCHAR * 128),
            ('dwState', w.DWORD),
            ('dwStateMask', w.DWORD),
            ('szInfo', w.WCHAR * 256),
            ('uTimeoutOrVersion', w.UINT),
            ('szInfoTitle', w.WCHAR * 64),
            ('dwInfoFlags', w.DWORD),
            ('guidItem', ctypes.c_byte * 16),
            ('hBalloonIcon', w.HICON)
        ]


class WindowsTrayService:
    """Low-overhead native Windows system tray icon manager."""
    def __init__(self, manager=None, port: int = 5055):
        self.manager = manager
        self.port = port
        self.running = False
        self.hwnd = None
        self.nid = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        """Starts background system tray thread."""
        if not IS_WINDOWS or self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_tray, daemon=True, name="AeroPoint-Tray")
        self.thread.start()
        print(f"[+] Windows System Tray service active (Tray Icon initialized)")

    def stop(self):
        """Removes tray icon and terminates window thread."""
        self.running = False
        if self.hwnd and IS_WINDOWS:
            try:
                if self.nid:
                    shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.nid))
                user32.PostMessageW(self.hwnd, WM_DESTROY, 0, 0)
            except Exception:
                pass
        self.hwnd = None

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAYICON:
            if lparam in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                webbrowser.open(f"http://127.0.0.1:{self.port}")
            elif lparam == WM_RBUTTONUP:
                self._show_context_menu(hwnd)
            return 0
        elif msg == WM_COMMAND:
            cmd_id = wparam & 0xFFFF
            if cmd_id == ID_TRAY_OPEN:
                webbrowser.open(f"http://127.0.0.1:{self.port}")
            elif cmd_id == ID_TRAY_TOGGLE_PAUSE:
                if self.manager:
                    self.manager.manual_pause = not self.manager.manual_pause
                    print(f"[*] Tray menu: Manual pause is now {self.manager.manual_pause}")
            elif cmd_id == ID_TRAY_CALIBRATE:
                if self.manager and hasattr(self.manager, 'precision_engine'):
                    self.manager.trigger_calibration(3.0) if hasattr(self.manager, 'trigger_calibration') else self.manager.precision_engine.reset()
                    print("[*] Tray menu: Calibration triggered")
            elif cmd_id == ID_TRAY_EXIT:
                if self.manager:
                    self.manager.stop()
                sys.exit(0)
            return 0
        elif msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _show_context_menu(self, hwnd):
        hmenu = user32.CreatePopupMenu()
        user32.AppendMenuW(hmenu, MF_STRING, ID_TRAY_OPEN, "🌐 Открыть AeroPoint Studio")
        pause_text = "▶️ Возобновить управление" if (self.manager and self.manager.manual_pause) else "⏸️ Приостановить управление"
        user32.AppendMenuW(hmenu, MF_STRING, ID_TRAY_TOGGLE_PAUSE, pause_text)
        user32.AppendMenuW(hmenu, MF_STRING, ID_TRAY_CALIBRATE, "🎯 Авто-калибровка фильтров")
        user32.AppendMenuW(hmenu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(hmenu, MF_STRING, ID_TRAY_EXIT, "❌ Завершить AeroPoint")

        pos = w.POINT()
        user32.GetCursorPos(ctypes.byref(pos))
        user32.SetForegroundWindow(hwnd)
        user32.TrackPopupMenuEx(hmenu, TPM_RIGHTBUTTON, pos.x, pos.y, hwnd, None)
        user32.DestroyMenu(hmenu)

    def _run_tray(self):
        class_name = f"AeroPointTrayClass_{int(time.time())}"
        hinstance = kernel32.GetModuleHandleW(None)

        wndproc_cb = WNDPROC(self._wnd_proc)

        wndclass = WNDCLASSEXW()
        wndclass.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wndclass.lpfnWndProc = wndproc_cb
        wndclass.hInstance = hinstance
        wndclass.lpszClassName = class_name
        user32.RegisterClassExW(ctypes.byref(wndclass))

        self.hwnd = user32.CreateWindowExW(
            0, class_name, "AeroPoint Tray Window",
            0, 0, 0, 0, 0, 0, 0, hinstance, None
        )

        # Application Icon
        hicon = user32.LoadImageW(
            0, IDI_APPLICATION, IMAGE_ICON,
            0, 0, LR_DEFAULTSIZE | LR_SHARED
        )

        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self.hwnd
        nid.uID = 100
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAYICON
        nid.hIcon = hicon
        nid.szTip = "AeroPoint Quantum 3.0 — Neural Gesture HCI"
        self.nid = nid

        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))

        # Windows Message pump
        msg = w.MSG()
        while self.running and user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        # Cleanup
        try:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
        except Exception:
            pass
