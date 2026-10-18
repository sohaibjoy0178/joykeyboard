"""Microphone capture and the two explicitly selected speech engines."""

from __future__ import annotations

import io
import os
import subprocess
import sys
import threading
import wave
from collections.abc import Callable
from pathlib import Path

import numpy as np
import sounddevice as sd
import speech_recognition as sr

Status = Callable[[str], None] | None
MODELS = ("tiny", "base", "small")


class VoiceError(RuntimeError):
    """An actionable recording or recognition error safe to show in the UI."""


class WebAudio(sr.AudioData):
    def get_flac_data(self, convert_rate=None, convert_width=None):
        # Windowed Windows apps can have invalid inherited stderr handles; own all three pipes.
        result = subprocess.run(
            [sr.get_flac_converter(), "--stdout", "--totally-silent", "--best", "-"],
            input=self.get_wav_data(convert_rate, convert_width),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return result.stdout


def list_microphones() -> list[tuple[int, str]]:
    try:
        return [
            (index, device["name"])
            for index, device in enumerate(sd.query_devices())
            if device["max_input_channels"] > 0
        ]
    except Exception as exc:
        raise VoiceError("Cannot list microphones. Check Windows sound settings.") from exc


class Recorder:
    MAX_SECONDS = 65

    def __init__(self, device: int | None = None):
        self.device = device
        self._lock = threading.Lock()
        self._lifecycle = threading.Lock()
        self._stream = None
        self._recording = False
        self._buffer = bytearray()
        self._size = 0
        self._sample_rate = 16000
        self._level = 0.0
        self._error = None

    @property
    def level(self) -> float:
        with self._lock:
            return self._level

    @property
    def error(self) -> str | None:
        with self._lock:
            return self._error

    def tail(self, seconds=8) -> tuple[bytes, int, int]:
        with self._lock:
            start = max(0, self._size - int(seconds * self._sample_rate) * 2)
            return bytes(self._buffer[start:self._size]), self._sample_rate, self._size // 2

    def start(self) -> None:
        with self._lifecycle:
            if self._stream is not None:
                raise VoiceError("Microphone is already recording.")
            try:
                info = sd.query_devices(self.device, "input")
                rate = int(info["default_samplerate"])
                if not 8000 <= rate <= 192000:
                    raise VoiceError("Microphone reports an unsupported sample rate.")
                with self._lock:
                    self._sample_rate = rate
                    self._buffer = bytearray(rate * 2 * self.MAX_SECONDS)
                    self._size = 0
                    self._level = 0.0
                    self._error = None
                    self._recording = True
                self._stream = sd.RawInputStream(
                    samplerate=rate,
                    device=self.device,
                    channels=1,
                    dtype="int16",
                    callback=self._callback,
                )
                self._stream.start()
            except Exception as exc:
                try:
                    self._close(abort=True)
                except sd.PortAudioError:
                    self._error = "Microphone disconnected while opening."
                if isinstance(exc, VoiceError):
                    raise
                raise VoiceError(
                    "Cannot open microphone. Check its connection, Windows microphone "
                    "privacy permission, and selected input device."
                ) from exc

    def _callback(self, indata, frames, timing, status) -> None:
        with self._lock:
            if not self._recording:
                raise sd.CallbackAbort
            if status:
                self._error = "Microphone lost audio. Close other audio apps and try again."
                self._recording = False
                raise sd.CallbackAbort
            remaining = len(self._buffer) - self._size
            count = min(len(indata), remaining)
            count -= count % 2
            self._buffer[self._size : self._size + count] = indata[:count]
            self._size += count
            samples = np.frombuffer(indata, dtype=np.int16)
            if samples.size:
                samples_float = samples.astype(np.float32)
                self._level = min(1.0, float(np.sqrt(np.mean(samples_float**2))) / 8192)
            if self._size == len(self._buffer):
                self._recording = False
                self._error = "Recording reached the 65-second safety limit. Use shorter clips."
                raise sd.CallbackAbort

    def _close(self, abort: bool = False) -> None:
        with self._lock:
            self._recording = False
            self._level = 0.0
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                if abort:
                    stream.abort()
                else:
                    stream.stop()
            finally:
                stream.close()

    def stop(self) -> tuple[bytes, int]:
        with self._lifecycle:
            try:
                self._close()
            except Exception as exc:
                raise VoiceError("Microphone could not stop cleanly. Reconnect it and retry.") from exc
            with self._lock:
                pcm = bytes(self._buffer[: self._size])
                self._buffer = bytearray()
                self._size = 0
                if self._error:
                    raise VoiceError(self._error)
                return pcm, self._sample_rate

    def cancel(self) -> None:
        with self._lifecycle:
            try:
                self._close(abort=True)
            except sd.PortAudioError:
                self._error = "Microphone disconnected while cancelling."
            with self._lock:
                self._buffer = bytearray()
                self._size = 0


class LoopbackRecorder(Recorder):
    """Capture the default speaker through WASAPI on one owned audio thread."""

    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()
        self._ready = threading.Event()
        self._thread = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            raise VoiceError("System audio is already recording.")
        self._stop_event.clear()
        self._ready.clear()
        with self._lock:
            self._sample_rate = 48000
            self._buffer = bytearray(self._sample_rate * 2 * self.MAX_SECONDS)
            self._size = 0
            self._level = 0.0
            self._error = None
            self._recording = True
        self._thread = threading.Thread(target=self._capture, daemon=True, name="JoyKeyboard-loopback")
        self._thread.start()
        if not self._ready.wait(5):
            self._stop_event.set()
            raise VoiceError("System audio did not open. Check the default Windows output device.")
        if self.error:
            raise VoiceError(self.error)

    def _capture(self):
        try:
            import soundcard as sc

            speaker = sc.default_speaker()
            if speaker is None:
                raise VoiceError("No default speaker is available.")
            source = sc.get_microphone(speaker.id, include_loopback=True)
            with source.recorder(samplerate=48000, channels=None, blocksize=2048) as stream:
                self._ready.set()
                while not self._stop_event.is_set():
                    samples = stream.record(numframes=2048)
                    if samples.ndim > 1:
                        samples = samples.mean(axis=1)
                    pcm = (np.clip(samples, -1, 1) * 32767).astype(np.int16).tobytes()
                    try:
                        self._callback(pcm, len(samples), None, False)
                    except sd.CallbackAbort:
                        break
        except Exception:
            with self._lock:
                self._error = "System audio capture failed. Check the default speaker and Windows audio settings."
        finally:
            self._ready.set()

    def _finish_thread(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(2)
            if self._thread.is_alive():
                raise VoiceError("System audio has not stopped yet. Retry after the Windows audio device recovers.")
            self._thread = None

    def stop(self) -> tuple[bytes, int]:
        self._finish_thread()
        return super().stop()

    def cancel(self) -> None:
        self._stop_event.set()
        super().cancel()
        if self._thread:
            self._thread.join(2)


class PauseMonitor(threading.Thread):
    """Local speech detection off the audio/UI threads; never transcribes or uploads."""
    PAUSE_SECONDS = 1.5
    NO_SPEECH_SECONDS = 10

    def __init__(self, recorder):
        super().__init__(daemon=True, name="JoyKeyboard speech pause")
        self.recorder = recorder
        self.reason = None
        self.error = None
        self._stop_event = threading.Event()
        self._last_end = None
        self._processed = 0

    def stop(self):
        self._stop_event.set()

    def check(self):
        from faster_whisper.vad import VadOptions, get_speech_timestamps

        pcm, rate, total = self.recorder.tail()
        if not pcm or total == self._processed or self._stop_event.is_set():
            return
        self._processed = total
        raw = sr.AudioData(pcm, rate, 2).get_raw_data(convert_rate=16000, convert_width=2)
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
        chunks = get_speech_timestamps(samples, VadOptions(
            # Resolve chunk ends promptly; the 1.5-second pause timer is applied below.
            min_speech_duration_ms=120, min_silence_duration_ms=100, speech_pad_ms=0,
        ))
        if self._stop_event.is_set():
            return
        duration = total / rate
        if chunks:
            end = (total - len(pcm) // 2) / rate + chunks[-1]["end"] / 16000
            self._last_end = max(self._last_end or 0, end)
        if self._last_end is not None and duration - self._last_end >= self.PAUSE_SECONDS:
            self.reason = "pause"
        elif self._last_end is None and duration >= self.NO_SPEECH_SECONDS:
            self.reason = "no_speech"

    def run(self):
        try:
            while not self._stop_event.wait(0.25):
                self.check()
                if self.reason:
                    break
        except Exception:
            if not self._stop_event.is_set():
                self.error = "Automatic pause detection is unavailable. Click Finish or press Ctrl+Alt+Space to transcribe."


class Recognizer:
    def __init__(self, cache_dir: Path, bundled_dir: Path | None = None):
        self.cache_dir = Path(cache_dir)
        self.bundled_dir = Path(bundled_dir) if bundled_dir is not None else Path(
            getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
        ) / "assets" / "models"
        self._model = None
        self._model_name = None

    def _model_path(self, model: str) -> Path:
        if model not in MODELS:
            raise VoiceError("Choose a supported offline model: tiny, base, or small.")
        cached = self.cache_dir / model
        if self._complete(cached):
            return cached
        bundled = self.bundled_dir / model
        return bundled if self._complete(bundled) else cached

    @staticmethod
    def _complete(path: Path) -> bool:
        return all((path / name).is_file() for name in ("model.bin", "config.json", "tokenizer.json"))

    def model_ready(self, model: str = "base") -> bool:
        path = self._model_path(model)
        return self._complete(path)

    @staticmethod
    def _check_cancel(cancel_event: threading.Event | None) -> None:
        if cancel_event is not None and cancel_event.is_set():
            raise VoiceError("Cancelled.")

    def _load_model(self, model: str):
        if model != self._model_name or self._model is None:
            from faster_whisper import WhisperModel

            self._model = None
            self._model = WhisperModel(
                str(self._model_path(model)), device="cpu", compute_type="int8",
                local_files_only=True, cpu_threads=max(1, min(2, (os.cpu_count() or 2) // 2)),
            )
            self._model_name = model
        return self._model

    def prepare_model(
        self, model: str = "base", status: Status = None,
        cancel_event: threading.Event | None = None,
        force: bool = False,
    ) -> None:
        path = self._model_path(model)
        self._check_cancel(cancel_event)
        try:
            if force or not self.model_ready(model):
                from faster_whisper.utils import download_model

                if status:
                    status(f"Downloading {model} speech model. This runs only once.")
                path = self.cache_dir / model
                path.mkdir(parents=True, exist_ok=True)
                # shortcut: downloads finish before cancellation applies; add chunk cancellation if needed.
                download_model(model, output_dir=str(path))
                self._model = None
                self._model_name = None
            self._check_cancel(cancel_event)
            if status:
                status("Checking offline speech model…")
            self._load_model(model)
            self._check_cancel(cancel_event)
        except VoiceError:
            raise
        except Exception as exc:
            raise VoiceError(
                "Could not prepare offline model. Check internet, free disk space, "
                "and antivirus permissions, then retry Prepare Model."
            ) from exc

    def transcribe(
        self, pcm: bytes, sample_rate: int, language: str, engine: str,
        model: str = "base", status: Status = None,
        cancel_event: threading.Event | None = None,
    ) -> str:
        self._check_cancel(cancel_event)
        if language not in ("bn-BD", "en-US"):
            raise VoiceError("Choose Bangla or English as the speech language.")
        if engine not in ("google", "offline"):
            raise VoiceError("Choose Google online or offline speech recognition.")
        if not isinstance(sample_rate, int) or not 8000 <= sample_rate <= 192000:
            raise VoiceError("Unsupported audio sample rate. Select another microphone.")
        if not isinstance(pcm, bytes) or len(pcm) % 2:
            raise VoiceError("Recorded audio is invalid. Record again.")
        if len(pcm) < sample_rate // 5:
            raise VoiceError("Recording is too short. Speak for at least a moment.")
        if len(pcm) > sample_rate * 2 * Recorder.MAX_SECONDS:
            raise VoiceError("Recording is too long. Use clips shorter than 65 seconds.")
        samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
        if float(np.sqrt(np.mean(samples ** 2))) < 12:
            raise VoiceError("Recording is silent. Check microphone input and speak closer to it.")
        if status:
            status("Recognizing speech…")
        try:
            if engine == "google":
                recognizer = sr.Recognizer()
                recognizer.operation_timeout = 30
                # Experimental service's built-in generic key, never an extracted app credential.
                text = recognizer.recognize_google(
                    WebAudio(pcm, sample_rate, 2), language=language,
                    endpoint="https://www.google.com/speech-api/v2/recognize",
                )
            else:
                if not self.model_ready(model):
                    raise VoiceError("Offline model is missing. Click Prepare Model first.")
                audio = io.BytesIO()
                with wave.open(audio, "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(sample_rate)
                    wav.writeframes(pcm)
                audio.seek(0)
                segments, _ = self._load_model(model).transcribe(
                    audio, language=language.split("-")[0], beam_size=5,
                    vad_filter=True, condition_on_previous_text=False,
                )
                parts = []
                for segment in segments:
                    self._check_cancel(cancel_event)
                    parts.append(segment.text.strip())
                text = " ".join(parts)
            self._check_cancel(cancel_event)
            if not text.strip():
                raise VoiceError("No speech was understood. Move closer to the microphone and retry.")
            return text.strip()
        except VoiceError:
            raise
        except sr.UnknownValueError as exc:
            raise VoiceError("Speech was not understood. Check language and speak clearly.") from exc
        except sr.RequestError as exc:
            raise VoiceError(
                "Google speech is unavailable. Check internet or switch to the prepared offline model."
            ) from exc
        except Exception as exc:
            if engine == "offline":
                message = "Offline speech failed. Retry Prepare Model or select a smaller model."
            else:
                message = "Online recognition failed or timed out. Check internet and retry."
            raise VoiceError(message) from exc
