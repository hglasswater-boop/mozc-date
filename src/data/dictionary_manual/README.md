# data/dictionary_manual

This directory contains word entries to be added to the main dictionary.

The data here are used for proactive fixes before the main dictionary is
updated.

## TSV files (e.g. places.tsv, words.tsv)

Entries are added to the main dictionary with the following adjustments:

*   The POS (e.g., 名詞) is converted to a POS ID (e.g., 1843).
*   The cost is set to the median cost of all words sharing the same POS.

These adjustments are performed by
[dictionary/gen_aux_dictionary.py](https://github.com/google/mozc/blob/master/src/dictionary/gen_aux_dictionary.py).

If the same entries already exist in the main dictionary, the entries in this
directory are ignored. For more control, you may want to use
`aux_dictionary.tsv` and `dictionary_filter.tsv`.

*   https://github.com/google/mozc/blob/master/src/data/dictionary_oss/aux_dictionary.tsv
*   https://github.com/google/mozc/blob/master/src/data/dictionary_oss/dictionary_filter.tsv

## domain.txt

This file uses the same format as the main dictionary and is used as part of it.

We recommend using the TSV files instead, as the POS IDs and cost values
typically change with each dictionary update.

## Modern katakana/English supplement

`modern_katakana_english.json` is a small, manually reviewed supplement for
current product and technical terms. It records the English spelling source,
the date checked, and the project-chosen Japanese reading. The readings are
editorial input choices, not claims that the referenced pages prescribe a
Japanese pronunciation. Entries contain factual names and mappings only; no
third-party definitions or dictionary text is copied.

Review the source pages when adding terms, and review this list monthly or when
requested. There is no automatic trend discovery or scheduled update. The
offline generator checks the schema and duplicate source mappings, adds a
shortened alias only when a reading longer than three characters ends in `ー`,
then writes the committed TSV and metadata deterministically. The same English
spelling may appear under distinct readings:

```sh
python tools/dictionary/generate_modern_katakana_english.py
python -m unittest tools.dictionary.test_generate_modern_katakana_english
```

The metadata SHA-256 covers the committed authored JSON manifest bytes only;
it does not hash or snapshot the linked webpages. Generation and dictionary
builds use only local files and do not access the network. The generated TSV
is added beside the existing pinned `katakana_english.tsv` input; that dataset
is kept unchanged.
