#!/usr/bin/env python
"""Review helper for an open pull request (read-only)."""
import json
import os
import sys
import urllib.error
import urllib.request

TOKEN = os.environ.get("GITHUB_TOKEN", "")
BASE = "https://api.github.com/repos/AngelDark92/GalaxyXR-Forge"
HEADERS = {
    "User-Agent": "gxr-pr-review",
    "Accept": "application/vnd.github+json",
}
if TOKEN:
    HEADERS["Authorization"] = "Bearer " + TOKEN


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"code": e.code, "body": e.read().decode()[:400]}


def main(number):
    p = get(f"{BASE}/pulls/{number}")
    print("== PR", number, "==")
    for key in ("title", "state", "mergeable", "rebaseable", "draft", "created_at", "updated_at"):
        print(f"  {key}: {p.get(key)}")
    head_repo = (p["head"].get("repo") or {}).get("full_name")
    print("  base:", p["base"]["sha"][:8], p["base"]["ref"], "| head:", p["head"]["sha"][:8], head_repo)
    print("  commits:", p.get("commits"), "| files:", p.get("changed_files"),
          "| +", p.get("additions"), "-", p.get("deletions"))
    print("  body:", (p.get("body") or "(empty)").replace("\n", "\n        "))

    print("\n== files ==")
    for f in get(f"{BASE}/pulls/{number}/files"):
        print(f"  {f['status']:<9} +{f['additions']:<5} -{f['deletions']:<5} {f['filename']}")

    print("\n== commits ==")
    for c in get(f"{BASE}/pulls/{number}/commits"):
        print("  ", c["sha"][:8], c["commit"]["message"].splitlines()[0])

    sha = p["head"]["sha"]
    cr = get(f"{BASE}/commits/{sha}/check-runs")
    print("\n== check-runs:", cr.get("total_count"))
    for c in cr.get("check_runs", []):
        print("  ", c["name"], c["status"], c["conclusion"])
    st = get(f"{BASE}/commits/{sha}/status")
    print("== status:", st.get("state"), [s.get("context") for s in st.get("statuses", [])])

    print("\nmain sha:", get(f"{BASE}/commits/main")["sha"][:8])
    print("base sha:", p["base"]["sha"][:8])


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
