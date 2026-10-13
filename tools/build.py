#!/usr/bin/env python
"""Build the Galaxy XR Forge index.

    catalog.json  ->  README.md  +  docs/index.html

Usage:
    python tools/build.py           validate, then write the generated files
    python tools/build.py --check   validate catalog.json only

Rules:
    - catalog.json is the single source of truth. Never hand-edit README.md
      or docs/index.html; edit the catalog and rerun this script.
    - Dependency-free: Python 3.10+, stdlib only, runs on any host.
"""

import html
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "catalog.json"
README_PATH = ROOT / "README.md"
SITE_PATH = ROOT / "docs" / "index.html"

REPO_URL = "https://github.com/AngelDark92/GalaxyXR-Forge"
TAGLINE = (
    "Every community repo for the Samsung Galaxy XR (SM-I610) in one place: "
    "root tools, KernelSU modules, streaming drivers, app patches, ports and diagnostics."
)

# ---------------------------------------------------------------------------
# catalog loading and validation
# ---------------------------------------------------------------------------


def load_catalog():
    with CATALOG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def validate(cat):
    errors = []
    seen_ids = set()
    seen_repos = set()
    groups = cat.get("groups") or []
    if not groups:
        errors.append("catalog has no groups")
    for g in groups:
        gid = g.get("id", "")
        if not gid or not all(c.islower() or c.isdigit() or c == "-" for c in gid):
            errors.append(f"bad group id: {gid!r}")
        if gid in seen_ids:
            errors.append(f"duplicate group id: {gid}")
        seen_ids.add(gid)
        for key in ("title", "icon", "hue", "blurb"):
            if not g.get(key):
                errors.append(f"group {gid}: missing {key}")
        if not g.get("repos"):
            errors.append(f"group {gid}: no repos")
        for r in g.get("repos", []):
            repo = r.get("repo", "")
            if not repo or repo.count("/") != 1:
                errors.append(f"group {gid}: bad repo field {repo!r}")
            if repo in seen_repos:
                errors.append(f"duplicate repo: {repo}")
            seen_repos.add(repo)
            if not str(r.get("url", "")).startswith("https://github.com/") or not str(r.get("url", "")).endswith(repo):
                errors.append(f"{repo}: url must be https://github.com/<repo>")
            about = r.get("about", "")
            if not about:
                errors.append(f"{repo}: missing about")
            elif len(about) > 160:
                errors.append(f"{repo}: about too long ({len(about)} chars)")
    return errors, seen_repos


# ---------------------------------------------------------------------------
# README
# ---------------------------------------------------------------------------


def render_readme(cat):
    groups = cat["groups"]
    total = sum(len(g["repos"]) for g in groups)
    updated = cat.get("updated", date.today().isoformat())
    L = []
    A = L.append
    A('<div align="center">')
    A("")
    A("# ⚡ Galaxy XR Forge")
    A("")
    A(f"**{TAGLINE}**")
    A("")
    A(f"[![community repos](https://img.shields.io/badge/community_repos-{total}-orange?style=flat-square)](#catalog)")
    A("[![PRs welcome](https://img.shields.io/badge/PRs-welcome-2ea44f?style=flat-square)](#add-your-repo)")
    A(f"[![last commit](https://img.shields.io/github/last-commit/AngelDark92/GalaxyXR-Forge?style=flat-square)]({REPO_URL}/commits/main)")
    A("")
    nav = " · ".join(f'[{g["icon"]} {g["title"]}](#{g["id"]})' for g in groups)
    A(f"<sub>{nav}</sub>")
    A("")
    A("</div>")
    A("")
    A("---")
    A("")
    A(
        f"Community-maintained index of projects built for the **Samsung Galaxy XR** "
        f"(`SM-I610`, Android XR): root and kernel tooling, KernelSU modules, PC VR "
        f"streaming drivers, patched and ported apps, emulation, and diagnostics. "
        f"Curated `{updated}` — {total} repos in {len(groups)} groups."
    )
    A("")
    A('<a id="catalog"></a>')
    A("")
    for g in groups:
        A(f'<a id="{g["id"]}"></a>')
        A("")
        A(f'## {g["icon"]} {g["title"]}')
        A("")
        A(f'> {g["blurb"]}')
        A("")
        A("| Repository | What it does |")
        A("| --- | --- |")
        for r in g["repos"]:
            badges = [f'![stars](https://img.shields.io/github/stars/{r["repo"]}?style=flat-square)']
            if r.get("release"):
                badges.append(
                    f'![release](https://img.shields.io/github/v/release/{r["repo"]}?style=flat-square&label=release)'
                )
            name = f'**[{r["repo"]}]({r["url"]})**<br>{" ".join(badges)}'
            A(f'| {name} | {r["about"]} |')
        A("")
    A("---")
    A("")
    A("## Add your repo")
    A("")
    A("1. Add an entry to [`catalog.json`](catalog.json) — the single source of truth — in the right group.")
    A("2. Regenerate the index: `python tools/build.py` (rewrites this README and the [docs site](docs/)).")
    A("3. Verify `python tools/check-links.py` passes, then open a PR.")
    A("")
    A("Keep descriptions to one factual line. See [`.agents/skills/`](.agents/skills/) for the full procedure.")
    A("")
    A("## For agents")
    A("")
    A(
        "This repo is agent-ready. Start with [`AGENTS.md`](AGENTS.md); "
        "[`catalog.json`](catalog.json) is the machine-readable index; "
        "[`.agents/skills/`](.agents/skills/) maps every Galaxy XR repo and its local checkout."
    )
    A("")
    A("## Notes")
    A("")
    A("- Unofficial community hub — not affiliated with Samsung. Each catalogued project keeps its own license.")
    A("- Rooting and module installation carry risk; read the owning project's docs first.")
    A("- No game files, firmware dumps or proprietary binaries are distributed here.")
    A("")
    A(f'<div align="center"><sub>Curated {updated} · {total} repos</sub></div>')
    A("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# site
# ---------------------------------------------------------------------------


def render_chips(cat):
    total = sum(len(g["repos"]) for g in cat["groups"])
    chips = [
        f'<button type="button" class="chip is-active" data-group="all" style="--hue:#f97316">'
        f'<span class="dot"></span>All <b>{total}</b></button>'
    ]
    for g in cat["groups"]:
        chips.append(
            f'<button type="button" class="chip" data-group="{g["id"]}" style="--hue:{g["hue"]}">'
            f'<span class="dot"></span>{g["icon"]} {html.escape(g["title"])} <b>{len(g["repos"])}</b></button>'
        )
    return "\n        ".join(chips)


def render_sections(cat):
    out = []
    for g in cat["groups"]:
        cards = []
        for r in g["repos"]:
            owner, name = r["repo"].split("/")
            badges = [
                f'<img src="https://img.shields.io/github/stars/{r["repo"]}?style=flat-square" '
                f'alt="GitHub stars" loading="lazy">'
            ]
            if r.get("release"):
                badges.append(
                    f'<img src="https://img.shields.io/github/v/release/{r["repo"]}?style=flat-square&label=release" '
                    f'alt="latest release" loading="lazy">'
                )
            links = [f'<a href="{r["url"]}" target="_blank" rel="noopener">GitHub</a>']
            if r.get("release"):
                links.append(f'<a href="{r["url"]}/releases" target="_blank" rel="noopener">Releases</a>')
            hay = " ".join(
                [r["repo"], r.get("about", ""), r.get("license") or ""] + list(r.get("tags", []))
            ).lower()
            cards.append(
                f'<article class="card" data-group="{g["id"]}" data-text="{html.escape(hay, quote=True)}">'
                f'<div class="card-top"><h3><a href="{r["url"]}" target="_blank" rel="noopener">'
                f'<span class="owner">{owner}/</span>{name}</a></h3>'
                f'<div class="badges">{"".join(badges)}</div></div>'
                f'<p class="about">{html.escape(r["about"])}</p>'
                f'<div class="card-foot"><span class="license">{html.escape(r.get("license") or "")}</span>'
                f'<span class="links">{"".join(links)}</span></div>'
                f"</article>"
            )
        out.append(
            f'<section class="group" id="{g["id"]}" style="--hue:{g["hue"]}">'
            f'<div class="group-head"><h2><span class="dot"></span>{g["icon"]} {html.escape(g["title"])}</h2>'
            f'<p class="blurb">{html.escape(g["blurb"])}</p></div>'
            f'<div class="cards">{"".join(cards)}</div>'
            f"</section>"
        )
    return "\n  ".join(out)


SITE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Galaxy XR Forge — community repos for the Samsung Galaxy XR (SM-I610)</title>
<meta name="description" content="__TAGLINE__">
<meta name="theme-color" content="#0a0e14">
<meta property="og:title" content="Galaxy XR Forge">
<meta property="og:description" content="__TAGLINE__">
<meta property="og:type" content="website">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%230a0e14'/%3E%3Cpath d='M18 4 8 18h6l-2 10L24 13h-6z' fill='%23f97316'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#0a0e14; --bg-2:#0d131c; --card:#101822; --line:#1d2836; --line-2:#273546;
  --ink:#e9eff7; --muted:#8fa1b6; --dim:#64748b;
  --accent:#f97316; --accent-2:#fbbf24;
  --font-sans:'IBM Plex Sans',system-ui,-apple-system,sans-serif;
  --font-mono:'IBM Plex Mono',ui-monospace,'Cascadia Mono',monospace;
  --font-disp:'Space Grotesk',var(--font-sans);
}
*,*::before,*::after{box-sizing:border-box}
html{scroll-behavior:smooth}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 var(--font-sans);-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
.skip{position:absolute;left:-9999px;top:0;background:var(--accent);color:#0a0e14;padding:8px 12px;border-radius:0 0 8px 0;z-index:60}
.skip:focus{left:0}
.wrap{max-width:1120px;margin:0 auto;padding:0 22px}
.hero{position:relative;overflow:hidden;border-bottom:1px solid var(--line);
  background:
    radial-gradient(900px 380px at 12% -10%, rgba(249,115,22,.14), transparent 60%),
    radial-gradient(700px 300px at 88% -20%, rgba(56,189,248,.10), transparent 60%),
    var(--bg);
}
.hero::before{content:"";position:absolute;inset:0;pointer-events:none;
  background-image:linear-gradient(rgba(148,163,184,.05) 1px,transparent 1px),
    linear-gradient(90deg,rgba(148,163,184,.05) 1px,transparent 1px);
  background-size:44px 44px;
  mask-image:linear-gradient(180deg,rgba(0,0,0,.9),transparent 85%);
  -webkit-mask-image:linear-gradient(180deg,rgba(0,0,0,.9),transparent 85%);
}
.hero .wrap{position:relative;padding-top:64px;padding-bottom:38px}
.kicker{font:500 12px var(--font-mono);letter-spacing:.22em;text-transform:uppercase;color:var(--accent);margin:0 0 14px}
h1{font:700 clamp(2.3rem,5.4vw,3.5rem)/1.05 var(--font-disp);letter-spacing:-.02em;margin:0 0 14px}
h1 .accent{background:linear-gradient(90deg,var(--accent),var(--accent-2));-webkit-background-clip:text;background-clip:text;color:transparent}
.tagline{max-width:680px;color:var(--muted);font-size:16.5px;margin:0 0 28px}
.stats{display:flex;flex-wrap:wrap}
.stat{padding:0 24px;border-left:1px solid var(--line-2)}
.stat:first-child{padding-left:0;border-left:0}
.stat b{display:block;font:600 22px var(--font-mono);color:var(--ink)}
.stat span{font:12px var(--font-mono);color:var(--dim);text-transform:uppercase;letter-spacing:.08em}
.filters{position:sticky;top:0;z-index:30;background:rgba(10,14,20,.97);border-bottom:1px solid var(--line)}
.filters-inner{max-width:1120px;margin:0 auto;padding:12px 22px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
#q{flex:1 1 240px;min-width:200px;background:var(--bg-2);border:1px solid var(--line-2);color:var(--ink);border-radius:10px;padding:10px 14px;font:14px var(--font-sans);outline:none}
#q:focus{border-color:var(--accent)}
#q::placeholder{color:var(--dim)}
.chips{display:flex;gap:8px;flex-wrap:wrap}
.chip{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--line-2);background:transparent;color:var(--muted);border-radius:999px;padding:7px 13px;font:500 12.5px var(--font-mono);cursor:pointer;min-height:34px}
.chip .dot{width:8px;height:8px;border-radius:50%;background:var(--hue,var(--line-2));flex:none}
.chip b{font-weight:500;color:var(--dim)}
.chip:hover{border-color:var(--muted);color:var(--ink)}
.chip.is-active{border-color:var(--accent);color:var(--ink);background:rgba(249,115,22,.10)}
main{padding:34px 0 6px}
.group{max-width:1120px;margin:0 auto 42px;padding:0 22px}
.group-head h2{display:flex;align-items:center;gap:10px;font:600 1.35rem var(--font-disp);margin:0 0 6px}
.group-head .dot{width:10px;height:10px;border-radius:3px;background:var(--hue);flex:none}
.blurb{color:var(--muted);margin:0 0 18px;font-size:14.5px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
.card{display:flex;flex-direction:column;gap:10px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 16px 12px;transition:border-color .15s ease,transform .15s ease,box-shadow .15s ease}
.card:hover{border-color:var(--hue);transform:translateY(-2px);box-shadow:0 14px 34px -22px #000}
.card-top{display:flex;align-items:flex-start;gap:10px;justify-content:space-between}
.card h3{font:600 16px/1.3 var(--font-disp);margin:0}
.card h3 .owner{font:400 13px var(--font-mono);color:var(--dim)}
.card h3 a:hover{color:var(--accent-2)}
.badges{display:flex;flex-direction:column;align-items:flex-end;gap:4px;flex:none}
.badges img{height:20px;display:block}
.card .about{color:var(--muted);font-size:13.5px;margin:0;flex:1}
.card-foot{display:flex;align-items:center;gap:10px;font:11.5px var(--font-mono);color:var(--dim);padding-top:9px;border-top:1px solid var(--line)}
.card-foot .links{margin-left:auto;display:flex;gap:12px}
.card-foot a{color:var(--muted);font:500 12px var(--font-mono)}
.card-foot a:hover{color:var(--accent)}
.empty{max-width:1120px;margin:0 auto;padding:0 22px 30px;color:var(--muted);font-style:italic}
footer{border-top:1px solid var(--line);margin-top:14px;padding:22px 0 42px;color:var(--dim);font-size:13px}
footer .wrap{display:flex;flex-wrap:wrap;gap:8px 28px;justify-content:space-between}
footer a{color:var(--muted)}
footer a:hover{color:var(--accent)}
code{font-family:var(--font-mono);background:var(--bg-2);border:1px solid var(--line);border-radius:6px;padding:1px 6px;font-size:.9em}
@media (max-width:640px){
  .hero .wrap{padding-top:44px;padding-bottom:30px}
  .stat{padding:0 14px}
  .stat b{font-size:18px}
}
</style>
</head>
<body>
<a class="skip" href="#catalog">Skip to catalog</a>
<header class="hero">
  <div class="wrap">
    <p class="kicker">Samsung Galaxy XR · SM-I610 · Android XR</p>
    <h1>Galaxy XR <span class="accent">Forge</span></h1>
    <p class="tagline">__TAGLINE__</p>
    <div class="stats">
      <div class="stat"><b id="count">__TOTAL__</b><span>repos shown</span></div>
      <div class="stat"><b>__GROUPS__</b><span>groups</span></div>
      <div class="stat"><b>__DATE__</b><span>curated</span></div>
    </div>
  </div>
</header>
<nav class="filters" aria-label="Filter repositories">
  <div class="filters-inner">
    <input id="q" type="search" placeholder="Filter repos: name, tag, description…" aria-label="Filter repositories">
    <div class="chips" role="group" aria-label="Repository groups">
        __CHIPS__
    </div>
  </div>
</nav>
<main id="catalog">
  __SECTIONS__
  <p class="empty" id="empty" style="display:none">No repository matches that filter.</p>
</main>
<footer>
  <div class="wrap">
    <span>Unofficial community hub — not affiliated with Samsung. Each project keeps its own license.</span>
    <span>Add a repo: edit <code>catalog.json</code>, run <code>python tools/build.py</code>, open a PR · Agents: <a href="__REPO_URL__/blob/main/AGENTS.md">AGENTS.md</a></span>
  </div>
</footer>
<script>
(function () {
  var q = document.getElementById('q');
  var chips = [].slice.call(document.querySelectorAll('.chip'));
  var cards = [].slice.call(document.querySelectorAll('.card'));
  var sections = [].slice.call(document.querySelectorAll('.group'));
  var count = document.getElementById('count');
  var empty = document.getElementById('empty');
  var state = { q: '', group: 'all' };
  function apply() {
    var query = state.q.trim().toLowerCase();
    var shown = 0;
    cards.forEach(function (c) {
      var okG = state.group === 'all' || c.dataset.group === state.group;
      var okQ = !query || c.dataset.text.indexOf(query) > -1;
      var show = okG && okQ;
      c.style.display = show ? '' : 'none';
      if (show) shown++;
    });
    sections.forEach(function (s) {
      var any = [].slice.call(s.querySelectorAll('.card')).some(function (c) {
        return c.style.display !== 'none';
      });
      s.style.display = any ? '' : 'none';
    });
    if (count) count.textContent = shown;
    if (empty) empty.style.display = shown ? 'none' : '';
  }
  if (q) q.addEventListener('input', function () { state.q = q.value; apply(); });
  chips.forEach(function (ch) {
    ch.addEventListener('click', function () {
      chips.forEach(function (c) { c.classList.remove('is-active'); });
      ch.classList.add('is-active');
      state.group = ch.dataset.group;
      apply();
    });
  });
  apply();
})();
</script>
</body>
</html>
"""


def render_site(cat):
    total = sum(len(g["repos"]) for g in cat["groups"])
    updated = cat.get("updated", date.today().isoformat())
    page = SITE_TEMPLATE
    page = page.replace("__TAGLINE__", html.escape(TAGLINE, quote=True))
    page = page.replace("__TOTAL__", str(total))
    page = page.replace("__GROUPS__", str(len(cat["groups"])))
    page = page.replace("__DATE__", updated)
    page = page.replace("__CHIPS__", render_chips(cat))
    page = page.replace("__SECTIONS__", render_sections(cat))
    page = page.replace("__REPO_URL__", REPO_URL)
    return page


# ---------------------------------------------------------------------------


def main():
    args = sys.argv[1:]
    check_only = "--check" in args
    cat = load_catalog()
    errors, repos = validate(cat)
    if errors:
        print("catalog.json INVALID:")
        for e in errors:
            print("  -", e)
        return 1
    if check_only:
        print(f"catalog OK: {len(repos)} repos in {len(cat['groups'])} groups")
        return 0
    readme = render_readme(cat)
    site = render_site(cat)
    README_PATH.write_text(readme, encoding="utf-8", newline="\n")
    SITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SITE_PATH.write_text(site, encoding="utf-8", newline="\n")
    print(f"wrote README.md ({len(readme)} bytes)")
    print(f"wrote docs/index.html ({len(site)} bytes)")
    print(f"catalog: {len(repos)} repos in {len(cat['groups'])} groups")
    return 0


if __name__ == "__main__":
    sys.exit(main())
