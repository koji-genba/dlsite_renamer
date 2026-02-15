# DLsite Folder Renamer

DLsiteから購入した作品のフォルダを、RJ番号から日本語タイトルにリネームするPythonツールです。

## 要件

- Python 3.6以上
- DLsite購入履歴CSVファイル(https://github.com/koji-genba/dlsite_listMaker で作成)

## インストール

```bash
# リポジトリをクローンまたはスクリプトをダウンロード
git clone <repository-url>
cd dlsite_renamer

# 実行権限を付与
chmod +x dlsite_renamer.py
```

## 使い方

### 基本的な使い方

```bash
# 1. まずドライランで確認（推奨）
python3 dlsite_renamer.py /path/to/dlsite/folders --dry-run

# 2. 問題なければ実行
python3 dlsite_renamer.py /path/to/dlsite/folders
```

### コマンドライン引数

```
使用法: dlsite_renamer.py <directory> [options]

必須引数:
  directory              リネーム対象のフォルダがあるディレクトリ

オプション:
  --csv PATH             CSVファイルのパス
                         (デフォルト: dlsite_purchases_20260118_204640.csv)

  --dry-run              ドライランモード（実際にはリネームしない）

  --yes                  確認プロンプトをスキップ

  --log-dir PATH         ログ出力ディレクトリ
                         (デフォルト: logs)

  --format {table,json}  プレビュー出力形式
                         (デフォルト: table)

  --max-length NUM       ファイル名の最大長
                         (デフォルト: 200)

  --update-mtime         フォルダの更新日時を購入日に設定
                         (年月日のみ、時刻は00:00:00に設定)

  --remove-suffix        フォルダが1つだけの場合は.partNサフィックスを除去
                         (重複回避のため複数ある場合は保持)

  --include-renamed      既にリネーム済みのフォルダも処理対象に含める
                         (タイトル名のフォルダも検索・リネーム)

  -h, --help             ヘルプメッセージを表示
```

### 使用例

#### 例1: ドライラン（プレビュー）

```bash
python3 dlsite_renamer.py /dlsite --dry-run
```

出力例:
```
================================================================================
RENAMING PREVIEW
================================================================================
Old Name                                 => New Name
--------------------------------------------------------------------------------
RJ243414                                 => メイドと暮らそ♪くるみちゃんと...
RJ243448.part1                           => 【全年齢】癒しガール１.part1
RJ243448.part2                           => 【全年齢】癒しガール１.part2
================================================================================
Total operations: 79
================================================================================
```

#### 例2: 実行（確認プロンプトあり）

```bash
python3 dlsite_renamer.py /mnt/nas/dlsite --csv ./dlsite_purchases_20260118_204640.csv
```

プレビューが表示された後、確認を求められます:
```
Proceed with renaming? (yes/no): yes
```

#### 例3: 実行（確認スキップ）

```bash
python3 dlsite_renamer.py /mnt/nas/dlsite --yes
```

スクリプトやバッチ処理に適しています。

#### 例4: JSON形式でプレビュー

```bash
python3 dlsite_renamer.py /mnt/nas/dlsite --dry-run --format json > preview.json
```

JSON形式で出力され、他のツールと連携できます。

#### 例5: カスタムCSVとログディレクトリ

```bash
python3 dlsite_renamer.py /mnt/nas/dlsite \
  --csv /path/to/custom.csv \
  --log-dir /var/log/dlsite_renamer
```

#### 例6: 更新日時を購入日に設定

```bash
python3 dlsite_renamer.py /mnt/nas/dlsite --update-mtime
```

フォルダの更新日時（modification time）がCSVの購入日（年月日のみ、時刻は00:00:00）に設定されます。これにより、ファイルマネージャーで購入日順にソートできます。

#### 例7: サフィックスを除去（安全な場合のみ）

```bash
python3 dlsite_renamer.py /mnt/nas/dlsite --remove-suffix
```

`.part1`などのサフィックスを、重複が起きない場合のみ除去します。

- `RJ243414.part1`（これだけ） → `タイトル`
- `RJ243448.part1` + `RJ243448.part2`（両方ある） → `タイトル.part1` + `タイトル.part2`

#### 例8: 既にリネーム済みのフォルダも処理

```bash
python3 dlsite_renamer.py /mnt/nas/dlsite --include-renamed
```

RJ番号のフォルダだけでなく、既にタイトル名にリネーム済みのフォルダも処理対象に含めます。以下のような用途に便利です：

- CSVのタイトルが更新された場合の再リネーム
- サニタイズ規則が変更された場合の再処理
- 過去にリネームしたフォルダの統一

**組み合わせ例：**
```bash
# リネーム済みフォルダも含めて、すべての更新日時を設定
python3 dlsite_renamer.py /mnt/nas/dlsite --include-renamed --update-mtime
```

## ファイル名サニタイズ

以下の文字は自動的に全角文字に置換されます:

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

## マルチパートフォルダ

分割ダウンロードされた作品の`.part1`、`.part2`などのサフィックスは自動的に保持されます:

```
RJ243448           => 【全年齢】癒しガール１
RJ243448.part1     => 【全年齢】癒しガール１.part1
RJ243448.part2     => 【全年齢】癒しガール１.part2
```

### サフィックスの自動除去

`--remove-suffix`オプションを使用すると、フォルダが1つだけの場合に限り`.partN`サフィックスを除去できます:

**デフォルト動作**:
```
RJ243414.part1（これだけ）  => タイトル.part1
```

**--remove-suffix使用時**:
```
RJ243414.part1（これだけ）  => タイトル
```

**重複回避（複数フォルダがある場合は自動的にサフィックス保持）**:
```
RJ243448.part1 + RJ243448.part2  => タイトル.part1 + タイトル.part2
```

これにより、不要なサフィックスを除去しつつ、名前の衝突を防ぎます。

## フォルダ更新日時の設定

`--update-mtime`オプションを使用すると、フォルダの更新日時をCSVの購入日に設定できます。

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
# リネームと同時に更新日時を設定
python3 dlsite_renamer.py /mnt/nas/dlsite --update-mtime --yes
```

**注意**:
- purchase_date列が空の場合は更新日時は変更されません
- 既存の更新日時は上書きされます
- ドライランモードでは実際の更新は行われません

### 既にリネーム済みのフォルダの処理

`--include-renamed`オプションを使用すると、**既に作品名にリネームされているフォルダ**も処理対象に含めることができます：

```bash
# 既にリネーム済みのフォルダも処理
python3 dlsite_renamer.py /mnt/nas/dlsite --include-renamed --yes
```

**動作:**
1. RJ番号のフォルダを検索 → リネーム
2. RJ番号が見つからない場合、作品名のフォルダを検索 → リネーム（または変更なし）

**オプションの組み合わせ:**

| オプション | 処理対象 | 動作 |
|-----------|---------|------|
| なし | RJ番号フォルダのみ | リネームのみ |
| `--update-mtime` | RJ番号フォルダのみ | リネーム + mtime更新 |
| `--include-renamed` | RJ + リネーム済み | すべてリネーム |
| `--include-renamed --update-mtime` | RJ + リネーム済み | すべてリネーム + mtime更新 |

これにより、過去にリネームしたフォルダに対しても、後から購入日時を設定したり、タイトルを更新したりできます。

## ログファイル

すべての操作は`logs/`ディレクトリにタイムスタンプ付きで記録されます:

```
logs/
└── rename_20260214_153045.log
```

ログには以下が含まれます:
- 各操作の成功/失敗
- エラーメッセージ
- 最終サマリー（成功数、失敗数）

例:
```
2026-02-14 15:30:45 - INFO - SUCCESS: RJ243414 => メイドと暮らそ♪くるみちゃんと一緒【バイノーラル】
2026-02-14 15:30:45 - ERROR - FAILED: RJ999999 => タイトル
2026-02-14 15:30:45 - ERROR -   Error: Source not found: /path/to/RJ999999
```

## トラブルシューティング

### Python 3がインストールされているか確認

```bash
python3 --version
```

Python 3.6以上が必要です。

### CSVの文字エンコーディング

UTF-8 (BOM付き/なし両方対応) が必要です。Excelで保存する場合は「CSV UTF-8」形式を選択してください。

### パス長の問題

Windowsで長いパスエラーが発生する場合:

```bash
# 最大長を短く設定
python3 dlsite_renamer.py /path/to/folders --max-length 100
```

または、Windows 10/11でレジストリ設定により長いパスを有効化:
```
HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem
LongPathsEnabled = 1
```
