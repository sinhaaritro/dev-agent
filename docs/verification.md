---
tags: [verification, verify, evidence, fingerprint, doctor, report, derived-status]
---

# Verification

## Current State

Verification runs through a single stdlib script, `.agents/skills/verification-runner/scripts/verify.py`,
and has **four** subcommands: `run`, `approve`, `doctor`, `status`, `report`. The core idea is that
**completion is derived, not asserted**: a task is "done" only when the evidence on disk still
matches reality.

### Run from the repo root

`verify.py` resolves the repo root by walking up from the **current working directory** first
(then the script location), using the nearest `AGENTS.md` as the marker. Commands run with
`cwd = repo root`, so relative paths and the canonical AGENTS.md Build/Test/Lint commands resolve
the same way a human runs them. This makes a self-contained sandbox (its own `AGENTS.md` + its own
copy of `verify.py`) resolve to itself, not to a parent repo (VERIFY-D01).

### Pre-approvals & the fingerprint

A verify command is **pre-approved** at 2-Handoff: the approval stores a **fingerprint** of
`sha256(command | expect | cwd)`. The `executor` is deliberately **not** part of the fingerprint,
so a human's pre-approval matches a coder's later run of the same command. A change to the command,
the `Expect` marker, or the CWD re-arms approval (the engine exits before execution, changing no
state, counting no attempt). Lanes A and B enforce this; Lane C is exempt (VERIFY-D02).

### Per-task evidence (content-hash based)

On a green `run` (exit 0 **and** the `Expect` marker present in the combined output), the engine
writes an **evidence block** into the task file: `{command, exit, expect, matched, at,
output_sha256}` plus the `sha256` of **every owned file**. This is the record that later lets a
task's completion be *derived* rather than trusted (VERIFY-D03).

### Derived status

`verify.py status --task <id>` reads the evidence block and reports:

| Status | Meaning |
| :--- | :--- |
| `MET` | verify passed and every owned file's hash still matches |
| `NOT MET` | verify has not passed (no green evidence) |
| `STALE` | evidence exists but an owned file changed since — re-verify required |
| `NO-EVIDENCE` | no evidence block recorded |

### The doctor (pre-flight)

`verify.py doctor --spec <spec>` runs, in order: (1) repo root resolved; (2) engine scripts
parseable; (3) state files parseable; (4) the spec is `Status: COMPILED` and `Handoff:`-stamped;
(5) a task file exists for every task in §5; (6) `Depends On` forms a valid DAG; (7) every task's
verify command is pre-approved; (8) the canonical AGENTS.md commands resolve; (9) a branch can be
created off `main`. Output: `PRECONDITIONS OK` on success, else a **named list of gaps** + non-zero
exit. These preconditions are enforced for **unattended** runs; an interactive run asks the human
at the moment instead of halting (VERIFY-D04).

### The report

`verify.py report --spec <spec>` writes `NNN-REPORT-<slug>.md`: the per-task status + evidence, the
`R#` outcome observations (one line each — a missing observation **fails** 4-Review), and the 4-Review
summary. Reports are **per spec only**; there is no combined batch file (VERIFY-D05).

## Decision Log

### VERIFY-D01 - Resolve the repo root from the CWD first
- **Date:** 2026-09-27
- **Why:** A self-contained sandbox (or a nested repo) must resolve to itself, not to a parent
  repo; walking up from the CWD before the script location gives that behavior.

### VERIFY-D02 - Fingerprint excludes the executor
- **Date:** 2026-09-27
- **Why:** A human's pre-approval of a command must match a coder's later run of the same command;
  folding the per-session executor into the hash would break that match and halt unattended runs
  on the first command.

### VERIFY-D03 - Per-task evidence is content-hash based
- **Date:** 2026-09-27
- **Why:** A green exit at verify time says nothing about whether the owned files still match;
  hashing every owned file lets `status` later report `STALE` when a file drifts, making completion
  derived rather than asserted.

### VERIFY-D04 - The doctor is the unattended pre-flight
- **Date:** 2026-09-27
- **Why:** An unattended run has no human to answer an approval prompt, so the nine ordered
  preconditions are checked up front (`PRECONDITIONS OK` or a named gap list) rather than discovered
  mid-run.

### VERIFY-D05 - Reports are per spec only
- **Date:** 2026-09-27
- **Why:** Each spec has its own branch, escalation, and commit; a per-spec `NNN-REPORT` keeps a
  bad spec from cascading into a shared batch record, and the batch ends with a chat summary instead.
