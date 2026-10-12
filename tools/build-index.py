#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""build-index.py — meta.yml から一覧・主題・版の頁 (index.html) を作る．

使い方 (talks/ で):
    uv run --script tools/build-index.py            # 下の 3 種類をすべて作り直す
    uv run --script tools/build-index.py /path/to/talks

作るもの:
    index.html                    主題の一覧 (最新の版の日付の新しい順)
    <主題>/index.html             主題の頁: 概要，育てていく資料，講演の版の一覧 (新しい順)
    <主題>/<版>/index.html        版の頁: その講演の資料，最新の資料への案内，訂正の記録

サイト全体の題などは site.yml．主題は <主題>/meta.yml (edition が無いもの)，
版は <主題>/<YYYY-MM-DD[-b]>/meta.yml (edition があるもの)．
作る頁には generator の印を付ける (check.py はこの頁の参照の検査をしない)．
"""
from __future__ import annotations

import datetime as dt
import html
import re
import sys
from pathlib import Path

import yaml

GENERATOR = "talks/tools/build-index.py"
EDITION_RE = re.compile(r"\d{4}-\d{2}-\d{2}(?:-[a-z])?")
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
main{max-width:52rem;margin:0 auto;padding:2.5rem 1rem 4rem}
a{color:var(--accent)}
nav.crumb{font-size:.85rem;color:var(--muted);margin-bottom:1.2rem}
nav.crumb a{color:inherit}
header h1{font-size:1.6rem;margin:0 0 .25rem;line-height:1.35}
header p{margin:0;color:var(--muted)}
h2.sec{font-size:1rem;margin:2rem 0 .2rem;color:var(--muted);font-weight:600;letter-spacing:.02em}
article{border-top:1px solid var(--line);padding:1.3rem 0}
article h2,article h3{font-size:1.2rem;margin:0;line-height:1.4}
article h3{font-size:1.05rem}
article h2 a,article h3 a{color:inherit;text-decoration:none}
article h2 a:hover,article h3 a:hover{color:var(--accent)}
.sub{margin:.15rem 0 0;color:var(--muted)}
.ev{margin:.4rem 0 0;font-size:.9rem;color:var(--muted)}
time{font-variant-numeric:tabular-nums}
.abs{margin:.8rem 0 0}
.links{display:flex;flex-wrap:wrap;gap:.5rem;margin:.7rem 0 0;padding:0;list-style:none}
.links a{display:inline-block;padding:.2rem .7rem;border-radius:999px;background:var(--chip);color:var(--accent);text-decoration:none;font-size:.9rem}
.links a:hover{outline:1px solid var(--accent)}
.note{margin:1.2rem 0 0;padding:.8rem 1rem;border-left:3px solid var(--accent);background:var(--chip);font-size:.92rem}
.small{font-size:.82rem;color:var(--muted)}
ul.rev{margin:.3rem 0 0;padding-left:1.2rem;font-size:.9rem}
footer{border-top:1px solid var(--line);margin-top:2rem;padding-top:1rem;font-size:.82rem;color:var(--muted)}
footer a{color:inherit}
"""


def e(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def load(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def label_of(it: dict) -> str:
    return it.get("label") or KIND_LABEL.get(it.get("kind"), it.get("kind", "資料"))


def chips(items, prefix: str = "") -> str:
    li = [f'<li><a href="{e(prefix + str(it["path"]))}">{e(label_of(it))}</a></li>'
          for it in items or [] if it and it.get("path") is not None]
    return '<ul class="links">' + "".join(li) + "</ul>" if li else ""


def event_line(m: dict) -> str:
    parts = [f'<time datetime="{e(m.get("date"))}">{e(m.get("date"))}</time>']
    venue = e(m.get("venue"))
    if m.get("event_url") and venue:
        venue = f'<a href="{e(m["event_url"])}">{venue}</a>'
    if venue:
        parts.append(venue)
    if m.get("kind"):
        parts.append(e(m["kind"]))
    return "　".join(parts)


def license_line(meta: dict) -> str:
    lic = LICENSES.get(meta.get("license"))
    return f'資料: <a href="{lic[1]}">{lic[0]}</a>' if lic else (f"資料: {e(meta['license'])}" if meta.get("license") else "")


def page(title: str, body: list[str], lang: str, site: dict, depth: int) -> str:
    foot = site.get("footer", "")
    return f"""<!doctype html>
<html lang="{e(lang)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{GENERATOR}">
<title>{e(title)}</title>
<style>{CSS}</style>
</head>
<body>
<main>
{chr(10).join(body)}
<footer>{foot}<br>この頁は tools/build-index.py が meta.yml から作る ({dt.date.today().isoformat()})．</footer>
</main>
</body>
</html>
"""


def first(*xs):
    for x in xs:
        if x:
            return x
    return None


# ------------------------------------------------------------------ 集める
def collect(root: Path) -> list[dict]:
    topics = []
    for mp in sorted(root.glob("*/meta.yml")):
        meta = load(mp)
        if "edition" in meta:
            continue
        tdir = mp.parent
        eds = []
        for ep in sorted(tdir.glob("*/meta.yml")):
            if EDITION_RE.fullmatch(ep.parent.name):
                em = load(ep)
                if "edition" in em:
                    em["_name"] = ep.parent.name
                    eds.append(em)
        eds.sort(key=lambda m: (str(m.get("date", "")), m["_name"]), reverse=True)
        topics.append({"id": tdir.name, "meta": meta, "editions": eds})
    topics.sort(key=lambda t: str(first(t["editions"][0].get("date") if t["editions"] else None,
                                        t["meta"].get("updated"), "")), reverse=True)
    return topics


# ------------------------------------------------------------------ 頁
def top_page(root: Path, site: dict, topics: list[dict]) -> None:
    title = site.get("title", "講演資料")
    body = [f'<header><h1>{e(title)}</h1>']
    if site.get("description"):
        body.append(f'<p>{e(site["description"])}</p>')
    body.append("</header>")
    for t in topics:
        m, tid = t["meta"], t["id"]
        out = [f'<article id="{e(tid)}">', f'<h2><a href="{e(tid)}/">{e(m.get("title"))}</a></h2>']
        if m.get("subtitle"):
            out.append(f'<p class="sub">{e(m["subtitle"])}</p>')
        if t["editions"]:
            latest = t["editions"][0]
            n = len(t["editions"])
            out.append(f'<p class="ev">最新の講演: {event_line(latest)}'
                       + (f'　(ほか {n - 1} 回)' if n > 1 else "") + "</p>")
            links = [{"path": f'{latest["_name"]}/', "label": "最新の講演の資料"}]
        else:
            links = []
        links.append({"path": "", "label": "解説・デモ・講演の一覧"})
        out.append(chips(links, f"{tid}/"))
        out.append("</article>")
        body.append("\n".join(out))
    if not topics:
        body.append("<article><p>まだ講演はない．</p></article>")
    (root / "index.html").write_text(page(title, body, site.get("lang", "ja"), site, 0), encoding="utf-8")


def topic_page(root: Path, site: dict, t: dict) -> None:
    m, tid = t["meta"], t["id"]
    body = [f'<nav class="crumb"><a href="../">{e(site.get("title", "講演資料"))}</a></nav>',
            f'<header><h1>{e(m.get("title"))}</h1>']
    if m.get("subtitle"):
        body.append(f'<p>{e(m["subtitle"])}</p>')
    body.append("</header>")
    if m.get("abstract"):
        body.append(f'<p class="abs">{e(str(m["abstract"]).strip())}</p>')
    if m.get("items"):
        body.append('<h2 class="sec">最新の資料</h2>')
        body.append(chips(m["items"]))
        body.append(f'<p class="small">更新 {e(m.get("updated"))}　{license_line(m)}</p>')
    body.append('<h2 class="sec">講演</h2>')
    if not t["editions"]:
        body.append("<p>まだ講演の版はない．</p>")
    for ed in t["editions"]:
        name = ed["_name"]
        out = [f'<article id="{e(name)}">',
               f'<h3><a href="{e(name)}/">{e(ed.get("title") or m.get("title"))}</a></h3>']
        if ed.get("subtitle") and ed.get("subtitle") != m.get("subtitle"):
            out.append(f'<p class="sub">{e(ed["subtitle"])}</p>')
        out.append(f'<p class="ev">{event_line(ed)}'
                   + ('　(訂正あり)' if ed.get("revisions") else "") + "</p>")
        out.append(chips(ed.get("items"), f"{name}/"))
        out.append("</article>")
        body.append("\n".join(out))
    (root / tid / "index.html").write_text(
        page(f'{m.get("title")} — {site.get("title", "講演資料")}', body, m.get("lang", site.get("lang", "ja")), site, 1),
        encoding="utf-8")


def edition_page(root: Path, site: dict, t: dict, ed: dict) -> None:
    m, tid, name = t["meta"], t["id"], ed["_name"]
    title = ed.get("title") or m.get("title")
    body = [f'<nav class="crumb"><a href="../../">{e(site.get("title", "講演資料"))}</a> › '
            f'<a href="../">{e(m.get("title"))}</a></nav>',
            f'<header><h1>{e(title)}</h1>']
    sub = ed.get("subtitle") or m.get("subtitle")
    if sub:
        body.append(f'<p>{e(sub)}</p>')
    body.append(f'<p class="ev">{event_line(ed)}</p>')
    body.append("</header>")
    body.append('<h2 class="sec">この講演の資料</h2>')
    body.append(chips(ed.get("items")))
    note = (f'この頁の資料は講演の時点のまま固定している．'
            f'育てている最新の解説・デモは <a href="../">{e(m.get("title"))}</a> の頁にある．')
    body.append(f'<p class="note">{note}</p>')
    if m.get("items"):
        body.append(chips(m["items"], "../"))
    if ed.get("revisions"):
        body.append('<h2 class="sec">訂正の記録</h2><ul class="rev">'
                    + "".join(f'<li><time>{e(r.get("date"))}</time>　{e(r.get("note"))}</li>' for r in ed["revisions"])
                    + "</ul>")
    body.append(f'<p class="small">公開 {e(ed.get("published"))}　{license_line(ed)}</p>')
    (root / tid / name / "index.html").write_text(
        page(f'{title} ({ed.get("date")}) — {site.get("title", "講演資料")}', body,
             m.get("lang", site.get("lang", "ja")), site, 2),
        encoding="utf-8")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    site = load(root / "site.yml") if (root / "site.yml").exists() else {}
    topics = collect(root)
    top_page(root, site, topics)
    n_ed = 0
    for t in topics:
        topic_page(root, site, t)
        for ed in t["editions"]:
            edition_page(root, site, t, ed)
            n_ed += 1
    print(f"→ {root}/index.html ほか (主題 {len(topics)} 件，講演の版 {n_ed} 件)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
