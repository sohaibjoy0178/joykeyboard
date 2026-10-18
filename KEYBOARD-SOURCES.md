# Keyboard engine sources and redistribution

JoyKeyboard implements its own composition orchestration, personal word store, suggestion ranking and bounded encoding reorder. No NMS Kontho program code, dictionaries, icons, layouts or other unknown-license extracted assets are redistributed.

## Phonetic parser and legacy character map

- Dependency: `avro.py==2025.11.3`, by HitBlast and contributors. Source: https://github.com/hitblast/avro.py ; release: https://pypi.org/project/avro.py/2025.11.3/
- License: MIT OR Apache-2.0; JoyKeyboard elects MIT. Copy of MIT text: `assets/keyboard/AVRO-LICENSE-MIT.txt`. The installed package includes its original notices.
- `avro.parse(text)` supplies Bengali phonetic parsing. Its `avro.core.config.BIJOY_MAP` supplies Unicode/Bijoy character mappings.
- JoyKeyboard does **not** call avro.py's `to_bijoy`/`to_unicode`: version 2025.11.3's reorder logic can hang on reph words or index past string boundaries. `keyboard_engine.py` uses bounded regular-expression syllable processing instead. Unknown characters and whitespace pass through. Common vowel, reph and conjunct roundtrips are covered by tests.
- Conversion is for Bengali legacy Bijoy/Sutonny glyph encoding, not a general encoding detector. Latin letters/digits are themselves Bengali glyph codes in legacy input, so converting mixed English/Bengali legacy text can reinterpret English; select only the legacy portion. A compatible font remains necessary to display legacy output. Historic font-specific variants may require manual correction.

## Fixed layouts

- Source: m17n-db, `MIM/bn-probhat.mim` and `MIM/bn-inscript.mim` from https://git.savannah.nongnu.org/cgit/m17n/m17n-db.git/tree/MIM/ .
- Original MIM files and copyright notices retained in `assets/keyboard/`. LGPL-2.1-or-later; full text in `LGPL-2.1.txt`.
- Probhat credit: Red Hat, Inc.; original keymap by Taneem Ahmed, implementation by Jatin Nansi, documentation by Runa Bhattacharjee. InScript source credits Sun Microsystems, Inc. (2003), scim-tables, and iiimf unitLE's Bengali layout.
- Adaptation: `layouts.json` extracts printable ASCII/Shift mappings from the original MIM files. `prepare_data.py` reproduces extraction. AltGr and numeric keypad-specific rules are omitted. Maps remain separate replaceable JSON data; distribute source and license with them. This is a layout implementation, not Windows TSF/IME registration.

## Bengali and English word frequency data

- Source: `wordfreq==3.1.1`, https://github.com/rspeer/wordfreq ; package https://pypi.org/project/wordfreq/3.1.1/ . Copyright Robyn Speer and wordfreq contributors.
- Software license Apache-2.0: `WORDFREQ-LICENSE.txt`. **The exported word data is CC BY-SA 4.0**, not Apache-2.0: https://creativecommons.org/licenses/by-sa/4.0/ . Full upstream attribution and terms: `WORDFREQ-METADATA.txt` and `WORDFREQ-README.md`.
- Attributed underlying sources include Google Books Ngrams/Syntactic Ngrams, Wikipedia, University of Leeds Internet Corpus, ParaCrawl, OpenSubtitles, SUBTLEX authors Marc Brysbaert and colleagues, and other corpora individually credited in the bundled upstream metadata. Preserve that metadata when redistributing the dictionaries.
- Adaptation: flatten frequency bins in descending frequency order; NFC normalize; remove duplicates and non-word tokens; retain alphabetic ASCII English and Bengali-script word tokens. Exported JSON includes source, version, attribution, license URL and changes. The adapted JSON word lists remain CC BY-SA 4.0; equivalent share-alike terms apply to further adaptations of those data files, not automatically all independent app code.
- `prepare_data.py` with build-time wordfreq 3.1.1/msgpack regenerates the lists and layout JSON. Wordfreq is not required at app runtime. Combined word count: 504,240. These are statistical word lists, not an authoritative spelling dictionary; suggestions can include uncommon/incorrect words.

## Personal data and feature limits

- User dictionary, snippet, count, transition and history data reside in `%LOCALAPPDATA%/JoyKeyboard/keyboard.json`, outside EXE extraction. JSON import validates the whole structure before replacing memory; saves use `fsync` and atomic replacement. Invalid saved originals block automatic overwrite and produce `load_error` for the UI to surface.
- Suggestions combine licensed frequency rankings with user words/usage. Correction uses a bounded 3,000-word shortlist per first character. Next-word prediction learns only from text explicitly committed through JoyKeyboard; it is not a remote language model or a universal Bengali grammar checker.
- This implementation is independently developed from licensed components; it does not claim exact Kontho parity.
