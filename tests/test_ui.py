import threading

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app import JoyWindow
from windows import Target


@pytest.fixture(scope="module")
def qt_app():
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def window(qt_app, monkeypatch):
    from core import DEFAULT_RULES, DEFAULTS
    monkeypatch.setattr("app.load_settings", lambda _: ({**DEFAULTS, "rules": dict(DEFAULT_RULES)}, ""))
    monkeypatch.setattr("app.list_microphones", lambda: [(3, "Test microphone")])
    monkeypatch.setattr("app.key_down", lambda key: False)
    class FakePauseMonitor:
        reason = None
        error = None
        stopped = False
        def __init__(self, recorder):
            pass
        def start(self):
            pass
        def stop(self):
            self.stopped = True
    monkeypatch.setattr("app.PauseMonitor", FakePauseMonitor)
    view = JoyWindow(smoke=True)
    view.auto_type.setChecked(False)
    yield view
    view.close()


def test_speech_pause_finishes_without_click_and_types_once(window, monkeypatch):
    import time
    from types import SimpleNamespace
    window.recorder = SimpleNamespace(level=0.1, error=None, stop=lambda: (b"audio", 16000))
    window.started = time.monotonic()
    window.pause_monitor = SimpleNamespace(reason="pause", error=None, stop=lambda: None)
    monkeypatch.setattr("app.foreground_target", lambda: None)
    monkeypatch.setattr("app.key_down", lambda key: False)
    jobs = []
    monkeypatch.setattr(window, "start_job", lambda function, success: jobs.append(success))
    window.tick()
    window.tick()
    assert window.recorder is None and window.pause_monitor is None and len(jobs) == 1
    jobs[0]("আমি বাংলায় লিখি")
    assert window.transcript.toPlainText() == "আমি বাংলায় লিখি"


def test_empty_recording_cancels_locally_and_pause_failure_leaves_manual_finish(window, monkeypatch):
    import time
    from types import SimpleNamespace
    cancelled = []
    monkeypatch.setattr("app.foreground_target", lambda: None)
    monkeypatch.setattr("app.key_down", lambda key: False)
    window.started = time.monotonic()
    window.recorder = SimpleNamespace(level=0, error=None, cancel=lambda: cancelled.append(True))
    window.pause_monitor = SimpleNamespace(reason="no_speech", error=None, stop=lambda: None)
    window.tick()
    assert cancelled == [True] and window.job is None and window.state.text() == "No speech detected"
    window.recorder = SimpleNamespace(level=0.1, error=None, cancel=lambda: None)
    window.pause_monitor = SimpleNamespace(reason=None, error="Use Finish manually", stop=lambda: None)
    window.tick()
    assert window.recorder is not None and window.pause_monitor is None
    assert window.state.text() == "Finish manually"


def test_hold_key_waits_for_release_even_when_pause_is_detected(window, monkeypatch):
    import time
    from types import SimpleNamespace
    window.started = time.monotonic()
    window.hold.setChecked(True)
    window.last_hold = True
    window.recorder = SimpleNamespace(level=0.1, error=None, stop=lambda: (b"audio", 16000), cancel=lambda: None)
    window.pause_monitor = SimpleNamespace(reason="pause", error=None, stop=lambda: None)
    monkeypatch.setattr("app.foreground_target", lambda: None)
    monkeypatch.setattr("app.key_down", lambda key: key == 0xA3)
    window.tick()
    assert window.recorder is not None
    jobs = []
    monkeypatch.setattr(window, "start_job", lambda *args: jobs.append(True))
    monkeypatch.setattr("app.key_down", lambda key: False)
    window.tick()
    assert window.recorder is None and jobs == [True]


def test_auto_pause_setting_can_be_disabled_from_bar(window):
    assert window.auto_pause.isChecked()
    window.compact.main_menu()
    action = next(a for a in window.compact._menu.actions() if a.text() == "Finish on speech pause")
    action.trigger()
    assert not window.auto_pause.isChecked() and window.settings["auto_pause"] is False
    window.compact._menu.close()


def test_custom_voice_shortcut_updates_hints_and_default_reset(window):
    from PySide6.QtGui import QKeySequence
    window.shortcut_edit.setKeySequence(QKeySequence("Ctrl+Alt+V"))
    window.apply_voice_shortcut()
    assert window.settings["voice_shortcut"] == "Ctrl+Alt+V"
    assert "Ctrl+Alt+V" in window.compact.record.toolTip()
    assert "Ctrl+Alt+V" in window.tray.toolTip()
    window.reset_voice_shortcut()
    assert window.settings["voice_shortcut"] == "Ctrl+Alt+Space"


def test_shortcut_editor_records_chord_and_apply_button_saves_it(window, qt_app):
    window.open_workspace(2)
    window.shortcut_edit.setFocus()
    qt_app.processEvents()
    QTest.keyClick(window.shortcut_edit, Qt.Key.Key_V,
                   Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier)
    QTest.qWait(50)
    QTest.mouseClick(window.shortcut_apply, Qt.MouseButton.LeftButton)
    assert window.settings["voice_shortcut"] == "Ctrl+Alt+V"
    assert window.recorder is None


def test_voice_shortcut_conflict_and_save_error_leave_old_choice(window, monkeypatch):
    from PySide6.QtGui import QKeySequence
    class Manager:
        shortcut = "Ctrl+Alt+Space"
        def register(self, value):
            if value == "Ctrl+Alt+X":
                raise OSError("Already in use")
            self.shortcut = value
        def close(self):
            pass
    manager = Manager()
    window.voice_hotkey = manager
    window.shortcut_edit.setKeySequence(QKeySequence("Ctrl+Alt+X"))
    window.apply_voice_shortcut()
    assert window.settings["voice_shortcut"] == manager.shortcut == "Ctrl+Alt+Space"
    assert "Already in use" in window.shortcut_status.text()
    window.smoke = False
    def fail(*args):
        raise OSError("Disk full")
    monkeypatch.setattr("app.save_settings", fail)
    window.shortcut_edit.setKeySequence(QKeySequence("Ctrl+Alt+V"))
    window.apply_voice_shortcut()
    assert window.settings["voice_shortcut"] == manager.shortcut == "Ctrl+Alt+Space"
    assert "Disk full" in window.shortcut_status.text()
    window.smoke = True


def test_shortcut_capture_never_starts_recording(window, qt_app, monkeypatch):
    calls = []
    monkeypatch.setattr(window, "toggle_record", lambda: calls.append(True))
    window.open_workspace(2)
    window.shortcut_edit.setFocus()
    qt_app.processEvents()
    window.voice_shortcut_triggered()
    assert not calls
    window.hide()
    window.shortcut_edit.clearFocus()
    window.voice_shortcut_triggered()
    assert calls == [True]


def test_opacity_menu_updates_preferences_and_live_bar(window, qt_app):
    bar = window.compact
    window.show_compact()
    assert bar.width() == 384 and bar.height() == 48
    assert bar.windowOpacity() == 1.0
    bar.main_menu()
    menu = next(a.menu() for a in bar._menu.actions() if a.text() == "Bar opacity")
    menu.actions()[2].trigger()
    qt_app.processEvents()
    assert window.bar_opacity.currentData() == 80 and window.settings["bar_opacity"] == 80
    assert abs(bar.windowOpacity() - .8) < .01
    menu.actions()[0].trigger()
    assert bar.windowOpacity() == 1.0
    bar._menu.close()


def test_idle_sync_does_not_relayout_and_record_controls_fit(window, qt_app, monkeypatch):
    bar = window.compact
    window.show_compact()
    bar.sync_controls()
    resized = []
    original = bar._resize
    monkeypatch.setattr(bar, "_resize", lambda: resized.append(True))
    for _ in range(100):
        window.sync_keyboard_controls()
    assert not resized
    monkeypatch.setattr(bar, "_resize", original)
    window.recorder = object()
    window.cancel_btn.setEnabled(True)
    bar.sync_controls()
    qt_app.processEvents()
    controls = [bar.grip, bar.brand, bar.mode, bar.keyboard_btn, bar.record, bar.cancel, bar.more, bar.hide_btn]
    for left, right in zip(controls, controls[1:]):
        assert left.geometry().right() < right.geometry().left()
    assert bar.hide_btn.geometry().right() < bar.shell.width()
    window.recorder = None


def test_startup_checkbox_updates_windows_and_reverts_on_failure(window, monkeypatch):
    import startup
    calls = []
    monkeypatch.setattr(startup, "set_enabled", calls.append)
    window.smoke = False
    window.autostart.setChecked(False)
    calls.clear()
    window.autostart.setChecked(True)
    window.autostart.setChecked(False)
    assert calls == [True, False]
    def denied(_):
        raise PermissionError("Startup access denied")
    monkeypatch.setattr(startup, "set_enabled", denied)
    window.autostart.setChecked(True)
    assert not window.autostart.isChecked()
    assert window.state.text() == "Startup setting not saved"
    window.smoke = True


def test_cancelled_result_never_enters_transcript_or_types(window, monkeypatch):
    calls = []
    monkeypatch.setattr("app.insert_text", lambda *args: calls.append(args))
    window.generation = 2
    window.receive_text(1, "stale result")
    assert not window.transcript.toPlainText()
    assert not calls


def test_cancel_event_blocks_same_generation_delivery(window, monkeypatch):
    calls = []
    monkeypatch.setattr("app.insert_text", lambda *args: calls.append(args))
    window.cancel_event.set()
    window.deliver(window.generation, "stale result")
    assert not calls


def test_destination_failure_keeps_transcript(window, monkeypatch):
    def blocked(*_):
        raise RuntimeError("Focus changed")
    monkeypatch.setattr("app.insert_text", blocked)
    window.target = Target(123, 456, 789, "Test document")
    window.transcript.setPlainText("বাংলা লেখা")
    window.deliver(window.generation, "বাংলা লেখা")
    assert window.transcript.toPlainText() == "বাংলা লেখা"
    assert window.message.text() == "Focus changed"


def test_record_controls_have_room_at_default_size(window, qt_app):
    window.show()
    qt_app.processEvents()
    assert window.record_btn.height() >= 40
    assert window.state.height() >= 25
    assert window.cancel_btn.height() >= 25


def test_finish_uses_capture_configuration_and_serial_job(window, monkeypatch):
    class FakeRecorder:
        def stop(self):
            return b"audio", 16000
    window.recorder = FakeRecorder()
    window.cancel_event = threading.Event()
    launched = []
    monkeypatch.setattr(window, "start_job", lambda function, success: launched.append((function, success)))
    window.finish_recording()
    assert window.recorder is None
    assert len(launched) == 1
    assert not window.record_btn.isEnabled()


def test_missing_offline_model_does_not_start_microphone(window, monkeypatch):
    window.engine.setCurrentIndex(window.engine.findData("offline"))
    monkeypatch.setattr(window.recognizer, "model_ready", lambda _: False)
    window.start_recording()
    assert window.recorder is None
    assert window.state.text() == "Prepare offline model"


def test_output_encoding_reaches_hook_and_voice_but_not_reviewed_tools(window, monkeypatch):
    from keyboard_engine import to_ansi
    calls = []
    monkeypatch.setattr("app.insert_text", lambda target, text: calls.append(text))
    window.last_external = Target(123, 456, 789, "Test document")
    window.output_encoding.setCurrentIndex(window.output_encoding.findData("bijoy"))
    assert window.keyboard_hook.output_encoding == "bijoy"
    assert window.encode_output("বাংলা") == to_ansi("বাংলা")
    window.insert_tool_text("বাংলা")
    assert calls == ["বাংলা"]


def test_normal_startup_and_duplicate_instance_lock(qt_app, tmp_path, monkeypatch):
    from PySide6.QtCore import QLockFile, QTimer
    from PySide6.QtWidgets import QMessageBox

    import app
    monkeypatch.setattr(app, "data_directory", lambda: tmp_path)
    shown = []
    class FakeWindow:
        def __init__(self, smoke):
            assert smoke is False
        def show_compact(self):
            shown.append(True)
            QTimer.singleShot(0, qt_app.quit)
    monkeypatch.setattr(app, "JoyWindow", FakeWindow)
    notices = []
    monkeypatch.setattr(QMessageBox, "information", lambda *args: notices.append(args))
    lock = QLockFile(str(tmp_path / "JoyKeyboard.lock"))
    assert lock.tryLock(0)
    assert app.run() == 0
    assert notices and not shown
    lock.unlock()
    assert app.run() == 0
    assert shown == [True]


def test_bar_is_the_compact_default_and_does_not_accept_focus(window, qt_app):
    window.show_compact()
    qt_app.processEvents()
    bar = window.compact
    assert bar.isVisible() and not window.isVisible()
    assert bar.width() <= 520 and bar.height() <= 85
    assert bar.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert bar.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus
    assert bar.record.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert bar.record.text() == "Speak"


def test_bar_menu_changes_existing_controls_and_reaches_every_tool(window, qt_app):
    bar = window.compact
    bar.main_menu()
    def submenu(title):
        return next(action.menu() for action in bar._menu.actions() if action.text() == title)
    submenu("Speech engine").actions()[1].trigger()
    assert window.engine.currentData() == "offline"
    submenu("Voice language").actions()[1].trigger()
    assert window.language.currentData() == "en-US"
    submenu("Keyboard layout").actions()[2].trigger()
    assert window.settings["keyboard_layout"] == "probhat"
    assert window.tools.layout_choice.currentData() == "probhat"
    assert "Probhat" in bar.mode.text()
    for index, action in enumerate(submenu("Keyboard and writing tools").actions()):
        action.trigger()
        assert window.isVisible() and window.tabs.currentIndex() == 1
        assert window.tools.panels.currentIndex() == index
    bar._menu.close()


def test_developer_credit_links_to_requested_facebook_profile(window):
    from PySide6.QtWidgets import QLabel
    labels = window.tabs.widget(3).findChildren(QLabel)
    credit = next(item for item in labels if "Developed by Sohaib Islam Joy" in item.text())
    assert "https://www.facebook.com/sohaib.islam1997" in credit.text()
    assert credit.openExternalLinks()
    window.compact.main_menu()
    action = next(a for a in window.compact._menu.actions() if a.text() == "Developed by Sohaib Islam Joy")
    action.trigger()
    assert window.isVisible() and window.tabs.currentIndex() == 3
    window.compact._menu.close()


def test_bar_record_cancel_use_existing_voice_session(window, qt_app, monkeypatch):
    class FakeRecorder:
        level = 0.2
        error = None
        cancelled = False
        def __init__(self, device=None):
            pass
        def start(self):
            pass
        def cancel(self):
            self.cancelled = True
    monkeypatch.setattr("app.Recorder", FakeRecorder)
    monkeypatch.setattr("app.foreground_target", lambda: Target(123, 456, 789, "Test document"))
    window.show_compact()
    bar = window.compact
    QTest.mouseClick(bar.record, Qt.MouseButton.LeftButton)
    assert window.recorder is not None and window.target.pid == 456
    assert bar.record.text() == "Finish" and bar.cancel.isVisible()
    assert not bar.mode.isEnabled() and not bar.keyboard_btn.isEnabled()
    recorder = window.recorder
    QTest.mouseClick(bar.cancel, Qt.MouseButton.LeftButton)
    assert recorder.cancelled and window.recorder is None
    assert bar.record.text() == "Speak" and not bar.cancel.isVisible()
    assert bar.mode.isEnabled()


def test_bar_finish_delivers_transcript_without_opening_workspace(window, qt_app, monkeypatch):
    class FakeRecorder:
        def __init__(self, device=None):
            pass
        def start(self):
            pass
        def stop(self):
            return b"audio", 16000
    monkeypatch.setattr("app.Recorder", FakeRecorder)
    monkeypatch.setattr(window.recognizer, "transcribe", lambda *args, **kwargs: "আমি বাংলায় লিখি")
    window.show_compact()
    QTest.mouseClick(window.compact.record, Qt.MouseButton.LeftButton)
    QTest.mouseClick(window.compact.record, Qt.MouseButton.LeftButton)
    for _ in range(100):
        QTest.qWait(20)
        if window.job is None:
            break
    assert window.job is None and window.transcript.toPlainText() == "আমি বাংলায় লিখি"
    assert not window.isVisible() and window.compact.copy.isVisible()


def test_bar_candidates_commit_selected_index_and_collapse(window, qt_app, monkeypatch):
    chosen = []
    monkeypatch.setattr(window.keyboard_hook, "choose", chosen.append)
    window.show_compact()
    bar = window.compact
    idle_height = bar.height()
    bar.update_candidates("ami", "আমি", ["আমি", "আমার", "আমিও"])
    qt_app.processEvents()
    assert bar.height() > idle_height and bar.candidates.isVisible()
    QTest.mouseClick(bar.candidate_buttons[1], Qt.MouseButton.LeftButton)
    assert chosen == [1]
    bar.update_candidates("", "", [])
    qt_app.processEvents()
    assert not bar.candidates.isVisible() and bar.height() == idle_height


def test_bar_drag_saves_position_and_recovers_offscreen(window, qt_app):
    window.show_compact()
    bar = window.compact
    bar.move(QApplication.primaryScreen().availableGeometry().topLeft() + QPoint(50, 50))
    start = bar.pos()
    QTest.mousePress(bar.grip, Qt.MouseButton.LeftButton)
    QTest.mouseMove(bar.grip, QPoint(70, 30))
    QTest.mouseRelease(bar.grip, Qt.MouseButton.LeftButton, pos=QPoint(70, 30))
    assert bar.pos() != start
    assert window.settings["bar_position"] == [bar.x(), bar.y()]
    bar.move(-99999, -99999)
    bar.clamp_position()
    assert QApplication.primaryScreen().availableGeometry().contains(bar.geometry())


def test_workspace_close_returns_to_bar_without_losing_draft(window, qt_app, monkeypatch):
    window.smoke = False
    window.open_workspace(1, 4)
    window.tools.docpad.setPlainText("Keep this draft")
    assert window.close() is False
    assert not window.isVisible() and window.compact.isVisible()
    assert window.tools.docpad.toPlainText() == "Keep this draft"
    monkeypatch.setattr(window.tools, "confirm_document_close", lambda: False)
    window.request_quit()
    assert not window.quitting and window.compact.isVisible()
    window.smoke = True


def test_bar_error_stays_until_dismissed_and_transcript_can_be_copied(window, qt_app, monkeypatch):
    window.show_compact()
    window.transcript.setPlainText("বাংলা লেখা")
    window.set_status("Connection failed", "Check internet and retry", True)
    bar = window.compact
    assert bar.feedback.isVisible() and not bar.feedback_timer.isActive()
    copied = []
    class Clipboard:
        def setText(self, value):
            copied.append(value)
    monkeypatch.setattr(QApplication, "clipboard", lambda: Clipboard())
    QTest.mouseClick(bar.copy, Qt.MouseButton.LeftButton)
    assert copied == ["বাংলা লেখা"]
    QTest.mouseClick(bar.dismiss, Qt.MouseButton.LeftButton)
    assert not bar.feedback.isVisible()
