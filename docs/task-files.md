---
tags: [task-files, subagent, coder, owns, dag, dispatch, evidence]
---

# Task Files

## Current State

**Picture:** [flow.md](flow.md) — diagram 2, *Build run flow* (rolling dispatch).

A **task file** is the coder's own working file for exactly one task: `NNN-TASK-<NN>-<slug>.md`. It is a **self-contained briefing** (copied, not referenced) so a ~32k-context coder never needs the full spec. The **compile** step generates one task file per task from the spec's section 5 Tasks & Outcomes.

### Shape

Each task file carries: a **Role & rules** block (implement exactly this task, obey the given signatures, never commit / never plan / never expand scope / never touch files not Owned, read every listed skill first); a **Project overview** (1-2 lines; the global task list is *not* copied here); **Owns** (the files this task may write); **Reads / Context** (read-only context); an optional **Skills to use** (one line per skill: `- <name> (.agents/skills/<name>/SKILL.md)`, rendered from the task's `Skills:` or its `Area:`'s skills); an optional **Contract changes** block (the changed interface, `breaking` vs `shim`, and the owned callers); and a **`### Progress`** subtask checklist whose first item is `read every skill under "Skills to use"` when skills are listed. The **evidence block** (written by the runtime's `verify` command on a green verify) is appended to the task file.

### Skills are rendered, not hardcoded

Compile resolves each declared/inherited skill to an existing `.agents/skills/<name>/SKILL.md`; an unresolvable name is a **fatal** compile error, never a dangling name. `## Role & rules` and `building.md` both require the coder to read every listed skill before implementing. The engine does not hard-gate that read: `verify status` prints a `skills-unread` warning and `verify report` marks the task line `[skills-unread]` when the Progress item is unticked, so a skipped read is visible in the audit instead of passing silently (TASK-FILES-D03).

### Contract changes and the hazard checklist

A section-5 task that changes an exported signature/behavior declares `Contract Changes:` and lists every `Callers:`; the engine fails the plan unless each caller is in that task's `Target Files` (or `Compatibility: shim` is declared). This is one instance of the broader authoring hazard checklist (caller closure, shared mutable state, schema/migration atomicity, generated artifacts, cross-file renames, new-dependency lockfile ownership, build-tree collisions, duplicated sources of truth, shared fixtures, name-keyed registries) that planners walk in `implementation-plan-template.md` and critics walk in `vetting.md`. Mechanical checks stay in the engine; the hazard judgment stays with the author and the vetting critic.

### Ownership: one task file = one coder = one writer

The 1:1 ownership is what keeps parallel coders from touching a shared file. A file is owned by exactly one task, and the owning task owns **every** change to that file. Two tasks may be dispatched concurrently **only** if their `Owns` sets are disjoint (a mechanical set-intersection check); if they overlap on even one file they are serialized by a `Depends On` edge. Because the coder owns its task file, it may tick its own `### Progress` subtasks freely (`[ ]` → `[/]` → `[x]`).

### Subtasks vs the task's verify

Subtasks are **optional** steps *inside* the task file — the *how* of a 10-30-minute task, broken into steps the coder works through one at a time. A trivial single-edit task omits the list. Subtasks are the coder's **own checklist**, not a second verification gate: the task's task-level `Verify` (from the spec's section 5) is what decides pass/fail. The **global** task list — which tasks are done — lives only in the spec's section 5 and is written by the orchestrator; it is **not** copied into task files (TASK-FILES-D01).

### Why the spec → task-file split

A long build can be interrupted mid-way (a crash, a context limit, a human stepping away). Because the spec + task files are already on disk at the compile boundary, a fresh session can pick up exactly where the interrupted one left off instead of re-planning from scratch. The task file sized to ~10-30 minutes (≈3-5 file edits + 1 scoped verification) is the unit a single 32k agent can hold.

## Decision Log

### TASK-FILES-D01 - Global task list stays in the spec, not the task files
- **Date:** 2026-09-27
- **Why:** Copying the global "which tasks are done" list into every task file would let parallel coders write a shared record; keeping it only in the spec's section 5 (written by the orchestrator) preserves the 1:1 file-ownership invariant.

### TASK-FILES-D02 - Subtasks are the coder's own checklist, not a gate
- **Date:** 2026-09-27
- **Why:** The task's task-level `Verify` decides pass/fail; subtasks are just the internal step breakdown the coder ticks off because it owns the file. This avoids a second, redundant verification gate and keeps the task sized for a 32k context.

### TASK-FILES-D03 - Skills are resolved at compile and the read is audited, not hard-gated
- **Date:** 2026-10-20
- **Why:** The old hardcoded `## Skills to use` → `spec-builder` named the one skill that must not run during build. Compile now renders the task's declared `Skills:` (else its `Area:`'s skills) with the installed `SKILL.md` path and refuses an unresolvable name, so the briefing is actionable. The mandatory read item is enforced by visibility (`skills-unread` in status/report) rather than a hard gate, because a build gate that blocks on a checkbox would be trivially gamed and would fail closed on a coder that read the skill but forgot to tick; the audit line keeps the omission truthful.
