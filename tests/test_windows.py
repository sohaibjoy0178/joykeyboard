import ctypes

import pytest

import windows
from windows import Target, insert_text

pytestmark = pytest.mark.skipif(not windows.IS_WINDOWS, reason="Windows input integration")


def test_changed_external_window_blocks_input(monkeypatch):
    monkeypatch.setattr(windows.user32, "IsWindow", lambda _: True)
    monkeypatch.setattr(windows, "foreground_target", lambda: Target(2, 99, 0, "other"))
    with pytest.raises(RuntimeError, match="Focus changed"):
        insert_text(Target(1, 88, 0, "original"), "secret")


def test_changed_child_control_blocks_input(monkeypatch):
    monkeypatch.setattr(windows.user32, "IsWindow", lambda _: True)
    monkeypatch.setattr(windows, "foreground_target", lambda: Target(1, 88, 10, "original"))
    with pytest.raises(RuntimeError, match="control changed"):
        insert_text(Target(1, 88, 11, "original"), "secret")


def test_unicode_events_are_complete_utf16_pairs(monkeypatch):
    target = Target(1, 88, 10, "original")
    monkeypatch.setattr(windows.user32, "IsWindow", lambda _: True)
    monkeypatch.setattr(windows, "foreground_target", lambda: target)
    monkeypatch.setattr(windows, "key_down", lambda _: False)
    events = []
    def send(count, inputs, size):
        assert size == ctypes.sizeof(windows.Input)
        events.extend((inputs[i].value.ki.wScan, inputs[i].value.ki.dwFlags) for i in range(count))
        return count
    monkeypatch.setattr(windows.user32, "SendInput", send)
    insert_text(target, "আ🙂")
    assert len(events) == 6
    assert [flags for _, flags in events] == [4, 6, 4, 6, 4, 6]
    assert b"".join(unit.to_bytes(2, "little") for unit, _ in events[::2]).decode("utf-16-le") == "আ🙂"


def test_partial_send_is_reported(monkeypatch):
    target = Target(1, 88, 10, "original")
    monkeypatch.setattr(windows.user32, "IsWindow", lambda _: True)
    monkeypatch.setattr(windows, "foreground_target", lambda: target)
    monkeypatch.setattr(windows, "key_down", lambda _: False)
    monkeypatch.setattr(windows.user32, "SendInput", lambda *_: 0)
    with pytest.raises(RuntimeError, match="Windows blocked"):
        insert_text(target, "hello")
