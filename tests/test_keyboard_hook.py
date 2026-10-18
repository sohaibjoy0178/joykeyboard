import os

import pytest

import keyboard_hook as module
from windows import Target


class Engine:
    snippets = {"addr": "Dhaka, Bangladesh"}

    def __init__(self):
        self.learned = []

    def convert(self, text, layout):
        return {"ami": "আমি", "bangla": "বাংলা"}.get(text, text) if layout == "phonetic" else text

    def suggest(self, prefix, limit):
        return [prefix, "বাংলাদেশ"][:limit]

    def learn(self, word):
        self.learned.append(word)

    def commit_sentence(self, text):
        self.learned.append(text)


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setattr(module.user32, "GetKeyState", lambda _: 0)
    target = Target(101, os.getpid() + 100, 102, "Owned field")
    monkeypatch.setattr(module, "foreground_target", lambda: target)
    monkeypatch.setattr(module, "_native_password", lambda _: False)
    monkeypatch.setattr(module, "_caret", lambda _: (102, 0, 0))
    updates, errors, output = [], [], []
    engine = Engine()
    hook = module.KeyboardHook(engine, lambda *args: updates.append(args), errors.append)
    monkeypatch.setattr(hook, "_send", lambda text, key=None, key_down_only=False:
                        output.append((text, key, key_down_only)))
    monkeypatch.setattr(hook, "_replay", lambda key, down: output.append(("replay", key, down)))
    hook.set_enabled(True)
    return hook, engine, target, updates, errors, output


def type_word(hook, word):
    for char in word:
        key = ord(char.upper())
        assert hook._capture(key, True)
        assert hook._capture(key, False)


def test_composition_commits_actual_bengali_with_space_atomically(setup):
    hook, engine, _, updates, errors, output = setup
    type_word(hook, "ami")
    assert updates[-1][:2] == ("ami", "আমি")
    assert output == []
    assert hook._capture(0x20, True)
    assert hook._capture(0x20, False)
    assert output == [("আমি", 0x20, False)]
    assert hook.raw == ""
    assert engine.learned == ["আমি"]
    assert not errors


def test_repeated_delimiters_are_not_lost(setup):
    hook, _, target, _, _, output = setup
    type_word(hook, "ami")
    hook._consume(target, 0x20, "")
    hook._consume(target, 0x20, "")
    assert output == [("আমি", 0x20, False), ("", 0x20, False)]


def test_own_output_and_external_injected_toggle_are_never_converted(setup):
    hook, _, _, _, _, output = setup
    assert not hook._capture(0x41, True, 0x10, module.INPUT_TAG)
    assert not hook._capture(0x7B, True, 0x10)
    assert hook.enabled and not hook.raw and not output


def test_external_remapped_keys_compose_without_reprocessing_own_output(setup):
    hook, _, _, _, _, output = setup
    for key in (0x41, 0x4D, 0x49, 0x20):
        assert hook._capture(key, True, 0x10)
        assert hook._capture(key, False, 0x90)
    assert output == [("আমি", 0x20, False)]
    assert not hook._capture(0x20, True, 0x10, module.INPUT_TAG)
    assert hook.raw == "" and len(output) == 1


def test_slow_suggestions_do_not_block_commit_or_restore_stale_candidates(setup, monkeypatch):
    import threading
    hook, engine, target, _, _, output = setup
    started, release = threading.Event(), threading.Event()
    def slow(prefix, limit):
        started.set()
        assert release.wait(3)
        return [prefix]
    monkeypatch.setattr(engine, "suggest", slow)
    monkeypatch.setattr(module.user32, "PostThreadMessageW", lambda *args: True)
    hook._thread_id = 123
    try:
        hook.raw = "ami"
        hook._target = target
        hook._caret_at_start = module._caret(target)
        hook._refresh()
        assert started.wait(1)
        hook._consume(target, 0x20, "")
        assert output == [("আমি", 0x20, False)] and not release.is_set()
        release.set()
        hook._suggest_thread.join(2)
    finally:
        release.set()
        hook.stop()
    hook._drain()
    assert not hook.raw and not hook.suggestions


def test_shortcut_modifier_commits_and_replays_balanced_chord(setup):
    hook, _, _, _, _, output = setup
    type_word(hook, "ami")
    assert hook._capture(0xA2, True)
    assert hook._capture(0x43, True)
    assert hook._capture(0x43, False)
    assert hook._capture(0xA2, False)
    assert output == [("আমি", 0xA2, True), ("replay", 0x43, True),
                      ("replay", 0x43, False), ("replay", 0xA2, False)]


def test_queued_modifier_release_cannot_overtake_composition_commit(setup, monkeypatch):
    hook, _, _, _, _, output = setup
    type_word(hook, "ami")
    hook._thread_id = 123
    monkeypatch.setattr(module.user32, "PostThreadMessageW", lambda *_: True)
    assert hook._capture(0xA2, True)
    assert hook._capture(0x43, True)
    assert hook._capture(0xA2, False)
    assert hook._capture(0x43, False)
    assert output == []
    hook._drain()
    assert output == [("আমি", 0xA2, True), ("replay", 0x43, True),
                      ("replay", 0xA2, False), ("replay", 0x43, False)]
    assert not hook._chord and not hook._replay_keys


def test_composing_key_released_during_chord_clears_suppression(setup):
    hook, _, _, _, _, _ = setup
    assert hook._capture(0x41, True)
    assert hook._capture(0xA2, True)
    assert hook._capture(0x41, False)
    assert hook._capture(0xA2, False)
    hook.set_enabled(False)
    assert not hook._capture(0x41, True)
    assert not hook._capture(0x41, False)


def test_candidate_keys_and_escape_literal(setup):
    hook, _, _, _, _, output = setup
    type_word(hook, "bangla")
    assert hook._capture(0x71, True)
    assert hook._capture(0x71, False)
    assert output == [("বাংলাদেশ", None, False)]
    type_word(hook, "ami")
    assert hook._capture(0x1B, True)
    assert output[-1] == ("ami", None, False)


def test_backspace_edits_only_pending_roman_without_external_deletion(setup):
    hook, _, _, updates, _, output = setup
    type_word(hook, "ami")
    hook._capture(0x08, True)
    hook._capture(0x08, False)
    assert updates[-1][0] == "am"
    assert not output


def test_snippets_and_english_passthrough_words(setup):
    hook, _, _, _, _, output = setup
    hook.set_layout("english")
    type_word(hook, "addr")
    hook._capture(0x20, True)
    assert output == [("Dhaka, Bangladesh", 0x20, False)]


def test_bijoy_output_keeps_composition_and_learning_unicode(setup):
    from keyboard_engine import to_ansi

    hook, engine, _, updates, _, output = setup
    hook.set_output_encoding("bijoy")
    type_word(hook, "ami")
    assert updates[-1][1] == "আমি"
    hook._capture(0x20, True)
    assert output == [(to_ansi("আমি"), 0x20, False)]
    assert engine.learned == ["আমি"]


def test_output_encoding_change_commits_existing_word_in_old_encoding(setup):
    hook, _, _, _, _, output = setup
    type_word(hook, "ami")
    hook.set_output_encoding("bijoy")
    assert output == [("আমি", None, False)]
    with pytest.raises(ValueError, match="unicode or bijoy"):
        hook.set_output_encoding("unknown")


def test_changed_focus_discards_pending_without_injection(setup, monkeypatch):
    hook, _, _, _, errors, output = setup
    type_word(hook, "ami")
    monkeypatch.setattr(module, "foreground_target", lambda: Target(201, 9, 202, "Other"))
    hook._check_context()
    assert not hook.raw and not output
    assert "ami" in errors[-1]


def test_native_caret_move_discards_pending(setup, monkeypatch):
    hook, _, _, _, errors, output = setup
    type_word(hook, "ami")
    monkeypatch.setattr(module, "_caret", lambda _: (102, 10, 0))
    hook._check_context()
    assert not output and not hook.raw
    assert "caret changed" in errors[-1]


def test_own_windows_and_native_password_inputs_are_ignored(setup, monkeypatch):
    hook, _, _, _, _, output = setup
    monkeypatch.setattr(module, "_native_password", lambda _: True)
    assert not hook._capture(0x41, True)
    monkeypatch.setattr(module, "_native_password", lambda _: False)
    monkeypatch.setattr(module, "foreground_target", lambda: Target(1, os.getpid(), 2, "JoyKeyboard"))
    assert not hook._capture(0x42, True)
    assert not output and not hook.raw


def test_send_failure_disables_hook_preserves_recovery_text(setup, monkeypatch):
    hook, _, _, _, errors, _ = setup
    type_word(hook, "ami")

    def blocked(*_):
        raise RuntimeError("Windows blocked typing")

    monkeypatch.setattr(hook, "_send", blocked)
    hook._capture(0x20, True)
    assert not hook.enabled
    assert hook.raw == "ami"
    assert "ami" in errors[-1]


def test_f12_repeat_toggles_once_and_release_is_consumed(setup):
    hook, _, _, _, _, _ = setup
    assert hook._capture(0x7B, True)
    assert not hook.enabled
    assert hook._capture(0x7B, True)
    assert not hook.enabled
    assert hook._capture(0x7B, False)
    hook._capture(0x7B, True)
    assert hook.enabled


def test_shift_function_key_shortcuts_pass_through(setup):
    hook, _, _, _, _, _ = setup
    assert not hook._capture(0xA0, True)
    assert not hook._capture(0x7B, True)
    assert hook.enabled
    assert not hook._capture(0x7B, False)
    assert not hook._capture(0xA0, False)
    type_word(hook, "ami")
    assert not hook._capture(0xA0, True)
    assert not hook._capture(0x70, True)
    assert hook.raw == "ami"


@pytest.mark.skipif(not module.IS_WINDOWS, reason="Win32 SendInput")
def test_sendinput_uses_utf16_and_full_virtual_boundary(monkeypatch):
    output = []
    monkeypatch.setattr(module.user32, "GetAsyncKeyState", lambda _: 0)

    def send(count, events, size):
        output.extend((events[i].value.ki.wVk, events[i].value.ki.wScan,
                       events[i].value.ki.dwFlags) for i in range(count))
        return count

    monkeypatch.setattr(module.user32, "SendInput", send)
    module.KeyboardHook._send("আমি🙂", 0x20)
    assert output[-2:] == [(0x20, 0, 0), (0x20, 0, 2)]
    raw = b"".join(scan.to_bytes(2, "little") for _, scan, flags in output[:-2] if flags == 4)
    assert raw.decode("utf-16-le") == "আমি🙂"
