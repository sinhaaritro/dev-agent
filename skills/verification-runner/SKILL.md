---
name: verification-runner
description: Test execution, per-task verify + doctor/status/report - runs build/test commands from the repo root, tracks the 3-attempt per-task limit, derives task completion from the hash evidence block, writes escalation reports. Use when verifying build/test results, a task's verify fails and needs a retry, the 3-attempt limit is reached, a doctor pre-flight is needed, a task's MET/STALE status must be derived, a run report must be regenerated, or a project framework's canonical commands are needed.
tags:
  - test
  - verify
  - build
  - retry
  - circuit breaker
  - escalation
metadata:
  version: 1.0.0
  author: AI Agent
---

# Verification Runner

## Overview

You execute the plan's verification commands and enforce the per-task attempt limit: maximum **3 total attempts** (first try + 2 retries) per task, after which the task is `FAILED` and its dependents become `BLOCKED` — independent tasks keep running to exhaustion. A pass is evidence-gated: PASS = exit 0 AND the task's `Expect` marker present in the output, with a **hash evidence block** (command, pass timestamp, `sha256` of every owned file) written into the task file. Commands run from the repo root; the approval fingerprint is `sha256(command | expect | cwd)`, with `cwd` the repo root recorded repo-relative (`.`) so pre-approvals are portable (no executor, so a human's pre-approval matches the coder's run). Mechanics (retry counter, failure logs, escalation report, evidence block, approvals, `doctor`/`status`/`report`) belong to the runtime's `verify` command; you supply the judgment: what to run, the `Expect` marker, the hypothesis, the remediation options. You are the verification authority during build — `building.md` delegates verification duty to you.

## When to Use

- Every build task: run its `Verify` command (spec section 5 / task file) with its `Expect` marker; the canonical build/test commands (spec section 7) and `AGENTS.md` are the fallback source.
- A pre-flight is needed before an unattended run — `python .agents/scripts/devagent/main.py verify doctor --spec <ref>` runs the 11 ordered preconditions (including "every declared area has a command", "the generated `docs/_topics.md` is fresh", and "no durable file references a framework spec/decision ID") and prints `PRECONDITIONS OK` or a named list of gaps. `<ref>` is a spec id (`003`), a file name, a relative path, or an absolute path.
- A task's completion must be derived, not asserted — `python .agents/scripts/devagent/main.py verify status --task <id>` reads the evidence block and reports `MET` / `NOT MET` / `STALE` / `NO-EVIDENCE`. When the task lists skills and its `read every skill` item is unticked, the engine also prints a `skills-unread` warning (visible, not a hard gate). `<id>` is a task id (`007-Task 1`, `007-01`), a file name, a relative path, or an absolute path; `--spec <ref>` disambiguates a bare id shared across specs.
- A run report is **mandatory at review**, not optional — `python .agents/scripts/devagent/main.py verify report --spec <ref>` writes `NNN-REPORT-<slug>.md`, including one observation line per declared `R#` outcome; a missing observation, a non-`MET` task, or a dangling framework reference in docs/source (run `spec specs-lint`) **fails** review and exits 1. A green report advances the spec to `REVIEWED`; `spec accept` refuses without one. Tasks whose skills were not read are marked `[skills-unread]` in the report.
- A lane A/B command needs its first-run approval (exit 4 without it) — approvals are pre-recorded at compile into `NNN-APPROVALS-<slug>.json`; ad-hoc commands are approved with `python .agents/scripts/devagent/main.py verify approve` before their first execution.
- A task's verify fails and a fix attempt is made — the retry must go through the engine's ledger so the 3-attempt limit is real, never recalled from memory.
- No `Verify` on the task, no section 7 commands in the plan, and no Commands in `AGENTS.md` — detect the framework and suggest canonical commands.
- An escalation report needs finalizing (hypothesis + remediation options) after a task exhausts its attempts.

## Instructions

1. **Read the command source, in order.** The task's `Verify` command (spec section 5 / task file) is primary, with its `Expect` marker. If absent, the plan's section 7 (`- Build Command: ...` / `- Test Command: ...`) for the task's `Area:`, then that area's commands in `AGENTS.md`. In a mixed-stack repo (several `### <area>` headings) never borrow another area's commands. If both absent, run `detect` to identify the framework and read its page in `references/frameworks/` for canonical commands, then confirm Socratically before the first run (Lane C's only approval gate). When a project uses a non-default environment activator (a venv, conda, nvm use, etc.), the project declares a `Run Prefix` line in `AGENTS.md`; prefix the detected canonical commands with it. No prefix declared and no obvious global toolchain -> ask.
2. **Approve the command on its first run (lanes A/B).** Approving the plan does not approve its commands. The spec's verify commands are pre-approved at compile into `NNN-APPROVALS-<slug>.json` (fingerprint = `command | expect | cwd`, the repo root as `.`; no executor). For any ad-hoc command, present the exact command and `Expect` and approve it:
   `python .agents/scripts/devagent/main.py verify approve --command "<cmd>" --expect "<marker>"`
   The fingerprint is `sha256(command | expect | cwd)`, cached in the scratchpad `specs/temp/approvals.json` (per-task lifetime; a new session re-approves). Cached re-runs are free; any change to the command or `Expect` re-arms approval. Lanes A and B enforce this; lanes C/D are exempt.
3. **Run through the engine, never bare:**
   `python .agents/scripts/devagent/main.py verify run --command "<cmd>" --expect "<marker>" --task <task-id> --lane <A|B|C|D>`
   The command runs with `cwd=<repo root>`. Use the task identifier from the status header (e.g. `007-Task 1`), not a free-form label. 300s default timeout; interactive commands refused. Output is the contract: with `--expect`, `PASS (attempt N)` requires exit 0 AND the marker in the combined output and records evidence (`{command, exit, expect, matched, at, output_sha256}` + a `sha256` of every owned file) into the task file's evidence block and `specs/temp/verify-state.json`; without `--expect` the engine keeps exit-0-only behavior. `FAIL (attempt N/3)` increments the counter; at 3 the task is `FAILED` (exit 2) and its dependents become `BLOCKED`. Exit 4 = approval required (refused before execution, no state change, not an attempt) — approve, then re-run.
4. **Derive, don't assert.** After a run, `python .agents/scripts/devagent/main.py verify status --task <id>` re-derives the task's state from the evidence block: `MET` (verify passed and every owned file's hash still matches) / `NOT MET` (no passing evidence) / `STALE` (an owned file changed since the evidence) / `NO-EVIDENCE` (no evidence block). `doctor --spec <ref>` runs the 10 pre-flight preconditions; `report --spec <ref>` regenerates `NNN-REPORT-<slug>.md` (and refreshes the specs/README index + `docs/_topics.md`). Both `--spec` and `--task` take an id, a file name, or a path — never require the caller to know the directory.
5. **Plan the fix like a doctor, not a gambler.** On each failure: form a hypothesis, apply the next fix attempt, re-run through the engine. The engine's verbatim failure logs accumulate in the ledger, so the escalation report records all three attempts. Hypothesis and options ready at run time? Pass `--hypothesis` and `--options` (guided format `"A (Recommended): ...; B: ..."`) so a trip report is complete immediately.
6. **Finalize the escalation on a trip.** Pending sections: complete with `escalate` mode — it merges stored attempt logs with your hypothesis and options into the spec group's `specs/NNN-ESCALATION-<slug>.md` (or `specs/temp/escalation.md` when the task has no spec group), parks the spec `ESCALATED`, then reports the hand-back in blocks 3/4. A `FAILED` task is terminal: the engine refuses further runs on it.
7. **Load the framework page on demand.** After `detect` names the stack, read `references/frameworks/<stack>.md` for canonical build/test/lint commands, single-test vs full-suite invocation, and common failure patterns. The workflow above is identical on every stack — the pages only add knowledge. `detect` returns a family (`python`, `node-npm`); the page itself distinguishes the style (e.g. uv-managed vs plain venv) by its own detection rules.

## Output Contract

- Green: report `PASS` with the command, the matched `Expect` marker, and attempt number in block 2; mark the task's subtask `- [x]` only on this recorded evidence (the evidence block now carries it).
- Approval required (exit 4): do not run — present the exact command and `Expect` for approval (`python .agents/scripts/devagent/main.py verify approve`), then re-run.
- Failed: report `FAIL (attempt N/3)` with the engine's stdout verbatim plus your hypothesis in block 2.
- Task `FAILED` (3 attempts used): report the escalation path (`specs/NNN-ESCALATION-<slug>.md`, or `specs/temp/escalation.md` when the task has no spec group), the three attempts' verbatim logs, your hypothesis, and guided remediation options; block 4 states the halt — no further modifications without a human.
- Escalation report structure is engine-enforced; never hand-write a substitute.

## Notes

- **The engine is the counter:** a pass resets it; the 3rd attempt on a task marks it `FAILED`. State lives in `specs/temp/verify-state.json` — never hand-edited; `status` reads it, `run` writes it. The per-task evidence block lives in the task file itself (the task file *is* the record).
- **Approvals are separate from the counter:** the scratchpad `specs/temp/approvals.json` is the per-session fingerprint store (a new session re-approves); the per-spec `NNN-APPROVALS-<slug>.json` is written at compile and committed with the spec group — the durable pre-approval. Exit 4 is a pre-execution refusal, not a retry attempt — it never moves the counter.
- **Never run past the threshold:** after a task is `FAILED` the engine refuses it; honoring that refusal is the framework's safety guarantee.
- **`--state-dir` is for tests/evals only** — real runs target `specs/temp/`; sandbox runs must never point at the real state file.
- **Interactive commands are refused** (`--interactive`, `--watch`, `--live-reload`) — verification is non-interactive by design.
- **The escalation record is the audit record** of a halted task (`NNN-ESCALATION-<slug>.md`, or `specs/temp/escalation.md` for a task with no spec group): verbatim logs, hypothesis, remediation options, hand-back line — engine-generated so every report is reviewable and truthful.
- **The engine owns the build/review status receipts.** On PASS it advances the spec `COMPILED → BUILDING` (first pass) and `→ BUILT` once every task is `MET`; a green `report` (every task `MET` and every declared `R#` observed) advances `BUILDING`/`BUILT` `→ REVIEWED` (a failed review exits 1 and leaves the status unchanged). `ESCALATED` is stamped on a circuit-breaker trip. `doctor` accepts a `COMPILED` or `BUILDING` spec.
- Framework pages extend this skill per-project: add a page when a project needs one; never hardcode a stack into this file.
