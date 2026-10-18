"""Replay a public fixture through real pause detection and Google recognition, without Finish."""
import json
import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def probe():
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    import app
    with wave.open(str(ROOT / "artifacts" / "bn-10025278611427771211.pcm.wav"), "rb") as wav:
        rate = wav.getframerate()
        pcm = wav.readframes(wav.getnframes()) + b"\0\0" * (rate * 2)
    class FixtureRecorder:
        level = 0.1
        error = None
        def __init__(self, device=None):
            pass
        def start(self):
            pass
        def tail(self, seconds=8):
            return pcm[-rate * seconds * 2:], rate, len(pcm) // 2
        def stop(self):
            return pcm, rate
        def cancel(self):
            pass
    app.Recorder = FixtureRecorder
    app.foreground_target = lambda: None
    app.key_down = lambda key: False
    application = QApplication([])
    view = app.JoyWindow(smoke=True)
    view.auto_type.setChecked(False)
    view.auto_pause.setChecked(True)
    view.language.setCurrentIndex(view.language.findData("bn-BD"))
    view.engine.setCurrentIndex(view.engine.findData("google"))
    try:
        view.show_compact()
        QTest.mouseClick(view.compact.record, Qt.MouseButton.LeftButton)
        view.poll.start(40)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            QTest.qWait(40)
            time.sleep(0.01)
            if view.recorder is None and view.job is None and view.transcript.toPlainText():
                break
        text = view.transcript.toPlainText()
        assert view.recorder is None and view.job is None and "কিবোর্ড" in text, (view.message.text(), vars(view.pause_monitor) if view.pause_monitor else None)
        assert not view.isVisible() and view.pause_monitor is None
        report = {"passed": True, "start_clicks": 1, "finish_clicks": 0, "speech_detector": "actual local Silero",
                  "recognizer": "actual Google web", "audio": "public prerecorded Bengali fixture, accelerated replay",
                  "microphone_captured": False, "studio_stayed_hidden": True, "transcript": text}
        (ROOT / "artifacts" / "auto-pause-flow.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
    finally:
        view.close()
        application.processEvents()


if __name__ == "__main__":
    probe()
