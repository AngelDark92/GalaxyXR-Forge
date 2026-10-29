---
name: galaxyxr-forge-news
description: "Use when posting, editing or removing a news item on the Galaxy XR Forge site. One file per post under news.d/, then tools/build.py; the site form and add-news workflow open a pull request."
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [news, documentation, workflow]
    category: software-development
    related_skills: [galaxyxr-forge-catalog, galaxyxr-forge-map]
---

# Post news on the Forge

Workspace scope: `GalaxyXR-Forge/`.

Source of truth: `news.d/<YYYY-MM-DD>-<slug>.json`, one file per post. `docs/index.html` is generated — never edit it. News posts are **not** catalog changes: they need no `changelog.d/` entry.

## Procedure

**Prefer the site.** The News tab's **Post news** button opens a prefilled issue labelled `add-news` (or titled `News: …`). `.github/workflows/add-news.yml` parses it with `tools/issue-payload.py --news`, runs `tools/add-news.py`, writes the file, rebuilds every generated file and opens a pull request. A maintainer reviews and merges it; nothing is published before that.

**CLI:**

```sh
python tools/add-news.py \
  --title "LinkFT is in the catalog" \
  --body "First paragraph.

Second paragraph, blank line between them." \
  --kind release \
  --repo compdoge/LinkFT \
  --link "Release notes|https://github.com/compdoge/LinkFT/releases"
```

Add `--summary "one line"`, `--date YYYY-MM-DD`, `--dry-run`, or `--json payload.json`. Exit codes: 0 written, 1 error, 2 duplicate.

**Manual / edit an existing post:**

1. Create or edit `news.d/<date>-<slug>.json`. Renaming the file changes the permalink; keep the original date.
2. `python tools/build.py` and review `git diff`.
3. Stage your file plus every regenerated file, commit, push.

## Schema

```json
{
  "date": "YYYY-MM-DD",
  "title": "max 120 chars",
  "kind": "site | release | community | guide",
  "summary": "optional, max 200 chars — omit and the first body paragraph is the lede",
  "body": ["1 to 8 paragraphs, each max 800 chars"],
  "repo": "owner/name",
  "links": [{ "label": "max 60 chars", "url": "https://…" }],
  "author": "github-handle",
  "issue": 42
}
```

- The file name is `<date>-<slug>.json`; the slug is lowercase `a-z0-9-`, ≤60 chars, and `date` **must** equal the prefix. Future dates fail the build.
- `repo` is optional; when it is not in the catalog the build warns and the post renders it as plain text.
- `body` may be one string for hand-written files (split on blank lines).
- `kind` defaults to `community` when omitted; the four labels are `Community`, `Release`, `Guide` and `Site update`.
- Inline `` `code` `` and `**bold**` are honoured in the title, summary and body.
- `links` accepts only absolute `https://` URLs, max 4.
- `author` renders as an `@handle` link; `issue` ties the post back to its proposal and blocks a second import of the same issue.

## Issue body contract

The form and the workflow share these headings:

```
### Title
### News
### Summary (optional)
### Category (optional)
### Related repo (optional)
### Link (optional — "Label | https://…" or a bare URL)
```

`ISSUE_USER` becomes `author`; `ISSUE_NUMBER` becomes `issue`; the date defaults to the run date.

## Pitfalls

- Never re-date a post on rebase. `python tools/repair-add-pr.py --main origin/main` rewrites the post with its **original** date when a news PR conflicts.
- One file per post: two pending submissions never touch the same file, so only generated files can conflict.
- Do not copy headlines into `README.md`. The only news reference there is the generated single News link near the top.
- Do not add a changelog entry for a post. The changelog is catalog history; the News tab is its own history.
- The `add-news` label is the intended marker. If the repository has no such label yet, the workflow still accepts an issue whose title starts with `News:`.
- News links are checked for `https://` shape only, not fetched: a flaky third-party URL must not fail CI.
