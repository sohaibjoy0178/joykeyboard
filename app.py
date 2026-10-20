"""JoyKeyboard's desktop recording studio and compact typing toolbar."""
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import QLockFile, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QIcon, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import startup
from core import (
    DEFAULT_VOICE_SHORTCUT,
    data_directory,
    format_rules,
    load_settings,
    parse_rules,
    parse_voice_shortcut,
    process_text,
    save_settings,
)
from floating_bar import CompactBar
from hotkeys import VoiceHotkey
from keyboard_engine import LAYOUTS, KeyboardEngine, to_ansi
from keyboard_hook import KeyboardHook
from theme import paint_glass, round_window, style_sheet
from tools_ui import KeyboardTools
from voice import LoopbackRecorder, PauseMonitor, Recognizer, Recorder, list_microphones
from windows import foreground_target, insert_text, key_down, set_glass_blur

ASSETS = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "assets"



class WindowTitle(QLabel):
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.window().windowHandle().startSystemMove()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            window = self.window()
            window.showNormal() if window.isMaximized() else window.showMaximized()


def label(text, role=None, wrap=False):
    item = WindowTitle(text) if role == "title" else QLabel(text)
    if role == "title":
        item.setToolTip("Drag to move · double-click to maximize / restore")
    item.setWordWrap(wrap)
    if role:
        item.setObjectName(role)
    return item


def button(text, callback, role=None):
    item = QPushButton(text)
    item.clicked.connect(callback)
    if role:
        item.setObjectName(role)
    return item


class Job(QThread):
    result = Signal(object)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, function):
        super().__init__()
        self.function = function

    def run(self):
        try:
            self.result.emit(self.function(self.progress.emit))
        except Exception as exc:
            self.failed.emit(str(exc))


class JoyWindow(QMainWindow):
    keyboard_update = Signal(str, str, list)
    keyboard_error = Signal(str)

    def __init__(self, smoke=False):
        super().__init__()
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.native_glass = False
        self.smoke = smoke
        self.settings_path = data_directory() / "settings.json"
        self.settings, warning = load_settings(self.settings_path)
        self.keyboard_engine = KeyboardEngine(None if smoke else data_directory() / "keyboard-data.json")
        self.keyboard_update.connect(self.show_candidates)
        self.keyboard_error.connect(self.show_keyboard_error)
        self.keyboard_hook = KeyboardHook(self.keyboard_engine, self.keyboard_update.emit, self.keyboard_error.emit)
        self.keyboard_resume = False
        self.keyboard_closed = False
        self.previous_keyboard_enabled = False
        self.recognizer = Recognizer(data_directory() / "models")
        self.recorder = None
        self.pause_monitor = None
        self.job = None
        self.cancel_event = threading.Event()
        self.generation = 0
        self.quitting = False
        self.target = None
        self.last_external = None
        self.voice_hotkey = None
        self.last_hold = False
        self.started = 0.0
        self.last_text = ""
        self.setWindowTitle("JoyKeyboard · Keyboard & voice studio")
        self.setWindowIcon(QIcon(str(ASSETS / "joykeyboard.ico")))
        available = QApplication.primaryScreen().availableGeometry()
        self.resize(min(980, available.width() - 40), min(820, available.height() - 40))
        self.setMinimumSize(720, 500)
        self.setStyleSheet(style_sheet("workspace", self.settings["theme"]))
        self._build_ui()
        self.compact = CompactBar(self)
        self.tools = KeyboardTools(self, self.keyboard_engine, self.insert_tool_text)
        layout_index = self.tools.layout_choice.findData(self.settings["keyboard_layout"])
        self.tools.layout_choice.setCurrentIndex(max(0, layout_index))
        self.tools.enabled_changed.connect(self.set_keyboard_enabled)
        self.tools.layout_changed.connect(self.set_keyboard_layout)
        self.tools.candidate_selected.connect(self.keyboard_hook.choose)
        self.tabs.insertTab(1, self.tools, "Keyboard and tools")
        self.keyboard_hook.set_layout(self.settings["keyboard_layout"])
        self.keyboard_hook.set_output_encoding(self.settings["output_encoding"])
        self._build_tray()
        self.apply_theme()
        self.poll = QTimer(self)
        self.poll.timeout.connect(self.tick)
        if not smoke:
            try:
                self.keyboard_hook.start()
            except RuntimeError as exc:
                warning = f"Keyboard hook unavailable: {exc}"
            self.poll.start(40)
            self.voice_hotkey = VoiceHotkey(int(self.winId()), self.voice_shortcut_triggered)
            try:
                self.voice_hotkey.register(self.settings["voice_shortcut"])
                self.shortcut_status.setText(f"Active globally: {self.settings['voice_shortcut']} · press to start / finish")
            except OSError as exc:
                self.shortcut_status.setText(str(exc))
                warning = str(exc)
        if warning:
            self.set_status("Preferences recovered", warning, True)
        if self.keyboard_engine.load_error:
            self.message.setText(self.keyboard_engine.load_error)
        self.refresh_devices()
        self.update_engine()
        self.compact.sync_controls()

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("workspaceRoot")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(root)
        root.setMinimumSize(850, 780)
        self.setCentralWidget(scroll)
        page = QVBoxLayout(root)
        page.setContentsMargins(32, 26, 32, 24)
        page.setSpacing(18)
        header = QHBoxLayout()
        brand = QLabel()
        brand.setPixmap(QPixmap(str(ASSETS / "joykeyboard.png")).scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        header.addWidget(brand)
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(label("Keyboard & voice", "eyebrow"))
        names.addWidget(label("JoyKeyboard", "title"))
        header.addLayout(names)
        header.addStretch()
        self.keyboard_toggle = button("Keyboard OFF · F12", self.toggle_keyboard)
        header.addWidget(self.keyboard_toggle)
        header.addWidget(button("Floating bar", self.show_compact))
        minimize = button("−", self.showMinimized)
        minimize.setFixedSize(36, 36)
        minimize.setStyleSheet("padding:0; font-size:20px;")
        minimize.setToolTip("Minimize workspace")
        minimize.setAccessibleName("Minimize workspace")
        header.addWidget(minimize)
        close = button("×", self.close)
        close.setFixedSize(36, 36)
        close.setStyleSheet("padding:0; font-size:20px;")
        close.setToolTip("Close workspace · return to floating bar")
        close.setAccessibleName("Close workspace")
        header.addWidget(close)
        page.addLayout(header)
        self.tabs = QTabWidget()
        page.addWidget(self.tabs)
        studio = QWidget()
        columns = QHBoxLayout(studio)
        columns.setContentsMargins(0, 20, 0, 0)
        columns.setSpacing(22)
        controls = QVBoxLayout()
        controls.setSpacing(8)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.addWidget(label("Voice", "eyebrow"))
        self.language = QComboBox()
        self.language.addItem("বাংলা  ·  Bengali", "bn-BD")
        self.language.addItem("English  ·  United States", "en-US")
        self.language.setCurrentIndex(self.language.findData(self.settings["language"]))
        self.language.setAccessibleName("Recognition language")
        controls.addWidget(self.language)
        self.engine = QComboBox()
        self.engine.addItem("Google web  ·  online, no key", "google")
        self.engine.addItem("Whisper  ·  offline, no key", "offline")
        self.engine.setCurrentIndex(self.engine.findData(self.settings["engine"]))
        self.engine.setAccessibleName("Speech recognition engine")
        controls.addWidget(self.engine)
        self.engine_note = label("", "muted", True)
        controls.addWidget(self.engine_note)
        controls.addWidget(label("Audio input", "eyebrow"))
        self.devices = QComboBox()
        self.devices.setAccessibleName("Microphone device")
        devices_row = QHBoxLayout()
        devices_row.addWidget(self.devices, 1)
        refresh = button("↻", self.refresh_devices)
        refresh.setAccessibleName("Refresh microphones")
        refresh.setToolTip("Refresh microphones")
        devices_row.addWidget(refresh)
        controls.addLayout(devices_row)
        self.system_audio = QCheckBox("Record computer sound instead")
        self.system_audio.setChecked(self.settings["system_audio"])
        self.system_audio.setToolTip("Captures the default Windows speaker output. Choose a microphone by leaving this unchecked.")
        controls.addWidget(self.system_audio)
        panel = QFrame()
        panel.setObjectName("panel")
        recording = QVBoxLayout(panel)
        recording.setContentsMargins(18, 16, 18, 16)
        recording.setSpacing(10)
        panel.setMinimumHeight(200)
        self.state = label("Ready when you are", "state", True)
        self.clock = label("00:00  /  01:00", "muted")
        self.meter = QProgressBar()
        self.meter.setRange(0, 100)
        self.meter.setTextVisible(False)
        self.meter.setAccessibleName("Microphone input level")
        self.record_btn = button("●  Start recording", self.toggle_record, "primary")
        self.cancel_btn = button("Cancel", self.cancel, "cancel")
        self.cancel_btn.setEnabled(False)
        for item in (self.state, self.clock, self.meter, self.record_btn, self.cancel_btn):
            recording.addWidget(item)
        controls.addWidget(panel)
        self.auto_type = QCheckBox("Type into original app when ready")
        self.auto_type.setChecked(self.settings["auto_type"])
        self.auto_type.setToolTip("Uses the last focused external window. A change to another app blocks insertion; transcript stays available.")
        controls.addWidget(self.auto_type)
        self.shortcut_hint = label(f"{self.settings['voice_shortcut']}  ·  record / finish\nEsc in studio  ·  cancel", "muted", True)
        controls.addWidget(self.shortcut_hint)
        controls.addStretch()
        left = QWidget()
        left.setLayout(controls)
        left.setObjectName("voiceControls")
        controls.setContentsMargins(16, 18, 16, 18)
        left.setFixedWidth(335)
        columns.addWidget(left)
        right = QVBoxLayout()
        caption = QHBoxLayout()
        caption.addWidget(label("Transcript", "eyebrow"))
        caption.addStretch()
        self.word_count = label("0 words", "muted")
        caption.addWidget(self.word_count)
        right.addLayout(caption)
        self.transcript = QPlainTextEdit()
        self.transcript.setPlaceholderText(f"Your words, clearly.\n\nChoose a language, focus your document, then use {self.settings['voice_shortcut']}.\n\nThe transcript stays here if typing is blocked.")
        self.transcript.setAccessibleName("Editable recognition transcript")
        self.transcript.textChanged.connect(lambda: self.word_count.setText(f"{len(self.transcript.toPlainText().split())} words"))
        right.addWidget(self.transcript, 1)
        actions = QHBoxLayout()
        actions.addWidget(button("Copy", self.copy_text))
        actions.addWidget(button("Type again", self.type_again))
        actions.addWidget(button("Save .txt", self.save_text))
        actions.addStretch()
        actions.addWidget(button("Clear", self.transcript.clear))
        right.addLayout(actions)
        self.target_note = label("Focus a document to set your typing destination.", "muted", True)
        right.addWidget(self.target_note)
        columns.addLayout(right, 1)
        self.tabs.addTab(studio, "Voice studio")
        self._build_preferences()
        self._build_help()
        self.message = label("No account. No subscription. Your choice of online or local recognition.", "muted", True)
        self.message.setMinimumHeight(40)
        footer = QHBoxLayout()
        footer.addWidget(self.message, 1)
        footer.addWidget(QSizeGrip(self), 0, Qt.AlignmentFlag.AlignBottom)
        page.addLayout(footer)
        for combo in (self.language, self.engine, self.devices, self.model):
            combo.currentIndexChanged.connect(self.persist)
        self.engine.currentIndexChanged.connect(self.update_engine)
        self.language.currentIndexChanged.connect(self.update_engine)
        self.model.currentIndexChanged.connect(self.update_engine)
        for check in (self.auto_type, self.digits, self.hold, self.system_audio, self.auto_pause):
            check.toggled.connect(self.persist)

    def _build_preferences(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 22, 4, 0)
        layout.setSpacing(13)
        layout.addWidget(label("Voice shortcut  ·  works across Windows", "eyebrow"))
        layout.addWidget(label("Press once to start recording; press again to stop and transcribe. Works while the bar is hidden. Click below, press your chosen keys, then Apply.", "muted", True))
        shortcut_row = QHBoxLayout()
        self.shortcut_edit = QKeySequenceEdit(QKeySequence(self.settings["voice_shortcut"]))
        self.shortcut_edit.setMaximumSequenceLength(1)
        self.shortcut_edit.setAccessibleName("Global voice typing shortcut")
        self.shortcut_edit.setToolTip("Use Ctrl or Alt with a letter, digit or Space, or a function key. F12 stays the keyboard toggle.")
        shortcut_row.addWidget(self.shortcut_edit, 1)
        self.shortcut_apply = button("Apply shortcut", self.apply_voice_shortcut)
        shortcut_row.addWidget(self.shortcut_apply)
        self.shortcut_reset = button("Reset default", self.reset_voice_shortcut)
        shortcut_row.addWidget(self.shortcut_reset)
        layout.addLayout(shortcut_row)
        self.shortcut_status = label(f"Voice shortcut: {self.settings['voice_shortcut']}", "muted", True)
        layout.addWidget(self.shortcut_status)
        layout.addWidget(label("Local recognition", "eyebrow"))
        row = QHBoxLayout()
        self.model = QComboBox()
        for name, key in (("Tiny · fastest / lowest accuracy", "tiny"), ("Base · balanced", "base"), ("Small · larger / slower", "small")):
            self.model.addItem(name, key)
        self.model.setCurrentIndex(self.model.findData(self.settings["model"]))
        self.model.setAccessibleName("Offline Whisper model")
        row.addWidget(self.model, 1)
        self.prepare_btn = button("Download offline model", self.prepare_model)
        row.addWidget(self.prepare_btn)
        layout.addLayout(row)
        layout.addWidget(label("Download Tiny, Base or Small once to use offline voice. After download, local mode needs no internet, API key or GPU. Online voice works immediately with internet. Offline Bangla accuracy was poor in our sample checks; use online recognition for Bangla.", "muted", True))
        layout.addWidget(label("Appearance & startup", "eyebrow"))
        theme_row = QHBoxLayout()
        theme_row.addWidget(label("Theme"))
        self.theme_choice = QComboBox()
        self.theme_choice.addItem("Light Glass · transparent", "light")
        self.theme_choice.addItem("Dark Glass · transparent", "dark")
        self.theme_choice.setCurrentIndex(self.theme_choice.findData(self.settings["theme"]))
        self.theme_choice.setAccessibleName("Application theme")
        self.theme_choice.currentIndexChanged.connect(self.change_theme)
        theme_row.addWidget(self.theme_choice, 1)
        layout.addLayout(theme_row)
        appearance = QHBoxLayout()
        appearance.addWidget(label("Floating bar opacity"))
        self.bar_opacity = QComboBox()
        for value in (100, 90, 80, 70):
            self.bar_opacity.addItem("100% · crisp controls" if value == 100 else f"{value}%", value)
        self.bar_opacity.setCurrentIndex(self.bar_opacity.findData(self.settings["bar_opacity"]))
        self.bar_opacity.setAccessibleName("Floating bar opacity")
        self.bar_opacity.currentIndexChanged.connect(self.persist)
        appearance.addWidget(self.bar_opacity, 1)
        layout.addLayout(appearance)
        self.autostart = QCheckBox("Start JoyKeyboard when I sign in to Windows")
        self.autostart.setToolTip("Shows the floating bar at sign-in. Recording starts only when requested.")
        try:
            self.autostart.setChecked(startup.is_enabled())
        except OSError:
            self.autostart.setEnabled(False)
            self.autostart.setToolTip("Windows startup settings could not be read.")
        self.autostart.toggled.connect(self.change_autostart)
        layout.addWidget(self.autostart)
        encoding_row = QHBoxLayout()
        encoding_row.addWidget(label("Output encoding"))
        self.output_encoding = QComboBox()
        self.output_encoding.addItem("Unicode · modern apps", "unicode")
        self.output_encoding.addItem("Bijoy ANSI · legacy fonts", "bijoy")
        self.output_encoding.setCurrentIndex(self.output_encoding.findData(self.settings["output_encoding"]))
        self.output_encoding.currentIndexChanged.connect(self.persist)
        self.output_encoding.setToolTip("ANSI output needs a compatible legacy Bengali font in the destination app.")
        encoding_row.addWidget(self.output_encoding, 1)
        layout.addLayout(encoding_row)
        self.hold = QCheckBox("Hold Right Ctrl to record; release to transcribe")
        self.hold.setChecked(self.settings["hold_key"])
        layout.addWidget(self.hold)
        self.auto_pause = QCheckBox("Finish automatically after a speech pause (1.5 seconds)")
        self.auto_pause.setChecked(self.settings["auto_pause"])
        self.auto_pause.setToolTip("Detects speech locally, then finishes and transcribes after a pause. Stops listening after each phrase. Disable for long thinking pauses; holding Right Ctrl still waits for release.")
        layout.addWidget(self.auto_pause)
        self.digits = QCheckBox("Use বাংলা digits in Bengali transcripts")
        self.digits.setChecked(self.settings["bangla_digits"])
        layout.addWidget(self.digits)
        layout.addWidget(label("Speech replacements", "eyebrow"))
        layout.addWidget(label(r"One rule per line: spoken phrase => replacement. Use \n for a new line.", "muted", True))
        self.rules_editor = QPlainTextEdit(format_rules(self.settings["rules"]))
        self.rules_editor.setAccessibleName("Speech replacement rules")
        layout.addWidget(self.rules_editor, 1)
        layout.addWidget(button("Save replacements", self.save_rules))
        self.tabs.addTab(page, "Preferences")

    def _build_help(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 24, 4, 0)
        help_text = label("""<h2>Speak freely. Keep control.</h2>
<p><b>Custom global shortcut:</b> Preferences → Voice shortcut lets you press your chosen keys, then Apply. Default is Ctrl+Alt+Space. Press once to start recording, again to finish and transcribe, even with the bar hidden. Conflicting shortcuts keep your previous working choice. Reset default restores Ctrl+Alt+Space. Automatic speech-pause finishing can be disabled for manual shortcut control. JoyKeyboard must stay running; protected Windows desktops cannot receive the shortcut.</p>
<p><b>Start:</b> choose Bengali or English, select your microphone, focus a document and press <b>Ctrl + Alt + Space</b>. Speech pauses of about 1.5 seconds finish and transcribe automatically by default. Recording then stops; start again for the next phrase. Manual Finish or the shortcut also works. Ten seconds without speech discards an empty recording; the maximum is 60 seconds. Disable automatic finishing in Preferences or the bar menu for longer pauses.</p>
<p><b>Free online:</b> Google web mode needs internet and no user API key. Audio goes to Google. Its shared testing access can be limited or revoked; availability is not guaranteed.</p>
<p><b>Free offline:</b> download Tiny, Base or Small once in Preferences, then choose Whisper in Voice studio. No internet needed after download, no API key or per-minute service fee. Online voice works immediately with internet. Accuracy and speed depend on model and PC.</p>
<p><b>Keyboard:</b> F12 toggles system-wide typing. Choose phonetic, English or a fixed layout under Keyboard &amp; tools. A floating preview shows composition; Space/Enter commits the word, F1–F8 chooses a suggestion. Keyboard mode starts off each launch. Custom/browser secure fields may not be detected; turn keyboard mode off before passwords.</p>
<p><b>Official cloud credentials:</b> Google Cloud Speech-to-Text is a separate service. Create a project, enable billing and Speech-to-Text, then configure Application Default Credentials. It is not the generic key used by online mode. This version does not include a paid Cloud connector.</p>
<p><a href='https://docs.cloud.google.com/speech-to-text/docs/setup'>Google Cloud setup</a> &nbsp; · &nbsp;
<a href='https://docs.cloud.google.com/speech-to-text/docs/v1/authentication'>Authentication</a> &nbsp; · &nbsp;
<a href='https://cloud.google.com/speech-to-text/pricing'>Current pricing</a></p>
<p><b>Compatibility:</b> Windows 10/11, 64-bit Intel/AMD. Microphone required. Automatic typing works in many standard text fields; elevated apps, secure fields and some custom editors may block it. Copy transcript when needed.</p>
<p><b>Your data:</b> audio is not saved automatically. Local dictionary learning and word transitions are saved on quit; no cloud upload. Gemini text assistance uploads only text you explicitly submit with your own session key. Preferences and user models live in your local JoyKeyboard data folder.</p>
<p><b>Floating bar:</b> opens on launch. Drag the grip to move it; position is remembered. The language/layout selector and menu reach voice engines, inputs, output encoding and every tool. Closing this workspace returns to the bar; use Quit in its menu to exit.</p>
<p><b>Appearance and startup:</b> Light Glass and Dark Glass both show actual desktop colors through Windows compositor blur. Choose either in Preferences or the bar menu; choice is remembered. At 100% bar opacity controls stay crisp; Both materials remain translucent. Your selected light/dark theme is saved; older Clear Glass preferences become Light Glass. Drag the title to move the workspace, double-click to maximize/restore, or resize from the lower-right grip. Preferences and the installer offer startup at Windows sign-in, without automatically recording.</p>
<h3>Developed by Sohaib Islam Joy</h3>
<p><a href='https://www.facebook.com/sohaib.islam1997'>Facebook · Sohaib Islam Joy</a></p>
<p>JoyKeyboard 0.4.9 · Independently built keyboard and voice utility</p>""", wrap=True)
        help_text.setTextFormat(Qt.TextFormat.RichText)
        help_text.setOpenExternalLinks(True)
        layout.addWidget(help_text)
        layout.addStretch()
        self.tabs.addTab(page, "Help and privacy")

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        self.tray.setToolTip(f"JoyKeyboard · {self.settings['voice_shortcut']}")
        menu = QMenu()
        for text, callback in (("Show floating bar", self.show_compact), ("Voice studio / tools", self.show_studio), ("Keyboard ON / OFF · F12", self.toggle_keyboard), ("Record / finish", self.toggle_record), ("Quit", self.request_quit)):
            action = QAction(text, menu)
            action.triggered.connect(callback)
            menu.addAction(action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.show_compact() if reason in (QSystemTrayIcon.ActivationReason.DoubleClick, QSystemTrayIcon.ActivationReason.Trigger) else None)
        if not self.smoke:
            self.tray.show()

    def show_studio(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def show_compact(self):
        self.hide()
        self.compact.reveal()

    def open_workspace(self, page=0, tool=None):
        self.tabs.setCurrentIndex(page)
        if tool is not None:
            self.tools.panels.setCurrentIndex(tool)
        self.show_studio()

    def set_keyboard_layout(self, identity):
        if identity in LAYOUTS:
            self.keyboard_hook.set_layout(identity)
            self.settings["keyboard_layout"] = identity
            self.tools.layout_choice.blockSignals(True)
            self.tools.layout_choice.setCurrentIndex(self.tools.layout_choice.findData(identity))
            self.tools.layout_choice.blockSignals(False)
            self.persist()
            self.compact.sync_controls()

    def toggle_keyboard(self):
        self.set_keyboard_enabled(not self.keyboard_hook.enabled)

    def set_keyboard_enabled(self, enabled):
        if enabled and (self.recorder is not None or self.job is not None):
            self.set_status("Voice work in progress", "Finish voice work before enabling the keyboard.", True)
            return
        self.keyboard_hook.set_enabled(enabled)
        self.sync_keyboard_controls()
        if enabled:
            self.compact.reveal()

    def sync_keyboard_controls(self):
        enabled = self.keyboard_hook.enabled
        if enabled and not self.previous_keyboard_enabled:
            self.compact.reveal()
        self.previous_keyboard_enabled = enabled
        text = "Keyboard ON · F12" if enabled else "Keyboard OFF · F12"
        if self.keyboard_toggle.text() != text:
            self.keyboard_toggle.setText(text)
        self.compact.sync_controls()
        if self.tools.keyboard_enabled.isChecked() != enabled:
            self.tools.keyboard_enabled.blockSignals(True)
            self.tools.keyboard_enabled.setChecked(enabled)
            self.tools.keyboard_enabled.blockSignals(False)

    def show_candidates(self, raw, rendered, suggestions):
        self.tools.update_candidates(raw, rendered, suggestions)
        self.compact.update_candidates(raw, rendered, suggestions)

    def show_keyboard_error(self, message):
        self.set_status("Keyboard paused", message, True)
        self.sync_keyboard_controls()

    def insert_tool_text(self, text):
        if self.recorder is not None or self.job is not None:
            raise RuntimeError("Finish current voice operation before inserting text.")
        if not self.last_external:
            raise RuntimeError("Focus the destination document first, then return to JoyKeyboard.")
        self.keyboard_hook.reset()
        insert_text(self.last_external, text)

    def encode_output(self, text):
        return to_ansi(text) if self.output_encoding.currentData() == "bijoy" else text

    def refresh_devices(self):
        try:
            self.devices.blockSignals(True)
            self.devices.clear()
            self.devices.addItem("System default microphone", None)
            for index, name in list_microphones():
                self.devices.addItem(name, index)
            index = self.devices.findData(self.settings["device"])
            self.devices.setCurrentIndex(max(0, index))
        except Exception as exc:
            self.set_status("Microphone unavailable", str(exc), True)
        finally:
            self.devices.blockSignals(False)

    def persist(self):
        self.settings.update(language=self.language.currentData(), engine=self.engine.currentData(),
                             model=self.model.currentData(), device=self.devices.currentData(),
                             auto_type=self.auto_type.isChecked(), bangla_digits=self.digits.isChecked(),
                             auto_pause=self.auto_pause.isChecked(),
                             hold_key=self.hold.isChecked(), system_audio=self.system_audio.isChecked(),
                             output_encoding=self.output_encoding.currentData(),
                             bar_opacity=self.bar_opacity.currentData(), theme=self.theme_choice.currentData())
        if hasattr(self, "tools"):
            if self.keyboard_hook.output_encoding != self.settings["output_encoding"]:
                self.keyboard_hook.set_output_encoding(self.settings["output_encoding"])
            self.compact.sync_controls()
        try:
            if not self.smoke:
                save_settings(self.settings_path, self.settings)
        except OSError as exc:
            self.set_status("Preferences not saved", str(exc), True)

    def apply_theme(self):
        self.setStyleSheet(style_sheet("workspace", self.settings["theme"]))
        self.tools.setStyleSheet(style_sheet("tools", self.settings["theme"]))
        self.tray.contextMenu().setStyleSheet(style_sheet("bar", self.settings["theme"]))
        self.compact.apply_theme()
        self._refresh_blur()
        round_window(self, 0 if self.isMaximized() else 24)
        self.update()

    def _refresh_blur(self):
        self.native_glass = set_glass_blur(int(self.winId()), True)
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._refresh_blur)

    def paintEvent(self, event):
        paint_glass(self, 0 if self.isMaximized() else 24, not self.native_glass, self.settings["theme"] == "dark")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        round_window(self, 0 if self.isMaximized() else 24)

    def change_theme(self):
        self.settings["theme"] = self.theme_choice.currentData()
        self.apply_theme()
        self.persist()

    def change_autostart(self, enabled):
        try:
            if not self.smoke:
                startup.set_enabled(enabled)
        except OSError as exc:
            self.autostart.blockSignals(True)
            self.autostart.setChecked(not enabled)
            self.autostart.blockSignals(False)
            self.set_status("Startup setting not saved", str(exc), True)

    def voice_shortcut_triggered(self):
        focused = QApplication.focusWidget()
        editing = self.isActiveWindow() and (self.shortcut_edit.hasFocus() or (focused and self.shortcut_edit.isAncestorOf(focused)))
        if self.quitting or editing:
            return
        self.toggle_record()

    def apply_voice_shortcut(self):
        if self.recorder is not None or self.job is not None:
            self.shortcut_status.setText("Finish current voice work before changing the shortcut.")
            return
        previous = self.settings["voice_shortcut"]
        previous_registered = self.voice_hotkey.shortcut if self.voice_hotkey else None
        try:
            shortcut = parse_voice_shortcut(self.shortcut_edit.keySequence().toString(QKeySequence.SequenceFormat.PortableText))[0]
            if self.voice_hotkey:
                self.voice_hotkey.register(shortcut)
            if not self.smoke:
                save_settings(self.settings_path, {**self.settings, "voice_shortcut": shortcut})
        except (ValueError, OSError) as exc:
            if self.voice_hotkey and self.voice_hotkey.shortcut != previous_registered:
                if previous_registered:
                    self.voice_hotkey.register(previous_registered)
                else:
                    self.voice_hotkey.close()
                    self.voice_hotkey = VoiceHotkey(int(self.winId()), self.voice_shortcut_triggered)
            self.shortcut_edit.setKeySequence(QKeySequence(previous))
            self.shortcut_status.setText(f"Shortcut unchanged. {exc}")
            return
        self.settings["voice_shortcut"] = shortcut
        self.shortcut_edit.setKeySequence(QKeySequence(shortcut))
        self.shortcut_status.setText(f"Active globally: {shortcut} · press to start / finish")
        self.tray.setToolTip(f"JoyKeyboard · {shortcut}")
        self.shortcut_hint.setText(f"{shortcut}  ·  record / finish\nEsc in studio  ·  cancel")
        self.transcript.setPlaceholderText(f"Focus your document and press {shortcut} to start / finish voice typing.")
        self.compact.sync_controls()

    def reset_voice_shortcut(self):
        self.shortcut_edit.setKeySequence(QKeySequence(DEFAULT_VOICE_SHORTCUT))
        self.apply_voice_shortcut()

    def save_rules(self):
        try:
            self.settings["rules"] = parse_rules(self.rules_editor.toPlainText())
            self.persist()
            self.message.setText("Speech replacements saved.")
        except ValueError as exc:
            self.message.setText(str(exc))

    def update_engine(self):
        offline = self.engine.currentData() == "offline"
        ready = self.recognizer.model_ready(self.model.currentData())
        note = ("Local audio processing. Model ready." if ready else "Prepare a model in Preferences before recording.") if offline else "Free personal/testing access. Audio sent to Google; internet required."
        if offline and self.language.currentData() == "bn-BD":
            note += " Offline Bangla was unreliable in sample checks; online recognition is recommended."
        self.engine_note.setText(note)

    def set_status(self, title, message="", error=False):
        self.state.setText(title)
        self.state.setProperty("error", error)
        self.state.style().unpolish(self.state)
        self.state.style().polish(self.state)
        if hasattr(self, "compact"):
            self.compact.set_status(title, message, error)
        if message:
            self.message.setText(message)

    def _controls(self, enabled):
        for widget in (self.shortcut_edit, self.shortcut_apply, self.shortcut_reset):
            widget.setEnabled(enabled)
        for widget in (self.language, self.engine, self.devices, self.model, self.prepare_btn, self.system_audio, self.output_encoding, self.auto_pause):
            widget.setEnabled(enabled)

    def _idle(self):
        self.stop_pause_monitor()
        self.record_btn.setEnabled(True)
        self.record_btn.setText("●  Start recording")
        self.cancel_btn.setEnabled(False)
        self.meter.setValue(0)
        self._controls(True)
        self.compact.sync_controls()
        if self.keyboard_resume and not self.quitting:
            self.keyboard_resume = False
            self.keyboard_hook.set_enabled(True)
            self.sync_keyboard_controls()
        elif self.quitting:
            self.keyboard_resume = False

    def toggle_record(self):
        if self.recorder is not None:
            self.finish_recording()
        elif self.job is None:
            self.start_recording()

    def start_recording(self):
        if self.engine.currentData() == "offline" and not self.recognizer.model_ready(self.model.currentData()):
            self.set_status("Prepare offline model", "Open Preferences and download a model first.", True)
            return
        self.generation += 1
        self.cancel_event = threading.Event()
        self.keyboard_resume = self.keyboard_hook.enabled
        self.keyboard_hook.set_enabled(False)
        self.keyboard_hook.reset()
        active = foreground_target()
        self.target = active if active and active.pid != os.getpid() else self.last_external
        self.recorder = LoopbackRecorder() if self.system_audio.isChecked() else Recorder(self.devices.currentData())
        try:
            self.recorder.start()
        except Exception as exc:
            self.recorder = None
            self._idle()
            self.set_status("Could not record", str(exc), True)
            return
        self.started = time.monotonic()
        self._controls(False)
        self.cancel_btn.setEnabled(True)
        self.record_btn.setText("■  Finish and transcribe")
        if self.auto_pause.isChecked():
            self.pause_monitor = PauseMonitor(self.recorder)
            self.pause_monitor.start()
        self.set_status("Listening…", f"Pause for about 1.5 seconds to finish automatically, or press {self.settings['voice_shortcut']} again to stop and transcribe." if self.auto_pause.isChecked() else f"Press {self.settings['voice_shortcut']} again to stop and transcribe. Cancel discards recording.")

    def stop_pause_monitor(self):
        monitor, self.pause_monitor = self.pause_monitor, None
        if monitor is not None:
            monitor.stop()

    def finish_recording(self):
        self.stop_pause_monitor()
        recorder, self.recorder = self.recorder, None
        if recorder is None:
            return
        try:
            audio, rate = recorder.stop()
        except Exception as exc:
            self._idle()
            self.set_status("Recording failed", str(exc), True)
            return
        token = self.generation
        language, engine, model = self.language.currentData(), self.engine.currentData(), self.model.currentData()
        self.record_btn.setEnabled(False)
        self.set_status("Transcribing…", "You can cancel; results from cancelled work will never be typed.")
        self.start_job(lambda status: self.recognizer.transcribe(audio, rate, language, engine, model, status=status, cancel_event=self.cancel_event),
                       lambda text: self.receive_text(token, text))

    def start_job(self, function, success):
        self.job = Job(function)
        self.job.result.connect(success)
        self.job.failed.connect(self.job_error)
        self.job.progress.connect(self.show_progress)
        self.job.finished.connect(self.job_finished)
        self.job.start()
        self.compact.sync_controls()

    def show_progress(self, message):
        self.message.setText(message)
        self.compact.set_status("Working…", message)

    def receive_text(self, token, text):
        if token != self.generation or self.cancel_event.is_set():
            return
        text = process_text(text, self.language.currentData(), self.settings["rules"], self.digits.isChecked())
        if not text:
            self.set_status("No speech found", "Try a little closer to the microphone.")
            return
        self.last_text = text
        self.keyboard_engine.commit_sentence(text)
        cursor = self.transcript.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(("\n\n" if self.transcript.toPlainText() else "") + text)
        self.set_status("Words, delivered", "Transcript ready. Edit, copy or save whenever you like.")
        if self.auto_type.isChecked() and self.target:
            QTimer.singleShot(160, lambda: self.deliver(token, self.encode_output(text) + " "))

    def deliver(self, token, text, attempts=0):
        if token != self.generation or self.cancel_event.is_set():
            return
        if any(key_down(key) for key in (0x10, 0x11, 0x12, 0x5B, 0x5C)) and attempts < 30:
            QTimer.singleShot(100, lambda: self.deliver(token, text, attempts + 1))
            return
        try:
            if not self.target:
                raise RuntimeError("Focus an external document first, then use the global shortcut.")
            insert_text(self.target, text)
            self.message.setText("Typed into original app. Clipboard unchanged.")
        except RuntimeError as exc:
            self.message.setText(str(exc))
            self.compact.set_status("Text kept in transcript", str(exc), True)

    def job_error(self, message):
        if not self.cancel_event.is_set():
            self.set_status("Needs attention", message, True)

    def job_finished(self):
        job, self.job = self.job, None
        if job:
            job.deleteLater()
        self._idle()
        self.update_engine()
        if self.cancel_event.is_set():
            self.set_status("Cancelled", "Recording discarded. Ready for a new session.")
        if self.quitting:
            QApplication.quit()

    def prepare_model(self):
        if self.job is not None or self.recorder is not None:
            return
        self.cancel_event = threading.Event()
        self._controls(False)
        self.record_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.set_status("Preparing model…", "Downloading to your local data folder. This can take a few minutes.")
        model = self.model.currentData()
        self.start_job(lambda status: self.recognizer.prepare_model(model, status=status, cancel_event=self.cancel_event),
                       lambda _: self.set_status("Offline model ready", "Choose Whisper in Voice studio to use local recognition."))

    def cancel(self):
        self.stop_pause_monitor()
        self.generation += 1
        self.cancel_event.set()
        if self.recorder:
            try:
                self.recorder.cancel()
            except RuntimeError as exc:
                self.message.setText(f"Recording cancelled; audio device cleanup needs attention: {exc}")
            self.recorder = None
        if self.job is None:
            self._idle()
            self.set_status("Cancelled", "Recording discarded.")
        else:
            self.cancel_btn.setEnabled(False)
            self.set_status("Cancelled", "Waiting for current engine operation to finish. No text will be typed.")

    def tick(self):
        active = foreground_target()
        if active and active.pid != os.getpid():
            self.last_external = active
            destination = f"Destination: {active.title[:70] or 'external app'}"
            if self.target_note.text() != destination:
                self.target_note.setText(destination)
        hold = key_down(0xA3)
        if self.hold.isChecked():
            if hold and not self.last_hold and not key_down(0x12) and self.recorder is None and self.job is None:
                self.start_recording()
            elif not hold and self.last_hold and self.recorder:
                self.finish_recording()
        self.last_hold = hold
        if (self.recorder is not None or self.job is not None) and self.keyboard_hook.enabled:
            self.keyboard_resume = True
            self.keyboard_hook.set_enabled(False)
        self.sync_keyboard_controls()
        if self.recorder:
            elapsed = time.monotonic() - self.started
            self.clock.setText(f"00:{min(int(elapsed), 60):02d}  /  01:00")
            self.meter.setValue(min(100, int(self.recorder.level * 100)))
            self.compact.update_recording(elapsed, self.recorder.level)
            if self.recorder.error:
                error = self.recorder.error
                self.cancel()
                self.set_status("Microphone interrupted", error, True)
            elif elapsed >= 60:
                self.finish_recording()
            elif self.pause_monitor is not None and not (self.hold.isChecked() and hold):
                if self.pause_monitor.error:
                    message = self.pause_monitor.error
                    self.stop_pause_monitor()
                    self.set_status("Finish manually", message, True)
                elif self.pause_monitor.reason == "pause":
                    self.finish_recording()
                elif self.pause_monitor.reason == "no_speech":
                    self.cancel()
                    self.set_status("No speech detected", "Recording discarded locally. Check the microphone and try again.", True)

    def copy_text(self):
        QApplication.clipboard().setText(self.transcript.toPlainText())
        self.message.setText("Transcript copied.")
        self.compact.set_status("Transcript copied")

    def type_again(self):
        if self.job is not None or self.recorder is not None:
            return
        self.target = self.last_external
        self.cancel_event = threading.Event()
        self.deliver(self.generation, self.encode_output(self.transcript.toPlainText()))

    def save_text(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save transcript", "JoyKeyboard transcript.txt", "Text files (*.txt)")
        if path:
            try:
                Path(path).write_text(self.transcript.toPlainText(), encoding="utf-8")
                self.message.setText("Transcript saved.")
            except OSError as exc:
                self.message.setText(f"Could not save transcript: {exc}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancel()
        else:
            super().keyPressEvent(event)

    def request_quit(self):
        if not self.smoke and not self.tools.confirm_document_close():
            return
        self.quitting = True
        self.close()

    def closeEvent(self, event):
        if not self.smoke and not self.quitting:
            self.show_compact()
            event.ignore()
            return
        if self.tools.shutdown() is False:
            event.ignore()
            self.quitting = False
            self.set_status("Waiting for text assistant", "Let the current request finish, then Quit again.", True)
            return
        self.keyboard_hook.stop()
        if self.voice_hotkey:
            self.voice_hotkey.close()
        if not self.smoke and not self.keyboard_closed:
            try:
                self.keyboard_engine.save()
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, "Dictionary not saved", str(exc))
            self.keyboard_closed = True
        self.cancel()
        if self.job is not None:
            self.quitting = True
            self.hide()
            self.compact.hide()
            event.ignore()
            return
        self.poll.stop()
        self.compact.close()
        self.tray.hide()
        event.accept()
        if not self.smoke:
            QApplication.quit()


def run(smoke_path=None):
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName("JoyKeyboard")
    app.setOrganizationName("JoyKeyboard")
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)
    lock = None
    if not smoke_path:
        directory = data_directory()
        directory.mkdir(parents=True, exist_ok=True)
        lock = QLockFile(str(directory / "JoyKeyboard.lock"))
        lock.setStaleLockTime(0)
        if not lock.tryLock(0):
            QMessageBox.information(None, "JoyKeyboard already running", "JoyKeyboard is already running. Open it from the Windows notification area.")
            return 0
    window = JoyWindow(smoke=bool(smoke_path))
    window.show_compact()
    if smoke_path:
        def capture():
            path = Path(smoke_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            if not window.compact.grab().save(str(path)):
                raise RuntimeError("Could not save UI verification screenshot.")
            window.close()
            app.quit()
        QTimer.singleShot(600, capture)
    return app.exec()
