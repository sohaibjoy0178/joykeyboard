"""Verified Sherpa model channel; staged files activate only between voice sessions."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from pathlib import Path

import numpy as np

import updates
import voice
from core import APP_VERSION

CHANNEL_URL = "https://api.github.com/repos/sohaibjoy0178/joykeyboard/contents/assets/models/sherpa-channel.json?ref=main"
MAX_MANIFEST = 16_384


def baseline_manifest():
    return {"schema": 1, "version": 1, "repo": voice.SHERPA_REPO,
            "revision": voice.SHERPA_REVISION, "minimum_app": "0.4.14",
            "files": {name: {"size": size, "sha256": digest}
                      for name, (size, digest) in voice.SHERPA_FILES.items()}}


def parse_manifest(value):
    if not isinstance(value, dict) or type(value.get("schema")) is not int or value["schema"] != 1:
        raise voice.VoiceError("Unsupported Sherpa update channel.")
    if type(value.get("version")) is not int or not 1 <= value["version"] <= 1_000_000:
        raise voice.VoiceError("Invalid Sherpa model version.")
    if value.get("repo") != voice.SHERPA_REPO or not isinstance(value.get("revision"), str) or not re.fullmatch(r"[0-9a-f]{40}", value["revision"]):
        raise voice.VoiceError("Untrusted Sherpa model source or revision.")
    updates.version_tuple(value.get("minimum_app"))
    files = value.get("files")
    if not isinstance(files, dict) or set(files) != set(voice.SHERPA_FILES):
        raise voice.VoiceError("Sherpa update has unexpected model files.")
    for item in files.values():
        if not isinstance(item, dict) or type(item.get("size")) is not int or not 1 <= item["size"] <= 256 * 1024**2:
            raise voice.VoiceError("Invalid Sherpa model size.")
        if not isinstance(item.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
            raise voice.VoiceError("Sherpa model has no valid SHA-256.")
    if sum(item["size"] for item in files.values()) > 384 * 1024**2:
        raise voice.VoiceError("Sherpa model update is too large.")
    return {key: value[key] for key in ("schema", "version", "repo", "revision", "minimum_app", "files")}


def files_ready(path, manifest):
    return all((path / name).is_file() and (path / name).stat().st_size == item["size"]
               for name, item in manifest["files"].items())


def candidate_path(cache, manifest):
    return Path(cache) / "sherpa-updates" / f"{manifest['version']}-{manifest['revision']}"


def active_model(cache):
    cache = Path(cache)
    pointer = cache / "sherpa-active.json"
    try:
        if pointer.stat().st_size > MAX_MANIFEST:
            raise ValueError("Model pointer is too large.")
        manifest = parse_manifest(json.loads(pointer.read_text(encoding="utf-8")))
        path = candidate_path(cache, manifest)
        if updates.version_tuple(manifest["minimum_app"]) <= updates.version_tuple(APP_VERSION) and files_ready(path, manifest):
            return path, manifest
    except (OSError, ValueError, voice.VoiceError, updates.UpdateError):
        pass
    return cache / voice.SHERPA_MODEL, baseline_manifest()


def download_model(path, manifest, cancel=None, status=None, force=False):
    from huggingface_hub import hf_hub_download

    for name, item in manifest["files"].items():
        voice.Recognizer._check_cancel(cancel)
        if status:
            status(f"Preparing Sherpa Bangla: {name}.")
        downloaded = path / name
        if force or not downloaded.is_file():
            # shortcut: cancellation applies between file downloads; use chunked transport if needed.
            downloaded = Path(hf_hub_download(manifest["repo"], name, revision=manifest["revision"],
                                             local_dir=str(path), token=False, force_download=force))
        if downloaded.resolve() != (path / name).resolve():
            raise voice.VoiceError("Sherpa download returned an unexpected file location.")
        with downloaded.open("rb") as stream:
            valid = downloaded.stat().st_size == item["size"] and hashlib.file_digest(stream, "sha256").hexdigest() == item["sha256"]
        if not valid:
            downloaded.unlink()
            raise voice.VoiceError("Sherpa model verification failed. Retry the download.")
    voice.Recognizer._check_cancel(cancel)


def check_channel():
    with updates._open(CHANNEL_URL) as response:
        body = response.read(64_001)
    if len(body) > 64_000:
        raise voice.VoiceError("Sherpa update response is too large.")
    envelope = json.loads(body)
    if not isinstance(envelope, dict) or envelope.get("encoding") != "base64" or not isinstance(envelope.get("content"), str):
        raise voice.VoiceError("Invalid Sherpa update response.")
    raw = base64.b64decode("".join(envelope["content"].split()), validate=True)
    if len(raw) > MAX_MANIFEST:
        raise voice.VoiceError("Sherpa update manifest is too large.")
    return parse_manifest(json.loads(raw))


def prepare_update(client, cancel, status=None):
    voice.Recognizer._check_cancel(cancel)
    if not client.model_ready(voice.SHERPA_MODEL):
        return None  # Never download a first model without the user's explicit Prepare action.
    manifest = check_channel()
    _, current = active_model(client.cache_dir)
    if manifest["version"] <= current["version"]:
        return None
    if updates.version_tuple(manifest["minimum_app"]) > updates.version_tuple(APP_VERSION):
        raise voice.VoiceError(f"New Sherpa model needs JoyKeyboard {manifest['minimum_app']}. Install the app update first.")
    path = candidate_path(client.cache_dir, manifest)
    download_model(path, manifest, cancel, status)
    if status:
        status("Checking downloaded Sherpa model compatibility…")
    engine = voice.Recognizer.build_sherpa(path)
    stream = engine.create_stream()
    stream.accept_waveform(16000, np.zeros(16000, dtype=np.float32))
    stream.input_finished()
    while engine.is_ready(stream):
        voice.Recognizer._check_cancel(cancel)
        engine.decode_stream(stream)
    engine.get_result(stream)
    del stream, engine
    voice.Recognizer._check_cancel(cancel)
    return manifest


def activate_update(client, manifest):
    manifest = parse_manifest(manifest)
    _, current = active_model(client.cache_dir)
    if manifest["version"] <= current["version"]:
        return
    if updates.version_tuple(manifest["minimum_app"]) > updates.version_tuple(APP_VERSION):
        raise voice.VoiceError("Install the app update before activating this Sherpa model.")
    if not files_ready(candidate_path(client.cache_dir, manifest), manifest):
        raise voice.VoiceError("Downloaded Sherpa update is incomplete. Current model kept.")
    pointer = client.cache_dir / "sherpa-active.json"
    temporary = pointer.with_suffix(".tmp")
    try:
        temporary.write_text(json.dumps(manifest), encoding="utf-8")
        os.replace(temporary, pointer)
    finally:
        temporary.unlink(missing_ok=True)
    client._sherpa = None
    # shortcut: old model files are retained for recovery; add bounded cleanup if models change often.
