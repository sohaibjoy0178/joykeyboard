"""Compare actual desktop pixels outside rounded bar against an owned static backdrop."""

import json
import os
import statistics
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="joy-rounded-bar-")


def probe():
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPainter
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QWidget

    from app import JoyWindow

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
    bar = window.compact
    bar.move(140, 140)
    bar._placed = True
    results = {}
    try:
        for theme in ("light", "dark"):
            window.theme_choice.setCurrentIndex(window.theme_choice.findData(theme))
            for state in ("idle", "feedback", "candidates"):
                bar.dismiss_feedback()
                bar.update_candidates("", "", [])
                if state == "feedback":
                    window.set_status("Example error", "Corner boundary check", True)
                elif state == "candidates":
                    bar.update_candidates("ami", "আমি", ["আমি", "আমার", "আমিও"])
                bar.hide()
                QTest.qWait(100)
                point = bar.pos()

                def desktop():
                    return bar.screen().grabWindow(0, point.x(), point.y(), bar.width(), bar.height()).toImage()

                before = desktop()
                bar.reveal()
                QTest.qWait(180)
                after = desktop()
                raw = bar.grab().toImage()
                assert before.size() == after.size() == raw.size()
                differences = []
                for y in range(raw.height()):
                    for x in range(raw.width()):
                        if raw.pixelColor(x, y).alpha() == 0:
                            a, b = after.pixelColor(x, y), before.pixelColor(x, y)
                            differences.append(
                                max(abs(a.red() - b.red()), abs(a.green() - b.green()), abs(a.blue() - b.blue()))
                            )
                scale = raw.devicePixelRatio()
                alpha = raw.pixelColor(round(5 * scale), round(bar.height() / 2 * scale)).alpha()
                line = [
                    after.pixelColor(round(x * scale), round((bar.height() - 8) * scale)).red() for x in range(30, 350)
                ]
                check = dict(
                    outside_pixels=len(differences),
                    maximum_outside_difference=max(differences),
                    material_alpha=alpha,
                    backdrop_variation=round(statistics.pstdev(line), 2),
                    bar_size=[bar.width(), bar.height()],
                )
                check["passed"] = (
                    len(differences) > 100
                    and max(differences) <= 2
                    and 100 < alpha < 230
                    and statistics.pstdev(line) > 15
                )
                results[f"{theme}-{state}"] = check
                assert raw.save(str(ROOT / "artifacts" / f"{theme}-rounded-{state}.png"))
        print(json.dumps(results))
        (ROOT / "artifacts/glass-native-check.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        assert all(value["passed"] for value in results.values()), results
    finally:
        window.close()
        backdrop.close()


if __name__ == "__main__":
    probe()
