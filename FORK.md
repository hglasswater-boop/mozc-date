# mozc-date

このリポジトリは [google/mozc](https://github.com/google/mozc) の公開ソース
（取得時点のコミット `7eff5b3be9781ea6c86f47ef2077aa2342fc8b37`）を
起点にした、独立した派生版です。既存の Mozkey-date リポジトリの履歴や追加機能は
引き継いでいません。製品版の Google 日本語入力のソースではありません。

追加した機能は次のとおりです。

- **日付変換**: `20260908`、`9/8`、`2026-9-8` などの入力から日付候補を作成します。
  曜日の読みから今週・来週・先週の日付を表示します。設定画面の「日付」タブで
  書式を追加・編集・削除し、表示順を変更できます。`{YEAR}`、`{MONTH}`、
  `{DATE}` はゼロ埋め、`{YEAR_NOZERO}`、`{MONTH_NOZERO}`、`{DATE_NOZERO}` は
  ゼロ埋めなしです。曜日は `{WEEKDAY}` または `{WEEKDAY_LONG}` で指定できます。
- **英単語辞書**: ASCII の英単語入力中に補完候補を表示し、変換時に綴り修正候補を
  表示します。設定画面でそれぞれ有効・無効を選べます。
- **自動更新**: Windows x64 の「mozc-date について」画面から新リリースを確認し、
  SHA-256 を照合した MSI で更新します。

カタカナから英語への変換は、Mozc 標準の「カタカナ語を英語に変換する」設定に
従います。公開の EDICT 由来カタカナ英語辞書から抽出した対応表を組み込み、
末尾の長音を省いた読みも追加します。日本語候補より低い優先度で登録します。
出典、固定した取得リビジョン、変更内容と CC BY-SA 3.0 の条件は
[`src/data/dictionary_manual/katakana_english.LICENSE.md`](src/data/dictionary_manual/katakana_english.LICENSE.md)
に記載しています。ASCII 入力の英単語補完設定とは独立しています。

英単語データは ESDB/SCOWL から生成した表を使用します。ライセンスと出典は
[`src/rewriter/english_word_dictionary_ESDB_LICENSE.txt`](src/rewriter/english_word_dictionary_ESDB_LICENSE.txt)
に記載しています。

Windows x64 版のビルド手順は [`docs/build_mozc_in_windows.md`](docs/build_mozc_in_windows.md)
を参照してください。GitHub Actions は Windows x64 の日付・英単語テストと
インストーラーのビルドだけを実行します。
