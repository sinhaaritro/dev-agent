---
name: spec-builder
description: Spec lifecycle - drafts implementation plans in docs/temp/, enforces templates, promotes approved specs to docs/specs/ at approval, files ADRs for architectural decisions, records Phase 1.5 handoffs
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

You own plan drafting, spec promotion, ADR filing, and handoff recording. The templates in `references/` are the single source of format truth - every draft, every promoted spec, and every ADR must match them, which is why validation and promotion mechanics run through your engine instead of judgment. Per `.agents/rules/system.md` section 2, you are the first on-demand skill in step 4: phase-protocol's `plan.md` routes Lane B and A planning to you and its approval step (plan.md section 5) routes promotion, ADR filing, and the Phase 1.5 handoff record to you; `review.md` routes spec finalization to you.

## When to Use

- Lane B or A planning (phase-protocol `plan.md` section 2): draft the implementation plan into `docs/temp/draft-plan.md` under the enforced template.
- Approval-step promotion (phase-protocol `plan.md` section 5): on plan approval, promote `docs/temp/draft-plan.md` to `docs/specs/` and file ADRs for every architectural decision, then record the Phase 1.5 handoff - before implementation starts (spec-first, two-step lifecycle).
- Review finalization (phase-protocol `review.md` section 3): confirm the build matches the promoted spec and sync its checkboxes.
- Any request to "draft a plan", "write a spec", "promote", "write an ADR", or check the format of an implementation plan - even if the user does not name the skill.

## Instructions

1. **Draft per lane into the running plan.** Lane B: sections **1 (Goal), 3 (Affected Files), 4 (TODO)** of `references/implementation-plan-template.md` only. Lane A: the full template - all six sections including 2 (Architectural Decisions & Trade-offs), 5 (Verification Commands), 6 (Rollback Strategy). Write to `docs/temp/draft-plan.md` and reuse that one running file for the task - never create multiple plan files per task. Drafts live in `docs/temp/` (gitignored) and are never committed.
2. **Validate before presenting.** Run the engine's check mode so a plan is never shown or promoted half-formed:
   `python .agents/skills/spec-builder/scripts/promote_spec.py check docs/temp/draft-plan.md --lane <B|A>`
   Exit 0 = the lane's required sections are present; exit 1 prints the missing section numbers - add them before continuing. The check is mechanical because template drift is the failure mode that silently breaks the promotion pipeline.
3. **Maintain the TODO checklist in real time.** Follow `references/todo-checklist-format.md` exactly: `- [ ]` pending -> `- [/]` in progress -> `- [x]` completed. Mark `[x]` only after that step's local verification passed - never mark `[x]` with blank verification, and revert to `[ ]` when a step fails 3 consecutive times (the circuit breaker fires per phase-protocol `build.md`).
4. **Promote through the approval gate.** Promotion happens at the end of planning, on plan approval (spec-first lifecycle, Step 1) - never during review, and never before implementation starts. Promotion requires human acceptance, or a compliant autonomous resolution per phase-protocol (which leaves `docs/temp/gate-log.md` audit entries and marks the spec provisional). Run the engine with the status that matches the gate that actually passed:
   `python .agents/skills/spec-builder/scripts/promote_spec.py promote docs/temp/draft-plan.md --lane <B|A> --status <APPROVED|PROVISIONAL>`
   The engine validates the draft, computes the next sequential number by scanning `docs/specs/` (never guess it), derives the slug from the draft's title, and refuses to overwrite an existing target. `APPROVED` for human acceptance; `PROVISIONAL` renders `PROVISIONAL - AUTONOMOUS DEFAULT`, which stays until a human explicitly clears the tag (000 section 3.4.3). The engine is mechanics only - the gate itself is asserted by the status you pass, so never promote without the gate. Both Lane A and Lane B promote (B's abbreviated spec, sections 1/3/4).
5. **ADRs are triggered by the decision, not the lane.** Any architectural decision at any lane (schema, public API, auth/security, new dependency) gets a permanent ADR in `docs/decisions/`. Lane A always files one per section-2 decision; Lane B files only when a decision surfaces (its abbreviated plan has no section 2). At the approval step, draft each ADR against `references/adr-template.md` into `docs/temp/` and file it through the engine:
   `python .agents/skills/spec-builder/scripts/promote_spec.py adr docs/temp/adr-draft-<topic>.md --source <promoted-spec>`
   The engine validates the template sections, derives the next `NNN` by scanning `docs/decisions/`, and refuses to overwrite an existing ADR. ADRs are written only alongside `APPROVED` (human gate); autonomous resolutions file none until a human clears the tag. Never edit an existing ADR - protected files (system.md section 3).
6. **Record the handoff - then stop.** After promotion and ADR filing (Phase 1.5), run the engine's handoff mode so the spec-producing session proves it stopped and the next session can confirm:
   `python .agents/skills/spec-builder/scripts/promote_spec.py handoff docs/specs/<NNN>-<slug>.md --lane <B|A> [--handoff-dir <sandbox>] [--dry-run]`
   The engine validates the spec exists with `Status: APPROVED` (Lane A also requires at least one ADR whose `Source:` points at the spec; Lane B allows zero), writes `docs/temp/handoff.md` (ephemeral; task-cleaner purges it at review), and stamps `Handoff: <YYYY-MM-DD>` on the spec's status header (durable). Idempotent on re-run; `--dry-run` prints without writing. Lanes C and D have no approval step, so no handoff applies there (spec 008 D3). A session that recorded a handoff MUST NOT open `references/build.md` in the same session.

## Output Contract

- During Plan: the validated draft at `docs/temp/draft-plan.md` (abbreviated for B, full for A), with real-time TODO markers.
- At approval (Step 1): the promoted spec path and status, e.g. `promoted: docs/specs/004-<slug>.md` with `Status: APPROVED` (or `PROVISIONAL - AUTONOMOUS DEFAULT`), plus `adr: docs/decisions/adr-<NNN>-<slug>.md` for every architectural decision (Lane A always; Lane B when a decision surfaced).
- At Phase 1.5 (handoff): `handoff: docs/temp/handoff.md` written and `Handoff: <YYYY-MM-DD>` stamped on the spec header; the session then stops.
- During Review (Step 2): the finalized spec - `Phase: 3-Review`, section-4 checkboxes synced to `- [x]` with green verification evidence; no new promotion.

## Notes

- **Never promote without the gate.** No human acceptance, no compliant autonomous resolution (phase-protocol) - no promotion. The status argument is your assertion of which gate passed; the gate-log is the audit record.
- **Numbering is engine-derived.** The next `NNN` for specs comes from scanning `docs/specs/` and for ADRs from scanning `docs/decisions/` - a hand-written number can silently overwrite a committed record.
- **`--specs-dir` / `--decisions-dir` are for tests only.** Verification and evals run against a sandbox; real promotions always target `docs/specs/` and real ADRs always target `docs/decisions/`.
- **ADRs are protected files.** Filed ADRs in `docs/decisions/` are never edited or deleted without explicit human confirmation (system.md section 3).
- **Never touch protected files while drafting**: `.env*`, credentials, lockfiles, or existing `docs/decisions/*` (system.md section 3).
- **Drafts are ephemeral.** `docs/temp/draft-plan.md` is gitignored; `task-cleaner` purges it after approval - the promoted spec and its ADRs are the durable record.
- **The handoff record closes the loop.** `docs/temp/handoff.md` is ephemeral; the `Handoff:` header stamp on the spec is the durable proof the split happened, and `build.md` refuses to build without it (spec 008).