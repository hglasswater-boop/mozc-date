import unittest
from dictionary import gen_katakana_english_dictionary as generator


class DictionaryTest(unittest.TestCase):
    def test_preserves_native_pos_and_adds_cost(self):
        result = list(generator.generate(
            [("こんとろーる", "control")], [[
                "こんとろーる\t5\t6\t3200\tコントロール\n",
                "こんとろーる\t7\t8\t4000\tコントロール\n",
            ]], 99))
        self.assertEqual(result, ["こんとろーる\t5\t6\t5700\tcontrol\n"])

    def test_existing_english_is_not_duplicated(self):
        result = list(generator.generate(
            [("あいす", "Ice"), ("あいす", "Ice")],
            [["あいす\t1\t1\t2000\tIce\n"]], 99))
        self.assertEqual(result, [])

    def test_missing_native_word_uses_noun_id(self):
        result = list(generator.generate([("さーば", "server")], [], 123))
        self.assertEqual(result, ["さーば\t123\t123\t9000\tserver\n"])


if __name__ == "__main__":
    unittest.main()
