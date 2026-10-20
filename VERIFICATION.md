# JoyKeyboard 0.4.6 verification

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
