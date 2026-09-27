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

`1-Plan → 1.5-Vetting → 2-Handoff → 3-Build → 4-Review → 4.5-Sign-off →
5-Done`, driven by phase-protocol from auto-router's lane verdict. A spec has a
**single `Status:` receipt** (no separate `Phase:` field) that moves through the
canonical set `DRAFTED / COMPILED / BUILDING / BUILT / REVIEWED / COMPLETED /
PLAN_REVISION_REQUIRED / REVIEW_REVISION_REQUIRED / ESCALATED / ABORTED`:

| Phase | Lane entry | Tool posture | Exit (status) |
| :--- | :--- | :--- | :--- |
| **1-Plan** | B, A (C runs a single pass; D is header-only, no phases) | Read-only — no file edits | Validated draft in `specs/temp/` (`Status: DRAFTED`) |
| **1.5-Vetting** | B, A — optional, when the spec's `vetting: on` | Read-only | Vetting gate cleared on the draft (a block drops the spec to `PLAN_REVISION_REQUIRED`) |
| **2-Handoff** | B, A — mandatory after "approve draft" | Read-only | Spec compiled into one task file per task, `Handoff:` stamp, `Status: COMPILED`, **session stops** |
| **3-Build** | B, A — always a *new* session / explicit run, starting from the `COMPILED` spec | Edits within the spec's branch, task scope only | All task files `MET` (`Verify` + `Expect`, content-hash evidence recorded) via `verify.py`; commands pre-approved on lanes A/B → `Status: BUILT` |
| **4-Review** | B, A | Read-only | `verify.py report` green (every `R#` outcome observed); missing outcome fails review → `Status: REVIEWED` (a review block drops it to `REVIEW_REVISION_REQUIRED`) |
| **4.5-Sign-off** | B, A — when the spec's `signoff: on` | Read-only | Human signs off; an unattended run **pauses** here (never refused) |
| **5-Done** | — | — | The run commits on the spec's branch → `Status: COMPLETED` (terminal) |

Key invariants:

- **Spec-first two-step lifecycle.** Step 1 (spec production) ends at the
  "approve handoff" gate, which compiles the draft into `specs/` (spec + one
  task file per task), records topic decisions, and stamps the spec `COMPILED`
  with a `Handoff:` date. Step 2 (implementation) is a separate session that
  builds from the `COMPILED` spec. A spec-producing session never builds in the
  same session — a run will not start against a spec that is not `COMPILED`.
- **Phase checklists are loaded one at a time.** At each phase start the agent
  loads only `references/<phase>.md` — never all references. Model tiering per
  phase is situational, loaded only when a harness/model choice is in play.
- **Lane C** is a single pass: edit, verify once (`Verify` + `Expect` via
  `verify.py`); 3 consecutive failures escalate to Lane B. **Lane D** is
  informational: the 5-tag header is emitted, but no phases, no gates.
- **Passes are evidence-gated and commands are pre-approved:** a task is `MET`
  only when its `Verify` exits 0 AND its `Expect` marker matches, with a
  content-hash evidence block written into the task file (`verify.py` records
  `sha256` of every owned file); on lanes A/B a first-ever command is approved
  (`verify.py approve`) before it runs, or the engine refuses with exit 4
  before execution (no state change, not an attempt).

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
| **0** | Proceed / resolved | Non-blocking: default stated, continue. Autonomous blocking: Recommended Option applied, the decision recorded verbatim in the spec's `Gates:` section (question, options, choice, timestamp) |
| **1** | Halt for human answer | Interactive blocking gate — await the human's reply |
| **2** | Fail-closed | `supervised` non-interactive blocking gate, or any Lane-A surface gate — the pending question and options are recorded in the spec's `Gates:` section, no changes made, clean exit |

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

### Run mode (the non-interactive autonomy axis)

Declared per spec (frontmatter) and resolved by the lead agent from the
session type at trigger time (default: Interactive → `supervised`,
Non-Interactive → `unattended`, no signal → `unattended` — fail toward
caution; an explicit trigger may override either way). See `docs/run-contract.md`.

- **`supervised`**: a blocking gate in a non-interactive session **fails
  closed** (exit 2). The run ends "blocked", not "success" — nothing ships
  without a human answering.
- **`unattended`**: a blocking gate resolves to the **Recommended Option**
  automatically, subject to strict audit:
  1. The choice is recorded verbatim in the spec's `Gates:` section.
  2. Any spec compiled under an autonomous resolution stays `COMPILED` but
     its `Gates:` record marks it **autonomous**, and it records **no topic
     decisions** until a human clears that mark.
  3. Never applies to Lane-A surfaces — those always fail closed (section 2).
  4. An unattended run does **not** pause for `signoff: on`; it **pauses at
     4.5** and waits for a human to sign off (it is not refused).

## 4. The 4-block response schema (5-tag header)

Every response — including Lane D answers and Lane C micro-edits — carries:

```text
[STATUS: <Status> | Task: <ID> | Lane: <A|B|C|D> | Worktree: <name> | Session: <Interactive|Non-Interactive>]

1. SUMMARY OF UNDERSTANDING
   One-sentence recap of the user input or processed state.
2. ACTIONS TAKEN / DISCOVERY
   Files inspected, searches run, draft plans written to specs/temp/. Verification claims carry re-measured evidence: each verify command, the matched Expect marker, and attempt count — from a fresh re-run, never memory of what ran.
3. SOCRATIC GATE / DECISION PROPOSAL
   Guided multiple-choice options with recommended defaults (only if ambiguity exists).
4. NEXT STEP
   The exact execution step that happens on human reply or autonomous resolution. When a task is ESCALATED or any work is unmet, this block states the halt/handoff — never a silent "done".
```

The five header tags are **Status** (the spec's single lifecycle receipt, e.g.
`2-Handoff` while in that phase or a state like `COMPILED`), Task, Lane,
Worktree (`main` unless a worktree is active), and Session. Lane D answers
carry the header without phases or gates.

## 5. Tool posture per phase

| Phase | Allowed |
| :--- | :--- |
| 1-Plan | Read-only: inspect, search, draft in `specs/temp/` |
| 1.5-Vetting | Read-only: vetting gate on the draft |
| 2-Handoff | Read-only: engine compile (spec + task files), topic decisions, `COMPILED` stamp |
| 3-Build | Edits on the spec's branch within task `Owns` scope; verification through `verify.py` |
| 4-Review | Read-only: `verify.py report`, audit |
| 4.5-Sign-off | Read-only: human sign-off |

Scope creep toward a higher lane stops the build: the router reclassifies and
announces the escalation before work continues (see 003, section 3).
