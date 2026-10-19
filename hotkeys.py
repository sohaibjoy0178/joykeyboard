"""Windows global voice chord, delivered through Qt's native message loop."""
import ctypes
from ctypes import wintypes as w

from PySide6.QtCore import QAbstractNativeEventFilter
from PySide6.QtWidgets import QApplication

from core import parse_voice_shortcut
from windows import IS_WINDOWS

if IS_WINDOWS:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.RegisterHotKey.argtypes = [w.HWND, ctypes.c_int, w.UINT, w.UINT]
    user32.RegisterHotKey.restype = w.BOOL
    user32.UnregisterHotKey.argtypes = [w.HWND, ctypes.c_int]
    user32.UnregisterHotKey.restype = w.BOOL


class VoiceHotkey(QAbstractNativeEventFilter):
    def __init__(self, hwnd, callback):
        super().__init__()
        self.hwnd = hwnd
        self.callback = callback
        self.identity = None
        self.shortcut = None
        QApplication.instance().installNativeEventFilter(self)

    def register(self, value):
        canonical, modifiers, key = parse_voice_shortcut(value)
        if canonical == self.shortcut:
            return canonical
        if not IS_WINDOWS:
            raise OSError("Global voice shortcuts require Windows.")
        identity = 0x4A11 if self.identity == 0x4A10 else 0x4A10
        if not user32.RegisterHotKey(self.hwnd, identity, modifiers | 0x4000, key):
            raise OSError(f"{canonical} is unavailable or used by another app. Choose a different shortcut.")
        if self.identity is not None:
            user32.UnregisterHotKey(self.hwnd, self.identity)
        self.identity, self.shortcut = identity, canonical
        return canonical

    def nativeEventFilter(self, event_type, message):
        if bytes(event_type) in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            event = w.MSG.from_address(int(message))
            if event.message == 0x0312 and event.hWnd == self.hwnd and event.wParam == self.identity:
                self.callback()
                return True, 0
        return False, 0

    def close(self):
        if self.identity is not None:
            user32.UnregisterHotKey(self.hwnd, self.identity)
            self.identity = self.shortcut = None
        QApplication.instance().removeNativeEventFilter(self)
