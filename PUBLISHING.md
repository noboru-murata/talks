# 公開の約束 (PUBLISHING.md)

このリポジトリ (talks) は講演資料を GitHub Pages で公開するためのもの．
**ここには，各講演の `make publish` / `make publish-edition` が写したものと，
`tools/build-index.py` が作る頁だけを置く．手で直さない．**
講演の原本 (org・計算・コード) は各講演の private リポジトリにある．

この文書は，公開側 (talks) と講演側 (各講演のリポジトリ) と ox-quarto の
三者の取り決めである．どの作業からも手元のファイルとして読めるよう，ここに置く．
決定: 2026-10-11．主題と版の形に改めた: 2026-10-12．

## 0. 場所

| | |
|---|---|
| 手元 | `~/Desktop/claude/talks/` (講演のリポジトリと同じ階層．publish.mk の既定 `PUB_ROOT = ../../talks`) |
| GitHub | https://github.com/noboru-murata/talks (public．main の / を Pages で公開) |
| 公開の URL | https://noboru-murata.github.io/talks/ (主題の一覧) |
| 共通の部品 | `~/Desktop/claude/ox-quarto/tools/` (publish.mk，oxq-publish.py，oxq-pdf.py --no-notes) |

push すると 1〜2 分で反映される．

## 1. 主題と版

同じ主題の資料は，講演を重ねるたびに拡張版として増えていく．そこで二つに分ける．

- **主題** (`<主題>/`): 解説文・デモなど**育てていくもの**．常に最新．一覧には主題が 1 つだけ出る．
- **講演の版** (`<主題>/<版>/`): その講演で見せたスライド・配布物．**講演の場で見せた URL の先が
  後から変わらない**よう，講演の日の翌日から固定する (4)．

    talks/
    ├── index.html                  主題の一覧 (build-index が作る．最新の講演の日付の新しい順)
    ├── site.yml                    一覧の題と説明
    ├── PUBLISHING.md / README.md / LICENSE / LICENSE-CODE / .nojekyll / Makefile
    ├── tools/                      check.py (公開前の検査)，build-index.py (頁を作る)
    └── physics-informed-ml/        主題 (id)
        ├── index.html              主題の頁 (build-index が作る): 概要，最新の資料，講演の版の一覧
        ├── meta.yml                主題の情報 (make publish が書く)
        ├── report/…  demo/…        育てていく資料 (make publish が書く)
        └── 2026-10-19/             講演の版 (make publish-edition が書く)
            ├── index.html          版の頁 (build-index が作る): その講演の資料，最新の資料への案内，訂正の記録
            ├── meta.yml            版の情報
            ├── talk/physics-informed-ml.html, talk/physics-informed-ml-handout.pdf
            └── demo/clothoid-pinn.html   スライドが ../demo/ で読むので，版の中に固定して写す

- **主題の id** は英小文字・数字・ハイフン (例 `physics-informed-ml`)．URL になるので一度決めたら変えない．
- **版の名前**は講演の日付 `YYYY-MM-DD`．同じ日に 2 つ目があれば `YYYY-MM-DD-b`，`-c` …
  主題の部分には，この形の名前のフォルダを置かない．
- **書き手を分ける**: 主題の部分は `make publish`，版の中は `make publish-edition`，
  `index.html` は `tools/build-index.py` だけが書く．
- **並びは原本での相対位置を保つ**: スライドが `../demo/x.html` を読んでいるなら，版の中でも
  `talk/` と `demo/` を兄弟にする (パスを書き換えない)．版の中の参照は版のフォルダの中で閉じる．
  主題の部分から版の中は参照しない (版の頁と主題の頁は build-index が結ぶ)．

## 2. URL の約束

| 何 | URL |
|---|---|
| 主題の一覧 | `https://noboru-murata.github.io/talks/` |
| 主題の頁 | `https://noboru-murata.github.io/talks/<主題>/` |
| **講演で見せる URL・QR コード** | **版の頁** `https://noboru-murata.github.io/talks/<主題>/<版>/` |
| スライドそのもの | `…/talks/<主題>/<版>/talk/<主題>.html` (これも固定) |

版の頁からはその講演の資料と，主題の頁 (最新の解説・デモ) へたどれる．
一度公開した URL は消さない・名前を変えない．

## 3. 役割

| どこ | 受け持つもの |
|---|---|
| talks (ここ) | この約束，`tools/check.py`，`tools/build-index.py`，公開そのもの (push はユーザー) |
| ox-quarto | `tools/publish.mk` と `tools/oxq-publish.py` (集める・写す・固定)，`oxq-pdf.py --no-notes` |
| 各講演 | 原本の `meta.yml` (既定 `publish/meta.yml`)，Makefile の変数 |

## 4. 版の固定 (封印) と訂正

- **講演の日までは** `make publish-edition` で何度でも上書きできる (前もって公開し，当日まで直してよい)．
- **講演の日の翌日から固定**．同じ版への `make publish-edition` は止まる．判定は版の `date` と今日の日付だけ．
- **訂正だけは例外**として認める: 誤字，壊れたリンク，事実の誤り，権利上の理由での差し替え．
  `make publish-edition PUB_FIX="図 3 の出典を追記"` のように理由を付けて実行する．
  - ファイルの追加・削除・改名はできない (URL を変えないため)．並びが変われば止まる．
  - 理由は版の `meta.yml` の `revisions` に記録され，版の頁に「訂正の記録」として出る．
- 内容を足したい・作り直したいときは，主題の部分 (`make publish`) を育てるか，次の講演の版にする．
- 権利上の理由でファイルそのものを消さなければならないときは，手で talks から消して commit し，
  消した理由を commit の文に書く (例外中の例外)．

## 5. タグ

- 講演が終わって固定されたら，一度だけ `git tag <主題>/<版>` (例 `physics-informed-ml/2026-10-19`)．
- 訂正のたびに新しいタグは付けない (履歴は git と `revisions`)．主題の部分にはタグを付けない．

## 6. 講演側の書き方

### Makefile (例 `talk/Makefile` の最後)

```make
PUB_ID            := physics-informed-ml
PUB_FILES         := piml-review.html=report/physics-informed-ml-review.html \
                     piml-review.pdf=report/physics-informed-ml-review.pdf \
                     ../demo/clothoid-pinn.html=demo/clothoid-pinn.html
PUB_EDITION       := 2026-10-19
PUB_EDITION_FILES := piml.html=talk/physics-informed-ml.html \
                     piml-handout.pdf=talk/physics-informed-ml-handout.pdf \
                     ../demo/clothoid-pinn.html=demo/clothoid-pinn.html
include $(OXQ)/tools/publish.mk
```

- `*_FILES` は「元のパス (Makefile から見た相対パス)=公開側のパス」の並び．
  `PUB_FILES` の右側は主題のフォルダから，`PUB_EDITION_FILES` の右側は版のフォルダから見たパス．
- 原本のファイル名は変えなくてよい．公開側の名前は右側で決める．
- `PUB_EDITION` はいま作っている版だけ．次の講演では書き換える (過去の版の元ファイルは要らない)．
- `.gitignore` に `_publish/` を足す．

| コマンド | すること |
|---|---|
| `make publish` | 主題の部分を `talks/<主題>/` に写す (`rsync --delete`．版のフォルダと頁は消さない) |
| `make publish-edition` | 版を `talks/<主題>/<版>/` に写す (その版のフォルダの中だけ)．固定後は `PUB_FIX` が要る |
| `make publish-all` | 上の 2 つを続けて (初めての公開と講演の当日に)．主題がまだ無いと `publish-edition` は止まる |
| `make publish-diff` / `make publish-edition-diff` | 調べたうえで，変わる所を表示するだけ |
| `make publish-check` / `make publish-edition-check` | 仮置き場 (`_publish/`) に集めて調べるだけ |
| `make <名前>-handout.pdf` | ノートなしの配布用 PDF (`oxq-pdf.py --no-notes`．並べ方は `PUB_HANDOUT_OPTS`) |

どれも最後に `index.html` (一覧・主題・版の頁) を作り直す．そのあと talks で `git diff` を見て，
ユーザーが commit と push をする．並列 (`make -j`) では動かさない．

### meta.yml (講演側の原本 `publish/meta.yml`．主題の情報と全部の版を 1 つに)

```yaml
title: 物理を組み込む機械学習
subtitle: 制約付き曲線の設計で見る PINN から作用素学習まで
lang: ja
authors:
  - name: 村田 昇
abstract: >
  主題の頁と一覧に出す 2〜3 行の紹介．
license: CC-BY-NC-4.0
publish:                      # 既定．版ごとに上書きできる
  notes: false                # 発表者ノートを公開するか．既定 false
  figures_cleared: true       # 他人の図の引用を確かめたら true (8 の人の確認)．true でないと公開できない
items:                        # 主題の部分 (育てていくもの)．path は <主題>/ から見た相対パス
  - {kind: report,     path: report/physics-informed-ml-review.html, label: 解説}
  - {kind: report-pdf, path: report/physics-informed-ml-review.pdf,  label: 解説 (PDF)}
  - {kind: demo,       path: demo/clothoid-pinn.html,                label: デモ}
editions:                     # 講演の版．キーは版の名前 (引用符で囲んで文字列にする)
  "2026-10-19":
    venue: 第34回鉄鋼工学アドバンストセミナー
    kind: 基調講演
    # 任意: date (省けば名前の日付)，title / subtitle (この版だけの題)，event_url，publish (上書き)
    items:                    # path は <主題>/<版>/ から見た相対パス
      - {kind: slides,  path: talk/physics-informed-ml.html,        label: スライド}
      - {kind: handout, path: talk/physics-informed-ml-handout.pdf, label: 配布用 PDF}
      - {kind: demo,    path: demo/clothoid-pinn.html,              label: デモ (この講演の版)}
```

- `kind` は `slides` `handout` `report` `report-pdf` `demo` `video` `code` のどれか (頁の既定の名前に使う)．
- 公開側には，この原本から次の 2 つが作られる (手で書かない):
  - `<主題>/meta.yml`: `editions` を除いたもの＋ `id`・`updated`．版の一覧は持たない (build-index がフォルダから集める)．
  - `<主題>/<版>/meta.yml`: その版の項目＋ `edition`・`topic`・`date`・`title`・`license`・`publish` (主題の値を引き継ぎ，
    版の上書きを反映)・`published` (初めて公開した日)・`revisions` (訂正の記録)．

## 7. 公開前の検査 (`tools/check.py`．publish のたびに必ず通る)

talks で `make check` を実行すると，すべての主題とその中の版を調べ直す．フォルダの種類は
`meta.yml` で見分ける (`edition` があれば版，なければ主題)．

誤り (公開を止める):

1. **許可リスト**: 公開してよい拡張子は html・pdf・css・js・json・yml・画像・フォント・動画だけ．
   org・qmd・tex・bib・R・py・ipynb・csv などのデータやコードはそもそも通らない．
2. **禁止するパス**: `waseda` を含む名前，`_quarto/`，`local/`，`notes/`，隠しファイル，シンボリックリンク．
3. **ロゴ**: `_quarto/local/` の画像 (校章など．商標) が埋め込まれていないか，base64 の断片で照合する．
4. **手元の情報**: `/Users/…` などの絶対パス，`file://`・`localhost` へのリンク (html・css・js・PDF の文書情報)．
5. **発表者ノート** (`publish.notes: false` のとき): html に `<aside class="notes">` が残っていないこと
   (ノートはスライドの html の中にあるので，stage が取り除く)．配布用 PDF (`kind: handout`，と items に無い PDF)
   にノートの文が載っていないこと．解説文の PDF (`report-pdf`) はノートと同じ文を含むことがあるので照合から除く．
6. **文字コード**: html に `<meta charset>` などの指定が無ければ誤り．
   先頭 1024 バイトより後ろにあるだけなら警告 (stage が `<head>` の直後に足すので，ふつうは出ない．
   Quarto の embed-resources はスクリプトを指定より前に埋め込み，charset を送らないサーバーで文字化けする)．
   `<!doctype html>` が無ければ警告．
7. **相対参照**: 実在するファイルを指すこと．版の中の参照は版のフォルダの中で閉じること．
   主題の部分から版の中を参照しないこと．build-index が作る頁は除く．
8. **meta.yml**:
   - 主題: `id` がフォルダ名と同じ，`title`・`license`，`items` のパスが実在，`editions` を持たない．
   - 版: `edition` がフォルダ名 (`YYYY-MM-DD[-b]`) と同じ，`date` がその日付，`topic` が主題のフォルダ名，
     `title`・`venue`・`items`・`license`，`revisions` には `date` と `note`．
   - どちらも `publish.figures_cleared: true`．
   - 主題の中に，版の名前の形でないのに日付で始まるフォルダがあれば誤り．
9. **大きさ**: 1 ファイル 95MB を超えたら誤り (GitHub の上限は 100MB)．50MB を超えたら警告．

### 人の確認 (自動では調べられない．`figures_cleared: true` にする前に)

- **他人の図の引用**: 会場の参加者から世界中に見る人が広がる．出典の明記，引用の必要性と主従関係を確かめ，
  許諾が要る図は差し替えるか外す．
- **未発表の結果・共同研究者の確認**: 公開してよいと合意しているか．
- **個人の情報**: 写真・氏名 (謝辞の頁など) を公開してよいか．
- ノートを公開する (`notes: true`) ときは，ノートの言い回しが公開に耐えるか．

## 8. html の形

- **スライド (revealjs) は embed-resources で 1 ファイルにする** (ox-quarto の talk.yaml の既定のまま)．
  - デモの iframe は ox-quarto の `iframe.lua` が `data-iframe-src` に入れて表示時に読むので，
    埋め込みの影響を受けない．相対パスは 1 の約束で保つ．
  - MathJax は reveal.js の math プラグインが CDN (jsdelivr) から読む．
- `*_files/` を伴う html (embed-resources を使わないもの) も置ける．stage が `<名前>_files/` の中の参照先を一緒に集める．
- 手で書く html (デモなど) には `<!doctype html>` と `<meta charset="utf-8">` を入れる．
- フォント・ライブラリ (reveal.js，MathJax など) はそれぞれ元のライセンスに従う (README)．

## 9. ライセンス

- 資料 (スライド・PDF・解説文): CC BY-NC 4.0 (`LICENSE`)．
- コード (デモの html に含まれるスクリプト，`tools/`): MIT (`LICENSE-CODE`)．
- 主題や版ごとに変えるときは meta.yml の `license` に書く．
