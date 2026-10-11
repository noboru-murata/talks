# 公開の約束 (PUBLISHING.md)

このリポジトリ (talks) は講演資料を GitHub Pages で公開するためのもの．
**ここには，各講演の `make publish` が写したものだけを置く．手で直さない．**
講演の原本 (org・計算・コード) は各講演の private リポジトリにある．

この文書は，公開側 (talks) と講演側 (各講演のリポジトリ) と ox-quarto の
三者の取り決めである．どの作業からも手元のファイルとして読めるよう，ここに置く．
決定: 2026-10-11．

## 1. 並び

    talks/
    ├── index.html          講演の一覧．tools/build-index.py が各講演の meta.yml から作る (手で直さない)
    ├── site.yml            一覧ページの題と説明
    ├── PUBLISHING.md       この文書
    ├── README.md / LICENSE / LICENSE-CODE
    ├── .nojekyll           _ で始まるフォルダも公開させる
    ├── Makefile            make index / make check
    ├── tools/              check.py (公開前の検査)，build-index.py (一覧)
    └── <id>/               講演ごとのフォルダ．中身は講演側の make publish だけが書く
        ├── meta.yml
        ├── talk/<id>.html, talk/<id>-handout.pdf
        ├── report/…        解説文など
        └── demo/…          スライドが iframe で読むデモ

- `<id>` は英小文字・数字・ハイフン (例 `piml`)．URL になるので一度決めたら変えない．
- 講演のフォルダの中の並びは，**原本での相対位置を保つ**．スライドが `../demo/x.html` を
  読んでいるなら，公開側でも `talk/` と `demo/` を兄弟にする (パスを書き換えない)．
  `make publish-stage` が相対参照を一つずつ確かめ，ずれていれば止める．

## 2. 役割

| どこ | 受け持つもの |
|---|---|
| talks (ここ) | この約束，`tools/check.py` (検査)，`tools/build-index.py` (一覧)，公開そのもの (push はユーザー) |
| ox-quarto | `tools/publish.mk` と `tools/oxq-publish.py` (集める・写す) |
| 各講演 | 原本の `meta.yml` (既定 `publish/meta.yml`)，Makefile の `PUB_ID` と `PUB_FILES` |

## 3. 講演側の書き方

講演の Makefile (例 `talk/Makefile`) の最後に:

```make
PUB_ID    := piml
PUB_FILES := piml.html=talk/piml.html \
             piml-handout.pdf=talk/piml-handout.pdf \
             piml-review.html=report/piml-review.html \
             piml-review.pdf=report/piml-review.pdf \
             ../demo/clothoid-pinn.html=demo/clothoid-pinn.html
include $(OXQ)/tools/publish.mk
```

`PUB_FILES` は「元のパス (Makefile から見た相対パス)=公開側のパス (`<id>/` から見た相対パス)」の並び．
`.gitignore` に `_publish/` を足す．

| コマンド | すること |
|---|---|
| `make publish-stage` | `_publish/<id>/` に公開する形で集める．発表者ノートを取り除く (既定) |
| `make publish-check` | 集めたものを `tools/check.py` で調べる |
| `make publish-diff` | 調べたうえで，`talks/<id>/` がどう変わるかを表示するだけ |
| `make publish` | 調べたうえで `talks/<id>/` に写し (`rsync --delete`．そのフォルダの中だけ)，`index.html` を作り直す |

そのあと talks で `git diff` を見て，ユーザーが commit と push をする．

## 4. meta.yml

講演の原本 (`publish/meta.yml`) に書く．`id` と `updated` は `make publish` が書き足す．

```yaml
title: 物理を組み込む機械学習
subtitle: 制約付き曲線の設計で見る PINN から作用素学習まで
lang: ja
authors:
  - name: 村田 昇
abstract: >
  一覧ページに出す 2〜3 行の紹介．
events:                       # 新しい順．一覧は先頭の日付で並ぶ
  - date: 2026-11-05          # YYYY-MM-DD
    venue: ○○研究会
    kind: 招待講演
items:                        # 一覧ページのリンク．path は <id>/ から見た相対パス
  - {kind: slides,     path: talk/piml.html,          label: スライド}
  - {kind: handout,    path: talk/piml-handout.pdf,   label: 配布用 PDF}
  - {kind: report,     path: report/piml-review.html, label: 解説}
  - {kind: report-pdf, path: report/piml-review.pdf,  label: 解説 (PDF)}
  - {kind: demo,       path: demo/clothoid-pinn.html, label: デモ}
license: CC-BY-NC-4.0
publish:
  notes: false                # 発表者ノートを公開するか．既定 false
  figures_cleared: false      # 他人の図の引用を確かめたら true (5 の人の確認)．true でないと公開できない
```

- `kind` は `slides` `handout` `report` `report-pdf` `demo` `video` `code` のどれか (一覧の既定の名前に使う)．
- 一覧ページの題は `kind: slides` の項へのリンクになる．

## 5. 公開前の確認

### 自動の検査 (`tools/check.py`．publish のたびに必ず通る)

誤り (公開を止める):

1. **許可リスト**: 公開してよい拡張子は html・pdf・css・js・json・yml・画像・フォント・動画だけ．
   org・qmd・tex・bib・R・py・ipynb・csv などのデータやコードはそもそも通らない．
2. **禁止するパス**: `waseda` を含む名前，`_quarto/`，`local/`，`notes/`，隠しファイル，シンボリックリンク．
3. **ロゴ**: `_quarto/local/` の画像 (校章など．商標) が html に埋め込まれていないか，base64 の断片で照合する．
   embed-resources で埋め込むとファイル名が消えるので，名前だけでは見つからないため．
   PDF は html から作るので，html が通れば PDF にも載っていない．
4. **手元の情報**: `/Users/…` などの絶対パス，`file://`，`localhost` へのリンク (html・css・js・PDF の文書情報)．
5. **発表者ノート** (`publish.notes: false` のとき):
   html に `<aside class="notes">` が残っていないこと．
   **ノートはスライドの html の中にある** (S キーの発表者表示やソースで読める) ので，
   PDF を外すだけでは足りない．`make publish-stage` が取り除き，ここで確かめる．
   配布用 PDF (`kind: handout`，と items に無い PDF) にノートの文が載っていないことも調べる．
   ノートなしの配布用 PDF は `make <名前>-handout.pdf` (publish.mk の規則．`oxq-pdf.py --no-notes`) で作る．
   解説文の PDF (`report-pdf`) はノートと同じ文を含むことがあるので，この照合からは除く．
6. **相対参照**: html の相対リンク・画像・iframe が講演のフォルダの中の実在するファイルを指すこと．
7. **meta.yml**: 必要な項目，`items` のパスが実在すること，`publish.figures_cleared: true`．
8. **大きさ**: 1 ファイル 95MB を超えたら誤り (GitHub の上限は 100MB)．50MB を超えたら警告．

### 人の確認 (自動では調べられない．`figures_cleared: true` にする前に)

- **他人の図の引用**: 会場の参加者から世界中に見る人が広がる．出典の明記，引用の必要性と主従関係を確かめ，
  許諾が要る図は差し替えるか外す．
- **未発表の結果・共同研究者の確認**: 公開してよいと合意しているか．
- **個人の情報**: 写真・氏名 (謝辞の頁など) を公開してよいか．
- ノートを公開する (`notes: true`) ときは，ノートの言い回しが公開に耐えるか．

## 6. html の形

- **スライド (revealjs) は embed-resources で 1 ファイルにする** (ox-quarto の talk.yaml の既定のまま)．
  - デモの iframe は ox-quarto の `iframe.lua` が `data-iframe-src` に入れて表示時に読むので，
    埋め込みの影響を受けない．相対パスは 1 の約束で保つ．
  - MathJax は reveal.js の math プラグインが CDN (jsdelivr) から読む．埋め込まれないが，それでよい．
- `*_files/` を伴う html (embed-resources を使わないもの) も置ける．`make publish-stage` が
  `<名前>_files/` の中の参照先を一緒に集める．
- フォント・ライブラリ (reveal.js，MathJax など) はそれぞれ元のライセンスに従う (README)．

## 7. 版の残し方

- 公開するのは **最新版だけ** (`<id>/`)．講演で見せる QR コードや URL は `…/talks/<id>/` を指す．
- 過去の版は talks の git の履歴とタグで残す．講演の日に公開したら `git tag <id>-YYYY-MM-DD`．
- 同じ講演を別の場で話したら，`events` の先頭に足す (同じフォルダのまま)．
- 大きく作り直して旧版も見せたいときだけ，別の id (例 `piml-2027`) にする．

## 8. ライセンス

- 資料 (スライド・PDF・解説文): CC BY-NC 4.0 (`LICENSE`)．
- コード (デモの html に含まれるスクリプト，`tools/`): MIT (`LICENSE-CODE`)．
- 講演ごとに変えるときは meta.yml の `license` に書く．
