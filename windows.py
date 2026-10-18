"""Small Windows integration layer; Unicode insertion never touches clipboard."""
from __future__ import annotations

import ctypes
import os
import time
from ctypes import wintypes as w
from dataclasses import dataclass

IS_WINDOWS = os.name == "nt"
INPUT_TAG = 0x4A4F594B

if IS_WINDOWS:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetForegroundWindow.restype = w.HWND
    user32.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
    user32.GetWindowThreadProcessId.restype = w.DWORD
    user32.IsWindow.argtypes = [w.HWND]
    user32.SetForegroundWindow.argtypes = [w.HWND]
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user32.GetAsyncKeyState.restype = ctypes.c_short
    user32.GetWindowTextW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]

    class GuiInfo(ctypes.Structure):
        _fields_ = [("cbSize", w.DWORD), ("flags", w.DWORD),
                    ("hwndActive", w.HWND), ("hwndFocus", w.HWND),
                    ("hwndCapture", w.HWND), ("hwndMenuOwner", w.HWND),
                    ("hwndMoveSize", w.HWND), ("hwndCaret", w.HWND), ("rcCaret", w.RECT)]

    class KeyInput(ctypes.Structure):
        _fields_ = [("wVk", w.WORD), ("wScan", w.WORD), ("dwFlags", w.DWORD),
                    ("time", w.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

    class MouseInput(ctypes.Structure):
        _fields_ = [("dx", w.LONG), ("dy", w.LONG), ("mouseData", w.DWORD),
                    ("dwFlags", w.DWORD), ("time", w.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

    class InputUnion(ctypes.Union):
        _fields_ = [("ki", KeyInput), ("mi", MouseInput)]

    class Input(ctypes.Structure):
        _fields_ = [("type", w.DWORD), ("value", InputUnion)]

    user32.SendInput.argtypes = [w.UINT, ctypes.POINTER(Input), ctypes.c_int]
    user32.SendInput.restype = w.UINT
    user32.GetGUIThreadInfo.argtypes = [w.DWORD, ctypes.POINTER(GuiInfo)]


@dataclass(frozen=True)
class Target:
    hwnd: int
    pid: int
    focus: int
    title: str


def key_down(key: int) -> bool:
    return IS_WINDOWS and bool(user32.GetAsyncKeyState(key) & 0x8000)


def foreground_target() -> Target | None:
    if not IS_WINDOWS:
        return None
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = w.DWORD()
    thread = user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    info = GuiInfo()
    info.cbSize = ctypes.sizeof(info)
    focus = int(info.hwndFocus or 0) if user32.GetGUIThreadInfo(thread, ctypes.byref(info)) else 0
    title = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, title, len(title))
    return Target(int(hwnd), int(pid.value), focus, title.value)


def insert_text(target: Target, text: str) -> None:
    if not IS_WINDOWS:
        raise RuntimeError("Automatic typing is available in the Windows build.")
    if not text:
        return
    if not user32.IsWindow(target.hwnd):
        raise RuntimeError("Target window closed. Text is available in Transcript.")
    active = foreground_target()
    if active is None:
        raise RuntimeError("No active input window. Copy the transcript instead.")
    if active.hwnd != target.hwnd:
        if active.pid != os.getpid():
            raise RuntimeError("Focus changed to another app. Text kept in Transcript.")
        user32.SetForegroundWindow(target.hwnd)
        time.sleep(0.12)
        active = foreground_target()
    if active is None or active.hwnd != target.hwnd or active.pid != target.pid:
        raise RuntimeError("Could not focus the original app. Copy the transcript instead.")
    if target.focus and active.focus != target.focus:
        raise RuntimeError("Focused control changed. Text kept in Transcript.")
    if any(key_down(key) for key in (0x10, 0x11, 0x12, 0x5B, 0x5C)):
        raise RuntimeError("Release modifier keys, then use Type again.")
    # Windows UTF-16 input supports Bengali and surrogate pairs without keyboard-layout conversion.
    batches = []
    events = []
    for character in text.replace("\r\n", "\n").replace("\r", "\n"):
        surrogate = ord(character) > 0xFFFF
        boundary = surrogate or character == "\n"
        if boundary and events:
            batches.append((events, True))
            events = []
        if character == "\n":
            batches.append(([Input(1, InputUnion(ki=KeyInput(0x0D, 0, 0, 0, INPUT_TAG))),
                             Input(1, InputUnion(ki=KeyInput(0x0D, 0, 0x0002, 0, INPUT_TAG)))], True))
            continue
        raw = character.encode("utf-16-le")
        for index in range(0, len(raw), 2):
            unit = int.from_bytes(raw[index:index + 2], "little")
            events.extend((Input(1, InputUnion(ki=KeyInput(0, unit, 0x0004, 0, INPUT_TAG))),
                           Input(1, InputUnion(ki=KeyInput(0, unit, 0x0004 | 0x0002, 0, INPUT_TAG)))))
        if surrogate or len(events) >= 256:
            batches.append((events, surrogate))
            events = []
    if events:
        batches.append((events, False))
    for batch, commit_boundary in batches:
        current = foreground_target()
        if not current or current.hwnd != target.hwnd or current.pid != target.pid:
            raise RuntimeError("Focus changed during typing; insertion stopped.")
        if target.focus and current.focus != target.focus:
            raise RuntimeError("Focused control changed during typing; insertion stopped.")
        inputs = (Input * len(batch))(*batch)
        if user32.SendInput(len(inputs), inputs, ctypes.sizeof(Input)) != len(inputs):
            raise RuntimeError("Windows blocked typing. Copy text, or match the target app's privilege level.")
        if commit_boundary:
            # shortcut: 30ms lets Windows editors commit input boundaries; test new target editors before promising support.
            time.sleep(0.03)
