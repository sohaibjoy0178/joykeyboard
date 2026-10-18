# JoyKeyboard build plan

Scope: independent Windows desktop voice keyboard inspired by the investigated behavior. Voice typing is the priority. Prior discussion establishes Bangla/English, system-wide insertion, free recognition and a premium icon. No original Kontho assets, credentials or dictionaries will be copied.

1. Build Python 3.12 / PySide6 desktop app in this isolated directory.
2. Implement selected-microphone capture, click/global-shortcut recording, explicit cancellation, background recognition and guarded Unicode insertion.
3. Offer Google web recognition (no user key, online, experimental/personal use) and local faster-whisper CPU/int8 (free, no key, initial model download). Do not claim guaranteed free third-party service.
4. Add polished English/Bangla UI, microphone meter, transcript editor/copy, speech mapping, tray and compact floating controls.
5. Save JSON preferences under the user's local app data, outside installation directory.
6. Create original SVG/PNG/ICO mark; package Windows x64 portable build with bundled Python and dependencies, and reproducible build instructions.
7. Verify text/session logic, UI launch/render, capture/device detection, recorded-sample transcription where available, build launch and safe cross-window insertion. Report actual test boundaries.

Compatibility target: Windows 10/11 x64 Intel/AMD, microphone required. No Python/GPU required after packaging. ARM, 32-bit, Windows 7, macOS and Linux binaries are not promised by a Windows-built executable.

Ownership: main agent owns UI, Windows integration and release integration; backend specialist owns audio/recognition and backend tests; visual/package specialist owns original icon, build scripts and user documentation. All use the shared interfaces below.

Backend contract (module `voice.py`): `list_microphones() -> list[tuple[int,str]]`; `Recorder(device: int|None)` with `start()`, `stop() -> tuple[bytes,int]` (mono PCM16 + sample rate), `cancel()`, `level` (0..1), `error` (str|None). `Recognizer(cache_dir: Path)` with `transcribe(pcm: bytes, sample_rate: int, language: str, engine: str, model: str='base', status: callable|None=None) -> str`, `prepare_model(model='base', status=None)`, `model_ready(model='base') -> bool`. Languages `bn-BD`/`en-US`; engines `google`/`offline`. Capture max duration handled by UI (60 seconds). Recognition serialized by UI. Downloads occur only from explicit Prepare Model action. Offline transcribe must never silently download.
