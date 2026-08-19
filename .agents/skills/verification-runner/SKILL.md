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
---

# Verification Runner

## Overview

You execute the plan's verification commands and enforce the framework's circuit breaker (000 section 9): maximum **3 consecutive failed attempts**, then escalation and human handoff - "blocked" is a valid terminal state, never a silent pass. The mechanical core (retry counter, failure logs, escalation report) is owned by the engine `scripts/verify.py`; you supply the judgment (what to run, the hypothesis, the remediation options). Per `.agents/rules/system.md` section 2 step 4, you are the verification authority during Build - phase-protocol's `build.md` delegates circuit-breaker duty to you.

## When to Use

- Every Build-phase step needs verification: run the plan's verification commands (section 5 of the implementation-plan-template) after each TODO step, per phase-protocol `build.md` section 2.
- A verification command fails and a fix attempt is made - the retry must go through the engine's ledger so the 3-attempt limit is real, never recalled from memory.
- The 3rd consecutive failure hits - the engine trips the breaker, writes `docs/temp/escalation.md`, and you halt for human handoff. Never retry past the threshold.
- A plan has no section 5 and `AGENTS.md` has no Commands - detect the framework and suggest canonical commands.
- An escalation report needs finalizing (hypothesis + remediation options) after a breaker trip.

## Instructions

1. **Read the command source, in order.** The plan's section 5 (`- Build Command: ...` / `- Test Command: ...` lines) is the primary source per phase-protocol `build.md`. If absent, read `AGENTS.md`'s Commands block. If both absent, run `detect` to identify the framework and read its page in `references/frameworks/` for canonical commands. Only ask Socratically if genuinely ambiguous - a framework page's defaults are usually the answer.
2. **Run through the engine, never bare.** Every verification execution goes through the ledger so the outcome is recorded:
   `python .agents/skills/verification-runner/scripts/verify.py run --command "<cmd>" --task <task-id>`
   Use the task identifier from the status header (e.g. `auth-001`), not a free-form label. The engine executes with a 300s default timeout and refuses interactive commands. Its output is the contract: `PASS (attempt N)` resets the counter; `FAIL (attempt N/3)` increments it; `CIRCUIT BREAKER TRIPPED` at 3 means cease all code modifications, revert uncommitted dirty edits that break build integrity, and halt - exit 2.
3. **Plan the fix like a doctor, not a gambler.** On each failure: form a hypothesis, apply the next fix attempt, re-run through the engine. The engine's verbatim failure logs accumulate in the ledger, so the escalation report records the truth of all three attempts. If you have a hypothesis and remediation options ready at run time, pass `--hypothesis` and `--options` (guided Socratic format `"A (Recommended): ...; B: ..."`) so the trip report is complete immediately.
4. **Finalize the escalation on a trip.** If the trip report has pending sections, complete them with the engine's `escalate` mode - it merges the stored attempt logs with your hypothesis and options into `docs/temp/escalation.md`. Then report the handoff to the human in the response's block 3/4. A tripped task is terminal: the engine refuses further runs on it.
5. **Load the framework page on demand.** After `detect` names the stack, read `references/frameworks/<stack>.md` for canonical build/test/lint commands, single-test vs. full-suite invocation, and common failure patterns. The workflow above is identical on every stack - the pages only add knowledge.

## Output Contract

- Green run: report `PASS` with the command and attempt number in the response's block 2 (ACTIONS TAKEN / DISCOVERY); update the plan's TODO checkbox to `- [x]` only on this evidence.
- Failed run: report `FAIL (attempt N/3)` with the engine's stdout verbatim and your hypothesis in block 2.
- Breaker trip: report the escalation path (`docs/temp/escalation.md`), the three attempts' verbatim logs, your hypothesis, and the guided remediation options; block 4 states the halt - no further modifications without a human.
- Escalation report structure is engine-enforced; never hand-write a substitute.

## Notes

- **The engine is the counter.** A passing attempt resets it; the 3rd consecutive failure trips the breaker. State lives in `docs/temp/verify-state.json` - do not edit it by hand; `status` reads it, `run` writes it.
- **Never run past the threshold** (000 section 9): after a trip the engine refuses the task; honoring that refusal is the framework's safety guarantee.
- **`--state-dir` is for tests and evals only** - real runs target the default `docs/temp/`. Sandbox runs must never point at the real state file.
- **Interactive commands are refused** (`--interactive`, `--watch`, `--live-reload`) - verification must be non-interactive by design.
- **Escalation.md is the audit record** of a halted task (000 section 9): verbatim logs, hypothesis, remediation options, handoff line - engine-generated so every report is reviewable and truthful.
- The framework pages extend this skill per-project (per the 005 spec D5): add a page when a project needs one; never hardcode a stack into this file.