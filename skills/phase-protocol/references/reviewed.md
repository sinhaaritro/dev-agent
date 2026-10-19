# REVIEWED - REVIEW (reference checklist)

Load when the build is `BUILT` (all tasks `MET`). **Read-only - no more edits; review and finalize.**

## 1. Quality audit

1. Review the full diff against the plan: no drift, no dead code, no debug leftovers.
2. Re-check the affected surface: no protected files touched (`.env*`, credentials, lockfiles, `specs/*`), no unannounced schema/API/auth changes.
3. Report audit: immediately before reporting, re-measure every completion claim and number — a fresh re-run of every task's `Verify` (old evidence is not re-execution) plus the canonical AGENTS.md Build/Test/Lint commands, confirm no task is unmet or `ABANDON`ed, and that no owner decision is still pending. A "done" report is never composed while any of those is open.

## 2. Security & risk pass (Lane A mandatory, others advisable)

1. Scan for credential leaks, injection surface, unsafe defaults, and privilege changes.
2. Record findings in the review reply (block 2).
3. Any gate that surfaces here (e.g., a discovered auth implication) resolves through the engine like every other gate — never by judgment, never silently.

## 3. Finalize the spec (spec-builder)

The spec was promoted at approval; this step finalizes it, not births it.

1. Confirm the implementation matches the spec: no drift from section 4 (affected files & contracts), no dead code, no debug leftovers.
2. Set the spec header to `Status: REVIEWED`; confirm every task's derived status is `MET` with re-measured evidence (sync any task the build moved). Any `FAILED`/`BLOCKED` task is reported as a visible hand-back in the final response — never checked off, never silently dropped.
3. Re-run the verification suite (every task's `Verify` + the canonical AGENTS.md commands) if the diff changed since the last run; record the evidence.
4. Any NEW architectural decision surfaced during build and not yet recorded gets a topic log entry now via the runtime's `spec topic` command (spec-builder instruction 5). Entries recorded at approval are never edited here — a change to one is a revision (next ID, `--supersedes`), never an in-place rewrite of history.
5. The spec carries `Status: REVIEWED` on a green review; the evidence blocks + checked boxes carry the per-task proof.

## 4. Wrap-up & cleanup

1. Summarize outcome + re-measured verification evidence in the final response (fresh re-run per section 1): each task's `Verify` command, the matched `Expect` marker, and attempt count — not memory of what ran. If any task is `FAILED`/`ABANDON`ed or unmet, block 4 states the halt/hand-back, never a "done".
2. The Sign-off gate (when `signoff: on`) is the human's "say ok" on the reviewed result; pass -> commit on the spec's branch -> `Status: COMPLETED` (commit is terminal; see building.md section 3), block -> `REVIEW_REVISION_REQUIRED` -> re-build. An unresolvable failure parks the spec as `ESCALATED` (not `ABORTED`) and the batch continues to the next spec.
3. Call `task-cleaner` when the human accepts the task (purges `specs/temp/`; gate entries live in the spec's `## 6. Gates`).
4. Unresolved issues -> route back to Plan/Build; never silently downgrade the lane.
