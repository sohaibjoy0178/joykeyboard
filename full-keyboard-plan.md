# JoyKeyboard full desktop release

The user now explicitly requires a full typing application, not merely dictation, and one standalone Windows executable rather than a ZIP. Voice remains the top priority. This plan supersedes the first release's reduced feature scope; preserve existing user settings/transcripts and working voice functionality.

## Scope and completion evidence

- Keyboard mode: live Bengali phonetic conversion, fixed layouts, English mode, global toggle, suggestions/corrections, recent-word ranking, snippets and editable user dictionary.
- Tools: word manager with import/export, encoding converter including Unicode/Bijoy compatibility, on-screen keyboard, document pad, sentence/history prediction, optional Gemini text assistance.
- Voice: selected microphone, online/offline engines, validated model preparation, system audio where supported, mapping/output encoding, explicit errors/cancellation, real Bengali sample check if available. Never promise perfect ASR or unsupported old PCs.
- Packaging: one-file EXE with Python/libraries/assets, original premium icon, offline tiny model bundled if redistribution license verified so a fresh PC has a key-free local engine without a separate download. Larger model download remains explicit. User data stored outside temporary extraction/install locations.
- Verification: deterministic engine tests; real owned editor hook/insertion tests; source and one-file packaged UI/recognition checks from a clean folder, with Python paths removed. Keep an honest feature checklist with unsupported/incomplete cases.

## Parallel ownership

1. Engine/data specialist owns `keyboard_engine.py`, `assets/keyboard/`, `tests/test_keyboard_engine.py`, `KEYBOARD-SOURCES.md`, optional `keyboard-requirements.txt` only. Reuse licensed public phonetic/conversion/dictionary libraries/data; do not copy unknown-license Kontho data.
2. Windows hook specialist owns `keyboard_hook.py`, `tests/test_keyboard_hook.py`, `tests/keyboard_native_probe.py` only. Use engine below; preserve foreground safety and ignore injected events. Root owns existing `windows.py` and application integration.
3. Tools specialist owns `tools_ui.py`, `tests/test_tools_ui.py` only. UI composes keyboard engine, suggestions/word manager, converter, on-screen keyboard, document pad and optional Gemini assistance. No edits to main app/core/build files.
4. Root owns voice improvements, application/settings integration, packaging/requirements/license integration, release tests, docs and final EXE.

## Shared engine contract

`KeyboardEngine(path: Path | None = None)`; module `LAYOUTS` dictionary mapping IDs to display names (`phonetic`, `english`, plus conventional fixed layouts). Methods `convert(text: str, layout: str='phonetic')->str`, `suggest(prefix: str, limit: int=8)->list[str]`, `learn(word: str)->None`, `predict(previous: str, limit:int=5)->list[str]`, `commit_sentence(text:str)->None`, `export_data()->dict`, `import_data(data:dict)->None`, `save()->None`. Mutable `custom_words: list[str]` and `snippets: dict[str,str]` are edited by UI then saved with validation. `to_ansi(text:str)->str` and `from_ansi(text:str)->str` are module functions. Provide methods/properties adapters only if needed, agree changes by message.

## Hook contract

`KeyboardHook(engine, on_update: callable, on_error: callable)` uses one owned Windows message-loop thread. `start()`, `stop()`, `set_enabled(bool)`, `set_layout(id)`, `choose(index:int)`, `reset()`, `enabled` property. Callback `on_update(raw:str, rendered:str, suggestions:list[str])` must be safe to bridge to Qt signals. Hook may ignore JoyKeyboard-owned windows by default; tools' local editor supplies its own phonetic preview. Global F12 toggles keyboard mode; F1-F8 select visible suggestions. Avoid conversion during Ctrl/Alt/Win chords and password/secure fields; injected events never re-enter engine. Shut down cleanly and never hook during smoke tests.

## Tools UI contract

`KeyboardTools(owner, engine, insert_callback: callable)` is a QWidget for an application tab. Emits `settings_changed` when engine data changes. `update_candidates(raw, rendered, suggestions)` updates visible keyboard state. `insert_callback(text)` routes through owner's guarded target insertion. UI supports actual local operations; unavailable optional Gemini features must explain missing key/network without fake success. Persist no API secrets in plain text; session-only key is acceptable for this release.

## Compatibility and risk

Target Windows 10 1809+ / Windows 11 Intel/AMD x64. A Windows x64 executable cannot promise every CPU/OS. Low-level keyboard hooks and editor backspace semantics must be exercised before shipping. Do not discard or overwrite user dictionaries/settings on migration. No automatic service fallback that uploads locally chosen audio without explicit user selection.

## Completed release

0.2.0 standalone EXE built and verified. 119 tests pass. Clean-folder packaged UI, bundled offline English, online Bangla, normal startup/hook/shutdown all pass. Final source/archive and required assets match. See VERIFICATION.md for evidence and accuracy/compatibility limits.

## Floating UI release 0.3.0

Default compact floating bar, native focus preservation, drag/persist/recover, complete tool/control menu, recording/cancel feedback and eight clickable candidates delivered. 128 tests pass. Final EXE source/assets match; clean-folder UI, offline English, online Bengali, normal bar startup and explicit quit all pass.

## Automatic finish release 0.3.1

Local speech-pause monitoring defaults on, auto-finishes after about 1.5 seconds, stops after each phrase, and preserves manual/hold/cancel paths. 138 tests plus actual recorded-Bengali UI/model/sample-rate/noise checks pass. New standalone EXE at dist/0.3.1/JoyKeyboard.exe passes all five clean-folder checks; currently running old EXE left untouched.
