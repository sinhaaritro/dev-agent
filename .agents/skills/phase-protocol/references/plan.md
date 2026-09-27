# PHASE 1 - PLAN (reference checklist)

Load when a task starts (Lanes B and A; Lane C runs a single pass). **Read-only - no file edits during planning.**

## 1. Understand & analyze

1. Recap intent in 1 sentence (block 1 of the response schema).
2. Inspect affected code/files (read-only); search existing patterns; Lanes A/B consult the topic docs the plan touches (`docs/<name>.md`; AI index: `docs/_topics.md`) — a plan that reverses a topic's Current State must surface it (system.md §3 Topic guardrail).
3. Record findings in `specs/temp/active-task.md`.

## 2. Draft the plan via spec-builder

1. Lane B: abbreviated — sections 1 (Goal & Context), 4 (Affected Files & Contracts), 5 (Task DAG) only.
2. Lane A: all seven sections per `.agents/skills/spec-builder/references/implementation-plan-template.md` — 1 Goal & Context, 2 Architectural Decisions & Trade-offs, 3 Risks & Open Questions (the `> [!IMPORTANT] User Review Required` callout plus a `### Open Questions` list, each question carrying a deadline), 4 Affected Files & Contracts, 5 Task DAG, 6 Verification Commands, 7 Rollback Strategy.
3. Write to `specs/temp/draft-plan.md`; never commit it.

## 3. Gate every architectural decision

1. For each decision point, present guided multiple-choice options with a recommended default (phase-protocol SKILL.md, step 3).
2. **Blocking** (security, schemas, public APIs, Lane A criteria): resolve exclusively through the engine — `python .agents/skills/phase-protocol/scripts/resolve_gate.py --gate blocking --session <Interactive|Non-Interactive> --lane <lane> [--lane-a-surface] --question "<text>" --options "<A (Recommended): ...; B: ...>"`. Exit 1 = await the human; exit 2 = fail-closed (escalation.md written, stop); exit 0 = autonomous resolution applied, gate-log.md appended (non-interactive only, never Lane-A surfaces).
3. **Non-blocking:** state the default and proceed immediately (engine exits 0 without writing files).

## 4. Exit criteria

- [ ] Lane assigned and announced in the `[STATUS:]` header
- [ ] `draft-plan.md` written (abbreviated for B, full for A)
- [ ] U2 authoring lint passed: every Task DAG `Verify`/`Expect` pair can fail — no no-op `Verify` (`true`/`:`/`exit 0`/bare `echo`), no empty `Expect`, no `Expect` that matches unconditionally (a substring of the `Verify` command, or a marker that passes when the command selects zero tests); `promote_spec.py check` reports no structure/oracle violations before the plan is presented
- [ ] Blocking gates resolved or escalated (fail-closed for `supervised` non-interactive)
- [ ] A blocking gate that cannot resolve -> `specs/temp/escalation.md` and stop

## 5. Approval step (draft -> approved spec + topic decisions)

On human approval (or a compliant autonomous resolution), run promotion through spec-builder — Step 1 of the spec-first lifecycle:

1. Promote the draft to a permanent spec:
   `python .agents/skills/spec-builder/scripts/promote_spec.py promote specs/temp/draft-plan.md --lane <B|A> --status <APPROVED|PROVISIONAL>`
   The spec lands in `specs/` (committed) and becomes the working contract; `specs/temp/draft-plan.md` no longer drives work.
2. Record a topic log entry for every architectural decision (trigger is the decision, not the lane): Lane A always (one per section-2 decision); Lane B only when one surfaces. File each via `promote_spec.py topic <name> --why <text> [--title <t>]` (format truth: spec-builder `references/topic-template.md`; a reversal is a revision — `--supersedes <ID>`, never delete+recreate). Entries accompany `APPROVED` only; autonomous resolutions stay `PROVISIONAL` and record none until a human clears the tag. After any topic-doc edit, rebuild the index: `generate_map.py sync-docs`.
3. Call `task-cleaner` to purge the scratchpad (preserves `gate-log.md`).
4. **Vet (optional), then hand off — never start implementation in this session.** When `vetting: on`, the 1.5-Vetting gate runs a fresh critic on the draft: pass (or accept-as-is) proceeds; a block sets `Status: PLAN_REVISION_REQUIRED` and returns to the authoring loop (3-block cap -> escalate). Then load `references/handoff.md` (2-Handoff) and compile via the engine: `python .agents/skills/spec-builder/scripts/promote_spec.py compile specs/<NNN>-<SPEC>-<slug>.md` (writes the task files + `NNN-APPROVALS-<slug>.json`, stamps `Handoff: <date>` + `Status: COMPILED` on the spec header). Then STOP. Implementation is a separate new session reading the compiled spec + task files — coding after approval in the same session is a rule violation.
