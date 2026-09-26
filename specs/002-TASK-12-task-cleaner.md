# TASK 002-12 — `task-cleaner` scope / `specs/temp` fate

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
  12 task-cleaner

task
  Update `clean.py` + the skill to the new world: evidence lives in the **task files**
  under `specs/`, the gate log lives in the **spec's `Gates:` section**, and approvals are a
  **gitignored** per-spec file. So `specs/temp/` now holds only draft-phase scratch
  (`draft-plan.md`, `active-task.md`) and is safe to purge on approval. Define and implement:
  purge everything in `specs/temp/` except `.gitignore`; never touch `specs/` group files,
  `docs/`, or `BACKLOG.md`; report `purged: N, preserved: M`.

  subtasks                      (static, generation-time — follow, do not check off)
    - retire gate-log.md/verify-state.json/approvals.json as scratch concepts
    - implement the new purge scope + dry-run/status
    - keep the scratchpad guard (refuse targets at/above repo root)
    - add cases to tests/test_clean.py

Owns
  .agents/skills/task-cleaner/scripts/clean.py
  .agents/skills/task-cleaner/SKILL.md
  tests/test_clean.py

Reads/Context                     (read-only)
  specs/002-subagent-task-files-phase-renumbering-and-full-plan-execution.md
  .agents/skills/verification-runner/scripts/verify.py

Skills to use
  - task-cleaner

upstream interfaces
  def clean(temp_dir: Path, preserve: list[str], dry_run: bool) -> tuple[list[str], list[str]]

verification
  python -m unittest tests.test_clean -v
  Expect: OK
