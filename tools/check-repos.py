#!/usr/bin/env python
"""Check every catalog.json repo against GitHub's canonical name and state.

Why this exists: a renamed or transferred repository still answers at its old
URL (GitHub redirects it), so `tools/check-links.py` stays green while the
catalog points at a name nobody else uses. That is how `compdoge/gxr-alvr-ft`
sat stale after the repo became `compdoge/gxr-root-ft`.

This reads each repository back from the GitHub API and compares it with the
catalog entry. Nothing is written.

States:
    OK        the catalogued owner/name is the repository's canonical full_name
    RENAMED   the repository now lives under a different owner/name
    GONE      the API answers 404 (deleted, renamed elsewhere, or private)
    ARCHIVED  the repository is read-only
    CASE      same name ignoring letter case; the catalog differs only by case
    ERROR     the API could not be read (rate limit, network, other HTTP)

RENAMED, GONE and ERROR fail the run. ARCHIVED and CASE are printed as
warnings; `--strict` turns them into failures too.

Usage:
    python tools/check-repos.py                    # GITHUB_TOKEN is optional
    GITHUB_TOKEN=... python tools/check-repos.py   # avoids the 60/hour limit
    python tools/check-repos.py --strict           # warnings fail as well
    python tools/check-repos.py --only owner/name  # repeatable, for one entry

Exit code 0 = clean for the selected mode, 1 = at least one failure.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402  (same directory, dependency-free module)

ROOT = Path(__file__).resolve().parent.parent

TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
HEADERS = {"User-Agent": "gxr-forge-repocheck", "Accept": "application/vnd.github+json"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

FAILING = {"RENAMED", "GONE", "ERROR"}
WARNING = {"ARCHIVED", "CASE"}


def repo_meta(full_name):
    """Return (meta, status) - status is None on success, else an HTTP code or text."""
    req = urllib.request.Request(f"https://api.github.com/repos/{full_name}", headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.load(r), None
    except urllib.error.HTTPError as e:
        return None, e.code
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def classify(catalogued, meta, status):
    """Return (state, detail) for one catalog entry."""
    if status is not None:
        if status == 404:
            return "GONE", "no repository at this name (deleted, renamed elsewhere, or private)"
        if status in (403, 429):
            return "ERROR", f"HTTP {status} (GitHub rate limit? set GITHUB_TOKEN)"
        return "ERROR", f"HTTP {status}"

    canonical = str(meta.get("full_name") or "")
    if canonical == catalogued:
        state, detail = "OK", ""
    elif canonical.lower() == catalogued.lower():
        state, detail = "CASE", f"canonical case is {canonical}"
    else:
        state, detail = "RENAMED", f"now {canonical}"

    if meta.get("archived"):
        detail = f"{detail}; archived" if detail else "repository is archived"
        if state == "OK":
            state = "ARCHIVED"
    return state, detail


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check catalog.json repos against GitHub.")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--only", metavar="OWNER/NAME", action="append",
                        help="check only this repo (repeatable)")
    args = parser.parse_args(argv)

    cat = build.load_catalog()

    checked = failed = warned = 0
    for g in cat["groups"]:
        for r in g["repos"]:
            repo = r["repo"]
            if args.only and repo not in args.only:
                continue
            meta, status = repo_meta(repo)
            state, detail = classify(repo, meta, status)
            is_failure = state in FAILING or (args.strict and state in WARNING)
            if is_failure:
                failed += 1
            elif state in WARNING:
                warned += 1
            checked += 1
            line = f"{state:<9}{repo}"
            print(f"{line}  {detail}" if detail else line)
            time.sleep(0.1)

    for missing in set(args.only or []) - {
        r["repo"] for g in cat["groups"] for r in g["repos"]
    }:
        print(f"{'MISSING':<9}{missing}  not in catalog.json")
        failed += 1

    print(f"\n{checked} repos checked, {failed} failed, {warned} warnings")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
