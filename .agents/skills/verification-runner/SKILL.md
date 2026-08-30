---
name: verification-runner
description: Test execution & circuit breaker - runs build/test commands, tracks the 3-retry limit, writes escalation reports. Use when verifying build/test results, a verification step fails and needs retry, the circuit breaker threshold (3 consecutive failures) is reached, an escalation report must be written, or a project framework's canonical commands are needed.
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

You execute the plan's verification commands and enforce the framework's circuit breaker: maximum **3 consecutive failed attempts**, then escalation and human handoff — "blocked" is a valid terminal state, never a silent pass. A pass is evidence-gated: PASS = exit 0 AND the subtask's `Expect` marker present in the output, with evidence recorded in the ledger. Command approval is separate from plan approval: on lanes A/B a first-ever command must be approved before it runs, or the engine refuses with exit 4. Mechanics (retry counter, failure logs, escalation report, evidence, approvals) belong to `scripts/verify.py`; you supply the judgment: what to run, the `Expect` marker, the hypothesis, the remediation options. You are the verification authority during Build — `build.md` delegates circuit-breaker duty to you.

## When to Use

- Every Build-phase subtask: run its `Verify` command (section 5 Task DAG) with its `Expect` marker; the canonical build/test commands (section 6) and `AGENTS.md` are the fallback source.
- A lane A/B command needs its first-run approval (exit 4 without it) — approve it before the first execution.
- A verification command fails and a fix attempt is made — the retry must go through the engine's ledger so the 3-attempt limit is real, never recalled from memory.
- The 3rd consecutive failure — the engine trips the breaker, writes `docs/temp/escalation.md`; you halt for human handoff. Never retry past the threshold.
- No `Verify` on the subtask, no section 6 commands in the plan, and no Commands in `AGENTS.md` — detect the framework and suggest canonical commands.
- An escalation report needs finalizing (hypothesis + remediation options) after a trip.

## Instructions

1. **Read the command source, in order.** The subtask's `Verify` command (section 5 Task DAG) is primary, with its `Expect` marker. If absent, the plan's section 6 (`- Build Command: ...` / `- Test Command: ...`), then `AGENTS.md`'s Commands block. If both absent, run `detect` to identify the framework and read its page in `references/frameworks/` for canonical commands, then confirm Socratically before the first run (Lane C's only approval gate). When a project uses a non-default environment activator (a venv, conda, nvm use, etc.), the project declares a `Run Prefix` line in `AGENTS.md`; prefix the detected canonical commands with it. No prefix declared and no obvious global toolchain -> ask.
2. **Approve the command on its first run (lanes A/B).** Approving the plan does not approve its commands. Before the first execution of each distinct `Verify`/Phase-Gate command, present the exact command and `Expect` and approve it:
   `python .agents/skills/verification-runner/scripts/verify.py approve --command "<cmd>" --expect "<marker>"`
   The fingerprint is `sha256(command | expect | cwd | executor)`, cached in `docs/temp/approvals.json` (per-task lifetime; a new session re-approves). Cached re-runs are free; any change to the command, `Expect`, or CWD re-arms approval. Lanes A and B enforce this; lanes C/D are exempt.
3. **Run through the engine, never bare:**
   `python .agents/skills/verification-runner/scripts/verify.py run --command "<cmd>" --expect "<marker>" --task <task-id> --lane <A|B|C|D>`
   Use the task identifier from the status header (e.g. `auth-001`), not a free-form label. 300s default timeout; interactive commands refused. Output is the contract: with `--expect`, `PASS (attempt N)` requires exit 0 AND the marker in the combined output and records evidence (`{command, exit, expect, matched, at, output_sha256}`) in `docs/temp/verify-state.json`; without `--expect` the engine keeps exit-0-only behavior. `FAIL (attempt N/3)` increments the counter; `CIRCUIT BREAKER TRIPPED` at 3 (exit 2) means cease all code modifications, revert uncommitted dirty edits that break build integrity, and halt. Exit 4 = approval required (refused before execution, no state change, not an attempt) — approve, then re-run.
4. **Plan the fix like a doctor, not a gambler.** On each failure: form a hypothesis, apply the next fix attempt, re-run through the engine. The engine's verbatim failure logs accumulate in the ledger, so the escalation report records all three attempts. Hypothesis and options ready at run time? Pass `--hypothesis` and `--options` (guided format `"A (Recommended): ...; B: ..."`) so a trip report is complete immediately.
5. **Finalize the escalation on a trip.** Pending sections: complete with `escalate` mode — it merges stored attempt logs with your hypothesis and options into `docs/temp/escalation.md`, then report the handoff in blocks 3/4. A tripped task is terminal: the engine refuses further runs on it.
6. **Load the framework page on demand.** After `detect` names the stack, read `references/frameworks/<stack>.md` for canonical build/test/lint commands, single-test vs full-suite invocation, and common failure patterns. The workflow above is identical on every stack — the pages only add knowledge. `detect` returns a family (`python`, `node-npm`); the page itself distinguishes the style (e.g. uv-managed vs plain venv) by its own detection rules.

## Output Contract

- Green: report `PASS` with the command, the matched `Expect` marker, and attempt number in block 2; mark the subtask `- [x]` only on this recorded evidence.
- Approval required (exit 4): do not run — present the exact command and `Expect` for approval (`verify.py approve`), then re-run.
- Failed: report `FAIL (attempt N/3)` with the engine's stdout verbatim plus your hypothesis in block 2.
- Breaker trip: report the escalation path (`docs/temp/escalation.md`), the three attempts' verbatim logs, your hypothesis, and guided remediation options; block 4 states the halt — no further modifications without a human.
- Escalation report structure is engine-enforced; never hand-write a substitute.

## Notes

- **The engine is the counter:** a pass resets it; the 3rd consecutive failure trips the breaker. State lives in `docs/temp/verify-state.json` — never hand-edited; `status` reads it, `run` writes it.
- **Approvals are separate from the counter:** `docs/temp/approvals.json` is the fingerprint store (per-task lifetime, scratch; a new session re-approves). Exit 4 is a pre-execution refusal, not a retry attempt — it never moves the counter.
- **Never run past the threshold:** after a trip the engine refuses the task; honoring that refusal is the framework's safety guarantee.
- **`--state-dir` is for tests/evals only** — real runs target `docs/temp/`; sandbox runs must never point at the real state file.
- **Interactive commands are refused** (`--interactive`, `--watch`, `--live-reload`) — verification is non-interactive by design.
- **escalation.md is the audit record** of a halted task: verbatim logs, hypothesis, remediation options, handoff line — engine-generated so every report is reviewable and truthful.
- Framework pages extend this skill per-project: add a page when a project needs one; never hardcode a stack into this file.
