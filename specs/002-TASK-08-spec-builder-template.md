# TASK 002-08 — spec-builder spec: new template + task-file format

## Role & rules
Implement ONLY this task. Obey the given signatures. Do not plan, do not touch files you
don't Own, do not commit.

## Project overview
Dev-agent: a portable meta-framework that drives coding tasks through a phase protocol
(1-Plan → 2-Handoff → 3-Build → 4-Review → 5-Done).

## Task
Update `.agents/skills/spec-builder/references/implementation-plan-template.md` to the new
section set: 0 Frontmatter (`tags`, `vetting`, `signoff`, `review_revision`), 1 Goal & Context,
2 The Change (thematic subsections), 3 Risks & Open Questions, 4 Affected Files & Contracts,
5 Tasks & Outcomes (task → `Depends On` + `Verify`/`Expect`, with `R#`), 6 Gates, 7 Verification
Commands, 8 Rollback Strategy. Rewrite `todo-checklist-format.md` for the new task-level verify
(subtasks are the coder's own progress checklist, not a gate). Keep `topic-template.md`. Update
`spec-builder/SKILL.md` to point at the new template, the task-file schema, and the new
`compile`/`purge`/`sync`/`accept` subcommands.

### Progress
- [x] rewrite the template sections 0..8
- [x] rewrite todo-checklist-format for task-level state (derived MET/STALE; Progress = own steps)
- [x] update SKILL.md pointers + subcommand list
- [x] keep the `tags:` frontmatter rules

## Owns
- `.agents/skills/spec-builder/references/implementation-plan-template.md`
- `.agents/skills/spec-builder/references/todo-checklist-format.md`
- `.agents/skills/spec-builder/references/topic-template.md`
- `.agents/skills/spec-builder/SKILL.md`

## Reads / Context (read-only)
- `specs/002-SPEC-subagent-task-files-full-plan.md`
- `specs/002-TASK-01-new-template-check.md`

## Skills to use
- spec-builder

## Upstream interfaces
(none)

## Verification
```bash
bash -c 'grep -q "Tasks & Outcomes" .agents/skills/spec-builder/references/implementation-plan-template.md && grep -q "Gates" .agents/skills/spec-builder/references/implementation-plan-template.md && echo TEMPLATE-OK'
```
**Expect:** `TEMPLATE-OK`
