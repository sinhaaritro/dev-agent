# TASK 002-14 — drift test + full canonical verification

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
  14 drift test + final verify

task
  Add `tests/test_drift_phases.py` asserting the canonical sets appear exactly and the old
  ones are gone: phases `1-Plan`, `1.5-Vetting`, `2-Handoff`, `3-Build`, `4-Review`,
  `4.5-Sign-off`, `5-Done`; statuses `DRAFTED/COMPILED/BUILDING/BUILT/REVIEWED/COMPLETED/
  PLAN_REVISION_REQUIRED/REVIEW_REVISION_REQUIRED/ESCALATED/ABORTED`; no `Phase:` field; no
  `1.5-Handoff`/`2-Build`/`3-Review`. Fill the `AGENTS.md` command placeholders with the
  canonical Build/Test/Lint commands.

  subtasks                      (static, generation-time — follow, do not check off)
    - write the drift test over .agents, docs, README.md, AGENTS.md
    - fill AGENTS.md commands
    - run the full suite + lint

Owns
  tests/test_drift_phases.py
  AGENTS.md

Reads/Context                     (read-only)
  specs/002-subagent-task-files-phase-renumbering-and-full-plan-execution.md

Skills to use
  - verification-runner

upstream interfaces
  (none)

verification
  python .agents/skills/verification-runner/scripts/verify.py run --command "python -m unittest discover -s tests -v" --expect "OK" --task T14 --lane A
  Expect: OK
