---
tags: [task-files, subagent, coder, owns, dag, dispatch, evidence]
---

# Task Files

## Current State

A **task file** is the coder's own working file for exactly one task: `NNN-TASK-<NN>-<slug>.md`.
It is a **self-contained briefing** (copied, not referenced) so a ~32k-context coder never
needs the full spec. The **compile** step generates one task file per task from the
spec's §5 Tasks & Outcomes.

### Shape

Each task file carries: a **Role & rules** block (implement exactly this task, obey the given
signatures, never commit / never plan / never expand scope / never touch files not Owned); a
**Project overview** (1-2 lines; the global task list is *not* copied here); **Owns** (the
files this task may write); **Reads / Context** (read-only context); and a **`### Progress`**
subtask checklist. The **evidence block** (written by `verify.py` on a green verify) is appended
to the task file.

### Ownership: one task file = one coder = one writer

The 1:1 ownership is what keeps parallel coders from touching a shared file. A file is owned
by exactly one task, and the owning task owns **every** change to that file. Two tasks may be
dispatched concurrently **only** if their `Owns` sets are disjoint (a mechanical
set-intersection check); if they overlap on even one file they are serialized by a `Depends On`
edge. Because the coder owns its task file, it may tick its own `### Progress` subtasks freely
(`[ ]` → `[/]` → `[x]`).

### Subtasks vs the task's verify

Subtasks are **optional** steps *inside* the task file — the *how* of a 10-30-minute task,
broken into steps the coder works through one at a time. A trivial single-edit task omits the
list. Subtasks are the coder's **own checklist**, not a second verification gate: the task's
task-level `Verify` (from the spec's §5) is what decides pass/fail. The **global** task list —
which tasks are done — lives only in the spec's §5 and is written by the orchestrator; it is
**not** copied into task files (TASK-FILES-D01).

### Why the spec → task-file split

A long build can be interrupted mid-way (a crash, a context limit, a human stepping away).
Because the spec + task files are already on disk at the compile boundary, a fresh session can
pick up exactly where the interrupted one left off instead of re-planning from scratch. The
task file sized to ~10-30 minutes (≈3-5 file edits + 1 scoped verification) is the unit a
single 32k agent can hold.

## Decision Log

### TASK-FILES-D01 - Global task list stays in the spec, not the task files
- **Date:** 2026-09-27
- **Why:** Copying the global "which tasks are done" list into every task file would let
  parallel coders write a shared record; keeping it only in the spec's §5 (written by the
  orchestrator) preserves the 1:1 file-ownership invariant.

### TASK-FILES-D02 - Subtasks are the coder's own checklist, not a gate
- **Date:** 2026-09-27
- **Why:** The task's task-level `Verify` decides pass/fail; subtasks are just the internal
  step breakdown the coder ticks off because it owns the file. This avoids a second, redundant
  verification gate and keeps the task sized for a 32k context.
