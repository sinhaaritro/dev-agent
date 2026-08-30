# Task DAG Completion Rules (plan section 5)

State markers live on **subtasks** in the plan's section-5 Task DAG
(`implementation-plan-template.md`, spec-builder SKILL.md). Updated in real
time during Phase 2-Build inside the running spec:

| Marker | Meaning | Rule |
| :--- | :--- | :--- |
| `- [ ]` | Pending | Subtask has not started. |
| `- [/]` | In Progress | Active editing underway. |
| `- [x]` | Done | Verify exited 0 AND output matched Expect, with evidence recorded. |
| `ABANDON: <reason>` | Terminal non-completion | Subtask impossible/out of scope; reason non-empty; never becomes `[x]`. |

Completion rules:

1. A subtask is `[x]` only when its Verify command exited 0 AND its output
   matched its Expect marker; evidence (command, exit, matched marker) is
   recorded in `docs/temp/verify-state.json`. Exit 0 alone is never enough; a
   checkbox without evidence counts as unmet.
2. Before marking `[x]`, run the four passes: (1) implement complete, no
   placeholders; (2) expert re-read, replace the cheap version of each part;
   (3) hunt defects (correctness, integration, portability, performance);
   (4) polish — repeat until a full pass finds nothing.
3. `ABANDON: <non-empty reason>` under a subtask is a terminal
   non-completion: the subtask never becomes `[x]`, its task never closes, and
   the spec ends in visible handoff — never silent completion. An impossible
   or out-of-scope subtask is never deleted.
4. A task is done only when every subtask is `[x]` AND its Phase Gate is green
   (Lane B has no Phase Gate: task done = all subtasks `[x]`).
5. A task starts only when every task in its `Depends On` is done.
6. The spec is done only when every task is done AND a fresh re-run of every
   Phase Gate is green (old evidence is not re-execution).
7. A subtask failing verification 3 consecutive times reverts to `[ ]` and the
   circuit breaker fires (phase-protocol `build.md`); the escalation halts the
   task until a human hands it back.
