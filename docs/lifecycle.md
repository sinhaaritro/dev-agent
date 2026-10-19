---
tags: [lifecycle, status, gates, autonomy, socratic, protocol, compile]
---

# Spec Lifecycle, Gates & Autonomy

The process-governance layer: how a triaged task moves through the lifecycle statuses, how Socratic gates are resolved, how autonomy policy governs non-interactive sessions, and the response schema every reply carries.

## Current State

**Picture:** [flow.md](flow.md) — diagrams 1 and 3, *Master per-spec state machine* and *Review & acceptance*.

A spec is a unit of planned work with a single lifecycle receipt — the `Status:` field in its header — that moves through a fixed set of states. There is **no separate stage field**: the `Status:` receipt is the only lifecycle marker, and it is the single place a reader looks to know where a spec is.

### The status flow

The canonical statuses are `DRAFTED → APPROVED → COMPILED → BUILDING → BUILT → REVIEWED → COMPLETED`, with the Vetting and Sign-off gates attached to the flow. A spec travels through them, and its `Status:` reflects the stage it is in. The status boundaries are **save points**: at each one you can stop, switch session or model, and resume with no information loss — the draft (before "approve draft"), the permanent spec + task files (before "compile"), and the built diff (before "say ok").

### The `Status:` receipt set

The canonical `Status:` values are: `DRAFTED`, `APPROVED`, `PROVISIONAL`, `COMPILED`, `BUILDING`, `BUILT`, `REVIEWED`, `COMPLETED`, `PLAN_REVISION_REQUIRED`, `REVIEW_REVISION_REQUIRED`, `ESCALATED`, `ABORTED`. The engine (`promote_spec.py`) owns this set; a spec is never in two states at once.

- **`DRAFTED`** — still being authored (the drafting loop). Nothing is published; the draft self-revises until plan-readiness is green.
- **`APPROVED`** / **`PROVISIONAL`** — the promote step wrote the spec into `specs/` (human acceptance / autonomous default). Compile reads it next; a run still starts only from `COMPILED`.
- **`COMPILED`** — the "approve draft" gate cleared at compile. The task list has been compiled into one task file per task and the spec carries `Status: COMPILED`. This is the **only** state a run may start from — `COMPILED` is unreachable without passing the gate.
- **`BUILDING`** / **`BUILT`** — the build in flight / all tasks `MET`.
- **`REVIEWED`** — review is green; awaiting the commit (or a `pre-commit` stop).
- **`COMPLETED`** — the run committed on the spec's branch. **Terminal.**
- **`PLAN_REVISION_REQUIRED`** / **`REVIEW_REVISION_REQUIRED`** — a gate (Vetting / Sign-off) blocked; the spec drops back to re-plan or re-build.
- **`ESCALATED`** — a run failure (build red or review red). A visible, resumable halt with a consolidated `NNN-ESCALATION`; **not** `ABORTED`.
- **`ABORTED`** — reserved for a human deliberately stopping a spec at a gate.

### Status table

| Status | Lane entry | Tool posture | Exit (status) |
| :--- | :--- | :--- | :--- |
| **DRAFTED** (planning) | B, A (C runs a single pass; D is header-only, no lifecycle) | Read-only — no file edits | Validated draft in `specs/temp/` (`Status: DRAFTED`) |
| **APPROVED** / **PROVISIONAL** (promoted) | B, A | Read-only | Promoted spec in `specs/` (`Status: APPROVED`, or `PROVISIONAL - AUTONOMOUS DEFAULT`); compile follows |
| **Vetting gate** | B, A — optional, when the spec's `vetting: on` | Read-only | Vetting gate cleared on the draft (a block drops the spec to `PLAN_REVISION_REQUIRED`) |
| **COMPILED** (compile) | B, A — mandatory after "approve draft" | Read-only | Spec compiled into one task file per task, `Status: COMPILED`, **session stops** |
| **BUILDING** (build) | B, A — always a *new* session / explicit run, starting from the `COMPILED` spec | Edits within the spec's branch, task scope only | All task files `MET` (`Verify` + `Expect`, content-hash evidence recorded) via `verify.py`; commands pre-approved on lanes A/B → `Status: BUILT` |
| **REVIEWED** (review) | B, A | Read-only | `verify.py report` green (every `R#` outcome observed); missing outcome fails review → `Status: REVIEWED` (a review block drops it to `REVIEW_REVISION_REQUIRED`) |
| **Sign-off gate** | B, A — when the spec's `signoff: on` | Read-only | Human signs off; an unattended run **pauses** here (never refused) |
| **COMPLETED** (commit) | — | — | The run commits on the spec's branch → `Status: COMPLETED` (terminal) |

### Key invariants

- **Spec-first two-step lifecycle.** Step 1 (spec production) ends at the approve step, which compiles the draft into `specs/` (spec + one task file per task), records topic decisions, and stamps the spec `Status: COMPILED`. Step 2 (implementation) is a separate session that builds from the `COMPILED` spec. A spec-producing session never builds in the same session — a run will not start against a spec that is not `COMPILED`.
- **Status checklists are loaded one at a time.** At each status start the agent loads only `references/<name>.md` — never all references. Model tiering per status is situational, loaded only when a harness/model choice is in play.
- **Lane C** is a single pass: edit, verify once (`Verify` + `Expect` via `verify.py`); 3 consecutive failures escalate to Lane B. **Lane D** is informational: the 5-tag header is emitted, but no lifecycle, no gates.
- **Passes are evidence-gated and commands are pre-approved:** a task is `MET` only when its `Verify` exits 0 AND its `Expect` marker matches, with a content-hash evidence block written into the task file (`verify.py` records `sha256` of every owned file); on lanes A/B a first-ever command is approved (`verify.py approve`) before it runs, or the engine refuses with exit 4 before execution (no state change, not an attempt).

### The Socratic gate

Ambiguity (in planning or at scope escalation) is resolved via **guided multiple-choice inquiry, never open-ended questions**:

```text
A (Recommended): <approach> — trade-offs stated.
B: <alternative> — trade-offs stated.
```

Gates are classified before resolution:

- **Blocking** — touches security, database schemas, public APIs, or Lane A criteria. Execution halts until answered or governed by the autonomy policy.
- **Non-blocking** — minor internal scope. The agent states the default and proceeds immediately.

#### Gate engine contract

Blocking gates are resolved **exclusively** through the engine — never by judgment alone:

```text
python .agents/skills/phase-protocol/scripts/resolve_gate.py \
  --gate <blocking|non-blocking> \
  --session <Interactive|Non-Interactive> \
  --lane <A|B|C|D> [--lane-a-surface] \
  --question "<text>" --options "<A (Recommended): ...; B: ...>"
```

Exit code is the contract:

| Exit | Meaning | Side effects |
| :--- | :--- | :--- |
| **0** | Proceed / resolved | Non-blocking: default stated, continue. Autonomous blocking: Recommended Option applied, the decision recorded verbatim in the spec's `Gates:` section (question, options, choice, timestamp) |
| **1** | Halt for human answer | Interactive blocking gate — await the human's reply |
| **2** | Fail-closed | `supervised` non-interactive blocking gate, or any Lane-A surface gate — the pending question and options are recorded in the spec's `Gates:` section, no changes made, clean exit |

The **Lane-A exception is encoded in the engine, never advisory:** gates touching database schema, authentication, or public APIs (pass `--lane-a-surface`) always fail closed, even under `autonomous` policy. Autonomy can shortcut minor architectural defaults; it can never shortcut irreversible or security-relevant choices.

### Session detection & autonomy policy

Before the first gate fires, the session is classified:

- **Interactive** — a human can plausibly respond within the current turn (chat UI, IDE copilot).
- **Non-Interactive** — headless, no human in the loop (CI, scheduled batch, background daemon).
- No signal from the harness → **default Non-Interactive** (fail toward caution).

Gate behavior by session type:

| Gate type | Interactive | Non-Interactive |
| :--- | :--- | :--- |
| Non-blocking | State default, proceed | State default, proceed (unchanged) |
| Blocking | Halt, await human | Governed by the autonomy policy — never hangs |

#### Run mode (the non-interactive autonomy axis)

Declared per spec (frontmatter) and resolved by the lead agent from the session type at trigger time (default: Interactive → `supervised`, Non-Interactive → `unattended`, no signal → `unattended` — fail toward caution; an explicit trigger may override either way). See `run-contract.md`.

- **`supervised`**: a blocking gate in a non-interactive session **fails closed** (exit 2). The run ends "blocked", not "success" — nothing ships without a human answering.
- **`unattended`**: a blocking gate resolves to the **Recommended Option** automatically, subject to strict audit:
  1. The choice is recorded verbatim in the spec's `Gates:` section.
  2. Any spec compiled under an autonomous resolution stays `COMPILED` but its `Gates:` record marks it **autonomous**, and it records **no topic decisions** until a human clears that mark.
  3. Never applies to Lane-A surfaces — those always fail closed.
  4. An unattended run does **not** pause for `signoff: on`; it **pauses at 4.5** and waits for a human to sign off (it is not refused).

### The 4-block response schema (5-tag header)

Every response — including Lane D answers and Lane C micro-edits — carries:

```text
[STATUS: <Status> | Task: <ID> | Lane: <A|B|C|D> | Worktree: <name> | Session: <Interactive|Non-Interactive>]

1. SUMMARY OF UNDERSTANDING
   One-sentence recap of the user input or processed state.
2. ACTIONS TAKEN / DISCOVERY
   Files inspected, searches run, draft plans written to specs/temp/ — cited by path, never pasted. Verification claims carry re-measured evidence: each verify command, the matched Expect marker, and attempt count — from a fresh re-run, never memory of what ran.
3. SOCRATIC GATE / DECISION PROPOSAL
   Guided multiple-choice options with recommended defaults (only if ambiguity exists).
4. NEXT STEP
   The exact execution step that happens on human reply or autonomous resolution. When a task is ESCALATED or any work is unmet, this block states the halt/hand-back — never a silent "done".
```

The five header tags are **Status**, Task, Lane, Worktree (`main` unless a worktree is active), and Session. The `Status:` tag is always a canonical `Status:` value from `DRAFTED` … `ABORTED` — never a step label such as `plan` or `review`:

- **Lanes A/B (spec-backed):** the active spec's lifecycle receipt.
- **Lane C (micro-edit, no spec):** `DRAFTED` while drafting, `BUILDING` while the edit is applied, `BUILT` once its `Verify` passes, `COMPLETED` when done.
- **Lane D (question, no spec):** `COMPLETED` — the header is emitted with no lifecycle and no gates.

### Tool posture per status

| Status | Allowed |
| :--- | :--- |
| DRAFTED (planning) | Read-only: inspect, search, draft in `specs/temp/` |
| Vetting gate | Read-only: vetting gate on the draft |
| COMPILED (compile) | Read-only: engine compile (spec + task files), topic decisions, `COMPILED` stamp |
| BUILDING (build) | Edits on the spec's branch within task `Owns` scope; verification through `verify.py` |
| REVIEWED (review) | Read-only: `verify.py report`, audit |
| Sign-off gate | Read-only: human sign-off |

Scope creep toward a higher lane stops the build: the router reclassifies and announces the escalation before work continues (see `routing.md`).

## Decision Log

### LIFECYCLE-D01 - Single `Status:` receipt replaces the separate stage field
- **Date:** 2026-09-27
- **Why:** A separate stage header and `Status:` value could disagree; one receipt (the state set `DRAFTED…ABORTED`) removes the ambiguity and is drift-testable.

### LIFECYCLE-D02 - `ESCALATED` for failures, `ABORTED` for human stops
- **Date:** 2026-09-27
- **Why:** A run failure must be a visible, resumable halt (consolidated `NNN-ESCALATION`, batch continues), not a silent abort; `ABORTED` is reserved for a human deliberately stopping a spec at a gate.

### LIFECYCLE-D03 - Transitions are engine-owned; promote writes a canonical receipt
- **Date:** 2026-10-19
- **Why:** `Status:` was declared canonical but `promote` wrote the non-canonical `APPROVED`/`PROVISIONAL`, and six statuses had no engine writer (hand-edited drift). `APPROVED`/`PROVISIONAL` joined the canonical set; `verify.py` owns `BUILDING`/`BUILT`/`REVIEWED` (build/report), `resolve_gate.py` owns `PLAN_REVISION_REQUIRED`/`REVIEW_REVISION_REQUIRED` (gate block), and `promote_spec.py transition` is the edge-checked writer for the rest; `check`/`doctor` validate canonicality and a drift test guards `specs/*-SPEC-*.md`.
