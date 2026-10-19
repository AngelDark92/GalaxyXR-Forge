#!/usr/bin/env python
"""Build the Galaxy XR Forge index.

    catalog.json (groups) + catalog.d/ (one file per repo)
    + changelog.d/ (one file per change)
        ->  README.md + CHANGELOG.md + docs/index.html + docs/catalog-index.json

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
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "catalog.json"
CATALOG_DIR = ROOT / "catalog.d"
CHANGELOG_PATH = ROOT / "changelog.json"
CHANGELOG_DIR = ROOT / "changelog.d"
README_PATH = ROOT / "README.md"
CHANGELOG_MD_PATH = ROOT / "CHANGELOG.md"
SITE_PATH = ROOT / "docs" / "index.html"
INDEX_PATH = ROOT / "docs" / "catalog-index.json"

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
    """Groups from catalog.json, entries from catalog.d/<group>/<owner>__<name>.json.

    One file per repo is what makes two pending additions unable to conflict: they
    add different files. Falls back to the single-file layout when catalog.d is absent.
    """
    with CATALOG_PATH.open(encoding="utf-8") as f:
        cat = json.load(f)
    if not CATALOG_DIR.is_dir():
        return cat

    errors = []
    for g in cat.get("groups", []):
        gid = g.get("id", "")
        g.pop("repos", None)
        entries = []
        folder = CATALOG_DIR / gid
        for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
            with path.open(encoding="utf-8") as f:
                entry = json.load(f)
            owner, sep, name = path.stem.partition("__")
            want = f"{owner}/{name}"
            if not sep or entry.get("repo", "").lower() != want.lower():
                errors.append(
                    f"{path.relative_to(ROOT)}: repo {entry.get('repo')!r} "
                    f"does not match the file name ({want})"
                )
            entries.append(entry)
        g["repos"] = entries
    if errors:
        raise SystemExit("catalog.d is inconsistent:\n  " + "\n  ".join(errors))
    return cat


def dump_json(value):
    """2-space JSON, short string arrays inline — the catalog file style."""
    return _dump(value, 0) + "\n"


def _dump(value, depth):
    pad = "  " * depth
    if isinstance(value, dict):
        if not value:
            return "{}"
        parts = [
            f"{pad}  {json.dumps(k, ensure_ascii=False)}: {_dump(v, depth + 1).lstrip()}"
            for k, v in value.items()
        ]
        return "{\n" + ",\n".join(parts) + "\n" + pad + "}"
    if isinstance(value, list):
        if not value:
            return "[]"
        if all(isinstance(x, str) for x in value):
            inline = "[" + ", ".join(json.dumps(x, ensure_ascii=False) for x in value) + "]"
            if len(inline) <= 78:
                return inline
        parts = [f"{pad}  {_dump(x, depth + 1).lstrip()}" for x in value]
        return "[\n" + ",\n".join(parts) + "\n" + pad + "]"
    return json.dumps(value, ensure_ascii=False)


def repo_path(group_id, repo):
    owner, name = repo.split("/", 1)
    return CATALOG_DIR / group_id / f"{owner}__{name}.json"


def write_repo_entry(group_id, entry):
    path = repo_path(group_id, entry["repo"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_json(entry), encoding="utf-8", newline="\n")
    return path


def write_changelog_entry(entry):
    slug = re.sub(r"[^a-z0-9]+", "-", str(entry["title"]).lower()).strip("-")[:48] or "change"
    path = CHANGELOG_DIR / f"{entry['date']}-{slug}.json"
    n = 2
    while path.exists():
        path = CHANGELOG_DIR / f"{entry['date']}-{slug}-{n}.json"
        n += 1
    CHANGELOG_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_json(entry), encoding="utf-8", newline="\n")
    return path


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
    """Entries from changelog.d/*.json, newest first; falls back to changelog.json."""
    if CHANGELOG_DIR.is_dir():
        entries = []
        for path in CHANGELOG_DIR.glob("*.json"):
            with path.open(encoding="utf-8") as f:
                entry = json.load(f)
            entry["_file"] = path.name
            entries.append(entry)
        entries.sort(key=lambda e: (str(e.get("date", "")), e["_file"]), reverse=True)
        for entry in entries:
            entry.pop("_file", None)
        return {"entries": entries}
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


def newest_date(cat, changelog):
    """Newest `added`/changelog date, computed at build time.

    Storing this in catalog.json made every single PR edit the same line, so two
    pending adds always conflicted. Derive it instead.
    """
    dates = [r.get("added") for g in cat["groups"] for r in g["repos"] if r.get("added")]
    dates += [e.get("date") for e in changelog.get("entries", []) if e.get("date")]
    return max(dates) if dates else date.today().isoformat()


def render_readme(cat, changelog):
    groups = cat["groups"]
    total = sum(len(g["repos"]) for g in groups)
    updated = newest_date(cat, changelog)
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
    A(
        f"**Fastest:** use the **Add repo** button on the [site]({SITE_URL}/#add-repo) — paste the link, pick a group. "
        "CI adds the card, regenerates the README and site, and opens a pull request for review."
    )
    A("")
    A("Or run it locally, one command:")
    A("")
    A("```sh")
    A("python tools/add-repo.py https://github.com/owner/name --group apps-samples")
    A("```")
    A("")
    A(
        "The tool refuses private or already-listed repos, reads the license and latest release, writes the entry "
        "with today's `added` date, appends a changelog entry, regenerates every generated file and runs both link "
        "checks. `--dry-run` prints the entry without writing anything."
    )
    A("")
    A(
        "Manual edits still work: add a file under `catalog.d/<group>/` and one under `changelog.d/`, run "
        "`python tools/build.py`, then `python tools/check-links.py` and `python tools/check-repos.py`. One file "
        "per repo is why two pending additions never conflict."
    )
    A("")
    A(
        "CI gates every pull request on all four checks, so a PR with stale or hand-edited generated files cannot merge. "
        "See [`.agents/skills/`](.agents/skills/) for the full procedure."
    )
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
        f'<button type="button" class="chip is-active" data-group="all" aria-pressed="true" '
        f'style="--hue:#f97316" title="Show every group">'
        f'<span class="dot"></span><span class="lbl">All</span><b>{total}</b></button>'
    ]
    for g in cat["groups"]:
        chips.append(
            f'<button type="button" class="chip" data-group="{g["id"]}" aria-pressed="false" '
            f'style="--hue:{g["hue"]}" title="{html.escape(g["blurb"], quote=True)}">'
            f'<span class="dot"></span><span class="lbl">{g["icon"]} {html.escape(g["title"])}</span>'
            f'<b>{len(g["repos"])}</b></button>'
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
            f'<span class="lbl">{label}</span><b id="{chip_id}">{start}</b></button>'
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
            release_attr = ' data-release="1"' if r.get("release") else ""
            cards.append(
                f'<article class="card" data-group="{g["id"]}" data-repo="{html.escape(r["repo"], quote=True)}"'
                f' data-text="{html.escape(hay, quote=True)}"{added_attr}{release_attr}>'
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
.glow{position:fixed;left:0;top:0;width:620px;height:620px;margin:-310px 0 0 -310px;z-index:-1;pointer-events:none;border-radius:50%;
  background:radial-gradient(closest-side, rgba(249,115,22,.22), rgba(249,115,22,.07) 55%, transparent 100%);
  transform:translate3d(var(--gx,50vw),var(--gy,28vh),0);opacity:0;transition:opacity .5s ease;will-change:transform}
body.glow-on .glow{opacity:1}
@media (prefers-reduced-motion:reduce){.glow{display:none}}
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
.topbar{position:sticky;top:0;z-index:30;background:rgba(10,14,20,.97);border-bottom:1px solid var(--line)}
.topbar-inner{max-width:1120px;margin:0 auto;padding:10px 22px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.menu-btn{display:inline-flex;align-items:center;gap:9px;border:1px solid var(--line-2);background:transparent;color:var(--muted);border-radius:999px;padding:7px 15px 7px 12px;font:500 13px var(--font-mono);cursor:pointer;min-height:36px}
.menu-btn:hover{border-color:var(--muted);color:var(--ink)}
.menu-btn[aria-expanded="true"]{border-color:var(--accent);color:var(--ink);background:rgba(249,115,22,.10)}
.menu-btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.menu-btn svg{width:15px;height:15px;flex:none}
.tab{border:1px solid var(--line-2);background:transparent;color:var(--muted);border-radius:999px;padding:8px 16px;font:500 13px var(--font-mono);cursor:pointer;min-height:36px}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin-left:auto}
.tab b{font-weight:500;color:var(--dim)}
.tab:hover{border-color:var(--muted);color:var(--ink)}
.tab.is-active{border-color:var(--accent);color:var(--ink);background:rgba(249,115,22,.12)}
.tab.is-active b{color:var(--accent-2)}
.tab:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.shell{max-width:1120px;margin:0 auto;padding:26px 22px 0;display:grid;grid-template-columns:308px minmax(0,1fr);gap:26px;align-items:start}
.content{min-width:0}
.side{position:sticky;top:74px;max-height:calc(100vh - 96px);overflow:auto;display:flex;flex-direction:column;gap:18px;padding:16px 14px;width:308px;border:1px solid rgba(148,163,184,.20);border-radius:16px;
  background:linear-gradient(160deg,rgba(30,41,56,.72),rgba(12,18,26,.80));
  -webkit-backdrop-filter:blur(16px) saturate(160%);backdrop-filter:blur(16px) saturate(160%);
  box-shadow:0 28px 70px -30px rgba(0,0,0,.9),inset 0 1px 0 rgba(255,255,255,.06);
  transform-origin:top left;
  transition:opacity .18s ease,transform .22s cubic-bezier(.2,.9,.3,1.15),visibility 0s linear 0s;scrollbar-width:thin}
@supports not ((backdrop-filter:blur(1px)) or (-webkit-backdrop-filter:blur(1px))){
  .side{background:linear-gradient(160deg,#141d29,#0c121a)}
}
.side::-webkit-scrollbar{width:8px}
.side::-webkit-scrollbar-track{background:transparent}
.side::-webkit-scrollbar-thumb{background:var(--line-2);border-radius:8px}
.side::-webkit-scrollbar-thumb:hover{background:var(--muted)}
.side-head{display:none;align-items:center;justify-content:space-between}
.side-title{font:600 12px var(--font-disp);letter-spacing:.16em;text-transform:uppercase;color:var(--accent)}
.side-close{display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border:1px solid var(--line-2);background:transparent;color:var(--muted);border-radius:9px;cursor:pointer}
.side-close:hover{border-color:var(--muted);color:var(--ink)}
.side-close svg{width:13px;height:13px}
.side-section{display:flex;flex-direction:column;gap:8px;min-width:0}
.side-label{font:500 10.5px var(--font-mono);letter-spacing:.16em;text-transform:uppercase;color:var(--dim)}
#q{width:100%;background:var(--bg);border:1px solid var(--line-2);color:var(--ink);border-radius:9px;padding:9px 12px;font:13px var(--font-sans);outline:none}
#q:focus{border-color:var(--accent)}
#q::placeholder{color:var(--dim)}
.chips{display:flex;flex-direction:column;gap:6px;min-width:0}
.chip{display:flex;align-items:center;gap:9px;width:100%;border:1px solid var(--line-2);background:transparent;color:var(--muted);border-radius:9px;padding:8px 11px;font:500 12.5px var(--font-mono);cursor:pointer;min-height:34px;text-align:left}
.chip .dot{width:8px;height:8px;border-radius:50%;background:var(--hue,var(--line-2));flex:none}
.chip .lbl{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.chip b{margin-left:auto;flex:none;font-weight:500;color:var(--dim)}
.chip:hover{border-color:var(--muted);color:var(--ink)}
.chip:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.chip.is-active{border-color:var(--accent);color:var(--ink);background:rgba(249,115,22,.10)}
.chip.is-active b{color:var(--ink)}
.chip[data-group].is-active{border-color:var(--hue)}
.chip[data-status="new"].is-active{border-color:rgba(249,115,22,.6);background:rgba(249,115,22,.12)}
.chip[data-status="fav"].is-active{border-color:rgba(251,191,36,.6);background:rgba(251,191,36,.12)}
.chip[data-status="done"].is-active{border-color:rgba(52,211,153,.6);background:rgba(52,211,153,.12)}
.chip[data-status="todo"].is-active{border-color:var(--muted);background:rgba(148,163,184,.10)}
.side-done{display:none;align-items:center;justify-content:center;gap:8px;width:100%;border:1px solid rgba(249,115,22,.55);background:rgba(249,115,22,.14);color:var(--ink);border-radius:10px;padding:11px 14px;font:500 13px var(--font-mono);cursor:pointer;min-height:42px}
.side-done:hover{background:rgba(249,115,22,.24)}
.side-done b{color:var(--accent-2);font-weight:600}
.backdrop{display:none}
#catalog,#changelog{scroll-margin-top:74px}
body.view-changelog .side,body.view-changelog .menu-btn{display:none}
body.view-changelog .shell{grid-template-columns:minmax(0,1fr)}
@media (min-width:1001px){
  /* Collapsed: keep two tracks and shrink the first to zero. A single-column
     template would wrap .content into a second row below the (invisible) rail
     and shove the whole catalog down the page. */
  body.side-closed .shell{grid-template-columns:0 minmax(0,1fr);gap:0}
  body.side-closed .side{opacity:0;transform:translateY(-10px) scale(.97);visibility:hidden;pointer-events:none;
    transition:opacity .16s ease,transform .2s ease,visibility 0s linear .2s}
}
@media (min-width:1840px){
  /* The rail leaves the centered column: its grid track collapses to zero and a
     negative margin pulls the panel out to the left, a constant 26px from the repo
     grid, which keeps the freed width (three cards per row). Sticky stays, so the
     rail still starts below the hero and pins under the top bar on scroll.
     1840px is where 308px rail + gap + 1120px column fit without crowding the
     window edge. */
  .shell{grid-template-columns:0 minmax(0,1fr);gap:0}
  .side{width:308px;margin-left:-334px}
}
@media (max-width:1000px){
  .shell{grid-template-columns:minmax(0,1fr);padding-top:20px}
  .side{position:fixed;top:0;bottom:0;left:0;z-index:60;width:min(320px,86vw);max-height:none;border-radius:0 16px 16px 0;border-left:0;padding:16px 16px 22px;
    background:linear-gradient(160deg,rgba(24,34,47,.88),rgba(9,13,19,.92));
    transform:translateX(-104%);visibility:hidden;transition:transform .24s cubic-bezier(.2,.9,.3,1.1),visibility 0s linear .24s}
  body.side-open .side{transform:none;visibility:visible;box-shadow:0 40px 90px -30px #000;transition:transform .24s cubic-bezier(.2,.9,.3,1.1),visibility 0s linear 0s}
  .side-head{display:flex}
  .side-done{display:flex}
  .backdrop:not([hidden]){display:block;position:fixed;inset:0;z-index:50;background:rgba(4,7,11,.60);
    -webkit-backdrop-filter:blur(3px);backdrop-filter:blur(3px)}
}
@media (prefers-reduced-motion:reduce){
  .side{transition:none}
}
.changelog{padding:6px 0 10px}
.changelog h2{font:600 1.35rem var(--font-disp);margin:0 0 6px}
.entries{list-style:none;margin:0;padding:0}
.entry{border-top:1px solid var(--line);padding:18px 0}
.entry:first-child{border-top:0}
.entry-head{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.entry-head time{font:500 12.5px var(--font-mono);color:var(--accent);letter-spacing:.06em}
.entry-head h3{font:600 16px var(--font-disp);margin:0}
.entry ul{margin:8px 0 0;padding-left:20px;color:var(--muted);font-size:14px}
.entry li{margin:4px 0}
main{padding:0 0 6px}
.group{margin:0 0 42px}
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
.empty{margin:0;padding:0 0 30px;color:var(--muted);font-style:italic}
footer{border-top:1px solid var(--line);margin-top:14px;padding:22px 0 42px;color:var(--dim);font-size:13px}
footer .wrap{display:flex;flex-wrap:wrap;gap:8px 28px;justify-content:space-between}
footer a{color:var(--muted)}
footer a:hover{color:var(--accent)}
code{font-family:var(--font-mono);background:var(--bg-2);border:1px solid var(--line);border-radius:6px;padding:1px 6px;font-size:.9em}
.add-btn{display:inline-flex;align-items:center;gap:8px;border:1px solid rgba(249,115,22,.45);background:rgba(249,115,22,.12);color:var(--ink);border-radius:999px;padding:8px 16px;font:600 13px var(--font-mono);cursor:pointer;min-height:36px;text-decoration:none}
.add-btn:hover{background:rgba(249,115,22,.2);border-color:var(--accent)}
.add-btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.add-dialog{border:1px solid var(--line-2);border-radius:16px;background:var(--card);color:var(--ink);padding:0;width:min(540px,calc(100vw - 28px));max-height:min(88vh,720px);overflow:auto;box-shadow:0 30px 80px -30px #000}
.add-dialog::backdrop{background:rgba(4,7,11,.72)}
.add-form{display:flex;flex-direction:column;gap:9px;padding:22px 22px 18px}
.add-form h2{font:600 1.25rem var(--font-disp);margin:0}
.add-form .dlg-lede{margin:0 0 4px;color:var(--muted);font-size:13.5px}
.add-form label{font:500 11.5px var(--font-mono);color:var(--dim);text-transform:uppercase;letter-spacing:.09em;margin-top:7px}
.add-form label .opt{text-transform:none;letter-spacing:0;color:var(--dim)}
.add-form input,.add-form select{background:var(--bg-2);border:1px solid var(--line-2);color:var(--ink);border-radius:10px;padding:10px 12px;font:14px var(--font-sans);outline:none;width:100%}
.add-form input:focus,.add-form select:focus{border-color:var(--accent)}
.dlg-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
.dlg-close{border:1px solid var(--line-2);background:transparent;color:var(--muted);border-radius:8px;width:30px;height:30px;cursor:pointer;font:13px/1 var(--font-mono)}
.dlg-close:hover{color:var(--ink);border-color:var(--muted)}
.dlg-actions{display:flex;align-items:center;gap:12px;margin-top:14px;flex-wrap:wrap}
.add-submit{display:inline-flex;align-items:center;background:linear-gradient(90deg,var(--accent),var(--accent-2));color:#180b02;font:600 13px var(--font-mono);padding:10px 16px;border-radius:10px;text-decoration:none}
.add-submit.is-disabled{opacity:.45;pointer-events:none}
.dlg-alt{color:var(--dim);font-size:12px}
.dlg-note{margin:2px 0 6px;padding:10px 12px;border-left:3px solid var(--accent);background:rgba(249,115,22,.09);border-radius:0 8px 8px 0;color:var(--ink);font-size:12.5px;line-height:1.45}
.dlg-status{margin:2px 0 0;min-height:16px;font:12px var(--font-mono);color:var(--dim)}
.dlg-status.ok{color:#4ade80}
.dlg-status.warn{color:#fbbf24}
@media (max-width:640px){
  .hero .wrap{padding-top:44px;padding-bottom:30px}
  .stat{padding:0 14px}
  .stat b{font-size:18px}
  .topbar-inner{padding:9px 14px}
  .shell{padding:18px 14px 0}
  .menu-btn span{display:none}
  .menu-btn{padding:7px 11px}
}
</style>
<noscript><style>
/* No JS: the drawer cannot open, so show the rail inline on small screens. */
@media (max-width:1000px){
  .side{position:static;transform:none;visibility:visible;max-height:none;width:auto;border-radius:14px;border-left:1px solid var(--line)}
  .menu-btn,.side-head,.side-done{display:none}
}
</style></noscript>
</head>
<body>
<a class="skip" href="#catalog">Skip to catalog</a>
<div class="glow" aria-hidden="true"></div>
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
<nav class="topbar" aria-label="Views">
  <div class="topbar-inner">
    <button type="button" class="menu-btn" id="menu-btn" aria-expanded="true" aria-controls="sidebar" title="Show or hide the filters">
      <svg viewBox="0 0 16 16" aria-hidden="true" fill="none"><path d="M2 3.5h12M2 8h12M2 12.5h12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
      <span>Filters</span>
    </button>
    <div class="tabs" role="tablist" aria-label="Views">
      <button type="button" class="tab is-active" data-view="catalog" role="tab" aria-selected="true">Catalog <b>__TOTAL__</b></button>
      <button type="button" class="tab" data-view="changelog" role="tab" aria-selected="false">Changelog <b>__CHANGELOG_COUNT__</b></button>
    </div>
    <a class="add-btn" id="add-repo-btn" href="__REPO_URL__/issues/new?template=add-repo.md&labels=add-repo" aria-haspopup="dialog" aria-controls="add-repo-dialog">＋ Add repo</a>
  </div>
</nav>
<div class="shell" id="shell">
  <aside class="side" id="sidebar" aria-label="Filters">
    <div class="side-head">
      <span class="side-title">Filters</span>
      <button type="button" class="side-close" id="side-close" aria-label="Close filters">
        <svg viewBox="0 0 14 14" aria-hidden="true" fill="none"><path d="M2 2l10 10M12 2L2 12" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
      </button>
    </div>
    <div class="side-section">
      <label class="side-label" for="q">Search</label>
      <input id="q" type="search" placeholder="name, tag, description…" aria-label="Filter repositories">
    </div>
    <div class="side-section">
      <span class="side-label" id="lbl-groups">Group</span>
      <div class="chips" role="group" aria-labelledby="lbl-groups">
        __CHIPS__
      </div>
    </div>
    <div class="side-section">
      <span class="side-label" id="lbl-status">Status</span>
      <div class="chips" role="group" aria-labelledby="lbl-status">
        __STATUS__
      </div>
    </div>
    <button type="button" class="side-done" id="side-done">Show <b id="side-count">__TOTAL__</b> repos</button>
  </aside>
  <div class="content">
    <main id="catalog">
      __SECTIONS__
      <p class="empty" id="empty" style="display:none">No repository matches these filters.</p>
    </main>
    <div id="changelog" hidden>
      __CHANGELOG__
    </div>
  </div>
</div>
<div class="backdrop" id="backdrop" hidden></div>
<dialog id="add-repo-dialog" class="add-dialog" aria-labelledby="add-repo-title">
  <div class="add-form">
    <div class="dlg-head">
      <h2 id="add-repo-title">Add a repo</h2>
      <button type="button" class="dlg-close" id="add-repo-close" aria-label="Close">✕</button>
    </div>
    <p class="dlg-lede">Paste the link and pick a group. This opens a prefilled issue; CI prepares the card and a pull request — <strong>nothing merges automatically</strong>.</p>
    <p class="dlg-note"><strong>Reviewed, never auto-merged.</strong> A maintainer merges only after verifying the repository is public, relevant to the Galaxy XR, clearly licensed, and not already listed or proposed.</p>
    <label for="add-repo-url">Repository URL</label>
    <input id="add-repo-url" type="url" inputmode="url" placeholder="https://github.com/owner/name" autocomplete="off" spellcheck="false">
    <p class="dlg-status" id="add-repo-status" role="status" aria-live="polite"></p>
    <label for="add-repo-group">Group</label>
    <select id="add-repo-group">
      __GROUP_OPTIONS__
    </select>
    <label for="add-repo-about">Description <span class="opt">(optional)</span></label>
    <input id="add-repo-about" maxlength="160" placeholder="One short line — defaults to the repo's GitHub description" autocomplete="off">
    <div class="dlg-actions">
      <a class="add-submit" id="add-repo-issue" href="#" target="_blank" rel="noopener">Open GitHub issue</a>
      <span class="dlg-alt">Prefers a terminal? <code>python tools/add-repo.py &lt;url&gt; --group &lt;id&gt;</code></span>
    </div>
  </div>
</dialog>
<footer>
  <div class="wrap">
    <span>Unofficial community hub — not affiliated with Samsung. Each project keeps its own license.</span>
    <span>Add a repo: <a href="__REPO_URL__/issues/new?template=add-repo.md&labels=add-repo">file it from the site</a>, or run <code>python tools/add-repo.py</code> · <a href="#changelog">Changelog</a> · Agents: <a href="__REPO_URL__/blob/main/AGENTS.md">AGENTS.md</a></span>
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
    var shown = 0;
    var groupN = {};
    var statusN = { 'new': 0, fav: 0, done: 0, todo: 0 };
    cards.forEach(function (c) {
      var repo = c.dataset.repo;
      var fav = !!state.fav[repo];
      var done = !!state.done[repo];
      var isNew = isNewCard(c);
      var mark = { 'new': isNew, fav: fav, done: done, todo: !done };
      // Facet numbers: every figure in the rail counts the cards that would be
      // listed if that filter were picked, given the other active filters and the
      // search box. Group numbers ignore the group selection because those chips
      // are alternatives, not toggles; a status chip's own predicate is always
      // part of its count, so "Checked 0" means checking would show nothing.
      function pass() {
        for (var i = 0; i < active.length; i++) {
          if (!mark[active[i]]) return false;
        }
        return true;
      }
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
      var okMark = pass();
      if (okText && okMark) {
        groupN[c.dataset.group] = (groupN[c.dataset.group] || 0) + 1;
      }
      if (okText && okMark && okGroup) {
        // Status chips read as "what this filter shows right now", so they follow
        // the search box, the other status filters and the selected group.
        ['new', 'fav', 'done', 'todo'].forEach(function (s) {
          if (mark[s]) statusN[s]++;
        });
      }
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
    groupChips.forEach(function (ch) {
      var id = ch.dataset.group;
      var n = id === 'all'
        ? Object.keys(groupN).reduce(function (a, k) { return a + groupN[k]; }, 0)
        : (groupN[id] || 0);
      var b = ch.querySelector('b');
      if (b) b.textContent = n;
    });
    setCount('cnt-new', statusN['new']);
    setCount('cnt-fav', statusN.fav);
    setCount('cnt-done', statusN.done);
    setCount('cnt-todo', statusN.todo);
    if (count) count.textContent = shown;
    setCount('side-count', shown);
    if (empty) empty.style.display = shown ? 'none' : '';
  }

  if (q) q.addEventListener('input', function () { state.q = q.value; apply(); });
  groupChips.forEach(function (ch) {
    ch.addEventListener('click', function () {
      groupChips.forEach(function (c) {
        c.classList.toggle('is-active', c === ch);
        c.setAttribute('aria-pressed', c === ch ? 'true' : 'false');
      });
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

// Filters rail. Desktop: a sticky rail left of the catalog, collapsed and expanded
// with the Filters button, choice remembered in localStorage. Narrow screens: the
// same rail becomes an off-canvas drawer with a backdrop, closed on load and closed
// again by the X, the backdrop, Escape or the Show-N button. The Changelog view
// hides it (body.view-changelog).
(function () {
  var KEY = 'gxrforge.sidebar';
  var btn = document.getElementById('menu-btn');
  if (!btn) return;
  var closeBtn = document.getElementById('side-close');
  var doneBtn = document.getElementById('side-done');
  var backdrop = document.getElementById('backdrop');
  var mq = window.matchMedia('(max-width:1000px)');

  function drawerOpen() { return document.body.classList.contains('side-open'); }
  function drawer(isOpen) {
    document.body.classList.toggle('side-open', isOpen);
    if (backdrop) backdrop.hidden = !isOpen;
    btn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  }
  function rail(isOpen) {
    document.body.classList.toggle('side-closed', !isOpen);
    btn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    try { window.localStorage.setItem(KEY, isOpen ? '1' : '0'); } catch (e) {}
  }
  function sync() {
    var isOpen = mq.matches ? drawerOpen() : !document.body.classList.contains('side-closed');
    btn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  }
  window.gxrForgeCloseFilters = function () { if (mq.matches) drawer(false); };

  try { if (window.localStorage.getItem(KEY) === '0') document.body.classList.add('side-closed'); } catch (e) {}
  sync();

  btn.addEventListener('click', function () {
    if (mq.matches) drawer(!drawerOpen());
    else rail(document.body.classList.contains('side-closed'));
  });
  if (closeBtn) closeBtn.addEventListener('click', function () { drawer(false); });
  if (doneBtn) doneBtn.addEventListener('click', function () { drawer(false); });
  if (backdrop) backdrop.addEventListener('click', function () { drawer(false); });
  // Escape closes the panel; on phones the backdrop does the same. No click-away
  // on desktop: the rail is a filter panel you keep open while flagging cards, and
  // closing it on every card click made the catalog jump.
  document.addEventListener('keydown', function (ev) {
    if (ev.key !== 'Escape') return;
    if (drawerOpen()) drawer(false);
    else if (!mq.matches) rail(false);
  });
  function onBreak() { drawer(false); sync(); }
  if (mq.addEventListener) mq.addEventListener('change', onBreak);
  else if (mq.addListener) mq.addListener(onBreak);
})();

// Catalog / Changelog views. The active view is mirrored in the URL hash, so a
// link like #changelog opens the history directly.
(function () {
  var tabs = [].slice.call(document.querySelectorAll('.tab'));
  var views = { catalog: document.getElementById('catalog'), changelog: document.getElementById('changelog') };
  function show(view) {
    tabs.forEach(function (t) {
      var on = t.dataset.view === view;
      t.classList.toggle('is-active', on);
      t.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    Object.keys(views).forEach(function (k) {
      if (views[k]) views[k].hidden = k !== view;
    });
    // The filter rail belongs to the catalog view only; an open drawer also closes.
    document.body.classList.toggle('view-changelog', view !== 'catalog');
    if (view !== 'catalog' && typeof window.gxrForgeCloseFilters === 'function') window.gxrForgeCloseFilters();
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
  // Each helper resolves {ok, value, bad}; ok false means "could not determine",
  // bad true means shields answered with a word instead of a value. shields.io
  // does that whenever it cannot read the upstream data ("invalid" while its own
  // GitHub tokens are rate limited, "repo not found" for a dead repo): an error
  // string is not data, so it never becomes a pill, its badge image (which would
  // show the same word) is dropped, and nothing is cached from it.
  var BAD_VALUE = /invalid|not[ -]?found|no data|unable|error|rate limit|too many|unavailable/i;
  var NO_RELEASE = /no releases/i;
  var STARS_OK = /^[\\d.,]+[kM]?/;

  function fetchStars(repo) {
    return getJSON('https://img.shields.io/github/stars/' + repo + '.json')
      .then(function (d) {
        var v = String(d.value || '').trim();
        if (NO_RELEASE.test(v) || BAD_VALUE.test(v)) return { ok: false, bad: true, value: null };
        if (!STARS_OK.test(v)) return { ok: false, bad: false, value: null };
        return { ok: true, bad: false, value: v };
      })
      .catch(function () {
        return getJSON('https://ungh.cc/repos/' + repo)
          .then(function (d) {
            var n = (d.repo || {}).stars;
            if (!isFinite(Number(n))) return { ok: false, bad: false, value: null };
            return { ok: true, bad: false, value: compact(n) };
          })
          .catch(function () { return { ok: false, bad: false, value: null }; });
      });
  }
  function fetchRelease(repo) {
    return getJSON('https://img.shields.io/github/v/release/' + repo + '.json?include_prereleases')
      .then(function (d) {
        var v = String(d.value || '').trim();
        // "no releases" is definitive (the repo publishes none); other words are
        // shields failing, which is worth hiding and retrying.
        if (NO_RELEASE.test(v)) return { ok: true, bad: true, value: null };
        if (BAD_VALUE.test(v)) return { ok: false, bad: true, value: null };
        if (!v) return { ok: true, bad: false, value: null };
        return { ok: true, bad: false, value: v };
      })
      .catch(function () {
        return getJSON('https://ungh.cc/repos/' + repo + '/releases/latest')
          .then(function (d) {
            var tag = d.release && d.release.tag ? String(d.release.tag) : null;
            if (!tag) return { ok: false, bad: false, value: null };
            return { ok: true, bad: false, value: tag };
          })
          .catch(function () { return { ok: false, bad: false, value: null }; });
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
    if (data.rn && card.dataset.release) {
      // data-release marks the repos whose catalog entry has a single release
      // stream (release: null means per-module tags, where a "latest release"
      // badge would mislead). The live fetch refreshes that badge's value only,
      // it never adds a release to a card that was built without one.
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
        // Hide the badge image when shields answered with a word: the image would
        // render the same error text, so it carries no value worth keeping.
        var bd = card.querySelector('.badges');
        if (bd && stars.bad) dropImg(bd, 'stars');
        if (bd && rel.bad) dropImg(bd, 'release');
        if (!stars.ok && !rel.ok) return; // keep the badges; retry after the cache TTL
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

// Cursor glow: one fixed radial-gradient layer, eased toward the pointer in a
// single rAF loop and moved with a composited transform. Pointer devices only;
// reduced-motion users keep the static page and the loop stops when the pointer
// settles or the tab is hidden.
(function () {
  var glow = document.querySelector('.glow');
  if (!glow || !window.matchMedia) return;
  if (window.matchMedia('(pointer:coarse)').matches) return;
  if (window.matchMedia('(prefers-reduced-motion:reduce)').matches) return;
  var x = window.innerWidth / 2, y = window.innerHeight * 0.3, tx = x, ty = y, raf = 0, on = false;
  glow.style.setProperty('--gx', x + 'px');
  glow.style.setProperty('--gy', y + 'px');
  function frame() {
    raf = 0;
    x += (tx - x) * 0.16;
    y += (ty - y) * 0.16;
    if (Math.abs(tx - x) < 0.4 && Math.abs(ty - y) < 0.4) { x = tx; y = ty; }
    glow.style.setProperty('--gx', x.toFixed(1) + 'px');
    glow.style.setProperty('--gy', y.toFixed(1) + 'px');
    if (x !== tx || y !== ty) raf = window.requestAnimationFrame(frame);
  }
  window.addEventListener('pointermove', function (ev) {
    if (ev.pointerType === 'touch') return;
    tx = ev.clientX; ty = ev.clientY;
    if (!on) { on = true; document.body.classList.add('glow-on'); }
    if (!raf) raf = window.requestAnimationFrame(frame);
  }, { passive: true });
  function fade() { on = false; document.body.classList.remove('glow-on'); }
  document.documentElement.addEventListener('mouseleave', fade);
  window.addEventListener('blur', fade);
})();

// "Add repo" dialog. Pages is static, so the form cannot post anywhere itself:
// it builds a prefilled GitHub issue, and the add-repo workflow turns that issue
// into a branch and a pull request. Without JS the button is a plain link to the
// issue template.
(function () {
  var dlg = document.getElementById('add-repo-dialog');
  var btn = document.getElementById('add-repo-btn');
  if (!dlg || !btn) return;
  var closeBtn = document.getElementById('add-repo-close');
  var urlInput = document.getElementById('add-repo-url');
  var groupSel = document.getElementById('add-repo-group');
  var aboutInput = document.getElementById('add-repo-about');
  var go = document.getElementById('add-repo-issue');
  var BASE = '__REPO_URL__';

  function openDlg() {
    if (typeof dlg.showModal === 'function') { dlg.showModal(); } else { dlg.setAttribute('open', ''); }
    refresh();
    window.setTimeout(function () { urlInput.focus(); }, 40);
  }
  function closeDlg() {
    if (typeof dlg.close === 'function') { dlg.close(); } else { dlg.removeAttribute('open'); }
  }

  function issueHref() {
    var raw = (urlInput.value || '').trim();
    if (raw.slice(-4) === '.git') raw = raw.slice(0, -4);
    while (raw.slice(-1) === '/') raw = raw.slice(0, -1);
    var parts = raw.split('/');
    if (parts.length !== 5 || parts[0] !== 'https:' || parts[1] !== '' ||
        parts[2] !== 'github.com' || !parts[3] || !parts[4]) return null;
    var m = [raw, parts[3], parts[4]];
    if (m[1].indexOf('?') !== -1 || m[2].indexOf('?') !== -1) return null;
    var body = '### Repo URL\\nhttps://github.com/' + m[1] + '/' + m[2] +
      '\\n\\n### Group\\n' + groupSel.value + '\\n';
    var about = (aboutInput.value || '').trim();
    if (about) body += '\\n### About\\n' + about + '\\n';
    return BASE + '/issues/new?labels=' + encodeURIComponent('add-repo') +
      '&title=' + encodeURIComponent('Add repo: ' + m[1] + '/' + m[2]) +
      '&body=' + encodeURIComponent(body);
  }

  function refresh() {
    var href = issueHref();
    go.href = href || '#';
    var blocked = window.__gxrDup === true;
    go.classList.toggle('is-disabled', !href || blocked);
    go.setAttribute('aria-disabled', (!href || blocked) ? 'true' : 'false');
  }

  btn.addEventListener('click', function (ev) {
    if (typeof dlg.showModal !== 'function') return; // plain link fallback
    ev.preventDefault();
    openDlg();
  });
  if (closeBtn) closeBtn.addEventListener('click', closeDlg);
  dlg.addEventListener('click', function (ev) { if (ev.target === dlg) closeDlg(); });
  [urlInput, aboutInput].forEach(function (el) { if (el) el.addEventListener('input', refresh); });
  if (groupSel) groupSel.addEventListener('change', refresh);
  go.addEventListener('click', function (ev) {
    if (!issueHref()) { ev.preventDefault(); urlInput.focus(); }
  });
  refresh();
  if (location.hash === '#add-repo') openDlg();
})();

// Duplicate check: the generated catalog index plus open `add-repo` issues. The
// page check is advisory and can fail offline; add-repo.py re-checks server-side
// (catalog, open issues, open PRs) before it writes anything.
(function () {
  var input = document.getElementById('add-repo-url');
  var status = document.getElementById('add-repo-status');
  var btn = document.getElementById('add-repo-btn');
  if (!input || !status) return;
  var indexP = null, propP = null, timer = 0, seq = 0;

  function norm(u) {
    var t = (u || '').trim();
    if (t.slice(-4) === '.git') t = t.slice(0, -4);
    while (t.slice(-1) === '/') t = t.slice(0, -1);
    return t.toLowerCase();
  }
  function key() {
    var t = norm(input.value).replace('https://github.com/', '');
    var p = t.split('/');
    return (p.length === 2 && p[0] && p[1]) ? p[0] + '/' + p[1] : null;
  }
  function loadIndex() {
    if (!indexP) {
      indexP = fetch('catalog-index.json?t=' + Date.now())
        .then(function (r) { return r.ok ? r.json() : { repos: [] }; })
        .then(function (d) {
          var s = {};
          (d.repos || []).forEach(function (x) { s[x.repo.toLowerCase()] = 1; });
          return s;
        })
        .catch(function () { return {}; });
    }
    return indexP;
  }
  function loadProposals() {
    if (!propP) {
      propP = fetch('https://api.github.com/search/issues?q=' +
        encodeURIComponent('repo:__REPO_SLUG__ is:open label:add-repo') + '&per_page=100')
        .then(function (r) { return r.ok ? r.json() : { items: [] }; })
        .then(function (d) {
          var s = {}, NL = String.fromCharCode(10);
          (d.items || []).forEach(function (it) {
            (it.body || '').split(NL).forEach(function (line) {
              var t = line.trim();
              if (t.indexOf('https://github.com/') === 0) {
                var k = norm(t).replace('https://github.com/', '');
                if (k) s[k] = it.number;
              }
            });
          });
          return s;
        })
        .catch(function () { return {}; });
    }
    return propP;
  }
  function set(state, text) {
    status.className = 'dlg-status' + (state ? ' ' + state : '');
    status.textContent = text || '';
    var go = document.getElementById('add-repo-issue');
    var blocked = state === 'warn';
    window.__gxrDup = blocked;
    if (go) {
      var href = go.getAttribute('href');
      var bad = blocked || !href || href === '#';
      go.classList.toggle('is-disabled', bad);
      go.setAttribute('aria-disabled', bad ? 'true' : 'false');
    }
  }
  function check() {
    var k = key();
    var mine = ++seq;
    if (!k) { set('', ''); return; }
    set('', 'Checking the catalog and open proposals…');
    Promise.all([loadIndex(), loadProposals()]).then(function (res) {
      if (mine !== seq) return;
      if (res[0][k]) { set('warn', 'Already in the catalog: ' + k); return; }
      if (res[1][k]) { set('warn', 'Already proposed in #' + res[1][k] + ' — wait for that one.'); return; }
      set('ok', 'Not listed, not proposed. A maintainer reviews it before anything merges.');
    });
  }
  input.addEventListener('input', function () {
    window.clearTimeout(timer);
    timer = window.setTimeout(check, 450);
  });
  if (btn) btn.addEventListener('click', function () { window.setTimeout(check, 60); });
})();
</script>
</body>
</html>
"""


def render_group_options(cat):
    return "\n      ".join(
        f'<option value="{g["id"]}">{g["icon"]} {html.escape(g["title"])}</option>'
        for g in cat["groups"]
    )


def inline_md(text):
    """Escape, then honour the inline markers changelog entries use: `code` and **bold**."""
    s = html.escape(str(text))
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)


def render_changelog_view(changelog):
    entries = []
    for e in changelog["entries"]:
        items = "".join(f"<li>{inline_md(i)}</li>" for i in e["items"])
        entries.append(
            f'<li class="entry"><div class="entry-head">'
            f'<time datetime="{e["date"]}">{e["date"]}</time>'
            f'<h3>{inline_md(e["title"])}</h3></div><ul>{items}</ul></li>'
        )
    return (
        '<section class="changelog"><h2>Changelog</h2>'
        '<p class="blurb">Every catalog change — repos added, moved or removed. Newest first.</p>'
        f'<ol class="entries">{"".join(entries)}</ol></section>'
    )


def render_site(cat, changelog):
    total = sum(len(g["repos"]) for g in cat["groups"])
    updated = newest_date(cat, changelog)
    page = SITE_TEMPLATE
    page = page.replace("__TAGLINE__", html.escape(TAGLINE, quote=True))
    page = page.replace("__TOTAL__", str(total))
    page = page.replace("__GROUPS__", str(len(cat["groups"])))
    page = page.replace("__DATE__", updated)
    page = page.replace("__CHIPS__", render_chips(cat))
    page = page.replace("__STATUS__", render_status_chips(cat))
    page = page.replace("__SECTIONS__", render_sections(cat))
    page = page.replace("__CHANGELOG_COUNT__", str(len(changelog.get("entries", []))))
    page = page.replace("__GROUP_OPTIONS__", render_group_options(cat))
    page = page.replace("__CHANGELOG__", render_changelog_view(changelog))
    page = page.replace("__REPO_SLUG__", REPO_URL.split("github.com/")[-1])
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
    index = {
        "updated": newest_date(cat, changelog),
        "repos": [
            {"repo": r["repo"], "url": r["url"], "group": g["id"]}
            for g in cat["groups"]
            for r in g["repos"]
        ],
    }
    INDEX_PATH.write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
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
