# TASK 002-06 — run contract in `auto-router` + `system.md`

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
  06 run contract

task
  Add the **run contract** to `auto-router` and `system.md`: a run starts only from an
  explicit trigger (never self-starts) and resolves to `targets` / `mode` (`supervised` |
  `unattended`) / `stop point` (`commit` | `pre-commit`). The **mode default** comes from the
  detected session type (Interactive → supervised, Non-Interactive → unattended; no signal →
  unattended), and the trigger may override either way. Document that a `signoff: on` spec
  **pauses at 4.5** under unattended. Keep it short.

  subtasks                      (static, generation-time — follow, do not check off)
    - document the run contract + Option A default in lane-matrix.md
    - update auto-router SKILL.md to emit it
    - add the run-contract/guardrail line to system.md
    - state the opt-in start condition (allowlist = the cost gate)

Owns
  .agents/skills/auto-router/SKILL.md
  .agents/skills/auto-router/references/lane-matrix.md
  .agents/rules/system.md

Reads/Context                     (read-only)
  specs/002-subagent-task-files-phase-renumbering-and-full-plan-execution.md

Skills to use
  - auto-router

upstream interfaces
  (none)

verification
  bash -c 'grep -q "run contract" .agents/skills/auto-router/references/lane-matrix.md && grep -q "unattended" .agents/skills/auto-router/references/lane-matrix.md && echo RUN-CONTRACT-OK'
  Expect: RUN-CONTRACT-OK
