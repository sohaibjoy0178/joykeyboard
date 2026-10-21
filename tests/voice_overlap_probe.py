"""Replay public WAV fixtures in real time through the UI and real Google recognition."""
import json
import os
import sys
import tempfile
import time
import wave
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def probe():
    from PySide6.QtWidgets import QApplication

    import app
    import voice

    os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="joy-overlap-probe-")
    application = QApplication([])
    reports = []
    cases = [("baseline", "bn-BD", ROOT / "artifacts/bn-10025278611427771211.pcm.wav"),
             ("overlap", "bn-BD", ROOT / "artifacts/bn-10025278611427771211.pcm.wav"),
             ("overlap", "en-US", Path(tempfile.gettempdir()) / "joykeyboard-jfk.wav")]
    for mode, language, path in cases:
        with wave.open(str(path), "rb") as wav:
            assert wav.getnchannels() == 1 and wav.getsampwidth() == 2
            rate = wav.getframerate()
            pcm = wav.readframes(wav.getnframes())
        speech_end = voice._speech_chunks(pcm, rate)[-1]["end"] / 16000
        padded = pcm + b"\0\0" * (rate * 2)
        uploads, results = [], []

        class Replay:
            level, error = 0.1, None
            def __init__(self, device=None):
                self.started, self.stopped = 0, None
            def start(self):
                self.started = time.monotonic()
            def size(self):
                return min(len(padded) // 2, int((time.monotonic() - self.started) * rate))
            def tail(self):
                count = self.size()
                return padded[max(0, count - rate * 8) * 2:count * 2], rate, count
            def snapshot(self):
                return padded[:self.size() * 2], rate
            def stop(self):
                self.stopped = time.monotonic()
                return self.snapshot()
            def cancel(self):
                pass

        original_upload = voice.sr.Recognizer.recognize_google
        def upload(client, audio, **kwargs):
            uploads.append({"at_seconds": time.monotonic() - capture.started,
                            "audio_seconds": len(audio.frame_data) / (audio.sample_rate * 2)})
            return original_upload(client, audio, **kwargs)

        with patch.object(app, "Recorder", Replay), patch.object(app, "foreground_target", return_value=None), \
             patch.object(app, "key_down", return_value=False), patch.object(app, "list_microphones", return_value=[]), \
             patch.object(voice.PauseMonitor, "EARLY_SECONDS", 100 if mode == "baseline" else 0.35), \
             patch.object(voice.sr.Recognizer, "recognize_google", upload):
            view = app.JoyWindow(smoke=True)
            view.auto_type.setChecked(False)
            view.engine.setCurrentIndex(view.engine.findData("google"))
            view.language.setCurrentIndex(view.language.findData(language))
            original_receive = view.receive_text
            def receive(token, text):
                results.append({"text": text, "at_seconds": time.monotonic() - capture.started})
                original_receive(token, text)
            view.receive_text = receive
            view.poll.start(40)
            view.start_recording()
            capture = view.recorder
            assert capture is not None
            try:
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    application.processEvents()
                    if capture.stopped and view.job is None:
                        break
                    time.sleep(0.005)
                assert capture.stopped and view.job is None and len(results) == 1, view.message.text()
                text = results[0]["text"]
                assert "কিবোর্ড" in text if language == "bn-BD" else "country" in text.lower() and "fellow" in text.lower()
                assert len(uploads) <= 2
                report = {"mode": mode, "language": language, "fixture": path.name,
                          "reference_speech_end_seconds": speech_end,
                          "stop_seconds": capture.stopped - capture.started,
                          "text_seconds": results[0]["at_seconds"],
                          "after_speech_seconds": results[0]["at_seconds"] - speech_end,
                          "uploads": uploads, "text": text, "passed": True}
                reports.append(report)
                print(json.dumps(report, ensure_ascii=True), flush=True)
            finally:
                view.cancel()
                while view.job is not None:
                    application.processEvents()
                    time.sleep(0.01)
                view.close()
                application.processEvents()
    assert len(reports[1]["uploads"]) == 1, "Final Bengali phrase should reuse early request"
    assert len(reports[2]["uploads"]) == 2, "Resumed English speech must use complete recording"
    result = {"cases": reports, "bengali_seconds_saved": reports[0]["after_speech_seconds"] - reports[1]["after_speech_seconds"],
              "live_microphone": False, "passed": True}
    (ROOT / "artifacts/voice-overlap-realtime.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    probe()
