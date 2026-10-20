"""Upgrade only an owned temporary installation; preserve existing user registry/shortcut state."""
import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import winreg
from ctypes import wintypes as w
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def probe():
    from installer_probe import RUN_KEY, UNINSTALL, read_startup
    from package_probe import close_owned_window

    from updates import ReadyUpdate, Release, launch_installer

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL):
            raise RuntimeError("Existing JoyKeyboard installation found; do not overwrite its uninstall record.")
    except FileNotFoundError:
        pass
    old_setup = ROOT / "dist/0.4.9/JoyKeyboard-Setup.exe"
    new_setup = ROOT / "dist/0.4.10/JoyKeyboard-Setup.exe"
    directory = Path(tempfile.mkdtemp(prefix="joy-update-check-"))
    installed = directory / "Joy's App $(literal)"
    executable = installed / "JoyKeyboard.exe"
    profile = directory / "profile"
    data = profile / "JoyKeyboard"
    cache = data / "updates/JoyKeyboard-Setup.exe"
    shortcut = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/JoyKeyboard.lnk"
    old_shortcut = shortcut.read_bytes() if shortcut.exists() else None
    original_startup = read_startup()
    environment = dict(os.environ, LOCALAPPDATA=str(profile), PATH=str(Path(os.environ["SystemRoot"]) / "System32"))
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    results = {}
    process = helper = None
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.IsWindowVisible.argtypes = [w.HWND]

    def visible_bar():
        return any(user.IsWindowVisible(hwnd) for hwnd in close_owned_window(executable, close=False))

    def wait_for(predicate, description, seconds=30):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(.1)
        raise AssertionError(description)

    def read_version():
        return (installed / "_internal/README.md").read_text(encoding="utf-8").splitlines()[0]

    try:
        subprocess.run([str(old_setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-",
                        f"/DIR={installed}", "/TASKS="], check=True, timeout=180)
        assert read_startup() is None and "0.4.9" in read_version()
        data.mkdir(parents=True, exist_ok=True)
        (data / "settings.json").write_text(json.dumps({"theme": "dark", "auto_updates": False,
                                                       "voice_shortcut": "Ctrl+Alt+Shift+F9"}), encoding="utf-8")
        (data / "keyboard-data.json").write_text(json.dumps({"version": 1, "custom_words": ["জয়"]}), encoding="utf-8")
        sentinel = data / "models/keep-this-model.txt"
        sentinel.parent.mkdir(parents=True)
        sentinel.write_text("preserve existing downloaded models", encoding="utf-8")
        cache.parent.mkdir()
        shutil.copy2(new_setup, cache)
        release = Release("0.4.10", "unused local verification fixture", cache.stat().st_size,
                          hashlib.sha256(cache.read_bytes()).hexdigest())
        ready = ReadyUpdate(release, cache)
        process = subprocess.Popen([str(executable)], env=environment, creationflags=subprocess.CREATE_NO_WINDOW)
        wait_for(lambda: bool(close_owned_window(executable, close=False)), "Old app did not start")
        with patch.dict(os.environ, environment, clear=True):
            helper = launch_installer(ready, executable, process.pid, False)
        time.sleep(.6)
        assert process.poll() is None and helper.poll() is None and "0.4.9" in read_version()
        # A changed cache after consent must be rejected by the independent helper.
        with cache.open("r+b") as stream:
            stream.write(b"X")
        assert close_owned_window(executable)
        assert process.wait(timeout=30) == 0
        helper.wait(timeout=150)
        assert (cache.parent / "install-error.txt").is_file()
        assert "SHA-256 changed" in (cache.parent / "install-error.txt").read_text(encoding="utf-8-sig")
        assert "0.4.9" in read_version()
        wait_for(visible_bar, "Failed update did not reopen a visible old bar")
        results["waits_for_parent_and_rejects_changed_cache_then_reopens_old_app"] = True
        assert close_owned_window(executable)
        wait_for(lambda: not close_owned_window(executable, close=False), "Old app did not close")
        time.sleep(.5)
        shutil.copy2(new_setup, cache)
        process = subprocess.Popen([str(executable)], env=environment, creationflags=subprocess.CREATE_NO_WINDOW)
        wait_for(lambda: bool(close_owned_window(executable, close=False)), "Old app did not restart")
        with patch.dict(os.environ, environment, clear=True):
            helper = launch_installer(ready, executable, process.pid, False)
        time.sleep(.6)
        assert "0.4.9" in read_version() and process.poll() is None
        assert close_owned_window(executable)
        assert process.wait(timeout=30) == 0
        assert helper.wait(timeout=150) == 0
        wait_for(visible_bar, "Updated app did not reopen a visible bar")
        assert "0.4.10" in read_version() and not (cache.parent / "install-error.txt").exists()
        assert read_startup() is None
        settings = json.loads((data / "settings.json").read_text(encoding="utf-8"))
        assert settings["theme"] == "dark" and settings["voice_shortcut"] == "Ctrl+Alt+Shift+F9"
        assert settings["auto_updates"] is False and sentinel.read_text() == "preserve existing downloaded models"
        assert "জয়" in json.loads((data / "keyboard-data.json").read_text(encoding="utf-8"))["custom_words"]
        results["silent_upgrade_restarts_app_and_preserves_settings_words_models_startup_off"] = True
        assert close_owned_window(executable)
        wait_for(lambda: not close_owned_window(executable, close=False), "Updated app did not close")
        time.sleep(.5)
    finally:
        if process is not None and process.poll() is None:
            close_owned_window(executable)
            process.wait(timeout=30)
        if helper is not None and helper.poll() is None:
            helper.wait(timeout=150)
        close_owned_window(executable)
        uninstall = installed / "unins000.exe"
        if uninstall.exists():
            subprocess.run([str(uninstall), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], timeout=90, check=False)
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, access=winreg.KEY_SET_VALUE) as key:
            if original_startup is None:
                try:
                    winreg.DeleteValue(key, "JoyKeyboard")
                except FileNotFoundError:
                    pass
            else:
                winreg.SetValueEx(key, "JoyKeyboard", 0, original_startup[1], original_startup[0])
        if old_shortcut is not None:
            shortcut.write_bytes(old_shortcut)
        assert read_startup() == original_startup
    report = {"passed": True, "test_directory": str(directory), "original_startup_restored": True, "checks": results}
    (ROOT / "artifacts/updater-install-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    probe()
