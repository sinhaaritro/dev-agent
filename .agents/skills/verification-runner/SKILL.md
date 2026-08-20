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

You execute the plan's verification commands and enforce the framework's circuit breaker: maximum **3 consecutive failed attempts**, then escalation and human handoff — "blocked" is a valid terminal state, never a silent pass. Mechanics (retry counter, failure logs, escalation report) belong to `scripts/verify.py`; you supply the judgment: what to run, the hypothesis, the remediation options. You are the verification authority during Build — `build.md` delegates circuit-breaker duty to you.

## When to Use

- Every Build-phase step: run the plan's verification commands (template section 5) after each TODO step.
- A verification command fails and a fix attempt is made — the retry must go through the engine's ledger so the 3-attempt limit is real, never recalled from memory.
- The 3rd consecutive failure — the engine trips the breaker, writes `docs/temp/escalation.md`; you halt for human handoff. Never retry past the threshold.
- No section 5 in the plan and no Commands in `AGENTS.md` — detect the framework and suggest canonical commands.
- An escalation report needs finalizing (hypothesis + remediation options) after a trip.

## Instructions

1. **Read the command source, in order.** The plan's section 5 (`- Build Command: ...` / `- Test Command: ...`) is primary. If absent, `AGENTS.md`'s Commands block. If both absent, run `detect` to identify the framework and read its page in `references/frameworks/` for canonical commands, then confirm Socratically before the first run. When a project uses a non-default environment activator (a venv, conda, nvm use, etc.), the project declares a `Run Prefix` line in `AGENTS.md`; prefix the detected canonical commands with it. No prefix declared and no obvious global toolchain -> ask.
2. **Run through the engine, never bare:**
   `python .agents/skills/verification-runner/scripts/verify.py run --command "<cmd>" --task <task-id>`
   Use the task identifier from the status header (e.g. `auth-001`), not a free-form label. 300s default timeout; interactive commands refused. Output is the contract: `PASS (attempt N)` resets the counter; `FAIL (attempt N/3)` increments it; `CIRCUIT BREAKER TRIPPED` at 3 (exit 2) means cease all code modifications, revert uncommitted dirty edits that break build integrity, and halt.
3. **Plan the fix like a doctor, not a gambler.** On each failure: form a hypothesis, apply the next fix attempt, re-run through the engine. The engine's verbatim failure logs accumulate in the ledger, so the escalation report records all three attempts. Hypothesis and options ready at run time? Pass `--hypothesis` and `--options` (guided format `"A (Recommended): ...; B: ..."`) so a trip report is complete immediately.
4. **Finalize the escalation on a trip.** Pending sections: complete with `escalate` mode — it merges stored attempt logs with your hypothesis and options into `docs/temp/escalation.md`, then report the handoff in blocks 3/4. A tripped task is terminal: the engine refuses further runs on it.
5. **Load the framework page on demand.** After `detect` names the stack, read `references/frameworks/<stack>.md` for canonical build/test/lint commands, single-test vs full-suite invocation, and common failure patterns. The workflow above is identical on every stack — the pages only add knowledge. `detect` returns a family (`python`, `node-npm`); the page itself distinguishes the style (e.g. uv-managed vs plain venv) by its own detection rules.

## Output Contract

- Green: report `PASS` with command and attempt number in block 2; update the plan's TODO checkbox to `- [x]` only on this evidence.
- Failed: report `FAIL (attempt N/3)` with the engine's stdout verbatim plus your hypothesis in block 2.
- Breaker trip: report the escalation path (`docs/temp/escalation.md`), the three attempts' verbatim logs, your hypothesis, and guided remediation options; block 4 states the halt — no further modifications without a human.
- Escalation report structure is engine-enforced; never hand-write a substitute.

## Notes

- **The engine is the counter:** a pass resets it; the 3rd consecutive failure trips the breaker. State lives in `docs/temp/verify-state.json` — never hand-edited; `status` reads it, `run` writes it.
- **Never run past the threshold:** after a trip the engine refuses the task; honoring that refusal is the framework's safety guarantee.
- **`--state-dir` is for tests/evals only** — real runs target `docs/temp/`; sandbox runs must never point at the real state file.
- **Interactive commands are refused** (`--interactive`, `--watch`, `--live-reload`) — verification is non-interactive by design.
- **escalation.md is the audit record** of a halted task: verbatim logs, hypothesis, remediation options, handoff line — engine-generated so every report is reviewable and truthful.
- Framework pages extend this skill per-project: add a page when a project needs one; never hardcode a stack into this file.
