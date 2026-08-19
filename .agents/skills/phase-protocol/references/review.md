# PHASE 3 - REVIEW (reference checklist)

Load when all build steps are green. **Read-only - no more edits; review and finalize.**

## 1. Quality audit

1. Review the full diff against the plan: no drift, no dead code, no debug leftovers.
2. Re-check the affected surface: no protected files touched (`.env*`, credentials, lockfiles, `docs/decisions/*`), no unannounced schema/API/auth changes.
3. Re-run the full verification suite once more if the diff changed since the last run.

## 2. Security & risk pass (Lane A mandatory, others advisable)

1. Scan for credential leaks, injection surface, unsafe defaults, and privilege changes.
2. Record findings in the review reply (block 2).
3. Any gate that surfaces here (e.g., a discovered auth implication) resolves through the engine like every other gate — never by judgment, never silently.

## 3. Finalize the spec (spec-builder)

The spec was promoted at approval; this phase finalizes it, not births it.

1. Confirm the implementation matches the spec: no drift from section 3 (affected files), no dead code, no debug leftovers.
2. Set the spec header to `Phase: 3-Review`; confirm every section-4 checkbox is `- [x]` with green verification recorded (sync any checkbox the build moved).
3. Re-run the verification suite if the diff changed since the last run; record the evidence.
4. Any NEW architectural decision surfaced during build and not yet filed gets its ADR now via `promote_spec.py adr` (spec-builder instruction 5). ADRs filed at approval are never edited here — protected.
5. The spec keeps `Status: APPROVED` (unchanged on completion; the `Phase:` header and checked boxes carry that).

## 4. Handoff & cleanup

1. Summarize outcome + verification evidence in the final response.
2. Call `task-cleaner` when the human accepts the task (purges `docs/temp/`; preserves unreviewed `gate-log.md`).
3. Unresolved issues -> route back to Plan/Build; never silently downgrade the lane.
