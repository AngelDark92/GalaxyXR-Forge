#!/usr/bin/env python
"""One-off: add an "added" date to every catalog.json entry.

Inserted as a text-level line edit right after each entry's "release" line so the
diff stays small. Everything that existed before the 2026-10-14 commits is
dated 2026-10-13; the four entries added on 2026-10-14 get that date.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog.json"

RECENT = {
    "compdoge/gxr-ksu-modules": "2026-10-14",
    "DienerTech/vectorxr": "2026-10-14",
    "ImranR98/Obtainium": "2026-10-14",
    "RJNY/Obtainium-Emulation-Pack": "2026-10-14",
    "whyorean/AuroraStore": "2026-10-14",
}
DEFAULT = "2026-10-13"

lines = CATALOG.read_text(encoding="utf-8").split("\n")
out = []
current = None
inserted = 0
for line in lines:
    m = re.match(r'\s*"repo": "([^"]+)",\s*$', line)
    if m:
        current = m.group(1)
    out.append(line)
    if re.match(r'\s*"release": ', line) and current:
        if '"added"' in line:
            continue
        out.append(f'          "added": "{RECENT.get(current, DEFAULT)}",')
        inserted += 1

CATALOG.write_text("\n".join(out), encoding="utf-8", newline="\n")
data = json.loads(CATALOG.read_text(encoding="utf-8"))
repos = [r for g in data["groups"] for r in g["repos"]]
missing = [r["repo"] for r in repos if "added" not in r]
print(f"inserted: {inserted} | repos: {len(repos)} | missing added: {missing}")
