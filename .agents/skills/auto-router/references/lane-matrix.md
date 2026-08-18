# Lane Matrix — Classification, Escalation & Session Detection

Single source of truth for lane criteria, escalation rules, and session detection. Loaded at every triage (auto-router SKILL.md instruction 1). Semantics derive verbatim from `docs/architecture/000-modular-agent-orchestration-v7.md` section 4.

## 1. Lane table

| Lane | Name | Scope Criteria | Docs Artifact | Socratic Gate | Verification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **D** | Read-Only / Informational | No file mutations. Explanations, comparisons, code Q&A. | None | None - informational, non-mutating | None |
| **C** | Micro-Edit | Single file. No schema, public API, auth, or dependency changes. Diff under ~30 lines. | None (inline diff output) | Non-blocking only | Single pass; 3-fail escalates to Lane B |
| **B** | Scoped Multi-File Edit | 2-5 files. No schema/API/auth/security surface touched. No new external dependencies. | Abbreviated `docs/temp/draft-plan.md` (Sections 1, 3, 4 only) via `spec-builder`, promoted to `docs/specs/` on approval (no ADRs unless a decision surfaces) | Non-blocking by default; blocking only if scope creeps toward Lane A criteria | Full circuit breaker (3-retry) via `verification-runner` |
| **A** | Full SDLC | >5 files, OR touches database schema, public API contracts, auth/security, or introduces a new architectural dependency. | Full implementation plan (`.agents/skills/spec-builder/references/implementation-plan-template.md`), promoted to `docs/specs/` on plan approval, with an ADR in `docs/decisions/` for every architectural decision | Blocking mandatory for every architectural decision point | Full circuit breaker + review phase |

## 2. Classification order (top-down)

Classify the request by walking the criteria top-down; the first lane whose criteria fit wins:

1. Non-mutating (no file changes implied)? -> **Lane D**
2. Single file, diff under ~30 lines, no schema/API/auth/dependency surface? -> **Lane C**
3. 2-5 files, no Lane-A surface (schema/API/auth/security, new external deps)? -> **Lane B**
4. Otherwise (more than 5 files, or any Lane-A surface, or new architectural dependency)? -> **Lane A**

A request can touch many files yet stay mutating, and a request touching exactly one file can still be Lane A (schema/API/auth triggers outrank file count). File count is a heuristic, not a rule: surface triggers always win.

## 3. Escalation rules

1. **Escalate upward immediately and announce it.** If execution reveals a higher-lane criterion (e.g., a Lane C edit turns out to require touching an auth middleware), reclassify now, halt, and report the reclassification to the human before continuing. Never ask permission to escalate - only announce it.
2. **Never de-escalate without explicit human confirmation.** A task never quietly downgrades from A to B; that would skip planning artifacts already assumed to exist.
3. **When the lane is ambiguous, choose the higher lane.** Over-scoping a small task costs less than under-scoping a schema change.
4. **Never auto-escalate Lane D.** If a read-only request implies a change ("explain this, then fix the bug"), split it: answer in Lane D, then re-triage the change request separately.

## 4. Session detection

- The session is **Interactive** if a human can plausibly respond within the current turn (chat UI, IDE copilot session).
- The session is **Non-Interactive** if the harness runs headless with no human in the loop for this invocation (CI-triggered agent, scheduled batch job, background daemon).
- If the harness gives no signal either way, **default to Non-Interactive** (fail toward caution).

## 5. Worked examples

### 000 section 4's four canonical cases

- *"What's the time complexity of this sort?"* -> **Lane D** (read-only, informational).
- *"Rename this variable in `utils.ts`."* -> **Lane C** (single file, small diff, no surface).
- *"Extract this logic into a shared helper used by three call sites."* -> **Lane B** (multi-file, no Lane-A surface).
- *"Add a new `refresh_token` column and update the auth flow."* -> **Lane A** (schema + auth trigger, regardless of file count).

### Ambiguous cases

- **Docs-only multi-file edit** — *"Update the README and the architecture doc to reflect the new flow."* Two files, no code, no schema/API/auth surface -> **Lane B**. The surface criteria (not the code-to-doc ratio) decide; a docs-only edit still mutates two files, so Lane C's single-file rule does not apply. If it were one doc file -> **Lane C**.
- **"Explain, then fix" request split** — *"Explain this function, then fix the bug you find."* -> Split: answer the explanation in **Lane D** (read-only, no mutation), then re-triage the fix request separately as its own classification (likely C or B depending on blast radius). Never auto-escalate Lane D into a single mutating run.
- **Mid-flight escalation C -> B** — A Lane C edit to one file reveals a second file must change for the build to pass. -> Reclassify to **Lane B** immediately, announce the escalation to the human, then continue under B's contract (abbreviated draft plan, circuit breaker). Do not ask permission; do not silently keep going as C.