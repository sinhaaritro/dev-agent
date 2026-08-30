---
tags: [lowercase-kebab, ...]
---

# [SPEC-ID]: Feature Title

Status: DRAFT | Phase: 1-Plan | Date: YYYY-MM-DD

## 1. Goal & Context

1-2 sentences explaining the business/technical goal.

## 2. Architectural Decisions & Trade-offs

Ownership rule: a fact lives in exactly one place. Section 2 owns the choice +
rejected alternative + reason and points forward ("consequence flagged in
section 3"); section 3 owns the consequence awaiting sign-off, referenced by
decision number, and the open questions.

1. **<Decision>.** Alternative: <option>. Rejected: <reason>. (consequence flagged in section 3)
2. **<Decision>.** Alternative: <option>. Rejected: <reason>.

## 3. Risks & Open Questions

> [!IMPORTANT]
> **User Review Required**
> - <consequence of a settled decision awaiting human acceptance> — consequence of decision 2.N. Acceptable?

### Open Questions

- [ ] Q1: <unsettled choice>? — <what it resolves>; answer before <Task N>, or park as follow-up?

## 4. Affected Files & Contracts

One entry per file. The tag + path is the scope boundary; the contract block
states the shape the file's code must take (interface, signature, behavior).
Files without an interface (migrations, tests, config) carry no contract block.

- Deleted: none

### [MODIFY] src/auth/service.ts

<one-line purpose>.

- Contract:
  - `signToken(user: User): Promise<string>` — payload now includes `role`
  - `verifyToken(token: string): TokenPayload`

### [NEW] src/middleware/requireRole.ts

<one-line purpose>.

- Contract:
  - exports `requireRole(roles: Role[]): RequestHandler`

## 5. Task DAG

Tasks are units of coherence (one component/behavior); subtasks are units of
atomic action (2-10 minutes). Build order is read from `Depends On`.

### Task 1: <coherent component/behavior>

- Target Files: [NEW] migrations/add_role.sql, [NEW] src/auth/roles.ts
- Depends On: None
- Subtasks:
  - [ ] 1.1 <atomic step>.
    - Input: <what this subtask consumes>
    - Output: <what this subtask produces>
    - Verify: <exact command>
    - Expect: "<marker the output must contain>"
  - [ ] 1.2 <atomic step>.
    - Input: <output of 1.1>
    - Output: <artifact>
    - Verify: <exact command>
    - Expect: "<marker>"
- Phase Gate: <command confirming the whole task is done>

RED→GREEN is permitted, not mandated: a feature task may open with an
`(expect RED)` subtask (Expect: a failing-test marker) before its implementing
subtask; non-feature tasks omit it.

### Completion rules

- State lives on subtasks: `[ ]` pending → `[/]` in progress → `[x]` done.
- A subtask is `[x]` only when Verify exits 0 AND the output matches Expect;
  record evidence (command, exit, matched marker) in docs/temp/verify-state.json.
  Exit 0 alone is never enough; a checkbox with no evidence counts as unmet.
- Before marking `[x]`, run the four passes: (1) implement complete, no
  placeholders; (2) expert re-read, replace the cheap version of each part;
  (3) hunt defects (correctness, integration, portability, performance);
  (4) polish — repeat until a full pass finds nothing.
- An impossible or out-of-scope subtask is never deleted: add
  `ABANDON: <non-empty reason>` under it. An ABANDONed subtask never becomes
  `[x]`; its task never closes; the spec ends in visible handoff, never silent
  completion.
- A task is done only when every subtask is `[x]` AND its Phase Gate is green.
- A task starts only when every task in its `Depends On` is done.
- The spec is done only when every task is done AND a fresh re-run of every
  Phase Gate is green (old evidence is not re-execution).

## 6. Verification Commands

- Build Command: <canonical repo build command>
- Test Command: <canonical repo test command>
- Lint Command: <canonical repo lint command>

## 7. Rollback Strategy

Revert edits in reverse Task DAG order: Task N (...) → ... → Task 1 (...).
If verification fails 3 consecutive times on any subtask the circuit breaker
fires (escalation.md), dirty edits are reverted, and the subtask reverts to
`[ ]`.

---
Usage: drafted at `docs/temp/draft-plan.md` during Phase 1-Plan; validated with
`promote_spec.py check <draft> --lane <B|A>` (the check also lints the `tags:`
field, validates the section-5 Task DAG structure, and lints every
Verify/Expect pair); on acceptance promoted to
`docs/specs/<id>-<feature>.md` via
`promote_spec.py promote <draft> --lane <B|A> --status <APPROVED|PROVISIONAL>`.
Lane A mandates all 7 sections; Lane B uses sections 1, 4, 5 only. The `tags:`
field is mandatory on committed docs and lives in the YAML frontmatter block
at the top of the file (lowercase-kebab, 2-30 chars, max 7); a bare `tags:`
line outside frontmatter is accepted for reading and normalized into
frontmatter by the engine on promote/adr/tag-rename.

## Lane B abbreviated skeleton (sections 1, 4, 5 only)

A Lane B plan carries section 1 (Goal & Context), section 4 (Affected Files &
Contracts), and section 5 (Task DAG) only. Section 5 is a single degenerate
task — no `Phase Gate` (the per-subtask Verify is the gate; Lane B has no
section 6):

### Task 1: <scope>

- Target Files: [MODIFY] src/foo.ts
- Depends On: None
- Subtasks:
  - [ ] 1.1 <atomic step>.
    - Input: <input>
    - Output: <artifact>
    - Verify: <exact command>
    - Expect: "<marker>"

`Depends On:` is required: `None` in the canonical single-task shape, a
`Task N` reference when a B plan splits into multiple tasks.

Lane B completion rules (trimmed): a subtask is `[x]` only when Verify exits 0
AND the output matches Expect (evidence recorded in docs/temp/verify-state.json);
an impossible subtask gets `ABANDON: <non-empty reason>` (visible handoff, never
silent completion); task done = all subtasks `[x]`; spec done = all subtasks
`[x]` with recorded evidence.

Authoring rule (both lanes): every `Verify`/`Expect` pair must be able to
fail — no no-op commands (`true`, `:`, `exit 0`, bare `echo`), no expectation
that matches unconditionally (Expect must not appear in the Verify command
line), no command that selects zero tests — pin the expected count in Expect.
This is checked by the engine (`check`), but the judgment "could this fail in
the wild?" is yours at authoring time.
