"""Opt-in real-model staged update with a higher-version fixture, no live microphone."""
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

    import app
    import model_updates as models
    from voice import SHERPA_FILES, SHERPA_MODEL, Recognizer

    profile = Path(tempfile.mkdtemp(prefix="joy-sherpa-update-"))
    os.environ["LOCALAPPDATA"] = str(profile)
    os.environ["HF_HUB_OFFLINE"] = "1"
    cache = profile / "JoyKeyboard/models"
    baseline = cache / SHERPA_MODEL
    baseline.mkdir(parents=True)
    manifest = models.baseline_manifest()
    manifest["version"] = 2
    candidate = models.candidate_path(cache, manifest)
    candidate.mkdir(parents=True)
    for name in SHERPA_FILES:
        shutil.copy2(ROOT / "artifacts/sherpa-bn-model" / name, baseline / name)
        shutil.copy2(baseline / name, candidate / name)
    application = QApplication.instance() or QApplication([])
    with patch.object(app, "list_microphones", return_value=[]):
        view = app.JoyWindow(smoke=True)
    view.auto_type.setChecked(False)
    view.show_compact()

    def wait_done():
        deadline = time.monotonic() + 40
        while view.model_update_job is not None and time.monotonic() < deadline:
            application.processEvents()
            time.sleep(.005)
        assert view.model_update_job is None, view.model_update_status.text()

    try:
        with wave.open(str(ROOT / "artifacts/bn-10025278611427771211.pcm.wav"), "rb") as wav:
            rate, pcm = wav.getframerate(), wav.readframes(wav.getnframes())
        before = view.recognizer.transcribe(pcm, rate, "bn-BD", "sherpa")
        old_engine = view.recognizer._sherpa
        with patch.object(models, "check_channel", return_value=manifest):
            view.check_model_updates(manual=True)
            assert view.model_update_job is not None and view.record_btn.isEnabled()
            view.recorder = object()  # Model update completes while capture is marked busy.
            wait_done()
        assert view.ready_model_update == manifest
        assert view.recognizer._sherpa is old_engine and not (cache / "sherpa-active.json").exists()
        view.recorder = None
        view._idle()
        assert view.ready_model_update is None and view.recognizer._sherpa is None
        assert view.recognizer._model_path(SHERPA_MODEL) == candidate
        after = view.recognizer.transcribe(pcm, rate, "bn-BD", "sherpa")
        assert before == after and "আশ্চর্য" in after
        assert Recognizer(cache)._model_path(SHERPA_MODEL) == candidate
        loaded = view.recognizer._sherpa
        pointer = (cache / "sherpa-active.json").read_bytes()
        broken = json.loads(json.dumps(manifest))
        broken["version"] = 3
        broken["files"]["encoder.onnx"]["sha256"] = "0" * 64
        bad_path = models.candidate_path(cache, broken)
        bad_path.mkdir(parents=True)
        for name in SHERPA_FILES:
            shutil.copy2(baseline / name, bad_path / name)
        with patch.object(models, "check_channel", return_value=broken):
            view.check_model_updates(manual=True)
            wait_done()
        assert "current model kept" in view.model_update_status.text()
        assert (cache / "sherpa-active.json").read_bytes() == pointer and view.recognizer._sherpa is loaded
        assert baseline.is_dir() and view.record_btn.isEnabled()
        report = dict(passed=True, profile=str(profile), actual_model_hashes_and_native_validation=True,
                      version_fixture=2, real_future_model=False, activation_deferred_during_capture=True,
                      offline_transcript_unchanged=True, restart_uses_updated_path=True,
                      bad_hash_keeps_model=True, live_microphone=False, transcript=after)
        (ROOT / "artifacts/sherpa-update-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=True))
    finally:
        view.recorder = None
        view.close()


if __name__ == "__main__":
    probe()
