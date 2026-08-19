# PHASE 2 - BUILD (reference checklist)

Load when the approved spec exists (Step 1 complete; plan.md section 5). **Edits allowed within lane scope only.**

**Session gate:** this phase runs ONLY in a new session that did NOT produce the spec. Before building, verify the spec header carries `Handoff: <date>` (recorded at Phase 1.5). Absent -> go back to plan.md section 5 and run the handoff. Never build in the spec-producing session (spec 008 D1).

## 1. Execute the plan

1. Work strictly from the approved spec at `docs/specs/<NNN>-<slug>.md` — never add scope silently. (The spec replaced the draft at approval.)
2. Mark the spec `Phase: 2-Build` in its header when work starts.
3. One TODO step at a time; update its section-4 checkbox in real time: `- [ ]` pending -> `- [/]` in progress -> `- [x]` completed. `[x]` ONLY after that step's local verification passed.
4. Scope creep: an edit revealing higher-lane criteria (schema, auth, API, dependency) stops work — re-run the router; escalation is automatic and announced, never silent. A mid-build blocking gate resolves through the engine exactly as in planning; in a `supervised` non-interactive session it fails closed: `docs/temp/escalation.md`, no further changes.

## 2. Verify via verification-runner

1. Run the spec's verification commands (section 5) after each step.
2. Failure -> `verification-runner`: max **3 consecutive failed attempts** (circuit breaker), then escalation.md + revert broken dirty edits + handoff.
3. Mark steps `- [x]` only on green verification.

## 3. Exit criteria

- [ ] All section-4 TODO steps `- [x]` with verified results
- [ ] No scope creep — or reclassified lane announced
- [ ] No unresolved blocking gate; fail-closed respected in non-interactive `supervised` sessions
- [ ] Any NEW architectural decision surfaced during build filed as an ADR (spec-builder instruction 5)

Proceed to `references/review.md`.
