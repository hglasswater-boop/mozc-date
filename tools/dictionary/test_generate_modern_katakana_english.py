import json
from pathlib import Path
import unittest

from tools.dictionary.generate_modern_katakana_english import render


def manifest(entries):
    return json.dumps({"schema_version": 1, "entries": entries}, ensure_ascii=False).encode()


def entry(reading="くろーど", spelling="Claude"):
    return {
        "reading": reading,
        "spelling": spelling,
        "source_url": "https://example.test/",
        "checked_on": "2026-10-03",
        "reading_note": "Editorial Japanese reading.",
    }


class ModernSupplementTest(unittest.TestCase):
    def test_committed_artifacts_match_generator(self):
        root = Path(__file__).resolve().parents[2]
        data_dir = root / "src/data/dictionary_manual"
        tsv, metadata = render((data_dir / "modern_katakana_english.json").read_bytes())
        self.assertEqual(tsv, (data_dir / "modern_katakana_english.tsv").read_bytes())
        self.assertEqual(metadata, (data_dir / "modern_katakana_english.sources.json").read_bytes())

    def test_deterministic_sorted_tsv_and_explicit_hash_scope(self):
        raw = manifest([entry("でぃーぷしーく", "DeepSeek"), entry()])
        tsv1, metadata1 = render(raw)
        tsv2, metadata2 = render(raw)
        self.assertEqual((tsv1, metadata1), (tsv2, metadata2))
        self.assertLess(tsv1.index(b"Claude"), tsv1.index(b"DeepSeek"))
        metadata = json.loads(metadata1)
        self.assertEqual(metadata["entry_count"], 2)
        self.assertEqual(metadata["mapping_count"], 2)
        self.assertEqual(metadata["manifest_sha256_scope"], "committed authored manifest bytes only")
        self.assertFalse(metadata["external_webpages_hashed"])

    def test_rejects_duplicate_pair(self):
        with self.assertRaisesRegex(ValueError, "duplicate mapping"):
            render(manifest([entry(), entry()]))

    def test_allows_same_spelling_for_distinct_readings(self):
        tsv, metadata = render(manifest([
            entry("えむしーぴー", "MCP"),
            entry("えむしーぴ", "MCP"),
        ]))
        self.assertEqual(tsv.count(b"\tMCP\n"), 2)
        self.assertEqual(json.loads(metadata)["entry_count"], 2)

    def test_only_absorbs_terminal_long_vowel(self):
        tsv, metadata = render(manifest([
            entry("えむしーぴー", "MCP"),
            entry("でぃーぷしーく", "DeepSeek"),
            entry("こーどー", "Code"),
        ]))
        rows = set(tsv.decode().splitlines())
        self.assertIn("えむしーぴー\tMCP", rows)
        self.assertIn("えむしーぴ\tMCP", rows)
        self.assertIn("でぃーぷしーく\tDeepSeek", rows)
        self.assertIn("こーどー\tCode", rows)
        self.assertIn("こーど\tCode", rows)
        self.assertNotIn("でぃぷしーく\tDeepSeek", rows)
        self.assertEqual(json.loads(metadata)["entry_count"], 3)
        self.assertEqual(json.loads(metadata)["mapping_count"], 5)

    def test_rejects_missing_provenance_and_invalid_reading(self):
        bad = entry(reading="Claude")
        with self.assertRaisesRegex(ValueError, "hiragana"):
            render(manifest([bad]))
        bad = entry()
        del bad["source_url"]
        with self.assertRaisesRegex(ValueError, "source_url"):
            render(manifest([bad]))

if __name__ == "__main__":
    unittest.main()
