import base64
import hashlib
import io
import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import urlsplit
from urllib.request import Request

import pytest

import model_updates as models
import voice


@pytest.fixture
def installed(tmp_path, monkeypatch):
    data = {name: (name + "-old").encode() for name in voice.SHERPA_FILES}
    monkeypatch.setattr(voice, "SHERPA_FILES", {
        name: (len(raw), hashlib.sha256(raw).hexdigest()) for name, raw in data.items()
    })
    client = voice.Recognizer(tmp_path / "cache")
    path = client.cache_dir / voice.SHERPA_MODEL
    path.mkdir(parents=True)
    for name, raw in data.items():
        (path / name).write_bytes(raw)
    return client


def newer():
    manifest = models.baseline_manifest()
    manifest.update(version=2, revision="b" * 40)
    return manifest


def stage(client, manifest):
    path = models.candidate_path(client.cache_dir, manifest)
    path.mkdir(parents=True, exist_ok=True)
    for name in manifest["files"]:
        (path / name).write_bytes((name + "-old").encode())
    return path


def test_no_first_model_download_or_network_without_explicit_preparation(tmp_path, monkeypatch):
    client = voice.Recognizer(tmp_path)
    check = Mock()
    monkeypatch.setattr(models, "check_channel", check)
    assert models.prepare_update(client, threading.Event()) is None
    check.assert_not_called()


@pytest.mark.parametrize("change", [
    {"schema": True}, {"version": True}, {"version": 0}, {"version": 1_000_001},
    {"repo": "attacker/model"}, {"revision": "../escape"}, {"minimum_app": "latest"},
    {"files": {"../model.onnx": {"size": 1, "sha256": "f" * 64}}},
], ids=["schema", "boolean-version", "zero", "huge-version", "repo", "revision", "app-version", "path"])
def test_channel_rejects_untrusted_or_unsupported_manifest(change):
    manifest = models.baseline_manifest()
    manifest.update(change)
    with pytest.raises((voice.VoiceError, models.updates.UpdateError)):
        models.parse_manifest(manifest)


@pytest.mark.parametrize("change", [{"size": True}, {"size": 0}, {"size": 257 * 1024**2}, {"sha256": "bad"}],
                         ids=["boolean-size", "empty-file", "oversize", "hash"])
def test_channel_rejects_invalid_file_metadata(change):
    manifest = models.baseline_manifest()
    manifest["files"]["encoder.onnx"].update(change)
    with pytest.raises(voice.VoiceError):
        models.parse_manifest(manifest)


def test_bounded_github_channel_uses_fixed_public_url(monkeypatch):
    manifest = models.baseline_manifest()
    envelope = {"encoding": "base64", "content": base64.encodebytes(json.dumps(manifest).encode()).decode()}
    fetch = Mock(return_value=io.BytesIO(json.dumps(envelope).encode()))
    monkeypatch.setattr(models.updates, "_open", fetch)
    assert models.check_channel() == manifest
    fetch.assert_called_once_with(models.CHANNEL_URL)
    for raw in (b"x" * 64_001, b'{}', json.dumps({"encoding": "base64", "content": "!"}).encode()):
        fetch.return_value = io.BytesIO(raw)
        with pytest.raises((voice.VoiceError, ValueError)):
            models.check_channel()


def test_same_older_or_incompatible_channel_never_downloads(installed, monkeypatch):
    download = Mock()
    monkeypatch.setattr(models, "download_model", download)
    monkeypatch.setattr(models, "check_channel", models.baseline_manifest)
    assert models.prepare_update(installed, threading.Event()) is None
    manifest = newer()
    manifest["minimum_app"] = "99.0.0"
    monkeypatch.setattr(models, "check_channel", lambda: manifest)
    with pytest.raises(voice.VoiceError, match="Install the app update"):
        models.prepare_update(installed, threading.Event())
    download.assert_not_called()


def test_verified_download_native_validation_atomic_activation_and_restart(installed, monkeypatch):
    manifest = newer()
    original = installed._model_path(voice.SHERPA_MODEL)
    monkeypatch.setattr(models, "check_channel", lambda: manifest)
    def download(url, cancel):
        assert f"/{voice.SHERPA_REPO}/resolve/{'b' * 40}/" in url
        name = Path(urlsplit(url).path).name
        response = io.BytesIO((name + "-old").encode())
        response.headers = {}
        return response
    monkeypatch.setattr(models, "_open_model", download)
    stream = SimpleNamespace(accept_waveform=Mock(), input_finished=Mock())
    engine = SimpleNamespace(create_stream=lambda: stream, is_ready=lambda _: False, get_result=lambda _: "")
    build = Mock(return_value=engine)
    monkeypatch.setattr(voice.Recognizer, "build_sherpa", build)
    loaded = installed._sherpa = object()
    assert models.prepare_update(installed, threading.Event()) == manifest
    assert installed._model_path(voice.SHERPA_MODEL) == original and installed._sherpa is loaded
    assert build.call_args.args[0] == models.candidate_path(installed.cache_dir, manifest)
    stream.input_finished.assert_called_once()
    models.activate_update(installed, manifest)
    assert installed._sherpa is None and installed.model_ready(voice.SHERPA_MODEL)
    restarted = voice.Recognizer(installed.cache_dir)
    assert restarted._model_path(voice.SHERPA_MODEL) == models.candidate_path(installed.cache_dir, manifest)
    assert original.is_dir() and not (installed.cache_dir / "sherpa-active.tmp").exists()
    monkeypatch.setattr(models, "check_channel", models.baseline_manifest)
    assert models.prepare_update(restarted, threading.Event()) is None  # No rollback to an older channel.


@pytest.mark.parametrize("failure", ["hash", "native", "cancel"], ids=["hash", "native", "cancel"])
def test_bad_cancelled_or_incompatible_candidate_preserves_active_model(installed, monkeypatch, failure):
    manifest = newer()
    original = installed._model_path(voice.SHERPA_MODEL)
    path = stage(installed, manifest)
    cancel = threading.Event()
    if failure == "hash":
        (path / "encoder.onnx").write_bytes(b"corrupt")
    elif failure == "cancel":
        cancel.set()
    monkeypatch.setattr(models, "check_channel", lambda: manifest)
    monkeypatch.setattr(voice.Recognizer, "build_sherpa", Mock(side_effect=RuntimeError("incompatible model")))
    with pytest.raises((voice.VoiceError, RuntimeError)):
        models.prepare_update(installed, cancel)
    assert installed._model_path(voice.SHERPA_MODEL) == original
    assert not (installed.cache_dir / "sherpa-active.json").exists()


def test_atomic_pointer_failure_and_incomplete_candidate_keep_existing_model(installed, monkeypatch):
    manifest = newer()
    original = installed._model_path(voice.SHERPA_MODEL)
    with pytest.raises(voice.VoiceError, match="incomplete"):
        models.activate_update(installed, manifest)
    stage(installed, manifest)
    monkeypatch.setattr(models.os, "replace", Mock(side_effect=OSError("disk full")))
    with pytest.raises(OSError, match="disk full"):
        models.activate_update(installed, manifest)
    assert installed._model_path(voice.SHERPA_MODEL) == original
    assert not (installed.cache_dir / "sherpa-active.tmp").exists()


def test_damaged_pointer_or_missing_updated_files_falls_back_to_baseline(installed):
    pointer = installed.cache_dir / "sherpa-active.json"
    for raw in ("invalid json", "x" * (models.MAX_MANIFEST + 1), json.dumps(newer())):
        pointer.write_text(raw, encoding="utf-8")
        assert installed._model_path(voice.SHERPA_MODEL) == installed.cache_dir / voice.SHERPA_MODEL
        assert installed.model_ready(voice.SHERPA_MODEL)


def test_published_channel_is_valid_and_does_not_redefine_baseline_version():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "assets/models/sherpa-channel.json").read_text(encoding="utf-8"))
    models.parse_manifest(manifest)
    if manifest["version"] == 1:
        assert manifest == models.baseline_manifest()


def test_two_download_attempts_without_console_never_use_console_progress(installed, monkeypatch):
    manifest = models.baseline_manifest()
    path = installed.cache_dir / voice.SHERPA_MODEL
    def opened(url, cancel):
        name = Path(urlsplit(url).path).name
        response = io.BytesIO((name + "-old").encode())
        response.headers = {}
        return response
    monkeypatch.setattr(models, "_open_model", opened)
    monkeypatch.setattr(sys, "stderr", None)
    monkeypatch.setattr(sys, "stdout", None)
    progress = []
    for _ in range(2):
        models.download_model(path, manifest, status=progress.append, force=True)
    assert models.files_ready(path, manifest) and any("100%" in item for item in progress)
    assert not list(path.glob("*.part"))


@pytest.mark.parametrize("url", ["http://huggingface.co/file", "https://huggingface.co.evil.test/file",
                                     "https://evil.test/file", "https://user@huggingface.co/file",
                                     "https://huggingface.co:444/file", "file:///tmp/model"],
                         ids=["http", "suffix", "foreign", "credentials", "port", "file"])
def test_model_redirect_rejects_foreign_or_insecure_hosts(url):
    redirect = models.ModelRedirects(None)
    with pytest.raises(voice.VoiceError, match="untrusted"):
        redirect.redirect_request(Request("https://huggingface.co/file"), None, 302, "found", {}, url)


def test_model_connection_timeout_no_credentials_and_cancelled_redirect(monkeypatch):
    opener = Mock()
    monkeypatch.setattr(models, "build_opener", Mock(return_value=opener))
    models._open_model("https://huggingface.co/file", None)
    request = opener.open.call_args.args[0]
    assert request.get_header("Authorization") is None
    assert request.get_header("Accept-encoding") == "identity"
    assert opener.open.call_args.kwargs["timeout"] == 5
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(voice.VoiceError, match="Cancelled"):
        models.ModelRedirects(cancel).redirect_request(request, None, 302, "found", {}, "https://cdn-lfs.huggingface.co/file")


@pytest.mark.parametrize("kind", ["declared-size", "invalid-length", "truncated", "oversized", "wrong-hash"],
                         ids=["declared-size", "invalid-length", "truncated", "oversized", "wrong-hash"])
def test_bad_stream_never_replaces_existing_valid_file(installed, monkeypatch, kind):
    manifest = models.baseline_manifest()
    path = installed.cache_dir / voice.SHERPA_MODEL
    original = (path / "encoder.onnx").read_bytes()
    contents = {"truncated": original[:-1], "oversized": original + b"x", "wrong-hash": b"x" * len(original)}.get(kind, original)
    response = io.BytesIO(contents)
    response.headers = {"Content-Length": "999999" if kind == "declared-size" else "invalid"} if kind in ("declared-size", "invalid-length") else {}
    monkeypatch.setattr(models, "_open_model", Mock(return_value=response))
    with pytest.raises(voice.VoiceError, match="verification failed"):
        models.download_model(path, manifest, force=True)
    assert (path / "encoder.onnx").read_bytes() == original and not list(path.glob("*.part"))


def test_mid_stream_cancel_closes_response_and_cleans_partial(installed, monkeypatch):
    manifest = models.baseline_manifest()
    raw = b"a" * 200_000
    manifest["files"]["encoder.onnx"] = {"size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    response = io.BytesIO(raw)
    response.headers = {}
    monkeypatch.setattr(models, "_open_model", Mock(return_value=response))
    cancel = threading.Event()
    def progress(message):
        if "%" in message:
            cancel.set()
    path = installed.cache_dir / "candidate"
    with pytest.raises(voice.VoiceError, match="Cancelled"):
        models.download_model(path, manifest, cancel, progress)
    assert response.closed and not (path / "encoder.onnx").exists() and not list(path.glob("*.part"))


def test_stalled_stream_times_out_cleans_partial_and_allows_retry(installed, monkeypatch):
    manifest = models.baseline_manifest()
    path = installed.cache_dir / "candidate"
    class Stalled(io.BytesIO):
        headers = {}
        def read1(self, size):
            raise TimeoutError("server stopped responding")
    monkeypatch.setattr(models, "_open_model", Mock(return_value=Stalled()))
    with pytest.raises(voice.VoiceError, match="timed out"):
        models.download_model(path, manifest)
    assert not list(path.glob("*.part"))
    def opened(url, cancel):
        name = Path(urlsplit(url).path).name
        response = io.BytesIO((name + "-old").encode())
        response.headers = {}
        return response
    monkeypatch.setattr(models, "_open_model", opened)
    models.download_model(path, manifest)
    assert models.files_ready(path, manifest)
