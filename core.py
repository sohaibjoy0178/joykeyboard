"""Data-only preferences and deterministic speech text processing."""
from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path

DEFAULT_RULES = {
    "question mark": "?", "exclamation mark": "!", "new line": "\n",
    "প্রশ্নবোধক চিহ্ন": "?", "দাড়ি চিহ্ন": "।", "কমা চিহ্ন": ",",
    "নতুন লাইন": "\n",
}
DEFAULT_VOICE_SHORTCUT = "Ctrl+Alt+Space"


def parse_voice_shortcut(value):
    """Canonical display text and Win32 modifier/key codes for one global chord."""
    if not isinstance(value, str) or len(value) > 80:
        raise ValueError("Choose one shortcut, such as Ctrl+Alt+V.")
    parts = value.strip().split("+")
    modifiers = {"ctrl": ("Ctrl", 2), "alt": ("Alt", 1), "shift": ("Shift", 4)}
    mask = 0
    for part in parts[:-1]:
        modifier = modifiers.get(part.strip().lower())
        if modifier is None or mask & modifier[1]:
            raise ValueError("Use Ctrl, Alt or Shift with one letter, digit, function key or Space.")
        mask |= modifier[1]
    key = parts[-1].strip().upper()
    special = {"SPACE": ("Space", 0x20), "PAUSE": ("Pause", 0x13),
               "INSERT": ("Insert", 0x2D), "INS": ("Insert", 0x2D),
               "HOME": ("Home", 0x24), "END": ("End", 0x23),
               "PGUP": ("PgUp", 0x21), "PGDOWN": ("PgDown", 0x22)}
    if len(key) == 1 and key in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
        name, vk = key, ord(key)
    elif re.fullmatch(r"F(?:[1-9]|1[0-9]|2[0-4])", key):
        name, vk = key, 0x70 + int(key[1:]) - 1
    elif key in special:
        name, vk = special[key]
    else:
        raise ValueError("Choose a letter, digit, F1–F11/F13–F24, Space, Pause, Insert, Home, End or Page key.")
    if key == "F12":
        raise ValueError("F12 is reserved for the keyboard toggle. Choose another shortcut.")
    if not mask and not name.startswith("F"):
        raise ValueError("Add Ctrl, Alt or Shift so ordinary typing does not start recording.")
    if not mask and 0x70 <= vk <= 0x77:
        raise ValueError("F1–F8 select word suggestions. Add Ctrl or Alt for a voice shortcut.")
    if mask == 4 and not name.startswith("F"):
        raise ValueError("Use Ctrl or Alt; Shift alone would interrupt ordinary typing.")
    prefix = [title for title, bit in modifiers.values() if mask & bit]
    return "+".join(prefix + [name]), mask, vk


DEFAULTS = {
    "language": "bn-BD", "engine": "google", "model": "base", "device": None,
    "auto_type": True, "bangla_digits": False, "hold_key": False, "auto_pause": True,
    "keyboard_layout": "phonetic", "output_encoding": "unicode", "system_audio": False,
    "bar_position": None, "bar_opacity": 100, "theme": "glass",
    "voice_shortcut": DEFAULT_VOICE_SHORTCUT,
    "rules": DEFAULT_RULES,
}


def data_directory() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share"))
    return root / "JoyKeyboard"


def validate_rules(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or len(value) > 200:
        raise ValueError("Use at most 200 speech replacements.")
    result = {}
    for phrase, replacement in value.items():
        if not isinstance(phrase, str) or not phrase.strip() or len(phrase) > 200:
            raise ValueError("Each spoken phrase must contain 1–200 characters.")
        if not isinstance(replacement, str) or len(replacement) > 1000:
            raise ValueError("Each replacement must contain at most 1,000 characters.")
        result[phrase.strip()] = replacement
    return result


def load_settings(path: Path) -> tuple[dict, str]:
    values = {**DEFAULTS, "rules": dict(DEFAULT_RULES)}
    try:
        if not path.exists():
            return values, ""
        if path.stat().st_size > 1_000_000:
            raise ValueError("Settings file is too large.")
        saved = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(saved, dict):
            raise ValueError("Settings must be a JSON object.")
        for key, allowed in {"language": ("bn-BD", "en-US"),
                             "engine": ("google", "offline"),
                             "theme": ("light", "glass"),
                             "model": ("tiny", "base", "small")}.items():
            if saved.get(key) in allowed:
                values[key] = saved[key]
        if saved.get("theme") == "dark":
            values["theme"] = "glass"
        if saved.get("keyboard_layout") in ("phonetic", "english", "probhat", "inscript"):
            values["keyboard_layout"] = saved["keyboard_layout"]
        if saved.get("output_encoding") in ("unicode", "bijoy"):
            values["output_encoding"] = saved["output_encoding"]
        if "voice_shortcut" in saved:
            try:
                values["voice_shortcut"] = parse_voice_shortcut(saved["voice_shortcut"])[0]
            except ValueError:
                pass
        position = saved.get("bar_position")
        if type(saved.get("bar_opacity")) is int and saved["bar_opacity"] in (70, 80, 90, 100):
            values["bar_opacity"] = saved["bar_opacity"]
        if isinstance(position, list) and len(position) == 2 and all(type(n) is int and -100000 <= n <= 100000 for n in position):
            values["bar_position"] = position
        for key in ("auto_type", "bangla_digits", "hold_key", "system_audio", "auto_pause"):
            if type(saved.get(key)) is bool:
                values[key] = saved[key]
        device = saved.get("device")
        if device is None or (type(device) is int and 0 <= device < 10000):
            values["device"] = device
        if "rules" in saved:
            values["rules"] = validate_rules(saved["rules"])
        return values, ""
    except (OSError, UnicodeError, ValueError) as exc:
        return {**DEFAULTS, "rules": dict(DEFAULT_RULES)}, f"Preferences could not be read: {exc}"


def save_settings(path: Path, values: dict) -> None:
    validate_rules(values["rules"])
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(values, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def process_text(text: str, language: str, rules: dict[str, str], bangla_digits: bool) -> str:
    text = unicodedata.normalize("NFC", text).strip()
    if rules:
        # One pass prevents a replacement from accidentally triggering another rule.
        pattern = re.compile("|".join(re.escape(p) for p in sorted(rules, key=len, reverse=True)), re.IGNORECASE)
        lookup = {key.casefold(): value for key, value in rules.items()}
        text = pattern.sub(lambda match: lookup[match.group().casefold()], text)
    text = re.sub(r"[ \t]+([,।?!;:])", r"\1", text)
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    if bangla_digits and language == "bn-BD":
        text = text.translate(str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯"))
    return text.strip()


def parse_rules(text: str) -> dict[str, str]:
    rules = {}
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        phrase, separator, replacement = line.partition("=>")
        if not separator:
            raise ValueError(f"Line {number}: use spoken phrase => replacement.")
        rules[phrase.strip()] = replacement.strip().replace(r"\n", "\n")
    return validate_rules(rules)


def format_rules(rules: dict[str, str]) -> str:
    return "\n".join(f"{key} => {value.replace(chr(10), r'\n')}" for key, value in rules.items())
