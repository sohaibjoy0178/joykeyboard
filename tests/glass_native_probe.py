"""Owned striped backdrop proves real transparency/blur; never captures unrelated screen areas."""

import json
import os
import statistics
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="joy-glass-native-")


def probe():
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPainter
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QWidget

    from app import JoyWindow
    from windows import set_glass_blur

    class Backdrop(QWidget):
        def paintEvent(self, event):
            painter = QPainter(self)
            for x in range(0, self.width(), 8):
                painter.fillRect(x, 0, 8, self.height(), QColor("#163A64" if (x // 8) % 2 else "#F2C2B0"))

    application = QApplication([])
    backdrop = Backdrop(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    backdrop.setGeometry(application.primaryScreen().availableGeometry())
    backdrop.show()
    window = JoyWindow(smoke=True)
    window.compact.move(140, 140)
    window.compact._placed = True
    window.show_compact()
    QTest.qWait(400)
    bar = window.compact

    def capture(name):
        QTest.qWait(200)
        point = bar.pos()
        frame = bar.screen().grabWindow(0, point.x(), point.y(), bar.width(), bar.height()).toImage()
        frame.save(str(ROOT / "artifacts" / name))
        scale = frame.devicePixelRatio()
        y = round(41 * scale)
        values = [frame.pixelColor(round(x * scale), y).red() for x in range(30, 350)]
        return round(statistics.pstdev(values), 2)

    blur = capture("clear-native-blurred.png")
    set_glass_blur(int(bar.winId()), False)
    plain = capture("clear-native-no-blur.png")
    set_glass_blur(int(bar.winId()), True)
    restored = capture("clear-native-restored.png")
    report = dict(
        blur_deviation=blur,
        no_blur_deviation=plain,
        restored_deviation=restored,
        native_accepted=not bar.shell.fallback,
        theme=window.settings["theme"],
    )
    print(json.dumps(report))
    (ROOT / "artifacts/glass-native-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    window.close()
    backdrop.close()
    assert plain > 15 and blur < plain * 0.4 and restored < plain * 0.4, report


if __name__ == "__main__":
    probe()
