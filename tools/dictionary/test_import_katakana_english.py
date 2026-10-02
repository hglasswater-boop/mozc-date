import unittest
from pathlib import Path
from import_katakana_english import extract


class ImportTest(unittest.TestCase):
    def test_committed_dictionary_covers_common_words(self):
        path = Path(__file__).resolve().parents[2] / "src/data/dictionary_manual/katakana_english.tsv"
        entries = {tuple(line.split("\t")) for line in
                   path.read_text(encoding="utf-8").splitlines()
                   if line and not line.startswith("#")}
        self.assertGreater(len(entries), 28000)
        for key, word in [("こんとろーる", "control"),
                          ("こんぴゅーた", "computer"),
                          ("こんぴゅーたー", "computer"),
                          ("さーば", "server"), ("さーばー", "server")]:
            self.assertIn((key, word), entries)

    def test_long_vowel_alias_only_at_end(self):
        entries = extract("さーばー\tserver\t名詞\tサーバー\n")
        self.assertEqual(entries, {("さーばー", "server"), ("さーば", "server")})

    def test_filters_definitions_and_japanese_translations(self):
        entries = extract(
            "こんとろーる\tcontrol\t名詞\tコントロール\n"
            "こんとろーる\tcontrol (something)\t名詞\tコントロール\n"
            "あーかいぶさき\tarchiving destination\t名詞\tアーカイブ先\n"
            "what\tAh\t名詞\tアー\n")
        self.assertEqual(entries, {("こんとろーる", "control")})

    def test_normalizes_half_width_katakana(self):
        entries = extract("こんぴゅーたー\tcomputer\t名詞\tｺﾝﾋﾟｭｰﾀｰ\n")
        self.assertEqual(entries, {("こんぴゅーた", "computer"),
                                   ("こんぴゅーたー", "computer")})


if __name__ == "__main__":
    unittest.main()
