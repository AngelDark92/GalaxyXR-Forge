---
name: galaxyxr-forge-catalog
description: "Use when adding, updating or removing a repo entry in the Galaxy XR Forge catalog. Edit catalog.json, run tools/build.py, check links, commit."
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [catalog, documentation, workflow]
    category: software-development
    related_skills: [galaxyxr-forge-map]
---

# Update the catalog

`catalog.json` is the single source of truth for the README and the docs site. `README.md` and `docs/index.html` are generated — never edit them by hand.

## Procedure

1. Open `catalog.json` and pick the target group by `groups[].id` (`root-kernel`, `kernelsu-modules`, `face-eye`, `pcvr-drivers`, `app-patches`, `games`, `tools`, `apps-samples`, `foundations`).
2. Add or edit one entry per repo:

   ```
   {
     "repo": "owner/name",
     "url": "https://github.com/owner/name",
     "about": "One short factual line, target ~14 words (build enforces 160 chars).",
     "license": "GPL-3.0",
     "release": "v1.2.3",
     "tags": ["optional", "search", "words"]
   }
   ```

   - `license`: SPDX id or `null` when the repo has none.
   - `release`: only when the repo has releases AND a single version stream. Per-module tags (e.g. `module-name/v0.1.0`) → use `null`; the badge would be misleading.
   - Bump the top-level `"updated"` date.
3. Regenerate and validate:
   - `python tools/build.py` (writes `README.md` + `docs/index.html`)
   - `python tools/check-links.py` (every URL must answer)
4. Review the `git diff` — README table and site cards both come from your entry.
5. Commit with a short message. Push only when the user authorized it.

## Pitfalls

- Hand-editing `README.md` or `docs/index.html` is lost work: `build.py` overwrites both entirely.
- Duplicate `repo` values or a bad URL fail the build on purpose — fix the catalog, not the build.
- Group `id` values are README anchors and site filter keys. Renaming breaks links; don't.
- Release badges are live (shields.io) — never hardcode versions in `about`.
- Keep `about` factual and stable; it appears in three places (README, site, search index).
