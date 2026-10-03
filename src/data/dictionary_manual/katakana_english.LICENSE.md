# Katakana English dictionary — CC BY-SA 3.0

This data is adapted from the **Google IME Katakana English Dictionary**, an
EDICT-derived dictionary credited by its publisher to the unnamed original
author and community contributors. KEINOS maintains the public mirror:
https://github.com/KEINOS/google-ime-user-dictionary-ja-en

Source revision: `7d241dafcf6ee1f9eafefc0ae7a929c095860246`.
The six input files and their SHA-256 digests are recorded in
`katakana_english.sources.json`.

The original dictionary and these modified dictionary data are distributed under
**Creative Commons Attribution-ShareAlike 3.0 Unported**:
https://creativecommons.org/licenses/by-sa/3.0/
Full license: https://creativecommons.org/licenses/by-sa/3.0/legalcode

Changes made in mozc-date: retain entries whose original Japanese spelling is
entirely katakana; normalize width and kana readings; exclude glosses and
non-English symbols; deduplicate; add readings without a terminal long-vowel
mark; generate Mozc noun tokens and conservative costs. These changes do not
imply endorsement by the original authors or mirror maintainer.

Reproduce the TSV from the pinned public sources with:
`python tools/dictionary/import_katakana_english.py` (repository root).
Builds use the committed data and do not download the reference dictionary.

Share-alike applies to this dictionary data and its generated derivative.
Keep this attribution and license when redistributing it, including compiled data.
The separate Mozc program code retains its existing license.
