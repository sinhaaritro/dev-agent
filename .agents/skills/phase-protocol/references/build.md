# PHASE 2 - BUILD (reference checklist)

Load when the approved spec exists (Step 1 completed; plan.md section 5).
**Edits allowed within lane scope only.**

**Session gate:** this phase runs ONLY in a new session that did NOT produce
the spec. Before building, verify the spec's header carries `Handoff: <date>`
(recorded at Phase 1.5). If the marker is absent, go back to plan.md section 5
and run the handoff - never build in the spec-producing session (spec 008 D1).

## 1. Execute the plan

1. Work strictly from the approved spec at `docs/specs/<NNN>-<slug>.md` - never add scope silently. (The spec replaced the draft at approval; in a single-session run the draft was promoted per plan.md section 5 before this phase.)
2. Mark the spec `Phase: 2-Build` in its header when work starts.
3. One TODO step at a time; update its checkbox in the spec's section 4 in real time:
   - `- [ ]` pending -> `- [/]` in progress (editing underway) -> `- [x]` completed.
   - `- [x]` ONLY after local verification passed for that step.
4. Scope creep detection: if an edit reveals higher-lane criteria (schema, auth, API, dependency), stop and re-run the router - escalation is automatic and announced, never silent. A mid-build blocking gate resolves through the engine exactly as in planning (phase-protocol SKILL.md, Instructions step 3); in a `supervised` non-interactive session it fails closed: `docs/temp/escalation.md`, no further changes.

## 2. Verify via verification-runner

1. Run the spec's verification commands (section 5 of the template) after each step.
2. On failure, call `verification-runner`: max **3 consecutive failed attempts** (000 section 9 circuit breaker), then escalation.md + revert broken dirty edits + handoff.
3. Mark steps `- [x]` only on green verification.

## 3. Exit criteria

- [ ] All section-4 TODO steps `- [x]` with verified results
- [ ] No scope creep - or reclassified lane announced
- [ ] No unresolved blocking gate; fail-closed respected in non-interactive `supervised` sessions
- [ ] Any NEW architectural decision surfaced during build filed as an ADR (spec-builder SKILL.md, instruction 5)

Proceed to `references/review.md`.