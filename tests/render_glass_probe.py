"""Render the actual UI with disposable data and sample text; no recording or network."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="joy-glass-preview-")


def render():
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from app import JoyWindow

    application = QApplication([])
    application.setStyle("Fusion")
    window = JoyWindow(smoke=True)
    destination = ROOT / "artifacts"
    destination.mkdir(exist_ok=True)
    def capture():
        def save(widget, name):
            application.processEvents()
            assert widget.grab().save(str(destination / f"glass-{name}.png"))
        for theme in ("light", "dark"):
            window.theme_choice.setCurrentIndex(window.theme_choice.findData(theme))
            prefix = "dark-" if theme == "dark" else ""
            window.show_compact()
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
            for index, name in enumerate(("keyboard", "words", "converter", "screen-keys", "docpad", "assistant")):
                window.open_workspace(1, index)
                save(window, prefix + name)
        window.close()
        application.quit()
    QTimer.singleShot(600, capture)
    application.exec()


if __name__ == "__main__":
    render()
