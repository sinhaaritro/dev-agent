# TASK 002-13 — migrate `001`, add `BACKLOG.md`, regenerate TOCs

## Role & rules
Implement ONLY this task. Obey the given signatures. Do not plan, do not touch files you
don't Own, do not commit.

## Project overview
Dev-agent: a portable meta-framework that drives coding tasks through a phase protocol
(1-Plan → 2-Handoff → 3-Build → 4-Review → 5-Done).

## Task
One-time migration: `git mv specs/001-tba-001-topic-based-adr-replace-many-adr-files-with-per-subsystem-topic-docs.md`
to `specs/001-SPEC-<slug>.md` and bring its header onto the new `Status:` receipt set +
template (no old status survives). Create `BACKLOG.md` at the repo root with the entry format
(`- [ ] <when> | what | where | who | how`). Regenerate `specs/README.md` and `docs/README.md`
via the engine `toc`. Also rename this spec's own file to `002-SPEC-<slug>.md` and update the
paths referenced by `specs/002-TASK-*.md`.

### Progress
- [ ] git mv 001 → `001-SPEC-<slug>.md`; migrate header/template
- [ ] git mv `002-subagent-...md` → `002-SPEC-<slug>.md`; fix internal path references
- [ ] create BACKLOG.md
- [ ] run `promote_spec.py toc`
- [ ] verify no `Status: DRAFT ` / `Phase:` remains under specs/

## Owns
- `specs/001-tba-001-topic-based-adr-replace-many-adr-files-with-per-subsystem-topic-docs.md`
- `specs/002-subagent-task-files-phase-renumbering-and-full-plan-execution.md`
- `specs/002-TASK-01-new-template-check.md`
- `BACKLOG.md`
- `specs/README.md`
- `docs/README.md`

## Reads / Context (read-only)
- `specs/002-flow-design.md`

## Skills to use
- spec-builder
- map-generator

## Upstream interfaces
(none)

## Verification
```bash
bash -c 'ls specs/001-SPEC-*.md >/dev/null 2>&1 && test -f BACKLOG.md && test -z "$(grep -rn "| Phase:\|Status: DRAFT " specs/ | grep -v README)" && echo MIGRATE-OK'
```
**Expect:** `MIGRATE-OK`
