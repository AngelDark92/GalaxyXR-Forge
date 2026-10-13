#!/usr/bin/env python
"""Fetch metadata for a few extra Galaxy XR repos and sweep key user pages."""
import json
import os
import urllib.error
import urllib.request

TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
H = {"User-Agent": "gxr-meta"}
if TOKEN:
    H["Authorization"] = f"Bearer {TOKEN}"

REPOS = [
    "ovrport/app",
    "compdoge/gxr-alvr-ft",
    "compdoge/gxr-face-bridge",
    "BlueScorpioVR/galaxyxr-modules",
    "MorpheApp/morphe-patches",
]

USERS = [
    "4uva4ek", "AngelDark92", "compdoge", "logkim1", "timkhronos",
    "BreadDoesStuff", "evertec82", "BlueScorpioVR", "SinonVT", "diabl0w",
]

KEY = ("gxr", "galaxy", "xrvst", "kernelsu", "steamlink", "steam link",
       "morphe", "overport", "4xvr", "vrlink", "xr-")


def get(url):
    req = urllib.request.Request(url, headers=H)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"__http__": e.code}
    except Exception as e:  # noqa: BLE001
        return {"__err__": str(e)}


def main():
    print("== extra repos")
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
            f"pushed={m.get('pushed_at')} fork={m.get('fork')}\n    desc: {m.get('description')}"
        )

    print("\n== user sweeps")
    for u in USERS:
        repos = get(f"https://api.github.com/users/{u}/repos?per_page=100&sort=pushed")
        if not isinstance(repos, list):
            print(f"{u}: FAIL {repos}")
            continue
        hits = []
        for it in repos:
            text = (it["name"] + " " + str(it.get("description"))).lower()
            if any(k in text for k in KEY):
                hits.append(it)
        print(f"{u}: {len(repos)} repos, {len(hits)} GXR-ish")
        for it in hits:
            print(
                f"  {it['full_name']} stars={it['stargazers_count']} fork={it['fork']} "
                f"pushed={it['pushed_at'][:10]} :: {str(it.get('description'))[:90]}"
            )


if __name__ == "__main__":
    main()
