"""Confirm the standalone archive contains final source and required assets."""
import json
import marshal
import sys
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader

ROOT = Path(__file__).resolve().parents[1]
executable = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "dist" / "JoyKeyboard.exe"
archive = CArchiveReader(str(executable))
python_archive = archive.open_embedded_archive("PYZ.pyz")
results = {}
for name in ("app", "core", "voice", "windows", "diagnostics", "keyboard_engine", "keyboard_hook", "tools_ui", "floating_bar", "startup", "hotkeys", "theme", "updates"):
    code = python_archive.extract(name)
    expected = compile((ROOT / f"{name}.py").read_text(encoding="utf-8"), code.co_filename, "exec")
    results[name] = code == expected
    assert results[name], name
main = marshal.loads(archive.extract("main"))
assert main == compile((ROOT / "main.py").read_text(encoding="utf-8"), main.co_filename, "exec")
results["main"] = True
names = {name.replace("\\", "/") for name in archive.toc}
for name in ("assets/keyboard/bn-words.json", "assets/keyboard/en-words.json", "assets/keyboard/layouts.json",
             "faster_whisper/assets/silero_vad_v6.onnx", "speech_recognition/flac-win32.exe", "licenses/KEYBOARD-SOURCES.md",
             "assets/joykeyboard.ico", "assets/models/WHISPER-LICENSE.txt"):
    assert name in names or (executable.parent / "_internal" / name).is_file(), name
results["required_assets"] = True
for name in ("assets/models/base/model.bin", "assets/models/tiny/model.bin", "speech_recognition/pocketsphinx-data"):
    assert not any(entry.startswith(name) for entry in names), name
    assert not (executable.parent / "_internal" / name).exists(), name
results["compact_payload"] = True
(ROOT / "artifacts" / "package-code-check.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print(json.dumps(results))
