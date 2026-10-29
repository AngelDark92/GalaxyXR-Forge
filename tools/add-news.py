#!/usr/bin/env python
"""Publish one news post on the Galaxy XR Forge site in one command.

Usage:
    python tools/add-news.py --title "News tab is live" --body "First line.

    Second paragraph." --kind site
    python tools/add-news.py --json payload.json        # CI: parsed issue fields
    python tools/add-news.py ... --link "Release notes|https://example.com/r"
    python tools/add-news.py ... --dry-run              # show, write nothing

What it does:
    1. reads the fields from the flags, or from the `add-news` issue payload
    2. drops empty optionals and checks the entry against the news schema and
       the catalog (tools/build.py owns both)
    3. writes news.d/<date>-<slug>.json (the date is data: a rebase must keep it)
    4. regenerates README.md, CHANGELOG.md and the site (including the news
       archive), then re-validates

News posts are not catalog changes: they add no changelog.d/ entry.

Exit codes:
    0  published
    1  error (bad field, uncommitted news.d, failed validation or build)
    2  already posted (same date and slug, or the same issue number)
"""

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

KINDS = ("site", "release", "community", "guide")
MAX_LINKS = 4

REPO_PART_RE = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
BARE_REPO_RE = re.compile(r"([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def load_json(path):
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise SystemExit(f"error: cannot read {path}: {e}") from None
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise SystemExit(f"error: {path} is not valid UTF-8 JSON: {e}") from None


def load_build():
    """Load tools/build.py — it owns the layout, the JSON style and the writers."""
    spec = importlib.util.spec_from_file_location("gxr_build", ROOT / "tools" / "build.py")
    if spec is None or spec.loader is None:
        raise SystemExit("error: cannot load tools/build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(cmd, capture=True):
    return subprocess.run(
        [sys.executable] + cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=capture,
        encoding="utf-8",
        errors="replace",
    )


def parse_repo(value):
    """Accept a full URL or owner/name; the catalog stores owner/name."""
    raw = (value or "").strip().strip("`").strip()
    m = REPO_PART_RE.search(raw) or BARE_REPO_RE.fullmatch(raw)
    if not m:
        raise SystemExit(
            f"error: not a repository (want owner/name or a GitHub URL): {value!r}"
        )
    owner, name = m.group(1), m.group(2)
    if name.endswith(".git"):
        name = name[:-4]
    if not owner or not name:
        raise SystemExit(f"error: not a repository (want owner/name): {value!r}")
    return f"{owner}/{name}"


def parse_link(value):
    """`Label | https://url` or a bare https URL; the label defaults to `Link`."""
    raw = (value or "").strip()
    if not raw:
        return None
    if "|" in raw:
        label, url = raw.split("|", 1)
    else:
        label, url = "Link", raw
    label = label.strip() or "Link"
    url = url.strip().strip("<>").strip()
    if not url.startswith("https://"):
        raise SystemExit(f"error: link must be an absolute https:// URL: {raw!r}")
    return {"label": label, "url": url}


def as_paragraphs(value):
    """A string splits on blank lines; a list is taken as one paragraph each."""
    if value is None:
        return []
    blocks = value if isinstance(value, list) else re.split(r"\n\s*\n", str(value))
    return [" ".join(str(block).split()) for block in blocks if str(block).strip()]


def parse_date(value):
    if not value:
        return date.today()
    try:
        day = date.fromisoformat(str(value).strip())
    except ValueError:
        raise SystemExit(f"error: bad date {value!r}; use YYYY-MM-DD") from None
    if day > date.today():
        raise SystemExit(f"error: date {day.isoformat()} is in the future")
    return day


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv=None):
    ap = argparse.ArgumentParser(description="Publish a news post on the Galaxy XR Forge site.")
    ap.add_argument("--title", help="headline (max 120 chars)")
    ap.add_argument("--body", help="post text; blank line between paragraphs")
    ap.add_argument("--summary", help="one line under the headline (max 200 chars)")
    ap.add_argument("--kind", choices=KINDS, help="category (default: community)")
    ap.add_argument("--repo", help="related repository, owner/name or a GitHub URL")
    ap.add_argument(
        "--link",
        action="append",
        metavar="LABEL|URL",
        help="related link, `Label | https://...`; repeatable (max 4)",
    )
    ap.add_argument("--date", help="post date YYYY-MM-DD (default: today)")
    ap.add_argument("--json", metavar="FILE", help="JSON payload {title, body, ...}")
    ap.add_argument("--dry-run", action="store_true", help="print the entry, write nothing")
    ap.add_argument("--no-checks", action="store_true", help="skip the post-write build --check")
    ap.add_argument("--force", action="store_true", help="run even if news.d has uncommitted edits")
    args = ap.parse_args(argv)

    payload = {}
    if args.json:
        payload = load_json(Path(args.json))

    title = " ".join(str(args.title or payload.get("title") or "").split())
    if not title:
        raise SystemExit("error: give a title (--title or --json payload.json)")

    body_in = args.body if args.body is not None else payload.get("body")
    body = as_paragraphs(body_in)
    if not body:
        raise SystemExit("error: give the post text (--body or --json payload.json)")

    summary_in = args.summary if args.summary is not None else payload.get("summary")
    summary = " ".join(str(summary_in or "").split())

    kind = (args.kind or payload.get("kind") or "community").strip().lower()
    if kind not in KINDS:
        raise SystemExit(f"error: unknown kind {kind!r}; one of: {', '.join(KINDS)}")

    repo_in = args.repo if args.repo is not None else payload.get("repo")
    repo = parse_repo(repo_in) if repo_in else None

    raw_links = list(args.link or [])
    for item in payload.get("links") or []:
        if isinstance(item, dict):
            raw_links.append(f"{item.get('label') or 'Link'}|{item.get('url') or ''}")
        else:
            raw_links.append(str(item))
    links = [link for link in (parse_link(raw) for raw in raw_links) if link]
    if len(links) > MAX_LINKS:
        raise SystemExit(f"error: {len(links)} links (max {MAX_LINKS})")

    author = " ".join(str(payload.get("author") or "").split()).lstrip("@")
    issue = int(payload.get("issue") or 0)
    day = parse_date(args.date if args.date is not None else payload.get("date"))

    gxr = load_build()
    cat = gxr.load_catalog()

    # A pending post from another branch or session in the same checkout would be
    # carried into this run. Refuse instead.
    if not args.force:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "--", "news.d"],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            raise SystemExit(
                "error: news.d has uncommitted edits.\n"
                "Commit or stash them first, or pass --force if they are yours."
            )

    slug = gxr.news_slug(title)
    target = f"{day.isoformat()}-{slug}"
    existing = gxr.load_news()
    for entry in existing.get("entries", []):
        stem = str(entry.get("_file", ""))[:-5]
        if stem == target or stem.startswith(target + "-"):
            print(
                f"already posted: news.d/{entry.get('_file')} — {entry.get('title', '')}"
                " (same date and title; nothing to do)"
            )
            return 2
        if issue > 0 and int(entry.get("issue") or 0) == issue:
            print(
                f"already posted: news.d/{entry.get('_file')} — {entry.get('title', '')}"
                f" (from issue #{issue}; nothing to do)"
            )
            return 2

    entry = {"date": day.isoformat(), "title": title, "kind": kind}
    if summary:
        entry["summary"] = summary
    entry["body"] = body
    if repo:
        entry["repo"] = repo
    if links:
        entry["links"] = links
    if author:
        entry["author"] = author
    if issue > 0:
        entry["issue"] = issue

    errors, warnings = gxr.validate_news(
        {"entries": [dict(entry, _file=f"{target}.json")]},
        cat,
    )
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"title:  {title}")
    line = f"date:   {day.isoformat()} | kind: {kind}"
    if repo:
        line += f" | repo: {repo}"
    if links:
        line += f" | links: {len(links)}"
    print(line)
    if args.dry_run:
        print("\nentry (dry run, not written):")
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        return 0

    path = gxr.write_news_entry(entry)
    print(f"wrote {path.relative_to(ROOT).as_posix()}")

    res_build = run(["tools/build.py"])
    if res_build.returncode != 0:
        sys.stderr.write(res_build.stdout + res_build.stderr)
        raise SystemExit("error: tools/build.py failed after the edit")

    if not args.no_checks:
        res = run(["tools/build.py", "--check"])
        tail = (res.stdout or "").strip().splitlines()[-1:] or [""]
        print(f"tools/build.py --check: exit {res.returncode} — {tail[0]}")
        if res.returncode != 0:
            sys.stderr.write(res.stdout + res.stderr)
            raise SystemExit("error: tools/build.py --check failed; fix before committing")

    print(
        "next: review `git diff`, then commit news.d/ plus README.md CHANGELOG.md docs/ "
        "and push the current branch (outside contributors: open a PR)"
    )
    print(
        "RESULT "
        + json.dumps(
            {
                "date": day.isoformat(),
                "title": title,
                "file": path.relative_to(ROOT).as_posix(),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
