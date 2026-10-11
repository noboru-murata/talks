#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6", "pypdf>=4"]
# ///
"""check.py — 講演のフォルダ (公開する形に並べたもの) を公開してよいか調べる．

使い方:
    uv run --script tools/check.py piml/                      # 公開済みのフォルダを調べ直す
    uv run --script tools/check.py _publish/piml \\
        --forbid-assets _quarto/local --notes-snippets _publish/piml.notes.txt
                                                             # 講演側の make publish から (publish.mk)

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
SIZE_WARN = 50 * 2**20
SIZE_ERROR = 95 * 2**20      # GitHub の上限は 1 ファイル 100MB

REQUIRED_META = ["id", "title", "events", "items", "license", "publish"]


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


def logo_fingerprints(dirs: list[Path], unreadable: list[str]) -> list[tuple[str, str, str]]:
    """禁止する画像の (名前, base64 の断片, 生のバイト列の断片)．埋め込まれていれば見つかる．"""
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
                b64 = base64.b64encode(raw).decode()
                # data URI はファイルの先頭から符号化されるので，途中の断片で照合できる
                # (先頭は PNG の見出しなどで他の画像と共通なので避ける)
                frag = b64[120:200]
                fps.append((p.name, frag, ""))
    return fps


def check_meta(root: Path, rep: Report) -> dict:
    mp = root / "meta.yml"
    if not mp.exists():
        rep.error("meta.yml", "ない")
        return {}
    try:
        meta = yaml.safe_load(mp.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        rep.error("meta.yml", f"YAML として読めない: {e}")
        return {}
    for k in REQUIRED_META:
        if k not in meta:
            rep.error("meta.yml", f"{k} がない")
    if meta.get("id") and meta["id"] != root.name and not root.name.startswith("_"):
        # 仮置き場 (_publish/<id>) でも公開側 (talks/<id>) でもフォルダ名と一致させる
        rep.error("meta.yml", f"id ({meta['id']}) がフォルダ名 ({root.name}) と違う")
    if meta.get("id") and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(meta["id"])):
        rep.error("meta.yml", f"id ({meta['id']}) は英小文字・数字・ハイフンだけにする")
    ev = meta.get("events")
    if ev is not None:
        if not isinstance(ev, list) or not ev:
            rep.error("meta.yml", "events は 1 つ以上の並び")
        else:
            for i, e in enumerate(ev):
                d = (e or {}).get("date")
                if not isinstance(d, (dt.date, str)) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(d)):
                    rep.error("meta.yml", f"events[{i}].date が YYYY-MM-DD でない ({d!r})")
    items = meta.get("items") or []
    if not isinstance(items, list) or not items:
        rep.error("meta.yml", "items は 1 つ以上の並び")
        items = []
    for i, it in enumerate(items):
        path = (it or {}).get("path")
        if not path:
            rep.error("meta.yml", f"items[{i}] に path がない")
        elif ".." in Path(path).parts or path.startswith("/"):
            rep.error("meta.yml", f"items[{i}].path ({path}) はフォルダの中の相対パスにする")
        elif not (root / path).is_file():
            rep.error("meta.yml", f"items[{i}].path ({path}) のファイルがない")
        if not (it or {}).get("label"):
            rep.warn("meta.yml", f"items[{i}] に label がない (一覧ページでは kind を出す)")
    pub = meta.get("publish") or {}
    if pub.get("figures_cleared") is not True:
        rep.error("meta.yml", "publish.figures_cleared が true でない (他人の図の引用を確かめてから true にする．PUBLISHING.md)")
    if not isinstance(pub.get("notes", False), bool):
        rep.error("meta.yml", "publish.notes は true か false")
    return meta


def check_files(root: Path, meta: dict, logos, snippets: list[str], rep: Report) -> None:
    notes_public = bool((meta.get("publish") or {}).get("notes", False))
    # 発表者ノートの文を探す PDF: 配布用 (kind: handout) と，items に無い PDF．
    # 解説文 (report-pdf など) はノートと同じ文を含むことがあるので除く
    kinds = {str((it or {}).get("path")): (it or {}).get("kind") for it in (meta.get("items") or [])}
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        rel = p.relative_to(root).as_posix()
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
            for name, frag, _ in logos:
                if frag and frag in text:
                    rep.error(rel, f"禁止した画像 {name} が埋め込まれている")
            if ext == ".html":
                if not notes_public and NOTES_RE.search(text):
                    rep.error(rel, '発表者ノート (<aside class="notes">) が残っている (publish.notes: false)')
                for ref in REF_ATTR.findall(text):
                    if not is_local_ref(ref):
                        continue
                    target = ref.split("#")[0].split("?")[0]
                    if not target:
                        continue
                    t = (p.parent / target).resolve()
                    try:
                        t.relative_to(root.resolve())
                    except ValueError:
                        rep.error(rel, f"講演のフォルダの外を指す参照: {ref}")
                        continue
                    if not t.exists():
                        rep.error(rel, f"参照先がない: {ref}")
        elif ext == ".pdf":
            look = kinds.get(rel, "handout") == "handout"
            check_pdf(p, rel, logos, snippets if look else [], notes_public, rep)


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def check_pdf(p: Path, rel: str, logos, snippets, notes_public, rep: Report) -> None:
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


def main() -> int:
    ap = argparse.ArgumentParser(description="講演のフォルダを公開してよいか調べる (PUBLISHING.md)")
    ap.add_argument("dirs", nargs="+", type=Path, help="講演のフォルダ (meta.yml のある所)")
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
    snippets: list[str] = []
    if a.notes_snippets and a.notes_snippets.exists():
        snippets = [norm(s) for s in a.notes_snippets.read_text(encoding="utf-8").splitlines() if len(norm(s)) >= 12]

    failed = False
    for root in a.dirs:
        rep = Report()
        if not root.is_dir():
            print(f"✗ {root}: フォルダがない")
            failed = True
            continue
        meta = check_meta(root, rep)
        check_files(root, meta, logos, snippets, rep)
        for w in rep.warnings:
            print(f"  ! {root.name}/{w}")
        for e in rep.errors:
            print(f"  ✗ {root.name}/{e}")
        n = sum(1 for _ in root.rglob("*") if _.is_file())
        extra = f"．禁止画像 {len(logos)} 件と照合" if logos else ""
        if rep.errors:
            print(f"✗ {root}: 誤り {len(rep.errors)} 件，警告 {len(rep.warnings)} 件 (ファイル {n} 個{extra})")
            failed = True
        else:
            print(f"✓ {root}: 公開してよい (ファイル {n} 個，警告 {len(rep.warnings)} 件{extra})")
    if a.forbid_assets and not logos:
        print("! --forbid-assets に画像が見つからなかった (ロゴの照合をしていない)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
