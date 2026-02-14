# DLsite Folder Renamer

DLsiteから購入した作品のフォルダを、RJ番号から日本語タイトルにリネームするPythonツールです。

## 特徴

- **標準ライブラリのみ**: 外部依存なし、Python 3さえあれば動作
- **Windows互換**: NTFS/ZFS、SMB共有で使用可能
- **安全設計**: ドライランモード、重複検出、詳細ログ
- **マルチパート対応**: `.part1`、`.part2`などのサフィックスを自動保持
- **日本語対応**: UTF-8 BOM対応、全角文字への自動変換

## 要件

- Python 3.6以上
- DLsite購入履歴CSVファイル

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

  -h, --help             ヘルプメッセージを表示
```

### 使用例

#### 例1: ドライラン（プレビュー）

```bash
python3 dlsite_renamer.py /mnt/nas/dlsite --dry-run
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

## CSVファイル形式

CSVファイルには最低限以下の列が必要です:

- `rj_number`: DLsite作品番号（例: RJ243414）
- `title`: 作品タイトル（日本語）

例:
```csv
rj_number,title,circle,purchase_date,...
RJ243414,メイドと暮らそ♪くるみちゃんと一緒【バイノーラル】,サークル名,2019/01/21 21:56,...
RJ346413,【全年齢】癒しガール１,別のサークル,2020/05/15 12:30,...
```

## ファイル名サニタイズ

Windows非対応文字は自動的に全角文字に置換されます:

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

これにより、タイトルの視認性を保ちつつWindows/NTFS/ZFSで使用可能になります。

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

### すでにリネーム済みのフォルダの更新日時設定

`--update-mtime`オプションを使用すると、**すでに作品名にリネームされているフォルダ**に対しても、更新日時だけを設定できます：

```bash
# すでにリネーム済みのフォルダの日付も更新
python3 dlsite_renamer.py /mnt/nas/dlsite --update-mtime --yes
```

**動作:**
1. RJ番号のフォルダを検索 → リネーム + mtime更新
2. RJ番号が見つからない場合、作品名のフォルダを検索 → mtimeのみ更新

これにより、過去にリネームしたフォルダに対しても、後から購入日時を設定できます。

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

## エラーハンドリング

### よくあるエラーと対処法

#### 1. フォルダが見つからない

```
WARNING - Folders not found for X RJ numbers
```

**原因**: CSV内のRJ番号に対応するフォルダがディレクトリ内に存在しない

**対処**: 正常な動作です。ダウンロードしていない作品はスキップされます。

#### 2. 重複ターゲット名

```
ERROR - Duplicate target names detected:
  タイトル名:
    - RJ123456
    - RJ789012
```

**原因**: 複数の異なるRJ番号が同じタイトルを持っている

**対処**: CSVを確認し、タイトルを区別できるように手動で調整してください。

#### 3. ターゲットがすでに存在

```
ERROR - Target already exists: /path/to/新しいタイトル
```

**原因**: リネーム先のフォルダ名がすでに存在する

**対処**: 既存のフォルダを削除または別名に変更してください。

#### 4. 書き込み権限なし

```
ERROR - No write permission: /path/to/directory
```

**原因**: ディレクトリに書き込み権限がない

**対処**: `chmod`で権限を変更するか、管理者として実行してください。

## 推奨ワークフロー

本番環境で使用する前の推奨手順:

```bash
# 1. ドライランで全体をプレビュー
python3 dlsite_renamer.py /mnt/nas/dlsite --dry-run > preview.txt

# 2. プレビューを目視確認
less preview.txt

# 3. 小規模テスト（数個のフォルダで試す）
mkdir test_folders
cp -r /mnt/nas/dlsite/RJ243414 test_folders/
python3 dlsite_renamer.py test_folders --yes

# 4. バックアップ作成（推奨）
rsync -av /mnt/nas/dlsite /mnt/nas/dlsite_backup

# 5. 本番実行
python3 dlsite_renamer.py /mnt/nas/dlsite

# 6. ログを確認
cat logs/rename_*.log | grep -E "FAILED|ERROR"
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

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

バグ報告や機能リクエストはIssueでお願いします。プルリクエストも歓迎します。

## 免責事項

このツールはフォルダ名を変更します。実行前に必ずバックアップを取ることを強く推奨します。作者はデータ損失について一切の責任を負いません。
