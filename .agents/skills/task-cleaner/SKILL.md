---
name: task-cleaner
description: Garbage collector - purges docs/temp/ scratchpad on human acceptance, preserves unreviewed gate-log.md. Use when a task is accepted or confirmed complete, phase 3 review sign-off happens, a spec is promoted and the scratchpad should reset, or scratchpad cleanup is requested.
tags:
  - cleanup
  - purge
  - acceptance
  - reset
  - garbage collection
metadata:
  version: 1.0.0
  author: AI Agent
---

# Task Cleaner

## Overview

You reset the ephemeral scratchpad (`docs/temp/`) when a task is accepted or confirmed complete — usually at the end of Phase 3 Review (`review.md` section 4) — preparing it for the next session. Purge mechanics belong to `scripts/clean.py`; you decide WHEN cleanup is lawful (acceptance gate passed) and report WHAT happened. Non-negotiable: `docs/temp/gate-log.md` is append-only and never purged until a human explicitly reviews and clears it — the engine preserves it by default, and only an explicit `--preserve ""` surrender is lawful.

## When to Use

- The human accepts the task or confirms completion — the final step of Review, after spec promotion.
- A task closes and the scratchpad must reset for the next session.
- Cleanup is requested explicitly ("clean up the temp folder", "reset the workspace"), or a dry-run check is wanted first.
- After a human reviewed and cleared the gate-log, a full purge including it is requested.

## Instructions

1. **Confirm the acceptance gate first.** Run cleanup only after human acceptance or confirmed completion. The engine never decides this — you do. Task still open → do not purge.
2. **Run the engine, never a hand-rolled delete:**
   `python .agents/skills/task-cleaner/scripts/clean.py clean`
   Default: everything in `docs/temp/` is purged **except** `gate-log.md` and `.gitignore`. The report is the contract: `purged: N, preserved: M` followed by the preserved names.
3. **Check before you destroy.** In doubt, run `clean --dry-run` (lists would-purge/would-preserve, deletes nothing) or `status` (classifies current contents). A dry run costs nothing and makes the blast radius explicit.
4. **Never touch the gate-log without an explicit human clear.** It survives every default purge. Only after a human explicitly reviews and clears its entries may you purge it, via `clean --preserve ""`. A hand-deleted gate-log is a policy violation with no audit trail; the override leaves a legible record.
5. **Report the cleanup.** State exactly what was purged and what was preserved — the gate-log is always listed when preserved. The engine restores no template stubs; if the next task needs scratchpad files, the Plan phase creates them on demand.

## Output Contract

- Cleanup: the engine's `purged: N, preserved: M` verbatim in block 2, preserved names listed; block 4 states the scratchpad is reset for the next session.
- Dry-run/status: the classification lists (would-purge / would-preserve) verbatim; block 4 states the purge proceeds only on confirmation.
- Gate-log preserved: state it explicitly in every cleanup report — it is the audit file that survives.
- Purge-all: when `--preserve ""` was used, state that the gate-log was cleared by human review and purged via the explicit override.

## Notes

- **The preserve list is the guardrail:** `gate-log.md` (audit trail) and `.gitignore` (what makes the directory ephemeral) survive by default; `--preserve ""` is the only lawful surrender.
- **Scope is the scratchpad and nothing else:** `docs/specs/`, `docs/decisions/`, `docs/reference/` are persistent and never touched; the engine refuses targets at or above the repo root.
- **`--temp-dir` is for tests/evals only** — real purges target `docs/temp/`; sandbox runs must never point at the real scratchpad.
- **Purged on acceptance, by design:** `verify-state.json` (verification-runner's ledger) and per-session workspaces are ephemeral — a closed task's counter and scratch are gone with it.
- The trigger belongs to Review, but the skill is on-demand: any explicit cleanup request also loads it.
