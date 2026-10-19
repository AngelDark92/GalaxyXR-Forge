# Changelog

Catalog changes, newest first. Generated from [`changelog.json`](changelog.json) by `tools/build.py` — never edit this file by hand.

## 2026-10-19 — Add-PR conflicts repaired, entry dates preserved

- `catalog.json` no longer stores `updated`: `build.py` derives the newest date from entries and the changelog, so two pending adds no longer edit the same line.
- `tools/repair-add-pr.py` rebuilds a conflicted add-PR on main: it keeps this branch's entry and its **original** `added` date, takes main's generated files, rebuilds and commits. A rebase never re-dates an entry.
- `tools/add-repo.py` refuses to run while `catalog.json` or `changelog.json` has uncommitted edits, so a pending add in the same checkout cannot ride into the next entry (`--force` overrides).

## 2026-10-19 — Bachata-S4 added

- Added JICA98/Bachata-S4 to Foundations & Upstreams (issue #2).

## 2026-10-19 — One-command add and a zero-backend contribution path

- `tools/add-repo.py` adds a repo in one command: it refuses private, archived or already-listed repos, reads license, latest release and topics, writes the entry with today's date, appends the changelog entry, rebuilds every generated file and runs both link checks.
- The site now has an **Add repo** button: paste the link, pick a group, and it opens a prefilled GitHub issue. `add-repo.yml` turns that issue into a branch and a pull request through the same tool; it never trusts the issue for anything but the URL and the group.
- `validate.yml` gates every pull request: catalog and changelog validation, a stale-generated-file diff, `check-links.py` and `check-repos.py`. A PR with hand-edited or stale `README.md`, `CHANGELOG.md` or `docs/index.html` cannot merge.
- `tools/issue-payload.py` parses the issue body; `.github/ISSUE_TEMPLATE/add-repo.md` is the manual form of the same three fields.

## 2026-10-19 — ScreenStreamerXR added

- Added BlueScorpioVR/ScreenStreamerXR to Apps & Samples (issue #1).

## 2026-10-17 — AstroQuest back in the catalog

- Restored evertec82/AstroQuest to Games & Emulation. It had answered 404 from three independent checks — the GitHub API, shields.io and a signed-in browser — and was removed; it answers again, so the card is back.
- Its release badge now reads v0.8.6 (Game 1.04 soccer timing fix, 2026-10-14). Every other catalogued repo was re-checked the same way: 54 of 54 are present, none renamed, transferred, archived or gone.

## 2026-10-17 — Filter figures now count what each filter would show

- Every number in the filters panel is computed from the current selection: group counts follow the search box and the active status filters, status counts also follow the chosen group, and each status chip counts the repositories it would leave on screen.
- Fixed: collapsing the panel wrapped the repo grid into a second grid row and pushed the whole catalog down the page — the collapsed track now shrinks to zero instead of dropping out of the grid.
- Fixed: on desktop the panel no longer closes when a card is clicked; the Filters button and Escape close it, and the phone drawer keeps its backdrop click.

## 2026-10-17 — AstroQuest removed; badge errors no longer print

- Removed evertec82/AstroQuest from Games & Emulation: the repository is gone now (GitHub answers 404), so its card linked nowhere.
- Site cards no longer print an error word as a figure: when shields.io answers "invalid" or another error string, that badge is hidden rather than showing the word, the string is never cached, and the value is retried once the cache expires.
- A release pill now only appears for repositories the catalog gives a single release stream, so the live lookup can no longer add one to a card built without a release badge.

## 2026-10-17 — Filters menu opens as a glass dropdown

- The filter panel is frosted glass now: translucent gradient, blur and saturation backdrop filter, hairline border and a deep shadow, with an opaque fallback on browsers without backdrop-filter.
- Opening and closing is pure CSS — fade, drop and a slight scale from the top-left corner, sliding in the same panel on phones — and the panel closes on Escape or a click outside it, like a dropdown.

## 2026-10-17 — Filters rail moves out to the left on wide screens

- Site layout: from 1840px up the filter rail leaves the centered column and sits to its left with a fixed 26px gap — closer to the window edge, but never flush against it.
- The width the rail frees goes to the repository grid, which shows three cards per row there; narrower screens keep the previous layout.

## 2026-10-17 — Orange cursor glow

- The site now carries a soft orange glow that eases toward the pointer: one fixed radial-gradient layer moved with a composited transform in a single requestAnimationFrame loop.
- The glow is skipped on touch devices and for reduced-motion visitors, and its loop stops when the pointer settles or the tab is hidden.

## 2026-10-17 — Filters move into a left side rail

- Site layout: search, group and status filters now sit in a rail on the left of the catalog — sticky on desktop and collapsed or expanded with the Filters button.
- On narrow screens the rail becomes an off-canvas drawer with a backdrop, closed by the X, the backdrop, Escape or the Show-N button; the Changelog tab hides the rail.
- The rail shows live counts per group and per status chip; the desktop show / hide choice is remembered in the browser.

## 2026-10-16 — Input Forwarder for Apollo streaming

- Added BlueScorpioVR/androidInputForwarder to PC VR & Streaming: a root-only app that forwards a Bluetooth controller, keyboard and mouse to an Apollo PC while another app owns the screen.

## 2026-10-16 — Stars and releases load live on the site cards

- Site cards now fetch each repo's star count and latest release in the visitor's browser (shields.io JSON, cached 30 minutes, refreshed in the background), so both stay current with no catalog edits or rebuilds.
- Release badges include prereleases now, so beta-only repos no longer show a red "no releases or repo not found" badge.

## 2026-10-16 — ALVR face-tracking module, and a badge bump

- Added compdoge/VRCFT-ALVR-UE to Face & Eye Tracking: the PC-side VRCFaceTracking receiver that pairs with gxr-root-ft.
- compdoge/gxr-root-ft release badge brought up to v1.3.8.

## 2026-10-14 — NEW badge and New filter brought back into sync

- Fixed: the badge's own CSS overrode the hidden attribute, so every card wore NEW while the filter matched only the window set.
- The 5-day window is now the only rule — no baseline — and the badge, the chip count and the New filter share one predicate.

## 2026-10-14 — NEW badge tuned to real additions

- The badge now starts from the catalog's new_badge_since baseline, so the initial bulk seeding is not flagged as new.
- Only entries added on or after 2026-10-14, within the last 5 days, carry NEW.

## 2026-10-14 — NEW badges for freshly added repos

- Every catalog entry now records the date it was added.
- The site marks entries from the last 5 days with a NEW badge and a New filter, computed in the visitor's browser so they expire on their own.

## 2026-10-14 — KernelSU module source, and a renamed relay repo

- Added compdoge/gxr-ksu-modules to KernelSU Modules: a module source the GXR manager browses under Sources.
- compdoge/gxr-alvr-ft follows its rename to compdoge/gxr-root-ft, with its release badge brought up to date.

## 2026-10-14 — Aurora Store and a changelog tab

- Added whyorean/AuroraStore to Tools & Diagnostics.
- The site gained a Changelog tab, rendered from this file like everything else; CHANGELOG.md mirrors it for GitHub.

## 2026-10-14 — Obtainium and the emulation pack

- Added ImranR98/Obtainium to Tools & Diagnostics.
- Added RJNY/Obtainium-Emulation-Pack to Games & Emulation.

## 2026-10-14 — VectorXR

- Added DienerTech/vectorxr to PC VR & Streaming.

## 2026-10-13 — PimaxMagic4All, PCVR Mods Hub and Moonlight XR

- Added mbucchia/PimaxMagic4All, Mr-Nlce/PCVR-Mods-Installer-Hub and Gilleece/moonlight-android-xr to PC VR & Streaming.
- Widened that group's blurb to cover PC-side VR tooling.

## 2026-10-13 — ALVR USB badge and pyrowave note

- Terminal-ennui/Galaxy_XR_ALVR_USB gained its v0.2.0-beta release badge and a sharper line.
- Terminal-ennui/pyrowave is now marked as the codec fork behind the ALVR 4:4:4 builds.

## 2026-10-13 — Game Link and QuestLHSync entries enriched

- 4uva4ek/galaxy-xr-game-link line corrected after reading its README.
- stearnsbq/questlhsync-galaxy-xr gained its v0.4.1 release badge and a PC-side requirement note.

## 2026-10-13 — diabl0w/KernelSU moved to Foundations

- Moved diabl0w/KernelSU out of Root & Kernel: it is the source base both root stacks build on, not an XR deliverable.

## 2026-10-13 — 20 more repos and a new Apps & Samples group

- Added 20 community repos found by a GitHub sweep: Lighthouse sync modules, ALVR streaming variants, face-tracking relays, lens QR tools and more.
- New Apps & Samples group for players, samples and small apps.

## 2026-10-13 — Catalog opens with 25 repos

- Added the first 25 repos across 8 groups: root and kernel tooling, KernelSU modules, PC VR drivers, app patches, emulation and diagnostics.
- README, Pages site and agent docs published, all generated from catalog.json.
