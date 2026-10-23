---
name: galaxyxr-forge-map
description: "Use when you need to know where a Galaxy XR repo or local checkout lives, or which repo to touch for a Galaxy XR task. Hub map: groups, local paths, routing."
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [galaxy-xr, map, routing, workspace]
    category: software-development
    related_skills: [galaxyxr-forge-catalog]
---

# Galaxy XR repo map

Workspace scope: `GalaxyXR-Forge/`. Prose paths below are relative to that
checkout unless they are explicit workspace links.

Where everything Galaxy XR lives. `catalog.json` in the GalaxyXR-Forge repo is the source of truth for the published list (repo, group, description); this skill adds the local-machine layout and the routing rules.

## Read first

- `catalog.json` — every catalogued repo, grouped by id: `root-kernel`, `kernelsu-modules`, `face-eye`, `pcvr-drivers`, `app-patches`, `games`, `tools`, `apps-samples`, `foundations`.
- `AGENTS.md` — rules for working in the Forge repo.

## Local checkouts (owner machine)

Root: `D:\Angelo\Desktop\SteamLink-GalaxyXR-Windows-Toolkit-FULL\`

| What | Path | Notes |
| --- | --- | --- |
| GalaxyXR-Driver (production) | `../GalaxyXR-Driver` | SteamVR driver; own AGENTS.md + workspace `.opencode/skills/` |
| GalaxyXR-Driver (dev channel) | `../GalaxyXR-Driver-dev` | Branch `dev`; dev releases |
| xr-porting-hub | `../steamlink-patches` | Steam Link Morphe patches (canonical repo name is xr-porting-hub) |
| gxr-kernel | `../gxr-kernel` | Kernel/root research workspace; nested checkouts `KernelSU-Next-GXR/`, `GXR-Root_manager/`, `galaxyxr-modules/` — not all public |
| SteamVRColourLab | `../SteamVRColourLab` | Colour Lab app + tests |
| Build outputs | `../builds/<project>/` | All build artifacts live outside checkouts |
| APK stash | `../Best Apks` | Local APKs, not a repo |
| Toolkit | `../Tools` | ADB/platform tools, diagnostics, install scripts |

Nested repos inside `gxr-kernel/` are separate GitHub repos. Commit them in their own checkout, never "through" gxr-kernel.

## Which repo for the task

| You want to... | Go to |
| --- | --- |
| Root the headset / manage root | `4uva4ek/KernelSU-GXR` + `diabl0w/DFRoot`; local: `../gxr-kernel` |
| Device-side tracking, haptic or thermal fixes | `4uva4ek/galaxyxr-modules`, `BreadDoesStuff/galaxy-xr-modules` (KernelSU modules) |
| SteamVR / PCVR driver issues (identity, resolution, colour, distortion) | `../GalaxyXR-Driver` (production) or `../GalaxyXR-Driver-dev` (dev) |
| Steam Link app patches (resolution, mic, permissions, tracking) | `../steamlink-patches` (xr-porting-hub) |
| Face or eye tracking in PC VR | `compdoge/gxr-alvr-ft`, `compdoge/gxr-face-bridge` |
| Patch a Quest/PICO APK for Galaxy XR | xr-porting-hub patch source + `MorpheApp/morphe-manager` |
| PS4 games on the headset | `evertec82/AstroQuest` |
| Panel colour testing | `../SteamVRColourLab` |
| Update the hub itself | This repo: `.opencode/skills/galaxyxr-forge-catalog/SKILL.md` |

## Rules

- Every non-Forge checkout is its own project with its own AGENTS.md and skills; read those before editing anything.
- Do not duplicate repo descriptions here — `catalog.json` owns them. When a repo moves or a new one is adopted, update `catalog.json`, rerun `tools/build.py`, and refresh the local-path table above if the layout changed.
- Private repos stay out of `catalog.json` until they are public — dead links break `tools/check-links.py`.
