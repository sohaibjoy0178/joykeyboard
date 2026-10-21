import io
import sys
import threading
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import pytest

import voice

PCM = b"\x00\x10" * 16000


def test_web_flac_encoder_owns_windows_handles_and_roundtrips():
    from faster_whisper.audio import decode_audio
    encoded = voice.WebAudio(PCM, 16000, 2).get_flac_data(convert_width=2)
    assert encoded.startswith(b"fLaC")
    decoded = decode_audio(io.BytesIO(encoded))
    assert len(decoded) == 16000
    assert np.allclose(decoded, 0.125)
    with patch.object(voice.subprocess, "run", return_value=SimpleNamespace(stdout=b"flac")) as run:
        assert voice.WebAudio(PCM, 16000, 2).get_flac_data() == b"flac"
        assert run.call_args.kwargs["stdout"] == voice.subprocess.PIPE
        assert run.call_args.kwargs["stderr"] == voice.subprocess.PIPE
        assert run.call_args.kwargs["input"].startswith(b"RIFF")
        assert run.call_args.kwargs["timeout"] == 30
        assert "--fast" in run.call_args.args[0]


def test_loopback_downmix_and_stop(monkeypatch):
    recorder = voice.LoopbackRecorder()
    class Stream:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def record(self, numframes):
            recorder._stop_event.set()
            return np.array([[0.5, -0.5], [0.5, 0.5]], dtype=np.float32)
    source = Mock()
    source.recorder.return_value = Stream()
    soundcard = SimpleNamespace(default_speaker=lambda: SimpleNamespace(id="test-speaker"),
                                get_microphone=Mock(return_value=source))
    monkeypatch.setitem(sys.modules, "soundcard", soundcard)
    recorder.start()
    pcm, rate = recorder.stop()
    assert rate == 48000
    assert np.frombuffer(pcm, dtype=np.int16).tolist() == [0, 16383]
    soundcard.get_microphone.assert_called_once_with("test-speaker", include_loopback=True)
    assert recorder._thread is None


def test_loopback_device_failure_visible(monkeypatch):
    monkeypatch.setitem(sys.modules, "soundcard", SimpleNamespace(default_speaker=lambda: None))
    recorder = voice.LoopbackRecorder()
    with pytest.raises(voice.VoiceError, match="System audio capture failed"):
        recorder.start()
    recorder.cancel()

@pytest.fixture
def microphone():
    stream = Mock()
    with patch.object(voice.sd, "query_devices", return_value={"default_samplerate": 48000}), patch.object(
        voice.sd, "RawInputStream", return_value=stream
    ) as constructor:
        yield stream, constructor


def test_recorder_pcm_meter_and_cleanup(microphone):
    stream, constructor = microphone
    recorder = voice.Recorder(4)
    recorder.start()
    pcm = np.full(480, 4096, dtype=np.int16).tobytes()
    constructor.call_args.kwargs["callback"](pcm, 480, None, False)
    assert 0.49 < recorder.level < 0.51
    assert recorder.snapshot() == (pcm, 48000)
    assert recorder.read_since(240) == (pcm[480:], 48000, 480)
    assert recorder.stop() == (pcm, 48000)
    assert recorder.level == 0
    stream.stop.assert_called_once()
    stream.close.assert_called_once()
    assert constructor.call_args.kwargs["device"] == 4


def test_recorder_tail_is_bounded_and_preserves_frame_offset(microphone):
    recorder = voice.Recorder()
    recorder.start()
    pcm = np.arange(4800, dtype=np.int16).tobytes()
    recorder._callback(pcm, 4800, None, False)
    assert recorder.tail(seconds=0.05) == (pcm[-4800:], 48000, 4800)
    recorder.cancel()


def test_pause_requires_speech_and_long_enough_silence():
    state = {"seconds": 1}
    recorder = SimpleNamespace(tail=lambda: (PCM * state["seconds"], 16000, 16000 * state["seconds"]))
    monitor = voice.PauseMonitor(recorder)
    with patch("faster_whisper.vad.get_speech_timestamps", side_effect=[[{"start": 0, "end": 16000}], [], []]):
        monitor.check()
        assert monitor.reason is None
        state["seconds"] = 2
        monitor.check()
        assert monitor.reason is None
        state["seconds"] = 3
        monitor.check()
        assert monitor.reason == "pause"


def test_resumed_speech_resets_pause_and_rolling_tail_uses_absolute_time():
    state = {"seconds": 1}
    recorder = SimpleNamespace(tail=lambda: (PCM * min(8, state["seconds"]), 16000, 16000 * state["seconds"]))
    monitor = voice.PauseMonitor(recorder)
    with patch("faster_whisper.vad.get_speech_timestamps", side_effect=[
        [{"start": 0, "end": 16000}], [{"start": 0, "end": 48000}], [{"start": 0, "end": 96000}],
    ]):
        monitor.check()
        state["seconds"] = 3
        monitor.check()
        assert monitor.reason is None
        state["seconds"] = 20
        monitor.check()
        assert monitor.reason == "pause" and monitor._last_end == 18


def test_pause_finishes_at_1_2_seconds_but_keeps_short_hesitation():
    state = {"duration": 1.0}
    recorder = SimpleNamespace(tail=lambda: (
        PCM + b"\0\0" * int(16000 * (state["duration"] - 1)),
        16000, int(16000 * state["duration"]),
    ))
    monitor = voice.PauseMonitor(recorder)
    with patch("faster_whisper.vad.get_speech_timestamps", return_value=[{"start": 0, "end": 16000}]):
        for duration in (1.0, 2.0, 2.19):
            state["duration"] = duration
            monitor.check()
            assert monitor.reason is None
        state["duration"] = 2.21
        monitor.check()
        assert monitor.reason == "pause"


def test_early_pause_resets_when_speech_resumes_without_finishing():
    state = {"frames": 16000}
    recorder = SimpleNamespace(tail=lambda: (b"\0\0" * state["frames"], 16000, state["frames"]))
    monitor = voice.PauseMonitor(recorder)
    with patch.object(voice, "_speech_chunks", side_effect=[
        [{"end": 16000}], [{"end": 16000}], [{"end": 28000}], [{"end": 28000}],
    ]):
        monitor.check()
        assert not monitor.early_ready
        state["frames"] = 24000
        monitor.check()
        assert monitor.early_ready and monitor.reason is None
        state["frames"] = 28000
        monitor.check()
        assert not monitor.early_ready and monitor.reason is None
        state["frames"] = 48000
        monitor.check()
        assert monitor.early_ready and monitor.reason == "pause"


def test_no_speech_timeout_and_stopped_monitor_does_not_deliver():
    recorder = SimpleNamespace(tail=lambda: (b"\0\0" * 160000, 16000, 160000))
    monitor = voice.PauseMonitor(recorder)
    with patch("faster_whisper.vad.get_speech_timestamps", return_value=[]):
        monitor.check()
        assert monitor.reason == "no_speech"
    monitor = voice.PauseMonitor(recorder)
    monitor.stop()
    with patch("faster_whisper.vad.get_speech_timestamps") as vad:
        monitor.check()
        vad.assert_not_called()
        assert monitor.reason is None


def test_pause_detection_error_requests_manual_finish():
    monitor = voice.PauseMonitor(None)
    with patch.object(monitor, "check", side_effect=RuntimeError("missing model")):
        monitor.start()
        monitor.join(2)
    assert not monitor.is_alive() and monitor.reason is None
    assert "Finish" in monitor.error


def test_recording_cancel_discards_audio(microphone):
    stream, _ = microphone
    recorder = voice.Recorder()
    recorder.start()
    recorder._callback(b"\0\0" * 10, 10, None, False)
    recorder.cancel()
    assert recorder.stop() == (b"", 48000)
    stream.abort.assert_called_once()
    stream.close.assert_called_once()


def test_recording_is_bounded(microphone):
    recorder = voice.Recorder()
    recorder.MAX_SECONDS = 1
    recorder.start()
    with pytest.raises(voice.sd.CallbackAbort):
        recorder._callback(b"\0\0" * 48001, 48001, None, False)
    assert recorder._size == 48000 * 2
    assert len(recorder._buffer) == 48000 * 2
    with pytest.raises(voice.VoiceError, match="safety limit"):
        recorder.stop()


def test_capture_failure_closes_device(microphone):
    stream, _ = microphone
    stream.start.side_effect = RuntimeError("device disconnected")
    recorder = voice.Recorder()
    with pytest.raises(voice.VoiceError, match="Cannot open microphone"):
        recorder.start()
    stream.close.assert_called_once()
    assert recorder._stream is None


def test_capture_overflow_is_reported(microphone):
    recorder = voice.Recorder()
    recorder.start()
    with pytest.raises(voice.sd.CallbackAbort):
        recorder._callback(b"\0\0" * 480, 480, None, True)
    with pytest.raises(voice.VoiceError, match="lost audio"):
        recorder.stop()


def test_google_uses_https_timeout_and_no_user_key(tmp_path):
    client = Mock()
    client.recognize_google.return_value = " বাংলা লেখা "
    with patch.object(voice.sr, "Recognizer", return_value=client):
        text = voice.Recognizer(tmp_path).transcribe(PCM, 16000, "bn-BD", "google")
    assert text == "বাংলা লেখা"
    assert client.operation_timeout == 30
    assert client.recognize_google.call_args.kwargs == {
        "language": "bn-BD", "endpoint": "https://www.google.com/speech-api/v2/recognize"
    }


@pytest.mark.parametrize("rate", [8000, 16000, 44100, 48000, 192000])
def test_google_upload_is_speech_rate_with_matching_header_and_lossless_flac(tmp_path, rate):
    from faster_whisper.audio import decode_audio
    from speech_recognition.recognizers.google import RequestBuilder
    original = np.full(rate, 4096, dtype=np.int16).tobytes()
    with patch.object(voice.sr.Recognizer, "recognize_google", return_value="text") as recognize:
        voice.Recognizer(tmp_path).transcribe(original, rate, "en-US", "google")
    audio = recognize.call_args.args[0]
    assert audio.sample_rate == min(rate, 16000)
    assert len(audio.frame_data) // 2 == audio.sample_rate
    builder = RequestBuilder(endpoint="", key="", language="en-US", filter_level=0)
    assert builder.build_headers(audio) == {"Content-Type": f"audio/x-flac; rate={audio.sample_rate}"}
    decoded = decode_audio(io.BytesIO(audio.get_flac_data()), sampling_rate=audio.sample_rate)
    assert len(decoded) == audio.sample_rate and np.allclose(decoded, 0.125)


@pytest.mark.parametrize("error", [voice.sr.RequestError("network"), voice.sr.UnknownValueError()])
def test_google_errors_are_readable(tmp_path, error):
    with patch.object(voice.sr.Recognizer, "recognize_google", side_effect=error), pytest.raises(voice.VoiceError):
        voice.Recognizer(tmp_path).transcribe(PCM, 16000, "en-US", "google")


def test_offline_transcribe_never_downloads(tmp_path):
    with patch("faster_whisper.utils.download_model") as download, pytest.raises(voice.VoiceError, match="Prepare Model"):
        voice.Recognizer(tmp_path, bundled_dir=tmp_path / "no-bundle").transcribe(PCM, 16000, "bn-BD", "offline")
    download.assert_not_called()


def test_local_model_and_language_are_forwarded(tmp_path):
    client = voice.Recognizer(tmp_path)
    model = Mock()
    model.transcribe.return_value = (iter([SimpleNamespace(text=" Hello "), SimpleNamespace(text="world")]), None)
    with patch.object(client, "model_ready", return_value=True), patch.object(client, "_load_model", return_value=model):
        assert client.transcribe(PCM * 3, 48000, "en-US", "offline", "tiny") == "Hello world"
    audio = model.transcribe.call_args.args[0]
    with voice.wave.open(audio, "rb") as wav:
        assert wav.getframerate() == 48000
        assert wav.getnchannels() == 1
    assert model.transcribe.call_args.kwargs["language"] == "en"


def test_prepare_is_only_explicit_download_path(tmp_path):
    client = voice.Recognizer(tmp_path, bundled_dir=tmp_path / "absent")
    with patch("faster_whisper.utils.download_model") as download, patch.object(client, "_load_model") as load:
        client.prepare_model("tiny")
    download.assert_called_once_with("tiny", output_dir=str(tmp_path / "tiny"))
    load.assert_called_once_with("tiny")


def test_local_model_load_cannot_download(tmp_path):
    client = voice.Recognizer(tmp_path, bundled_dir=tmp_path / "absent")
    with patch("faster_whisper.WhisperModel") as loader:
        client._load_model("tiny")
        client._load_model("tiny")
    assert loader.call_count == 1
    assert loader.call_args.args == (str(tmp_path / "tiny"),)
    assert loader.call_args.kwargs["local_files_only"] is True
    assert 1 <= loader.call_args.kwargs["cpu_threads"] <= 2


def test_cancelled_result_is_discarded(tmp_path):
    cancelled = threading.Event()
    def recognize(*args, **kwargs):
        cancelled.set()
        return "Should never be pasted"
    with patch.object(voice.sr.Recognizer, "recognize_google", side_effect=recognize), pytest.raises(voice.VoiceError, match="Cancelled"):
        voice.Recognizer(tmp_path).transcribe(
            PCM, 16000, "en-US", "google", cancel_event=cancelled
        )


@pytest.mark.parametrize("pcm,rate,lang,engine", [
    (b"", 16000, "en-US", "google"),
    (b"\0" * 32001, 16000, "en-US", "google"),
    (b"\0" * 32000, 0, "en-US", "google"),
    (b"\0" * 32000, 16000, "xx", "google"),
    (b"\0" * 32000, 16000, "en-US", "unknown"),
], ids=["empty", "partial_sample", "bad_rate", "bad_language", "bad_engine"])
def test_invalid_input_is_rejected(tmp_path, pcm, rate, lang, engine):
    with pytest.raises(voice.VoiceError):
        voice.Recognizer(tmp_path).transcribe(pcm, rate, lang, engine)


def test_model_name_cannot_escape_cache(tmp_path):
    with pytest.raises(voice.VoiceError):
        voice.Recognizer(tmp_path).model_ready("../../outside")


def test_offline_audio_decoder_dependency_compatibility():
    from faster_whisper.audio import decode_audio

    audio = io.BytesIO()
    with voice.wave.open(audio, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(48000)
        wav.writeframes(b"\0\0" * 4800)
    audio.seek(0)
    decoded = decode_audio(audio, sampling_rate=16000)
    assert decoded.dtype == np.float32
    assert 1500 <= len(decoded) <= 1700


def test_silent_capture_never_calls_online_service(tmp_path):
    with patch.object(voice.sr.Recognizer, "recognize_google") as recognize:
        with pytest.raises(voice.VoiceError, match="silent"):
            voice.Recognizer(tmp_path).transcribe(b"\0\0" * 16000, 16000, "bn-BD", "google")
        recognize.assert_not_called()


def test_bundled_model_works_without_user_cache_or_download(tmp_path):
    bundle = tmp_path / "bundle" / "base"
    bundle.mkdir(parents=True)
    for name in ("model.bin", "config.json", "tokenizer.json"):
        (bundle / name).write_bytes(b"test")
    client = voice.Recognizer(tmp_path / "empty-cache", bundled_dir=bundle.parent)
    assert client.model_ready("base")
    assert client._model_path("base") == bundle
    with patch("faster_whisper.WhisperModel") as load:
        client._load_model("base")
    assert load.call_args.args == (str(bundle),)
    assert load.call_args.kwargs["local_files_only"] is True


def test_user_model_precedes_bundled_model(tmp_path):
    for root in (tmp_path / "cache", tmp_path / "bundle"):
        (root / "base").mkdir(parents=True)
        for name in ("model.bin", "config.json", "tokenizer.json"):
            (root / "base" / name).write_bytes(b"test")
    client = voice.Recognizer(tmp_path / "cache", bundled_dir=tmp_path / "bundle")
    assert client._model_path("base") == tmp_path / "cache" / "base"
