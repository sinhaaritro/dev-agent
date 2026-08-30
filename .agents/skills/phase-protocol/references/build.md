# PHASE 2 - BUILD (reference checklist)

Load when the approved spec exists (Step 1 complete; plan.md section 5). **Edits allowed within lane scope only.**

**Session gate:** this phase runs ONLY in a new session that did NOT produce the spec. Before building, verify the spec header carries `Handoff: <date>` (recorded at Phase 1.5). Absent -> go back to plan.md section 5 and run the handoff. Never build in the spec-producing session.

## 1. Execute the Task DAG in order

1. Work strictly from the approved spec at `docs/specs/<NNN>-<slug>.md` — never add scope silently. (The spec replaced the draft at approval.)
2. Mark the spec `Phase: 2-Build` in its header when work starts.
3. The execution unit is the **subtask**, not the task. Read build order from `Depends On`: start a task only when every task in its `Depends On` is done (all its subtasks `[x]` and its Phase Gate green). Within a task, work subtask by subtask.
4. Update subtask state in real time: `- [ ]` pending -> `- [/]` in progress -> `- [x]` done. A subtask is `[x]` ONLY when its `Verify` passes with recorded evidence (section 2) — never exit-0 alone, never without evidence.
5. Before marking a subtask `[x]`, run the four passes: (1) implement complete, no placeholders; (2) expert re-read — replace the cheap version of each part; (3) hunt defects (correctness, integration, portability, performance); (4) polish — repeat until a full pass finds nothing.
6. An impossible or out-of-scope subtask is never deleted: add `ABANDON: <non-empty reason>` under it. Its task never closes; the spec ends in visible handoff (escalation.md + block 4), never silent completion.
7. Scope creep: an edit revealing higher-lane criteria (schema, auth, API, dependency) stops work — re-run the router; escalation is automatic and announced, never silent. A mid-build blocking gate resolves through the engine exactly as in planning; in a `supervised` non-interactive session it fails closed: `docs/temp/escalation.md`, no further changes.

## 2. Verify each subtask via verification-runner

1. First-run approval: before the first execution of each distinct `Verify`/Phase-Gate command, present the exact command and `Expect` and approve it — `verify.py approve --command "<cmd>" --expect "<marker>"`. Approving the spec does NOT approve its commands. Cached re-runs are free; any change to the command, `Expect`, or CWD re-arms approval (exit 4 before execution — no state change, not an attempt). Lanes A and B enforce this; Lane C is exempt.
2. Run the subtask's `Verify` through the engine: `verify.py run --command "<cmd>" --expect "<marker>" --task <id> --lane <A|B|C>`. PASS = exit 0 AND the `Expect` marker present in the combined output; on PASS the engine records evidence (`{command, exit, expect, matched, at, output_sha256}`) in `docs/temp/verify-state.json`.
3. Failure -> max **3 consecutive failed attempts** on the subtask (circuit breaker), then escalation.md + revert broken dirty edits + handoff. A subtask is `- [x]` only on a green PASS with evidence.
4. When every subtask in a task is `[x]`, run its `Phase Gate` command the same way (approval + `--expect`); a task is done only once its Phase Gate is green.

## 3. Exit criteria

- [ ] Every section-5 subtask is `- [x]` with recorded evidence, or `ABANDON`ed with a non-empty reason (reported as visible handoff)
- [ ] Every task's Phase Gate is green
- [ ] No scope creep — or reclassified lane announced
- [ ] No unresolved blocking gate; fail-closed respected in non-interactive `supervised` sessions
- [ ] Any NEW architectural decision surfaced during build filed as an ADR (spec-builder instruction 5)
- [ ] If any subtask is `ABANDON`ed or unmet, the response halts for handoff — never reports "done"

Proceed to `references/review.md`.
