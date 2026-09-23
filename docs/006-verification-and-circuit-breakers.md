---
tags: [verification, testing, circuit-breaker, escalation]
---

# 006 - Verification & Circuit Breakers

The verification authority during Build: how verification commands are
resolved, how the 3-retry circuit breaker is enforced by the engine, and how
escalation reports produce a human handoff. "Blocked" is a valid terminal
state — never a silent pass.

**Skills covered:** `verification-runner` (command resolution, retry ledger,
breaker, escalation reports).

## 1. Command source (resolution order)

1. The subtask's **`Verify`** command (section 5 Task DAG) is primary, with
   its `Expect` marker.
2. If absent, the plan's **section 6** (`- Build Command: ...` / `- Test
   Command: ...`), then `AGENTS.md`'s **Commands block**.
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

- `--task` is the task identifier from the status header (e.g. `auth-001`),
  not a free-form label.
- `--expect <marker>`: PASS = exit 0 **AND** the marker present in the combined
  stdout+stderr; on PASS the engine records evidence
  (`{command, exit, expect, matched, at, output_sha256}`) on the task entry.
  Without `--expect` the engine keeps the legacy exit-0-only behavior (Lane C
  ad-hoc runs, legacy invocations).
- `--lane` makes command approval mandatory for A/B (section 3).
- 300s default timeout; **interactive commands are refused**
  (`--interactive`, `--watch`, `--live-reload`) — verification is
  non-interactive by design.
- Output is the contract:
  - `PASS (attempt N)` → counter **reset** (with `--expect`, marker matched +
    evidence recorded).
  - `FAIL (attempt N/3)` → counter incremented, verbatim failure logged.
  - `CIRCUIT BREAKER TRIPPED` at 3 consecutive failures (exit 2) → cease all
    code modifications, revert uncommitted dirty edits that break build
    integrity, halt.

Exit codes: **0** green (counter reset), **1** failed (retry remaining),
**2** breaker tripped (escalation.md written, halt), **3** command source
unresolved (detect the framework or ask), **4** approval required (refused
before execution, no state change, not an attempt).

Optional at run time: `--hypothesis "<text>"` and `--options "<A
(Recommended): ...; B: ...>"` — if the fix plan is ready, the trip report is
complete immediately.

## 3. Command approval (separate from plan approval)

A `Verify`/Phase-Gate command is shell code written by the AI; approving the
spec does not approve its commands (spec 001 D5 / U6).

- Before the first execution of each distinct command on lanes A/B, approve it
  (idempotent; writes the fingerprint to `specs/temp/approvals.json`):
  `python .agents/skills/verification-runner/scripts/verify.py approve --command "<cmd>" --expect "<marker>"`
- The fingerprint is `sha256(command | expect | cwd | executor)`. Any change to
  the command, `Expect`, or CWD re-arms approval; cached re-runs are free.
- `run --lane <A|B>` on an unapproved command exits **4 before execution** — no
  state change, not a retry attempt. Approve, then re-run.
- Lanes C/D (or no `--lane`) are exempt.
- Approvals are per-task scratch: a new session re-approves (the safe default).

## 4. The retry ledger (engine-owned counter)

State lives in `specs/temp/verify-state.json` — **never hand-tracked, never
hand-edited**. `status` reads it; `run` writes it.

- A pass resets the counter for that task.
- The 3rd **consecutive** failure trips the breaker.
- After a trip the task is **terminal**: the engine refuses further runs on
  it. Honoring that refusal is the framework's safety guarantee — never retry
  past the threshold, never clear the counter by hand.
- The ledger is ephemeral: `task-cleaner` purges `verify-state.json` with the
  scratchpad when the task closes.
- `--state-dir` is for tests/evals only — sandbox runs must never point at
  the real `specs/temp/` state file.

## 5. Fixing like a doctor, not a gambler

On each failure:

1. Form a **hypothesis** (what broke and why).
2. Apply the next fix attempt.
3. Re-run **through the engine** — the verbatim failure logs accumulate in
   the ledger, so the escalation report records all three attempts.

This is what makes the breaker meaningful: the count is real, the logs are
verbatim, and the report is reviewable.

## 6. Escalation on a trip

When the breaker trips:

1. The engine writes `specs/temp/escalation.md` (engine-generated,
   engine-enforced structure — never hand-write a substitute).
2. Finalize with `verify.py escalate` mode: it merges the stored attempt logs
   with the agent's hypothesis and guided remediation options into the report.
3. Report the handoff in response blocks 3/4: the escalation path, the three
   attempts' verbatim logs, the hypothesis, and the options; block 4 states
   the halt — no further modifications without a human.

The escalation report is the **audit record** of a halted task: verbatim
logs, hypothesis, remediation options, handoff line.

## 7. Subtask checkbox coupling

A subtask's checkbox moves to `- [x]` **only** on green verification evidence
(`PASS` with the `Expect` marker matched and evidence recorded in
`verify-state.json`, reported in block 2) — a checkbox without evidence is
unmet. A subtask that fails 3 consecutive times reverts to `[ ]` and the task
halts per the breaker; an impossible subtask is never deleted but gets
`ABANDON: <non-empty reason>` (terminal non-completion, visible handoff). The
checkbox state and the ledger never disagree.

## 8. Guardrails context

Verification never overrides the global guardrails (001, section 6): running
an "approved dependency command" is the one sanctioned exception to the
lockfile rule; everything else — `.env*`, credentials, `specs/*` —
stays protected regardless of what a verification command would touch.
