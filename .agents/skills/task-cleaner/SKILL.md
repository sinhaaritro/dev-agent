---
name: task-cleaner
description: Garbage collector - purges docs/temp/ scratchpad on human acceptance, preserves unreviewed gate-log.md. Use when a task is accepted or confirmed complete, phase 3 review sign-off happens, a spec is promoted and the scratchpad should reset, or scratchpad cleanup is requested.
tags:
  - cleanup
  - purge
  - acceptance
  - reset
  - garbage collection
---

# Task Cleaner

## Overview

You reset the ephemeral scratchpad (`docs/temp/`) when a task is accepted or confirmed complete — usually at the end of Phase 3 Review (phase-protocol `review.md` section 4.2) — preparing it for the next session. The purge mechanics are owned by the engine `scripts/clean.py`; you decide WHEN cleanup is lawful (the acceptance gate has passed) and report WHAT happened. The framework's one non-negotiable: `docs/temp/gate-log.md` is append-only and never purged until a human explicitly reviews and clears it (000 section 3.4.2, system.md section 3) — the engine preserves it by default, and only an explicit `--preserve ""` surrender is lawful.

## When to Use

- The human accepts the task or confirms completion — the final step of Phase 3 Review, after spec promotion (per phase-protocol `review.md` section 4.2: "Call `task-cleaner` when the human accepts the task").
- A task closes and the scratchpad must reset for the next session.
- Cleanup is requested explicitly ("clean up the temp folder", "reset the workspace"), or a dry-run check is wanted before a real purge.
- After the human has reviewed and cleared the gate-log, a full purge including it is requested.

## Instructions

1. **Confirm the acceptance gate first.** Run cleanup only when the human has accepted the task or confirmed completion. The engine never decides this — you do. If the task is still open, do not purge.
2. **Run the engine, never a hand-rolled delete.** The purge goes through the ledger-equivalent report so what happened is reviewable:
   `python .agents/skills/task-cleaner/scripts/clean.py clean`
   Default behavior: everything inside `docs/temp/` is purged **except** `gate-log.md` and `.gitignore`. The report is the contract: `purged: N, preserved: M` followed by the preserved names.
3. **Check before you destroy.** If in doubt about what the purge would remove, run `clean --dry-run` first (lists would-purge/would-preserve, deletes nothing) or `status` (classifies the current contents). A dry run costs nothing and makes the purge's blast radius explicit.
4. **Never touch the gate-log without an explicit human clear.** `gate-log.md` survives every default purge. Only when a human has explicitly reviewed and cleared its entries may you purge it, and only via the explicit override: `clean --preserve ""`. A hand-deleted gate-log is a policy violation with no audit trail; the override leaves a legible record.
5. **Report the cleanup.** In the response, state exactly what was purged and what was preserved — the gate-log is always listed when preserved. The engine does not restore template stubs (no framework Phase-1 skeleton exists in this repository); if the next task needs scratchpad files, the Plan phase creates them on demand (spec-builder drafts into `docs/temp/draft-plan.md`).

## Output Contract

- Cleanup run: `purged: N, preserved: M` from the engine verbatim in the response's block 2, with the preserved names listed; block 4 states the scratchpad is reset for the next session.
- Dry-run/status: the classification lists (would-purge / would-preserve) verbatim; block 4 states the purge proceeds only on confirmation.
- Gate-log preserved: state it explicitly in every cleanup report — it is the audit file that survives.
- Purge-all: when `--preserve ""` was used, state that the gate-log was cleared by human review and purged via the explicit override.

## Notes

- **The engine's preserve list is the guardrail.** `gate-log.md` (audit trail, 000 section 3.4.2) and `.gitignore` (what makes the directory ephemeral) survive by default. `--preserve ""` is the only lawful surrender.
- **Scope is the scratchpad and nothing else.** `docs/specs/`, `docs/decisions/`, `docs/architecture/` are persistent by design and never touched; the engine refuses targets at or above the repo root.
- **`--temp-dir` is for tests and evals only** — real purges target the default `docs/temp/`. Sandbox runs must never point at the real scratchpad.
- **Purged on acceptance, by design:** `verify-state.json` (verification-runner's per-task ledger, 005 D1) and per-session workspaces are ephemeral — a closed task's counter and scratch are gone with it.
- The trigger belongs to Review, but the skill is on-demand: any explicit cleanup request also loads it.