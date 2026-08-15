# PHASE 3 - REVIEW (reference checklist)

Load when all build steps are green. **Read-only posture - no more edits; review and promote.**

## 1. Quality audit

1. Review the full diff against the plan: no drift, no dead code, no debug leftovers.
2. Re-check the affected surface: no protected files touched (`.env*`, credentials, lockfiles, `docs/decisions/*`), no unannounced schema/API/auth changes.
3. Re-run the full verification suite once more if the diff changed since last run.

## 2. Security & risk pass (Lane A mandatory, others advisable)

1. Scan for credential leaks, injection surface, unsafe defaults, and privilege changes.
2. Record findings in the review reply (block 2 of the response schema).
3. Any gate that surfaces here (e.g., a discovered auth implication) resolves through the engine like every other gate (phase-protocol SKILL.md, Instructions step 3) - never by judgment, never silently.

## 3. Spec promotion via spec-builder

1. On human acceptance: promote `docs/temp/draft-plan.md` -> `docs/specs/<NNN>-<feature-slug>.md`; update Status header to APPROVED.
2. Autonomous-resolved specs keep `Status: PROVISIONAL - AUTONOMOUS DEFAULT` until a human clears it.
3. Lane A architectural choices (database, auth, API contracts): write an ADR to `docs/decisions/adr-<NNN>-<topic>.md`.

## 4. Handoff & cleanup

1. Summarize outcome + verification evidence in the final response.
2. Call `task-cleaner` when the human accepts the task (purges `docs/temp/` scratchpad; preserves unreviewed `gate-log.md`).
3. If review finds unresolved issues -> route back to Plan/Build; never silently downgrade the lane.