"""A non-activating floating control surface for the existing keyboard and voice state."""
from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, QPoint, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QSystemTrayIcon,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from keyboard_engine import LAYOUTS

BAR_WIDTH = 384
BAR_STYLE = """
QWidget { color:#F4F5ED; font-family:'Segoe UI Variable Text','Segoe UI'; font-size:12px; font-style:normal; font-weight:400; }
QWidget#floatingRoot { background:transparent; }
QFrame#shell { background:#19221E; border:1px solid #455248; border-radius:12px; }
QLabel { background:transparent; border:0; }
QToolButton { border:1px solid transparent; border-radius:8px; padding:4px; }
QToolButton:hover { background:#39483C; border:1px solid #53634E; }
QToolButton:pressed { background:#46563F; }
QToolButton:disabled { color:#7D8B80; }
QToolButton#brand { font-size:15px; font-weight:600; padding:0; }
QToolButton#mode { color:#E6EBDE; font-size:12px; }
QToolButton#keyboard[active="true"] { background:#405331; border:1px solid #748756; }
QToolButton#speak { color:#192313; background:#D8ED92; border:1px solid #E4F2B5; font-weight:600; }
QToolButton#speak:hover { background:#E6F5AF; }
QToolButton#speak:pressed { background:#BDDA77; }
QToolButton#speak[recording="true"] { background:#F4B6A6; border-color:#FFD2C3; color:#341D17; }
QToolButton#speak:disabled { background:#35432E; border-color:#4B5D3F; color:#B7C6A6; }
QToolButton#candidate { background:#2E3D30; border:1px solid #475D43; border-radius:6px; padding:2px 5px; text-align:left; }
QToolButton#candidate:hover { background:#465E38; border-color:#9DB678; }
QLabel#composition { color:#D8ED92; font-size:13px; }
QLabel#status { color:#C3CEC0; font-size:11px; }
QLabel#status[error="true"] { color:#FFC4B6; }
QProgressBar { background:#465445; border:0; border-radius:2px; max-height:3px; min-height:3px; }
QProgressBar::chunk { background:#D8ED92; border-radius:2px; }
QMenu { background:#1C2720; color:#F4F5ED; border:1px solid #4A5B4C; padding:7px; border-radius:9px; font-family:'Segoe UI'; font-size:13px; }
QMenu::item { padding:8px 28px 8px 19px; border-radius:5px; }
QMenu::item:selected { background:#3A4E31; color:#E5F4B7; }
QMenu::item:disabled { color:#8D9F8D; }
QMenu::separator { background:#3A4C3B; height:1px; margin:6px 10px; }
QToolTip { background:#233025; color:#F4F5ED; border:1px solid #65785B; padding:7px; }
"""
_PATHS = {
    "mic": '<rect x="9" y="3" width="6" height="12" rx="3"/><path d="M6 11v2a6 6 0 0 0 12 0v-2M12 19v3m-3 0h6"/>',
    "stop": '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    "keyboard": '<rect x="2.5" y="5" width="19" height="14" rx="3"/><path d="M6 9h.1M10 9h.1M14 9h.1M18 9h.1M6 12h.1M10 12h.1M14 12h.1M18 12h.1M7 15h10"/>',
    "more": '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
    "hide": '<path d="M5 12h14"/>',
    "close": '<path d="m7 7 10 10M17 7 7 17"/>',
    "grip": '<path d="M9 6h.1M15 6h.1M9 12h.1M15 12h.1M9 18h.1M15 18h.1"/>',
    "open": '<path d="M13 4h7v7m0-7L10 14M10 5H6a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-4"/>',
    "copy": '<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M15 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>',
}


@lru_cache(maxsize=32)
def line_icon(name, color="#C6D3BE"):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><g fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{_PATHS[name]}</g></svg>'
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    QSvgRenderer(QByteArray(svg.encode())).render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)


def _flag(widget, name, value):
    if widget.property(name) != value:
        widget.setProperty(name, value)
        widget.style().unpolish(widget)
        widget.style().polish(widget)


class DragGrip(QLabel):
    def __init__(self, bar):
        super().__init__(bar)
        self.bar = bar
        self.offset = None
        self.setPixmap(line_icon("grip", "#8DA084").pixmap(16, 22))
        self.setFixedSize(10, 30)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setToolTip("Drag to move JoyKeyboard")
        self.setAccessibleName("Move floating bar")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.offset = event.globalPosition().toPoint() - self.bar.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.bar.move(event.globalPosition().toPoint() - self.offset)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.offset is not None:
            self.offset = None
            self.bar.clamp_position()
            self.bar.owner.settings["bar_position"] = [self.bar.x(), self.bar.y()]
            self.bar.owner.persist()


class CompactBar(QWidget):
    def __init__(self, owner):
        flags = (Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                 Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        super().__init__(None, flags)
        self.owner = owner
        self._placed = False
        self._menu = None
        self._last_state = None
        self.setObjectName("floatingRoot")
        self.setWindowTitle("JoyKeyboard · Floating bar")
        self.setWindowIcon(owner.windowIcon())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet(BAR_STYLE)
        self.setFixedWidth(BAR_WIDTH)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(2, 2, 2, 2)
        self.shell = QFrame()
        self.shell.setObjectName("shell")
        outer.addWidget(self.shell)
        self.body = QVBoxLayout(self.shell)
        self.body.setContentsMargins(6, 6, 6, 6)
        self.body.setSpacing(7)
        row = QHBoxLayout()
        row.setSpacing(4)
        self.body.addLayout(row)
        self.grip = DragGrip(self)
        row.addWidget(self.grip)
        self.brand = self._button("brand", "Open JoyKeyboard workspace", owner.show_studio, 30)
        self.brand.setIcon(owner.windowIcon())
        self.brand.setIconSize(QSize(24, 24))
        row.addWidget(self.brand)
        self.mode = self._button("mode", "Choose voice language and keyboard layout", self.input_menu, 116)
        row.addWidget(self.mode)
        self.keyboard_btn = self._button("keyboard", "Toggle keyboard · F12", owner.toggle_keyboard, 30, "keyboard")
        row.addWidget(self.keyboard_btn)
        self.record = self._button("speak", "Start voice typing · Ctrl+Alt+Space", owner.toggle_record, 78, "mic")
        self.record.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        row.addWidget(self.record)
        self.cancel = self._button("cancel", "Cancel and discard voice recording", owner.cancel, 24, "close")
        self.cancel.hide()
        row.addWidget(self.cancel)
        row.addStretch(1)
        self.more = self._button("more", "All controls, tools and settings", self.main_menu, 28, "more")
        row.addWidget(self.more)
        self.hide_btn = self._button("hide", "Hide to notification area", self.hide, 20, "hide")
        row.addWidget(self.hide_btn)

        self.feedback = QFrame()
        feedback_row = QHBoxLayout(self.feedback)
        feedback_row.setContentsMargins(4, 0, 0, 0)
        feedback_row.setSpacing(4)
        self.status = QLabel("Ready")
        self.status.setObjectName("status")
        feedback_row.addWidget(self.status, 1)
        self.meter = QProgressBar()
        self.meter.setRange(0, 100)
        self.meter.setTextVisible(False)
        self.meter.setFixedWidth(45)
        self.meter.setAccessibleName("Recording level")
        feedback_row.addWidget(self.meter)
        self.copy = self._button("copy", "Copy transcript", owner.copy_text, 24, "copy")
        feedback_row.addWidget(self.copy)
        self.open = self._button("open", "Open transcript and details", lambda: owner.open_workspace(0), 24, "open")
        feedback_row.addWidget(self.open)
        self.dismiss = self._button("dismiss", "Dismiss status", self.dismiss_feedback, 22, "close")
        feedback_row.addWidget(self.dismiss)
        self.body.addWidget(self.feedback)
        self.feedback.hide()

        self.candidates = QWidget()
        candidate_layout = QVBoxLayout(self.candidates)
        candidate_layout.setContentsMargins(4, 0, 4, 2)
        candidate_layout.setSpacing(5)
        self.composition = QLabel()
        self.composition.setObjectName("composition")
        candidate_layout.addWidget(self.composition)
        grid = QGridLayout()
        grid.setSpacing(4)
        candidate_layout.addLayout(grid)
        self.candidate_buttons = []
        for index in range(8):
            item = self._button("candidate", f"Choose suggestion {index + 1}", lambda _=False, i=index: owner.keyboard_hook.choose(i), 84)
            item.setFixedHeight(27)
            grid.addWidget(item, index // 4, index % 4)
            self.candidate_buttons.append(item)
        self.body.addWidget(self.candidates)
        self.candidates.hide()
        self.feedback_timer = QTimer(self)
        self.feedback_timer.setSingleShot(True)
        self.feedback_timer.timeout.connect(self.dismiss_feedback)
        self.adjustSize()

    def _button(self, name, description, callback, width, icon=None):
        item = QToolButton()
        item.setObjectName(name)
        item.setFixedSize(width, 30)
        item.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        item.setCursor(Qt.CursorShape.PointingHandCursor)
        item.setAccessibleName(description)
        item.setToolTip(description)
        if icon:
            item.setIcon(line_icon(icon))
            item.setIconSize(QSize(18, 18))
        item.clicked.connect(callback)
        return item

    def reveal(self):
        if not self._placed:
            area = QGuiApplication.primaryScreen().availableGeometry()
            position = self.owner.settings.get("bar_position")
            self.move(QPoint(*position) if position else QPoint(area.center().x() - self.width() // 2, area.top() + 16))
            self._placed = True
        self.clamp_position()
        self.show()
        self.raise_()

    def clamp_position(self):
        screen = QGuiApplication.screenAt(self.pos() + QPoint(self.width() // 2, 15)) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        self.move(max(area.left(), min(self.x(), area.right() - self.width() + 1)),
                  max(area.top(), min(self.y(), area.bottom() - self.height() + 1)))

    def _resize(self):
        self.body.activate()
        self.layout().activate()
        self.adjustSize()
        if self._placed:
            self.clamp_position()

    def sync_controls(self):
        owner = self.owner
        recording = owner.recorder is not None
        busy = owner.job is not None
        enabled = owner.keyboard_hook.enabled
        state = (recording, busy, enabled, owner.settings["keyboard_layout"],
                 owner.language.currentIndex(), owner.language.isEnabled(),
                 owner.record_btn.isEnabled(), owner.cancel_btn.isEnabled(),
                 owner.tray.isVisible(), owner.transcript.document().isEmpty(),
                 owner.settings["bar_opacity"])
        state += (owner.settings["voice_shortcut"],)
        if state == self._last_state:
            return
        self._last_state = state
        self.setWindowOpacity(owner.settings["bar_opacity"] / 100)
        layout = {"phonetic": "Phonetic", "english": "English", "probhat": "Probhat", "inscript": "InScript"}[owner.settings["keyboard_layout"]]
        self.mode.setText(f"{'বাং' if owner.language.currentData() == 'bn-BD' else 'EN'} · {layout} ▾")
        self.mode.setToolTip(f"Voice: {owner.language.currentText()}\nKeyboard: {LAYOUTS[owner.settings['keyboard_layout']]}\nClick to change language or layout")
        self.mode.setEnabled(owner.language.isEnabled())
        _flag(self.keyboard_btn, "active", enabled)
        self.keyboard_btn.setIcon(line_icon("keyboard", "#DEF1A6" if enabled else "#C6D3BE"))
        self.keyboard_btn.setToolTip(f"Keyboard {'ON' if enabled else 'OFF'} · F12\nType ami, then Space → আমি (phonetic)\nSpace or Enter inserts the composed word")
        self.keyboard_btn.setAccessibleName(self.keyboard_btn.toolTip())
        self.keyboard_btn.setEnabled(not recording and not busy)
        _flag(self.record, "recording", recording)
        self.record.setIcon(line_icon("stop" if recording else "more" if busy else "mic", "#26351B"))
        self.record.setText("Finish" if recording else "Working" if busy else "Speak")
        self.record.setEnabled(owner.record_btn.isEnabled())
        self.record.setAccessibleName(f"{'Finish and transcribe' if recording else 'Start voice typing'} · {owner.settings['voice_shortcut']}")
        self.record.setToolTip(self.record.accessibleName())
        self.cancel.setVisible(owner.cancel_btn.isEnabled())
        self.cancel.setEnabled(owner.cancel_btn.isEnabled())
        self.hide_btn.setEnabled(owner.tray.isVisible() and QSystemTrayIcon.isSystemTrayAvailable() and not recording and not busy)
        self.meter.setVisible(recording)
        self.copy.setVisible(not owner.transcript.document().isEmpty() and not recording and not busy)
        self.dismiss.setVisible(not recording and not busy)
        self._resize()

    def set_status(self, title, message="", error=False):
        _flag(self.status, "error", error)
        self.status.setText(self.status.fontMetrics().elidedText(title, Qt.TextElideMode.ElideRight, 220))
        self.feedback.setToolTip(message or title)
        self.feedback.show()
        self.feedback_timer.stop()
        if not error:
            self.feedback_timer.start(8000)
        if error or self.owner.recorder is not None or self.owner.job is not None:
            self.reveal()
        self.sync_controls()
        self._resize()

    def dismiss_feedback(self):
        if self.owner.recorder is None and self.owner.job is None:
            self.feedback.hide()
            self._resize()

    def update_recording(self, elapsed, level):
        self.status.setText(f"Listening  ·  00:{min(int(elapsed), 60):02d}")
        self.meter.setValue(min(100, int(level * 100)))

    def update_candidates(self, raw, rendered, suggestions):
        self.composition.setText(self.composition.fontMetrics().elidedText(f"{raw}  →  {rendered}", Qt.TextElideMode.ElideRight, 340))
        self.composition.setToolTip(f"{raw} → {rendered}")
        for index, item in enumerate(self.candidate_buttons):
            item.setVisible(index < len(suggestions))
            if index < len(suggestions):
                text = f"{index + 1}  {suggestions[index]}"
                item.setText(item.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, 72))
                item.setToolTip(f"F{index + 1} · {suggestions[index]}")
                item.setAccessibleName(f"Choose {suggestions[index]}")
        self.candidates.setVisible(bool(raw))
        self._resize()

    def _action(self, menu, text, callback, checked=None, enabled=True):
        action = QAction(text, menu)
        action.setEnabled(enabled)
        if checked is not None:
            action.setCheckable(True)
            action.setChecked(checked)
        if checked is None:
            action.triggered.connect(callback)
        else:
            action.triggered.connect(lambda value: callback(value))
        menu.addAction(action)
        return action

    def _choices(self, menu, combo):
        group = QActionGroup(menu)
        for index in range(combo.count()):
            group.addAction(self._action(menu, combo.itemText(index), lambda _=False, i=index: combo.setCurrentIndex(i),
                                         checked=index == combo.currentIndex(), enabled=combo.isEnabled()))

    def _input_choices(self, menu):
        self._choices(menu.addMenu("Voice language"), self.owner.language)
        layouts = menu.addMenu("Keyboard layout")
        group = QActionGroup(layouts)
        for identity, title in LAYOUTS.items():
            group.addAction(self._action(layouts, title, lambda _=False, key=identity: self.owner.set_keyboard_layout(key),
                                         checked=identity == self.owner.settings["keyboard_layout"], enabled=self.mode.isEnabled()))

    def _popup(self, menu, anchor):
        if self._menu is not None:
            self._menu.deleteLater()
        self._menu = menu
        menu.setStyleSheet(BAR_STYLE)
        menu.popup(anchor.mapToGlobal(QPoint(0, anchor.height() + 9)))

    def input_menu(self):
        menu = QMenu(self)
        self._input_choices(menu)
        self._popup(menu, self.mode)

    def main_menu(self):
        owner = self.owner
        menu = QMenu(self)
        self._action(menu, "JoyKeyboard  0.4.2", lambda: None, enabled=False)
        self._action(menu, "Voice studio / transcript", lambda: owner.open_workspace(0))
        tools = menu.addMenu("Keyboard and writing tools")
        for index, title in enumerate(("Keyboard", "Words & snippets", "Unicode / Bijoy converter", "Screen keys", "DocPad / PDF", "Text assistant")):
            self._action(tools, title, lambda _=False, i=index: owner.open_workspace(1, i))
        menu.addSeparator()
        self._input_choices(menu)
        self._choices(menu.addMenu("Speech engine"), owner.engine)
        microphones = menu.addMenu("Audio input")
        self._choices(microphones, owner.devices)
        microphones.addSeparator()
        self._action(microphones, "Record computer sound", owner.system_audio.setChecked,
                     checked=owner.system_audio.isChecked(), enabled=owner.system_audio.isEnabled())
        self._action(microphones, "Refresh microphones", owner.refresh_devices, enabled=owner.devices.isEnabled())
        self._choices(menu.addMenu("Output encoding"), owner.output_encoding)
        self._action(menu, "Type transcript into original app", owner.auto_type.setChecked, checked=owner.auto_type.isChecked())
        self._action(menu, "Finish on speech pause", owner.auto_pause.setChecked,
                     checked=owner.auto_pause.isChecked(), enabled=owner.auto_pause.isEnabled())
        menu.addSeparator()
        self._action(menu, f"Voice shortcut: {owner.settings['voice_shortcut']}…", lambda: owner.open_workspace(2))
        self._choices(menu.addMenu("Bar opacity"), owner.bar_opacity)
        self._action(menu, "Preferences", lambda: owner.open_workspace(2))
        self._action(menu, "Help and privacy", lambda: owner.open_workspace(3))
        self._action(menu, "Developed by Sohaib Islam Joy", lambda: owner.open_workspace(3))
        menu.addSeparator()
        self._action(menu, "Hide to notification area", self.hide, enabled=self.hide_btn.isEnabled())
        self._action(menu, "Quit JoyKeyboard", owner.request_quit)
        self._popup(menu, self.more)

    def closeEvent(self, event):
        if self.owner.quitting or self.owner.smoke:
            event.accept()
        else:
            event.ignore()
            self.owner.request_quit()
