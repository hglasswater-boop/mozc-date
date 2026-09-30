# Mozc Date English

公開版の [Mozc](https://github.com/google/mozc) を起点にした Windows x64 向けの派生版です。
製品版 Google 日本語入力のソースではありません。

追加機能は日付変換、英単語辞書による補完・綴り修正、アプリ内からの更新確認と
GitHub Release 経由の自動更新です。既存の Mozkey-date とは別リポジトリです。
詳しい機能と出典は [FORK.md](FORK.md) を参照してください。

## 入手・ビルド

Windows x64 の MSI は [Releases](https://github.com/hglasswater-boop/mozkey-date-minimal/releases)
から入手できます。公開前のビルド成果物は
[Windows x64 CI](https://github.com/hglasswater-boop/mozkey-date-minimal/actions/workflows/windows.yaml)
にあります。ローカルビルドは [公式の Windows 手順](docs/build_mozc_in_windows.md)
を参照してください。

## 更新

「Mozc について」画面で「更新を確認」を押すと、このリポジトリの最新 Release を
確認します。更新可能なときは「更新する」から x64 MSI をダウンロードし、SHA-256 を
照合してから Windows Installer を起動します。更新時に管理者権限の確認が表示されます。

製品版数と Release タグは `v0.x.y` を使用し、About 画面にも同じ版数を表示します。
Mozc 本体のエンジン版数は `src/version.bzl` で独立して管理します。MSI の
`ProductVersion` は製品版数の先頭に 100 を加え、例として `v0.2.1` は `100.2.1` に
なります。既存版の UpgradeCode を維持し、旧 `v3.x` / `v4.0.0.0` から MSI で上書き
更新できるようにしています。Windows バイナリのファイル版数も `100.x.y.0` とし、
旧版より高い値でファイルを置換します。過去の4桁タグは履歴として扱います。

旧版に組み込まれた更新ツールは4桁タグ専用のため、`v0.x.y` への最初の移行では
Releases から新しい MSI をダウンロードして実行してください。新しい版の更新確認では
MSI 版数の順序を使うため、古い `v4.x` を新しい `v0.x.y` より新しいと判定しません。

タグを push すると Windows x64 CI が日付・英単語・設定の回帰テストと、タグ、About
表示用版数、MSI 内部の版数、UpgradeCode の整合性を検証してから Release に公開します。
リリース検証記録には対象コミットと検証した機能・テストを記録します。
ローカル開発の製品版数は `src/product_version.txt` の `0.0.0` が既定値です。
特定の版数をビルドするには `--action_env=MOZKEY_PRODUCT_VERSION=0.2.1` を Bazel に
渡してください。MSI の制約により、製品版数の先頭は155以下、2番目は255以下、
3番目は65535以下とし、先頭ゼロや接尾辞は使用しません。

リリース前には旧版インストール済みの Windows で上書きインストールし、About の版数が
タグと一致すること、新しい日付・英単語設定が表示されること、旧バイナリや旧設定画面が
起動しないことを実機確認してください。

元の Mozc の説明は [UPSTREAM_README.md](UPSTREAM_README.md) に保存しています。
