# AGENTS.md — GalaxyXR-Forge

Always-on guidance for every agent working in this checkout. Current user instructions take precedence.

## What this repo is

GalaxyXR-Forge is the community index for **Samsung Galaxy XR** (SM-I610, Android XR) projects: the catalog, the generated README, the GitHub Pages site, and the project skills. There is no device code here — implementation work happens in the catalogued repositories. This repo describes, links and curates them.

## Golden rules

1. `catalog.json` is the single source of truth. Never hand-edit `README.md` or `docs/index.html` — both are generated.
2. After every catalog change run `python tools/build.py` (regenerates both files) and review the git diff before committing.
3. Keep descriptions to one factual line (build enforces ≤160 chars; target ~14 words). No marketing.
4. Do not rename group `id` values — README anchors, site filters and chips depend on them.
5. Commit and push only when the user asked. Editing files and running `build.py` / `check-links.py` are always fine; pushing to GitHub or changing Pages settings requires explicit authorization.
6. Links only: never copy code, binaries or proprietary blobs from catalogued repos into this one.
7. Keep `tools/build.py` and `tools/check-links.py` dependency-free (Python 3.10+, stdlib only) so any host can run them.

## Layout

| Path | Role |
| --- | --- |
| `catalog.json` | Source of truth: groups + repo entries; everything else derives from it |
| `tools/build.py` | Regenerates `README.md` and `docs/index.html` from `catalog.json` |
| `tools/check-links.py` | Checks that every catalog URL answers |
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
| Add / update / remove a catalog entry | Follow `.agents/skills/galaxyxr-forge-catalog/SKILL.md` |
| Find where a repo or project lives; which repo to touch | `.agents/skills/galaxyxr-forge-map/SKILL.md` |
| Adjust README or site layout | Edit the templates inside `tools/build.py`, rerun it |
| Bug in a driver, module, patch or app itself | Go to that project's checkout — do not fix it here |

## Agent hosts

| Host | Always-loaded context | Skills |
| --- | --- | --- |
| Hermes | `AGENTS.md` (git-root → cwd chain) | `.agents/skills/` after `hermes skills trust` in this checkout root |
| Codex | `AGENTS.md` | `.agents/skills/` |
| Claude Code | `CLAUDE.md` (points here) | none |
| GitHub Copilot | `.github/copilot-instructions.md` | none |

## Verification

- `python tools/build.py` exits 0 and prints repo/group counts; `python tools/build.py --check` validates without writing.
- `python tools/check-links.py` reports no failures.
- Never claim the Pages site updated without fetching the live URL.
