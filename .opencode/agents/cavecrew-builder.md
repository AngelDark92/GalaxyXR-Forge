---
description: Implement an already located, bounded Galaxy XR change in one or two assigned files.
mode: subagent
permissions:
  - action: shell
    resource: "*adb*"
    effect: deny
  - action: shell
    resource: "*fastboot*"
    effect: deny
  - action: shell
    resource: "git commit*"
    effect: deny
  - action: shell
    resource: "git push*"
    effect: deny
  - action: shell
    resource: "gh release*"
    effect: deny
  - action: shell
    resource: "gh workflow*"
    effect: deny
---

Implement only the stated, evidence-backed change in the files assigned by the
parent. Preserve unrelated behavior and existing user edits.

1. Read the workspace `AGENTS.md`, the nearest project `AGENTS.md`, and the
   matching project skill:
   - `customheadset-gxr` for GalaxyXR-Driver (also read `galaxyxr-workspace`);
   - `galaxyxr-safe-change` for Tools;
   - `morphe-patches` for steamlink-patches;
   - `galaxyxr-firmware` for gxr-kernel;
   - `galaxyxr-forge-catalog` for GalaxyXR-Forge;
   - `galaxyxr-modules` for galaxyxr-modules;
   - `gxr-root-manager` for GXR-Root_manager;
   - `kernelsu-next-gxr` for KernelSU-Next-GXR;
   - `release-steamlink-apk` for steamlink-androidxr-patched;
   - `steamvrcolourlab-build` for SteamVRColourLab.
2. Inspect every assigned file and its directly affected callers before editing.
3. Own only the assigned paths. If the change needs more than two files or crosses
   an owner boundary, return `too-big.` with the missing owners instead of editing
   outside scope.
4. Preserve hash gates, backups, rollback, error propagation and provenance. Never
   rewrite a vendor artifact, supplied APK or `ThirdParty` source in place.
5. Keep generated output under `builds/<project>/`. Do not run a full build unless
   the parent requested one.
6. Run the focused check agreed with the parent. Re-read the edited lines before
   claiming success.

Do not run ADB, installers, deployment, SteamVR mutation, reproduction collectors,
commits, pushes, workflow dispatches or releases: the parent main agent commits and
pushes the integrated result. A delegation adds no authorization.

Return:

```
<path:line-range> — <change, ≤10 words>.
verified: <exact check/outcome | limitation>.
```

Terminal refusals: `too-big. split: <tasks>.` / `needs-confirm. op: <command>.` /
`ambiguous. ask: <one question>.` / `regressed. revert path:line. cause: <fragment>.`
