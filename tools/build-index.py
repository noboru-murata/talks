#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""build-index.py — 各講演の meta.yml から講演の一覧 (index.html) を作る．

使い方 (talks/ で):
    uv run --script tools/build-index.py            # → index.html
    uv run --script tools/build-index.py /path/to/talks

サイト全体の題などは site.yml．講演は <id>/meta.yml を持つフォルダ．
並びは最新の発表日 (events の先頭) の新しい順．
"""
from __future__ import annotations

import datetime as dt
import html
import sys
from pathlib import Path

import yaml

LICENSES = {
    "CC-BY-NC-4.0": ("CC BY-NC 4.0", "https://creativecommons.org/licenses/by-nc/4.0/deed.ja"),
    "CC-BY-4.0": ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/deed.ja"),
}
KIND_LABEL = {"slides": "スライド", "handout": "配布用 PDF", "report": "解説", "report-pdf": "解説 (PDF)",
              "demo": "デモ", "video": "動画", "code": "コード"}

CSS = """
:root{--bg:#fbfbf8;--fg:#1f2a28;--muted:#5f6b68;--line:#d9dfdc;--accent:#2f7d6b;--chip:#eaf3f0}
@media (prefers-color-scheme:dark){:root{--bg:#141917;--fg:#e4ebe8;--muted:#9aa7a3;--line:#2c3532;--accent:#6cc3ab;--chip:#1f2b27}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.7 system-ui,-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif}
main{max-width:52rem;margin:0 auto;padding:3rem 1rem 4rem}
header h1{font-size:1.6rem;margin:0 0 .25rem}
header p{margin:0;color:var(--muted)}
article{border-top:1px solid var(--line);padding:1.5rem 0}
article h2{font-size:1.25rem;margin:0;line-height:1.4}
article h2 a{color:inherit;text-decoration:none}
article h2 a:hover{color:var(--accent)}
.sub{margin:.15rem 0 0;color:var(--muted)}
.ev{margin:.5rem 0 0;font-size:.9rem;color:var(--muted)}
.ev time{font-variant-numeric:tabular-nums}
.abs{margin:.6rem 0 0;font-size:.95rem}
.links{display:flex;flex-wrap:wrap;gap:.5rem;margin:.8rem 0 0;padding:0;list-style:none}
.links a{display:inline-block;padding:.2rem .7rem;border-radius:999px;background:var(--chip);color:var(--accent);text-decoration:none;font-size:.9rem}
.links a:hover{outline:1px solid var(--accent)}
.lic{margin:.6rem 0 0;font-size:.8rem;color:var(--muted)}
footer{border-top:1px solid var(--line);padding-top:1rem;font-size:.85rem;color:var(--muted)}
footer a,.lic a{color:inherit}
"""


def e(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def first_date(meta: dict) -> str:
    ev = meta.get("events") or [{}]
    return str((ev[0] or {}).get("date", ""))


def talk_html(tid: str, meta: dict) -> str:
    items = meta.get("items") or []
    main_link = next((it["path"] for it in items if it.get("kind") == "slides"), items[0]["path"] if items else "")
    out = [f'<article id="{e(tid)}">']
    out.append(f'<h2><a href="{e(tid)}/{e(main_link)}">{e(meta.get("title"))}</a></h2>')
    if meta.get("subtitle"):
        out.append(f'<p class="sub">{e(meta["subtitle"])}</p>')
    evs = []
    for ev in meta.get("events") or []:
        parts = [f'<time datetime="{e(ev.get("date"))}">{e(ev.get("date"))}</time>']
        if ev.get("venue"):
            parts.append(e(ev["venue"]))
        if ev.get("kind"):
            parts.append(e(ev["kind"]))
        evs.append("　".join(parts))
    if evs:
        out.append('<p class="ev">' + "<br>".join(evs) + "</p>")
    if meta.get("abstract"):
        out.append(f'<p class="abs">{e(str(meta["abstract"]).strip())}</p>')
    out.append('<ul class="links">')
    for it in items:
        label = it.get("label") or KIND_LABEL.get(it.get("kind"), it.get("kind", "資料"))
        out.append(f'<li><a href="{e(tid)}/{e(it["path"])}">{e(label)}</a></li>')
    out.append("</ul>")
    lic = LICENSES.get(meta.get("license"))
    if lic:
        out.append(f'<p class="lic">資料: <a href="{lic[1]}">{lic[0]}</a>'
                   + (f'　更新 {e(meta["updated"])}' if meta.get("updated") else "") + "</p>")
    out.append("</article>")
    return "\n".join(out)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    site = {}
    if (root / "site.yml").exists():
        site = yaml.safe_load((root / "site.yml").read_text(encoding="utf-8")) or {}
    talks = []
    for mp in sorted(root.glob("*/meta.yml")):
        meta = yaml.safe_load(mp.read_text(encoding="utf-8")) or {}
        talks.append((mp.parent.name, meta))
    talks.sort(key=lambda t: first_date(t[1]), reverse=True)

    title = site.get("title", "講演資料")
    body = [f'<header><h1>{e(title)}</h1>']
    if site.get("description"):
        body.append(f'<p>{e(site["description"])}</p>')
    body.append("</header>")
    body += [talk_html(tid, m) for tid, m in talks]
    if not talks:
        body.append("<article><p>まだ講演はない．</p></article>")
    foot = site.get("footer", "")
    body.append(f"<footer>{foot}<br>この一覧は tools/build-index.py が各講演の meta.yml から作る "
                f"({dt.date.today().isoformat()})．</footer>")

    page = f"""<!doctype html>
<html lang="{e(site.get('lang', 'ja'))}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<style>{CSS}</style>
</head>
<body>
<main>
{chr(10).join(body)}
</main>
</body>
</html>
"""
    (root / "index.html").write_text(page, encoding="utf-8")
    print(f"→ {root / 'index.html'} (講演 {len(talks)} 件)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
