import base64
import hashlib
import io
import json
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import model_updates as models
import voice


@pytest.fixture
def installed(tmp_path, monkeypatch):
    data = {name: (name + "-old").encode() for name in voice.SHERPA_FILES}
    monkeypatch.setattr(voice, "SHERPA_FILES", {
        name: (len(raw), hashlib.sha256(raw).hexdigest()) for name, raw in data.items()
    })
    client = voice.Recognizer(tmp_path / "cache", tmp_path / "no-bundle")
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
    def download(repo, name, **kwargs):
        assert repo == voice.SHERPA_REPO and kwargs["revision"] == "b" * 40 and kwargs["token"] is False
        path = Path(kwargs["local_dir"]) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((name + "-old").encode())
        return str(path)
    monkeypatch.setattr("huggingface_hub.hf_hub_download", download)
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
