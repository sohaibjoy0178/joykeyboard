"""Real Windows global chords while a separate owned editor has focus; fixture microphone."""
import ctypes
import json
import os
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes as w
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def probe():
    from PySide6.QtGui import QKeySequence
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    import app
    from core import load_settings
    from windows import Input, InputUnion, KeyInput, MouseInput, foreground_target, user32

    directory = Path(tempfile.mkdtemp(prefix="joy-global-voice-"))
    os.environ["LOCALAPPDATA"] = str(directory / "profile")
    output, command = directory / "editor.json", directory / "command.txt"
    command.write_text("editor", encoding="utf-8")
    child = subprocess.Popen([sys.executable, str(ROOT / "tests/keyboard_native_probe.py"),
                              "--field", str(output), str(command)])
    application = QApplication([])
    application.setQuitOnLastWindowClosed(False)
    class FixtureRecorder:
        level = .1
        error = None
        def __init__(self, device=None):
            pass
        def start(self):
            pass
        def stop(self):
            return b"fixture", 16000
        def cancel(self):
            pass
    app.Recorder = FixtureRecorder
    window = app.JoyWindow()
    window.theme_choice.setCurrentIndex(window.theme_choice.findData("dark"))
    window.auto_pause.setChecked(False)
    window.auto_type.setChecked(True)
    window.recognizer.transcribe = lambda *args, **kwargs: "আমি বাংলায় লিখি"
    calls = []
    toggle = window.toggle_record
    def counted():
        calls.append(True)
        toggle()
    window.toggle_record = counted
    last_info = {}

    def info():
        try:
            last_info.update(json.loads(output.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
        return last_info

    def wait_for(predicate, message, seconds=5):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            application.processEvents()
            if predicate():
                return
            QTest.qWait(10)
            time.sleep(.005)
        raise AssertionError(f"{message}; {window.message.text()}; {info()}")

    def keys(values, down):
        assert foreground_target().pid == info()["pid"], "Owned editor lost focus; stop input"
        events = (Input * len(values))(*(Input(1, InputUnion(ki=KeyInput(key, 0, 0 if down else 2, 0, 0))) for key in values))
        assert user32.SendInput(len(events), events, ctypes.sizeof(Input)) == len(events)

    try:
        window.shortcut_edit.setKeySequence(QKeySequence("Ctrl+Alt+Shift+F9"))
        window.apply_voice_shortcut()
        assert window.voice_hotkey.shortcut == "Ctrl+Alt+Shift+F9", window.shortcut_status.text()
        assert load_settings(window.settings_path)[0]["voice_shortcut"] == "Ctrl+Alt+Shift+F9"
        window.hide()
        window.compact.hide()
        wait_for(lambda: bool(info().get("hwnd")), "Owned editor not ready")
        user32.SetWindowPos.argtypes = [w.HWND, w.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, w.UINT]
        user32.GetWindowRect.argtypes = [w.HWND, ctypes.POINTER(w.RECT)]
        user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
        user32.GetCursorPos.argtypes = [ctypes.POINTER(w.POINT)]
        rectangle, cursor = w.RECT(), w.POINT()
        hwnd = info()["hwnd"]
        user32.GetCursorPos(ctypes.byref(cursor))
        user32.SetWindowPos(hwnd, w.HWND(-1), 0, 0, 0, 0, 0x13)
        user32.GetWindowRect(hwnd, ctypes.byref(rectangle))
        user32.SetCursorPos(rectangle.left + 60, rectangle.top + 80)
        events = (Input * 2)(Input(0, InputUnion(mi=MouseInput(0, 0, 0, 2, 0, 0))),
                             Input(0, InputUnion(mi=MouseInput(0, 0, 0, 4, 0, 0))))
        user32.SendInput(2, events, ctypes.sizeof(Input))
        user32.SetWindowPos(hwnd, w.HWND(-2), 0, 0, 0, 0, 0x13)
        user32.SetCursorPos(cursor.x, cursor.y)
        wait_for(lambda: foreground_target().pid == info()["pid"], "Owned editor not focused")
        window.set_keyboard_enabled(True)
        wait_for(lambda: window.keyboard_hook.enabled, "Keyboard not enabled")
        chord = [0x11, 0x12, 0x10, 0x78]
        keys(chord, True)
        wait_for(lambda: window.recorder is not None, "Global shortcut did not start recording")
        wait_for(lambda: not window.keyboard_hook.enabled, "Voice did not pause keyboard composition")
        keys([0x78], True)
        QTest.qWait(150)
        assert len(calls) == 1 and window.recorder is not None, "Key repeat toggled recording"
        keys(list(reversed(chord)), False)
        QTest.qWait(80)
        keys(chord, True)
        keys(list(reversed(chord)), False)
        wait_for(lambda: window.job is None and len(calls) == 2 and info().get("actual") == "আমি বাংলায় লিখি ",
                 "Global shortcut did not finish/deliver")
        assert not window.isVisible()
        assert foreground_target().pid == info()["pid"]
        wait_for(lambda: window.keyboard_hook.enabled, "Voice did not restore keyboard mode")
        report = dict(passed=True, theme=window.settings["theme"], shortcut="Ctrl+Alt+Shift+F9", saved=True, hidden_bar_start=True,
                      repeat_did_not_toggle=True, global_start_finish=True, editor_focus_preserved=True,
                      keyboard_resumed=True, actual=info()["actual"], microphone="fixture, no live capture", recognizer="fixture stub")
        (ROOT / "artifacts/voice-shortcut-check.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(report))
    finally:
        window.smoke = True
        window.close()
        application.processEvents()
        command.write_text("finish", encoding="utf-8")
        child.wait(timeout=5)


if __name__ == "__main__":
    probe()
