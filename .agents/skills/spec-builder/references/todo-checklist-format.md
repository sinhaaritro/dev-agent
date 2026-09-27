# Task-Level State (task file `### Progress` + derived status)

There are **two distinct levels of state**, and they are not the same thing:

1. **Subtasks — the coder's own progress checklist.** Inside a task file, the
   `### Progress` bullets (`- [ ]` → `- [/]` → `- [x]`) are the *how* of a single
   10-30-minute task, broken into steps a ~32k-context coder works through one at a
   time. The coder **owns the task file**, so it may tick them off freely. They are
   **optional** (a trivial single-edit task omits the list) and they are **not a gate**
   — ticking every subtask does not complete the task.
2. **Task — verified, derived state.** Whether a task is done is decided by its
   **task-level `Verify`/`Expect`** (the spec's §5), not by the subtask checkboxes.
   On a green PASS the engine writes an evidence block (command, exit, matched marker,
   `sha256` of every owned file) into the task file, and the task's completion is
   **derived from that evidence**, never asserted.

## 1. Subtask markers (the coder's own checklist)

| Marker | Meaning | Rule |
| :--- | :--- | :--- |
| `- [ ]` | Pending | Step not started. |
| `- [/]` | In Progress | Active editing underway. |
| `- [x]` | Step done | This step's work is complete (its own scoped check, if it has one). |
| `ABANDON: <reason>` | Terminal non-completion | Step impossible/out of scope; reason non-empty; never becomes `[x]`. |

The coder ticks these in real time as it works. A subtask that is impossible or
out-of-scope is **never deleted** — it gets `ABANDON: <non-empty reason>`.

## 2. Task state (derived, not asserted)

`verify.py status --task <id>` reads the task file's evidence block and reports:

| Status | Meaning |
| :--- | :--- |
| `MET` | The task's `Verify` passed **and** every owned file's hash still matches the evidence. |
| `NOT MET` | The task's `Verify` has not passed (no green evidence). |
| `STALE` | Evidence exists but an owned file changed since — re-verify required. |
| `NO-EVIDENCE` | No evidence block recorded yet (never verified, or purged). |

Completion rules:

1. A task is `MET` only on a green `Verify` (exit 0 AND the `Expect` marker present)
   with the evidence block written by the engine; the subtask checkboxes alone never
   make a task done.
2. A task starts only when every task in its `Depends On` is `MET`.
3. A task that exhausts its 3 attempts is `FAILED`; its dependents become `BLOCKED`;
   independent tasks keep running to exhaustion (no "3 consecutive failures" breaker).
4. An `ABANDON`ed subtask means its task never closes; the spec ends in visible
   handoff (escalation) — never silent completion.
5. The spec is done only when every task is `MET` (a fresh re-run at 4-Review, since
   old evidence is not re-execution) or the spec parks as `ESCALATED` with a
   consolidated halt report.
