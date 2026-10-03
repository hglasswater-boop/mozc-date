"""Generate the offline modern katakana/English supplement and its metadata."""

import argparse
import hashlib
import json
import re
from pathlib import Path


_READING = re.compile(r"^[ぁ-ゖー]+$")
_SPELLING = re.compile(r"^[A-Za-z]+(?:[ '-][A-Za-z]+)*$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def render(manifest_bytes):
    """Return TSV and metadata bytes after validating the authored manifest."""
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("manifest must be UTF-8 JSON") from error
    if set(manifest) != {"schema_version", "entries"} or manifest["schema_version"] != 1:
        raise ValueError("expected schema_version 1 and entries only")
    if not isinstance(manifest["entries"], list) or not manifest["entries"]:
        raise ValueError("entries must be a non-empty list")

    rows = []
    seen = set()
    for entry in manifest["entries"]:
        expected = {"reading", "spelling", "source_url", "checked_on", "reading_note"}
        if not isinstance(entry, dict) or set(entry) != expected:
            raise ValueError("each entry must include reading, spelling, source_url, checked_on, reading_note")
        reading, spelling = entry["reading"], entry["spelling"]
        if not isinstance(reading, str) or not _READING.fullmatch(reading):
            raise ValueError(f"invalid hiragana reading: {reading!r}")
        if not isinstance(spelling, str) or not _SPELLING.fullmatch(spelling):
            raise ValueError(f"invalid English spelling: {spelling!r}")
        if not entry["source_url"].startswith("https://") or not _DATE.fullmatch(entry["checked_on"]):
            raise ValueError("source_url must be HTTPS and checked_on must be YYYY-MM-DD")
        if not entry["reading_note"].strip():
            raise ValueError("reading_note must describe the editorial reading choice")
        pair = (reading, spelling)
        if pair in seen:
            raise ValueError(f"duplicate mapping: {reading} -> {spelling}")
        seen.add(pair)
        rows.append(pair)

    # Mirror the terminal-long-vowel absorption used by the existing
    # katakana/English importer: keep the explicit reading and add a shortened
    # alias only when the final character is ー and the reading is > 3 chars.
    mappings = set(rows)
    for reading, spelling in rows:
        if len(reading) > 3 and reading.endswith("ー"):
            mappings.add((reading[:-1], spelling))
    mappings = sorted(mappings)
    tsv = "# Authored modern-word supplement; see modern_katakana_english.json for provenance.\n"
    tsv += "".join(f"{reading}\t{spelling}\n" for reading, spelling in mappings)
    metadata = {
        "schema_version": 1,
        "manifest": "modern_katakana_english.json",
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "manifest_sha256_scope": "committed authored manifest bytes only",
        "external_webpages_hashed": False,
        "entry_count": len(rows),
        "mapping_count": len(mappings),
        "tsv_sha256": hashlib.sha256(tsv.encode("utf-8")).hexdigest(),
    }
    return tsv.encode("utf-8"), (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("src/data/dictionary_manual/modern_katakana_english.json"))
    parser.add_argument("--tsv", type=Path, default=Path("src/data/dictionary_manual/modern_katakana_english.tsv"))
    parser.add_argument("--metadata", type=Path, default=Path("src/data/dictionary_manual/modern_katakana_english.sources.json"))
    args = parser.parse_args()
    tsv, metadata = render(args.manifest.read_bytes())
    args.tsv.write_bytes(tsv)
    args.metadata.write_bytes(metadata)


if __name__ == "__main__":
    main()
