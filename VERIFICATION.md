# JoyKeyboard 0.4.15 verification

Delivered `dist/0.4.15/JoyKeyboard-Setup.exe`, **100,939,073 bytes** (100.9 MB). SHA-256: `fb6350ae5472ff3484211e7429b2ea8b1c7d8d13cc3e5bea630ba3281fc70406`. Installer/checksum: [v0.4.15](https://github.com/sohaibjoy0178/joykeyboard/releases/tag/v0.4.15).

## Sherpa Prepare hang: reproduced and fixed

The actual released 0.4.14 EXE was driven through Windows UI Automation in an owned empty profile with no Python on PATH: select Preferences, click Prepare Sherpa, observe Needs attention, click Prepare again, then Quit. The retry remained blocked and did not quit within eight seconds; only this owned test process was terminated (`tests/prepare_download_probe.ps1 -Mode Reproduce`, `artifacts/prepare-actual-0.4.14-repro.log`). The user's app/process was not terminated.

A source Qt reproduction and an instrumented frozen build captured the underlying error: Hugging Face's console progress display writes to `sys.stderr`, which is None in the windowed app. Its first refresh raises AttributeError before releasing the global tqdm progress lock. A new voice Job thread on the second Prepare waits on that lock indefinitely; cooperative cancellation cannot interrupt a lock acquire, so Quit also waits. The source repeat trace confirmed the worker at tqdm/std.py __new__ while the UI continued servicing events (`artifacts/prepare-retry-bug-repro.log`, `prepare-frozen-bug-repro.log`). Earlier source-only model downloads had not exercised this actual frozen Preferences path.

Sherpa manual preparation and automatic model updates now share a console-free standard-library HTTPS stream. No tqdm, Hub native transfer backend or Hub file lock is used on this path. Pinned repository/revision/filenames, trusted HTTPS redirects, bounded declared/actual sizes and SHA-256 remain enforced. Downloads read at most 64 KiB per iteration, check cancellation around reads and redirects, report per-file percentage, and use five-second network I/O timeouts. Unique partial files are removed on failure/cancellation; a complete verified file replaces its destination atomically. Failed forced replacement preserves an existing valid file. Cached weights are still verified locally without network. Whisper already uses its existing disabled console-progress helper and is unchanged.

The existing floating-bar feedback displays preparation progress instead of generic Working. Cancelled late progress is ignored. Idle bar remains 384x48; no new timer/control/dependency or model/runtime upgrade.

## Executed checks

- **336 pytest tests passed**, two upstream Python deprecation warnings (`artifacts/tests-0.4.15-final.log`). New/updated tests cover repeat downloads with no stdout/stderr, secure redirects, no credentials, socket timeout, wrong/truncated/oversized/hash-invalid responses, cancellation during a file, response closure/partial cleanup, preserving a valid file, timeout then successful retry, visible compact progress and ignored cancelled late progress. Existing three-engine, model-channel, keyboard, settings, shortcut, theme and app-update tests passed. Ruff, pip check and Git whitespace passed.
- **Actual final EXE UI tests**, all using Windows accessibility actions against only the owned child PID, empty application/model profiles and System32-only PATH (`tests/prepare_download_probe.ps1`): Complete performed two Prepare clicks successfully, verified all four model hashes and quit normally; Cancel observed live encoder progress at 1%, cancelled, recovered controls in **0.191 seconds**, retried to completion and quit; Quit observed active progress at 3% and exited in **0.116 seconds**. No forced kill and no remaining .part files in any fixed-app scenario. Reports: `artifacts/prepare-0.4.15-Complete.log`, `prepare-0.4.15-Cancel.log`, `prepare-0.4.15-Quit.log`. Timings are single measurements on this host/connection, not global cancellation/exit guarantees.
- New source windowed/no-console replay completed an actual fresh download with **149 UI timer ticks over 16.3 seconds**, model ready and no error (`artifacts/prepare-source-fixed.log`). The user's requested Sherpa model was also downloaded/verified successfully through the fixed path in the existing models folder, without changing settings (`artifacts/user-sherpa-recovery-0.4.15.json`). Existing stale zero-byte Hub incomplete files were left alone; they are not used by the new transport.
- Final clean PyInstaller/Inno builds passed after all bundled source/assets/README edits (`artifacts/build-0.4.15-final.log`, `build-0.4.15-setup-final.log`). Fourteen embedded modules plus main match source, required licenses/assets present, optional weights excluded and bundled README byte-identical to source.
- Final fresh-folder packaged app passed Light/Dark alpha, Google Bengali and automatic-pause/early recognition, explicit Tiny/offline English, explicit Sherpa/offline Bengali, a staged higher-version current-model fixture followed by frozen offline recognition/automatic pause, normal hook startup and graceful close (`artifacts/prepare-fix-package-final.log`, `standalone-check.json`). Offline child processes had Hub access disabled. The separate UI Automation checks above cover the previously missed frozen Prepare/download click itself. CLI accelerated replay is not realtime latency.
- Actual temporary installer/reinstall/uninstall passed startup default/on-off removal, quoted Run command, developer/Facebook metadata, normal startup/graceful exit, user-data retention and restoration of original registry/shortcut (`artifacts/installer-0.4.15-final.log`). User's existing runtime folder was untouched. Installed Google/Dark ten-second sample: **135.16 MiB resident, 75.23 MiB private, 1.562% of one CPU core**; sample includes ordinary app/update activity and concurrent verification, not a resource ceiling.
- Release assets are checked against local byte counts/hashes before publication; public app-update discovery and the unchanged verified model channel are checked afterwards. Complete app-update installation-helper lifecycle and new microphone/accuracy benchmarks were not rerun; their unchanged paths retain previous evidence. Existing unrelated dictionary preparation-script lint issues remain as recorded in 0.4.11.

Limits: networking can fail or time out, and OS DNS resolution may outlast a socket timeout. Cancellation is checked between network operations; the measured sub-second results are not universal. Recognition accuracy/model version and installer signing are unchanged; installer remains unsigned. If an already-running old copy is stuck, copy unsaved text and end that process once before installing this fix.

# Historical 0.4.14 verification

Delivered `dist/0.4.14/JoyKeyboard-Setup.exe`, **100,921,992 bytes** (100.9 MB). SHA-256: `a33191a1f6ce9c4119eb4b58f6338657ff8935c747e439405c82b095f1cb43e5`. Installer/checksum: [v0.4.14](https://github.com/sohaibjoy0178/joykeyboard/releases/tag/v0.4.14).

## Automatic Sherpa model updates

After the optional first Sherpa model download, installed copies check the public JoyKeyboard model channel at startup and every six hours, reusing the app-update schedule. The existing automatic-updates setting controls both checks; manual Check for updates covers both even when automatic checks are off. A separate existing Job/QThread pattern handles model work; no new timer, polling loop or floating-bar control. Preferences > Local recognition reports checking/downloading/ready/failure status. App installation still asks permission; compatible model replacements activate automatically between voice sessions.

The channel is the fixed public GitHub repository contents endpoint for `assets/models/sherpa-channel.json`. Model changes require maintainer accuracy/latency/resource review and a versioned manifest push, independently of an app release. No arbitrary upstream upload is silently adopted. The manifest pins the existing model repository and a full immutable revision, exactly four fixed filenames, bounded sizes, SHA-256 values, schema/version and minimum app version. Foreign repositories, mutable revisions, extra/path-traversal filenames, invalid/oversized metadata, older versions and incompatible app requirements are rejected or deferred. No credentials or first-model download are introduced.

Downloads stage in a separate version directory and pass size/hash verification and an actual single-thread Sherpa construction/decode check. Current dictation retains its model. A verified candidate waits for recording/voice jobs to finish, then an atomic small-pointer replacement selects it for the next recording and drops the old loaded recognizer reference. Offline, corrupt, incompatible and cancelled candidates never replace the current pointer. Startup validates the pointer and file sizes; missing/malformed selections fall back to the retained original model. No existing model files are overwritten or deleted during update activation. Automatic-update disable/quit cancels pending model work and rejects late results. Sherpa runtime/library upgrades continue through normal full app releases.

## Executed checks

- **320 pytest tests passed**, two upstream Python deprecation warnings (`artifacts/tests-0.4.14-final.log`). New coverage includes strict channel/source/hash/size/schema validation, bounded Base64 GitHub responses, metadata versus installer HTTP media types, no initial automatic model download, no rollback, minimum-app gating, immutable/account-free downloads, native compatibility failure, cancellation, atomic pointer failure, restart/fallback, busy-voice deferral, separate voice availability, setting-off late-result suppression, quit lifecycle and independent error status. A subsequent test-only maintenance adjustment permits future channel versions without redefining baseline version 1; its 22 module tests passed (`artifacts/tests-0.4.14-channel-final.log`). Application/tests/hooks Ruff, pip check and Git whitespace passed.
- **Real-model update probe** (`tests/sherpa_update_probe.py`, `artifacts/sherpa-update-real-model.log`): actual model file hashes and native Sherpa compatibility/decode ran in the Qt update worker using current weights under a higher-version test manifest. Capture was marked busy while download/validation completed; old pointer/loaded engine stayed intact until idle. Activation selected the staged path, subsequent offline Bangla transcript matched, a restarted recognizer used the updated path, and an intentionally bad later hash preserved the active pointer and loaded engine. No future upstream model or live microphone was used. The public GitHub contents transport was also exercised without authentication; an incompatible Accept header found during testing was fixed and protected by three request-header tests before the final build.
- **Clean PyInstaller/Inno builds** after all bundled source/assets/README edits passed (`artifacts/build-0.4.14-final.log`, `build-0.4.14-setup-final.log`). Fourteen embedded modules plus main match source, including the new model updater; required licenses/assets present and optional weights excluded. Bundled README matches source byte-for-byte. New Preferences controls/status rendered and inspected (`artifacts/sherpa-update-preferences.png`; the final app-installation wording is slightly clearer).
- **Final fresh-folder packaged EXE**, initially empty profile and System32-only PATH, passed Light/Dark alpha, Google Bengali, Google automatic-pause/early recognition, explicit Tiny/offline English, explicit Sherpa/offline Bengali, staged higher-version model activation followed by frozen offline Sherpa automatic-pause recognition with the unchanged full transcript, normal hook startup and graceful close (`artifacts/sherpa-updates-package-final.log`, `standalone-check.json`). This uses real current weights under a version fixture, not a published fake model update. Source preparation uses the same shared explicit download path; frozen Preferences download click was not separately automated. Hub network access was disabled in offline child processes. CLI replay times are accelerated processing time, not live latency.
- **Final actual temporary install/reinstall/uninstall** passed default startup selection, quoted Run command, developer/Facebook metadata, startup-off removal, normal startup/graceful exit and preserved user data (`artifacts/installer-0.4.14-final.log`). Original registry/shortcut restored; user's running copy untouched. Installed default-Google Dark ten-second sample: **133.02 MiB resident, 74.63 MiB private, 1.406% of one CPU core**, including ordinary app/update activity. This is not a low-end hardware guarantee.
- During publication, the fixed unauthenticated production model channel is checked against the committed manifest, release assets against local bytes/SHA-256, and normal production app-update discovery against v0.4.14. Complete update-install helper lifecycle was not rerun; helper code is unchanged and its tests passed. Existing unrelated dictionary preparation-script lint issues remain as recorded in 0.4.11.

Limits: this release keeps the same speech model and accuracy measured in 0.4.13; no newer upstream model, new live-microphone accuracy or low-end hardware benchmark was performed. Model-file cancellation takes effect after that file completes. Old weights stay on disk for recovery and can accumulate across future releases; compatibility validation can temporarily hold an extra model in RAM. GitHub/Hub availability and rate limits apply. Manifest and file hashes provide trusted-channel integrity, not an Authenticode signature; installer remains unsigned.

# Historical 0.4.13 verification

Delivered `dist/0.4.13/JoyKeyboard-Setup.exe`, **100,919,813 bytes** (100.9 MB). SHA-256: `9acd2c385759438399ce0964dbda86ef23d4f0d6f5c8bccf10d617fc322155f9`. Installer/checksum: [v0.4.13](https://github.com/sohaibjoy0178/joykeyboard/releases/tag/v0.4.13).

## Optional experimental Bangla streaming

Sherpa is a third speech engine alongside Google and Whisper. Google remains default. After reviewing the accuracy difference below, the user explicitly approved an optional experimental engine. Select Sherpa Bangla in Voice studio or the floating-bar Speech engine menu, then Preferences > Local recognition > Prepare Sherpa Bangla. Its ~90 MiB model is an explicit one-time download, excluded from the installer. Subsequent recognition is local, Bangla-only, with no account, API key, internet or GPU requirement. CPU inference uses one thread. Existing shortcut, hold and automatic-pause controls work with the streaming worker. The 384x48 idle bar, Light/Dark alpha and hover shortcut remain unchanged.

The existing voice QThread decodes while capture continues; model loading and inference do not run on the UI/audio callback thread. Partial text appears only as a preview on the existing recording row, elided to fit; final text is delivered once through the existing guarded insertion path. Stop drains the final recording tail even after Recorder clears its capture buffer. Generation/cancellation checks prevent cancelled or late results from being typed. Errors stop capture and remain visible. Switching engines drops model references; native libraries/shared VAD resources and allocator caches can retain memory. Selecting Sherpa or starting the app does not implicitly download or load its model. Preparation pins the model revision, disables account tokens and verifies fixed file sizes and SHA-256 hashes before loading. Cancellation during an individual model-file download takes effect after that file completes.

## Accuracy, speed and resources

Reproducible measurements and raw hypotheses: [benchmark methodology](docs/benchmarks/README.md), [results](docs/benchmarks/sherpa-0.4.13.json), [fixture manifest](tests/fixtures/sherpa-bengali.json). Google FLEURS Bengali India test split, first twelve archive entries, 157.56 seconds / 235 reference words, all labelled MALE; no transcript-based selection. Identical PCM for both engines. NFC/case/punctuation normalization, whitespace word scoring; compound spacing/spelling variations count as errors. This is a small read-speech screen rather than microphone/accent certification.

| Paired accuracy screen | Sherpa | Google |
| --- | ---: | ---: |
| Word error rate | 22.13% | 19.57% |
| Character error rate | 5.84% | 4.75% |

Four-path beam search did not improve Sherpa accuracy (22.55% WER), so greedy decoding is retained. Original/exported model provenance, Apache-2.0 license, pinned revision and hashes are recorded under assets/models; FLEURS reference metadata is attributed under CC BY 4.0. No model weights or audio are committed.

Host: AMD Ryzen 9 7900X, 24 logical CPUs, about 31 GiB usable RAM, Windows x64. OpenBLAS/OMP settings match main.py. Percentages below are process CPU time divided by wall time, expressed relative to **one core**, not total machine capacity. RAM is process working set, including shared libraries; compositor/GPU allocations are excluded.

| Actual source Qt app replay | Measured |
| --- | ---: |
| Google idle before model use | 135.14 MiB resident / 81.35 MiB private |
| First live preview | 1.501 seconds after recording starts |
| Sherpa loaded idle | 329.72 MiB resident / 286.73 MiB private |
| First recording including loading and pause detection | 15.66% of one core |
| Warm recording including pause detection | 6.59% of one core |
| Loaded idle, short five-second sample | 0.31% of one core |
| Stop to recognition-result UI callback | 24.8 ms first / 50.5 ms warm |
| Switch back to Google | 200.99 MiB resident / 152.00 MiB private |

This profile uses the actual Qt job, visible bar, fixture recorder, local PauseMonitor, automatic typing disabled and no native keyboard hook. Stop timing ends at the callback, **before external typing**; the existing 1.2-second automatic-pause confirmation still applies. Repeating/cancelling/unloading left ~201.35 MiB resident, without another large retained-model increase. Idle percentages use short Windows-counter samples. Cancellation's coarse-clock zero is within timer resolution, not literally zero work.

A separate three-clip realtime engine-only replay produced first partials in 1.516-1.519 seconds and final flush in 1.4-17.4 ms after input end, with 0.5 seconds of zero padding fed immediately. Active CPU was 2.54-3.43% of one core; loaded idle rounded to zero at counter resolution. Resident engine process was ~198-200 MiB versus Google's ~48 MiB. These exclude Qt, pause confirmation, microphone callbacks and delivery; do not present them as full-app latency or CPU.

## Executed checks

- **290 pytest tests passed**, two upstream Python deprecation warnings (`artifacts/tests-0.4.13-final.log`). New tests cover pinned explicit model download, hashes/path/size rejection, cancellation and offline cache reuse; lazy one-thread loading and model release; Bangla/missing-model guards; live preview versus one final result; draining stopped capture; cancellation during decoding; silence/invalid-rate/short audio; unchanged bar width in both themes; and streaming UI worker/error/control lifecycle. Existing keyboard, voice, shortcuts, settings and updater tests passed.
- Source Qt realtime fixture replay exercised preview, finalization, warm repeat, cancellation and model release (`artifacts/sherpa-ui-profile-final.log`). Actual Windows global-shortcut and floating-bar probes passed with fixture capture/recognition: hidden-bar start/finish, focus retained, Bengali insertion once, keyboard resumed and hover hint visible (`artifacts/sherpa-global-shortcut.log`, `sherpa-floating-native.log`). No live microphone/physical input used.
- Clean PyInstaller/Inno builds passed after all bundled source/assets/README changes (`artifacts/build-0.4.13-final.log`, `build-0.4.13-setup-final.log`). Thirteen embedded modules plus main match source; required licenses/assets present, optional model weights excluded. Bundled README exactly matches source.
- Full fresh-folder packaged probe with initially empty profile and System32-only PATH passed Light/Dark alpha, online Bengali, Google early automatic-pause recognition, explicitly prepared Tiny offline English, explicitly prepared **Sherpa offline Bengali**, normal hook startup and graceful close (`artifacts/sherpa-package-final.log`). Model preparation uses the shared source path; the frozen Preferences download click was not separately automated. That full probe preceded only a README wording cleanup; final rebuilt binary passed code/README equality, UI smoke and **48 kHz Sherpa + automatic pause/VAD** with Hub access disabled (`artifacts/sherpa-final-rebuild-check.log`, `standalone-sherpa-48k-auto-pause-final.json`). Both packaged native ONNX runtimes loaded together successfully. CLI accelerated replay time is not realtime latency.
- Final installer actual temporary install/reinstall/uninstall passed default-checked startup, quoted Run command, developer/Facebook metadata, startup-off removal, normal startup/graceful quit and preserved user data. Original registry/shortcut restored; user's running app untouched (`artifacts/installer-0.4.13-final.log`). Installed default-Google Dark ten-second sample: **133.25 MiB resident, 74.88 MiB private, 1.094% of one core**, including ordinary app/update activity. This is not a low-end hardware guarantee.
- Application/tests/hooks Ruff, pip dependency validation and Git whitespace checks passed. Existing unrelated dictionary preparation-script lint issues remain as documented in 0.4.11. Updater code is unchanged; its tests passed, but complete update-install helper lifecycle was not rerun this release. Published release metadata/digest and the unauthenticated production update feed are checked during publication.

Limits: real microphone performance, broad accents/female speech/noise and low-end/other PCs untested. Sherpa has slightly higher measured error rate and substantially more loaded RAM than Google; it previews locally but types the final result on finish. Google availability/network latency can vary. Installer unsigned. This release does not promise perfect recognition or identical Android-style behavior on every PC.

# Historical 0.4.12 verification

Delivered `dist/0.4.12/JoyKeyboard-Setup.exe`, **95,001,594 bytes** (95.0 MB). SHA-256: `a54f0154ab02a367f37c4ea1cdaddfeeef14822b0de1525faaa7e3ac2ca80cde`. Installer/checksum: [v0.4.12](https://github.com/sohaibjoy0178/joykeyboard/releases/tag/v0.4.12).

## Free early recognition during speech pauses

User chose completely free operation without a paid API/account requirement. Google web mode now makes one early recognition attempt during a locally detected short gap (0.35 seconds plus detector polling). Recording continues until the unchanged 1.2-second automatic finish threshold. No partial result enters the transcript or external editor before finish.

The final recognition worker checks session identity, language, sample rate and exact PCM prefix, then rechecks stopped audio for speech beyond the snapshot, including arrivals after the monitor's last poll. If speech resumed or validation fails, the complete recording uses the ordinary Google path. Otherwise the worker reuses or waits for the early result. One attempt per recording, one early network worker per recognizer at a time; at most one additional request when continued speech invalidates the early snapshot. Network errors from a reusable request are reported without repeating it. Cancellation prevents delivery and waiting is interruptible. In-flight early requests cannot be aborted; a bounded daemon with no Qt/UI references finishes in the background within existing FLAC/network timeouts. Cancel/restart cannot accumulate early workers.

No paid engine, new key, new setting or new runtime dependency. Early recognition applies only to Google with automatic pause finish; hold-Right-Ctrl, manual-only and offline flows retain existing behavior. No new floating-bar control, size change or timer; Light/Dark glass and hover shortcuts retained. Existing shared Google testing-service limitations remain.

## Executed checks

- **Real-time UI/audio replay with real Google requests** (`tests/voice_overlap_probe.py`, `artifacts/voice-overlap-realtime.json`): Bengali reference speech end 9.696 seconds. Baseline (early recognition disabled) delivered text at 12.860 seconds, **3.164 seconds after speech**. Early path delivered at 11.984 seconds, **2.288 seconds after speech**: **0.876 seconds sooner** in this one paired comparison, same full transcript and one upload each. Early upload began at 10.312 seconds while capture remained active until 11.109. This is a measured fixture result, not a universal percentage/latency guarantee or a live microphone benchmark.
- English fixture with internal pauses started an early request at 2.812 seconds, then correctly rejected it after resumed speech and uploaded the complete 12.375-second recording. Full 'fellow American ... country' transcript preserved with two uploads; that path has no guaranteed speed gain. Shorter finish thresholds were not introduced.
- **273 pytest tests passed**, `artifacts/tests-0.4.12-final.log`. New checks cover bounded workers and thread-start failure, snapshot capture without stopping, early-gap reset on resumed speech, no premature UI delivery, one attempt, final forwarding, held-key/offline/empty-input exclusions, exact prefix/session/language/rate checks, fresh speech validation/failure fallback, complete-audio upload on resumption, request failure without duplicate retry, cancel during wait and late-result rejection. Diagnostic checks exercise one early attempt and correct online/auto-only forwarding. Existing voice, keyboard, shortcuts, themes, updates and settings passed. Two upstream Python deprecation warnings remain.
- Real Windows custom hidden-bar shortcut and actual floating-bar clicks passed: Bengali fixture insertion into owned editor, focus retained, keyboard resumed, no key-repeat toggle, inactive hover shortcut visible (`artifacts/overlap-shortcut-native.log`, `overlap-floating-native.log`). These use fixture recording/recognition, without physical input or live microphone capture.
- Final clean PyInstaller/Inno builds passed. Thirteen embedded modules plus main match final source; required assets present, optional offline weights/PocketSphinx excluded. Fresh-folder packaged EXE with empty profile/System32-only PATH passed Light/Dark alpha, Google Bengali, **automatic pause with actual early recognition enabled**, explicit Tiny download/offline English, normal hook startup and graceful close (`artifacts/overlap-package-final.log`). Offline fixture preparation uses the source shared model path; the frozen Preferences download click was not separately automated.
- Additional packaged **48 kHz Bengali and English** automatic-pause checks passed with early recognition enabled and complete phrases retained, without offline model download (`artifacts/overlap-packaged-48k.json`). CLI diagnostic replay is accelerated and its processing-time field is not realtime end-of-speech latency; the separate UI probe above uses realtime replay.
- Actual temporary installer/reinstall/uninstall passed default startup selection, quoted Run command, developer/Facebook metadata, startup-off removal, normal startup/graceful quit and preserved user data. Original registry/shortcut restored; user's running app untouched (`artifacts/installer-0.4.12.log`). Installed Dark ten-second app-process sample: **133.25 MiB working set, 74.84 MiB private memory, 0.937% of one CPU core**. This sample includes ordinary app/update work and is not a low-end hardware guarantee.
- Application/tests/hooks Ruff, pip dependency validation and Git whitespace checks passed. Pre-existing unrelated dictionary preparation-script lint issues remain as recorded in 0.4.11. Updater code is unchanged; existing full tests passed, but its complete installation helper lifecycle was not rerun this release.

Limits: still completed-phrase recognition, without Android-style live partial words. Real microphone accuracy/timing and other PCs not measured. Internet/service latency varies; resumed-speech fallback may add a request or save no time. Shared Google access can be limited/revoked. Installer unsigned.

# Historical 0.4.11 verification

Delivered `dist/0.4.11/JoyKeyboard-Setup.exe`, **95,006,063 bytes** (95.0 MB). SHA-256: `b79a1f54697047c150a61df755ee442ab8eacbdc005a75e2b55106b789a0fd00`. Installer/checksum: [v0.4.11](https://github.com/sohaibjoy0178/joykeyboard/releases/tag/v0.4.11).

## Faster voice delivery

Automatic finish now waits about **1.2 seconds**, previously 1.5; the extra **160 ms** before delivery is removed. The unchanged 250 ms detector polling can round the pause upward. Key-release, cancellation and target/control checks still guard delivery. Users needing longer thinking pauses can disable automatic finish and use their existing voice shortcut or hold Right Ctrl.

Google audio is resampled to at most **16 kHz mono PCM16 before request creation**, so the encoded FLAC rate and HTTP header agree. Lower-rate microphones retain their rate. Fast FLAC compression reduces encoding work; compression itself is lossless after resampling. Offline Whisper/model settings are unchanged. No new dependency, credential, background listener or polling loop.

## Measurement and regression checks

- Interleaved three-round Bengali fixture comparison at simulated 48 kHz microphone format: old 48 kHz/best FLAC **392,697 bytes**, new 16 kHz/fast FLAC **193,725 bytes**, **50.7% smaller**. Median preparation 30.5 -> 23.8 ms. Google request medians **1.951 -> 1.972 seconds**: no measured server-response improvement; all six transcripts matched. Report: `artifacts/voice-latency-baseline.json`. This isolates payload preparation/network work rather than claiming Android-style streaming or a guaranteed total speedup.
- Very short 0.8-1.1 second pauses prematurely ended the English fixture. Chosen 1.2 second policy preserved the full tested Bengali and English phrases. At 250 ms fixture steps, recording finished **11.25 -> 11.00 seconds** for Bengali (speech end 9.750) and **12.25 -> 12.00 seconds** for English (speech end 10.572). The removed typing delay saves a further 160 ms when modifier/focus checks allow immediate delivery. Reports: `artifacts/voice-pause-baseline.json`, `voice-speed-source-check.json`.
- **251 pytest tests passed** (`artifacts/tests-0.4.11.log`). New cases cover 8/16/44.1/48/192 kHz input, matching Google rate headers and real FLAC decoding, faster pause boundary/short hesitation, immediate scheduling and held-Ctrl deferral. Existing voice, hotkeys, keyboard, Light/Dark transparency, updates and settings checks passed. Application/tests/hooks Ruff, pip check and Git whitespace checks passed. Repository-wide Ruff also reports pre-existing import issues in the unrelated dictionary preparation script `assets/keyboard/prepare_data.py`; that file was left unchanged. Two upstream Python deprecation warnings remain.
- Real Windows global custom shortcut with hidden bar passed: start/finish, no key-repeat toggle, focus preserved, Bengali inserted into an owned external editor and keyboard resumed. Actual floating-bar clicks and inactive hover shortcut also passed with immediate delivery (`artifacts/voice-speed-shortcut-probe.log`, `voice-speed-floating-probe.log`). These use fixture capture/recognition, without live microphone capture or physical key/mouse testing.
- Final clean PyInstaller/Inno builds passed. All thirteen embedded modules plus main match final source; required assets present and optional model weights/PocketSphinx excluded. Fresh-folder EXE with empty profile/System32-only PATH passed Light/Dark alpha, online Bengali and automatic pause before model download, explicitly prepared Tiny offline English, normal hook startup and graceful close (`artifacts/voice-speed-package.log`). Additional **packaged 48 kHz Bengali and English automatic-pause requests** preserved both complete fixture phrases without offline weights (`artifacts/voice-speed-packaged-48k.json`). Diagnostic processing time includes accelerated local fixture replay and is not realtime end-of-speech latency.
- Actual temporary install/reinstall/uninstall passed: default-checked startup, quoted Run command, developer/Facebook metadata, startup-off removal and retained user data. Original registry/shortcut state restored; user copy left running. Installed Dark ten-second app-process sample: **133.25 MiB working set, 74.95 MiB private memory, 0.312% of one CPU core** (`artifacts/installer-0.4.11.log`). Sample is not a low-end hardware guarantee. Existing updater installation mechanism was not separately retested this release; its unchanged code and full unit suite passed.

Limits: recognition remains completed-phrase based, without live partial text. Internet/server time still dominates many requests. Earlier automatic finish can end a deliberate thinking pause; use manual/hold mode for those. Live microphone latency/accuracy and other PCs were not measured. Installer remains unsigned.

# Historical 0.4.10 verification

Delivered `dist/0.4.10/JoyKeyboard-Setup.exe`, **94,995,288 bytes** (95.0 MB). SHA-256: `9fcc1b7db4020a5375196df7af48d61edd908d2467d2145c54a51bf8e4a3bfea`. Installer/checksum: [v0.4.10](https://github.com/sohaibjoy0178/joykeyboard/releases/tag/v0.4.10). The existing repository is now public, confirmed through unauthenticated API/download access and the user's confirmation; no separate update repository or credentials are needed.

## Stable updates with installation permission

Installed copies check GitHub latest published stable releases about ten seconds after startup and every six hours. Automatic checks defer during voice work; ready updates wait for user choice. Preferences has automatic-check/download toggle, status, manual check and Install controls. Existing bar/tray menus expose updates; tray notifications announce availability and readiness without enlarging the bar. Drafts, prereleases, same/older versions and plain code pushes do not trigger installation.

Updater uses a separate existing Job/QThread, strict numeric versions, bounded JSON/file sizes, fixed repository/asset identity, trusted GitHub HTTPS redirects, published size/SHA-256 checks, atomic partial-file replacement and cache reuse only after verification. No bundled token, new runtime dependency or rapid polling. Disable automatic checks/downloads in Preferences; manual checks remain available.

Installing requires an explicit Yes (No is default), idle voice/assistant work and existing unsaved-document/word-edit checks. A hidden Windows PowerShell helper waits for the app process to exit, rechecks SHA-256 with built-in .NET, runs the installer without Windows restart or forced application closure, preserves install directory/startup choice, and reopens the app. A changed file or installer failure leaves an error record and reopens the existing app. Source/development builds can check/download; in-app installation is offered from a frozen EXE. Install 0.4.10 once to bootstrap this feature in older copies.

## Executed checks

- **244 pytest tests passed**, `artifacts/tests-0.4.10.log`: strict release versions (including 0.4.10 > 0.4.9), draft/prerelease/older filtering, asset URL/digest/size validation, untrusted HTTPS/redirect rejection, API rate-limit/offline/oversize errors, cached installer verification, corrupt/truncated/oversized/cancelled downloads, partial cleanup, helper quoting and hash recheck, changed-file refusal, permission No/default/unsaved-document cancellation, approval handoff, recording refusal, launch failure, independent workers, manual checks with auto disabled, pending-ready retention and safe quit cancellation. Existing keyboard, voice, hover, themes, settings and document tests passed. Two upstream Python 3.12 deprecation warnings remain.
- Downloaded the actual public v0.4.9 installer through the production updater without authentication and verified all **94,988,171 bytes** against GitHub SHA-256 (`artifacts/public-update-download-check.json`). Current release metadata/asset sizes and digests are also verified during publication.
- Actual temporary **0.4.9 → 0.4.10** installation through the helper passed (`tests/updater_install_probe.py`, `artifacts/updater-install-check.json`, `updater-install-final.log`). An installer deliberately altered after helper launch was rejected specifically by SHA-256 and the old app reopened visibly. A valid installer then silently upgraded and reopened a visible bar. Saved dark theme/custom shortcut, learned-word data, model sentinel and startup-off state survived. Target path included spaces, apostrophe and literal `$()` to exercise quoting. Original registry/shortcut state restored; user's running copy untouched. Clean-environment testing caught a missing PowerShell `Get-FileHash` command; final helper uses .NET directly and passed the same limited-PATH test.
- Final clean PyInstaller/Inno builds passed. All **thirteen embedded modules plus main**, including updater, match final source; required assets present; optional Whisper weights/PocketSphinx remain excluded (`artifacts/package-code-check.json`).
- Final fresh-folder packaged app with empty user profile/System32-only PATH passed default Light/saved Dark alpha checks, Google Bengali and local automatic pause before any Whisper model download, explicit Tiny preparation and packaged offline English with Hub network access disabled, normal hook startup and graceful close (`artifacts/standalone-check.json`, `updates-package-final.log`). Shared source model-preparation path was used for this fixture download; frozen Preferences download click was not separately automated. Hub warnings did not prevent download.
- Rendered and inspected the new Dark Preferences update controls. Bar geometry remains 384×48 and hover shortcuts remain intact. No new floating control or animation/capture loop.
- Ruff, pip dependency validation and Git whitespace checks passed. No new runtime dependency. A new idle-performance benchmark was not run; update network/hash work is active work rather than an idle-resource guarantee.

Limits: installer unsigned; GitHub SHA-256 verifies integrity, not an Authenticode publisher certificate. Internet/GitHub availability and request limits apply. Windows PowerShell/installer policy may block installation. Other PCs/Windows 10 hardware, portable one-file update behavior and live microphone quality were not checked. Transcript is not automatically saved by updating; confirmation tells users to save/copy it first. Existing voice accuracy/service and sixty-second recording limits remain.

# Historical 0.4.9 verification

Delivered `dist/0.4.9/JoyKeyboard-Setup.exe`, **94,988,171 bytes** (95.0 MB). SHA-256: `2cf3709ecd38b2075f5272fa6e33323cf994bcc0d7794ea119198a5bdb33cd5f`. Installer/checksum: [v0.4.9](https://github.com/sohaibjoy0178/joykeyboard/releases/tag/v0.4.9). Private repository access required.

## Hover shortcut instructions on the compact bar

Hover Speak/Stop to see the saved voice shortcut, press-once/start-again/stop instructions and where to customize keys. The bar remains **384×48** with the same rounded transparent Light/Dark surfaces. Shortcut text occupies only the tooltip. Recording action reads **Stop**; listening details also show the configured shortcut. The top-level bar enables Qt's `WA_AlwaysShowToolTips`, allowing tips while another app keeps typing focus. No new dependency or background timer. Optional offline downloads and compact packaging retained.

## Executed checks

- **200 pytest tests passed**, `artifacts/tests-0.4.9.log`. New Light/Dark cases dispatch a tooltip event and verify the actual visible tooltip includes a saved custom chord and stop instructions, without recording or changing 384×48 geometry. Checks also cover default reset, recording Stop tooltip, keyboard, voice, conflicts, settings and transparency. Two upstream Python 3.12 deprecation warnings remain.
- Actual Windows pointer hover over the inactive bar displayed the shortcut while an owned external editor retained focus. Native keyboard/voice clicks also preserved focus and fixture Bengali text reached that editor (`tests/floating_native_probe.py`, `artifacts/floating-native-result.json`). Probe uses a disposable profile and restores pointer position; no physical mouse or live microphone used. Inspected the actual tip capture (`artifacts/voice-hover-tip.png`).
- Rendered Light/Dark bar previews match the prior compact bar images; no permanent key badge or width change. All tool/menu preview captures executed from disposable data.
- Final clean PyInstaller/Inno builds succeeded. Twelve embedded modules plus main matched final source; required assets present; Whisper weights and PocketSphinx data remain excluded (`artifacts/package-code-check.json`).
- Fresh-folder packaged app with empty profile and System32-only PATH passed default Light/saved Dark alpha checks, Google Bengali and automatic-pause Bengali without offline weights, explicit Tiny download through the shared source preparation path, packaged offline English with Hub network access disabled, normal hook startup and graceful close (`artifacts/standalone-check.json`). Frozen Preferences download button was not separately automated. Upstream Hub symlink deprecation/rate-limit advice did not prevent download.
- Actual temporary install/reinstall/uninstall passed: default-checked autostart, quoted Run command, developer/Facebook metadata, disabling autostart, normal startup/graceful quit, startup removal and preserved user data. Original startup/shortcut state restored; user's running copy untouched (`artifacts/installer-check.json`).
- Installed Dark idle ten-second sample: **129.61 MiB working set**, **74.46 MiB private memory**, **0.000% of one CPU core** at counter resolution. App-process-only sample excluding compositor/GPU; does not establish zero CPU use or a low-end ceiling.
- Ruff, pip dependency validation and Git whitespace checks passed. Installer checksum included with release.

Installer unsigned. Other PCs/Windows 10 hardware, physical input and live microphone quality not checked. Global shortcut requires the app running; existing online availability, offline accuracy and sixty-second recording limits remain.

# Historical 0.4.8 verification

Delivered compact `dist/0.4.8/JoyKeyboard-Setup.exe`, **94,973,054 bytes** (95.0 MB / 90.6 MiB), down from **322,302,837 bytes**: **70.5% smaller**. SHA-256: `3dd14f013d19b46addad2a246363aad687a9f7af93b7a7f49e1b080af1544b61`. Installer/checksum: [v0.4.8](https://github.com/sohaibjoy0178/joykeyboard/releases/tag/v0.4.8). Private repository access required.

## Smaller installer with optional offline downloads

Measured prior payload: Base/Tiny weights alone consumed **210.53 MiB**; SpeechRecognition data occupied 42.48 MiB, including unused PocketSphinx models and encoders for other platforms; developer preview images occupied 3.81 MiB. Model weights now download only through the existing explicit Preferences action, as requested. A custom packaging hook includes SpeechRecognition's required version file and Windows FLAC encoder, omitting unused data. Only the three README previews are packaged. Speech engines, CPU inference runtime, audio codecs, local Silero pause detection, keyboard dictionaries, Qt rendering fallbacks and licenses remain. Uncompressed runtime payload measures **346.81 MiB**, before optional model downloads.

Online voice typing and local pause detection work immediately with internet. To use offline voice, choose Tiny/Base/Small under Preferences → Local recognition and click Download offline model once. Afterward inference works without internet. Cached user models remain supported; no automatic downloads were introduced. Preferences/Help/README explain this change. Both transparent themes and the rounded bar fix are retained.

## Executed checks

- **198 pytest tests passed**, `artifacts/tests-0.4.8.log`, covering existing voice, explicit-download-only behavior, missing-model handling, cached/bundled model lookup, UI, shortcuts, keyboard and transparency checks. Two upstream Python 3.12 deprecation warnings remain.
- Clean PyInstaller/Inno builds passed. All twelve embedded modules plus main matched final source. Required dictionaries, icons, Windows FLAC encoder, Silero ONNX model and notices found. Both Whisper weight files and PocketSphinx data absent (`artifacts/package-code-check.json`). Build log confirms project SpeechRecognition hook loaded.
- Actual compact EXE ran from a fresh folder with System32-only PATH and empty profile. Default Light/saved Dark pixel checks passed. Google Bengali recognition and automatic pause Bengali passed **before any offline model was downloaded** (`artifacts/standalone-check.json`).
- Downloaded Tiny through the source Recognizer's existing explicit preparation path into a disposable profile with no bundled-model fallback. The packaged EXE then transcribed the English fixture using that cached model with `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`. This exercises real model download plus packaged offline inference; clicking Preferences download in the frozen UI was not automated. Upstream Hub emitted unauthenticated rate-limit advice and a deprecated symlink-argument warning, without blocking download.
- Packaged normal hook startup/graceful close passed. Native packaged keyboard event probe stopped at its focus-preservation guard after another window became foreground, before typing. It was not repeatedly retried against an active desktop; this release's manual-keyboard regression check is incomplete. Keyboard composition/hook source is unchanged, and the full unit suite passed.
- Actual temporary install/reinstall/uninstall passed: default checked autostart, quoted Run command, developer/Facebook metadata, disabling autostart, startup/graceful quit, startup removal on uninstall and preserved user data. Startup and shortcut state restored; user's app not overwritten or terminated (`artifacts/installer-check.json`).
- Installed Dark Glass ten-second idle sample: **130.01 MiB working set**, **74.62 MiB private memory**, **1.250% of one CPU core**. App-process-only sample on this development PC, excluding DWM/GPU. Not a universal performance ceiling; package size reduction does not establish a CPU/RAM reduction.
- Ruff, pip dependency check and Git whitespace validation passed. Installer SHA-256 accompanies release.

Installer unsigned. Other PCs/Windows 10 hardware and live microphone quality not checked. Online speech needs internet and has existing service/accuracy limits. Offline setup now requires one explicit model download; first-time offline speech is unavailable until that finishes. No engine guarantees perfect Bengali accuracy.

# Historical 0.4.7 verification

Delivered `dist/0.4.7/JoyKeyboard-Setup.exe`, **322,302,837 bytes**. SHA-256: `64ab485cca3eeae42db4277720c0a671c323db00015f8b52a534d03f72139139`. Installer/checksum: [v0.4.7](https://github.com/sohaibjoy0178/joykeyboard/releases/tag/v0.4.7). Private repository access required.

## Rounded floating bar without square backing

Windows native accent blur paints a rectangle outside the floating bar's rounded per-pixel surface, despite Qt's rounded window mask. The bar now explicitly disables that effect, retaining the existing transparent painted shell, reflected edges, shape and Light Glass/Dark Glass choices. Workspace blur remains enabled. No new dependency, rendering loop or background capture is added. README bar previews are raw RGBA PNGs with transparent corners rather than rectangular desktop crops.

## Executed checks

- **198 pytest tests passed**, `artifacts/tests-0.4.7.log`. Two new theme cases ensure bar show, hide/reveal, feedback and theme application never enable native rectangular blur. Existing keyboard, voice, settings, transparency and geometry checks passed. Two upstream Python 3.12 deprecation warnings remain.
- Actual Windows compositor check over an owned static striped backdrop passed all six cases: Light/Dark idle, feedback and candidates (`tests/glass_native_probe.py`, `artifacts/glass-native-check.json`). Every fully transparent pixel was compared before/after showing the bar: **maximum outside RGB difference 0** in each case, across 3,024–3,849 pixels. Shell alpha **140/255 Light**, **165/255 Dark**, with visible background variation **49.50/38.50** respectively. This verifies transparent corners and absence of the rectangular backdrop, including expanded states. Native bar blur is intentionally absent.
- Actual Light/Dark raw bar PNGs inspected and committed under `docs/screenshots/glass-light-bar.png` and `glass-dark-bar.png`. Workspace, tools, menus and candidate captures also executed with disposable profiles. Capture backdrop exists only in test harnesses.
- Native source keyboard/voice focus checks and custom global shortcut start/finish with hidden bar, no repeat and keyboard resume passed. Audio/recognizer use fixtures for these flow tests (`artifacts/floating-native-result.json`, `voice-shortcut-check.json`).
- Packaged actual Windows input passed saved Dark Glass/custom voice chord, hidden-bar shortcut dispatch, fast multiword Bangla, Backspace and native password pass-through. No physical input hardware was exercised (`artifacts/packaged-keyboard-event-check.json`).
- Final clean PyInstaller/Inno builds succeeded. All twelve embedded modules plus main matched final sources, and required assets/models were present (`artifacts/package-code-check.json`).
- Fresh-folder packaged app with empty user cache and System32-only PATH passed Light/Dark alpha and tint checks, bundled Base offline English, Google online Bengali, automatic pause Bengali, normal hook startup and graceful close (`artifacts/standalone-check.json`). No Python installation or model downloads used.
- Real temporary install/reinstall/uninstall passed: default-checked autostart, quoted Run command, developer/Facebook metadata, disabling startup, normal startup/graceful quit, uninstall startup removal and user-data preservation. Original startup/shortcut state restored; user's running app was not overwritten or stopped (`artifacts/installer-check.json`).
- Installed Dark Glass ten-second idle sample: **129.72 MiB working set**, **74.39 MiB private memory**, **0.000% of one CPU core** at the counter's resolution. App-process-only sample on this Ryzen 9 Windows 11 PC; excludes compositor/GPU cost and does not establish zero CPU use or a low-end-device ceiling.
- Ruff, pip dependency validation and Git whitespace checks passed. Installer checksum included with release.

Installer unsigned. Other PCs, Windows 10 hardware, physical keyboard/mouse and live microphone quality were not checked this release. Voice engine accuracy/service availability limits remain. Workspace blur uses an optional undocumented Windows API; effects vary with Windows settings and drivers. Floating bar retains transparency without backdrop blur.

# Historical 0.4.6 verification

Delivered `dist/0.4.6/JoyKeyboard-Setup.exe`, **322,297,467 bytes**. SHA-256: `a11632cd99425e28be4c15b2cfaf35033c37cf012e2b28f5dfec06c1c38ae406`. Installer/checksum: [v0.4.6](https://github.com/sohaibjoy0178/joykeyboard/releases/tag/v0.4.6). Source/previews committed; private repository access required.

## Both Light and Dark with transparent glass

Two permanent choices: **Light Glass** and **Dark Glass**, both with real per-pixel transparency, Windows compositor blur and reflective edges. Light uses silver tint/navy text; Dark uses smoke tint/ivory text. Outer material and tool/input overlays remain translucent in both modes. Foreground stays crisp at 100% bar opacity. Theme switches immediately in bar menu or Preferences and persists after restart. Saved light/dark choices remain intact; legacy Clear Glass maps to Light Glass. Bar footprint stays 384×48 logical pixels; keyboard, voice, drafts, startup and credit behavior retained.

## Executed checks

- **196 pytest tests passed**, `artifacts/tests-0.4.6.log`. Parameterized live switch/save/restart, native-blur fallback and actual alpha pixels for **each** theme; two menu choices required; retained transcript, shortcut, opacity and live error colors; legacy settings migration; dark/light contrast reference pairs. Existing voice/keyboard/document/native API checks passed. Two upstream Python 3.12 deprecation warnings remain.
- Real compositor blur verified independently in both themes over an owned striped backdrop (`artifacts/glass-native-check.json`, `tests/glass_native_probe.py`). Light red-channel variation: **0.69 with blur vs 49.50 without**; Dark: **0.52 with blur vs 38.50 without**. Restoring blur restored low variation. This proves background blur in both modes rather than opaque gradients or whole-window fading.
- Actual UI captures inspected for Light/Dark bar, Dark studio and Light/Dark Settings; both themes captured across all six writing tools, candidate words, Help and menus. Composited previews under `docs/screenshots/` use the same controlled owned test backdrop; no product wallpaper or capture loop. Dark outer labels/status use brighter text for readable glass over bright backgrounds.
- Native source Dark Glass focus/keyboard/voice fixture insertion passed (`artifacts/floating-native-result.json`). Real custom global chord start/finish with hidden bar, no repeat and keyboard resume passed (`artifacts/voice-shortcut-check.json`). These flow checks use fixture microphone/recognizer stubs with real Windows events.
- Actual packaged Dark Glass startup with saved custom shortcut passed hidden-bar dispatch, fast multiword Bangla input, Backspace and native password pass-through (`artifacts/packaged-keyboard-event-check.json`). Missing Small model prevents real microphone capture in packaged shortcut-dispatch test.
- Final clean PyInstaller/Inno builds succeeded. All twelve embedded modules plus main matched final source and required models/assets were present (`artifacts/package-code-check.json`).
- Fresh-folder packaged app, System32-only PATH/no Python environment: default Light Glass and saved Dark Glass **both** passed translucent alpha and correct tint pixel assertions. Bundled Base offline English, Google online Bengali, automatic speech-pause Bengali, normal hook startup and graceful close passed (`artifacts/standalone-check.json`). No model downloads.
- Actual installer install/reinstall/uninstall passed: checked-by-default sign-in startup, quoted Run command, developer/Facebook metadata, removal when unchecked, normal startup/shutdown and preserved user data. Original registry/shortcut state restored (`artifacts/installer-check.json`). Existing user's app copy not terminated or overwritten.
- Installed Dark Glass idle ten-second sample: **129.45 MiB working set**, **74.29 MiB private memory**, **0.156% of one CPU core**. App-process-only measurement on this Ryzen 9 Windows 11 PC; excludes compositor/GPU cost and is not a low-end-device ceiling. Recording/transcription costs more.
- Ruff, pip dependency check and Git diff whitespace checks passed. No new runtime dependency or continuous repaint/capture timer.

Blur uses an optional undocumented Windows composition API with denser translucent fallback in the selected theme. Effects/contrast vary with Windows settings, drivers and background. Native popups retain matching readable surfaces; OS dialogs retain Windows appearance. Apple-inspired Windows treatment, not Apple's renderer. Installer unsigned. Windows 10, other PCs/VMs, physical keyboard/mouse and live microphone quality were not verified this release. Existing offline-Bengali accuracy and online-service availability limitations remain.

# Historical 0.4.5 verification

Delivered `dist/0.4.5/JoyKeyboard-Setup.exe`, **320,222,354 bytes**. SHA-256: `1fbb64a2a8b74f3875134bf3b65de81b3643fe42dba2c77926dc16150f9d50d5`. Installer and checksum are release assets at [v0.4.5](https://github.com/sohaibjoy0178/joykeyboard/releases/tag/v0.4.5); source and actual UI previews are in Git. Private-repository access required.

## Actual Clear Glass

Clear Glass replaces the former Dark Glass choice: real alpha surfaces over Windows compositor blur, neutral silver tint, thin reflected rims and crisp navy text/blue controls. New profiles default to Clear Glass; saved Dark Glass migrates to Clear Glass. Existing Light Glass remains opaque. Preferences and bar Theme menu switch and save immediately. Studio, all six writing tools, inputs and suggestions use translucent layers; popup/native menus remain opaque for readability. No simulated product wallpaper, continuous desktop capture, refraction shader, animation timer or new runtime dependency. Native windows are rounded and the bar remains 384×48 logical pixels. At 100% opacity, foreground controls remain opaque while Clear Glass material is translucent.

Qt's Windows per-pixel transparency requires a frameless workspace. Added draggable title, title double-click maximize/restore, minimize, close-to-bar and a resize grip. Existing drafts, keyboard/voice state, shortcuts, credits and startup behavior retained.

## Executed checks

- **189 pytest tests passed**, `artifacts/tests-0.4.5.log`. Settings migration/validation/atomic roundtrip; live all-surface switch retaining transcript, shortcut and opacity; actual alpha pixels; saved theme launch; native API arguments with full-width HWND; unavailable/rejected blur fallback; frame/maximize/restore/resize; existing voice, keyboard and document checks. Two upstream Python 3.12 deprecation warnings remain. Contrast checks cover opaque reference surfaces and sample glass control backgrounds, not arbitrary desktops.
- Actual compositor test over an owned striped backdrop passed: red-channel variation **0.69 with blur vs 49.50 without**, restored to 0.69 after enabling again (`artifacts/glass-native-check.json`, `tests/glass_native_probe.py`). Shows real background blur rather than merely painted gradients or whole-window fading. Captures cover our owned backdrop and app. Real UI previews over an owned controlled gradient backdrop committed under `docs/screenshots/`; the backdrop is test-only.
- Dark-background legibility improved with a neutral shell alpha floor of 140/255. Unavailable native blur uses denser 210/255 tint; Light Glass offers consistently opaque surfaces. Pixel contrast still depends on actual background and transparency settings.
- Native source checks under Clear Glass passed: real Windows editor focus preservation for keyboard/voice clicks and fixture Bengali voice insertion (`artifacts/floating-native-result.json`). Custom global chord start/finish with hidden bar, repeat suppression, focus preservation and keyboard resume passed (`artifacts/voice-shortcut-check.json`). Audio/recognizer are fixture stubs in these flow checks.
- Actual packaged EXE passed saved Clear Glass/custom Ctrl+Alt+Shift+F9, hidden-bar shortcut dispatch, fast multiword Bangla, Backspace and native password pass-through (`artifacts/packaged-keyboard-event-check.json`). The probe now waits for the bar to be visible before input: glass creates a hidden native handle earlier than previous releases. This fixed a test startup race. Missing Small model prevents microphone capture in the packaged shortcut check. Additional posted-message route check passed (`artifacts/packaged-hotkey-message-check.json`); this auxiliary check is not a real chord test.
- Clean PyInstaller/Inno builds succeeded. Twelve embedded modules plus main matched final sources; required models/assets found (`artifacts/package-code-check.json`).
- Fresh-folder packaged app with System32-only PATH passed default translucent Clear Glass, saved opaque Light Glass pixel checks, bundled Base offline English, Google online Bengali, automatic pause finishing, normal hook startup and graceful shutdown (`artifacts/standalone-check.json`). No Python environment or model downloads required.
- Actual installer install/reinstall/uninstall passed: default checked autostart, quoted Run command, developer/Facebook metadata, startup removal when unchecked, normal startup/shutdown and preserved user data. Original registry/shortcut state restored (`artifacts/installer-check.json`). Existing user's running JoyKeyboard copy was not terminated or overwritten.
- Installed Clear Glass idle ten-second sample: **129.61 MiB working set**, **74.19 MiB private memory**, **0.469% of one CPU core**. This measures the app process on this Ryzen 9 Windows 11 PC, excluding compositor/GPU cost. Not a low-end-device ceiling or certification; recording/transcription costs more.
- Ruff and pip dependency checks passed.

Windows blur uses an optional undocumented composition entry point with explicit failure handling. Future Windows versions, policies, remote sessions or drivers may change appearance/support; opaque Light Glass remains available. This is a Windows approximation, not Apple's proprietary Liquid Glass renderer. Installer unsigned. Windows 10, a second PC/VM, physical keyboard/mouse and live microphone quality were not checked this release. Native OS dialogs retain Windows styling. Existing offline-Bengali accuracy and online-service availability limitations remain.

# Historical 0.4.4 verification

Delivered `dist/0.4.4/JoyKeyboard-Setup.exe`, **319,098,846 bytes**. SHA-256: `c692af7e464f8cefb319925358d2ee525018b77bf3881edfe37c0b788ba4c434`. Installer and checksum are release assets at [v0.4.4](https://github.com/sohaibjoy0178/joykeyboard/releases/tag/v0.4.4); source and actual UI preview images are in Git. Private-repository access is required.

## Light and Dark Glass

Select **bar menu → Theme → Dark Glass**, or **Preferences → Appearance & startup → Theme**. Black/charcoal reflected surfaces and ivory text cover studio, all six tools, inputs, suggestions, error states, popup menus and tray menu. Light Glass remains available and is the default for old/missing/invalid settings. Theme switches immediately, is saved atomically with preferences and is restored at launch. Transcript, voice shortcut and independently chosen opacity are preserved. Static Qt painting adds no blur/capture loop, animation timer or dependency. Idle bar stays 384×48 logical pixels, opaque at 100% with clear rounded corners.

## Executed checks

- **189 pytest cases passed**, `artifacts/tests-0.4.4.log`. New checks execute theme migration/validation/roundtrip, all-surface switching via bar menu, real preference saves, saved-dark launch, retained transcript/shortcut/opacity, live error-color changes and dark shell pixels/clear corners. Light/dark primary, muted, selected, recording and error text contrast checks passed (4.5:1 minimum for the tested pairs). Existing voice, keyboard, document, geometry and global shortcut tests passed. Two upstream Python 3.12 deprecation warnings remain.
- Actual light/dark UI captures inspected for bar, Bangla candidates, studio, Settings, converter, Help and main menu. All six tool pages captured. `tests/render_glass_probe.py` uses disposable profile/sample text and no microphone/network. Selected captures committed under `docs/screenshots/`.
- Native Windows editor checks under Dark Glass passed: showing bar, keyboard click and voice click preserved destination focus; fixture Bengali voice result inserted correctly (`artifacts/floating-native-result.json`). Full custom global shortcut start/finish with hidden bar, repeat suppression, focus preservation and keyboard resume passed (`artifacts/voice-shortcut-check.json`). These use fixture microphone/recognizer stubs with actual Windows registration and input.
- Actual packaged app launched with saved Dark Glass and custom Ctrl+Alt+Shift+F9. Hidden-bar shortcut dispatch, multiword/fast Bangla input, Backspace and native password pass-through passed (`artifacts/packaged-keyboard-event-check.json`). Intentionally absent Small model prevented real microphone capture in that shortcut-dispatch probe.
- Clean PyInstaller and Inno Setup builds passed. All twelve embedded modules plus main matched final sources; required assets/models found (`artifacts/package-code-check.json`).
- Fresh-folder packaged app passed default Light Glass and saved Dark Glass UI checks, including actual screenshot pixel assertions, with System32-only PATH and no Python environment. Bundled Base offline English, Google online Bengali, automatic speech-pause Bengali, normal hook startup and graceful close passed (`artifacts/standalone-check.json`). No model downloads.
- Actual single-EXE install/reinstall/uninstall passed: checked-by-default autostart, quoted Run command, developer/Facebook publisher values, startup removal when unchecked, normal startup/shutdown and preserved user data. Original registry/shortcut state restored (`artifacts/installer-check.json`).
- Installed **Dark Glass** idle ten-second sample: **126.53 MiB working set**, **71.21 MiB private committed memory**, **0.625% of one CPU core**. Measurement on this Ryzen 9 Windows 11 development PC, not a universal ceiling or low-end certification. Recording/transcription uses more resources.
- Ruff and pip dependency checks passed. No new runtime dependencies. User's existing app was not force-terminated.

Installer remains unsigned. No second PC/VM, full third-party application matrix, physical keyboard or live microphone quality check this release. Native OS dialogs/title bars follow Windows behavior; app themes do not change Windows itself. Existing offline-Bengali accuracy and online-service availability limitations remain.

# Historical 0.4.3 verification

Delivered `dist/0.4.3/JoyKeyboard-Setup.exe`, **318,743,432 bytes**. SHA-256: `89324f45b507a9b077e6e8e7834d4511ba1e2b43d5bb4ac022aff8c078a33fec`. Installer and checksum are release assets at [v0.4.3](https://github.com/sohaibjoy0178/joykeyboard/releases/tag/v0.4.3); source and preview images are in Git. Private-repository access is required.

## Pearl Glass interface

Shared silver/blue light theme covers studio, Settings, every writing-tool tab, popup menus, inputs and state feedback. Compact bar uses a static painted shell with reflected highlights, white rim and a fine lower edge; original SVG/PNG/ICO artwork matches. Bar stays 384×48 logical pixels. 100% opacity remains fully opaque inside rounded clear corners; existing 70/80/90% options remain available. No continuous blur, desktop capture, shader, background animation or added runtime dependency. This is Apple-inspired styling, not Apple's native Liquid Glass framework.

Explicit Nirmala UI fallback keeps Bengali controls/transcript/candidates readable even when automatic font fallback chooses a legacy font. Default launch, workspace navigation, keyboard/voice controls, custom global shortcut, credit/Facebook link, data-loss checks and autostart are preserved.

## Executed checks

- **178 pytest cases passed**, `artifacts/tests-0.4.3.log`. New checks verify primary/error/recording/muted text contrast of at least 4.5:1 and the bar's opaque light shell, clear corner and absence of graphics effects. Existing geometry, opacity, voice, keyboard, document and shortcut tests passed. Two upstream Python 3.12 deprecation warnings remain.
- Actual UI captures inspected for idle bar, Bengali candidates, voice studio with sample text, Settings, keyboard tools, converter, screen keys and DocPad. `tests/render_glass_probe.py` renders from disposable local data without recording/network. Repo preview images: `docs/screenshots/`.
- Real native editor focus and voice fixture insertion passed with the new bar: `artifacts/floating-native-result.json`. Global shortcut start/finish with bar hidden, no repeat and keyboard pause/resume passed: `artifacts/voice-shortcut-check.json`. These flow tests use fixture microphone/recognizer stubs, actual Windows input and registration.
- Actual packaged app loaded the saved custom voice shortcut with bar hidden and passed multiword Bangla, fast typing, Backspace and native password pass-through: `artifacts/packaged-keyboard-event-check.json`.
- Clean PyInstaller/Inno builds passed. Twelve embedded modules plus main matched final sources, including shared theme; required models/assets found: `artifacts/package-code-check.json`.
- Fresh-folder packaged UI, bundled Base offline English, Google online Bengali, automatic speech-pause Bengali, normal startup and graceful shutdown passed with System32-only PATH, empty app data and downloads disabled: `artifacts/standalone-check.json`.
- Actual installer install/reinstall/uninstall passed, including startup checkbox default/removal, developer/Facebook publisher values, preserving user data and restoring original test registry/shortcut state: `artifacts/installer-check.json`.
- Installed idle ten-second sample: **124.48 MiB working set**, **70.02 MiB private committed memory**, **0.469% of one core**. Source smoke probe: 131.77 MiB, 75.97 MiB, 0.937% of one core: `artifacts/glass-idle.json`. Measurements on this Ryzen 9 Windows 11 development PC, not universal ceilings or old-hardware certification. Capture/recognition uses additional resources.
- Ruff and pip dependency check passed. ICO renderer validated all ten Windows icon sizes.

Installer remains unsigned; no second PC/VM, full application matrix, live physical keyboard or live microphone quality check. Existing offline-Bengali and online-service limitations still apply. No user app was force-terminated.

# Historical 0.4.2 verification

Delivered `dist/0.4.2/JoyKeyboard-Setup.exe`, **318,595,240 bytes**. SHA-256: `81bba8b113debe76bfdae1a7d7f7717bdec46db7f752d16d4a675382d4bb2232`.

## Custom global voice shortcut

Preferences now records one chosen key chord with Apply and Reset default. Default Ctrl+Alt+Space toggles start/finish; the same shortcut is shown in studio, tray, bar tooltip and the bar's shortcut-settings route. The shortcut is persisted and restored at startup. Editing the field does not activate the microphone. F12 remains keyboard mode; bare F1–F8 remain suggestion selection. Ordinary unmodified typing and invalid/multi-step/reserved combinations are rejected.

Windows RegisterHotKey with MOD_NOREPEAT delivers WM_HOTKEY to Qt's native event filter. Replaces the former 40ms voice-key polling, so quick presses do not depend on a polling tick. Failed registration preserves the previous chord; failed settings saves restore it. Closing the app releases registration. Right-Ctrl hold recording and automatic pause finishing remain available. Disable automatic finishing if only the global shortcut should finish a clip.

Execution evidence:

- **169 pytest cases passed**, `artifacts/tests-0.4.2.log`: migration/validation, conflict handling, real Windows competing registrations/release, native-message routing, rollback on save failure, actual shortcut-editor key capture/Apply, live hints/reset and edit-without-recording. Existing keyboard/voice/tools protections passed too.
- Full native global start/finish flow against a separate owned editor, with the bar initially hidden and keyboard mode ON. Actual global chord started recording, repeated down event did not stop it, release/new press finished it, Bengali transcript was inserted into the original editor, and keyboard mode resumed. Microphone and speech recognition were fixture stubs for this test; actual Windows registration, Qt events, input hook and Unicode insertion were used. `artifacts/voice-shortcut-check.json`.
- Actual packaged app launched with saved Ctrl+Alt+Shift+F9 and System32-only PATH. After hiding its bar to the tray, Windows key input triggered the saved shortcut and revealed the missing-model error. An intentionally absent Small model prevented any microphone capture. This verifies packaged registration/restoration and hidden-bar dispatch; complete start/finish uses the source-flow fixture test above. Manual multiword Bangla, fast input, Backspace and native password pass-through also passed: `artifacts/packaged-keyboard-event-check.json`.
- Delivered embedded code matched all eleven current modules plus main; models/assets verified. `artifacts/package-code-check.json`.
- Fresh-folder packaged UI, bundled offline Base English, Google Bengali, automatic-pause Bengali, normal hook startup and graceful shutdown passed: `artifacts/standalone-check.json`. No model downloads or Python on PATH.
- Real installer install/reinstall/uninstall passed with autostart and developer/Facebook values intact; preserves settings and restores test registry/shortcut state. `artifacts/installer-check.json`. Fresh installed idle working set 122.51 MiB, private commit 66.88 MiB; short ten-second sample CPU 1.094% of one core on this PC, not a performance ceiling.
- Clean PyInstaller/Inno builds, Ruff and pip dependency check passed. Preferences screenshot inspected: `artifacts/shortcut-settings.png`.

References: [Microsoft RegisterHotKey](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerhotkey), [Qt QKeySequenceEdit](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QKeySequenceEdit.html).

Windows secure desktops/lock screens cannot use the app shortcut. Protected/elevated/custom fields can still reject insertion; transcript stays available. No live physical-keyboard, all-app matrix, second-PC or reboot test. Installer unsigned. Existing user apps were not terminated. Existing speech-quality limitations remain.

# Historical 0.4.1 verification

Delivered `dist/0.4.1/JoyKeyboard-Setup.exe`, **318,605,911 bytes**. SHA-256: `2b5d1fd2674e43cc8493ecb31b31b0211a51fea1dac7578c78530367dc9f02bb`.

## Developer credit

Added **Developed by Sohaib Islam Joy** and `https://www.facebook.com/sohaib.islam1997` to Help, the bar's developer-credit route, README and installer. Installer welcome text includes the credit and URL; Windows uninstall metadata identifies Sohaib Islam Joy as publisher and includes the requested Facebook publisher link. UI routing/link assertions and actual installed publisher registry values passed.

## Manual keyboard fixes and evidence

- Reproduced English pass-through with keyboard ON using real Windows virtual-key input into a separate native Edit window. The hook rejected all events marked injected, including remapped/on-screen input. Output now carries JoyKeyboard's own `dwExtraInfo` marker; only that output is ignored for composition, preventing recursion while allowing external virtual-key input. Injected F12 remains excluded from mode toggling.
- A fast multiword test then reproduced dropped letters: native caret movement from JoyKeyboard's previous insertion arrived after the next composition started. It was mistaken for a user caret movement, discarding the first letter. The commit path now pumps pending hook input and allows bounded native caret settling (20ms stable within a 100ms limit) before beginning another word. Focus/password checks remain enforced. Slow/custom editors may still require different integration; this is a Windows hook, not TSF inline composition.
- Dictionary loading/fuzzy suggestions run on a separate worker, without delaying word insertion. Only the latest queued request is retained; revision checks reject stale candidates after commit/clear. A blocking-suggestion regression test proves the word can commit before suggestions finish and old candidates do not return.
- Actual source Windows-event test passed five consecutive runs, including multiword Bangla at 3ms key intervals, Backspace correction and native password pass-through. A deliberate 1.4-second initial suggestion delay also passed without blocking composition. `artifacts/keyboard-event-check.json`.
- **Packaged application** launched with fresh settings and System32-only PATH. Test clicked its real floating-bar keyboard button, then sent virtual-key events through Windows into a separate native editor. Result: `আমি বাংলায় লিখি আমি বাংলা আমি `. Fast multiword typing, Backspace and unchanged Latin input in a native password field passed. No direct composition calls or recognition stubs used: `artifacts/packaged-keyboard-event-check.json`.
- Existing native hook/output suite rerun: phonetic, English, fixed layout, snippets, candidates, F12, Bijoy output, password guard and balanced deferred modifiers passed: `artifacts/keyboard-native-result.json`. That broader suite feeds physical-event decisions directly and verifies actual native output; it does not prove physical hardware.
- Pending words still appear in the bar until Space/Enter or a candidate commits them. Example: enable **Bangla phonetic**, turn keyboard ON, type `ami`, then Space to insert `আমি`.

Threading reference: [Microsoft LowLevelKeyboardProc guidance](https://learn.microsoft.com/en-us/windows/win32/winmsg/lowlevelkeyboardproc).

## Release validation

- **147 pytest cases passed**, `artifacts/tests-0.4.1.log`. Changed product files, tests and probes passed Ruff; `pip check` passed.
- Clean PyInstaller rebuild and Inno Setup compilation succeeded. Final embedded modules/main matched current source and required assets were verified: `artifacts/package-code-check.json`.
- Fresh-folder packaged UI, offline Base English, Google Bengali, automatic-pause Bengali and normal startup/graceful shutdown passed with no Python on PATH and no model downloads: `artifacts/standalone-check.json`.
- Actual 0.4.1 installer install/reinstall/uninstall passed, including developer publisher/Facebook values, autostart checked by default, unchecked task removing startup, and uninstall preserving settings/removing startup. Original startup/shortcut state restored: `artifacts/installer-check.json`.
- Fresh installed idle working set **121.46 MiB**, private commit **67.46 MiB**. Ten-second CPU sample reported 0 seconds at Windows timer resolution; do not interpret this as a zero-CPU guarantee. Earlier 0.4.0 idle comparisons below remain historical measurements.

No live physical keyboard, complete browser/editor matrix, second PC or sign-in reboot test. Installer remains unsigned. Prior live microphone/loopback and speech-quality limitations still apply. Existing user apps were not force-terminated.

# Historical 0.4.0 verification

Delivered `dist/0.4.0/JoyKeyboard-Setup.exe`, **318,579,537 bytes**. SHA-256: `25e319774509761a33c016162f2faad7c2e42e03c28a81ad26a7f962e26d1819`.

Built/tested on Windows 11, AMD Ryzen 9 7900X (24 logical processors), Python 3.12.10 x64, PySide6 6.12.0, PyInstaller 6.22.3, Inno Setup 6.7.3. Target: Windows 10 1809+/11 Intel/AMD x64; no low-end hardware certification.

## Current installer and startup checks

Actual installer executed in a disposable folder containing spaces. Evidence: `artifacts/installer-check.json` and the recorded test folder's install logs.

- Saved installer INF and HKCU Run value confirm startup is selected by default and the executable path is quoted correctly.
- Installer bundles Python, native runtime, dictionaries and Base/Tiny models. Runtime stays installed; subsequent launches avoid one-file extraction. Distribute only the setup EXE; it creates its installed files automatically.
- Installed UI launched without Python on PATH, with fresh application data. Normal launch initialized the actual keyboard hook and closed gracefully, saving dictionary data.
- Reinstalling with startup unchecked removed its existing Run entry.
- After startup was re-enabled, uninstall removed the entry even though the last installer task was unchecked. Uninstall removed app files and preserved user data.
- Test restored original startup registry state and any existing Start Menu shortcut. No sign-out or reboot performed.
- Preferences controls the same Run value. A real disposable registry test covers enable/disable, repeated disable and quoted paths. UI test covers checkbox wiring and error rollback. Startup never enables recording.
- Build script parsed successfully; clean PyInstaller and Inno compilation passed. Compiler downloaded from official release; Authenticode status verified Valid before use.

## Current appearance and resource checks

- Default bar **384 × 48 logical pixels**, previously 504 × 74. Icon brand, solid surface, fine border; no drop shadow, blur or idle animation. Delivered screenshot inspected: `artifacts/installed-bar.png`.
- Menu and Preferences offer 70/80/90/100% opacity. Default 100% is opaque within rounded shell. Tests execute live changes, persistence validation and invalid/invisible value recovery.
- Regression test confirms 100 unchanged syncs perform no bar layout work; recording controls fit without overlap. Dictionaries load on first suggestions request; startup and voice learning avoid that memory cost.
- Numerical pools bounded by default (OpenBLAS one thread, OMP two; explicit environment settings respected). Offline Whisper uses at most two CPU threads, scaled down on smaller CPUs. Models and loaded dictionaries stay resident for reuse, so recording/transcription and subsequent idle memory can exceed fresh-start figures.

Ten-second visible-idle measurements:

| Measurement | Before, source | After, source with thread limits | Installed app |
| --- | ---: | ---: | ---: |
| Working set | 194.81 MiB | 125.61 MiB | 121.26 MiB |
| Private committed memory | 879.15 MiB | 72.43 MiB | 67.30 MiB |
| CPU, percent of one core | 9.526% | 0.469% | 0.469% |

Evidence: `artifacts/idle-before.json`, `artifacts/idle-after.json`, `artifacts/idle-after-bounded.json`, `artifacts/installer-check.json`; source script: `tests/idle_probe.py`. Source probe uses smoke mode with foreground/shortcut polling, without another system hook. Installed measurement uses normal startup and actual hook. Single short samples on development hardware with ordinary background activity, not performance ceilings or low-end-PC certification.

## Current regression and packaged execution

- **144 pytest cases passed.** Includes existing keyboard, tools, data protection, voice lifecycle/cancellation, Windows input guards, auto-finish and new opacity/startup checks. Two upstream Python 3.12 deprecation warnings remain (`aifc`, `audioop`).
- Ruff passed for changed product files, changed unit tests and package audit scripts. `pip check` passed.
- Embedded code from ten modules plus main matched final source. Required dictionaries, icons, licenses and model weights verified in payload. `artifacts/package-code-check.json`.
- Full installed runtime copied into a fresh folder; PATH limited to System32, no PYTHONPATH/PYTHONHOME, empty LOCALAPPDATA, downloads disabled. UI, bundled Base offline English, Google Bengali, automatic-pause Bengali and normal startup/graceful quit all passed: `artifacts/standalone-check.json`. Installed EXE needs its installed `_internal` folder; the single setup EXE includes both.
- Public Bengali replay passed full Qt flow: one Speak click, zero Finish clicks, actual local Silero and Google recognition, hidden studio. `artifacts/auto-pause-flow.json`. Packaged detector found speech ending at 9.75 seconds and finished capture at 11.25 seconds: `artifacts/standalone-auto-pause.json`.
- Native mouse injection into owned bar preserved separate editor focus and delivered Bengali while studio stayed hidden: `artifacts/floating-native-result.json`. Recognition stubbed only for this focus test; no live microphone captured.

No second PC/VM/old CPU, live user microphone quality, physical keyboard across all apps, real speaker-loopback quality or live Gemini key tested. Installer unsigned. Offline Bengali accuracy remains poor; Google web mode remains experimental. No perfect recognition or universal-PC guarantee. Existing user processes were not force-terminated.

# Historical 0.3.1 verification

Details below describe the previous portable release, not the current installer. Relevant unit tests were rerun above; older broad hardware/encoding experiments were not all repeated for this update.

Release: `dist/0.3.1/JoyKeyboard.exe`, 371,784,415 bytes. SHA-256: `f48c49a596770cd311f33bf5e56e251da1d1c1147814d31ae740ad126e549879`. All five clean-folder executable checks passed; `artifacts/standalone-check.json`. The older running copy was preserved.

## Passed

- 138 pytest cases: composition, four layouts, suggestion/word/snippet persistence, bounded encoding conversion, Word/DocPad data-loss guards, tools, mocked microphone/loopback lifecycle, cancellation, output encoding, Windows input guards, and normal-startup/duplicate-instance locking.
- Ruff and `pip check` clean. Two upstream Python 3.12 deprecation warnings (`aifc`, `audioop`) remain.
- Common Unicode/Bijoy roundtrip: 2,000 frequent Bengali words, zero mismatches. This does not certify arbitrary legacy fonts or mixed text.
- Installed real Windows keyboard hook plus actual output into a separate owned native editor: Bangla/English/fixed layout, snippets, F1/F12, modifiers, Bijoy, injected-event bypass, native password guard. Evidence: `artifacts/keyboard-native-result.json`. Trusted physical keyboard hardware was NOT simulated: composition decisions were fed explicitly, then Windows injection delivered actual output.
- Source normal startup with actual hook, fresh user data and graceful shutdown saved dictionary: `artifacts/source-normal-launch.json`.
- Source screenshots inspected for voice, keyboard, screen keys and DocPad; all six tools tabs rendered. Small displays use scrolling.
- Original multi-size ICO/PNG/SVG validated. Bundled keyboard data, licenses, Base/Tiny model weights and final Python code inspected in executable archive: `artifacts/package-code-check.json`.

## Floating bar

- Default launch is a 504 by 74 logical-pixel frameless, always-on-top bar. Position persistence, offscreen recovery, language/layout/engine/output menus, every tool route, recording/cancel/finish, eight clickable suggestions, workspace-close/draft retention and feedback copying were executed. Evidence: `artifacts/tests-floating.log`, `artifacts/tests-floating-ui.log`.
- Native Windows mouse injections clicked only the owned floating bar. Showing it, toggling keyboard and starting/finishing voice preserved the separate editor's focus. A fixture speech result was inserted into that editor while the studio remained hidden. No microphone audio was captured for this UI-flow test. Evidence: `artifacts/floating-native-result.json`.
- Idle, recording, suggestions and menu screenshots inspected: `artifacts/floating-source.png`, `artifacts/floating-recording.png`, `artifacts/floating-candidates.png`, `artifacts/floating-menu.png`.
- Workspace close hides to the bar. Explicit Quit retains unsaved-draft checks and worker cancellation/shutdown. Tray restores the bar; hiding disabled during voice work or without a usable tray.

## Automatic finish

- Auto-finish defaults on, including migration from older settings. Local Silero VAD detects about 1.5 seconds after speech; no Finish click required. Each phrase stops the microphone; continuous listening is not implemented. Manual Finish, cancel, disabled auto-finish, hold-until-release and the 60-second cap remain available. No speech for 10 seconds cancels locally. Detector failures leave manual Finish available.
- Regression tests cover short silence, resumed speech, rolling-window absolute offsets, stop/error handling, UI auto-finish dispatch, local empty cancellation, hold-release precedence, preference validation and menu toggling. Tests now isolate real-user Caps Lock/settings from unit fixtures.
- Actual Bengali fixture tested at 16,000 / 44,100 / 48,000 Hz; quieter speech plus generated noise; silence/noise-only cancellation: `artifacts/pause-calibration.json`. Calibration used generated/public audio, not the live microphone.
- Full Qt flow with real Silero and Google recognition passed with one Speak click, zero Finish clicks, accelerated recorded-fixture input, hidden workspace: `artifacts/auto-pause-flow.json`.
- Delivered one-file EXE automatically detected the recorded Bengali phrase ending at 9.75 seconds and finished at 11.25 seconds, then Google returned the full readable Bengali sentence. `artifacts/standalone-auto-pause.json`. No external VAD download/key needed.

## Voice evidence

- Three public Google FLEURS Bengali read-speech samples produced readable Bengali using Google web HTTPS recognition, with errors. Source evidence: `artifacts/bengali-recognition.json`, `artifacts/bengali-google-third.json`; fixture provenance: `artifacts/bengali-fixtures.json`.
- Offline Base and Small Bengali tests were poor, including Latin transliteration, wrong scripts and hallucinations. Float32/prompt experiment also failed. Larger is not a guaranteed fix. Offline Bengali is explicitly flagged as unreliable in the app/README; online is recommended.
- Actual Base CPU/int8 recognition correctly transcribed an 11-second public English JFK fixture, both source and standalone EXE. Source URL/provenance: `artifacts/recognition-smoke.json`.
- One-file Windows Google encoder failure was reproduced and fixed by owning stdin/stdout/stderr handles for the bundled FLAC subprocess. Regression test verifies pipes and a lossless FLAC roundtrip.
- Final standalone results: `artifacts/standalone-offline-english.json`, `artifacts/standalone-online-bengali.json` and `artifacts/standalone-check.json`. Clean test copies ONLY the EXE outside the project, limits PATH to Windows System32, removes PYTHONPATH/PYTHONHOME, starts with empty LOCALAPPDATA and disables model downloads. It exercises UI, bundled offline English, online Bengali, normal hook startup and graceful close.

## Boundaries

Test machine: this Windows 11 Intel/AMD x64 PC. No clean VM or second physical PC tested. Windows 10 1809+/11 x64 is the supported target, not every operating system/CPU. Python and GPU not required by the bundle. One-file extraction needs temporary disk space and increases startup time.

Live user microphone quality, real speaker loopback, physical keyboard behavior across applications and Gemini with a live key are not tested. Capture/backend mock tests and public recorded fixtures cannot certify these. FLEURS samples are Indian Bengali read speech, not a Bangladeshi dialect/noise benchmark.

Google web access needs no user key but is experimental and can be limited or stopped. Offline processing requires suitable hardware and has poor Bengali quality in the checks above. No perfect recognition guarantee.

Full typing utility, without a claim of exact Kontho parity: four layouts, printable/Shift fixed positions, word-level composition, local suggestions/correction/learning, snippets, encoding, screen text keys, DocPad/PDF and optional text assistant. No TSF IME registration, AltGr/keypad layout extensions or universal custom/password/editor compatibility. Elevated applications can reject simulated input.

Words/history/transitions are stored locally after commits, including successful voice text. Audio is not saved automatically. Online engines upload only when explicitly selected/submitted. Gemini key session-only. Shutdown waits for outstanding work; cancelled results are suppressed, but underlying network/model calls may finish later.

Unsigned EXE; no signing certificate or SmartScreen reputation created. Older ZIP and 0.2 studio-first output are superseded; deliver `dist/JoyKeyboard.exe` only.
