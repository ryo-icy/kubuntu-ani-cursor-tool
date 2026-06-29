---
description: zip ファイルまたはディレクトリにある Windows .ani/.cur カーソルファイルを KDE カーソルテーマ（.tar.gz）に変換する。ファイル一覧からロールを自動推定し、不明なものはユーザーに確認してから変換する。
argument-hint: "[テーマ名] [zipファイルまたはディレクトリ]"
arguments: [theme, source]
disable-model-invocation: false
allowed-tools: Bash Read
---

zip ファイルまたはディレクトリに含まれる `.ani`/`.cur` ファイルを調べ、ロールを自動判定して `src/main.py` で KDE カーソルテーマアーカイブを作成する。

引数は `/convert-cursors <テーマ名> <ソース>` の形式で渡せる。

## 手順

### 1. 入力を受け取る

以下をそれぞれ確認する。引数（`$theme`、`$source`）で渡されていればそれを使い、不足している項目だけユーザーに聞く。

- **ソース**（`$source`）— zip ファイルまたはディレクトリのパス。未指定なら必ず聞く。
- **テーマ名**（`$theme`）— KDE に表示されるテーマの名前。未指定なら **必ずユーザーに確認する**（ディレクトリ名や zip 名をデフォルトにしない）。
- **アーカイブ出力先** — 未指定なら `./<テーマ名>.tar.gz` をデフォルトとして使う。

### 2. ファイルを展開・一覧取得する

**zip の場合** — 一時ディレクトリに展開する:
```bash
tmpdir=$(mktemp -d)
unzip -q "<zipファイル>" -d "$tmpdir"
find "$tmpdir" -iname "*.ani" -o -iname "*.cur"
```

**ディレクトリの場合** — そのまま一覧を取得する:
```bash
find "<ディレクトリ>" -iname "*.ani" -o -iname "*.cur"
```

### 3. ロールを自動推定する

ファイル名（拡張子を除いたステム）を見て、下記の判定基準でロールを割り当てる。

**ツールの組み込み推定を先に試す**（`FILENAME_ROLE_MAP` が英語ステムを網羅している）:
```bash
python3 src/main.py --list-roles
```

**ファイル名の意味からの推定基準**（日本語・その他言語も含む）:

| 意味のキーワード例 | ロール |
|---|---|
| 通常・矢印・arrow・default・left_ptr | `arrow` |
| 待ち・ビジー・busy・wait・砂時計 | `wait` |
| バックグラウンド・作業中・working | `working` |
| テキスト・文字・ibeam・text・beam | `text` |
| リンク・hand・pointer・指 | `link` |
| ヘルプ・help・? | `help` |
| 移動・move・全方向 | `move` |
| 不可・禁止・unavailable・no・circle | `unavailable` |
| 十字・crosshair・領域・cell | `crosshair` |
| 上下・縦・size_ns・ns・↕ | `size_ns` |
| 左右・横・size_ew・ew・↔ | `size_ew` |
| 斜め（↖↘）・size_nwse・nwse | `size_nwse` |
| 斜め（↗↙）・size_nesw・nesw | `size_nesw` |
| 上矢印・up_arrow | `up_arrow` |
| ペン・手書き・pen・pencil | `pen` |

**判定の確信度に応じて分類する:**
- **確定**（ファイル名から明確に判断できる）→ そのまま採用
- **不明・曖昧**（ファイル名から判断できない、または複数のロールが候補になる）→ ユーザーに確認

### 4. 不明なファイルをユーザーに確認する

不明・曖昧なファイルがある場合は、候補ロールを添えてまとめて提示する:

```
以下のファイルのロールを確認してください:
  ドット絵.ani  → 候補: arrow（確信なし）/ 別のロールであれば教えてください
  代替選択.ani  → 候補: crosshair か arrow？
```

確認が取れたら次のステップに進む。

### 5. マッピング案をユーザーに提示して承認を得る

変換前に全マッピングを表示して確認を求める:

```
以下のマッピングで変換します。よろしいですか？

  arrow    ← ファイル名.ani
  wait     ← ファイル名.ani
  text     ← ファイル名.ani
  ...

問題なければ「はい」、修正があれば教えてください。
```

### 6. 環境を確認する

`win2xcur` が PATH にあるか確認する:
```bash
which win2xcur
```
見つからない場合は、プロジェクトルートで `direnv allow` を実行するか `nix develop` で dev shell に入るよう伝えて中断する。

### 7. 変換を実行する

承認されたマッピングで変換する:
```bash
python3 src/main.py --name "<テーマ名>" --archive "<出力先>" \
  role1:"/path/to/file1.ani" \
  role2:"/path/to/file2.ani" \
  ...
```

### 8. 結果を報告する

変換完了後、以下を報告する:
1. 作成されたアーカイブのパス
2. 最終的なロールマッピング一覧（ロール → ファイル名）
3. KDE への適用手順:
   > KDE システム設定 → カーソル → ファイルからインストール → アーカイブを選択

zip を展開した一時ディレクトリは報告後に削除する:
```bash
rm -rf "$tmpdir" && echo "ok" || echo "FAILED"
```
削除に失敗した場合（`FAILED` が出た場合）は、その旨をユーザーに伝え、以下のコマンドを手動で実行するよう依頼する:
```bash
rm -rf "$tmpdir"
```

## 注意事項

- 同じロールに複数のファイルが割り当てられると警告が出て後勝ちになるため、重複を避ける。
- `--role` は1ファイルのみに使用可能。複数ファイルは必ず `role:file` 形式で渡す。
- アーカイブは一時ディレクトリでビルドされ、`~/.local/share/icons/` には何も書き込まれない。
- 同じ `--archive` パスで再実行するとファイルは上書きされる。
