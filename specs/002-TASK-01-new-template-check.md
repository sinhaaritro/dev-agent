# TASK 002-01 — new-template `check` + canonical `Status:` set

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
  01 new-template check + canonical Status: set

task
  Make `promote_spec.py check` validate the NEW spec template and retire the old
  `### Task N:` / `Phase Gate:` structure check. `check` must:
  - accept the new section set (0 Frontmatter, 1 Goal, 2 The Change, 3 Risks, 4 Affected Files,
    5 Tasks & Outcomes, 6 Gates, 7 Verification, 8 Rollback);
  - parse the new §5 task shape (`### Task N:` with `Depends On:` and a `Verify:`/`Expect:`
    pair) and require at least one task;
  - keep the existing Verify/Expect lint (no no-op command, no empty Expect, Expect must not
    appear in the Verify line);
  - treat the canonical `Status:` set as `DRAFTED`, `COMPILED`, `BUILDING`, `BUILT`,
    `REVIEWED`, `COMPLETED`, `PLAN_REVISION_REQUIRED`, `REVIEW_REVISION_REQUIRED`,
    `ESCALATED`, `ABORTED`;
  - print `structure: ok` on success and exit 0.

  subtasks                      (static, generation-time — follow, do not check off)
    - read `check_draft()` and `_validate_task_dag()` in promote_spec.py
    - replace the old task-DAG parse with the new §5 parse (Task -> Depends On + Verify/Expect)
    - drop the `Phase Gate` and `>=1 subtask` requirements
    - accept sections 0..8 (update the Lane A section expectations)
    - print `structure: ok`; keep the tag lint
    - add a case to tests/test_promote_spec.py

Owns
  .agents/skills/spec-builder/scripts/promote_spec.py
  tests/test_promote_spec.py

Reads/Context                     (read-only)
  specs/002-subagent-task-files-phase-renumbering-and-full-plan-execution.md
  .agents/skills/spec-builder/references/implementation-plan-template.md

Skills to use
  - spec-builder

upstream interfaces
  def find_root() -> Path
  def parse_sections(text: str) -> set[int]
  def check_draft(draft: Path, lane: str) -> tuple[bool, list[int], list[str]]
  def _is_noop_verify(cmd: str) -> bool

verification
  python .agents/skills/spec-builder/scripts/promote_spec.py check specs/002-subagent-task-files-phase-renumbering-and-full-plan-execution.md --lane A
  Expect: structure: ok
