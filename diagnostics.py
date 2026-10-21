"""Explicit, non-recording speech checks for source and packaged builds."""

import hashlib
import json
import platform
import sys
import threading
import time
import wave
from datetime import UTC, datetime
from pathlib import Path

from core import data_directory
from voice import PauseMonitor, Recognizer, Recorder, VoiceError


def pause_capture(pcm: bytes, rate: int, on_early=None) -> tuple[bytes, dict]:
    """Feed a public fixture with trailing silence through the actual local detector."""
    padded = pcm + b"\0\0" * (rate * 2)
    class Feed:
        size = 0
        def tail(self):
            return padded[max(0, self.size - rate * 16):self.size], rate, self.size // 2
    feed = Feed()
    monitor = PauseMonitor(feed)
    attempted = False
    step = (rate // 4) * 2
    for size in range(step, min(len(padded), rate * 120) + 1, step):
        feed.size = size
        monitor.check()
        if monitor.reason == "pause":
            return padded[:size], {"auto_pause_detected": True, "speech_end_seconds": round(monitor._last_end, 3),
                                   "capture_end_seconds": round(size / (rate * 2), 3)}
        if monitor.reason == "no_speech":
            raise VoiceError("No speech detected in pause test fixture.")
        if on_early is not None and monitor.early_ready and not attempted:
            attempted = True
            on_early(padded[:size])
    raise VoiceError("No completed speech pause detected in test fixture.")


def check_audio(path: Path, engine: str, output: Path, language="en-US", model="base", auto_pause=False) -> dict:
    path, output = Path(path), Path(output)
    if path.resolve() == output.resolve():
        raise VoiceError("Diagnostic output must differ from the input audio file.")
    if engine not in ("google", "offline"):
        raise VoiceError("Choose google or offline for the diagnostic engine.")
    try:
        if path.stat().st_size > 30_000_000:
            raise VoiceError("Diagnostic WAV must be smaller than 30 MB.")
        with wave.open(str(path), "rb") as wav:
            if wav.getnchannels() != 1 or wav.getsampwidth() != 2 or wav.getcomptype() != "NONE":
                raise VoiceError("Diagnostic input must be an uncompressed mono PCM16 WAV.")
            rate, frames = wav.getframerate(), wav.getnframes()
            if not 8000 <= rate <= 192000 or frames > rate * Recorder.MAX_SECONDS:
                raise VoiceError("Diagnostic WAV needs an 8–192 kHz rate and duration under 65 seconds.")
            pcm = wav.readframes(frames)
            if len(pcm) != frames * 2:
                raise VoiceError("Diagnostic WAV is truncated. Choose a complete recording.")
    except (OSError, EOFError, wave.Error) as exc:
        raise VoiceError("Cannot read diagnostic audio. Choose a valid mono PCM16 WAV.") from exc
    started = time.perf_counter()
    pause_result = {}
    recognizer = Recognizer(data_directory() / "models")
    cancelled = threading.Event()
    early = None
    def begin_early(audio):
        nonlocal early
        early = recognizer.start_early(audio, rate, language, cancelled)
    if auto_pause:
        pcm, pause_result = pause_capture(pcm, rate, begin_early if engine == "google" else None)
        frames = len(pcm) // 2
    transcript = recognizer.transcribe(
        pcm, rate, language, engine, model=model, cancel_event=cancelled, early=early,
    )
    result = {
        "engine": engine,
        "language": language,
        "model": model if engine == "offline" else None,
        "transcript": transcript,
        "seconds": round(time.perf_counter() - started, 3),
        "sample_rate": rate,
        "channels": 1,
        "sample_width_bytes": 2,
        "audio_seconds": round(frames / rate, 3),
        "early_recognition_started": early is not None,
        "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
        "input_path": str(path.resolve()),
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "packaged": bool(getattr(sys, "frozen", False)),
        "python": platform.python_version(),
        "machine": platform.machine(),
        **pause_result,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result
