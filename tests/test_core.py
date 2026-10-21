from core import (
    DEFAULT_RULES,
    format_rules,
    load_settings,
    parse_rules,
    process_text,
    save_settings,
)


def test_mapping_is_single_pass_and_longest_first():
    assert process_text("HELLO WORLD hello", "en-US", {"hello world": "hello", "hello": "hi"}, False) == "hello hi"


def test_auto_updates_default_on_and_only_boolean_preferences_are_loaded(tmp_path):
    import json
    path = tmp_path / "settings.json"
    for value, expected in (({}, True), ({"auto_updates": False}, False), ({"auto_updates": "false"}, True)):
        path.write_text(json.dumps(value), encoding="utf-8")
        settings, _ = load_settings(path)
        assert settings["auto_updates"] is expected
        save_settings(path, settings)
        assert load_settings(path)[0]["auto_updates"] is expected


def test_bengali_punctuation_digits_and_newline():
    assert process_text("আজ 12 কমা চিহ্ন নতুন লাইন কাল", "bn-BD", DEFAULT_RULES, True) == "আজ ১২,\nকাল"


def test_rules_roundtrip():
    assert parse_rules(format_rules(DEFAULT_RULES)) == DEFAULT_RULES


def test_corrupt_preferences_recover_without_overwriting(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("broken", encoding="utf-8")
    settings, warning = load_settings(path)
    assert warning and settings["language"] == "bn-BD"
    assert path.read_text() == "broken"


def test_settings_atomic_roundtrip(tmp_path):
    path = tmp_path / "settings.json"
    settings, _ = load_settings(path)
    settings["language"] = "en-US"
    save_settings(path, settings)
    assert load_settings(path)[0] == settings
    assert not path.with_suffix(".tmp").exists()


def test_experimental_sherpa_engine_roundtrips_without_changing_default(tmp_path):
    path = tmp_path / "settings.json"
    settings, _ = load_settings(path)
    assert settings["engine"] == "google"
    settings["engine"] = "sherpa"
    save_settings(path, settings)
    assert load_settings(path)[0]["engine"] == "sherpa"


def test_auto_pause_defaults_on_for_old_settings_and_accepts_only_bool(tmp_path):
    import json
    path = tmp_path / "settings.json"
    for saved, expected in (({}, True), ({"auto_pause": False}, False), ({"auto_pause": "false"}, True)):
        path.write_text(json.dumps(saved), encoding="utf-8")
        assert load_settings(path)[0]["auto_pause"] is expected


def test_bar_position_validates_and_preserves_negative_monitor_coordinates(tmp_path):
    import json
    path = tmp_path / "settings.json"
    for value, expected in (([-900, 25], [-900, 25]), ([True, 1], None), ([1], None), ([999999, 1], None), ("10,20", None)):
        path.write_text(json.dumps({"bar_position": value}), encoding="utf-8")
        assert load_settings(path)[0]["bar_position"] == expected


def test_opacity_cannot_make_bar_invisible_and_migrates_old_settings(tmp_path):
    import json
    path = tmp_path / "settings.json"
    for value, expected in ((70, 70), (100, 100), (0, 100), (True, 100), ("80", 100), (None, 100)):
        path.write_text(json.dumps({"bar_opacity": value}), encoding="utf-8")
        assert load_settings(path)[0]["bar_opacity"] == expected


def test_theme_migrates_validates_and_roundtrips(tmp_path):
    import json
    path = tmp_path / "settings.json"
    for saved, expected in (({}, "light"), ({"theme": "dark"}, "dark"), ({"theme": "glass"}, "light"),
                            ({"theme": "light"}, "light"), ({"theme": "auto"}, "light"),
                            ({"theme": ["dark"]}, "light"), ({"theme": None}, "light")):
        path.write_text(json.dumps(saved), encoding="utf-8")
        settings, warning = load_settings(path)
        assert settings["theme"] == expected and not warning
        save_settings(path, settings)
        assert load_settings(path)[0]["theme"] == expected


def test_removed_whisper_preferences_migrate_to_google_without_touching_models(tmp_path):
    import json
    model = tmp_path / "models/small/model.bin"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"retained user download")
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"engine": "offline", "model": "small", "theme": "dark", "voice_shortcut": "Ctrl+Alt+V"}), encoding="utf-8")
    settings, warning = load_settings(path)
    assert not warning and settings["engine"] == "google" and "model" not in settings
    assert settings["theme"] == "dark" and settings["voice_shortcut"] == "Ctrl+Alt+V"
    save_settings(path, settings)
    assert model.read_bytes() == b"retained user download"
