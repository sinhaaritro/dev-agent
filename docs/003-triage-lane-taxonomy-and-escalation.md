---
tags: [triage, lanes, escalation, routing, session]
---

# 003 - Triage, Lane Taxonomy & Escalation

The intent-triage layer: every incoming request is classified into exactly one
Execution Lane before any other work happens, the session type is detected,
candidate skills are recalled, and scope escalation is monitored throughout.

**Skills covered:** `auto-router` (lane classification, escalation, recall
stage 2). The mechanical half of skill recall (`match_skills.py`) is covered
in 002, section 4.

## 1. The four lanes

Single source of truth:
`.agents/skills/auto-router/references/lane-matrix.md`.

| Lane | Name | Scope criteria | Docs artifact | Gate | Verification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **D** | Read-Only / Informational | No file mutations. Explanations, comparisons, code Q&A. | None | None — informational | None |
| **C** | Micro-Edit | Single file; no schema/public-API/auth/dependency changes; diff under ~30 lines | None (inline diff output) | Non-blocking only | Single pass with `Verify` + `Expect` via `verify.py` (PASS = exit 0 + marker); 3 fails escalate to B |
| **B** | Scoped Multi-File Edit | 2–5 files; no schema/API/auth/security surface; no new external dependencies | Abbreviated plan (sections 1, 4, 5), compiled into a spec group on approval | Non-blocking by default; blocking only if scope creeps toward A | Task verify with 3-attempt run-to-exhaustion, then `ESCALATED` |
| **A** | Full SDLC | >5 files, OR database schema, public API contracts, auth/security, OR a new architectural dependency | Full implementation plan, compiled on approval, topic decision per architectural decision | Blocking mandatory at every decision point | Task verify + review, run-to-exhaustion, then `ESCALATED` |

**Surface triggers outrank file count.** File count is a heuristic: a
single-file edit that touches an auth middleware is Lane A; a wide but
surface-free refactor may be Lane B.

### Classification order (top-down, first fit wins)

1. Non-mutating (no file changes implied)? → **D**
2. Single file, diff under ~30 lines, no Lane-A surface? → **C**
3. 2–5 files, no Lane-A surface? → **B**
4. Otherwise → **A**

## 2. Session detection

- **Interactive** — a human can plausibly respond within the current turn.
- **Non-Interactive** — headless, no human in the loop (CI, batch, daemon).
- No harness signal → **default Non-Interactive** (fail toward caution).

The session type feeds two consumers — triage detects it, the rest consume it:

- **Gate behavior** (004, section 3): Interactive blocking gates halt for a
  human; Non-Interactive ones are governed by the autonomy policy.
- **Run mode** (004, section 3): the run contract's `mode` defaults from the
  session type — **Interactive → `supervised`**, **Non-Interactive →
  `unattended`**, **no signal → `unattended`** (fail toward caution). An
  explicit trigger may override either way (`wait for me at 4.5` forces
  `supervised`; `run it overnight` forces `unattended`). See the topic doc
  `docs/run-contract.md`.

## 3. Escalation rules

1. **Upward escalation is automatic and announce-only.** A higher-lane
   criterion revealed mid-execution (e.g., a Lane C edit touches auth
   middleware) → reclassify now, halt, announce to the human, then continue
   under the new lane's contract. The router never asks permission to
   escalate — it only announces.
2. **Downward escalation requires explicit human confirmation.** A task never
   quietly downgrades (that would skip planning artifacts already assumed to
   exist).
3. **Ambiguity defaults to the higher lane.** Over-scoping a small task costs
   less than under-scoping a schema change.
4. **Lane D never auto-escalates.** "Explain this function, then fix the bug"
   splits: answer in D (read-only), then re-triage the fix separately.

5. **Run failures park `ESCALATED`, not `ABORTED`.** When a task exhausts its
   3 verify attempts and no unblocked task remains, the spec is stamped
   **`ESCALATED`** with a consolidated `NNN-ESCALATION-<slug>.md` (every failed
   task with its attempts + last output, every blocked task, the dirty edits
   left in the tree). The run stops **that spec's branch** and the batch
   **continues** to the next spec — a bad spec cannot cascade. `ABORTED` is
   reserved for a human deliberately stopping a spec at a gate. This is
   distinct from the upward re-lane escalation above (which is mid-run and
   announced); here the run itself halts the spec. See `docs/branching.md` and
   `docs/run-contract.md`.

## 4. Worked examples

Canonical:

- "What's the time complexity of this sort?" → **D** (read-only).
- "Rename this variable in `utils.ts`." → **C** (single file, small diff).
- "Extract this logic into a shared helper used by three call sites." → **B**
  (multi-file, no Lane-A surface).
- "Add a new `refresh_token` column and update the auth flow." → **A**
  (schema + auth trigger, regardless of file count).

Ambiguous:

- Docs-only multi-file edit (two files, no code, no surface) → **B**; one doc
  file → **C**. Surface criteria decide, not code-to-doc ratio.
- "Explain, then fix" → D for the answer, separate re-triage for the fix.
- Mid-flight C → B (a second file must change for the build to pass) →
  reclassify, announce, continue under B's contract (abbreviated plan, task
  verify). No asking permission, no silent continuation as C.

## 5. The routing verdict

auto-router's output contract is exactly:

- **Lane** (A/B/C/D)
- **Session** (Interactive/Non-Interactive)
- **candidate skills** (from the two-stage recall — 002, sections 4–5)
- optional **escalation flag**

phase-protocol consumes the verdict into the `[STATUS: ...]` header and drives
the status lifecycle, gates, autonomy, and the 4-block schema. The division is strict:
auto-router owns triage and holds **no gate authority**; phase-protocol owns
gates and **never re-triages the lane**. auto-router never drafts plans, writes
specs, or executes the task — it routes it.

## 6. Recall stage 2 (judgment)

Stage 1 is `match_skills.py` (002, section 4). Stage 2 is judgment: engine
output is candidates only and can never exclude a skill. Thin or zero
candidates → re-read the full `MAP.md` and match by semantic relation; a
skill with zero literal hits can still apply. Absence from the engine's list
is never proof a skill does not apply.
