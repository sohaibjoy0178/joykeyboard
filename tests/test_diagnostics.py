import wave
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import diagnostics


def test_pause_fixture_starts_one_early_request_and_still_waits_for_finish(monkeypatch):
    class Monitor:
        reason, early_ready, _last_end = None, False, 1.0
        def __init__(self, recorder):
            self.count = 0
        def check(self):
            self.count += 1
            self.early_ready = self.count >= 6
            if self.count >= 9:
                self.reason = "pause"
    monkeypatch.setattr(diagnostics, "PauseMonitor", Monitor)
    early = Mock()
    pcm, result = diagnostics.pause_capture(b"\x00\x10" * 16000, 16000, early)
    assert result["capture_end_seconds"] == 2.25 and len(pcm) == 72000
    early.assert_called_once()
    assert len(early.call_args.args[0]) == 48000


@pytest.mark.parametrize("engine,auto_pause", [("google", True), ("google", False), ("offline", True)])
def test_packaged_diagnostic_exercises_early_path_only_for_online_pause(tmp_path, monkeypatch, engine, auto_pause):
    source = tmp_path / "speech.wav"
    with wave.open(str(source), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x10" * 16000)
    pending = object()
    client = SimpleNamespace(start_early=Mock(return_value=pending), transcribe=Mock(return_value="text"))
    monkeypatch.setattr(diagnostics, "Recognizer", lambda _: client)
    def capture(pcm, rate, on_early):
        if on_early is not None:
            on_early(pcm)
        return pcm, {"auto_pause_detected": True}
    monkeypatch.setattr(diagnostics, "pause_capture", capture)
    result = diagnostics.check_audio(source, engine, tmp_path / "result.json", auto_pause=auto_pause)
    expected = engine == "google" and auto_pause
    assert result["early_recognition_started"] is expected
    assert client.transcribe.call_args.kwargs["early"] is (pending if expected else None)
    assert client.start_early.call_count == int(expected)
