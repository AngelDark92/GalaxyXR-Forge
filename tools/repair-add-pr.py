#!/usr/bin/env python
"""Rebase one pending PR onto current main, without hand-resolving JSON.

Two PR kinds conflict here, and both are "one new file" changes:

* catalog.d/<group>/<owner>__<name>.json — a catalog entry, rebuilt with its
  ORIGINAL `added` date and its changelog line;
* news.d/<YYYY-MM-DD>-<slug>.json — a news post, rebuilt with its ORIGINAL date
  and its original slug. The date is data: a rebase never re-dates a post.

A rebuild is: take main, write this branch's one file again.

    1. read this branch's entry (repo, group, about, tags, added) from the worktree
    2. reset the branch onto main
    3. write the entry file and its changelog file, with the ORIGINAL `added` date
    4. rebuild README/CHANGELOG/site/index and commit

The catalog path runs first. Only when the branch adds no catalog entry does the
news path run, with the same steps and the post's original date/slug instead.

Usage:
    python tools/repair-add-pr.py                  # the single entry/post this branch adds
    python tools/repair-add-pr.py --repo o/n       # pick one if the branch adds several repos
    python tools/repair-add-pr.py --slug <slug>    # pick one if the branch adds several posts
    python tools/repair-add-pr.py --file news.d/<YYYY-MM-DD>-<slug>.json
    python tools/repair-add-pr.py --main origin/main --dry-run
    python tools/repair-add-pr.py --root .

Exit codes: 0 repaired, 1 error, 2 nothing to repair (nothing new on this branch).
"""

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
GENERATED = ["README.md", "CHANGELOG.md", "docs/index.html", "docs/catalog-index.json", "docs/news.json"]


def load_build():
    spec = importlib.util.spec_from_file_location("gxr_build", TOOLS / "build.py")
    if spec is None or spec.loader is None:
        raise SystemExit("error: cannot load tools/build.py from the workspace")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args, check=True):
    res = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    if check and res.returncode != 0:
        raise SystemExit(
            f"error: git {' '.join(args)} failed (exit {res.returncode}):\n"
            f"{res.stderr.strip()}\n{res.stdout.strip()}"
        )
    return res


def read_entries(root):
    """{repo_lower: (group_id, entry)} from catalog.d, else the legacy catalog.json."""
    out = {}
    folder = root / "catalog.d"
    if folder.is_dir():
        for path in sorted(folder.glob("*/*.json")):
            entry = json.loads(path.read_text(encoding="utf-8"))
            out[entry["repo"].lower()] = (path.parent.name, entry)
        return out
    cat = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    for group in cat["groups"]:
        for entry in group.get("repos", []):
            out[entry["repo"].lower()] = (group["id"], entry)
    return out


def read_changelog_entry(root, full):
    """The branch's changelog entry for this repo, so hand-edited wording survives."""
    folder = root / "changelog.d"
    if folder.is_dir():
        for path in sorted(folder.glob("*.json")):
            entry = json.loads(path.read_text(encoding="utf-8"))
            if full in " ".join(entry.get("items", [])):
                return entry
        return None
    log = json.loads((root / "changelog.json").read_text(encoding="utf-8"))
    return next((e for e in log["entries"] if full in " ".join(e.get("items", []))), None)


def main_entries(ref):
    """Repos already on <ref>, read through git so the worktree stays untouched."""
    tree = git("ls-tree", "-r", "--name-only", ref, "--", "catalog.d").stdout.split()
    if tree:
        out = {}
        for name in tree:
            entry = json.loads(git("show", f"{ref}:{name}").stdout)
            out[entry["repo"].lower()] = name.split("/")[1]
        return out
    cat = json.loads(git("show", f"{ref}:catalog.json").stdout)
    return {r["repo"].lower(): g["id"] for g in cat["groups"] for r in g.get("repos", [])}


NEWS_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)$")


def read_news(root):
    """{file_name: entry} for news.d/*.json in the worktree (the branch checkout)."""
    folder = root / "news.d"
    if not folder.is_dir():
        return {}
    out = {}
    for path in sorted(folder.glob("*.json"), key=lambda f: (f.name.lower(), f.name)):
        out[path.name] = json.loads(path.read_text(encoding="utf-8"))
    return out


def news_slug_of(name):
    """The slug of a news file: its stem minus the `YYYY-MM-DD-` prefix."""
    stem = name[:-5] if name.endswith(".json") else name
    m = NEWS_NAME_RE.match(stem)
    return m.group(2) if m else stem


def main_news(ref):
    """Posts already on <ref>, read through git so the worktree stays untouched."""
    tree = git("ls-tree", "-r", "--name-only", ref, "--", "news.d").stdout.split()
    out = {}
    for path in tree:
        if not path.endswith(".json"):
            continue
        name = path.split("/", 1)[1]
        out[name] = json.loads(git("show", f"{ref}:{path}").stdout)
    return out


def repair_news(args):
    """News fallback: rewrite this branch's one new post on main, date kept."""
    branch_news = read_news(ROOT)
    on_main = main_news(args.main)
    added = sorted(name for name in branch_news if name not in on_main)

    if args.file:
        wanted = Path(args.file.strip()).name
        added = [name for name in added if name == wanted]
        if not added:
            raise SystemExit(f"error: news.d/{wanted} is not a new post on this branch")
    elif args.slug:
        wanted = args.slug.strip()
        added = [
            name for name in added
            if wanted in (news_slug_of(name), name[:-5], name)
        ]
        if not added:
            raise SystemExit(f"error: {wanted} is not a new news post on this branch")

    if not added:
        print("nothing to repair: no new catalog entry or news post on this branch")
        return 2
    if len(added) > 1:
        raise SystemExit(
            "error: this branch adds several news posts; pass --file or --slug:\n  "
            + "\n  ".join(added)
        )

    name = added[0]
    entry = branch_news[name]
    stem = name[:-5] if name.endswith(".json") else name
    m = NEWS_NAME_RE.match(stem)
    file_date = m.group(1) if m else None
    slug = m.group(2) if m else stem
    # The date is data, not a build stamp: it comes from the post itself and is
    # written back verbatim. The file name only has to agree with it.
    day = entry.get("date")
    if not day:
        raise SystemExit(f"error: news.d/{name} has no date; cannot rebuild it")
    if file_date and str(day) != file_date:
        raise SystemExit(
            f"error: news.d/{name} says date {day!r} but its file name says {file_date}; "
            "fix the post's date before repairing"
        )
    print(f"post:    news.d/{name}")
    print(f"date:    {day} (kept, not rewritten)")
    print(f"title:   {entry.get('title')}")
    print(f"slug:    {slug} (kept, not rewritten)")

    if args.dry_run:
        print(f"\nplanned file: news.d/{day}-{slug}.json")
        print("planned post:")
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        return 0

    print(f"rebuilding the branch on {args.main}")
    git("reset", "--hard", args.main)

    gxr = load_build()
    post_path = gxr.write_news_entry(entry, slug=slug)

    built = subprocess.run([sys.executable, str(TOOLS / "build.py")], cwd=ROOT, text=True, capture_output=True)
    if built.returncode != 0:
        sys.stderr.write(built.stdout + built.stderr)
        raise SystemExit("error: tools/build.py failed after the repair")

    paths = [str(post_path.relative_to(ROOT))] + GENERATED
    git("add", "--", *paths)
    staged = git("diff", "--cached", "--name-only").stdout.strip()
    print("staged:", staged.replace("\n", ", ") or "(nothing)")
    git("commit", "-m", f"fix: rebase news post {day} ({slug}) onto {args.main}")
    print(f"repaired on {args.main}: news.d/{post_path.name}, date {day}")
    print("push the branch to update the pull request")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Re-apply a branch's catalog entry or news post onto main."
    )
    pick = ap.add_mutually_exclusive_group()
    pick.add_argument("--repo", help="owner/name to keep (default: the one entry main lacks)")
    pick.add_argument("--file", help="news.d file to keep (default: the one post main lacks)")
    pick.add_argument("--slug", help="news post slug to keep, if the branch adds several")
    ap.add_argument("--main", default="origin/main", help="ref to rebuild on (default origin/main)")
    ap.add_argument("--root", help="repository root (default: the tool's parent directory)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, change nothing")
    args = ap.parse_args(argv)

    global ROOT, TOOLS
    if args.root:
        ROOT = Path(args.root).resolve()
        TOOLS = ROOT / "tools"

    if not (ROOT / ".git").exists():
        raise SystemExit("error: run this inside the repository checkout")
    if git("rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode == 0:
        print("note: aborting the in-progress merge first")
        git("merge", "--abort")

    git("fetch", "origin", "main", check=False)

    branch_entries = read_entries(ROOT)
    on_main = main_entries(args.main)
    added = [full for full in branch_entries if full not in on_main]

    if args.repo:
        wanted = args.repo.strip().lower().removeprefix("https://github.com/").removesuffix(".git")
        added = [full for full in added if full == wanted]
        if not added:
            raise SystemExit(f"error: {wanted} is not a new entry on this branch")
    if not added:
        return repair_news(args)
    if len(added) > 1:
        raise SystemExit("error: this branch adds several entries; pass --repo:\n  " + "\n  ".join(added))

    full = added[0]
    group_id, entry = branch_entries[full]
    print(f"entry:   {entry['repo']}")
    print(f"group:   {group_id}")
    print(f"added:   {entry.get('added')} (kept, not rewritten)")

    old_log = read_changelog_entry(ROOT, full)
    item = (old_log or {}).get("items", [None])[0] or f"Added {full} to {group_id}."
    day = entry.get("added") or (old_log or {}).get("date")
    log_entry = {"date": day, "title": f"{full.split('/')[1]} added", "items": [item]}

    if args.dry_run:
        print("\nplanned entry:")
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        print("planned changelog:", json.dumps(log_entry, ensure_ascii=False))
        return 0

    # Rebuild the branch ON main. Rewriting files on the old base is not enough:
    # git still sees both sides changing the same hunks, which stays a conflict.
    print(f"rebuilding the branch on {args.main}")
    git("reset", "--hard", args.main)

    gxr = load_build()
    entry_path = gxr.write_repo_entry(group_id, entry)
    log_path = gxr.write_changelog_entry(log_entry)

    built = subprocess.run([sys.executable, str(TOOLS / "build.py")], cwd=ROOT, text=True, capture_output=True)
    if built.returncode != 0:
        sys.stderr.write(built.stdout + built.stderr)
        raise SystemExit("error: tools/build.py failed after the repair")

    paths = [str(entry_path.relative_to(ROOT)), str(log_path.relative_to(ROOT))] + GENERATED
    git("add", "--", *paths)
    staged = git("diff", "--cached", "--name-only").stdout.strip()
    print("staged:", staged.replace("\n", ", ") or "(nothing)")
    git("commit", "-m", f"fix: rebase {full} onto {args.main} (added date kept: {entry.get('added')})")
    print(f"repaired on {args.main}: {full}, added {entry.get('added')}")
    print("push the branch to update the pull request")
    return 0


if __name__ == "__main__":
    sys.exit(main())
