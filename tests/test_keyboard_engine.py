import json
import unicodedata

import pytest

import keyboard_engine
from keyboard_engine import KeyboardEngine, from_ansi, to_ansi


@pytest.fixture
def engine(tmp_path):
    return KeyboardEngine(tmp_path / "keyboard.json")


def test_phonetic_english_and_verified_layouts(engine):
    assert engine.convert("ami banglay gan gai.") == unicodedata.normalize("NFC", "আমি বাংলায় গান গাই।")
    assert engine.convert("Hello 123!", "english") == "Hello 123!"
    assert engine.convert("k/S", "probhat") == "ক্ষ"
    assert engine.convert("k", "inscript") == "ক"
    assert engine.convert("kf", "inscript") == "কি"
    with pytest.raises(ValueError):
        engine.convert("x", "unknown")


def test_voice_learning_does_not_load_large_dictionaries(tmp_path, monkeypatch):
    def forbidden():
        raise AssertionError("Idle startup and learning must not load dictionaries")
    monkeypatch.setattr(keyboard_engine, "_dictionaries", forbidden)
    local = KeyboardEngine(tmp_path / "fresh.json")
    local.commit_sentence("আমি ভালো আছি")
    assert local.predict("আমি ভালো") == ["আছি"]
    local.save()


@pytest.mark.parametrize("text", [
    "আমি বাংলা লিখি।", "কর্ম ধর্ম রক্ত শক্তি", "র্ক র্কি ত্র ক্ষ ক্ষ্ম শ্রদ্ধা",
    "কি কী কু কূ কে কৈ কো কৌ", "  বাংলা\n১২৩  ", "কাঁ চাঁদ দুর্গা সূর্য",
    "বাংলাদেশ স্বাধীন রাষ্ট্র", "শিক্ষার্থী কর্মী প্রশ্ন উত্তর", "",
])
def test_bijoy_roundtrip_common_bengali(text):
    assert from_ansi(to_ansi(text)) == unicodedata.normalize("NFC", text)


def test_known_bijoy_encoding_and_whitespace():
    assert to_ansi("আমি") == "Avwg"
    assert from_ansi("Avwg evsjv wjwL|") == "আমি বাংলা লিখি।"
    assert to_ansi("কর্ম") == "Kg©"
    assert from_ansi("Kg©") == "কর্ম"
    assert to_ansi(" \n\t") == " \n\t"


def test_dictionary_is_full_ranked_and_personal_words_win(engine):
    assert len(engine._words) > 400_000
    assert "বাংলাদেশ" in engine.suggest("বাংল")
    assert "hello" in engine.suggest("hello")
    engine.custom_words.append("বাংলাপ্রিয়")
    assert engine.suggest("বাংল")[0] == "বাংলাপ্রিয়"
    engine.learn("বাংলাভাষী")
    assert engine.suggest("বাংল")[0] == "বাংলাভাষী"
    assert len(engine.suggest("a", 3)) == 3
    assert engine.suggest("") == []
    assert engine.suggest("বাংল", 0) == []


def test_spelling_correction_and_snippets(engine):
    assert "hello" in engine.suggest("hellp")
    engine.snippets["addr"] = "Dhaka, Bangladesh"
    assert engine.suggest("addr")[0] == "Dhaka, Bangladesh"


def test_next_word_history_and_persistence(engine):
    engine.commit_sentence("আমি ভালো আছি")
    engine.commit_sentence("আমি ভালো আছি")
    assert engine.predict("আমি ভালো") == ["আছি"]
    assert engine.history == ["আমি ভালো আছি"]
    engine.snippets["addr"] = "Dhaka\nBangladesh"
    engine.custom_words.append("পরীক্ষা")
    engine.save()
    restored = KeyboardEngine(engine.path)
    assert restored.export_data() == engine.export_data()
    exported = engine.export_data()
    exported["snippets"]["addr"] = "changed"
    assert engine.snippets["addr"] != "changed"


@pytest.mark.parametrize("bad", [
    [], {"version": 2}, {"custom_words": ["two words"]}, {"custom_words": [1]},
    {"snippets": {"x": 3}}, {"snippets": {"x": "a\x00b"}},
    {"learned": {"hello": -1}}, {"learned": {"hello": True}},
    {"transitions": {"hello": {"world": -1}}}, {"history": [None]},
])
def test_bad_import_changes_no_data_or_disk(engine, bad):
    engine.custom_words = ["বাংলা"]
    engine.save()
    before = engine.export_data()
    disk = engine.path.read_bytes()
    with pytest.raises(ValueError):
        engine.import_data(bad)
    assert engine.export_data() == before
    assert engine.path.read_bytes() == disk


def test_corrupt_saved_data_is_never_silently_overwritten(tmp_path):
    path = tmp_path / "keyboard.json"
    path.write_text('{"custom_words": [42]}', encoding="utf-8")
    original = path.read_bytes()
    engine = KeyboardEngine(path)
    assert engine.load_error
    engine.learn("hello")
    with pytest.raises(ValueError):
        engine.save()
    assert path.read_bytes() == original
    engine.import_data({"custom_words": ["restored"]})
    engine.save()
    assert json.loads(path.read_text(encoding="utf-8"))["custom_words"] == ["restored"]


def test_failed_atomic_replace_keeps_original(engine, monkeypatch):
    engine.save()
    original = engine.path.read_bytes()
    engine.learn("new")
    def fail(*args):
        raise OSError("disk blocked")
    monkeypatch.setattr(keyboard_engine.os, "replace", fail)
    with pytest.raises(OSError):
        engine.save()
    assert engine.path.read_bytes() == original
    assert list(engine.path.parent.glob(".keyboard-*.tmp")) == []


def test_mutable_values_are_validated_on_save(engine):
    engine.snippets["bad trigger"] = "value"
    with pytest.raises(ValueError):
        engine.save()
    assert not engine.path.exists()
