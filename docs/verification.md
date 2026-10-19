---
tags: [verification, verify, evidence, fingerprint, doctor, report, circuit-breaker]
---

# Verification & Escalation

The verification authority during build: how verification commands are resolved, how per-task content-hash evidence makes completion **derived rather than asserted**, how a task is run to exhaustion (3 attempts), and how a consolidated escalation report produces a human hand-back. A failed spec parks `ESCALATED` (visible and resumable) — never a silent pass, never `ABORTED`.

## Current State

**Picture:** [flow.md](flow.md) — diagram 2, *Build run flow*.

Verification runs through the shared dev-agent runtime — `python .agents/scripts/devagent/main.py verify` — with subcommands `run`, `approve`, `doctor`, `status`, `report`, and `escalate`. The core idea is that **completion is derived, not asserted**: a task is "done" only when the evidence on disk still matches reality.

### Command source (resolution order)

1. The task's **`Verify`** command (the spec's section 5 Tasks & Outcomes) is primary, with its `Expect` marker.
2. If absent, the plan's **section 7 Verification Commands**, then `AGENTS.md`'s **Commands block** (the canonical Build/Test/Lint).
3. If all absent, the runtime's `verify detect` subcommand identifies the framework family and the agent reads `references/frameworks/<stack>.md` (currently `python.md`, `node-npm.md`) for canonical commands, then confirms Socratically before the first run (Lane C's only approval gate).

When a project uses a non-default environment activator (venv, conda, `nvm use`), the project declares a `Run Prefix` line in `AGENTS.md`; detected canonical commands are prefixed with it. No prefix declared and no obvious global toolchain → ask.

### Run from the repo root

The runtime resolves the project root by walking up from the **current working directory** first (then the script location), using the nearest `AGENTS.md` as the marker. Commands run with `cwd = repo root`, so relative paths and the canonical AGENTS.md Build/Test/Lint commands resolve the same way a human runs them. This lets a self-contained sandbox (its own `AGENTS.md`) resolve to itself, not to a parent repo (VERIFY-D01). The runtime *install* it uses is discovered separately, by walking up from the CWD for `.agents/.devagent.json` — which is what lets a globally installed skill operate on the project it is run in.

### Running through the engine (never bare)

```text
python .agents/scripts/devagent/main.py verify run \
  --command "<cmd>" --expect "<marker>" --task <task-id> --lane <A|B|C|D>
```

- `--task` is the task identifier (e.g. `002-Task 14`), used to locate the task file and to key the per-task retry ledger.
- The engine resolves the **repo root by walking up from the CWD** (then the script location), using the nearest `AGENTS.md` as the marker; commands run with `cwd = repo root` (VERIFY-D01).
- `--expect <marker>`: PASS = exit 0 **AND** the marker present in the combined stdout+stderr; on PASS the engine writes a **content-hash evidence block** into the task file — `{command, exit, expect, matched, at, output_sha256}` plus the `sha256` of **every owned file** (VERIFY-D03). Without `--expect` the engine keeps the legacy exit-0-only behavior (Lane C ad-hoc runs).
- `--lane` makes command approval mandatory for A/B.
- 300s default timeout; **interactive commands are refused** (`--interactive`, `--watch`, `--live-reload`) — verification is non-interactive by design.
- Output is the contract:
  - `PASS (attempt N)` → the task's retry counter **resets** (evidence block written into the task file). On PASS the spec's build status advances: a `COMPILED` spec becomes `BUILDING` on the first pass; once **every** task is `MET` it becomes `BUILT`.
  - `FAIL (attempt N/3)` → counter incremented, verbatim failure logged.
  - **3 attempts exhausted** (exit 2) → the engine writes the consolidated escalation record and the spec parks `ESCALATED`; cease modifications on that task, leave the tree for a human (the run never reverts mid-build).

Exit codes: **0** green (evidence written, counter reset), **1** failed (retry remaining), **2** attempts exhausted (escalation record written, halt that task), **3** command source unresolved (detect the framework or ask), **4** approval required (refused before execution, no state change, not an attempt).

Optional at run time: `--hypothesis "<text>"` and `--options "<A (Recommended): ...; B: ...>"` — if the fix plan is ready, the escalation report is complete immediately.

### Command approval (separate from plan approval)

A `Verify` command is shell code written by the AI; approving the spec does not approve its commands.

- Pre-approvals happen at **compile**: the spec group carries a `NNN-APPROVALS-<slug>.json` with the fingerprint of each verify command, so a human's pre-approval matches a coder's later run. A coder can also approve inline (idempotent): `python .agents/scripts/devagent/main.py verify approve --command "<cmd>" --expect "<marker>"`
- The fingerprint is `sha256(command | expect | cwd)`, with `cwd` the repo root recorded repo-relative (`.`) so a committed `NNN-APPROVALS` file is portable across clones. The **executor is deliberately excluded** (VERIFY-D02) so a human's pre-approval matches a coder's run of the same command. Any change to the command or `Expect` re-arms approval; cached re-runs are free.
- `run --lane <A|B>` on an unapproved command exits **4 before execution** — no state change, not a retry attempt. Approve, then re-run.
- Lanes C/D (or no `--lane`) are exempt.
- Approvals travel with the spec group (committed as the group's companion), not per-session scratch.

### Per-task evidence (content-hash based)

On a green `run` (exit 0 **and** the `Expect` marker present in the combined output), the engine writes an **evidence block** into the task file: `{command, exit, expect, matched, at, output_sha256}` plus the `sha256` of **every owned file**. This is the record that later lets a task's completion be *derived* rather than trusted (VERIFY-D03).

### Derived status

`python .agents/scripts/devagent/main.py verify status --task <id>` reads the evidence block and reports:

| Status | Meaning |
| :--- | :--- |
| `MET` | verify passed and every owned file's hash still matches |
| `NOT MET` | verify has not passed (no green evidence) |
| `STALE` | evidence exists but an owned file changed since — re-verify required |
| `NO-EVIDENCE` | no evidence block recorded |

`<id>` is a task id (`007-Task 1`, `007-01`), a bare file name, a relative path, or an absolute path; a bare id that is ambiguous across specs is rejected with the candidate list, and `--spec <ref>` disambiguates it. Without a resolvable task file, `status` falls back to the retry ledger (`attempts`, `green`/`escalated`).

### The per-task retry ledger (engine-owned counter)

The per-task attempt counter is engine state — **never hand-tracked, never hand-edited**. The durable completion record is the task file's evidence block.

- A pass resets the counter for that task.
- The task is **run to exhaustion**: it gets exactly **3 attempts**; the 3rd failure parks it (there is no separate "3-consecutive" breaker — the three attempts *are* the budget).
- After exhaustion the task is **terminal**: the engine refuses further runs on it. Honoring that refusal is the framework's safety guarantee — never retry past the threshold, never clear the counter by hand.
- The per-task ledger is ephemeral session state; the durable record (evidence block + the escalation record) is committed with the spec group.
- `--state-dir` is for tests/evals only — sandbox runs must never point at the real state file.

### The doctor (pre-flight)

`python .agents/scripts/devagent/main.py verify doctor --spec <ref>` runs nine ordered preconditions, in order: (1) repo root resolved; (2) engine scripts parseable; (3) state files parseable; (4) the spec is `Status: COMPILED` or `BUILDING`; (5) a task file exists for every task in section 5; (6) `Depends On` forms a valid DAG; (7) every task's verify command is pre-approved; (8) the canonical AGENTS.md commands resolve; (9) a branch can be created off `main`/`master`. Output: `PRECONDITIONS OK` on success, else a **named list of gaps** + non-zero exit (VERIFY-D04). These preconditions are enforced for **unattended** runs; an interactive run asks the human at the moment instead of halting. `<ref>` is a spec id (`003`), a file name, a relative path, or an absolute path — the same forms `report --spec <ref>` accepts.

### Fixing like a doctor, not a gambler

On each failure:

1. Form a **hypothesis** (what broke and why).
2. Apply the next fix attempt.
3. Re-run **through the engine** — the verbatim failure logs accumulate, so the escalation report records all three attempts.

This is what makes run-to-exhaustion meaningful: the count is real, the logs are verbatim, and the report is reviewable.

### Escalation & the report

When a task exhausts its 3 attempts and no unblocked task remains:

1. The engine writes the consolidated `NNN-ESCALATION-<slug>.md` (engine-generated, engine-enforced structure — never hand-write a substitute): every `FAILED` task with its attempts + last output, every `BLOCKED` task, and the dirty edits left in the tree.
2. Finalize with `python .agents/scripts/devagent/main.py verify escalate --task <id> --hypothesis "<text>"`: it merges the stored attempt logs with the agent's hypothesis and guided remediation options into the report.
3. The spec is parked **`ESCALATED`** (not `ABORTED`) and that spec's branch stops; the batch **continues** to the next spec. Report the hand-back in response blocks 3/4: the escalation record, the attempts' verbatim logs, the hypothesis, and the options; block 4 states the halt — no further modifications without a human.

`python .agents/scripts/devagent/main.py verify report --spec <ref>` writes the per-spec `NNN-REPORT-<slug>.md` (the same spec-reference forms as `doctor`): the per-task derived status + evidence, the `R#` outcome observations (one line each — a missing observation **fails** review), and the review summary. An `R#` is observed only when every task whose `Outcomes:` line names it is `MET` (an outcome delivered by no task is never observed). Reports are **per spec only**; there is no combined batch file (VERIFY-D05). A green report (every task `MET` **and** every declared `R#` observed) advances the spec `BUILDING`/`BUILT` → `REVIEWED` and exits **0**; a task that is not `MET` or an unobserved `R#` leaves the status unchanged and exits **1** (an unresolvable `<ref>` exits **2**); a Sign-off block parks it `REVIEW_REVISION_REQUIRED`.

### Guardrails context

Verification never overrides the global guardrails (see `overview.md`): running an "approved dependency command" is the one sanctioned exception to the lockfile rule; everything else — `.env*`, credentials, `specs/*` — stays protected regardless of what a verification command would touch.

## Decision Log

### VERIFY-D01 - Resolve the repo root from the CWD first
- **Date:** 2026-09-27
- **Why:** A self-contained sandbox (or a nested repo) must resolve to itself, not to a parent repo; walking up from the CWD before the script location gives that behavior.

### VERIFY-D02 - Fingerprint excludes the executor
- **Date:** 2026-09-27
- **Why:** A human's pre-approval of a command must match a coder's later run of the same command; folding the per-session executor into the hash would break that match and halt unattended runs on the first command.

### VERIFY-D03 - Per-task evidence is content-hash based
- **Date:** 2026-09-27
- **Why:** A green exit at verify time says nothing about whether the owned files still match; hashing every owned file lets `status` later report `STALE` when a file drifts, making completion derived rather than asserted.

### VERIFY-D04 - The doctor is the unattended pre-flight
- **Date:** 2026-09-27
- **Why:** An unattended run has no human to answer an approval prompt, so the nine ordered preconditions are checked up front (`PRECONDITIONS OK` or a named gap list) rather than discovered mid-run.

### VERIFY-D05 - Reports are per spec only
- **Date:** 2026-09-27
- **Why:** Each spec has its own branch, escalation, and commit; a per-spec `NNN-REPORT` keeps a bad spec from cascading into a shared batch record, and the batch ends with a chat summary instead.

### VERIFY-D06 - An outcome is observed only when its tasks are MET
- **Date:** 2026-10-19
- **Why:** The documented review gate ("a missing observation **fails** review") needs a derived, not asserted, meaning of "observed". Tying each `R#` to the tasks whose `Outcomes:` line names it, and requiring every such task to be `MET`, makes the report fail closed: an outcome no task delivers — or one whose task regressed to `STALE` — is `MISSING`, and a failed review exits 1 without advancing the spec to `REVIEWED`.

### VERIFY-D07 - Spec and task references resolve from their segments
- **Date:** 2026-10-19
- **Why:** The documented `--spec <NNN>` / `--task <id>` forms only worked with a concrete path, so a caller had to know the file's directory. `resolve_spec`/`resolve_task` now accept a spec/task number, a bare file name, a relative path, or an absolute path, matching the file name or the leading `NNN` against the `specs/` group. An ambiguous bare id is rejected with the candidate list (never guessed), and `status --spec` disambiguates across specs; a genuine miss is a named error, not a stray file.
