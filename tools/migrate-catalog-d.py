#!/usr/bin/env python
"""One-off migration: split catalog.json and changelog.json into catalog.d / changelog.d.

    python tools/migrate-catalog-d.py

Writes one file per repo (catalog.d/<group>/<owner>__<name>.json) and one per
changelog entry (changelog.d/<date>-<slug>.json), then rewrites catalog.json to
group metadata only. Safe to re-run: existing entry files are left alone.
"""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog.json"
CHANGELOG = ROOT / "changelog.json"


def load_build():
    spec = importlib.util.spec_from_file_location("gxr_build", ROOT / "tools" / "build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    build = load_build()
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    log = json.loads(CHANGELOG.read_text(encoding="utf-8"))

    repos = 0
    for group in cat["groups"]:
        for entry in group.pop("repos", []):
            path = build.repo_path(group["id"], entry["repo"])
            if path.exists():
                continue
            build.write_repo_entry(group["id"], entry)
            repos += 1

    logs = 0
    for entry in log["entries"]:
        slug = build.write_changelog_entry(entry)
        logs += 1

    CATALOG.write_text(build.dump_json(cat), encoding="utf-8", newline="\n")
    print(f"wrote {repos} catalog entries, {logs} changelog entries")
    print("catalog.json now holds group metadata only; changelog.json can be removed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
