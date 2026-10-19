"""Keyboard workspace, local text tools, and explicitly requested online assistance."""
from __future__ import annotations

import json
import os
import re
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from PySide6.QtCore import QMarginsF, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPageLayout, QPageSize, QPdfWriter, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from keyboard_engine import LAYOUTS, from_ansi, to_ansi
from theme import TOOLS_STYLE

MAX_FILE_BYTES = 10 * 1024 * 1024


def _note(text):
    widget = QLabel(text)
    widget.setWordWrap(True)
    widget.setObjectName("muted")
    return widget


def _button(text, callback):
    widget = QPushButton(text)
    widget.clicked.connect(callback)
    return widget


def _edit(name, placeholder=""):
    widget = QLineEdit()
    widget.setAccessibleName(name)
    widget.setPlaceholderText(placeholder)
    return widget


def _text(name, readonly=False):
    widget = QPlainTextEdit()
    widget.setAccessibleName(name)
    widget.setReadOnly(readonly)
    return widget


def _atomic_text(path, text):
    """Keep the original document intact when a write fails."""
    path = Path(path)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def gemini_text(key, model, instruction, text):
    """REST generateContent: https://ai.google.dev/api/generate-content."""
    if not key.strip():
        raise ValueError("Enter your Gemini API key. Key stays in memory for this session.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,512}", key.strip()):
        raise ValueError("Gemini API key contains invalid characters or is too long.")
    if not re.fullmatch(r"gemini-[A-Za-z0-9._-]{1,100}", model):
        raise ValueError("Use a Gemini model ID, for example gemini-3.5-flash.")
    if not text.strip():
        raise ValueError("Enter or select text first.")
    if len(text) > 50_000:
        raise ValueError("Select at most 50,000 characters for one request.")
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps({
            "contents": [{"parts": [{"text": f"{instruction}\n\n{text}"}]}],
            "generationConfig": {"maxOutputTokens": 4096},
        }).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key.strip()},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read(2 * 1024 * 1024 + 1)
        if len(body) > 2 * 1024 * 1024:
            raise ValueError("Gemini response exceeded the size limit.")
        data = json.loads(body)
    except urllib.error.HTTPError as exc:
        raise ValueError(f"Gemini returned HTTP {exc.code}. Check key, model access, quota and billing.") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ValueError("Gemini connection failed or timed out. Check internet connection.") from None
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError("Gemini returned an unreadable response.") from None
    candidates = data.get("candidates", []) if isinstance(data, dict) else []
    candidate = candidates[0] if isinstance(candidates, list) and candidates else {}
    content = candidate.get("content", {}) if isinstance(candidate, dict) else {}
    parts = content.get("parts", []) if isinstance(content, dict) else []
    if not isinstance(parts, list):
        raise ValueError("Gemini returned an unreadable response.")
    result = "".join(part["text"] for part in parts
                     if isinstance(part, dict) and isinstance(part.get("text"), str) and not part.get("thought")).strip()
    if not result:
        raise ValueError("Gemini returned no text. The request may have been blocked or interrupted.")
    return result


class AssistantJob(QThread):
    result = Signal(str)
    failed = Signal(str)

    def __init__(self, key, model, instruction, text, parent=None):
        super().__init__(parent)
        self.arguments = (key, model, instruction, text)

    def run(self):
        try:
            result = gemini_text(*self.arguments)
            if not self.isInterruptionRequested():
                self.result.emit(result)
        except Exception as exc:
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))
        finally:
            self.arguments = ()


class KeyboardTools(QWidget):
    settings_changed = Signal()
    layout_changed = Signal(str)
    enabled_changed = Signal(bool)
    candidate_selected = Signal(int)

    def __init__(self, owner, engine, insert_callback):
        super().__init__(owner)
        self.engine = engine
        self.insert_callback = insert_callback
        self.document_path = None
        self.ai_job = None
        self.ai_cancelled = False
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 10, 0, 0)
        self.panels = QTabWidget()
        root.addWidget(self.panels)
        self._build_keyboard()
        self._build_words()
        self._build_converter()
        self._build_screen_keys()
        self._build_docpad()
        self._build_assistant()
        self.status = _note("Local keyboard tools ready. Voice controls stay in Voice studio.")
        root.addWidget(self.status)
        self.setStyleSheet(TOOLS_STYLE)

    def _panel(self, name):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(10)
        self.panels.addTab(panel, name)
        return layout

    def _attempt(self, action, message=None):
        try:
            result = action()
            if message:
                self.status.setText(message)
            return result
        except Exception as exc:
            self.status.setText(f"Could not complete action: {exc}")
            return None

    def _send(self, text):
        if text:
            self._attempt(lambda: self.insert_callback(text), "Text sent to selected destination.")
        else:
            self.status.setText("Enter text first.")

    def _copy(self, text):
        QApplication.clipboard().setText(text)
        self.status.setText("Copied to clipboard.")

    def _build_keyboard(self):
        page = self._panel("Keyboard")
        row = QHBoxLayout()
        self.keyboard_enabled = QCheckBox("System-wide keyboard · F12")
        self.keyboard_enabled.toggled.connect(self.enabled_changed.emit)
        row.addWidget(self.keyboard_enabled)
        self.layout_choice = QComboBox()
        self.layout_choice.setAccessibleName("Keyboard layout")
        for identity, name in LAYOUTS.items():
            self.layout_choice.addItem(name, identity)
        self.layout_choice.currentIndexChanged.connect(self._layout_changed)
        row.addWidget(self.layout_choice)
        page.addLayout(row)
        page.addWidget(_note("Type Latin keys below for a local preview. F12 enables typing into other apps; F1–F8 select global suggestions. Secure/elevated apps may reject insertion."))
        self.preview_input = _edit("Local typing input", "Try: ami banglay gan gai")
        self.preview_input.textChanged.connect(self._preview_changed)
        page.addWidget(self.preview_input)
        self.preview_output = _text("Converted typing preview", True)
        self.preview_output.setMaximumHeight(105)
        page.addWidget(self.preview_output)
        self.local_candidates = QListWidget()
        self.local_candidates.setAccessibleName("Local word suggestions")
        self.local_candidates.itemActivated.connect(self._local_candidate)
        page.addWidget(self.local_candidates)
        row = QHBoxLayout()
        row.addWidget(_button("Copy preview", lambda: self._copy(self.preview_output.toPlainText())))
        row.addWidget(_button("Insert preview", lambda: self._send(self.preview_output.toPlainText())))
        row.addWidget(_button("Learn preview", self._learn_preview))
        page.addLayout(row)
        self.live_state = _note("System keyboard idle")
        page.addWidget(self.live_state)
        self.global_candidates = QListWidget()
        self.global_candidates.setAccessibleName("System keyboard suggestions")
        self.global_candidates.setMaximumHeight(100)
        self.global_candidates.itemActivated.connect(lambda item: self.candidate_selected.emit(self.global_candidates.row(item)))
        page.addWidget(self.global_candidates)

    def _layout_changed(self):
        identity = self.layout_choice.currentData()
        self.layout_changed.emit(identity)
        self._preview_changed()

    def _preview_changed(self):
        try:
            text = self.engine.convert(self.preview_input.text(), self.layout_choice.currentData())
            self.preview_output.setPlainText(text)
            self.local_candidates.clear()
            word = text.split()[-1] if text.split() else ""
            if word:
                self.local_candidates.addItems(self.engine.suggest(word))
        except Exception as exc:
            if hasattr(self, "status"):
                self.status.setText(str(exc))

    def _local_candidate(self, item):
        raw = self.preview_input.text()
        parts = raw.rsplit(maxsplit=1)
        prefix = raw[:len(raw) - len(parts[-1])] if parts else ""
        self.preview_input.setText(prefix + item.text())

    def _learn_preview(self):
        def learn():
            if getattr(self.engine, "load_error", ""):
                raise ValueError(self.engine.load_error + " Import a valid backup before changing word data.")
            text = self.preview_output.toPlainText().strip()
            if not text:
                raise ValueError("Enter a word or sentence first.")
            previous = self.engine.export_data()
            try:
                self.engine.commit_sentence(text)
                self.engine.save()
            except Exception:
                self.engine.import_data(previous)
                raise
            self.settings_changed.emit()
        self._attempt(learn, "Preview learned for local suggestions and sentence prediction.")

    def update_candidates(self, raw, rendered, suggestions):
        self.live_state.setText(f"Keys: {raw}    →    {rendered}" if raw else "System keyboard idle")
        self.global_candidates.clear()
        self.global_candidates.addItems([f"F{index + 1}  {word}" for index, word in enumerate(suggestions[:8])])

    def _build_words(self):
        page = self._panel("Words")
        page.addWidget(_note("Custom words improve local suggestions. Snippets expand a short trigger when committed. Save applies edits. Import replaces local word data; export a backup first."))
        self.words_editor = _text("Custom words, one per line")
        self.words_editor.setPlaceholderText("Custom words · one per line")
        page.addWidget(self.words_editor)
        self.snippets_editor = _text("Snippets: trigger, tab, expansion")
        self.snippets_editor.setPlaceholderText("Snippets · trigger<TAB>expansion, one per line")
        page.addWidget(self.snippets_editor)
        self.reload_words()
        row = QHBoxLayout()
        row.addWidget(_button("Apply words & snippets", self.apply_words))
        row.addWidget(_button("Reload saved", self._choose_reload_words))
        row.addWidget(_button("Import JSON…", self._choose_import))
        row.addWidget(_button("Export JSON…", self._choose_export))
        page.addLayout(row)
        self.prediction_input = _edit("Sentence prediction context", "Enter previous words for local sentence prediction")
        self.prediction_input.textChanged.connect(self._predict)
        page.addWidget(self.prediction_input)
        self.predictions = QListWidget()
        self.predictions.setAccessibleName("Predicted next words")
        self.predictions.itemActivated.connect(lambda item: self._send(item.text() + " "))
        page.addWidget(self.predictions)

    def reload_words(self):
        self.words_editor.setPlainText("\n".join(self.engine.custom_words))
        self.snippets_editor.setPlainText("\n".join(f"{key}\t{value}" for key, value in self.engine.snippets.items()))
        self.words_editor.document().setModified(False)
        self.snippets_editor.document().setModified(False)

    def _confirm_word_edits(self):
        if not any(editor.document().isModified() for editor in (self.words_editor, self.snippets_editor)):
            return True
        answer = QMessageBox.question(self, "Unapplied word edits", "Apply word and snippet edits before continuing?",
                                      QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                      QMessageBox.StandardButton.Save)
        if answer == QMessageBox.StandardButton.Save:
            return bool(self.apply_words())
        return answer == QMessageBox.StandardButton.Discard

    def _choose_reload_words(self):
        if self._confirm_word_edits():
            self.reload_words()

    def apply_words(self):
        def apply():
            if getattr(self.engine, "load_error", ""):
                raise ValueError(self.engine.load_error + " Import a valid backup before changing word data.")
            snippets = {}
            for number, line in enumerate(self.snippets_editor.toPlainText().splitlines(), 1):
                if not line.strip():
                    continue
                if "\t" not in line:
                    raise ValueError(f"Snippet line {number} needs a tab between trigger and expansion.")
                key, value = line.split("\t", 1)
                if key in snippets:
                    raise ValueError(f"Duplicate snippet trigger on line {number}.")
                snippets[key] = value
            previous = self.engine.export_data()
            data = dict(previous)
            data["custom_words"] = [word.strip() for word in self.words_editor.toPlainText().splitlines() if word.strip()]
            data["snippets"] = snippets
            self.engine.import_data(data)
            try:
                self.engine.save()
            except Exception:
                self.engine.import_data(previous)
                raise
            self.reload_words()
            self.settings_changed.emit()
            return True
        return self._attempt(apply, "Custom words and snippets saved.")

    def import_dictionary(self, path):
        path = Path(path)
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("Dictionary JSON must be smaller than 10 MiB.")
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        previous = self.engine.export_data()
        previous_error = getattr(self.engine, "load_error", "")
        self.engine.import_data(data)
        try:
            self.engine.save()
        except Exception:
            self.engine.import_data(previous)
            if hasattr(self.engine, "load_error"):
                self.engine.load_error = previous_error
            raise
        self.reload_words()
        self.settings_changed.emit()

    def export_dictionary(self, path):
        _atomic_text(path, json.dumps(self.engine.export_data(), ensure_ascii=False, indent=2))

    def _choose_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import word data", "", "Word data (*.json)")
        if path:
            answer = QMessageBox.question(self, "Replace word data?", "Import replaces custom words, snippets, learned suggestions and unapplied edits. Export a backup first if you need the existing data. Continue?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
            self._attempt(lambda: self.import_dictionary(path), "Dictionary imported.")

    def _choose_export(self):
        if not self._confirm_word_edits():
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export word data", "joykeyboard-words.json", "Word data (*.json)")
        if path:
            self._attempt(lambda: self.export_dictionary(path), "Dictionary exported.")

    def _predict(self):
        self.predictions.clear()
        self.predictions.addItems(self.engine.predict(self.prediction_input.text()))

    def _build_converter(self):
        page = self._panel("Converter")
        page.addWidget(_note("Convert Bengali Unicode and legacy Bijoy/ANSI text. Legacy text needs a compatible font in the destination; conversion can lose unsupported characters."))
        self.converter_input = _text("Text to convert")
        self.converter_input.setPlaceholderText("Paste source text")
        page.addWidget(self.converter_input)
        row = QHBoxLayout()
        row.addWidget(_button("Unicode → Bijoy", lambda: self._convert_encoding(to_ansi)))
        row.addWidget(_button("Bijoy → Unicode", lambda: self._convert_encoding(from_ansi)))
        page.addLayout(row)
        self.converter_output = _text("Converted encoding", True)
        page.addWidget(self.converter_output)
        row = QHBoxLayout()
        row.addWidget(_button("Copy result", lambda: self._copy(self.converter_output.toPlainText())))
        row.addWidget(_button("Insert result", lambda: self._send(self.converter_output.toPlainText())))
        page.addLayout(row)

    def _convert_encoding(self, convert):
        self._attempt(lambda: self.converter_output.setPlainText(convert(self.converter_input.toPlainText())))

    def _build_screen_keys(self):
        page = self._panel("Screen keys")
        page.addWidget(_note("Compose text with Bengali or Latin keys, then Insert into the chosen destination. Shift changes Latin case. These keys compose text here; they do not simulate system Ctrl/Alt shortcuts."))
        row = QHBoxLayout()
        self.screen_language = QComboBox()
        self.screen_language.addItems(["বাংলা", "English"])
        self.screen_language.setAccessibleName("On-screen key language")
        self.screen_language.currentIndexChanged.connect(self._refresh_keys)
        row.addWidget(self.screen_language)
        self.screen_shift = QCheckBox("Shift")
        self.screen_shift.toggled.connect(self._refresh_keys)
        row.addWidget(self.screen_shift)
        page.addLayout(row)
        self.screen_keys = QGridLayout()
        self.screen_buttons = []
        for index in range(84):
            key = _button("", lambda checked=False, position=index: self._screen_character(position))
            key.setMinimumWidth(38)
            key.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self.screen_buttons.append(key)
            self.screen_keys.addWidget(key, index // 12, index % 12)
        page.addLayout(self.screen_keys)
        row = QHBoxLayout()
        for text, value in [("Space", " "), ("Enter", "\n"), ("Tab", "\t"), ("Backspace", None)]:
            key = _button(text, lambda checked=False, character=value: self._screen_insert(character))
            key.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            row.addWidget(key)
        page.addLayout(row)
        self.screen_text = _text("On-screen keyboard composition")
        page.addWidget(self.screen_text)
        row = QHBoxLayout()
        row.addWidget(_button("Copy text", lambda: self._copy(self.screen_text.toPlainText())))
        row.addWidget(_button("Insert text", lambda: self._send(self.screen_text.toPlainText())))
        row.addWidget(_button("Clear", self.screen_text.clear))
        page.addLayout(row)
        self._refresh_keys()

    def _refresh_keys(self):
        if self.screen_language.currentIndex() == 0:
            keys = "অ আ ই ঈ উ ঊ ঋ এ ঐ ও ঔ ং ঃ ঁ ক খ গ ঘ ঙ চ ছ জ ঝ ঞ ট ঠ ড ঢ ণ ত থ দ ধ ন প ফ ব ভ ম য র ল শ ষ স হ ড় ঢ় য় ৎ া ি ী ু ূ ৃ ে ৈ ো ৌ ্ । ০ ১ ২ ৩ ৪ ৫ ৬ ৭ ৮ ৯".split()
            if self.screen_shift.isChecked():
                keys = list("ািীুূৃেৈোৌ্ঁংঃ়ৎঽৗ০১২৩৪৫৬৭৮৯।,!?;:()[]{}+-=/%\"'@#&*")
        else:
            keys = list("1234567890-=qwertyuiop[]asdfghjkl;'zxcvbnm,./`\\")
            if self.screen_shift.isChecked():
                keys = list("!@#$%^&*()_+QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?~|")
        self.current_screen_keys = keys
        for index, key in enumerate(self.screen_buttons):
            character = keys[index] if index < len(keys) else ""
            key.setText(character)
            key.setAccessibleName(f"Insert {character}" if character else "Unused key")
            key.setVisible(bool(character))

    def _screen_character(self, index):
        if index < len(self.current_screen_keys):
            self._screen_insert(self.current_screen_keys[index])

    def _screen_insert(self, character):
        cursor = self.screen_text.textCursor()
        if character is None:
            cursor.deletePreviousChar()
        else:
            cursor.insertText(character)
        self.screen_text.setTextCursor(cursor)

    def _build_docpad(self):
        page = self._panel("DocPad")
        row = QHBoxLayout()
        row.addWidget(_button("New", self.new_document))
        row.addWidget(_button("Open…", self._choose_open_document))
        row.addWidget(_button("Save", self._choose_save_document))
        row.addWidget(_button("Save as…", lambda: self._choose_save_document(True)))
        row.addWidget(_button("Export PDF…", self._choose_pdf))
        page.addLayout(row)
        self.document_label = _note("Untitled · UTF-8 text")
        page.addWidget(self.document_label)
        self.docpad = _text("Document text")
        self.docpad.document().modificationChanged.connect(self._document_modified)
        page.addWidget(self.docpad)
        row = QHBoxLayout()
        self.find_text = _edit("Find text", "Find")
        self.replace_text = _edit("Replacement text", "Replace with")
        self.find_text.returnPressed.connect(self.find_next)
        row.addWidget(self.find_text)
        row.addWidget(self.replace_text)
        row.addWidget(_button("Find next", self.find_next))
        row.addWidget(_button("Replace all", self.replace_all))
        page.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(_button("Undo", self.docpad.undo))
        row.addWidget(_button("Redo", self.docpad.redo))
        row.addWidget(_button("Copy all", lambda: self._copy(self.docpad.toPlainText())))
        row.addWidget(_button("Insert selection / all", lambda: self._send(self.docpad.textCursor().selectedText().replace("\u2029", "\n") or self.docpad.toPlainText())))
        page.addLayout(row)

    def _document_modified(self):
        name = str(self.document_path) if self.document_path else "Untitled"
        self.document_label.setText(name + (" · unsaved changes" if self.docpad.document().isModified() else " · UTF-8 text"))

    def confirm_document_close(self, include_words=True):
        if include_words and not self._confirm_word_edits():
            return False
        if not self.docpad.document().isModified():
            return True
        answer = QMessageBox.question(self, "Unsaved document", "Save DocPad changes before continuing?", QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Save)
        if answer == QMessageBox.StandardButton.Save:
            return bool(self._choose_save_document())
        return answer == QMessageBox.StandardButton.Discard

    def new_document(self):
        if self.confirm_document_close(include_words=False):
            self.document_path = None
            self.docpad.clear()
            self.docpad.document().setModified(False)
            self._document_modified()

    def open_document(self, path):
        path = Path(path)
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("Text documents must be smaller than 10 MiB.")
        text = path.read_text(encoding="utf-8-sig")
        self.docpad.setPlainText(text)
        self.document_path = path
        self.docpad.document().setModified(False)
        self._document_modified()

    def save_document(self, path):
        _atomic_text(path, self.docpad.toPlainText())
        self.document_path = Path(path)
        self.docpad.document().setModified(False)
        self._document_modified()
        return True

    def _choose_open_document(self):
        if not self.confirm_document_close(include_words=False):
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open UTF-8 document", "", "Text files (*.txt *.md);;All files (*)")
        if path:
            self._attempt(lambda: self.open_document(path), "Document opened.")

    def _choose_save_document(self, save_as=False):
        path = self.document_path if not save_as else None
        if not path:
            path, _ = QFileDialog.getSaveFileName(self, "Save UTF-8 document", str(self.document_path or "Untitled.txt"), "Text files (*.txt);;All files (*)")
        return self._attempt(lambda: self.save_document(path), "Document saved.") if path else False

    def export_pdf(self, path):
        descriptor, temporary = tempfile.mkstemp(suffix=".pdf", dir=Path(path).parent)
        os.close(descriptor)
        try:
            writer = QPdfWriter(temporary)
            writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            writer.setPageMargins(QMarginsF(20, 20, 20, 20), QPageLayout.Unit.Millimeter)
            writer.setTitle(Path(path).stem)
            document = QTextDocument()
            document.setPlainText(self.docpad.toPlainText())
            document.print_(writer)
            del writer
            if Path(temporary).stat().st_size == 0:
                raise OSError("PDF writer produced an empty file.")
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _choose_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export document PDF", "JoyKeyboard-document.pdf", "PDF (*.pdf)")
        if path:
            self._attempt(lambda: self.export_pdf(path), "PDF exported.")

    def find_next(self):
        needle = self.find_text.text()
        if not needle:
            self.status.setText("Enter text to find.")
            return
        if not self.docpad.find(needle):
            cursor = self.docpad.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.docpad.setTextCursor(cursor)
            if not self.docpad.find(needle):
                self.status.setText("Text not found.")

    def replace_all(self):
        needle = self.find_text.text()
        if not needle:
            self.status.setText("Enter text to find.")
            return
        count = self.docpad.toPlainText().count(needle)
        cursor = self.docpad.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.docpad.setTextCursor(cursor)
        while self.docpad.find(needle):
            self.docpad.textCursor().insertText(self.replace_text.text())
        cursor.endEditBlock()
        self.status.setText(f"Replaced {count} occurrence(s). Undo restores original text.")

    def _build_assistant(self):
        page = self._panel("Text assistant")
        page.addWidget(_note("Optional Gemini assistance sends only the text below to Google when you click Generate. Needs your own API key and available quota; fees may apply. Key is never saved. Voice typing does not need this key."))
        row = QHBoxLayout()
        self.ai_key = _edit("Session-only Gemini API key", "Gemini API key · session only")
        self.ai_key.setEchoMode(QLineEdit.EchoMode.Password)
        row.addWidget(self.ai_key)
        row.addWidget(_button("Get API key ↗", lambda: QDesktopServices.openUrl(QUrl("https://aistudio.google.com/apikey"))))
        page.addLayout(row)
        row = QHBoxLayout()
        self.ai_model = QComboBox()
        self.ai_model.setEditable(True)
        self.ai_model.addItems(["gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite"])
        self.ai_model.setAccessibleName("Gemini model ID")
        row.addWidget(self.ai_model)
        self.ai_action = QComboBox()
        self.ai_action.setAccessibleName("Text assistance task")
        self.ai_action.addItem("Correct spelling & grammar", "Correct spelling, punctuation and grammar. Preserve language and meaning. Return corrected text only.")
        self.ai_action.addItem("Rewrite clearly", "Rewrite clearly and naturally in the same language. Preserve meaning. Return rewritten text only.")
        self.ai_action.addItem("Predict next sentence", "Continue with one plausible next sentence in the same language. Return only the new sentence.")
        self.ai_action.addItem("Translate to Bengali", "Translate this text into natural Bengali. Return translation only.")
        self.ai_action.addItem("Translate to English", "Translate this text into natural English. Return translation only.")
        row.addWidget(self.ai_action)
        page.addLayout(row)
        self.ai_input = _text("Text sent to Gemini")
        self.ai_input.setPlaceholderText("Paste text, or use DocPad selection below")
        page.addWidget(self.ai_input)
        row = QHBoxLayout()
        row.addWidget(_button("Use DocPad selection / all", self._assistant_from_document))
        self.ai_generate = _button("Generate", self.start_assistant)
        row.addWidget(self.ai_generate)
        self.ai_cancel = _button("Cancel result", self.cancel_assistant)
        self.ai_cancel.setEnabled(False)
        row.addWidget(self.ai_cancel)
        page.addLayout(row)
        self.ai_output = _text("Gemini result", True)
        page.addWidget(self.ai_output)
        row = QHBoxLayout()
        row.addWidget(_button("Copy result", lambda: self._copy(self.ai_output.toPlainText())))
        row.addWidget(_button("Insert result", lambda: self._send(self.ai_output.toPlainText())))
        page.addLayout(row)

    def _assistant_from_document(self):
        self.ai_input.setPlainText(self.docpad.textCursor().selectedText().replace("\u2029", "\n") or self.docpad.toPlainText())

    def start_assistant(self):
        if self.ai_job is not None:
            return
        key, model, text = self.ai_key.text().strip(), self.ai_model.currentText().strip(), self.ai_input.toPlainText()
        if not key or not text.strip():
            self.status.setText("Enter API key and text first. Key stays in memory for this session.")
            return
        self.ai_cancelled = False
        self.ai_job = AssistantJob(key, model, self.ai_action.currentData(), text, self)
        self.ai_job.result.connect(self._assistant_result)
        self.ai_job.failed.connect(self._assistant_failed)
        self.ai_job.finished.connect(self._assistant_finished)
        self.ai_generate.setEnabled(False)
        self.ai_cancel.setEnabled(True)
        self.status.setText("Generating via Google Gemini…")
        self.ai_job.start()

    def _assistant_result(self, text):
        if not self.ai_job or self.ai_cancelled:
            return
        self.ai_output.setPlainText(text)
        self.status.setText("Generated text ready for review.")

    def _assistant_failed(self, text):
        if self.ai_job and not self.ai_cancelled:
            self.status.setText(text)

    def _assistant_finished(self):
        job = self.ai_job
        self.ai_job = None
        if job:
            job.deleteLater()
        self.ai_generate.setEnabled(True)
        self.ai_cancel.setEnabled(False)

    def cancel_assistant(self):
        if self.ai_job:
            self.ai_cancelled = True
            self.ai_job.requestInterruption()
            self.status.setText("Result cancelled. Finishing the current network request; connection timeout is 20 seconds.")
            self.ai_cancel.setEnabled(False)

    def shutdown(self):
        self.ai_key.clear()
        if self.ai_job:
            self.ai_cancelled = True
            self.ai_job.requestInterruption()
            if not self.ai_job.wait(25_000):
                self.status.setText("Network request is still finishing. Try Quit again shortly.")
                return False
        return True

    def closeEvent(self, event):
        if not self.confirm_document_close() or not self.shutdown():
            event.ignore()
            return
        super().closeEvent(event)
