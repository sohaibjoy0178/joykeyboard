import ctypes
from ctypes import wintypes as w

import pytest
from PySide6.QtCore import QByteArray
from PySide6.QtWidgets import QApplication, QWidget

import hotkeys
from core import DEFAULT_VOICE_SHORTCUT, load_settings, parse_voice_shortcut


@pytest.mark.parametrize("value,expected", [("ctrl+alt+v", ("Ctrl+Alt+V", 3, 0x56)),
    ("Shift+Alt+F9", ("Alt+Shift+F9", 5, 0x78)), ("F9", ("F9", 0, 0x78)),
    (DEFAULT_VOICE_SHORTCUT, (DEFAULT_VOICE_SHORTCUT, 3, 0x20))])
def test_parse_shortcut(value, expected):
    assert parse_voice_shortcut(value) == expected


@pytest.mark.parametrize("value", [None, "", "V", "Space", "Shift+V", "Ctrl", "Ctrl+F12", "F8", "Win+H", "Ctrl+Ctrl+V", "Ctrl+V, Ctrl+B"])
def test_reject_ordinary_typing_reserved_and_multichord_shortcuts(value):
    with pytest.raises(ValueError):
        parse_voice_shortcut(value)


def test_shortcut_settings_migrate_and_ignore_invalid_values(tmp_path):
    import json
    path = tmp_path / "settings.json"
    for value, expected in (({}, DEFAULT_VOICE_SHORTCUT), ({"voice_shortcut": "ctrl+alt+v"}, "Ctrl+Alt+V"),
                            ({"voice_shortcut": "V"}, DEFAULT_VOICE_SHORTCUT)):
        path.write_text(json.dumps(value), encoding="utf-8")
        assert load_settings(path)[0]["voice_shortcut"] == expected


def test_registration_conflict_retains_old_chord_and_filters_native_messages(monkeypatch):
    application = QApplication.instance() or QApplication([])
    registrations, releases, callbacks = [], [], []
    def register(hwnd, identity, flags, key):
        registrations.append((identity, flags, key))
        return key != ord("X")
    monkeypatch.setattr(hotkeys.user32, "RegisterHotKey", register)
    monkeypatch.setattr(hotkeys.user32, "UnregisterHotKey", lambda hwnd, identity: releases.append(identity))
    manager = hotkeys.VoiceHotkey(123, lambda: callbacks.append(True))
    try:
        manager.register("Ctrl+Alt+V")
        identity = manager.identity
        assert registrations[-1][1] & 0x4000
        with pytest.raises(OSError):
            manager.register("Ctrl+Alt+X")
        assert manager.identity == identity and manager.shortcut == "Ctrl+Alt+V" and not releases
        manager.register("Ctrl+Alt+B")
        assert releases == [identity]
        event = w.MSG()
        event.hWnd, event.message, event.wParam = 123, 0x0312, manager.identity
        assert manager.nativeEventFilter(QByteArray(b"windows_generic_MSG"), ctypes.addressof(event)) == (True, 0)
        assert callbacks == [True]
        event.wParam = identity
        assert manager.nativeEventFilter(QByteArray(b"windows_generic_MSG"), ctypes.addressof(event)) == (False, 0)
    finally:
        manager.close()
    assert len(releases) == 2
    assert application is not None


def test_real_windows_registration_conflict_and_release():
    application = QApplication.instance() or QApplication([])
    first, second = QWidget(), QWidget()
    a = hotkeys.VoiceHotkey(int(first.winId()), lambda: None)
    b = hotkeys.VoiceHotkey(int(second.winId()), lambda: None)
    try:
        a.register("Ctrl+Alt+Shift+F10")
        b.register("Ctrl+Alt+Shift+F11")
        with pytest.raises(OSError):
            b.register("Ctrl+Alt+Shift+F10")
        assert b.shortcut == "Ctrl+Alt+Shift+F11"
        a.close()
        b.register("Ctrl+Alt+Shift+F10")
    finally:
        a.close()
        b.close()
        first.close()
        second.close()
    assert application is not None
