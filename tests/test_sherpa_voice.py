import hashlib
import io
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import urlsplit

import numpy as np
import pytest

import model_updates
import voice


@pytest.fixture
def files(monkeypatch, tmp_path):
    data = {name: (name + "-test").encode() for name in voice.SHERPA_FILES}
    monkeypatch.setattr(voice, "SHERPA_FILES", {
        name: (len(raw), hashlib.sha256(raw).hexdigest()) for name, raw in data.items()
    })
    client = voice.Recognizer(tmp_path / "cache", tmp_path / "no-bundle")
    return client, data


def test_explicit_download_pins_revision_checks_hash_and_needs_no_account(files, monkeypatch):
    client, data = files
    def download(url, cancel):
        assert f"/{voice.SHERPA_REPO}/resolve/{voice.SHERPA_REVISION}/" in url
        response = io.BytesIO(data[Path(urlsplit(url).path).name])
        response.headers = {}
        return response
    fetch = Mock(side_effect=download)
    monkeypatch.setattr(model_updates, "_open_model", fetch)
    monkeypatch.setattr(client, "_load_sherpa", Mock())
    assert not client.model_ready(voice.SHERPA_MODEL)
    client.prepare_model(voice.SHERPA_MODEL)
    assert client.model_ready(voice.SHERPA_MODEL) and fetch.call_count == 4
    fetch.reset_mock()
    client.prepare_model(voice.SHERPA_MODEL)
    fetch.assert_not_called()


def test_corrupt_download_is_removed_and_cannot_be_loaded(files, monkeypatch):
    client, _ = files
    def download(url, cancel):
        response = io.BytesIO(b"corrupt")
        response.headers = {}
        return response
    monkeypatch.setattr(model_updates, "_open_model", download)
    load = Mock()
    monkeypatch.setattr(client, "_load_sherpa", load)
    with pytest.raises(voice.VoiceError, match="verification failed"):
        client.prepare_model(voice.SHERPA_MODEL)
    assert not client.model_ready(voice.SHERPA_MODEL)
    assert not (client.cache_dir / voice.SHERPA_MODEL / "encoder.onnx").exists()
    load.assert_not_called()


def test_preparation_cancels_during_a_file_without_committing_it(files, monkeypatch):
    client, data = files
    cancelled = threading.Event()
    def download(url, cancel):
        class Response(io.BytesIO):
            headers = {}
            def read1(self, size):
                cancelled.set()
                return super().read1(size)
        return Response(data[Path(urlsplit(url).path).name])
    fetch = Mock(side_effect=download)
    monkeypatch.setattr(model_updates, "_open_model", fetch)
    with pytest.raises(voice.VoiceError, match="Cancelled"):
        client.prepare_model(voice.SHERPA_MODEL, cancel_event=cancelled)
    assert fetch.call_count == 1 and not client.model_ready(voice.SHERPA_MODEL)
    assert not list((client.cache_dir / voice.SHERPA_MODEL).glob("*.part"))


def test_model_load_is_lazy_local_cpu_single_thread_and_switch_releases_models(files, monkeypatch):
    client, data = files
    path = client.cache_dir / voice.SHERPA_MODEL
    path.mkdir(parents=True)
    for name, raw in data.items():
        (path / name).write_bytes(raw)
    build = Mock(return_value=object())
    monkeypatch.setitem(sys.modules, "sherpa_onnx", SimpleNamespace(OnlineRecognizer=SimpleNamespace(from_transducer=build)))
    client._model = object()
    model = client._load_sherpa()
    assert client._load_sherpa() is model and build.call_count == 1
    assert client._model is None
    assert build.call_args.kwargs["num_threads"] == 1
    assert build.call_args.kwargs["provider"] == "cpu"
    assert build.call_args.kwargs["decoding_method"] == "greedy_search"
    client.unload_models("google")
    assert client._sherpa is None and client._model is None


def test_missing_model_and_english_never_download_or_guess_language(files, monkeypatch):
    client, _ = files
    fetch = Mock()
    monkeypatch.setattr("huggingface_hub.hf_hub_download", fetch)
    with pytest.raises(voice.VoiceError, match="missing"):
        client._load_sherpa()
    with pytest.raises(voice.VoiceError, match="Bangla only"):
        client.transcribe(b"\x00\x10" * 16000, 16000, "en-US", "sherpa")
    fetch.assert_not_called()


def test_stream_keeps_preview_separate_and_drains_final_samples_after_recorder_stops(tmp_path):
    client = voice.Recognizer(tmp_path)
    first = np.full(1600, 4096, dtype=np.int16).tobytes()
    full = first + np.full(800, 8192, dtype=np.int16).tobytes()
    fed = []
    class Stream:
        def accept_waveform(self, rate, samples):
            assert rate == 16000
            fed.append(samples.copy())
        def input_finished(self):
            pass
    engine = SimpleNamespace(create_stream=Stream, is_ready=lambda _: False,
                             get_result=lambda _: "আমি" if len(fed) == 1 else "আমি বাংলায় লিখি")
    client._sherpa = engine
    client._load_sherpa = lambda: engine
    class Recorder:
        def read_since(self, frame):
            if frame == 0:
                return first, 16000, 1600
            session.finish(full, 16000)
            return b"", 16000, 0  # stop() already cleared the capture buffer.
    session = voice.SherpaSession(client, Recorder(), threading.Event())
    previews = []
    assert session.run(previews.append) == "আমি বাংলায় লিখি"
    assert any(x == "Live preview: আমি" for x in previews)
    decoded = np.concatenate(fed[:-1])
    assert np.allclose(decoded, np.frombuffer(full, dtype=np.int16) / 32768)
    assert len(fed[-1]) == 8000 and not fed[-1].any()


def test_stream_cancellation_interrupts_decode_and_never_returns_text(tmp_path):
    client, cancelled = voice.Recognizer(tmp_path), threading.Event()
    stream = SimpleNamespace(accept_waveform=lambda *args: None, input_finished=lambda: None)
    engine = SimpleNamespace(create_stream=lambda: stream, is_ready=lambda _: True,
                             decode_stream=lambda _: cancelled.set())
    client._load_sherpa = lambda: engine
    session = voice.SherpaSession(client, None, cancelled)
    session.finish(b"\x00\x10" * 16000, 16000)
    with pytest.raises(voice.VoiceError, match="Cancelled"):
        session.run()


@pytest.mark.parametrize("pcm,rate,message", [(b"\0\0" * 16000, 16000, "silent"),
                                             (b"\x00\x10", 16000, "too short"),
                                             (b"\x00\x10" * 16000, 0, "sample rate")],
                         ids=["silent", "short", "invalid-rate"])
def test_stream_final_audio_validation_prevents_invalid_or_silent_delivery(tmp_path, pcm, rate, message):
    client = voice.Recognizer(tmp_path)
    client._load_sherpa = lambda: SimpleNamespace(create_stream=lambda: object())
    session = voice.SherpaSession(client, None, threading.Event())
    session.finish(pcm, rate)
    with pytest.raises(voice.VoiceError, match=message):
        session.run()
