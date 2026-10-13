#!/usr/bin/env python
"""One-off research helper: fetch GitHub metadata for Galaxy XR candidate repos.

Reads GITHUB_TOKEN from the environment (optional). Writes listed-repos.json
next to this script and prints a readable summary, including a few search
queries so extra Galaxy XR repos surface for review.

This file is a research artifact; it is not part of the published catalog
workflow (tools/build.py is).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
HEADERS = {"User-Agent": "gxr-forge-meta"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

REPOS = [
    # the 10 repos from the task list (unique)
    "4uva4ek/overport-galaxyxr",
    "4uva4ek/galaxyxr-modules",
    "4uva4ek/KernelSU-GXR",
    "evertec82/AstroQuest",
    "AngelDark92/GalaxyXR-Driver",
    "AngelDark92/xr-porting-hub",
    "AngelDark92/SteamVRColourLab",
    "logkim1/4XVR-GalaxyXR",
    "timkhronos/CustomHeadsetOpenVrGxR",
    "BreadDoesStuff/galaxy-xr-modules",
    # candidate extras
    "4uva4ek/overport",
    "AngelDark92/gxr-kernel",
    "AngelDark92/KernelSU-Next-GXR",
    "AngelDark92/GXR-Root_manager",
    "AngelDark92/GalaxyXR-Forge",
    "diabl0w/DFRoot",
    "diabl0w/KernelSU",
    "sboys3/CustomHeadsetOpenVR",
    "shadps4-emu/shadPS4",
    "zenithblue-oss/shadps4-arm64",
    "Vauzi-17/mesa-tu8",
    "MorpheApp/morphe-manager",
    "MorpheApp/Morphe-Manager",
    "MorpheApp/morphe-patches",
]

SEARCHES = [
    "morphe manager android patcher",
    "galaxy xr headset",
    "galaxyxr",
    "xrvst2",
    "galaxy xr kernelSU",
    "galaxy xr steam link",
]


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"__http__": e.code}
    except Exception as e:  # noqa: BLE001
        return {"__err__": str(e)}


def main():
    out = []
    for full in REPOS:
        meta = get(f"https://api.github.com/repos/{full}")
        if "__http__" in meta or "__err__" in meta:
            status = meta.get("__http__", meta.get("__err__"))
            out.append({"repo": full, "status": status})
            print(f"{full}: FAIL {status}")
            continue
        rel = get(f"https://api.github.com/repos/{full}/releases/latest")
        lic = (meta.get("license") or {}).get("spdx_id")
        row = {
            "repo": full,
            "url": meta["html_url"],
            "description": meta.get("description"),
            "stars": meta["stargazers_count"],
            "forks": meta["forks_count"],
            "license": None if lic in (None, "NOASSERTION") else lic,
            "default_branch": meta.get("default_branch"),
            "pushed_at": meta.get("pushed_at"),
            "archived": meta.get("archived"),
            "fork": meta.get("fork"),
            "homepage": meta.get("homepage"),
            "latest_release": None if "__http__" in rel or "__err__" in rel else rel.get("tag_name"),
        }
        out.append(row)
        print(
            f"{full}: OK stars={row['stars']} license={row['license']} "
            f"release={row['latest_release']} pushed={row['pushed_at']}"
        )
        time.sleep(0.2)

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "listed-repos.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote {path} ({len(out)} entries)")

    for q in SEARCHES:
        url = "https://api.github.com/search/repositories?q=" + urllib.parse.quote(q) + "&sort=stars&per_page=8"
        res = get(url)
        items = res.get("items", []) if isinstance(res, dict) else []
        print(f"\n== search: {q}  ({len(items)} results)")
        for it in items:
            desc = str(it.get("description"))[:80]
            print(f"  {it['full_name']}  stars={it['stargazers_count']}  {desc}")


if __name__ == "__main__":
    sys.exit(main())
