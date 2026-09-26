# TASK 002-10 — slim `.agents` skills (detail moved to `docs/`)

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
  10 slim skills

task
  Cut the `.agents/{rules,skills}` files down to the operational minimum (context budget):
  keep the triggers, the exact commands, and the guardrails; replace long explanation with a
  short pointer to the matching `docs/` topic (e.g. "why: docs/lifecycle.md"). Target:
  `phase-protocol/SKILL.md` under ~120 lines, same discipline for the other SKILL.md files.
  Do not lose any normative rule — move it to docs, don't delete it.

  subtasks                      (static, generation-time — follow, do not check off)
    - pick the long prose blocks in each SKILL.md
    - move them to the right docs/ topic; leave a one-line pointer
    - verify every pointer target exists
    - keep frontmatter `name`/`description`/`tags` intact

Owns
  .agents/skills/phase-protocol/SKILL.md
  .agents/skills/auto-router/SKILL.md
  .agents/skills/spec-builder/SKILL.md
  .agents/skills/verification-runner/SKILL.md
  .agents/skills/task-cleaner/SKILL.md
  .agents/rules/system.md

Reads/Context                     (read-only)
  docs/lifecycle.md
  docs/task-files.md
  docs/verification.md
  docs/run-contract.md
  docs/branching.md

Skills to use
  - map-generator

upstream interfaces
  (none)

verification
  bash -c 'test "$(wc -l < .agents/skills/phase-protocol/SKILL.md)" -lt 120 && echo LEAN-OK'
  Expect: LEAN-OK
