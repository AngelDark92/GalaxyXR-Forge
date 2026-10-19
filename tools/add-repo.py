#!/usr/bin/env python
"""Add one GitHub repository to the Galaxy XR Forge catalog in one command.

Usage:
    python tools/add-repo.py https://github.com/owner/name --group apps-samples
    python tools/add-repo.py owner/name --group tools --about "Short line."
    python tools/add-repo.py --json payload.json        # CI: parsed issue fields
    python tools/add-repo.py ... --dry-run              # show, write nothing

What it does:
    1. resolves and validates the repository (public, not already listed)
    2. reads license, latest release and topics from the GitHub API
    3. writes a short `about` line (yours, or the repo description trimmed)
    4. inserts the entry in the chosen group with today's `added` date
    5. appends a changelog.json entry and bumps `updated`
    6. regenerates README.md, CHANGELOG.md and docs/index.html, then runs the
       link and repo-state checks

Environment:
    GITHUB_TOKEN   optional; lifts the anonymous API rate limit (add-repo in CI
                   passes the workflow token). Never required locally.

Exit codes:
    0  added
    1  error (bad URL, unknown group, private/missing repo, failed checks)
    2  already in the catalog (nothing written)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "catalog.json"
CHANGELOG_PATH = ROOT / "changelog.json"

REPO_URL_RE = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$")
ABOUT_MAX = 160
ABOUT_TARGET = 150

TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()


# ---------------------------------------------------------------------------
# GitHub API
# ---------------------------------------------------------------------------


def api(url, auth=True, timeout=25):
    headers = {"User-Agent": "gxr-add-repo", "Accept": "application/vnd.github+json"}
    if auth and TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:  # noqa: BLE001
        return 0, {"error": str(e)}


def parse_repo(value):
    """Accept a full URL, owner/name, or a URL with .git / trailing slash."""
    raw = (value or "").strip()
    raw = raw.rstrip("/")
    if raw.endswith(".git"):
        raw = raw[:-4]
    if raw.lower().startswith("github.com/"):
        raw = "https://" + raw
    if raw.startswith("http://"):
        raw = "https://" + raw[len("http://"):]
    if not raw.startswith("https://"):
        raw = "https://github.com/" + raw.lstrip("/")
    m = REPO_URL_RE.match(raw)
    if not m:
        raise SystemExit(f"error: not a GitHub repository URL: {value!r}")
    return m.group(1), m.group(2)


def fetch_repo(owner, name):
    full = f"{owner}/{name}"
    code, meta = api(f"https://api.github.com/repos/{full}")
    if code == 404:
        raise SystemExit(f"error: {full} is not public, or does not exist")
    if code != 200 or not meta:
        raise SystemExit(f"error: GitHub API answered {code} for {full}")
    # Authed 200 is not proof of visibility: confirm anonymously too.
    anon_code, _ = api(f"https://api.github.com/repos/{full}", auth=False)
    if anon_code == 404:
        raise SystemExit(f"error: {full} is private; the catalog only lists public repos")

    licence = (meta.get("license") or {}).get("spdx_id")
    if licence in (None, "NOASSERTION"):
        licence = None

    release = None
    code, rels = api(f"https://api.github.com/repos/{full}/releases?per_page=10")
    if code == 200 and isinstance(rels, list):
        stable = [r for r in rels if not r.get("draft") and not r.get("prerelease")]
        pre = [r for r in rels if not r.get("draft") and r.get("prerelease")]
        pick = (stable or pre or [None])[0]
        if pick:
            release = pick.get("tag_name")

    return {
        "repo": full,
        "url": meta.get("html_url") or f"https://github.com/{full}",
        "description": (meta.get("description") or "").strip(),
        "license": licence,
        "release": release,
        "topics": [t for t in (meta.get("topics") or []) if isinstance(t, str)][:4],
        "archived": bool(meta.get("archived")),
        "fork": bool(meta.get("fork")),
    }


# ---------------------------------------------------------------------------
# catalog access
# ---------------------------------------------------------------------------


def load_json(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def dump_json(value):
    """2-space JSON with short string arrays kept inline, matching the catalog style."""
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


def find_repo(cat, full):
    low = full.lower()
    for g in cat["groups"]:
        for r in g["repos"]:
            if r["repo"].lower() == low:
                return g, r
    return None, None


def repo_slug():
    """owner/repo of this checkout, for searching its own issues and PRs."""
    res = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"], cwd=str(ROOT), text=True, capture_output=True
    )
    url = (res.stdout or "").strip() or os.environ.get("GITHUB_REPOSITORY", "")
    m = re.search(r"github\.com[:/]+([^/]+)/([^/]+?)(?:\.git)?$", url)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def find_proposals(full):
    """Open issues/PRs in this repository that already name this repo."""
    slug = repo_slug()
    if not slug:
        return []
    query = urllib.parse.quote(f'repo:{slug} is:open "{full}"')
    code, data = api(f"https://api.github.com/search/issues?q={query}&per_page=10")
    if code != 200 or not isinstance(data, dict):
        return []
    out = []
    for item in data.get("items", []):
        kind = "pr" if item.get("pull_request") else "issue"
        out.append((item["number"], item.get("title", ""), item.get("html_url", ""), kind))
    return out


def guess_group(cat, owner, name, description):
    """Keyword heuristic; the CLI prints the guess so it can be overridden."""
    text = f"{name} {description}".lower()
    rules = [
        ("kernelsu-modules", ("kernelsu", "module", "magisk", "ksu")),
        ("root-kernel", ("root", "kernel", "boot", "su ", "payload")),
        ("face-eye", ("face", "eye", "vrcft", "facetracking", "eye-tracking")),
        ("app-patches", ("patch", "morphe", "port", "apk", "4xvr", "overport")),
        ("games", ("emulator", "ps4", "game", "winlator", "rom")),
        ("pcvr-drivers", ("steamvr", "driver", "alvr", "stream", "openvr", "moonlight", "vridge")),
        ("tools", ("tool", "diagnostic", "qr", "sensor", "calibrat", "updater")),
        ("apps-samples", ("app", "sample", "player", "demo", "showcase")),
    ]
    best, score = None, 0
    for gid, words in rules:
        hits = sum(1 for w in words if w in text)
        if hits > score:
            best, score = gid, hits
    return best


STOPWORDS = set(
    "the and for with this that from into your you our its their are was were will can not "
    "but all any how what when where who why app apps based using".split()
)


def keywords(description, group_id):
    """Fallback search tags when the repo has no topics."""
    out, seen = [], set()
    for word in re.findall(r"[a-z0-9][a-z0-9-]{3,}", (description or "").lower()):
        if word in STOPWORDS or word in seen:
            continue
        seen.add(word)
        out.append(word)
        if len(out) == 4:
            break
    return out or [group_id]


def make_about(meta, explicit):
    if explicit:
        about = " ".join(explicit.split())
    else:
        about = " ".join(meta["description"].split())
    if not about:
        about = f"{meta['repo'].split('/')[1]} — see the repository README for details."
    if len(about) > ABOUT_TARGET:
        cut = about[:ABOUT_TARGET].rsplit(" ", 1)[0].rstrip(",;:-")
        about = cut + "…"
    if len(about) > ABOUT_MAX:
        about = about[: ABOUT_MAX - 1] + "…"
    return about


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def run(cmd, capture=True):
    return subprocess.run(
        [sys.executable] + cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=capture,
        encoding="utf-8",
        errors="replace",
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description="Add a GitHub repo to the Galaxy XR Forge catalog.")
    ap.add_argument("repo", nargs="?", help="https://github.com/owner/name or owner/name")
    ap.add_argument("--json", metavar="FILE", help="JSON payload {repo, group, about?, issue?}")
    ap.add_argument("--group", help="group id (see `python tools/build.py --check`)")
    ap.add_argument("--about", help="one-line description (default: repo description)")
    ap.add_argument("--tags", help="comma-separated search tags (default: repo topics, else keywords)")
    ap.add_argument("--issue", type=int, default=0, help="issue number, for attribution")
    ap.add_argument("--dry-run", action="store_true", help="print the entry, write nothing")
    ap.add_argument("--no-checks", action="store_true", help="skip check-links / check-repos")
    ap.add_argument("--force", action="store_true", help="run even if catalog files have uncommitted edits")
    args = ap.parse_args(argv)

    payload = {}
    if args.json:
        payload = load_json(Path(args.json))
    repo_value = args.repo or payload.get("repo")
    if not repo_value:
        raise SystemExit("error: give a repo URL or --json payload.json")
    group_id = args.group or payload.get("group")
    about_in = args.about or payload.get("about")
    tags_in = [t.strip().lower() for t in (args.tags or "").split(",") if t.strip()]
    if not tags_in:
        tags_in = [str(t).strip().lower() for t in (payload.get("tags") or []) if str(t).strip()]
    issue = args.issue or int(payload.get("issue") or 0)

    cat = load_json(CATALOG_PATH)
    changelog = load_json(CHANGELOG_PATH)

    # A pending add from another branch or session in the same checkout would be
    # carried into this entry, and its date would ride along. Refuse instead.
    if not args.force:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "--", "catalog.json", "changelog.json"],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            raise SystemExit(
                "error: catalog.json or changelog.json has uncommitted edits.\n"
                "Commit or stash them first, or pass --force if they are yours."
            )

    owner, name = parse_repo(repo_value)
    full = f"{owner}/{name}"
    existing_group, _ = find_repo(cat, full)
    if existing_group:
        print(f"already listed: {full} in {existing_group['id']} — nothing to do")
        return 2

    # A second submission for the same repo is as much a duplicate as one already
    # merged: check open issues and pull requests before touching anything.
    if not args.force:
        proposals = [p for p in find_proposals(full) if p[0] != issue]
        if proposals:
            number, title, url, kind = proposals[0]
            print(f"already proposed: {kind} #{number} {url} — {title}")
            for other in proposals[1:]:
                print(f"  also open: {other[3]} #{other[0]} {other[2]}")
            return 2

    meta = fetch_repo(owner, name)
    if meta["archived"]:
        raise SystemExit(f"error: {full} is archived; the catalog does not list dead projects")

    if not group_id:
        group_id = guess_group(cat, owner, name, meta["description"])
        if not group_id:
            ids = ", ".join(g["id"] for g in cat["groups"])
            raise SystemExit(f"error: could not guess a group; pass --group ({ids})")
        print(f"group not given: guessed {group_id} (override with --group)")

    group = next((g for g in cat["groups"] if g["id"] == group_id), None)
    if group is None:
        ids = ", ".join(g["id"] for g in cat["groups"])
        raise SystemExit(f"error: unknown group {group_id!r}; one of: {ids}")

    today = date.today().isoformat()
    tags = tags_in or meta["topics"] or keywords(meta["description"], group_id)
    entry = {
        "repo": full,
        "url": f"https://github.com/{full}",
        "about": make_about(meta, about_in),
        "license": meta["license"],
        "release": meta["release"],
        "added": today,
        "tags": tags,
    }

    print(f"repo:    {full}")
    print(f"group:   {group['id']} ({group['title']})")
    print(f"about:   {entry['about']}")
    print(f"license: {entry['license']} | release: {entry['release']} | added: {today}")
    if args.dry_run:
        print("\nentry (dry run, not written):")
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        return 0

    group["repos"].append(entry)
    changelog["entries"].insert(
        0,
        {
            "date": today,
            "title": f"{name} added",
            "items": [
                f"Added {full} to {group['title']}"
                + (f" (issue #{issue})." if issue else ".")
            ],
        },
    )

    CATALOG_PATH.write_text(dump_json(cat), encoding="utf-8", newline="\n")
    CHANGELOG_PATH.write_text(dump_json(changelog), encoding="utf-8", newline="\n")
    print(f"wrote catalog.json ({sum(len(g['repos']) for g in cat['groups'])} repos) and changelog.json")
    build = run(["tools/build.py"])
    if build.returncode != 0:
        sys.stderr.write(build.stdout + build.stderr)
        raise SystemExit("error: tools/build.py failed after the edit")

    if not args.no_checks:
        for tool in ("tools/check-links.py", "tools/check-repos.py"):
            if not (ROOT / tool).exists():
                continue
            res = run([tool])
            tail = (res.stdout or "").strip().splitlines()[-1:] or [""]
            print(f"{tool}: exit {res.returncode} — {tail[0]}")
            if res.returncode != 0:
                raise SystemExit(f"error: {tool} failed; fix before committing")

    print(
        "next: review `git diff`, then commit catalog.json changelog.json README.md "
        "CHANGELOG.md docs/index.html and open a PR"
    )
    print("RESULT " + json.dumps({"repo": full, "group": group["id"], "added": today}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
