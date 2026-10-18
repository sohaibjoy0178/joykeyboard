"""Local Bengali composition, licensed dictionaries and validated personal word data."""
from __future__ import annotations

import bisect
import copy
import heapq
import json
import os
import re
import tempfile
import threading
import unicodedata
from functools import lru_cache
from pathlib import Path

import avro
from avro.core.config import BIJOY_MAP

from core import data_directory

ASSETS = Path(__file__).resolve().parent / "assets" / "keyboard"
LAYOUTS = {"phonetic": "Bangla phonetic", "english": "English", "probhat": "Probhat", "inscript": "Bengali InScript"}
_C = r"[ক-হড়ঢ়য়ৎ]"
_CORE = _C + r"[়]?(?:্[‌‍]?" + _C + r"[়]?)*"
_SYLLABLE = re.compile(_CORE + r"[ািীুূৃেৈোৌৗ]?[ঁংঃ]*")
_LEGACY_SYLLABLE = re.compile(r"([িেৈ]?)(" + _CORE + r")(©?)([াীুূৃৗ]?)([ঁংঃ]*)")
_FORWARD = re.compile("|".join(re.escape(k) for k in sorted(BIJOY_MAP, key=len, reverse=True)))
_REVERSE_MAP = {v: k for k, v in BIJOY_MAP.items() if k != "র্"}
_REVERSE_MAP.update({"†": "ে", "ˆ": "ৈ", "z": "ু", "ƒ": "ূ", "„": "ৃ", "ÿ": "ক্ষ", "¹": "জ্ঞ"})
_REVERSE = re.compile("|".join(re.escape(k) for k in sorted(_REVERSE_MAP, key=len, reverse=True)))
_WORDS = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?|[\u0980-\u09ff\u200c\u200d]+")


def _normalize(text):
    if not isinstance(text, str):
        raise ValueError("Text must be a string.")
    return unicodedata.normalize("NFC", text)


def to_ansi(text: str) -> str:
    """Convert Unicode Bengali to Bijoy glyph order, preserving whitespace."""
    text = _normalize(text)
    def reorder(match):
        syllable = match.group()
        reph = syllable.startswith("র্") and len(syllable) > 2 and syllable[2] not in "‌‍"
        if reph:
            syllable = syllable[2:]
        pre = ""
        for vowel in "িেৈোৌ":
            if vowel in syllable:
                before, after = syllable.split(vowel, 1)
                pre = {"ো": "ে", "ৌ": "ে"}.get(vowel, vowel)
                syllable = before + ("র্" if reph else "") + {"ো": "া", "ৌ": "ৗ"}.get(vowel, "") + after
                break
        else:
            if reph:
                consonants = re.match(_CORE, syllable).group()
                syllable = consonants + "র্" + syllable[len(consonants):]
        return pre + syllable
    ordered = _SYLLABLE.sub(reorder, text)
    return _FORWARD.sub(lambda m: BIJOY_MAP[m.group()], ordered)


def from_ansi(text: str) -> str:
    """Decode legacy Bijoy text; input must already use that encoding."""
    text = _REVERSE.sub(lambda m: _REVERSE_MAP[m.group()], _normalize(text))
    def reorder(match):
        pre, core, reph, post, marks = match.groups()
        vowel = {"ো": "ো", "ৌ": "ৌ"}.get(pre + post, pre + post)
        return ("র্" if reph else "") + core + vowel + marks
    return _normalize(_LEGACY_SYLLABLE.sub(reorder, text).replace("অা", "আ"))


@lru_cache(maxsize=1)
def _dictionaries():
    words, ranks = [], {}
    for lang in ("bn", "en"):
        data = json.loads((ASSETS / f"{lang}-words.json").read_text(encoding="utf-8"))
        for rank, word in enumerate(data["words"]):
            ranks[word] = rank
            words.append(word)
    return sorted(set(words)), ranks


@lru_cache(maxsize=1)
def _layouts():
    return json.loads((ASSETS / "layouts.json").read_text(encoding="utf-8"))["layouts"]


def _word(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 128 or any(c.isspace() or unicodedata.category(c) == "Cc" for c in value):
        raise ValueError("Words and snippet triggers must contain 1–128 non-space characters.")
    return _normalize(value)


def _validate(data):
    if not isinstance(data, dict) or data.get("version", 1) != 1:
        raise ValueError("Unsupported keyboard dictionary format.")
    result = {"version": 1, "custom_words": [], "snippets": {}, "learned": {}, "transitions": {}, "history": []}
    for name in ("custom_words", "history"):
        values = data.get(name, [])
        if not isinstance(values, list) or len(values) > (20000 if name == "custom_words" else 200):
            raise ValueError(f"Invalid or oversized {name} list.")
        if name == "custom_words":
            result[name] = list(dict.fromkeys(_word(v) for v in values))
        else:
            if any(not isinstance(v, str) or len(v) > 10000 for v in values):
                raise ValueError("History entries must be text up to 10,000 characters.")
            result[name] = [_normalize(v) for v in values]
    snippets = data.get("snippets", {})
    if not isinstance(snippets, dict) or len(snippets) > 2000:
        raise ValueError("Use at most 2,000 snippets.")
    for key, value in snippets.items():
        if not isinstance(value, str) or not value or len(value) > 10000 or "\x00" in value:
            raise ValueError("Each snippet needs 1–10,000 characters without null bytes.")
        normalized = _word(key)
        if normalized in result["snippets"]:
            raise ValueError("Duplicate normalized snippet trigger.")
        result["snippets"][normalized] = _normalize(value)
    for name, maximum in (("learned", 20000), ("transitions", 10000)):
        values = data.get(name, {})
        if not isinstance(values, dict) or len(values) > maximum:
            raise ValueError(f"Invalid or oversized {name} map.")
        for key, value in values.items():
            key = _word(key)
            if name == "transitions":
                if not isinstance(value, dict) or len(value) > 100:
                    raise ValueError("Invalid next-word counts.")
                entry = {}
                for following, count in value.items():
                    if type(count) is not int or not 1 <= count <= 1_000_000_000:
                        raise ValueError("Word counts must be positive integers.")
                    entry[_word(following)] = count
                result[name][key] = entry
            else:
                if type(value) is not int or not 1 <= value <= 1_000_000_000:
                    raise ValueError("Word counts must be positive integers.")
                result[name][key] = value
    return result


class KeyboardEngine:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else data_directory() / "keyboard.json"
        self._lock = threading.RLock()
        self.load_error = ""
        self._set_data(_validate({}))
        if self.path.exists():
            try:
                if self.path.stat().st_size > 10 * 1024 * 1024:
                    raise ValueError("Keyboard data exceeds 10 MiB.")
                self._set_data(_validate(json.loads(self.path.read_text(encoding="utf-8-sig"))))
            except (OSError, ValueError, UnicodeError) as exc:
                self.load_error = f"Keyboard data could not be read; original preserved: {exc}"

    @property
    def _words(self):
        return _dictionaries()[0]

    @property
    def _ranks(self):
        return _dictionaries()[1]

    def _set_data(self, data):
        for name in ("custom_words", "snippets", "learned", "transitions", "history"):
            setattr(self, name, data[name])

    def convert(self, text: str, layout: str = "phonetic") -> str:
        text = _normalize(text)
        if layout not in LAYOUTS:
            raise ValueError("Unknown keyboard layout.")
        if layout == "english":
            return text
        if layout == "phonetic":
            return _normalize(avro.parse(text))
        mapping = _layouts()[layout]
        return _normalize("".join(mapping.get(char, char) for char in text))

    def suggest(self, prefix: str, limit: int = 8) -> list[str]:
        prefix = _normalize(prefix).strip()
        limit = max(0, min(int(limit), 50))
        if not prefix or not limit:
            return []
        with self._lock:
            candidates = set(w for w in self.custom_words + list(self.learned) if w.startswith(prefix))
            start = bisect.bisect_left(self._words, prefix)
            stop = bisect.bisect_left(self._words, prefix + "\U0010ffff")
            candidates.update(heapq.nsmallest(limit, self._words[start:stop], key=lambda w: self._ranks[w]))
            ranked = sorted(candidates, key=lambda w: (-self.learned.get(w, 0), w not in self.custom_words, self._ranks.get(w, 10**9), w))
            # shortcut: bounded spelling correction; use a dedicated morphology model for exhaustive Bengali corrections.
            if len(ranked) < limit and len(prefix) >= 3:
                from difflib import get_close_matches
                shortlist = self._words[bisect.bisect_left(self._words, prefix[0]):bisect.bisect_left(self._words, prefix[0] + "\U0010ffff")]
                ranked += [w for w in get_close_matches(prefix, heapq.nsmallest(3000, shortlist, key=lambda w: self._ranks[w]), n=limit, cutoff=.75) if w not in ranked]
            if prefix in self.snippets:
                ranked.insert(0, self.snippets[prefix])
            return list(dict.fromkeys(ranked))[:limit]

    def learn(self, word: str) -> None:
        word = _word(word)
        with self._lock:
            if word not in self.learned and len(self.learned) >= 20000:
                del self.learned[min(self.learned, key=self.learned.get)]
            self.learned[word] = min(self.learned.get(word, 0) + 1, 1_000_000_000)

    def predict(self, previous: str, limit: int = 5) -> list[str]:
        words = _WORDS.findall(_normalize(previous))
        if not words:
            return []
        with self._lock:
            following = self.transitions.get(words[-1], {})
            return sorted(following, key=lambda w: (-following[w], w))[:max(0, min(int(limit), 50))]

    def commit_sentence(self, text: str) -> None:
        text = _normalize(text).strip()
        if not text:
            return
        if len(text) > 10000:
            raise ValueError("Use at most 10,000 characters per learned sentence.")
        with self._lock:
            words = [w for w in _WORDS.findall(text) if len(w) <= 128]
            for word in words:
                self.learn(word)
            for before, after in zip(words, words[1:]):
                if before not in self.transitions and len(self.transitions) >= 10000:
                    del self.transitions[next(iter(self.transitions))]
                counts = self.transitions.setdefault(before, {})
                if after not in counts and len(counts) >= 100:
                    del counts[min(counts, key=counts.get)]
                counts[after] = min(counts.get(after, 0) + 1, 1_000_000_000)
            self.history = ([text] + [s for s in self.history if s != text])[:200]

    def export_data(self) -> dict:
        with self._lock:
            return copy.deepcopy({"version": 1, **{name: getattr(self, name) for name in ("custom_words", "snippets", "learned", "transitions", "history")}})

    def import_data(self, data: dict) -> None:
        validated = _validate(data)
        with self._lock:
            self._set_data(validated)
            self.load_error = ""

    def save(self) -> None:
        with self._lock:
            if self.load_error:
                raise ValueError(self.load_error + " Export recovered data or explicitly import a valid backup before replacing it.")
            validated = _validate(self.export_data())
            self.path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(prefix=".keyboard-", suffix=".tmp", dir=self.path.parent)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                    json.dump(validated, stream, ensure_ascii=False, indent=2)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
