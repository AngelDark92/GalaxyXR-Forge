#!/usr/bin/env python
"""Rebase one pending catalog addition onto current main, without hand-resolving JSON.

Catalog entries live one per file (catalog.d/<group>/<owner>__<name>.json), so a
rebuild is: take main, write this branch's one file again. The entry keeps its
original `added` date and its changelog line.

    1. read this branch's entry (repo, group, about, tags, added) from the worktree
    2. reset the branch onto main
    3. write the entry file and its changelog file, with the ORIGINAL `added` date
    4. rebuild README/CHANGELOG/site/index and commit

Usage:
    python tools/repair-add-pr.py                  # the single entry this branch adds
    python tools/repair-add-pr.py --repo o/n       # pick one if the branch adds several
    python tools/repair-add-pr.py --main origin/main --dry-run
    python tools/repair-add-pr.py --root .

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
GENERATED = ["README.md", "CHANGELOG.md", "docs/index.html", "docs/catalog-index.json"]


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


def main(argv=None):
    ap = argparse.ArgumentParser(description="Re-apply a branch's catalog entry onto main.")
    ap.add_argument("--repo", help="owner/name to keep (default: the one entry main lacks)")
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
        print("nothing to repair: every entry on this branch is already on " + args.main)
        return 2
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
