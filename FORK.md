# Mozc の日付・英単語版

このリポジトリは [google/mozc](https://github.com/google/mozc) の公開ソースを
起点にした、独立した派生版です。既存の Mozkey-date リポジトリの履歴や追加機能は
引き継いでいません。製品版の Google 日本語入力のソースではありません。

追加した機能は次の二つです。

- **日付変換**: `20260908`、`9/8`、`2026-9-8` などの入力から日付候補を作成します。
  曜日の読みから今週・来週・先週の日付を表示します。設定画面では
  `{YEAR}`、`{MONTH}`、`{DATE}` などを使った追加書式を `;` 区切りで指定できます。
- **英単語辞書**: ASCII の英単語入力中に補完候補を表示し、変換時に綴り修正候補を
  表示します。設定画面でそれぞれ有効・無効を選べます。

英単語データは ESDB/SCOWL から生成した表を使用します。ライセンスと出典は
[`src/rewriter/english_word_dictionary_ESDB_LICENSE.txt`](src/rewriter/english_word_dictionary_ESDB_LICENSE.txt)
に記載しています。

Windows 版のビルド手順は [`docs/build_mozc_in_windows.md`](docs/build_mozc_in_windows.md)
を参照してください。GitHub Actions の Windows CI は日付・英単語のテストを実行してから
インストーラーをビルドします。
