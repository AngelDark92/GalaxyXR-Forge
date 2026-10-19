---
name: galaxyxr-forge-catalog
description: "Use when adding, updating or removing a repo entry in the Galaxy XR Forge catalog. Edit catalog.json + changelog.json, run tools/build.py, check links, commit."
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [catalog, documentation, workflow]
    category: software-development
    related_skills: [galaxyxr-forge-map]
---

# Update the catalog

`catalog.json` lists the repos; `changelog.json` records every change to that list. `README.md`, `CHANGELOG.md` and `docs/index.html` are generated — never edit them by hand.

## Procedure

**Prefer the tool.** For an addition it does everything below in one command:

```sh
python tools/add-repo.py https://github.com/owner/name --group apps-samples
# optional: --about "…" --tags a,b --issue 12 --dry-run
```

It refuses private, archived or already-listed repos, reads license/release/topics, writes the entry with today's `added` date, appends the changelog entry, rebuilds all generated files and runs `check-links.py` + `check-repos.py`. The manual steps stay for moves, removals and overrides.

### Manual steps

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
   - `release`: only when the repo has releases AND a single version stream. Per-module tags (e.g. `module-name/v0.1.0`) → use `null`; the badge would be misleading. It only gates the README badge: the site loads star counts and the latest release live in the browser (prereleases included) for every repo, so the value never needs bumping.
   - `added`: the date the repo entered this catalog, `YYYY-MM-DD`. Always set it on a new entry — the site's NEW badge and New filter read it (browser-side, 5-day window; badge and filter share the one predicate).
   - Bump the top-level `"updated"` date.
3. Add a `changelog.json` entry covering the same change, newest first:

   ```
   {
     "date": "YYYY-MM-DD",
     "title": "Short title",
     "items": ["Added owner/name to Group Title."]
   }
   ```

   One item per repo added, moved or removed. Never rewrite or delete older entries; append only.
4. Regenerate and validate:
   - `python tools/build.py` (writes `README.md`, `CHANGELOG.md` + `docs/index.html`)
   - `python tools/check-links.py` (every URL must answer)
5. Review the `git diff` — the README table, the site cards and the Changelog tab all come from your edits.
6. Commit with a short message. Push only when the user authorized it.

## Pitfalls

- Hand-editing `README.md` or `docs/index.html` is lost work: `build.py` overwrites both entirely.
- A catalog change without a `changelog.json` entry is incomplete: the site's Changelog tab and `CHANGELOG.md` are generated from that file, and every build overwrites them.
- Append changelog entries newest first; never rewrite or delete history.
- Duplicate `repo` values or a bad URL fail the build on purpose — fix the catalog, not the build.
- Group `id` values are README anchors and site filter keys. Renaming breaks links; don't.
- Release badges are live (shields.io images; keep `?include_prereleases` in the URL or beta-only repos show a red "no releases" badge), and the site loads star counts and latest tags in the visitor's browser (shields.io JSON → `localStorage`, 30-min TTL, badge image as fallback) — never hardcode versions in `about`, and never bake star counts, release tags or other live values into generated files.
- Keep `about` factual and stable; it appears in three places (README, site, search index).
