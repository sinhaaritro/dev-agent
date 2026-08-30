# PHASE 3 - REVIEW (reference checklist)

Load when all build steps are green. **Read-only - no more edits; review and finalize.**

## 1. Quality audit

1. Review the full diff against the plan: no drift, no dead code, no debug leftovers.
2. Re-check the affected surface: no protected files touched (`.env*`, credentials, lockfiles, `docs/decisions/*`), no unannounced schema/API/auth changes.
3. Report audit: immediately before reporting, re-measure every completion claim and number — a fresh re-run of every Phase Gate (old evidence is not re-execution), confirm no subtask is unmet or `ABANDON`ed, and that no owner decision is still pending. A "done" report is never composed while any of those is open.

## 2. Security & risk pass (Lane A mandatory, others advisable)

1. Scan for credential leaks, injection surface, unsafe defaults, and privilege changes.
2. Record findings in the review reply (block 2).
3. Any gate that surfaces here (e.g., a discovered auth implication) resolves through the engine like every other gate — never by judgment, never silently.

## 3. Finalize the spec (spec-builder)

The spec was promoted at approval; this phase finalizes it, not births it.

1. Confirm the implementation matches the spec: no drift from section 4 (affected files & contracts), no dead code, no debug leftovers.
2. Set the spec header to `Phase: 3-Review`; confirm every section-5 subtask is `- [x]` with re-measured evidence (sync any subtask the build moved). Any `ABANDON`ed subtask is reported as visible handoff in the final response — never checked off, never silently dropped.
3. Re-run the verification suite if the diff changed since the last run; record the evidence.
4. Any NEW architectural decision surfaced during build and not yet filed gets its ADR now via `promote_spec.py adr` (spec-builder instruction 5). ADRs filed at approval are never edited here — protected.
5. The spec keeps `Status: APPROVED` (unchanged on completion; the `Phase:` header and checked boxes carry that).

## 4. Handoff & cleanup

1. Summarize outcome + re-measured verification evidence in the final response (fresh Phase-Gate re-run per section 1): each Phase Gate command, the matched `Expect` marker, and attempt count — not memory of what ran. If any subtask is `ABANDON`ed or unmet, block 4 states the halt/handoff, never a "done".
2. Call `task-cleaner` when the human accepts the task (purges `docs/temp/`; preserves unreviewed `gate-log.md`).
3. Unresolved issues -> route back to Plan/Build; never silently downgrade the lane.
