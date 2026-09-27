---
tags: [lifecycle, status, gates, spec, compile]
---

# Spec Lifecycle

## Current State

A spec is a unit of planned work with a single lifecycle receipt — the `Status:`
field in its header — that moves through a fixed set of states. There is **no
separate stage field**: the `Status:` receipt is the only lifecycle marker, and it
is the single place a reader looks to know where a spec is.

### The status flow

The canonical statuses are `DRAFTED → COMPILED → BUILDING → BUILT → REVIEWED →
COMPLETED`, with the Vetting and Sign-off gates attached to the flow. A spec travels
through them, and its `Status:` reflects the stage it is in. The status boundaries
are **save points**: at each one you can stop,
switch session or model, and resume with no information loss — the draft (before
"approve draft"), the permanent spec + task files (before "compile"), and the
built diff (before "say ok").

### The `Status:` receipt set

The canonical `Status:` values are: `DRAFTED`, `COMPILED`, `BUILDING`, `BUILT`,
`REVIEWED`, `COMPLETED`, `PLAN_REVISION_REQUIRED`, `REVIEW_REVISION_REQUIRED`,
`ESCALATED`, `ABORTED`. The engine (`promote_spec.py`) knows this set; a spec is
never in two states at once.

- **`DRAFTED`** — still being authored (the drafting loop). Nothing is
  published; the draft self-revises until plan-readiness is green.
- **`COMPILED`** — the "approve draft" gate cleared at compile. The task list has
  been compiled into one task file per task and the spec carries `Status: COMPILED`.
  This is the **only** state a run may start from — `COMPILED` is unreachable without
  passing the gate.
- **`BUILDING`** / **`BUILT`** — the build in flight / all tasks `MET`.
- **`REVIEWED`** — review is green; awaiting the commit (or a `pre-commit` stop).
- **`COMPLETED`** — the run committed on the spec's branch. **Terminal.**
- **`PLAN_REVISION_REQUIRED`** / **`REVIEW_REVISION_REQUIRED`** — a gate (Vetting /
  Sign-off) blocked; the spec drops back to re-plan or re-build.
- **`ESCALATED`** — a run failure (build red or review red). A visible, resumable
  halt with a consolidated `NNN-ESCALATION`; **not** `ABORTED`.
- **`ABORTED`** — reserved for a human deliberately stopping a spec at a gate.

### Why a single `Status:` field

The old model carried a separate stage field plus a `Status:` value, which
let the two disagree (a spec in one stage but "Status: APPROVED"). Collapsing to one
receipt removes the ambiguity: the state *is* the stage, and the state set is small
enough to reason about and to drift-test. `ESCALATED` vs `ABORTED` is the key
distinction — a failure parks the spec for resume, while an abort is an explicit human
stop (LIFECYCLE-D01, LIFECYCLE-D02).

## Decision Log

### LIFECYCLE-D01 - Single `Status:` receipt replaces the separate stage field
- **Date:** 2026-09-27
- **Why:** A separate stage header and `Status:` value could disagree; one receipt
  (the state set `DRAFTED…ABORTED`) removes the ambiguity and is drift-testable.

### LIFECYCLE-D02 - `ESCALATED` for failures, `ABORTED` for human stops
- **Date:** 2026-09-27
- **Why:** A run failure must be a visible, resumable halt (consolidated
  `NNN-ESCALATION`, batch continues), not a silent abort; `ABORTED` is reserved for a
  human deliberately stopping a spec at a gate.
