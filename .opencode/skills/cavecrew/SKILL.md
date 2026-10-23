---
name: cavecrew
description: >
  Decision guide for delegating to caveman-style subagents. Tells the main
  thread WHEN to spawn `cavecrew-investigator` (locate code), `cavecrew-builder`
  (1-2 file edit), or `cavecrew-reviewer` (diff review) instead of doing the
  work inline or using the general/explore agent. Subagent output is caveman-compressed
  so the tool-result injected back into main context is ~60% smaller — main
  context lasts longer across long sessions.
  Trigger: "delegate to subagent", "use cavecrew", "spawn investigator/builder/reviewer",
  "save context", "compressed agent output".
---

Cavecrew = three subagent presets that emit caveman output. Same job as OpenCode's built-in `explore`/`general` subagents and a normal edit pass; the difference is that the returned tool result is compressed, so main context shrinks per delegation.

## Under OpenCode (named subagents)

OpenCode discovers `cavecrew-*` from the nearest `.opencode/agents/`. This workspace
defines them once at the root, and every project that carries a local `.opencode/`
copy carries the same three files, so the skill works from either location.

Ask the main agent to use `cavecrew-investigator`, `cavecrew-builder` or
`cavecrew-reviewer`. Subagents get fresh context: pass the goal, the bound, the
expected receipt and whether writes are authorized. The investigator and reviewer
permissions keep them read-only.

## Call contract (what cavecrew needs before it starts)

Every call must state all five lines. If one is missing, the role returns
`ambiguous. ask: <the missing line>` instead of guessing.

1. **Role** — `investigator`, `builder` or `reviewer`.
2. **Goal** — one answerable question or one stated change.
3. **Bound** — exact files or directories; nothing outside them.
4. **Evidence** — the symptom, log line, failing check or diff the role starts from.
5. **Write authorization** — `read-only`, or the exact files the builder may edit.

When called, each role does this in order:

- **Investigator** — reads `AGENTS.md`, loads the project skill, traces symbols and
  callers, and returns `path:line` evidence plus what it ruled out.
- **Builder** — reads the assigned files and their direct callers, makes only the
  stated change, re-reads the edited lines, runs the agreed focused check, and
  returns the changed range plus the verification outcome.
- **Reviewer** — reads the changed path and every directly affected consumer,
  reports only concrete defects with a fix, and finishes with severity totals.

If the task exceeds the role's contract — more than two files for a builder, writes
for an investigator or reviewer, a missing authorization, or a guessed
binary/device fact — the role stops with its terminal refusal token.

## Per-project use

Every project with a local `.opencode/` carries its own relevant skill subset and
the three agent files. Use those IDs from that checkout; do not assume the
workspace-root definitions are visible when OpenCode starts inside a subproject.

## Under Hermes (delegate_task, not presets)

Hermes has no named agent presets and reads no `.github/agents/` or `.codex/` files. Run the roles as
`delegate_task` children: paste the matching contract from [references/hermes-roles.md](references/hermes-roles.md)
into each child's `context`, with the goal and every path. Children inherit the parent's tools and model and
cannot call `clarify` — keep the `ambiguous. ask:` terminal line. Their summaries are self-reports: the main
thread re-reads the cited lines and reruns the checks.

## When to use cavecrew vs alternatives

| Task | Use |
|---|---|
| "Where is X defined / what calls Y / list uses of Z" | `cavecrew-investigator` |
| Same but you also want suggestions/architecture commentary | Built-in `explore` agent (more prose) |
| Surgical edit, ≤2 files, scope obvious | `cavecrew-builder` |
| New feature / 3+ files / cross-cutting refactor | Main thread or built-in `general` agent |
| Review diff, branch, or file for bugs | `cavecrew-reviewer` |
| Deep code review with rationale + alternatives | Built-in `general` agent or main thread |
| One-line answer you already know | Main thread, no subagent |

Rule of thumb: **if you'd want the subagent's output in 1/3 the tokens, pick cavecrew. If you'd want prose, pick vanilla.**

## Why this exists (the real win)

Subagent tool results get injected into main context verbatim. A built-in `explore` agent that returns 2k tokens of prose costs 2k tokens of main-context budget every time. The same finding from `cavecrew-investigator` returns ~700 tokens. Across 20 delegations in one session that's the difference between context exhaustion and finishing the task.

## Output contracts

What main thread can rely on per agent:

**`cavecrew-investigator`**
```
<Header>:
- path:line — `symbol` — short note
totals: <counts>.
```
Or `No match.` Always file-path-first, line-number-attached, backticked symbols. Safe to grep with `path:\d+`.

**`cavecrew-builder`**
```
<path:line-range> — <change ≤10 words>.
verified: <re-read OK | mismatch @ path:line>.
```
Or one of: `too-big.` / `needs-confirm.` / `ambiguous.` / `regressed.` (terminal first token).

**`cavecrew-reviewer`**
```
path:line: <emoji> <severity>: <problem>. <fix>.
totals: N🔴 N🟡 N🔵 N❓
```
Or `No issues.` Findings sorted file → line ascending.

## Chaining patterns

**Locate → fix → verify** (most common):
1. `cavecrew-investigator` returns site list.
2. Main thread picks 1-2 sites, hands paths to `cavecrew-builder`.
3. `cavecrew-reviewer` audits the diff.

**Parallel scout** (when investigation is broad):
Spawn 2-3 `cavecrew-investigator` calls in one message (different angles: defs vs callers vs tests). Aggregate in main thread.

**Single-shot edit** (when site is already known):
Skip investigator. Hand exact path:line to `cavecrew-builder` directly.

## What NOT to do

- Don't use `cavecrew-builder` when you don't already know the file. Spawn investigator first or main thread will eat tokens passing context.
- Don't chain `cavecrew-investigator → cavecrew-builder` for a 5-file refactor. Builder will return `too-big.` and you'll have wasted a turn.
- Don't ask `cavecrew-reviewer` for "general feedback" — it returns findings only, no architecture opinions. Use the built-in `general` agent for that.
- Don't expect prose. Cavecrew output is structured, sometimes terse to the point of cryptic. If a human will read it directly, paraphrase.

## Auto-clarity (inherited)

Subagents drop caveman → normal English for security warnings, irreversible-action confirmations, and any output where fragment ambiguity could be misread. Resume caveman after.
