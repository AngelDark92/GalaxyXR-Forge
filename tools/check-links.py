#!/usr/bin/env python
"""Check that every catalog.json URL answers.

Usage:
    python tools/check-links.py

Exit code 0 = all good, 1 = at least one failure.
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def status(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "gxr-forge-linkcheck"}, method="GET"
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:  # noqa: BLE001
        return str(e)


def main():
    cat = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    checked = 0
    failed = 0
    for g in cat["groups"]:
        for r in g["repos"]:
            urls = [r["url"]]
            if r.get("release"):
                urls.append(r["url"] + "/releases")
            for url in urls:
                s = status(url)
                ok = isinstance(s, int) and 200 <= s < 400
                print(("OK   " if ok else "FAIL ") + f"{s}  {url}")
                checked += 1
                if not ok:
                    failed += 1
    print(f"\n{checked} URLs checked, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
