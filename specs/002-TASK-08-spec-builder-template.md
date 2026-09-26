# TASK 002-08 — spec-builder spec: new template + task-file format

role & rules
  You are a coder. Implement ONLY this task. Obey the given signatures.
  Do not plan, do not touch files you don't Own, do not commit.

project overview
  Dev-agent: a portable meta-framework that drives coding tasks through a phase protocol
  (1-Plan → 2-Handoff → 3-Build → 4-Review → 5-Done).

plan progress            (as written at 2-Handoff; updated live during the run)
  [ ] 01 new-template check + statuses
  [ ] 02 compile + purge/sync/accept
  [ ] 03 verify.py doctor/hash/status/report
  [ ] 04 coder contract
  [ ] 05 phase renumber
  [ ] 06 run contract
  [ ] 07 branch/commit guardrail
  [ ] 08 spec-builder template
  [ ] 09 docs + charts
  [ ] 10 slim skills
  [ ] 11 bootstrap seeds
  [ ] 12 task-cleaner
  [ ] 13 migrate 001 + backlog
  [ ] 14 drift test + final verify

this task
  08 spec-builder template

task
  Update `.agents/skills/spec-builder/references/implementation-plan-template.md` to the new
  section set: 0 Frontmatter (`tags`, `vetting`, `signoff`, `review_revision`), 1 Goal & Context,
  2 The Change (thematic subsections), 3 Risks & Open Questions, 4 Affected Files & Contracts,
  5 Tasks & Outcomes (task -> `Depends On` + `Verify`/`Expect`, with `R#`), 6 Gates, 7 Verification
  Commands, 8 Rollback Strategy. Rewrite `todo-checklist-format.md` for the new task-level verify
  (subtasks are guidance, not checked). Keep `topic-template.md`. Update `spec-builder/SKILL.md`
  to point at the new template and the new `compile`/`purge`/`sync`/`accept` subcommands.

  subtasks                      (static, generation-time — follow, do not check off)
    - rewrite the template sections 0..8
    - rewrite todo-checklist-format for task-level state (MET/STALE derived, subtasks guidance)
    - update SKILL.md pointers + subcommand list
    - keep the `tags:` frontmatter rules

Owns
  .agents/skills/spec-builder/references/implementation-plan-template.md
  .agents/skills/spec-builder/references/todo-checklist-format.md
  .agents/skills/spec-builder/references/topic-template.md
  .agents/skills/spec-builder/SKILL.md

Reads/Context                     (read-only)
  specs/002-subagent-task-files-phase-renumbering-and-full-plan-execution.md
  specs/002-TASK-01-new-template-check.md

Skills to use
  - spec-builder

upstream interfaces
  (none)

verification
  bash -c 'grep -q "Tasks & Outcomes" .agents/skills/spec-builder/references/implementation-plan-template.md && grep -q "Gates" .agents/skills/spec-builder/references/implementation-plan-template.md && echo TEMPLATE-OK'
  Expect: TEMPLATE-OK
