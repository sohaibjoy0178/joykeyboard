"""Word composition for Windows, with a dedicated low-level hook message thread.

Composition stays in the toolbar until a delimiter or candidate selection commits it.
Own output is tagged to avoid conversion loops; external remapped keys can compose.
"""
from __future__ import annotations

import ctypes
import os
import queue
import threading
import time
from ctypes import wintypes as w

from windows import INPUT_TAG, IS_WINDOWS, Target, foreground_target

_WAKE = 0x8000 + 73
_MODIFIERS = {0x11, 0x12, 0x5B, 0x5C, 0xA2, 0xA3, 0xA4, 0xA5}
_SHIFTS = {0x10, 0xA0, 0xA1}
_PUNCTUATION = {
    0xBA: (';', ':'), 0xBB: ('=', '+'), 0xBC: (',', '<'),
    0xBD: ('-', '_'), 0xBE: ('.', '>'), 0xBF: ('/', '?'),
    0xC0: ('`', '~'), 0xDB: ('[', '{'), 0xDC: ('\\', '|'),
    0xDD: (']', '}'), 0xDE: ("'", '"'),
}

if IS_WINDOWS:
    from windows import GuiInfo, Input, InputUnion, KeyInput, user32

    _LRESULT = ctypes.c_ssize_t
    _HOOKPROC = ctypes.WINFUNCTYPE(_LRESULT, ctypes.c_int, w.WPARAM, w.LPARAM)

    class _HookEvent(ctypes.Structure):
        _fields_ = [("vkCode", w.DWORD), ("scanCode", w.DWORD), ("flags", w.DWORD),
                    ("time", w.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

    user32.SetWindowsHookExW.argtypes = [ctypes.c_int, _HOOKPROC, w.HINSTANCE, w.DWORD]
    user32.SetWindowsHookExW.restype = w.HANDLE
    user32.CallNextHookEx.argtypes = [w.HANDLE, ctypes.c_int, w.WPARAM, w.LPARAM]
    user32.CallNextHookEx.restype = _LRESULT
    user32.UnhookWindowsHookEx.argtypes = [w.HANDLE]
    user32.PostThreadMessageW.argtypes = [w.DWORD, w.UINT, w.WPARAM, w.LPARAM]
    user32.GetMessageW.argtypes = [ctypes.POINTER(w.MSG), w.HWND, w.UINT, w.UINT]
    user32.PeekMessageW.argtypes = [ctypes.POINTER(w.MSG), w.HWND, w.UINT, w.UINT, w.UINT]
    user32.GetClassNameW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
    user32.GetWindowLongW.argtypes = [w.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = w.LONG
    user32.SetTimer.argtypes = [w.HWND, ctypes.c_size_t, w.UINT, ctypes.c_void_p]
    user32.SetTimer.restype = ctypes.c_size_t
    user32.KillTimer.argtypes = [w.HWND, ctypes.c_size_t]
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.GetCurrentThreadId.restype = w.DWORD
    _kernel32.GetModuleHandleW.argtypes = [w.LPCWSTR]
    _kernel32.GetModuleHandleW.restype = w.HMODULE


def _identity(target: Target | None):
    return (target.hwnd, target.pid, target.focus) if target else None


def _native_password(target: Target) -> bool:
    if not IS_WINDOWS or not target.focus:
        return False
    name = ctypes.create_unicode_buffer(128)
    user32.GetClassNameW(target.focus, name, len(name))
    # ES_PASSWORD applies to native Edit and RichEdit controls. Custom secure fields need TSF/UIA support.
    return "edit" in name.value.lower() and bool(user32.GetWindowLongW(target.focus, -16) & 0x20)


def _caret(target: Target):
    if not IS_WINDOWS:
        return None
    thread = user32.GetWindowThreadProcessId(target.hwnd, None)
    info = GuiInfo()
    info.cbSize = ctypes.sizeof(info)
    if not user32.GetGUIThreadInfo(thread, ctypes.byref(info)) or not info.hwndCaret:
        return None
    return (int(info.hwndCaret), info.rcCaret.left, info.rcCaret.top)


class KeyboardHook:
    def __init__(self, engine, on_update, on_error):
        self.engine = engine
        self.on_update = on_update
        self.on_error = on_error
        self._enabled = False
        self.layout = "phonetic"
        self.output_encoding = "unicode"
        self.raw = ""
        self.rendered = ""
        self.suggestions = []
        self._target = None
        self._caret_at_start = None
        self._capturing = False
        self._held = set()
        self._suppressed = set()
        self._replay_keys = set()
        self._replayed_down = set()
        self._chord = False
        self._queue = queue.Queue(maxsize=256)
        self._thread = None
        self._thread_id = 0
        self._ready = threading.Event()
        self._start_error = None
        self._suggest_queue = queue.Queue(maxsize=1)
        self._suggest_stop = threading.Event()
        self._suggest_thread = None
        self._revision = 0

    @property
    def enabled(self):
        return self._enabled

    def start(self):
        if not IS_WINDOWS:
            raise RuntimeError("Global keyboard typing requires Windows.")
        if self._thread and self._thread.is_alive():
            return
        self._ready.clear()
        self._suggest_stop.clear()
        self._start_error = None
        self._thread = threading.Thread(target=self._run, name="JoyKeyboard input", daemon=True)
        self._thread.start()
        if not self._ready.wait(3):
            raise RuntimeError("Windows keyboard hook did not start.")
        if self._start_error:
            raise RuntimeError(self._start_error)

    def stop(self):
        self._enabled = False
        self._suggest_stop.set()
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=3)
        if self._suggest_thread and self._suggest_thread is not threading.current_thread():
            self._suggest_thread.join(timeout=3)

    def set_enabled(self, enabled: bool):
        self._post(("enabled", bool(enabled)))

    def set_layout(self, layout: str):
        self._post(("layout", layout))

    def set_output_encoding(self, encoding: str):
        if encoding not in ("unicode", "bijoy"):
            raise ValueError("Keyboard output must be unicode or bijoy.")
        self._post(("encoding", encoding))

    def choose(self, index: int):
        self._post(("choose", index))

    def reset(self):
        self._post(("reset",))

    def _post(self, item):
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            self._enabled = False
            self.on_error("Keyboard paused: input queue full. Pending text remains in composition preview.")
            return False
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, _WAKE, 0, 0)
        else:
            self._drain()
        return True

    def _run(self):
        hook = timer = None
        try:
            self._thread_id = int(_kernel32.GetCurrentThreadId())
            message = w.MSG()
            user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 0)
            # Releases identify left/right keys; seeding generic aliases would leave them held forever.
            self._held = {key for key in (_MODIFIERS | _SHIFTS) - {0x10, 0x11, 0x12}
                          if user32.GetAsyncKeyState(key) & 0x8000}

            @_HOOKPROC
            def callback(code, kind, address):
                if code >= 0:
                    event = ctypes.cast(address, ctypes.POINTER(_HookEvent)).contents
                    try:
                        if self._capture(int(event.vkCode), kind in (0x100, 0x104), int(event.flags), int(event.dwExtraInfo)):
                            return 1
                    except Exception as error:
                        self._enabled = False
                        self._post(("error", f"Keyboard paused: {error}"))
                return user32.CallNextHookEx(hook, code, kind, address)

            self._callback = callback
            hook = user32.SetWindowsHookExW(13, callback, _kernel32.GetModuleHandleW(None), 0)
            if not hook:
                raise ctypes.WinError(ctypes.get_last_error())
            timer = user32.SetTimer(None, 0, 100, None)
            self._ready.set()
            while True:
                status = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                if status <= 0:
                    if status < 0:
                        raise ctypes.WinError(ctypes.get_last_error())
                    break
                if message.message == _WAKE:
                    self._drain()
                elif message.message == 0x113:
                    self._check_context()
                else:
                    user32.TranslateMessage(ctypes.byref(message))
                    user32.DispatchMessageW(ctypes.byref(message))
        except Exception as error:
            self._start_error = str(error)
            self._enabled = False
            self.on_error(f"Keyboard unavailable: {error}")
        finally:
            for key in list(self._replayed_down):
                try:
                    self._replay(key, False)
                except Exception as error:
                    self.on_error(f"Release keyboard modifiers manually: {error}")
            if timer:
                user32.KillTimer(None, timer)
            if hook:
                user32.UnhookWindowsHookEx(hook)
            self._thread_id = 0
            self._ready.set()

    def _capture(self, key: int, down: bool, flags: int = 0, extra_info: int = 0) -> bool:
        """Fast hook decision; engine work and SendInput run after callback returns."""
        if extra_info == INPUT_TAG or (flags & 0x12 and key == 0x7B):
            return False
        repeated = key in self._held
        if down:
            self._held.add(key)
        else:
            self._held.discard(key)
        if self._chord or key in self._replay_keys:
            if down:
                self._replay_keys.add(key)
            else:
                self._replay_keys.discard(key)
                self._suppressed.discard(key)
            self._chord = bool(self._held & _MODIFIERS)
            self._post(("replay", key, down))
            return True
        if not down:
            if key in self._suppressed:
                self._suppressed.discard(key)
                return True
            return False
        modified = bool(self._held & _MODIFIERS) or bool(flags & 0x20)
        shift = bool(self._held & _SHIFTS)
        if key == 0x7B and not modified and not shift:
            if not repeated:
                self._post(("toggle",))
            self._suppressed.add(key)
            return True
        if not self._enabled:
            return False
        target = foreground_target()
        if not target or target.pid == os.getpid() or _native_password(target):
            if self._capturing:
                self._post(("context",))
            return False
        if modified:
            # Commit before the modifier reaches the editor; replay its down event in the same SendInput batch.
            if key in _MODIFIERS and self._capturing:
                self._chord = True
                self._replay_keys.add(key)
                if self._post(("key", target, key, "", True)):
                    return True
                self._chord = False
                self._replay_keys.discard(key)
            return False
        if key in _SHIFTS or key == 0x14:
            return False
        text = self._character(key, shift)
        select = 0x70 <= key <= 0x77 and self._capturing and not shift
        boundary = key in (0x08, 0x09, 0x0D, 0x1B, 0x20, 0x21, 0x22, 0x23, 0x24,
                           0x25, 0x26, 0x27, 0x28, 0x2E)
        if not text and not select and not (boundary and self._capturing):
            return False
        if text and not self._capturing:
            self._capturing = True
        if not self._post(("key", target, key, text, False)):
            return False
        self._suppressed.add(key)
        return True

    @staticmethod
    def _character(key, shift):
        # shortcut: Bengali layouts use US physical key positions; add locale-aware translation for other Latin layouts.
        if 0x41 <= key <= 0x5A:
            caps = bool(IS_WINDOWS and user32.GetKeyState(0x14) & 1)
            value = chr(key)
            return value if shift != caps else value.lower()
        if 0x30 <= key <= 0x39:
            return ")!@#$%^&*("[key - 0x30] if shift else chr(key)
        if 0x60 <= key <= 0x69:
            return chr(key - 0x60 + 0x30)
        if key in _PUNCTUATION:
            return _PUNCTUATION[key][int(shift)]
        return ""

    def _drain(self):
        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                return
            try:
                self._command(item)
            except Exception as error:
                self._enabled = False
                self.on_error(f"Keyboard paused: {error}. Pending text: {self.raw or self.rendered}")

    def _command(self, item):
        kind = item[0]
        if kind in ("enabled", "toggle"):
            self._commit()
            self._enabled = item[1] if kind == "enabled" else not self._enabled
            self._publish()
        elif kind == "layout":
            self._commit()
            self.layout = item[1]
            self._publish()
        elif kind == "encoding":
            self._commit()
            self.output_encoding = item[1]
        elif kind == "choose":
            index = item[1]
            if 0 <= index < len(self.suggestions):
                self._commit(text=self.suggestions[index])
        elif kind == "reset":
            self._clear()
        elif kind == "context":
            self._check_context()
        elif kind == "error":
            self.on_error(item[1])
        elif kind == "replay":
            self._replay(*item[1:])
        elif kind == "suggestions":
            if item[1] == self._revision and self.raw:
                self.suggestions = item[2]
                self._publish()
        elif kind == "key":
            self._consume(*item[1:])

    def _consume(self, target, key, text, modifier=False):
        if self.raw and _identity(target) != _identity(self._target):
            self._discard("Input focus changed")
        elif self.raw and _caret(target) != self._caret_at_start:
            self._discard("Input caret changed")
        if not self._safe_target(target):
            if self.raw:
                self._discard("Input focus changed")
            self.on_error(f"Keyboard input stopped after focus changed. Uncommitted key: {text or key}")
            return
        if not self.raw:
            self._target = target
        if modifier:
            self._commit(virtual_key=key, key_down_only=True)
            return
        if 0x70 <= key <= 0x77:
            if key - 0x70 < len(self.suggestions):
                self._commit(text=self.suggestions[key - 0x70])
            return
        if key == 0x08:
            self.raw = self.raw[:-1]
            self._refresh()
        elif key == 0x1B:
            self._commit(text=self.raw)
        elif not text:
            self._commit(virtual_key=key)
        elif self.layout == "phonetic" and text in ".,;:!?()[]{}\"/\\=+<>|@#$%^&*":
            self._commit(text=(self.rendered if self.raw else "") + text)
        elif len(self.raw) >= 128:
            self._commit()
            self._target = target
            self.raw = text
            self._caret_at_start = _caret(target)
            self._refresh()
        else:
            if not self.raw:
                self._target = target
                self._caret_at_start = _caret(target)
            self.raw += text
            self._refresh()

    def _refresh(self):
        self._revision += 1
        self._capturing = bool(self.raw)
        self.rendered = self.engine.convert(self.raw, self.layout) if self.raw else ""
        self.suggestions = []
        if self.raw:
            if self._thread_id:
                # Dictionary I/O and fuzzy matching must not block Windows' hook message pump.
                if self._suggest_thread is None or not self._suggest_thread.is_alive():
                    self._suggest_thread = threading.Thread(target=self._suggest_loop, daemon=True,
                                                            name="JoyKeyboard suggestions")
                    self._suggest_thread.start()
                try:
                    self._suggest_queue.get_nowait()
                except queue.Empty:
                    pass
                self._suggest_queue.put_nowait((self._revision, self.rendered))
            else:
                self.suggestions = self.engine.suggest(self.rendered, 8)
        self._publish()

    def _suggest_loop(self):
        while not self._suggest_stop.is_set():
            try:
                revision, prefix = self._suggest_queue.get(timeout=.2)
            except queue.Empty:
                continue
            try:
                suggestions = self.engine.suggest(prefix, 8)
                if not self._suggest_stop.is_set():
                    self._post(("suggestions", revision, suggestions))
            except Exception as error:
                if not self._suggest_stop.is_set():
                    self._post(("error", f"Word suggestions unavailable: {error}"))

    def _publish(self):
        self.on_update(self.raw, self.rendered, list(self.suggestions))

    def _clear(self):
        self._revision += 1
        self.raw = self.rendered = ""
        self.suggestions = []
        self._capturing = False
        self._target = None
        self._caret_at_start = None
        self._publish()

    def _safe_target(self, target):
        return bool(target and target.pid != os.getpid() and
                    _identity(foreground_target()) == _identity(target) and not _native_password(target))

    def _check_context(self):
        if self.raw and (not self._safe_target(self._target) or
                         (_caret(self._target) != self._caret_at_start)):
            self._discard("Input focus or caret changed")

    def _discard(self, reason):
        pending = self.raw
        self._clear()
        self.on_error(f"{reason}. Composition not inserted: {pending}")

    def _commit(self, text=None, virtual_key=None, key_down_only=False):
        value = self.rendered if text is None else text
        if text is None and self.raw in self.engine.snippets:
            value = self.engine.snippets[self.raw]
        target = self._target
        if value or virtual_key is not None:
            if not target or not self._safe_target(target):
                if self.raw:
                    self._discard("Input focus changed")
                return
            if self.raw and _caret(target) != self._caret_at_start:
                self._discard("Input caret changed")
                return
            output = value
            if self.output_encoding == "bijoy":
                from keyboard_engine import to_ansi
                output = to_ansi(value)
            self._send(output, virtual_key, key_down_only)
            if self._thread_id and self._caret_at_start is not None:
                # shortcut: allow 100ms for native caret settling; TSF is needed for true inline composition.
                deadline = time.monotonic() + .1
                message = w.MSG()
                previous, changed = self._caret_at_start, time.monotonic()
                moved = False
                while self._safe_target(target) and time.monotonic() < deadline:
                    user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 0)
                    current = _caret(target)
                    if current != previous:
                        previous, changed, moved = current, time.monotonic(), True
                    if moved and time.monotonic() - changed >= .02:
                        break
                    time.sleep(.001)
            if key_down_only:
                self._replayed_down.add(virtual_key)
        self._clear()
        if value:
            self.engine.commit_sentence(value)

    def _replay(self, key, down):
        # Keep deferred chord releases ordered even if focus changes after its press.
        flags = (0 if down else 2) | (1 if key in {0xA3, 0xA5, 0x5B, 0x5C,
                                                0x21, 0x22, 0x23, 0x24, 0x25, 0x26,
                                                0x27, 0x28, 0x2D, 0x2E, 0x6F} else 0)
        events = (Input * 1)(Input(1, InputUnion(ki=KeyInput(key, 0, flags, 0, INPUT_TAG))))
        if user32.SendInput(1, events, ctypes.sizeof(Input)) != 1:
            raise RuntimeError("Windows blocked shortcut replay; release modifier keys")
        if down:
            self._replayed_down.add(key)
        else:
            self._replayed_down.discard(key)

    @staticmethod
    def _send(text, virtual_key=None, key_down_only=False):
        events = []
        held_modifiers = [key for key in (0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0x5B, 0x5C)
                          if user32.GetAsyncKeyState(key) & 0x8000]
        for key in held_modifiers:
            events.append(Input(1, InputUnion(ki=KeyInput(key, 0, 2, 0, INPUT_TAG))))
        for character in text.replace("\r\n", "\n").replace("\r", "\n"):
            if character == "\n":
                events.extend((Input(1, InputUnion(ki=KeyInput(0x0D, 0, 0, 0, INPUT_TAG))),
                               Input(1, InputUnion(ki=KeyInput(0x0D, 0, 2, 0, INPUT_TAG)))))
            else:
                raw = character.encode("utf-16-le")
                for offset in range(0, len(raw), 2):
                    unit = int.from_bytes(raw[offset:offset + 2], "little")
                    events.extend((Input(1, InputUnion(ki=KeyInput(0, unit, 4, 0, INPUT_TAG))),
                                   Input(1, InputUnion(ki=KeyInput(0, unit, 6, 0, INPUT_TAG)))))
        if virtual_key is not None:
            events.append(Input(1, InputUnion(ki=KeyInput(virtual_key, 0, 0, 0, INPUT_TAG))))
            if not key_down_only:
                events.append(Input(1, InputUnion(ki=KeyInput(virtual_key, 0, 2, 0, INPUT_TAG))))
        for key in held_modifiers:
            if not key_down_only or key != virtual_key:
                events.append(Input(1, InputUnion(ki=KeyInput(key, 0, 0, 0, INPUT_TAG))))
        if events:
            inputs = (Input * len(events))(*events)
            if user32.SendInput(len(inputs), inputs, ctypes.sizeof(Input)) != len(inputs):
                raise RuntimeError("Windows blocked typing; match the target app's privilege level")
