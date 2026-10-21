# -*- mode: python ; coding: utf-8 -*-
from importlib.metadata import distributions
import os
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all, copy_metadata

project = Path(SPECPATH)
# Unrelated tools on PATH can supply an incompatible ICU/OpenSSL DLL during scanning.
windows = Path(os.environ["SystemRoot"])
os.environ["PATH"] = os.pathsep.join(str(path) for path in (
    Path(sys.executable).parent, Path(sys.base_prefix), Path(sys.base_prefix) / "DLLs",
    windows / "System32", windows,
))
datas = [(str(project / "docs" / "screenshots" / name), "docs/screenshots")
         for name in ("glass-light-bar.png", "glass-dark-bar.png", "dark-studio-composited.png")]
datas += [
         (str(project / "assets" / "joykeyboard.png"), "assets"),
         (str(project / "assets" / "joykeyboard.ico"), "assets"),
         (str(project / "assets" / "joykeyboard.svg"), "assets"),
         (str(project / "assets" / "keyboard"), "assets/keyboard"),
         (str(project / "assets" / "vad"), "assets/vad"),
         (str(project / "assets" / "models" / "SHERPA-LICENSE.txt"), "assets/models"),
         (str(project / "assets" / "models" / "SOURCES.txt"), "assets/models"),
         (str(project / "README.md"), "."),
         (str(project / "KEYBOARD-SOURCES.md"), "licenses"),
         (str(project / "assets" / "licenses"), "licenses/OpenSource")]
binaries = []
hiddenimports = []

# Lazy recognition imports still need their native runtimes in the portable build.
for package in ("onnxruntime", "sherpa_onnx", "sounddevice", "_sounddevice_data", "soundcard", "avro"):
    package_datas, package_binaries, package_imports = collect_all(package, include_py_files=False)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_imports
datas += copy_metadata("SpeechRecognition", recursive=True)

# Preserve upstream license files, including Qt/PySide6 LGPL notices and FFmpeg notices.
dependency_notices = []
for distribution in distributions():
    dependency_notices.append("\n".join([
        f"{distribution.metadata['Name']} {distribution.version}",
        "License: " + str(distribution.metadata.get("License-Expression") or distribution.metadata.get("License") or "See upstream license"),
        *distribution.metadata.get_all("Project-URL", []),
    ]))
    for relative in distribution.files or ():
        lower = str(relative).lower()
        if any(name in Path(lower).name for name in ("license", "licence", "copying", "notice")):
            source = Path(distribution.locate_file(relative))
            if source.is_file():
                parent = Path(*[part for part in Path(relative).parent.parts if part not in ("..", ".")])
                destination = Path("licenses") / distribution.metadata["Name"] / parent
                datas.append((str(source), str(destination)))
python_license = Path(sys.base_prefix) / "LICENSE.txt"
if python_license.is_file():
    datas.append((str(python_license), "licenses/Python"))
notice_path = project / "build" / "DEPENDENCIES.txt"
notice_path.parent.mkdir(exist_ok=True)
notice_path.write_text("\n\n".join(sorted(dependency_notices)), encoding="utf-8")
datas.append((str(notice_path), "licenses"))

a = Analysis(
    [str(project / "main.py")], pathex=[str(project)],
    binaries=binaries, datas=datas, hiddenimports=hiddenimports,
    hookspath=[str(project / "hooks")], hooksconfig={}, runtime_hooks=[],
    excludes=["tkinter", "pytest", "IPython", "matplotlib", "scipy", "torch", "tensorflow", "faster_whisper", "ctranslate2", "tokenizers", "huggingface_hub", "hf_xet", "av",
              "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQml",
              "PySide6.QtQuick", "PySide6.Qt3DCore", "PySide6.QtOpenGLWidgets"],
    noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
installed = os.environ.get("JOYKEYBOARD_INSTALLER") == "1"
exe = EXE(
    pyz, a.scripts, *([] if installed else [a.binaries, a.datas]), [],
    exclude_binaries=installed,
    name="JoyKeyboard", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False,
    icon=str(project / "assets" / "joykeyboard.ico"),
)
if installed:
    collect = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="JoyKeyboard")
