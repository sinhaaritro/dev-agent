---
tags: [phases, gates, autonomy, socratic, protocol]
---

# 004 - Phases, Gates & Autonomy

The process-governance layer: how a triaged task moves through the SDLC
phases, how Socratic gates are resolved, how autonomy policy governs
non-interactive sessions, and the response schema every reply carries.

**Skills covered:** `phase-protocol` (meta-skill — owns phases, gates,
autonomy, and the response schema exclusively).

## 1. The SDLC phases

`Plan → 1.5-Handoff → Build → Review`, driven by phase-protocol from
auto-router's lane verdict:

| Phase | Lane entry | Tool posture | Exit |
| :--- | :--- | :--- | :--- |
| **1-Plan** | B, A (C runs a single pass; D is header-only, no phases) | Read-only — no file edits | Validated `draft-plan.md` in `specs/temp/` |
| **1.5-Handoff** | B, A — mandatory after approval | Read-only | `specs/temp/handoff.md` written, spec stamped `Handoff: <date>`, **session stops** |
| **2-Build** | B, A — always a *new* session, starting from the promoted spec | Edits within lane scope only | All section-5 subtasks verified green (`Verify` + `Expect`, evidence recorded) via `verify.py`; commands pre-approved on lanes A/B |
| **3-Review** | B, A | Read-only | Spec finalized (`Phase: 3-Review`, section-5 subtasks synced with re-measured evidence), scratchpad purged on acceptance |

Key invariants:

- **Spec-first two-step lifecycle.** Step 1 (spec production) ends at the
  approval gate, which promotes the draft to `specs/`, records topic
  decisions, and records the 1.5 handoff. Step 2 (implementation) is a separate session that
  builds from the promoted spec. A spec-producing session never builds in the
  same session — `build.md` refuses to start without the `Handoff:` marker.
- **Phase checklists are loaded one at a time.** At each phase start the agent
  loads only `references/<phase>.md` (`plan.md`, `handoff.md`, `build.md`,
  `review.md`) — never all references. `references/harness.md` (model tiering
  per phase) is situational, loaded only when a harness/model choice is in
  play.
- **Lane C** is a single pass: edit, verify once (`Verify` + `Expect` via
  `verify.py`); 3 consecutive failures escalate to Lane B. **Lane D** is
  informational: the 5-tag header is emitted, but no phases, no gates.
- **Passes are evidence-gated and commands are pre-approved** (spec 001
  D4/D5): a subtask is done only when its `Verify` exits 0 AND its `Expect`
  marker matches, with evidence recorded in `specs/temp/verify-state.json`; on
  lanes A/B a first-ever command is approved (`verify.py approve`) before it
  runs, or the engine refuses with exit 4 before execution (no state change,
  not an attempt).

## 2. The Socratic gate

Ambiguity (in planning or at scope escalation) is resolved via **guided
multiple-choice inquiry, never open-ended questions**:

```text
A (Recommended): <approach> — trade-offs stated.
B: <alternative> — trade-offs stated.
```

Gates are classified before resolution:

- **Blocking** — touches security, database schemas, public APIs, or Lane A
  criteria. Execution halts until answered or governed by the autonomy policy.
- **Non-blocking** — minor internal scope. The agent states the default and
  proceeds immediately.

### Gate engine contract

Blocking gates are resolved **exclusively** through the engine — never by
judgment alone:

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
| **0** | Proceed / resolved | Non-blocking: default stated, continue. Autonomous blocking: Recommended Option applied, `specs/temp/gate-log.md` appended verbatim (question, options, choice, timestamp) |
| **1** | Halt for human answer | Interactive blocking gate — await the human's reply |
| **2** | Fail-closed | `supervised` non-interactive blocking gate, or any Lane-A surface gate — `specs/temp/escalation.md` written with the pending question and options, no changes made, clean exit |

The **Lane-A exception is encoded in the engine, never advisory:** gates
touching database schema, authentication, or public APIs (pass
`--lane-a-surface`) always fail closed, even under `autonomous` policy.
Autonomy can shortcut minor architectural defaults; it can never shortcut
irreversible or security-relevant choices.

## 3. Session detection & autonomy policy

Before the first gate fires, the session is classified:

- **Interactive** — a human can plausibly respond within the current turn
  (chat UI, IDE copilot).
- **Non-Interactive** — headless, no human in the loop (CI, scheduled batch,
  background daemon).
- No signal from the harness → **default Non-Interactive** (fail toward
  caution).

Gate behavior by session type:

| Gate type | Interactive | Non-Interactive |
| :--- | :--- | :--- |
| Non-blocking | State default, proceed | State default, proceed (unchanged) |
| Blocking | Halt, await human | Governed by the autonomy policy — never hangs |

### Autonomy levels

Declared in `AGENTS.md`:

```yaml
autonomy_level: supervised   # Options: supervised | autonomous
```

- **`supervised`** (default when unset): a blocking gate in a non-interactive
  session **fails closed** (exit 2). The run ends "blocked", not "success" —
  nothing ships without a human answering.
- **`autonomous`**: a blocking gate resolves to the **Recommended Option**
  automatically, subject to strict audit:
  1. The choice is logged verbatim to `specs/temp/gate-log.md` — never purged
     until a human reviews it.
  2. Any spec promoted under autonomous resolution is tagged
     `Status: PROVISIONAL - AUTONOMOUS DEFAULT` until a human clears the tag
     (and records no decisions until then).
  3. Never applies to Lane-A surfaces — those always fail closed (section 2).

## 4. The 4-block response schema (5-tag header)

Every response — including Lane D answers and Lane C micro-edits — carries:

```text
[STATUS: <Phase> | Task: <ID> | Lane: <A|B|C|D> | Worktree: <name> | Session: <Interactive|Non-Interactive>]

1. SUMMARY OF UNDERSTANDING
   One-sentence recap of the user input or processed state.
2. ACTIONS TAKEN / DISCOVERY
   Files inspected, searches run, draft plans written to specs/temp/. Verification claims carry re-measured evidence: each Phase Gate command, the matched Expect marker, and attempt count — from a fresh re-run, never memory of what ran.
3. SOCRATIC GATE / DECISION PROPOSAL
   Guided multiple-choice options with recommended defaults (only if ambiguity exists).
4. NEXT STEP
   The exact execution step that happens on human reply or autonomous resolution. When a subtask is ABANDONed or any work is unmet, this block states the halt/handoff — never a silent "done".
```

The five header tags are Phase, Task, Lane, Worktree (`main` unless a
worktree is active), and Session. Lane D answers carry the header without
phases or gates.

## 5. Tool posture per phase

| Phase | Allowed |
| :--- | :--- |
| Plan | Read-only: inspect, search, draft in `specs/temp/` |
| 1.5-Handoff | Read-only: engine promotion/topic/handoff writes only |
| Build | Edits within the lane's scope (per auto-router `references/lane-matrix.md`); verification through `verify.py` |
| Review | Read-only: audit, sync spec checkboxes, cleanup via `clean.py` |

Scope creep toward a higher lane stops the build: the router reclassifies and
announces the escalation before work continues (see 003, section 3).
