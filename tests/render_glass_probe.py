"""Render the actual UI with disposable data and sample text; no recording or network."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="joy-glass-preview-")


def render():
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QColor, QLinearGradient, QPainter
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QWidget

    from app import JoyWindow

    application = QApplication([])
    application.setStyle("Fusion")
    class Backdrop(QWidget):
        def paintEvent(self, event):
            painter = QPainter(self)
            gradient = QLinearGradient(0, 0, self.width(), self.height())
            for stop, color in ((0, "#2F7885"), (.35, "#95C3CF"), (.65, "#C6A9C8"), (1, "#F0C3A0")):
                gradient.setColorAt(stop, QColor(color))
            painter.fillRect(self.rect(), gradient)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 60))
            painter.drawEllipse(self.width() // 3, -100, 580, 580)
            painter.setBrush(QColor(24, 65, 110, 40))
            painter.drawEllipse(-200, self.height() // 2, 950, 600)
    backdrop = Backdrop(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
    backdrop.setGeometry(application.primaryScreen().availableGeometry())
    backdrop.show()
    window = JoyWindow(smoke=True)
    window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
    destination = ROOT / "artifacts"
    destination.mkdir(exist_ok=True)
    def capture():
        def save(widget, name):
            application.processEvents()
            assert widget.grab().save(str(destination / f"glass-{name}.png"))
        for theme in ("glass", "light"):
            window.theme_choice.setCurrentIndex(window.theme_choice.findData(theme))
            prefix = "clear-" if theme == "glass" else ""
            window.show_compact()
            if theme == "glass":
                QTest.qWait(120)
                point = window.compact.pos()
                assert window.compact.screen().grabWindow(0, point.x(), point.y(), window.compact.width(), window.compact.height()).save(str(destination / "clear-bar-composited.png"))
            save(window.compact, prefix + "bar")
            window.compact.main_menu()
            save(window.compact._menu, prefix + "menu")
            window.compact._menu.close()
            window.compact.update_candidates("ami", "আমি", ["আমি", "আমার", "আমিও", "আমাদের"])
            save(window.compact, prefix + "candidates")
            window.compact.update_candidates("", "", [])
            window.transcript.setPlainText("আমি বাংলায় লিখি।\n\nYour voice. Your words.\n\nPress your shortcut to start, speak, then press again to finish.")
            for page, name in [(0, "studio"), (2, "settings"), (3, "help")]:
                window.open_workspace(page)
                save(window, prefix + name)
                if theme == "glass" and name in ("studio", "settings"):
                    QTest.qWait(120)
                    point = window.pos()
                    assert window.screen().grabWindow(0, point.x(), point.y(), window.width(), window.height()).save(str(destination / f"clear-{name}-composited.png"))
            for index, name in enumerate(("keyboard", "words", "converter", "screen-keys", "docpad", "assistant")):
                window.open_workspace(1, index)
                save(window, prefix + name)
                if theme == "glass" and name in ("studio", "settings"):
                    QTest.qWait(120)
                    point = window.pos()
                    assert window.screen().grabWindow(0, point.x(), point.y(), window.width(), window.height()).save(str(destination / f"clear-{name}-composited.png"))
        window.close()
        backdrop.close()
        application.quit()
    QTimer.singleShot(600, capture)
    application.exec()


if __name__ == "__main__":
    render()
