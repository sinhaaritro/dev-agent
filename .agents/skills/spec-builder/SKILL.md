---
name: spec-builder
description: Spec lifecycle - drafts implementation plans in docs/temp/, enforces templates, promotes approved specs to docs/specs/
version: 1.0.0
author: AI Agent
tags:
  - spec
  - plan draft
  - promote
  - implementation plan
  - template
scope: on-demand
---

# Spec Builder

## Overview

You own plan drafting and spec promotion. The templates in `references/` are the single source of format truth - every draft and every promoted spec must match them, which is why draft validation and promotion mechanics run through your engine instead of judgment. Per `.agents/rules/system.md` section 2, you are the first on-demand skill in step 4: phase-protocol's `plan.md` routes Lane B and A planning to you, and `review.md` routes promotion to you on acceptance.

## When to Use

- Lane B or A planning (phase-protocol `plan.md` section 2): draft the implementation plan into `docs/temp/draft-plan.md` under the enforced template.
- Review-phase promotion (phase-protocol `review.md` section 3): promote an approved `docs/temp/draft-plan.md` to `docs/specs/`.
- Any request to "draft a plan", "write a spec", "promote", or check the format of an implementation plan - even if the user does not name the skill.

## Instructions

1. **Draft per lane into the running plan.** Lane B: sections **1 (Goal), 3 (Affected Files), 4 (TODO)** of `references/implementation-plan-template.md` only. Lane A: the full template - all six sections including 2 (Architectural Decisions & Trade-offs), 5 (Verification Commands), 6 (Rollback Strategy). Write to `docs/temp/draft-plan.md` and reuse that one running file for the task - never create multiple plan files per task. Drafts live in `docs/temp/` (gitignored) and are never committed.
2. **Validate before presenting.** Run the engine's check mode so a plan is never shown or promoted half-formed:
   `uv run python .agents/skills/spec-builder/scripts/promote_spec.py check docs/temp/draft-plan.md --lane <B|A>`
   Exit 0 = the lane's required sections are present; exit 1 prints the missing section numbers - add them before continuing. The check is mechanical because template drift is the failure mode that silently breaks the promotion pipeline.
3. **Maintain the TODO checklist in real time.** Follow `references/todo-checklist-format.md` exactly: `- [ ]` pending -> `- [/]` in progress -> `- [x]` completed. Mark `[x]` only after that step's local verification passed - never mark `[x]` with blank verification, and revert to `[ ]` when a step fails 3 consecutive times (the circuit breaker fires per phase-protocol `build.md`).
4. **Promote only through the acceptance gate.** Promotion requires human acceptance, or a compliant autonomous resolution per phase-protocol (which leaves `docs/temp/gate-log.md` audit entries and marks the spec provisional). Run the engine with the status that matches the gate that actually passed:
   `uv run python .agents/skills/spec-builder/scripts/promote_spec.py promote docs/temp/draft-plan.md --lane <B|A> --status <APPROVED|PROVISIONAL>`
   The engine validates the draft, computes the next sequential number by scanning `docs/specs/` (never guess it), derives the slug from the draft's title, and refuses to overwrite an existing target. `APPROVED` for human acceptance; `PROVISIONAL` renders `PROVISIONAL - AUTONOMOUS DEFAULT`, which stays until a human explicitly clears the tag (000 section 3.4.3). The engine is mechanics only - the gate itself is asserted by the status you pass, so never promote without the gate.
5. **Lane A decisions produce ADRs.** For Lane A architectural choices (database, auth, public API contracts), also draft `docs/decisions/adr-<NNN>-<topic>.md` during Review (phase-protocol `review.md` section 3) - never edit an existing ADR.

## Output Contract

- During Plan: the validated draft at `docs/temp/draft-plan.md` (abbreviated for B, full for A), with real-time TODO markers.
- During Review: the promoted spec path and status, e.g. `promoted: docs/specs/004-<slug>.md` with `Status: APPROVED` (or `PROVISIONAL - AUTONOMOUS DEFAULT`), plus `docs/decisions/adr-...` for Lane A.

## Notes

- **Never promote without the gate.** No human acceptance, no compliant autonomous resolution (phase-protocol) - no promotion. The status argument is your assertion of which gate passed; the gate-log is the audit record.
- **Numbering is engine-derived.** The next `NNN` comes from scanning `docs/specs/` - a hand-written number can silently overwrite a committed spec.
- **`--specs-dir` is for tests only.** Verification and evals run against a sandbox; real promotions always target `docs/specs/`.
- **Never touch protected files while drafting**: `.env*`, credentials, lockfiles, or existing `docs/decisions/*` (system.md section 3).
- **Drafts are ephemeral.** `docs/temp/draft-plan.md` is gitignored; `task-cleaner` purges it on task acceptance - the promoted spec is the durable record.