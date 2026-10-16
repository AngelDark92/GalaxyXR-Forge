#!/usr/bin/env python
"""Build the Galaxy XR Forge index.

    catalog.json + changelog.json  ->  README.md + CHANGELOG.md + docs/index.html

Usage:
    python tools/build.py           validate, then write the generated files
    python tools/build.py --check   validate the inputs only

Rules:
    - catalog.json is the single source of truth for the repo list; changelog.json
      holds the change history. Never hand-edit README.md, CHANGELOG.md or
      docs/index.html: edit the inputs and rerun this script.
    - Dependency-free: Python 3.10+, stdlib only, runs on any host.
"""

import html
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "catalog.json"
CHANGELOG_PATH = ROOT / "changelog.json"
README_PATH = ROOT / "README.md"
CHANGELOG_MD_PATH = ROOT / "CHANGELOG.md"
SITE_PATH = ROOT / "docs" / "index.html"

REPO_URL = "https://github.com/AngelDark92/GalaxyXR-Forge"
SITE_URL = "https://angeldark92.github.io/GalaxyXR-Forge"
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
            added = r.get("added")
            if added is not None and (
                len(str(added)) != 10 or str(added)[4] != "-" or str(added)[7] != "-"
            ):
                errors.append(f"{repo}: bad added date {added!r} (want YYYY-MM-DD)")
    return errors, seen_repos


# ---------------------------------------------------------------------------
# changelog loading and validation
# ---------------------------------------------------------------------------


def load_changelog():
    with CHANGELOG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def validate_changelog(changelog):
    """Every catalog change needs an entry: date, title and at least one item."""
    errors = []
    entries = changelog.get("entries") or []
    if not entries:
        errors.append("changelog has no entries")
    for i, e in enumerate(entries):
        label = f"changelog entry {i + 1}"
        when = str(e.get("date", ""))
        if len(when) != 10 or when[4] != "-" or when[7] != "-":
            errors.append(f"{label}: bad date {when!r} (want YYYY-MM-DD)")
        if not e.get("title"):
            errors.append(f"{label}: missing title")
        if not (e.get("items") or []):
            errors.append(f"{label}: no items")
        for item in e.get("items") or []:
            if not str(item).strip():
                errors.append(f"{label}: empty item")
    return errors


def render_changelog_md(changelog):
    L = [
        "# Changelog",
        "",
        "Catalog changes, newest first. Generated from [`changelog.json`](changelog.json) "
        "by `tools/build.py` — never edit this file by hand.",
        "",
    ]
    for e in changelog["entries"]:
        L.append(f'## {e["date"]} — {e["title"]}')
        L.append("")
        for item in e["items"]:
            L.append(f"- {item}")
        L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# README
# ---------------------------------------------------------------------------


def render_readme(cat, changelog):
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
                    f'![release](https://img.shields.io/github/v/release/{r["repo"]}?include_prereleases&style=flat-square&label=release)'
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
    A("## Changelog")
    A("")
    for e in changelog.get("entries", [])[:6]:
        A(f'- `{e["date"]}` — {e["title"]}')
    A("")
    A(f'Full history: [`CHANGELOG.md`](CHANGELOG.md) · [site Changelog tab]({SITE_URL}/#changelog).')
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


def count_new(cat, days=5):
    """How many repos were added within the last `days` days, by the build date.

    The site recomputes this in the browser on every load (see the NEW badge JS);
    this build-time number is only the starting value before scripts run.
    """
    today = date.today()
    n = 0
    for g in cat["groups"]:
        for r in g["repos"]:
            added = r.get("added")
            if not added:
                continue
            try:
                when = date(int(str(added)[0:4]), int(str(added)[5:7]), int(str(added)[8:10]))
            except (TypeError, ValueError):
                continue
            if 0 <= (today - when).days < days:
                n += 1
    return n


def render_status_chips(cat):
    total = sum(len(g["repos"]) for g in cat["groups"])
    spec = [
        ("new", "#f97316", "\u2726 New", "cnt-new", count_new(cat),
         "Show only repositories added in the last 5 days \u2014 combines with the other mark filters (AND)"),
        ("fav", "#fbbf24", "\u2605 Favourites", "cnt-fav", 0,
         "Show only favourites \u2014 combines with the other mark filters (AND)"),
        ("done", "#34d399", "\u2713 Checked", "cnt-done", 0,
         "Show only repositories already checked / installed \u2014 combines with the other mark filters (AND)"),
        ("todo", "#64748b", "\u2610 To check", "cnt-todo", total,
         "Show only repositories not checked yet \u2014 combines with the other mark filters (AND)"),
    ]
    chips = []
    for key, hue, label, chip_id, start, title in spec:
        chips.append(
            f'<button type="button" class="chip" data-status="{key}" aria-pressed="false" '
            f'title="{html.escape(title, quote=True)}" style="--hue:{hue}">'
            f'{label} <b id="{chip_id}">{start}</b></button>'
        )
    return "\n        ".join(chips)


def render_sections(cat):
    out = []
    for g in cat["groups"]:
        cards = []
        for r in g["repos"]:
            repo = r["repo"]
            owner, name = repo.split("/")
            badges = [
                f'<img data-badge="stars" src="https://img.shields.io/github/stars/{r["repo"]}?style=flat-square" '
                f'alt="GitHub stars" loading="lazy">'
            ]
            if r.get("release"):
                badges.append(
                    f'<img data-badge="release" src="https://img.shields.io/github/v/release/{r["repo"]}?include_prereleases&style=flat-square&label=release" '
                    f'alt="latest release" loading="lazy">'
                )
            flags = (
                f'<span class="flags">'
                f'<button type="button" class="flag fav" data-flag="fav" aria-pressed="false" '
                f'aria-label="Favourite {repo}" title="Favourite \u2014 saved in this browser">'
                f'<span aria-hidden="true">\u2605</span></button>'
                f'<button type="button" class="flag done" data-flag="done" aria-pressed="false" '
                f'aria-label="Mark {repo} as checked" title="Mark as checked / installed \u2014 saved in this browser">'
                f'<span aria-hidden="true">\u2713</span></button>'
                f'</span>'
            )
            links = [f'<a href="{r["url"]}" target="_blank" rel="noopener">GitHub</a>']
            if r.get("release"):
                links.append(f'<a href="{r["url"]}/releases" target="_blank" rel="noopener">Releases</a>')
            hay = " ".join(
                [r["repo"], r.get("about", ""), r.get("license") or ""] + list(r.get("tags", []))
            ).lower()
            added = r.get("added")
            added_attr = f' data-added="{html.escape(str(added), quote=True)}"' if added else ""
            cards.append(
                f'<article class="card" data-group="{g["id"]}" data-repo="{html.escape(r["repo"], quote=True)}"'
                f' data-text="{html.escape(hay, quote=True)}"{added_attr}>'
                f'<div class="card-top"><h3><a href="{r["url"]}" target="_blank" rel="noopener">'
                f'<span class="owner">{owner}/</span>{name}</a><span class="tag-new" hidden>NEW</span></h3>'
                f'<div class="badges">{"".join(badges)}</div></div>'
                f'<p class="about">{html.escape(r["about"])}</p>'
                f'<div class="card-foot"><span class="license">{html.escape(r.get("license") or "")}</span>'
                f'{flags}'
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
.filters-inner{max-width:1120px;margin:0 auto;padding:10px 22px 12px;display:flex;flex-direction:column;gap:10px}
#q{flex:1 1 240px;min-width:200px;background:var(--bg-2);border:1px solid var(--line-2);color:var(--ink);border-radius:10px;padding:10px 14px;font:14px var(--font-sans);outline:none}
#q:focus{border-color:var(--accent)}
#q::placeholder{color:var(--dim)}
.chips{display:flex;gap:8px;flex-wrap:wrap}
.chip{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--line-2);background:transparent;color:var(--muted);border-radius:999px;padding:7px 13px;font:500 12.5px var(--font-mono);cursor:pointer;min-height:34px}
.chip .dot{width:8px;height:8px;border-radius:50%;background:var(--hue,var(--line-2));flex:none}
.chip b{font-weight:500;color:var(--dim)}
.chip:hover{border-color:var(--muted);color:var(--ink)}
.chip.is-active{border-color:var(--accent);color:var(--ink);background:rgba(249,115,22,.10)}
.chip[data-status="new"].is-active{border-color:rgba(249,115,22,.6);background:rgba(249,115,22,.12)}
.chip[data-status="fav"].is-active{border-color:rgba(251,191,36,.6);background:rgba(251,191,36,.12)}
.chip[data-status="done"].is-active{border-color:rgba(52,211,153,.6);background:rgba(52,211,153,.12)}
.chip[data-status="todo"].is-active{border-color:var(--muted);background:rgba(148,163,184,.10)}
.tabs{display:flex;gap:6px;flex-wrap:wrap;align-self:stretch;border-bottom:1px solid var(--line);padding-bottom:10px}
.tab{border:1px solid var(--line-2);background:transparent;color:var(--muted);border-radius:999px;padding:8px 16px;font:500 13px var(--font-mono);cursor:pointer;min-height:36px}
.tab b{font-weight:500;color:var(--dim)}
.tab:hover{border-color:var(--muted);color:var(--ink)}
.tab.is-active{border-color:var(--accent);color:var(--ink);background:rgba(249,115,22,.12)}
.tab.is-active b{color:var(--accent-2)}
.tab:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.catalog-controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap;min-width:0}
.catalog-controls[hidden]{display:none}
.changelog{max-width:1120px;margin:0 auto;padding:30px 22px 10px}
.changelog h2{font:600 1.35rem var(--font-disp);margin:0 0 6px}
.entries{list-style:none;margin:0;padding:0}
.entry{border-top:1px solid var(--line);padding:18px 0}
.entry:first-child{border-top:0}
.entry-head{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.entry-head time{font:500 12.5px var(--font-mono);color:var(--accent);letter-spacing:.06em}
.entry-head h3{font:600 16px var(--font-disp);margin:0}
.entry ul{margin:8px 0 0;padding-left:20px;color:var(--muted);font-size:14px}
.entry li{margin:4px 0}
main{padding:34px 0 6px}
.group{max-width:1120px;margin:0 auto 42px;padding:0 22px}
.group-head h2{display:flex;align-items:center;gap:10px;font:600 1.35rem var(--font-disp);margin:0 0 6px}
.group-head .dot{width:10px;height:10px;border-radius:3px;background:var(--hue);flex:none}
.blurb{color:var(--muted);margin:0 0 18px;font-size:14.5px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
.card{display:flex;flex-direction:column;gap:10px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 16px 12px;transition:border-color .15s ease,transform .15s ease,box-shadow .15s ease}
.card:hover{border-color:var(--hue);transform:translateY(-2px);box-shadow:0 14px 34px -22px #000}
.card.is-fav{border-color:rgba(251,191,36,.42)}
.card.is-done{background:#0c1119;border-color:#182230}
.card.is-done h3 a{color:var(--muted)}
.card.is-done h3 .owner{color:#516074}
.card.is-done .about{color:#5d6b7e}
.card.is-done .badges{opacity:.45;filter:grayscale(1)}
.card.is-done .card-foot{color:#4b596b;border-top-color:#161f2b}
.card.is-done .card-foot .license{color:#4b596b}
.card.is-done .card-foot a{color:#5d6b7e}
.card.is-done:hover{transform:none;box-shadow:none;border-color:var(--line-2)}
.card.is-new{border-color:rgba(249,115,22,.38)}
.tag-new{display:none;align-items:center;margin-left:8px;padding:2px 8px;border-radius:999px;font:600 10px/1.7 var(--font-mono);letter-spacing:.12em;text-transform:uppercase;color:#180b02;background:linear-gradient(90deg,var(--accent),var(--accent-2));box-shadow:0 6px 18px -12px rgba(249,115,22,.9);vertical-align:middle;white-space:nowrap}
.card.is-new .tag-new{display:inline-flex}
.card-top{display:flex;align-items:flex-start;gap:10px;justify-content:space-between}
.card h3{font:600 16px/1.3 var(--font-disp);margin:0;flex:1 1 auto;min-width:0;overflow-wrap:anywhere;word-break:break-word}
.card h3 .owner{font:400 13px var(--font-mono);color:var(--dim);overflow-wrap:anywhere}
.card h3 a:hover{color:var(--accent-2)}
.badges{display:flex;flex-direction:column;align-items:flex-end;gap:4px;flex:none}
.badges img{height:20px;display:block}
.pill{display:inline-flex;align-items:center;gap:5px;max-width:170px;height:20px;padding:0 8px;border:1px solid var(--line-2);border-radius:999px;font:500 10.5px var(--font-mono);color:var(--muted);white-space:nowrap}
.pill:hover{border-color:var(--accent);color:var(--ink)}
.pill .sym{color:var(--accent-2)}
.pill .v{overflow:hidden;text-overflow:ellipsis}
.card .about{color:var(--muted);font-size:13.5px;margin:0;flex:1;overflow-wrap:anywhere;word-break:break-word}
.card-foot{display:flex;align-items:center;gap:10px;font:11.5px var(--font-mono);color:var(--dim);padding-top:9px;border-top:1px solid var(--line);min-width:0}
.card-foot .license{min-width:0;overflow-wrap:anywhere}
.flags{display:flex;gap:6px;margin-left:auto;flex:none}
.flag{display:inline-flex;align-items:center;justify-content:center;width:30px;height:26px;padding:0;border:1px solid var(--line-2);background:transparent;color:var(--dim);border-radius:8px;cursor:pointer;font:13px/1 var(--font-mono)}
.flag:hover{border-color:var(--muted);color:var(--ink)}
.flag:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.flag.fav.is-on{color:var(--accent-2);border-color:rgba(251,191,36,.55);background:rgba(251,191,36,.14)}
.flag.done.is-on{color:#34d399;border-color:rgba(52,211,153,.5);background:rgba(52,211,153,.14)}
.card-foot .links{display:flex;gap:12px;flex:none}
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
  .filters-inner{padding:8px 14px 10px}
  .tabs{padding-bottom:8px}
  .chips{flex-wrap:nowrap;overflow-x:auto;width:100%;padding-bottom:2px;scrollbar-width:none}
  .chips::-webkit-scrollbar{display:none}
  .chip{flex:none}
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
<nav class="filters" aria-label="Views and filters">
  <div class="filters-inner">
    <div class="tabs" role="tablist" aria-label="Views">
      <button type="button" class="tab is-active" data-view="catalog" role="tab" aria-selected="true">Catalog <b>__TOTAL__</b></button>
      <button type="button" class="tab" data-view="changelog" role="tab" aria-selected="false">Changelog <b>__CHANGELOG_COUNT__</b></button>
    </div>
    <div class="catalog-controls" id="catalog-controls">
      <input id="q" type="search" placeholder="Filter repos: name, tag, description…" aria-label="Filter repositories">
      <div class="chips" role="group" aria-label="Repository groups">
        __CHIPS__
      </div>
      <div class="chips" role="group" aria-label="Checked and favourite repositories">
        __STATUS__
      </div>
    </div>
  </div>
</nav>
<main id="catalog">
  __SECTIONS__
  <p class="empty" id="empty" style="display:none">No repository matches these filters.</p>
</main>
<div id="changelog" hidden>
  __CHANGELOG__
</div>
<footer>
  <div class="wrap">
    <span>Unofficial community hub — not affiliated with Samsung. Each project keeps its own license.</span>
    <span>Add a repo: edit <code>catalog.json</code> and <code>changelog.json</code>, run <code>python tools/build.py</code>, open a PR · <a href="#changelog">Changelog</a> · Agents: <a href="__REPO_URL__/blob/main/AGENTS.md">AGENTS.md</a></span>
  </div>
</footer>
<script>
(function () {
  var STORE_KEY = 'gxrforge.marks';
  var COOKIE_KEY = 'gxrforge_marks';
  var q = document.getElementById('q');
  var groupChips = [].slice.call(document.querySelectorAll('.chip[data-group]'));
  var statusChips = [].slice.call(document.querySelectorAll('.chip[data-status]'));
  var cards = [].slice.call(document.querySelectorAll('.card'));
  var sections = [].slice.call(document.querySelectorAll('.group'));
  var count = document.getElementById('count');
  var empty = document.getElementById('empty');
  var main = document.getElementById('catalog');
  var state = { q: '', group: 'all', status: {}, fav: {}, done: {} };

  // "New" is computed here, in the visitor's browser, from the date the entry was
  // added to the catalog. GitHub Pages is static with no per-request logic, and the
  // date-only string is parsed as local midnight, so no timezone or server clock
  // enters into it. Cards age out of NEW on their own, without a rebuild.
  var NEW_MS = 5 * 24 * 60 * 60 * 1000;
  function isNewCard(card) {
    var raw = card.dataset.added;
    if (!raw) return false;
    var p = raw.split('-');
    if (p.length !== 3) return false;
    var t = new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2])).getTime();
    return Date.now() - t < NEW_MS;
  }

  // Star and check marks live in localStorage, with a cookie kept in sync as a
  // fallback, so they survive reloads and a browser restart. Nothing is sent anywhere.
  function readRaw() {
    try {
      var stored = window.localStorage.getItem(STORE_KEY);
      if (stored) return stored;
    } catch (e) {}
    var hit = document.cookie.match(new RegExp('(?:^|;\\s*)' + COOKIE_KEY + '=([^;]*)'));
    return hit ? decodeURIComponent(hit[1]) : '';
  }
  function writeRaw(raw) {
    try { window.localStorage.setItem(STORE_KEY, raw); } catch (e) {}
    document.cookie = COOKIE_KEY + '=' + encodeURIComponent(raw) +
      '; path=/; max-age=31536000; samesite=lax';
  }
  function listOf(marks) {
    var out = [];
    for (var k in marks) { if (Object.prototype.hasOwnProperty.call(marks, k)) out.push(k); }
    return out.sort();
  }
  function loadMarks() {
    var raw = readRaw();
    if (!raw) return;
    var data = null;
    try { data = JSON.parse(raw); } catch (e) { return; }
    if (!data) return;
    ['fav', 'done'].forEach(function (key) {
      (data[key] || []).forEach(function (repo) { state[key][repo] = true; });
    });
  }
  function saveMarks() {
    writeRaw(JSON.stringify({ fav: listOf(state.fav), done: listOf(state.done) }));
  }
  function setCount(id, n) {
    var el = document.getElementById(id);
    if (el) el.textContent = n;
  }

  function apply() {
    var query = state.q.trim().toLowerCase();
    var active = [];
    ['new', 'fav', 'done', 'todo'].forEach(function (s) { if (state.status[s]) active.push(s); });
    var shown = 0, favN = 0, doneN = 0, newN = 0;
    cards.forEach(function (c) {
      var repo = c.dataset.repo;
      var fav = !!state.fav[repo];
      var done = !!state.done[repo];
      var isNew = isNewCard(c);
      if (fav) favN++;
      if (done) doneN++;
      if (isNew) newN++;
      var pill = c.querySelector('.tag-new');
      if (pill) pill.hidden = !isNew;
      c.classList.toggle('is-new', isNew);
      c.classList.toggle('is-fav', fav);
      c.classList.toggle('is-done', done);
      var favBtn = c.querySelector('.flag.fav');
      var doneBtn = c.querySelector('.flag.done');
      if (favBtn) {
        favBtn.classList.toggle('is-on', fav);
        favBtn.setAttribute('aria-pressed', fav ? 'true' : 'false');
      }
      if (doneBtn) {
        doneBtn.classList.toggle('is-on', done);
        doneBtn.setAttribute('aria-pressed', done ? 'true' : 'false');
      }
      var okGroup = state.group === 'all' || c.dataset.group === state.group;
      var okText = !query || c.dataset.text.indexOf(query) > -1;
      var okMark = active.every(function (s) {
        if (s === 'new') return isNew;
        if (s === 'fav') return fav;
        if (s === 'done') return done;
        return !done;
      });
      var show = okGroup && okText && okMark;
      c.style.display = show ? '' : 'none';
      if (show) shown++;
    });
    sections.forEach(function (s) {
      var any = [].slice.call(s.querySelectorAll('.card')).some(function (c) {
        return c.style.display !== 'none';
      });
      s.style.display = any ? '' : 'none';
    });
    setCount('cnt-new', newN);
    setCount('cnt-fav', favN);
    setCount('cnt-done', doneN);
    setCount('cnt-todo', cards.length - doneN);
    if (count) count.textContent = shown;
    if (empty) empty.style.display = shown ? 'none' : '';
  }

  if (q) q.addEventListener('input', function () { state.q = q.value; apply(); });
  groupChips.forEach(function (ch) {
    ch.addEventListener('click', function () {
      groupChips.forEach(function (c) { c.classList.remove('is-active'); });
      ch.classList.add('is-active');
      state.group = ch.dataset.group;
      apply();
    });
  });
  statusChips.forEach(function (ch) {
    ch.setAttribute('aria-pressed', 'false');
    ch.addEventListener('click', function () {
      var key = ch.dataset.status;
      state.status[key] = !state.status[key];
      ch.classList.toggle('is-active', !!state.status[key]);
      ch.setAttribute('aria-pressed', state.status[key] ? 'true' : 'false');
      apply();
    });
  });
  if (main) {
    main.addEventListener('click', function (ev) {
      var btn = ev.target && ev.target.closest ? ev.target.closest('.flag') : null;
      if (!btn) return;
      var card = btn.closest('.card');
      if (!card) return;
      var store = state[btn.dataset.flag];
      var repo = card.dataset.repo;
      if (!store || !repo) return;
      if (store[repo]) { delete store[repo]; } else { store[repo] = true; }
      saveMarks();
      apply();
    });
  }
  loadMarks();
  apply();
})();

// Catalog / Changelog views. The active view is mirrored in the URL hash, so a
// link like #changelog opens the history directly.
(function () {
  var tabs = [].slice.call(document.querySelectorAll('.tab'));
  var views = { catalog: document.getElementById('catalog'), changelog: document.getElementById('changelog') };
  var controls = document.getElementById('catalog-controls');
  function show(view) {
    tabs.forEach(function (t) {
      var on = t.dataset.view === view;
      t.classList.toggle('is-active', on);
      t.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    Object.keys(views).forEach(function (k) {
      if (views[k]) views[k].hidden = k !== view;
    });
    if (controls) controls.hidden = view !== 'catalog';
    if (window.history && window.history.replaceState) window.history.replaceState(null, '', '#' + view);
  }
  tabs.forEach(function (t) {
    t.addEventListener('click', function () { show(t.dataset.view); });
  });
  if (window.location.hash === '#changelog') show('changelog');
})();

// Live stars and latest release, fetched in the visitor's browser so both stay
// current with no rebuild: shields.io JSON endpoints (CORS-open, edge-cached),
// ungh.cc as fallback, results cached in localStorage for 30 minutes and
// refreshed in the background. The badge images stay until a value arrives, so
// nothing breaks without JS or when a fetch fails.
(function () {
  var STORE = 'gxrforge.live.v1';
  var TTL = 30 * 60 * 1000;
  var MAX_PARALLEL = 6;
  var cards = [].slice.call(document.querySelectorAll('.card[data-repo]'));
  if (!cards.length || !window.fetch) return;
  var cache = {};
  try { cache = JSON.parse(window.localStorage.getItem(STORE) || '{}') || {}; } catch (e) { cache = {}; }
  var queue = [];
  var active = 0;

  function save() {
    try { window.localStorage.setItem(STORE, JSON.stringify(cache)); } catch (e) {}
  }
  function getJSON(url) {
    return window.fetch(url, { credentials: 'omit' }).then(function (res) {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    });
  }
  function compact(n) {
    n = Number(n);
    if (!isFinite(n)) return '';
    if (n >= 1000) return (n / 1000).toFixed(1).replace(/[.]0$/, '') + 'k';
    return String(n);
  }
  // Each helper resolves {ok, value}; ok false means "could not determine,
  // leave the badge image in place and retry on the next visit".
  function fetchStars(repo) {
    return getJSON('https://img.shields.io/github/stars/' + repo + '.json')
      .then(function (d) { var v = String(d.value || ''); return { ok: !!v, value: v }; })
      .catch(function () {
        return getJSON('https://ungh.cc/repos/' + repo)
          .then(function (d) { return { ok: true, value: compact((d.repo || {}).stars) }; })
          .catch(function () { return { ok: false, value: null }; });
      });
  }
  function fetchRelease(repo) {
    return getJSON('https://img.shields.io/github/v/release/' + repo + '.json?include_prereleases')
      .then(function (d) {
        var v = String(d.value || '');
        if (!v || /no releases|not found/i.test(v)) return { ok: true, value: null };
        return { ok: true, value: v };
      })
      .catch(function () {
        return getJSON('https://ungh.cc/repos/' + repo + '/releases/latest')
          .then(function (d) {
            var tag = d.release && d.release.tag ? String(d.release.tag) : null;
            return { ok: true, value: tag };
          })
          .catch(function () { return { ok: false, value: null }; });
      });
  }
  function dropImg(badges, which) {
    var img = badges.querySelector('img[data-badge="' + which + '"]');
    if (img && img.parentNode) img.parentNode.removeChild(img);
  }
  function pill(badges, cls, href, sym) {
    var el = badges.querySelector('a.pill.' + cls);
    if (el) return el;
    el = document.createElement('a');
    el.className = 'pill ' + cls;
    el.href = href;
    el.target = '_blank';
    el.rel = 'noopener';
    if (sym) {
      var s = document.createElement('span');
      s.className = 'sym';
      s.setAttribute('aria-hidden', 'true');
      s.textContent = sym;
      el.appendChild(s);
    }
    var v = document.createElement('span');
    v.className = 'v';
    el.appendChild(v);
    return el;
  }
  function render(card, repo, data) {
    var badges = card.querySelector('.badges');
    if (!badges) return;
    if (data.s) {
      var sp = pill(badges, 'stars', 'https://github.com/' + repo + '/stargazers', '\u2605');
      sp.querySelector('.v').textContent = data.s;
      sp.title = data.s + ' stars on GitHub';
      if (sp.parentNode !== badges) badges.insertBefore(sp, badges.firstChild);
      dropImg(badges, 'stars');
    }
    if (data.rn) {
      dropImg(badges, 'release');
      var old = badges.querySelector('a.pill.rel');
      if (data.r) {
        var rp = pill(badges, 'rel', 'https://github.com/' + repo + '/releases', null);
        rp.querySelector('.v').textContent = data.r;
        rp.title = 'Latest release: ' + data.r;
        if (rp.parentNode !== badges) {
          var sp2 = badges.querySelector('a.pill.stars');
          if (sp2 && sp2.parentNode === badges) badges.insertBefore(rp, sp2.nextSibling);
          else badges.insertBefore(rp, badges.firstChild);
        }
      } else if (old && old.parentNode) {
        old.parentNode.removeChild(old);
      }
    }
  }
  function pump() {
    while (active < MAX_PARALLEL && queue.length) {
      active++;
      (queue.shift())().then(function () { active--; pump(); }, function () { active--; pump(); });
    }
  }
  function schedule(fn) { queue.push(fn); pump(); }

  cards.forEach(function (card) {
    var repo = card.dataset.repo;
    if (!repo || repo.indexOf('/') < 0) return;
    var hit = cache[repo] || null;
    if (hit) render(card, repo, { s: hit.s, r: hit.r, rn: hit.rn });
    if (hit && Date.now() - (hit.t || 0) < TTL) return;
    schedule(function () {
      return Promise.all([fetchStars(repo), fetchRelease(repo)]).then(function (res) {
        var stars = res[0], rel = res[1];
        if (!stars.ok && !rel.ok) return; // keep the badges; retry on the next visit
        var entry = {
          s: stars.ok ? stars.value : (hit && hit.s) || null,
          r: rel.ok ? rel.value : (hit && hit.r) || null,
          rn: rel.ok ? true : !!(hit && hit.rn),
          t: Date.now()
        };
        cache[repo] = entry;
        save();
        render(card, repo, entry);
      });
    });
  });
})();
</script>
</body>
</html>
"""


def render_changelog_view(changelog):
    entries = []
    for e in changelog["entries"]:
        items = "".join(f"<li>{html.escape(str(i))}</li>" for i in e["items"])
        entries.append(
            f'<li class="entry"><div class="entry-head">'
            f'<time datetime="{e["date"]}">{e["date"]}</time>'
            f'<h3>{html.escape(str(e["title"]))}</h3></div><ul>{items}</ul></li>'
        )
    return (
        '<section class="changelog"><h2>Changelog</h2>'
        '<p class="blurb">Every catalog change — repos added, moved or removed. Newest first.</p>'
        f'<ol class="entries">{"".join(entries)}</ol></section>'
    )


def render_site(cat, changelog):
    total = sum(len(g["repos"]) for g in cat["groups"])
    updated = cat.get("updated", date.today().isoformat())
    page = SITE_TEMPLATE
    page = page.replace("__TAGLINE__", html.escape(TAGLINE, quote=True))
    page = page.replace("__TOTAL__", str(total))
    page = page.replace("__GROUPS__", str(len(cat["groups"])))
    page = page.replace("__DATE__", updated)
    page = page.replace("__CHIPS__", render_chips(cat))
    page = page.replace("__STATUS__", render_status_chips(cat))
    page = page.replace("__SECTIONS__", render_sections(cat))
    page = page.replace("__CHANGELOG_COUNT__", str(len(changelog.get("entries", []))))
    page = page.replace("__CHANGELOG__", render_changelog_view(changelog))
    page = page.replace("__REPO_URL__", REPO_URL)
    return page


# ---------------------------------------------------------------------------


def main():
    args = sys.argv[1:]
    check_only = "--check" in args
    cat = load_catalog()
    changelog = load_changelog()
    errors, repos = validate(cat)
    errors += validate_changelog(changelog)
    if errors:
        print("input INVALID:")
        for e in errors:
            print("  -", e)
        return 1
    if check_only:
        print(
            f"OK: {len(repos)} repos in {len(cat['groups'])} groups; "
            f"changelog: {len(changelog['entries'])} entries"
        )
        return 0
    readme = render_readme(cat, changelog)
    changelog_md = render_changelog_md(changelog)
    site = render_site(cat, changelog)
    README_PATH.write_text(readme, encoding="utf-8", newline="\n")
    CHANGELOG_MD_PATH.write_text(changelog_md, encoding="utf-8", newline="\n")
    SITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SITE_PATH.write_text(site, encoding="utf-8", newline="\n")
    print(f"wrote README.md ({len(readme)} bytes)")
    print(f"wrote CHANGELOG.md ({len(changelog_md)} bytes)")
    print(f"wrote docs/index.html ({len(site)} bytes)")
    print(
        f"catalog: {len(repos)} repos in {len(cat['groups'])} groups; "
        f"changelog: {len(changelog['entries'])} entries"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
