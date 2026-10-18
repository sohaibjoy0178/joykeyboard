import copy
import json
import time
import urllib.error

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

import tools_ui
from tools_ui import KeyboardTools, gemini_text


class FakeEngine:
    def __init__(self):
        self.custom_words = ["বাংলা"]
        self.snippets = {"addr": "Dhaka"}
        self.saved = 0
        self.sentences = []

    def convert(self, text, layout):
        return text.replace("bangla", "বাংলা") if layout == "phonetic" else text

    def suggest(self, prefix):
        return ["বাংলা", "বাংলায়"] if prefix.startswith("বাংল") else []

    def learn(self, word):
        self.custom_words.append(word)

    def predict(self, previous):
        return ["আছি"] if previous == "আমি ভালো" else []

    def commit_sentence(self, text):
        self.sentences.append(text)

    def export_data(self):
        return {"version": 1, "custom_words": self.custom_words[:], "snippets": self.snippets.copy(), "learned": {}, "transitions": {}, "history": []}

    def import_data(self, data):
        if not isinstance(data, dict) or not isinstance(data.get("custom_words"), list):
            raise ValueError("Invalid dictionary")
        if any(not isinstance(word, str) for word in data["custom_words"]):
            raise ValueError("Invalid word")
        self.custom_words = data["custom_words"][:]
        self.snippets = data["snippets"].copy()

    def save(self):
        self.saved += 1


@pytest.fixture(scope="module")
def qt_app():
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def workspace(qt_app):
    engine = FakeEngine()
    inserted = []
    widget = KeyboardTools(None, engine, inserted.append)
    yield widget, engine, inserted
    widget.docpad.document().setModified(False)
    widget.words_editor.document().setModified(False)
    widget.snippets_editor.document().setModified(False)
    widget.shutdown()
    widget.close()


def test_keyboard_preview_uses_engine_and_emits_global_candidate(workspace):
    view, engine, inserted = workspace
    view.preview_input.setText("bangla")
    assert view.preview_output.toPlainText() == "বাংলা"
    assert view.local_candidates.count() == 2
    view._local_candidate(view.local_candidates.item(1))
    assert view.preview_output.toPlainText() == "বাংলায়"
    view._send(view.preview_output.toPlainText())
    assert inserted == ["বাংলায়"]
    chosen = []
    view.candidate_selected.connect(chosen.append)
    view.update_candidates("bangla", "বাংলা", ["বাংলায়"])
    view.global_candidates.itemActivated.emit(view.global_candidates.item(0))
    assert chosen == [0]
    assert "বাংলা" in view.live_state.text()


def test_layout_enable_and_prediction_signals(workspace):
    view, _, _ = workspace
    layouts, enabled = [], []
    view.layout_changed.connect(layouts.append)
    view.enabled_changed.connect(enabled.append)
    view.layout_choice.setCurrentIndex(view.layout_choice.findData("english"))
    view.keyboard_enabled.setChecked(True)
    view.prediction_input.setText("আমি ভালো")
    assert layouts == ["english"]
    assert enabled == [True]
    assert view.predictions.item(0).text() == "আছি"


def test_word_edits_validate_before_apply_and_allow_deletion(workspace):
    view, engine, _ = workspace
    before = copy.deepcopy(engine.export_data())
    view.words_editor.setPlainText("নতুন")
    view.snippets_editor.setPlainText("missing tab")
    assert view.apply_words() is None
    assert engine.export_data() == before
    assert "needs a tab" in view.status.text()
    view.snippets_editor.setPlainText("mail\tHello")
    assert view.apply_words() is True
    assert engine.custom_words == ["নতুন"]
    assert engine.snippets == {"mail": "Hello"}
    assert engine.saved == 1


def test_dictionary_export_and_invalid_import_preserve_data(workspace, tmp_path):
    view, engine, _ = workspace
    path = tmp_path / "dictionary.json"
    view.export_dictionary(path)
    assert json.loads(path.read_text(encoding="utf-8"))["custom_words"] == ["বাংলা"]
    path.write_text('{"custom_words": [42], "snippets": {}}', encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid word"):
        view.import_dictionary(path)
    assert engine.custom_words == ["বাংলা"]


def test_docpad_unicode_save_open_find_replace_and_undo(workspace, tmp_path):
    view, _, _ = workspace
    path = tmp_path / "বাংলা.txt"
    view.docpad.setPlainText("বাংলা ভাষা বাংলা")
    view.save_document(path)
    assert path.read_text(encoding="utf-8") == "বাংলা ভাষা বাংলা"
    assert not view.docpad.document().isModified()
    view.docpad.clear()
    view.open_document(path)
    view.find_text.setText("বাংলা")
    view.replace_text.setText("বাংলাদেশ")
    view.replace_all()
    assert view.docpad.toPlainText() == "বাংলাদেশ ভাষা বাংলাদেশ"
    assert view.docpad.document().isModified()
    view.docpad.undo()
    assert view.docpad.toPlainText() == "বাংলা ভাষা বাংলা"
    view.find_next()
    assert view.docpad.textCursor().selectedText() == "বাংলা"


def test_failed_document_write_keeps_original(workspace, tmp_path, monkeypatch):
    view, _, _ = workspace
    path = tmp_path / "document.txt"
    path.write_text("original", encoding="utf-8")
    view.docpad.setPlainText("replacement")

    def failed_replace(*args):
        raise PermissionError("Destination unavailable")

    monkeypatch.setattr(tools_ui.os, "replace", failed_replace)
    with pytest.raises(PermissionError):
        view.save_document(path)
    assert path.read_text(encoding="utf-8") == "original"
    assert len(list(tmp_path.iterdir())) == 1


def test_pdf_export_produces_real_pdf(workspace, tmp_path):
    view, _, _ = workspace
    view.docpad.setPlainText("বাংলা লেখা\nJoyKeyboard document")
    path = tmp_path / "document.pdf"
    view.export_pdf(path)
    assert path.read_bytes().startswith(b"%PDF-")
    assert path.stat().st_size > 1000


def test_screen_keys_compose_language_shift_and_backspace(workspace):
    view, _, inserted = workspace
    view._screen_character(0)
    assert view.screen_text.toPlainText() == "অ"
    view._screen_insert(None)
    assert not view.screen_text.toPlainText()
    view.screen_language.setCurrentIndex(1)
    view.screen_shift.setChecked(True)
    view._screen_character(12)
    view._screen_insert(" ")
    assert view.screen_text.toPlainText() == "Q "
    view._send(view.screen_text.toPlainText())
    assert inserted == ["Q "]
    assert len(view.current_screen_keys) <= len(view.screen_buttons)


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def read(self, _):
        return self.data


def test_gemini_request_uses_header_and_parses_text_without_persisting_key(monkeypatch):
    requests = []

    def response(request, timeout):
        requests.append((request, timeout))
        return FakeResponse(json.dumps({"candidates": [{"content": {"parts": [{"text": "hidden", "thought": True}, {"text": "বাংলা"}]}}]}).encode())

    monkeypatch.setattr(tools_ui.urllib.request, "urlopen", response)
    assert gemini_text("session-secret", "gemini-2.5-flash", "Translate", "Bengali") == "বাংলা"
    request, timeout = requests[0]
    assert request.get_header("X-goog-api-key") == "session-secret"
    assert "session-secret" not in request.full_url
    assert timeout == 20
    assert json.loads(request.data)["contents"][0]["parts"][0]["text"] == "Translate\n\nBengali"


@pytest.mark.parametrize("key, model, text", [("", "gemini-2.5-flash", "hello"), ("key", "https://evil.example", "hello"), ("key", "gemini-2.5-flash", ""), ("key", "gemini-2.5-flash", "x" * 50001)], ids=["missing-key", "invalid-model", "missing-text", "oversized-text"])
def test_gemini_validates_before_network(key, model, text, monkeypatch):
    monkeypatch.setattr(tools_ui.urllib.request, "urlopen", lambda *_args, **_kwargs: pytest.fail("Unexpected network"))
    with pytest.raises(ValueError):
        gemini_text(key, model, "Rewrite", text)


def test_gemini_http_failure_does_not_expose_key(monkeypatch):
    def failed(*args, **kwargs):
        raise urllib.error.HTTPError("https://example.test", 403, "secret raw payload", {}, None)
    monkeypatch.setattr(tools_ui.urllib.request, "urlopen", failed)
    with pytest.raises(ValueError, match="HTTP 403") as error:
        gemini_text("session-secret", "gemini-2.5-flash", "Rewrite", "Hello")
    assert "secret" not in str(error.value)


def test_gemini_invalid_header_key_fails_without_exposing_secret(monkeypatch):
    monkeypatch.setattr(tools_ui.urllib.request, "urlopen", lambda *_args, **_kwargs: pytest.fail("Unexpected network"))
    with pytest.raises(ValueError, match="invalid characters") as error:
        gemini_text("secret\nheader", "gemini-2.5-flash", "Rewrite", "Hello")
    assert "secret" not in str(error.value)


def test_assistant_thread_delivers_and_clears_key_on_shutdown(workspace, qt_app, monkeypatch):
    view, _, _ = workspace
    monkeypatch.setattr(tools_ui, "gemini_text", lambda *_: "Rewritten text")
    view.ai_key.setText("session-secret")
    view.ai_input.setPlainText("Hello")
    view.start_assistant()
    deadline = time.monotonic() + 3
    while view.ai_job is not None and time.monotonic() < deadline:
        qt_app.processEvents()
        time.sleep(0.01)
    assert view.ai_output.toPlainText() == "Rewritten text"
    assert view.ai_job is None
    assert view.ai_generate.isEnabled()
    view.shutdown()
    assert not view.ai_key.text()


def test_cancelled_queued_result_never_replaces_output(workspace):
    view, _, _ = workspace
    job = tools_ui.AssistantJob("key", "gemini-2.5-flash", "Rewrite", "Hello")
    view.ai_job = job
    view.cancel_assistant()
    view._assistant_result("stale result")
    assert not view.ai_output.toPlainText()
    view.ai_job = None


def test_all_tabs_have_accessible_editors(workspace):
    view, _, _ = workspace
    assert view.panels.count() == 6
    for editor in view.findChildren(tools_ui.QPlainTextEdit) + view.findChildren(tools_ui.QLineEdit):
        if editor.parent() is view.ai_model:
            continue
        assert editor.accessibleName()
    assert view.screen_buttons[0].focusPolicy() == Qt.FocusPolicy.StrongFocus


def test_screen_keys_preserve_bengali_letters_with_nukta(workspace):
    view, _, _ = workspace
    for letter in ("ড়", "ঢ়", "য়"):
        view._screen_character(view.current_screen_keys.index(letter))
    assert view.screen_text.toPlainText() == "ড়ঢ়য়"


def test_words_rollback_after_save_failure(workspace, monkeypatch):
    view, engine, _ = workspace
    before = copy.deepcopy(engine.export_data())
    view.words_editor.setPlainText("নতুন")
    view.snippets_editor.setPlainText("mail\tHello")
    monkeypatch.setattr(engine, "save", lambda: (_ for _ in ()).throw(OSError("disk full")))
    assert view.apply_words() is None
    assert engine.export_data() == before
    assert "disk full" in view.status.text()


def test_dictionary_import_rolls_back_after_save_failure(workspace, tmp_path, monkeypatch):
    view, engine, _ = workspace
    before = copy.deepcopy(engine.export_data())
    path = tmp_path / "import.json"
    path.write_text(json.dumps({"custom_words": ["নতুন"], "snippets": {}}), encoding="utf-8")
    monkeypatch.setattr(engine, "save", lambda: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError, match="disk full"):
        view.import_dictionary(path)
    assert engine.export_data() == before


def test_unapplied_words_cannot_be_discarded_without_confirmation(workspace, monkeypatch):
    view, engine, _ = workspace
    view.words_editor.insertPlainText("নতুন\n")
    monkeypatch.setattr(tools_ui.QMessageBox, "question", lambda *_: tools_ui.QMessageBox.StandardButton.Cancel)
    view._choose_reload_words()
    assert "নতুন" in view.words_editor.toPlainText()
    assert not view.confirm_document_close()
    assert engine.custom_words == ["বাংলা"]
    monkeypatch.setattr(tools_ui.QMessageBox, "question", lambda *_: tools_ui.QMessageBox.StandardButton.Save)
    assert view.confirm_document_close()
    assert "নতুন" in engine.custom_words
    assert not view.words_editor.document().isModified()


def test_docpad_close_cancellation_and_save_failure_keep_document(workspace, monkeypatch):
    view, _, _ = workspace
    view.docpad.insertPlainText("unsaved বাংলা")
    monkeypatch.setattr(tools_ui.QMessageBox, "question", lambda *_: tools_ui.QMessageBox.StandardButton.Cancel)
    view.new_document()
    assert view.docpad.toPlainText() == "unsaved বাংলা"
    assert not view.confirm_document_close()
    monkeypatch.setattr(tools_ui.QMessageBox, "question", lambda *_: tools_ui.QMessageBox.StandardButton.Save)
    monkeypatch.setattr(view, "_choose_save_document", lambda: False)
    assert not view.confirm_document_close()
    assert view.docpad.document().isModified()


def test_converter_uses_both_real_encoding_directions(workspace):
    view, _, _ = workspace
    view.converter_input.setPlainText("বাংলা")
    view._convert_encoding(tools_ui.to_ansi)
    ansi = view.converter_output.toPlainText()
    assert ansi and ansi != "বাংলা"
    view.converter_input.setPlainText(ansi)
    view._convert_encoding(tools_ui.from_ansi)
    assert view.converter_output.toPlainText() == "বাংলা"


@pytest.mark.parametrize("response", [{"candidates": [None]}, {"candidates": [{"content": None}]},
                                      {"candidates": [{"content": {"parts": 42}}]},
                                      {"candidates": [{"content": {"parts": [{"text": 42}]}}]}])
def test_gemini_malformed_response_is_safe_error(monkeypatch, response):
    monkeypatch.setattr(tools_ui.urllib.request, "urlopen", lambda *_args, **_kwargs: FakeResponse(json.dumps(response).encode()))
    with pytest.raises(ValueError, match="Gemini returned"):
        gemini_text("session-secret", "gemini-2.5-flash", "Rewrite", "Hello")


def test_shutdown_keeps_running_worker_alive_on_timeout(workspace):
    view, _, _ = workspace

    class PendingJob:
        def requestInterruption(self):
            pass

        def wait(self, timeout):
            assert timeout == 25000
            return False

    view.ai_job = PendingJob()
    assert view.shutdown() is False
    assert view.ai_job is not None
    assert "Try Quit" in view.status.text()
    view.ai_job = None


def test_tools_work_with_real_engine_layouts_learning_and_dictionary(qt_app, tmp_path):
    from keyboard_engine import LAYOUTS, KeyboardEngine

    engine = KeyboardEngine(tmp_path / "keyboard.json")
    inserted = []
    view = KeyboardTools(None, engine, inserted.append)
    try:
        view.preview_input.setText("ami banglay gan gai")
        assert view.preview_output.toPlainText() == "আমি বাংলায় গান গাই"
        view._learn_preview()
        assert engine.predict("আমি") == ["বাংলায়"]
        assert engine.learned["আমি"] == 1
        for layout in LAYOUTS:
            view.layout_choice.setCurrentIndex(view.layout_choice.findData(layout))
            view.preview_input.setText("abc")
            assert view.preview_output.toPlainText() == engine.convert("abc", layout)
        view.words_editor.setPlainText("জয়কিবোর্ড")
        view.snippets_editor.setPlainText("office\tDhaka, Bangladesh")
        assert view.apply_words()
        assert engine.suggest("জয়কি")[0] == "জয়কিবোর্ড"
        saved = KeyboardEngine(engine.path)
        assert saved.snippets == {"office": "Dhaka, Bangladesh"}
        assert saved.custom_words == ["জয়কিবোর্ড"]
        export = tmp_path / "backup.json"
        view.export_dictionary(export)
        saved.import_data(json.loads(export.read_text(encoding="utf-8")))
        assert saved.export_data() == engine.export_data()
    finally:
        view.docpad.document().setModified(False)
        view.words_editor.document().setModified(False)
        view.snippets_editor.document().setModified(False)
        view.close()


def test_corrupt_dictionary_is_not_overwritten_by_normal_ui_edits(qt_app, tmp_path):
    from keyboard_engine import KeyboardEngine

    path = tmp_path / "keyboard.json"
    path.write_text("corrupt user data", encoding="utf-8")
    engine = KeyboardEngine(path)
    view = KeyboardTools(None, engine, lambda _: None)
    try:
        view.words_editor.setPlainText("নতুন")
        assert view.apply_words() is None
        view.preview_input.setText("ami")
        view._learn_preview()
        assert engine.load_error
        assert not engine.learned
        assert path.read_text(encoding="utf-8") == "corrupt user data"
    finally:
        view.words_editor.document().setModified(False)
        view.close()
