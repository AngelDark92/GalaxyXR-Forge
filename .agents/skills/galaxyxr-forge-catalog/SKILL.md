---
name: galaxyxr-forge-catalog
description: "Use when adding, updating or removing a repo entry in the Galaxy XR Forge catalog. One file per repo under catalog.d/, one changelog file under changelog.d/, then tools/build.py."
version: 1.1.0
license: MIT
metadata:
  hermes:
    tags: [catalog, documentation, workflow]
    category: software-development
    related_skills: [galaxyxr-forge-map]
---

# Update the catalog

Sources of truth:

- `catalog.json` — group metadata only (`id`, `title`, `icon`, `hue`, `blurb`).
- `catalog.d/<group>/<owner>__<name>.json` — one entry per repo.
- `changelog.d/<date>-<slug>.json` — one entry per change.

`README.md`, `CHANGELOG.md`, `docs/index.html` and `docs/catalog-index.json` are generated — never edit them by hand. One file per repo is deliberate: two pending additions touch different files, so they cannot conflict.

## Procedure

**Prefer the tool.** It does the whole addition in one command:

```sh
python tools/add-repo.py https://github.com/owner/name --group apps-samples
# optional: --about "…" --tags a,b --issue 12 --dry-run
```

It refuses private, archived, already-listed repos **and repos that already have an open issue or pull request**, reads license/release/topics, writes the entry file with today's `added` date, writes the changelog file, rebuilds every generated file and runs `check-links.py` + `check-repos.py`. It also refuses to run while `catalog.d/`, `changelog.d/` or `catalog.json` has uncommitted edits (`--force` overrides).

### Manual steps

1. Pick the group id: `root-kernel`, `kernelsu-modules`, `face-eye`, `pcvr-drivers`, `app-patches`, `games`, `tools`, `apps-samples`, `foundations`.
2. Create `catalog.d/<group>/<owner>__<name>.json`:

   ```json
   {
     "repo": "owner/name",
     "url": "https://github.com/owner/name",
     "about": "One short factual line, target ~14 words (build enforces 160 chars).",
     "license": "GPL-3.0",
     "release": "v1.2.3",
     "added": "YYYY-MM-DD",
     "tags": ["optional", "search", "words"]
   }
   ```

   - File name must match the repo exactly (`__` between owner and name); the build fails otherwise.
   - `license`: SPDX id or `null` when the repo has none.
   - `release`: only with a single version stream. Per-module tags (`module-name/v0.1.0`) → `null`.
   - `added`: the day the repo entered the catalog. Always set it — the NEW badge and New filter read it in the browser.
3. Create `changelog.d/<date>-<slug>.json`:

   ```json
   {
     "date": "YYYY-MM-DD",
     "title": "Short title",
     "items": ["Added owner/name to Group Title."]
   }
   ```

   One item per repo added, moved or removed. Never rewrite or delete older files.
4. Regenerate and validate: `python tools/build.py`, then `python tools/check-links.py` and `python tools/check-repos.py`.
5. Review `git diff` — the README table, the site cards and the Changelog tab all come from your files.
6. Commit and push: stage the entry, the changelog file and every regenerated file, commit, and push the current branch. This is standing authorization — do not stop to ask. If the push is rejected, open a PR. Leave unrelated user edits out of the commit.

## When the PR conflicts

Only generated files can conflict now. Do not hand-resolve. On the PR branch:

```sh
python tools/repair-add-pr.py --main origin/main
```

It resets the branch onto main, rewrites this branch's entry file and changelog file with the **original** `added` date, rebuilds and commits. The date is data: a rebase must never re-date an entry, or the NEW badge silently restarts.

## Pitfalls

- Hand-editing a generated file is lost work: `build.py` overwrites it entirely.
- A catalog change without a `changelog.d/` file is incomplete.
- A catalog change that is left uncommitted or unpushed is incomplete.
- Duplicate `repo` values (across any group) fail the build on purpose.
- Group `id` values are README anchors and site filter keys. Renaming breaks links; don't.
- Release badges are live (shields.io images with `?include_prereleases`); stars and latest tags load in the visitor's browser. Never hardcode versions or bake live values into generated files.
- Keep `about` factual and stable; it appears in the README, the site and search.
