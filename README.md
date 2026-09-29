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

製品版数は Mozc の版数から独立させています。独自版数の開始タグは `v4.0.0.0` です。
既存の `v3.x` から MSI で上書き更新できるように `4` から始めます。以後は3番目の数字を
増やし、例として次のリリースは `v4.0.1.0` にします。4番目の数字は Windows Installer
が更新判定に使わないため、常に `0` にしてください。タグを push すると Windows x64 CI が
MSI 内部の版数を照合してから、MSI、チェックサム、更新スクリプトを Release に公開します。

元の Mozc の説明は [UPSTREAM_README.md](UPSTREAM_README.md) に保存しています。
