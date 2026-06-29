# kubuntu-ani-cursor-tool

Windows の `.ani` / `.cur` カーソルファイルを KDE Plasma で使えるカーソルテーマ（`.tar.gz`）に変換する CLI ツールです。

## 必要なもの

- [Nix](https://nixos.org/)（Determinate Systems 版推奨）
- [direnv](https://direnv.net/)

Python や pip のインストールは不要です。Nix がすべて管理します。

## セットアップ

```bash
git clone https://github.com/ryo-icy/kubuntu-ani-cursor-tool
cd kubuntu-ani-cursor-tool
direnv allow   # 初回のみ。Nix が依存関係をダウンロードします
```

> **初回は時間がかかります。** `win2xcur` 等のパッケージをダウンロードするためです。

## 使い方

### 基本

```bash
# 1つのファイルを変換（ファイル名からカーソルの役割を自動推定）
python src/main.py --name "MyTheme" cursor.ani

# 役割（role）を明示して変換
python src/main.py --name "MyTheme" --role wait busy.ani

# 複数ファイルを一括変換（role:ファイル名 の形式）
python src/main.py --name "MyTheme" \
    arrow:arrow.ani \
    wait:busy.ani \
    text:text.ani

# アーカイブの出力先を指定
python src/main.py --name "MyTheme" --archive ~/MyTheme.tar.gz arrow:arrow.ani
```

デフォルトの出力先は `./<テーマ名>.tar.gz` です。

### オプション

| オプション | 短縮形 | 説明 |
|---|---|---|
| `--name THEME_NAME` | `-n` | テーマ名（必須） |
| `--archive FILE.tar.gz` | `-a` | 出力アーカイブのパス（デフォルト: `./<THEME_NAME>.tar.gz`） |
| `--role ROLE` | `-r` | 単一ファイルの役割を指定（ファイルが2つ以上の場合はエラー） |
| `--list-roles` | | 指定できる役割の一覧を表示 |

### 役割（role）一覧

```bash
python src/main.py --list-roles
```

主な役割:

| role | 意味 |
|---|---|
| `arrow` | 通常のカーソル（左矢印） |
| `wait` | 待ち状態（砂時計/スピナー） |
| `working` | バックグラウンド処理中 |
| `text` | テキスト入力（Iビーム） |
| `link` | リンク上（人差し指ポインタ） |
| `help` | ヘルプカーソル |
| `move` | 移動 |
| `unavailable` | 操作不可 |
| `crosshair` | 十字カーソル |
| `size_ns` | 上下リサイズ |
| `size_ew` | 左右リサイズ |
| `size_nwse` | 斜め（↖↘）リサイズ |
| `size_nesw` | 斜め（↗↙）リサイズ |
| `up_arrow` | 上矢印 |
| `pen` | ペン / 手書き |

## KDE への適用

変換後に生成された `.tar.gz` ファイルを KDE でインストールします：

**システム設定 → 外観 → カーソル → 「ファイルからインストール」→ `.tar.gz` を選択 → 適用**

## ファイル構成

```
.
├── flake.nix                              # Nix 環境定義
├── flake.lock
├── .envrc                                 # direnv 設定
├── .claude/
│   └── skills/
│       └── convert-cursors/
│           └── SKILL.md                   # AI 向けスキル定義
├── AGENTS.md                              # AI 向けドキュメント
├── CLAUDE.md -> AGENTS.md                 # AGENTS.md へのシンボリックリンク
└── src/
    └── main.py                            # ツール本体
```
