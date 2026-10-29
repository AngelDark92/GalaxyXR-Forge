#!/usr/bin/env python
"""Build the Galaxy XR Forge index.

    catalog.json (groups) + catalog.d/ (one file per repo)
    + modules.d/ (one file per module-publishing repo)
    + news.d/ (one file per news post)
    + changelog.d/ (one file per change)
        ->  README.md + CHANGELOG.md + docs/index.html + docs/catalog-index.json

Usage:
    python tools/build.py           validate, then write the generated files
    python tools/build.py --check   validate the inputs only

Rules:
    - catalog.json is the single source of truth for the repo list; modules.d/
      holds the module detail used by the Kernel modules tab; news.d/ holds the
      posts shown on the News tab; changelog.d/ holds the change history. Never
      hand-edit README.md, CHANGELOG.md or docs/index.html: edit the inputs and
      rerun this script.
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
MODULES_DIR = ROOT / "modules.d"
NEWS_DIR = ROOT / "news.d"
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
        files = folder.glob("*.json") if folder.is_dir() else []
        # pathlib orders case-insensitively on Windows and by bytes on POSIX; name
        # keys keep the card order identical on every host (CI included).
        for path in sorted(files, key=lambda f: (f.name.lower(), f.name)):
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


MODULE_STATUSES = ("stable", "experimental", "deprecated", "internal")
MODULE_STATUS_LABEL = {
    "experimental": "Experimental",
    "deprecated": "Deprecated",
    "internal": "Internal",
}


def load_modules(cat):
    """Module records from modules.d/<owner>__<name>.json, one file per repo.

    Kept beside the catalog instead of inside a card entry: a repo can list 19
    modules without bloating its catalog file, and repairing a catalog entry
    cannot drop them. Sorted by catalog group, then repo name, so the site order
    is stable on every host.
    """
    if not MODULES_DIR.is_dir():
        return []
    group_order = {g["id"]: i for i, g in enumerate(cat.get("groups", []))}
    repo_group = {
        r["repo"].lower(): g["id"]
        for g in cat.get("groups", [])
        for r in g.get("repos", [])
    }
    entries = []
    for path in sorted(MODULES_DIR.glob("*.json"), key=lambda f: (f.name.lower(), f.name)):
        with path.open(encoding="utf-8") as f:
            entry = json.load(f)
        entry["_file"] = path.name
        entry["_group"] = repo_group.get(str(entry.get("repo", "")).lower(), "")
        entries.append(entry)
    entries.sort(
        key=lambda e: (
            group_order.get(e.get("_group", ""), 999),
            str(e.get("repo", "")).lower(),
        )
    )
    return entries


def is_date(value):
    """True for a YYYY-MM-DD string; catalog and module files share the shape."""
    return (
        isinstance(value, str)
        and len(value) == 10
        and value[4] == "-"
        and value[7] == "-"
        and value[:4].isdigit()
        and value[5:7].isdigit()
        and value[8:].isdigit()
    )


def validate_modules(cat, module_index):
    """Validate modules.d against the catalog. Returns (errors, warnings)."""
    errors = []
    warnings = []
    catalog = {
        r["repo"].lower()
        for g in cat.get("groups", [])
        for r in g.get("repos", [])
    }
    seen_repos = set()
    for entry in module_index:
        path = entry.get("_file", "?")
        repo = str(entry.get("repo", ""))
        if repo.count("/") != 1:
            errors.append(f"modules.d/{path}: bad repo field {repo!r}")
            continue
        owner, name = repo.split("/", 1)
        want = f"{owner}__{name}.json"
        if path.lower() != want.lower():
            errors.append(
                f"modules.d/{path}: file name does not match repo {repo} (want {want})"
            )
        if repo.lower() not in catalog:
            errors.append(f"modules.d/{path}: repo {repo} is not in the catalog")
        if repo.lower() in seen_repos:
            errors.append(f"modules.d/{path}: duplicate repo {repo}")
        seen_repos.add(repo.lower())

        if not is_date(entry.get("checked")):
            errors.append(
                f"modules.d/{path}: bad checked date {entry.get('checked')!r} "
                "(want YYYY-MM-DD)"
            )
        note = entry.get("note")
        if note is not None and (not isinstance(note, str) or len(note) > 240):
            errors.append(
                f"modules.d/{path}: note must be a string of at most 240 chars"
            )

        mods = entry.get("modules")
        if not isinstance(mods, list) or not mods:
            errors.append(f"modules.d/{path}: modules must be a non-empty list")
            continue
        seen_ids = set()
        for m in mods:
            if not isinstance(m, dict):
                errors.append(f"modules.d/{path}: module records must be objects")
                continue
            mid = str(m.get("id", "")).strip()
            mname = str(m.get("name", "")).strip()
            about = str(m.get("about", "")).strip()
            status = m.get("status", "stable")
            if not mid:
                errors.append(f"modules.d/{path}: module without id")
            elif mid in seen_ids:
                errors.append(f"modules.d/{path}: duplicate module id {mid}")
            seen_ids.add(mid)
            if not mname:
                errors.append(f"modules.d/{path}: {mid or '?'} has no name")
            if not about:
                errors.append(f"modules.d/{path}: {mid or '?'} has no about")
            elif len(about) > 160:
                errors.append(
                    f"modules.d/{path}: {mid or '?'} about too long ({len(about)} chars)"
                )
            if status not in MODULE_STATUSES:
                errors.append(
                    f"modules.d/{path}: {mid or '?'} bad status {status!r} "
                    f"(want one of {', '.join(MODULE_STATUSES)})"
                )

    module_group = next(
        (g for g in cat.get("groups", []) if g["id"] == "kernelsu-modules"), None
    )
    if module_group:
        for r in module_group.get("repos", []):
            if r["repo"].lower() not in seen_repos:
                warnings.append(
                    f"modules.d: {r['repo']} is in kernelsu-modules "
                    "but has no module records"
                )
    return errors, warnings


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
            if added is not None and not is_date(added):
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
        entries.sort(
            key=lambda e: (str(e.get("date", "")), e["_file"].lower(), e["_file"]), reverse=True
        )
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
        "Catalog changes, newest first. Generated from [`changelog.d/`](changelog.d/) "
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
# news loading and validation
# ---------------------------------------------------------------------------


NEWS_KINDS = ("site", "release", "community", "guide")
NEWS_KIND_LABEL = {
    "site": "Site update",
    "release": "Release",
    "community": "Community",
    "guide": "Guide",
}
NEWS_FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-([a-z0-9][a-z0-9-]{0,59})$")
NEWS_MAX_TITLE = 120
NEWS_MAX_SUMMARY = 200
NEWS_MAX_PARAGRAPHS = 8
NEWS_MAX_PARAGRAPH = 800
NEWS_MAX_LINKS = 4
NEWS_MAX_LABEL = 60
MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


def load_news():
    """Posts from news.d/<YYYY-MM-DD>-<slug>.json, newest first.

    One file per post, like catalog.d/: two pending submissions add different
    files and cannot conflict. The date is in the file name so the feed order is
    identical on every host, and a rebase rewrites the file without re-dating it.
    A string `body` is accepted for hand-written files and split on blank lines.
    """
    if not NEWS_DIR.is_dir():
        return {"entries": []}
    entries = []
    for path in sorted(NEWS_DIR.glob("*.json"), key=lambda f: (f.name.lower(), f.name)):
        with path.open(encoding="utf-8") as f:
            entry = json.load(f)
        entry["_file"] = path.name
        body = entry.get("body")
        if isinstance(body, str):
            entry["body"] = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        entries.append(entry)
    entries.sort(
        key=lambda e: (str(e.get("date", "")), e["_file"].lower(), e["_file"]), reverse=True
    )
    return {"entries": entries}


def validate_news(news, cat):
    """Validate news.d against the schema and the catalog. Returns (errors, warnings)."""
    errors = []
    warnings = []
    catalog = {
        r["repo"].lower(): g
        for g in cat.get("groups", [])
        for r in g.get("repos", [])
    }
    seen = set()
    today = date.today()
    for entry in news.get("entries", []):
        name = entry.get("_file", "?")
        stem = name[:-5] if name.endswith(".json") else name
        label = f"news.d/{name}"
        m = NEWS_FILE_RE.match(stem)
        if not m:
            errors.append(f"{label}: file name must be YYYY-MM-DD-slug.json")
            continue
        file_date, slug = m.group(1), m.group(2)
        when = entry.get("date")
        if when != file_date:
            errors.append(f"{label}: date {when!r} does not match the file name")
        day = None
        try:
            day = date.fromisoformat(str(when))
        except ValueError:
            errors.append(f"{label}: bad date {when!r} (want YYYY-MM-DD)")
        if day and day > today:
            errors.append(f"{label}: date {when} is in the future")
        if (when, slug) in seen:
            errors.append(f"{label}: duplicate post for {when} ({slug})")
        seen.add((when, slug))

        title = entry.get("title")
        if not isinstance(title, str) or not title.strip():
            errors.append(f"{label}: missing title")
        elif len(title) > NEWS_MAX_TITLE:
            errors.append(
                f"{label}: title too long ({len(title)} chars, max {NEWS_MAX_TITLE})"
            )

        summary = entry.get("summary")
        if summary is not None:
            if not isinstance(summary, str) or not summary.strip():
                errors.append(f"{label}: summary must be a non-empty string or omitted")
            elif len(summary) > NEWS_MAX_SUMMARY:
                errors.append(
                    f"{label}: summary too long ({len(summary)} chars, max {NEWS_MAX_SUMMARY})"
                )

        kind = entry.get("kind", "community")
        if kind not in NEWS_KINDS:
            errors.append(
                f"{label}: bad kind {kind!r} (want one of {', '.join(NEWS_KINDS)})"
            )

        body = entry.get("body")
        if not isinstance(body, list) or not body:
            errors.append(f"{label}: body must be a non-empty list of paragraphs")
        else:
            if len(body) > NEWS_MAX_PARAGRAPHS:
                errors.append(
                    f"{label}: body has {len(body)} paragraphs (max {NEWS_MAX_PARAGRAPHS})"
                )
            for i, para in enumerate(body, 1):
                if not isinstance(para, str) or not para.strip():
                    errors.append(f"{label}: body paragraph {i} is empty")
                elif len(para) > NEWS_MAX_PARAGRAPH:
                    errors.append(
                        f"{label}: body paragraph {i} is too long "
                        f"({len(para)} chars, max {NEWS_MAX_PARAGRAPH})"
                    )

        links = entry.get("links") or []
        if not isinstance(links, list):
            errors.append(f"{label}: links must be a list")
        elif len(links) > NEWS_MAX_LINKS:
            errors.append(f"{label}: {len(links)} links (max {NEWS_MAX_LINKS})")
        else:
            for i, link in enumerate(links, 1):
                if not isinstance(link, dict):
                    errors.append(f"{label}: link {i} must be an object")
                    continue
                text = str(link.get("label", "")).strip()
                url = str(link.get("url", "")).strip()
                if not text or len(text) > NEWS_MAX_LABEL:
                    errors.append(
                        f"{label}: link {i} needs a label of at most {NEWS_MAX_LABEL} chars"
                    )
                if not url.startswith("https://") or " " in url or "." not in url[8:]:
                    errors.append(f"{label}: link {i} must be an absolute https:// URL")

        repo = entry.get("repo")
        if repo:
            if not isinstance(repo, str) or repo.count("/") != 1 or not all(repo.split("/")):
                errors.append(f"{label}: bad repo field {repo!r} (want owner/name)")
            elif repo.lower() not in catalog:
                warnings.append(
                    f"{label}: repo {repo} is not in the catalog "
                    "(the post renders it as plain text)"
                )

        author = entry.get("author")
        if author is not None and (
            not isinstance(author, str)
            or not re.fullmatch(r"[A-Za-z0-9-]{1,39}", author)
        ):
            errors.append(f"{label}: author must be a GitHub handle")
    return errors, warnings


def news_slug(title):
    """File-name slug for a title: lowercase words joined by single dashes."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(title).lower()).strip("-")[:60].strip("-")
    return slug or "news"


def news_path(day, slug):
    return NEWS_DIR / f"{day}-{slug}.json"


def write_news_entry(entry, slug=None):
    """Write one news.d file; a same-day slug collision gets a numeric suffix.

    `slug` is not stored in the file: the file name is the identity and the date
    prefix keeps it sortable. The date itself is data — a rebase rewrites the file
    with the original date, never today's.
    """
    day = str(entry["date"])
    base = slug or news_slug(entry.get("title", ""))
    path = news_path(day, base)
    n = 2
    while path.exists():
        path = news_path(day, f"{base}-{n}")
        n += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = {k: v for k, v in entry.items() if k not in ("slug", "_file")}
    path.write_text(dump_json(clean), encoding="utf-8", newline="\n")
    return path


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
    A("[![PRs welcome](https://img.shields.io/badge/PRs-welcome-2ea44f?style=flat-square)](#suggest-a-repo)")
    A(f"[![GitHub stars](https://img.shields.io/github/stars/AngelDark92/GalaxyXR-Forge?style=flat-square&label=star)]({REPO_URL})")
    A(f"[![last commit](https://img.shields.io/github/last-commit/AngelDark92/GalaxyXR-Forge?style=flat-square)]({REPO_URL}/commits/main)")
    A("")
    nav = " · ".join(f'[{g["icon"]} {g["title"]}](#{g["id"]})' for g in groups)
    A(f"<sub>{nav}</sub>")
    A("")
    A(f"⭐ **[Star this repo]({REPO_URL})** — it helps other Galaxy XR owners find the index.")
    A("")
    A(f"📰 **[News]({SITE_URL}/#news)** — releases, guides and site updates from the community.")
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
    A("## Suggest a repo")
    A("")
    A(
        f"**Fastest:** use the **Suggest a repo** button on the [site]({SITE_URL}/#suggest-a-repo) — paste the link, pick a group. "
        "CI prepares the card and a pull request; nothing is added until a maintainer reviews and merges it."
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
  --tab-h:44px; --hero-bleed:1px;
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
/* Hero */
.hero{position:relative;overflow:hidden;border-bottom:var(--hero-bleed) solid var(--line);
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
.hero .wrap{position:relative;padding-top:48px;padding-bottom:32px}
.hero-top{display:flex;align-items:flex-start;justify-content:space-between;gap:24px}
.hero-brand{flex:1;min-width:0}
.kicker{font:500 12px var(--font-mono);letter-spacing:.22em;text-transform:uppercase;color:var(--accent);margin:0 0 14px}
h1{font:700 clamp(2.3rem,5.4vw,3.5rem)/1.05 var(--font-disp);letter-spacing:-.02em;margin:0 0 14px}
h1 .accent{background:linear-gradient(90deg,var(--accent),var(--accent-2));-webkit-background-clip:text;background-clip:text;color:transparent}
.tagline{max-width:680px;color:var(--muted);font-size:16.5px;margin:0 0 28px}
.stats{display:flex;flex-wrap:wrap}
.stat{padding:0 24px;border-left:1px solid var(--line-2)}
.stat:first-child{padding-left:0;border-left:0}
.stat b{display:block;font:600 22px var(--font-mono);color:var(--ink)}
.stat span{font:12px var(--font-mono);color:var(--dim);text-transform:uppercase;letter-spacing:.08em}
/* Hero actions */
.hero-actions{display:flex;align-items:center;gap:10px;flex:none;flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;gap:7px;border-radius:10px;padding:8px 16px;font:600 13px var(--font-mono);cursor:pointer;text-decoration:none;border:1px solid var(--line-2);min-height:36px;white-space:nowrap}
.btn-primary{background:linear-gradient(90deg,var(--accent),var(--accent-2));color:#180b02;border-color:transparent}
.btn-primary:hover{filter:brightness(1.08)}
.btn-ghost{background:transparent;color:var(--muted);border-color:var(--line-2)}
.btn-ghost:hover{color:var(--ink);border-color:var(--muted)}
.btn-sm{padding:6px 12px;font-size:12.5px;min-height:32px}
.btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media (max-width:760px){
  .hero-top{flex-direction:column}
  .hero-actions{width:100%}
}
@media (max-width:640px){
  .hero .wrap{padding-top:38px;padding-bottom:24px}
  .stat{padding:0 14px}
  .stat b{font-size:18px}
}
/* Tab bar */
.tabbar{position:sticky;top:0;z-index:29;background:rgba(10,14,20,.96);border-bottom:1px solid var(--line);
  backdrop-filter:blur(12px) saturate(140%);-webkit-backdrop-filter:blur(12px) saturate(140%)}
.tabbar-inner{max-width:1120px;margin:0 auto;padding:0 22px;display:flex;align-items:stretch;gap:2px;overflow-x:auto;overflow-y:hidden;scrollbar-width:none}
.tabbar-inner::-webkit-scrollbar{display:none}
.tab{position:relative;display:inline-flex;align-items:center;gap:7px;border:0;background:transparent;color:var(--muted);padding:0 14px;font:500 13px var(--font-mono);cursor:pointer;min-height:var(--tab-h);white-space:nowrap;border-bottom:2px solid transparent;margin-bottom:-1px;flex:none}
.tab svg{width:14px;height:14px;flex:none;opacity:.9}
.tab b{font-weight:500;color:var(--dim);background:rgba(148,163,184,.14);border-radius:99px;padding:1px 7px;font-size:11.5px}
.tab:hover{color:var(--ink)}
.tab.is-active{color:var(--ink);border-bottom-color:var(--accent);background:rgba(249,115,22,.08)}
.tab.is-active b{color:var(--ink);background:rgba(249,115,22,.18)}
.tab:focus-visible{outline:2px solid var(--accent);outline-offset:-2px;border-radius:4px}
.tab .tab-long{ } .tab .tab-short{display:none}
@media (max-width:700px){
  .tab .tab-long{display:none} .tab .tab-short{display:inline}
}
@media (max-width:560px){
  .tab b{display:none}
  .tab svg{display:none}
  .tab{padding:0 11px;font-size:12.5px;gap:4px}
}
.tabbar-inner{
  -webkit-mask-image:linear-gradient(90deg,#000 calc(100% - 18px),transparent 100%);
  mask-image:linear-gradient(90deg,#000 calc(100% - 18px),transparent 100%);
}
/* Shell / sidebar */
.shell{max-width:1120px;margin:0 auto;padding:26px 22px 0;display:grid;grid-template-columns:308px minmax(0,1fr);gap:26px;align-items:start}
.content{min-width:0}
.side{position:sticky;top:calc(var(--tab-h) + 12px);max-height:calc(100vh - var(--tab-h) - 24px);overflow:auto;display:flex;flex-direction:column;gap:0;padding:0;width:308px;border:1px solid var(--line);border-radius:12px;background:var(--card);box-shadow:0 12px 40px -20px rgba(0,0,0,.5);scrollbar-width:thin}
.side::-webkit-scrollbar{width:8px}
.side::-webkit-scrollbar-track{background:transparent}
.side::-webkit-scrollbar-thumb{background:var(--line-2);border-radius:8px}
.side::-webkit-scrollbar-thumb:hover{background:var(--muted)}
.side-head{display:none;align-items:center;justify-content:space-between;padding:14px 16px;border-bottom:1px solid var(--line)}
.side-title{font:600 12px var(--font-disp);letter-spacing:.16em;text-transform:uppercase;color:var(--accent)}
.side-close{display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border:1px solid var(--line-2);background:transparent;color:var(--muted);border-radius:9px;cursor:pointer}
.side-close:hover{border-color:var(--muted);color:var(--ink)}
.side-close svg{width:13px;height:13px}
.side-section{display:flex;flex-direction:column;gap:0;min-width:0;padding:14px 14px 16px;border-bottom:1px solid var(--line)}
.side-section:last-of-type{border-bottom:0}
.side-label{font:500 10.5px var(--font-mono);letter-spacing:.16em;text-transform:uppercase;color:var(--dim);margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--line)}
.side-foot{padding:12px 14px}
.side-clear{width:100%;border:0;background:transparent;color:var(--muted);font:500 12.5px var(--font-mono);cursor:pointer;padding:8px;text-align:center}
.side-clear:hover{color:var(--accent)}
#q{width:100%;background:var(--bg);border:1px solid var(--line-2);color:var(--ink);border-radius:9px;padding:9px 12px;font:13px var(--font-sans);outline:none}
#q:focus{border-color:var(--accent)}
#q::placeholder{color:var(--dim)}
.chips{display:flex;flex-direction:column;gap:6px;min-width:0}
.chip{display:flex;align-items:center;gap:9px;width:100%;border:1px solid var(--line);background:transparent;color:var(--muted);border-radius:9px;padding:8px 11px;font:500 12.5px var(--font-mono);cursor:pointer;min-height:34px;text-align:left}
.chip .dot{width:8px;height:8px;border-radius:50%;background:var(--hue,var(--line-2));flex:none}
.chip .lbl{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.chip b{margin-left:auto;flex:none;font-weight:500;color:var(--dim);background:rgba(148,163,184,.12);border-radius:99px;padding:1px 6px;font-size:11px}
.chip:hover{border-color:var(--muted);color:var(--ink)}
.chip:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.chip.is-active{color:var(--ink);background:rgba(249,115,22,.10);border-color:var(--hue, var(--accent))}
.chip.is-active b{color:var(--ink);background:rgba(249,115,22,.18)}
.chip[data-status="new"].is-active{border-color:rgba(249,115,22,.45);background:rgba(249,115,22,.12)}
.chip[data-status="fav"].is-active{border-color:rgba(251,191,36,.45);background:rgba(251,191,36,.12)}
.chip[data-status="done"].is-active{border-color:rgba(52,211,153,.45);background:rgba(52,211,153,.12)}
.chip[data-status="todo"].is-active{border-color:var(--muted);background:rgba(148,163,184,.10)}
.side-done{display:none;align-items:center;justify-content:center;gap:8px;width:100%;border:1px solid rgba(249,115,22,.55);background:rgba(249,115,22,.14);color:var(--ink);border-radius:10px;padding:11px 14px;font:500 13px var(--font-mono);cursor:pointer;min-height:42px}
.side-done:hover{background:rgba(249,115,22,.24)}
.side-done b{color:var(--accent-2);font-weight:600}
.backdrop{display:none}
#catalog,#modules,#changelog,#news{scroll-margin-top:calc(var(--tab-h) + 16px)}
body.view-noncatalog .side{display:none}
body.view-noncatalog .shell{grid-template-columns:minmax(0,1fr)}
@media (min-width:1001px){
  body.side-closed .shell{grid-template-columns:0 minmax(0,1fr);gap:0}
  body.side-closed .side{opacity:0;visibility:hidden;pointer-events:none}
}
@media (min-width:1840px){
  .shell{grid-template-columns:0 minmax(0,1fr);gap:0}
  .side{width:308px;margin-left:-334px}
}
@media (max-width:1000px){
  .shell{grid-template-columns:minmax(0,1fr);padding-top:20px}
  .side{position:fixed;top:0;bottom:0;left:0;z-index:60;width:min(320px,86vw);max-height:none;border-radius:0 16px 16px 0;border-left:0;padding:0;background:var(--card);transform:translateX(-104%);visibility:hidden;transition:transform .24s cubic-bezier(.2,.9,.3,1.1),visibility 0s linear .24s;overflow:auto}
  body.side-open .side{transform:none;visibility:visible;box-shadow:0 40px 90px -30px #000;transition:transform .24s cubic-bezier(.2,.9,.3,1.1),visibility 0s linear 0s}
  .side-head{display:flex}
  .side-done{display:flex}
  .side-done-wrap{padding:14px 16px;border-top:1px solid var(--line)}
  .backdrop:not([hidden]){display:block;position:fixed;inset:0;z-index:50;background:rgba(4,7,11,.60);-webkit-backdrop-filter:blur(3px);backdrop-filter:blur(3px)}
}
@media (prefers-reduced-motion:reduce){.side{transition:none}}
/* View headers */
.view-head{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;padding:8px 0 20px;border-bottom:1px solid var(--line);margin-bottom:20px}
.view-head-text{flex:1;min-width:0}
.eyebrow{font:500 11px var(--font-mono);letter-spacing:.18em;text-transform:uppercase;color:var(--accent);margin:0 0 6px}
.view-head h2{font:600 1.35rem var(--font-disp);margin:0 0 6px}
.view-head-meta{flex:none;align-self:center;font:500 12px var(--font-mono);color:var(--muted);white-space:nowrap}
.changelog{max-width:820px;padding:6px 0 10px}
.changelog h2{font:600 1.35rem var(--font-disp);margin:0 0 6px}
.entries{list-style:none;margin:0;padding:0}
.entry{border-top:1px solid var(--line);padding:18px 0}
.entry:first-child{border-top:0}
.entry-head{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.entry-head time{font:500 12.5px var(--font-mono);color:var(--accent);letter-spacing:.06em}
.entry-head h3{font:600 16px var(--font-disp);margin:0}
.entry ul{margin:8px 0 0;padding-left:20px;color:var(--muted);font-size:14px}
.entry li{margin:4px 0}
.mods{max-width:820px;padding:6px 0 10px}
.mods h2{font:600 1.35rem var(--font-disp);margin:0 0 6px}
.mod-repo{margin:0 0 34px}
.mod-head{display:flex;align-items:baseline;gap:10px 12px;flex-wrap:wrap;padding-bottom:10px;border-bottom:1px solid var(--line)}
.mod-head h3{display:flex;align-items:center;gap:9px;font:600 18px/1.3 var(--font-disp);margin:0;min-width:0;overflow-wrap:anywhere}
.mod-head h3 .dot{width:9px;height:9px;border-radius:3px;background:var(--hue);flex:none}
.mod-head h3 .owner{font:400 13px var(--font-mono);color:var(--dim)}
.mod-head h3 a{min-width:0;overflow-wrap:anywhere}
.mod-head h3 a:hover{color:var(--accent-2)}
.grp{display:inline-flex;align-items:center;gap:6px;padding:2px 9px;border:1px solid var(--line-2);border-radius:999px;font:500 10.5px var(--font-mono);color:var(--muted);white-space:nowrap}
.mod-meta{margin-left:auto;display:flex;align-items:center;gap:6px 14px;flex-wrap:wrap;font:11.5px var(--font-mono);color:var(--dim)}
.mod-meta a{color:var(--muted)}
.mod-meta a:hover{color:var(--accent)}
.mod-note{margin:10px 0 0;color:var(--dim);font-size:13px}
.mod-list{list-style:none;margin:14px 0 0;padding:0;display:grid;gap:10px}
.mod-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px 14px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:13px 15px}
.mod-row h4{display:flex;align-items:baseline;gap:9px;flex-wrap:wrap;margin:0;font:600 14.5px var(--font-disp);min-width:0;overflow-wrap:anywhere}
.mod-row h4 code{font-size:11.5px;color:var(--dim);background:transparent;border:0;padding:0;overflow-wrap:anywhere}
.mod-row p{grid-column:1/-1;margin:0;color:var(--muted);font-size:13.5px;overflow-wrap:anywhere}
.mod-tag{justify-self:end;padding:2px 8px;border:1px solid var(--line-2);border-radius:999px;font:600 10px/1.7 var(--font-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted);white-space:nowrap}
.mod-tag.experimental{color:#fbbf24;border-color:rgba(251,191,36,.45);background:rgba(251,191,36,.10)}
.mod-tag.deprecated{color:#fb7185;border-color:rgba(251,113,133,.45);background:rgba(251,113,133,.10)}
.mod-tag.internal{color:#94a3b8;border-color:rgba(148,163,184,.35);background:rgba(148,163,184,.08)}
@media (max-width:620px){
  .mod-head h3{font-size:16px}
  .mod-meta{margin-left:0;width:100%}
  .mod-row{grid-template-columns:minmax(0,1fr)}
  .mod-tag{justify-self:start}
}
main{padding:0 0 6px}
.group{margin:0 0 42px}
.group-head h2{display:flex;align-items:center;gap:10px;font:600 1.35rem var(--font-disp);margin:0 0 6px}
.group-head .dot{width:10px;height:10px;border-radius:3px;background:var(--hue);flex:none}
.blurb{color:var(--muted);margin:0 0 18px;font-size:14.5px;line-height:1.5}
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
/* Catalog toolbar */
.catalog-toolbar{display:flex;align-items:center;gap:12px;margin-bottom:18px;flex-wrap:wrap}
.search-wrap{position:relative;flex:1;min-width:200px;max-width:420px}
.search-wrap svg{position:absolute;left:11px;top:50%;transform:translateY(-50%);width:14px;height:14px;color:var(--dim);pointer-events:none}
.search-wrap input{width:100%;background:var(--card);border:1px solid var(--line);color:var(--ink);border-radius:10px;padding:9px 34px 9px 32px;font:13px var(--font-sans);outline:none}
.search-wrap input:focus{border-color:var(--accent)}
.search-wrap input::placeholder{color:var(--dim)}
.search-clear{position:absolute;right:8px;top:50%;transform:translateY(-50%);border:0;background:transparent;color:var(--dim);cursor:pointer;font-size:14px;padding:4px 6px;border-radius:6px}
.search-clear:hover{color:var(--ink);background:var(--line)}
.filter-btn{display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line);background:var(--card);color:var(--muted);border-radius:10px;padding:8px 14px;font:500 13px var(--font-mono);cursor:pointer;min-height:36px;white-space:nowrap}
.filter-btn:hover{border-color:var(--muted);color:var(--ink)}
.filter-btn[aria-expanded="true"]{border-color:var(--accent);color:var(--ink);background:rgba(249,115,22,.10)}
.filter-btn svg{width:14px;height:14px;flex:none}
.filter-badge{display:none;align-items:center;justify-content:center;min-width:18px;height:18px;padding:0 5px;border-radius:99px;background:var(--accent);color:#fff;font:600 11px var(--font-mono)}
.filter-badge.has-count{display:inline-flex}
.toolbar-clear{border:0;background:transparent;color:var(--muted);font:500 13px var(--font-mono);cursor:pointer;padding:6px 8px}
.toolbar-clear:hover{color:var(--accent)}
.empty{margin:0;padding:0 0 30px;color:var(--muted);font-style:italic}
.empty-state{border:1px solid var(--line);border-radius:12px;padding:28px 24px;text-align:center;color:var(--muted);margin-bottom:24px}
.empty-state .empty-title{font:600 16px var(--font-disp);color:var(--ink);margin:0 0 6px}
.empty-state p{margin:0 0 14px}
.empty-actions{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
/* News */
.news{max-width:820px}
.news-feed{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:0}
.news-item{padding:22px 0;border-top:1px solid var(--line);scroll-margin-top:calc(var(--tab-h) + 20px)}
.news-item:first-child{border-top:0;padding-top:0}
.news-meta{display:flex;align-items:center;gap:10px;flex-wrap:wrap;font:11.5px var(--font-mono);color:var(--dim);margin-bottom:8px}
.news-meta time{color:var(--muted)}
.news-kind{display:inline-flex;padding:2px 8px;border-radius:99px;font:600 10.5px var(--font-mono);letter-spacing:.06em;text-transform:uppercase;border:1px solid var(--line-2);color:var(--muted)}
.news-kind[data-kind="site"]{color:#38bdf8;border-color:rgba(56,189,248,.35);background:rgba(56,189,248,.08)}
.news-kind[data-kind="release"]{color:#34d399;border-color:rgba(52,211,153,.35);background:rgba(52,211,153,.08)}
.news-kind[data-kind="community"]{color:#fbbf24;border-color:rgba(251,191,36,.35);background:rgba(251,191,36,.08)}
.news-kind[data-kind="guide"]{color:#a78bfa;border-color:rgba(167,139,250,.35);background:rgba(167,139,250,.08)}
.news-author{color:var(--muted)}
.news-author:hover{color:var(--accent)}
.news-title{font:600 18px/1.3 var(--font-disp);margin:0 0 8px;display:flex;align-items:baseline;gap:8px}
.news-anchor{font:400 14px var(--font-mono);color:var(--dim);opacity:0}
.news-item:hover .news-anchor{opacity:1}
.news-anchor:hover{color:var(--accent)}
.news-summary{font:500 14.5px/1.6 var(--font-sans);color:var(--muted);margin:0 0 10px;border-left:2px solid var(--line-2);padding-left:12px}
.news-body{color:var(--muted);font-size:14px;line-height:1.65}
.news-body p{margin:0 0 10px}
.news-body p:last-child{margin-bottom:0}
.news-body p.lede{font-size:15px;color:var(--ink)}
.news-body code{font-family:var(--font-mono);background:var(--bg-2);border:1px solid var(--line);border-radius:6px;padding:1px 6px;font-size:.9em}
.news-body strong{color:var(--ink)}
.news-repo{margin:10px 0 0;font:12px var(--font-mono);color:var(--dim);display:flex;align-items:center;gap:8px}
.news-repo a{color:var(--muted)}
.news-repo a:hover{color:var(--accent)}
.news-repo .owner{color:var(--dim)}
.news-links{margin:10px 0 0;display:flex;gap:8px;flex-wrap:wrap}
.news-link{display:inline-flex;align-items:center;border:1px solid var(--line-2);border-radius:8px;padding:5px 12px;font:500 12.5px var(--font-mono);color:var(--muted)}
.news-link:hover{border-color:var(--accent);color:var(--ink)}
footer{border-top:1px solid var(--line);margin-top:14px;padding:22px 0 42px;color:var(--dim);font-size:13px}
footer .wrap{display:flex;flex-wrap:wrap;gap:8px 28px;justify-content:space-between}
footer a{color:var(--muted)}
footer a:hover{color:var(--accent)}
code{font-family:var(--font-mono);background:var(--bg-2);border:1px solid var(--line);border-radius:6px;padding:1px 6px;font-size:.9em}
.add-dialog{border:1px solid var(--line-2);border-radius:16px;background:var(--card);color:var(--ink);padding:0;width:min(540px,calc(100vw - 28px));max-height:min(88vh,720px);overflow:auto;box-shadow:0 30px 80px -30px #000}
.add-dialog::backdrop{background:rgba(4,7,11,.72)}
.add-form{display:flex;flex-direction:column;gap:9px;padding:22px 22px 18px}
.add-form h2{font:600 1.25rem var(--font-disp);margin:0}
.add-form .dlg-lede{margin:0 0 4px;color:var(--muted);font-size:13.5px}
.add-form label{font:500 11.5px var(--font-mono);color:var(--dim);text-transform:uppercase;letter-spacing:.09em;margin-top:7px}
.add-form label .opt{text-transform:none;letter-spacing:0;color:var(--dim)}
.add-form input,.add-form select,.add-form textarea{background:var(--bg-2);border:1px solid var(--line-2);color:var(--ink);border-radius:10px;padding:10px 12px;font:14px var(--font-sans);outline:none;width:100%}
.add-form textarea{resize:vertical;min-height:90px}
.add-form input:focus,.add-form select:focus,.add-form textarea:focus{border-color:var(--accent)}
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
</style>
<noscript><style>
.tabbar{display:none}
#catalog,#modules,#changelog,#news{display:block !important}
#catalog[hidden],#modules[hidden],#changelog[hidden],#news[hidden]{display:block !important}
@media (max-width:1000px){
  .side{position:static;transform:none;visibility:visible;max-height:none;width:auto;border-radius:12px;border-left:1px solid var(--line)}
  .side-head,.side-done-wrap,.filter-btn{display:none}
}
</style></noscript>
</head>
<body>
<a class="skip" href="#catalog">Skip to catalog</a>
<div class="glow" aria-hidden="true"></div>
<header class="hero">
  <div class="wrap">
    <div class="hero-top">
      <div class="hero-brand">
        <p class="kicker">Samsung Galaxy XR · SM-I610 · Android XR</p>
        <h1>Galaxy XR <span class="accent">Forge</span></h1>
        <p class="tagline">__TAGLINE__</p>
      </div>
      <div class="hero-actions">
        <a class="btn btn-primary" id="add-repo-btn" href="__REPO_URL__/issues/new?template=add-repo.md&labels=add-repo" aria-haspopup="dialog" aria-controls="add-repo-dialog">＋ Suggest a repo</a>
        <a class="btn btn-ghost" href="__REPO_URL__" target="_blank" rel="noopener">★ Star on GitHub</a>
      </div>
    </div>
    <div class="stats">
      <div class="stat"><b id="count">__TOTAL__</b><span>repos shown</span></div>
      <div class="stat"><b>__GROUPS__</b><span>groups</span></div>
      <div class="stat"><b>__MODULE_TOTAL__</b><span>modules</span></div>
      <div class="stat"><b>__DATE__</b><span>curated</span></div>
    </div>
  </div>
</header>
<nav class="tabbar" aria-label="Views">
  <div class="tabbar-inner" role="tablist" aria-label="Views">
    <a class="tab is-active" role="tab" href="#catalog" data-view="catalog" aria-selected="true" aria-controls="catalog" tabindex="0" id="tab-catalog"><svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2 3.5h5v5H2zM9 3.5h5v5H9zM2 10.5h5v3H2zM9 10.5h5v3H9z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg> Catalog <b>__TOTAL__</b></a>
    <a class="tab" role="tab" href="#modules" data-view="modules" aria-selected="false" aria-controls="modules" tabindex="-1" id="tab-modules"><svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 2L2 5.5 8 9l6-3.5zM2 10l6 3.5L14 10" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg> <span class="tab-long">Kernel modules</span><span class="tab-short">Modules</span> <b>__MODULE_TOTAL__</b></a>
    <a class="tab" role="tab" href="#changelog" data-view="changelog" aria-selected="false" aria-controls="changelog" tabindex="-1" id="tab-changelog"><svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M4 2.5h6l2 2V13H4zM8 2.5v2h2" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/><path d="M6 8.5h4M6 11h4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg> Changelog <b>__CHANGELOG_COUNT__</b></a>
    <a class="tab" role="tab" href="#news" data-view="news" aria-selected="false" aria-controls="news" tabindex="-1" id="tab-news"><svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2 3h10v10H2z" stroke="currentColor" stroke-width="1.2"/><path d="M5 5.5h4M5 8h4M5 10.5h4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg> News <b>__NEWS_COUNT__</b></a>
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
    <div class="side-foot">
      <button type="button" class="side-clear" id="side-clear">Clear all filters</button>
    </div>
    <div class="side-done-wrap">
      <button type="button" class="side-done" id="side-done">Show <b id="side-count">__TOTAL__</b> repos</button>
    </div>
  </aside>
  <div class="content">
    <main id="catalog" role="tabpanel" aria-labelledby="tab-catalog">
      <div class="view-head">
        <div class="view-head-text">
          <p class="eyebrow">Community index</p>
          <h2>Catalog</h2>
          <p class="blurb">Every community repo for the Galaxy XR, grouped and searchable.</p>
        </div>
      </div>
      <div class="catalog-toolbar">
        <div class="search-wrap">
          <svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="6.5" cy="6.5" r="4" stroke="currentColor" stroke-width="1.4"/><path d="M9.5 9.5l3 3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
          <input id="q" type="search" placeholder="Search repos…" aria-label="Filter repositories">
          <button type="button" class="search-clear" id="q-clear" aria-label="Clear search" hidden>×</button>
        </div>
        <button type="button" class="filter-btn" id="menu-btn" aria-expanded="true" aria-controls="sidebar">
          <svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2 4h12M4 8h8M6 12h4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg> Filters <span class="filter-badge" id="filter-count"></span>
        </button>
        <button type="button" class="toolbar-clear" id="toolbar-clear" hidden>Clear</button>
      </div>
      __SECTIONS__
      <div class="empty-state" id="empty" style="display:none">
        <p class="empty-title">No repository matches these filters</p>
        <p>Try adjusting your search or filter selection.</p>
        <div class="empty-actions">
          <button type="button" class="btn btn-ghost btn-sm" id="empty-clear">Clear filters</button>
          <a class="btn btn-primary btn-sm" href="__REPO_URL__/issues/new?template=add-repo.md&labels=add-repo" target="_blank" rel="noopener">Suggest a repo</a>
        </div>
      </div>
    </main>
    <div id="modules" hidden role="tabpanel" aria-labelledby="tab-modules">
      __MODULES__
    </div>
    <div id="changelog" hidden role="tabpanel" aria-labelledby="tab-changelog">
      __CHANGELOG__
    </div>
    <div id="news" hidden role="tabpanel" aria-labelledby="tab-news">
      __NEWS__
    </div>
  </div>
</div>
<div class="backdrop" id="backdrop" hidden></div>
<dialog id="post-news-dialog" class="add-dialog" aria-labelledby="post-news-title">
  <div class="add-form">
    <div class="dlg-head">
      <h2 id="post-news-title">Post news</h2>
      <button type="button" class="dlg-close" id="post-news-close" aria-label="Close">✕</button>
    </div>
    <p class="dlg-lede">Share a release, guide or site update. This opens a proposal issue — nothing is published until a maintainer merges it.</p>
    <label for="post-news-title-input">Title</label>
    <input id="post-news-title-input" maxlength="120" placeholder="News title" autocomplete="off">
    <label for="post-news-body">News text</label>
    <textarea id="post-news-body" rows="5" placeholder="Write your news here. Blank line = new paragraph."></textarea>
    <label for="post-news-summary">Summary <span class="opt">(optional, max 200)</span></label>
    <input id="post-news-summary" maxlength="200" placeholder="One-line summary" autocomplete="off">
    <label for="post-news-kind">Category</label>
    <select id="post-news-kind"><option value="community" selected>Community</option><option value="release">Release</option><option value="guide">Guide</option><option value="site">Site update</option></select>
    <label for="post-news-repo">Related repo <span class="opt">(optional, owner/name)</span></label>
    <input id="post-news-repo" placeholder="owner/name" autocomplete="off" spellcheck="false">
    <label for="post-news-link-label">Link label <span class="opt">(optional)</span></label>
    <input id="post-news-link-label" placeholder="e.g. Release notes" autocomplete="off">
    <label for="post-news-link-url">Link URL <span class="opt">(optional, https://)</span></label>
    <input id="post-news-link-url" type="url" placeholder="https://..." autocomplete="off" spellcheck="false">
    <p class="dlg-status" id="post-news-status" role="status" aria-live="polite"></p>
    <div class="dlg-actions">
      <a class="add-submit" id="post-news-issue" href="#" target="_blank" rel="noopener">Open GitHub issue</a>
    </div>
  </div>
</dialog>
<dialog id="add-repo-dialog" class="add-dialog" aria-labelledby="add-repo-title">
  <div class="add-form">
    <div class="dlg-head">
      <h2 id="add-repo-title">Suggest a repo</h2>
      <button type="button" class="dlg-close" id="add-repo-close" aria-label="Close">✕</button>
    </div>
    <p class="dlg-lede">Paste the link and pick a group. This opens a proposal issue; CI prepares the card and a pull request — <strong>nothing is added until a maintainer merges it</strong>.</p>
    <p class="dlg-note"><strong>Reviewed before merge.</strong> Nothing is added automatically: a maintainer checks that the repository is public, relevant to the Galaxy XR, clearly licensed, and not already listed or proposed.</p>
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
    <span>Suggest a repo: <a href="__REPO_URL__/issues/new?template=add-repo.md&labels=add-repo">file it from the site</a>, or run <code>python tools/add-repo.py</code> · <a href="__REPO_URL__" target="_blank" rel="noopener">★ Star on GitHub</a> · <a href="#changelog">Changelog</a> · <a href="#news">News</a> · Agents: <a href="__REPO_URL__/blob/main/AGENTS.md">AGENTS.md</a></span>
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

  var qClear = document.getElementById('q-clear');
  var filterCount = document.getElementById('filter-count');
  var toolbarClear = document.getElementById('toolbar-clear');
  function updateFilterUI() {
    var n = 0;
    if (state.group !== 'all') n++;
    ['new','fav','done','todo'].forEach(function(k){ if(state.status[k]) n++; });
    if (filterCount) {
      filterCount.textContent = n || '';
      filterCount.classList.toggle('has-count', n > 0);
    }
    if (toolbarClear) toolbarClear.hidden = n === 0;
  }
  function clearAllFilters() {
    state.group = 'all';
    state.status = {};
    groupChips.forEach(function(c){
      var on = c.dataset.group === 'all';
      c.classList.toggle('is-active', on);
      c.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    statusChips.forEach(function(c){
      c.classList.remove('is-active');
      c.setAttribute('aria-pressed','false');
    });
    if (q) { q.value = ''; state.q = ''; }
    apply();
  }
  var emptyClear = document.getElementById('empty-clear');
  if (emptyClear) emptyClear.addEventListener('click', clearAllFilters);
  var sideClear = document.getElementById('side-clear');
  if (sideClear) sideClear.addEventListener('click', clearAllFilters);
  if (toolbarClear) toolbarClear.addEventListener('click', clearAllFilters);
  var _origApply = apply;
  apply = function() {
    _origApply();
    updateFilterUI();
    if (qClear) qClear.hidden = !state.q.trim();
  };
  if (q) q.addEventListener('input', function () { state.q = q.value; apply(); });
  if (qClear) qClear.addEventListener('click', function(){ if(q){ q.value=''; state.q=''; q.focus(); apply(); } });
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
// again by the X, the backdrop, Escape or the Show-N button. The Changelog and
// Kernel modules views hide it (body.view-changelog).
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

// Tabs: ARIA tablist with keyboard nav, hash routing including #news-<slug>
(function () {
  var tabs = [].slice.call(document.querySelectorAll('.tab'));
  var views = {
    catalog: document.getElementById('catalog'),
    modules: document.getElementById('modules'),
    changelog: document.getElementById('changelog'),
    news: document.getElementById('news')
  };
  function show(view, opts) {
    var noPush = opts && opts.noPush;
    tabs.forEach(function (t) {
      var on = t.dataset.view === view;
      t.classList.toggle('is-active', on);
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.setAttribute('tabindex', on ? '0' : '-1');
    });
    Object.keys(views).forEach(function (k) {
      if (views[k]) views[k].hidden = k !== view;
    });
    document.body.classList.toggle('view-noncatalog', view !== 'catalog');
    if (view !== 'catalog' && typeof window.gxrForgeCloseFilters === 'function') window.gxrForgeCloseFilters();
    if (!noPush && window.history && window.history.replaceState) window.history.replaceState(null, '', '#' + view);
  }
  tabs.forEach(function (t) {
    t.addEventListener('click', function (ev) {
      ev.preventDefault();
      show(t.dataset.view);
    });
  });
  // Keyboard: Left/Right/Home/End
  var tablist = document.querySelector('.tabbar-inner');
  if (tablist) {
    tablist.addEventListener('keydown', function (ev) {
      var keys = ['ArrowLeft','ArrowRight','Home','End'];
      if (keys.indexOf(ev.key) === -1) return;
      ev.preventDefault();
      var idx = -1;
      for (var i = 0; i < tabs.length; i++) if (tabs[i] === document.activeElement) idx = i;
      if (idx === -1) idx = 0;
      if (ev.key === 'ArrowLeft') idx = (idx - 1 + tabs.length) % tabs.length;
      else if (ev.key === 'ArrowRight') idx = (idx + 1) % tabs.length;
      else if (ev.key === 'Home') idx = 0;
      else if (ev.key === 'End') idx = tabs.length - 1;
      tabs[idx].focus();
      show(tabs[idx].dataset.view);
    });
  }
  function fromHash() {
    var raw = window.location.hash.replace(/^#/, '');
    if (!raw) { show('catalog', {noPush:true}); return; }
    if (views[raw]) { show(raw, {noPush:true}); return; }
    if (raw.indexOf('news-') === 0) {
      show('news', {noPush:true});
      var el = document.getElementById(raw);
      if (el) setTimeout(function(){ el.scrollIntoView({behavior:'smooth', block:'start'}); }, 80);
      return;
    }
    show('catalog', {noPush:true});
  }
  window.addEventListener('hashchange', fromHash);
  fromHash();
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

// "Suggest a repo" dialog. Pages is static, so the form cannot post anywhere itself:
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
      '&title=' + encodeURIComponent('Suggest repo: ' + m[1] + '/' + m[2]) +
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
  if (location.hash === '#add-repo' || location.hash === '#suggest-a-repo') openDlg();
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

// Post-news dialog
(function(){
  var dlg = document.getElementById('post-news-dialog');
  if(!dlg) return;
  var titleIn = document.getElementById('post-news-title-input');
  var bodyIn = document.getElementById('post-news-body');
  var summaryIn = document.getElementById('post-news-summary');
  var kindSel = document.getElementById('post-news-kind');
  var repoIn = document.getElementById('post-news-repo');
  var linkLabelIn = document.getElementById('post-news-link-label');
  var linkUrlIn = document.getElementById('post-news-link-url');
  var go = document.getElementById('post-news-issue');
  var status = document.getElementById('post-news-status');
  var closeBtn = document.getElementById('post-news-close');
  var BASE = '__REPO_URL__';
  function openDlg(){
    if(typeof dlg.showModal==='function') dlg.showModal(); else dlg.setAttribute('open','');
    refresh();
    setTimeout(function(){ titleIn.focus(); },40);
  }
  function closeDlg(){
    if(typeof dlg.close==='function') dlg.close(); else dlg.removeAttribute('open');
  }
  function issueHref(){
    var title = (titleIn.value||'').trim();
    var body = (bodyIn.value||'').trim();
    if(!title || !body) return null;
    var parts = [];
    parts.push('### Title\\n'+title+'\\n');
    parts.push('### News\\n'+body+'\\n');
    var summary=(summaryIn.value||'').trim();
    if(summary) parts.push('### Summary\\n'+summary+'\\n');
    var kind=kindSel.value||'site';
    parts.push('### Category\\n'+kind+'\\n');
    var repo=(repoIn.value||'').trim();
    if(repo) parts.push('### Related repo\\n'+repo+'\\n');
    var ll=(linkLabelIn.value||'').trim(), lu=(linkUrlIn.value||'').trim();
    if(ll||lu) parts.push('### Link\\n'+(ll||'')+' | '+(lu||'')+'\\n');
    var b=parts.join('\\n');
    return BASE+'/issues/new?labels='+encodeURIComponent('add-news')+'&title='+encodeURIComponent('News: '+title)+'&body='+encodeURIComponent(b);
  }
  function refresh(){
    var href=issueHref();
    go.href=href||'#';
    var ok=!!href;
    go.classList.toggle('is-disabled', !ok);
    go.setAttribute('aria-disabled', ok?'false':'true');
    if(status){
      if(!titleIn.value.trim()) status.textContent='Enter a title.';
      else if(!bodyIn.value.trim()) status.textContent='Enter the news text.';
      else status.textContent='';
    }
  }
  document.addEventListener('click', function(ev){
    var a=ev.target.closest&&ev.target.closest('#post-news-btn');
    if(!a) return;
    if(typeof dlg.showModal==='function'){ ev.preventDefault(); openDlg(); }
  });
  if(closeBtn) closeBtn.addEventListener('click', closeDlg);
  dlg.addEventListener('click', function(ev){ if(ev.target===dlg) closeDlg(); });
  [titleIn,bodyIn,summaryIn,repoIn,linkLabelIn,linkUrlIn].forEach(function(el){ if(el) el.addEventListener('input', refresh); });
  if(kindSel) kindSel.addEventListener('change', refresh);
  go.addEventListener('click', function(ev){ if(!issueHref()){ ev.preventDefault(); titleIn.focus(); }});
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
        '<section class="changelog">'
        '<div class="view-head">'
        '<div class="view-head-text">'
        '<p class="eyebrow">History</p>'
        '<h2>Changelog</h2>'
        '<p class="blurb">Every catalog change \u2014 repos added, moved or removed.</p>'
        '</div>'
        f'<span class="view-head-meta">{len(entries)} entries \u00b7 newest first</span>'
        '</div>'
        f'<ol class="entries">{"".join(entries)}</ol></section>'
    )


def render_modules_view(cat, module_index):
    """Kernel-module index grouped by repository, including repos outside the group."""
    repo_meta = {
        r["repo"].lower(): (g, r)
        for g in cat.get("groups", [])
        for r in g.get("repos", [])
    }
    sections = []
    for entry in module_index:
        repo = entry.get("repo", "")
        group, card = repo_meta.get(repo.lower(), (None, None))
        if group is None:
            continue
        owner, name = repo.split("/", 1)
        mods = entry.get("modules", [])
        rows = []
        for m in mods:
            status = m.get("status", "stable")
            tag = ""
            if status != "stable":
                tag = (
                    f'<span class="mod-tag {html.escape(status, quote=True)}">'
                    f'{MODULE_STATUS_LABEL.get(status, status.title())}</span>'
                )
            rows.append(
                f'<li class="mod-row">'
                f'<h4>{html.escape(m["name"])}<code>{html.escape(m["id"])}</code></h4>'
                f"{tag}"
                f'<p>{html.escape(m["about"])}</p>'
                f"</li>"
            )
        count = len(mods)
        meta = [f'{count} module{"s" if count != 1 else ""}']
        if entry.get("checked"):
            meta.append(f'checked {html.escape(str(entry["checked"]))}')
        url = html.escape(card["url"], quote=True)
        meta.append(f'<a href="{url}" target="_blank" rel="noopener">GitHub</a>')
        if card.get("release"):
            meta.append(
                f'<a href="{url}/releases" target="_blank" rel="noopener">Releases</a>'
            )
        note = entry.get("note")
        note_html = f'<p class="mod-note">{html.escape(note)}</p>' if note else ""
        sections.append(
            f'<section class="mod-repo" style="--hue:{html.escape(group["hue"], quote=True)}">'
            f'<div class="mod-head">'
            f'<h3><span class="dot"></span><a href="{url}" target="_blank" rel="noopener">'
            f'<span class="owner">{html.escape(owner)}/</span>{html.escape(name)}</a></h3>'
            f'<span class="grp">{html.escape(group["icon"])} {html.escape(group["title"])}</span>'
            f'<span class="mod-meta">{" &middot; ".join(meta)}</span>'
            f"</div>"
            f"{note_html}"
            f'<ul class="mod-list">{"".join(rows)}</ul>'
            f"</section>"
        )
    return (
        '<section class="mods">'
        '<div class="view-head">'
        '<div class="view-head-text">'
        '<p class="eyebrow">Module index</p>'
        '<h2>Kernel modules</h2>'
        '<p class="blurb">Every KernelSU module published by a catalogued repository \u2014 grouped by repo.</p>'
        '</div>'
        f'<span class="view-head-meta">{sum(len(e.get("modules",[])) for e in module_index)} modules \u00b7 {len(sections)} repos</span>'
        '</div>'
        f'{"".join(sections)}</section>'
    )


def news_date_label(value):
    """`2026-10-29` -> `29 Oct 2026`; the month names are explicit so the output
    does not depend on the CI host locale."""
    try:
        d = date.fromisoformat(str(value))
    except ValueError:
        return str(value)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def render_news_view(news, cat):
    """News feed, newest first, with one deep-linkable anchor per post."""
    repo_meta = {
        r["repo"].lower(): (g, r)
        for g in cat.get("groups", [])
        for r in g.get("repos", [])
    }
    post_link = (
        'id="post-news-btn" href="__REPO_URL__/issues/new?'
        'template=add-news.md&labels=add-news" target="_blank" rel="noopener"'
    )
    head = (
        '<div class="view-head">'
        '<div class="view-head-text">'
        '<p class="eyebrow">Community</p>'
        '<h2 id="news-title">News</h2>'
        '<p class="blurb">Releases, guides and site updates from the Galaxy XR '
        "community. Newest first.</p>"
        "</div>"
        f'<a class="btn btn-primary" {post_link}>＋ Post news</a>'
        "</div>"
    )

    items = []
    for e in news.get("entries", []):
        stem = html.escape(str(e.get("_file", "news"))[:-5], quote=True)
        kind = e.get("kind") or "community"
        meta = [
            f'<time datetime="{html.escape(str(e.get("date")), quote=True)}">'
            f'{news_date_label(e.get("date"))}</time>'
        ]
        meta.append(
            f'<span class="news-kind" data-kind="{html.escape(kind, quote=True)}">'
            f'{html.escape(NEWS_KIND_LABEL.get(kind, kind.title()))}</span>'
        )
        author = e.get("author")
        if author:
            handle = html.escape(str(author))
            meta.append(
                f'<a class="news-author" href="https://github.com/{handle}" '
                f'target="_blank" rel="noopener">@{handle}</a>'
            )

        summary = e.get("summary")
        paras = []
        for i, para in enumerate(e.get("body") or []):
            cls = ' class="lede"' if i == 0 and not summary else ""
            paras.append(f"<p{cls}>{inline_md(para)}</p>")

        repo_html = ""
        repo = e.get("repo")
        if repo:
            owner, name = str(repo).split("/", 1)
            hit = repo_meta.get(str(repo).lower())
            if hit:
                group, card = hit
                repo_html = (
                    f'<p class="news-repo"><a href="{html.escape(card["url"], quote=True)}" '
                    f'target="_blank" rel="noopener"><span class="owner">{html.escape(owner)}/</span>'
                    f'{html.escape(name)}</a><span class="grp">{html.escape(group["icon"])} '
                    f'{html.escape(group["title"])}</span></p>'
                )
            else:
                repo_html = (
                    f'<p class="news-repo"><span class="owner">{html.escape(owner)}/</span>'
                    f"{html.escape(name)}</p>"
                )

        links_html = ""
        links = e.get("links") or []
        if links:
            anchors = "".join(
                f'<a class="news-link" href="{html.escape(str(link["url"]), quote=True)}" '
                f'target="_blank" rel="noopener">{html.escape(str(link["label"]))}</a>'
                for link in links
            )
            links_html = f'<p class="news-links">{anchors}</p>'

        parts = [
            f'<li class="news-item" id="news-{stem}" data-kind='
            f'"{html.escape(kind, quote=True)}">',
            f'<div class="news-meta">{"".join(meta)}</div>',
            f'<h3 class="news-title">{inline_md(e.get("title", ""))}'
            f'<a class="news-anchor" href="#news-{stem}" '
            f'aria-label="Link to this post">#</a></h3>',
        ]
        if summary:
            parts.append(f'<p class="news-summary">{inline_md(summary)}</p>')
        parts.append(f'<div class="news-body">{"".join(paras)}</div>')
        parts.append(repo_html + links_html)
        parts.append("</li>")
        items.append("".join(parts))

    if items:
        feed = f'<ol class="news-feed">{"".join(items)}</ol>'
    else:
        feed = (
            '<div class="empty-state"><p class="empty-title">No news yet</p>'
            "<p>Releases, guides and site updates will appear here as they are "
            "posted — the first one could be yours.</p></div>"
        )
    return f'<section class="news" aria-labelledby="news-title">{head}{feed}</section>'


def render_site(cat, changelog, module_index, news):
    total = sum(len(g["repos"]) for g in cat["groups"])
    module_total = sum(len(e.get("modules", [])) for e in module_index)
    updated = newest_date(cat, changelog)
    page = SITE_TEMPLATE
    page = page.replace("__TAGLINE__", html.escape(TAGLINE, quote=True))
    page = page.replace("__TOTAL__", str(total))
    page = page.replace("__MODULE_TOTAL__", str(module_total))
    page = page.replace("__GROUPS__", str(len(cat["groups"])))
    page = page.replace("__DATE__", updated)
    page = page.replace("__CHIPS__", render_chips(cat))
    page = page.replace("__STATUS__", render_status_chips(cat))
    page = page.replace("__SECTIONS__", render_sections(cat))
    page = page.replace("__CHANGELOG_COUNT__", str(len(changelog.get("entries", []))))
    page = page.replace("__NEWS_COUNT__", str(len(news.get("entries", []))))
    page = page.replace("__GROUP_OPTIONS__", render_group_options(cat))
    page = page.replace("__CHANGELOG__", render_changelog_view(changelog))
    page = page.replace("__NEWS__", render_news_view(news, cat))
    page = page.replace("__MODULES__", render_modules_view(cat, module_index))
    page = page.replace("__REPO_SLUG__", REPO_URL.split("github.com/")[-1])
    page = page.replace("__REPO_URL__", REPO_URL)
    return page


# ---------------------------------------------------------------------------


def main():
    args = sys.argv[1:]
    check_only = "--check" in args
    cat = load_catalog()
    changelog = load_changelog()
    module_index = load_modules(cat)
    news = load_news()
    errors, repos = validate(cat)
    module_errors, module_warnings = validate_modules(cat, module_index)
    news_errors, news_warnings = validate_news(news, cat)
    errors += module_errors
    errors += validate_changelog(changelog)
    errors += news_errors
    for warning in module_warnings + news_warnings:
        print("warning:", warning)
    if errors:
        print("input INVALID:")
        for e in errors:
            print("  -", e)
        return 1
    module_total = sum(len(e.get("modules", [])) for e in module_index)
    news_total = len(news.get("entries", []))
    if check_only:
        print(
            f"OK: {len(repos)} repos in {len(cat['groups'])} groups; "
            f"{module_total} modules in {len(module_index)} repos; "
            f"{news_total} news posts; "
            f"changelog: {len(changelog['entries'])} entries"
        )
        return 0
    readme = render_readme(cat, changelog)
    changelog_md = render_changelog_md(changelog)
    site = render_site(cat, changelog, module_index, news)
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
        f"modules: {module_total} in {len(module_index)} repos; "
        f"news: {news_total} posts; "
        f"changelog: {len(changelog['entries'])} entries"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
