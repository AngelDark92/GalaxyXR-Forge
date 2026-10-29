# AGENTS.md — GalaxyXR-Forge

Always-on guidance for every agent working in this checkout. Current user instructions take precedence.

## What this repo is

GalaxyXR-Forge is the community index for **Samsung Galaxy XR** (SM-I610, Android XR) projects: the catalog, the generated README, the GitHub Pages site, and the project skills. There is no device code here — implementation work happens in the catalogued repositories. This repo describes, links and curates them.

## Golden rules

1. `catalog.json` (group metadata), `catalog.d/` (one file per repo), `modules.d/` (one file per module-publishing repo), `news.d/` (one file per news post) and `changelog.d/` (one file per change) are the single sources of truth. Never hand-edit `README.md`, `CHANGELOG.md`, `docs/index.html`, `docs/catalog-index.json` or `docs/news.json` — they are generated.
2. After every catalog or news change run `python tools/build.py` (regenerates README, changelog and site) and review the git diff before committing.
3. Keep descriptions to one factual line (build enforces ≤160 chars; target ~14 words). No marketing.
4. Every catalog change needs an entry in `changelog.d/` (date, title, one item per repo added, moved or removed). `build.py` renders `CHANGELOG.md` and the site's Changelog tab from it — a catalog edit without a changelog entry is an incomplete change. News posts are not catalog changes: they live in `news.d/` and need no changelog entry. Set `"added": "YYYY-MM-DD"` on every new entry: the site's NEW badge and New filter derive from it, computed client-side because Pages is static: one rule for both the badge and the New filter — an entry is NEW while its `added` date is inside the 5-day window.
5. Do not rename group `id` values — README anchors, site filters and chips depend on them.
6. Commit and push every completed change. This is standing authorization: after the checks pass and you have reviewed the diff, stage only the files you changed, commit, and push the current branch. Do not stop to ask for commit or push permission. Read-only subagents never commit; the main agent commits their integrated result. Leave unrelated user edits unstaged. If the push is rejected, open a PR. Changing Pages settings still requires explicit authorization.
7. Links only: never copy code, binaries or proprietary blobs from catalogued repos into this one.
8. Keep every tool in `tools/` dependency-free (Python 3.10+, stdlib only) so any host can run them.
9. Add repos with `python tools/add-repo.py <url> --group <id>` — it validates visibility, writes the entry and changelog, rebuilds every generated file and runs both checks. Do not hand-write entries when the tool can do it.
10. CI is the gate: `validate.yml` re-runs the build, fails any PR whose generated files differ (stale or hand-edited), and runs the link and repo-state checks. A red PR is not reviewable.
11. Entries are one file each, so two pending adds never touch the same file; only generated files can conflict. Never hand-resolve those: run `python tools/repair-add-pr.py --main origin/main` on the branch. It resets onto main, rewrites this branch's entry file with its **original** `added` date (or the news post with its original `date`), rebuilds and commits. `added` is a fact — a rebase must never re-date an entry.
12. `catalog.json` has no `updated` field: `build.py` derives it from entry and changelog dates, so one PR cannot overwrite another's stamp.
13. Open in-repo PRs are rebased automatically when `main` moves (`rebase-open-prs.yml`): clean rebase pushed as-is, conflict rebuilt by `repair-add-pr.py`, then `validate.yml` is dispatched on the branch. Fork PRs are skipped — this workflow cannot push to them.
14. `main` has branch protection requiring the `catalog` status. `validate.yml` publishes it as a **commit status**, not only a check run: a check run from a dispatched run is not attached to the pull request, so protection would sit at "blocked" forever. Admins are exempt, so direct pushes still work.

## Layout

| Path | Role |
| --- | --- |
| `catalog.json` | Group metadata (id, title, icon, hue, blurb); entries live in `catalog.d/` |
| `catalog.d/<group>/<owner>__<name>.json` | One repo entry per file — an add touches exactly one file |
| `modules.d/<owner>__<name>.json` | Module list per module-publishing repo, grouped by repo in the site's Kernel modules tab |
| `news.d/<date>-<slug>.json` | One news post per file; `build.py` sorts newest first and renders the site's News tab |
| `changelog.d/<date>-<slug>.json` | One changelog entry per file; `build.py` sorts newest first |
| `tools/build.py` | Merges `catalog.d/` + `modules.d/` + `news.d/` + `changelog.d/` into `README.md`, `CHANGELOG.md`, `docs/index.html`, `docs/catalog-index.json`, `docs/news.json` |
| `CHANGELOG.md` | Generated changelog (the GitHub view of `changelog.d/`) |
| `tools/check-links.py` | Checks that every catalog URL answers |
| `tools/check-repos.py` | Reads each repo back: renamed, transferred, archived or gone |
| `tools/add-repo.py` | One-command contributor tool: validate, entry + changelog, rebuild, checks |
| `tools/add-news.py` | One-command news post: validate against the catalog, write `news.d/`, rebuild |
| `tools/repair-add-pr.py` | Rebuilds a conflicted add-PR or news PR on main; keeps the entry's original `added` / `date` |
| `tools/issue-payload.py` | Turns an `add-repo` or `add-news` issue body into the JSON payload the tools read |
| `.github/workflows/validate.yml` | PR gate: catalog check, generated files fresh, links, repo state |
| `.github/workflows/add-repo.yml` | Issue labelled `add-repo` → branch + PR through `add-repo.py` |
| `.github/workflows/add-news.yml` | Issue labelled `add-news` or titled `News: …` → branch + PR through `add-news.py` |
| `.github/workflows/rebase-open-prs.yml` | On every `main` push: rebases open PRs, repairs conflicts, re-runs `validate` |
| `README.md` | Generated GitHub landing page |
| `docs/` | Generated GitHub Pages site (Pages: branch `main`, folder `/docs`) |
| `docs/news.json` | Generated news archive (every post as rendered HTML); the News tab fetches it on demand |
| `docs/.nojekyll` | Disables Jekyll on Pages; keep it |
| `.opencode/skills/` | Workspace skills; see the host table below |
| `.research/` | Metadata snapshots and fetch scripts used to build the catalog (safe to publish; token comes from env) |
| `IDEA.md` | Owner notes. Leave as-is. |

## Where the actual work lives (owner machine)

Root: `D:\Angelo\Desktop\SteamLink-GalaxyXR-Windows-Toolkit-FULL\`

| Catalog repo | Local checkout | Use it for |
| --- | --- | --- |
| AngelDark92/GalaxyXR-Driver | `../GalaxyXR-Driver` (main) and `../GalaxyXR-Driver-dev` (branch `dev`, dev channel) | SteamVR driver work; each checkout has its own AGENTS.md + skills |
| AngelDark92/xr-porting-hub | `../steamlink-patches` (canonical name is xr-porting-hub) | Steam Link Morphe patches and releases |
| gxr-kernel (local workspace; nested repos not all public) | `../gxr-kernel` | Kernel/root research; contains nested checkouts `KernelSU-Next-GXR/`, `GXR-Root_manager/`, `galaxyxr-modules/` |
| AngelDark92/SteamVRColourLab | `../SteamVRColourLab` | Colour Lab app and tests |
| (build outputs) | `../builds/<project>/` | Every generated build artifact, per the sibling-project artifact contract |
| (APK stash) | `../Best Apks` | Local APKs, not a repo |
| (toolkit) | `../Tools` | ADB/platform tools, diagnostics, install scripts |

Nested checkouts inside `gxr-kernel/` are separate GitHub repos (some private): commit them in their own checkout, not "through" gxr-kernel, and do not link a private repo from the public catalog until it is public.

## Task routing

| Task | Do this |
| --- | --- |
| Add / update / remove a catalog entry (plus its changelog entry) | Follow `.opencode/skills/galaxyxr-forge-catalog/SKILL.md` |
| A visitor proposed a repo (issue labelled `add-repo`) | `add-repo.yml` already ran `tools/add-repo.py` and opened a PR; review and merge it |
| Post or edit a news item on the site | `.opencode/skills/galaxyxr-forge-news/SKILL.md` — site form, `python tools/add-news.py`, or hand-write one `news.d/` file |
| Find where a repo or project lives; which repo to touch | `.opencode/skills/galaxyxr-forge-map/SKILL.md` |
| Adjust README or site layout | Edit the templates inside `tools/build.py`, rerun it |
| Add or update the Kernel modules tab | Edit `modules.d/<owner>__<name>.json`, rerun `python tools/build.py` |
| Confirm catalogued repos still exist and are not renamed, transferred or archived | `python tools/check-repos.py` |
| Bug in a driver, module, patch or app itself | Go to that project's checkout — do not fix it here |

## Agent hosts

| Host | Always-loaded context | Skills |
| --- | --- | --- |
| OpenCode | `../AGENTS.md` and `AGENTS.md` | `.opencode/skills/` and `.opencode/agents/`; workspace copies also load when run from the root |
| Cursor | `.cursor/rules/project.mdc`, `AGENTS.md` | rules only; skills stay in `.opencode/skills/` |
| Hermes | `AGENTS.md` (git-root → cwd chain) | `.agents/skills/` after `hermes skills trust` in this checkout root |
| Codex | `AGENTS.md` | `.agents/skills/` |
| Claude Code | `CLAUDE.md` (points here) | none |
| GitHub Copilot | `.github/copilot-instructions.md` | none |

## Verification

- `python tools/build.py` exits 0 and prints repo, group, module, news and changelog counts; `python tools/build.py --check` validates without writing.
- Every `modules.d/` file names a catalogued repo and a valid module status; a `kernelsu-modules` repo without module records produces a warning.
- Every `news.d/` file matches `YYYY-MM-DD-slug.json`, its `date` equals the file prefix and is not in the future, and its body has 1–8 paragraphs. A post whose `repo` is not catalogued produces a warning.
- News is paginated: `docs/index.html` carries only the newest `NEWS_PAGE_SIZE` posts; `docs/news.json` holds the whole archive and is fetched on demand. Deep links (`#news-<stem>`) must still reach an older post, and the newest page must read without JS.
- Every catalog edit carries a matching `changelog.d/` entry, appended newest first, and a new entry carries its `added` date. News posts do not create changelog entries.
- The NEW badge is browser-side logic over `data-added`; it expires on its own after 5 days with no rebuild. Do not freeze "new" into the generated README or the site HTML.
- Star counts and latest releases on the site cards are fetched in the visitor's browser (shields.io JSON + `localStorage` cache; the badge image is the no-JS/failure fallback). Live values are never baked into the README, the site HTML or the changelog.
- `python tools/check-links.py` reports no failures.
- `validate.yml` is green on the PR: catalog check, stale-generated check, links, repo state.
- A bot PR (`add-repo.yml`) dispatches `validate.yml` on its branch explicitly: a branch pushed with `GITHUB_TOKEN` never fires `pull_request`, so without the dispatch the gate would silently not run.
- `python tools/check-repos.py` reports no renames, transfers, archived or missing repos. A renamed repo still answers, so link checks alone will not catch it.
- Every completed change is committed and pushed; `git status --short` shows only unrelated user edits before you report done.
- Never claim the Pages site updated without fetching the live URL.
