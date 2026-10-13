#!/usr/bin/env python
"""Fetch metadata for the final batch of candidate Galaxy XR repos."""
import json
import os
import urllib.error
import urllib.request

TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
H = {"User-Agent": "gxr-meta"}
if TOKEN:
    H["Authorization"] = f"Bearer {TOKEN}"

REPOS = [
    "4uva4ek/galaxy-xr-game-link",
    "BlueScorpioVR/WinlatorXR",
    "SinonVT/GalaxyXR-EyeTracking-Fix-Virtual-Desktop",
    "diabl0w/Root-My-Galaxy-Payloads",
]


def get(url):
    req = urllib.request.Request(url, headers=H)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"__http__": e.code}
    except Exception as e:  # noqa: BLE001
        return {"__err__": str(e)}


for full in REPOS:
    m = get(f"https://api.github.com/repos/{full}")
    if "__http__" in m or "__err__" in m:
        print(f"{full}: FAIL {m.get('__http__', m.get('__err__'))}")
        continue
    rel = get(f"https://api.github.com/repos/{full}/releases/latest")
    lic = (m.get("license") or {}).get("spdx_id")
    print(
        f"{full}: stars={m['stargazers_count']} forks={m['forks_count']} "
        f"license={lic} release={rel.get('tag_name') if '__http__' not in rel else None} "
        f"pushed={m.get('pushed_at')} fork={m.get('fork')} parent={((m.get('parent') or {}).get('full_name'))}"
    )
    print(f"    desc: {m.get('description')}")
