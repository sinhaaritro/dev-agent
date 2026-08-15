# PHASE 2 - BUILD (reference checklist)

Load when the plan is approved. **Edits allowed within lane scope only.**

## 1. Execute the plan

1. Work strictly from `docs/temp/draft-plan.md` - never add scope silently.
2. One TODO step at a time; update its checkbox in real time:
   - `- [ ]` pending -> `- [/]` in progress (editing underway) -> `- [x]` completed.
   - `- [x]` ONLY after local verification passed for that step.
3. Scope creep detection: if an edit reveals higher-lane criteria (schema, auth, API, dependency), stop and re-run the router - escalation is automatic and announced, never silent. A mid-build blocking gate resolves through the engine exactly as in planning (phase-protocol SKILL.md, Instructions step 3); in a `supervised` non-interactive session it fails closed: `docs/temp/escalation.md`, no further changes.

## 2. Verify via verification-runner

1. Run the plan's verification commands (section 5 of the template) after each step.
2. On failure, call `verification-runner`: max **3 consecutive failed attempts** (000 section 9 circuit breaker), then escalation.md + revert broken dirty edits + handoff.
3. Mark steps `- [x]` only on green verification.

## 3. Exit criteria

- [ ] All TODO steps `- [x]` with verified results
- [ ] No scope creep - or reclassified lane announced
- [ ] No unresolved blocking gate; fail-closed respected in non-interactive `supervised` sessions

Proceed to `references/review.md`.