"""Owned-editor integration probe. Synthetic events cannot prove physical hardware.

Installs the actual hook and checks ignored own-tagged output, then exercises its
physical-event decision entry point against a separate owned native editor.
"""
import ctypes
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes as w
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TITLE = "JoyKeyboard owned keyboard composition probe"


def field(output: Path, command: Path):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QWidget

    from windows import user32

    user32.CreateWindowExW.argtypes = [w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD,
                                     ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                     w.HWND, w.HMENU, w.HINSTANCE, ctypes.c_void_p]
    user32.CreateWindowExW.restype = w.HWND
    user32.SetFocus.argtypes = [w.HWND]
    application = QApplication([])
    owner = QWidget()
    owner.setWindowTitle(TITLE)
    owner.resize(600, 240)
    owner.show()
    parent = int(owner.winId())
    editor = user32.CreateWindowExW(0x200, "EDIT", "", 0x50010004,
                                  12, 12, 575, 150, parent, None, None, None)
    password = user32.CreateWindowExW(0x200, "EDIT", "", 0x50010020,
                                    12, 180, 575, 30, parent, None, None, None)
    assert editor and password
    owner.activateWindow()
    user32.SetForegroundWindow(parent)
    user32.SetFocus(editor)
    QTimer.singleShot(200, lambda: user32.SetFocus(editor))

    def snapshot(done=False):
        def value(hwnd):
            text = ctypes.create_unicode_buffer(4096)
            user32.GetWindowTextW(hwnd, text, len(text))
            return text.value

        payload = {"pid": os.getpid(), "hwnd": parent, "editor": int(editor),
                   "password": int(password), "actual": value(editor),
                   "password_text": value(password), "done": done}
        temporary = output.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        try:
            temporary.replace(output)
        except PermissionError:
            # The reader can briefly hold Windows' non-delete-sharing file handle.
            pass

    seen = ""

    def poll():
        nonlocal seen
        request = command.read_text(encoding="utf-8") if command.exists() else ""
        if request != seen:
            seen = request
            if request == "password":
                user32.SetFocus(password)
            elif request == "editor":
                user32.SetFocus(editor)
            elif request == "finish":
                snapshot(True)
                application.quit()
                return
        snapshot()

    timer = QTimer()
    timer.timeout.connect(poll)
    timer.start(40)
    QTimer.singleShot(20000, application.quit)
    snapshot()
    return application.exec()


def probe():
    from keyboard_engine import KeyboardEngine, to_ansi
    from keyboard_hook import KeyboardHook, _native_password
    from windows import foreground_target, user32

    output = ROOT / "artifacts/keyboard-native-field.json"
    command = ROOT / "artifacts/keyboard-native-command.txt"
    result_path = ROOT / "artifacts/keyboard-native-result.json"
    output.parent.mkdir(exist_ok=True)
    command.write_text("editor", encoding="utf-8")
    child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--field", str(output), str(command)])
    errors, updates = [], []
    hook = KeyboardHook(KeyboardEngine(ROOT / "artifacts/keyboard-probe-data.json"),
                        lambda *args: updates.append(args), errors.append)

    def wait_for(predicate, description, timeout=4):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.025)
        raise AssertionError(f"{description}; foreground={foreground_target()}; field={info()}")

    def info():
        try:
            return json.loads(output.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def owned_focus(control):
        target = foreground_target()
        state = info()
        return bool(target and target.pid == state.get("pid") and target.focus == state.get(control))

    def physical_word(value, delimiter=True):
        # Win32 labels all SendInput events injected. Feed hardware decisions explicitly;
        # all committed output still traverses the real installed hook and native Edit.
        for char in value:
            key = ord(char.upper())
            assert hook._capture(key, True)
            assert hook._capture(key, False)
        if delimiter:
            assert hook._capture(0x20, True)
            assert hook._capture(0x20, False)

    try:
        wait_for(lambda: bool(info().get("hwnd")), "Owned editor did not start")
        from windows import Input, InputUnion, MouseInput
        user32.GetWindowRect.argtypes = [w.HWND, ctypes.POINTER(w.RECT)]
        user32.SetWindowPos.argtypes = [w.HWND, w.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, w.UINT]
        user32.GetCursorPos.argtypes = [ctypes.POINTER(w.POINT)]
        user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
        rectangle, old_cursor = w.RECT(), w.POINT()
        user32.GetCursorPos(ctypes.byref(old_cursor))
        hwnd = info()["hwnd"]
        user32.SetWindowPos(hwnd, w.HWND(-1), 0, 0, 0, 0, 0x13)
        user32.GetWindowRect(hwnd, ctypes.byref(rectangle))
        user32.SetCursorPos(rectangle.left + 60, rectangle.top + 80)
        clicks = (Input * 2)(Input(0, InputUnion(mi=MouseInput(0, 0, 0, 2, 0, 0))),
                              Input(0, InputUnion(mi=MouseInput(0, 0, 0, 4, 0, 0))))
        user32.SendInput(2, clicks, ctypes.sizeof(Input))
        user32.SetWindowPos(hwnd, w.HWND(-2), 0, 0, 0, 0, 0x13)
        user32.SetCursorPos(old_cursor.x, old_cursor.y)
        wait_for(lambda: owned_focus("editor"), "Owned editor failed to receive focus")
        hook.start()
        hook.set_enabled(True)
        wait_for(lambda: hook.enabled, "Keyboard did not enable")
        hook._send("x")
        wait_for(lambda: info().get("actual") == "x", "Injected event did not pass through")
        assert not hook.raw
        physical_word("ami")
        wait_for(lambda: info().get("actual") == "xআমি ", "Actual Bengali composition did not reach native Edit")
        hook.set_layout("english")
        wait_for(lambda: hook.layout == "english", "Layout command not processed")
        hook.engine.snippets["addr"] = "Dhaka"
        physical_word("addr")
        wait_for(lambda: info().get("actual") == "xআমি Dhaka ", "Snippet commit failed")
        expected = "xআমি Dhaka "
        physical_word("hello")
        expected += "hello "
        wait_for(lambda: info().get("actual") == expected, "English commit failed")
        hook.set_layout("probhat")
        wait_for(lambda: hook.layout == "probhat", "Fixed layout command not processed")
        physical_word("ami")
        expected += hook.engine.convert("ami", "probhat") + " "
        wait_for(lambda: info().get("actual") == expected, "Fixed layout commit failed")
        hook.set_layout("phonetic")
        wait_for(lambda: hook.layout == "phonetic", "Phonetic layout command not processed")
        physical_word("bangla", False)
        wait_for(lambda: bool(hook.suggestions), "No candidates produced")
        candidate = hook.suggestions[0]
        assert hook._capture(0x70, True)
        assert hook._capture(0x70, False)
        expected += candidate
        wait_for(lambda: info().get("actual") == expected, "Candidate selection failed")
        physical_word("ami", False)
        for key, down in ((0xA2, True), (0x23, True), (0xA2, False), (0x23, False)):
            assert hook._capture(key, down)
        expected += "আমি"
        wait_for(lambda: info().get("actual") == expected, "Modifier commit failed")
        wait_for(lambda: not hook._replayed_down, "Deferred shortcut left keys held")
        wait_for(lambda: not user32.GetAsyncKeyState(0xA2) & 0x8000, "Windows did not apply the deferred Ctrl release")
        for enabled in (False, True):
            assert hook._capture(0x7B, True)
            assert hook._capture(0x7B, False)
            wait_for(lambda: hook.enabled == enabled, "F12 mode toggle failed")
        hook.set_output_encoding("bijoy")
        wait_for(lambda: hook.output_encoding == "bijoy", "Bijoy output command failed")
        physical_word("ami")
        expected += to_ansi("আমি") + " "
        wait_for(lambda: info().get("actual") == expected, "Bijoy output commit failed")
        command.write_text("password", encoding="utf-8")
        wait_for(lambda: owned_focus("password"), "Owned password control failed to receive focus")
        assert _native_password(foreground_target())
        assert not hook._capture(ord("S"), True)
        assert not hook._capture(ord("S"), False)
        assert not hook.raw
        hook._send("s")
        wait_for(lambda: info().get("password_text") == "s", "Password pass-through failed")
        assert not errors, errors
        command.write_text("finish", encoding="utf-8")
        child.wait(timeout=5)
        result = info()
        result.update(passed=True, hook_started=True, own_injected_output_ignored=True,
                      bengali_native_commit=True, native_password_guard=True,
                      english_commit=True, fixed_layout_commit=True, candidate_commit=True,
                      modifier_replay_balanced=True, f12_toggle=True, bijoy_output_commit=True,
                      physical_hardware_tested=False, errors=errors)
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result))
    finally:
        hook.stop()
        if child.poll() is None:
            child.terminate()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--field":
        raise SystemExit(field(Path(sys.argv[2]), Path(sys.argv[3])))
    probe()
