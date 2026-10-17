# BUILDING - BUILD (reference checklist)

Load when the compiled spec + task files exist (Step 1 complete; drafted.md section 5). **Edits allowed within lane scope only.**

**Session gate:** this step runs ONLY in a new session that did NOT produce the spec. Before building, verify the spec header carries `Status: COMPILED` (recorded at compile). Absent -> go back to drafted.md section 5 and run the compile. Never build in the spec-producing session.

## 1. Execute the task list (the DAG) in order

1. Work strictly from the compiled spec at `specs/<NNN>-<SPEC>-<slug>.md` and its task files — never add scope silently. (The spec replaced the draft at compile.)
2. Stamp the spec `Status: BUILDING` in its header when work starts.
3. The execution unit is the **task**, dispatched to a coder subagent that owns exactly one task file. Read build order from `Depends On`: start a task only when every task in its `Depends On` is `MET`. Within a task, the coder works its `### Progress` checklist one subtask at a time.
4. Update subtask state in real time (inside the task file): `- [ ]` pending -> `- [/]` in progress -> `- [x]` done. A subtask is `[x]` ONLY when its `Verify` passes with recorded evidence (section 2) — never exit-0 alone, never without evidence.
5. Before marking a subtask `[x]`, run the four passes: (1) implement complete, no placeholders; (2) expert re-read — replace the cheap version of each part; (3) hunt defects (correctness, integration, portability, performance); (4) polish — repeat until a full pass finds nothing.
6. An impossible or out-of-scope subtask is never deleted: add `ABANDON: <non-empty reason>` under it. Its task never closes; the spec ends in a visible hand-back (escalation.md + block 4), never silent completion.
7. Scope creep: an edit revealing higher-lane criteria (schema, auth, API, dependency) stops work — re-run the router; escalation is automatic and announced, never silent. A mid-build blocking gate resolves through the engine exactly as in planning; in a `supervised` non-interactive session it fails closed: `specs/temp/escalation.md`, no further changes.

## 2. Verify each task via verification-runner

1. Approvals are pre-recorded at compile into `NNN-APPROVALS-<slug>.json` (fingerprint = `command | expect | cwd`). First-run approval is still available for ad-hoc commands: `verify.py approve --command "<cmd>" --expect "<marker>"`. Approving the spec does NOT approve its commands. Cached re-runs are free; any change to the command, `Expect`, or CWD re-arms approval (exit 4 before execution — no state change, not an attempt). Lanes A and B enforce this; Lane C is exempt.
2. Run the task's `Verify` through the engine (from the repo root): `verify.py run --command "<cmd>" --expect "<marker>" --task <id> --lane <A|B|C>`. PASS = exit 0 AND the `Expect` marker present in the combined output; on PASS the engine records evidence (`{command, exit, expect, matched, at, output_sha256}` + a `sha256` of every owned file) into the task file's evidence block and `specs/temp/verify-state.json`.
3. Failure -> max **3 total attempts** on the task (first try + 2 retries), then the task is `FAILED` and its dependents become `BLOCKED`; independent tasks keep running to exhaustion. A task is done only on a green PASS with evidence.
4. A task's completion is **derived, not asserted**: `verify.py status --task <id>` reads the evidence block and reports `MET` (every owned file's hash still matches) / `NOT MET` / `STALE` (an owned file changed) / `NO-EVIDENCE`.

## 3. Branch-per-spec & commit model

- **Branch per spec.** Specs are authored on `main`; a run creates **one branch per spec off `main` (+ worktree)** and does all coding there. It **never edits `main`** — planning artifacts live on `main`, code changes live on the spec's branch.
- **Commit is terminal.** At spec end (final verification green), the run **commits on its branch and stamps `Status: COMPLETED` immediately; there are no post-commit checks.**
- **Failure parks as `ESCALATED`, not `ABORTED`.** When a spec cannot complete (a task exhausts its 3 attempts and no unblocked task remains), it is marked `ESCALATED` (a visible, resumable halt) and the batch **continues to the next spec** — a bad spec cannot cascade. `ABORTED` is reserved for an explicit human cancel, not a run failure.

## 4. Exit criteria

- [ ] Every task's `Verify` is `MET` (evidence recorded, owned-file hashes match), or the task is `FAILED`/`BLOCKED` with a non-empty reason (reported as a visible hand-back)
- [ ] No scope creep — or reclassified lane announced
- [ ] No unresolved blocking gate; fail-closed respected in non-interactive `supervised` sessions
- [ ] Any NEW architectural decision surfaced during build recorded as a topic log entry (spec-builder instruction 5)
- [ ] If any task is `FAILED` or unmet, the response halts for hand-back — never reports "done"

Proceed to `references/reviewed.md`.
