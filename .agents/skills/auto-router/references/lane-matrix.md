# Lane Matrix — Classification, Escalation & Session Detection

Single source of truth for lane criteria, escalation rules, and session detection. Loaded at every triage (auto-router instruction 1).

## 1. Lane table

| Lane | Name | Scope Criteria | Docs Artifact | Socratic Gate | Verification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **D** | Read-Only / Informational | No file mutations. Explanations, comparisons, code Q&A. | None | None - informational, non-mutating | None |
| **C** | Micro-Edit | Single file. No schema, public API, auth, or dependency changes. Diff under ~30 lines. | None (inline diff output) | Non-blocking only | Single pass with `Verify` + `Expect` via `verify.py` (PASS = exit 0 + marker); 3-fail escalates to Lane B |
| **B** | Scoped Multi-File Edit | 2-5 files. No schema/API/auth/security surface touched. No new external dependencies. | Abbreviated `docs/temp/draft-plan.md` (Sections 1, 4, 5 only) via `spec-builder`, promoted to `docs/specs/` on approval (no ADRs unless a decision surfaces) | Non-blocking by default; blocking only if scope creeps toward Lane A criteria | Full circuit breaker (3-retry) via `verification-runner` |
| **A** | Full SDLC | >5 files, OR touches database schema, public API contracts, auth/security, or introduces a new architectural dependency. | Full implementation plan (`.agents/skills/spec-builder/references/implementation-plan-template.md`), promoted to `docs/specs/` on plan approval, with an ADR in `docs/decisions/` for every architectural decision | Blocking mandatory for every architectural decision point | Full circuit breaker + review phase |

## 2. Classification order (top-down)

Walk top-down; the first lane whose criteria fit wins:

1. Non-mutating (no file changes implied)? -> **D**
2. Single file, diff under ~30 lines, no schema/API/auth/dependency surface? -> **C**
3. 2-5 files, no Lane-A surface (schema/API/auth/security, new external deps)? -> **B**
4. Otherwise (>5 files, any Lane-A surface, or new architectural dependency)? -> **A**

File count is a heuristic, not a rule: surface triggers always win. A request touching many files can be a lower lane; a single-file edit can be Lane A.

## 3. Escalation rules

1. **Escalate upward immediately and announce it.** Higher-lane criterion revealed mid-execution (e.g., a Lane C edit touches an auth middleware): reclassify now, halt, report before continuing. Never ask permission — only announce.
2. **Never de-escalate without explicit human confirmation** — that would skip planning artifacts already assumed to exist.
3. **Ambiguous lane? Choose the higher one.** Over-scoping a small task costs less than under-scoping a schema change.
4. **Never auto-escalate Lane D.** "Explain, then fix" splits: answer in D (read-only), then re-triage the change separately.

## 4. Session detection

- **Interactive:** a human can plausibly respond within the current turn (chat UI, IDE copilot).
- **Non-Interactive:** headless with no human in the loop for this invocation (CI, scheduled batch, background daemon).
- No signal from the harness -> **default Non-Interactive** (fail toward caution).

## 5. Worked examples

Canonical:

- "What's the time complexity of this sort?" -> **D** (read-only, informational).
- "Rename this variable in `utils.ts`." -> **C** (single file, small diff, no surface).
- "Extract this logic into a shared helper used by three call sites." -> **B** (multi-file, no Lane-A surface).
- "Add a new `refresh_token` column and update the auth flow." -> **A** (schema + auth trigger, regardless of file count).

Ambiguous:

- **Docs-only multi-file edit** ("Update the README and the architecture doc"). Two files, no code, no surface -> **B** — surface criteria decide, not code-to-doc ratio; one doc file would be **C**.
- **"Explain, then fix" split** -> answer in **D**, re-triage the fix separately (likely C or B by blast radius). Never auto-escalate D into a single mutating run.
- **Mid-flight escalation C -> B** — a C edit reveals a second file must change for the build to pass. Reclassify immediately, announce, continue under B's contract (abbreviated draft plan, circuit breaker). No asking permission, no silent continuation as C.
