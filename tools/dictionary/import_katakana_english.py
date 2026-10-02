"""Reproduce the CC BY-SA 3.0 kana mappings from a pinned public dictionary.

Run from the repository root. Builds consume the committed TSV, never the network.
"""
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import quote
from urllib.request import urlopen

SOURCE = "KEINOS/google-ime-user-dictionary-ja-en"
REVISION = "7d241dafcf6ee1f9eafefc0ae7a929c095860246"
FILES = [
    "google-ime-jp-カタカナ英語辞書01-あ～お(1).txt",
    "google-ime-jp-カタカナ英語辞書02-おぞん～さばら.txt",
    "google-ime-jp-カタカナ英語辞書03-さはりん～でぃんぎー.txt",
    "google-ime-jp-カタカナ英語辞書04-でぃんご～ひっぷ.txt",
    "google-ime-jp-カタカナ英語辞書05-ひっぷ～みすたいぷ.txt",
    "google-ime-jp-カタカナ英語辞書06-みずだこ～んびら.txt",
]


def hiragana(text):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c
                   for c in unicodedata.normalize("NFKC", text))


def extract(text):
    """Keep kana loanwords and clean English spellings, excluding definitions."""
    result = set()
    for line in text.splitlines():
        fields = line.lstrip("\ufeff").split("\t")
        if len(fields) == 3:
            # One source file uses katakana keys and omits the comment column.
            key, value, _ = fields
            original = key
        elif len(fields) == 4:
            key, value, _, original = fields
        else:
            continue
        original = unicodedata.normalize("NFKC", original)
        key = hiragana(key)
        if not re.fullmatch(r"[ァ-ヶー・]{2,40}", original):
            continue
        if not re.fullmatch(r"[ぁ-ゖー・]{2,40}", key):
            continue
        if hiragana(original) != key:
            continue
        # Same alphabet as Mozc's IsEnglishTransliteration; no gloss punctuation.
        if not re.fullmatch(r"[A-Za-z]+(?:[ '-][A-Za-z]+){0,3}", value):
            continue
        if len(key) == 2 and not re.fullmatch(r"[A-Za-z]{3,}", value):
            continue
        result.add((key, value))
        # Only terminal long vowels: dropping internal ones creates false readings.
        if key.endswith("ー") and len(key) > 3:
            result.add((key[:-1], value))
    return result


def main():
    entries = set()
    hashes = {}
    for name in FILES:
        path = "Google-ime-jp-カタカナ英語辞典/" + name
        url = f"https://raw.githubusercontent.com/{SOURCE}/{REVISION}/{quote(path)}"
        with urlopen(url) as response:
            data = response.read()
        hashes[path] = hashlib.sha256(data).hexdigest()
        entries.update(extract(data.decode("utf-8-sig")))
    destination = Path("src/data/dictionary_manual")
    with (destination / "katakana_english.tsv").open("w", encoding="utf-8", newline="\n") as output:
        output.write("# CC BY-SA 3.0. See katakana_english.LICENSE.md.\n")
        for key, value in sorted(entries):
            output.write(f"{key}\t{value}\n")
    (destination / "katakana_english.sources.json").write_text(
        json.dumps({"repository": SOURCE, "revision": REVISION,
                    "sha256": hashes, "entries": len(entries)}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(f"Imported {len(entries)} reading/spelling pairs")


if __name__ == "__main__":
    main()
