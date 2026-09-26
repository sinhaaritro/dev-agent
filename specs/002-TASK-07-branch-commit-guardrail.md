# TASK 002-07 — branch-per-spec, commit-terminal, never-merge guardrail

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
  07 branch/commit guardrail

task
  Document the build/commit model in `system.md` and the phase references:
  - specs are authored on `main`; a run creates **one branch per spec off `main` (+worktree)**
    and **never edits `main`**;
  - **commit is terminal** — at spec end the run commits on its branch and stamps `COMPLETED`
    immediately; there are no post-commit checks;
  - **hard guardrail: never merge or push to the default/release branch** — merging is
    human-only, even for headless runs;
  - on failure the spec parks as `ESCALATED` (not `ABORTED`) and the batch continues.

  subtasks                      (static, generation-time — follow, do not check off)
    - add the branch rule + commit-terminal to build.md
    - add the never-merge guardrail to system.md
    - note ESCALATED vs ABORTED and batch-continue in build.md/review.md

Owns
  .agents/rules/system.md
  .agents/skills/phase-protocol/references/build.md
  .agents/skills/phase-protocol/references/review.md

Reads/Context                     (read-only)
  specs/002-subagent-task-files-phase-renumbering-and-full-plan-execution.md

Skills to use
  - phase-protocol

upstream interfaces
  (none)

verification
  bash -c 'grep -qi "never merge" .agents/rules/system.md && grep -qi "commit is terminal" .agents/skills/phase-protocol/references/build.md && echo BRANCH-GUARD-OK'
  Expect: BRANCH-GUARD-OK
