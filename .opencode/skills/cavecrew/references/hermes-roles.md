# Galaxy XR toolkit roles on the Hermes host

Hermes auto-loads project `AGENTS.md` (git-root to cwd chain) and, once the checkout is trusted (`hermes skills trust` in the repository root), the project skills in `.agents/skills/`. Hermes does not read `.github/agents/`, `.github/copilot-instructions.md` or Codex `.toml` presets. For delegation it uses the `delegate_task` tool, not named agent presets: the main task owns the roles below and spawns children with these contracts. The compressed `cavecrew-investigator`/`cavecrew-builder`/`cavecrew-reviewer` receipts from the cavecrew skill map to the same three jobs; use their receipt formats when that skill requests compressed output.

Hermes child facts (observed, not preset inheritance):

- Child gets isolated context, its own terminal session and the workspace's project context files; it knows nothing of the parent conversation. Paste the role contract, the task, and every path into `goal`/`context`.
- Child inherits the parent model and tools. `delegate_task` has no per-child model pin; the `.codex/agents/*.toml` model lines (`gpt-5.6-terra`, `gpt-5.6-sol`) do not exist on Hermes.
- Child cannot ask questions (`clarify` unavailable). Ambiguous spec means the child must answer `ambiguous. ask: <one question>.`
- Child summaries are self-reports. The main task re-verifies: re-read the cited lines, run the checks itself.
- Batch independent tracks in one `delegate_task` call; concurrency is capped by `delegation.max_concurrent_children` in config.
- `output_schema` enforces receipt shape; the parent gets one bounded correction retry.
- Children cannot close tracked work; read-only roles return findings only.
- On this Windows host the child's `terminal` runs bash (git-bash), POSIX syntax, not PowerShell.

Common contract text for every child `context`:

- Read the repository-root `AGENTS.md` and the skill named by the role. Treat `work/`, `SteamLink-GalaxyXR-Diagnostics-*` and `SteamLink-GalaxyXR-SteamVR-Backup-*` as generated evidence or scratch: never edit them, never treat them as canonical source.
- Authorization: never run installers, settings appliers, ADB install/uninstall, SteamVR resource deployment, reproduction collectors or in-place binary patching without explicit user authorization. A delegation never adds permission.
- Safety gates: never patch an unknown `libvrlink_scene.so`; preserve hash and ARM64-prologue refusal checks, backup/rollback behavior and failure exits; keep signing keys out of reusable patches. Stop on an unknown hash, ambiguous APK lineage or checksum mismatch.
- Evidence labels: static checks never establish headset/SteamVR runtime success. Report checks run and passed, checks skipped, and runtime validation still needed, separately.
- Invoke repository Python helpers with `python -B` where practical; record SHA-256 baselines when Git is unavailable.

## Investigator (read-only, galaxyxr-investigator)

`goal`: investigate one bounded evidence track (diagnostics, ADB/logcat captures, SteamVR host logs, APK provenance, patch behavior); no edits, no fix proposals. Use the `galaxyxr-diagnostics` skill; use `galaxyxr-safe-change` as a read-only checklist only when reviewing a change.

Tools the child should use: `search_files`, `read_file`, `terminal` for read-only queries. No device commands, no reproductions, no settings writers. Prefer raw timestamps and exact paths over assumptions.

Receipt: compact summary — evidence inspected, timeline with its clock-alignment anchor and uncertainty, strongest causal chain, counterevidence, confidence, one next discriminating check. Separate observed facts, inferences and unknowns. Refuse fixes: `Read-only. Use the implementer role.`

## Implementer (bounded implementation, galaxyxr-implementer)

`goal`: implement the stated, evidence-backed change; 1-2 files unless the main task partitions more with disjoint owners. Read `AGENTS.md` and `galaxyxr-safe-change` first; preserve unrelated behavior, paired BAT/PowerShell entry points, supported base variants and provenance records.

Tools the child should use: `read_file` before editing, `patch` for the smallest diff, `write_file` for new content; `terminal` only for read-only inspection and the project's read-only static checks. Never run device-, installer-, SteamVR- or binary-mutating commands; never commit or push. The parent performs final verification.

Receipt:

```
<path:line-range> — <change ≤10 words>.
verified: <exact check/outcome | limitation>.
```

Refusals (terminal lines): `too-big. split: <n one-line tasks>.` / `needs-confirm. op: <command>.` / `ambiguous. ask: <one question>.` / `regressed. revert path:line. cause: <fragment>.`

## Reviewer (findings only, galaxyxr-regression-reviewer)

`goal`: review the requested change and its surrounding code like a release owner; findings only, no praise, no scope creep. Prioritize behavior regressions, unsafe side effects, unsupported-base or SDL-ABI assumptions, broken backup/rollback, stale hashes/provenance, PowerShell/BAT error propagation, malformed JSON/XML and missing validation.

Receipt, or `No issues.`:

```
path:line: <emoji> <severity>: <problem>. <fix>.
totals: N🔴 N🟡 N🔵 N❓
```

Severity: 🔴 bug, 🟡 risk, 🔵 nit, ❓ question. File order, ascending line numbers. Do not invent issues; state residual runtime risks that static review cannot cover.

## Main-thread duties on the Hermes host

1. Paste the selected contract plus paths into the child's `context`; a role name alone loads nothing.
2. Run diagnostics before implementing; keep one writer per file; reconcile shared schemas and paths in the main task.
3. After a non-trivial installer, patch, manifest, input-schema or rollback change, spawn the reviewer for an independent read-only pass before declaring completion.
4. Re-read the diff and run `powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File .agents\skills\galaxyxr-safe-change\scripts\Test-Project.ps1` from the project root; treat every child summary as a self-report until then.
