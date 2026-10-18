"""Opt-in real Windows typing probe, confined to a separate owned text window."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TITLE = "JoyKeyboard owned Unicode probe"
EXPECTED = "JoyKeyboard বাংলা লেখা 🙂\nদ্বিতীয় লাইন"


def field(output):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QPlainTextEdit
    application = QApplication([])
    edit = QPlainTextEdit()
    edit.setWindowTitle(TITLE)
    edit.resize(540, 180)
    edit.show()
    edit.activateWindow()
    edit.setFocus()
    output.write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")

    def finish():
        output.write_text(json.dumps({"actual": edit.toPlainText(), "pid": os.getpid()}, ensure_ascii=False), encoding="utf-8")
        application.quit()
    QTimer.singleShot(4000, finish)
    return application.exec()


def probe():
    from windows import foreground_target, insert_text
    output = ROOT / "artifacts/native-unicode.json"
    output.parent.mkdir(exist_ok=True)
    child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--field", str(output)])
    try:
        deadline = time.monotonic() + 3
        target = None
        owned_pid = None
        while time.monotonic() < deadline:
            if output.exists():
                owned_pid = json.loads(output.read_text(encoding="utf-8")).get("pid")
            target = foreground_target()
            if target and target.pid == owned_pid and target.title == TITLE:
                break
            time.sleep(0.05)
        assert target and target.pid == owned_pid and target.title == TITLE, "Owned test window could not get focus"
        insert_text(target, EXPECTED)
        child.wait(timeout=7)
        result = json.loads(output.read_text(encoding="utf-8"))
        result.update(expected=EXPECTED, passed=result["actual"] == EXPECTED)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        assert result["passed"]
    finally:
        if child.poll() is None:
            child.terminate()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--field":
        raise SystemExit(field(Path(sys.argv[2])))
    probe()
