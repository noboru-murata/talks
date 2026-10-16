#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6", "pypdf>=4"]
# ///
"""check.py — 主題や講演の版のフォルダを公開してよいか調べる．

使い方:
    uv run --script tools/check.py physics-informed-ml/          # 主題と，その中の版をすべて
    uv run --script tools/check.py physics-informed-ml/2026-10-19
    uv run --script tools/check.py _publish/topic/<主題> \\
        --forbid-assets _quarto/local --notes-snippets …notes.txt   # publish.mk から

フォルダの種類は meta.yml で見分ける: edition があれば講演の版，なければ主題．
規則は PUBLISHING.md の「公開前の検査」．誤りが 1 つでもあれば終了コード 1．
警告は表示するだけで止めない．
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import re
import sys
from pathlib import Path

import yaml

ID_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
EDITION_RE = re.compile(r"\d{4}-\d{2}-\d{2}(?:-[a-z])?")

# 公開してよい拡張子 (許可リスト)．これ以外のファイルがあれば誤り
ALLOWED_EXT = {
    ".html", ".pdf", ".css", ".js", ".mjs", ".json", ".yml",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".woff", ".woff2", ".ttf", ".otf",
    ".mp4", ".webm",
}
# パスに含まれていたら誤り (大文字小文字を区別しない)
FORBIDDEN_PATH = [
    (re.compile(r"waseda", re.I), "校章などのロゴ (商標)"),
    (re.compile(r"(^|/)_quarto(/|$)"), "_quarto/ (テーマの原本・ロゴ)"),
    (re.compile(r"(^|/)local(/|$)"), "local/ (配布しないファイル)"),
    (re.compile(r"(^|/)notes(/|$)"), "notes/ (作業メモ)"),
    (re.compile(r"(^|/)\."), "隠しファイル"),
]
# 文書の中に含まれていたら誤り
FORBIDDEN_TEXT = [
    (re.compile(r"/Users/[A-Za-z0-9_.-]+"), "手元の絶対パス"),
    (re.compile(r"/home/[a-z][A-Za-z0-9_.-]*/"), "手元の絶対パス"),
    # リンク・読み込みの値として現れたものだけ (reveal.js などの注釈の中の file:// は除く)
    (re.compile(r"""(?:\b(?:src|href|action|data-[\w-]+)\s*=\s*["']|url\(\s*["']?)file://"""), "file:// のリンク"),
    (re.compile(r"""(?:\b(?:src|href|action|data-[\w-]+)\s*=\s*["']|url\(\s*["']?)https?://(?:localhost|127\.0\.0\.1)\b"""),
     "localhost へのリンク"),
    (re.compile(r"waseda[-_][A-Za-z0-9_-]*\.(?:png|svg|jpe?g|scss)", re.I), "ロゴのファイル名"),
]
TEXT_EXT = {".html", ".css", ".js", ".mjs", ".json", ".svg", ".yml"}
REF_ATTR = re.compile(r'''\b(?:src|href|poster|data-src|data-iframe-src|data-background-image|data-background-iframe)\s*=\s*"([^"]*)"''')
NOTES_RE = re.compile(r'<aside\b[^>]*class="[^"]*\bnotes\b')
CHARSET_RE = re.compile(r"""<meta\b[^>]*\bcharset\s*=|<meta\b[^>]*http-equiv\s*=\s*["']?content-type""", re.I)
DOCTYPE_RE = re.compile(r"^\s*(?:<!--.*?-->\s*)*<!doctype\s+html", re.I | re.S)
# 道具が作る頁 (参照の検査はしない): build-index.py と，Hugo のテーマ oxq-pages (ox-quarto/samples/publish/hugo)
GENERATORS = ("talks/tools/build-index.py", "oxq-pages (Hugo)")
# macOS の Finder がフォルダを開くと作るファイル．.gitignore で除いてあり公開されないので，調べない
OS_JUNK = {".DS_Store"}
SIZE_WARN = 50 * 2**20
SIZE_ERROR = 95 * 2**20      # GitHub の上限は 1 ファイル 100MB


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")


def is_local_ref(ref: str) -> bool:
    """html の属性の値のうち，同じサイトの中のファイルを指すものか．"""
    if not ref or ref.startswith(("#", "data:", "mailto:", "javascript:", "//")):
        return False
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", ref):        # http: https: など
        return False
    if any(c in ref for c in "'+{}$` <>"):                    # スクリプトの中の文字列の断片
        return False
    return True


def logo_fingerprints(dirs: list[Path], unreadable: list[str]) -> list[tuple[str, str]]:
    """禁止する画像の (名前, base64 の断片)．埋め込まれていれば見つかる．"""
    fps = []
    for d in dirs:
        if not d.exists():
            continue
        for p in sorted(d.rglob("*")):
            if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp", ".pdf"}:
                try:
                    raw = p.read_bytes()
                except OSError as e:      # iCloud に退避されて読めないなど
                    unreadable.append(f"{p} ({e.strerror})")
                    continue
                if len(raw) < 256:
                    continue
                # data URI はファイルの先頭から符号化されるので，途中の断片で照合できる
                # (先頭は PNG の見出しなどで他の画像と共通なので避ける)
                fps.append((p.name, base64.b64encode(raw).decode()[120:200]))
    return fps


def load_meta(root: Path, rep: Report) -> dict | None:
    mp = root / "meta.yml"
    if not mp.exists():
        rep.error("meta.yml", "ない")
        return None
    try:
        return yaml.safe_load(mp.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        rep.error("meta.yml", f"YAML として読めない: {e}")
        return None


def check_items(root: Path, meta: dict, rep: Report, allow_empty: bool) -> None:
    items = meta.get("items")
    if items is None or (not items and not allow_empty):
        rep.error("meta.yml", "items は 1 つ以上の並び")
        return
    if not isinstance(items, list):
        rep.error("meta.yml", "items は並び")
        return
    for i, it in enumerate(items):
        path = (it or {}).get("path")
        if not path:
            rep.error("meta.yml", f"items[{i}] に path がない")
        elif ".." in Path(path).parts or path.startswith("/"):
            rep.error("meta.yml", f"items[{i}].path ({path}) はフォルダの中の相対パスにする")
        elif not (root / path).is_file():
            rep.error("meta.yml", f"items[{i}].path ({path}) のファイルがない")
        if not (it or {}).get("label"):
            rep.warn("meta.yml", f"items[{i}] に label がない (頁では kind を出す)")


def check_publish(meta: dict, rep: Report) -> None:
    pub = meta.get("publish") or {}
    if pub.get("figures_cleared") is not True:
        rep.error("meta.yml", "publish.figures_cleared が true でない (他人の図の引用を確かめてから true にする．PUBLISHING.md)")
    if not isinstance(pub.get("notes", False), bool):
        rep.error("meta.yml", "publish.notes は true か false")
    if not meta.get("license"):
        rep.error("meta.yml", "license がない")


def check_topic_meta(root: Path, meta: dict, rep: Report) -> None:
    tid = meta.get("id")
    if not tid:
        rep.error("meta.yml", "id がない")
    elif not ID_RE.fullmatch(str(tid)):
        rep.error("meta.yml", f"id ({tid}) は英小文字・数字・ハイフンだけにする")
    elif tid != root.name:
        rep.error("meta.yml", f"id ({tid}) がフォルダ名 ({root.name}) と違う")
    if not meta.get("title"):
        rep.error("meta.yml", "title がない")
    if "editions" in meta:
        rep.error("meta.yml", "主題の meta.yml に editions を書かない (版は版のフォルダの meta.yml)")
    check_items(root, meta, rep, allow_empty=True)
    if not meta.get("items"):
        rep.warn("meta.yml", "主題の items (育てていく資料) が空")
    for it in meta.get("items") or []:
        top = Path(str((it or {}).get("path", ""))).parts[:1]
        if top and EDITION_RE.fullmatch(top[0]):
            rep.error("meta.yml", f"主題の items に版の中のファイル ({it.get('path')}) を書かない")
    check_publish(meta, rep)


def check_edition_meta(root: Path, meta: dict, rep: Report) -> None:
    ed = str(meta.get("edition", ""))
    if not EDITION_RE.fullmatch(ed):
        rep.error("meta.yml", f"edition ({ed!r}) は YYYY-MM-DD か YYYY-MM-DD-b")
    elif ed != root.name:
        rep.error("meta.yml", f"edition ({ed}) がフォルダ名 ({root.name}) と違う")
    topic = meta.get("topic")
    if not topic:
        rep.error("meta.yml", "topic がない")
    elif topic != root.parent.name:
        rep.error("meta.yml", f"topic ({topic}) が主題のフォルダ名 ({root.parent.name}) と違う")
    d = meta.get("date")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(d)):
        rep.error("meta.yml", f"date が YYYY-MM-DD でない ({d!r})")
    elif ed and str(d) != ed[:10]:
        rep.error("meta.yml", f"date ({d}) が版の名前 ({ed}) の日付と違う")
    for k in ("title", "venue"):
        if not meta.get(k):
            rep.error("meta.yml", f"{k} がない")
    if not meta.get("kind"):
        rep.warn("meta.yml", "kind (基調講演・招待講演など) がない")
    for i, r in enumerate(meta.get("revisions") or []):
        if not (r or {}).get("note") or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str((r or {}).get("date"))):
            rep.error("meta.yml", f"revisions[{i}] には date と note が要る")
    check_items(root, meta, rep, allow_empty=False)
    check_publish(meta, rep)


def check_files(root: Path, meta: dict, is_topic: bool, logos, snippets: list[str], rep: Report) -> int:
    notes_public = bool((meta.get("publish") or {}).get("notes", False))
    # 発表者ノートの文を探す PDF: 配布用 (kind: handout) と，items に無い PDF．
    # 解説文 (report-pdf など) はノートと同じ文を含むことがあるので除く
    kinds = {str((it or {}).get("path")): (it or {}).get("kind") for it in (meta.get("items") or [])}
    edition_dirs = set()
    if is_topic:
        for d in root.iterdir():
            if d.is_dir() and EDITION_RE.fullmatch(d.name):
                edition_dirs.add(d.name)
    n = 0
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if is_topic and rel.split("/", 1)[0] in edition_dirs:
            continue                                  # 版は別に調べる
        if p.is_dir() or p.name in OS_JUNK:
            continue
        n += 1
        if p.is_symlink():
            rep.error(rel, "シンボリックリンクは置かない")
            continue
        ext = p.suffix.lower()
        if ext not in ALLOWED_EXT:
            rep.error(rel, f"公開しない種類のファイル ({ext or '拡張子なし'})")
        for pat, why in FORBIDDEN_PATH:
            if pat.search(rel):
                rep.error(rel, f"パスに {why} が含まれる")
        size = p.stat().st_size
        if size > SIZE_ERROR:
            rep.error(rel, f"大きすぎる ({size / 2**20:.0f}MB．GitHub の上限は 100MB)")
        elif size > SIZE_WARN:
            rep.warn(rel, f"大きい ({size / 2**20:.0f}MB)")

        if ext in TEXT_EXT:
            text = p.read_text(encoding="utf-8", errors="replace")
            for pat, why in FORBIDDEN_TEXT:
                m = pat.search(text)
                if m:
                    rep.error(rel, f"{why}がある: {m.group(0)[:60]}")
            for name, frag in logos:
                if frag and frag in text:
                    rep.error(rel, f"禁止した画像 {name} が埋め込まれている")
            if ext == ".html":
                check_html(root, p, rel, text, notes_public, is_topic, rep)
        elif ext == ".pdf":
            look = kinds.get(rel, "handout") == "handout"
            check_pdf(p, rel, snippets if look else [], notes_public, rep)
    return n


def check_html(root: Path, p: Path, rel: str, text: str, notes_public: bool, is_topic: bool, rep: Report) -> None:
    # GitHub Pages は charset=utf-8 を付けて送るが，手元のサーバーや保存した html では
    # 文書の中の指定が頼り．無ければ誤り．先頭 1024 バイトより後ろにあるだけなら警告
    # (Quarto の embed-resources はスクリプトを <meta charset> より前に埋め込む)
    m = CHARSET_RE.search(text[:200_000])
    if not m:
        rep.error(rel, '文字コードの指定 (<meta charset="utf-8">) がない (文字化けする)')
    elif m.start() > 1024:
        rep.warn(rel, f"文字コードの指定が先頭 1024 バイトより後ろ ({m.start()} バイト目)．"
                      "Pages では問題ないが，ほかのサーバーでは文字化けすることがある")
    if not DOCTYPE_RE.match(text):
        rep.warn(rel, "<!doctype html> がない")
    if not notes_public and NOTES_RE.search(text):
        rep.error(rel, '発表者ノート (<aside class="notes">) が残っている (publish.notes: false)')
    if any(g in text[:4096] for g in GENERATORS):
        return                                        # 一覧・主題・版の頁はフォルダをまたいでよい
    for ref in REF_ATTR.findall(text):
        if not is_local_ref(ref):
            continue
        target = ref.split("#")[0].split("?")[0]
        if not target:
            continue
        t = (p.parent / target).resolve()
        try:
            inner = t.relative_to(root.resolve())
        except ValueError:
            where = "版" if not is_topic else "主題"
            rep.error(rel, f"{where}のフォルダの外を指す参照: {ref}")
            continue
        if is_topic and inner.parts and EDITION_RE.fullmatch(inner.parts[0]):
            rep.error(rel, f"主題の部分から版の中を参照しない: {ref}")
            continue
        if not t.exists():
            rep.error(rel, f"参照先がない: {ref}")


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def check_pdf(p: Path, rel: str, snippets, notes_public, rep: Report) -> None:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(p))
        text = norm("".join((pg.extract_text() or "") for pg in reader.pages))
        info = reader.metadata or {}
    except Exception as e:  # noqa: BLE001
        rep.warn(rel, f"PDF を読めなかった ({e})．発表者ノートの検査を飛ばした")
        return
    for k, v in dict(info).items():
        for pat, why in FORBIDDEN_TEXT:
            if isinstance(v, str) and pat.search(v):
                rep.error(rel, f"PDF の文書情報 {k} に{why}がある")
    if not notes_public and snippets:
        hits = [s for s in snippets if s in text]
        if hits:
            rep.error(rel, f"発表者ノートの文が載っている ({len(hits)} 箇所．例:「{hits[0][:20]}…」)．"
                           "publish.notes: false ならノートなしの配布用 PDF にする")


def check_dir(root: Path, logos, snippets, label: str) -> bool:
    """1 つのフォルダ (主題か版) を調べて結果を出す．主題なら中の版も調べる．誤りがなければ True．"""
    rep = Report()
    meta = load_meta(root, rep)
    is_topic = True
    if meta is not None:
        is_topic = "edition" not in meta
        (check_topic_meta if is_topic else check_edition_meta)(root, meta, rep)
    n = check_files(root, meta or {}, is_topic, logos, snippets, rep)
    kind = "主題" if is_topic else "版"
    for w in rep.warnings:
        print(f"  ! {label}/{w}")
    for e in rep.errors:
        print(f"  ✗ {label}/{e}")
    if rep.errors:
        print(f"✗ {kind} {label}: 誤り {len(rep.errors)} 件，警告 {len(rep.warnings)} 件 (ファイル {n} 個)")
    else:
        print(f"✓ {kind} {label}: 公開してよい (ファイル {n} 個，警告 {len(rep.warnings)} 件)")
    ok = not rep.errors
    if is_topic:
        for d in sorted(root.iterdir()):
            if d.is_dir() and EDITION_RE.fullmatch(d.name):
                ok = check_dir(d, logos, snippets, f"{label}/{d.name}") and ok
            elif d.is_dir() and re.fullmatch(r"\d{4}-.*", d.name):
                print(f"  ✗ {label}/{d.name}: 版の名前の形 (YYYY-MM-DD[-b]) でない")
                ok = False
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="主題や講演の版のフォルダを公開してよいか調べる (PUBLISHING.md)")
    ap.add_argument("dirs", nargs="+", type=Path, help="主題か版のフォルダ (meta.yml のある所)")
    ap.add_argument("--forbid-assets", action="append", type=Path, default=[],
                    help="公開しない画像の置き場 (例 _quarto/local)．中の画像が埋め込まれていないか照合する")
    ap.add_argument("--notes-snippets", type=Path,
                    help="発表者ノートの断片 (1 行に 1 つ．publish.mk の stage が作る)．PDF に載っていないか調べる")
    a = ap.parse_args()

    unreadable: list[str] = []
    logos = logo_fingerprints(a.forbid_assets, unreadable)
    if unreadable:
        for u in unreadable:
            print(f"✗ 禁止する画像を読めない (照合できないので止める): {u}")
        return 1
    if a.forbid_assets:
        print(f"  (禁止する画像 {len(logos)} 件と照合)" if logos
              else "! --forbid-assets に画像が見つからなかった (ロゴの照合をしていない)")
    snippets: list[str] = []
    if a.notes_snippets and a.notes_snippets.exists():
        snippets = [norm(s) for s in a.notes_snippets.read_text(encoding="utf-8").splitlines() if len(norm(s)) >= 12]

    ok = True
    for root in a.dirs:
        root = root.resolve() if root.name in ("", ".") else root
        if not root.is_dir():
            print(f"✗ {root}: フォルダがない")
            ok = False
            continue
        ok = check_dir(root, logos, snippets, root.name) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
