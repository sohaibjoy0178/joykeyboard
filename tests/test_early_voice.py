import threading
import time
from unittest.mock import patch

import pytest

import voice

PCM = b"\x00\x10" * 16000


def pending(client, cancelled):
    result = voice.EarlyRecognition(client, PCM, 16000, "bn-BD", cancelled)
    result.text = "সম্পূর্ণ বাংলা"
    result.ready.set()
    return result


def test_only_one_early_request_can_be_in_flight(tmp_path):
    client, cancelled = voice.Recognizer(tmp_path), threading.Event()
    entered, release = threading.Event(), threading.Event()
    def recognize(*args, **kwargs):
        entered.set()
        assert release.wait(3)
        return "সম্পূর্ণ বাংলা"
    with patch.object(voice.sr.Recognizer, "recognize_google", side_effect=recognize):
        worker = client.start_early(PCM, 16000, "bn-BD", cancelled)
        try:
            assert entered.wait(3)
            assert client.start_early(PCM, 16000, "bn-BD", cancelled) is None
            assert not worker.ready.is_set()
        finally:
            release.set()
            worker.join(3)
    assert not worker.is_alive() and worker.ready.is_set()
    assert worker.text == "সম্পূর্ণ বাংলা" and worker.error is None
    assert client._early is None


def test_finished_phrase_reuses_result_without_second_upload(tmp_path):
    client, cancelled = voice.Recognizer(tmp_path), threading.Event()
    early = pending(client, cancelled)
    with patch.object(voice, "_speech_chunks", return_value=[]), patch.object(
        voice.sr.Recognizer, "recognize_google"
    ) as upload:
        text = client.transcribe(PCM + b"\0\0" * 16000, 16000, "bn-BD", "google",
                                 cancel_event=cancelled, early=early)
    assert text == early.text
    upload.assert_not_called()


def test_resumed_speech_after_snapshot_forces_complete_recording_upload(tmp_path):
    client, cancelled = voice.Recognizer(tmp_path), threading.Event()
    early = pending(client, cancelled)
    full = PCM * 2
    with patch.object(voice, "_speech_chunks", return_value=[{"end": 24000}]), patch.object(
        voice.sr.Recognizer, "recognize_google", return_value="পুরো বাক্য নতুন কথা"
    ) as upload:
        text = client.transcribe(full, 16000, "bn-BD", "google", cancel_event=cancelled, early=early)
    assert text == "পুরো বাক্য নতুন কথা"
    assert upload.call_args.args[0].frame_data == full


@pytest.mark.parametrize("kind", ["rate", "language", "cancel_event", "prefix", "detector_failure"])
def test_incompatible_or_unverifiable_snapshot_uses_normal_recognition(tmp_path, kind):
    client, cancelled = voice.Recognizer(tmp_path), threading.Event()
    early = pending(client, cancelled)
    rate, language, pcm = 16000, "bn-BD", PCM + b"\0\0" * 16000
    if kind == "rate":
        rate = 48000
    elif kind == "language":
        language = "en-US"
    elif kind == "cancel_event":
        cancelled = threading.Event()
    elif kind == "prefix":
        pcm = b"\x00\x20" * 16000
    with patch.object(voice, "_speech_chunks", side_effect=RuntimeError("no detector")), patch.object(
        voice.sr.Recognizer, "recognize_google", return_value="complete"
    ) as upload:
        assert client.transcribe(pcm, rate, language, "google", cancel_event=cancelled, early=early) == "complete"
    upload.assert_called_once()


def test_early_failure_is_reported_without_repeating_same_request(tmp_path):
    client, cancelled = voice.Recognizer(tmp_path), threading.Event()
    early = pending(client, cancelled)
    early.error = voice.VoiceError("Google speech is unavailable.")
    with patch.object(voice.sr.Recognizer, "recognize_google") as upload, pytest.raises(
        voice.VoiceError, match="unavailable"
    ):
        client.transcribe(PCM, 16000, "bn-BD", "google", cancel_event=cancelled, early=early)
    upload.assert_not_called()


def test_cancel_interrupts_waiting_for_early_network_result(tmp_path):
    client, cancelled = voice.Recognizer(tmp_path), threading.Event()
    early = pending(client, cancelled)
    early.ready.clear()
    timer = threading.Timer(0.05, cancelled.set)
    timer.start()
    started = time.monotonic()
    try:
        with pytest.raises(voice.VoiceError, match="Cancelled"):
            client.transcribe(PCM, 16000, "bn-BD", "google", cancel_event=cancelled, early=early)
    finally:
        timer.join()
    assert time.monotonic() - started < 1


def test_early_worker_keeps_failure_and_releases_busy_slot(tmp_path):
    client = voice.Recognizer(tmp_path)
    with patch.object(client, "transcribe", side_effect=voice.VoiceError("network")):
        worker = client.start_early(PCM, 16000, "bn-BD", threading.Event())
        worker.join(3)
    assert worker.ready.is_set() and str(worker.error) == "network" and client._early is None


def test_thread_start_failure_leaves_ordinary_recognition_available(tmp_path):
    client = voice.Recognizer(tmp_path)
    with patch.object(voice.EarlyRecognition, "start", side_effect=RuntimeError("no thread")):
        assert client.start_early(PCM, 16000, "bn-BD", threading.Event()) is None
    assert client._early is None


def test_cancelled_early_worker_cannot_return_late_text_or_build_up_workers(tmp_path):
    client, cancelled = voice.Recognizer(tmp_path), threading.Event()
    entered, release = threading.Event(), threading.Event()
    def recognize(*args, **kwargs):
        entered.set()
        assert release.wait(3)
        return "late text"
    with patch.object(voice.sr.Recognizer, "recognize_google", side_effect=recognize):
        worker = client.start_early(PCM, 16000, "bn-BD", cancelled)
        try:
            assert entered.wait(3)
            cancelled.set()
            assert client.start_early(PCM, 16000, "bn-BD", threading.Event()) is None
        finally:
            release.set()
            worker.join(3)
    assert worker.ready.is_set() and worker.text == ""
    assert isinstance(worker.error, voice.VoiceError) and str(worker.error) == "Cancelled."
    assert client._early is None
