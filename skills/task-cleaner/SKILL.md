---
name: task-cleaner
description: Garbage collector - purges the specs/temp/ draft-stage scratchpad on human acceptance (preserves .gitignore); never touches specs/ group files, docs/, or BACKLOG.md. Use when a task is accepted or confirmed complete, review sign-off happens, a spec is promoted and the scratchpad should reset, or scratchpad cleanup is requested.
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

You reset the ephemeral scratchpad (`specs/temp/`) when a task is accepted or confirmed complete — usually at the end of review (`reviewed.md` section 4) — preparing it for the next session. In the new world the scratchpad holds **only draft-stage scratch** (`draft-plan.md`, `active-task.md`, flow diagrams): per-task verification evidence lives in the **task files** under `specs/`, the gate log lives in the **spec's `Gates:` section**, and approvals are a **per-spec file committed with the group** (`NNN-APPROVALS-<slug>.json`). Purge mechanics belong to the runtime's `clean` command; you decide WHEN cleanup is lawful (acceptance gate passed) and report WHAT happened. Non-negotiable: the purge never touches `specs/` group files, `docs/`, or `BACKLOG.md` — those are durable and live outside `specs/temp/`. The default preserve list is `.gitignore` only (the file that makes the directory ephemeral).

## When to Use

- The human accepts the task or confirms completion — the final step of review, after spec promotion.
- A task closes and the scratchpad must reset for the next session.
- Cleanup is requested explicitly ("clean up the scratchpad", "reset the workspace"), or a dry-run check is wanted first.

## Instructions

1. **Confirm the acceptance gate first.** Run cleanup only after human acceptance or confirmed completion. The engine never decides this — you do. Task still open → do not purge.
2. **Run the engine, never a hand-rolled delete:**
    `python .agents/scripts/devagent/main.py clean clean`
    Default: everything in `specs/temp/` is purged **except** `.gitignore` (the file that makes the directory ephemeral). `gate-log.md` is no longer a scratchpad file — the gate log lives in the spec's `Gates:` section — so it is purged like any other draft scratch. The report is the contract: `purged: N, preserved: M` followed by the preserved names.
3. **Check before you destroy.** In doubt, run `clean --dry-run` (lists would-purge/would-preserve, deletes nothing) or `status` (classifies current contents). A dry run costs nothing and makes the blast radius explicit.
4. **Never touch the durable records.** The gate log lives in the spec's `Gates:` section (under `specs/`, not the scratchpad) and approvals are a per-spec file committed with the group — neither is in `specs/temp/`, so the purge never touches them. The only in-scratchpad preservation is `.gitignore`; an explicit `--preserve ""` purges even that (rarely needed).
5. **Report the cleanup.** State exactly what was purged and what was preserved (the default preserve is `.gitignore`). The engine restores no template stubs; if the next task needs scratchpad files, the planning status (`DRAFTED`) creates them on demand.

## Output Contract

- Cleanup: the engine's `purged: N, preserved: M` verbatim in block 2, preserved names listed; block 4 states the scratchpad is reset for the next session.
- Dry-run/status: the classification lists (would-purge / would-preserve) verbatim; block 4 states the purge proceeds only on confirmation.
- Purge-all: when `--preserve ""` was used, state that even `.gitignore` was purged by the explicit override.

## Notes

- **The preserve list is the guardrail:** `.gitignore` (what makes the directory ephemeral) survives by default; `--preserve ""` is the only surrender. There is no longer an append-only audit file in the scratchpad — the gate log is the spec's `Gates:` section and approvals are a per-spec file committed with the group.
- **Scope is the scratchpad and nothing else:** `specs/` group files, the topic docs under `docs/`, and `BACKLOG.md` are persistent and never touched; the engine refuses targets at or above the repo root.
- **`--temp-dir` is for tests/evals only** — real purges target `specs/temp/`; sandbox runs must never point at the real scratchpad.
- **Purged on acceptance, by design:** draft-stage scratch (`draft-plan.md`, `active-task.md`) is ephemeral — a closed task's draft is gone with it; the durable record is the spec + task files + report.
- The trigger belongs to review, but the skill is on-demand: any explicit cleanup request also loads it.
