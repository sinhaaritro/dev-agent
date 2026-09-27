---
tags: [verification, testing, circuit-breaker, escalation]
---

# 006 - Verification & Escalation

The verification authority during build: how verification commands are
resolved, how per-task content-hash evidence makes completion **derived rather
than asserted**, how a task is run to exhaustion (3 attempts), and how a
consolidated escalation report produces a human handoff. A failed spec parks
`ESCALATED` (visible and resumable) — never a silent pass, never `ABORTED`.

**Skills covered:** `verification-runner` (command resolution, per-task
evidence, `doctor`/`status`/`report`, consolidated escalation). See the topic
doc `docs/verification.md`.

## 1. Command source (resolution order)

1. The task's **`Verify`** command (the spec's §5 Tasks & Outcomes) is primary,
   with its `Expect` marker.
2. If absent, the plan's **section 7 Verification Commands**, then
   `AGENTS.md`'s **Commands block** (the canonical Build/Test/Lint).
3. If all absent, `verify.py detect` identifies the framework family and the
   agent reads `references/frameworks/<stack>.md` (currently `python.md`,
   `node-npm.md`) for canonical commands, then confirms Socratically before
   the first run (Lane C's only approval gate).

When a project uses a non-default environment activator (venv, conda, nvm
use), the project declares a `Run Prefix` line in `AGENTS.md`; detected
canonical commands are prefixed with it. No prefix declared and no obvious
global toolchain → ask.

## 2. Running through the engine (never bare)

```text
python .agents/skills/verification-runner/scripts/verify.py run \
  --command "<cmd>" --expect "<marker>" --task <task-id> --lane <A|B|C|D>
```

- `--task` is the task identifier (e.g. `002-Task 14`), used to locate the
  task file and to key the per-task retry ledger.
- The engine resolves the **repo root by walking up from the CWD** (then the
  script location), using the nearest `AGENTS.md` as the marker; commands run
  with `cwd = repo root` (VERIFY-D01).
- `--expect <marker>`: PASS = exit 0 **AND** the marker present in the combined
  stdout+stderr; on PASS the engine writes a **content-hash evidence block**
  into the task file — `{command, exit, expect, matched, at, output_sha256}`
  plus the `sha256` of **every owned file** (VERIFY-D03). Without `--expect`
  the engine keeps the legacy exit-0-only behavior (Lane C ad-hoc runs).
- `--lane` makes command approval mandatory for A/B (section 3).
- 300s default timeout; **interactive commands are refused**
  (`--interactive`, `--watch`, `--live-reload`) — verification is
  non-interactive by design.
- Output is the contract:
  - `PASS (attempt N)` → the task's retry counter **resets** (evidence block
    written into the task file).
  - `FAIL (attempt N/3)` → counter incremented, verbatim failure logged.
  - **3 attempts exhausted** (exit 2) → the engine writes the consolidated
    escalation record and the spec parks `ESCALATED`; cease modifications on
    that task, leave the tree for a human (the run never reverts mid-build).

Exit codes: **0** green (evidence written, counter reset), **1** failed (retry
remaining), **2** attempts exhausted (escalation record written, halt that
task), **3** command source unresolved (detect the framework or ask), **4**
approval required (refused before execution, no state change, not an attempt).

Optional at run time: `--hypothesis "<text>"` and `--options "<A
(Recommended): ...; B: ...>"` — if the fix plan is ready, the escalation
report is complete immediately.

## 3. Command approval (separate from plan approval)

A `Verify` command is shell code written by the AI; approving the spec does
not approve its commands.

- Pre-approvals happen at **handoff**: the spec group carries a
  `NNN-APPROVALS-<slug>.json` with the fingerprint of each verify command, so
  a human's pre-approval matches a coder's later run. A coder can also approve
  inline (idempotent):
  `python .agents/skills/verification-runner/scripts/verify.py approve --command "<cmd>" --expect "<marker>"`
- The fingerprint is `sha256(command | expect | cwd)`. The **executor is
  deliberately excluded** (VERIFY-D02) so a human's pre-approval matches a
  coder's run of the same command. Any change to the command, `Expect`, or CWD
  re-arms approval; cached re-runs are free.
- `run --lane <A|B>` on an unapproved command exits **4 before execution** — no
  state change, not a retry attempt. Approve, then re-run.
- Lanes C/D (or no `--lane`) are exempt.
- Approvals travel with the spec group (committed as the group's companion),
  not per-session scratch.

## 4. The per-task retry ledger (engine-owned counter)

The per-task attempt counter is engine state — **never hand-tracked, never
hand-edited**. The durable completion record is the task file's evidence block
(section 2).

- A pass resets the counter for that task.
- The task is **run to exhaustion**: it gets exactly **3 attempts**; the 3rd
  failure parks it (there is no separate "3-consecutive" breaker — the three
  attempts *are* the budget).
- After exhaustion the task is **terminal**: the engine refuses further runs
  on it. Honoring that refusal is the framework's safety guarantee — never
  retry past the threshold, never clear the counter by hand.
- The per-task ledger is ephemeral session state; the durable record (evidence
  block + the escalation record) is committed with the spec group.
- `--state-dir` is for tests/evals only — sandbox runs must never point at the
  real state file.

## 4a. Derived status (`verify.py status`)

`verify.py status --task <id>` reads a task's evidence block and reports
**derived** completion, never asserted:

| Status | Meaning |
| :--- | :--- |
| `MET` | verify passed and every owned file's hash still matches |
| `NOT MET` | verify has not passed (no green evidence) |
| `STALE` | evidence exists but an owned file changed since — re-verify required |
| `NO-EVIDENCE` | no evidence block recorded |

## 5. The doctor (pre-flight, `verify.py doctor`)

`verify.py doctor --spec <spec>` runs nine ordered preconditions (repo root
resolved, engine scripts parseable, state files parseable, spec is
`COMPILED` + `Handoff:`-stamped, a task file exists per §5 task, `Depends On`
forms a valid DAG, every verify command is pre-approved, canonical AGENTS.md
commands resolve, a branch can be created off `main`). Output:
`PRECONDITIONS OK` on success, else a **named list of gaps** + non-zero exit
(VERIFY-D04). These are enforced for **unattended** runs; an interactive run
asks the human at the moment instead of halting.

## 6. Fixing like a doctor, not a gambler

On each failure:

1. Form a **hypothesis** (what broke and why).
2. Apply the next fix attempt.
3. Re-run **through the engine** — the verbatim failure logs accumulate, so
   the escalation report records all three attempts.

This is what makes run-to-exhaustion meaningful: the count is real, the logs
are verbatim, and the report is reviewable.

## 7. Escalation & the report

When a task exhausts its 3 attempts and no unblocked task remains:

1. The engine writes the consolidated `NNN-ESCALATION-<slug>.md`
   (engine-generated, engine-enforced structure — never hand-write a
   substitute): every `FAILED` task with its attempts + last output, every
   `BLOCKED` task, and the dirty edits left in the tree.
2. Finalize with `verify.py escalate --task <id> --hypothesis "<text>"`: it
   merges the stored attempt logs with the agent's hypothesis and guided
   remediation options into the report.
3. The spec is parked **`ESCALATED`** (not `ABORTED`) and that spec's branch
   stops; the batch **continues** to the next spec. Report the handoff in
   response blocks 3/4: the escalation record, the attempts' verbatim logs,
   the hypothesis, and the options; block 4 states the halt — no further
   modifications without a human.

`verify.py report --spec <spec>` writes the per-spec `NNN-REPORT-<slug>.md`:
the per-task derived status + evidence, the `R#` outcome observations (a
missing observation **fails** review), and the review summary. Reports are
**per spec only** — there is no combined batch file (VERIFY-D05).

## 8. Guardrails context

Verification never overrides the global guardrails (001, section 6): running
an "approved dependency command" is the one sanctioned exception to the
lockfile rule; everything else — `.env*`, credentials, `specs/*` —
stays protected regardless of what a verification command would touch.
