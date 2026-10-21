"""Send actual Windows input through the live hook into a separate owned editor."""
import ctypes
import json
import os
import subprocess
import sys
import tempfile
import time
import unicodedata
from ctypes import wintypes as w
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def probe(executable=None):
    from package_probe import close_owned_window

    from keyboard_engine import KeyboardEngine
    from keyboard_hook import KeyboardHook
    from windows import Input, InputUnion, KeyInput, MouseInput, foreground_target, user32

    directory = Path(tempfile.mkdtemp(prefix="joykeyboard-event-check-"))
    output, command = directory / "editor.json", directory / "command.txt"
    command.write_text("editor", encoding="utf-8")
    environment = dict(os.environ, PYTHONUTF8="1")
    child = subprocess.Popen([sys.executable, str(ROOT / "tests/keyboard_native_probe.py"),
                              "--field", str(output), str(command)], env=environment)
    errors = []
    class Engine(KeyboardEngine):
        first = True
        def suggest(self, prefix, limit=8):
            if "--slow-suggestions" in sys.argv and self.first:
                self.first = False
                time.sleep(1.4)
            return super().suggest(prefix, limit)
    hook = None if executable else KeyboardHook(Engine(directory / "words.json"), lambda *args: None, errors.append)
    app_process = None

    def info():
        try:
            return json.loads(output.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def wait_for(predicate, description, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(.02)
        raise AssertionError(f"{description}: field={info()}, raw={getattr(hook, 'raw', '')!r}, errors={errors}")

    def send(phrase, delay=.025):
        for character in phrase:
            target = foreground_target()
            assert target and target.pid == owned_pid, "Owned test editor lost focus; input stopped"
            key = 0x20 if character == " " else ord(character.upper())
            events = (Input * 2)(Input(1, InputUnion(ki=KeyInput(key, 0, 0, 0, 0))),
                                 Input(1, InputUnion(ki=KeyInput(key, 0, 2, 0, 0))))
            assert user32.SendInput(2, events, ctypes.sizeof(Input)) == 2
            time.sleep(delay)

    try:
        wait_for(lambda: bool(info().get("pid")), "Owned editor did not start")
        owned_pid = info()["pid"]
        user32.GetWindowRect.argtypes = [w.HWND, ctypes.POINTER(w.RECT)]
        user32.SetWindowPos.argtypes = [w.HWND, w.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, w.UINT]
        user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
        user32.GetCursorPos.argtypes = [ctypes.POINTER(w.POINT)]
        old_cursor = w.POINT()
        user32.GetCursorPos(ctypes.byref(old_cursor))
        hwnd = info()["hwnd"]
        user32.SetWindowPos(hwnd, w.HWND(-1), 0, 0, 0, 0, 0x13)
        rectangle = w.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rectangle))
        user32.SetCursorPos(rectangle.left + 60, rectangle.top + 80)
        clicks = (Input * 2)(Input(0, InputUnion(mi=MouseInput(0, 0, 0, 2, 0, 0))),
                              Input(0, InputUnion(mi=MouseInput(0, 0, 0, 4, 0, 0))))
        user32.SendInput(2, clicks, ctypes.sizeof(Input))
        wait_for(lambda: foreground_target() and foreground_target().pid == owned_pid,
                 "Owned editor did not receive click focus")
        user32.SetWindowPos(hwnd, w.HWND(-2), 0, 0, 0, 0, 0x13)
        user32.SetCursorPos(old_cursor.x, old_cursor.y)
        wait_for(lambda: foreground_target() and foreground_target().pid == owned_pid,
                 "Owned editor did not receive focus")
        if executable:
            profile = directory / "profile/JoyKeyboard"
            profile.mkdir(parents=True)
            settings = {"bar_position": [300, 20], "theme": "dark"}
            if "--voice-shortcut" in sys.argv:
                settings.update(voice_shortcut="Ctrl+Alt+Shift+F9", engine="sherpa")
            (profile / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
            app_env = dict(environment, LOCALAPPDATA=str(directory / "profile"),
                           PATH=str(Path(os.environ["SystemRoot"]) / "System32"))
            app_env.pop("PYTHONPATH", None)
            app_env.pop("PYTHONHOME", None)
            app_process = subprocess.Popen([str(executable)], env=app_env, creationflags=subprocess.CREATE_NO_WINDOW)
            user32.IsWindowVisible.argtypes = [w.HWND]
            def bar_ready():
                bars = close_owned_window(executable, close=False)
                return bool(bars and user32.IsWindowVisible(bars[0]))
            # Native glass creates its handle before registration; wait for completed startup/show.
            wait_for(bar_ready, "Packaged bar did not appear", timeout=30)
            bar = close_owned_window(executable, close=False)[0]
            user32.GetWindowRect(bar, ctypes.byref(rectangle))
            scale = (rectangle.right - rectangle.left) / 384
            if "--voice-shortcut" in sys.argv:
                user32.SetCursorPos(rectangle.left + round(364 * scale), rectangle.top + round(24 * scale))
                assert user32.SendInput(2, clicks, ctypes.sizeof(Input)) == 2
                wait_for(lambda: not user32.IsWindowVisible(bar), "Bar did not hide to tray")
                assert foreground_target().pid == owned_pid
                chord = [0x11, 0x12, 0x10, 0x78]
                events = [Input(1, InputUnion(ki=KeyInput(key, 0, 0, 0, 0))) for key in chord]
                events += [Input(1, InputUnion(ki=KeyInput(key, 0, 2, 0, 0))) for key in reversed(chord)]
                batch = (Input * len(events))(*events)
                assert user32.SendInput(len(events), batch, ctypes.sizeof(Input)) == len(events)
                # Missing Sherpa model intentionally prevents microphone capture; shortcut reveals its error.
                wait_for(lambda: bool(user32.IsWindowVisible(bar)), "Saved global shortcut did not reach packaged app")
                assert foreground_target().pid == owned_pid
                def feedback_visible():
                    user32.GetWindowRect(bar, ctypes.byref(rectangle))
                    return (rectangle.bottom - rectangle.top) / scale > 48
                wait_for(feedback_visible, "No missing-model feedback")
            # The fixed compact layout puts the keyboard icon at (192, 24) logical pixels.
            user32.SetCursorPos(rectangle.left + round(192 * scale), rectangle.top + round(24 * scale))
            assert user32.SendInput(2, clicks, ctypes.sizeof(Input)) == 2
            user32.SetCursorPos(old_cursor.x, old_cursor.y)
            time.sleep(.3)
        else:
            hook.start()
            hook.set_enabled(True)
            wait_for(lambda: hook.enabled, "Keyboard did not enable")
        started = time.monotonic()
        send("ami banglay likhi ")
        wait_for(lambda: info().get("actual") == unicodedata.normalize("NFC", "আমি বাংলায় লিখি "), "Bangla input failed")
        send("ami bangla ", delay=.003)
        expected = unicodedata.normalize("NFC", "আমি বাংলায় লিখি আমি বাংলা ")
        wait_for(lambda: info().get("actual") == expected, "Fast multiword input failed")
        send("ami\b\bmi ")
        expected += "আমি "
        wait_for(lambda: info().get("actual") == expected, "Backspace composition failed")
        command.write_text("password", encoding="utf-8")
        wait_for(lambda: foreground_target() and foreground_target().focus == info().get("password"), "Owned password field lost focus")
        send("ami ")
        wait_for(lambda: info().get("password_text") == "ami ", "Password must stay unconverted")
        assert not errors, errors
        report = dict(passed=True, actual=info()["actual"], real_windows_hook=True,
                      input="Windows SendInput virtual-key events, no direct composition calls",
                      physical_hardware_tested=False, packaged=bool(executable),
                      packaged_saved_theme="dark" if executable else None,
                      packaged_saved_voice_shortcut="--voice-shortcut" in sys.argv,
                      fast_multiword_input=True, backspace_composition=True, native_password_passthrough=True,
                      slow_suggestions="--slow-suggestions" in sys.argv,
                      seconds=round(time.monotonic() - started, 3))
        result_name = "packaged-keyboard-event-check.json" if executable else "keyboard-event-check.json"
        (ROOT / "artifacts" / result_name).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report))
    finally:
        if hook:
            hook.stop()
        if app_process:
            close_owned_window(executable)
            app_process.wait(timeout=15)
        command.write_text("finish", encoding="utf-8")
        child.wait(timeout=5)


if __name__ == "__main__":
    probe(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else None)
