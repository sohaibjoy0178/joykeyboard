"""The installer and Preferences share one per-user Windows sign-in entry."""
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "JoyKeyboard"


def command_line():
    executable = Path(sys.executable).resolve()
    if getattr(sys, "frozen", False):
        return f'"{executable}"'
    windowed = executable.with_name("pythonw.exe")
    return subprocess.list2cmdline([str(windowed if windowed.exists() else executable),
                                   str(Path(__file__).resolve().with_name("main.py"))])


def is_enabled():
    if sys.platform != "win32":
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, kind = winreg.QueryValueEx(key, VALUE_NAME)
        return kind == winreg.REG_SZ and value.casefold() == command_line().casefold()
    except FileNotFoundError:
        return False


def set_enabled(enabled):
    if sys.platform != "win32":
        raise OSError("Sign-in startup requires Windows.")
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, access=winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command_line())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass
