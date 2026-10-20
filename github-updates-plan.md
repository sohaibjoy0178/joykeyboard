# GitHub app updates

- [x] Use the existing public repository's latest published stable release; ordinary commits are not installer updates.
- [x] Check after startup and every six hours, with a manual check and an automatic-download switch in Preferences.
- [x] Download on a separate worker, cap network/file sizes, verify GitHub SHA-256, and reuse only verified cached installers.
- [x] Notify through the tray and existing menus; keep the floating bar size. Ask explicitly before installation and preserve document/voice safety checks.
- [x] Run a hidden Windows helper that waits for this app to exit, rechecks the file, installs without restarting Windows, preserves autostart, and reopens the app. Report failures on next launch.
- [x] Test release validation, corrupted/cancelled downloads, denied permission, worker shutdown, actual public-feed access and temporary install/update lifecycle. Clean-build, verify, and publish the EXE with checksum.
