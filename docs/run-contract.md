---
tags: [run-contract, trigger, mode, unattended, supervised, stop-point, opt-in]
---

# Run Contract

## Current State

**Picture:** [flow.md](flow.md) — diagram 5, *Build loop (orchestrator / coders / verify)*.

A **run** is a full-plan execution: it takes one or more `COMPILED` specs and drives them through Build → review → commit. A run has **three fields**, resolved by the lead agent from an explicit trigger:

- **targets** — which specs (`this`, a list, or `all`), each already `COMPILED`.
- **mode** — `supervised` (ask) | `unattended` (don't ask).
- **stop point** — `commit` (default; commit → `COMPLETED`) | `pre-commit` (run to `REVIEWED`, stop before commit so the human inspects/commits).

### A run never self-starts

The framework never self-starts. A run begins **only** from an explicit trigger — free-form text like `implement / execute / complete <spec>` — that the lead agent resolves into a run contract. This is the **opt-in start (the cost gate)**: in CI, a ticket existing is only an *event*; the wrapper maps an event to a trigger **only when it matches an allowlist** (a label, a `/agent` command, an approval, a schedule). Nothing runs, and nothing costs money, unless a trigger explicitly fires. The allowlist is what bounds spend (RUN-CONTRACT-D01).

### The mode default (Option A)

The mode default comes from the **session type** the auto-router detects: **Interactive → `supervised`**, **Non-Interactive → `unattended`**, **no signal → `unattended`** (fail toward caution). The trigger may override either way ("run it overnight" forces `unattended`; "wait for me at 4.5" forces `supervised`) (RUN-CONTRACT-D02).

### Unattended behavior

An unattended run does not ask for approvals or gate answers; it runs to the stop point. It **pauses** only at a spec-level human point — `signoff: on` (at 4.5) or a `review_revision: halt` review failure — and then waits for a human. A `signoff: on` spec under unattended therefore **pauses at 4.5** until a human signs off; it is **not** refused (RUN-CONTRACT-D03).

### Dispatch is rolling

When several specs are targeted they run **one at a time, in order**, each on its own branch. Within a spec, the orchestrator dispatches every **unblocked** task (all its `Depends On` green) up to the harness's max-parallel-subagent setting, and newly unblocked tasks start immediately — no waiting for unrelated work (rolling, not wave-based).

## Decision Log

### RUN-CONTRACT-D01 - Opt-in start is the cost gate
- **Date:** 2026-09-27
- **Why:** In CI a ticket is only an event; mapping an event to a run only on an allowlist match means nothing runs (and nothing costs money) unless a trigger explicitly fires.

### RUN-CONTRACT-D02 - Mode default from the session type (Option A)
- **Date:** 2026-09-27
- **Why:** Defaulting to the detected session type (Interactive → supervised, Non-Interactive → unattended, no signal → unattended) makes the safe default explicit and fail toward caution, while the trigger can still override either way.

### RUN-CONTRACT-D03 - `signoff: on` pauses at 4.5 under unattended
- **Date:** 2026-09-27
- **Why:** A spec that declared a human is part of the run must not be auto-waived in an unattended run; it runs and pauses at 4.5 until a human signs off, rather than being refused.
