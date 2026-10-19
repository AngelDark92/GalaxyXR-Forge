# AGENTS.md — GalaxyXR-Forge

Always-on guidance for every agent working in this checkout. Current user instructions take precedence.

## What this repo is

GalaxyXR-Forge is the community index for **Samsung Galaxy XR** (SM-I610, Android XR) projects: the catalog, the generated README, the GitHub Pages site, and the project skills. There is no device code here — implementation work happens in the catalogued repositories. This repo describes, links and curates them.

## Golden rules

1. `catalog.json` and `changelog.json` are the single sources of truth. Never hand-edit `README.md`, `CHANGELOG.md` or `docs/index.html` — they are generated.
2. After every catalog change run `python tools/build.py` (regenerates README, changelog and site) and review the git diff before committing.
3. Keep descriptions to one factual line (build enforces ≤160 chars; target ~14 words). No marketing.
4. Every catalog change needs an entry in `changelog.json` (date, title, one item per repo added, moved or removed). `build.py` renders `CHANGELOG.md` and the site's Changelog tab from it — a catalog edit without a changelog entry is an incomplete change. Set `"added": "YYYY-MM-DD"` on every new entry: the site's NEW badge and New filter derive from it, computed client-side because Pages is static: one rule for both the badge and the New filter — an entry is NEW while its `added` date is inside the 5-day window.
5. Do not rename group `id` values — README anchors, site filters and chips depend on them.
6. Commit and push only when the user asked. Editing files and running `build.py` / `check-links.py` / `check-repos.py` are always fine; pushing to GitHub or changing Pages settings requires explicit authorization.
7. Links only: never copy code, binaries or proprietary blobs from catalogued repos into this one.
8. Keep every tool in `tools/` dependency-free (Python 3.10+, stdlib only) so any host can run them.
9. Add repos with `python tools/add-repo.py <url> --group <id>` — it validates visibility, writes the entry and changelog, rebuilds every generated file and runs both checks. Do not hand-write entries when the tool can do it.
10. CI is the gate: `validate.yml` re-runs the build, fails any PR whose generated files differ (stale or hand-edited), and runs the link and repo-state checks. A red PR is not reviewable.

## Layout

| Path | Role |
| --- | --- |
| `catalog.json` | Source of truth: groups + repo entries; everything else derives from it |
| `changelog.json` | Source of truth for the change history: one entry per catalog change |
| `tools/build.py` | Regenerates `README.md`, `CHANGELOG.md` and `docs/index.html` from the two JSON inputs |
| `CHANGELOG.md` | Generated changelog (the GitHub view of `changelog.json`) |
| `tools/check-links.py` | Checks that every catalog URL answers |
| `tools/check-repos.py` | Reads each repo back: renamed, transferred, archived or gone |
| `tools/add-repo.py` | One-command contributor tool: validate, entry + changelog, rebuild, checks |
| `tools/issue-payload.py` | Turns an `add-repo` issue body into the JSON payload the tool reads |
| `.github/workflows/validate.yml` | PR gate: catalog check, generated files fresh, links, repo state |
| `.github/workflows/add-repo.yml` | Issue labelled `add-repo` → branch + PR through `add-repo.py` |
| `README.md` | Generated GitHub landing page |
| `docs/` | Generated GitHub Pages site (Pages: branch `main`, folder `/docs`) |
| `docs/.nojekyll` | Disables Jekyll on Pages; keep it |
| `.agents/skills/` | Project skills; see the host table below |
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
| Add / update / remove a catalog entry (plus its changelog entry) | Follow `.agents/skills/galaxyxr-forge-catalog/SKILL.md` |
| A visitor proposed a repo (issue labelled `add-repo`) | `add-repo.yml` already ran `tools/add-repo.py` and opened a PR; review and merge it |
| Find where a repo or project lives; which repo to touch | `.agents/skills/galaxyxr-forge-map/SKILL.md` |
| Adjust README or site layout | Edit the templates inside `tools/build.py`, rerun it |
| Confirm catalogued repos still exist and are not renamed, transferred or archived | `python tools/check-repos.py` |
| Bug in a driver, module, patch or app itself | Go to that project's checkout — do not fix it here |

## Agent hosts

| Host | Always-loaded context | Skills |
| --- | --- | --- |
| Hermes | `AGENTS.md` (git-root → cwd chain) | `.agents/skills/` after `hermes skills trust` in this checkout root |
| Codex | `AGENTS.md` | `.agents/skills/` |
| Claude Code | `CLAUDE.md` (points here) | none |
| GitHub Copilot | `.github/copilot-instructions.md` | none |

## Verification

- `python tools/build.py` exits 0 and prints repo, group and changelog counts; `python tools/build.py --check` validates without writing.
- Every catalog edit carries a matching `changelog.json` entry, appended newest first, and a new entry carries its `added` date.
- The NEW badge is browser-side logic over `data-added`; it expires on its own after 5 days with no rebuild. Do not freeze "new" into the generated README or the site HTML.
- Star counts and latest releases on the site cards are fetched in the visitor's browser (shields.io JSON + `localStorage` cache; the badge image is the no-JS/failure fallback). Live values are never baked into the README, the site HTML or the changelog.
- `python tools/check-links.py` reports no failures.
- `validate.yml` is green on the PR: catalog check, stale-generated check, links, repo state.
- A bot PR (`add-repo.yml`) dispatches `validate.yml` on its branch explicitly: a branch pushed with `GITHUB_TOKEN` never fires `pull_request`, so without the dispatch the gate would silently not run.
- `python tools/check-repos.py` reports no renames, transfers, archived or missing repos. A renamed repo still answers, so link checks alone will not catch it.
- Never claim the Pages site updated without fetching the live URL.
