#!/usr/bin/env python
"""Rebase one pending catalog addition onto current main, without hand-resolving JSON.

Two add-PRs made on the same day conflict on the same lines: the new entry's tail,
the changelog head, and (before it was derived) the `updated` field. Resolving those
by hand is where an entry loses its original `added` date. This tool rebuilds the
branch deterministically:

    1. read this branch's entry (repo, group, about, tags, added) from HEAD
    2. take catalog.json + changelog.json + generated files from main
    3. append the entry and its changelog line, with the ORIGINAL `added` date
    4. rebuild README/CHANGELOG/site and commit

Usage:
    python tools/repair-add-pr.py                  # the single entry this branch adds
    python tools/repair-add-pr.py --repo o/n       # pick one if the branch adds several
    python tools/repair-add-pr.py --main origin/main --dry-run

Exit codes: 0 repaired, 1 error, 2 nothing to repair (entry already on main).
"""

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
CATALOG = ROOT / "catalog.json"
CHANGELOG = ROOT / "changelog.json"
GENERATED = ["catalog.json", "changelog.json", "README.md", "CHANGELOG.md", "docs/index.html"]


def load_addrepo():
    """Import tools/add-repo.py (hyphen in the name, so load it by path)."""
    spec = importlib.util.spec_from_file_location("add_repo", TOOLS / "add-repo.py")
    if spec is None or spec.loader is None:
        raise SystemExit("error: cannot load tools/add-repo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args, check=True):
    res = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    if check and res.returncode != 0:
        raise SystemExit(f"error: git {' '.join(args)} failed:\n{res.stderr.strip()}")
    return res


def show_json(ref, path):
    res = git("show", f"{ref}:{path}")
    return json.loads(res.stdout)


def entries_by_repo(catalog):
    return {r["repo"].lower(): (g, r) for g in catalog["groups"] for r in g["repos"]}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Re-apply a branch's catalog entry onto main.")
    ap.add_argument("--repo", help="owner/name to keep (default: the one entry main lacks)")
    ap.add_argument("--main", default="origin/main", help="ref to rebuild on (default origin/main)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, change nothing")
    args = ap.parse_args(argv)

    if not (ROOT / ".git").exists():
        raise SystemExit("error: run this inside the repository checkout")
    if git("rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode == 0:
        print("note: aborting the in-progress merge first")
        git("merge", "--abort")

    git("fetch", "origin", "main", check=False)
    addrepo = load_addrepo()

    branch_cat = addrepo.load_json(CATALOG)
    main_cat = show_json(args.main, "catalog.json")
    branch_entries = entries_by_repo(branch_cat)
    main_entries = entries_by_repo(main_cat)

    added = [full for full in branch_entries if full not in main_entries]
    if args.repo:
        wanted = args.repo.strip().lower()
        wanted = wanted.removeprefix("https://github.com/").removesuffix(".git")
        added = [full for full in added if full == wanted]
        if not added:
            raise SystemExit(f"error: {wanted} is not a new entry on this branch")
    if not added:
        print("nothing to repair: every entry on this branch is already on " + args.main)
        return 2
    if len(added) > 1:
        raise SystemExit("error: this branch adds several entries; pass --repo:\n  " + "\n  ".join(added))

    full = added[0]
    group_branch, entry = branch_entries[full]
    group_id = group_branch["id"]
    group_main = next((g for g in main_cat["groups"] if g["id"] == group_id), None)
    if group_main is None:
        raise SystemExit(f"error: group {group_id!r} no longer exists on {args.main}")

    # Keep the entry as the branch wrote it — including the day it was first added.
    preserved = {k: entry[k] for k in ("repo", "url", "about", "license", "release", "added", "tags") if k in entry}
    print(f"entry:   {full}")
    print(f"group:   {group_id} ({group_main['title']})")
    print(f"added:   {preserved.get('added')} (kept, not rewritten)")

    # Changelog line from the branch, so hand-edited wording survives.
    branch_log = addrepo.load_json(CHANGELOG)
    old_entry = next((e for e in branch_log["entries"] if full in " ".join(e.get("items", []))), None)
    item = old_entry["items"][0] if old_entry and old_entry.get("items") else f"Added {full} to {group_main['title']}."
    day = preserved.get("added") or (old_entry or {}).get("date")
    log_entry = {"date": day, "title": f"{full.split('/')[1]} added", "items": [item]}

    if args.dry_run:
        print("\nplanned entry:")
        print(json.dumps(preserved, indent=2, ensure_ascii=False))
        print("planned changelog:", json.dumps(log_entry, ensure_ascii=False))
        return 0

    # Take main's copies wholesale: generated files are never hand-resolved.
    git("checkout", args.main, "--", *GENERATED)

    catalog = addrepo.load_json(CATALOG)
    changelog = addrepo.load_json(CHANGELOG)
    group = next(g for g in catalog["groups"] if g["id"] == group_id)
    group["repos"].append(preserved)
    catalog.pop("updated", None)
    same_day = [i for i, e in enumerate(changelog["entries"]) if e.get("date") == day]
    changelog["entries"].insert(same_day[0] if same_day else 0, log_entry)

    CATALOG.write_text(addrepo.dump_json(catalog), encoding="utf-8", newline="\n")
    CHANGELOG.write_text(addrepo.dump_json(changelog), encoding="utf-8", newline="\n")

    build = subprocess.run([sys.executable, str(TOOLS / "build.py")], cwd=ROOT, text=True, capture_output=True)
    if build.returncode != 0:
        sys.stderr.write(build.stdout + build.stderr)
        raise SystemExit("error: tools/build.py failed after the repair")

    git("add", "--", *GENERATED)
    git("commit", "-m", f"fix: rebase {full} onto {args.main} (added date kept: {preserved.get('added')})")
    print(f"repaired on {args.main}: {full}, added {preserved.get('added')}")
    print("push the branch to update the pull request")
    return 0


if __name__ == "__main__":
    sys.exit(main())
