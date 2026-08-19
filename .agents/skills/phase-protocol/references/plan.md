# PHASE 1 - PLAN (reference checklist)

Load when a task starts (Lanes B and A; Lane C runs a single pass). **Read-only posture - no file edits during planning.**

## 1. Understand & analyze

1. Recap intent in 1 sentence (block 1 of the response schema).
2. Inspect the affected code/files (read-only), search for existing patterns and prior ADRs in `docs/decisions/`.
3. Record findings in `docs/temp/active-task.md`.

## 2. Draft the plan via spec-builder

1. Lane B: abbreviated plan - sections 1 (Goal), 3 (Affected Files), 4 (TODO) only.
2. Lane A: full plan using `.agents/skills/spec-builder/references/implementation-plan-template.md` (forward contract; spec-builder is built after phase-protocol).
3. Write to `docs/temp/draft-plan.md`; never commit it.

## 3. Gate every architectural decision

1. For each decision point, present guided multiple-choice options with a recommended default (phase-protocol SKILL.md, Instructions step 3).
2. **Blocking gate** (security, schemas, public APIs, Lane A criteria): resolve exclusively through the engine - `python .agents/skills/phase-protocol/scripts/resolve_gate.py --gate blocking --session <Interactive|Non-Interactive> --lane <lane> [--lane-a-surface] --question "<text>" --options "<A (Recommended): ...; B: ...>"`. Exit 1 = await the human's answer; exit 2 = fail-closed (escalation.md written, stop); exit 0 = autonomous resolution applied and gate-log.md appended (non-interactive only, never Lane-A surfaces).
3. **Non-blocking**: state the default and proceed immediately (engine exits 0 without writing files).

## 4. Exit criteria

- [ ] Lane assigned and announced in the `[STATUS:]` header
- [ ] `draft-plan.md` written (abbreviated for B, full for A)
- [ ] Blocking gates resolved or escalated (fail-closed for `supervised` non-interactive)
- [ ] A blocking gate that cannot resolve -> `docs/temp/escalation.md` and stop

## 5. Approval step (draft -> approved spec + ADRs)

On human approval (or a compliant autonomous resolution), run the promotion
step through spec-builder - this is Step 1 of the spec-first lifecycle:

1. Promote the draft to a permanent spec:
   `python .agents/skills/spec-builder/scripts/promote_spec.py promote docs/temp/draft-plan.md --lane <B|A> --status <APPROVED|PROVISIONAL>`
   The promoted file lands in `docs/specs/` (committed to git). The spec is
   now the working contract; `docs/temp/draft-plan.md` no longer drives work.
2. File an ADR for every architectural decision (spec-builder SKILL.md,
   instruction 5 - the trigger is the decision, not the lane): Lane A always
   (one per section-2 decision); Lane B only when a decision surfaces. Draft
   each ADR against `references/adr-template.md` in `docs/temp/` and file via
   `promote_spec.py adr <draft> --source <promoted-spec>`. ADRs are written
   only alongside `APPROVED` (human gate); autonomous resolutions stay
   `PROVISIONAL` and file no ADR until a human clears the tag.
3. Call `task-cleaner` to purge the scratchpad (preserves `gate-log.md`).
4. **Hand off - never start implementation in this session.** The approved
   spec plus its ADRs is Step 1 of the spec-first lifecycle. Load
   `references/handoff.md` (Phase 1.5) and record the handoff through the
   engine: `python .agents/skills/spec-builder/scripts/promote_spec.py
   handoff docs/specs/<NNN>-<slug>.md --lane <B|A>` (writes `docs/temp/handoff.md`
   and stamps `Handoff: <date>` on the spec header). Then STOP. Implementation
   is a separate new session that reads the promoted spec (spec 008 D1 - the
   in-session proceed option is removed; coding after approval is a rule
   violation).