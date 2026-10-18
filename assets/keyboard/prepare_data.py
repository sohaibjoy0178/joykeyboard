"""Reproduce bundled word data; run with wordfreq==3.1.1 installed."""
import gzip
import importlib.metadata
import json
from pathlib import Path
import re
import shutil
import unicodedata
import urllib.request

import msgpack

ROOT = Path(__file__).resolve().parent


def main():
    dist = importlib.metadata.distribution("wordfreq")
    shutil.copyfile(dist.locate_file("wordfreq-3.1.1.dist-info/LICENSE.txt"), ROOT / "WORDFREQ-LICENSE.txt")
    (ROOT / "WORDFREQ-METADATA.txt").write_text(dist.read_text("METADATA"), encoding="utf-8")
    attribution = {
        "license": "CC-BY-SA-4.0",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "source": "https://github.com/rspeer/wordfreq",
        "source_version": "3.1.1",
        "author": "Robyn Speer and wordfreq contributors",
        "attribution": "See WORDFREQ-METADATA.txt for full attribution: Google Books, Wikipedia, Leeds Internet Corpus, ParaCrawl, OpenSubtitles, SUBTLEX authors Marc Brysbaert et al. SUBTLEX is freely available data.",
        "changes": "Flattened frequency bins in descending frequency order, NFC normalized, non-word tokens filtered, duplicates removed. Rank is word position. This JSON adaptation is CC BY SA 4.0.",
    }
    for language in ("bn", "en"):
        source = Path(dist.locate_file(f"wordfreq/data/large_{language}.msgpack.gz"))
        rows = msgpack.unpackb(gzip.decompress(source.read_bytes()), raw=False)
        assert rows[0] == {"format": "cB", "version": 1}
        words, seen = [], set()
        for frequency_bin in rows[1:]:
            for raw in frequency_bin:
                word = unicodedata.normalize("NFC", raw)
                if language == "bn":
                    valid = all("\u0980" <= c <= "\u09ff" or c in "\u200c\u200d" for c in word) and any(c.isalpha() for c in word)
                else:
                    valid = word.isascii() and word.isalpha()
                if valid and 1 <= len(word) <= 64 and word not in seen:
                    words.append(word)
                    seen.add(word)
        data = {**attribution, "language": language, "words": words}
        (ROOT / f"{language}-words.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(language, len(words))

    layouts = {}
    for name in ("probhat", "inscript"):
        source = (ROOT / f"bn-{name}.mim").read_text(encoding="utf-8")
        pairs = re.findall(r'^\s*\("((?:\\.|[^"\\])*)"\s+(?:\?((?:\\.|.))|"((?:\\.|[^"\\])*)")\)', source, re.MULTILINE)
        mapping = {}
        for key, char, string in pairs:
            key = json.loads('"' + key + '"')
            value = json.loads('"' + (char or string) + '"') if (char or string) != "\\" else "\\"
            mapping[key] = value
        assert mapping["k"] == "ক" and len(mapping) >= 90
        layouts[name] = mapping
        print(name, len(mapping))
    (ROOT / "layouts.json").write_text(json.dumps({"license": "LGPL-2.1-or-later", "source": "m17n-db MIM/bn-probhat.mim and MIM/bn-inscript.mim; original sources and COPYING included", "changes": "Extracted printable ASCII key maps; AltGr and keypad mapping omitted.", "layouts": layouts}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
