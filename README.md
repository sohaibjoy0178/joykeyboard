# JoyKeyboard 0.4.12

**Developed by Sohaib Islam Joy** · [Facebook](https://www.facebook.com/sohaib.islam1997)

Windows Bengali/English keyboard and voice studio. Independently built; no NMS Kontho proprietary code, dictionaries, branding, credentials or license checks reused. Original J/microphone icon included.

![Light Glass bar with transparent rounded corners](docs/screenshots/glass-light-bar.png)

![Dark Glass bar with transparent rounded corners](docs/screenshots/glass-dark-bar.png)

![Dark Glass studio, shown with sample text](docs/screenshots/dark-studio-composited.png)

## Install with one EXE

Open **dist/0.4.12/JoyKeyboard-Setup.exe**. Quit any older running copy before opening the installed app. One installer EXE, no ZIP or separate Python/runtime download. Installs for your Windows account without administrator permission, with Start Menu shortcut and an uninstaller. Python, speech libraries, automatic pause detection and dictionaries are included. **Online voice typing works immediately with internet. Offline model weights are optional downloads:** open Preferences → Local recognition, choose Tiny/Base/Small and click **Download offline model** once; then use Whisper without internet. Runtime files stay installed, avoiding extraction at every launch. Allow roughly 500 MB free installation space, plus optional models. Settings, learned words and downloaded models stay in `%LOCALAPPDATA%/JoyKeyboard`; uninstall preserves them.

Installer's **Select Additional Tasks** page offers **Start JoyKeyboard when I sign in to Windows**, checked by default, plus an optional desktop shortcut. Change startup any time under **Preferences → Appearance & startup**. Both use the same HKCU Run entry. Startup displays the idle floating bar; it never starts recording automatically. Windows Startup Apps policies can override startup. App uses one instance per user.

Target: **Windows 10 1809+ / Windows 11, Intel/AMD x64**. ARM, 32-bit Windows, Windows 7, macOS/Linux and every old CPU are not certified. Audio devices/drivers required for recording; offline models need additional memory and supported CPU instructions. The EXE is unsigned, so Windows may display an unknown-publisher warning.

## Floating bar

The app opens as a **384 × 48 logical-pixel floating bar**, always on top. Drag the dotted grip to move it; its position is remembered and recovered onto a connected screen. Click the language/layout selector to choose Bangla/English speech and a keyboard layout. The keyboard icon toggles typing; **Speak / Stop** controls recording. **Hover Speak or Stop to see your voice shortcut** and start/stop instructions. Press those keys once to start, again to stop and transcribe; change them under **menu → Voice shortcut**. The shortcut stays in the hover tip so the bar stays compact. Cancel, timer and level appear while recording; clickable word suggestions appear while composing.

The **three-dot menu** reaches every tool, speech engine, microphone/computer audio choice, Unicode/Bijoy output, automatic typing, Preferences and privacy help. Click the **Joy icon** for the full workspace. Closing the workspace returns to the bar and keeps drafts; **Quit JoyKeyboard** in the bar/tray menu exits with unsaved-draft checks. The minus button hides the idle bar to the notification area; click the tray icon to restore it. Errors/transcript feedback appear in an expandable strip with Copy/Open controls.

**Light Glass and Dark Glass — both transparent:** Both themes use real per-pixel transparency and reflected edges. The workspace keeps Windows compositor blur. The floating bar uses transparency without native backdrop blur, because that effect paints a square rectangle outside custom rounded corners. Only the rounded bar is drawn; no rectangular backing or shadow surface. Light uses silver tint with navy text; Dark uses smoke tint with ivory text. Choose **bar menu → Theme → Light Glass / Dark Glass**, or **Preferences → Appearance & startup → Theme**. Your choice saves immediately and survives restart. Existing light/dark settings are preserved; older Clear Glass settings map to Light Glass. No theme is removed or replaced when switching.

Bar, workspace, all six writing tools and input surfaces follow the selected transparent theme. Foreground text/icons remain crisp at 100% bar opacity; both backgrounds stay see-through. 70/80/90% foreground opacity remains available. Native popup menus use readable matching surfaces; OS file dialogs retain Windows appearance. Bar previews are actual RGBA captures with transparent outer pixels. Workspace previews show the actual app over an owned test backdrop, not a wallpaper included in the product.

Windows blur availability varies by OS/settings/driver. Unsupported blur uses a denser translucent tint in your chosen theme. Uses an optional Windows composition entry point with failure handling, no new library, desktop-capture loop, refraction shader or animation timer. Apple-inspired Windows glass; no proprietary Apple renderer. Actual contrast and graphics cost depend on your desktop and PC.

The workspace has a draggable title (double-click maximize/restore), minimize/close-to-bar buttons and a lower-right resize grip. Closing still preserves drafts and returns to the floating bar. Native file dialogs retain Windows appearance.


## Download from GitHub

[Latest installer and source release](https://github.com/sohaibjoy0178/joykeyboard/releases/latest). Download **JoyKeyboard-Setup.exe** and install; no ZIP extraction needed. `SHA256SUMS.txt` accompanies the installer. Repository and published releases are public; no GitHub login or token is needed. EXE is attached to GitHub Releases; source/build scripts remain in Git history. Large offline model weights are downloaded only when explicitly requested in Preferences; they are excluded from the installer and Git source history. Previously downloaded models remain usable.

## App updates

Install **0.4.10 or newer once** to enable in-app updates. The installed EXE checks GitHub's latest published **stable release** about ten seconds after launch and every six hours. Automatic checks defer while voice work is active. A plain Git push without a published installer release is not an app update; drafts, prereleases and older versions are ignored.

When a newer version exists, JoyKeyboard shows a notification and downloads its installer on a separate worker. Download size and GitHub's SHA-256 digest must match before installation is offered. Checks use public GitHub HTTPS endpoints without bundled credentials. GitHub can limit requests; offline/rate-limit failures leave the app running and can be retried. This checks download integrity, not a Microsoft code-signing certificate; installers remain unsigned.

Choose **bar/tray menu → Install update**, or **Preferences → App updates → Install**. **Installation always asks permission**, with No selected by default. A ready update waits for your decision instead of being discarded by periodic checks. Finish voice/assistant work first, save/copy any needed transcript, and answer existing unsaved-document prompts. After approval the app exits normally; a hidden Windows PowerShell helper waits for exit, rechecks the installer using built-in .NET hashing, installs without restarting Windows, and reopens JoyKeyboard. Settings, words, downloaded models, installation folder and sign-in startup choice are preserved. Failed installation reopens the existing copy and leaves a retry message in update settings. Administrator policy can block PowerShell or installers.

**Preferences → App updates** provides manual checks and a switch to disable automatic checks/downloads. Updates cache uses one installer plus a temporary partial download; interrupted files never replace a verified cache. Quitting cancels network work and lets its worker finish safely. The floating bar stays 384×48 with the existing hover shortcuts.

For maintainers: bump `APP_VERSION` in `core.py` and installer/build paths, build and verify the EXE, upload `JoyKeyboard-Setup.exe` plus `SHA256SUMS.txt` to a draft `vX.Y.Z` release, verify assets, then publish it as Latest. GitHub supplies the asset SHA-256 consumed by the updater. Never attach an older installer under a newer version tag.

## Resource use

Idle controls resize/repaint only when state changes. Large dictionaries load on first suggestion request, so idle and voice-only use avoid their memory cost. Native numerical thread pools are bounded by default; offline recognition uses at most two CPU threads (one on one/two-core PCs). Google online is the lighter transcription option; local speech-pause detection still runs during capture. Offline recognition requires more RAM/CPU and models stay loaded for reuse. Models stay on disk until needed.

On this Ryzen 9 Windows 11 development PC, visible-idle ten-second checks dropped working set from roughly **195 to 126 MiB**, private committed memory from **879 to 72 MiB**, and CPU from **9.5% to 0.5% of one core**. These are idle results, not low-end-device certification or recording/transcription memory limits. See `VERIFICATION.md` and `artifacts/idle-*.json`.

## Voice typing

### Custom global shortcut

Default **Ctrl+Alt+Space** works across normal Windows apps while JoyKeyboard is running, even with its bar hidden. Press once to start, speak, press again to stop and transcribe into the original field. Recognition finishes before text appears; pressing during recognition does not start another recording. Microphone stops on Finish. Automatic speech-pause finishing stays available; disable it in Preferences when you want only the shortcut to finish.

Customize: **bar menu → Voice shortcut** (or **Preferences → Voice shortcut**). Click the shortcut box, press your chosen combination, then **Apply shortcut**. Example: **Ctrl+Alt+V**. Current shortcut appears in bar tooltips, studio and tray. **Reset default** restores Ctrl+Alt+Space. Choice is saved across restarts. Editing the box never starts recording.

Uses native Windows global registration, without key polling. Held keys do not repeatedly toggle. Already-used/reserved combinations show an inline error and keep the previous working shortcut; saving failures roll back. Use Ctrl/Alt/Shift plus one supported key, or F9–F11/F13–F24 alone. F12 stays the keyboard toggle; bare F1–F8 stay candidate selection. Windows-key chords and multi-step sequences are not supported. Windows secure desktops/lock screens are outside this feature. Elevated/custom fields may still block text insertion; transcript stays available. Closing JoyKeyboard releases its shortcut.

**Automatic Finish is enabled by default.** After speech, a pause of about 1.2 seconds finishes the recording and starts transcription; you do not need to click Finish. Disable automatic finishing for longer thinking pauses. Recognition takes additional time. The microphone then stops: click Speak or use the shortcut to start the next phrase. This release handles one phrase per recording, without continuous background listening.

**Faster free Google delivery in 0.4.12:** with automatic finish enabled, recognition can begin during a short speech gap while recording continues until the usual 1.2-second finish threshold. Results stay hidden until you finish. Stopped audio is checked again; if you resumed speaking or the early result cannot be verified, the complete recording is recognized normally. One early attempt per recording, at most one early network worker at a time. Continuing after a gap can use one additional Google request. No account, paid API or new runtime dependency. Hold-Right-Ctrl, manual-only and offline modes keep their existing flow. Cancellation discards results; an in-flight early Google request may finish in the background within existing timeouts. This overlaps work rather than providing live partial words or a guaranteed speedup; shared Google access can still be limited or revoked.

**Delivery improvements retained from 0.4.11:** the pause wait is 0.3 seconds shorter and the previous 0.16-second typing delay is removed. Google uploads use mono PCM16 at up to 16 kHz with fast lossless FLAC encoding, reducing upload size from typical 44.1/48 kHz microphones. Audio already below 16 kHz keeps its original rate. Shortcut modifier-release and destination checks still apply. This reduces local waiting and upload work; Google still processes completed phrases, so internet/server response time remains and words do not appear live while speaking. Offline Whisper retains its existing accuracy settings.

Turn **Finish on speech pause** off in the bar's three-dot menu or Preferences when you want longer thinking pauses. Holding Right Ctrl still waits for release. Speech detection runs locally using the already bundled Silero VAD, without a key/download. Ten seconds with no detected speech discards the recording locally. If detection fails to load, the bar explains that manual Finish is needed; your recording remains available. Manual Finish, shortcut and Cancel still work.

1. Allow desktop microphone access in Windows Privacy settings.
2. Choose Bangla/English with the bar's language selector. Microphone and engine choices are in its three-dot menu or Voice studio.
3. Focus the destination text field. Click **Speak** or press **Ctrl+Alt+Space**, speak, then pause to finish automatically. You can also click **Finish** or press the shortcut again. Optional **hold Right Ctrl** is in Preferences. Recording stops at 60 seconds. The bar's cancel control discards recording; Esc also cancels while studio is focused.
4. Review the transcript, copy/save it, or let **Type into original app when ready** insert it. Disable automatic typing for review first. If destination changes or rejects insertion, the transcript remains available.

**Bangla recommendation: Google online.** Three public FLEURS Bengali samples produced readable Bengali in testing, with recognition errors. Offline Base and Small produced poor Bangla, including incorrect scripts/hallucinations. Do not rely on offline Bangla for important text. Tiny/Base remain available as free local engines, particularly for English. No engine guarantees perfect recognition; review names, numbers and punctuation.

| Engine | Key / cost | Behavior |
| --- | --- | --- |
| Google web, experimental | No user API key or app subscription | Sends recorded audio to Google. Internet required; access can change, be limited or stop. No production service guarantee. |
| Offline Whisper | No key or per-minute service charge | Download Tiny, Base or Small once in Preferences. Then runs on CPU without internet or audio upload; larger does not guarantee better Bangla. |

No voice API key needed for these integrated modes. Official Google Cloud Speech-to-Text is a separate service, not integrated; its credentials cannot be entered here. Optional Gemini text assistance uses a separate user-supplied session key and may incur provider charges. Never embed shared secrets in a distributed EXE.

**Record computer sound instead** captures default Windows speaker through WASAPI loopback. It records all audio playing through that output; stop unrelated playback first. Spoken phrase replacements, Bengali digits and Unicode/Bijoy output are under Preferences. Bijoy needs a compatible legacy Bengali font in the destination; Unicode recommended for modern apps.

## Keyboard and tools

**0.4.1 typing fixes:** remapped/on-screen virtual-key input now goes through Bangla composition. JoyKeyboard marks only its own generated keystrokes to prevent feedback loops; other input is no longer discarded merely because Windows marks it injected. Fast typing no longer mistakes delayed caret movement from an inserted word for a user caret change; native editors get a bounded settling interval. Dictionary loading/matching runs in a separate worker so word insertion does not wait for suggestions. Choose **Bangla phonetic**, enable the keyboard icon or **F12**, focus Notepad/browser, type `ami banglay likhi`, then **Space** to insert `আমি বাংলায় লিখি`. Pending word appears in the floating bar until Space/Enter or a candidate selection commits it. Unicode recommended for modern apps.

- **F12** toggles system-wide keyboard mode. Starts off every launch. Layouts: Bengali phonetic, English, Probhat and Bengali InScript. Fixed layouts cover printable/Shift positions on a US physical keyboard; AltGr/keypad extensions absent.
- Composition appears in floating toolbar. **Space/Enter/punctuation commits** the word; **F1-F8** chooses candidate. This uses a Windows hook, not TSF IME registration. Turn mode off before passwords; custom/browser secure fields may not be detected.
- Licensed Bengali/English dictionaries contain 504,240 entries. Suggestions combine frequency, personal usage and bounded correction. Next-word prediction learns committed word transitions locally.
- Words manager edits personal words/snippets, imports/exports validated JSON and shows recent committed words. Invalid original files protected against silent overwrite.
- Converter supports Unicode/Bijoy. Common-word coverage tested; arbitrary mixed Latin/legacy text and every font variant not guaranteed.
- Screen keys compose Bengali/Latin text for insertion, without system Ctrl/Alt shortcut simulation.
- DocPad opens/saves UTF-8 text, finds/replaces and exports PDF, with unsaved-edit protection.
- Optional Gemini sends only text explicitly submitted, with an in-memory API key. No key bundled or saved. Review results before insertion.

Protected/elevated apps, games and custom editors may reject simulated typing. Native target/control/caret checks reduce accidental delivery; they cannot identify every browser field. Clipboard changes only on explicit Copy. Keep keyboard mode off when unused.

## Privacy and local data

Audio recorded only on request, not saved automatically. Google mode uploads clips to Google; offline mode stays local. No silent cloud fallback. **Committed words, recent word history and transitions are retained locally** in `keyboard-data.json` when app closes. Successful voice transcripts also feed local learning. Avoid committing sensitive text if you do not want it in local learning. Words tab provides import/export/history controls. Preferences: `settings.json`; user model downloads: `models/` under same local data directory.

## Build from source

Requires Windows x64 and Python 3.12 x64:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
powershell -ExecutionPolicy Bypass -File .\build.ps1 -SkipInstall
powershell -ExecutionPolicy Bypass -File .\build-installer.ps1 -SkipInstall
```

`build-installer.ps1` requires Inno Setup 6.7+ ([official download](https://jrsoftware.org/isdl.php)); pass `-IsccPath` if not detected. It validates icons, runs tests, clean-builds installed runtime under `dist/0.4.12/JoyKeyboard/` and compiles the single `JoyKeyboard-Setup.exe`. Keep the runtime folder for debugging; distribute only the setup EXE. Original `build.ps1` still builds an optional portable one-file app at `dist/JoyKeyboard.exe`. Build on Windows x64; no cross-compilation. Offline model weights are not required to build and are never bundled. `assets/models/` supplies provenance and MIT notices. SpeechRecognition data includes only its required version file and Windows FLAC encoder; unused PocketSphinx models and other-platform encoders are excluded. Only the three README preview images are bundled. Dictionary provenance: `assets/keyboard/` and `KEYBOARD-SOURCES.md`.

## Licenses and replacement

Third-party notices, model MIT license, original layout files and dictionary attribution bundled in the installed `_internal` folder under `licenses/` and `assets/`, and available in this source project. See **KEYBOARD-SOURCES.md** for parser/layout/dictionary source URLs and licenses, including CC-BY-SA data. Original icon artwork: `assets/joykeyboard.svg`.

PySide6/Qt and FFmpeg shared libraries retain upstream LGPL terms. This source project/build specification let recipients rebuild/relink with compatible modified libraries; one-file extraction contents are temporary and replaced on launch. Reverse engineering library modifications for debugging permitted under applicable licenses. Obtain exact corresponding upstream sources matching `requirements-lock.txt`:

- [Qt LGPL guidance](https://www.qt.io/licensing/open-source-lgpl-obligations), [Qt sources](https://download.qt.io/archive/qt/), [PySide sources](https://download.qt.io/official_releases/QtForPython/)
- [FFmpeg sources](https://ffmpeg.org/download.html#get-sources), [PyAV wheel recipes](https://github.com/PyAV-Org/pyav-wheels)
- [Whisper MIT sources/models](https://github.com/openai/whisper), [faster-whisper](https://github.com/SYSTRAN/faster-whisper)

See `VERIFICATION.md` for executed checks and boundaries. No claim of exact Kontho feature parity or universal PC compatibility.
