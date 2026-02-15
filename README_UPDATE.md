# DLsite Auxiliary Update Script

**dlsite_update_renamed.py** は、既にリネーム済みのDLsiteフォルダ（「RJ番号_タイトル」形式）を最新のCSVデータで更新するための補助スクリプトです。

## 位置付け

このスクリプトは [dlsite_renamer.py](README.md) の補助ツールです：

| スクリプト | 入力フォルダ | 出力フォルダ | 用途 |
|-----------|------------|------------|------|
| **dlsite_renamer.py** | `RJ243414` | `RJ243414_メイドと暮らそ♪...` | 初回リネーム |
| **dlsite_update_renamed.py** | `RJ243414_古いタイトル` | `RJ243414_新しいタイトル` | 更新・再処理 |

## 使用シーン

- CSVのタイトルが更新された場合の一括再リネーム
- フォルダの更新日時（mtime）を購入日に一括設定したい場合
- サニタイズ規則が変更された際の再処理
- 一時的な大規模更新作業

## 要件

- Python 3.6以上
- **dlsite_renamer.py**（このスクリプトから関数をインポートします）
- DLsite購入履歴CSVファイル

## インストール

```bash
# 既にdlsite_renamer.pyがある場合
# 同じディレクトリにdlsite_update_renamed.pyを配置

# 実行権限を付与
chmod +x dlsite_update_renamed.py
```

## 使い方

### 基本的な使い方

```bash
# 1. まずドライランで確認（推奨）
python3 dlsite_update_renamed.py /path/to/dlsite/folders --dry-run

# 2. 問題なければ実行
python3 dlsite_update_renamed.py /path/to/dlsite/folders
```

### コマンドライン引数

```
使用法: dlsite_update_renamed.py <directory> [options]

必須引数:
  directory              更新対象のフォルダがあるディレクトリ
                         (RJ番号_タイトル形式のフォルダを含む)

オプション:
  --csv PATH             CSVファイルのパス
                         (デフォルト: dlsite_purchases.csv)

  --dry-run              ドライランモード（実際には更新しない）

  --yes                  確認プロンプトをスキップ

  --log-dir PATH         ログ出力ディレクトリ
                         (デフォルト: logs)

  --format {table,json}  プレビュー出力形式
                         (デフォルト: table)

  --max-length NUM       ファイル名の最大長
                         (デフォルト: 200)

  -h, --help             ヘルプメッセージを表示
```

**注意**: このスクリプトは**常に更新日時（mtime）を購入日に設定**します。

## 使用例

### 例1: ドライラン（プレビュー）

```bash
python3 dlsite_update_renamed.py /dlsite --dry-run
```

出力例:
```
================================================================================
RENAMING PREVIEW
================================================================================
Old Name                                 => New Name
--------------------------------------------------------------------------------
RJ243414_古いタイトル                    => RJ243414_メイドと暮らそ♪くるみち...
RJ243448_旧タイトル.part1                => RJ243448_幼馴染とドキドキ押し入れ...
================================================================================
Total operations: 15
================================================================================
```

### 例2: 実行（確認プロンプトあり）

```bash
python3 dlsite_update_renamed.py /mnt/nas/dlsite --csv dlsite_purchases_20260118_204640.csv
```

プレビューが表示された後、確認を求められます:
```
Proceed with updates? (yes/no): yes
```

### 例3: 実行（確認スキップ）

```bash
python3 dlsite_update_renamed.py /mnt/nas/dlsite --yes
```

スクリプトやバッチ処理に適しています。

### 例4: JSON形式でプレビュー

```bash
python3 dlsite_update_renamed.py /mnt/nas/dlsite --dry-run --format json > preview.json
```

JSON形式で出力され、他のツールと連携できます。

### 例5: カスタムCSVとログディレクトリ

```bash
python3 dlsite_update_renamed.py /mnt/nas/dlsite \
  --csv /path/to/custom.csv \
  --log-dir /var/log/dlsite_renamer
```

## 処理の仕組み

### 1. フォルダの検出

スクリプトは以下のパターンのフォルダを自動検出します：

```
✓ RJ243414_メイドと暮らそ♪くるみちゃんと一緒【バイノーラル】
✓ RJ01382778_小さなお姉さんと頑張りたい
✓ RJ243448_タイトル.part1
✓ RJ243448 （タイトル無しのフォルダにもタイトルを追加）
✗ メイドと暮らそ♪... （RJ番号がないフォルダは対象外）
```

### 2. RJ番号の抽出

フォルダ名の先頭からRJ番号を正規表現で抽出します：

```
RJ243414_古いタイトル.part1  →  RJ243414
```

### 3. CSVマッチング

抽出したRJ番号をCSVの`rj_number`列と照合し、最新のタイトルと購入日を取得します。

### 4. リネーム + mtime更新

```python
# タイトルが変更されている場合
RJ243414_古いタイトル  →  RJ243414_新しいタイトル

# タイトルが同じ場合はmtimeのみ更新
RJ243414_タイトル  →  RJ243414_タイトル (mtime更新のみ)
```

## マルチパートフォルダ

`.part1`、`.part2`などのサフィックスは自動的に保持されます:

```
RJ243448_古いタイトル.part1  =>  RJ243448_新しいタイトル.part1
RJ243448_古いタイトル.part2  =>  RJ243448_新しいタイトル.part2
```

## ファイル名サニタイズ

dlsite_renamer.pyと同じサニタイズルールを使用します（全角文字置換）:

| 元の文字 | 置換後 | 説明 |
|---------|--------|------|
| `?` | `？` | 全角疑問符 |
| `/` | `／` | 全角スラッシュ |
| `:` | `：` | 全角コロン |
| `*` | `＊` | 全角アスタリスク |
| `<` | `＜` | 全角小なり |
| `>` | `＞` | 全角大なり |
| `\|` | `｜` | 全角縦棒 |
| `"` | `＂` | 全角引用符 |
| `\` | `＼` | 全角バックスラッシュ |

## フォルダ更新日時（mtime）の設定

**このスクリプトは常に更新日時を設定します**（dlsite_renamer.pyの`--update-mtime`オプション相当）。

### 動作

- CSVの`purchase_date`列（例: `2019/01/21 21:56`）から年月日を抽出
- 時刻を`00:00:00`に設定
- フォルダの更新日時（modification time）とアクセス日時（access time）を設定

### 用途

- ファイルマネージャーで購入日順にソート
- バックアップツールでの日付管理
- 購入時期の視覚的な把握

### 例

```bash
# すべてのRJ番号_タイトルフォルダのmtimeを購入日に設定
python3 dlsite_update_renamed.py /mnt/nas/dlsite --yes
```

リネームが不要なフォルダ（タイトルが既に最新）でも、mtimeは更新されます。

## ログファイル

すべての操作は`logs/`ディレクトリにタイムスタンプ付きで記録されます（dlsite_renamer.pyと共通）:

```
logs/
└── rename_20260215_153045.log
```

ログには以下が含まれます:
- 各操作の成功/失敗
- mtime更新の情報
- エラーメッセージ
- 最終サマリー（成功数、失敗数）

例:
```
2026-02-15 15:30:45 - INFO - SUCCESS: RJ243414_古いタイトル => RJ243414_新しいタイトル
2026-02-15 15:30:45 - DEBUG -   Updated mtime for RJ243414_新しいタイトル to 2019-01-21
2026-02-15 15:30:46 - INFO - SUCCESS (mtime only): RJ243448_既に正しいタイトル
2026-02-15 15:30:46 - ERROR - FAILED: RJ999999_タイトル => RJ999999_新タイトル
2026-02-15 15:30:46 - ERROR -   Error: RJ number not found in CSV
```

## エラーハンドリング

### RJ番号がCSVにない場合

```
WARNING: RJ number not in CSV: RJ999999
```

フォルダはスキップされ、処理を継続します。

### タイトルが空の場合

```
ERROR: Failed to sanitize title for RJ243414: Title became empty after sanitization
```

フォルダはスキップされ、処理を継続します。

### 購入日がない場合

```
WARNING: No purchase date for RJ243414, skipping mtime update
```

リネームは行われますが、mtime更新はスキップされます。

### 重複するターゲット名

```
ERROR: Duplicate target names detected:
  RJ243414_タイトル:
    - RJ243414_古いタイトル1
    - RJ243414_古いタイトル2
```

重複が検出された場合、**すべての操作が中止**されます。CSVを修正してから再実行してください。

## トラブルシューティング

### dlsite_renamer.pyが見つからない

```
ModuleNotFoundError: No module named 'dlsite_renamer'
```

**解決方法**: dlsite_update_renamed.pyとdlsite_renamer.pyを同じディレクトリに配置してください。

### フォルダが検出されない

- フォルダ名が`RJ\d+`で始まっているか確認してください（例: `RJ243414_タイトル`）
- 大文字小文字は区別されません（`rj243414_タイトル`でもOK）

### CSVの文字エンコーディング

UTF-8 (BOM付き/なし両方対応) が必要です。Excelで保存する場合は「CSV UTF-8」形式を選択してください。

### パス長の問題

Windowsで長いパスエラーが発生する場合:

```bash
# 最大長を短く設定
python3 dlsite_update_renamed.py /path/to/folders --max-length 100
```

## 実装詳細

### 既存機能の再利用

dlsite_renamer.pyから以下の関数をインポートして再利用しています：

- `load_renaming_map()`: CSV読み込み
- `sanitize_filename()`: ファイル名サニタイズ
- `parse_purchase_date()`: 日付パース（00:00:00正規化）
- `setup_logging()`: ロギング設定
- `log_operation()`, `generate_summary_report()`: ログ・レポート機能
- `preview_renaming()`, `check_for_duplicates()`: プレビュー・検証機能
- `Config`: 設定定数

これにより、コードの重複を避け、メインスクリプトとの整合性を保っています。

### パフォーマンス最適化

- **フォルダキャッシュ**: ディレクトリを1回だけスキャンし、O(n)の時間計算量で処理
- **正規表現の事前コンパイル**: パターンマッチングの高速化
- **バッチ処理**: すべての操作を計画してから一括実行

### 安全機能

- **ドライランモード**: 実行前にプレビュー可能
- **重複検出**: 名前の衝突を事前にチェック
- **包括的ログ**: すべての操作を記録
- **確認プロンプト**: デフォルトで確認を要求（`--yes`で無効化可能）
- **エラー継続**: 1つの操作が失敗しても処理を継続

## 使用上の注意

### 一時的な使用を想定

このスクリプトは**一時的な大規模更新作業**を想定しています。

日常的な使用には、メインスクリプト（dlsite_renamer.py）の`--include-renamed`オプションを使用することもできます：

```bash
# メインスクリプトでも同様の処理が可能
python3 dlsite_renamer.py /path/to/folders --include-renamed --update-mtime
```

ただし、補助スクリプト（dlsite_update_renamed.py）の方が：
- 目的が明確
- CLIがシンプル
- 使い捨てに適している

### バックアップの推奨

大規模なリネーム作業の前に、**必ずバックアップを取る**ことを推奨します：

```bash
# バックアップ例
rsync -av /dlsite /backup/dlsite-$(date +%Y%m%d)

# または
tar czf dlsite-backup-$(date +%Y%m%d).tar.gz /dlsite
```

## ワークフロー例

### 初回セットアップ

```bash
# 1. メインスクリプトで初回リネーム
python3 dlsite_renamer.py /dlsite --yes

# 2. （オプション）後から購入日時を設定
python3 dlsite_update_renamed.py /dlsite --yes
```

### CSVタイトル更新後の再処理

```bash
# 1. 最新のCSVをダウンロード
# （https://github.com/koji-genba/dlsite_listMaker で作成）

# 2. プレビューで変更を確認
python3 dlsite_update_renamed.py /dlsite --csv dlsite_purchases_20260215.csv --dry-run

# 3. 問題なければ実行
python3 dlsite_update_renamed.py /dlsite --csv dlsite_purchases_20260215.csv --yes
```

### mtime一括更新（リネーム不要）

```bash
# タイトルは変更せず、mtimeだけ更新
# （タイトルが既に最新の場合、自動的にmtimeのみ更新されます）
python3 dlsite_update_renamed.py /dlsite --yes
```

## 関連リンク

- [メインスクリプト (dlsite_renamer.py)](README.md)
- [DLsite購入履歴CSV作成ツール](https://github.com/koji-genba/dlsite_listMaker)
