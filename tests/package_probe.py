"""Run the delivered single file from a fresh folder without Python on PATH."""
import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def close_owned_window(executable: Path, close=True):
    from ctypes import wintypes as w
    user = ctypes.WinDLL("user32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
    user.EnumWindows.argtypes = [callback_type, w.LPARAM]
    user.GetWindowTextW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
    user.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
    user.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
    kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    kernel.OpenProcess.restype = w.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD)]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    found = []

    @callback_type
    def visit(hwnd, _):
        title = ctypes.create_unicode_buffer(256)
        user.GetWindowTextW(hwnd, title, len(title))
        if title.value != "JoyKeyboard · Floating bar":
            return True
        pid = w.DWORD()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process = kernel.OpenProcess(0x1000, False, pid.value)
        if process:
            try:
                path = ctypes.create_unicode_buffer(32768)
                length = w.DWORD(len(path))
                if kernel.QueryFullProcessImageNameW(process, 0, path, ctypes.byref(length)):
                    if Path(path.value).resolve() == executable.resolve():
                        found.append(int(hwnd))
            finally:
                kernel.CloseHandle(process)
        return True

    user.EnumWindows(visit, 0)
    if not close:
        return found
    for hwnd in found:
        user.PostMessageW(hwnd, 0x0010, 0, 0)
    return bool(found)


def probe():
    source = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "dist" / "JoyKeyboard.exe"
    directory = Path(tempfile.mkdtemp(prefix="JoyKeyboard-standalone-"))
    executable = directory / source.name
    shutil.copy2(source, executable)
    if (source.parent / "_internal").is_dir():
        shutil.copytree(source.parent / "_internal", directory / "_internal")
    environment = {key: value for key, value in os.environ.items()
                   if key.upper() not in ("PYTHONPATH", "PYTHONHOME", "LOCALAPPDATA", "PATH")}
    environment["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
    environment["LOCALAPPDATA"] = str(directory / "user-data")
    environment["HF_HUB_OFFLINE"] = "1"
    environment["TRANSFORMERS_OFFLINE"] = "1"
    checks = []

    def run(name, arguments):
        started = time.monotonic()
        result = subprocess.run([str(executable), *arguments], cwd=directory, env=environment,
                                timeout=120, creationflags=subprocess.CREATE_NO_WINDOW,
                                capture_output=True)
        checks.append({"name": name, "returncode": result.returncode,
                       "seconds": round(time.monotonic() - started, 2),
                       "stdout": result.stdout.decode("utf-8", errors="replace"),
                       "stderr": result.stderr.decode("utf-8", errors="replace")})
        assert result.returncode == 0, checks[-1]

    ui = ROOT / "artifacts" / "standalone-ui.png"
    run("standalone-ui", ["--smoke-test", str(ui)])
    assert ui.is_file() and ui.stat().st_size > 5000
    profile = directory / "user-data/JoyKeyboard/settings.json"
    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_text('{"theme":"dark"}', encoding="utf-8")
    dark_ui = ROOT / "artifacts/standalone-dark-ui.png"
    run("standalone-saved-dark-theme", ["--smoke-test", str(dark_ui)])
    from PySide6.QtGui import QImage
    for path, dark in ((ui, False), (dark_ui, True)):
        frame = QImage(str(path))
        center = frame.pixelColor(round(frame.width() * .018), frame.height() // 2)
        assert 100 < center.alpha() < 230
        assert (max(center.red(), center.green(), center.blue()) < 60) if dark else (min(center.red(), center.green(), center.blue()) > 200)
    assert not (directory / "user-data" / "JoyKeyboard" / "models").exists()
    bengali = ROOT / "artifacts" / "standalone-online-bengali.json"
    run("online-bengali", ["--check-audio", str(ROOT / "artifacts" / "bn-10025278611427771211.pcm.wav"),
                           "--check-output", str(bengali), "--check-engine", "google",
                           "--check-language", "bn-BD"])
    online = json.loads(bengali.read_text(encoding="utf-8"))
    assert online["packaged"] and "কিবোর্ড" in online["transcript"]
    pause = ROOT / "artifacts" / "standalone-auto-pause.json"
    run("auto-pause-bengali", ["--check-audio", str(ROOT / "artifacts" / "bn-10025278611427771211.pcm.wav"),
                               "--check-output", str(pause), "--check-engine", "google",
                               "--check-language", "bn-BD", "--check-auto-pause"])
    paused = json.loads(pause.read_text(encoding="utf-8"))
    assert paused["packaged"] and paused["auto_pause_detected"] and "কিবোর্ড" in paused["transcript"]
    assert paused["early_recognition_started"]
    assert not (directory / "user-data" / "JoyKeyboard" / "models").exists()
    sys.path.insert(0, str(ROOT))
    from voice import SHERPA_MODEL, Recognizer
    # Exercise the same explicit download path as Preferences, then use it in the EXE.
    cache = directory / "user-data/JoyKeyboard/models"
    client = Recognizer(cache, bundled_dir=directory / "no-bundle")
    client.prepare_model("tiny")
    assert client.model_ready("tiny")
    english = ROOT / "artifacts" / "standalone-offline-english.json"
    run("offline-downloaded-tiny", ["--check-audio", str(Path(tempfile.gettempdir()) / "joykeyboard-jfk.wav"),
                                   "--check-output", str(english), "--check-model", "tiny"])
    offline = json.loads(english.read_text(encoding="utf-8"))
    assert offline["packaged"] and "country" in offline["transcript"].lower()
    client.prepare_model(SHERPA_MODEL)
    sherpa = ROOT / "artifacts/standalone-sherpa-bengali.json"
    run("offline-streaming-sherpa-bengali", ["--check-audio", str(ROOT / "artifacts/bn-10025278611427771211.pcm.wav"),
                                            "--check-output", str(sherpa), "--check-engine", "sherpa",
                                            "--check-language", "bn-BD"])
    live = json.loads(sherpa.read_text(encoding="utf-8"))
    assert live["packaged"] and "আশ্চর্য" in live["transcript"] and "যখন" in live["transcript"]
    normal = subprocess.Popen([str(executable)], cwd=directory, env=environment,
                              creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and normal.poll() is None:
            if close_owned_window(executable):
                break
            time.sleep(0.2)
        assert normal.wait(timeout=20) == 0
        assert (directory / "user-data" / "JoyKeyboard" / "keyboard-data.json").is_file()
        checks.append({"name": "normal-hook-startup-and-graceful-close", "returncode": 0})
    finally:
        if normal.poll() is None:
            normal.terminate()
    report = {"executable": str(executable), "bytes": executable.stat().st_size,
              "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
              "limited_path": environment["PATH"], "initial_user_cache_empty": True,
              "online_and_auto_pause_without_model_download": True,
              "offline_model_downloaded_explicitly": "tiny", "checks": checks, "passed": True}
    (ROOT / "artifacts" / "standalone-check.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    probe()
