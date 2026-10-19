#!/usr/bin/env python
"""Turn an `add-repo` issue body into the JSON payload tools/add-repo.py reads.

Reads ISSUE_BODY (and ISSUE_NUMBER) from the environment. Prints JSON:
    {"repo": "https://github.com/owner/name", "group": "apps-samples",
     "about": null, "issue": 12}

Accepted body shapes, in order of preference:
    1. the site form / issue template headings:
           ### Repo URL
           https://github.com/owner/name
           ### Group
           apps-samples
           ### About            (optional)
           One short line.
    2. bare `repo:` / `group:` / `about:` lines.

Exit codes: 0 ok, 1 unparseable or invalid (message on stdout/stderr).
"""

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog.json"

REPO_URL_RE = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$")


def sections(body):
    """Map '### Heading' blocks to their text."""
    out = {}
    current = None
    for line in body.splitlines():
        m = re.match(r"^\s*#{2,4}\s+(.+?)\s*$", line)
        if m:
            current = m.group(1).strip().lower()
            out.setdefault(current, [])
            continue
        if current is not None:
            out[current].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def first_url(text):
    m = re.search(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", text or "")
    return m.group(0) if m else None


def main():
    body = os.environ.get("ISSUE_BODY", "")
    number = os.environ.get("ISSUE_NUMBER", "0")
    sec = sections(body)

    repo = first_url(sec.get("repo url") or body)
    if not repo:
        print("error: no GitHub repository URL found in the issue body", file=sys.stderr)
        return 1
    repo = repo.rstrip("/")
    if repo.endswith(".git"):
        repo = repo[:-4]
    m = REPO_URL_RE.match(repo)
    if not m:
        print(f"error: not a plain repository URL: {repo}", file=sys.stderr)
        return 1

    group = (sec.get("group") or "").strip().lower()
    if not group:
        for line in body.splitlines():
            hit = re.match(r"^\s*group\s*:\s*(\S+)\s*$", line, re.I)
            if hit:
                group = hit.group(1).lower()
                break

    groups = json.loads(CATALOG.read_text(encoding="utf-8"))["groups"]
    ids = [g["id"] for g in groups]
    if group not in ids:
        print(
            "error: group must be one of: " + ", ".join(ids),
            file=sys.stderr,
        )
        return 1

    about = (sec.get("about") or sec.get("notes") or "").strip()
    if len(about) > 160:
        about = about[:157].rstrip() + "…"
    if about.lower() in ("(optional)", "optional", "-"):
        about = ""

    print(
        json.dumps(
            {
                "repo": f"https://github.com/{m.group(1)}/{m.group(2)}",
                "group": group,
                "about": about or None,
                "issue": int(number or 0),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
