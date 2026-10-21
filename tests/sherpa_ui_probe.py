"""Real Sherpa in the actual Qt voice job; fixture capture, no live microphone or typing."""
import json
import os
import shutil
import sys
import tempfile
import time
import wave
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "2")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def probe():
    from PySide6.QtWidgets import QApplication
    from sherpa_benchmark import memory

    import app
    from voice import SHERPA_FILES, SHERPA_MODEL

    profile = Path(tempfile.mkdtemp(prefix="joy-sherpa-ui-"))
    os.environ["LOCALAPPDATA"] = str(profile)
    cache = profile / "JoyKeyboard/models" / SHERPA_MODEL
    cache.mkdir(parents=True)
    for name in SHERPA_FILES:
        shutil.copy2(ROOT / "artifacts/sherpa-bn-model" / name, cache / name)
    source = ROOT / "artifacts/bn-10025278611427771211.pcm.wav"
    with wave.open(str(source), "rb") as wav:
        rate, pcm = wav.getframerate(), wav.readframes(wav.getnframes())
    padded = pcm + b"\0\0" * rate * 2
    class Replay:
        level, error = .1, None
        def __init__(self, device=None):
            self.started, self.stopped, self.cleared = 0, None, False
        def start(self):
            self.started = time.perf_counter()
        def count(self):
            return min(len(padded) // 2, int((time.perf_counter() - self.started) * rate))
        def tail(self):
            count = self.count()
            return padded[max(0, count - rate * 8) * 2:count * 2], rate, count
        def read_since(self, frame):
            count = 0 if self.cleared else self.count()
            return padded[frame * 2:count * 2], rate, count
        def stop(self):
            self.stopped = time.perf_counter()
            result = padded[:self.count() * 2], rate
            self.cleared = True
            return result
        def cancel(self):
            self.cleared = True
    application = QApplication([])
    report = {}
    with patch.object(app, "Recorder", Replay), patch.object(app, "key_down", return_value=False), \
         patch.object(app, "foreground_target", return_value=None), patch.object(app, "list_microphones", return_value=[]):
        view = app.JoyWindow(smoke=True)
        view.auto_type.setChecked(False)
        view.poll.start(40)
        view.compact._placed = True
        view.compact.move(80, 160)
        view.show_compact()
        def wait_until(predicate, seconds=35):
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                application.processEvents()
                if predicate():
                    return
                time.sleep(.005)
            raise AssertionError(view.message.text())
        def idle_sample():
            started, cpu = time.perf_counter(), time.process_time()
            deadline = started + 5
            while time.perf_counter() < deadline:
                application.processEvents()
                time.sleep(.02)
            elapsed, used = time.perf_counter() - started, time.process_time() - cpu
            return {"one_core_percent": used / elapsed * 100, **memory()}
        report["google_idle_before"] = idle_sample()
        original_receive = view.receive_text
        results = []
        def receive(token, text):
            results.append((time.perf_counter(), text))
            original_receive(token, text)
        view.receive_text = receive
        try:
            view.engine.setCurrentIndex(view.engine.findData("sherpa"))
            started, cpu = time.perf_counter(), time.process_time()
            view.start_recording()
            capture = view.recorder
            assert capture is not None and view.job is not None
            wait_until(lambda: bool(view.stream_speech and view.stream_speech.partial))
            report["first_preview_seconds"] = time.perf_counter() - capture.started
            assert not view.transcript.toPlainText() and view.compact.record.isEnabled()
            report["preview_memory"] = memory()
            view.compact.grab().save(str(ROOT / "artifacts/sherpa-live-preview.png"))
            wait_until(lambda: view.job is None)
            elapsed, used = time.perf_counter() - started, time.process_time() - cpu
            assert len(results) == 1 and "আশ্চর্য" in results[0][1]
            report["result"] = results[0][1]
            report["finish_to_text_seconds"] = results[0][0] - capture.stopped
            report["recording_one_core_percent_including_load_and_vad"] = used / elapsed * 100
            report["sherpa_idle_loaded"] = idle_sample()
            started, cpu = time.perf_counter(), time.process_time()
            view.start_recording()
            warm_capture = view.recorder
            wait_until(lambda: view.job is None)
            elapsed, used = time.perf_counter() - started, time.process_time() - cpu
            assert len(results) == 2 and results[1][1] == results[0][1]
            report["warm_recording_one_core_percent_with_vad"] = used / elapsed * 100
            report["warm_finish_to_text_seconds"] = results[1][0] - warm_capture.stopped
            view.engine.setCurrentIndex(view.engine.findData("google"))
            assert view.recognizer._sherpa is None
            report["google_idle_after_unload"] = idle_sample()
            before = view.transcript.toPlainText()
            view.engine.setCurrentIndex(view.engine.findData("sherpa"))
            view.start_recording()
            wait_until(lambda: bool(view.stream_speech and view.stream_speech.partial))
            cancelled_at = time.monotonic()
            view.cancel()
            wait_until(lambda: view.job is None)
            report["cancel_seconds"] = time.monotonic() - cancelled_at
            assert view.transcript.toPlainText() == before
            view.engine.setCurrentIndex(view.engine.findData("google"))
            report["memory_after_second_cycle"] = memory()
            report.update(passed=True, live_microphone=False, auto_type=False,
                          scope="actual source Qt app in smoke mode, fixture capture, no native keyboard hook")
        finally:
            view.cancel()
            wait_until(lambda: view.job is None)
            view.close()
    (ROOT / "artifacts/sherpa-ui-profile.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True))


if __name__ == "__main__":
    probe()
