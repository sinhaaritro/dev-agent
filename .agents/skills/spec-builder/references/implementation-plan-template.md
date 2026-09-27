---
tags: [lowercase-kebab, ...]
vetting: off          # Vetting gate (plan review): on | off
signoff: off          # Sign-off gate: on | off (on => pauses for a human when unattended)
review_revision: auto # review failure: auto (<=3 re-build cycles) | halt (straight to human)
---

# [SPEC-ID]: Feature Title

Status: DRAFTED | Date: YYYY-MM-DD

## 0. Frontmatter

The YAML block above the title is the single, easy-to-flip home for the per-spec
flow flags (set at draft time; §2.1 of the plan spec):

- `tags:` — lowercase-kebab, 2-30 chars, max 7 (mandatory on committed docs).
- `vetting: on|off` — the Vetting (plan review) gate. Default `on` for a
  Lane-A surface, `off` otherwise (token cost).
- `signoff: on|off` — the Sign-off (human "say ok") gate. The **one spec-level
  human point**: in an unattended run `signoff: on` **pauses at 4.5** until a human
  signs off.
- `review_revision: auto|halt` — on a `REVIEWED` failure, `auto` allows up to 3
  re-build cycles before a human; `halt` goes straight to a human.

## 1. Goal & Context

1-2 sentences explaining the business/technical goal.

## 2. The Change (end state, by area)

Ownership rule: a fact lives in exactly one place. Section 2 owns the **choice +
rejected alternative + reason** and points forward ("consequence flagged in
section 3"); section 3 owns the **consequence awaiting sign-off**, referenced by
decision number, and the open questions.

Write this as **thematic subsections, not a flat list of items** — one `###` per
area the change touches (a component, a contract, a subsystem), each stating the
end state for that area.

### <Area / component>

- **<Decision>.** Alternative: <option>. Rejected: <reason>. (consequence flagged in section 3)
- End state: <what is true here after this spec>

### <Area / component>

- **<Decision>.** Alternative: <option>. Rejected: <reason>.
- End state: <what is true here after this spec>

## 3. Risks & Open Questions

> [!IMPORTANT]
> **User Review Required**
> - <consequence of a settled decision awaiting human acceptance> — consequence of a section-2 decision. Acceptable?

### Open Questions

- [ ] Q1: <unsettled choice>? — <what it resolves>; answer before <Task N>, or park as follow-up?

## 4. Affected Files & Contracts

One entry per file. The tag + path is the scope boundary; the contract block
states the shape the file's code must take (interface, signature, behavior).
This section is the **contract source** the task files copy as their `Owns` /
`Reads` context. Files without an interface (migrations, tests, config) carry no
contract block.

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

## 5. Tasks & Outcomes

> This list is the **source** the handoff compiles into one task file per task
> (`NNN-TASK-<NN>-<slug>.md`). The global task list lives **only here** (it is not
> copied into task files). Build order is read from `Depends On`.

**Outcomes:** each task delivers one or more `R#` outcomes; every `R#` must have a
recorded observation by review (reconciliation).

| ID | Outcome (what the user gets) |
|----|------------------------------|
| R1 | <outcome> |
| R2 | <outcome> |

---

### Task 1: <coherent component/behavior>

- Target Files: [NEW] migrations/add_role.sql, [NEW] src/auth/roles.ts
- Depends On: None
- Outcomes: R1
- Verify: `python -m unittest tests.test_role -v`
- Expect: "OK"

### Task 2: <coherent component/behavior>

- Target Files: [MODIFY] src/auth/service.ts
- Depends On: Task 1
- Outcomes: R1, R2
- Verify: `python -m unittest tests.test_auth -v`
- Expect: "OK"

**Task shape (one per task):**

- `Depends On:` — required. `None`, or a `Task N` reference (or list). It forms the
  DAG; a task starts only when every task it depends on is `MET`.
- `Outcomes:` — the `R#` IDs this task delivers (see the Outcomes table).
- `Verify:` / `Expect:` — the **task-level** verification. `Verify` is the exact
  command (run from the repo root); `Expect` is the marker the combined output
  must contain. On PASS the engine records evidence (command, exit, matched marker,
  `sha256` of every owned file) into the task file.

**Authoring rule (both lanes):** every `Verify`/`Expect` pair must be able to fail —
no no-op commands (`true`, `:`, `exit 0`, bare `echo`), no expectation that matches
unconditionally (Expect must not appear in the Verify command line), no command that
selects zero tests — pin the expected count in Expect. This is checked by the engine
(`check`); the judgment "could this fail in the wild?" is yours at authoring time.

**Subtasks are NOT here.** A task's internal step checklist (`### Progress`) lives in
its own task file, written by the handoff compile — it is the coder's own progress
checklist, not a gate and not a section-5 field. RED→GREEN is still permitted at the
coder level (a task may open with an `(expect RED)` subtask) but the task's `Verify`
above is what decides pass/fail.

## 6. Gates

_(empty until a gate runs — §2.1. One entry per gate that ran: which gate
(Vetting / Sign-off / blocking), when, the note, pass/block. A blocked entry
records the issues that triggered `PLAN_REVISION_REQUIRED` / `REVIEW_REVISION_REQUIRED`.
A gate that is off writes nothing.)_

## 7. Verification Commands

- Build Command: <canonical repo build command>
- Test Command: <canonical repo test command>
- Lint Command: <canonical repo lint command>

## 8. Rollback Strategy

The run **never reverts** a mid-build failure — it leaves the working tree dirty for
a human to inspect. On a failure the spec parks as `ESCALATED` (not `ABORTED`): the run
writes `NNN-ESCALATION-<slug>.md` (every `FAILED` task with its attempts + last
output, every `BLOCKED` task, the dirty edits left in the tree) and stops that spec's
branch. Because the run commits only at the end of a spec, a **mid-build** failure has
no commit yet; a **completed-but-wrong** task is re-dispatched to its coder (bounded to
its own `Owns` set). Once a spec's commit lands on its branch, any task reverts as one
`git revert`; each spec has its own branch + commit, so reverting one spec never
touches another.

---
Usage: drafted at `specs/temp/draft-plan.md` during plan; validated with
`promote_spec.py check <draft> --lane <B|A>` (the check lints the `tags:` field,
validates the section-5 Tasks & Outcomes structure, and lints every Verify/Expect
pair); on acceptance promoted to `specs/<NNN>-<SPEC>-<slug>.md` via
`promote_spec.py promote <draft> --lane <B|A> --status <APPROVED|PROVISIONAL>`,
then compiled into task files at handoff via `promote_spec.py compile <spec>`.
Lane A mandates sections 1-8 (plus the 0 Frontmatter); Lane B uses sections 1, 4, 5
only. The `tags:` field is mandatory on committed docs and lives in the YAML
frontmatter block at the top of the file (lowercase-kebab, 2-30 chars, max 7); the
flow flags (`vetting`, `signoff`, `review_revision`) ride in the same block.

## Lane B abbreviated skeleton (sections 1, 4, 5 only)

A Lane B plan carries section 1 (Goal & Context), section 4 (Affected Files &
Contracts), and section 5 (Tasks & Outcomes) only. Section 5 is a single degenerate
task (no subtasks here; the task-level `Verify` is the gate; Lane B has no section 6):

### Task 1: <scope>

- Target Files: [MODIFY] src/foo.ts
- Depends On: None
- Outcomes: R1
- Verify: `python -m unittest tests.test_foo -v`
- Expect: "OK"

`Depends On:` is required: `None` in the canonical single-task shape, a `Task N`
reference when a B plan splits into multiple tasks.

Authoring rule (both lanes): every `Verify`/`Expect` pair must be able to fail —
no no-op commands, no unconditional Expect, no command that selects zero tests.
This is checked by the engine (`check`), but the judgment "could this fail in the
wild?" is yours at authoring time.
