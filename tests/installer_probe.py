"""Install/uninstall the real setup in a temporary folder; restore owned registry/shortcut state."""
import configparser
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import winreg
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
UNINSTALL = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{51281235-DF17-48AE-AE18-445279EB0C4E}_is1"


def read_startup():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            return winreg.QueryValueEx(key, "JoyKeyboard")
    except FileNotFoundError:
        return None


def probe():
    from package_probe import close_owned_window

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL):
            raise RuntimeError("Existing JoyKeyboard installation found; do not overwrite its uninstall record.")
    except FileNotFoundError:
        pass
    setup = ROOT / "dist" / "0.4.1" / "JoyKeyboard-Setup.exe"
    directory = Path(tempfile.mkdtemp(prefix="joykeyboard-install-check-"))
    installed = directory / "App With Spaces"
    shortcut = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/JoyKeyboard.lnk"
    old_shortcut = shortcut.read_bytes() if shortcut.exists() else None
    original_startup = read_startup()
    environment = dict(os.environ)
    environment["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["LOCALAPPDATA"] = str(directory / "profile")
    common = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-", f"/DIR={installed}"]
    results = {}
    try:
        # No /TASKS override: verify sign-in startup is selected by default.
        subprocess.run([str(setup), *common, f"/SAVEINF={directory / 'default.inf'}",
                        f"/LOG={directory / 'install.log'}"], check=True, timeout=180)
        executable = installed / "JoyKeyboard.exe"
        uninstall = installed / "unins000.exe"
        assert executable.is_file() and (installed / "_internal/assets/models/base/model.bin").is_file()
        expected = (f'"{executable}"', winreg.REG_SZ)
        assert read_startup() == expected, read_startup()
        defaults = configparser.ConfigParser()
        defaults.read(directory / "default.inf", encoding="utf-8-sig")
        assert "autostart" in defaults["Setup"]["Tasks"]
        results["default_startup_checked_and_quoted_command"] = True
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL) as metadata:
            assert winreg.QueryValueEx(metadata, "Publisher")[0] == "Sohaib Islam Joy"
            assert winreg.QueryValueEx(metadata, "URLInfoAbout")[0] == "https://www.facebook.com/sohaib.islam1997"
        results["developer_credit_and_facebook_publisher_link"] = True
        # Run the installed app with no Python on PATH and fresh application data.
        subprocess.run([str(executable), "--smoke-test", str(ROOT / "artifacts/installed-bar.png")],
                       check=True, env=environment, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
        process = subprocess.Popen([str(executable)], env=environment, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            time.sleep(3)
            assert process.poll() is None
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.OpenProcess.restype = ctypes.c_void_p
            handle = kernel.OpenProcess(0x1000, False, process.pid)
            def cpu_time():
                values = [ctypes.c_ulonglong() for _ in range(4)]
                kernel.GetProcessTimes.argtypes = [ctypes.c_void_p] + [ctypes.c_void_p] * 4
                assert kernel.GetProcessTimes(handle, *(ctypes.byref(v) for v in values))
                return (values[2].value + values[3].value) / 10_000_000
            begin, wall = cpu_time(), time.perf_counter()
            time.sleep(10)
            cpu, seconds = cpu_time() - begin, time.perf_counter() - wall
            class Memory(ctypes.Structure):
                _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong),
                            *[(n, ctypes.c_size_t) for n in ("peak_ws", "ws", "peak_paged", "paged", "peak_nonpaged", "nonpaged", "pagefile", "peak_pagefile", "private")]]
            memory = Memory()
            memory.cb = ctypes.sizeof(memory)
            ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong)
            assert ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(memory), memory.cb)
            kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            kernel.CloseHandle(handle)
            results["installed_idle"] = dict(seconds=round(seconds, 2), one_core_percent=round(cpu / seconds * 100, 3),
                                             working_set_mib=round(memory.ws / 2**20, 2), private_mib=round(memory.private / 2**20, 2))
            assert close_owned_window(executable)
            assert process.wait(timeout=30) == 0
            results["installed_normal_startup_and_graceful_quit"] = True
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(10)
        # Upgrade with startup unchecked removes the previous Run value.
        subprocess.run([str(setup), *common, "/TASKS=", f"/LOG={directory / 'disable-startup.log'}"], check=True, timeout=180)
        assert read_startup() is None
        results["unchecked_startup_removes_existing_entry"] = True
        # Re-enable as Preferences does. Uninstall must remove it even if the last installer task was off.
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, access=winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "JoyKeyboard", 0, winreg.REG_SZ, expected[0])
        data_file = directory / "profile/JoyKeyboard/settings.json"
        data_file.parent.mkdir(parents=True, exist_ok=True)
        data_file.write_text('{"bar_opacity":80}', encoding="utf-8")
        subprocess.run([str(uninstall), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], check=True, timeout=90)
        assert read_startup() is None and not executable.exists() and data_file.is_file()
        results["uninstall_removes_startup_preserves_user_data"] = True
    finally:
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
    report = {"setup": str(setup), "bytes": setup.stat().st_size,
              "sha256": hashlib.sha256(setup.read_bytes()).hexdigest(), "test_directory": str(directory),
              "original_startup_restored": True, "passed": True, "checks": results}
    (ROOT / "artifacts/installer-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    probe()
