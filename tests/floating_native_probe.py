"""Click only our floating bar; verify a separate owned editor keeps focus and receives text."""
import ctypes
import json
import subprocess
import sys
import time
from ctypes import wintypes as w
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def probe():
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    import app
    from windows import Input, InputUnion, MouseInput, foreground_target, user32

    application = QApplication([])
    application.setStyle("Fusion")
    view = app.JoyWindow(smoke=True)
    view.auto_type.setChecked(True)
    view.system_audio.setChecked(False)
    view.auto_pause.setChecked(False)
    class FixtureRecorder:
        level = 0.1
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
    view.recognizer.transcribe = lambda *args, **kwargs: "আমি বাংলায় লিখি"
    output = ROOT / "artifacts" / "floating-native-editor.json"
    output.write_text("{}", encoding="utf-8")
    child = subprocess.Popen([sys.executable, str(ROOT / "tests" / "native_probe.py"), "--field", str(output)])
    user32.GetCursorPos.argtypes = [ctypes.POINTER(w.POINT)]
    user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    user32.FindWindowW.argtypes = [w.LPCWSTR, w.LPCWSTR]
    user32.FindWindowW.restype = w.HWND
    user32.GetWindowRect.argtypes = [w.HWND, ctypes.POINTER(w.RECT)]
    user32.SetWindowPos.argtypes = [w.HWND, w.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, w.UINT]
    old_cursor = w.POINT()
    user32.GetCursorPos(ctypes.byref(old_cursor))
    def click_at(x, y):
        user32.SetCursorPos(x, y)
        events = (Input * 2)(
            Input(type=0, value=InputUnion(mi=MouseInput(0, 0, 0, 0x0002, 0, 0))),
            Input(type=0, value=InputUnion(mi=MouseInput(0, 0, 0, 0x0004, 0, 0))),
        )
        assert user32.SendInput(2, events, ctypes.sizeof(Input)) == 2
        QTest.qWait(120)
    try:
        deadline = time.monotonic() + 3
        target = None
        while time.monotonic() < deadline:
            application.processEvents()
            try:
                owned_pid = json.loads(output.read_text(encoding="utf-8")).get("pid")
            except (OSError, ValueError):
                owned_pid = None
            target = foreground_target()
            if target and target.pid == owned_pid:
                break
            hwnd = user32.FindWindowW(None, "JoyKeyboard owned Unicode probe")
            pid = w.DWORD()
            if hwnd:
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if hwnd and pid.value == owned_pid:
                rectangle = w.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rectangle))
                user32.SetWindowPos(hwnd, w.HWND(-1), 0, 0, 0, 0, 0x13)
                click_at((rectangle.left + rectangle.right) // 2, (rectangle.top + rectangle.bottom) // 2)
                user32.SetWindowPos(hwnd, w.HWND(-2), 0, 0, 0, 0, 0x13)
            QTest.qWait(20)
        assert target and target.pid == owned_pid, "Owned editor did not receive focus"
        view.last_external = target
        view.show_compact()
        QTest.qWait(80)
        assert foreground_target().hwnd == target.hwnd, "Showing floating bar took focus"
        def click(widget):
            rectangle = w.RECT()
            user32.GetWindowRect(int(view.compact.winId()), ctypes.byref(rectangle))
            point = widget.mapTo(view.compact, widget.rect().center())
            scale = (rectangle.right - rectangle.left) / view.compact.width()
            click_at(rectangle.left + round(point.x() * scale), rectangle.top + round(point.y() * scale))
        click(view.compact.keyboard_btn)
        assert view.keyboard_hook.enabled
        assert foreground_target().hwnd == target.hwnd, "Keyboard click took focus"
        click(view.compact.record)
        assert view.recorder is not None and view.target.hwnd == target.hwnd
        assert foreground_target().hwnd == target.hwnd, "Record click took focus"
        click(view.compact.record)
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and (view.job is not None or not view.transcript.toPlainText()):
            QTest.qWait(30)
        QTest.qWait(350)
        assert view.transcript.toPlainText() == "আমি বাংলায় লিখি"
        assert not view.isVisible()
        child.wait(timeout=5)
        result = json.loads(output.read_text(encoding="utf-8"))
        assert result["actual"] == "আমি বাংলায় লিখি ", result
        report = {"passed": True, "show_preserves_focus": True, "native_keyboard_click_preserves_focus": True,
                  "native_record_click_preserves_focus": True, "voice_result_inserted_into_owned_editor": True,
                  "studio_stayed_hidden": True, "actual": result["actual"],
                  "speech_backend": "fixture stub, no microphone captured", "physical_mouse_tested": False}
        (ROOT / "artifacts" / "floating-native-result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
    finally:
        user32.SetCursorPos(old_cursor.x, old_cursor.y)
        view.close()
        if child.poll() is None:
            child.terminate()


if __name__ == "__main__":
    probe()
