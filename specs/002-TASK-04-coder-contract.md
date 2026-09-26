# TASK 002-04 — portable `coder` contract + bootstrap seeding

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
  04 coder contract

task
  Write `.agents/agents/coder.md` — the portable behavioral contract for the coder subagent:
  role; input = the task file only; fetch more context on demand; return search/replace
  blocks for large files; run the task's listed verification; **never commit, never plan,
  never expand scope, never touch files it does not Own**. Keep it short; the harness adapter
  (model binding + permission surface) is per-harness and lives with it.
  Then update `.agents/skills/bootstrap/SKILL.md` to seed `agents/coder.md` + the adapter
  notes when bootstrapping a new project.

  subtasks                      (static, generation-time — follow, do not check off)
    - create .agents/agents/coder.md with the sections above
    - add the seed step to bootstrap/SKILL.md (and its reference copy if present)
    - note the trivial direct-fix exception (lead may edit directly; recorded `direct`)

Owns
  .agents/agents/coder.md
  .agents/skills/bootstrap/SKILL.md

Reads/Context                     (read-only)
  specs/002-subagent-task-files-phase-renumbering-and-full-plan-execution.md
  .agents/skills/phase-protocol/SKILL.md

Skills to use
  - bootstrap

upstream interfaces
  (none)

verification
  bash -c 'grep -q "never commit" .agents/agents/coder.md && echo CODER-CONTRACT-OK'
  Expect: CODER-CONTRACT-OK
