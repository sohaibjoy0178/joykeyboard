"""Exercise startup operations in a disposable key, never the real Run key."""
import sys
import uuid

import pytest

import startup


@pytest.mark.skipif(sys.platform != "win32", reason="Windows registry integration")
def test_startup_roundtrip_and_quoted_installed_path(monkeypatch):
    import winreg
    key = rf"Software\JoyKeyboard-Tests\{uuid.uuid4()}"
    monkeypatch.setattr(startup, "RUN_KEY", key)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Program Files\JoyKeyboard\JoyKeyboard.exe")
    try:
        assert not startup.is_enabled()
        startup.set_enabled(True)
        assert startup.is_enabled()
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as registry:
            value, kind = winreg.QueryValueEx(registry, "JoyKeyboard")
        assert value == '"C:\\Program Files\\JoyKeyboard\\JoyKeyboard.exe"'
        assert kind == winreg.REG_SZ
        startup.set_enabled(False)
        startup.set_enabled(False)
        assert not startup.is_enabled()
    finally:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
